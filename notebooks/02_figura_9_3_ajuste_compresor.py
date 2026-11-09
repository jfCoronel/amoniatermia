# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: amoniatermia
#     language: python
#     name: amoniatermia
# ---

# %% [markdown]
# # 02 - Figura 9.3: el compresor por polinomios de UNE-EN 12900 frente a sus datos
#
# Notebook de EXPERIMENTACION. El modelo vive en el paquete `amoniatermia`,
# no aqui: esto carga, ejecuta y grafica.
#
# Desde el 15/10/2026 (decision del autor, `docs/DECISIONES_2026_10_15.md`) el
# compresor se describe con polinomios de UNE-EN 12900 ajustados a los puntos de
# BOCK VAP en toda la envolvente, a 960, 1100, 1250 y 1450 rpm con 5 K de
# recalentamiento. La figura muestra dos series:
#
# - AJUSTE: los 228 puntos de VAP, cada uno con el polinomio de su velocidad.
# - VALIDACION de la regla del recalentamiento: los 46 puntos del catalogo, a 1 K
#   y 1450 rpm, que no entran en el ajuste.
#
# Las bandas son los criterios de N1 de la tabla 6.5: 5 % en caudal (que sigue a
# la capacidad), 8 % en potencia al eje y 5 K en temperatura de descarga.
#
# Salida: `docs/figuras/fig_9_3_ajuste_compresor.{png,pdf}`. El PNG va a 300 ppp
# para insertarlo en el documento de Word; el PDF se conserva por ser vectorial.

# %%
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from amoniatermia import Fluid
from amoniatermia import data as D

# %% [markdown]
# ## Paleta y tipografia
#
# Dos series, dos hues validados y DOS FORMAS de marcador: la identidad no puede
# descansar solo en el color, porque la figura se va a imprimir y puede acabar
# en blanco y negro. Los textos van en tinta y nunca en el color de la serie.

# %%
AZUL = "#2a78d6"        # ajuste (puntos de VAP)
NARANJA = "#eb6834"     # validacion (catalogo a 1 K)
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRIS = "#b8b7b2"

mpl.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "legend.fontsize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "axes.edgecolor": TINTA_2,
    "axes.labelcolor": TINTA,
    "text.color": TINTA,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "axes.grid": True,
    "grid.color": GRIS,
    "grid.linewidth": 0.4,
    "grid.alpha": 0.6,
    "axes.axisbelow": True,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

# %% [markdown]
# ## Los puntos, resueltos con el compresor por polinomios

# %%
f = Fluid("Ammonia")
comp = D.compressor(fluid=f)

SERIES = {
    "Ajuste: VAP, 4 velocidades, 5 K": (D.compressor_en12900_points(), AZUL, "o"),
    "Validación: catálogo, 1 K": ([dict(p, rpm=1450.0) for p in D.compressor_catalog()],
                                  NARANJA, "^"),
}
JUEGOS = {n: (None, c, m) for n, (_, c, m) in SERIES.items()}

datos = {}
for nombre, (pts, _, _) in SERIES.items():
    fila = {k: [] for k in ("Q_cat", "Q_mod", "W_cat", "W_mod", "T_cat", "T_mod", "T0")}
    for pt in pts:
        comp.fija_velocidad(pt["rpm"])
        r = comp.solve(pt["P_ad"], pt["T_su"], pt["P_ex"])
        # La capacidad del modelo se obtiene del caudal con el MISMO salto
        # entalpico con que el fabricante la publica, que es como `data` dedujo
        # el caudal de referencia: la desviacion relativa en capacidad y en
        # caudal son la misma magnitud.
        fila["Q_cat"].append(pt["Q0"] / 1000.0)
        fila["Q_mod"].append(pt["Q0"] / 1000.0 * r.m_dot / pt["m_dot"])
        fila["W_cat"].append(pt["W_shaft"] / 1000.0)
        fila["W_mod"].append(r.W_shaft / 1000.0)
        fila["T_cat"].append(pt["T_dis"] - 273.15)
        fila["T_mod"].append(r.T_dis - 273.15)
        fila["T0"].append(pt["T0"] - 273.15)
    datos[nombre] = {k: np.array(v) for k, v in fila.items()}
comp.fija_velocidad(1450.0)

for n in SERIES:
    print(f"{n}: {len(datos[n]['Q_cat'])} puntos")

# %% [markdown]
# ## La figura
#
# Tres paneles de paridad —una magnitud por panel, nunca dos escalas en un
# mismo eje— y un cuarto con el error de la temperatura de descarga frente a la
# de evaporacion, la variable que recorre toda la envolvente.

# %%
PANELES = [
    ("a", "Q_cat", "Q_mod", "Capacidad frigorífica", "kW", 0.05, None),
    ("b", "W_cat", "W_mod", "Potencia al eje", "kW", 0.08, None),
    ("c", "T_cat", "T_mod", "Temperatura de descarga", "°C", None, 5.0),
]

fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.6))
axes = axes.ravel()

