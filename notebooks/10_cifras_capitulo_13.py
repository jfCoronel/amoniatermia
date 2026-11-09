# %% [markdown]
# # Cifras del capitulo 13: comparacion entre fluidos (H5) y TEWI/LCCP (H7)
#
# Decisiones del autor del 05/10/2026 (`docs/DECISIONES_2026_10_05.md`). R-717 con el
# Bock F2 abierto; R-290 con el Bock HG22e/160-4 S HC y R-32 con el Copeland
# ZE49KME-TFM, identificados en el cuaderno 09, con la cilindrada igualada para dar la
# capacidad del R-717 en A35/W12-7 (decision 9b del 29/09) y tubo de cobre en la
# bateria (9c). Misma geometria, consignas y metodo estacional (cap. 12), con la
# MISMA carga de diseno para los tres fluidos (decision 2). Los resultados se guardan
# en `results/cap13/`; con `--reutilizar` la hoja se regenera sin resolver.
#
# Uso: `uv run python notebooks/10_cifras_capitulo_13.py [secciones] [--reutilizar]`

# %%
import importlib.util
import json
import sys
import time
from pathlib import Path

from amoniatermia import ambiental as A
from amoniatermia import campaign as C
from amoniatermia import comparacion as K
from amoniatermia import indicators as I
from amoniatermia import seasonal as S
from amoniatermia import uncertainty as U
from amoniatermia.circuit import MODES
from amoniatermia.reporting import HojaDeCifras, tabla

RES = Path("results/cap13")
REUTILIZAR = "--reutilizar" in sys.argv
FLUIDOS = ("Ammonia", "Propane", "R32")
NOMBRE = {"Ammonia": "R-717", "Propane": "R-290", "R32": "R-32"}
OTROS = ("Propane", "R32")
MODOS = ("M-1", "M-2", "M-3", "M-4", "M-5")
APLICACIONES = (35, 45, 55)
Q_OBJETIVO_W = 10308.0      # R-717 en A35/W12-7 (cap. 12, condicion A del SEER)
KC = 273.15


def _nb(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


NB6 = _nb("nb6", "notebooks/06_cifras_capitulo_11.py")
NB7 = _nb("nb7", "notebooks/07_cifras_capitulo_12.py")


def _guardar(nombre, datos):
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"{nombre}.json").write_text(json.dumps(datos, indent=1, default=float), encoding="utf-8")


def _leer(nombre):
    return json.loads((RES / f"{nombre}.json").read_text(encoding="utf-8"))


def _calculado(nombre, funcion):
    if REUTILIZAR and (RES / f"{nombre}.json").exists():
        return _leer(nombre)
    d = funcion()
    _guardar(nombre, d)
    return d


# %% [markdown]
# ## Igualacion de capacidad (decision 9b)

# %%
def igualacion():
    def f():
        out = {"Ammonia": {"factor": 1.0, "Q": Q_OBJETIVO_W, "sustituciones": {}, "compresor": "compresor_bock_f2"}}
        for fl in OTROS:
            r = K.igualar_cilindrada(fl, Q_OBJETIVO_W)
            out[fl] = {"factor": r.factor, "Q": r.Q, "sustituciones": r.sustituciones, "compresor": r.compresor,
                       "V_swept_catalogo": r.V_swept_catalogo, "iteraciones": r.iteraciones}
        return out
    return _calculado("igualacion", f)


def circuito(fl):
    return C.build_circuit(fluido=fl, sustituciones=igualacion()[fl]["sustituciones"] or None)[0]


def sec_igualacion():
    ig = igualacion()
    filas = [[NOMBRE[fl], ig[fl]["compresor"], f"{ig[fl]['factor']:.4f}", f"{ig[fl]['Q']:.0f} W"] for fl in FLUIDOS]
    return ("Cilindrada escalada hasta igualar la potencia frigorífica del R-717 en A35/W12-7 "
            f"({Q_OBJETIVO_W:.0f} W, cap. 12), con sustitución declarada sobre el volumen barrido.\n\n"
            + tabla(["Fluido", "Compresor", "Factor de cilindrada", "Potencia en A35/W12-7"], filas))


# %% [markdown]
# ## Puntos de diseno de los cinco modos

