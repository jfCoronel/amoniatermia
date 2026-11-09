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
# # 06 - Cifras del capitulo 11 (campana parametrica en regimen permanente)
#
# Notebook de EXPERIMENTACION: escribe `docs/cifras_capitulo_11.md` con
# `reporting.HojaDeCifras`. La seccion `factorial` resuelve la campana
# (decision del autor 2 del 30/09/2026) y guarda un mapa por modo en
# `results/cap11/` (fuera de git; se regenera). Las demas secciones LEEN esos
# mapas: se pueden rehacer sin resolver de nuevo, pero la hoja solo es
# reproducible si se genera entera sobre arbol limpio.
#
#     uv run python notebooks/06_cifras_capitulo_11.py            # todo (~2 h)
#     uv run python notebooks/06_cifras_capitulo_11.py h4 h3      # sobre los mapas ya hechos

# %%
import sys
from pathlib import Path

import numpy as np

from amoniatermia import AirState, Boundary, Setpoints, WaterStream
from amoniatermia import data as D
from amoniatermia import indicators as I
from amoniatermia import maps as MP
from amoniatermia import uncertainty as U
from amoniatermia.circuit import MODES
from amoniatermia.reporting import HojaDeCifras, tabla

K = 273.15
M_AIRE = None   # 7 600 m3/h: el caudal masico lo deduce Boundary (01/10/2026)
V_FRONTAL = 3.30
RESULTADOS = Path("results/cap11")

#: Niveles de la campana (decision 2 del 30/09/2026).
AIRE_FRIO = (20.0, 25.0, 30.0, 35.0, 40.0)
AIRE_CALOR = (-10.0, -7.0, 2.0, 7.0, 12.0)
AIRE_ACS = (-7.0, 2.0, 7.0, 12.0, 20.0, 35.0)
AGUA_FRIO = (10.0, 12.0, 15.0)
AGUA_CALOR = (30.0, 35.0, 40.0)
RECAL = (3.0, 5.0, 8.0)
SUBENF = (0.0, 2.0, 5.0)

#: Caudales de agua y consignas de ACS de los puntos de diseno (tabla 9.6).
# Caudal unico de climatizacion en M-1 a M-4 (decision del autor, 01/10/2026,
# `circuitos_agua.yaml`). Con el, M-3 y M-4 comparten caudal y H3 en calor se
# lee directamente sobre sus dos campanas: la subcampana de M-3 con el caudal de
# M-4 (decision 3 del mismo dia) ya no hace falta.
CAUDAL = {m: D.caudal_climatizacion() for m in ("M-1", "M-2", "M-3", "M-4")}
ACS_ENTRADA_K, ACS_CONSIGNA_K = 35 + K, 67 + K           # M-1 y M-3
ACS5_ENTRADA_K, ACS5_CONSIGNA_K = 15 + K, 52 + K         # M-5


def aire(T_C):
    """Aire exterior. En calor, bulbo humedo 1 K por debajo, como en las
    condiciones de UNE-EN 14825 (A7/6, A2/1, A-7/-8...); por encima de 14 °C,
    humedad relativa del 45 %, la de los puntos de diseno de verano y de M-5.
    En frio la bateria es condensador y el aire va seco."""
    if T_C <= 14.0:
        return AirState.at(T=T_C + K, V_frontal=V_FRONTAL, T_wb=T_C - 1.0 + K)
    return AirState.at(T=T_C + K, V_frontal=V_FRONTAL, RH=0.45)


def caso(modo, caudal=None):
    q = caudal or CAUDAL.get(modo)

    def f(c):
        sp_kw = dict(superheat=c["recalentamiento_K"], subcooling=c["subenfriamiento_K"])
        if modo in ("M-1", "M-2"):
            a = AirState(T=c["T_aire_C"] + K, V_frontal=V_FRONTAL)
            clima = WaterStream(c["T_agua_C"] + K, q)
        elif modo in ("M-3", "M-4"):
            a = aire(c["T_aire_C"])
            clima = WaterStream(c["T_agua_C"] + K, q)
        else:
            a, clima = aire(c["T_aire_C"]), None
        acs = None
        if modo in ("M-1", "M-3"):
            acs = WaterStream(ACS_ENTRADA_K)
            sp_kw["T_acs"] = ACS_CONSIGNA_K
        elif modo == "M-5":
            acs = WaterStream(ACS5_ENTRADA_K)
            sp_kw["T_acs"] = ACS5_CONSIGNA_K
        bc = Boundary(air=a, m_dot_air=M_AIRE, clima=clima, acs=acs,
                      T_amb=c["T_aire_C"] + K)
        return bc, Setpoints(**sp_kw)
    return f


