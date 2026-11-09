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
# # 05 - Cifras del capitulo 10 (verificacion, validacion y dominio)
#
# Notebook de EXPERIMENTACION: carga el paquete, ejecuta y escribe
# `docs/cifras_capitulo_10.md` con `reporting.HojaDeCifras` (la revision se lee
# al arrancar y el fichero se reescribe tras cada seccion).
#
# Secciones: compresor (N1 del compresor por polinomios: velocidad omitida y regla del
# recalentamiento), malla (independencia de la
# discretizacion del sistema), intercambiadores (N2), bandas (correlaciones
# alternativas), dominio (dominio de validez), incertidumbre (sensibilidad
# local y cribado de Morris, C10-8).
#
#     uv run python notebooks/05_cifras_capitulo_10.py            # todo (~1 h)
#     uv run python notebooks/05_cifras_capitulo_10.py malla bandas

# %%
import sys

from amoniatermia import (AirState, Boundary, Setpoints, WaterStream,
                          campaign as C)
from amoniatermia import data as D
from amoniatermia import uncertainty as U
from amoniatermia.reporting import HojaDeCifras, tabla
from amoniatermia.validation import bands as B
from amoniatermia.validation import domain as DOM
from amoniatermia.validation import exchangers as X
from amoniatermia.validation import mesh as MESH

K = 273.15
M_AIRE = None   # 7 600 m3/h: el caudal masico lo deduce Boundary (01/10/2026)
Q_CLIMA = D.caudal_climatizacion()     # el mismo en M-1 a M-4 (01/10/2026)
VERANO = AirState(T=35 + K, V_frontal=3.30)
INVIERNO = AirState.at(T=7 + K, V_frontal=3.30, T_wb=6 + K)
AIRE_M5 = AirState.at(T=32 + K, V_frontal=3.30, RH=0.45)
SP = Setpoints(superheat=5.0, subcooling=2.0)
SP_ACS = Setpoints(superheat=5.0, subcooling=2.0, T_acs=67 + K)

#: Puntos de diseno de los cinco modos (los de la tabla 9.6), con los
#: pinzamientos de arranque cuando el modo los necesita.
CASOS = {
    "M-1": (Boundary(air=VERANO, m_dot_air=M_AIRE, clima=WaterStream(12 + K, Q_CLIMA),
                     acs=WaterStream(35 + K), T_amb=35 + K), SP_ACS, None),
    "M-2": (Boundary(air=VERANO, m_dot_air=M_AIRE, clima=WaterStream(12 + K, Q_CLIMA),
                     T_amb=35 + K), SP, None),
    "M-3": (Boundary(air=INVIERNO, m_dot_air=M_AIRE, clima=WaterStream(40 + K, Q_CLIMA),
                     acs=WaterStream(35 + K), T_amb=7 + K), SP_ACS, (6.0, 4.0)),
    "M-4": (Boundary(air=INVIERNO, m_dot_air=M_AIRE, clima=WaterStream(40 + K, Q_CLIMA),
                     T_amb=7 + K), SP, None),
    "M-5": (Boundary(air=AIRE_M5, m_dot_air=M_AIRE, acs=WaterStream(15 + K), T_amb=32 + K),
            Setpoints(superheat=5.0, subcooling=2.0, T_acs=52 + K), None),
}


def pc(x, n=2):
    return f"{100 * x:.{n}f} %"


# %% [markdown]
# ## Validacion del compresor (N1)
#
# Desde el 15/10/2026 el compresor se describe con polinomios de UNE-EN 12900
# ajustados a los puntos de VAP en toda la envolvente (`docs/DECISIONES_2026_10_15.md`).
# Los puntos de ajuste quedan consumidos; validan lo que el ajuste no ha visto:
# la velocidad omitida, los puntos a 960 y 1200 rpm del 29/09/2026 y, para la
# regla del recalentamiento, el catalogo a 1 K y los puntos a 1 y 10 K.

