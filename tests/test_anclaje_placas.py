"""Anclaje del condensador de placas sobre su punto de selección. §9.6.4.

La ficha del AlfaNova 27-30H es al condensador de placas lo que el punto de
ficha de la batería es al serpentín: el único punto de operación disponible.
A diferencia de aquel, trae DOS datos independientes —el térmico y el
hidráulico—, y la correlación de Martin los liga a través del ángulo de
corrugación. Eso permite identificar β y anclar φc·φv, que es lo que saca al
submodelo de placas del atasco del §9.6.4.
"""
import math

import pytest

from amoniatermia import Fluid
from amoniatermia import data as D
from amoniatermia.components.plate_hx import (PlateHeatExchanger,
                                              anchor_from_selection_point)
from amoniatermia.correlations import available, get, info

TOL = 0.02


def rel(a, b):
    return abs(a - b) / abs(b)


@pytest.fixture(scope="module")
def anclaje():
    return anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"))


@pytest.fixture(scope="module")
def df():
    return D.load("placas_alfanova")


# ---------------------------------------------------------------------------
# El vínculo: Martin liga fricción y transferencia por el ángulo
# ---------------------------------------------------------------------------

def test_la_friccion_de_martin_esta_registrada_y_exige_el_angulo():
    """Es el único vínculo que permite identificar β desde una pérdida de carga
    medida, y por eso tiene que ser invocable por nombre. Sin ángulo falla, en
    lugar de adoptar uno implícito."""
    f = get("friction", "martin_vdi")
    assert "martin_vdi" in available("friction")
    with pytest.raises(ValueError):
        f(800.0)
    assert f(800.0, beta_c=math.radians(60.0)) > 0.0
    # a mayor ángulo, más fricción: es lo que hace invertible la relación
    assert (f(800.0, beta_c=math.radians(70.0))
            > f(800.0, beta_c=math.radians(50.0)))


def test_con_angulo_nulo_martin_degenera_en_conducto_liso():
    """Comprobación del convenio de ángulo: se mide desde la DIRECCIÓN DE FLUJO,
    de modo que β = 0 es corrugación alineada con el flujo y debe dar el factor
    de fricción liso. La literatura usa también el convenio complementario, y
    confundirlos intercambia una placa L por una H."""
    f = get("friction", "martin_vdi")
    assert rel(f(800.0, beta_c=1e-9), 16.0 / 800.0) < 1e-6      # Fanning laminar


# ---------------------------------------------------------------------------
# La identificación
# ---------------------------------------------------------------------------

def test_el_angulo_identificado_es_de_placa_H(anclaje, df):
    """El resultado que cierra el dato, y su corroboración independiente.

    β sale de la pérdida de carga del agua, 7.93 kPa a 1.83 m³/h. La ficha, por
    otra vía que nada tiene que ver, designa los 29 canales como H, de alta
    transferencia. Un ángulo de 71° es de placa H: las dos informaciones son
    ajenas entre sí y coinciden.
    """
    g = df.require("unidades.condensador_climatizacion.geometria")
    assert rel(anclaje.beta_c_deg, g["angulo_corrugacion_deg"]) < TOL
    assert 60.0 < anclaje.beta_c_deg < 80.0          # zona de placa H
    assert "H" in g["nomenclatura_H"]
    assert g["angulo_procedencia"].startswith("IDENTIFICADO")


@pytest.mark.parametrize("phi", [1.10, 1.15, 1.20, 1.25, 1.30])
def test_el_angulo_es_robusto_al_factor_de_alargamiento(phi, df):
    """Lo que hace utilizable la identificación. Φ sigue estimado y entra tres
    veces —en D_h, en el área desarrollada y en el Reynolds—, pero β apenas se
    mueve: 68.7 a 72.7° sobre toda la banda. El resultado no descansa sobre la
    suposición que queda abierta."""
    a = anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"), phi=phi)
    lo, hi = df.require("unidades.condensador_climatizacion.geometria."
                        "angulo_banda_deg")
    assert lo <= a.beta_c_deg <= hi


