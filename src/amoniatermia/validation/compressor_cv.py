"""Validacion cruzada del compresor (N1 de la tabla 6.5). Capitulo 10.

POR QUE CRUZADA
---------------
La desviacion que el §9.5.3 publica (±2.71 % en caudal, ±4.72 % en potencia,
±3.35 K en descarga) esta medida sobre los MISMOS 46 puntos con que se
identifico el compresor: se cumple por construccion, y por la regla del §6.3.1
esa fuente queda consumida para contrastarlo. Se valida por tanto identificando
con una parte de los puntos y prediciendo el resto.

ESQUEMA (decision del autor, 29/09/2026, fijado antes de ejecutar)
------------------------------------------------------------------
Por GRUPOS DE TEMPERATURA DE CONDENSACION: se deja fuera cada T_k del catalogo
por turno. Es mas exigente que un reparto aleatorio, que casi siempre deja
puntos vecinos en la identificacion, y es la variable que mas cambia entre
modos. Los grupos extremos (15 y 50 °C) miden extrapolacion y se publican
aparte; el criterio se aplica a los interiores.

PROTOCOLO DE CADA PARTICION
---------------------------
El mismo de la identificacion adoptada (§9.5.3): minimos cuadrados con cotas,
w3 = 16 en la descarga (4 sobre el residuo) y multiarranque. Se excluye el arranque que ya habia
visto los 46 puntos (el juego del 16/09/2026, S1 del fichero): usarlo sesgaria
la validacion a su favor. Se queda el arranque de menor coste.
"""
from __future__ import annotations

import numpy as np

from .. import data as D

#: Arranques independientes de los 46 puntos: la antigua tabla 10.4 (S2) y los
#: tres neutros del multiarranque del 24/09/2026 (S3 a S5). Orden de
#: `compressor.IDENTIFIED`: AU_su_n, AU_ex_n, AU_amb, A_leak, C, alpha_l,
#: W_loss0, r_v, eta_ic.
ARRANQUES = {
    "S3": [5.0, 5.0, 5.0, 1e-7, 0.05, 0.1, 200.0, 2.5, 0.7],
    "S4": [50.0, 20.0, 2.0, 0.0, 0.03, 0.2, 100.0, 3.5, 0.9],
    "S5": [1.0, 2.0, 10.0, 5e-7, 0.10, 0.05, 400.0, 1.5, 0.6],
}


def _arranques() -> dict:
    out = {"S2": list(D.compressor_params(variant="original").as_vector())}
    out.update(ARRANQUES)
    return out


def _desviaciones(comp, puntos) -> dict:
    dm, dW, dT = [], [], []
    for pt in puntos:
        r = comp.solve(pt["P_ad"], pt["T_su"], pt["P_ex"], pt.get("T_amb", 298.15))
        dm.append((r.m_dot - pt["m_dot"]) / pt["m_dot"])
        dW.append((r.W_shaft - pt["W_shaft"]) / pt["W_shaft"])
        dT.append(r.T_dis - pt["T_dis"])
    dm, dW, dT = map(np.asarray, (dm, dW, dT))
    return {"caudal_max": float(np.max(np.abs(dm))), "caudal_medio": float(np.mean(dm)),
            "potencia_max": float(np.max(np.abs(dW))), "potencia_medio": float(np.mean(dW)),
            "descarga_max_K": float(np.max(np.abs(dT))),
            "descarga_medio_K": float(np.mean(dT))}


def cross_validate_by_Tc(catalogo=None, arranques=None, progreso=False) -> dict:
    """Validacion cruzada dejando fuera cada T_k (esquema del 29/09/2026 sobre
    el catalogo de 46 puntos)."""
    from . import plan
    extremos = set(D.load(plan.FICHERO).require("niveles.N1.grupos_extremos_Tk_C"))
    return cross_validate(catalogo or D.compressor_catalog(), "Tc", extremos,
                          arranques, progreso)


def cross_validate(puntos, clave="Tc", extremos=(), arranques=None,
                   progreso=False) -> dict:
    """Validacion cruzada dejando fuera cada valor de `clave` ("Tc" o "T0"),
    con el protocolo de identificacion completo en cada particion. Devuelve las
    particiones y el veredicto frente al criterio de N1 en los grupos que no
    son `extremos` (valores en °C)."""
    from ..components.compressor import SemiEmpiricalCompressor
    from ..props import Fluid
    from . import plan

    cat = puntos
    arranques = arranques or _arranques()
    umbral = plan.threshold("N1")
    extremos = set(extremos)
    grupo = lambda p: round(p[clave] - 273.15)          # noqa: E731
    grupos = sorted({grupo(p) for p in cat})

    particiones = []
    for Tk in grupos:
        fuera = [p for p in cat if grupo(p) == Tk]
        dentro = [p for p in cat if grupo(p) != Tk]
        mejor = None
        for nombre, x0 in arranques.items():
            comp = SemiEmpiricalCompressor(Fluid("Ammonia"), D.compressor_geometry(),
                                           D.compressor_params())
            sol = comp.identify(dentro, x0=x0)
            if mejor is None or sol.cost < mejor[1]:
                mejor = (nombre, float(sol.cost), comp, list(map(float, sol.x)))
        nombre, coste, comp, x = mejor
        dev = _desviaciones(comp, fuera)
        cumple = (dev["caudal_max"] <= umbral["caudal"]
                  and dev["potencia_max"] <= umbral["potencia"]
                  and dev["descarga_max_K"] <= umbral["temperatura_descarga_K"])
        particiones.append({"grupo_C": Tk, "Tk_C": Tk, "clave": clave, "n_fuera": len(fuera), "n_dentro": len(dentro),
                            "extremo": Tk in extremos, "arranque": nombre, "coste": coste,
                            "parametros": x, "cumple": cumple, **dev})
        if progreso:
            print(f"{clave} = {Tk} °C: {dev} cumple={cumple}", flush=True)

    interiores = [p for p in particiones if not p["extremo"]]

    def peor(clave, conj):
        return max(p[clave] for p in conj) if conj else float("nan")

    return {"particiones": particiones, "umbral": umbral,
            "interiores": {k: peor(k, interiores) for k in
                           ("caudal_max", "potencia_max", "descarga_max_K")},
            "extremos": {k: peor(k, [p for p in particiones if p["extremo"]]) for k in
                         ("caudal_max", "potencia_max", "descarga_max_K")},
            "cumple_interiores": all(p["cumple"] for p in interiores)}
