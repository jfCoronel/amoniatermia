"""Correlaciones de cambio de fase en el INTERIOR DE TUBO. §9.7.5.

Ecuaciones 9-24 a 9-27, y la separación de familias que el apartado exige al
declarar que las correlaciones de placa corrugada «no son aplicables aquí».
"""
import math

import pytest

from amoniatermia import Fluid
from amoniatermia import data as D
from amoniatermia.correlations import available, get, info
from amoniatermia.correlations.tube import (cooper_solo, dobson_chato_regime,
                                            galileo, gungor_winterton,
                                            gungor_winterton_horizontal,
                                            soliman_froude,
                                            stratified_angle_fraction)

TOL = 0.02
G_FICHA = 48.0                      # kg/(m²·s), §9.7.1


def rel(a, b):
    return abs(a - b) / abs(b)


@pytest.fixture(scope="module")
def geom():
    return D.air_coil_geometry()


@pytest.fixture(scope="module")
def f():
    return Fluid("Ammonia")


def sat_at(f, T_C):
    P = f.Psat(T_C + 273.15)
    s = f.sat_props(P)
    s["p_red"] = f.p_reduced(P)
    return s


# ---------------------------------------------------------------------------
# La separación de familias: es el requisito estructural de C4
# ---------------------------------------------------------------------------

def test_las_familias_de_tubo_y_de_placa_estan_separadas():
    """§9.7.5: «las correlaciones adoptadas en los apartados 9.6.3 y 9.6.3
    son específicas de geometría de placas corrugadas y no son aplicables aquí».

    Si estuviesen en la misma familia, un intercambiador de placas podría elegir
    por nombre una correlación de tubo y la banda de incertidumbre del §6.11
    dejaría de significar nada: recorrería formulaciones que no describen la
    geometría del componente. La separación hace que ese error sea un KeyError.
    """
    assert set(available("tube_condensation")).isdisjoint(
        available("plate_condensation"))
    assert set(available("tube_boiling")).isdisjoint(available("plate_boiling"))
    with pytest.raises(KeyError):
        get("plate_condensation", "dobson_chato")
    with pytest.raises(KeyError):
        get("tube_boiling", "additive_cooper")
    with pytest.raises(KeyError):
        get("tube_condensation", "nusselt_film")


def test_ninguna_correlacion_de_tubo_declara_amoniaco_en_su_base():
    """§9.7.5 lo declara expresamente, y el §9.12.3 exige que la base viaje
    con la función. La atenuación también está cifrada en el apartado: con el
    lado de refrigerante pesando el 23 %, un error del 30 % en el coeficiente
    da menos del 8 % en la conductancia del componente."""
    for familia in ("tube_condensation", "tube_boiling"):
        for nombre in available(familia):
            ci = info(familia, nombre)
            if nombre == "ficha_cbn21_agregado":
                continue                       # es el dato, no una correlación
            assert "Ammonia" not in ci.validity.fluids
            assert ci.reference


# ---------------------------------------------------------------------------
# §9.7.5, ec. 9-24 y 9-25 — condensación con criterio de transición
# ---------------------------------------------------------------------------

def test_a_la_velocidad_masica_de_esta_bateria_no_hay_regimen_anular(f, geom):
    """§9.7.5: con 48 kg/(m²·s) —valor que el elevado calor latente del NH₃
    hace inevitablemente bajo— el régimen estratificado es el esperable en buena
    parte del serpentín. El modelo lo lleva más lejos: el Froude de Soliman no
    alcanza 20 en NINGÚN título, de modo que la condensación es estratificada de
    principio a fin."""
    sat = sat_at(f, 45.0)
    Fr = [soliman_froude(x, G_FICHA, sat, geom.d_i)
          for x in (0.05, 0.2, 0.4, 0.6, 0.8, 0.95)]
    assert max(Fr) < 20.0
    for x in (0.2, 0.5, 0.8):
        _, reg, _ = dobson_chato_regime(x, G_FICHA, sat, geom,
                                        T_wall=sat["Tsat"] - 4.0)
        assert reg == "estratificado"


def test_a_velocidad_masica_alta_el_regimen_pasa_a_anular(f, geom):
    """El criterio tiene que discriminar, no declarar siempre lo mismo. Con la
    misma geometría y un flujo másico de fluido halogenado equivalente —unas
    seis veces mayor, §9.7.5— el régimen cruza a anular."""
    sat = sat_at(f, 45.0)
    assert soliman_froude(0.5, 6 * G_FICHA, sat, geom.d_i) > 20.0
    _, reg, _ = dobson_chato_regime(0.5, 6 * G_FICHA, sat, geom,
                                    T_wall=sat["Tsat"] - 4.0)
    assert reg == "anular"


