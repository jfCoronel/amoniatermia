"""Propiedades del aire húmedo. §9.7.6.

El módulo `psychrometrics` sustituye a `HAPropsSI` por las formulaciones
analíticas de ASHRAE, por la misma razón por la que el §9.12.4 prohíbe
`PropsSI` en bucle: la marcha del §9.7.2 evalúa la curva de saturación del
orden de 10⁴ veces por punto de operación resuelto.

Sustituir una biblioteca de referencia por una correlación exige cuantificar el
error de la sustitución, exactamente como el §6.6.4 lo exige para el backend
tabular de CoolProp. Eso es lo que hace este fichero.
"""
import math

import CoolProp.CoolProp as CP
import pytest

from amoniatermia import psychrometrics as psy

P = psy.P_ATM


def rel(a, b):
    return abs(a - b) / abs(b)


# ---------------------------------------------------------------------------
# Contraste contra CoolProp sobre el dominio de trabajo del componente
# ---------------------------------------------------------------------------
DOMINIO = [-7.0, -2.0, 0.5, 2.0, 7.0, 15.0, 25.0, 35.0, 45.0]


@pytest.mark.parametrize("t_C", DOMINIO)
def test_humedad_de_saturacion_frente_a_coolprop(t_C):
    T = t_C + 273.15
    assert rel(psy.w_saturation(T), CP.HAPropsSI("W", "T", T, "P", P, "R", 1.0)) < 0.01


@pytest.mark.parametrize("t_C", DOMINIO)
def test_pendiente_de_la_curva_de_saturacion_frente_a_coolprop(t_C):
    """b' es la magnitud de la que depende la ec. 9-29, y por tanto la única
    cuya desviación se propaga a la conductancia del evaporador.

    La tolerancia se aprieta donde importa. La superficie solo está húmeda
    operando como evaporador —por debajo de 20 °C, y la tabla 9.20 no pasa de
    7 °C de aire—, y ahí el acuerdo es mejor del 0.5 %, incluido el cambio de
    rama sobre hielo. Por encima la formulación de gas ideal de ASHRAE se separa
    del gas real, hasta un 0.5 % a 45 °C, pero en ese dominio la superficie está
    seca y b' no se evalúa.
    """
    T = t_C + 273.15
    cp_ref = (CP.HAPropsSI("H", "T", T + 0.05, "P", P, "R", 1.0)
              - CP.HAPropsSI("H", "T", T - 0.05, "P", P, "R", 1.0)) / 0.1
    tol = 0.005 if t_C <= 20.0 else 0.01
    assert rel(psy.saturation_enthalpy_slope(T), cp_ref) < tol


@pytest.mark.parametrize("t_C", DOMINIO)
def test_la_entalpia_difiere_de_coolprop_solo_en_el_datum(t_C):
    """El datum de ASHRAE y el de CoolProp no coinciden, pero el método del
    potencial entálpico solo usa DIFERENCIAS de entalpía. Lo que hay que
    verificar es por tanto que las diferencias coinciden, no los valores."""
    T = t_C + 273.15
    w = 0.5 * psy.w_saturation(T)
    d_modelo = psy.enthalpy(T, w) - psy.enthalpy(T - 5.0, w)
    d_ref = (CP.HAPropsSI("H", "T", T, "P", P, "W", w)
             - CP.HAPropsSI("H", "T", T - 5.0, "P", P, "W", w))
    assert rel(d_modelo, d_ref) < 0.005


def test_bulbo_humedo_reproduce_la_condicion_nominal_EN14511():
    """7 °C bs / 6 °C bh es la condición nominal de la tabla 9.20."""
    T, T_wb = 280.15, 279.15
    w = psy.wet_bulb_humidity_ratio(T, T_wb)
    assert rel(w, CP.HAPropsSI("W", "T", T, "P", P, "B", T_wb)) < 0.01
    assert rel(psy.wet_bulb(T, w), T_wb) < 1e-4       # inversa consistente
    assert 4.5 < psy.dew_point(w) - 273.15 < 5.5