# %%
def diseno():
    def f():
        out = []
        for fl in FLUIDOS:
            c = circuito(fl)
            for modo in MODOS:
                bc, sp = NB6.punto_diseno(modo)
                pin = NB6.PINZAMIENTOS.get(modo) if fl == "Ammonia" else None
                x0 = c.initial_guess(modo, bc, sp, pinch_air=pin[0], pinch_water=pin[1]) if pin else None
                s = c.solve(modo, bc, sp, x0=x0)
                e = I.energy(s, MODES[modo])
                ind = {"M-1": e.EER, "M-2": e.EER, "M-3": e.COP, "M-4": e.COP}.get(modo, e.COP_global)
                out.append({"fluido": fl, "modo": modo, "convergido": s.converged, "valido": s.valid,
                            "admisible": s.admissible, "residuo": s.max_residual, "Q_util": e.Q_util_clima,
                            "Q_acs": s.Q_acs, "W_el": e.W_el, "indicador": ind, "COP_global": e.COP_global,
                            "T_cond_C": s.T_cond - KC, "T_evap_C": s.T_evap - KC, "T_dis_C": s.T_dis - KC,
                            "Pk_bar": s.unknowns["Pk"] / 1e5, "carga_g": 1e3 * s.charge_sistema.get("_max", float("nan")),
                            "incumple": s.envelope.get("incumple", [])})
                print(f"  {NOMBRE[fl]} {modo}: valido {s.valid} ind {ind:.3f}", flush=True)
        return out
    return _calculado("diseno", f)


def sec_diseno():
    filas = []
    for r in diseno():
        estado = "sí" if r["admisible"] else ("no válido" if not r["valido"] else "no: " + ", ".join(r["incumple"]))
        filas.append([NOMBRE[r["fluido"]], r["modo"], f"{r['Q_util']:.0f} W", f"{r['Q_acs']:.0f} W",
                      f"{r['W_el']:.0f} W", f"{r['indicador']:.3f}", f"{r['T_cond_C']:.1f} °C",
                      f"{r['T_dis_C']:.1f} °C", f"{r['Pk_bar']:.1f} bar", f"{r['carga_g']:.0f} g", estado,
                      f"{r['residuo']:.1e}"])
    return ("Puntos de diseño del capítulo 11 (recalentamiento 5 K, subenfriamiento 2 K). Indicador: EER en "
            "M-1 y M-2, COP en M-3 y M-4, COP global en M-5. Carga: sistema, peor caso de la banda.\n\n"
            + tabla(["Fluido", "Modo", "Q útil", "Q ACS", "W eléctrica", "Indicador", "Tk", "Descarga", "pk",
                     "Carga", "Admisible", "Residuo"], filas))


# %% [markdown]
# ## Estacional con la carga de diseno del R-717

# %%
def calor_nh3(velocidad="fija"):
    """SCOP del R-717 del cap. 12 (Tbiv = TOL). H5 se contrasta a VELOCIDAD FIJA para los tres
    fluidos (decisión V4 del 15/10/2026): el compresor de R-32 no admite velocidad variable. El
    resultado con velocidad variable del R-717 se publica aparte (`velocidad="variable"`)."""
    rs = json.loads(Path("results/cap12/calor_base.json").read_text(encoding="utf-8"))
    rs = [NB7._regla_actual(r) for r in rs]
    if velocidad == "variable":
        return rs
    return [dict(r["velocidad_fija"], fluido="Ammonia") if r.get("velocidad_fija") else r for r in rs]


def estacional():
    def f():
        pd = {(r["aplicacion"], r["clima"]): r["Pdesignh"] for r in calor_nh3() if r.get("TOL") is not None}
        out = {"frio": {}, "calor": []}
        for fl in OTROS:
            ev = S.Evaluador(circuito=circuito(fl))
            t = time.time()
            out["frio"][fl] = S.seer_equipo(ev, NB7.climas(), velocidad="fija")
            for a in APLICACIONES:
                Tin, Tout = S.NOMINAL_AGUA[a]
                m, _ = ev.caudal_nominal("M-4", 7.0, Tin, Tout)
                for c in NB7.climas():
                    r = S.scop_equipo(ev, c, a, m_agua=m, Pdesignh=pd.get((a, c.nombre)),
                                      velocidad="fija")
                    r["fluido"] = fl
                    out["calor"].append({k: v for k, v in r.items() if k != "intervalos"})
                    print(f"  {NOMBRE[fl]} {a} °C {c.nombre}: TOL {r.get('TOL')} SCOP {r.get('SCOP', float('nan')):.3f}",
                          flush=True)
            out.setdefault("tiempo_s", {})[fl] = time.time() - t
        return out
    return _calculado("estacional", f)


