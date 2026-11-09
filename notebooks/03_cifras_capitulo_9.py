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
# # 03 - Cifras del capitulo 9
#
# Notebook de EXPERIMENTACION. El modelo vive en el paquete `amoniatermia`,
# no aqui: esto carga, ejecuta y escribe.
#
# Calcula TODAS las tablas y cifras del capitulo 9 que produce el modelo y las
# escribe en `docs/cifras_capitulo_9.md`, con la procedencia del §6.12: la
# revision del codigo, la version de CoolProp y la fecha. Es la fuente unica de
# numeros para redactar el capitulo; si el modelo cambia, se vuelve a ejecutar.
#
# Uso:
#
#     uv run python notebooks/03_cifras_capitulo_9.py            # todo (~30 min)
#     uv run python notebooks/03_cifras_capitulo_9.py compresor m2
#
# Secciones: compresor, semiempirico, m2, evaporador, carga, desrecalentador, modos,
# exergia, tabular, continuacion, malla_placas, residuo_entalpico,
# tabular_modos.

# %%
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

import CoolProp

from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid, MODES,
                          PlateHeatExchanger,
                          Setpoints, WaterStream)
from amoniatermia import campaign as C
from amoniatermia.circuit import caudal_masico_aire
from amoniatermia import data as D
from amoniatermia import indicators as I
from amoniatermia.correlations.voidfraction import charge_range
from amoniatermia.props import git_revision

# %% [markdown]
# ## Condiciones comunes
#
# Las de las pruebas: 60 segmentos y 12 volumenes en los circuitos completos;
# aire de verano a 35 C y de invierno a 7 C bs / 6 C bh; climatizacion a 12 C y
# a 40 C en calor, con el caudal unico de `circuitos_agua.yaml` (0.45 kg/s); recalentamiento 5 K y
# subenfriamiento 2 K; impulsion de ACS a 67 C.

# %%
M_AIRE = None   # 7 600 m3/h: el caudal masico lo deduce Boundary (01/10/2026)
VERANO = AirState(T=35 + 273.15, V_frontal=3.30)
INVIERNO = AirState.at(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)
AIRE_M5 = AirState.at(T=32 + 273.15, V_frontal=3.30, RH=0.45)
CLIMA_FRIO = WaterStream(T_in=12 + 273.15, m_dot=D.caudal_climatizacion())
CLIMA_CALOR = WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion())
SP = Setpoints(superheat=5.0, subcooling=2.0)
SP_ACS = Setpoints(superheat=5.0, subcooling=2.0, T_acs=67 + 273.15)


def circuito_completo():
    f = Fluid("Ammonia")
    return Circuit(
        f, D.compressor(fluid=f),
        AirCoil(f, D.air_coil_geometry(), n_segments=60),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("condensador_climatizacion"),
                           n_cells=12),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("desrecalentador_acs"), n_cells=12))


def circuito_bateria(n=400):
    f = Fluid("Ammonia")
    return Circuit(f, D.compressor(fluid=f),
                   AirCoil(f, D.air_coil_geometry(), n_segments=n), None, None)


def tabla(cabecera, filas):
    L = ["| " + " | ".join(cabecera) + " |",
         "|" + "---|" * len(cabecera)]
    L += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(L)


