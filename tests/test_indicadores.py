"""Indicadores energéticos y exergéticos. §9.11, ecuaciones 9-34 a 9-36.

Las métricas de decisión de H1 y H6 salen de aquí: la tabla 6.2 contrasta H1
por «desviación media y máxima en COP y potencia térmica» y H6 por «cociente
de destrucción de exergía del compresor sobre el total».
"""
import math

import pytest

from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid, MODES,
                          PlateHeatExchanger, SemiEmpiricalCompressor,
                          Setpoints, WaterStream)
from amoniatermia import data as D
from amoniatermia import indicators as I
from amoniatermia import psychrometrics as psy


def _circuito(n_seg=40, n_cel=8):
    f = Fluid("Ammonia")
    return f, Circuit(
        f, SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params()),
        AirCoil(f, D.air_coil_geometry(), n_segments=n_seg),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("condensador_climatizacion"),
                           n_cells=n_cel),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("desrecalentador_acs"),
                           n_cells=n_cel))


SP = Setpoints(superheat=5.0, subcooling=2.0, T_acs=60 + 273.15)
VERANO = dict(air=AirState(T=35 + 273.15, V_frontal=3.30),
              m_dot_air=None, T_amb=35 + 273.15)
INVIERNO = dict(air=AirState.at(T=7 + 273.15, V_frontal=3.30,
                                T_wb=6 + 273.15),
                m_dot_air=None, T_amb=7 + 273.15)


@pytest.fixture(scope="module")
def m1():
    _, c = _circuito()
    bc = Boundary(clima=WaterStream(T_in=12 + 273.15, m_dot=0.45),
                  acs=WaterStream(T_in=10 + 273.15), **VERANO)
    return c.solve("M-2", bc, SP), MODES["M-2"]


@pytest.fixture(scope="module")
def m3():
    _, c = _circuito()
    bc = Boundary(clima=WaterStream(T_in=12 + 273.15, m_dot=0.45),
                  acs=WaterStream(T_in=10 + 273.15), **VERANO)
    return c.solve("M-1", bc, SP), MODES["M-1"]


@pytest.fixture(scope="module")
def m4():
    _, c = _circuito()
    bc = Boundary(clima=WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion()),
                  acs=WaterStream(T_in=10 + 273.15), **INVIERNO)
    return c.solve("M-3", bc, SP), MODES["M-3"]


# ---------------------------------------------------------------------------
# §9.11.1 — indicadores energéticos, ec. 9-34 y 9-34
# ---------------------------------------------------------------------------

def test_el_ventilador_esta_en_el_denominador(m1):
    """§9.7.7: la UNE-EN 14511 lo exige, «de modo que omitirlo produciría
    valores de COP y EER no comparables con los de los equipos comerciales,
    que es precisamente la comparación que sostiene la hipótesis H1».

    Con 780 W frente a ~2.7 kW del compresor, omitirlo inflaría el EER en
    torno a un 30 %.
    """
    sol, spec = m1
    e = I.energy(sol, spec)
    assert e.W_fan == pytest.approx(780.0)
    assert e.W_el == pytest.approx(e.W_el_compresor + e.W_fan)
    sin_ventilador = e.Q_util_clima / e.W_el_compresor
    assert sin_ventilador / e.EER - 1.0 > 0.25


def test_la_potencia_electrica_no_es_la_del_eje(m1):
    """§9.5.2: el compresor es ABIERTO y su motor externo no disipa al
    refrigerante. La distinción «no es un detalle contable»: es lo que permite
    separar la irreversibilidad de compresión de la pérdida de conversión."""
    sol, spec = m1
    e = I.energy(sol, spec)
    assert e.W_el_compresor > sol.W_shaft
    assert e.W_el_compresor / sol.W_shaft == pytest.approx(1 / (0.90 * 0.98),
                                                           rel=1e-6)


def test_sin_rendimientos_declarados_no_hay_indicador(m1):
    """CLAUDE.md: un dato que no existe hace fallar al cálculo, no lo rellena.
    Sin eta_motor no hay denominador y los indicadores no pueden calcularse."""
    sol, spec = m1
    comp = sol.components["compresor"]
    original = comp.W_el
    try:
        comp.W_el = None
        with pytest.raises(I.MissingElectricalData, match="eta_motor"):
            I.energy(sol, spec)
    finally:
        comp.W_el = original