def tabla_scop():
    """{(fluido, aplicacion, clima): resultado}."""
    t = {("Ammonia", r["aplicacion"], r["clima"]): r for r in calor_nh3() if r.get("TOL") is not None}
    for r in estacional()["calor"]:
        t[(r["fluido"], r["aplicacion"], r["clima"])] = r
    return t


def tabla_seer():
    f13 = {fl: d["climas"] for fl, d in estacional()["frio"].items()}
    fr = json.loads(Path("results/cap12/frio.json").read_text(encoding="utf-8"))
    f13["Ammonia"] = fr.get("velocidad_fija") or fr["climas"]     # H5 a velocidad fija (V4)
    f13["Ammonia_variable"] = fr["climas"]
    return f13


def sec_estacional():
    t = tabla_scop()
    filas = []
    for a in APLICACIONES:
        for c in NB7.climas():
            fila = [f"{a} °C", c.nombre]
            for fl in FLUIDOS:
                r = t.get((fl, a, c.nombre))
                fila.append("—" if r is None or r.get("TOL") is None else
                            f"{r['SCOP']:.3f} (TOL {r['TOL']} °C, apoyo {100 * r['fraccion_apoyo']:.0f} %)")
            filas.append(fila)
    var = {(r["aplicacion"], r["clima"]): r for r in calor_nh3("variable") if r.get("TOL") is not None}
    for fila, (a, c) in zip(filas, [(a, c.nombre) for a in APLICACIONES for c in NB7.climas()]):
        r = var.get((a, c))
        fila.append("—" if r is None else f"{r['SCOP']:.3f}")
    sr = tabla_seer()
    frio = [[c] + [f"{sr[fl][c]['SEER']:.3f}" for fl in FLUIDOS]
            + [f"{sr['Ammonia_variable'][c]['SEER']:.3f}" if c in sr["Ammonia_variable"] else "—"]
            for c in sr["Ammonia"]]
    return ("H5 a VELOCIDAD FIJA para los tres fluidos (decisión V4 del 15/10/2026): el compresor de "
            "R-32 no admite velocidad variable. La última columna es el R-717 con velocidad variable "
            "(cap. 12), resultado propio que no entra en H5. "
            "Carga de diseño de calefacción COMÚN: la del R-717 con Tbiv = TOL (cap. 12), en cada clima y "
            "aplicación (decisión 2 del 05/10/2026). La TOL de cada fluido es la de su compresor (zona sin "
            "límites de su diagrama y presiones máximas; el R-290 y el R-32 no tienen límite de descarga "
            "publicado). Refrigeración: Pdesignc = potencia en A de cada fluido, igualada.\n\n"
            + tabla(["Aplicación", "Clima"] + [f"SCOP {NOMBRE[fl]}" for fl in FLUIDOS]
                    + ["SCOP R-717, velocidad variable"], filas)
            + "\n### SEER\n\n" + tabla(["Clima"] + [NOMBRE[fl] for fl in FLUIDOS]
                                          + ["R-717, velocidad variable"], frio))


# %% [markdown]
# ## H5: el R-717 frente a cada fluido, +5 % y fuera de la banda

# %%
def bandas_h5():
    def f():
        ig = igualacion()
        out = {}
        evs = {}
        for fl in FLUIDOS:
            for modo in ("M-2", "M-4"):
                bc, sp = NB6.punto_diseno(modo)
                evs[(fl, modo)] = U.Evaluador(modo, bc, sp, fluido=fl, base=ig[fl]["sustituciones"])
        for fl in OTROS:
            for modo, mag in (("M-2", "EER"), ("M-4", "COP")):
                r = U.bandas_diferencia(evs[("Ammonia", modo)], evs[(fl, modo)], {mag: ("indicador", "indicador")})
                out[f"{fl}|{modo}"] = {k: v for k, v in r[mag].items() if k != "filas"}
                print(f"  {NOMBRE[fl]} {modo}: d {r[mag]['d']:+.4f} banda {r[mag]['banda_rss']:.4f}", flush=True)
        return out
    return _calculado("bandas_h5", f)


