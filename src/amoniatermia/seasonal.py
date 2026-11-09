"""Rendimiento estacional por el metodo de intervalos de UNE-EN 14825:2024 (cap. 12).

Decisiones del autor del 02/10/2026 (`docs/DECISIONES_2026_10_02.md`, 4 a 11):

- Climas: los tres de referencia de la norma (horas del anexo B en calefaccion y
  del anexo D en refrigeracion) y Sevilla, Madrid y Burgos con los climas de
  referencia del CTE (`data/clima/`).
- Aplicaciones de 35, 45 y 55 °C, con la salida variable de las tablas 8 a 10 y
  caudal fijo, el del ensayo nominal de UNE-EN 14511 (30/35, 40/45 y 47/55 a
  A7/6).
- TOL REAL del equipo: la temperatura entera mas baja desde la que todos los
  puntos son admisibles. Por debajo, apoyo electrico con COP 1 (formula 16). La
  norma exige TOL <= -7 °C en el clima medio; si el equipo no la alcanza, el
  resultado lo dice (`cumple_TOL_norma`) y el SCOP no es un valor declarable.
- Pdesignh con Tbiv = TOL real: la maquina cubre el 100 % de la carga hasta su
  TOL, como declara el mercado (mediana Tbiv -7 °C; decision 7 corregida el
  02/10/2026). La Tbiv maxima de la norma (+2 °C en el clima medio) se publica
  como sensibilidad.
- Pdesignc: la potencia en la condicion A de refrigeracion (35 °C, 12/7).
- Cd = 0.9, el valor por defecto de la norma para aire-agua (§3.1.30).
- Sin desescarche ni consumos auxiliares (P_TO, P_SB, P_CK, P_OFF = 0): el SCOP
  y el SEER son cota superior, y SCOP = SCOPon.

Cada punto de carga parcial se resuelve como equilibrio del sistema completo
(M-4 en calefaccion, M-2 en refrigeracion). La norma fija la temperatura de
SALIDA del agua y el modelo toma la de ENTRADA: un lazo de secante sobre la
entrada la ajusta. Entre puntos, interpolacion lineal (§7.6, §5.6), como la
norma.

Las horas por intervalo y las condiciones de ensayo son las de la norma y del
Reglamento (UE) 811/2013; se citan por tabla.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

K = 273.15
CD = 0.9                  # §3.1.30, aire-agua, sin ensayo
CC = 2.5                  # Reglamento (UE) 811/2013, coeficiente de conversion
F1 = 0.03                 # §7.2 y §5.2, controles de temperatura

# --- Tabla B.1: horas por intervalo de calefaccion -------------------------
_TJ_CALOR = list(range(-22, 16))
_H_FRIO = [1, 6, 13, 17, 19, 26, 39, 41, 35, 52, 37, 41, 43, 54, 90, 125, 169, 195, 278, 306,
           454, 385, 490, 533, 380, 228, 261, 279, 229, 269, 233, 230, 243, 191, 146, 150, 97, 61]
_H_MEDIO = [0] * 12 + [1, 25, 23, 24, 27, 68, 91, 89, 165, 173, 240, 280, 320, 357, 356, 303,
                       330, 326, 348, 335, 315, 215, 169, 151, 105, 74]
_H_CALIDO = [0] * 24 + [3, 22, 63, 63, 175, 162, 259, 360, 428, 430, 503, 444, 384, 294]
BINS_CALOR_NORMA = {
    "medio": dict(zip(_TJ_CALOR, _H_MEDIO)),
    "calido": dict(zip(_TJ_CALOR, _H_CALIDO)),
    "frio": dict(zip(_TJ_CALOR, _H_FRIO)),
}
# --- Tabla D.1: horas por intervalo de refrigeracion (solo clima medio) ------
BINS_FRIO_NORMA = dict(zip(range(17, 41), [205, 227, 225, 225, 216, 215, 218, 197, 178, 158, 137,
                                            109, 88, 63, 39, 31, 24, 17, 13, 9, 4, 3, 1, 0]))

# --- §6.3: temperaturas de diseno, bivalente maxima y TOL maxima ------------
TDESIGNH = {"medio": -10, "calido": 2, "frio": -22}
TBIV_MAX = {"medio": 2, "calido": 7, "frio": -7}
TOL_MAX = {"medio": -7, "calido": 2, "frio": -15}

# --- Tablas 8 a 10: salida variable del agua [°C] por clima y aplicacion ----
# {aplicacion: {clima: {Tj: T_salida}}}; en Tdesignh, la salida nominal.
SALIDA = {
    35: {"medio": {-7: 34, 2: 30, 7: 27, 12: 24}, "calido": {2: 35, 7: 31, 12: 26},
         "frio": {-15: 32, -7: 30, 2: 27, 7: 25, 12: 24}},
    45: {"medio": {-7: 43, 2: 37, 7: 33, 12: 28}, "calido": {2: 45, 7: 39, 12: 31},
         "frio": {-15: 41, -7: 38, 2: 33, 7: 30, 12: 26}},
    55: {"medio": {-7: 52, 2: 42, 7: 36, 12: 30}, "calido": {2: 55, 7: 46, 12: 34},
         "frio": {-15: 49, -7: 44, 2: 37, 7: 32, 12: 28}},
}
#: ACS de M-1 y M-3 en los puntos de la recuperacion: los de los mapas del cap. 11.
ACS_ENTRADA_C, ACS_CONSIGNA_C = 35.0, 67.0
#: UNE-EN 14511-2, tablas 12 a 14: condicion nominal A7(6) con el agua de entrada
#: y salida que fija el caudal fijo de cada aplicacion.
NOMINAL_AGUA = {35: (30.0, 35.0), 45: (40.0, 45.0), 55: (47.0, 55.0)}
#: Tabla 4, aplicacion con ventiloconvector y salida fija: 12/7 en A, salida 7 °C.
FRIO_PUNTOS = {"A": 35.0, "B": 30.0, "C": 25.0, "D": 20.0}
FRIO_AGUA = (12.0, 7.0)


# ---------------------------------------------------------------------------
# Climas
# ---------------------------------------------------------------------------
@dataclass
class Clima:
    nombre: str
    bins_calor: dict          # {Tj °C: horas}
    bins_frio: dict           # {Tj °C: horas}
    Tdesignh: int             # °C
    Tbiv_max: int             # °C
    TOL_max: int | None       # °C exigida por la norma; None = no la fija
    ley_salida: str           # clima de la norma cuya salida variable se usa
    procedencia: str = ""


def clima_norma(nombre: str) -> Clima:
    return Clima(nombre, {t: h for t, h in BINS_CALOR_NORMA[nombre].items() if h},
                 dict(BINS_FRIO_NORMA) if nombre == "medio" else {},
                 TDESIGNH[nombre], TBIV_MAX[nombre], TOL_MAX[nombre], nombre,
                 "UNE-EN 14825:2024, tablas B.1 y D.1, §6.3")


def leer_met(ruta) -> np.ndarray:
    """Temperatura seca horaria [°C] de un fichero .MET del CTE (8760 valores)."""
    filas = Path(ruta).read_text(encoding="latin-1").splitlines()[2:]
    T = np.array([float(f.split()[3]) for f in filas if f.strip()])
    if T.size != 8760:
        raise ValueError(f"{ruta}: {T.size} horas, se esperaban 8760")
    return T


def clima_cte(ciudad: str) -> Clima:
    """Sevilla, Madrid o Burgos con el clima de referencia CTE de su zona.

    Intervalos de 1 K con todas las horas del ano: calefaccion por debajo de
    15.5 °C y refrigeracion desde 16.5 °C (la temperatura limite de 16 °C de los
    anexos B y D). Tdesignh: percentil 99.6 % de la serie anual, redondeado al
    entero (decision 8). Tbiv: la del clima medio, +2 °C, o Tdesignh si es mayor.
    La salida variable sigue la ley del clima medio."""
    from . import data as D
    import yaml
    proc = yaml.safe_load((D.data_dir() / "clima" / "procedencia.yaml").read_text(encoding="utf-8"))
    c = proc["ciudades"][ciudad]
    T = leer_met(D.data_dir() / "clima" / c["fichero"])
    Tj = np.rint(T).astype(int)
    calor = {int(t): int((Tj == t).sum()) for t in range(int(Tj.min()), 16) if (Tj == t).any()}
    frio = {int(t): int((Tj == t).sum()) for t in range(17, int(Tj.max()) + 1) if (Tj == t).any()}
    Td = int(round(float(np.percentile(T, 0.4))))
    return Clima(ciudad, calor, frio, Td, max(2, Td), None, "medio",
                 f"CTE DB-HE, clima de referencia {c['zona']} ({c['fichero']})")


def salida_variable(aplicacion: int, clima: Clima, Tj: float) -> float:
    """Salida de agua [°C] en el intervalo Tj: tablas 8 a 10, interpolada en Tj
    entre los puntos de la tabla y Tdesignh (salida nominal); por encima del
    ultimo punto, la pendiente de los dos ultimos."""
    pts = {t: v for t, v in SALIDA[aplicacion][clima.ley_salida].items() if t > clima.Tdesignh}
    pts[clima.Tdesignh] = float(aplicacion)
    xs = sorted(pts)
    ys = [pts[x] for x in xs]
    if Tj <= xs[0]:
        return float(aplicacion)
    if Tj >= xs[-1]:
        a = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return ys[-1] + a * (Tj - xs[-1])
    return float(np.interp(Tj, xs, ys))


# ---------------------------------------------------------------------------
# Calculo de la norma, sobre puntos ya resueltos
# ---------------------------------------------------------------------------
def _interp(puntos: dict, T: float, campo: str) -> float:
    """Interpolacion lineal entre los dos puntos mas proximos; por encima del
    ultimo, extrapolacion con los dos ultimos (§7.6: C y D); por debajo del
    primero, el valor del primero."""
    xs = sorted(puntos)
    ys = [puntos[x][campo] for x in xs]
    if len(xs) == 1 or T <= xs[0]:
        return ys[0]
    if T >= xs[-1]:
        return ys[-1] + (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) * (T - xs[-1])
    return float(np.interp(T, xs, ys))


def cop_bin(cop_d: float, CR: float, Cd: float = CD) -> float:
    """Formulas (10) y (23): ciclo marcha/paro de aire-agua."""
    CR = min(CR, 1.0)
    return cop_d * CR / (Cd * CR + 1.0 - Cd)


#: Sensibilidad al desescarche (decision 10): perdida de COP en un ciclo de escarcha
#: y desescarche frente al regimen seco, 7.25 a 9.85 % segun la impulsion (Wang et
#: al., Building and Environment, 2024, doi:10.1016/j.buildenv.2024.112258). Se
#: aplica un 10 % a los intervalos con aire a 5 °C o menos.
DESESCARCHE = {"factor_COP": 0.90, "T_max_C": 5}


def scop(bins: dict, Tdesignh: float, Pdesignh: float, puntos: dict, TOL: float,
         Cd: float = CD, desescarche: dict | None = None) -> dict:
    """Formulas (16), (17) y (20). `puntos`: {T °C: {"P": W, "COP": -}} con T >= TOL.
    Devuelve SCOPon (= SCOP sin auxiliares), SCOPnet, la energia del apoyo y la
    tabla por intervalo."""
    num = den = den_net = num_net = elbu_tot = 0.0
    filas = []
    for Tj, h in sorted(bins.items()):
        if h <= 0:
            continue
        Ph = Pdesignh * (Tj - 16.0) / (Tdesignh - 16.0)
        if Ph <= 0:
            continue
        if Tj < TOL:
            Pdh, cop_d, cb = 0.0, float("nan"), float("nan")
            elbu = Ph
            consumo = elbu
        else:
            Pdh = _interp(puntos, Tj, "P")
            cop_d = _interp(puntos, Tj, "COP")
            if desescarche and Tj <= desescarche["T_max_C"]:
                cop_d *= desescarche["factor_COP"]
            CR = Ph / Pdh
            cb = cop_bin(cop_d, CR, Cd) if CR < 1.0 else cop_d
            elbu = max(0.0, Ph - Pdh)
            consumo = (Ph - elbu) / cb + elbu
            num_net += h * (Ph - elbu)
            den_net += h * (Ph - elbu) / cb
        num += h * Ph
        den += h * consumo
        elbu_tot += h * elbu
        filas.append({"Tj": Tj, "h": h, "Ph": Ph, "Pdh": Pdh, "COPd": cop_d, "COPbin": cb,
                      "elbu": elbu})
    s_on = num / den
    return {"SCOPon": s_on, "SCOP": s_on, "SCOPnet": num_net / den_net if den_net else float("nan"),
            "eta_s": 100.0 * (s_on / CC - F1), "Q_H_kWh": num / 1e3, "Q_elbu_kWh": elbu_tot / 1e3,
            "fraccion_apoyo": elbu_tot / num, "intervalos": filas}


def seer(bins: dict, Pdesignc: float, puntos: dict, Cd: float = CD) -> dict:
    """Formulas (6) a (8) y (10). `puntos`: {T °C: {"P": W, "EER": -}} en A a D."""
    num = den = 0.0
    filas = []
    TA, TD = max(puntos), min(puntos)
    for Tj, h in sorted(bins.items()):
        if h <= 0:
            continue
        Pc = Pdesignc * (Tj - 16.0) / (35.0 - 16.0)
        Tq = min(max(Tj, TD), TA)          # fuera de A..D, el EERbin de A o de D
        Pdc = _interp(puntos, Tq, "P")
        eer_d = _interp(puntos, Tq, "EER")
        CR = Pc / Pdc
        eb = cop_bin(eer_d, CR, Cd) if CR < 1.0 else eer_d
        num += h * Pc
        den += h * Pc / eb
        filas.append({"Tj": Tj, "h": h, "Pc": Pc, "Pdc": Pdc, "EERd": eer_d, "EERbin": eb})
    s = num / den
    return {"SEERon": s, "SEER": s, "eta_s": 100.0 * (s / CC - F1), "Q_C_kWh": num / 1e3,
            "intervalos": filas}


# ---------------------------------------------------------------------------
# Puntos de operacion con el modelo
# ---------------------------------------------------------------------------
def admisible(sol, variante: str = "base") -> bool:
    """`base`: la admisibilidad del modelo (solo la zona sin limites, 140 °C).
    `refrigeracion_suplementaria`: la variante de diseno con tapa de cilindro
    refrigerada, en que esa zona del diagrama tambien es admisible (decision 6,
    sensibilidad).
    `sin_envolvente`: un compresor ideal sin envolvente ni limite de descarga; todo punto
    valido es admisible. Muestra la tendencia del fluido; fuera de la envolvente los
    polinomios del compresor extrapolan."""
    if variante == "base":
        return bool(sol.admissible)
    if variante == "sin_envolvente":
        return bool(sol.valid)
    if variante != "refrigeracion_suplementaria":
        raise ValueError(variante)
    lim = sol.envelope.get("limites", {})
    otros = [v["estado"] for k, v in lim.items() if k != "diagrama_aplicacion"]
    zona = lim.get("diagrama_aplicacion", {}).get("valor")
    return bool(sol.valid and "incumple" not in otros
                and zona in ("sin_limites", "refrigeracion_suplementaria"))


class Agua:
    """Entalpia del agua liquida con un AbstractState reutilizado (SI)."""
    P = 3.0e5

    def __init__(self):
        import CoolProp
        self.s = CoolProp.AbstractState("HEOS", "Water")

    def h(self, T):
        import CoolProp
        self.s.update(CoolProp.PT_INPUTS, self.P, T)
        return self.s.hmass()

    def T(self, h):
        import CoolProp
        self.s.update(CoolProp.HmassP_INPUTS, h, self.P)
        return self.s.T()


@dataclass
class Punto:
    modo: str
    T_aire_C: float
    T_in_C: float
    T_out_C: float
    m_agua: float
    P: float                  # W entregados (calor) o absorbidos (frio), positivos
    W_el: float
    COP: float                # COP o EER segun el modo
    T_dis_C: float
    zona: str
    valido: bool
    admisible: dict = field(default_factory=dict)
    sol: object = None
    rpm: float = float("nan")         # velocidad del compresor
    regimen: str = "plena"            # plena | modulada | minima (velocidad variable)
    Q_acs: float = 0.0                # W al ACS (M-1 y M-3)


class Evaluador:
    """Resuelve puntos de M-4 y M-2 a la temperatura de SALIDA del agua pedida."""

    def __init__(self, circuito=None, recalentamiento=5.0, subenfriamiento=2.0, V_frontal=3.30):
        from . import campaign as C
        self.c = circuito or C.build_circuit()[0]
        self.sp_kw = dict(superheat=recalentamiento, subcooling=subenfriamiento)
        self.V = V_frontal
        self.agua = Agua()
        self.cache = {}
        self.n_soluciones = 0
        self.no_validos = []
        comp = self.c.compressor
        #: Velocidad variable (decisión P4 del autor, 15/10/2026): solo si el compresor la
        #: admite (polinomios a varias velocidades).
        self.rpm_max = getattr(comp, "rpm_max", comp.geom.n_rpm)
        self.rpm_min = getattr(comp, "rpm_min", comp.geom.n_rpm)

    def _velocidad(self, rpm):
        rpm = self.rpm_max if rpm is None else float(rpm)
        comp = self.c.compressor
        if hasattr(comp, "fija_velocidad"):
            comp.fija_velocidad(rpm)
        elif abs(rpm - comp.geom.n_rpm) > 1e-6:
            raise ValueError("este compresor no admite velocidad variable")
        return rpm

    def _aire(self, T_C, modo):
        from .circuit import AirState
        if modo == "M-2":
            return AirState(T=T_C + K, V_frontal=self.V)
        # Bulbo humedo 1 K por debajo del seco (§6.3); por debajo de -10 °C la
        # norma no lo define y se mantiene el mismo criterio.
        return AirState.at(T=T_C + K, V_frontal=self.V, T_wb=T_C - 1.0 + K)

    def resolver(self, modo, T_aire_C, T_in_C, m_agua, rpm=None) -> Punto:
        """Un punto de M-4 o M-2 (o de M-3 o M-1, con el ACS de los mapas del cap. 11: entrada
        a 35 °C y consigna de 67 °C) a la velocidad `rpm` (por defecto, la máxima)."""
        from .circuit import Boundary, Setpoints, WaterStream, MODES
        from . import indicators as I
        rpm = self._velocidad(rpm)
        clave = (modo, round(T_aire_C, 3), round(T_in_C, 4), round(m_agua, 5), round(rpm, 2))
        if clave in self.cache:
            return self.cache[clave]
        sp_kw = dict(self.sp_kw)
        acs = None
        if modo in ("M-1", "M-3"):
            acs = WaterStream(ACS_ENTRADA_C + K)
            sp_kw["T_acs"] = ACS_CONSIGNA_C + K
        bc = Boundary(air=self._aire(T_aire_C, modo), m_dot_air=None,
                      clima=WaterStream(T_in_C + K, m_agua), acs=acs, T_amb=T_aire_C + K)
        s = self.c.solve(modo, bc, Setpoints(**sp_kw))
        self.n_soluciones += 1
        if not s.valid:
            # Continuacion: arrancar desde la solucion valida mas cercana ya resuelta
            # (mismo modo y caudal; en aire, agua y velocidad). Un punto que no converge
            # por motivos numericos no debe confundirse con uno no admisible.
            vec = [p for k, p in self.cache.items()
                   if k[0] == modo and k[3] == clave[3] and p.valido]
            if vec:
                c_ = min(vec, key=lambda p: abs(p.T_aire_C - T_aire_C) + abs(p.T_in_C - T_in_C)
                         + abs(p.rpm - rpm) / 100.0)
                s2 = self.c.solve(modo, bc, Setpoints(**sp_kw), x0=dict(c_.sol.unknowns))
                self.n_soluciones += 1
                if s2.valid or s2.max_residual < s.max_residual:
                    s = s2
            if not s.valid:
                self.no_validos.append((modo, T_aire_C, T_in_C, float(s.max_residual), rpm))
        Q = abs(s.Q_clima)
        signo = 1.0 if modo in ("M-3", "M-4") else -1.0
        T_out = self.agua.T(self.agua.h(T_in_C + K) + signo * Q / m_agua) - K
        e = I.energy(s, MODES[modo])
        ind = {"M-4": e.COP, "M-3": e.COP, "M-2": e.EER, "M-1": e.EER}[modo]
        lim = s.envelope.get("limites", {})
        p = Punto(modo, T_aire_C, T_in_C, T_out, m_agua, Q, e.W_el, ind, s.T_dis - K,
                  lim.get("diagrama_aplicacion", {}).get("valor", "—"), s.valid,
                  {v: admisible(s, v) for v in ("base", "refrigeracion_suplementaria", "sin_envolvente")}, s,
                  rpm=rpm, Q_acs=abs(s.Q_acs or 0.0))
        self.cache[clave] = p
        return p

    def a_salida(self, modo, T_aire_C, T_out_C, m_agua, tol_K=0.02, max_it=8,
                 rpm=None, T_in_ini=None) -> Punto:
        """Secante sobre la entrada hasta que la salida es la pedida."""
        cp = 4180.0
        calor = modo in ("M-3", "M-4")
        ini = T_in_ini if T_in_ini is not None else T_out_C + (-1 if calor else 1) * 5.0
        p0 = self.resolver(modo, T_aire_C, ini, m_agua, rpm)
        dT = p0.P / (m_agua * cp)
        x1 = T_out_C - dT if calor else T_out_C + dT
        x0, f0 = p0.T_in_C, p0.T_out_C - T_out_C
        if abs(f0) < tol_K or not p0.valido:
            return p0
        p1 = self.resolver(modo, T_aire_C, x1, m_agua, rpm)
        for _ in range(max_it):
            f1 = p1.T_out_C - T_out_C
            if abs(f1) < tol_K or not p1.valido:
                return p1
            if f1 == f0:
                break
            x0, x1, f0 = x1, x1 - f1 * (x1 - x0) / (f1 - f0), f1
            p1 = self.resolver(modo, T_aire_C, x1, m_agua, rpm)
        return p1

    def a_carga(self, modo, T_aire_C, T_out_C, m_agua, P_obj, tol_rel=0.005, max_it=8) -> Punto:
        """Velocidad variable (UNE-EN 14825, equipos de capacidad variable; decisión P4 del
        15/10/2026): el punto a la salida pedida cuya capacidad iguala la carga `P_obj`.

        - `plena`: ni a la velocidad máxima se cubre la carga (el resto, apoyo o déficit).
        - `minima`: a la velocidad mínima la capacidad aún supera la carga; el equipo funciona
          ahí con marcha/paro (Cd sobre la relación de capacidad a esa velocidad).
        - `modulada`: secante sobre la velocidad hasta |P/P_obj - 1| < `tol_rel`.
        """
        p_max = self.a_salida(modo, T_aire_C, T_out_C, m_agua, rpm=self.rpm_max)
        if not p_max.valido or p_max.P <= P_obj * (1.0 + tol_rel) or self.rpm_min >= self.rpm_max:
            p_max.regimen = "plena"
            return p_max
        n1 = max(self.rpm_min, min(self.rpm_max, self.rpm_max * P_obj / p_max.P))
        p1 = self.a_salida(modo, T_aire_C, T_out_C, m_agua, rpm=n1, T_in_ini=p_max.T_in_C)
        n0, f0 = self.rpm_max, p_max.P - P_obj
        for _ in range(max_it):
            f1 = p1.P - P_obj
            if not p1.valido:
                break
            if abs(f1) <= tol_rel * P_obj:
                p1.regimen = "modulada"
                return p1
            if n1 <= self.rpm_min + 1e-6 and f1 > 0:
                p1.regimen = "minima"
                return p1
            n_new = n1 - f1 * (n1 - n0) / (f1 - f0) if f1 != f0 else n1
            n_new = max(self.rpm_min, min(self.rpm_max, n_new))
            n0, f0, n1 = n1, f1, n_new
            p1 = self.a_salida(modo, T_aire_C, T_out_C, m_agua, rpm=n1, T_in_ini=p1.T_in_C)
        p1.regimen = "modulada" if p1.valido else "no_valido"
        return p1

    def caudal_nominal(self, modo, T_aire_C, T_in_C, T_out_C, m0=0.45, tol_K=0.02, max_it=10):
        """Caudal fijo de la norma: el que da la entrada y la salida nominales."""
        cp = 4180.0
        m1 = m0
        p = self.resolver(modo, T_aire_C, T_in_C, m1)
        m_prev, f_prev = None, None
        for _ in range(max_it):
            f = abs(p.T_out_C - T_in_C) - abs(T_out_C - T_in_C)
            if abs(f) < tol_K or not p.valido:
                return m1, p
            if m_prev is None:
                m_new = p.P / (cp * abs(T_out_C - T_in_C))
            else:
                m_new = m1 - f * (m1 - m_prev) / (f - f_prev)
            m_prev, f_prev, m1 = m1, f, m_new
            p = self.resolver(modo, T_aire_C, T_in_C, m1)
        return m1, p


# ---------------------------------------------------------------------------
# SCOP y SEER del equipo
# ---------------------------------------------------------------------------
def scop_equipo(ev: Evaluador, clima: Clima, aplicacion: int, variante: str = "base",
                m_agua: float | None = None, regla_tbiv: str = "TOL",
                Pdesignh: float | None = None, velocidad: str = "variable") -> dict:
    """SCOP de M-4 en un clima y una aplicacion, con la TOL real del equipo.

    `velocidad`: "variable" (decisión P4 del autor, 15/10/2026) o "fija" (marcha/paro a la
    velocidad máxima, el método hasta esa fecha). Con velocidad variable, la TOL, la Tbiv y
    Pdesignh salen de los puntos a velocidad máxima, y en cada punto de la norma por encima de
    la TOL el equipo se resuelve a la velocidad cuya capacidad iguala la carga parcial
    (`Evaluador.a_carga`); si ni a la mínima baja hasta ella, marcha/paro a la mínima con Cd.
    La sensibilidad a la Tbiv máxima se calcula con los puntos a velocidad máxima."""
    if velocidad not in ("variable", "fija"):
        raise ValueError(velocidad)
    if m_agua is None:
        Tin, Tout = NOMINAL_AGUA[aplicacion]
        m_agua, _ = ev.caudal_nominal("M-4", 7.0, Tin, Tout)

    def punto(T):
        return ev.a_salida("M-4", float(T), salida_variable(aplicacion, clima, T), m_agua)

    # Puntos de la norma por encima de Tdesignh (A, B, C, D) y la Tbiv maxima.
    Tn = sorted({t for t in (-7, 2, 7, 12, clima.Tbiv_max) if t >= clima.Tdesignh})
    res = {T: punto(T) for T in Tn}

    def adm(T):
        """True/False si el punto es valido; None si no converge (no decide)."""
        p = punto(T)
        return p.admisible[variante] if p.valido else None

    # TOL: la temperatura entera mas baja desde la que todo es admisible. Un punto
    # no valido no se toma por no admisible: se excluye y se declara.
    no = [T for T in Tn if adm(T) is False]
    if not no:
        lo, hi = clima.Tdesignh, min(Tn)
        if adm(lo) is not False:
            TOL = lo
        else:
            TOL = None
    else:
        lo, hi = max(no), min([T for T in Tn if T > max(no)] or [16])
        TOL = None
    if TOL is None:
        # Biseccion entera entre lo (no admisible) y hi (admisible o 16).
        while hi - lo > 1:
            mid = (lo + hi) // 2
            a = adm(mid)
            if a is None:                        # no converge: decide el entero de encima
                a = adm(mid + 1) if mid + 1 < hi else True
            if a:
                hi = mid
            else:
                lo = mid
        TOL = hi
    if TOL >= 16:
        return {"clima": clima.nombre, "aplicacion": aplicacion, "variante": variante,
                "TOL": None, "SCOP": float("nan"), "motivo": "ningun punto admisible"}
    usados = {T: punto(T) for T in sorted(set(Tn) | {TOL}) if T >= TOL}
    puntos = [{"T_aire_C": T, "T_in_C": p.T_in_C, "T_out_C": p.T_out_C, "P": p.P,
               "COP": p.COP, "W_el": p.W_el, "rpm": p.rpm, "regimen": "plena",
               "T_dis_C": p.T_dis_C, "zona": p.zona, "valido": p.valido,
               "admisible": p.admisible[variante]}
              for T, p in sorted({**res, **usados}.items())]
    r = scop_desde_puntos(clima, aplicacion, puntos, TOL, regla_tbiv, Pdesignh=Pdesignh)
    r.update(variante=variante, m_agua=m_agua, velocidad="fija",
             puntos_no_validos=[p["T_aire_C"] for p in puntos if not p["valido"]],
             sensibilidad_tbiv_max=_sin_tabla(scop_desde_puntos(clima, aplicacion, puntos, TOL, "max")))
    if velocidad == "fija" or getattr(ev, "rpm_min", 0) >= getattr(ev, "rpm_max", 0):
        return r
    # Velocidad variable: los puntos de carga parcial.
    Pdh = r["Pdesignh"]
    pv = []
    for T in sorted(usados):
        Ph = Pdh * (T - 16.0) / (clima.Tdesignh - 16.0)
        q = ev.a_carga("M-4", float(T), salida_variable(aplicacion, clima, T), m_agua, Ph)
        pv.append({"T_aire_C": T, "T_in_C": q.T_in_C, "T_out_C": q.T_out_C, "P": q.P,
                   "carga": Ph, "COP": q.COP, "W_el": q.W_el, "rpm": q.rpm,
                   "regimen": q.regimen, "T_dis_C": q.T_dis_C, "zona": q.zona,
                   "valido": q.valido, "admisible": q.admisible[variante]})
    rv = scop_desde_puntos(clima, aplicacion, pv, TOL, regla_tbiv, Pdesignh=Pdh)
    rv.update(variante=variante, m_agua=m_agua, velocidad="variable", Tbiv=r["Tbiv"],
              regla_tbiv=regla_tbiv,
              puntos_velocidad_maxima=puntos,
              puntos_no_validos=[p["T_aire_C"] for p in pv if not p["valido"]],
              puntos_no_admisibles=[p["T_aire_C"] for p in pv if p["valido"] and not p["admisible"]],
              velocidad_fija=_sin_tabla(r),
              sensibilidad_tbiv_max=r["sensibilidad_tbiv_max"])
    return rv


def _sin_tabla(r):
    return {k: v for k, v in r.items() if k not in ("intervalos", "puntos")}


def scop_desde_puntos(clima: Clima, aplicacion: int, puntos: list, TOL: int,
                      regla_tbiv: str = "TOL", desescarche: dict | None = None,
                      Pdesignh: float | None = None) -> dict:
    """SCOP a partir de puntos ya resueltos (los de `scop_equipo`).

    `regla_tbiv`: "TOL" (decision 7 corregida el 02/10/2026, la del mercado: la
    maquina cubre el 100 % de la carga hasta su TOL) o "max" (la Tbiv maxima que
    admite la norma, sensibilidad). Pdesignh = Pdh(Tbiv)(Tdesignh - 16)/(Tbiv - 16)."""
    pts = {p["T_aire_C"]: {"P": p["P"], "COP": p["COP"]} for p in puntos
           if p["T_aire_C"] >= TOL and p.get("valido", True)}
    if regla_tbiv == "TOL":
        Tbiv = TOL
    elif regla_tbiv == "max":
        Tbiv = max(clima.Tbiv_max, TOL)
    else:
        raise ValueError(regla_tbiv)
    if Pdesignh is None:
        Pdesignh = _interp(pts, Tbiv, "P") * (clima.Tdesignh - 16.0) / (Tbiv - 16.0)
    else:
        # Carga de diseno impuesta (cap. 13, la del R-717 para los tres fluidos,
        # decision 2 del 05/10/2026): la Tbiv es la que resulte, informativa.
        Tbiv = None
    r = scop(clima.bins_calor, clima.Tdesignh, Pdesignh, pts, TOL, desescarche=desescarche)
    r.update(clima=clima.nombre, aplicacion=aplicacion, TOL=TOL, Tbiv=Tbiv, regla_tbiv=regla_tbiv,
             Pdesignh=Pdesignh, puntos=puntos,
             cumple_TOL_norma=(None if clima.TOL_max is None else TOL <= clima.TOL_max))
    return r


def seer_equipo(ev: Evaluador, climas: list, velocidad: str = "variable") -> dict:
    """SEER de M-2 (ventiloconvector, salida fija a 7 °C) en cada clima con horas
    de refrigeracion. La maquina es la misma en todos: los puntos A a D se
    resuelven una vez.

    `velocidad`: "variable" (decisión P4, 15/10/2026): B, C y D a la velocidad cuya capacidad
    iguala la carga parcial de la norma, Pc = Pdesignc (Tj - 16)/(35 - 16); "fija": a la
    velocidad máxima con marcha/paro."""
    if velocidad not in ("variable", "fija"):
        raise ValueError(velocidad)
    Tin, Tout = FRIO_AGUA
    m_agua, pA = ev.caudal_nominal("M-2", FRIO_PUNTOS["A"], Tin, Tout)
    pts_res = {"A": pA}
    for k in ("B", "C", "D"):
        if velocidad == "variable" and getattr(ev, "rpm_min", 0) < getattr(ev, "rpm_max", 0):
            Pc = pA.P * (FRIO_PUNTOS[k] - 16.0) / (35.0 - 16.0)
            pts_res[k] = ev.a_carga("M-2", FRIO_PUNTOS[k], Tout, m_agua, Pc)
        else:
            pts_res[k] = ev.a_salida("M-2", FRIO_PUNTOS[k], Tout, m_agua)
    pts = {FRIO_PUNTOS[k]: {"P": p.P, "EER": p.COP} for k, p in pts_res.items()}
    Pdesignc = pA.P
    out = {"m_agua": m_agua, "Pdesignc": Pdesignc, "velocidad": velocidad,
           "puntos": [{"condicion": k, "T_aire_C": p.T_aire_C, "T_in_C": p.T_in_C,
                       "T_out_C": p.T_out_C, "P": p.P, "EER": p.COP, "W_el": p.W_el,
                       "T_dis_C": p.T_dis_C, "rpm": p.rpm, "regimen": p.regimen,
                       "zona": p.zona, "valido": p.valido, "admisible": p.admisible["base"]}
                      for k, p in pts_res.items()],
           "climas": {}}
    for c in climas:
        if c.bins_frio:
            out["climas"][c.nombre] = seer(c.bins_frio, Pdesignc, pts)
    return out


# ---------------------------------------------------------------------------
# ACS anual (decisiones 9 y 12 del 02/10/2026)
# ---------------------------------------------------------------------------
QREF_L_KWH = 11.655        # UNE-EN 16147, perfil L, kWh/dia


def acs_puntos(ev: Evaluador, calor: dict | None, frio: dict | None) -> dict:
    """Recuperación de ACS en los puntos de carga parcial (decisión V5 del 15/10/2026).

    Con velocidad variable el compresor funciona todo el intervalo a menor velocidad, y la
    recuperación de los mapas a velocidad máxima la sobrestimaría. En cada punto del SCOP (M-4)
    y del SEER (M-2) se resuelve el modo con recuperación (M-3, M-1) a la MISMA velocidad, aire
    y entrada del agua de climatización, con el ACS de los mapas del cap. 11. Devuelve
    {"calor"|"frio": {T_aire: {"Q_acs" W, "dW" W (incremento eléctrico sobre el modo sin
    recuperación), "admisible"}}}."""
    out = {}
    for clave, res, modo in (("calor", calor, "M-3"), ("frio", frio, "M-1")):
        if not res:
            continue
        m_agua = res["m_agua"]
        d = {}
        for p in res["puntos"]:
            if not p.get("valido", True) or p["T_aire_C"] in d:
                continue
            rpm = p.get("rpm")
            q = ev.resolver(modo, float(p["T_aire_C"]), float(p["T_in_C"]), m_agua,
                            None if rpm is None or rpm != rpm else rpm)
            d[float(p["T_aire_C"])] = {"Q_acs": q.Q_acs, "dW": q.W_el - p["W_el"],
                                       "admisible": bool(q.valido and q.admisible["base"]),
                                       "rpm": q.rpm, "valido": q.valido}
        out[clave] = d
    return out


def acs_anual(clima: Clima, calor: dict, frio: dict | None, mapas: dict | None = None,
              Qref_kWh_dia: float = QREF_L_KWH, puntos_acs: dict | None = None) -> dict:
    """Reparto anual del ACS entre la recuperacion de M-1/M-3 y M-5, en regimen
    estacionario.

    - Demanda: Qref repartida por igual en las 8760 h (kWh/h = Qref/24).
    - En cada intervalo con climatizacion, la recuperacion aporta su potencia de
      ACS por la fraccion de tiempo en marcha (CR de la norma; 1 si la carga supera
      la potencia), con el tope de la demanda de esa hora; y nada por debajo de la
      TOL o si el modo con recuperacion no es admisible en ese punto.
    - El resto lo produce M-5 a 45 °C (RS-15, sin apoyo electrico), con su COP
      global medio en las horas en que es admisible. Las horas sin climatizacion
      de los climas de la norma se toman a 16 °C.
    - Electricidad del ACS: la de M-5 mas el INCREMENTO de M-1/M-3 sobre M-2/M-4
      en el mismo punto, por el tiempo en marcha.

    `calor`: resultado de `scop_desde_puntos` (aplicacion de 45 °C, la del diseno);
    `frio`: el de `seer` del mismo clima o None; `mapas`: PerformanceMap de M-1 a
    M-5 del cap. 11 (recalentamiento 5 K, subenfriamiento 2 K; agua de climatizacion
    acotada a la rejilla). Es una lectura de orden de magnitud, no un eta_wh."""
    d = Qref_kWh_dia / 24.0                                   # kW medios
    sh, sc = 5.0, 2.0
    if mapas is None:
        raise ValueError("acs_anual necesita los mapas del cap. 11: M-5 se lee siempre de ellos "
                         "(y M-1/M-3 si no se dan `puntos_acs`).")

    def m(modo, mag, T, agua=None):
        """Interpolacion lineal SOLO sobre los nudos validos con las consignas de
        diseno: la multilineal del mapa en 4 dimensiones propaga el NaN de un nudo
        no valido vecino aunque su peso sea nulo."""
        from scipy.interpolate import RegularGridInterpolator
        rs = [r for r in mapas[modo].rows if float(r["eje_recalentamiento_K"]) == sh
              and float(r["eje_subenfriamiento_K"]) == sc]
        Ts = sorted({float(r["eje_T_aire_C"]) for r in rs})
        if agua is None:
            v = {float(r["eje_T_aire_C"]): float(r[mag]) if r.get("valido") else np.nan for r in rs}
            return float(np.interp(T, Ts, [v[t] for t in Ts]))
        As = sorted({float(r["eje_T_agua_C"]) for r in rs})
        g = np.full((len(Ts), len(As)), np.nan)
        for r in rs:
            if r.get("valido"):
                g[Ts.index(float(r["eje_T_aire_C"])), As.index(float(r["eje_T_agua_C"]))] = float(r[mag])
        return float(RegularGridInterpolator([Ts, As], g)([[T, agua]])[0])

    def acot(x, lo, hi):
        return min(max(x, lo), hi)

    def adm(modo, T, agua=None):
        """Admisible si lo son todos los nudos de la rejilla que rodean al punto
        (la interpolacion de un booleano no tiene sentido)."""
        mp = mapas[modo]
        def entorno(eje, x):
            v = sorted(float(e) for e in mp.ejes[eje])
            lo = max([e for e in v if e <= x + 1e-9], default=v[0])
            hi = min([e for e in v if e >= x - 1e-9], default=v[-1])
            return {lo, hi}
        Ts = entorno("eje_T_aire_C" if "eje_T_aire_C" in mp.ejes else "T_aire_C", T)
        As = entorno("eje_T_agua_C" if "eje_T_agua_C" in mp.ejes else "T_agua_C", agua) if agua is not None else {None}
        ok = []
        for r in mp.rows:
            if float(r["eje_recalentamiento_K"]) != sh or float(r["eje_subenfriamiento_K"]) != sc:
                continue
            if float(r["eje_T_aire_C"]) in Ts and (agua is None or float(r["eje_T_agua_C"]) in As):
                ok.append(str(r.get("admisible")) == "True")
        return bool(ok) and all(ok)

    def en_puntos(clave, mag, Tj):
        """Interpolación lineal entre los puntos de carga parcial (como la norma con el COP),
        constante fuera de ellos; admisible si lo son los dos puntos que rodean a Tj. Un punto
        que no converge se excluye de la interpolación y no se toma por no admisible: es la regla
        del SCOP (`scop_equipo`). Los excluidos se publican en `puntos_acs_no_validos`."""
        P = {t: d for t, d in puntos_acs[clave].items() if d.get("valido", True)}
        if not P:
            return False if mag == "admisible" else 0.0
        xs = sorted(P)
        if mag == "admisible":
            lo = max([x for x in xs if x <= Tj + 1e-9], default=xs[0])
            hi = min([x for x in xs if x >= Tj - 1e-9], default=xs[-1])
            return P[lo]["admisible"] and P[hi]["admisible"]
        return float(np.interp(Tj, xs, [P[x][mag] for x in xs]))

    rec = dW = 0.0
    horas_clima = 0
    filas = []
    TOL = calor.get("TOL")
    for f in calor["intervalos"]:
        Tj, h = f["Tj"], f["h"]
        horas_clima += h
        if TOL is None or Tj < TOL:
            filas.append((Tj, h, "calor", 0.0)); continue
        CR = min(1.0, f["Ph"] / f["Pdh"]) if f["Pdh"] else 0.0
        if puntos_acs is not None:
            if not puntos_acs.get("calor") or not en_puntos("calor", "admisible", Tj):
                filas.append((Tj, h, "calor", 0.0)); continue
            q = CR * en_puntos("calor", "Q_acs", Tj) / 1e3
            dq = CR * en_puntos("calor", "dW", Tj) / 1e3
        else:
            Ta = acot(Tj, -10.0, 12.0)
            agua = acot(salida_variable(45, clima, Tj) - 5.0, 30.0, 40.0)
            if not adm("M-3", Ta, agua):
                filas.append((Tj, h, "calor", 0.0)); continue
            q = CR * m("M-3", "Q_acs", Ta, agua) / 1e3
            dq = CR * (m("M-3", "W_el", Ta, agua) - m("M-4", "W_el", Ta, agua)) / 1e3
        r = min(q, d)
        rec += r * h
        dW += h * dq * (r / q if q else 0)
        filas.append((Tj, h, "calor", r))
    if frio:
        for f in frio["intervalos"]:
            Tj, h = f["Tj"], f["h"]
            horas_clima += h
            CR = min(1.0, f["Pc"] / f["Pdc"])
            if puntos_acs is not None:
                if not puntos_acs.get("frio") or not en_puntos("frio", "admisible", Tj):
                    filas.append((Tj, h, "frio", 0.0)); continue
                q = CR * en_puntos("frio", "Q_acs", Tj) / 1e3
                dq = CR * en_puntos("frio", "dW", Tj) / 1e3
            else:
                Ta = acot(Tj, 20.0, 40.0)
                if not adm("M-1", Ta, 12.0):
                    filas.append((Tj, h, "frio", 0.0)); continue
                q = CR * m("M-1", "Q_acs", Ta, 12.0) / 1e3
                dq = CR * (m("M-1", "W_el", Ta, 12.0) - m("M-2", "W_el", Ta, 12.0)) / 1e3
            r = min(q, d)
            rec += r * h
            dW += h * dq * (r / q if q else 0)
            filas.append((Tj, h, "frio", r))
    demanda = Qref_kWh_dia * 365.0
    resto = max(0.0, demanda - rec)
    # COP global de M-5 en las horas en que es admisible (intervalos de la rejilla).
    horas_m5 = {}
    for Tj, h, _, _ in filas:
        horas_m5[Tj] = horas_m5.get(Tj, 0) + h
    neutras = max(0, 8760 - horas_clima)
    if neutras:
        horas_m5[16] = horas_m5.get(16, 0) + neutras
    num = hs = 0.0
    for Tj, h in horas_m5.items():
        Ta = acot(Tj, -7.0, 35.0)
        if adm("M-5", Ta):
            num += h / m("M-5", "COP_global", Ta)
            hs += h
    cop5 = hs / num if num else float("nan")
    E5 = resto / cop5 if num else float("nan")
    return {"clima": clima.nombre, "demanda_kWh": demanda, "recuperado_kWh": rec,
            "fraccion_recuperada": rec / demanda, "M5_kWh": resto, "COP_M5_medio": cop5,
            "horas_M5_admisible": hs, "E_M5_kWh": E5, "E_incremento_recuperacion_kWh": dW,
            "E_ACS_kWh": E5 + dW, "SPF_ACS": demanda / (E5 + dW) if num else float("nan"),
            "puntos_acs_no_validos": {k: [t for t, d in v.items() if not d.get("valido", True)]
                                      for k, v in (puntos_acs or {}).items()}}