def ejes(modo):
    if modo == "M-5":
        return {"T_aire_C": AIRE_ACS, "recalentamiento_K": RECAL, "subenfriamiento_K": SUBENF}
    frio = modo in ("M-1", "M-2")
    return {"T_aire_C": AIRE_FRIO if frio else AIRE_CALOR,
            "T_agua_C": AGUA_FRIO if frio else AGUA_CALOR,
            "recalentamiento_K": RECAL, "subenfriamiento_K": SUBENF}


MODOS = ("M-1", "M-2", "M-3", "M-4", "M-5")

#: Puntos de diseno (tabla 9.6), los mismos que el cuaderno 05: coordenadas de
#: la campana con recalentamiento 5 K y subenfriamiento 2 K. M-3 lleva los
#: pinzamientos de arranque que usan los cuadernos 05 y la incertidumbre.
DISENO = {"M-1": {"T_aire_C": 35.0, "T_agua_C": 12.0}, "M-2": {"T_aire_C": 35.0, "T_agua_C": 12.0},
          "M-3": {"T_aire_C": 7.0, "T_agua_C": 40.0}, "M-4": {"T_aire_C": 7.0, "T_agua_C": 40.0},
          "M-5": {"T_aire_C": 32.0}}
PINZAMIENTOS = {"M-3": (6.0, 4.0)}

def punto_diseno(modo, caudal=None):
    c = dict(DISENO[modo], recalentamiento_K=5.0, subenfriamiento_K=2.0)
    bc, sp = caso(modo, caudal)(c)
    if modo == "M-5":
        # El punto de diseno de M-5 (tabla 9.6) es aire a 32 °C con el 45 %.
        bc = Boundary(air=AirState.at(T=32 + K, V_frontal=V_FRONTAL, RH=0.45),
                      m_dot_air=M_AIRE, acs=bc.acs, T_amb=32 + K)
    return bc, sp


def mapa(modo) -> MP.PerformanceMap:
    return MP.PerformanceMap.read(RESULTADOS / modo)


def pc(x, n=1):
    return f"{100 * x:.{n}f} %"


def indicador(modo):
    return {"M-1": "EER", "M-2": "EER", "M-3": "COP", "M-4": "COP"}.get(modo, "COP_global")


# %% [markdown]
# ## Campana factorial (C11-2)

# %%
#: Con REUTILIZAR = True la seccion lee los mapas de `results/cap11` en lugar de
#: recalcularlos (2 h 47 min) y declara la revision con que se calcularon.
REUTILIZAR = "--reutilizar" in sys.argv


def sec_factorial():
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    filas, revs = [], set()
    for modo in MODOS:
        if REUTILIZAR:
            m = mapa(modo)
        else:
            m = MP.build(modo, ejes(modo), caso(modo), progreso=True)
            m.write(RESULTADOS / modo)
        revs.add(m.provenance.get("code_revision", "desconocida")[:7])
        n = len(m.rows)
        conv = sum(1 for r in m.rows if r.get("convergido"))
        val = m.n_validos
        adm = sum(1 for r in m.rows if r.get("admisible"))
        ind = [r[indicador(modo)] for r in m.rows
               if r.get("valido") and isinstance(r.get(indicador(modo)), float)]
        filas.append([modo, n, conv, val, adm,
                      f"{min(ind):.2f} – {max(ind):.2f}" if ind else "—"])
    niveles = tabla(["Factor", "Niveles"], [
        ["Aire, frío (M-1, M-2)", " / ".join(f"{t:g}" for t in AIRE_FRIO) + " °C"],
        ["Aire, calor (M-3, M-4)", " / ".join(f"{t:g}" for t in AIRE_CALOR) + " °C"],
        ["Aire, M-5", " / ".join(f"{t:g}" for t in AIRE_ACS) + " °C"],
        ["Agua de climatización, entrada (frío)", " / ".join(f"{t:g}" for t in AGUA_FRIO) + " °C"],
        ["Agua de climatización, entrada (calor)", " / ".join(f"{t:g}" for t in AGUA_CALOR) + " °C"],
        ["Recalentamiento", " / ".join(f"{t:g}" for t in RECAL) + " K"],
        ["Subenfriamiento", " / ".join(f"{t:g}" for t in SUBENF) + " K"]])
    origen = (f"Mapas leídos de `{RESULTADOS}`, calculados en la revisión "
              f"{', '.join(sorted(revs))}.\n\n" if REUTILIZAR else "")
    return (origen + "Niveles (decisión del autor, 30/09/2026). Caudales de agua y consignas de "
            "ACS de los puntos de diseño. Los nudos no convergidos y los no válidos se "
            "cuentan, no se descartan.\n\n" + niveles + "\n"
            + tabla(["Modo", "Nudos", "Convergidos", "Válidos", "Admisibles",
                     "Indicador (válidos)"], filas))