@pytest.mark.parametrize("dp_puerto", [0.0, 200.0, 400.0, 800.0])
def test_el_angulo_es_robusto_a_la_perdida_de_puerto(dp_puerto):
    """La Δp de ficha incluye las pérdidas de entrada y salida, que no son de
    la placa. Descontarlas entre 0 y el 10 % mueve β menos de 2.5°."""
    a = anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"),
                                    port_loss_Pa=dp_puerto)
    assert 69.0 < a.beta_c_deg < 74.0


def test_el_producto_esta_anclado_pero_NO_es_robusto(anclaje, df):
    """La otra cara, y hay que declararla con la misma claridad.

    φc·φv sí depende de lo que sigue supuesto: recorrer Φ de 1.10 a 1.30 lo
    mueve de 1.78 a 1.12, un factor 1.6, y cambiar el convenio de área de
    desarrollada a proyectada lo lleva a 2.37. El número no significa nada solo:
    debe viajar SIEMPRE con el Φ y el convenio con que se obtuvo.
    """
    ref = df.require("producto_phi_c_phi_v")
    assert rel(anclaje.phi_c_phi_v, ref["valor"]) < TOL
    assert ref["phi_adoptado"] == anclaje.phi_adoptado
    assert ref["convenio_area"] == "developed"

    bajo = anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"), phi=1.30)
    alto = anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"), phi=1.10)
    assert alto.phi_c_phi_v / bajo.phi_c_phi_v > 1.4      # NO es robusto
    proy = anchor_from_selection_point(Fluid("Ammonia"), Fluid("Water"),
                                       area_convention="projected")
    assert proy.phi_c_phi_v > 1.4 * anclaje.phi_c_phi_v
    assert proy.beta_c_deg == pytest.approx(anclaje.beta_c_deg)   # β no depende


def test_el_reparto_de_resistencias_del_condensador_de_placas(anclaje):
    """A diferencia de la batería, donde el aire se lleva el 73 %, aquí manda el
    agua con el 59 %, y la pared de inoxidable pesa casi un 10 %: la misma razón
    —RS-1 excluye el cobre— con el mismo efecto."""
    r = anclaje.reparto
    assert sum(r.values()) == pytest.approx(1.0)
    assert 0.5 < r["agua"] < 0.65
    assert 0.25 < r["refrigerante"] < 0.40
    assert r["pared"] > 0.05                  # con cobre sería despreciable
    assert anclaje.alpha_refrigerante > anclaje.alpha_agua


def test_el_ensuciamiento_no_se_cuenta_dos_veces(anclaje, df):
    """El U de servicio de ficha lo lleva dentro; el anclaje trabaja sobre el
    limpio. Restarlo otra vez se llevaría por delante el lado de refrigerante
    entero, porque 2.7e-4 es casi la resistencia global completa."""
    R_f = df.require("unidades.condensador_climatizacion.geometria."
                     "resistencia_ensuciamiento_m2K_W")
    A = 1.15 * 28 * 0.111 * 0.250                   # area desarrollada
    R_total = A / anclaje.UA_limpio
    assert R_f > 0.9 * R_total          # restarlo otra vez agotaria el reparto
    assert anclaje.reparto["refrigerante"] > 0.2    # y no se agota


# ---------------------------------------------------------------------------
# Lo que el anclaje deja cerrado, y lo que no
# ---------------------------------------------------------------------------

def test_el_condensador_de_placas_ya_se_construye_sin_inyectar_nada():
    """Era el atasco: `plate_geometry` fallaba con MissingData por el ángulo y
    el factor de alargamiento, y los modos con placas eran exploratorios."""
    g = D.plate_geometry("condensador_climatizacion")
    assert g.beta_c > 0.0 and g.phi > 0.0 and g.b > 0.0
    assert g.R_f > 0.0                              # y con el ensuciamiento


