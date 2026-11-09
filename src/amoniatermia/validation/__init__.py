"""Verificacion y validacion. Capitulo 6, §6.7, tabla 6.5.

`metrics` implementa las cuatro metricas del §6.7.4. `plan` da acceso a los
criterios de aceptacion de la tabla 6.5, inventaria la verificacion del §6.7.1 y
declara el estatuto de cada fuente.

Los casos de validacion del cap. 10 todavia no existen. El modulo se escribe
antes que ellos a proposito: ver la nota de cabecera de `plan`.
"""
from .metrics import Metrics, compare, parity_series
from .plan import (ESTRICTO, Fuente, ItemVerificacion, NIVELES, Nivel,
                   adopted_tolerance, divergencias_con_el_capitulo, levels,
                   metrics_required, missing_tests, parity_band, report,
                   sources, sources_for, suggested, threshold,
                   verification_items)

__all__ = ["Metrics", "compare", "parity_series", "ESTRICTO", "Fuente",
           "ItemVerificacion", "NIVELES", "Nivel", "adopted_tolerance",
           "divergencias_con_el_capitulo", "levels", "metrics_required",
           "missing_tests", "parity_band", "report", "sources", "sources_for",
           "suggested", "threshold", "verification_items"]