# %% [markdown]
# ## H4: carga con lineas (C11-4)

# %%
def sec_h4():
    """Sensibilidad de la carga sobre la campana, frente al presupuesto UNICO de
    RS-5 (decision 1 del 01/10/2026). El veredicto de H4 esta en `diseno`."""
    pres = I.presupuesto_RS5()
    m_max_g = 1e3 * pres["m_max_kg"]
    filas, por_sub = [], []
    for modo in MODOS:
        m = mapa(modo)
        val = [r for r in m.rows if r.get("valido") and r.get("carga_sistema_max_g") == r.get("carga_sistema_max_g")]
        if not val:
            continue
        peor = max(val, key=lambda r: r["carga_sistema_max_g"])
        filas.append([modo, len(val), f"{peor['carga_sistema_max_g']:.0f} g",
                      f"{peor['carga_sistema_max_g'] / m_max_g:.2f}",
                      sum(1 for r in val if r["carga_sistema_max_g"] > m_max_g),
                      ", ".join(f"{k[4:]} = {peor[k]:g}" for k in peor if k.startswith("eje_"))])
        for sc in SUBENF:
            sel = [r["carga_sistema_max_g"] / m_max_g for r in val if r["eje_subenfriamiento_K"] == sc]
            if sel:
                por_sub.append([modo, f"{sc:g} K", f"{min(sel):.2f}", f"{max(sel):.2f}"])
    return (f"Presupuesto único de RS-5: {m_max_g:.0f} g (50 g/kW sobre los "
            f"{pres['Q_ref_W'] / 1e3:.2f} kW del equilibrio de refrigeración del §9.7.8). "
            "Peor caso de la banda de fracción de huecos; sistema = componentes + líneas "
            "adoptadas (decisión 3b). Es SENSIBILIDAD: el veredicto de H4 se toma en los "
            "puntos de diseño (decisión 2 del 01/10/2026, sección `diseno`).\n\n"
            + tabla(["Modo", "Nudos válidos", "Carga peor", "Fracción del presupuesto",
                     "Nudos por encima", "Condición del peor"], filas)
            + "\n### Fracción del presupuesto frente al subenfriamiento\n\n"
            + tabla(["Modo", "Subenfriamiento", "Mínima", "Máxima"], por_sub))


# %% [markdown]
# ## Recalentamiento como variable (C11-6)

# %%
def sec_recalentamiento():
    filas = []
    for modo in MODOS:
        m = mapa(modo)
        k = indicador(modo)
        base = {tuple((kk, r[kk]) for kk in r if kk.startswith("eje_") and kk != "eje_recalentamiento_K"): r
                for r in m.rows if r.get("valido") and r["eje_recalentamiento_K"] == 5.0}
        for sh in (3.0, 8.0):
            d_ind, d_carga, d_tdis = [], [], []
            for r in m.rows:
                if not r.get("valido") or r["eje_recalentamiento_K"] != sh:
                    continue
                clave = tuple((kk, r[kk]) for kk in r if kk.startswith("eje_") and kk != "eje_recalentamiento_K")
                b = base.get(clave)
                if b is None:
                    continue
                d_ind.append(r[k] / b[k] - 1.0)
                d_carga.append(r["carga_sistema_max_g"] / b["carga_sistema_max_g"] - 1.0)
                d_tdis.append(r["T_dis_C"] - b["T_dis_C"])
            if d_ind:
                filas.append([modo, f"{sh:g} K", len(d_ind),
                              f"{pc(min(d_ind))} … {pc(max(d_ind))}",
                              f"{pc(min(d_carga))} … {pc(max(d_carga))}",
                              f"{min(d_tdis):+.1f} … {max(d_tdis):+.1f} K"])
    return ("Cambio frente a 5 K en los mismos nudos (resto de factores igual).\n\n"
            + tabla(["Modo", "Recalentamiento", "Pares", "Indicador", "Carga (peor)",
                     "Descarga"], filas))


# %% [markdown]
# ## H3: con frente a sin recuperacion (C11-3)

