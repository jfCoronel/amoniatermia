"""Ajuste y comprobación de los polinomios de UNE-EN 12900 del F2 NH3 (15/10/2026).

Datos: `data/compresor_bock_f2_vap_velocidades.csv` (57 puntos a 960, 1100, 1250 y 1450 rpm, 5 K
de recalentamiento, bloques E y F). Comprobaciones, contra el criterio de N1 (caudal 5 %,
potencia 8 %, descarga 5 K):

1. Ajuste a cada velocidad (desviación dentro de la muestra).
2. Interpolación en la velocidad: ajustar con tres velocidades y predecir la cuarta (1100 y
   1250 rpm), y predecir los puntos a 960 y 1200 rpm del 29/09/2026 (bloque C).
3. Regla del recalentamiento: predecir los 46 puntos del catálogo (1 K) y los bloques B (1, 5 y
   10 K) y D del 29/09/2026 con los rendimientos de 5 K.

Uso: uv run python herramientas/compresor/polinomios_en12900.py
"""
from __future__ import annotations

import json

import numpy as np

from amoniatermia import data as D
from amoniatermia.components.compressor_en12900 import (EN12900Compressor, PolinomiosVelocidad,
                                                        ajusta_polinomio, evalua)
from amoniatermia.props import Fluid
from amoniatermia.validation import plan

K = 273.15
FICHERO = "compresor_bock_f2_vap_velocidades.csv"
U = plan.threshold("N1")


def puntos():
    return D.compressor_vap_points(fichero=FICHERO)


def polinomios(pts, rpm):
    sel = [p for p in pts if p["rpm"] == rpm]
    t0 = [p["T0"] - K for p in sel]
    tc = [p["Tc"] - K for p in sel]
    return PolinomiosVelocidad(rpm=rpm,
                               m_dot=ajusta_polinomio(t0, tc, [p["m_dot"] for p in sel]),
                               W_eje=ajusta_polinomio(t0, tc, [p["W_shaft"] for p in sel]),
                               T_dis_C=ajusta_polinomio(t0, tc, [p["T_dis"] - K for p in sel]))


def compresor(pts, velocidades, rpm=1450.0):
    return EN12900Compressor(Fluid("Ammonia"), D.compressor_geometry(rpm=rpm),
                             [polinomios(pts, v) for v in velocidades])


def desviaciones(comp, sel):
    dm, dW, dT = [], [], []
    for p in sel:
        r = comp.solve(p["P_ad"], p["T_su"], p["P_ex"])
        dm.append(r.m_dot / p["m_dot"] - 1); dW.append(r.W_shaft / p["W_shaft"] - 1)
        dT.append(r.T_dis - p["T_dis"])
    dm, dW, dT = map(np.asarray, (dm, dW, dT))
    out = {"n": len(sel), "caudal_max_%": round(100 * np.max(np.abs(dm)), 2),
           "potencia_max_%": round(100 * np.max(np.abs(dW)), 2),
           "descarga_max_K": round(float(np.max(np.abs(dT))), 2),
           "caudal_medio_%": round(100 * np.mean(dm), 2), "potencia_media_%": round(100 * np.mean(dW), 2),
           "descarga_media_K": round(float(np.mean(dT)), 2)}
    out["N1"] = bool(out["caudal_max_%"] <= 100 * U["caudal"] and out["potencia_max_%"] <= 100 * U["potencia"]
                     and out["descarga_max_K"] <= U["temperatura_descarga_K"])
    return out


def main():
    pts = puntos()
    vel = sorted({p["rpm"] for p in pts})
    res = {"ajuste": {}, "velocidad": {}, "recalentamiento": {}}

    # 1. Ajuste a cada velocidad: un solo nudo, a su propia velocidad
    for v in vel:
        c = compresor(pts, [v], rpm=v)
        res["ajuste"][int(v)] = desviaciones(c, [p for p in pts if p["rpm"] == v])

    # 2. Interpolación en la velocidad, dejando fuera cada velocidad interior
    for fuera in (1100.0, 1250.0):
        c = compresor(pts, [v for v in vel if v != fuera], rpm=fuera)
        res["velocidad"][f"predice {int(fuera)} con {[int(v) for v in vel if v != fuera]}"] = \
            desviaciones(c, [p for p in pts if p["rpm"] == fuera])
    vap = D.compressor_vap_points()
    for v in (960.0, 1200.0):
        c = compresor(pts, vel, rpm=v)
        res["velocidad"][f"bloque C del 29/09 a {int(v)} rpm"] = desviaciones(
            c, [p for p in vap if p["bloque"] == "C" and p["rpm"] == v])

    # 3. Recalentamiento, a 1450 rpm con los cuatro nudos
    c = compresor(pts, vel, rpm=1450.0)
    cat = D.compressor_catalog()
    res["recalentamiento"]["catálogo, 46 puntos a 1 K"] = desviaciones(c, cat)
    for sh in (1.0, 10.0):
        sel = [p for p in vap if p["bloque"] == "B" and p["recalentamiento"] == sh]
        res["recalentamiento"][f"bloque B a {sh:g} K"] = desviaciones(c, sel)
    res["recalentamiento"]["bloque D (2/45 °C, 1 K)"] = desviaciones(c, [p for p in vap if p["bloque"] == "D"])

    # 4. Igualdad con el modelo vigente en el punto de diseño de M-2 (2/46.8 °C, 5 K)
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(2 + K), f.Psat(46.8 + K)
    r = c.solve(P0, 2 + K + 5, Pk)
    res["M2_2_46.8_5K"] = {"m_dot": r.m_dot, "W_eje": r.W_shaft, "T_dis_C": r.T_dis - K,
                          "eta_v": r.eta_v, "eta_is": r.eta_is, "Q_amb": r.Q_amb}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
