# %% [markdown]
# # Cifras del capitulo 12: rendimiento estacional (UNE-EN 14825:2024) y ACS
#
# Decisiones del autor del 02/10/2026 (`docs/DECISIONES_2026_10_02.md`, 4 a 11).
# Cada punto de carga parcial es un equilibrio del sistema completo
# (`seasonal.Evaluador`). Los resultados se guardan en `results/cap12/`; con
# `--reutilizar` la hoja se regenera desde ellos sin volver a resolver.
#
# Uso: `uv run python notebooks/07_cifras_capitulo_12.py [secciones] [--reutilizar]`

# %%
import json
import sys
import time
from pathlib import Path

from amoniatermia import seasonal as S
from amoniatermia.reporting import HojaDeCifras, tabla

RESULTADOS = Path("results/cap12")
REUTILIZAR = "--reutilizar" in sys.argv
APLICACIONES = (35, 45, 55)
CLIMAS_NORMA = ("medio", "calido", "frio")
CIUDADES = ("Sevilla", "Madrid", "Burgos")
_EV = None


def ev():
    global _EV
    if _EV is None:
        _EV = S.Evaluador()
    return _EV


def climas():
    return [S.clima_norma(c) for c in CLIMAS_NORMA] + [S.clima_cte(c) for c in CIUDADES]


def _guardar(nombre, datos):
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / f"{nombre}.json").write_text(json.dumps(datos, indent=1, default=float),
                                               encoding="utf-8")


def _leer(nombre):
    return json.loads((RESULTADOS / f"{nombre}.json").read_text(encoding="utf-8"))


def _sin_intervalos(r):
    return {k: v for k, v in r.items() if k != "intervalos"}


# %% [markdown]
# ## Climas

# %%
def sec_climas():
    filas = []
    for c in climas():
        filas.append([c.nombre, c.procedencia, f"{c.Tdesignh} °C", f"{c.Tbiv_max} °C",
                      f"≤ {c.TOL_max} °C" if c.TOL_max is not None else "—",
                      sum(c.bins_calor.values()), sum(c.bins_frio.values()) or "—"])
    return ("Horas por intervalo de 1 K. Los climas de la norma, de las tablas B.1 y D.1 (la "
            "refrigeración solo tiene clima medio); las ciudades, de todas las horas del clima de "
            "referencia CTE de su zona, por debajo de 15.5 °C en calefacción y desde 16.5 °C en "
            "refrigeración. Tdesignh de las ciudades: percentil 99.6 % (decisión 8); Tbiv máxima, "
            "la del clima medio. La norma no fija TOL para las ciudades.\n\n"
            + tabla(["Clima", "Fuente", "Tdesignh", "Tbiv máxima", "TOL exigida",
                     "Horas de calefacción", "Horas de refrigeración"], filas))


# %% [markdown]
# ## Refrigeracion: SEER (M-2, ventiloconvector, salida fija a 7 °C)