def test_tratar_todo_como_anular_INFRAestimaria_el_coeficiente(f, geom):
    """DISCREPANCIA REPORTADA. El §9.7.5 justifica el criterio de transición
    diciendo que «tratar toda la condensación como anular sobreestimaría el
    coeficiente». Con las correlaciones que el propio apartado prescribe ocurre
    lo contrario: a 48 kg/(m²·s) la rama anular da entre el 34 % y el 66 % de la
    estratificada.

    La razón es física y vale la pena anotarla. La rama anular es una forma de
    convección forzada gobernada por la cizalladura del vapor, y a Re_l ≈ 2000
    transfiere poco. La rama estratificada, en cambio, incorpora una película
    descendente gobernada por la GRAVEDAD sobre la generatriz superior, que a
    velocidad másica baja es muy eficaz; lo que transfiere mal es el remanso
    inferior, y este pesa solo por (1 − θ_l/π).

    El criterio sigue siendo imprescindible —cambia el coeficiente por un factor
    de hasta tres— pero la dirección del error es la contraria a la declarada.
    """
    sat = sat_at(f, 45.0)
    T_w = sat["Tsat"] - 4.0
    for x in (0.1, 0.3, 0.5, 0.9):
        h_estrat, reg, _ = dobson_chato_regime(x, G_FICHA, sat, geom, T_wall=T_w)
        assert reg == "estratificado"
        h_anular, reg2, _ = dobson_chato_regime(x, G_FICHA, sat, geom,
                                                T_wall=T_w, Fr_so_c=0.0)
        assert reg2 == "anular"
        assert 0.30 < h_anular / h_estrat < 0.70


def test_el_angulo_del_remanso_sale_de_la_fraccion_de_huecos():
    """1 − θ_l/π = arccos(2α − 1)/π. El capítulo escribe θ_l en la ec. 9-24 sin
    declarar cómo se obtiene; es de Dobson y Chato."""
    assert stratified_angle_fraction(1.0) == pytest.approx(0.0)   # sin remanso
    assert stratified_angle_fraction(0.5) == pytest.approx(0.5)
    assert stratified_angle_fraction(0.0) == pytest.approx(1.0)


def test_galileo_es_adimensional(f, geom):
    sat = sat_at(f, 45.0)
    Ga = galileo(sat["rho_l"], sat["rho_v"], geom.d_i, sat["mu_l"])
    assert Ga > 0.0
    # escala con d^3: duplicar el diámetro multiplica por ocho
    assert rel(galileo(sat["rho_l"], sat["rho_v"], 2 * geom.d_i, sat["mu_l"]),
               8 * Ga) < 1e-9


def test_la_rama_estratificada_depende_de_la_pared(f, geom):
    """Por el número de Jakob. Es el acoplamiento implícito que obliga al lazo
    interno por celda del §9.7.2."""
    sat = sat_at(f, 45.0)
    h2 = dobson_chato_regime(0.5, G_FICHA, sat, geom, T_wall=sat["Tsat"] - 2)[0]
    h8 = dobson_chato_regime(0.5, G_FICHA, sat, geom, T_wall=sat["Tsat"] - 8)[0]
    assert h2 > h8
    # h ∝ ΔT^(−1/4), pero solo el término de película lleva Ja: el del remanso
    # no depende de la pared y diluye el exponente. De ahí que la razón quede
    # algo por debajo de 4^(1/4) en lugar de igualarlo.
    assert 0.95 < (h2 / h8) / 4 ** 0.25 < 1.0


def test_la_ec_10_31_predice_un_coeficiente_muy_superior_al_de_ficha(f, geom):
    """DISCREPANCIA REPORTADA. La ficha declara 5200 W/(m²·K) agregados en
    condensación y la tabla 9.18 construye sobre ese valor el reparto de
    resistencias y el U de 38.2 W/(m²·K), que queda un 11 % por debajo del U
    de ficha (43).

    La ec. 9-24 predice del orden de 9000 W/(m²·K), y con él la conductancia
    reconstruida SÍ alcanza el valor de ficha sin tocar la eficiencia de aleta.
    La consecuencia es que el §9.7.4 no puede atribuir la discrepancia del 11 %
    únicamente al método de aleta equivalente: un coeficiente interior mayor que
    el declarado la explica igual de bien, y los dos efectos son
    indistinguibles a partir de un solo valor de U.
    """
    sat = sat_at(f, 45.0)
    T_w = sat["Tsat"] - 4.0
    hs = [dobson_chato_regime(x, G_FICHA, sat, geom, T_wall=T_w)[0]
          for x in (0.05, 0.2, 0.4, 0.5, 0.6, 0.8, 0.95)]
    medio = sum(hs) / len(hs)
    assert medio > 1.5 * 5200.0


