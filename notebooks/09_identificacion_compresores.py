# %% [markdown]
# # Identificacion de los compresores de R-290 y R-32 (cap. 13, H5)
#
# DESDE EL 15/10/2026 el modelo de estos compresores son polinomios de UNE-EN 12900
# (seccion `polinomios`). La identificacion semiempirica se conserva porque de ella
# sale la descarga del R-32, que Select 8 no publica.
#
# Mismo protocolo que el F2 de NH3 (§9.4.3.1): los nueve parametros, ec. 9-10,
# multiarranque (el juego del F2 y los tres neutros S3-S5), cotas de
# `SemiEmpiricalCompressor.BOUNDS`. Diferencias declaradas (decisiones del
# 05/10/2026): compresores HERMETICOS, identificados contra la potencia
# ELECTRICA; el R-32 sin temperatura de descarga (pesos 1, 1, 0), con la
# comprobacion de que la descarga del modelo no supera la cota adiabatica
# h1 + P/m de los mismos datos.
#
# Uso: `uv run python notebooks/09_identificacion_compresores.py`. Escribe
# `docs/cifras_compresores_cap13.md` y `results/cap13/identificacion.json`; los
# parametros se trasladan a mano a `data/compresor_r290.yaml` y `compresor_r32.yaml`.

# %%
import json
import time
from pathlib import Path

import numpy as np

from amoniatermia import data as D
from amoniatermia.components.compressor import IDENTIFIED, SemiEmpiricalCompressor
from amoniatermia.props import Fluid
from amoniatermia.reporting import HojaDeCifras, tabla
from amoniatermia.validation.compressor_cv import ARRANQUES

K = 273.15
CASOS = {"R-290": ("compresor_r290", "Propane", (1.0, 1.0, 0.0)),
         "R-32": ("compresor_r32", "R32", (1.0, 1.0, 0.0))}
#: Dominio de uso de la tesis (decision 11 del 05/10/2026) y, en el R-290, solo los
#: puntos con descarga >= T_k + 20 K (decision 7: con el IHX no se opera en los demas).
DOMINIO = {"T0_C": (-15.0, 10.0), "Tc_C": (25.0, 55.0)}
SOLO_DENTRO = {"R-290": True, "R-32": False}
RES = Path("results/cap13")


def arranques():
    return {"F2": list(D.compressor_params().as_vector()), **ARRANQUES}


def identificar(nombre):
    fichero, fluido, pesos = CASOS[nombre]
    f = Fluid(fluido)
    pts = puntos(nombre)
    df = D.load(fichero)
    out = {}
    lo = [SemiEmpiricalCompressor.BOUNDS[k][0] for k in IDENTIFIED]
    hi = [SemiEmpiricalCompressor.BOUNDS[k][1] for k in IDENTIFIED]
    hi[IDENTIFIED.index("AU_amb")] = lo[IDENTIFIED.index("AU_amb")] * (1 + 1e-6)   # pared adiabatica
    for s, x0 in arranques().items():
        comp = SemiEmpiricalCompressor(f, D.compressor_geometry(df), _params_vacios(df))
        t = time.time()
        sol = comp.identify([{k: v for k, v in p.items() if k != "T_dis"} for p in pts],
                            weights=pesos, x0=x0, bounds=(lo, hi))
        out[s] = {"x": list(map(float, sol.x)), "coste": float(sol.cost), "tiempo_s": time.time() - t}
        print(f"  {nombre} {s}: coste {sol.cost:.5f}", flush=True)
    mejor = min(out, key=lambda k: out[k]["coste"])
    return pts, out, mejor


def puntos(nombre):
    """Puntos de identificacion: dominio de uso y, en el R-290, Δt >= 20 K."""
    import csv
    fichero, fluido, _ = CASOS[nombre]
    zonas = {(float(r["T0_C"]), float(r["Tc_C"]), float(r["recalentamiento_K"])): r["zona"]
             for r in csv.DictReader((D.data_dir() / f"{fichero}_catalogo.csv").open(encoding="utf-8"))}
    out = []
    for p in D.compressor_catalog_fichero(fichero, Fluid(fluido)):
        T0, Tc = round(p["T0"] - K, 1), round(p["Tc"] - K, 1)
        if not (DOMINIO["T0_C"][0] <= T0 <= DOMINIO["T0_C"][1] and DOMINIO["Tc_C"][0] <= Tc <= DOMINIO["Tc_C"][1]):
            continue
        if SOLO_DENTRO[nombre] and zonas[(T0, Tc, p["recalentamiento"])] != "dentro":
            continue
        out.append(p)
    return out


def _params_vacios(df):
    from amoniatermia.components.compressor import CompressorParams
    return CompressorParams(n_reexp=df.require("parametros_identificados.n_politropico"),
                            eta_motor=1.0, eta_transm=1.0)


