"""Contraste de los intercambiadores con sus fichas (N2 de la tabla 6.5).

Cada ficha lleva su ESTATUTO (§6.3.1 y decisiones del autor del 29/09/2026):

- `validacion`: la ficha de la bateria como evaporador (26/03/2026). No
  interviene en ningun parametro: es la unica fuente independiente de N2.
- `coherencia`: fichas CONSUMIDAS por un anclaje. La de la bateria como
  condensador fijo el coeficiente del lado de aire, y la del AlfaNova 27-30H,
  el angulo de corrugacion y el producto phi_c*phi_v. Que el modelo las
  reproduzca es en buena parte por construccion, y se publica como tal.

Dentro de una ficha consumida puede quedar una magnitud que el anclaje NO uso:
la perdida de carga del refrigerante en el 27-30H (el anclaje uso la del
agua). Esa magnitud si es un contraste independiente, y se marca asi.
"""
from __future__ import annotations

from .. import data as D

K = 273.15


def _rel(a, b):
    return a / b - 1.0


def bateria_evaporador(n_segments=120) -> dict:
    from ..components.air_hx import AirCoil, AirState
    from ..props import Fluid
    df = D.air_coil()
    p = "punto_ficha_evaporador."
    f = Fluid("Ammonia")
    P = f.Psat(df.require(p + "T_evap_C") + K)
    sat = f.sat_props(P)
    aire = AirState.at(df.require(p + "aire.T_in_C") + K,
                       df.require(p + "aire.velocidad_frontal_m_s"),
                       RH=df.require(p + "aire.HR_in"))
    coil = AirCoil(f, D.air_coil_geometry(), n_segments=n_segments)
    r = coil.solve(P, sat["h_l"], df.require(p + "caudal_refrigerante_kg_h") / 3600,
                   aire, df.require(p + "aire.caudal_masico_kg_h") / 3600,
                   role="evaporator")
    Q = df.require(p + "capacidad_W")
    return {"ficha": "Frimetal CBN-21, evaporador a bomba (26/03/2026)",
            "estatuto": "validacion",
            "magnitudes": [
                {"magnitud": "Potencia", "modelo": r.Q_dot, "ficha": Q,
                 "desviacion": _rel(r.Q_dot, Q), "estatuto": "validacion"},
                {"magnitud": "U global", "modelo": r.U_mean,
                 "ficha": df.require(p + "U_global_W_m2K"),
                 "desviacion": _rel(r.U_mean, df.require(p + "U_global_W_m2K")),
                 "estatuto": "validacion"},
                {"magnitud": "T aire salida [°C]", "modelo": r.T_air_out - K,
                 "ficha": df.require(p + "aire.T_out_C"),
                 "desviacion_K": r.T_air_out - K - df.require(p + "aire.T_out_C"),
                 "estatuto": "validacion"},
                {"magnitud": "Fraccion humeda", "modelo": r.wet_fraction, "ficha": 0.0,
                 "estatuto": "validacion"},
            ]}


def bateria_condensador(n_segments=400) -> dict:
    from ..components.air_hx import AirCoil, AirState
    from ..props import Fluid
    df = D.air_coil()
    p = "punto_ficha_condensador."
    f = Fluid("Ammonia")
    P = f.Psat(df.require(p + "T_cond_C") + K)
    f.update_PQ(P, 1.0)
    aire = AirState(T=df.require(p + "aire.T_in_C") + K,
                    V_frontal=df.require(p + "aire.velocidad_frontal_m_s"))
    coil = AirCoil(f, D.air_coil_geometry(), n_segments=n_segments)
    r = coil.solve(P, f.h, df.require(p + "caudal_refrigerante_kg_h") / 3600, aire,
                   df.require(p + "aire.caudal_masico_kg_h") / 3600, role="condenser")
    Q = df.require(p + "capacidad_W")
    return {"ficha": "Frimetal CBN-21, condensador (16/03/2026)",
            "estatuto": "coherencia",
            "magnitudes": [
                {"magnitud": "Potencia", "modelo": -r.Q_dot, "ficha": Q,
                 "desviacion": _rel(-r.Q_dot, Q), "estatuto": "coherencia"},
                {"magnitud": "T aire salida [°C]", "modelo": r.T_air_out - K,
                 "ficha": df.require(p + "aire.T_out_C"),
                 "desviacion_K": r.T_air_out - K - df.require(p + "aire.T_out_C"),
                 "estatuto": "coherencia"},
            ]}


def placas_27_30H(n_cells=60) -> dict:
    from ..components.plate_hx import PlateHeatExchanger
    from ..props import Fluid
    df = D.load("placas_alfanova")
    p = "unidades.condensador_climatizacion.punto_diseno."
    f, agua = Fluid("Ammonia"), Fluid("Water")
    P = f.Psat(df.require(p + "T_cond_C") + K)
    f.update_PQ(P, 1.0)
    T_w = df.require(p + "agua_T_in_C") + K
    agua.update_PT(101325.0, T_w)
    m_w = df.require(p + "agua_caudal_m3_h") / 3600 * agua.rho
    Q = df.require(p + "Q_W")
    m_r = df.require(p + "caudal_amoniaco_kg_h") / 3600
    hx = PlateHeatExchanger(f, agua, D.plate_geometry("condensador_climatizacion"),
                            n_cells=n_cells, role="condenser")
    f.update_PQ(P, 1.0)
    r = hx.solve(P, f.h, m_r, T_w, m_w)
    dp = df.require(p + "dp_amoniaco_Pa")
    return {"ficha": "Alfa Laval AlfaNova 27-30H (23/03/2026)",
            "estatuto": "coherencia",
            "magnitudes": [
                {"magnitud": "Potencia", "modelo": -r.Q_dot, "ficha": Q,
                 "desviacion": _rel(-r.Q_dot, Q), "estatuto": "coherencia"},
                {"magnitud": "T agua salida [°C]", "modelo": r.T_sec_out - K,
                 "ficha": df.require(p + "agua_T_out_C"),
                 "desviacion_K": r.T_sec_out - K - df.require(p + "agua_T_out_C"),
                 "estatuto": "coherencia"},
                # El anclaje uso la perdida de carga del AGUA; la del
                # refrigerante no intervino: contraste independiente. Las fichas
                # de fabricante dan la perdida por FRICCION (y de puertos), sin
                # la columna estatica; se compara por tanto la friccional del
                # modelo, que ademas no incluye los puertos.
                {"magnitud": "Δp refrigerante por fricción [Pa]",
                 "modelo": r.dP_parts["friccional"], "ficha": dp,
                 "desviacion": _rel(r.dP_parts["friccional"], dp),
                 "estatuto": "validacion", "partes_modelo": dict(r.dP_parts)},
            ]}


def todos() -> list:
    return [bateria_evaporador(), bateria_condensador(), placas_27_30H()]
