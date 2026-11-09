"""Envolvente operativa de un punto resuelto. §7.6.4; hipotesis H2 y H3.

Que un punto converja y sea VALIDO (cierra balances, genera entropia) no dice
que el equipo pueda operar en el: eso lo decide la envolvente del compresor y
de la instalacion. H2 exige «funcionamiento estable en el punto de equilibrio
estacionario de todos los modos», y H3 que la consigna de ACS se alcance «sin
superar la presion de condensacion maxima admisible del compresor».

Cada limite se evalua con uno de tres estados, y el tercero no es una
formalidad:

- `cumple` / `incumple`: el limite existe y el punto lo respeta o no;
- `sin_dato`: el limite no existe en los datos. Se dice, no se supone: un punto
  con un limite `sin_dato` no puede declararse dentro de la envolvente, solo
  «dentro de lo comprobable».

Ademas se marca si el punto cae fuera del dominio del modelo de compresor. No es
un limite fisico sino de SOPORTE del modelo. Con los polinomios de UNE-EN 12900
(15/10/2026) el dominio es el de los datos del fabricante, que cubren su
envolvente: dentro de ella, la admisibilidad la deciden solo los limites del
compresor real (`dominio_compresor`).

Unidades: SI estricto.
"""
from __future__ import annotations

import csv
from functools import lru_cache

from . import data as D
from .psychrometrics import P_ATM


def _estado(valor: float, limite, mayor_es_peor: bool = True) -> str:
    if limite is None:
        return "sin_dato"
    ok = valor <= limite if mayor_es_peor else valor >= limite
    return "cumple" if ok else "incumple"