def test_el_punto_de_ficha_reproduce_la_humedad_declarada(df=None):
    """§9.7.6: la ficha declara 17.80 g/kg con aire a 35 °C y 50 % de HR."""
    assert rel(psy.humidity_ratio(308.15, 0.50), 0.01780) < 0.01


def test_la_densidad_del_aire_de_ficha_es_la_adoptada_en_el_anclaje():
    """1.13 kg/m³ es el valor con el que el §9.7.3 ancló la correlación."""
    assert rel(psy.density(308.15, 0.01777), 1.13) < 0.01
    assert rel(psy.viscosity(308.15), 1.89e-5) < 0.01
    assert rel(psy.prandtl(308.15, 0.01777), 0.71) < 0.02


# ---------------------------------------------------------------------------
# Inversas: son las que la marcha usa dentro del lazo por celda
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t_C", DOMINIO)
def test_las_inversas_son_consistentes(t_C):
    T = t_C + 273.15
    w = 0.6 * psy.w_saturation(T)
    h = psy.enthalpy(T, w)
    assert rel(psy.temperature_from_enthalpy(h, w), T) < 1e-9
    assert rel(psy.humidity_from_enthalpy(h, T), w) < 1e-9
    assert abs(psy.saturation_temperature(psy.saturation_enthalpy(T)) - T) < 1e-6


def test_el_rocio_es_el_umbral_de_saturacion():
    T, RH = 280.15, 0.87
    w = psy.humidity_ratio(T, RH)
    T_d = psy.dew_point(w)
    assert rel(psy.w_saturation(T_d), w) < 1e-4
    assert T_d < T


# ---------------------------------------------------------------------------
# §9.7.6 — el valor declarado por el capítulo
# ---------------------------------------------------------------------------
def test_el_1781_del_capitulo_no_esta_en_la_temperatura_que_declara():
    """DISCREPANCIA REPORTADA, no resuelta en el código.

    El §9.7.6 declara b' = 1781 J/(kg·K) «con una temperatura superficial del
    orden de 1 °C», y la ec. 9-29 define b' = dh_sat/dT|_{T_s}. Pero 1781 es el
    valor a 1.6 °C —la T_evap de la primera fila de la tabla 9.20—, no a 1 °C
    ni en la superficie, que en ese punto está a ~3 °C.

    Es un error de redacción, no de resultado: la eficiencia de aleta húmeda
    pasa de 0.337 a 0.336 y la efectividad superficial sigue siendo 0.358.
    """
    assert rel(psy.saturation_enthalpy_slope(1.6 + 273.15), 1781.0) < 0.002
    assert rel(psy.saturation_enthalpy_slope(1.0 + 273.15), 1781.0) > 0.015
    # el factor 1.77 veces cp que declara el capítulo es el de 1.6 °C
    assert rel(psy.saturation_enthalpy_slope(1.6 + 273.15) / psy.CP_DRY_AIR,
               1.77) < 0.005


def test_el_numero_de_lewis_esta_declarado_como_hipotesis():
    """§9.7.6: la analogía calor-masa con Le = 1 es hipótesis estándar y se
    declara como tal. Está expuesta como constante para que el cap. 10 pueda
    cuantificar el efecto de relajarla."""
    assert psy.LEWIS_NUMBER == 1.0


def test_la_curva_conmuta_a_hielo_bajo_cero():
    """§9.7.6: con aire a 2 °C la evaporación se sitúa en −2.9 °C, esto es,
    dentro del dominio de escarcha. Es la curva sobre HIELO la que gobierna el
    depósito, y la presión de saturación sobre hielo es menor que sobre agua
    subenfriada a la misma temperatura."""
    T = 268.15
    assert psy.p_sat(T) < 401.8 * 1.02
    assert psy.p_sat(T) == pytest.approx(401.8, rel=0.01)
    # Las dos ramas de ASHRAE no empalman exactamente en el punto triple: la de
    # hielo da 610.7 Pa y la de agua 611.7, un salto del 0.16 %. Es el error
    # propio de la correlación, no del modelo, y queda tres órdenes por debajo
    # de la incertidumbre de la correlación de aire. Se acota y se declara.
    assert rel(psy.p_sat(273.14), psy.p_sat(273.16)) < 0.002
