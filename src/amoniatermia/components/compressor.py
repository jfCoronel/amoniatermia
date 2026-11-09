"""Modelo semiempirico de compresor alternativo abierto.

Apartado 9.5, ecuaciones 9-1 a 9-10.

Particularizacion al compresor ABIERTO (apartado 9.5.2): el motor es externo,
su calor se disipa al ambiente y NO se incorpora al refrigerante. El balance
sobre la pared ficticia (ec. 9-8) no lleva termino de disipacion del motor, y
la potencia electrica se obtiene de la potencia al eje mediante los
rendimientos del motor y de la transmision (ec. 9-9).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
from scipy.optimize import root

from ..props import Fluid
from ..geometry import CompressorGeometry


#: Nombres de los parametros identificados, en el orden del vector de ajuste.
#: Son NUEVE: los siete de Winandy, Saavedra y Lebrun (2002) mas r_v y eta_ic,
#: que el ap. 9.5.3 incorpora como extension motivada por los datos
#: disponibles. r_v se identifica porque el fabricante no lo publica para este
#: modelo; eta_ic porque r_v por si solo no basta para reproducir la temperatura
#: de descarga: incluso en el extremo superior explorado, r_v = 5.5, el salto
#: entalpico maximo alcanzable (242 kJ/kg) queda por debajo del necesario para
#: el punto de referencia del fabricante (270.9 kJ/kg).
IDENTIFIED = ("AU_su_n", "AU_ex_n", "AU_amb", "A_leak", "C", "alpha_l",
              "W_loss0", "r_v", "eta_ic")


class MissingEfficiency(RuntimeError):
    """Se ha pedido la potencia electrica sin declarar los rendimientos."""


@dataclass
class CompressorParams:
    """Los NUEVE parametros a identificar del apartado 9.5.3.

    AU_su_n : conductancia de calentamiento en aspiracion en el punto nominal
    AU_ex_n : conductancia de enfriamiento en descarga
    AU_amb  : conductancia pared-ambiente
    A_leak  : area de fuga interna equivalente [m2]
    C       : fraccion de espacio muerto [-]
    alpha_l : fraccion de perdidas mecanicas proporcional al trabajo interno
    W_loss0 : perdidas mecanicas constantes [W] (incluye el cierre mecanico)
    r_v     : relacion de volumenes interna EFECTIVA [-]
    eta_ic  : rendimiento isoentropico interno [-]

    Sobre r_v. En un compresor de tornillo o scroll r_v tiene significado
    geometrico directo: la posicion fija del puerto de descarga. El compresor
    abierto seleccionado cierra mediante valvulas accionadas por presion, de
    modo que r_v NO corresponde aqui a ninguna cota de diseno medible: es un
    parametro efectivo que agrega el comportamiento neto de la dinamica real de
    las valvulas. De ahi que deba identificarse (ap. 9.5.1).

    Sobre los rendimientos electromecanicos. `eta_motor` y `eta_transm` NO son
    parametros identificados ni figuran en el capitulo: son datos del motor
    externo y de la transmision. Por defecto valen `None` y la potencia
    electrica falla si se pide, porque entran en el denominador de COP y EER
    por la ec. 9-9 y un valor supuesto ahi contamina el contraste de H1.
    """
    AU_su_n: float = 20.0
    AU_ex_n: float = 20.0
    AU_amb: float = 5.0
    A_leak: float = 0.0
    C: float = 0.03
    alpha_l: float = 0.05
    W_loss0: float = 250.0
    r_v: float = 2.8
    eta_ic: float = 1.0
    n_reexp: float = 1.20
    m_dot_n: float = 0.01
    eta_motor: float | None = None
    eta_transm: float | None = None

    def as_vector(self):
        return np.array([getattr(self, k) for k in IDENTIFIED])

    def set_vector(self, vec) -> None:
        for k, v in zip(IDENTIFIED, vec):
            setattr(self, k, float(v))

    @property
    def eta_electromechanical(self) -> float:
        if self.eta_motor is None or self.eta_transm is None:
            raise MissingEfficiency(
                "eta_motor y/o eta_transm sin declarar. La ec. 9-9 los "
                "necesita para pasar de potencia al eje a potencia electrica, y "
                "esta entra en el denominador de COP y EER (UNE-EN 14511), "
                "luego en el contraste de H1. No pueden suponerse "
                "(CLAUDE.md). Declararlos en data/compresor_bock_f2.yaml con "
                "su procedencia, o pasarlos explicitamente.")
        return self.eta_motor * self.eta_transm

    def as_dict(self):
        return asdict(self)


@dataclass
class CompressorResult:
    m_dot: float          # kg/s
    W_shaft: float        # W  potencia al eje
    W_el: float | None    # W  electrica; None si no se declararon rendimientos
    T_dis: float          # K  temperatura de descarga real
    h_dis: float          # J/kg
    T_wall: float         # K
    eta_v: float
    eta_is: float
    Q_amb: float          # W  disipado al ambiente
    converged: bool
    residuals: tuple = ()
    m_leak: float = 0.0   # kg/s  fuga interna
    choked: bool = False  # tobera de fuga en regimen critico
    w_in: float = 0.0     # J/kg  trabajo interno de compresion

    def as_dict(self):
        return asdict(self)


class SemiEmpiricalCompressor:
    """Compresor alternativo abierto, formulacion de subprocesos elementales."""

    #: Residuo admisible [W] de los dos balances internos (ec. 9-1 y 9-8).
    #: Del orden de 1e-8 de la potencia al eje, que es de unos 2.5 kW.
    TOL_RESIDUO_W = 1.0e-5

    def __init__(self, fluid: Fluid, geom: CompressorGeometry,
                 params: CompressorParams):
        self.fluid = fluid
        self.geom = geom
        self.p = params

    # ------------------------------------------------------------------
    def eta_v(self, P_ad: float, P_ex: float) -> float:
        """Rendimiento volumetrico, ecuacion 9-3."""
        C, n = self.p.C, self.p.n_reexp
        return 1.0 + C - C * (P_ex / P_ad) ** (1.0 / n)

    def _leakage(self, P_su, P_ex, h_dis):
        """Fuga interna mediante tobera equivalente, ap. 9.5.1.

        La fuga va de la descarga a la aspiracion a traves de un area efectiva
        A_leak. El capitulo pide evaluarla «en regimen critico o subcritico
        segun la relacion de presiones», de modo que se resuelve como tobera
        convergente isoentropica con propiedades reales:

            P* = P_ex (2/(gamma+1))^(gamma/(gamma-1))
            P_garganta = max(P_su, P*)            -> bloqueada si P_su < P*
            v_garganta = sqrt(2 (h_ex - h_garganta))
            m_leak = A_leak rho_garganta v_garganta

        La version anterior empleaba la forma incompresible
        A sqrt(2 rho dP), que sobreestima el caudal cuando la relacion de
        presiones supera la critica. Con NH3 (gamma ~ 1.34) esa relacion es de
        ~1.84, y el compresor opera en M-2 en torno a 3.85: la fuga esta
        BLOQUEADA en todo el dominio de trabajo, luego la distincion no es
        academica.

        Devuelve (m_leak, bloqueada).
        """
        if self.p.A_leak <= 0.0 or P_ex <= P_su:
            return 0.0, False
        f = self.fluid
        f.update_PH(P_ex, h_dis)
        h0, s0, g = f.h, f.s, f.gamma
        P_crit = P_ex * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
        choked = P_su < P_crit
        P_thr = max(P_su, P_crit)
        f.update_PS(P_thr, s0)
        h_thr, rho_thr = f.h, f.rho
        vel = np.sqrt(2.0 * max(h0 - h_thr, 0.0))
        return self.p.A_leak * rho_thr * vel, choked

    # ------------------------------------------------------------------
    def _residuals(self, unknowns, P_ad, T_su, P_ex, T_amb):
        """Sistema de dos residuos: calentamiento en aspiracion y balance de
        pared (ecuaciones 9-1 y 9-8).

        NOTA DE NOTACION. El capitulo emplea el subindice «ad» con dos
        significados distintos: en la ec. 9-3 `P_ad` es la presion de ADMISION
        (la relacion P_ex/P_ad es la de compresion, que gobierna la reexpansion
        del espacio muerto), mientras que en la ec. 9-5 `h_ad` y `P_ad` son el
        estado al final de la compresion interna hasta v_in. Aqui se desambigua:
        `P_ad` es siempre la aspiracion y el estado interno se llama `h_ad` /
        `P_int`. Conviene unificarlo en el capitulo.
        """
        T1, T_wall = unknowns
        f = self.fluid
        p = self.p
        T_sat_min = f.Tsat(P_ad) + 1e-3

        # estado de aspiracion real
        f.update_PT(P_ad, T_su)
        h_su = f.h

        # estado 1: tras el calentamiento en la aspiracion. CORREGIDO el
        # 24/09/2026: se acotaba con max(T1, T_su), y por debajo de T_su eso
        # hacia h1 = h_su y el residuo de la ec. 9-1 CONSTANTE, una meseta de
        # -AU_su (T_w - T_su) sobre la que el metodo se detenia. Con el juego
        # adoptado AU_su = 0.0056 W/K y la raiz esta a solo 0.04 K por encima
        # de T_su, de modo que caia en ella a menudo: el compresor devolvia un
        # caudal desviado un 0.02 % y un R3 de 4e-4 de la potencia al eje que
        # se atribuyo a la identificacion. La cota queda ahora en la
        # saturacion, que es lo unico que protege —no evaluar propiedades en la
        # campana— y deja el borde lejos de la raiz fisica.
        f.update_PT(P_ad, max(T1, T_sat_min))
        h1, v1, s1 = f.h, f.v, f.s

        # caudal desplazado (ec. 9-3)
        eta_v = self.eta_v(P_ad, P_ex)
        m_dot = eta_v * self.geom.V_dot_swept / v1

        # compresion hasta el volumen especifico interno (ec. 9-5)
        # El ap. 9.5.1 corrige el valor ideal con el rendimiento isoentropico
        # interno: h_ad = h1 + (h_ad,s - h1)/eta_ic, y exige que la presion de
        # la etapa a volumen constante se evalue en el estado REAL (v_in, h_ad)
        # y no en el ideal. Con eta_ic = 1 se recupera la formulacion original
        # de siete parametros.
        v_in = v1 / p.r_v
        f.update_DS(1.0 / v_in, s1)
        h_ad_s = f.h                                   # ideal, isoentropico
        h_ad = h1 + (h_ad_s - h1) / max(p.eta_ic, 1e-6)
        f.update_DH(1.0 / v_in, h_ad)                  # estado real a v_in
        P_int = f.P
        w_in = (h_ad - h1) + v_in * (P_ex - P_int)
        h2 = h1 + w_in

        # fuga interna (tobera critica o subcritica, ap. 9.5.1)
        m_leak, choked = self._leakage(P_ad, P_ex, h2)
        m_dot = max(m_dot - m_leak, 1e-8)

        # perdidas mecanicas (ec. 9-6)
        W_loss = p.alpha_l * m_dot * w_in + p.W_loss0

        # conductancias (ec. 9-2)
        scale = (m_dot / max(p.m_dot_n, 1e-9)) ** 0.8
        AU_su = p.AU_su_n * scale
        AU_ex = p.AU_ex_n * scale

        # residuo 1: calentamiento en aspiracion (ec. 9-1)
        Q_su = m_dot * (h1 - h_su)
        r1 = Q_su - AU_su * (T_wall - T_su)

        # enfriamiento en descarga (ec. 9-7)
        f.update_PH(P_ex, h2)
        T2 = f.T
        Q_ex = AU_ex * (T2 - T_wall)          # calor cedido por el refrigerante

        # residuo 2: balance sobre la pared ficticia (ec. 9-8)
        Q_amb = p.AU_amb * (T_wall - T_amb)
        r2 = W_loss + Q_ex - Q_su - Q_amb

        cache = dict(m_dot=m_dot, w_in=w_in, h1=h1, h2=h2, T2=T2, s1=s1,
                     W_loss=W_loss, Q_su=Q_su, Q_ex=Q_ex, Q_amb=Q_amb,
                     eta_v=eta_v, h_su=h_su, AU_ex=AU_ex, P_int=P_int,
                     m_leak=m_leak, choked=choked, h_ad=h_ad, h_ad_s=h_ad_s)
        return np.array([r1, r2]), cache

    # ------------------------------------------------------------------
    def solve(self, P_ad: float, T_su: float, P_ex: float,
              T_amb: float = 298.15, tol: float = 1e-6) -> CompressorResult:
        """Resuelve el compresor. Todas las entradas en SI estricto."""
        if P_ex <= P_ad:
            raise ValueError("P_ex debe ser mayor que P_ad")

        # Convergencia juzgada por los RESIDUOS, no por `sol.success`: `hybr`
        # puede declarar exito parado por `xtol` con un residuo de un vatio. Se
        # arranca con T1 junto a T_su —donde esta la raiz cuando AU_su es
        # pequeno— y, si no cierra, desde otros puntos.
        fun = lambda u: self._residuals(u, P_ad, T_su, P_ex, T_amb)[0]
        umbral = self.TOL_RESIDUO_W
        mejor = None
        for x0 in ((T_su + 0.1, T_su + 40.0), (T_su + 0.1, T_su + 150.0),
                   (T_su + 8.0, T_su + 40.0), (T_su + 1.0, T_su + 250.0)):
            sol = root(fun, np.array(x0), method="hybr", tol=tol)
            r = float(np.max(np.abs(sol.fun)))
            if mejor is None or r < mejor[0]:
                mejor = (r, sol)
            if r <= umbral:
                break
        r_max, sol = mejor

        res, c = self._residuals(sol.x, P_ad, T_su, P_ex, T_amb)
        T1, T_wall = sol.x

        # entalpia de descarga real tras el enfriamiento (ec. 9-7)
        h_dis = c["h2"] - c["Q_ex"] / c["m_dot"]
        self.fluid.update_PH(P_ex, h_dis)
        T_dis = self.fluid.T

        W_shaft = c["m_dot"] * c["w_in"] + c["W_loss"]
        # Potencia electrica, ec. 9-9. Solo si se han declarado los
        # rendimientos del motor externo y de la transmision: la distincion
        # entre potencia al eje y potencia electrica no es un detalle contable
        # (ap. 9.5.2) y suponerla contaminaria el denominador de COP y EER.
        try:
            W_el = W_shaft / self.p.eta_electromechanical
        except MissingEfficiency:
            W_el = None

        # rendimiento isoentropico aparente referido al estado de aspiracion
        self.fluid.update_PT(P_ad, T_su)
        h_su, s_su = self.fluid.h, self.fluid.s
        self.fluid.update_PS(P_ex, s_su)
        h_is = self.fluid.h
        eta_is = (h_is - h_su) / max(W_shaft / c["m_dot"], 1e-9)

        return CompressorResult(
            m_dot=c["m_dot"], W_shaft=W_shaft, W_el=W_el, T_dis=T_dis,
            h_dis=h_dis, T_wall=T_wall, eta_v=c["eta_v"], eta_is=eta_is,
            Q_amb=c["Q_amb"], converged=bool(r_max <= umbral),
            residuals=tuple(res), m_leak=c["m_leak"], choked=c["choked"],
            w_in=c["w_in"])

    # ------------------------------------------------------------------
    #: Cotas del ajuste. El capitulo no las publica, pero la tabla 9.8 anota
    #: AU_ex_n, AU_amb y r_v como «limite inferior del rango explorado», lo que
    #: las situa en 1.0, 1.0 y 2.0 respectivamente. El extremo superior de r_v
    #: (5.5) es el que el ap. 9.5.3 declara haber explorado.
    #:
    #: La cota inferior de r_v se ha bajado de 2.0 a 1.2. Motivo: en este
    #: compresor r_v NO es una cota geometrica sino un parametro EFECTIVO que
    #: agrega la dinamica de las valvulas (ap. 9.5.1), de modo que el 2.0 del
    #: capitulo no tiene justificacion fisica. Relajada la cota, el optimo queda
    #: en 1.965: apenas mordia, contra lo que sugiere la anotacion «limite
    #: inferior» de la tabla 9.8.
    BOUNDS = {
        "AU_su_n": (1.0e-3, 1.0e4),
        "AU_ex_n": (1.0, 1.0e4),
        "AU_amb": (1.0, 1.0e3),
        "A_leak": (0.0, 1.0e-5),
        "C": (1.0e-4, 0.30),
        "alpha_l": (0.0, 0.60),
        "W_loss0": (0.0, 5.0e3),
        "r_v": (1.2, 5.5),
        "eta_ic": (0.30, 1.0),
    }

    def identify(self, catalog_points, weights=(1.0, 1.0, 4.0),
                 x0=None, bounds=None, verbose=0):
        """Identificacion de los NUEVE parametros, ecuacion 9-10.

        DECISION METODOLOGICA (ap. 9.4.3.1). La temperatura de descarga entra en
        la funcion objetivo con peso NO NULO. Los procedimientos habituales ajustan
        solo caudal y potencia, lo que produce modelos que reproducen bien el
        rendimiento pero predicen mal T_dis (con w3 = 0 el juego yerra la descarga
        hasta en 94 K). La hipotesis H3 depende criticamente de esa temperatura,
        de modo que el ajuste debe penalizarla explicitamente.

        SOBRE LOS PESOS. `weights` multiplica el RESIDUO, y `least_squares`
        minimiza la suma de sus cuadrados: (1, 1, 4) aqui es w1 = w2 = 1, w3 = 16
        en la ec. 9-10, donde el peso va fuera del cuadrado. El 16 compensa la
        escala: el residuo de T_dis es relativo a la temperatura absoluta, y 1 K
        (0.28 % a 363 K) pesa como un 1.1 % de caudal o potencia.

        SOBRE LA POTENCIA. El catalogo de un compresor ABIERTO publica potencia
        AL EJE, no electrica. El ajuste se hace contra `W_shaft`: llevarlo
        contra `W_el` trasladaria el rendimiento del motor externo a los
        parametros de la maquina, que es justo la separacion que el ap. 9.5.2
        exige mantener para dar contenido cuantitativo a H6.

        Parameters
        ----------
        catalog_points : list of dict
            Cada punto: {P_ad, T_su, P_ex, m_dot, W_shaft, T_dis}, en SI.
            `data.compressor_catalog()` los devuelve en ese formato.
        weights : tuple
            (caudal, potencia al eje, temperatura de descarga), sobre el residuo;
            el peso de la ec. 9-10 es su cuadrado.
        """
        from scipy.optimize import least_squares

        n = len(catalog_points)
        if n < 20:
            import warnings
            warnings.warn(
                f"Solo {n} puntos de catalogo para 9 parametros: problema "
                "probablemente mal condicionado. El ap. 9.5.3 pide >= 20, y "
                "no solo en recuento: deben barrer el mapa P_ad-P_ex de los "
                "modos, no apinarse en un rango estrecho.", stacklevel=2)

        w1, w2, w3 = weights
        falta_Tdis = sum(1 for pt in catalog_points if "T_dis" not in pt)
        if w3 > 0.0 and falta_Tdis > n // 2:
            import warnings
            warnings.warn(
                f"{falta_Tdis} de {n} puntos sin T_dis. AU_ex_n y AU_amb quedan "
                "mal sujetos, y con ellos H3.", stacklevel=2)

        def residuals(vec):
            self.p.set_vector(vec)
            out = []
            for pt in catalog_points:
                try:
                    r = self.solve(pt["P_ad"], pt["T_su"], pt["P_ex"],
                                   pt.get("T_amb", 298.15))
                except Exception:
                    out.extend([10.0, 10.0, 10.0])
                    continue
                out.append(w1 * (r.m_dot - pt["m_dot"]) / pt["m_dot"])
                out.append(w2 * (r.W_shaft - pt["W_shaft"]) / pt["W_shaft"])
                if "T_dis" in pt and w3 > 0.0:
                    out.append(w3 * (r.T_dis - pt["T_dis"]) / pt["T_dis"])
                else:
                    out.append(0.0)
            return np.array(out)

        if x0 is None:
            x0 = self.p.as_vector()
        if bounds is None:
            lo = [self.BOUNDS[k][0] for k in IDENTIFIED]
            hi = [self.BOUNDS[k][1] for k in IDENTIFIED]
            bounds = (lo, hi)
        x0 = np.clip(np.asarray(x0, dtype=float), bounds[0], bounds[1])

        sol = least_squares(residuals, x0, bounds=bounds, method="trf",
                            verbose=verbose)
        self.p.set_vector(sol.x)
        return sol

    # ------------------------------------------------------------------
    def report(self, catalog_points) -> dict:
        """Desviaciones frente al catalogo, por magnitud.

        El ap. 9.5.3 declara capacidad dentro de +-2.7 %, potencia al eje
        dentro de +-6.6 % y temperatura de descarga dentro de +-10.5 K. Esta
        funcion es la que permite comprobarlo en lugar de creerlo.
        """
        dm, dW, dT, fallos = [], [], [], []
        for pt in catalog_points:
            try:
                r = self.solve(pt["P_ad"], pt["T_su"], pt["P_ex"],
                               pt.get("T_amb", 298.15))
            except Exception as exc:
                # Ap. 9.4.4: los casos que no convergen se REGISTRAN con la
                # condicion de contorno que los origino, no se descartan en
                # silencio. Un informe de ajuste que oculta los puntos fallidos
                # dice menos de lo que aparenta.
                fallos.append({"T0": pt.get("T0"), "Tc": pt.get("Tc"),
                               "error": f"{type(exc).__name__}: {exc}"[:120]})
                continue
            dm.append((r.m_dot - pt["m_dot"]) / pt["m_dot"])
            dW.append((r.W_shaft - pt["W_shaft"]) / pt["W_shaft"])
            if "T_dis" in pt:
                dT.append(r.T_dis - pt["T_dis"])
        if not dm:
            return {"n": len(catalog_points), "n_resueltos": 0,
                    "no_convergidos": fallos}
        out = {
            "n": len(catalog_points),
            "n_resueltos": len(dm),
            "no_convergidos": fallos,
            "m_dot": {"max_abs_rel": max(abs(v) for v in dm),
                      "rmse_rel": float(np.sqrt(np.mean(np.square(dm))))},
            "W_shaft": {"max_abs_rel": max(abs(v) for v in dW),
                        "rmse_rel": float(np.sqrt(np.mean(np.square(dW))))},
        }
        if dT:
            out["T_dis"] = {"max_abs_K": max(abs(v) for v in dT),
                            "rmse_K": float(np.sqrt(np.mean(np.square(dT))))}
        return out
