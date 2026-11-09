"""Contraste del compresor con los puntos del software VAP de Bock (N1). Capitulo 10.

POR QUE
-------
Los 39 puntos de `data/compresor_bock_f2_vap.csv` (generados por el autor el
29/09/2026) estan FUERA del dominio de identificacion —T0 de -20 a 15 °C frente
a 0-5 °C del catalogo, recalentamiento de 1 a 10 K, 960 y 1200 rpm— y traen
temperatura de descarga. No han entrado en la identificacion: son validacion
independiente del juego adoptado el 24/09/2026.

DECISION DEL AUTOR (29/09/2026, tarde)
--------------------------------------
Se ensayo reidentificar con los 46 puntos del catalogo y los 27 de VAP a
1450 rpm dentro de la envolvente. La validacion cruzada por grupos de T0 no
cumplia N1 en 7 de los 10 grupos interiores y empeoraba el nucleo de 0 a 3 °C
(potencia hasta un 8-9 %). Se mantiene el juego del 24/09/2026 y el sesgo a T0
bajo se declara como limitacion (§9.13): no es de datos, es de estructura
(perdida mecanica constante, r_v y eta_ic fijos). Ver
`docs/DECISIONES_2026_09_29.md`.

CLASES DE PUNTO
---------------
- `dominio`: T0 dentro del catalogo (0-5 °C) a 1450 rpm; interpolacion.
- `extrapolacion_T0`: T0 fuera del catalogo a 1450 rpm.
- `velocidad`: 960 y 1200 rpm. El modelo no tiene dependencia con la velocidad
  mas alla del caudal barrido (la perdida mecanica es constante): se reportan
  como contraste de H6, no se juzgan con N1.
- `control`: el punto del bloque D, que repite uno del catalogo.
Los puntos `fuera` del diagrama de limites se contrastan igual pero se marcan:
el compresor no puede operar alli.
"""
from __future__ import annotations

from .. import data as D

K = 273.15
T0_CATALOGO_C = (0.0, 5.0)


def clase(pt) -> str:
    if pt["bloque"] == "D":
        return "control"
    if pt["rpm"] != 1450.0:
        return "velocidad"
    t0 = pt["T0"] - K
    if T0_CATALOGO_C[0] - 1e-6 <= t0 <= T0_CATALOGO_C[1] + 1e-6:
        return "dominio"
    return "extrapolacion_T0"


def contraste(params=None) -> dict:
    """Desviacion modelo - VAP en cada punto y resumen por clase frente a N1.

    `params`: juego de `CompressorParams` (por defecto, el adoptado)."""
    from ..components.compressor import SemiEmpiricalCompressor
    from ..props import Fluid
    from . import plan

    params = params or D.compressor_params()
    umbral = plan.threshold("N1")
    comps = {}
    filas = []
    for pt in D.compressor_vap_points():
        rpm = pt["rpm"]
        if rpm not in comps:
            comps[rpm] = SemiEmpiricalCompressor(
                Fluid("Ammonia"), D.compressor_geometry(rpm=rpm), params)
        r = comps[rpm].solve(pt["P_ad"], pt["T_su"], pt["P_ex"], pt.get("T_amb", 298.15))
        filas.append({"bloque": pt["bloque"], "clase": clase(pt),
                      "T0_C": pt["T0"] - K, "Tk_C": pt["Tc"] - K,
                      "recalentamiento_K": pt["recalentamiento"], "rpm": rpm,
                      "zona": pt["zona_esperada"],
                      "d_caudal": r.m_dot / pt["m_dot"] - 1.0,
                      "d_potencia": r.W_shaft / pt["W_shaft"] - 1.0,
                      "d_descarga_K": r.T_dis - pt["T_dis"],
                      "T_dis_vap_C": pt["T_dis"] - K, "T_dis_modelo_C": r.T_dis - K})

    resumen = {}
    for c in ("dominio", "extrapolacion_T0", "velocidad", "control"):
        sel = [f for f in filas if f["clase"] == c]
        if not sel:
            continue
        m = {"n": len(sel),
             "caudal_max": max(abs(f["d_caudal"]) for f in sel),
             "potencia_max": max(abs(f["d_potencia"]) for f in sel),
             "descarga_max_K": max(abs(f["d_descarga_K"]) for f in sel)}
        m["cumple_N1"] = (m["caudal_max"] <= umbral["caudal"]
                          and m["potencia_max"] <= umbral["potencia"]
                          and m["descarga_max_K"] <= umbral["temperatura_descarga_K"])
        resumen[c] = m

    # Tramo de T0 contiguo al catalogo en que N1 se cumple en TODOS los puntos
    # VAP a 1450 rpm dentro de la envolvente: dominio de validez del compresor
    # en T0, a publicar en el §9.5.3 y en la tabla del dominio de validez.
    ok = {}
    for f in filas:
        if f["rpm"] == 1450.0 and f["zona"] != "fuera":
            t0 = round(f["T0_C"])
            c = (abs(f["d_caudal"]) <= umbral["caudal"]
                 and abs(f["d_potencia"]) <= umbral["potencia"]
                 and abs(f["d_descarga_K"]) <= umbral["temperatura_descarga_K"])
            ok[t0] = ok.get(t0, True) and c
    lo, hi = T0_CATALOGO_C
    for t0 in sorted((t for t in ok if t < lo), reverse=True):
        if not ok[t0]:
            break
        lo = t0
    for t0 in sorted(t for t in ok if t > hi):
        if not ok[t0]:
            break
        hi = t0
    return {"umbral": umbral, "puntos": filas, "resumen": resumen,
            "dominio_N1_T0_C": (lo, hi), "cumple_por_T0": dict(sorted(ok.items()))}
