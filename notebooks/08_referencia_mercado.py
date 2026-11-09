# %% [markdown]
# # Referencia de mercado (H5, opcion C; capitulos 13 y 14)
#
# Muestra de bombas de calor reales del Heat Pump Keymark a traves de hplib
# (`data/mercado/`, 10/2024, CC BY 4.0). Criterio (decision del autor, 02/10/2026):
# aire-agua exterior, R-32 o R-290, de 6 a 12 kW de potencia nominal a baja
# temperatura. Sin recorrer el Keymark: la muestra mezcla monobloc y split, y el
# frio solo se compara en los modelos que declaran SEER, que es voluntario.
#
# Uso: `uv run python notebooks/08_referencia_mercado.py`

# %%
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from amoniatermia import data as D
from amoniatermia.reporting import HojaDeCifras, tabla

DATOS = D.data_dir() / "mercado"
CC, F1 = 2.5, 3.0


def muestra() -> pd.DataFrame:
    d = pd.read_csv(DATOS / "hplib_database.csv")
    f = d[(d["Type"] == "Outdoor Air/Water") & d["Refrigerant"].isin(["R32", "R290"])
          & d["Rated Power low T [kW]"].between(6, 12)].copy()
    clave = ["Manufacturer", "Model", "Titel", "Refrigerant", "Mass of Refrigerant [kg]",
             "Rated Power low T [kW]", "eta low T [%]", "eta medium T [%]", "SEER low T"]
    f = f.drop_duplicates(clave)
    f["carga_kg"] = (f["Mass of Refrigerant [kg]"].astype(str).str.replace("kg", "")
                     .str.replace(",", ".").str.strip().astype(float))
    f["g_por_kW"] = 1e3 * f["carga_kg"] / f["Rated Power low T [kW]"]
    f["SCOP35"] = (f["eta low T [%]"] + F1) * CC / 100
    f["SCOP55"] = (f["eta medium T [%]"] + F1) * CC / 100
    return f


def _q(x):
    x = pd.Series(x).dropna()
    if x.empty:
        return ["—"] * 6
    p = np.percentile(x, [10, 25, 50, 75, 90])
    return [len(x)] + [f"{v:.3g}" for v in p]


# %%
def sec_muestra():
    f = muestra()
    proc = yaml.safe_load((DATOS / "procedencia.yaml").read_text(encoding="utf-8"))
    filas = [[r, (f.Refrigerant == r).sum(), f[f.Refrigerant == r].Manufacturer.nunique(),
              f[(f.Refrigerant == r) & f["SEER low T"].notna()].shape[0]] for r in ("R32", "R290")]
    return (f"Fuente: {proc['fuente']['nombre']}, DOI {proc['fuente']['doi']}, "
            f"{proc['fuente']['licencia_datos']}; commit {proc['fuente']['commit_fichero'][:7]} "
            f"(10/2024). Criterio: aire-agua exterior, R-32 o R-290, 6–12 kW nominales a baja "
            f"temperatura; filas duplicadas eliminadas. Limitaciones: "
            + "; ".join(proc["limitaciones"]) + "\n\n"
            + tabla(["Refrigerante", "Modelos", "Fabricantes", "Con SEER declarado"], filas))


def sec_distribuciones():
    f = muestra()
    mag = [("η_s a 35 °C [%]", "eta low T [%]"), ("η_s a 55 °C [%]", "eta medium T [%]"),
           ("SCOP a 35 °C (de η_s)", "SCOP35"), ("SCOP a 55 °C (de η_s)", "SCOP55"),
           ("SEER a 7 °C", "SEER low T"), ("EER en el punto A (35 °C)", "EER_c_ref"),
           ("Carga [kg]", "carga_kg"), ("Carga específica [g/kW de calor nominal]", "g_por_kW"),
           ("TOL declarada [°C]", "Tolerance temperature [°C]"),
           ("Tbiv declarada [°C]", "Bivalence temperature [°C]")]
    filas = []
    for nombre, col in mag:
        for r in ("R32", "R290"):
            filas.append([nombre, r] + _q(f.loc[f.Refrigerant == r, col]))
    return ("Percentiles de la muestra en el clima medio (el de la clase del 811/2013). El SCOP a "
            "35 y 55 °C se deduce de η_s con CC = 2.5 y F(1) = 3 %. La carga específica se refiere a "
            "la potencia nominal de calefacción a 35 °C; la de H4 se refiere a la capacidad "
            "frigorífica, de modo que no son directamente comparables sin declararlo.\n\n"
            + tabla(["Magnitud", "Refrigerante", "n", "P10", "P25", "Mediana", "P75", "P90"], filas))


# %%
SECCIONES = {"muestra": sec_muestra, "distribuciones": sec_distribuciones}

if __name__ == "__main__":
    import sys
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SECCIONES)
    hoja = HojaDeCifras("docs/cifras_mercado.md", "Referencia de mercado",
                        "notebooks/08_referencia_mercado.py")
    for nombre in pedidas:
        hoja.seccion(nombre, SECCIONES[nombre]())
    print("escrito", hoja.ruta)