# %%
def sec_frio():
    if REUTILIZAR:
        r = _leer("frio")
    else:
        t = time.time()
        r = S.seer_equipo(ev(), climas())
        r["velocidad_fija"] = {c: S._sin_tabla(v) for c, v in
                               S.seer_equipo(ev(), climas(), velocidad="fija")["climas"].items()}
        r["tiempo_s"] = time.time() - t
        _guardar("frio", r)
    pts = [[p["condicion"], f"{p['T_aire_C']:g} °C", f"{p['T_in_C']:.2f} / {p['T_out_C']:.2f} °C",
            f"{p['P']:.0f} W", f"{p['EER']:.3f}", f"{p.get('rpm', 1450):.0f} rpm",
            p.get("regimen", "plena"), f"{p['T_dis_C']:.1f} °C", p["zona"],
            "sí" if p["admisible"] else "no"] for p in r["puntos"]]
    res = [[c, f"{v['SEER']:.3f}", f"{v['eta_s']:.1f} %", f"{v['Q_C_kWh']:.0f} kWh"]
           for c, v in r["climas"].items()]
    fija = r.get("velocidad_fija") or {}
    res = [[c, f"{v['SEER']:.3f}", f"{v['eta_s']:.1f} %", f"{v['Q_C_kWh']:.0f} kWh",
            f"{fija[c]['SEER']:.3f}" if c in fija else "—"]
           for c, v in r["climas"].items()]
    return (f"Velocidad variable (decisión P4 del 15/10/2026): A a la velocidad máxima; B, C y D a la "
            "velocidad cuya capacidad iguala la carga parcial de la norma, o a la mínima (960 rpm) con "
            "marcha/paro si aun así la supera. "
            f"Caudal fijo del ensayo A (12/7 °C): {r['m_agua']:.4f} kg/s. Pdesignc = potencia en A, "
            f"{r['Pdesignc']:.0f} W. Cd = 0.9; sin auxiliares (cota superior); η_s,c = SEER/2.5 − 3 %. "
            "Ventilador a caudal y consumo constantes (decisión V3).\n\n"
            + tabla(["Condición", "Aire", "Agua entrada / salida", "Potencia frigorífica", "EER",
                     "Velocidad", "Régimen", "Descarga", "Zona", "Admisible"], pts)
            + "\n" + tabla(["Clima", "SEER", "η_s,c", "Demanda anual",
                             "SEER a velocidad fija (marcha/paro a 1450 rpm)"], res))


# %% [markdown]
# ## Calefaccion: SCOP (M-4) por clima y aplicacion

# %%
def _calor(variante):
    nombre = f"calor_{variante}"
    if REUTILIZAR:
        return [_regla_actual(r) for r in _leer(nombre)]
    out = []
    caudal = {}
    for a in APLICACIONES:
        Tin, Tout = S.NOMINAL_AGUA[a]
        caudal[a], _ = ev().caudal_nominal("M-4", 7.0, Tin, Tout)
        for c in climas():
            t = time.time()
            r = S.scop_equipo(ev(), c, a, variante=variante, m_agua=caudal[a])
            r["tiempo_s"] = time.time() - t
            out.append(r)
            print(f"  {variante} {a} °C {c.nombre}: TOL {r.get('TOL')} SCOP {r.get('SCOP', float('nan')):.3f}",
                  flush=True)
    _guardar(nombre, out)
    return out


def _regla_actual(r):
    """Resultados guardados con la regla anterior (Tbiv maxima): se recalculan
    desde los mismos puntos con Tbiv = TOL y la sensibilidad (decision 7 corregida)."""
    if r.get("TOL") is None or "regla_tbiv" in r:
        return r
    c = {k.nombre: k for k in climas()}[r["clima"]]
    n = S.scop_desde_puntos(c, r["aplicacion"], r["puntos"], r["TOL"], "TOL")
    n.update(variante=r["variante"], m_agua=r["m_agua"],
             sensibilidad_tbiv_max=S._sin_tabla(
                 S.scop_desde_puntos(c, r["aplicacion"], r["puntos"], r["TOL"], "max")))
    return n


def _tabla_calor(rs):
    filas = []
    for r in rs:
        if r.get("TOL") is None:
            filas.append([f"{r['aplicacion']} °C", r["clima"], "—", "—", "—", "—", "—", "—", "—", "—", "—"])
            continue
        cumple = r.get("cumple_TOL_norma")
        filas.append([f"{r['aplicacion']} °C", r["clima"], f"{r['TOL']} °C",
                      "sí" if cumple else ("no" if cumple is False else "—"), f"{r['Tbiv']} °C",
                      f"{r['Pdesignh'] / 1e3:.2f} kW", f"{r['SCOP']:.3f}", f"{r['eta_s']:.0f} %",
                      f"{100 * r['fraccion_apoyo']:.1f} %",
                      f"{r['sensibilidad_tbiv_max']['SCOP']:.3f} (Tbiv {r['sensibilidad_tbiv_max']['Tbiv']} °C)",
                      f"{r['velocidad_fija']['SCOP']:.3f}" if r.get("velocidad_fija") else "—"])
    return tabla(["Aplicación", "Clima", "TOL real", "TOL de la norma", "Tbiv", "Pdesignh",
                  "SCOP", "η_s,h", "Calor del apoyo", "SCOP con Tbiv máxima (velocidad máxima)",
                  "SCOP a velocidad fija"], filas)