def salida_desrecalentador(c, s):
    f = c.fluid
    d = s.components["desrecalentador"]
    # Presion uniforme en el intercambiador (M8, decision del 29/09/2026): la
    # saturacion de referencia es la de descarga, como en `envelope`.
    P = s.unknowns["Pk"]
    T_sat, sat = f.Tsat(P), f.sat_props(P)
    f.update_PH(P, d.h_ref_out)
    x = (d.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
    return f.T - T_sat, x, d.wet_wall_fraction


# %% [markdown]
# ## Secciones

# %%
def sec_compresor():
    """Modelo del compresor desde el 15/10/2026: polinomios de UNE-EN 12900 ajustados a los
    puntos de BOCK VAP en toda la envolvente (`docs/DECISIONES_2026_10_15.md`)."""
    from amoniatermia.validation import compressor_en12900 as V
    f = Fluid("Ammonia")
    comp = D.compressor(fluid=f)
    v = V.validacion()
    filas_aj = [[f"{rpm} rpm", d["n"], f"±{d['caudal_max']*100:.2f} %",
                 f"±{d['potencia_max']*100:.2f} %", f"±{d['descarga_max_K']:.2f} K"]
                for rpm, d in v["ajuste"].items()]
    nombres = ["c0 (1)", "c1 (t0)", "c2 (tc)", "c3 (t0²)", "c4 (t0·tc)", "c5 (tc²)",
               "c6 (t0³)", "c7 (tc·t0²)", "c8 (t0·tc²)", "c9 (tc³)"]
    coef = []
    for p in comp.pol:
        filas = [[n, f"{1e3 * a:.6g}", f"{b:.6g}", f"{c:.6g}"]
                 for n, a, b, c in zip(nombres, p.m_dot, p.W_eje, p.T_dis_C)]
        coef.append(f"#### {p.rpm:.0f} rpm ({p.n_puntos} puntos)\n\n" + tabla(
            ["Término", "Caudal [g/s]", "Potencia al eje [W]", "Descarga [°C]"], filas))
    # Rendimientos y prestaciones en el punto de referencia del §9.7.8 (2 / 46.8 °C).
    P0, Pk = f.Psat(275.15), f.Psat(46.8 + 273.15)
    filas_r = []
    for rpm in (960.0, 1450.0):
        comp.fija_velocidad(rpm)
        ev, ei, ed = comp.rendimientos(P0, Pk)
        for sh in (1.0, 5.0):
            r = comp.solve(P0, 275.15 + sh, Pk)
            filas_r.append([f"{rpm:.0f} rpm", f"{sh:g} K", f"{ev:.4f}", f"{ei:.4f}", f"{ed:.4f}",
                            f"{r.m_dot * 3600:.2f} kg/h", f"{r.W_shaft:.0f} W",
                            f"{r.T_dis - 273.15:.2f} °C", f"{r.Q_amb:.0f} W"])
    comp.fija_velocidad(1450.0)
    semi = D.compressor(fluid=f, modelo="semiempirico")
    rs, rp = semi.solve(P0, 276.15, Pk), comp.solve(P0, 276.15, Pk)
    comparado = tabla(["Modelo", "Caudal", "Potencia al eje", "Descarga"], [
        ["Polinomios (adoptado)", f"{rp.m_dot*3600:.2f} kg/h", f"{rp.W_shaft:.0f} W",
         f"{rp.T_dis - 273.15:.2f} °C"],
        ["Semiempírico (24/09/2026)", f"{rs.m_dot*3600:.2f} kg/h", f"{rs.W_shaft:.0f} W",
         f"{rs.T_dis - 273.15:.2f} °C"]])
    return "\n\n".join([
        "### Calidad del ajuste de los polinomios a cada velocidad (desviación máxima sobre sus "
        "propios puntos, 5 K de recalentamiento)", tabla(
            ["Velocidad", "Puntos", "Caudal", "Potencia al eje", "Descarga"], filas_aj),
        "### Rendimientos que se conservan al cambiar el recalentamiento (2 / 46.8 °C)",
        tabla(["Velocidad", "Recalentamiento", "η_v", "η_is (eje)", "η_dis", "Caudal",
               "Potencia al eje", "Descarga", "Calor al ambiente"], filas_r),
        "### Punto de referencia del §9.7.8 (2 / 46.8 °C, 1 K, 1450 rpm), con los dos modelos",
        comparado,
        "### Coeficientes de los polinomios (t0 y tc en °C; UNE-EN 12900)"] + coef)


def sec_m2():
    c = circuito_bateria()
    bc = Boundary(air=VERANO, m_dot_air=M_AIRE, T_amb=308.15)
    filas, x0 = [], None
    s0 = None
    for sc in (0.0, 7.3, 9.5, 10.6):
        s = c.solve("M-2", bc, Setpoints(superheat=1.0, subcooling=sc,
                                         T_evap=2 + 273.15), x0=x0)
        x0 = dict(s.unknowns) if s.converged else None
        s0 = s0 or s
        coil = s.components["bateria"]
        filas.append([f"{sc:.1f} K", f"{coil.volume_fraction['liquido']*100:.1f} %",
                      f"{s.charge['_min']*1e3:.0f} – {s.charge['_max']*1e3:.0f} g",
                      f"{s.Q_evap/1e3:.2f} kW",
                      f"{s.charge['_RS5_peor_caso']*100:.0f} %"])
    s = s0
    t19 = tabla(["Magnitud", "Modelo"], [
        ["Temperatura de condensación", f"{s.T_cond - 273.15:.2f} °C"],
        ["Calor evacuado", f"{-s.Q_high/1e3:.2f} kW"],
        ["Potencia frigorífica", f"{s.Q_evap/1e3:.2f} kW"],
        ["Potencia al eje", f"{s.W_shaft/1e3:.3f} kW"],
        ["Caudal másico", f"{s.m_dot*3600:.2f} kg/h"],
        ["Temperatura de descarga", f"{s.T_dis - 273.15:.2f} °C"],
        ["Presupuesto de RS-5", f"{s.charge['_RS5_limite_kg']*1e3:.0f} g"],
        ["Residuo / válido", f"{s.max_residual:.1e} / {s.valid}"]])
    return "\n\n".join([
        "### Tabla 9.19 — equilibrio de M-2 (evaporación a 2 °C, aire a 35 °C)", t19,
        "### Tabla 9.22 — carga de la batería frente al subenfriamiento", tabla(
            ["Subenfriamiento", "Volumen anegado", "Carga (banda)", "Capacidad",
             "% del presupuesto de RS-5 de la fila"], filas)])


def sec_evaporador():
    f = Fluid("Ammonia")
    comp = D.compressor(fluid=f)
    coil_g = D.air_coil_geometry()
    Pk = f.Psat(50 + 273.15)
    f.update_PQ(Pk, 0.0)
    h_in = f.h
    filas = []
    for nombre, Tbs, Tbh, Tev_imp in (("7 °C bs / 6 °C bh", 7, 6, 1.6),
                                      ("2 °C bs / 1 °C bh", 2, 1, -2.9),
                                      ("−7 °C bs / −8 °C bh", -7, -8, -11.1)):
        air = AirState.at(T=Tbs + 273.15, V_frontal=3.30, T_wb=Tbh + 273.15)
        hx = AirCoil(f, coil_g, n_segments=120,
                     corr={"tube_boiling": "gungor_winterton"})

        def capacidad(T_ev):
            P0 = f.Psat(T_ev + 273.15)
            r = comp.solve(P0, T_ev + 274.15, Pk, T_amb=298.15)
            f.update_PT(P0, T_ev + 274.15)
            return r, r.m_dot * (f.h - h_in)

        def residuo(T_ev):
            r, Q = capacidad(T_ev)
            return hx.solve(f.Psat(T_ev + 273.15), h_in, r.m_dot, air, caudal_masico_aire(air),
                            role="evaporator").Q_dot - Q

        ri, Qi = capacidad(Tev_imp)
        T_ev = brentq(residuo, Tbs - 22.0, Tbs - 0.5, xtol=1e-3)
        rr, Qr = capacidad(T_ev)
        U = hx.solve(f.Psat(T_ev + 273.15), h_in, rr.m_dot, air, caudal_masico_aire(air),
                     role="evaporator").U_mean
        cop = lambda r: r.m_dot * (r.h_dis - h_in) / r.W_shaft
        filas.append([nombre, f"{Tev_imp:.1f} / {T_ev:.2f} °C",
                      f"{Qi/1e3:.2f} / {Qr/1e3:.2f} kW",
                      f"{cop(ri):.2f} / {cop(rr):.2f}", f"{U:.1f}",
                      f"{(1 - Qr / Qi)*100:.1f} %"])
    return "### Tabla 9.20 — operación como evaporador (condensación a 50 °C)\n\n" + tabla(
        ["Aire exterior", "T_evap impuesta / resuelta", "Q impuesta / resuelta",
         "COP impuesto / resuelto", "U [W/(m²·K)]", "Diferencia"], filas)


def sec_carga():
    f = Fluid("Ammonia")
    sat = f.sat_props(f.Psat(45 + 273.15))
    xs = np.linspace(1e-4, 1 - 1e-4, 2001)
    filas = []
    for nombre, clave in (("Homogéneo", "homogeneous"), ("Zivi", "zivi"),
                          ("Lockhart-Martinelli", "lockhart_martinelli"),
                          ("Rouhani-Axelsson", "rouhani_axelsson")):
        v = [charge_range(x, sat, 48.0, 0.0123, names=(clave,))[clave] for x in xs]
        a = float(np.mean([w["alpha"] for w in v]))
        rho = float(np.mean([w["rho_mean"] for w in v]))
        filas.append([nombre, f"{a:.3f}", f"{rho:.1f} kg/m³", f"{rho*3.8:.0f} g"])
    return ("### Tabla 9.21 — carga de la batería como condensador (45 °C, 3.8 L, "
            "promedio uniforme en título, G = 48 kg/(m²·s))\n\n" +
            tabla(["Correlación", "Fracción de huecos", "Densidad media", "Masa"], filas))


def sec_desrecalentador():
    out = []
    for modo, aire, clima, T_amb, x0_pin in (
            ("M-1", VERANO, CLIMA_FRIO, 308.15, None),
            ("M-3", INVIERNO, CLIMA_CALOR, 280.15, None)):
        c = circuito_completo()
        bc = lambda T: Boundary(air=aire, m_dot_air=M_AIRE, clima=clima,
                                acs=WaterStream(T_in=T + 273.15), T_amb=T_amb)
        x0 = (c.initial_guess(modo, bc(35), SP_ACS, pinch_air=x0_pin[0],
                              pinch_water=x0_pin[1]) if x0_pin else None)
        s35 = c.solve(modo, bc(35), SP_ACS, x0=x0)
        if modo == "M-1":
            s_m1 = s35
        filas = {}
        for rama in ([35, 30, 25], [45, 55, 60]):
            x = dict(s35.unknowns)
            for T in rama:
                s = s35 if T == 35 else c.solve(modo, bc(T), SP_ACS, x0=x)
                if s.converged:
                    x = dict(s.unknowns)
                margen, xs, humeda = salida_desrecalentador(c, s)
                estado = (f"+{margen:.2f} K" if xs >= 1.0
                          else f"condensa, x = {xs:.3f}")
                filas[T] = [f"{T} °C", f"{s.unknowns['m_acs']*3600:.1f} kg/h",
                            f"{s.Q_acs:.0f} W", estado, f"{humeda*100:.0f} %",
                            f"{s.T_cond - 273.15:.2f} °C", str(s.valid)]
        out.append(f"### Tabla 9.16 — barrido del retorno, {modo}, impulsión 67 °C\n\n" +
                   tabla(["Retorno", "Caudal de ACS", "Q recuperado",
                          "Margen / título de salida", "Pared húmeda", "T_cond",
                          "Válido"], [filas[T] for T in sorted(filas)]))
    # Tabla 9.15, en el punto de diseno (M-1 resuelto)
    f, agua = Fluid("Ammonia"), Fluid("Water")
    # Estado del punto de diseno de M-1 resuelto, no valores escritos a mano.
    P = s_m1.unknowns["Pk"]
    sat = f.sat_props(P)
    m_r = s_m1.m_dot
    h_dis = s_m1.components["compresor"].h_dis
    filas = []
    for nombre, unidad, ov in (("AlfaNova 16-10H", "desrecalentador_acs", {}),
                               ("AlfaNova 27, 10 placas", "condensador_climatizacion",
                                {"n_plates": 10}),
                               ("AlfaNova 27-30H", "condensador_climatizacion", {})):
        g = D.plate_geometry(unidad, **ov)

        def res(m):
            hx = PlateHeatExchanger(f, agua, g, n_cells=60, role="condenser")
            return hx.solve(P, h_dis, m_dot=m_r, T_sec_in=35 + 273.15,
                            m_sec=m / 3600)
        m = brentq(lambda m: res(m).T_sec_out - 273.15 - 67.0, 20, 900, xtol=0.05)
        r = res(m)
        xs = (r.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
        f.update_PH(P, r.h_ref_out)
        estado = (f"vapor, +{f.T - sat['Tsat']:.1f} K" if xs > 1
                  else f"bifásico, x = {xs:.3f}")
        filas.append([nombre, f"{g.A_total:.3f} m²", f"{m:.1f} kg/h",
                      f"{-r.Q_dot:.0f} W", estado])
    out.append("### Tabla 9.15 — geometrías candidatas en el punto de diseño\n\n" +
               tabla(["Geometría", "Área", "Caudal de ACS", "Q", "Salida"], filas))
    return "\n\n".join(out)


def casos_diseno():
    """Los cinco puntos de diseno, desde la estimacion por defecto."""
    return [
        ("M-1, ACS 35 → 67 °C", "M-1", Boundary(air=VERANO, m_dot_air=M_AIRE, clima=CLIMA_FRIO,
                                                acs=WaterStream(T_in=35 + 273.15), T_amb=308.15), SP_ACS),
        ("M-2", "M-2", Boundary(air=VERANO, m_dot_air=M_AIRE, clima=CLIMA_FRIO, T_amb=308.15), SP),
        ("M-3, ACS 35 → 67 °C", "M-3", Boundary(air=INVIERNO, m_dot_air=M_AIRE, clima=CLIMA_CALOR,
                                                acs=WaterStream(T_in=35 + 273.15), T_amb=280.15), SP_ACS),
        ("M-4", "M-4", Boundary(air=INVIERNO, m_dot_air=M_AIRE,
                                clima=CLIMA_CALOR, T_amb=280.15), SP),
        ("M-5, ACS 15 → 52 °C", "M-5", Boundary(air=AIRE_M5, m_dot_air=M_AIRE,
                                                acs=WaterStream(T_in=15 + 273.15), T_amb=305.15),
         Setpoints(superheat=5.0, subcooling=2.0, T_acs=52 + 273.15)),
    ]


def resolver_contando(c, modo, bc, sp, x0=None):
    """Resuelve y cuenta las evaluaciones del circuito (pasadas completas)."""
    n = [0]
    evaluar = c.evaluate

    def contada(*a, **kw):
        n[0] += 1
        return evaluar(*a, **kw)

    c.evaluate = contada
    t = time.time()
    try:
        s = c.solve(modo, bc, sp, x0=x0)
    finally:
        c.evaluate = evaluar
    return s, n[0], time.time() - t


def sec_modos():
    # Sin arranques forzados: cada modo sale de la estimacion por defecto, que
    # es lo que dice la leyenda de la tabla. Si alguno necesitase un arranque
    # alternativo, el mensaje del resultado lo registra y se publica.
    filas = []
    for nombre, modo, bc, sp in casos_diseno():
        c = circuito_completo()
        s, nfev, dt = resolver_contando(c, modo, bc, sp)
        bal = max(s.checks["balance_componentes"].values())
        placas = {k: r for k, r in s.components.items() if hasattr(r, "dT_sat_equivalente")}
        dp = sum(r.dP_ref for r in placas.values())
        dT = sum(r.dT_sat_equivalente for r in placas.values())
        alt = "sí" if "arranque alternativo" in s.message else "no"
        filas.append([nombre, f"{s.max_residual:.1e}", f"{bal:.1e}", str(s.converged),
                      str(s.valid), nfev, alt, f"{dt:.0f} s",
                      f"{s.unknowns['Pk'] / s.unknowns['P0']:.2f}",
                      f"{dp / 1e3:.1f} kPa / {dT:.2f} K"])
    return ("### Tabla 9.6 — residuo y validez por modo (60 segmentos, 12 volúmenes, "
            "desde la estimación por defecto)\n\n" + tabla(
                ["Modo", "Residuo", "Peor balance de componente", "Converge", "Válido",
                 "Evaluaciones", "Arranque alternativo", "Tiempo desde la estimación",
                 "p_k/p_0", "Δp placas / salto de saturación (M8)"], filas))


def sec_continuacion():
    """Coste de un punto arrancando de uno convergido: el paso de campana."""
    vecino = {"M-1": AirState(T=36 + 273.15, V_frontal=3.30),
              "M-2": AirState(T=36 + 273.15, V_frontal=3.30),
              "M-3": AirState.at(T=8 + 273.15, V_frontal=3.30, T_wb=7 + 273.15),
              "M-4": AirState.at(T=8 + 273.15, V_frontal=3.30, T_wb=7 + 273.15),
              "M-5": AirState.at(T=33 + 273.15, V_frontal=3.30, RH=0.45)}
    filas = []
    for nombre, modo, bc, sp in casos_diseno():
        c = circuito_completo()
        s0 = c.solve(modo, bc, sp)
        bc1 = Boundary(air=vecino[modo], m_dot_air=M_AIRE, clima=bc.clima,
                       acs=bc.acs, T_amb=bc.T_amb)
        s1, nfev, dt = resolver_contando(c, modo, bc1, sp, x0=dict(s0.unknowns))
        filas.append([nombre, nfev, f"{dt:.1f} s", f"{s1.max_residual:.1e}", str(s1.converged)])
    return ("### §9.4.4 — coste arrancando del punto convergido vecino (aire exterior +1 K)\n\n" +
            tabla(["Modo", "Evaluaciones", "Tiempo", "Residuo", "Converge"], filas))


def _condensador_sobrecalentado(n, **kw):
    """27-30H condensando a 50 °C con entrada sobrecalentada a 70 °C: el caso
    en que hay dos fronteras de fase dentro del componente."""
    f = Fluid("Ammonia")
    P = f.Psat(50 + 273.15)
    hx = PlateHeatExchanger(f, Fluid("Water"), D.plate_geometry("condensador_climatizacion"),
                            n_cells=n, role="condenser", **kw)
    f.update_PT(P, 70 + 273.15)
    return -hx.solve(P, f.h, 40.3 / 3600, 40 + 273.15, 1830.0 / 3600).Q_dot


def sec_malla_placas():
    Ns = (10, 20, 40, 80, 160, 320)
    Q = {tr: {n: _condensador_sobrecalentado(n, track_phase=tr) for n in Ns}
         for tr in (False, True)}
    cab = ["Seguimiento de la frontera"] + [f"{a} → {b}" for a, b in zip(Ns[1:], Ns[2:])]
    filas = [["con" if tr else "sin"] +
             [f"{abs(Q[tr][b] - Q[tr][a]) / Q[tr][b]:.1e}" for a, b in zip(Ns[1:], Ns[2:])]
             for tr in (False, True)]
    out = ["### Tabla 9.12 — variación relativa de la potencia al refinar la malla "
           "(condensador 27-30H, entrada a 70 °C, condensación a 50 °C)\n\n" + tabla(cab, filas)]
    out.append(f"Con seguimiento, 10 volúmenes frente a 320: "
               f"{abs(Q[True][10] - Q[True][320]) / Q[True][320] * 100:.2f} %.")
    filas = []
    for n in (20, 40, 80, 160):
        lm = _condensador_sobrecalentado(n)
        ar = _condensador_sobrecalentado(n, dT_mean="arithmetic")
        filas.append([n, f"{abs(ar - lm) / lm:.1e}"])
    out.append("### §9.5.4 — media logarítmica frente a aritmética (mismo caso)\n\n" +
               tabla(["Volúmenes", "Diferencia relativa en la potencia"], filas))
    return "\n\n".join(out)


def sec_residuo_entalpico():
    """Por que R4 se escribe sobre el subenfriamiento: el mismo cierre escrito
    sobre la entalpia de salida, en M-2, al refinar la bateria."""
    bc = Boundary(air=VERANO, m_dot_air=M_AIRE, clima=CLIMA_FRIO, T_amb=308.15)
    filas = []
    for n in (50, 100, 200, 400):
        f = Fluid("Ammonia")
        c = Circuit(f, D.compressor(fluid=f),
                    AirCoil(f, D.air_coil_geometry(), n_segments=n),
                    PlateHeatExchanger(f, Fluid("Water"), D.plate_geometry("condensador_climatizacion"),
                                       n_cells=12),
                    PlateHeatExchanger(f, Fluid("Water"), D.plate_geometry("desrecalentador_acs"),
                                       n_cells=12))
        evaluar = c.evaluate

        def entalpico(*a, **kw):
            st = evaluar(*a, **kw)
            P = st["P_hi"]
            f.update_PT(P, f.Tsat(P) - SP.subcooling)
            h_obj = f.h
            st["residuals"]["R4"] = (st["h_hi"] - h_obj) / (st["comp"].h_dis - h_obj)
            return st

        c.evaluate = entalpico
        s = c.solve("M-2", bc, SP)
        filas.append([n, f"{abs(s.residuals['R4']):.1e}", f"{s.max_residual:.1e}", str(s.converged)])
    return ("### §9.4.5 — R4 escrito sobre la entalpía de salida (M-2)\n\n" +
            tabla(["Segmentos de la batería", "|R4| alcanzado", "Residuo máximo", "Converge"], filas))


def sec_tabular_modos():
    filas = []
    for nombre, modo, bc, sp in casos_diseno():
        c_h = circuito_completo()
        c_t, _ = C.build_circuit(backend_hx="BICUBIC&HEOS", umbral_backend=1e-3)
        s_h, _, t_h = resolver_contando(c_h, modo, bc, sp)
        s_t, _, t_t = resolver_contando(c_t, modo, bc, sp)
        e_h, e_t = I.energy(s_h, MODES[modo]), I.energy(s_t, MODES[modo])
        k = "EER" if modo in ("M-1", "M-2") else ("COP" if modo in ("M-3", "M-4") else "COP_global")
        v_h, v_t = getattr(e_h, k), getattr(e_t, k)
        filas.append([nombre, f"{t_h:.0f} s", f"{t_t:.0f} s", f"{t_h / t_t:.1f}",
                      f"{k} {abs(v_t - v_h) / v_h:.1e}"])
    return ("### §9.8 — backend tabular en los intercambiadores frente a HEOS (60 / 12)\n\n" +
            tabla(["Modo", "HEOS", "Tabular", "Factor", "Diferencia en el indicador"], filas))


def sec_exergia():
    filas = []
    for nombre, modo, bc in (
            ("M-1, verano, ACS 10 → 60 °C", "M-1",
             Boundary(air=VERANO, m_dot_air=M_AIRE, clima=CLIMA_FRIO,
                      acs=WaterStream(T_in=10 + 273.15), T_amb=308.15)),
            ("M-3, invierno, ACS 10 → 60 °C", "M-3",
             Boundary(air=INVIERNO, m_dot_air=M_AIRE, clima=CLIMA_CALOR,
                      acs=WaterStream(T_in=10 + 273.15), T_amb=280.15))):
        c = circuito_completo()
        s = c.solve(modo, bc, Setpoints(superheat=5.0, subcooling=2.0,
                                        T_acs=60 + 273.15))
        e, x = I.energy(s, MODES[modo]), I.exergy(s, MODES[modo])
        base = e.EER if modo == "M-1" else e.COP
        filas.append([nombre, f"{e.Q_acs:.0f} W", f"{x.Ex_productos['acs']:+.1f} W",
                      f"{(e.COP_global / base - 1)*100:.1f} %", f"{x.eta_II:.3f}"])
    return ("### §9.11.2 — el ACS tiene energía y, en verano, no tiene exergía\n\n" +
            tabla(["Caso", "Calor al ACS", "Exergía del ACS",
                   "Subida del COP global", "η_II"], filas))


def sec_tabular():
    bc = Boundary(air=VERANO, m_dot_air=M_AIRE, clima=CLIMA_FRIO, T_amb=308.15)
    filas = []
    for backend, umbral in (("HEOS", None), ("BICUBIC&HEOS", 1e-3)):
        c, _ = C.build_circuit(backend_hx=backend, umbral_backend=umbral, n_segments=120)
        t = time.time()
        s = c.solve("M-2", bc, SP)
        filas.append([backend, f"{s.max_residual:.1e}", f"{time.time() - t:.0f} s"])
    return ("### §9.12.4 — residuo alcanzado con cada backend (M-2, 120 segmentos)\n\n" +
            tabla(["Backend de los intercambiadores", "Residuo", "Tiempo"], filas))


def sec_semiempirico():
    """El modelo semiempírico del §9.5 hasta el 15/10/2026, descartado. Se conserva el ajuste
    del juego adoptado sobre los 46 puntos del catálogo y el ensayo de ampliación sobre los 95
    puntos del catálogo y la envolvente (`herramientas/compresor/ensayo_estructura.py`)."""
    import json
    f = Fluid("Ammonia")
    cat = D.compressor_catalog()
    c = D.compressor(fluid=f, modelo="semiempirico")
    r = c.report(cat)
    env = [p for p in D.compressor_vap_points(fichero="compresor_bock_f2_vap_envolvente.csv")
           if p["bloque"] == "E"]
    re_ = c.report(env)
    t1 = tabla(["Puntos", "Caudal", "Potencia al eje", "Descarga"], [
        ["Catálogo, 46 (identificación)", f"±{r['m_dot']['max_abs_rel']*100:.2f} %",
         f"±{r['W_shaft']['max_abs_rel']*100:.2f} %", f"±{r['T_dis']['max_abs_K']:.2f} K"],
        ["Envolvente de VAP, 49 (sin límites, 1450 rpm, 5 K)",
         f"±{re_['m_dot']['max_abs_rel']*100:.2f} %", f"±{re_['W_shaft']['max_abs_rel']*100:.2f} %",
         f"±{re_['T_dis']['max_abs_K']:.2f} K"]])
    partes = ["### Juego semiempírico del 24/09/2026 frente al catálogo y a la envolvente", t1]
    ensayo = Path("results/compresor/ensayo_estructura_2026_10_15.jsonl")
    if ensayo.is_file():
        nombres = {"base": "Vigente", "n": "+ exponente de reexpansión libre",
                   "mezcla": "+ fuga mezclada en la aspiración",
                   "mezcla+n": "+ fuga mezclada y exponente",
                   "mezcla+n+ic": "+ las dos y η_ic con la relación de presiones",
                   "mezcla+n+dp": "+ las dos y pérdida mecánica con ΔP",
                   "mezcla+n+dp+ic": "Las cuatro"}
        filas = []
        datos = {json.loads(l)["variante"]: json.loads(l) for l in ensayo.read_text().splitlines()}
        for clave in [k for k in nombres if k in datos]:
            d = datos[clave]
            t = d["todos"]
            filas.append([nombres.get(d["variante"], d["variante"]), len(d["parametros"]),
                          f"{t['caudal_max']*100:.1f} %", f"{t['potencia_max']*100:.1f} %",
                          f"{t['descarga_max_K']:.1f} K"])
        partes += ["### Ensayo de ampliación (15/10/2026): reidentificación sobre los 95 puntos, "
                   "desviación máxima dentro de la muestra", tabla(
                       ["Estructura", "Parámetros", "Caudal", "Potencia al eje", "Descarga"], filas)]
    else:
        partes.append("Ensayo de ampliación: ver `docs/DECISIONES_2026_10_15.md` (los resultados "
                      "se regeneran con `herramientas/compresor/ensayo_estructura.py`).")
    return "\n\n".join(partes)


SECCIONES = {"compresor": sec_compresor, "semiempirico": sec_semiempirico, "m2": sec_m2, "evaporador": sec_evaporador,
             "carga": sec_carga, "desrecalentador": sec_desrecalentador,
             "modos": sec_modos, "exergia": sec_exergia, "tabular": sec_tabular,
             "continuacion": sec_continuacion, "malla_placas": sec_malla_placas,
             "residuo_entalpico": sec_residuo_entalpico, "tabular_modos": sec_tabular_modos}

# %%
if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(SECCIONES)
    rev = git_revision()
    partes = [
        "# Cifras del capítulo 9, calculadas por el modelo",
        "",
        "Generado por `notebooks/03_cifras_capitulo_9.py`. **No editar a mano**: "
        "se vuelve a ejecutar cuando el modelo cambia.",
        "",
        f"- Revisión del código: `{rev}`",
        f"- CoolProp {CoolProp.__version__}",
        f"- Generado: {time.strftime('%Y-%m-%d %H:%M')}",
        f"- Secciones: {', '.join(pedidas)}",
        "",
    ]
    if rev.endswith("-dirty"):
        partes.append("> **Aviso**: árbol de trabajo con cambios sin confirmar; "
                      "estas cifras no son reproducibles tal cual (§6.12).\n")
    salida = Path("docs/cifras_capitulo_9.md")
    # Se escribe tras CADA seccion: la ejecucion completa dura media hora y
    # una interrupcion no debe perder lo ya calculado.
    for nombre in pedidas:
        t = time.time()
        print(f"[{nombre}] calculando…", flush=True)
        partes.append(f"## {nombre}\n\n" + SECCIONES[nombre]() + "\n")
        salida.write_text("\n".join(partes) + "\n", encoding="utf-8")
        print(f"[{nombre}] {time.time() - t:.0f} s", flush=True)
    print(f"escrito {salida}")
