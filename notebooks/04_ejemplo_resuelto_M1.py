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
# # 04 - Ejemplo resuelto de M-1 para el nuevo capitulo 9
#
# Notebook de EXPERIMENTACION. Resuelve el punto de diseno de M-1 (aire a 35 C,
# climatizacion 12 C y 0.45 kg/s, ACS de 35 a 67 C, recalentamiento 5 K,
# subenfriamiento 2 K; 60 segmentos y 12 volumenes) y deja TRAZA de todo lo que
# el capitulo necesita contar: la estimacion inicial, la historia del lazo
# externo evaluacion a evaluacion, el estado de cada componente, las
# verificaciones y lo que se reporta junto al punto.
#
# Incluye ademas el contraste de la bateria con la ficha de Frimetal como
# evaporador (26/03/2026), que no se ha usado para anclar nada.
#
# Escribe `docs/cifras_ejemplo_M1.md` y las figuras
# `docs/figuras/fig_ejemplo_M1_perfiles.{png,pdf}` (temperaturas a lo largo de los
# tres intercambiadores) y `fig_ejemplo_M1_convergencia.{png,pdf}`. Uso (~1 min):
#
#     uv run python notebooks/04_ejemplo_resuelto_M1.py

# %%
import time
from pathlib import Path

import CoolProp
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid, MODES,
                          PlateHeatExchanger,
                          Setpoints, WaterStream)
from amoniatermia import data as D
from amoniatermia import indicators as I
from amoniatermia.props import git_revision

PRES_RS5 = I.presupuesto_RS5()

K = 273.15
M_AIRE = None   # 7 600 m3/h: el caudal masico lo deduce Boundary (01/10/2026)


def tabla(cab, filas):
    s = "| " + " | ".join(cab) + " |\n|" + "---|" * len(cab) + "\n"
    return s + "".join("| " + " | ".join(str(c) for c in f) + " |\n" for f in filas)


def circuito():
    f = Fluid("Ammonia")
    return f, Circuit(
        f, D.compressor(fluid=f),
        AirCoil(f, D.air_coil_geometry(), n_segments=60),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("condensador_climatizacion"), n_cells=12),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("desrecalentador_acs"), n_cells=12))


# %% [markdown]
# ## Punto de diseno de M-1, con traza del lazo externo

