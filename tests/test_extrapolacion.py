"""Marcado de resultados extrapolados.

CLAUDE.md, «Lo que el modelo debe reportar»: marcar como extrapolado cualquier
resultado en que una correlación opere fuera de su base experimental.

El mecanismo distingue dos situaciones que no son la misma:

- la correlación declara su base y el punto se sale de ella;
- la correlación no declara base alguna, de modo que no hay nada contra lo que
  comparar. La antigua tabla 10.7 deja expresamente sin fijar los coeficientes de varias
  correlaciones, así que hoy este es el caso mayoritario, y tratarlo como «sin
  incidencias» sería justo el silencio que la regla prohíbe.
"""
import math

import pytest

from amoniatermia.correlations import (
    ExtrapolationLog, OutOfRange, Validity, available, families, get, info,
    register)


# ---------------------------------------------------------------------------
# Metadatos del registro
# ---------------------------------------------------------------------------

def test_toda_correlacion_registrada_declara_referencia():
    """§9.6.4: cada correlación viaja con su fuente. Recopilarlas al final,
    sobre código ya escrito, es más lento y más propenso a error."""
    sin_referencia = [(f, n) for f in families() for n in available(f)
                      if not info(f, n).reference]
    assert sin_referencia == []


def test_la_validez_no_declarada_no_equivale_a_validez_universal():
    """`chevron_generic` tiene C y m provisionales (antigua tabla 10.7): no puede
    certificar ningún resultado como dentro de rango."""
    assert info("singlephase", "chevron_generic").validity_declared is False
    log = ExtrapolationLog()
    log.check("singlephase", "chevron_generic", Re=3000.0)
    assert log.extrapolated
    assert log.excursions[0].undeclared


def test_correlacion_con_base_declarada_dentro_de_rango_no_marca():
    """Dittus-Boelter es la única con rango declarado hoy: Re > 1e4, Pr 0.6-160."""
    log = ExtrapolationLog()
    log.check("singlephase", "dittus_boelter", Re=5.0e4, Pr=3.0)
    assert not log.extrapolated
    assert log.report().startswith("Sin excursiones")


def test_correlacion_fuera_de_rango_se_marca():
    """El contraste que exige CLAUDE.md, y que el §9.12.5 pide automatizado."""
    log = ExtrapolationLog()
    log.check("singlephase", "dittus_boelter", Re=1.2e3, Pr=3.0)
    assert log.extrapolated
    e = log.excursions[0]
    assert e.variable == "Re"
    assert not e.undeclared
    assert e.low == pytest.approx(1.0e4)
    assert "fuera de" in str(e)


def test_el_modo_estricto_detiene_el_calculo():
    """Útil en verificación: convierte la marca en un fallo."""
    log = ExtrapolationLog(strict=True)
    with pytest.raises(OutOfRange, match="Re="):
        log.check("singlephase", "dittus_boelter", Re=1.2e3, Pr=3.0)


def test_las_excursiones_se_agregan_y_no_se_acumulan_una_por_evaluacion():
    """Con ~1e5 evaluaciones por punto resuelto (§9.12.4) una lista plana
    sería inmanejable. Interesa el rango recorrido y el recuento."""
    log = ExtrapolationLog()
    for re in (1.0e3, 5.0e3, 2.0e3):
        log.check("singlephase", "dittus_boelter", Re=re, Pr=3.0)
    assert len(log.excursions) == 1
    e = log.excursions[0]
    assert e.count == 3
    assert e.value_min == pytest.approx(1.0e3)
    assert e.value_max == pytest.approx(5.0e3)


def test_la_marca_viaja_en_el_resultado_del_intercambiador():
    """Un resultado extrapolado no es inválido, pero tampoco está soportado: la
    marca debe llegar a la salida, no quedarse en el componente."""
    from amoniatermia.components.plate_hx import PlateHeatExchanger
    from amoniatermia.geometry import PlateGeometry
    from amoniatermia.props import Fluid

    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    hx = PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom, n_cells=10,
                            corr_params={"plate_condensation": {"phi_c": 1.0,
                                                          "phi_v": 1.0}})
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)

    # `chevron_generic` no declara base experimental (antigua tabla 10.7)
    assert r.extrapolated
    assert any(e.undeclared for e in r.excursions)
    assert r.excursions[0].count > 0


def test_as_dict_es_serializable_para_adjuntar_a_los_resultados():
    log = ExtrapolationLog()
    log.check("singlephase", "dittus_boelter", Re=1.2e3, Pr=3.0)
    d = log.as_dict()
    assert d["extrapolado"] is True
    assert d["excursiones"][0]["variable"] == "Re"
    import json
    json.dumps(d)          # no debe lanzar


# ---------------------------------------------------------------------------
# Intercambiabilidad
# ---------------------------------------------------------------------------

def test_registrar_en_una_familia_inexistente_falla():
    with pytest.raises(KeyError, match="Familia desconocida"):
        register("no_existe", "x")(lambda: None)


def test_get_de_un_nombre_no_registrado_enumera_los_disponibles():
    with pytest.raises(KeyError, match="Disponibles"):
        get("plate_boiling", "inexistente")


def test_la_banda_de_ebullicion_en_placas_tiene_dos_formulaciones():
    """Vacío V-1: no hay correlación específica de NH3 en placas. La banda de
    ebullición tiene dos formulaciones, y las dos comparten Cooper y los
    factores F y S: es más estrecha de lo que aparenta y el §9.13 lo declara.
    El marcador que ocupaba el tercer puesto se retiró el 28/09/2026: una
    correlación registrada que solo lanza una excepción no es una alternativa."""
    assert set(available("plate_boiling")) == {"additive_cooper",
                                                "asymptotic_cooper"}


# ---------------------------------------------------------------------------
# Limites redondeados y registro por componente (28/09/2026)
# ---------------------------------------------------------------------------

def test_el_punto_de_anclaje_no_sale_marcado_por_el_redondeo_del_limite():
    """El Re_Dc del punto de ficha es 4189.9 y el capitulo publica 4190: sin
    la tolerancia de los limites, el propio anclaje salia como extrapolado."""
    log = ExtrapolationLog()
    log.check("airside", "colburn_anclada_cbn21", Re_Dc=4189.9)
    assert not log.extrapolated
    log.check("airside", "colburn_anclada_cbn21", Re_Dc=4100.0)
    assert log.extrapolated


def test_el_registro_de_un_componente_reenvia_al_del_punto():
    """Cada componente lleva SOLO sus excursiones; el punto, todas."""
    punto = ExtrapolationLog()
    a = ExtrapolationLog(parent=punto)
    b = ExtrapolationLog(parent=punto)
    a.check("airside", "colburn_anclada_cbn21", Re_Dc=4000.0)
    b.check("fin", "schmidt_annular")
    assert {e.family for e in a.excursions} == {"airside"}
    assert {e.family for e in b.excursions} == {"fin"}
    assert {e.family for e in punto.excursions} == {"airside", "fin"}