def contraste(nombre, x):
    fichero, fluido, _ = CASOS[nombre]
    f = Fluid(fluido)
    df = D.load(fichero)
    comp = SemiEmpiricalCompressor(f, D.compressor_geometry(df), _params_vacios(df))
    comp.p.set_vector(x)
    pts = puntos(nombre)
    dm, dW, dT, exc = [], [], [], []
    for p in pts:
        r = comp.solve(p["P_ad"], p["T_su"], p["P_ex"], 298.15)
        dm.append(r.m_dot / p["m_dot"] - 1)
        dW.append(r.W_shaft / p["W_shaft"] - 1)
        if "T_dis" in p:
            dT.append(r.T_dis - p["T_dis"])
        f.update_PT(p["P_ad"], p["T_su"])
        h_ad = f.h + p["W_shaft"] / p["m_dot"]
        f.update_PH(p["P_ex"], h_ad)
        exc.append(r.T_dis - f.T)          # >0: el modelo supera la cota adiabatica
    return {"n": len(pts), "caudal_max": float(np.max(np.abs(dm))), "caudal_medio": float(np.mean(dm)),
            "potencia_max": float(np.max(np.abs(dW))), "potencia_medio": float(np.mean(dW)),
            "descarga_max_K": float(np.max(np.abs(dT))) if dT else None,
            "descarga_medio_K": float(np.mean(dT)) if dT else None,
            "exceso_sobre_adiabatica_max_K": float(np.max(exc))}


# %%
def sec_identificacion():
    RES.mkdir(parents=True, exist_ok=True)
    todo, filas, par = {}, [], []
    for nombre in CASOS:
        pts, out, mejor = identificar(nombre)
        c = contraste(nombre, out[mejor]["x"])
        todo[nombre] = {"arranques": out, "adoptado": mejor, "contraste": c}
        for s, v in out.items():
            filas.append([nombre, s, f"{v['coste']:.5f}", "adoptado" if s == mejor else "",
                          f"{v['tiempo_s']:.0f} s"])
        par.append([nombre] + [f"{v:.4g}" for v in out[mejor]["x"]])
        todo[nombre]["contraste_tabla"] = [nombre, c["n"], f"{100*c['caudal_max']:.2f} %",
                                            f"{100*c['potencia_max']:.2f} %",
                                            f"{c['descarga_max_K']:.2f} K" if c["descarga_max_K"] is not None else "—",
                                            f"{c['exceso_sobre_adiabatica_max_K']:+.2f} K"]
    (RES / "identificacion.json").write_text(json.dumps(todo, indent=1), encoding="utf-8")
    return ("Multiarranque desde el juego del F2 y los tres arranques neutros del 24/09/2026 (S3-S5). "
            "Dominio de uso (T0 de -15 a 10 °C, Tk de 25 a 55 °C); R-290 solo con descarga >= Tk + 20 K. "
            "Solo caudal y potencia, pared adiabatica (AU_amb en su cota inferior): las descargas de los "
            "fabricantes son la adiabatica (decision 11 del 05/10/2026); la del R-290 se contrasta igual.\n\n"
            + tabla(["Compresor", "Arranque", "Coste", "", "Tiempo"], filas)
            + "\n### Parámetros adoptados\n\n"
            + tabla(["Compresor"] + list(IDENTIFIED), par)
            + "\n### Contraste sobre los propios puntos\n\n"
            + tabla(["Compresor", "Puntos", "Caudal máx.", "Potencia máx.", "Descarga máx.",
                     "Exceso máx. sobre la cota adiabática"], [v["contraste_tabla"] for v in todo.values()]))


# %%
def sec_polinomios():
    """Desde el 15/10/2026 (decisión P2) los compresores del cap. 13 se describen, como el F2,
    con polinomios de UNE-EN 12900 en caudal y potencia eléctrica ajustados a los puntos del
    software de selección con 5 K de recalentamiento. El R-290 también en descarga, y sus puntos
    a 1 y 10 K comprueban la regla del recalentamiento; el R-32 toma la descarga del
    semiempírico identificado arriba (Select 8 no la da)."""
    filas = []
    for nombre, (fichero, fluido, _) in CASOS.items():
        df = D.load(fichero)
        comp = D.compressor_en12900(df)
        todos = D.compressor_catalog_fichero(fichero, Fluid(fluido))
        sh = float(df.require("modelo_en12900.recalentamiento_ref_K"))
        for etq, sel in (("ajuste (5 K)", [p for p in todos if p["recalentamiento"] == sh]),
                         ("regla del recalentamiento (1 y 10 K)",
                          [p for p in todos if p["recalentamiento"] != sh])):
            if not sel:
                continue
            dm = [comp.solve(p["P_ad"], p["T_su"], p["P_ex"]).m_dot / p["m_dot"] - 1 for p in sel]
            dW = [comp.solve(p["P_ad"], p["T_su"], p["P_ex"]).W_shaft / p["W_shaft"] - 1 for p in sel]
            dT = [comp.solve(p["P_ad"], p["T_su"], p["P_ex"]).T_dis - p["T_dis"] for p in sel
                  if "T_dis" in p]
            filas.append([nombre, etq, len(sel), f"{100*max(map(abs, dm)):.2f} %",
                          f"{100*max(map(abs, dW)):.2f} %",
                          f"{max(map(abs, dT)):.2f} K" if dT else "— (semiempírico)"])
    return ("Polinomios de UNE-EN 12900 (diez coeficientes, t0 y tc en °C) a una velocidad, como el "
            "F2 (decisión P2 del 15/10/2026). Desviación máxima modelo − fabricante.\n\n"
            + tabla(["Compresor", "Puntos", "n", "Caudal máx.", "Potencia eléctrica máx.",
                     "Descarga máx."], filas))


# %%
if __name__ == "__main__":
    hoja = HojaDeCifras("docs/cifras_compresores_cap13.md", "Identificación de los compresores del capítulo 13",
                        "notebooks/09_identificacion_compresores.py")
    hoja.seccion("polinomios", sec_polinomios())
    hoja.seccion("identificacion", sec_identificacion())
    print("escrito", hoja.ruta)