# %%
def sec_h3():
    filas = []
    for con, sin in (("M-1", "M-2"), ("M-3", "M-4")):
        mc, ms = mapa(con), mapa(sin)
        idx = {tuple(r["_indice"]): r for r in ms.rows if r.get("valido")}
        for r in mc.rows:
            if not r.get("valido"):
                continue
            s = idx.get(tuple(r["_indice"]))
            if s is None or r["eje_recalentamiento_K"] != 5.0 or r["eje_subenfriamiento_K"] != 2.0:
                continue
            filas.append([f"{con} / {sin}", f"{r['eje_T_aire_C']:g} °C", f"{r['eje_T_agua_C']:g} °C",
                          f"{r['Q_acs']:.0f} W / {3600 * r['m_acs']:.1f} kg/h",
                          f"{r.get('margen_no_condensacion_K', float('nan')):+.2f} K",
                          f"{(r['Pk'] - s['Pk']) / 100:+.0f} mbar",
                          pc(r["COP_global"] / s[indicador(sin)] - 1.0)])
    return ("Mismo aire, misma entrada de agua y mismas consignas (recalentamiento 5 K, "
            "subenfriamiento 2 K); el ACS sale siempre a la consigna de 67 °C, que "
            "impone R3. Los cuatro modos comparten el caudal de climatización "
            f"({CAUDAL['M-4']} kg/s, 01/10/2026), de modo que la diferencia es solo la "
            "recuperación. ΔCOP global: el del modo con recuperación frente al "
            "indicador del modo sin ella.\n\n"
            + tabla(["Modos", "Aire", "Agua", "ACS recuperado", "Margen de no condensación",
                     "Δp_k", "ΔCOP global"], filas))


# %% [markdown]
# ## H6: destruccion de exergia del compresor (C11-5)

# %%
def sec_h6():
    filas = []
    for modo in MODOS:
        m = mapa(modo)
        val = [r for r in m.rows if r.get("valido") and "componente_mayor_ciclo" in r]
        if not val:
            continue
        y = [r.get("y_D_ciclo_compresor_con_motor", float("nan")) for r in val]
        cumple = sum(1 for r in val if r["componente_mayor_ciclo"] == "compresor_con_motor")
        otros = {}
        for r in val:
            if r["componente_mayor_ciclo"] != "compresor_con_motor":
                otros[r["componente_mayor_ciclo"]] = otros.get(r["componente_mayor_ciclo"], 0) + 1
        filas.append([modo, len(val), f"{min(y):.3f} – {max(y):.3f}", f"{cumple} / {len(val)}",
                      ", ".join(f"{k} ({v})" for k, v in otros.items()) or "—"])
    return ("Clasificación de componentes del ciclo con el ventilador como auxiliar "
            "(decisión 2 del 29/09/2026). El margen recuperable con velocidad variable "
            "queda pendiente del η_is de referencia de esa tecnología.\n\n"
            + tabla(["Modo", "Nudos válidos", "y_D del compresor con motor",
                     "Nudos en que es el mayor", "Mayor en los demás"], filas))


# %% [markdown]
# ## Puntos de diseno: veredicto de H4 y margen de H6

# %%
_DISENO = {}


def soluciones_diseno():
    """Puntos de diseno de los cinco modos, resueltos una sola vez."""
    if not _DISENO:
        from amoniatermia import campaign as C
        c, _ = C.build_circuit()
        for modo in MODOS:
            bc, sp = punto_diseno(modo)
            pin = PINZAMIENTOS.get(modo)
            x0 = c.initial_guess(modo, bc, sp, pinch_air=pin[0], pinch_water=pin[1]) if pin else None
            _DISENO[modo] = c.solve(modo, bc, sp, x0=x0)
    return _DISENO