# %%
def sec_compresor():
    from amoniatermia.validation import compressor_en12900 as V
    r = V.validacion()
    u = r["umbral"]

    def fila(nombre, d):
        return [nombre, d["n"], pc(d["caudal_max"]), pc(d["caudal_medio"]),
                pc(d["potencia_max"]), pc(d["potencia_medio"]),
                f"{d['descarga_max_K']:.2f} K", f"{d['descarga_medio_K']:+.2f} K",
                "sí" if d["cumple_N1"] else "NO"]
    cab = ["Conjunto", "Puntos", "Caudal máx.", "Caudal medio", "Potencia máx.",
           "Potencia media", "Descarga máx.", "Descarga media", "N1"]
    aj = [fila(f"{v} rpm", d) for v, d in r["ajuste"].items()]
    ve = [fila(k, d) for k, d in r["velocidad"].items()]
    re = [fila(k, d) for k, d in r["recalentamiento"].items()]
    pv = r["peor_validacion"]
    return ("### Validación del compresor por polinomios (N1)\n\n"
            f"Criterio de N1: caudal ≤ {pc(u['caudal'], 0)}, potencia al eje ≤ "
            f"{pc(u['potencia'], 0)}, descarga ≤ {u['temperatura_descarga_K']:.0f} K, como "
            "desviación máxima. Desviación = modelo − fabricante.\n\n"
            "#### Ajuste (no es validación: los puntos están consumidos)\n\n" + tabla(cab, aj)
            + "\n#### Velocidad: la omitida y los puntos del 29/09/2026\n\n" + tabla(cab, ve)
            + "\n#### Recalentamiento: regla de conservación de los rendimientos de 5 K\n\n"
            + tabla(cab, re)
            + f"\n**N1 {'se cumple' if r['cumple_N1'] else 'NO se cumple'}** en todas las "
              f"validaciones. Peor caso: caudal {pc(pv['caudal_max'])}, potencia "
              f"{pc(pv['potencia_max'])}, descarga {pv['descarga_max_K']:.2f} K. Dominio de "
              "validez del compresor: su envolvente (zonas sin límites y de refrigeración "
              "suplementaria del diagrama), de 960 a 1450 rpm y de 1 a 10 K de "
              "recalentamiento.\n")


# %% [markdown]
# ## Independencia de la discretizacion del sistema

# %%
def sec_malla():
    out = []
    resumen = []
    for m, (bc, sp, pin) in CASOS.items():
        r = MESH.mesh_series(m, bc, sp, pinzamientos=pin)
        filas = [[f"{f['segmentos']} / {f['volumenes']}", f"{f['Q_util']:.1f} W",
                  f"{f['W_el']:.1f} W", f"{f['indicador']:.4f}",
                  f"{f['T_evap'] - K:.3f}", f"{f['T_cond'] - K:.3f}",
                  f"{f['T_dis'] - K:.2f}", f"{1e3 * f['carga_max']:.1f} g",
                  str(f["valido"]), f"{f['t_s']:.0f} s"] for f in r["filas"]]
        out.append(f"### {m}\n\n" + tabla(
            ["Segmentos / volúmenes", "Q útil", "W eléctrica", "Indicador", "T_evap °C",
             "T_cond °C", "T_dis °C", "Carga (peor)", "Válido", "Tiempo"], filas))
        t = r["trabajo_frente_a_la_mas_fina"]
        resumen.append([m, pc(t["Q_util"], 3), pc(t["W_el"], 3), pc(t["indicador"], 3),
                        pc(t["carga_max"], 2),
                        ", ".join(k for k, v in r["monotona"].items() if not v) or "—"])
    return ("### Discretización de trabajo (60 / 12) frente a la más fina (240 / 48)\n\n"
            + tabla(["Modo", "Q útil", "W eléctrica", "Indicador", "Carga (peor)",
                     "Series no monótonas"], resumen) + "\n" + "\n\n".join(out))


# %% [markdown]
# ## Contraste de los intercambiadores (N2)

# %%
def sec_intercambiadores():
    filas = []
    for c in X.todos():
        for mg in c["magnitudes"]:
            dev = (pc(mg["desviacion"], 1) if "desviacion" in mg
                   else (f"{mg['desviacion_K']:+.2f} K" if "desviacion_K" in mg else "—"))
            filas.append([c["ficha"], mg["magnitud"], f"{mg['modelo']:.4g}",
                          f"{mg['ficha']:.4g}", dev, mg["estatuto"]])
    return ("### Fichas de fabricante\n\n`validacion`: la magnitud no intervino en ningún "
            "anclaje. `coherencia`: ficha consumida por un anclaje (§6.3.1).\n\n"
            + tabla(["Ficha", "Magnitud", "Modelo", "Ficha", "Desviación", "Estatuto"],
                    filas))


# %% [markdown]
# ## Bandas de correlacion