def sec_h5():
    t, sr, b = tabla_scop(), tabla_seer(), bandas_h5()
    filas = []
    for fl in OTROS:
        for a in APLICACIONES:
            r0, r1 = t.get(("Ammonia", a, "medio")), t.get((fl, a, "medio"))
            if r0 and r1:
                d = r0["SCOP"] / r1["SCOP"] - 1
                filas.append([f"R-717 frente a {NOMBRE[fl]}", f"SCOP {a} °C, clima medio", f"{100 * d:+.1f} %",
                              "sí" if d >= 0.05 else "no"])
        d = sr["Ammonia"]["medio"]["SEER"] / sr[fl]["medio"]["SEER"] - 1
        filas.append([f"R-717 frente a {NOMBRE[fl]}", "SEER, clima medio", f"{100 * d:+.1f} %", "sí" if d >= 0.05 else "no"])
    bf = [[f"R-717 frente a {NOMBRE[k.split('|')[0]]}", k.split("|")[1], f"{100 * v['d']:+.2f} %",
           f"± {100 * v['banda_rss']:.2f} %", f"± {100 * v['banda_lineal']:.2f} %",
           ", ".join(f"{g} {100 * x:.2f} %" for g, x in v["grupos"].items())] for k, v in b.items()]
    return ("Criterio de H5 (tabla 1.2): SCOP y SEER del R-717 iguales o mayores que los de R-290 y R-32 más "
            "un 5 %, sobre la misma arquitectura; la diferencia cuenta si sale de la banda de incertidumbre "
            "sobre la diferencia (§6.11). La banda se calcula en los puntos de diseño (M-2: EER; M-4: COP), "
            "aplicando cada perturbación a los dos fluidos a la vez. El rendimiento electromecánico solo "
            "perturba al R-717 (los herméticos llevan el motor dentro de sus parámetros): no se cancela.\n\n"
            + tabla(["Comparación", "Indicador", "Diferencia del R-717", "Cumple +5 %"], filas)
            + "\n### Banda de incertidumbre sobre la diferencia (puntos de diseño)\n\n"
            + tabla(["Comparación", "Modo", "Diferencia", "Banda RSS", "Banda lineal", "Grupos"], bf))


# %% [markdown]
# ## TEWI y LCCP (H7)

# %%
def consumo_anual(fl, clima, aplicacion=45):
    """kWh/año de calefacción (aplicación de diseño, 45 °C) y refrigeración por el
    método de la norma (decisión 12 del 05/10/2026)."""
    r = tabla_scop().get((fl, aplicacion, clima))
    sr = tabla_seer()[fl].get(clima)
    Eh = r["Q_H_kWh"] / r["SCOP"] if r and r.get("SCOP") else 0.0
    Ec = sr["Q_C_kWh"] / sr["SEER"] if sr else 0.0
    return Eh + Ec, Eh, Ec


def carga_peor(fl):
    return max(r["carga_g"] for r in diseno() if r["fluido"] == fl and r["valido"]) / 1e3


def sec_tewi():
    filas = []
    for clima in ("medio", "Sevilla", "Madrid", "Burgos"):
        for beta in (0.103, 0.15, 0.36):
            fila = [clima, f"{beta:.3f}"]
            for fl in FLUIDOS:
                E, _, _ = consumo_anual(fl, clima)
                t = A.tewi(fl, carga_peor(fl), E, beta)
                fila.append(f"{t['TEWI'] / 1e3:.2f} t ({100 * (t['directo_fugas'] + t['directo_fin_de_vida']) / t['TEWI']:.1f} % directo)")
            filas.append(fila)
    rd = [[NOMBRE[fl], f"{1e3 * carga_peor(fl):.0f} g",
           f"{A.tewi_rd552(fl, carga_peor(fl), consumo_anual(fl, 'medio')[0], 0.15)['TEWI'] / 1e3:.2f} t"] for fl in FLUIDOS]
    return ("TEWI con el caso base del IIR (fugas 2.5 %/año, 15 % al fin de vida, 15 años; decisión 4) y el GWP "
            "del Reglamento (UE) 2024/573 (decisión 3). Consumo: calefacción a 45 °C y refrigeración por el método "
            "de la norma (decisión 12). Carga: el peor modo válido de cada fluido, sistema, peor caso de la banda. "
            "Factor de emisión: cota inferior y superior de H7 y el dato de REE de 2024.\n\n"
            + tabla(["Clima", "β [kg/kWh]"] + [NOMBRE[fl] for fl in FLUIDOS], filas)
            + "\n### Caso reglamentario RD 552/2019 (clima medio, β = 0.15)\n\n"
            + tabla(["Fluido", "Carga", "TEWI"], rd))


