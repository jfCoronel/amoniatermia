"""Infraestructura comun de los capitulos 10 a 13 (docs/historico/PLAN_CAPITULOS_10_13.md).

I-1 mapas de prestaciones, I-2 resultados tabulares, I-3 sustituciones
declaradas, I-4 envolvente operativa, I-5 hojas de cifras. Los circuitos de
estas pruebas son de compresor y bateria, con la evaporacion impuesta como en
el §9.7.8, para que resuelvan en pocos segundos.
"""
import json
import math

import pytest

from amoniatermia import (AirState, Boundary, Setpoints, campaign as C,
                          data as D, envelope as E, maps as M, reporting as R)

K = 273.15


def _bc(T_aire=35.0):
    return Boundary(air=AirState(T=T_aire + K, V_frontal=3.30),
                    m_dot_air=None, T_amb=T_aire + K)


SP = Setpoints(superheat=1.0, subcooling=0.0, T_evap=2 + K)


@pytest.fixture(scope="module")
def punto():
    c, _ = C.build_circuit(con_placas=False)
    return c, c.solve("M-2", _bc(), SP)


# --- I-3: sustituciones declaradas ---------------------------------------------

def test_la_sustitucion_cambia_el_dato_solo_dentro_del_contexto():
    df = D.load("compresor_bock_f2")
    antes = df.require("transmision.eta_motor")
    with D.sustituciones({"compresor_bock_f2:transmision.eta_motor": 0.88}):
        assert df.require("transmision.eta_motor") == 0.88
    assert df.require("transmision.eta_motor") == antes
    assert D.sustituciones_activas() == {}


def test_la_sustitucion_llega_a_los_subdiccionarios():
    """`air_coil_geometry` pide `geometria` entera y lee sus claves."""
    with D.sustituciones({"bateria_frimetal_cbn21:geometria.paso_aleta_m": 0.0025}):
        assert D.air_coil_geometry().fin_pitch == 0.0025
    assert D.air_coil_geometry().fin_pitch == 0.0021


def test_una_ruta_inexistente_no_se_admite():
    with pytest.raises(D.SustitucionInvalida, match="no existe"):
        with D.sustituciones({"compresor_bock_f2:transmision.eta_motr": 0.9}):
            pass


def test_rellenar_un_dato_que_no_existe_queda_marcado():
    ruta = "bateria_frimetal_cbn21:pendientes.circuiteria_distribuidor"
    with D.sustituciones({ruta: "inventada"}) as reg:
        assert reg[ruta]["rellena_un_dato_que_no_existe"] is True


def test_el_circuito_resuelve_con_sus_sustituciones_y_las_declara(punto):
    _, base = punto
    sus = {"compresor_bock_f2:transmision.eta_motor": 0.88}
    c, _ = C.build_circuit(con_placas=False, sustituciones=sus)
    s = c.solve("M-2", _bc(), SP)
    W, W0 = s.components["compresor"].W_el, base.components["compresor"].W_el
    assert W / W0 == pytest.approx(0.90 / 0.88, rel=1e-6)
    assert set(s.provenance["sustituciones"]) == set(sus)
    assert base.provenance["sustituciones"] == {}


# --- I-4: envolvente operativa ---------------------------------------------------

def test_las_presiones_del_catalogo_son_manometricas(punto):
    _, s = punto
    lim = s.envelope["limites"]["presion_alta"]["limite"]
    assert lim == pytest.approx(25e5 + 101325.0)


def test_la_descarga_se_comprueba_con_el_limite_del_capitulo_7(punto):
    """El catálogo no publica la temperatura de descarga admisible; se adopta
    el límite orientativo de 140 °C del §7.7.1 (decisión del autor,
    29/09/2026) y la envolvente queda completa. El equilibrio de M-2 descarga a
    120 °C: cumple."""
    _, s = punto
    lim = s.envelope["limites"]["temperatura_descarga"]
    assert lim["limite"] == pytest.approx(140 + K)
    assert lim["estado"] == "cumple"
    assert s.envelope["completa"] is True
    assert s.admissible


def test_el_ventilador_queda_fuera_de_la_clasificacion_de_H6(punto):
    """Decisión del autor (29/09/2026): el ventilador es auxiliar; el compresor
    se clasifica con su motor y su transmisión."""
    from amoniatermia import MODES, indicators as I
    _, s = punto
    x = I.exergy(s, MODES["M-2"])
    assert "ventilador" in x.y_D and "ventilador" not in x.y_D_ciclo
    assert "compresor_con_motor" in x.y_D_ciclo
    assert sum(x.y_D_ciclo.values()) == pytest.approx(1.0)
    assert x.componente_mayor_ciclo == "compresor_con_motor"


def test_con_un_limite_adoptado_la_descarga_se_comprueba():
    ruta = "compresor_bock_f2:limites.T_descarga_max_K"
    c, _ = C.build_circuit(con_placas=False, sustituciones={ruta: 110 + K})
    s = c.solve("M-2", _bc(), SP)
    assert s.envelope["limites"]["temperatura_descarga"]["estado"] == "incumple"
    assert s.valid and not s.admissible