def sec_diseno():
    pres = I.presupuesto_RS5()
    eta = I.eta_is_catalogo()
    h4, h6 = [], []
    sol = soluciones_diseno()
    for modo in MODOS:
        s = sol[modo]
        lin = sum(r.charge["_max"] for r in s.lines.values())
        h4.append([modo, str(s.valid), f"{1e3 * s.charge['_max']:.0f} g", f"{1e3 * lin:.0f} g",
                   f"{1e3 * s.charge_sistema['_max']:.0f} g",
                   f"{I.fraccion_RS5(s, pres):.3f}", f"{s.charge_sistema['_RS5_peor_caso']:.3f}"])
        mg = I.margen_compresor(s, MODES[modo], eta["max"])
        x = I.exergy(s, MODES[modo])
        mayor = x.componente_mayor_ciclo
        h6.append([modo, f"{x.y_D_ciclo['compresor_con_motor']:.3f}", mayor,
                   f"{mg['indicador']:.3f}", f"{mg['eta_is']:.3f}",
                   f"{mg['termodinamica']['dW_el_W']:.0f} W ({pc(mg['termodinamica']['d_indicador'])})",
                   f"{mg['tecnica']['dW_el_W']:.0f} W ({pc(mg['tecnica']['d_indicador'])})"])
    peor = max(MODOS, key=lambda m: I.fraccion_RS5(sol[m], pres))
    f_peor = I.fraccion_RS5(sol[peor], pres)
    q_m2 = sol["M-2"].Q_evap
    return (f"### H4: presupuesto único de RS-5\n\n"
            f"Equilibrio de refrigeración del §9.7.8 (M-2, evaporación impuesta a 2 °C, aire "
            f"a 35 °C, recalentamiento 1 K, subenfriamiento 0): {pres['Q_ref_W'] / 1e3:.2f} kW, "
            f"presupuesto de **{1e3 * pres['m_max_kg']:.0f} g** (decisión 1 del 01/10/2026). "
            f"DISCREPANCIA declarada: el sistema completo en el punto de diseño de M-2 entrega "
            f"{q_m2 / 1e3:.2f} kW, que daría {50 * q_m2 / 1e3:.0f} g; el capítulo debe decir de "
            "cuál de los dos equilibrios se trata.\n\n"
            + tabla(["Modo", "Válido", "Componentes", "Líneas", "Sistema",
                     "Fracción del presupuesto único", "Fracción con la capacidad del modo "
                     "(informativa)"], h4)
            + f"\n**Modo más desfavorable: {peor}, {f_peor:.3f} del presupuesto** "
              f"({'H4 NO se cumple' if f_peor > 1 else 'H4 se cumple'} en el peor caso de la "
              "banda; en M-1 el resultado se publica en el límite, decisión 1 del 30/09/2026: "
              "depende de la geometría de líneas, de 0.99 a 1.07).\n\n"
            "### H6: destrucción de exergía y margen recuperable en el compresor\n\n"
            f"Cota técnica: el mismo compresor con el mejor rendimiento isoentrópico de su "
            f"catálogo, η_is = {eta['max']:.3f} (T₀ = {eta['punto_max']['T0_C']:.0f} °C, "
            f"T_k = {eta['punto_max']['Tk_C']:.0f} °C; mediana {eta['mediana']:.3f}). Cota "
            "termodinámica: la exergía destruida en el compresor con su motor. Las dos son de "
            "primer orden (misma capacidad y mismo ciclo). Un η_is del punto por encima del "
            "del catálogo es extrapolación (M-5 está fuera del dominio del compresor) y da "
            "margen técnico nulo.\n\n"
            + tabla(["Modo", "y_D del compresor con motor", "Mayor del ciclo", "Indicador",
                     "η_is del punto", "Cota termodinámica", "Cota técnica"], h6))


# %% [markdown]
# ## Penalizacion entre modos (H2, C11-8)

# %%
def sec_modos():
    filas, detalle = [], []
    for nombre, (a, qa), (b, qb) in (
            ("Frío, M-1 frente a M-2", ("M-1", None), ("M-2", None)),
            ("Calor, M-3 frente a M-4", ("M-3", None), ("M-4", None))):
        evs = []
        for modo, q in ((a, qa), (b, qb)):
            bc, sp = punto_diseno(modo, q)
            evs.append(U.Evaluador(modo, bc, sp, pinzamientos=PINZAMIENTOS.get(modo)))
        rr = U.bandas_diferencia(*evs, {
            "servicio": ("indicador", "indicador"),
            "global": ("COP_global", "indicador")})
        for clave, texto in (("servicio", "indicador del servicio (EER o COP de climatización)"),
                             ("global", "COP global con ACS frente al indicador sin ella")):
            r = rr[clave]
            filas.append([nombre, texto, pc(r["d"], 2), f"± {pc(r['banda_rss'], 2)}",
                          f"± {pc(r['banda_lineal'], 2)}",
                          "sí" if r["significativa"] else "no",
                          "sí" if r["significativa_conservadora"] else "no"])
        r = rr["servicio"]
        detalle.append(f"#### {nombre}: indicador del servicio\n\n" + tabla(
            ["Fuente", "Grupo", "Perturbación", "Estado", "Cambio de la diferencia",
             "Cambio en el primero", "Cambio en el segundo"],
            [[f["fuente"], f["grupo"], f["perturbacion"], f["estado"],
              pc(f["cambio_d"], 2) if "cambio_d" in f else "—",
              pc(f["cambio_a"], 2) if "cambio_a" in f else "—",
              pc(f["cambio_b"], 2) if "cambio_b" in f else "—"] for f in r["filas"]]))
    return ("Criterio (decisión 3 del 30/09/2026): una penalización cuenta si supera la "
            "incertidumbre del modelo SOBRE LA DIFERENCIA. Cada alternativa de correlación "
            "(C10-7) y cada extremo de parámetro o juego del compresor (C10-8) se aplica a "
            "los dos modos a la vez; por grupo, el mayor cambio; los grupos se combinan en "
            "raíz de la suma de cuadrados, con la suma lineal como cota conservadora. Puntos "
            "de diseño, recalentamiento 5 K y subenfriamiento 2 K.\n\n"
            "Dos lecturas, que el capítulo debe distinguir. En frío el ACS es un subproducto "
            "y la penalización es la del EER: en M-2 el desrecalentador trabaja como "
            "evaporador adicional (tren del §9.3.1) y en M-1 no. En calor el ACS se lleva "
            "parte del mismo calor, de modo que el COP de climatización baja por "
            "construcción; la penalización de rendimiento es la del COP global.\n\n"
            + tabla(["Comparación", "Magnitud", "Diferencia", "Banda (RSS)", "Banda (lineal)",
                     "Significativa", "Significativa (conservadora)"], filas)
            + "\n" + "\n\n".join(detalle))