# %%
def sec_m1():
    f, c = circuito()
    bc = Boundary(air=AirState(T=35 + K, V_frontal=3.30), m_dot_air=M_AIRE,
                  clima=WaterStream(T_in=12 + K, m_dot=D.caudal_climatizacion()),
                  acs=WaterStream(T_in=35 + K), T_amb=308.15)
    sp = Setpoints(superheat=5.0, subcooling=2.0, T_acs=67 + K)
    out = []

    x0 = c.initial_guess("M-1", bc, sp)
    unknowns, residuals = c.active_system("M-1", sp)
    out.append("### Estimación inicial (parámetros agrupados, 10 K en aire y 6 K en agua)\n\n" + tabla(
        ["Magnitud", "Valor"],
        [["T_evap (12 − 6)", f"{f.Tsat(x0['P0']) - K:.2f} °C"],
         ["T_cond (35 + 10)", f"{f.Tsat(x0['Pk']) - K:.2f} °C"],
         ["A_ef", f"{x0['A_ef'] * 1e6:.4f} mm²"],
         ["Caudal de ACS", f"{x0['m_acs'] * 3600:.1f} kg/h"],
         ["Incógnitas efectivas", ", ".join(unknowns)],
         ["Residuos efectivos", ", ".join(residuals)]]))

    hist = []
    evaluar = c.evaluate

    def con_traza(x, *a, **kw):
        st = evaluar(x, *a, **kw)
        v, r = st["vals"], st["residuals"]
        hist.append((f.Tsat(v["P0"]) - K, f.Tsat(v["Pk"]) - K, v["m_acs"] * 3600,
                     v["A_ef"] * 1e6, r["R2"], r["R4"], r["R5"]))
        return st

    c.evaluate = con_traza
    t = time.time()
    s = c.solve("M-1", bc, sp)
    dt = time.time() - t

    filas, mejor = [], float("inf")
    for i, h in enumerate(hist):
        m = max(abs(v) for v in h[4:])
        if i < 3 or m < 0.3 * mejor or i == len(hist) - 1:
            mejor = min(mejor, m)
            filas.append([i, f"{h[0]:.3f}", f"{h[1]:.3f}", f"{h[2]:.2f}", f"{h[3]:.4f}",
                          f"{h[4]:.2e}", f"{h[5]:.2e}", f"{h[6]:.2e}", f"{m:.1e}"])
    out.append(f"### Historia del lazo externo ({len(hist)} evaluaciones, {dt:.0f} s; "
               f"`{s.message}`)\n\n" + tabla(
                   ["Eval.", "T_evap °C", "T_cond °C", "ṁ_ACS kg/h", "A_ef mm²",
                    "R2", "R4", "R5", "máx |R|"], filas))

    comp = s.components["compresor"]
    out.append("### Punto resuelto\n\n" + tabla(["Magnitud", "Valor"], [
        ["T_evap / T_cond", f"{s.T_evap - K:.2f} / {s.T_cond - K:.2f} °C"],
        ["Caudal de refrigerante", f"{s.m_dot * 3600:.2f} kg/h"],
        ["Caudal de ACS", f"{s.unknowns['m_acs'] * 3600:.2f} kg/h"],
        ["A_ef (forma cerrada)", f"{s.unknowns['A_ef'] * 1e6:.4f} mm²"],
        ["Recalentamiento / subenfriamiento", f"{s.superheat:.3f} / {s.subcooling:.3f} K"],
        ["Q evaporador (placas 27-30H)", f"{s.Q_evap:.0f} W"],
        ["Q desrecalentador (ACS)", f"{s.Q_acs:.0f} W"],
        ["Q batería", f"{-s.components['bateria'].Q_dot:.0f} W"],
        ["T descarga", f"{s.T_dis - K:.2f} °C"],
        ["W eje / W eléctrico compresor", f"{comp.W_shaft:.0f} / {comp.W_el:.0f} W"],
        ["η_v / η_is", f"{comp.eta_v:.4f} / {comp.eta_is:.4f}"],
        ["T pared ficticia", f"{comp.T_wall - K:.1f} °C"],
        ["Q al ambiente (compresor)", f"{comp.Q_amb:.1f} W"],
        ["Residuos R2 / R4 / R5", " / ".join(f"{s.residuals[k]:.1e}" for k in ("R2", "R4", "R5"))],
        ["Convergido / válido", f"{s.converged} / {s.valid}"]]))

    filas = []
    for k, nombre in (("desrecalentador", "Desrecalentador 16-10H"),
                      ("bateria", "Batería CBN-21"),
                      ("placas_clima", "Evaporador 27-30H")):
        r = s.components[k]
        n = getattr(r, "n_volumenes", 0) or getattr(r, "n_segmentos", 0)
        T_sec = (f"{r.T_sec_out - K:.2f} °C" if hasattr(r, "T_sec_out")
                 else f"{r.T_air_out - K:.2f} °C (aire)")
        filas.append([nombre, f"{r.Q_dot:.0f} W", n, r.n_recortes, T_sec,
                      f"{getattr(r, 'dP_ref', float('nan')):.0f} Pa",
                      f"{r.energy_balance_error:.1e}" if hasattr(r, "energy_balance_error")
                      else f"{s.checks['balance_componentes']['bateria']:.1e}"])
    out.append("### Componentes\n\n" + tabla(
        ["Componente", "Q", "Volúmenes resueltos", "Recortes", "Salida secundario",
         "Δp refrigerante", "Balance"], filas))

    b = s.components["bateria"]
    ev = s.components["placas_clima"]
    de = s.components["desrecalentador"]
    out.append("### Diagnóstico por componente\n\n" + tabla(["Magnitud", "Valor"], [
        ["Batería: fracción de volumen vapor / bifásico / líquido",
         " / ".join(f"{b.volume_fraction[k]:.3f}" for k in ("vapor", "condensando", "liquido"))],
        ["Batería: régimen de condensación", str(b.condensation_regime.get("volumen"))],
        ["Batería: h_aire, η_aleta, η_superficie, U medio",
         f"{b.h_air:.1f} W/(m²K), {b.eta_fin:.3f}, {b.eta_surface:.3f}, {b.U_mean:.1f} W/(m²K)"],
        ["Desrecalentador: pared húmeda", f"{de.wet_wall_fraction:.3f}"],
        ["Desrecalentador: α refrigerante (vapor)", f"{de.alpha_profile.min():.0f}–{de.alpha_profile.max():.0f} W/(m²K)"],
        ["Evaporador: título de entrada", f"{ev.x_profile[0]:.4f}"],
        ["Evaporador: α refrigerante (bifásico → vapor)",
         f"{ev.alpha_profile[0]:.0f} → {ev.alpha_profile[-3]:.0f} → {ev.alpha_profile[-1]:.0f} W/(m²K)"]]))

    ch = s.checks
    out.append("### Verificaciones independientes\n\n" + tabla(["Verificación", "Valor"], [
        ["Masa", f"{ch['masa']:.1e}"], ["Energía del sistema", f"{ch['energia']:.1e}"],
        ["R3 pared del compresor", f"{ch['R3_pared_compresor_W']:.1e} W"],
        ["Entropía generada (mín.)", f"{ch['entropia_minima']:.3f} W/K"],
        ["Entropía por componente", ", ".join(f"{k} {v:.3f}" for k, v in ch["entropia"].items())],
        ["Área efectiva de válvula (resultado)", f"{ch['area_efectiva_valvula_m2'] * 1e6:.4f} mm²"],
        ["Salto de saturación por Δp (M8)", ", ".join(f"{k} {v:.3f} K" for k, v in ch["M8_salto_saturacion_K"].items())],
        ["ok", str(ch["ok"])]]))

    e = I.energy(s, MODES["M-1"])
    x = I.exergy(s, MODES["M-1"], e)
    ca = s.charge
    out.append("### Salidas\n\n" + tabla(["Magnitud", "Valor"], [
        ["W eléctrico total (compresor + ventilador)", f"{e.W_el:.0f} W"],
        ["EER / COP global", f"{e.EER:.3f} / {e.COP_global:.3f}"],
        ["η_II / cierre exergético", f"{x.eta_II:.3f} / {x.cierre:.3f}"],
        ["H6: reparto entre componentes del ciclo (sin ventilador)",
         ", ".join(f"{k} {100 * v:.1f} %" for k, v in
                   sorted(x.y_D_ciclo.items(), key=lambda kv: -kv[1]))],
        ["Cuota del ventilador sobre el total destruido", f"{100 * x.y_D.get('ventilador', 0):.1f} %"],
        ["Carga: homogéneo / Zivi / L-M / Rouhani-Axelsson",
         " / ".join(f"{ca[k] * 1e3:.0f} g" for k in
                    ("homogeneous", "zivi", "lockhart_martinelli", "rouhani_axelsson"))],
        # Presupuesto UNICO de RS-5 (decision 1 del 01/10/2026, §8.5.2): 50 g/kW sobre
        # el equilibrio de refrigeracion del §9.7.8, no sobre la capacidad del modo.
        ["Presupuesto RS-5 (único) / peor caso de los componentes",
         f"{PRES_RS5['m_max_kg'] * 1e3:.0f} g / {ca['_max'] / PRES_RS5['m_max_kg'] * 100:.1f} %"],
        ["Extrapolado", str(s.extrapolated)]]))
    out.append("### Marca de extrapolación\n\n" + "".join(f"- {e}\n" for e in s.excursions))
    return "\n\n".join(out), s, hist


