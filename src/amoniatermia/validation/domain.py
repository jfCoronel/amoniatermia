"""Dominio de validez del modelo (§6.7.4). Capitulo 10.

DESDE EL 15/10/2026 el compresor se describe con polinomios de UNE-EN 12900 ajustados a
datos del fabricante que barren toda su envolvente (`DECISIONES_2026_10_15.md`): el dominio
de validez del compresor ES la envolvente, y dentro de ella la admisibilidad la deciden solo
los limites del compresor real. Lo que sigue describe el dominio del semiempirico, que se
conserva para reproducir las cifras anteriores.

El §6.7.4 pide cerrar el capitulo 10 declarando «el rango de temperatura de
evaporacion, temperatura de condensacion, relacion de compresion y potencia
dentro del cual se han verificado los criterios de aceptacion», y restringir a
el los resultados de los capitulos 11 a 13; fuera, los resultados son
TENDENCIA y no prediccion.

El factor que lo acota es el compresor: su catalogo cubre T0 de 0 a 5 °C y T_k
de 15 a 50 °C. La validacion cruzada por grupos de T_k (`compressor_cv`) mide
los grupos interiores como interpolacion y los extremos como extrapolacion
dentro del catalogo.

Fuera del rectangulo del catalogo, los puntos del software VAP de Bock
(`compressor_vap`, 29/09/2026) amplian el contraste: N1 se cumple en T0 de -5 a
5 °C con T_k de 25 a 50 °C. Un punto ahi es `validado_VAP`; fuera de eso, no
hay contraste que cumpla N1 y el resultado es tendencia.
"""
from __future__ import annotations

from functools import lru_cache

from ..envelope import dominio_identificacion

K = 273.15


@lru_cache(maxsize=1)
def dominio_validado() -> dict:
    """Rectangulo T0 x T_k [K] en que N1 se cumple con los puntos VAP a la
    velocidad nominal dentro de la envolvente del fabricante."""
    from . import compressor_vap
    r = compressor_vap.contraste()
    lo, hi = r["dominio_N1_T0_C"]
    tk = [f["Tk_C"] for f in r["puntos"]
          if f["rpm"] == 1450.0 and f["zona"] != "fuera" and lo <= f["T0_C"] <= hi]
    return {"T0": (lo + K, hi + K), "Tc": (min(tk) + K, max(tk) + K)}


def clasifica(T_evap: float, T_cond: float, extremos_Tk_C=(15, 50),
              modelo: str | None = None, fichero: str = "compresor_bock_f2") -> str:
    """Clase de dominio de un punto.

    Con el compresor por polinomios de UNE-EN 12900 (15/10/2026): `dentro_del_dominio` si el
    punto cae en una zona del diagrama que cubren los datos (sin límites o refrigeración
    suplementaria), `fuera_del_dominio` si no. La velocidad y el recalentamiento los comprueba
    `envelope.evaluate`, que conoce el punto entero.

    Con el semiempírico (hasta esa fecha): `interpolado`, `extremo_del_catalogo`,
    `validado_VAP` o `fuera_del_dominio`."""
    from .. import data as D
    from ..envelope import zona_diagrama

    modelo = modelo or D.compressor_model(D.load(fichero))
    if modelo == "en12900":
        z = zona_diagrama(T_evap, T_cond, fichero=fichero)
        return "fuera_del_dominio" if z == "fuera" else "dentro_del_dominio"
    dom = dominio_identificacion()
    (t0a, t0b), (tka, tkb) = dom["T0"], dom["Tc"]
    tol = 0.05
    if not (t0a - tol <= T_evap <= t0b + tol and tka - tol <= T_cond <= tkb + tol):
        v = dominio_validado()
        (v0a, v0b), (vka, vkb) = v["T0"], v["Tc"]
        if v0a - tol <= T_evap <= v0b + tol and vka - tol <= T_cond <= vkb + tol:
            return "validado_VAP"
        return "fuera_del_dominio"
    # Los grupos extremos se validan como extrapolacion: por debajo del
    # segundo grupo o por encima del penultimo.
    lo_int, hi_int = extremos_Tk_C[0] + 5 + K, extremos_Tk_C[1] - 5 + K
    if T_cond < lo_int or T_cond > hi_int:
        return "extremo_del_catalogo"
    return "interpolado"


def resumen(soluciones: dict, modelo: str | None = None) -> list:
    """Clasifica un conjunto {etiqueta: CircuitSolution}."""
    from .. import data as D

    modelo = modelo or D.compressor_model(D.load("compresor_bock_f2"))
    out = []
    for etq, s in soluciones.items():
        env = s.envelope or {}
        fila = {"punto": etq, "modo": s.mode, "T_evap_C": s.T_evap - K,
                "T_cond_C": s.T_cond - K,
                "relacion_compresion": s.unknowns["Pk"] / s.unknowns["P0"],
                "clase": clasifica(s.T_evap, s.T_cond, modelo=modelo),
                "zona_diagrama": env.get("limites", {}).get(
                    "diagrama_aplicacion", {}).get("valor"),
                "fuera_del_dominio_del_compresor": env.get("fuera_del_dominio_del_compresor"),
                "valido": bool(s.valid), "admisible": bool(s.admissible)}
        if modelo != "en12900":
            dom, val = dominio_identificacion(), dominio_validado()
            fila["dT0_fuera_K"] = max(dom["T0"][0] - s.T_evap, s.T_evap - dom["T0"][1], 0.0)
            fila["dT0_fuera_validado_K"] = max(val["T0"][0] - s.T_evap,
                                               s.T_evap - val["T0"][1], 0.0)
        out.append(fila)
    return out