def _tabla_puntos(rs, aplicacion, clima):
    for r in rs:
        if r["aplicacion"] == aplicacion and r["clima"] == clima and r.get("puntos"):
            return tabla(["Aire", "Agua entrada / salida", "Carga", "Potencia", "COP", "Velocidad",
                          "Régimen", "Descarga", "Zona", "Admisible"],
                         [[f"{p['T_aire_C']:g} °C", f"{p['T_in_C']:.2f} / {p['T_out_C']:.2f} °C",
                           f"{p.get('carga', p['P']):.0f} W", f"{p['P']:.0f} W", f"{p['COP']:.3f}",
                           f"{p.get('rpm', 1450):.0f} rpm", p.get("regimen", "plena"),
                           f"{p['T_dis_C']:.1f} °C", p["zona"],
                           "sí" if p["admisible"] else "no"] for p in r["puntos"]])
    return "—"


def sec_calor():
    rs = _calor("base")
    caudales = sorted({(r["aplicacion"], r["m_agua"]) for r in rs if "m_agua" in r})
    return ("Velocidad variable (decisión P4 del 15/10/2026): TOL real, Tbiv y Pdesignh con los puntos a "
            "la velocidad máxima; en cada punto de la norma por encima de la TOL, el equipo a la velocidad "
            "cuya capacidad iguala la carga parcial, o a la mínima (960 rpm) con marcha/paro si aun así "
            "la supera. Motor y transmisión con rendimiento constante y ventilador a caudal y consumo "
            "constantes (decisiones V2 y V3). "
            "TOL real: la temperatura entera más baja desde la que todos los puntos son admisibles "
            "(solo la zona sin límites del diagrama y descarga ≤ 140 °C). Por debajo, apoyo eléctrico "
            "con COP 1. Pdesignh con Tbiv = TOL real, como declara el mercado (decisión 7 corregida el "
            "02/10/2026); la Tbiv máxima de la norma, como sensibilidad. Cd = 0.9; sin "
            "desescarche ni auxiliares: cota superior. η_s,h = SCOP/2.5 − 3 %. Caudales fijos del "
            "ensayo nominal A7/6: " + ", ".join(f"{a} °C {m:.4f} kg/s" for a, m in caudales) + ".\n\n"
            + _tabla_calor(rs)
            + "\n### Puntos del clima medio a 35 °C\n\n" + _tabla_puntos(rs, 35, "medio")
            + "\n### Puntos del clima medio a 55 °C\n\n" + _tabla_puntos(rs, 55, "medio"))


def sec_variante():
    rs = _calor("refrigeracion_suplementaria")
    return ("Sensibilidad (decisión 6): la misma máquina con tapa de cilindro refrigerada, en que la "
            "zona de refrigeración suplementaria del diagrama también es admisible; se mantiene el "
            "límite de 140 °C.\n\n" + _tabla_calor(rs))


# %% [markdown]
# ## ACS anual (decisiones 9 y 12): recuperacion de M-1/M-3 y M-5 a 45 °C

