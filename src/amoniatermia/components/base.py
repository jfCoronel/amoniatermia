"""Interfaz comun de componente. Apartado 9.14.

El diseno orientado a objetos con una clase por tipo de componente y una
interfaz comun de resolucion es lo que permite que la TOPOLOGIA cambie entre
los cinco modos de operacion sin alterar los objetos de componente
(requisito del apartado 9.3).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Port:
    """Estado termodinamico en un punto del circuito. SI estricto."""
    P: float          # Pa
    h: float          # J/kg
    m_dot: float      # kg/s

    def copy(self, **kw):
        d = dict(P=self.P, h=self.h, m_dot=self.m_dot)
        d.update(kw)
        return Port(**d)


class Component(ABC):
    """Contrato comun de todos los componentes."""

    name: str = "component"

    @abstractmethod
    def solve(self, *args, **kwargs):
        """Resuelve el componente y devuelve un objeto de resultado."""

    def charge(self) -> dict:
        """Inventario de refrigerante contenido (apartado 9.9).

        Devuelve un dict {nombre_correlacion: masa_kg}. Los componentes que
        no contengan refrigerante devuelven ceros.
        """
        return {}