# %% [markdown]
# ## Exergia en los puntos de diseno (H6, §6.9)

# %%
CICLO = ("compresor_con_motor", "placas_clima", "bateria", "desrecalentador", "valvula")


def sec_exergia():
    filas, tot, sep = [], [], []
    for modo, s in soluciones_diseno().items():
        x = I.exergy(s, MODES[modo])
        y = x.y_D_ciclo
        filas.append([modo] + [f"{100 * y.get(k, 0.0):.1f} %" for k in CICLO]
                     + [x.componente_mayor_ciclo])
        ciclo = sum(x.E_D[k] for k in x.E_D if k != "ventilador")
        sep.append([modo, f"{x.E_D_compresion:.0f} W ({100 * x.E_D_compresion / ciclo:.1f} %)",
                    f"{x.E_D_electromecanica:.0f} W ({100 * x.E_D_electromecanica / ciclo:.1f} %)",
                    max(((k, v) for k, v in y.items() if k != "compresor_con_motor"),
                        key=lambda kv: kv[1])[0]])
        tot.append([modo, f"{x.E_D_total:.0f} W", f"{100 * x.y_D.get('ventilador', 0.0):.1f} %",
                    f"{x.eta_II:.3f}" if x.eta_II is not None else "—",
                    f"{100 * x.cierre:+.2f} %"])
    return ("Reparto de la exergía destruida entre los componentes del ciclo (y_D del ciclo, "
            "sin el ventilador, decisión 2 del 29/09/2026; el compresor con su motor y su "
            "transmisión). Estado muerto: el aire exterior de cada punto.\n\n"
            + tabla(["Modo", "Compresor con motor", "Placas de climatización", "Batería",
                     "Desrecalentador", "Válvula", "Mayor"], filas)
            + "\n### Totales\n\n"
            + tabla(["Modo", "Exergía destruida total", "Ventilador (fracción del total)",
                     "η_II", "Cierre exergético"], tot)
            + "\n### Compresión frente a conversión electromecánica\n\n"
              "Separación del compresor con motor en la irreversibilidad propia de la compresión "
              "y la pérdida del motor y la transmisión, en W y en fracción de la exergía "
              "destruida en el ciclo (sin ventilador). El cálculo ilustrativo del capítulo 4 "
              "(§4.11) no incluye motor.\n\n"
            + tabla(["Modo", "Compresión", "Motor y transmisión", "Mayor de los demás componentes"], sep))


# %% [markdown]
# ## Admisibilidad sobre la campana (H2)

