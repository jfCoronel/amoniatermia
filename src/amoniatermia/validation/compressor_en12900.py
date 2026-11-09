"""Validación N1 del compresor por polinomios de UNE-EN 12900. Capítulo 10.

Desde el 15/10/2026 (`docs/DECISIONES_2026_10_15.md`) el compresor del R-717 se describe con
polinomios ajustados a los puntos de BOCK VAP en toda su envolvente, a 960, 1100, 1250 y 1450
rpm y 5 K de recalentamiento. Los puntos de ajuste quedan consumidos (regla del §6.3.1); la
validación usa lo que el ajuste no ha visto:

1. AJUSTE. Desviación de cada polinomio sobre sus propios puntos. No es validación: mide si
   la forma de diez coeficientes basta (con 57 puntos por velocidad).
2. VELOCIDAD. Se ajusta con tres velocidades y se predice la cuarta (1100 y 1250 rpm, las
   interiores), y se predicen los puntos de 960 y 1200 rpm del 29/09/2026 (bloque C de
   `compresor_bock_f2_vap.csv`), que no entran en el ajuste.
3. RECALENTAMIENTO. Con los rendimientos de 5 K se predicen los 46 puntos del catálogo (1 K)
   y los bloques B (1 y 10 K) y D del 29/09/2026.

Criterio: el de N1 (`plan.threshold("N1")`), sobre la desviación MÁXIMA.
"""
from __future__ import annotations

import numpy as np

from .. import data as D

K = 273.15


def _compresor(velocidades, rpm, puntos):
    from ..components.compressor_en12900 import (EN12900Compressor, PolinomiosVelocidad,
                                                 ajusta_polinomio)
    from ..props import Fluid

    df = D.load("compresor_bock_f2")
    pol = []
    for v in velocidades:
        sel = [p for p in puntos if p["rpm"] == v]
        t0 = [p["T0"] - K for p in sel]
        tc = [p["Tc"] - K for p in sel]
        pol.append(PolinomiosVelocidad(
            rpm=v, n_puntos=len(sel),
            m_dot=ajusta_polinomio(t0, tc, [p["m_dot"] for p in sel]),
            W_eje=ajusta_polinomio(t0, tc, [p["W_shaft"] for p in sel]),
            T_dis_C=ajusta_polinomio(t0, tc, [p["T_dis"] - K for p in sel])))
    m = df.require("modelo_en12900")
    return EN12900Compressor(Fluid("Ammonia"), D.compressor_geometry(df, rpm=rpm), pol,
                             recalentamiento_ref_K=float(m["recalentamiento_ref_K"]),
                             grado_velocidad=int(m["grado_velocidad"]),
                             V_swept_datos=float(m["volumen_barrido_datos_m3_rev"]))


def desviaciones(comp, puntos, umbral=None) -> dict:
    from . import plan

    u = umbral or plan.threshold("N1")
    dm, dW, dT = [], [], []
    for p in puntos:
        r = comp.solve(p["P_ad"], p["T_su"], p["P_ex"])
        dm.append(r.m_dot / p["m_dot"] - 1.0)
        dW.append(r.W_shaft / p["W_shaft"] - 1.0)
        dT.append(r.T_dis - p["T_dis"])
    dm, dW, dT = map(np.asarray, (dm, dW, dT))
    out = {"n": len(puntos),
           "caudal_max": float(np.max(np.abs(dm))), "caudal_medio": float(np.mean(dm)),
           "potencia_max": float(np.max(np.abs(dW))), "potencia_medio": float(np.mean(dW)),
           "descarga_max_K": float(np.max(np.abs(dT))), "descarga_medio_K": float(np.mean(dT))}
    out["cumple_N1"] = bool(out["caudal_max"] <= u["caudal"] and out["potencia_max"] <= u["potencia"]
                            and out["descarga_max_K"] <= u["temperatura_descarga_K"])
    return out


def validacion() -> dict:
    """Las tres comprobaciones, con su veredicto frente a N1."""
    from . import plan

    df = D.load("compresor_bock_f2")
    pts = D.compressor_en12900_points(df)
    vel = sorted({p["rpm"] for p in pts})
    out = {"umbral": plan.threshold("N1"), "velocidades_rpm": vel,
           "puntos_por_velocidad": {int(v): sum(1 for p in pts if p["rpm"] == v) for v in vel},
           "ajuste": {}, "velocidad": {}, "recalentamiento": {}}
    for v in vel:
        out["ajuste"][int(v)] = desviaciones(_compresor([v], v, pts),
                                             [p for p in pts if p["rpm"] == v])
    for fuera in vel[1:-1]:
        resto = [v for v in vel if v != fuera]
        out["velocidad"][f"{int(fuera)} rpm con {', '.join(str(int(v)) for v in resto)}"] = \
            desviaciones(_compresor(resto, fuera, pts), [p for p in pts if p["rpm"] == fuera])
    vap = D.compressor_vap_points()
    for v in sorted({p["rpm"] for p in vap if p["bloque"] == "C"}):
        out["velocidad"][f"{int(v)} rpm, puntos del 29/09/2026"] = desviaciones(
            _compresor(vel, v, pts), [p for p in vap if p["bloque"] == "C" and p["rpm"] == v])
    c = _compresor(vel, 1450.0, pts)
    out["recalentamiento"]["catálogo, 1 K"] = desviaciones(c, D.compressor_catalog())
    for sh in sorted({p["recalentamiento"] for p in vap if p["bloque"] == "B"}):
        out["recalentamiento"][f"{sh:g} K, puntos del 29/09/2026"] = desviaciones(
            c, [p for p in vap if p["bloque"] == "B" and p["recalentamiento"] == sh])
    out["recalentamiento"]["control del 29/09/2026 (2/45 °C, 1 K)"] = desviaciones(
        c, [p for p in vap if p["bloque"] == "D"])
    validaciones = [d for g in ("velocidad", "recalentamiento") for d in out[g].values()]
    out["cumple_N1"] = all(d["cumple_N1"] for d in validaciones)
    out["peor_validacion"] = {k: max(d[k] for d in validaciones)
                              for k in ("caudal_max", "potencia_max", "descarga_max_K")}
    return out


def banda_ajuste() -> dict:
    """Banda del error de ajuste de los polinomios (factor del compresor en la incertidumbre,
    decisión P3 del 15/10/2026): la mayor desviación de ajuste o de validación en cada
    magnitud."""
    v = validacion()
    todas = list(v["ajuste"].values()) + [d for g in ("velocidad", "recalentamiento")
                                          for d in v[g].values()]
    return {"caudal": max(d["caudal_max"] for d in todas),
            "potencia": max(d["potencia_max"] for d in todas),
            "descarga_K": max(d["descarga_max_K"] for d in todas)}
