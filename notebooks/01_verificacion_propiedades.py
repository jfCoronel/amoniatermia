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
# # 01 - Verificacion de la capa de propiedades
#
# Notebook de EXPERIMENTACION. El modelo vive en el paquete `amoniatermia`,
# no aqui. Este notebook solo carga, ejecuta y grafica.
#
# Cubre la verificacion cruzada del apartado 6.6.4 y produce la figura de
# dispersion entre correlaciones de fraccion de huecos que pide el
# apartado 4.12.

# %%
import time
import numpy as np
import matplotlib.pyplot as plt

from amoniatermia.props import Fluid, PropertyProvenance, backend_deviation_report
from amoniatermia.correlations.voidfraction import charge_range

# %% [markdown]
# ## 1. Trazabilidad (apartado 6.12)
# Todo fichero de resultados debe llevar esta procedencia adjunta.

# %%
prov = PropertyProvenance(backend="HEOS", fluids=("Ammonia", "Water"))
prov.as_dict()

# %% [markdown]
# ## 2. Coste de las llamadas de propiedades
# Justifica la decision del apartado 9.10 de no usar `PropsSI` en bucles.

# %%
N = 20000
rng = np.random.default_rng(0)
P = rng.uniform(3e5, 20e5, N)
T = rng.uniform(250, 400, N)

def bench(fluid):
    t0 = time.perf_counter()
    for p, t in zip(P, T):
        fluid.update_PT(p, t); fluid.h
    return (time.perf_counter() - t0) * 1e6 / N

print(f"HEOS      : {bench(Fluid('Ammonia','HEOS')):8.2f} us/llamada")
print(f"BICUBIC   : {bench(Fluid('Ammonia','BICUBIC&HEOS')):8.2f} us/llamada")

# %% [markdown]
# ## 3. Error del backend tabular (verificacion cruzada, ap. 6.6.4)

# %%
states = [(p, t) for p in np.linspace(3e5, 20e5, 8)
                 for t in np.linspace(255, 400, 8)]
rep = backend_deviation_report("Ammonia", states, "BICUBIC&HEOS")
for k, v in rep.items():
    print(f"{k:4s}  max {v['max']:.2e}   media {v['mean']:.2e}")

# %% [markdown]
# ## 4. Dispersion entre correlaciones de fraccion de huecos
# Figura para el apartado 4.12 / 9.9. Es la que justifica reportar RANGO
# de carga y no valor unico.

# %%
f = Fluid("Ammonia")
sat = f.sat_props(6.0e5); sat["p_red"] = f.p_reduced(6.0e5)
xs = np.linspace(0.02, 0.98, 60)

fig, ax = plt.subplots(figsize=(7, 4.2))
for name in ("homogeneous", "zivi", "rouhani_axelsson", "premoli"):
    alphas = [charge_range(x, sat, G=50.0, D_h=0.004)[name]["alpha"] for x in xs]
    ax.plot(xs, alphas, label=name)
ax.set_xlabel("Titulo de vapor  x  [-]")
ax.set_ylabel(r"Fraccion de huecos  $\alpha$  [-]")
ax.set_title("R-717 a 6 bar, G = 50 kg/m2s")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("../docs/fig_voidfraction_dispersion.png", dpi=200)