def sec_lccp():
    from amoniatermia import data as D
    masas = D.load("ambiental").require("masas_kg")
    filas = []
    for clima in ("medio", "Sevilla", "Madrid", "Burgos"):
        for beta in (0.103, 0.15, 0.36):
            fila = [clima, f"{beta:.3f}"]
            for fl in FLUIDOS:
                E, _, _ = consumo_anual(fl, clima)
                r = A.lccp(fl, carga_peor(fl), E, beta, masas[fl])
                fila.append(f"{r['LCCP'] / 1e3:.2f} t")
            filas.append(fila)
    E = {fl: consumo_anual(fl, "medio")[0] for fl in FLUIDOS}
    des = []
    for fl in FLUIDOS:
        r = A.lccp(fl, carga_peor(fl), E[fl], 0.15, masas[fl])
        des.append([NOMBRE[fl], f"{r['directo']:.0f}", f"{r['indirecto_energia']:.0f}",
                    f"{r['indirecto_materiales']:.0f}", f"{r['indirecto_refrigerante']:.1f}", f"{r['LCCP']:.0f}"])
    return ("LCCP (IIR, 2016) con los parámetros del TEWI, la fabricación del refrigerante (IIR, tabla 4.4; NH3, "
            "IPCC 2006) y la de los materiales (IIR, tabla 4.2; inoxidable, worldstainless), con las masas de "
            "`data/ambiental.yaml` (decisión 13).\n\n"
            + tabla(["Clima", "β [kg/kWh]"] + [NOMBRE[fl] for fl in FLUIDOS], filas)
            + "\n### Desglose en el clima medio con β = 0.15 [kg CO₂e]\n\n"
            + tabla(["Fluido", "Directo", "Energía", "Materiales", "Refrigerante", "LCCP"], des))


def sec_figuras():
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    COL = {"Ammonia": "#eb6834", "Propane": "#2e9a6b", "R32": "#2a78d6"}
    TINTA, TINTA_2, GRIS = "#0b0b0b", "#52514e", "#b8b7b2"
    mpl.rcParams.update({
        "figure.dpi": 120, "savefig.dpi": 300, "font.size": 8, "axes.titlesize": 8,
        "axes.labelsize": 8, "legend.fontsize": 7, "axes.edgecolor": GRIS,
        "axes.labelcolor": TINTA, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "lines.linewidth": 1.5})
    salida = Path("docs/figuras")
    t, sr = tabla_scop(), tabla_seer()
    climas = ["medio", "calido", "frio", "Sevilla", "Madrid", "Burgos"]
    etiqueta = {"medio": "Medio", "calido": "Cálido", "frio": "Frío"}
    # Figura 13.1: SCOP a 45 °C por clima y SEER
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.5), gridspec_kw={"width_ratios": [3, 2]})
    x = np.arange(len(climas)); w = 0.26
    for i, fl in enumerate(FLUIDOS):
        axes[0].bar(x + (i - 1) * w, [t[(fl, 45, c)]["SCOP"] for c in climas], w * 0.92,
                    color=COL[fl], label=NOMBRE[fl])
    axes[0].set_xticks(x, [etiqueta.get(c, c) for c in climas])
    axes[0].set_title("SCOP, aplicación de 45 °C", loc="left", color=TINTA)
    cf = list(sr["Ammonia"])
    x2 = np.arange(len(cf))
    for i, fl in enumerate(FLUIDOS):
        axes[1].bar(x2 + (i - 1) * w, [sr[fl][c]["SEER"] for c in cf], w * 0.92, color=COL[fl])
    axes[1].set_xticks(x2, [etiqueta.get(c, c) for c in cf])
    axes[1].set_title("SEER, agua a 7 °C", loc="left", color=TINTA)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_13_1_scop_seer.{ext}", bbox_inches="tight")
    plt.close(fig)
    # Figura 13.2: TEWI frente al factor de emision
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.4), sharey=False)
    betas = np.linspace(0.10, 0.36, 14)
    for ax, clima in zip(axes, ("medio", "Sevilla")):
        for fl in FLUIDOS:
            E = consumo_anual(fl, clima)[0]
            ax.plot(betas, [A.tewi(fl, carga_peor(fl), E, b)["TEWI"] / 1e3 for b in betas], color=COL[fl],
                    label=NOMBRE[fl])
        ax.axvspan(0.15, 0.36, color=GRIS, alpha=0.15, lw=0)
        ax.axvline(0.103, color=TINTA_2, lw=0.8, ls=":")
        ax.set_title(f"TEWI, clima {etiqueta.get(clima, clima).lower() if clima in etiqueta else 'de ' + clima}",
                     loc="left", color=TINTA)
        ax.set_xlabel("Factor de emisión de la red [kg CO₂/kWh]")
    axes[0].set_ylabel("TEWI en 15 años [t CO₂e]")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_13_2_tewi.{ext}", bbox_inches="tight")
    plt.close(fig)
    return "Figuras escritas en `docs/figuras`: fig_13_1_scop_seer, fig_13_2_tewi (png y pdf)."


