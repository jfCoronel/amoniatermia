"""Linea de refrigerante (C11-1). Capitulo 11; H4.

POR QUE
-------
El capitulo 7 (§7.4.2, §7.9) y el §4.8 lo dicen igual: la variable que gobierna
la carga es el anegado del circuito, «propiedad del circuito —receptor y
lineas—, no del intercambiador», y «un submodelo de lineas con volumen propio
pasa de refinamiento a requisito para contrastar H4». No hay receptor (el
§7.4.2 lo suprime por RS-5), de modo que lo que falta son las lineas.

CONVENIO
--------
Adiabatica y a presion uniforme, como los intercambiadores (M8): la perdida de
carga se calcula, se publica con su salto de saturacion equivalente y no se
resta. Con ese convenio la linea NO cambia la solucion del ciclo: el estado de
salida es el de entrada. Lo que aporta es su MASA, con la misma banda de
fraccion de huecos que el resto del inventario (§9.9), y su perdida de carga.

Geometria adoptada, no de diseno: `data/lineas_refrigerante.yaml` (decision 3b
del autor, 29/09/2026).

Interfaz comun (CLAUDE.md): potencia intercambiada (0), estado de salida,
perdida de carga y masa contenida.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..correlations import get
from ..correlations.voidfraction import CORRELACIONES_HUECOS, charge_range
from .base import Component


@dataclass(frozen=True)
class LineGeometry:
    nombre: str
    longitud: float        # m
    D_i: float             # m
    rugosidad: float       # m

    @property
    def area(self) -> float:
        return math.pi * self.D_i ** 2 / 4.0

    @property
    def volumen(self) -> float:
        return self.area * self.longitud


@dataclass
class LineResult:
    nombre: str
    Q_dot: float                  # W; adiabatica
    P_out: float                  # Pa; presion uniforme (M8)
    h_ref_out: float              # J/kg
    dP_ref: float                 # Pa, comprobacion a posteriori
    dT_sat_equivalente: float     # K
    regimen: str                  # liquido | bifasico | vapor
    titulo: float                 # -; fuera de (0, 1) en monofasico
    velocidad: float              # m/s (homogenea en bifasico)
    volumen: float                # m3
    charge: dict = field(default_factory=dict)   # {correlacion: kg}, _min, _max


class RefrigerantLine(Component):
    """Tramo de tuberia entre dos componentes."""

    name = "linea"

    def __init__(self, fluid, geom: LineGeometry,
                 friccion: str = "churchill_tubo",
                 multiplicador: str = "lockhart_martinelli_chisholm",
                 void_fraction_names=CORRELACIONES_HUECOS):
        self.fluid = fluid
        self.geom = geom
        self.friccion = friccion
        self.multiplicador = multiplicador
        self.void_fraction_names = tuple(void_fraction_names)

    def solve(self, P: float, h: float, m_dot: float) -> LineResult:
        f, g = self.fluid, self.geom
        sat = f.sat_props(P)
        x = (h - sat["h_l"]) / sat["h_lv"]
        G = m_dot / g.area
        f_single = get("friction", self.friccion)
        eps = g.rugosidad / g.D_i
        names = self.void_fraction_names

        if 0.0 < x < 1.0:
            regimen = "bifasico"
            rr = charge_range(x, sat, G, g.D_i, names=names)
            masa = {n: rr[n]["rho_mean"] * g.volumen for n in names}
            dP, _ = get("twophase_multiplier", self.multiplicador)(
                x, G, sat, g.D_i, g.longitud,
                lambda Re, **kw: f_single(Re, rugosidad_relativa=eps))
            v_h = (1.0 - x) / sat["rho_l"] + x / sat["rho_v"]
            velocidad = G * v_h
        else:
            regimen = "liquido" if x <= 0.0 else "vapor"
            f.update_PH(P, h)
            rho, mu = f.rho, f.mu
            masa = {n: rho * g.volumen for n in names}
            Re = G * g.D_i / mu
            dP = f_single(Re, rugosidad_relativa=eps) * (4.0 * g.longitud / g.D_i) \
                * G ** 2 / (2.0 * rho)
            velocidad = G / rho

        # Salto de saturacion equivalente: el mismo indicador que las placas.
        dT = sat["Tsat"] - f.Tsat(max(P - dP, 1.0))
        masa["_min"], masa["_max"] = min(masa[n] for n in names), max(masa[n] for n in names)
        return LineResult(nombre=g.nombre, Q_dot=0.0, P_out=P, h_ref_out=h, dP_ref=dP,
                          dT_sat_equivalente=dT, regimen=regimen, titulo=x,
                          velocidad=velocidad, volumen=g.volumen, charge=masa)


def reinventariar(sol, geometrias: dict, fluid, **kw) -> dict:
    """Lineas de una solucion ya resuelta con OTRA geometria {par: LineGeometry}.

    Como las lineas no cambian la solucion del ciclo (adiabaticas y a presion
    uniforme), la sensibilidad a su geometria no exige resolver de nuevo: basta
    con el estado que lleva cada linea activa, que es el de `sol.lines`. Los
    pares que falten en `geometrias` conservan la suya."""
    out = {}
    for par, r in sol.lines.items():
        geo = geometrias.get(par)
        if geo is None:
            out[par] = r
            continue
        out[par] = RefrigerantLine(fluid, geo, **kw).solve(r.P_out, r.h_ref_out, sol.m_dot)
    return out
