"""Dispositivo de expansion y lazo de recalentamiento. Apartado 9.8."""
from __future__ import annotations

import numpy as np

from .base import Component
from ..props import Fluid


class ExpansionValve(Component):
    """Valvula de expansion electronica, ecuacion 9-31.

        m_dot = Cd A_ef sqrt(2 rho_in (Pk - P0))

    En la resolucion estacionaria A_ef NO es un dato sino una incognita,
    determinada por la condicion de recalentamiento de consigna (residuo R2 de la tabla 9.4),
    que constituye el residuo R2 del lazo externo (tabla 9.4).
    """

    name = "expansion_valve"

    def __init__(self, fluid: Fluid, Cd: float = 0.65):
        # Sin area maxima (decision del autor, 29/09/2026). El valor por
        # defecto de 5e-6 m2 que se usaba como limite no procedia de ningun
        # dato: la valvula no esta seleccionada (§7.6.4). El modelo publica el
        # area efectiva que necesita cada punto, que es el dato para elegirla.
        self.fluid = fluid
        self.Cd = Cd

    def mass_flow(self, A_ef: float, P_in: float, h_in: float,
                  P_out: float) -> float:
        if P_in <= P_out:
            return 0.0
        self.fluid.update_PH(P_in, h_in)
        rho_in = self.fluid.rho
        return self.Cd * A_ef * np.sqrt(2.0 * rho_in * (P_in - P_out))

    def area_for_flow(self, m_dot: float, P_in: float, h_in: float,
                      P_out: float) -> float:
        """Area efectiva requerida para un caudal dado. Util para inicializar
        el lazo externo."""
        self.fluid.update_PH(P_in, h_in)
        rho_in = self.fluid.rho
        denom = self.Cd * np.sqrt(2.0 * rho_in * max(P_in - P_out, 1.0))
        return m_dot / denom

    def solve(self, A_ef, P_in, h_in, P_out):
        """Expansion isoentalpica (hipotesis M3)."""
        m_dot = self.mass_flow(A_ef, P_in, h_in, P_out)
        return {"m_dot": m_dot, "P_out": P_out, "h_out": h_in}