# %% [markdown]
# ## Contraste con la ficha de Frimetal como evaporador (26/03/2026)
#
# Evaporador «a bomba», relacion de recirculacion 3: entra liquido saturado a
# 4 C, 26 kg/h entre dos circuitos, aire a 7 C y 75 % a 7600 m3/h. La ficha
# declara 2999 W, U = 32 W/(m2 K), superficie seca. No se emplea para anclar.

# %%
def sec_ficha_evaporador():
    f = Fluid("Ammonia")
    P = f.Psat(4.0 + K)
    sat = f.sat_props(P)
    air = AirState.at(7.0 + K, 3.30, RH=0.75)
    filas = []
    for nombre in ("gungor_winterton", "gungor_winterton_horizontal", "cooper_solo"):
        for n in (120, 400):
            coil = AirCoil(f, D.air_coil_geometry(), n_segments=n,
                           corr={"tube_boiling": nombre})
            r = coil.solve(P, sat["h_l"], 26 / 3600, air, 9549 / 3600, role="evaporator")
            x_out = (r.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
            filas.append([nombre, n, f"{r.Q_dot:.0f} W", f"{(r.Q_dot / 2999 - 1) * 100:+.1f} %",
                          f"{r.U_mean:.1f}", f"{r.T_air_out - K:.2f} °C", f"{x_out:.3f}",
                          f"{r.wet_fraction:.2f}"])
    return ("### Batería frente a la ficha de evaporador (ficha: 2999 W, U = 32, "
            "aire a 5.9 °C, x_salida = 1/3, seca)\n\n" + tabla(
                ["Ebullición en tubo", "Segmentos", "Q", "Desv.", "U W/(m²K)",
                 "T aire salida", "x salida", "Fracción húmeda"], filas))


# %% [markdown]
# ## Figuras: perfiles de temperatura y convergencia
#
# Colores: los de la figura 9.3 mas un verde. Verde y naranja quedan en 7.4 de
# separacion para protanopia (validador de la guia de visualizacion), de modo
# que cada serie lleva ademas su tipo de linea y su etiqueta directa.

# %%
AZUL, NARANJA, VERDE = "#2a78d6", "#eb6834", "#2e9a6b"
TINTA, TINTA_2, GRIS = "#0b0b0b", "#52514e", "#b8b7b2"
mpl.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 300, "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "legend.fontsize": 7, "axes.edgecolor": GRIS,
    "axes.labelcolor": TINTA, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "lines.linewidth": 1.5})