def sec_puntos_no_validos():
    filas = [[NOMBRE[r["fluido"]], f"{r['aplicacion']} °C", r["clima"], ", ".join(f"{t:g} °C" for t in r["puntos_no_validos"])]
             for r in estacional()["calor"] if r.get("puntos_no_validos")]
    return ("Puntos de carga parcial que no convergen tras el reintento por continuación: se excluyen de la "
            "interpolación y no se toman por no admisibles.\n\n"
            + tabla(["Fluido", "Aplicación", "Clima", "Aire"], filas))


# %% [markdown]
# ## Escenario: compresor sin envolvente (decision del autor del 20/10/2026)
#
# Supone un compresor que, fuera de la envolvente de su fabricante, sigue la tendencia de sus
# datos: todo punto valido es admisible (sin diagrama ni limite de descarga) y los polinomios
# de UNE-EN 12900 extrapolan. La carga de diseno es la del caso base (la misma vivienda), y los
# tres fluidos se calculan a velocidad fija, como H5. Mide lo que la envolvente le quita a cada
# fluido; no es un resultado de un equipo existente.

# %%
def sin_envolvente(fl):
    if fl == "Ammonia":   # el R-717 a velocidad fija del escenario del cap. 12 (mismos puntos)
        rs = json.loads(Path("results/cap12/calor_sin_envolvente.json").read_text(encoding="utf-8"))
        return [dict(r["velocidad_fija"], fluido="Ammonia", puntos=r.get("puntos_velocidad_maxima", []))
                for r in rs if r.get("velocidad_fija")]

    def f():
        pd = {(r["aplicacion"], r["clima"]): r["Pdesignh"] for r in calor_nh3() if r.get("TOL") is not None}
        ev = S.Evaluador(circuito=circuito(fl))
        out = []
        for a in APLICACIONES:
            Tin, Tout = S.NOMINAL_AGUA[a]
            m, _ = ev.caudal_nominal("M-4", 7.0, Tin, Tout)
            for c in NB7.climas():
                r = S.scop_equipo(ev, c, a, m_agua=m, Pdesignh=pd.get((a, c.nombre)), velocidad="fija",
                                  variante="sin_envolvente")
                r["fluido"] = fl
                out.append({k: v for k, v in r.items() if k not in ("intervalos", "sensibilidad_tbiv_max")})
                print(f"  {NOMBRE[fl]} {a} °C {c.nombre}: TOL {r.get('TOL')} SCOP {r.get('SCOP', float('nan')):.3f}",
                      flush=True)
        return out
    return _calculado(f"sin_envolvente_{fl}", f)


def _fuera_envolvente(fl, p):
    """El punto queda fuera de la envolvente del caso base: fuera de la zona sin límites o, en el
    R-717, con la descarga por encima de 140 °C."""
    return (p.get("zona") != "sin_limites"
            or (fl == "Ammonia" and p.get("T_dis_C", 0.0) > 140.0))


def tabla_sin_envolvente():
    return {(r["fluido"], r["aplicacion"], r["clima"]): r for fl in FLUIDOS for r in sin_envolvente(fl)}


