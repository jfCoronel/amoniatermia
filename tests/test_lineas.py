"""Líneas de refrigerante (C11-1): geometría adoptada, estado por modo y carga.

Decisión del autor 3b (29/09/2026): dimensiones adoptadas por Claude para un
módulo compacto, declaradas. Sin receptor (§7.4.2, RS-5). Adiabáticas y a
presión uniforme (M8): no cambian la solución del ciclo.
"""
import math

import pytest

from amoniatermia import AirState, Boundary, Setpoints, WaterStream
from amoniatermia import campaign as C
from amoniatermia import data as D
from amoniatermia.components.line import LineGeometry, RefrigerantLine, reinventariar
from amoniatermia.correlations import get
from amoniatermia.props import Fluid

K = 273.15
M_AIRE = None     # 7600 m3/h; el caudal masico lo deduce Boundary


def test_churchill_da_16_sobre_Re_en_laminar_y_blasius_en_turbulento_liso():
    f = get("friction", "churchill_tubo")
    assert f(500.0) == pytest.approx(16.0 / 500.0, rel=1e-3)
    assert f(2.0e4) == pytest.approx(0.079 * 2.0e4 ** -0.25, rel=0.05)


def test_la_geometria_es_adoptada_y_esta_declarada():
    df = D.load("lineas_refrigerante")
    assert "adoptado" in df.require("procedencia")
    lineas = D.refrigerant_lines()
    assert all(g.D_i in (0.008, 0.016) for g in lineas.values())
    # Las claves son pares ordenados: la misma línea en los dos sentidos.
    assert all(par == "--".join(sorted(par.split("--"))) for par in lineas)


def test_una_linea_de_liquido_contiene_rho_por_volumen_en_todas_las_correlaciones():
    f = Fluid("Ammonia")
    P = f.Psat(43 + K)
    f.update_PT(P, 41 + K)
    geo = LineGeometry("prueba", 1.0, 0.008, 1.5e-6)
    r = RefrigerantLine(f, geo).solve(P, f.h, 0.0088)
    f.update_PT(P, 41 + K)
    assert r.regimen == "liquido"
    assert r.charge["_min"] == r.charge["_max"] == pytest.approx(f.rho * math.pi * 0.004 ** 2)
    assert r.Q_dot == 0.0 and r.P_out == P


def test_en_bifasico_la_carga_es_una_banda():
    f = Fluid("Ammonia")
    P = f.Psat(2 + K)
    sat = f.sat_props(P)
    r = RefrigerantLine(f, LineGeometry("prueba", 1.0, 0.008, 1.5e-6)).solve(
        P, sat["h_l"] + 0.15 * sat["h_lv"], 0.0088)
    assert r.regimen == "bifasico"
    assert r.charge["_max"] > 2.0 * r.charge["_min"]
    assert r.dP_ref > 0.0 and r.dT_sat_equivalente > 0.0


@pytest.fixture(scope="module")
def m1():
    bc = Boundary(air=AirState(T=35 + K, V_frontal=3.30), m_dot_air=M_AIRE,
                  clima=WaterStream(12 + K, 0.45), acs=WaterStream(35 + K), T_amb=35 + K)
    sp = Setpoints(superheat=5.0, subcooling=2.0, T_acs=67 + K)
    c, _ = C.build_circuit()
    return c, c.solve("M-1", bc, sp)


def test_las_lineas_activas_de_M1_siguen_el_recorrido_del_modo(m1):
    _, s = m1
    assert set(s.lines) == {"descarga--desrecalentador", "bateria--desrecalentador",
                            "bateria--valvula", "placas_clima--valvula",
                            "aspiracion--placas_clima"}
    assert s.lines["bateria--valvula"].regimen == "liquido"
    assert s.lines["placas_clima--valvula"].regimen == "bifasico"
    assert s.lines["aspiracion--placas_clima"].regimen == "vapor"


def test_las_lineas_no_cambian_el_ciclo(m1):
    """Mismo punto con y sin líneas: la solución es la misma."""
    c, s = m1
    c0, _ = C.build_circuit(con_lineas=False)
    s0 = c0.solve("M-1", s.boundary, s.setpoints)
    assert s0.Q_evap == pytest.approx(s.Q_evap, rel=1e-9)
    assert s0.charge["_max"] == pytest.approx(s.charge["_max"], rel=1e-9)
    assert not s0.lines and not s0.charge_sistema


def test_la_carga_del_sistema_suma_componentes_y_lineas(m1):
    _, s = m1
    lineas = sum(r.charge["_max"] for r in s.lines.values())
    # El máximo del sistema es el de la PEOR correlación sumada en todo, no la
    # suma de máximos; con las líneas en la misma correlación coinciden aquí.
    assert s.charge_sistema["_max"] == pytest.approx(s.charge["_max"] + lineas, rel=0.02)
    assert s.charge_sistema["_max"] > s.charge["_max"]


def test_H4_en_M1_con_lineas(m1):
    """HALLAZGO (30/09/2026): con las líneas adoptadas, el peor caso de M-1
    supera el presupuesto de RS-5, que solo con componentes se cumplía."""
    _, s = m1
    assert s.charge["_RS5_peor_caso"] < 1.0
    assert s.charge_sistema["_RS5_peor_caso"] > 1.0


def test_reinventariar_sin_resolver(m1):
    """La sensibilidad a la geometría no exige resolver: el estado es el mismo."""
    c, s = m1
    geo = D.refrigerant_lines()["bateria--valvula"]
    fina = LineGeometry(geo.nombre, geo.longitud, 0.006, geo.rugosidad)
    r = reinventariar(s, {"bateria--valvula": fina}, c.lines["bateria--valvula"].fluid)
    assert r["bateria--valvula"].charge["_max"] == pytest.approx(
        s.lines["bateria--valvula"].charge["_max"] * (6 / 8) ** 2, rel=1e-9)
    assert r["aspiracion--placas_clima"] is s.lines["aspiracion--placas_clima"]


def test_una_linea_que_el_modo_recorre_y_no_esta_declarada_falla(m1):
    _, s = m1
    c, _ = C.build_circuit()
    c.lines.pop("bateria--valvula")
    with pytest.raises(D.MissingData):
        c.solve("M-1", s.boundary, s.setpoints, x0=dict(s.unknowns))