# %%
def sec_bandas():
    out, resumen = [], []
    for m, (bc, sp, pin) in CASOS.items():
        x0 = None
        if pin:
            c, _ = C.build_circuit()
            x0 = c.initial_guess(m, bc, sp, pinch_air=pin[0], pinch_water=pin[1])
        r = B.band(m, bc, sp, x0=x0)
        filas = []
        for f in r["alternativas"]:
            if f["estado"] == "evaluada":
                filas.append([f["componente"], f["familia"], f["alternativa"], "evaluada",
                              pc(f["d_Q_util"]), pc(f["d_W_el"]), pc(f["d_indicador"]),
                              f"{f['dT_evap_K']:+.2f}", f"{f['dT_cond_K']:+.2f}"])
            else:
                filas.append([f["componente"], f["familia"], f["alternativa"], f["estado"],
                              "—", "—", "—", "—", "—"])
        out.append(f"### {m}\n\n" + tabla(
            ["Componente", "Familia", "Alternativa", "Estado", "ΔQ útil", "ΔW eléctrica",
             "ΔIndicador", "ΔT_evap K", "ΔT_cond K"], filas))
        b = r["banda"]
        resumen.append([m, f"{pc(b['d_Q_util'][0])} / {pc(b['d_Q_util'][1])}",
                        f"{pc(b['d_indicador'][0])} / {pc(b['d_indicador'][1])}"])
        fuera = B.band(m, bc, sp, x0=x0, alternativas=B.FUERA_DE_BASE)["alternativas"]
        for f in fuera:
            if f["estado"] == "evaluada":
                out.append(f"Fuera de la banda, por estar fuera de su base geométrica: "
                           f"{f['alternativa']} en {f['componente']} daría "
                           f"{pc(f['d_indicador'])} en el indicador.")
    return ("### Banda por modo (correlaciones evaluables dentro de su base)\n\n"
            + tabla(["Modo", "ΔQ útil (mín / máx)", "ΔIndicador (mín / máx)"], resumen)
            + "\n" + "\n\n".join(out))


# %% [markdown]
# ## Dominio de validez

# %%
def sec_dominio():
    sols = {}
    c, _ = C.build_circuit()
    for m, (bc, sp, pin) in CASOS.items():
        x0 = (c.initial_guess(m, bc, sp, pinch_air=pin[0], pinch_water=pin[1])
              if pin else None)
        sols[f"{m} diseño"] = c.solve(m, bc, sp, x0=x0)
    # Barridos de temperatura exterior: calefaccion (M-4) y frio (M-2).
    # Continuacion en pasos cortos; si da un punto no valido (un salto de 9 K
    # llego a converger a una evaporacion de 117 °C, marcada no valida), se
    # repite desde la estimacion por parametros agrupados.
    def barrido(modo, temps, hacer_bc, x0):
        for T in temps:
            bc = hacer_bc(T)
            s = c.solve(modo, bc, SP, x0=x0)
            if not s.valid:
                s = c.solve(modo, bc, SP)
            if s.valid:
                x0 = dict(s.unknowns)
            sols[f"{modo} aire {T} °C"] = s

    barrido("M-4", (12, 7, 4, 2, 0, -2, -5, -7, -10),
            lambda T: Boundary(air=AirState.at(T=T + K, V_frontal=3.30, RH=0.85),
                               m_dot_air=M_AIRE, clima=WaterStream(40 + K, Q_CLIMA),
                               T_amb=T + K),
            dict(sols["M-4 diseño"].unknowns))
    barrido("M-2", (20, 25, 30, 35, 40),
            lambda T: Boundary(air=AirState(T=T + K, V_frontal=3.30), m_dot_air=M_AIRE,
                               clima=WaterStream(12 + K, Q_CLIMA), T_amb=T + K),
            dict(sols["M-2 diseño"].unknowns))
    filas = [[r["punto"], f"{r['T_evap_C']:.2f}", f"{r['T_cond_C']:.2f}",
              f"{r['relacion_compresion']:.2f}", r["zona_diagrama"],
              "dentro" if r["clase"] == "dentro_del_dominio" else "fuera",
              str(r["valido"]), str(r["admisible"])]
             for r in DOM.resumen(sols)]
    return ("Compresor por polinomios de UNE-EN 12900 (15/10/2026): el dominio de validez es "
            "su envolvente, las zonas del diagrama que cubren los datos de VAP (sin límites y "
            "refrigeración suplementaria), de 960 a 1450 rpm y de 1 a 10 K de "
            "recalentamiento. Dentro, la admisibilidad la deciden solo los límites del "
            "compresor real (zona sin límites, 140 °C y presiones); fuera, el polinomio "
            "extrapola y el punto no es admisible.\n\n"
            + tabla(["Punto", "T_evap °C", "T_cond °C", "Relación de compresión",
                     "Zona del diagrama", "Dominio del compresor", "Válido", "Admisible"],
                    filas))


# %% [markdown]
# ## Incertidumbre de parametros (C10-8)