# ---------------------------------------------------------------------------
# §9.7.5, ec. 9-26 y 9-27 — ebullición
# ---------------------------------------------------------------------------

def test_cooper_solo_reproduce_las_cifras_publicadas(f, geom, df=None):
    """§9.7.5 publica «del orden de 3100 W/(m²·K) en la condición nominal de
    calefacción, descendiendo a 1900 W/(m²·K) en la condición del perfil frío».
    El modelo las reproduce con COOPER SOLO, a menos del 1.5 %."""
    pub = D.air_coil().require(
        "prediccion_evaporador.h_ebullicion_publicado_W_m2K")
    nominal = cooper_solo(0.5, G_FICHA, 8100.0, sat_at(f, 1.6), f.M, geom)
    frio = cooper_solo(0.5, G_FICHA, 4700.0, sat_at(f, -11.1), f.M, geom)
    assert rel(nominal, pub["nominal"]) < 0.02
    assert rel(frio, pub["perfil_frio"]) < 0.02
    assert pub["procedencia"] == "cooper_solo"


def test_la_ec_10_33_completa_duplica_lo_que_el_capitulo_publica(f, geom):
    """DISCREPANCIA REPORTADA, la principal de C4.

    El §9.7.5 declara adoptar la superposición de la ec. 9-26, h = S·h_nb +
    F·h_l, y a continuación publica unas cifras que son el término nucleado
    SOLO. Implementada como está escrita, la ecuación da entre dos y dos veces y
    media esos valores, porque el término convectivo F·h_l no es despreciable:
    F llega a 11 a título alto.

    Se reporta y no se resuelve. El modelo adopta la ecuación que el capítulo
    ESCRIBE, y conserva registrada la que el capítulo CALCULÓ.
    """
    sat = sat_at(f, 1.6)
    for x in (0.2, 0.5, 0.8):
        gw = gungor_winterton(x, G_FICHA, 8100.0, sat, f.M, geom)
        co = cooper_solo(x, G_FICHA, 8100.0, sat, f.M, geom)
        assert 1.7 < gw / co < 2.6


def test_la_correccion_de_tubo_horizontal_no_es_indiferente(f, geom):
    """La formulación original corrige F y S cuando el Froude del líquido baja
    de 0.05, y la ec. 9-27 no la recoge. Con G = 48 kg/(m²·s) esta batería
    opera JUSTO en ese umbral, de modo que la omisión no es académica: es una
    asimetría del capítulo, que trata la estratificación al condensar (ec.
    9-24) y la ignora al evaporar."""
    sat = sat_at(f, 1.6)
    Fr_l = G_FICHA ** 2 / (sat["rho_l"] ** 2 * 9.80665 * 0.0123)
    assert 0.02 < Fr_l < 0.05              # bajo el umbral, la corrección actúa
    con = gungor_winterton_horizontal(0.3, G_FICHA, 8100.0, sat, f.M, geom)
    sin = gungor_winterton(0.3, G_FICHA, 8100.0, sat, f.M, geom)
    assert con < sin
    assert 0.55 < con / sin < 0.95


def test_la_ebullicion_depende_del_flujo_de_calor(f, geom):
    """Por el número de ebullición y por Cooper. Es el otro acoplamiento
    implícito del §9.7.2."""
    sat = sat_at(f, 1.6)
    baja = gungor_winterton(0.5, G_FICHA, 2000.0, sat, f.M, geom)
    alta = gungor_winterton(0.5, G_FICHA, 16000.0, sat, f.M, geom)
    assert alta > baja


def test_el_coeficiente_de_ebullicion_es_muy_inferior_al_de_condensacion(
        f, geom):
    """§9.7.5: es la razón por la que el componente ofrece menor conductancia
    como evaporador que como condensador, y la tabla 9.20 lo cuantifica."""
    ebu = gungor_winterton(0.5, G_FICHA, 8100.0, sat_at(f, 1.6), f.M, geom)
    sat_c = sat_at(f, 45.0)
    con = dobson_chato_regime(0.5, G_FICHA, sat_c, geom,
                              T_wall=sat_c["Tsat"] - 4.0)[0]
    assert ebu < con