def test_el_modelo_reproduce_el_punto_de_seleccion_de_extremo_a_extremo(df):
    """Verificación de que el anclaje está bien conectado, no solo bien hecho.

    Se marcha el componente completo en sus condiciones de ficha. El residuo del
    3 % es del método: el anclaje se hizo con la MTD agregada y la marcha
    resuelve celda a celda con la diferencia local.
    """
    f, w = Fluid("Ammonia"), Fluid("Water")
    pt = df.require("unidades.condensador_climatizacion.punto_diseno")
    hx = PlateHeatExchanger(f, w, D.plate_geometry("condensador_climatizacion"),
                            n_cells=80, role="condenser")
    P = f.Psat(pt["T_cond_C"] + 273.15)
    f.update_PQ(P, 1.0)
    r = hx.solve(P, f.h, 35.73 / 3600, pt["agua_T_in_C"] + 273.15,
                 pt["agua_caudal_m3_h"] / 3600 * 990.8)
    assert rel(-r.Q_dot, pt["Q_W"]) < 0.05
    assert abs(r.T_sec_out - 273.15 - pt["agua_T_out_C"]) < 0.5


def test_phi_c_y_phi_v_por_separado_siguen_pendientes(df):
    """Lo identificado es el PRODUCTO, que es lo único que interviene en la
    ec. 9-17. Separarlos exige un segundo punto a otra velocidad de vapor,
    igual que C₁ y C₂ del §9.7.3 no se separaron con un solo punto."""
    for clave in ("phi_c", "phi_v"):
        with pytest.raises(D.MissingData):
            df.require(f"pendientes.{clave}")
    ci = info("plate_condensation", "nusselt_film_anclada_27_30H")
    assert "PRODUCTO" in ci.validity.notes
    assert ci.validity.fluids == ("Ammonia",)


def test_el_anclaje_se_marca_fuera_de_su_dominio():
    """El anclaje es de CONDENSACIÓN a 50 °C. Usarlo lejos de ahí extrapola el
    anclaje, no solo la correlación, y el registro debe decirlo."""
    from amoniatermia import ExtrapolationLog

    log = ExtrapolationLog()
    log.check("plate_condensation", "nusselt_film_anclada_27_30H",
              T_sat=323.15, dT=2.3)
    assert not log.extrapolated                     # el punto de anclaje
    log.check("plate_condensation", "nusselt_film_anclada_27_30H",
              T_sat=280.0, dT=2.3)
    assert log.extrapolated                         # como evaporador, fuera


def test_la_caida_declarada_del_amoniaco_no_puede_ser_la_neta(df):
    """La ficha declara 58 Pa en el lado de amoníaco. El modelo da −143 Pa
    netos, porque la columna de 0.25 m aporta −270 Pa y domina sobre los 128 Pa
    de fricción.

    Corrobora lo que el apartado 7 del plan ya pedía para el §9.6.6: los 58 Pa
    no pueden ser el cambio neto de presión de un condensador vertical
    descendente, de modo que o son solo la contribución friccional o el montaje
    es ascendente. El capítulo debe declarar el sentido de montaje.
    """
    f, w = Fluid("Ammonia"), Fluid("Water")
    hx = PlateHeatExchanger(f, w, D.plate_geometry("condensador_climatizacion"),
                            n_cells=60, role="condenser")
    P = f.Psat(50 + 273.15)
    f.update_PQ(P, 1.0)
    r = hx.solve(P, f.h, 35.73 / 3600, 40 + 273.15, 1.83 / 3600 * 990.8)
    dp_ficha = df.require("unidades.condensador_climatizacion.punto_diseno."
                          "dp_amoniaco_Pa")
    assert r.dP_parts["gravitatoria"] < -2.0 * dp_ficha
    assert r.dP_ref < 0.0                            # gana presion
    assert r.dP_parts["friccional"] > 0.0