# %%
SALIDAS = (("Q_util", "Q útil"), ("W_el", "W eléctrica"), ("indicador", "Indicador"),
           ("carga_max", "Carga (peor)"))


def _fmt(d, k):
    return f"{d[k]:+.2f} K" if k in U.ABSOLUTAS else f"{100 * d[k]:+.2f} %"


def sec_incertidumbre():
    rangos = [[n, f"{f.nominal:.4g}", f"{f.bajo:.4g}", f"{f.alto:.4g}", f.fuente]
              for n, f in U.FACTORES.items()]
    out = ["Rangos (decisión del autor, 29/09/2026). El ventilador no es factor: los "
           "780 W son dato. El compresor entra como factor discreto: los dos extremos de la "
           "banda del error de ajuste de sus polinomios (decisión P3 del 15/10/2026): "
           + "; ".join(f"{n}: caudal ×{j['factor_caudal']:.4f}, potencia ×{j['factor_potencia']:.4f}, "
                       f"descarga {j['desplazamiento_descarga_K']:+.2f} K"
                       for n, j in U.juegos_compresor().items() if n != "adoptado") + ".\n\n"
           + tabla(["Factor", "Nominal", "Bajo", "Alto", "Fuente"], rangos)]
    resumen = []
    for m, (bc, sp, pin) in CASOS.items():
        ev = U.Evaluador(m, bc, sp, pinzamientos=pin)
        loc = U.local(ev)
        filas = [[f["factor"], f["lado"], f"{f['valor']:.4g}", "sí" if f["valido"] else "NO"]
                 + [_fmt(f["cambio"], k) for k, _ in SALIDAS] + [_fmt(f["cambio"], "T_dis")]
                 for f in loc["filas"]]
        filas += [[f"compresor {n}", "—", "—", "sí" if j["valido"] else "NO"]
                  + [_fmt(j["cambio"], k) for k, _ in SALIDAS] + [_fmt(j["cambio"], "T_dis")]
                  for n, j in loc["compresor"].items()]
        mo = U.morris(ev)
        fm = [[f"{n} (n = {e['indicador']['n']})"] + [f"{e[k]['mu_estrella'] * (1 if k in U.ABSOLUTAS else 100):.2f} / "
                     f"{e[k]['sigma'] * (1 if k in U.ABSOLUTAS else 100):.2f}"
                     for k in ("Q_util", "indicador", "carga_max", "T_dis")]
              for n, e in mo["efectos"].items()]
        dom = max(mo["efectos"], key=lambda n: mo["efectos"][n]["indicador"]["mu_estrella"])
        resumen.append([m, dom, f"{100 * mo['efectos'][dom]['indicador']['mu_estrella']:.2f} %",
                        mo["evaluaciones"], mo["no_validos"]])
        out.append(f"### {m}\n\nSensibilidad local, cambio frente al nominal:\n\n"
                   + tabla(["Factor", "Extremo", "Valor", "Válido"]
                           + [t for _, t in SALIDAS] + ["T_dis"], filas)
                   + f"\nMorris (r = {mo['r']}, p = {mo['p']}, semilla {mo['semilla']}): "
                     "μ* / σ del efecto elemental por rango completo del factor, en % del "
                     "nominal (K para la descarga).\n\n"
                   + tabla(["Factor", "Q útil", "Indicador", "Carga (peor)", "T_dis K"], fm)
                   + ("\nPuntos no válidos (excluidos, no se relaja la tolerancia):\n\n"
                      + tabla(["Valores", "Residuo", "Mensaje"],
                              [[", ".join(f"{k} = {v:.4g}" for k, v in f["valores"].items()),
                                f"{f['residuo']:.1e}", f["mensaje"]] for f in mo["fallos"]])
                      if mo["fallos"] else ""))
    return (tabla(["Modo", "Factor dominante (indicador)", "μ* del indicador",
                   "Evaluaciones", "No válidas"], resumen) + "\n" + "\n\n".join(out))


# %%
SECCIONES = {"compresor": sec_compresor,
             "malla": sec_malla,
             "intercambiadores": sec_intercambiadores, "bandas": sec_bandas,
             "dominio": sec_dominio, "incertidumbre": sec_incertidumbre}

if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(SECCIONES)
    hoja = HojaDeCifras("docs/cifras_capitulo_10.md", "Cifras del capítulo 10",
                        "notebooks/05_cifras_capitulo_10.py")
    for nombre in pedidas:
        print(f"[{nombre}] calculando…", flush=True)
        hoja.seccion(nombre, SECCIONES[nombre]())
    print("escrito", hoja.ruta)