@lru_cache(maxsize=8)
def dominio_identificacion(fichero: str = "compresor_bock_f2") -> dict:
    """Rango de T0 y Tc de los puntos de catalogo del compresor [K]."""
    path = D.data_dir() / f"{fichero}_catalogo.csv"
    with path.open(encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    T0 = [float(r["T0_C"]) + 273.15 for r in filas]
    Tc = [float(r["Tc_C"]) + 273.15 for r in filas]
    return {"T0": (min(T0), max(T0)), "Tc": (min(Tc), max(Tc))}


#: Recalentamiento con que se ha comprobado la regla de conservación de los rendimientos del
#: compresor por polinomios: el catálogo (1 K) y los puntos de VAP a 1, 5 y 10 K.
RECALENTAMIENTO_COMPROBADO_K = (1.0, 10.0)


def dominio_compresor(circuit) -> dict:
    """Dominio de validez del modelo de compresor del circuito.

    - `en12900`: zonas del diagrama que cubren los datos (sin límites y refrigeración
      suplementaria), velocidades de los nudos y recalentamiento comprobado.
    - `semiempirico`: el rectángulo del catálogo de identificación (hasta el 15/10/2026)."""
    comp = getattr(circuit, "compressor", None)
    fichero = getattr(circuit, "compresor_fichero", "compresor_bock_f2")
    proc = getattr(comp, "procedencia", {}) or {}
    if proc.get("modelo") == "en12900":
        return {"modelo": "en12900", "zonas": ("sin_limites", "refrigeracion_suplementaria"),
                "rpm": (comp.rpm_min, comp.rpm_max), "rpm_actual": comp.rpm,
                "recalentamiento_K": RECALENTAMIENTO_COMPROBADO_K}
    return {"modelo": "semiempirico", **dominio_identificacion(fichero)}


#: Incertidumbre de lectura del diagrama digitalizado [K].
TOL_DIAGRAMA_K = 0.5


def _dentro(poligono, x, y, tol=0.0) -> bool:
    """Punto en poligono (regla par-impar), o a menos de `tol` de su borde."""
    n, dentro = len(poligono), False
    d_min = float("inf")
    for i in range(n):
        (x1, y1), (x2, y2) = poligono[i], poligono[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                dentro = not dentro
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        d_min = min(d_min, ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5)
    return dentro or d_min <= tol


def zona_diagrama(T_evap: float, T_cond: float, tol_K: float = TOL_DIAGRAMA_K,
                  fichero: str = "compresor_bock_f2") -> str:
    """Zona del diagrama de limites del fabricante: `sin_limites`,
    `refrigeracion_suplementaria` o `fuera`. Entradas en K. Un punto a menos
    de `tol_K` del borde de una zona cuenta dentro de ella (lectura ±0.5 K)."""
    diag = D.load(fichero).require("limites.diagrama_aplicacion")
    x, y = T_evap - 273.15, T_cond - 273.15
    if _dentro(diag["sin_limites_C"], x, y, tol_K):
        return "sin_limites"
    if diag.get("envolvente_C") and _dentro(diag["envolvente_C"], x, y, tol_K):
        return "refrigeracion_suplementaria"
    return "fuera"


def evaluate(circuit, sol) -> dict:
    """Envolvente del punto `sol`, resuelto con `circuit`."""
    fichero = getattr(circuit, "compresor_fichero", "compresor_bock_f2")
    df = D.load(fichero)
    offset = P_ATM if df.require("limites.presiones_manometricas") else 0.0
    P0, Pk = sol.unknowns["P0"], sol.unknowns["Pk"]
    T_dis_max = df.optional("limites.T_descarga_max_K")

    limites = {
        "presion_alta": {
            "valor": Pk, "limite": df.require("operacion.p_max_alta_Pa") + offset,
            "unidad": "Pa abs."},
        "presion_baja": {
            "valor": P0, "limite": df.require("operacion.p_max_baja_Pa") + offset,
            "unidad": "Pa abs."},
        "temperatura_descarga": {
            "valor": sol.T_dis, "limite": T_dis_max, "unidad": "K"},
    }
    for v in limites.values():
        v["estado"] = _estado(v["valor"], v["limite"])

    # Diagrama de aplicacion del fabricante. Decision del autor (29/09/2026):
    # solo la zona sin limites es admisible; la refrigeracion suplementaria
    # exige una tapa de cilindro refrigerada que la maquina no lleva.
    zona = zona_diagrama(sol.T_evap, sol.T_cond, fichero=fichero)
    limites["diagrama_aplicacion"] = {
        "valor": zona, "limite": "sin_limites", "unidad": "zona",
        "estado": "cumple" if zona == "sin_limites" else "incumple"}

    # RS-17: el refrigerante no baja de saturacion dentro del desrecalentador
    # en los modos que lo dedican al ACS. Es criterio de dimensionado (§9.6.7)
    # y metrica de H3.
    from .circuit import ACS
    spec = circuit.spec(sol.mode)
    if spec.secondary.get(ACS) == "acs" and ACS in sol.components:
        r = sol.components[ACS]
        f = circuit.fluid
        sat = f.sat_props(Pk)
        if r.h_ref_out >= sat["h_v"]:
            f.update_PH(Pk, r.h_ref_out)
            margen = f.T - sat["Tsat"]
        else:
            margen = (r.h_ref_out - sat["h_v"]) / sat["cp_v"]   # prolongado
        limites["margen_no_condensacion"] = {
            "valor": margen, "limite": 0.0, "unidad": "K",
            "estado": _estado(margen, 0.0, mayor_es_peor=False)}

    dom = dominio_compresor(circuit)
    if dom["modelo"] == "en12900":
        # Polinomios de UNE-EN 12900 (15/10/2026): el dominio es el de los datos, las zonas
        # del diagrama que cubre la rejilla de VAP, la velocidad de los nudos y el
        # recalentamiento de 1 a 10 K con que se comprobó la regla de conservación.
        sh = getattr(sol, "superheat", None)
        fuera = (zona not in dom["zonas"]
                 or not dom["rpm"][0] - 1e-6 <= dom["rpm_actual"] <= dom["rpm"][1] + 1e-6
                 or (sh is not None and not dom["recalentamiento_K"][0] - 1e-6 <= sh
                     <= dom["recalentamiento_K"][1] + 1e-6))
    else:
        fuera = not (dom["T0"][0] <= sol.T_evap <= dom["T0"][1]
                     and dom["Tc"][0] <= sol.T_cond <= dom["Tc"][1])
    estados = [v["estado"] for v in limites.values()]
    return {
        "limites": limites,
        "incumple": [k for k, v in limites.items() if v["estado"] == "incumple"],
        "sin_dato": [k for k, v in limites.items() if v["estado"] == "sin_dato"],
        "dentro_de_lo_comprobable": "incumple" not in estados,
        "completa": "sin_dato" not in estados,
        "fuera_del_dominio_del_compresor": fuera,
        # No es un limite: la valvula no esta seleccionada (§7.6.4) y este es el
        # dato para seleccionarla. Producto Cd*A_ef con Cd = circuit.valve.Cd.
        "area_efectiva_valvula_m2": sol.unknowns.get("A_ef"),
        "Cd_valvula": circuit.valve.Cd,
        "dominio_compresor": dom,
    }