# %%
def sec_acs():
    from amoniatermia import maps as MP
    # M-5 sigue leyéndose de los mapas del cap. 11 (produce ACS a velocidad máxima); la
    # recuperación de M-3 y M-1, en los puntos de carga parcial a su velocidad (decisión V5).
    mapas = {k: MP.PerformanceMap.read(Path("results/cap11") / k)
             for k in ("M-1", "M-2", "M-3", "M-4", "M-5")}
    calor = {r["clima"]: r for r in _calor("base") if r["aplicacion"] == 45 and r.get("TOL") is not None}
    frio = _leer("frio") if (RESULTADOS / "frio.json").exists() else S.seer_equipo(ev(), climas())
    filas = []
    for c in climas():
        if c.nombre not in calor:
            continue
        pa = S.acs_puntos(ev(), calor[c.nombre], frio if c.nombre in frio["climas"] else None)
        r = S.acs_anual(c, calor[c.nombre], frio["climas"].get(c.nombre), mapas, puntos_acs=pa)
        filas.append([c.nombre, f"{r['demanda_kWh']:.0f} kWh", f"{100 * r['fraccion_recuperada']:.1f} %",
                      f"{r['M5_kWh']:.0f} kWh", f"{r['COP_M5_medio']:.2f}",
                      f"{r['E_incremento_recuperacion_kWh']:+.0f} kWh", f"{r['E_ACS_kWh']:.0f} kWh",
                      f"{r['SPF_ACS']:.2f}",
                      ", ".join(f"{k} {', '.join(f'{t:g} °C' for t in v)}" for k, v in r.get("puntos_acs_no_validos", {}).items() if v) or "—"])
    return ("Perfil L (Qref = 11.655 kWh/día, UNE-EN 16147), demanda repartida por igual en las 8760 h. "
            "La recuperación de M-3 (calefacción a 45 °C) y de M-1 (frío) aporta su potencia de ACS por la "
            "fracción de tiempo en marcha, con el tope de la demanda de cada hora; el resto lo produce M-5 a "
            "45 °C sin apoyo eléctrico (RS-15). La recuperación se resuelve en los puntos de carga parcial, "
            "a la velocidad de cada uno (decisión V5), e interpola entre ellos como la norma con el COP; "
            "M-5, de los mapas del capítulo 11 (recalentamiento 5 K, subenfriamiento 2 K). La electricidad de la recuperación es el incremento de M-1/M-3 sobre "
            "M-2/M-4 en el mismo punto, negativo en frío porque el desrecalentador baja la condensación. "
            "Lectura estacionaria de orden de magnitud: no es un η_wh declarable.\n\n"
            + tabla(["Clima", "Demanda", "Recuperada", "Por M-5", "COP medio de M-5",
                     "Electricidad de la recuperación", "Electricidad del ACS", "SPF del ACS",
                     "Puntos de recuperación no válidos (excluidos)"], filas))


# %% [markdown]
# ## Sensibilidad al desescarche (decision 10)

# %%
def sec_desescarche():
    filas = []
    for r in _calor("base"):
        if r.get("TOL") is None:
            continue
        c = {k.nombre: k for k in climas()}[r["clima"]]
        p = S.scop_desde_puntos(c, r["aplicacion"], r["puntos"], r["TOL"], "TOL",
                                desescarche=S.DESESCARCHE)
        filas.append([f"{r['aplicacion']} °C", r["clima"], f"{r['SCOP']:.3f}", f"{p['SCOP']:.3f}",
                      f"{100 * (p['SCOP'] / r['SCOP'] - 1):+.1f} %"])
    return (f"COP de los intervalos con aire ≤ {S.DESESCARCHE['T_max_C']} °C multiplicado por "
            f"{S.DESESCARCHE['factor_COP']}: pérdida de un ciclo de escarcha y desescarche frente al "
            "régimen seco, 7.25 a 9.85 % según la impulsión (Wang et al., Building and Environment, "
            "2024, doi:10.1016/j.buildenv.2024.112258). La potencia no se penaliza.\n\n"
            + tabla(["Aplicación", "Clima", "SCOP sin desescarche", "SCOP con desescarche", "Cambio"],
                    filas))


# %% [markdown]
# ## Figuras del capitulo 12