# %%
def sec_admisibilidad():
    from amoniatermia.validation.domain import clasifica
    filas, region, dom = [], [], []
    for modo in MODOS:
        m = mapa(modo)
        val = [r for r in m.rows if r.get("valido")]
        no = [r for r in val if not r.get("admisible")]
        diag = sum(1 for r in no if r.get("envolvente_diagrama_aplicacion") == "incumple")
        tdis = sum(1 for r in no if r.get("envolvente_temperatura_descarga") == "incumple")
        palta = sum(1 for r in no if r.get("envolvente_presion_alta") == "incumple")
        filas.append([modo, len(val), len(val) - len(no), diag, tdis, palta,
                      f"{max(r['T_dis_C'] for r in val):.1f} °C",
                      f"{max(r['Pk'] for r in val) / 1e5:.1f} bar"])
        cl = [clasifica(r["T_evap_C"] + K, r["T_cond_C"] + K) for r in val]
        dentro = [c != "fuera_del_dominio" for c in cl]
        dom.append([modo, sum(dentro), len(cl) - sum(dentro),
                    sum(1 for r, d_ in zip(val, dentro) if d_ and r.get("admisible")),
                    sum(1 for r, d_ in zip(val, dentro) if not d_ and r.get("admisible"))])
        clave = [k for k in ("eje_T_aire_C", "eje_T_agua_C") if k in val[0]]
        celdas = {}
        for r in val:
            if r["eje_recalentamiento_K"] == 5.0 and r["eje_subenfriamiento_K"] == 2.0:
                celdas[tuple(r[k] for k in clave)] = r
        for k_, r in sorted(celdas.items()):
            region.append([modo] + [f"{v:g} °C" for v in k_] + (["—"] if len(k_) == 1 else [])
                          + [r["zona_diagrama"], f"{r['T_dis_C']:.1f} °C",
                             f"{r[indicador(modo)]:.2f}", "sí" if r["admisible"] else "no"])
    return ("Nudos válidos que no son admisibles, por causa (un nudo puede incumplir más de "
            "una). Solo la zona sin límites del diagrama del compresor es admisible, y la "
            "descarga no puede superar 140 °C (decisiones del 29/09/2026); la presión alta, "
            "25 bar manométricos.\n\n"
            + tabla(["Modo", "Válidos", "Admisibles", "Fuera de la zona sin límites",
                     "Descarga > 140 °C", "Presión alta", "Descarga máxima", "p_k máxima"], filas)
            + "\n### Dominio de validez del compresor (capítulo 10): su envolvente\n\n"
            "Con los polinomios de UNE-EN 12900 (15/10/2026) el dominio del compresor es la "
            "zona del diagrama que cubren los datos del fabricante; un nudo admisible está "
            "siempre dentro (la última columna debe ser 0).\n\n"
            + tabla(["Modo", "Dentro del dominio", "Fuera del dominio",
                     "Admisibles (dentro)", "Admisibles fuera del dominio"], dom)
            + "\n### Recalentamiento 5 K y subenfriamiento 2 K\n\n"
            + tabla(["Modo", "Aire", "Agua", "Zona del diagrama", "Descarga", "Indicador",
                     "Admisible"], region))


# %% [markdown]
# ## Figuras del capitulo 11
#
# Colores y estilo de las figuras 9.3 y del ejemplo de M-1. Cada serie lleva tipo
# de linea y marcador ademas del color; relleno = admisible, hueco = no admisible.

