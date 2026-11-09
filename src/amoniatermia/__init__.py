"""Modelo de simulacion de bomba de calor reversible de R-717 de baja carga.

Capitulo 9 de la tesis. Unidades internas: SI estricto (Pa, K, J/kg, kg/s, m).
La conversion a unidades de ingenieria se realiza SOLO en la frontera de E/S.
"""
from .props import Fluid, PropertyProvenance
from .geometry import PlateGeometry, CompressorGeometry, FinnedCoilGeometry
from .correlations import ExtrapolationLog
from .components.compressor import SemiEmpiricalCompressor, CompressorParams
from .components.plate_hx import PlateHeatExchanger
from .components.air_hx import AirCoil, AirState
from .components.expansion_valve import ExpansionValve
from .circuit import (APROXIMACION_ACS_K, Boundary, Circuit,
                      CircuitSolution, CONSIGNA_ACS_K,
                      CONSIGNA_DEPOSITO_ACS_K, ModeSpec, MODES,
                      RETORNO_ACS_K, Setpoints, WaterStream)
from . import data
from . import psychrometrics
from . import validation
from . import indicators
from . import campaign
from . import envelope
from . import maps
from . import reporting

__version__ = "0.1.0"
__all__ = ["Fluid", "PropertyProvenance", "PlateGeometry",
           "CompressorGeometry", "FinnedCoilGeometry",
           "SemiEmpiricalCompressor", "CompressorParams",
           "PlateHeatExchanger", "AirCoil", "AirState", "ExpansionValve",
           "ExtrapolationLog", "data", "psychrometrics", "validation", "indicators", "campaign",
           "envelope", "maps", "reporting",
           "Circuit", "CircuitSolution", "Boundary", "Setpoints",
           "WaterStream", "ModeSpec", "MODES", "CONSIGNA_ACS_K",
           "CONSIGNA_DEPOSITO_ACS_K", "APROXIMACION_ACS_K",
           "RETORNO_ACS_K"]
