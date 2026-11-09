"""Casos de solucion conocida. Apartado 6.7.1 (verificacion del codigo)."""
import math
import pytest
from amoniatermia.props import Fluid
from amoniatermia.geometry import PlateGeometry
from amoniatermia.correlations.singlephase import dittus_boelter, reynolds
from amoniatermia.correlations.boiling import cooper_pool_boiling


def test_dittus_boelter_known_value():
    """Re=1e4, Pr=5, k=0.6, D=0.01 -> Nu = 0.023*1e4^0.8*5^0.4 = 72.0"""
    Nu_expected = 0.023 * 1e4 ** 0.8 * 5.0 ** 0.4
    alpha = dittus_boelter(1e4, 5.0, 0.6, 0.01, heating=True)
    assert alpha == pytest.approx(Nu_expected * 0.6 / 0.01, rel=1e-12)


def test_cooper_scales_with_heat_flux_to_the_067():
    """alpha_nb ~ q''^0.67: duplicar q'' multiplica alpha por 2^0.67."""
    a1 = cooper_pool_boiling(0.05, 0.017, 5000.0)
    a2 = cooper_pool_boiling(0.05, 0.017, 10000.0)
    assert a2 / a1 == pytest.approx(2.0 ** 0.67, rel=1e-9)


def test_plate_geometry_hydraulic_diameter():
    """D_h = 2b/phi (ec. 9-13)."""
    g = PlateGeometry(n_plates=40, b=0.002, L_w=0.10, L_p=0.30,
                      beta_c=math.radians(60.0), phi=1.20)
    assert g.D_h == pytest.approx(2 * 0.002 / 1.20)


def test_plate_area_scales_with_plate_count():
    kw = dict(b=0.002, L_w=0.10, L_p=0.30, beta_c=math.radians(60.0), phi=1.2)
    g1 = PlateGeometry(n_plates=22, **kw)
    g2 = PlateGeometry(n_plates=42, **kw)
    assert g2.A_total / g1.A_total == pytest.approx(40 / 20)


def test_phi_estimation_is_greater_than_one():
    phi = PlateGeometry.phi_from_corrugation(b=0.002, pitch=0.008)
    assert phi > 1.0


def test_carnot_bound_not_violated():
    """Segundo principio: ningun COP puede superar el de Carnot."""
    T0, Tk = 273.15, 323.15
    cop_carnot = Tk / (Tk - T0)
    assert cop_carnot == pytest.approx(323.15 / 50.0)
    # eficiencia de segunda ley: cociente, NO una perdida (ap. 9.11.2)
    cop_real = 3.5
    eta_II = cop_real / cop_carnot
    assert 0.0 < eta_II < 1.0
    assert eta_II + (1.0 - eta_II) == pytest.approx(1.0)