def _mitad(A):
    return 0.5 * (A[1:] + A[:-1])


def figuras(s, hist):
    salida = Path("docs/figuras")
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.6), sharey=False)
    paneles = (("desrecalentador", "(a) Desrecalentador 16-10H", "T_sec", "Agua de ACS", "T_pared", "Pared"),
               ("bateria", "(b) Batería CBN-21", "T_aire_sal", "Aire (salida)", "T_sup", "Superficie"),
               ("placas_clima", "(c) Evaporador 27-30H", "T_sec", "Agua de climatización", "T_pared", "Pared"))
    for ax, (k, titulo, sec, nom_sec, par, nom_par) in zip(axes, paneles):
        p = s.components[k].profile
        A = p["A"] / p["A"][-1]
        ax.plot(A, p["T_ref"] - K, color=AZUL, ls="-", label="Refrigerante")
        x_sec = A if len(p[sec]) == len(A) else _mitad(A)
        ax.plot(x_sec, p[sec] - K, color=NARANJA, ls="--", label=nom_sec)
        ax.plot(_mitad(A), p[par] - K, color=VERDE, ls=":", label=nom_par)
        ax.set_title(titulo, loc="left", color=TINTA)
        ax.set_xlabel("Área acumulada / área total")
        ax.set_xlim(0, 1)
    axes[0].set_ylabel("Temperatura [°C]")
    for ax, loc in zip(axes, ("upper right", "upper right", "center left")):
        ax.legend(frameon=False, loc=loc, handlelength=2.2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_ejemplo_M1_perfiles.{ext}", bbox_inches="tight")
    plt.close(fig)

    r = np.array([max(abs(v) for v in h[4:]) for h in hist])
    # Una sola curva: el residuo del mejor punto alcanzado hasta cada evaluacion,
    # que es el iterado aceptado por el corrector. Las evaluaciones de
    # diferencias finitas perturban el punto a proposito y no son iterados, de
    # modo que no se dibujan (07/10/2026, a peticion del autor). Los residuos se
    # nombran como en el capitulo (R1, R2, R3), no como en el codigo.
    n = np.arange(len(r))
    mejor = np.minimum.accumulate(r)
    fig, ax = plt.subplots(figsize=(3.6, 2.5))
    ax.step(n, mejor, where="post", color=AZUL, lw=1.5)
    ax.set_yscale("log")
    ax.set_ylim(1e-12, 3)
    ax.set_yticks([1e0, 1e-2, 1e-4, 1e-6, 1e-8, 1e-10, 1e-12])
    ax.yaxis.set_minor_locator(mpl.ticker.NullLocator())
    ax.axhline(1e-6, color=TINTA_2, lw=0.8, ls="--")
    ax.text(n[-1], 1.6e-6, "tolerancia 10⁻⁶", ha="right", va="bottom", color=TINTA_2, fontsize=7)
    i_tol = int(np.argmax(mejor <= 1e-6))
    ax.axvline(i_tol, color=TINTA_2, lw=0.6, ls=":")
    ax.annotate(f"tolerancia alcanzada\n(evaluación {i_tol})", (i_tol, 1e-9), xytext=(-4, 0),
                textcoords="offset points", fontsize=6.5, color=TINTA_2, va="center", ha="right")
    ax.set_xlim(0, n[-1])
    ax.set_xlabel("Evaluación del circuito")
    ax.set_ylabel(r"Residuo máximo, máx $|R_i|$")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_ejemplo_M1_convergencia.{ext}", bbox_inches="tight")
    plt.close(fig)


# %%
if __name__ == "__main__":
    # La revision se lee ANTES de escribir nada: leida al final, las figuras
    # que el propio cuaderno acaba de escribir dejaban el arbol sucio.
    rev = git_revision()
    texto_m1, s, hist = sec_m1()
    figuras(s, hist)
    cuerpo = [texto_m1, sec_ficha_evaporador()]
    cab = (f"# Ejemplo resuelto de M-1 y ficha de evaporador\n\n"
           f"Generado por `notebooks/04_ejemplo_resuelto_M1.py` el "
           f"{time.strftime('%d/%m/%Y')}, revisión `{rev}`, "
           f"CoolProp {CoolProp.__version__}, HEOS. No editar a mano.\n\n")
    Path("docs/cifras_ejemplo_M1.md").write_text(cab + "\n\n".join(cuerpo) + "\n")
    print(cab + "\n\n".join(cuerpo))