def test_el_diagrama_digitalizado_reproduce_las_zonas_de_los_puntos_vap():
    """El diagrama de límites del fabricante, digitalizado el 29/09/2026, da
    la misma zona que el VAP en sus 39 puntos (con ±0.5 K de lectura)."""
    import csv
    with (D.data_dir() / "compresor_bock_f2_vap.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            z = E.zona_diagrama(float(r["T0_C"]) + K, float(r["Tc_C"]) + K)
            assert z == r["zona_esperada"], (r["T0_C"], r["Tc_C"])


def test_la_fila_de_50_grados_del_catalogo_pide_refrigeracion_suplementaria():
    """El catálogo lo anota en esa fila; el diagrama digitalizado lo recoge."""
    assert E.zona_diagrama(0 + K, 50 + K) == "refrigeracion_suplementaria"
    assert E.zona_diagrama(5 + K, 50 + K) == "sin_limites"


def test_solo_la_zona_sin_limites_es_admisible(punto):
    """Decisión del autor (29/09/2026): la máquina no lleva tapa de cilindro
    refrigerada. El equilibrio de M-2 está en la zona sin límites."""
    _, s = punto
    lim = s.envelope["limites"]["diagrama_aplicacion"]
    assert lim["valor"] == "sin_limites" and lim["estado"] == "cumple"


def test_el_dominio_del_compresor_es_el_del_catalogo(punto):
    _, s = punto
    dom = E.dominio_identificacion()
    assert dom["T0"] == pytest.approx((0 + K, 5 + K))
    assert dom["Tc"] == pytest.approx((15 + K, 50 + K))
    assert s.envelope["fuera_del_dominio_del_compresor"] is False


# --- I-2: resultados tabulares -------------------------------------------------

def test_la_campana_se_escribe_como_tabla_con_su_procedencia(tmp_path):
    r = C.run("M-2", [_bc(30.0), _bc(35.0)], sp=SP, etiquetas=["30", "35"],
              circuito=C.build_circuit(con_placas=False)[0])
    csv_path, meta_path = r.write_table(tmp_path / "campana")
    df = r.to_frame()
    for col in ("valido", "admisible", "T_cond_C", "Q_evap", "carga_max_g",
                "envolvente_presion_alta", "EER"):
        assert col in df.columns
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["resumen"]["validos"] == 2
    assert meta["unidades"]["T_cond_C"] == "°C"
    assert csv_path.read_text(encoding="utf-8").count("\n") == 3


# --- I-1: mapas de prestaciones ------------------------------------------------

def test_el_serpentin_recorre_vecinos():
    orden = M._serpentin((3, 2))
    assert orden == [(0, 0), (0, 1), (1, 1), (1, 0), (2, 0), (2, 1)]
    for a, b in zip(orden, orden[1:]):
        assert sum(abs(i - j) for i, j in zip(a, b)) == 1


@pytest.fixture(scope="module")
def mapa():
    return M.build("M-2", {"T_aire": [30.0, 35.0]},
                   lambda c: (_bc(c["T_aire"]), SP),
                   circuito=C.build_circuit(con_placas=False)[0])


def test_el_mapa_reproduce_sus_nudos_y_no_extrapola(mapa, punto):
    _, s = punto
    assert mapa.n_validos == 2
    assert mapa("Q_evap", T_aire=35.0) == pytest.approx(s.Q_evap, rel=1e-6)
    a, b = mapa("Q_evap", T_aire=30.0), mapa("Q_evap", T_aire=35.0)
    assert mapa("Q_evap", T_aire=32.5) == pytest.approx(0.5 * (a + b))
    assert math.isnan(mapa("Q_evap", T_aire=40.0))
    assert [r["arranque"] for r in mapa.rows] == ["estimacion", "continuacion"]


def test_el_mapa_se_escribe_y_se_relee_igual(mapa, tmp_path):
    mapa.write(tmp_path / "mapa")
    otro = M.PerformanceMap.read(tmp_path / "mapa")
    assert otro("Q_evap", T_aire=32.5) == pytest.approx(mapa("Q_evap", T_aire=32.5))


def test_los_ejes_no_pueden_ser_temperaturas_desordenadas():
    with pytest.raises(ValueError, match="creciente"):
        M.build("M-2", {"T_aire": [35.0, 30.0]}, lambda c: (_bc(), SP),
                circuito=object())


# --- I-5: hojas de cifras ------------------------------------------------------

def test_la_hoja_lee_la_revision_antes_de_escribir(tmp_path):
    hoja = R.HojaDeCifras(tmp_path / "cifras.md", "Prueba", "tests")
    rev = hoja.revision
    hoja.seccion("a", R.tabla(["x"], [[1]]))
    hoja.seccion("b", "texto")
    texto = (tmp_path / "cifras.md").read_text(encoding="utf-8")
    assert rev in texto and "## a" in texto and "## b" in texto
    assert "Secciones: a, b" in texto
