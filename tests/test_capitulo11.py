"""Contratos del capítulo 11: presupuesto de RS-5, margen de H6 y banda de C11-8.

Decisiones del autor del 01/10/2026: presupuesto ÚNICO de RS-5 sobre el
equilibrio de refrigeración (texto del cap. 1 y del §8.5.2); H4 en los puntos de
diseño; H6 con cotas propias; penalización entre modos frente a la banda de la
diferencia.
"""
import pytest

from amoniatermia import AirState, Boundary, Setpoints, WaterStream
from amoniatermia import campaign as C
from amoniatermia import indicators as I
from amoniatermia import uncertainty as U
from amoniatermia.circuit import MODES

K = 273.15


def test_el_presupuesto_unico_es_el_del_8_5_2():
    """9.49 kW en el equilibrio del §9.7.8 → 474 g. Se recalcula, no se escribe.

    Hasta el 15/10/2026 eran 9.52 kW y 476 g: el cambio es el del compresor a polinomios de
    UNE-EN 12900 (docs/DECISIONES_2026_10_15.md), y así figura en la V21 de la tesis."""
    p = I.presupuesto_RS5()
    assert p["Q_ref_W"] == pytest.approx(9488.0, rel=2e-3)
    assert 1e3 * p["m_max_kg"] == pytest.approx(474.0, abs=1.0)
    assert p["equilibrio"]["T_evap_K"] == 275.15


def test_el_mejor_rendimiento_del_catalogo():
    e = I.eta_is_catalogo()
    assert e["n"] == 46
    assert e["max"] == pytest.approx(0.732, abs=0.002)
    assert e["min"] < e["mediana"] < e["max"]


@pytest.fixture(scope="module")
def m2():
    bc = Boundary(air=AirState(T=35 + K, V_frontal=3.30), m_dot_air=None,
                  clima=WaterStream(12 + K, 0.45), T_amb=35 + K)
    c, _ = C.build_circuit()
    return c.solve("M-2", bc, Setpoints(superheat=5.0, subcooling=2.0))


def test_la_fraccion_usa_el_presupuesto_unico(m2):
    p = I.presupuesto_RS5()
    assert I.fraccion_RS5(m2, p) == pytest.approx(m2.charge_sistema["_max"] / p["m_max_kg"])
    # Con el presupuesto único es mayor que con la capacidad del propio modo,
    # porque el sistema completo de M-2 entrega más de 9.52 kW (discrepancia
    # declarada en `presupuesto_RS5`).
    assert I.fraccion_RS5(m2, p) > m2.charge_sistema["_RS5_peor_caso"]


def test_cotas_de_H6(m2):
    """La termodinámica es la exergía destruida en el compresor con su motor y
    acota a la técnica; con el η_is del punto como referencia, la técnica es 0."""
    eta = I.eta_is_catalogo()["max"]
    mg = I.margen_compresor(m2, MODES["M-2"], eta)
    x = I.exergy(m2, MODES["M-2"])
    E = x.E_D["compresor"] + x.E_D["compresor_electromecanico"]
    assert mg["termodinamica"]["dW_el_W"] == pytest.approx(E)
    assert 0.0 <= mg["tecnica"]["dW_el_W"] < mg["termodinamica"]["dW_el_W"]
    cero = I.margen_compresor(m2, MODES["M-2"], mg["eta_is"])
    assert cero["tecnica"]["dW_el_W"] == pytest.approx(0.0, abs=1e-9)


def test_las_perturbaciones_de_C11_8_son_las_de_C10_7_y_C10_8():
    from amoniatermia.validation.bands import ALTERNATIVAS
    p = U.perturbaciones()
    corr = [x for x in p if x[0] == "correlacion"]
    par = [x for x in p if x[0] == "parametro"]
    assert len(corr) == len(ALTERNATIVAS)
    assert {x[1] for x in par} == set(U.FACTORES) | {"compresor"}
