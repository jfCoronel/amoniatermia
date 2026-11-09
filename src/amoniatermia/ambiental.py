"""TEWI y LCCP (cap. 13, H7; §6.10.1).

TEWI (UNE-EN 378-1, anexo B):

    TEWI = GWP·L·n·m + GWP·m·(1 − α) + n·E·β

LCCP (guía del IIR, 2016), con la carga m, la tasa de fugas L, la vida n, la
recuperación α, el consumo anual E y el factor de emisión β:

    directas   = m·(L·n + (1 − α))·GWP
    indirectas = n·E·β + Σ masa_i·MM_i + m·(1 + L·n)·RFM

donde MM_i es el factor de emisión de fabricación de cada material y RFM el de la
fabricación del refrigerante. Las reglas del §6.10: el consumo anual viene del
capítulo 12, no de una potencia por unas horas, y la carga es el PEOR caso de la
banda de fracción de huecos, con líneas.

Todos los parámetros se leen de `data/ambiental.yaml`; un null detiene el cálculo.
SI estricto en el interior; kg CO2e y kWh solo en la frontera de este módulo,
que es donde se publican.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import data as D


@dataclass(frozen=True)
class Escenario:
    gwp: str = "reglamento"     # "reglamento" (2024/573, caso base) o "ar6" (sensibilidad)
    fugas: str = "base"         # "base", "minimo" o "maximo"
    recuperacion: str = "base"
    vida: str = "base"


def _p():
    return D.load("ambiental")


def gwp(fluido: str, conjunto: str = "reglamento") -> float:
    return float(_p().require(f"gwp_{conjunto}.{fluido}"))


def tewi(fluido: str, carga_kg: float, E_anual_kWh: float, beta_kgCO2_kWh: float,
         esc: Escenario = Escenario()) -> dict:
    """TEWI [kg CO2e] y su desglose."""
    p = _p()
    L = float(p.require(f"fugas_anuales.{esc.fugas}"))
    a = float(p.require(f"recuperacion_fin_de_vida.{esc.recuperacion}"))
    n = float(p.require(f"vida_util_anos.{esc.vida}"))
    G = gwp(fluido, esc.gwp)
    fugas = G * L * n * carga_kg
    fin_vida = G * carga_kg * (1.0 - a)
    indirecto = n * E_anual_kWh * beta_kgCO2_kWh
    return {"TEWI": fugas + fin_vida + indirecto, "directo_fugas": fugas,
            "directo_fin_de_vida": fin_vida, "indirecto": indirecto,
            "L": L, "alpha": a, "n": n, "GWP": G, "beta": beta_kgCO2_kWh}


def tewi_rd552(fluido: str, carga_kg: float, E_anual_kWh: float, beta_kgCO2_kWh: float,
               vida: str = "base") -> dict:
    """Caso reglamentario español (RD 552/2019, IF-02, apéndice 2): fugas
    L = 0,4·m^(2/3) kg/año y recuperación 0,6 de «línea blanca». Se publica
    aparte, no como caso base (decisión 4 del 05/10/2026): con cargas por debajo
    de 1 kg da fugas del 40 al 55 % anual."""
    p = _p()
    n = float(p.require(f"vida_util_anos.{vida}"))
    L_kg = float(p.require("rd_552_2019.coef_fugas_kg_ano")) * carga_kg ** float(
        p.require("rd_552_2019.exponente_fugas"))
    a = float(p.require("rd_552_2019.recuperacion"))
    G = gwp(fluido)
    fugas, fin_vida, ind = G * L_kg * n, G * carga_kg * (1.0 - a), n * E_anual_kWh * beta_kgCO2_kWh
    return {"TEWI": fugas + fin_vida + ind, "directo_fugas": fugas, "directo_fin_de_vida": fin_vida,
            "indirecto": ind, "L_kg_ano": L_kg, "alpha": a, "n": n, "GWP": G}


def lccp(fluido: str, carga_kg: float, E_anual_kWh: float, beta_kgCO2_kWh: float,
         masas_kg: dict, esc: Escenario = Escenario()) -> dict:
    """LCCP [kg CO2e]. `masas_kg`: {material: kg} de los componentes de la máquina."""
    p = _p()
    t = tewi(fluido, carga_kg, E_anual_kWh, beta_kgCO2_kWh, esc)
    RFM = float(p.require(f"lccp.fabricacion_refrigerante_kgCO2e_kg.{fluido}"))
    mat = sum(m * float(p.require(f"lccp.materiales_kgCO2e_kg.{k}")) for k, m in masas_kg.items())
    ref = carga_kg * (1.0 + t["L"] * t["n"]) * RFM
    directo = t["directo_fugas"] + t["directo_fin_de_vida"]
    indirecto = t["indirecto"] + mat + ref
    return {"LCCP": directo + indirecto, "directo": directo, "indirecto_energia": t["indirecto"],
            "indirecto_materiales": mat, "indirecto_refrigerante": ref, **{k: t[k] for k in
            ("L", "alpha", "n", "GWP", "beta")}}