def test_en_M5_el_producto_va_entero_por_la_via_del_ACS():
    """Qué cuenta como producto no se deduce del signo del calor.

    En M-5 el intercambiador de climatización cede calor exactamente igual que
    en M-4, pero allí lo cede al circuito de fan-coils —y es el servicio— y aquí
    lo cede al agua de ACS, porque los dos intercambiadores de placas trabajan
    para el ACS (tabla 9.3, y decisión del autor del 22/09/2026 que revierte
    D-1 en este modo).

    El modo tiene que declararlo: `clima = "inactivo"` significa que el CIRCUITO
    de climatización no presta servicio, no que su calor se tire.
    """
    assert MODES["M-5"].clima == "inactivo"
    assert MODES["M-4"].clima == "calor"
    assert MODES["M-2"].clima == "frio"
    # Y el intercambiador de climatización va al servicio de ACS, no al suyo.
    from amoniatermia.circuit import CLIMA
    assert MODES["M-5"].secondary[CLIMA] == "acs"


def test_la_recuperacion_sube_el_indicador_global(m3):
    """§9.11.1: en M-1 el calor recuperado «es un subproducto que en ausencia
    de recuperación se disiparía al ambiente». El capítulo exige reportar
    SIEMPRE el indicador por servicio junto al global, y comparar con equipos
    comerciales sobre el primero."""
    sol, spec = m3
    e = I.energy(sol, spec)
    assert e.Q_acs > 0.0
    assert e.COP_global > e.EER
    assert e.por_servicio == e.EER              # el comparable comercialmente
    assert 0.15 < e.recuperacion_aporta < 0.35


def test_el_indicador_se_declara_cota_superior(m1):
    """§6.8.2: omitir la potencia auxiliar «es una fuente frecuente de
    sobreestimación del rendimiento estacional». Las bombas no están
    modeladas, y la marca tiene que viajar con el número."""
    sol, spec = m1
    e = I.energy(sol, spec)
    assert e.W_el_es_cota_inferior
    assert any("bombas" in a for a in e.avisos)


# ---------------------------------------------------------------------------
# §9.11.2 — indicadores exergéticos, ec. 9-35 a 9-36
# ---------------------------------------------------------------------------

def test_la_exergia_destruida_es_T0_por_la_entropia_generada(m1):
    """Teorema de Gouy-Stodola, forma de la derecha de la ec. 9-35. No se
    recalcula por el balance de flujos: las dos vías son algebraicamente la
    misma y la de la entropía ya está verificada como positiva por el
    §9.4.4."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    for k, S in sol.checks["entropia"].items():
        assert x.E_D[k] == pytest.approx(x.T_0 * S)
    assert x.T_0 == sol.boundary.T_amb


def test_las_fracciones_de_destruccion_suman_uno(m1):
    sol, spec = m1
    x = I.exergy(sol, spec)
    assert sum(x.y_D.values()) == pytest.approx(1.0)
    assert all(v >= 0.0 for v in x.E_D.values())


def test_y_D_del_compresor_es_la_metrica_de_H6(m1):
    """Tabla 6.2: H6 se contrasta por el «cociente de destrucción de exergía
    del compresor sobre el total»."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    assert x.y_D_compresor == x.y_D["compresor"]
    assert 0.1 < x.y_D_compresor < 0.5


def test_la_conversion_electromecanica_se_separa_de_la_compresion(m1):
    """§9.5.2 y §9.11.2. Es la separación que «da contenido cuantitativo a la
    hipótesis H6»: la pérdida del motor externo es ajena al ciclo
    termodinámico y se destruye íntegra."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    comp = sol.components["compresor"]
    assert x.E_D_electromecanica == pytest.approx(comp.W_el - comp.W_shaft)
    assert x.E_D_compresion > x.E_D_electromecanica
    assert "compresor_electromecanico" in x.E_D


def test_el_margen_de_velocidad_variable_es_cota_superior(m1):
    """§9.11.2 lo exige declarar: «un variador real introduce sus propias
    pérdidas de conmutación y de armónicos, y la eficiencia del motor a
    velocidad parcial no coincide con la nominal». El cap. 11 no debe
    presentar esta cifra íntegra como margen capturable."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    assert x.margen_velocidad_variable == x.E_D_electromecanica
    assert "cota superior" in I.ExergyIndicators.margen_velocidad_variable.__doc__.lower()


