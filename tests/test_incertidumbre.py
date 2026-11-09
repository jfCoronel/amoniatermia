"""Incertidumbre de parámetros (§6.11, C10-8): rangos, configuración y Morris.

Los rangos son decisión del autor (29/09/2026) y quedan fijados aquí antes de
publicar resultados, como los criterios de N1.
"""
import numpy as np
import pytest

from amoniatermia import AirState, Boundary, Setpoints, WaterStream
from amoniatermia import data as D
from amoniatermia import uncertainty as U

K = 273.15


def test_los_rangos_son_los_decididos():
    f = U.FACTORES
    assert set(f) == {"C1_aire", "Phi_placas", "phi_md", "eta_electromecanico"}
    assert (f["C1_aire"].bajo, f["C1_aire"].alto) == pytest.approx((0.507 * 0.95, 0.507 * 1.05))
    assert (f["Phi_placas"].bajo, f["Phi_placas"].alto) == (1.10, 1.30)
    assert (f["phi_md"].bajo, f["phi_md"].alto) == (1.0, 1.3)
    assert f["eta_electromecanico"].bajo == 0.82
    assert f["eta_electromecanico"].alto == 0.89
    assert f["eta_electromecanico"].nominal == pytest.approx(0.90 * 0.98)


def test_el_ventilador_no_es_factor():
    """Los 780 W son dato del conjunto montado; los 296 W, la batería sola."""
    assert not any("ventilador" in n for n in U.FACTORES)


def test_los_nominales_son_los_del_fichero():
    assert U.FACTORES["C1_aire"].nominal == D.load("bateria_frimetal_cbn21").require(
        "correlacion_aire.C1")
    g = D.plate_geometry("condensador_climatizacion")
    assert U.FACTORES["Phi_placas"].nominal == g.phi


def test_en_el_nominal_no_hay_sustituciones():
    assert U.configuracion() == ({}, 1.0)


def test_phi_arrastra_el_angulo_y_el_producto():
    """Reanclar con otro Φ: β se mueve poco y φc·φv mucho (test_anclaje_placas)."""
    sus, _ = U.configuracion({"Phi_placas": 1.30})
    prod = sus["placas_alfanova:producto_phi_c_phi_v.valor"]
    assert prod == pytest.approx(1.118, abs=0.01)
    b27 = sus["placas_alfanova:unidades.condensador_climatizacion.geometria.angulo_corrugacion_rad"]
    b16 = sus["placas_alfanova:unidades.desrecalentador_acs.geometria.angulo_corrugacion_rad"]
    assert b27 == b16 and 67.0 < np.degrees(b27) < 74.0


def test_el_rendimiento_electromecanico_se_reparte_sobre_el_motor():
    sus, _ = U.configuracion({"eta_electromecanico": 0.85})
    eta_t = D.load("compresor_bock_f2").require("transmision.eta_transmision")
    assert sus["compresor_bock_f2:transmision.eta_motor"] * eta_t == pytest.approx(0.85)


def test_el_factor_del_compresor_es_la_banda_de_ajuste():
    """Desde el 15/10/2026 (P3): los dos extremos de la banda del error de ajuste de los
    polinomios, aplicados por sustitucion declarada al bloque `modelo_en12900.ajuste`."""
    juegos = U.juegos_compresor()
    assert set(juegos) == {"adoptado", "banda_desfavorable", "banda_favorable"}
    d = juegos["banda_desfavorable"]
    assert d["factor_caudal"] < 1.0 < d["factor_potencia"] and d["desplazamiento_descarga_K"] > 0
    assert 0 < 1.0 - d["factor_caudal"] < 0.02 and 0 < d["desplazamiento_descarga_K"] < 3.0
    sus = U.configuracion(juego="banda_desfavorable")[0]
    with D.sustituciones(sus):
        assert D.load("compresor_bock_f2").require(
            "modelo_en12900.ajuste.factor_potencia") == d["factor_potencia"]

def test_la_trayectoria_de_morris_cambia_un_factor_cada_vez():
    rng = np.random.default_rng(1)
    for _ in range(20):
        pts, cambios, delta = U._trayectoria(rng, 4, 4)
        assert len(pts) == 5 and sorted(cambios) == [0, 1, 2, 3]
        for j, i in enumerate(cambios):
            d = pts[j + 1] - pts[j]
            assert abs(abs(d[i]) - delta) < 1e-12
            assert np.count_nonzero(np.abs(d) > 1e-12) == 1
        assert all(((0.0 <= p) & (p <= 1.0)).all() for p in pts)


@pytest.fixture(scope="module")
def evaluador_m2():
    bc = Boundary(air=AirState(T=35 + K, V_frontal=3.30), m_dot_air=None,
                  clima=WaterStream(12 + K, 0.45), T_amb=35 + K)
    return U.Evaluador("M-2", bc, Setpoints(superheat=5.0, subcooling=2.0))


def test_el_rendimiento_electromecanico_no_toca_el_ciclo(evaluador_m2):
    """Solo cambia la potencia eléctrica: la potencia al eje, el ciclo y la
    capacidad no dependen de él."""
    y0, y = evaluador_m2.nominal, evaluador_m2({"eta_electromecanico": U.FACTORES["eta_electromecanico"].bajo})
    assert y["Q_util"] == pytest.approx(y0["Q_util"], rel=1e-4)
    assert y["T_cond"] == pytest.approx(y0["T_cond"], abs=0.01)
    assert y["W_el"] > 1.05 * y0["W_el"]


def test_mas_C1_en_la_bateria_condensadora_baja_la_condensacion(evaluador_m2):
    y0, y = evaluador_m2.nominal, evaluador_m2({"C1_aire": U.FACTORES["C1_aire"].alto})
    assert y["valido"] and y["T_cond"] < y0["T_cond"] and y["indicador"] > y0["indicador"]