# %%
def sec_figuras():
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    AZUL, NARANJA, VERDE = "#2a78d6", "#eb6834", "#2e9a6b"
    TINTA, TINTA_2, GRIS = "#0b0b0b", "#52514e", "#b8b7b2"
    mpl.rcParams.update({
        "figure.dpi": 120, "savefig.dpi": 300, "font.size": 8, "axes.titlesize": 8,
        "axes.labelsize": 8, "legend.fontsize": 7, "axes.edgecolor": GRIS,
        "axes.labelcolor": TINTA, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "lines.linewidth": 1.5})
    salida = Path("docs/figuras")
    salida.mkdir(parents=True, exist_ok=True)

    def serie(modo, agua=None, sh=5.0, sc=2.0, campo=None):
        rs = [r for r in mapa(modo).rows if r.get("valido") and r["eje_recalentamiento_K"] == sh
              and r["eje_subenfriamiento_K"] == sc and (agua is None or r.get("eje_T_agua_C") == agua)]
        rs.sort(key=lambda r: r["eje_T_aire_C"])
        return ([r["eje_T_aire_C"] for r in rs], [r[campo or indicador(modo)] for r in rs],
                [bool(r["admisible"]) for r in rs])

    def trazar(ax, x, y, adm, color, ls, mk, label):
        ax.plot(x, y, color=color, ls=ls, label=label)
        ax.scatter([a for a, b in zip(x, adm) if b], [a for a, b in zip(y, adm) if b],
                   color=color, marker=mk, s=18, zorder=3, edgecolors="white", linewidths=0.6)
        ax.scatter([a for a, b in zip(x, adm) if not b], [a for a, b in zip(y, adm) if not b],
                   facecolors="white", edgecolors=color, marker=mk, s=18, zorder=3, linewidths=1.0)

    hechas = []
    # Figura 11.1: indicador del servicio frente al aire exterior
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.5))
    for ax, titulo, pares, agua in (
            (axes[0], "Frío, agua a 12 °C\nEER", (("M-1", AZUL, "-", "o"), ("M-2", NARANJA, "--", "s")), 12.0),
            (axes[1], "Calor, agua a 40 °C\nCOP global (M-3), COP (M-4)", (("M-3", AZUL, "-", "o"), ("M-4", NARANJA, "--", "s")), 40.0),
            (axes[2], "Solo ACS\nCOP global", (("M-5", VERDE, "-", "^"),), None)):
        for modo, col, ls, mk in pares:
            campo = "COP_global" if modo == "M-3" else None
            x, y, adm = serie(modo, agua, campo=campo)
            trazar(ax, x, y, adm, col, ls, mk, modo)
        ax.set_title(titulo, loc="left", color=TINTA)
        ax.set_xlabel("Aire exterior [°C]")
        ax.legend(frameon=False)
    axes[0].set_ylabel("Indicador [-]")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_11_1_indicadores.{ext}", bbox_inches="tight")
    plt.close(fig)
    hechas.append("fig_11_1_indicadores")

    # Figura 11.2: margen de no condensacion (H3)
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.5), sharey=True)
    for ax, modo, aguas in ((axes[0], "M-1", (10.0, 12.0, 15.0)), (axes[1], "M-3", (30.0, 35.0, 40.0))):
        for agua, col, ls, mk in zip(aguas, (AZUL, NARANJA, VERDE), ("-", "--", ":"), ("o", "s", "^")):
            x, y, adm = serie(modo, agua, campo="margen_no_condensacion_K")
            trazar(ax, x, y, adm, col, ls, mk, f"agua a {agua:g} °C")
        ax.axhline(0.0, color=TINTA_2, lw=0.8)
        ax.set_title(f"{modo}: margen de no condensación", loc="left", color=TINTA)
        ax.set_xlabel("Aire exterior [°C]")
        ax.legend(frameon=False)
    axes[0].set_ylabel("Margen sobre la saturación [K]")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_11_2_margen_H3.{ext}", bbox_inches="tight")
    plt.close(fig)
    hechas.append("fig_11_2_margen_H3")

    # Figura 11.3: fraccion del presupuesto de RS-5 frente al subenfriamiento (H4)
    pres = I.presupuesto_RS5()
    m_max_g = 1e3 * pres["m_max_kg"]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.5), sharey=True)
    for ax, modo in ((axes[0], "M-1"), (axes[1], "M-2")):
        for sc, col, ls, mk in zip(SUBENF, (AZUL, NARANJA, VERDE), ("-", "--", ":"), ("o", "s", "^")):
            x, y, adm = serie(modo, 12.0, sc=sc, campo="carga_sistema_max_g")
            trazar(ax, x, [v / m_max_g for v in y], adm, col, ls, mk, f"subenfriamiento {sc:g} K")
        ax.axhline(1.0, color=TINTA_2, lw=0.8)
        ax.set_title(f"{modo}: carga peor / presupuesto de RS-5", loc="left", color=TINTA)
        ax.set_xlabel("Aire exterior [°C]")
    axes[0].set_ylabel(f"Fracción de {m_max_g:.0f} g [-]")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(salida / f"fig_11_3_carga_RS5.{ext}", bbox_inches="tight")
    plt.close(fig)
    hechas.append("fig_11_3_carga_RS5")
    return ("Figuras escritas en `docs/figuras` (png y pdf): " + ", ".join(hechas)
            + ". Recalentamiento 5 K; relleno = admisible, hueco = no admisible.")


# %%
SECCIONES = {"factorial": sec_factorial, "diseno": sec_diseno, "h4": sec_h4,
             "recalentamiento": sec_recalentamiento, "h3": sec_h3, "h6": sec_h6,
             "modos": sec_modos, "exergia": sec_exergia,
             "admisibilidad": sec_admisibilidad, "figuras": sec_figuras}

if __name__ == "__main__":
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SECCIONES)
    hoja = HojaDeCifras("docs/cifras_capitulo_11.md", "Cifras del capítulo 11",
                        "notebooks/06_cifras_capitulo_11.py")
    for nombre in pedidas:
        print(f"[{nombre}] calculando…", flush=True)
        hoja.seccion(nombre, SECCIONES[nombre]())
    print("escrito", hoja.ruta)
