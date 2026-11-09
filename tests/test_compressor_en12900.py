"""Compresor por polinomios de UNE-EN 12900 (decisión del autor, 15/10/2026).

Fija lo que `docs/DECISIONES_2026_10_15.md` y `docs/historico/PLAN_COMPRESOR_EN12900.md` declaran:
polinomios de diez coeficientes ajustados a los puntos de VAP a cuatro velocidades, regla de
conservación de los rendimientos al cambiar el recalentamiento, interpolación cuadrática en la
velocidad sin extrapolar, factores de incertidumbre y misma interfaz que el semiempírico.
"""
import numpy as np
import pytest

from amoniatermia import campaign as C
from amoniatermia import data as D
from amoniatermia.components.compressor_en12900 import (EN12900Compressor,
                                                        VelocidadFueraDeRango, ajusta_polinomio,
                                                        evalua, terminos)
from amoniatermia.props import Fluid

K = 273.15


@pytest.fixture(scope="module")
def comp():
    return D.compressor_en12900()


def test_el_polinomio_tiene_los_diez_terminos_de_la_norma():
    t = terminos(2.0, 45.0)
    assert t.shape == (10,)
    assert list(t) == [1, 2, 45, 4, 90, 2025, 8, 45 * 4, 2 * 2025, 45 ** 3]


def test_el_ajuste_reproduce_un_polinomio_exacto():
    rng = np.random.default_rng(1)
    c = rng.normal(size=10)
    t0, tc = rng.uniform(-25, 15, 40), rng.uniform(10, 55, 40)
    assert np.allclose(ajusta_polinomio(t0, tc, evalua(c, t0, tc)), c)


def test_el_F2_usa_polinomios_y_cuatro_velocidades(comp):
    assert D.compressor_model(D.load("compresor_bock_f2")) == "en12900"
    assert comp.procedencia["velocidades_rpm"] == [960.0, 1100.0, 1250.0, 1450.0]
    assert comp.procedencia["puntos_por_velocidad"] == [57, 57, 57, 57]
    assert comp.rpm == 1450.0


def test_reproduce_los_puntos_de_vap_a_cada_velocidad(comp):
    """Ajuste: menos de un 1 % en caudal y potencia y de 2 K en descarga."""
    pts = D.compressor_en12900_points()
    for rpm in (960.0, 1100.0, 1250.0, 1450.0):
        comp.fija_velocidad(rpm)
        for p in (q for q in pts if q["rpm"] == rpm):
            r = comp.solve(p["P_ad"], p["T_su"], p["P_ex"])
            assert abs(r.m_dot / p["m_dot"] - 1) < 0.01
            assert abs(r.W_shaft / p["W_shaft"] - 1) < 0.01
            assert abs(r.T_dis - p["T_dis"]) < 2.0
    comp.fija_velocidad(1450.0)


def test_la_regla_del_recalentamiento_reproduce_el_catalogo_a_1_K(comp):
    """Los 46 puntos del catálogo (1 K) no entran en el ajuste (5 K): validan la regla."""
    comp.fija_velocidad(1450.0)
    for p in D.compressor_catalog():
        r = comp.solve(p["P_ad"], p["T_su"], p["P_ex"])
        assert abs(r.m_dot / p["m_dot"] - 1) < 0.01
        assert abs(r.W_shaft / p["W_shaft"] - 1) < 0.01
        assert abs(r.T_dis - p["T_dis"]) < 2.0


def test_no_extrapola_en_la_velocidad(comp):
    with pytest.raises(VelocidadFueraDeRango):
        comp.fija_velocidad(900.0)
    with pytest.raises(VelocidadFueraDeRango):
        comp.fija_velocidad(1500.0)
    comp.fija_velocidad(1450.0)


def test_el_caudal_crece_con_la_velocidad(comp):
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(2 + K), f.Psat(45 + K)
    m = []
    for rpm in (960.0, 1200.0, 1450.0):
        comp.fija_velocidad(rpm)
        m.append(comp.solve(P0, 7 + K, Pk).m_dot)
    comp.fija_velocidad(1450.0)
    assert m[0] < m[1] < m[2]


def test_el_balance_de_energia_cierra(comp):
    """Q_amb = W_eje - m (h_dis - h_su)."""
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(0 + K), f.Psat(45 + K)
    r = comp.solve(P0, 5 + K, Pk)
    f.update_PT(P0, 5 + K)
    assert r.Q_amb == pytest.approx(r.W_shaft - r.m_dot * (r.h_dis - f.h), rel=1e-12)
    assert r.W_el == pytest.approx(r.W_shaft / (0.90 * 0.98))


def test_los_factores_de_incertidumbre_se_aplican():
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(2 + K), f.Psat(45 + K)
    base = D.compressor_en12900().solve(P0, 7 + K, Pk)
    sus = {"compresor_bock_f2:modelo_en12900.ajuste.factor_caudal": 0.99,
           "compresor_bock_f2:modelo_en12900.ajuste.factor_potencia": 1.01,
           "compresor_bock_f2:modelo_en12900.ajuste.desplazamiento_descarga_K": 1.0}
    with D.sustituciones(sus):
        r = D.compressor_en12900().solve(P0, 7 + K, Pk)
    assert r.m_dot == pytest.approx(0.99 * base.m_dot, rel=1e-9)
    assert r.W_shaft == pytest.approx(1.01 * base.W_shaft, rel=1e-9)
    assert r.T_dis > base.T_dis + 0.5


def test_r290_y_r32_por_polinomios_a_una_velocidad():
    for nombre, fluido in (("compresor_r290", "Propane"), ("compresor_r32", "R32")):
        df = D.load(nombre)
        c = D.compressor_en12900(df)
        assert len(c.pol) == 1
        for p in D.compressor_catalog_fichero(df.require("modelo_en12900.fichero_puntos"),
                                              Fluid(fluido)):
            r = c.solve(p["P_ad"], p["T_su"], p["P_ex"])
            assert abs(r.m_dot / p["m_dot"] - 1) < 0.02
            assert abs(r.W_shaft / p["W_shaft"] - 1) < 0.01
        with pytest.raises(VelocidadFueraDeRango):
            c.fija_velocidad(c.rpm_max + 100)


def test_el_r32_toma_la_descarga_del_semiempirico_declarado():
    df = D.load("compresor_r32")
    assert df.require("modelo_en12900.descarga") == "semiempirico"
    c = D.compressor_en12900(df)
    assert c.pol[0].T_dis_C is None and c.descarga_ref is not None


def test_el_circuito_usa_el_modelo_del_fichero_y_admite_el_semiempirico():
    c, _ = C.build_circuit(con_lineas=False)
    assert isinstance(c.compressor, EN12900Compressor)
    c2, _ = C.build_circuit(con_lineas=False, modelo_compresor="semiempirico")
    assert type(c2.compressor).__name__ == "SemiEmpiricalCompressor"