def sec_sin_envolvente():
    t0, t1 = tabla_scop(), tabla_sin_envolvente()
    filas = []
    for a in APLICACIONES:
        for c in NB7.climas():
            fila = [f"{a} °C", c.nombre]
            for fl in FLUIDOS:
                r0, r1 = t0.get((fl, a, c.nombre)), t1.get((fl, a, c.nombre))
                fila.append("—" if not r1 or r1.get("TOL") is None else
                            f"{r1['SCOP']:.3f} (base {r0['SCOP']:.3f}; TOL {r1['TOL']} °C, apoyo "
                            f"{100 * r1['fraccion_apoyo']:.0f} %)")
            filas.append(fila)
    h5 = []
    for fl in OTROS:
        for a in APLICACIONES:
            for c in ("medio", "Sevilla", "Madrid", "Burgos"):
                r0, r1 = t1.get(("Ammonia", a, c)), t1.get((fl, a, c))
                b0, b1 = t0.get(("Ammonia", a, c)), t0.get((fl, a, c))
                d, db = r0["SCOP"] / r1["SCOP"] - 1, b0["SCOP"] / b1["SCOP"] - 1
                h5.append([f"R-717 frente a {NOMBRE[fl]}", f"SCOP {a} °C, {c}", f"{100 * db:+.1f} %",
                           f"{100 * d:+.1f} %", "sí" if d >= 0.05 else "no"])
    ext = []
    for fl in FLUIDOS:
        pts = [p for r in sin_envolvente(fl) for p in r.get("puntos", [])]
        fuera = [p for p in pts if _fuera_envolvente(fl, p)]
        ext.append([NOMBRE[fl], str(len(pts)), str(len(fuera)),
                    f"{max(p['T_dis_C'] for p in pts):.0f} °C" if pts else "—"])
    tw = []
    for clima in ("medio", "Sevilla", "Madrid", "Burgos"):
        for beta in (0.15, 0.36):
            fila = [clima, f"{beta:.2f}"]
            for fl in FLUIDOS:
                r = t1.get((fl, 45, clima))
                sr = tabla_seer()[fl].get(clima)
                E = r["Q_H_kWh"] / r["SCOP"] + (sr["Q_C_kWh"] / sr["SEER"] if sr else 0.0)
                fila.append(f"{A.tewi(fl, carga_peor(fl), E, beta)['TEWI'] / 1e3:.2f} t")
            tw.append(fila)
    return ("Escenario del autor (20/10/2026): un compresor que fuera de la envolvente de su fabricante sigue "
            "la tendencia de sus datos. Todo punto válido es admisible —sin diagrama de aplicación ni límite de "
            "descarga— y los polinomios de UNE-EN 12900 extrapolan. Misma carga de diseño que el caso base (la "
            "del R-717 con su TOL real, la misma vivienda), velocidad fija en los tres fluidos, como H5. El SEER "
            "no cambia: todos los puntos de refrigeración ya eran admisibles.\n\n"
            + tabla(["Aplicación", "Clima"] + [f"SCOP {NOMBRE[fl]}" for fl in FLUIDOS], filas)
            + "\n### H5 en el escenario (diferencia del R-717; base y sin envolvente)\n\n"
            + tabla(["Comparación", "Indicador", "Base", "Sin envolvente", "Cumple +5 %"], h5)
            + "\n### Puntos fuera de la envolvente del caso base\n\n"
            + tabla(["Fluido", "Puntos de carga parcial", "Fuera de la envolvente", "Descarga máxima"], ext)
            + "\n### TEWI en el escenario (calefacción a 45 °C y refrigeración)\n\n"
            + tabla(["Clima", "β [kg/kWh]"] + [NOMBRE[fl] for fl in FLUIDOS], tw))


# %%
SECCIONES = {"igualacion": sec_igualacion, "diseno": sec_diseno, "estacional": sec_estacional,
             "h5": sec_h5, "tewi": sec_tewi, "lccp": sec_lccp, "no_validos": sec_puntos_no_validos,
             "sin_envolvente": sec_sin_envolvente, "figuras": sec_figuras}

if __name__ == "__main__":
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SECCIONES)
    hoja = HojaDeCifras("docs/cifras_capitulo_13.md", "Cifras del capítulo 13", "notebooks/10_cifras_capitulo_13.py")
    for nombre in pedidas:
        print(f"[{nombre}] calculando…", flush=True)
        hoja.seccion(nombre, SECCIONES[nombre]())
    print("escrito", hoja.ruta)