# %%
def sec_figuras():
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    AZUL, NARANJA, VERDE = "#2a78d6", "#eb6834", "#2e9a6b"
    TINTA, TINTA_2, GRIS = "#0b0b0b", "#52514e", "#b8b7b2"
    mpl.rcParams.update({
        "figure.dpi": 120, "savefig.dpi": 300, "font.size": 8, "axes.titlesize": 8,
        "axes.labelsize": 8, "legend.fontsize": 7, "axes.edgecolor": GRIS,
        "axes.labelcolor": TINTA, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "lines.linewidth": 1.5})
    salida = Path("docs/figuras")
    rs = {(r["aplicacion"], r["clima"]): r for r in _calor("base") if r.get("TOL") is not None}
    # Figura 12.1: potencia de la maquina frente a la carga, clima medio
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.4), sharey=True)
    for ax, a in zip(axes, APLICACIONES):
        r = rs[(a, "medio")]
        pts = sorted(r.get("puntos_velocidad_maxima") or r["puntos"], key=lambda p: p["T_aire_C"])
        x = [p["T_aire_C"] for p in pts]
        ax.plot(x, [p["P"] / 1e3 for p in pts], color=AZUL, label="Potencia de la máquina")
        for p in pts:
            ax.scatter(p["T_aire_C"], p["P"] / 1e3, s=18, zorder=3, linewidths=1.0,
                       color=AZUL if p["admisible"] else "white", edgecolors=AZUL)
        T = np.array([-10.0, 16.0])
        ax.plot(T, r["Pdesignh"] / 1e3 * (T - 16) / (-26), color=NARANJA, ls="--", label="Carga")
        ax.axvspan(-10, r["TOL"], color=GRIS, alpha=0.25, lw=0)
        ax.axvline(r["TOL"], color=TINTA_2, lw=0.8)
        ax.text(r["TOL"] + 0.4, 0.5, f"TOL {r['TOL']} °C", color=TINTA_2, fontsize=7)
        ax.set_title(f"Aplicación de {a} °C", loc="left", color=TINTA)
        ax.set_xlabel("Aire exterior [°C]")
        ax.set_ylim(0, None)
    axes[0].set_ylabel("Potencia térmica [kW]")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_12_1_potencia_carga.{ext}", bbox_inches="tight")
    plt.close(fig)
    # Figura 12.2: eta_s del equipo frente a la muestra de mercado (clima medio)
    import importlib.util
    spec = importlib.util.spec_from_file_location("merc", "notebooks/08_referencia_mercado.py")
    merc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(merc)
    f = merc.muestra()
    frio = _leer("frio")
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.4))
    for ax, (col, titulo, nuestro) in zip(axes, (
            ("eta low T [%]", "ηs,h a 35 °C [%]", rs[(35, "medio")]["eta_s"]),
            ("eta medium T [%]", "ηs,h a 55 °C [%]", rs[(55, "medio")]["eta_s"]),
            ("SEER low T", "SEER a 7 °C", frio["climas"]["medio"]["SEER"]))):
        datos = [f.loc[f.Refrigerant == r, col].dropna() for r in ("R32", "R290")]
        lo = min(min(d.min() for d in datos), nuestro) * 0.95
        hi = max(d.max() for d in datos) * 1.02
        bins = np.linspace(lo, hi, 30)
        for d, c, n in zip(datos, (AZUL, VERDE), ("R-32", "R-290")):
            ax.hist(d, bins=bins, color=c, alpha=0.55, label=f"{n} (n = {len(d)})",
                    weights=np.full(len(d), 100.0 / len(d)))
        ax.axvline(nuestro, color=NARANJA, lw=1.5)
        ax.text(nuestro, ax.get_ylim()[1] * 0.92, " R-717", color=NARANJA, fontsize=7)
        ax.set_title(titulo, loc="left", color=TINTA)
        ax.set_xlabel("")
    axes[0].set_ylabel("Modelos [% de la muestra]")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_12_2_mercado.{ext}", bbox_inches="tight")
    plt.close(fig)
    return "Figuras escritas en `docs/figuras`: fig_12_1_potencia_carga, fig_12_2_mercado (png y pdf)."


# %% [markdown]
# ## Escenario: compresor sin envolvente (decision del autor del 20/10/2026)