for ax, (letra, k_cat, k_mod, titulo, unidad, banda_rel, banda_abs) in zip(
        axes, PANELES):
    todos = np.concatenate([datos[n][k_cat] for n in JUEGOS]
                           + [datos[n][k_mod] for n in JUEGOS])
    lo, hi = todos.min(), todos.max()
    margen = 0.06 * (hi - lo)
    lim = (lo - margen, hi + margen)
    linea = np.array(lim)

    # Banda de la tolerancia DECLARADA por el ap. 9.5.3.
    if banda_rel is not None:
        ax.fill_between(linea, linea * (1 - banda_rel), linea * (1 + banda_rel),
                        color=GRIS, alpha=0.35, linewidth=0, zorder=0)
        etiqueta_banda = f"±{banda_rel*100:.1f} %"
    else:
        ax.fill_between(linea, linea - banda_abs, linea + banda_abs,
                        color=GRIS, alpha=0.35, linewidth=0, zorder=0)
        etiqueta_banda = f"±{banda_abs:.1f} K"
    ax.plot(linea, linea, color=TINTA_2, linewidth=0.9, zorder=1)

    for nombre, (_, color, marcador) in JUEGOS.items():
        d = datos[nombre]
        ax.scatter(d[k_cat], d[k_mod], s=22, marker=marcador,
                   facecolor="none", edgecolor=color, linewidth=0.9,
                   zorder=3, label=nombre)

    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"Fabricante [{unidad}]")
    ax.set_ylabel(f"Modelo [{unidad}]")
    ax.set_title(f"({letra}) {titulo}", loc="left", color=TINTA)
    ax.text(0.97, 0.06, f"criterio N1 {etiqueta_banda}", transform=ax.transAxes,
            ha="right", va="bottom", color=TINTA_2, fontsize=7)
    # La desviacion MEDIDA de cada juego, en el hueco que deja la diagonal.
    # Va en tinta y con el nombre del juego: el color lo lleva el marcador.
    lineas = []
    for nombre in JUEGOS:
        d = datos[nombre]
        if banda_rel is not None:
            e = np.abs(d[k_mod] - d[k_cat]) / d[k_cat]
            lineas.append(f"{nombre.split(':')[0]}: máx {100*e.max():.2f} %")
        else:
            e = np.abs(d[k_mod] - d[k_cat])
            lineas.append(f"{nombre.split(':')[0]}: máx {e.max():.1f} K")
    ax.text(0.04, 0.96, "\n".join(lineas), transform=ax.transAxes,
            ha="left", va="top", color=TINTA, fontsize=7, linespacing=1.5)

# --- panel (d): error de la temperatura de descarga en la envolvente -----
ax = axes[3]
ax.axhspan(-5.0, 5.0, color=GRIS, alpha=0.35, linewidth=0, zorder=0)
ax.axhline(0.0, color=TINTA_2, linewidth=0.9, zorder=1)
for nombre, (_, color, marcador) in JUEGOS.items():
    d = datos[nombre]
    err = d["T_mod"] - d["T_cat"]
    ax.scatter(d["T0"], err, s=14, marker=marcador, facecolor="none",
               edgecolor=color, linewidth=0.8, zorder=3, label=nombre)
ax.legend(loc="upper right", frameon=False, fontsize=6.5, handletextpad=0.3)
ax.set_xlabel("Temperatura de evaporación [°C]")
ax.set_ylabel("Modelo − fabricante [K]")
ax.set_title("(d) Error de la descarga", loc="left", color=TINTA)
ax.text(0.03, 0.06, "criterio N1 ±5.0 K", transform=ax.transAxes,
        ha="left", va="bottom", color=TINTA_2, fontsize=7)
ax.set_ylim(-6.0, 6.0)

fig.tight_layout()

salida = Path("docs/figuras")
salida.mkdir(parents=True, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(salida / f"fig_9_3_ajuste_compresor.{ext}",
                bbox_inches="tight", facecolor="white")
print("escrito en", salida)

# %% [markdown]
# ## Las cifras que acompañan a la figura
#
# Son las que el ap. 9.5.3 debe publicar junto a ella.

# %%
for nombre in JUEGOS:
    d = datos[nombre]
    dQ = (d["Q_mod"] - d["Q_cat"]) / d["Q_cat"]
    dW = (d["W_mod"] - d["W_cat"]) / d["W_cat"]
    dT = d["T_mod"] - d["T_cat"]
    print(f"{nombre}")
    print(f"   capacidad      max {100*np.abs(dQ).max():5.2f} %   "
          f"rmse {100*np.sqrt(np.mean(dQ**2)):5.2f} %")
    print(f"   potencia eje   max {100*np.abs(dW).max():5.2f} %   "
          f"rmse {100*np.sqrt(np.mean(dW**2)):5.2f} %")
    print(f"   T de descarga  max {np.abs(dT).max():5.2f} K   "
          f"rmse {np.sqrt(np.mean(dT**2)):5.2f} K   "
          f"media {dT.mean():+.2f} K")