def test_eta_II_es_una_EFICIENCIA_y_no_una_perdida(m1):
    """§9.11.2 y §6.9 lo marcan expresamente como error a corregir de la
    Rev10: «el cociente entre el rendimiento real y el de Carnot es la
    eficiencia de segunda ley, no una pérdida. La pérdida es su complemento a
    la unidad»."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    assert 0.0 < x.eta_II < 1.0
    assert x.perdida_segunda_ley == pytest.approx(1.0 - x.eta_II)
    e = I.energy(sol, spec)
    assert x.eta_II == pytest.approx(e.EER / x.COP_Carnot)


def test_el_Carnot_se_forma_con_los_focos_y_no_con_el_refrigerante(m1):
    """Decisión de modelado declarada: tomar las saturaciones del refrigerante
    ocultaría dentro del Carnot el salto térmico de los intercambiadores, que
    es justo una de las irreversibilidades que el análisis quiere localizar."""
    sol, spec = m1
    x = I.exergy(sol, spec)
    assert x.T_foco_caliente == pytest.approx(sol.boundary.air.T)
    assert x.T_foco_frio < sol.boundary.clima.T_in + 1.0
    # y el Carnot de los focos es MENOS exigente que el del refrigerante
    carnot_ref = sol.T_evap / (sol.T_cond - sol.T_evap)
    assert x.COP_Carnot > carnot_ref


# ---------------------------------------------------------------------------
# El cierre exergético: verificación, no resultado
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("caso", ["m1", "m3", "m4"])
def test_el_balance_exergetico_cierra(caso, request):
    """La exergía eléctrica que entra tiene que salir como producto o
    destruirse. Es la verificación que descubrió que el lado de aire del
    serpentín no contabilizaba la entropía del condensado."""
    sol, spec = request.getfixturevalue(caso)
    x = I.exergy(sol, spec)
    assert x.balance_cierra, f"cierre {100 * x.cierre:+.1f} %"


def test_el_cierre_detecta_un_componente_que_falta():
    """Con el lado de baja sin modelar —la configuración del §9.7.8, con la
    evaporación impuesta— falta el evaporador en el reparto de la ec. 9-35, y
    el cierre debe decirlo en lugar de dar un reparto plausible."""
    f = Fluid("Ammonia")
    c = Circuit(f, SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                           D.compressor_params()),
                AirCoil(f, D.air_coil_geometry(), n_segments=60), None, None)
    bc = Boundary(clima=WaterStream(T_in=12 + 273.15, m_dot=0.48), **VERANO)
    sol = c.solve("M-2", bc, Setpoints(superheat=1.0, subcooling=0.0,
                                       T_evap=2 + 273.15))
    x = I.exergy(sol, MODES["M-2"])
    assert not x.balance_cierra
    assert any("no instanciado" in a or "NO CIERRA" in a or "sin repartir" in a
               for a in x.avisos)


# ---------------------------------------------------------------------------
# El hallazgo: la exergía del ACS depende del estado muerto
# ---------------------------------------------------------------------------

def test_en_verano_el_ACS_tiene_energia_pero_no_exergia(m3):
    """HALLAZGO, y tiene consecuencia sobre H3 y H6.

    Con el estado muerto en el ambiente simulado —35 °C en refrigeración— el
    ACS de 10 a 60 °C tiene exergía prácticamente nula: la mitad del
    calentamiento ocurre POR DEBAJO del ambiente. El COP global sube un 23 %
    por la recuperación y el rendimiento de segunda ley no se mueve.

    La lectura energética y la exergética dicen cosas distintas del mismo
    subproducto, y el capítulo 11 tiene que elegir con cuál argumenta H3.
    """
    sol, spec = m3
    x = I.exergy(sol, spec)
    e = I.energy(sol, spec)
    assert e.Q_acs > 2000.0                       # energía, mucha
    assert abs(x.Ex_productos["acs"]) < 0.02 * e.Q_acs   # exergía, ninguna
    assert any("exergia del ACS" in a for a in x.avisos)
    # Cifras del §9.11.2 con la malla GRUESA de estas pruebas (40 segmentos,
    # 8 volumenes), remedidas el 25/09/2026: 2291 W, -5.0 W y un 24.0 %. Las que
    # se publican son las de la malla de trabajo, en docs/cifras_capitulo_9.md
    # (2338 W, -5.1 W, 24.5 %); la v30 publica 2238 W, -5 W y 23.5 %.
    # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: con 8 volúmenes el desrecalentador condensa, y el
    # volumen que seguía al recorte en h_v se marchaba como vapor. Ahora 2445 W,
    # -5.4 W y un 25.6 % (antes 2291 W, -5.0 W, 24.0 %).
    assert abs(e.Q_acs - 2445.3) < 15.0
    assert abs(x.Ex_productos["acs"] - (-5.38)) < 0.5
    assert abs(e.COP_global / e.EER - 1.0 - 0.256) < 0.003


def test_en_invierno_el_mismo_ACS_si_tiene_exergia(m4):
    """El contraste que cierra el argumento: con el ambiente a 7 °C el mismo
    salto de 10 a 60 °C sí tiene valor exergético. No es una propiedad del
    ACS, es del estado muerto.

    El §6.9 declara que «la elección del estado muerto afecta a los valores
    absolutos de exergía pero no a la ordenación relativa de las
    irreversibilidades entre componentes». Es cierto para las
    irreversibilidades y NO lo es para la exergía de los productos, que cambia
    de signo. Conviene que el capítulo lo matice.
    """
    sol, spec = m4
    x = I.exergy(sol, spec)
    e = I.energy(sol, spec)
    assert x.Ex_productos["acs"] > 0.05 * e.Q_acs
    # §9.11.2 con la malla gruesa: +258.6 W (malla de trabajo, en
    # docs/cifras_capitulo_9.md: +263.7 W; la v30 publica +252 W).
    # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: 277.8 W (antes 258.6 W).
    # Remedido el 01/10/2026 con el caudal único de 0.45 kg/s (antes 0.35): 267.1 W.
    assert abs(x.Ex_productos["acs"] - 267.1) < 3.0


# ---------------------------------------------------------------------------
# Un punto no válido no es un resultado
# ---------------------------------------------------------------------------

def test_un_punto_no_convergido_se_marca(m4):
    """§6.12: los casos de no convergencia «se registran y se reportan, en
    lugar de ser descartados silenciosamente». Se calculan, pero la marca
    viaja con el número."""
    sol, spec = m4
    e = I.energy(sol, spec)
    if not sol.converged:
        assert any("NO CONVERGIDO" in a for a in e.avisos)
    elif not sol.valid:
        assert any("no valido" in a for a in e.avisos)


def test_el_informe_reune_todo(m3):
    sol, spec = m3
    txt = I.report(sol, spec)
    for clave in ("W_el", "EER", "COP global", "Exergia destruida",
                  "y_D", "cierre del balance", "eta_II", "AVISO"):
        assert clave in txt


# ---------------------------------------------------------------------------
# La entropía del aire húmedo, que es lo que el cierre destapó
# ---------------------------------------------------------------------------

def test_la_entropia_del_aire_humedo_reproduce_a_coolprop():
    import CoolProp.CoolProp as CP

    for T, w in ((280.15, 0.0054), (300.0, 0.0100), (308.15, 0.0178)):
        ref = CP.HAPropsSI("S", "T", T, "P", psy.P_ATM, "W", w)
        assert abs(psy.entropy(T, w) - ref) < 0.5      # J/(kg aire seco K)


def test_con_serpentin_seco_el_termino_latente_no_actua(m1):
    """En M-2 la batería condensa sobre superficie seca: la entropía del aire
    es la sensible de siempre y la corrección no debe cambiar nada."""
    sol, _ = m1
    r = sol.components["bateria"]
    bc = sol.boundary
    assert r.m_condensate == 0.0
    sensible = bc.m_dot_air * bc.air.cp * math.log(r.T_air_out / bc.air.T)
    assert Circuit._dS_aire(r, bc) == pytest.approx(sensible)


def test_con_serpentin_humedo_el_termino_latente_domina(m4):
    """REGRESIÓN del error que el cierre exergético descubrió. Con la
    superficie húmeda, omitir la entropía del condensado dejaba la generación
    del serpentín en un factor veinte por encima de la real."""
    sol, _ = m4
    r = sol.components["bateria"]
    bc = sol.boundary
    assert r.m_condensate > 0.0
    sensible = bc.m_dot_air * bc.air.cp * math.log(r.T_air_out / bc.air.T)
    completo = Circuit._dS_aire(r, bc)
    assert completo < sensible                     # el latente resta
    assert abs(completo) > 1.4 * abs(sensible)