# %%
def calor_sin_envolvente():
    """La misma maquina con un compresor que, fuera de la envolvente del fabricante, sigue la
    tendencia de sus datos: todo punto valido es admisible y los polinomios extrapolan. Misma
    carga de diseno que el caso base (la misma vivienda). Guarda tambien la velocidad fija."""
    ruta = RESULTADOS / "calor_sin_envolvente.json"
    if ruta.exists():
        return _leer("calor_sin_envolvente")
    base = {(r["aplicacion"], r["clima"]): r for r in _calor("base") if r.get("TOL") is not None}
    out = []
    for a in APLICACIONES:
        Tin, Tout = S.NOMINAL_AGUA[a]
        m, _ = ev().caudal_nominal("M-4", 7.0, Tin, Tout)
        for c in climas():
            b = base.get((a, c.nombre))
            if b is None:
                continue
            t = time.time()
            r = S.scop_equipo(ev(), c, a, variante="sin_envolvente", m_agua=m, Pdesignh=b["Pdesignh"])
            r["tiempo_s"] = time.time() - t
            out.append({k: v for k, v in r.items() if k != "intervalos"})
            print(f"  sin envolvente {a} °C {c.nombre}: TOL {r.get('TOL')} SCOP {r.get('SCOP', float('nan')):.3f}",
                  flush=True)
    _guardar("calor_sin_envolvente", out)
    return out


def sec_sin_envolvente():
    base = {(r["aplicacion"], r["clima"]): r for r in _calor("base") if r.get("TOL") is not None}
    filas = []
    for r in calor_sin_envolvente():
        b = base[(r["aplicacion"], r["clima"])]
        pts = r.get("puntos_velocidad_maxima") or r.get("puntos") or []
        fuera = [p for p in pts if p.get("zona") != "sin_limites" or p.get("T_dis_C", 0.0) > 140.0]
        filas.append([f"{r['aplicacion']} °C", r["clima"], f"{b['TOL']} / {r['TOL']} °C",
                      f"{b['Pdesignh'] / 1e3:.2f} kW", f"{b['SCOP']:.3f}", f"{r['SCOP']:.3f}",
                      f"{100 * (r['SCOP'] / b['SCOP'] - 1):+.1f} %", f"{r['eta_s']:.0f} %",
                      f"{100 * b['fraccion_apoyo']:.1f} / {100 * r['fraccion_apoyo']:.1f} %",
                      f"{r['velocidad_fija']['SCOP']:.3f}" if r.get("velocidad_fija") else "—",
                      f"{len(fuera)} ({max((p['T_dis_C'] for p in fuera), default=float('nan')):.0f} °C)"])
    return ("Escenario del autor (20/10/2026): un compresor que, fuera de la envolvente del fabricante, sigue "
            "la tendencia de sus datos. Todo punto válido es admisible —sin diagrama de aplicación ni límite "
            "de 140 °C— y los polinomios de UNE-EN 12900 extrapolan. Misma carga de diseño que el caso base (la "
            "misma vivienda) y velocidad variable; la columna de velocidad fija es la que entra en H5 (cap. 13). "
            "Los puntos fuera de la envolvente son los de la velocidad máxima fuera de la zona sin límites o "
            "por encima de 140 °C, con la mayor descarga entre ellos.\n\n"
            + tabla(["Aplicación", "Clima", "TOL base / sin envolvente", "Pdesignh", "SCOP base",
                     "SCOP sin envolvente", "Diferencia", "η_s,h", "Calor del apoyo (base / sin env.)",
                     "SCOP a velocidad fija", "Puntos fuera (descarga máx.)"], filas))


# %%
SECCIONES = {"climas": sec_climas, "frio": sec_frio, "calor": sec_calor, "variante": sec_variante,
             "acs": sec_acs, "desescarche": sec_desescarche, "sin_envolvente": sec_sin_envolvente,
             "figuras": sec_figuras}

if __name__ == "__main__":
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SECCIONES)
    hoja = HojaDeCifras("docs/cifras_capitulo_12.md", "Cifras del capítulo 12",
                        "notebooks/07_cifras_capitulo_12.py")
    for nombre in pedidas:
        print(f"[{nombre}] calculando…", flush=True)
        hoja.seccion(nombre, SECCIONES[nombre]())
    if _EV is not None:
        print("equilibrios resueltos:", _EV.n_soluciones)
    print("escrito", hoja.ruta)
