"""Comparacion entre fluidos (cap. 13; tabla 6.6, decisiones 9b y 9c del 29/09/2026)."""
import pytest

from amoniatermia import campaign as C, comparacion as K, data as D


def test_cada_fluido_tiene_su_compresor_y_si_falta_se_declara_transferido():
    assert C.COMPRESOR_POR_FLUIDO == {"Ammonia": "compresor_bock_f2",
                                      "Propane": "compresor_r290", "R32": "compresor_r32"}
    c, _ = C.build_circuit(con_placas=False, con_lineas=False)
    assert c.compresor_fichero == "compresor_bock_f2" and not c.compresor_transferido
    if not (D.data_dir() / "compresor_r290.yaml").is_file():
        c, _ = C.build_circuit(fluido="Propane", con_placas=False, con_lineas=False)
        assert c.compresor_fichero == "compresor_bock_f2" and c.compresor_transferido


def test_fuera_del_amoniaco_la_bateria_lleva_tubo_de_cobre():
    c, _ = C.build_circuit(fluido="R32", con_placas=False, con_lineas=False)
    assert c.sustituciones["bateria_frimetal_cbn21:conductividad_tubo_W_mK"] == 339.0
    c, _ = C.build_circuit(fluido="R32", con_placas=False, con_lineas=False, materiales="base")
    assert "bateria_frimetal_cbn21:conductividad_tubo_W_mK" not in c.sustituciones
    c, _ = C.build_circuit(con_placas=False, con_lineas=False)
    assert c.sustituciones == {}


def test_la_igualacion_de_capacidad_escala_la_cilindrada():
    r = K.igualar_cilindrada("R32", 10308.0)
    assert r.Q == pytest.approx(10308.0, rel=2e-3)
    assert r.sustituciones == {f"{r.compresor}:geometria.volumen_barrido_m3_rev": r.V_swept}
    assert r.factor < 1.0          # el R-32 tiene mas capacidad volumetrica que el NH3
