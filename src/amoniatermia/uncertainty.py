"""Incertidumbre de parametros: sensibilidad local y cribado de Morris. §6.11; C10-8.

El §6.11 separa dos incertidumbres. La de las CORRELACIONES se mide como banda
recorriendo las alternativas registradas (`validation.bands`, C10-7). Esta es la
otra: la de los PARAMETROS que el modelo toma como datos y que no estan medidos
o estan anclados sobre un unico punto.

RANGOS (decision del autor, 29/09/2026; `docs/DECISIONES_2026_09_29.md`)
------------------------------------------------------------------------
Mixtos, fundados en evidencia propia donde la hay, y cada uno con su fuente
(`FACTORES`). El ventilador NO es factor: los 780 W son dato del conjunto
montado. El compresor entra como factor DISCRETO. Con los polinomios de UNE-EN 12900
(desde el 15/10/2026, decision P3): los dos extremos de la banda del error de ajuste
(`banda_compresor`), aplicados al compresor de cada fluido. Con el semiempirico: los
juegos equivalentes del multiarranque (`juegos_equivalentes_2026_09_24`).

Phi arrastra lo que depende de el. El producto phi_c*phi_v y el angulo de
corrugacion se anclaron con Phi = 1.15 sobre el punto de seleccion del 27-30H;
con otro Phi el anclaje da otros (`plate_hx.anchor_from_selection_point`), y
usar el de 1.15 con otro Phi seria incoherente. Se reancla en cada valor. El
16-10H adopta el angulo del 27-30H (hipotesis de familia) y el mismo Phi. El
espesor de placa se mantiene: el dato es el producto Phi*t, y t se mueve menos
de un 5 % en la banda.

METODOS
-------
- `local`: un factor cada vez en los extremos de su rango, desde el nominal.
  Elasticidad = (dY/Y) / (dx/x) con la diferencia al extremo; para el factor
  discreto, el recorrido maximo entre juegos.
- `morris`: efectos elementales de Morris (1991) sobre los factores continuos,
  en el cubo unidad (p = 4 niveles, Delta = p / (2 (p - 1))), con semilla fija.
  mu* ordena la influencia; sigma frente a mu* senala no linealidad o
  interaccion. Sobol solo si mu* no separa los dominantes (plan, C10-8).

Cada punto arranca de la solucion nominal del modo (continuacion); si no
resulta valido, se repite desde la estimacion por parametros agrupados. Un
punto que sigue sin ser valido NO se admite relajando la tolerancia: se cuenta,
se lista con su residuo (`Evaluador.fallos`) y Morris descarta los efectos
elementales que lo usan (el numero de efectos por factor se publica). En M-1,
el vertice C1 alto con Phi = 1.30 se estanca en 3-4e-6 frente a la tolerancia
de 1e-6 (parada por `xtol`, con todas las comprobaciones cumplidas).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import campaign as C
from . import data as D
from . import indicators as I
from .circuit import MODES

K = 273.15
_27 = "placas_alfanova:unidades.condensador_climatizacion.geometria."
_16 = "placas_alfanova:unidades.desrecalentador_acs.geometria."


@dataclass(frozen=True)
class Factor:
    nominal: float
    bajo: float
    alto: float
    fuente: str
    unidad: str = "-"


#: Factores continuos y sus rangos (decision del 29/09/2026).
FACTORES = {
    "C1_aire": Factor(0.507, 0.507 * 0.95, 0.507 * 1.05,
                      "±5 %: validacion con la ficha de evaporador (+4.2 %)"),
    "Phi_placas": Factor(1.15, 1.10, 1.30, "§9.6.4; arrastra beta y phi_c*phi_v"),
    "phi_md": Factor(1.0, 1.0, 1.3, "hipotesis M2 (maldistribucion de la bateria)"),
    # Reestimado el 01/10/2026: nominal 0.90 * 0.98 = 0.882; rango del motor IE3
    # a IE4 de 2.2-3 kW (IEC 60034-30-1) por transmision de 0.95 a 0.98.
    "eta_electromecanico": Factor(0.90 * 0.98, 0.82, 0.89,
                                  "motor IE3-IE4 de 2.2-3 kW por correa de 0.95-0.98"),
}

#: Orden de `compressor.IDENTIFIED` y claves del bloque del fichero.
_CLAVES_COMPRESOR = ("AU_su_n_W_K", "AU_ex_n_W_K", "AU_amb_W_K", "A_leak_m2", "C",
                     "alpha", "W_loss_0_W", "r_v", "eta_ic")
_BLOQUE = "compresor_bock_f2:reidentificacion_2026_09_24."


@lru_cache(maxsize=16)
def _anclaje(phi: float):
    from .components.plate_hx import anchor_from_selection_point
    from .props import Fluid
    return anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"), phi=phi)


@lru_cache(maxsize=1)
def banda_compresor() -> dict:
    """Banda del error de ajuste de los polinomios del compresor (P3, 15/10/2026)."""
    from .validation.compressor_en12900 import banda_ajuste
    return banda_ajuste()


def juegos_compresor() -> dict:
    """Factor discreto del compresor. El primero es el nominal y se llama `adoptado`.

    - Polinomios de UNE-EN 12900 (desde el 15/10/2026, decisión P3): los dos extremos de la
      banda del error de ajuste, {nombre: {clave de `modelo_en12900.ajuste`: valor}}. El
      desfavorable quita caudal, añade potencia y sube la descarga; el favorable, al revés.
    - Semiempírico: los juegos equivalentes del multiarranque {nombre: vector}."""
    df = D.load("compresor_bock_f2")
    if D.compressor_model(df) == "en12900":
        b = banda_compresor()
        return {"adoptado": {},
                "banda_desfavorable": {"factor_caudal": 1.0 - b["caudal"],
                                       "factor_potencia": 1.0 + b["potencia"],
                                       "desplazamiento_descarga_K": b["descarga_K"]},
                "banda_favorable": {"factor_caudal": 1.0 + b["caudal"],
                                    "factor_potencia": 1.0 - b["potencia"],
                                    "desplazamiento_descarga_K": -b["descarga_K"]}}
    out = {"adoptado": list(D.compressor_params().as_vector())}
    for nombre, x in df.require("juegos_equivalentes_2026_09_24.juegos").items():
        out[nombre] = list(map(float, x))
    return out


def configuracion(valores: dict | None = None, juego: str | None = None,
                  compresor: str = "compresor_bock_f2") -> tuple:
    """(sustituciones, phi_md) para unos valores de los factores. Los que no
    se dan quedan en su nominal y no generan sustitucion."""
    v = {k: f.nominal for k, f in FACTORES.items()}
    v.update(valores or {})
    sus = {}
    if v["C1_aire"] != FACTORES["C1_aire"].nominal:
        sus["bateria_frimetal_cbn21:correlacion_aire.C1"] = float(v["C1_aire"])
    if v["Phi_placas"] != FACTORES["Phi_placas"].nominal:
        a = _anclaje(round(float(v["Phi_placas"]), 6))
        for base in (_27, _16):
            sus[base + "factor_alargamiento"] = float(v["Phi_placas"])
            sus[base + "angulo_corrugacion_rad"] = float(a.beta_c)
        sus["placas_alfanova:producto_phi_c_phi_v.valor"] = float(a.phi_c_phi_v)
    eta = FACTORES["eta_electromecanico"]
    if v["eta_electromecanico"] != eta.nominal:
        # Se reparte sobre el motor; la transmision queda en su valor.
        eta_t = D.load("compresor_bock_f2").require("transmision.eta_transmision")
        sus["compresor_bock_f2:transmision.eta_motor"] = float(v["eta_electromecanico"]) / eta_t
    if juego and juego != "adoptado":
        j = juegos_compresor()[juego]
        if isinstance(j, dict):     # polinomios: la misma banda para cada compresor
            for k, x in j.items():
                sus[f"{compresor}:modelo_en12900.ajuste.{k}"] = float(x)
        else:
            for k, x in zip(_CLAVES_COMPRESOR, j):
                sus[_BLOQUE + k] = float(x)
    return sus, float(v["phi_md"])


def magnitudes(s, spec) -> dict:
    """Salidas que se siguen en cada punto."""
    e = I.energy(s, spec)
    util = {"frio": s.Q_evap, "calor": e.Q_util_clima}.get(spec.clima, s.Q_acs)
    ind = e.EER if spec.clima == "frio" else (e.COP if e.COP else e.COP_global)
    return {"Q_util": float(util), "W_el": float(e.W_el), "indicador": float(ind),
            "COP_global": float(e.COP_global),
            "T_dis": float(s.T_dis), "T_evap": float(s.T_evap), "T_cond": float(s.T_cond),
            "carga_max": float(s.charge.get("_max", float("nan")))}


#: Salidas relativas (se comparan en tanto por uno) y absolutas (en K).
RELATIVAS = ("Q_util", "W_el", "indicador", "carga_max")
ABSOLUTAS = ("T_dis", "T_evap", "T_cond")


class Evaluador:
    """Resuelve un punto de diseno con unos valores de los factores."""

    def __init__(self, modo, bc, sp, pinzamientos=None, fluido="Ammonia", base=None):
        """`fluido` y `base` (sustituciones fijas, p. ej. la cilindrada igualada del
        cap. 13) permiten comparar fluidos con las mismas perturbaciones. El
        rendimiento electromecanico solo perturba el compresor abierto del R-717:
        los hermeticos llevan el motor dentro de sus parametros identificados."""
        self.modo, self.bc, self.sp, self.pin = modo, bc, sp, pinzamientos
        self.fluido, self.base = fluido, dict(base or {})
        self.spec = MODES[modo]
        self.n = 0
        self.no_validos = 0
        self.fallos = []          # (valores, juego, motivo) de los no validos
        c, _ = C.build_circuit(fluido=fluido, sustituciones=self.base or None)
        x0 = (c.initial_guess(modo, bc, sp, pinch_air=pinzamientos[0],
                              pinch_water=pinzamientos[1]) if pinzamientos else None)
        s = c.solve(modo, bc, sp, x0=x0)
        if not s.valid:
            raise RuntimeError(f"{modo}: el punto nominal no es valido")
        self.x_nominal = dict(s.unknowns)
        self.nominal = magnitudes(s, self.spec)

    def __call__(self, valores=None, juego=None, correlaciones=None) -> dict:
        sus, phi_md = configuracion(valores, juego,
                                    C.COMPRESOR_POR_FLUIDO.get(self.fluido, "compresor_bock_f2"))
        if self.fluido != "Ammonia":     # los juegos equivalentes del semiempirico son del F2
            sus = {k: v for k, v in sus.items() if not k.startswith(_BLOQUE)}
        sus = {**self.base, **sus}
        c, _ = C.build_circuit(fluido=self.fluido, sustituciones=sus or None, phi_md=phi_md,
                               correlaciones=correlaciones)
        t = time.time()
        s = c.solve(self.modo, self.bc, self.sp, x0=self.x_nominal)
        if not s.valid:
            x0 = (c.initial_guess(self.modo, self.bc, self.sp, pinch_air=self.pin[0],
                                  pinch_water=self.pin[1]) if self.pin else None)
            s = c.solve(self.modo, self.bc, self.sp, x0=x0)
        self.n += 1
        if not s.valid:
            self.no_validos += 1
            self.fallos.append({"valores": {k: float(v) for k, v in (valores or {}).items()},
                                "juego": juego, "residuo": float(s.max_residual),
                                "convergido": bool(s.converged),
                                "mensaje": str(s.message)[:80]})
        return {"valido": bool(s.valid), "t_s": time.time() - t, **magnitudes(s, self.spec)}


def _cambio(y, y0) -> dict:
    d = {k: y[k] / y0[k] - 1.0 for k in RELATIVAS}
    d.update({k: y[k] - y0[k] for k in ABSOLUTAS})
    return d


def local(ev: Evaluador) -> dict:
    """Un factor cada vez en los dos extremos de su rango."""
    y0 = ev.nominal
    filas = []
    for nombre, f in FACTORES.items():
        for lado, x in (("bajo", f.bajo), ("alto", f.alto)):
            if x == f.nominal:
                continue
            y = ev({nombre: x})
            d = _cambio(y, y0)
            dx = x / f.nominal - 1.0
            filas.append({"factor": nombre, "lado": lado, "valor": x, "valido": y["valido"],
                          "cambio": d,
                          "elasticidad": {k: d[k] / dx for k in RELATIVAS}})
    # Factor discreto: los juegos equivalentes del compresor.
    juegos = {}
    for nombre in juegos_compresor():
        if nombre == "adoptado":
            continue
        y = ev(juego=nombre)
        juegos[nombre] = {"valido": y["valido"], "cambio": _cambio(y, y0)}
    recorrido = {k: max((abs(j["cambio"][k]) for j in juegos.values()), default=0.0)
                 for k in RELATIVAS + ABSOLUTAS}
    return {"nominal": y0, "filas": filas, "compresor": juegos,
            "compresor_recorrido": recorrido}


def _trayectoria(rng, k, p):
    """Trayectoria de Morris en el cubo unidad: k + 1 puntos."""
    delta = p / (2.0 * (p - 1))
    niveles = np.arange(p // 2) / (p - 1)          # los que admiten +delta
    x = rng.choice(niveles, size=k)
    orden = rng.permutation(k)
    pts, cambios = [x.copy()], []
    for i in orden:
        x = x.copy()
        x[i] += delta
        pts.append(x)
        cambios.append(i)
    # Mitad de los pasos hacia abajo, para no sesgar: se invierte la
    # trayectoria completa con probabilidad 1/2 (espejo sobre el cubo).
    if rng.random() < 0.5:
        pts = [1.0 - q for q in pts]
    return pts, cambios, delta


def morris(ev: Evaluador, r: int = 10, p: int = 4, semilla: int = 20260929) -> dict:
    """Cribado de Morris sobre los factores continuos. Los efectos elementales
    se expresan por RANGO COMPLETO del factor: en tanto por uno del nominal
    para las salidas relativas y en K para las absolutas."""
    nombres = list(FACTORES)
    k = len(nombres)
    rng = np.random.default_rng(semilla)
    efectos = {n: {s: [] for s in RELATIVAS + ABSOLUTAS} for n in nombres}
    y0 = ev.nominal

    def valores(u):
        return {n: FACTORES[n].bajo + ui * (FACTORES[n].alto - FACTORES[n].bajo)
                for n, ui in zip(nombres, u)}

    for _ in range(r):
        pts, cambios, delta = _trayectoria(rng, k, p)
        ys = [ev(valores(u)) for u in pts]
        for j, i in enumerate(cambios):
            a, b = ys[j], ys[j + 1]
            if not (a["valido"] and b["valido"]):
                continue
            paso = pts[j + 1][i] - pts[j][i]          # +delta o -delta
            for s in RELATIVAS:
                efectos[nombres[i]][s].append((b[s] - a[s]) / y0[s] / paso)
            for s in ABSOLUTAS:
                efectos[nombres[i]][s].append((b[s] - a[s]) / paso)
    out = {}
    for n in nombres:
        out[n] = {}
        for s, e in efectos[n].items():
            e = np.asarray(e)
            out[n][s] = {"mu_estrella": float(np.mean(np.abs(e))) if e.size else float("nan"),
                         "mu": float(np.mean(e)) if e.size else float("nan"),
                         "sigma": float(np.std(e, ddof=1)) if e.size > 1 else float("nan"),
                         "n": int(e.size)}
    return {"r": r, "p": p, "semilla": semilla, "efectos": out,
            "evaluaciones": ev.n, "no_validos": ev.no_validos, "fallos": list(ev.fallos)}


# ---------------------------------------------------------------------------
# Banda de la DIFERENCIA entre dos modos (H2, C11-8)
# ---------------------------------------------------------------------------

def perturbaciones() -> list:
    """(fuente, grupo, etiqueta, kwargs del evaluador): las alternativas de
    correlacion de C10-7 y los extremos de parametros y juegos del compresor de
    C10-8. El GRUPO reune las que son alternativas entre si (una familia de
    correlaciones, un parametro): de cada grupo se toma la peor."""
    from .validation.bands import ALTERNATIVAS
    out = []
    for comp, fam, nombre in ALTERNATIVAS:
        out.append(("correlacion", f"{comp}/{fam}", nombre,
                    {"correlaciones": {comp: {fam: nombre}}}))
    for n, f in FACTORES.items():
        for x in (f.bajo, f.alto):
            if x != f.nominal:
                out.append(("parametro", n, f"{n} = {x:.4g}", {"valores": {n: x}}))
    for j in juegos_compresor():
        if j != "adoptado":
            out.append(("parametro", "compresor", f"juego {j}", {"juego": j}))
    return out


def banda_diferencia(ev_a: Evaluador, ev_b: Evaluador, magnitud: str = "indicador",
                     magnitud_b: str | None = None) -> dict:
    """Diferencia relativa d = Y_a / Y_b - 1 y su banda; si se dan dos
    magnitudes, Y_a es `magnitud` del primero y Y_b `magnitud_b` del segundo
    (p. ej. COP global con ACS frente al COP sin ella).

    Cada perturbacion se aplica a LOS DOS modos: lo que mueve a los dos por
    igual se cancela en la diferencia, que es lo que el criterio de H2 necesita
    (decision 3 del 30/09/2026: la penalizacion cuenta si sale de la banda).
    Por grupo se toma el mayor cambio de d; los grupos se combinan en raiz de
    la suma de cuadrados (fuentes independientes) y se publica tambien la suma
    lineal como cota conservadora. Una perturbacion no valida en algun modo se
    lista y no entra."""
    return bandas_diferencia(ev_a, ev_b, {"d": (magnitud, magnitud_b or magnitud)})["d"]


def bandas_diferencia(ev_a: Evaluador, ev_b: Evaluador, pares: dict) -> dict:
    """Como `banda_diferencia`, para varias diferencias {nombre: (mag_a, mag_b)}
    sobre LAS MISMAS evaluaciones."""
    d0 = {n: ev_a.nominal[ma] / ev_b.nominal[mb] - 1.0 for n, (ma, mb) in pares.items()}
    filas = {n: [] for n in pares}
    grupos = {n: {} for n in pares}
    for fuente, grupo, etiqueta, kw in perturbaciones():
        base = {"fuente": fuente, "grupo": grupo, "perturbacion": etiqueta}
        try:
            ya, yb = ev_a(**kw), ev_b(**kw)
        except Exception as exc:                    # noqa: BLE001  (p. ej. MissingData)
            for n in pares:
                filas[n].append({**base, "estado": f"no evaluable: {type(exc).__name__}"})
            continue
        if not (ya["valido"] and yb["valido"]):
            for n in pares:
                filas[n].append({**base, "estado": "no valida"})
            continue
        for n, (ma, mb) in pares.items():
            dd = ya[ma] / yb[mb] - 1.0 - d0[n]
            filas[n].append({**base, "estado": "evaluada", "cambio_d": dd,
                             "cambio_a": ya[ma] / ev_a.nominal[ma] - 1.0,
                             "cambio_b": yb[mb] / ev_b.nominal[mb] - 1.0})
            grupos[n][grupo] = max(grupos[n].get(grupo, 0.0), abs(dd))
    out = {}
    for n in pares:
        rss = sum(v * v for v in grupos[n].values()) ** 0.5
        lineal = sum(grupos[n].values())
        out[n] = {"d": d0[n], "banda_rss": rss, "banda_lineal": lineal, "grupos": grupos[n],
                  "significativa": abs(d0[n]) > rss,
                  "significativa_conservadora": abs(d0[n]) > lineal, "filas": filas[n]}
    return out
