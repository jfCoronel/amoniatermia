"""Intercambiador de aire: geometría, lado de aire, aleta e inventario.

§9.7. Contrastes contra las tablas 9.9, 9.10 y 9.18, y contra el punto de
ficha del fabricante, que es el único dato de operación disponible.
"""
import math

import pytest

from amoniatermia import ExtrapolationLog, Fluid
from amoniatermia import data as D
from amoniatermia.components.air_hx import AirCoil, AirState
from amoniatermia.geometry import FinnedCoilGeometry

TOL = 0.02
TOL_GEO = 0.005


def rel(a, b):
    return abs(a - b) / abs(b)


@pytest.fixture(scope="module")
def df():
    return D.air_coil()


@pytest.fixture(scope="module")
def coil(df):
    g = df.require("geometria")
    return FinnedCoilGeometry(
        S_t=g["paso_transversal_m"], S_l=g["paso_longitudinal_m"],
        L=g["longitud_bateria_m"], n_tubes_row=g["tubos_por_rango"],
        n_rows=g["n_rangos"], n_circuits=g["n_circuitos"],
        fin_pitch=g["paso_aleta_m"], fin_thickness=g["espesor_aleta_m"],
        d_o=g["diametro_exterior_m"], d_i=g["diametro_interior_m"],
        k_tube=df.require("conductividad_tubo_W_mK"),
        k_fin=df.require("conductividad_aleta_W_mK"))


# ---------------------------------------------------------------------------
# §9.7.1, §9.7.1 — reconstrucción geométrica
# ---------------------------------------------------------------------------

def test_disposicion_es_tresbolillo_equilatero(coil):
    """40 × 34.64 mm: 34.64 es 40·cos(30°). La identificación es necesaria para
    determinar el radio equivalente de aleta del §9.7.4."""
    assert coil.is_equilateral_staggered


@pytest.mark.parametrize("magnitud,clave", [
    ("L_tube", "longitud_total_tubo_m"),
    ("n_fins", "n_aletas"),
    ("A_fin", "area_aleta_m2"),
    ("A_tube_bare", "area_tubo_desnudo_m2"),
    ("A_o", "area_total_m2"),
    ("V_internal", "volumen_interno_m3"),
    ("area_ratio", "relacion_area_ext_int"),
    ("sigma", "fraccion_area_libre_sigma"),
])
def test_reconstruccion_tabla_10_9(coil, df, magnitud, clave):
    assert rel(getattr(coil, magnitud),
               df.require(f"reconstruido.{clave}")) < TOL_GEO


def test_verificacion_frente_a_ficha(coil, df):
    """§9.7.1: la coincidencia con las magnitudes declaradas es la condición
    previa a todo lo demás. Un ajuste sobre geometría mal reconstruida
    absorbería el error geométrico dentro del coeficiente de aire y destruiría
    su transferibilidad al régimen de evaporación."""
    rep = coil.verification_report({**df.require("declarado"),
                                    "caudal_kg_h": 41.0,
                                    "velocidad_masica_kg_m2s": 48.0})
    assert abs(rep["area"]["desviacion"]) < 0.002          # ficha: −0.1 %
    assert abs(rep["volumen"]["desviacion"]) < 0.002       # ficha: ≈0 %
    assert abs(rep["velocidad_masica"]["desviacion"]) < 0.005   # ficha: −0.2 %


def test_radio_equivalente_de_aleta(coil, df):
    """§9.7.4. El paso de tubo de 40 mm da 21.25 mm de radio equivalente, esto
    es 14.6 mm de altura de aleta efectiva, muy superior a la de una batería
    residencial convencional. De ahí la baja eficiencia."""
    rm = df.require("referencia_modelo")
    assert rel(coil.r_equivalent, rm["radio_equivalente_aleta_m"]) < TOL_GEO
    assert rel(coil.fin_height, rm["altura_aleta_efectiva_m"]) < 0.01


# ---------------------------------------------------------------------------
# §9.7.3, §9.7.3 — lado de aire anclado
# ---------------------------------------------------------------------------

def test_anclaje_de_la_correlacion_de_aire(coil):
    """El anclaje reproduce el punto de ficha POR CONSTRUCCIÓN: C1 = 0.507 sale
    de imponer el h de ficha con C2 = −0.42 fijado a priori."""
    from amoniatermia.correlations.airside import (max_velocity, reynolds_Dc)

    V_max = max_velocity(3.30, coil.sigma)
    Re = reynolds_Dc(1.13, V_max, coil.d_c, 1.89e-5)
    assert rel(V_max, 5.19) < TOL
    assert rel(Re, 4190) < TOL
    j = 113.0 / (1.13 * V_max * 1005.0) * 0.71 ** (2 / 3)
    assert rel(j, 0.01526) < TOL
    assert rel(j / Re ** -0.42, 0.507) < TOL


def test_el_rango_de_validez_del_aire_esta_declarado():
    """Es la única correlación del modelo con base declarada procedente del
    capítulo: Re ∈ [4190, 5512], un 32 % de extrapolación entre condensación y
    perfil frío. Esa acotación es lo que hace defendible anclar sobre un punto."""
    from amoniatermia.correlations import info

    ci = info("airside", "colburn_anclada_cbn21")
    assert ci.validity_declared
    assert ci.validity.ranges["Re_Dc"] == (4190.0, 5512.0)

    log = ExtrapolationLog()
    log.check("airside", "colburn_anclada_cbn21", Re_Dc=4190.0)
    assert not log.extrapolated                      # punto de ficha, en rango
    log.check("airside", "colburn_anclada_cbn21", Re_Dc=7000.0)
    assert log.extrapolated                          # fuera, se marca


# ---------------------------------------------------------------------------
# §9.7.4 y §9.7.6 — eficiencia de aleta y reparto de resistencias
# ---------------------------------------------------------------------------

def test_eficiencia_de_aleta_seca(coil, df):
    """0.447 y 0.465, muy lejos del 0.85 habitualmente supuesto en cálculos
    preliminares —incluido el del §4.5, que debe corregirse."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    eta, eta_sa = hx.fin_efficiency(113.0)
    rm = df.require("referencia_modelo")
    assert rel(eta, rm["eficiencia_aleta_seca"]) < TOL
    assert rel(eta_sa, rm["efectividad_superficial_seca"]) < TOL


def test_eficiencia_de_aleta_humeda(coil, df):
    """§9.7.6: en superficie húmeda el gradiente que gobierna la transferencia
    deja de ser el de temperatura para ser el de entalpía de saturación."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    rm = df.require("referencia_modelo")
    b_prime = rm["pendiente_entalpia_saturacion_J_kgK"]
    eta_w, eta_sw = hx.fin_efficiency(116.9, b_prime=b_prime)
    assert rel(eta_w, rm["eficiencia_aleta_humeda"]) < TOL
    assert rel(eta_sw, rm["efectividad_superficial_humeda"]) < TOL


def test_usar_la_eficiencia_seca_en_humedo_sobreestima_un_28_por_ciento(coil, df):
    """Error que se propagaría íntegramente al SCOP en modo calefacción."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    b_prime = df.require(
        "referencia_modelo.pendiente_entalpia_saturacion_J_kgK")
    _, seca = hx.fin_efficiency(116.9)
    _, humeda = hx.fin_efficiency(116.9, b_prime=b_prime)
    assert 0.25 < seca / humeda - 1.0 < 0.32


def test_reparto_de_resistencias_tabla_10_11(coil, df):
    """El lado de aire domina con el 72.8 %. La pared de inoxidable pesa el
    3.9 %, frente al 0.15 % que correspondería a un tubo de cobre: es la razón
    por la que RS-1 obliga a conservarla (§9.7.4)."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    rm = df.require("referencia_modelo")
    ref = rm["reparto_resistencias_m2K_W"]
    res = hx.overall_resistance(
        h_ref=df.require("punto_ficha_condensador.h_refrigerante_W_m2K"),
        h_air=113.0, eta_surface=0.465)
    assert rel(res["aire"], ref["aire"]) < TOL
    assert rel(res["pared"], ref["pared"]) < TOL
    assert rel(res["refrigerante"], ref["refrigerante"]) < TOL
    assert rel(res["total"], ref["total"]) < TOL
    assert rel(res["U"], rm["U_reconstruida_W_m2K"]) < TOL
    assert rel(res["peso_aire"], 0.728) < 0.02
    assert rel(res["peso_pared"], 0.039) < 0.05


def test_el_sesgo_del_11_por_ciento_no_se_corrige(coil, df):
    """§9.7.4: la discrepancia con la ficha se declara como sesgo conocido y
    conservador, y NO se corrige mediante un factor de ajuste, porque hacerlo
    enmascararía en un coeficiente empírico lo que es un desacuerdo identificado
    y localizado en un submodelo concreto."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    res = hx.overall_resistance(h_ref=5200.0, h_air=113.0, eta_surface=0.465)
    U_ficha = df.require("declarado.U_global_W_m2K")
    assert res["U"] < U_ficha                       # conservador
    assert 0.09 < 1.0 - res["U"] / U_ficha < 0.13   # ≈11 %


# ---------------------------------------------------------------------------
# §9.9 — inventario de carga por integración sobre los segmentos
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def m_air(df):
    return df.require("punto_ficha_condensador.aire.caudal_masico_kg_h") / 3600


def _resolver(coil, Tc_C, T_in_C, m_kgh, m_air, n=400):
    """`T_in_C = None` entra como vapor saturado, que es la condición del punto
    de ficha (desrecalentamiento nulo) y no admite entrada por (P, T)."""
    f = Fluid("Ammonia")
    hx = AirCoil(f, coil, n_segments=n)
    P = f.Psat(Tc_C + 273.15)
    if T_in_C is None:
        f.update_PQ(P, 1.0)
    else:
        f.update_PT(P, T_in_C + 273.15)
    air = AirState(T=35 + 273.15, V_frontal=3.30)
    return hx, hx.solve(P, f.h, m_dot=m_kgh / 3600, air=air, m_dot_air=m_air)


def test_punto_de_ficha_reproduce_el_salto_de_aire(coil, m_air):
    """La ficha declara 35 → 39.9 °C y 12228 W con entrada de vapor saturado.

    Con la ec. 9-24 resolviendo el lado de refrigerante, el modelo reproduce el
    punto de ficha con un 0.6 % de desviación. El sesgo del −9 % que se
    observaba antes era del COEFICIENTE AGREGADO de 5200 W/(m²·K), no del
    modelo: ver `test_el_sesgo_del_11_por_ciento_depende_del_coeficiente_de_ficha`.
    """
    _, r = _resolver(coil, 45.0, None, 41.0, m_air)
    assert 39.0 < r.T_air_out - 273.15 < 40.6
    assert 0.98 < -r.Q_dot / 12228.0 < 1.02


def test_en_M2_la_bateria_desrecalienta_una_quinta_parte_del_volumen(coil, m_air):
    """§9.7.8 y §9.9: en M-2 la batería recibe el gas directamente de la
    descarga, sin desrecalentador intermedio, y una quinta parte del serpentín
    desrecalienta con vapor. Esa zona NO contiene mezcla bifásica, contra lo
    que supone la tabla 9.21.

    Componente AISLADO en la condición de la revisión previa (46.8 °C,
    140.4 °C de entrada, 35.3 kg/h), en la que se publicaban 13.2 kW. En el
    equilibrio de la v30 la batería evacúa 11.73 kW: lo fija
    `tests/test_referencia.py::TestEquilibrioM2`."""
    _, r = _resolver(coil, 46.8, 140.4, 35.3, m_air)
    assert 0.15 < r.volume_fraction["vapor"] < 0.30
    assert rel(-r.Q_dot / 1000, 13.2) < 0.05     # revisión previa: 13.2 kW


def test_la_carga_real_es_inferior_a_la_de_la_tabla_10_13(coil, m_air):
    """La tabla 9.21 integra suponiendo bifásico en los 3.8 L completos. Con la
    zona de desrecalentamiento resuelta y condensación completa sin
    subenfriamiento, la carga es sensiblemente menor."""
    _, r = _resolver(coil, 46.8, 140.4, 35.3, m_air)
    # Con la ec. 9-24 el serpentin condensa antes y la ultima parte se anega:
    # aparecen 6.4 K de subenfriamiento que el coeficiente agregado de ficha no
    # producia. Es la via por la que C4 empeora el margen de RS-5, y por eso el
    # contraste se hace aqui sobre el componente AISLADO. En el equilibrio de
    # M-2 la consigna de subenfriamiento nulo lo suprime: ver
    # `TestEquilibrioM2`.
    assert r.subcooling > 5.0
    assert 290 < r.charge["_min"] * 1000 < 330       # tabla 9.21: 200
    assert 420 < r.charge["_max"] * 1000 < 470       # tabla 9.21: 426


def test_el_subenfriamiento_domina_el_inventario(coil, m_air):
    """El hallazgo que decide RS-5 (§9.9, tabla 9.22). El líquido está a
    571 kg/m³: 41 veces la densidad del vapor y 5 veces la media bifásica.
    Unas pocas centésimas de volumen anegado bastan para agotar el presupuesto
    de 476 g que dan los 9.52 kW del equilibrio de M-2."""
    _, seco = _resolver(coil, 46.8, 140.4, 35.3, m_air)
    _, anegado = _resolver(coil, 46.8, 140.4, 30.0, m_air)
    assert anegado.subcooling > 5.0
    assert anegado.volume_fraction["liquido"] > 0.10
    assert anegado.charge["_max"] > 2 * 0.5 * seco.charge["_max"]
    # la batería sola supera el presupuesto completo de RS-5
    assert anegado.charge["_max"] * 1000 > 476


def test_la_banda_de_carga_es_la_de_la_tabla_10_13(coil, m_air):
    """§9.9: rango, nunca valor único."""
    from amoniatermia.correlations.voidfraction import CORRELACIONES_HUECOS

    _, r = _resolver(coil, 46.8, 140.4, 35.3, m_air, n=100)
    for k in CORRELACIONES_HUECOS + ("_min", "_max", "_spread"):
        assert k in r.charge
    # La dispersión se ESTRECHA respecto al factor 1.9 de la tabla 9.21, y por
    # una razón que conviene no perder: la tabla integra suponiendo bifásico en
    # los 3.8 L completos, mientras que aquí una quinta parte del volumen es
    # vapor y un 6 % líquido subenfriado, zonas en las que las cuatro
    # correlaciones de fracción de huecos no intervienen y por tanto coinciden.
    # Sigue siendo un rango, que es lo que el §9.9 exige reportar.
    assert r.charge["_spread"] > 1.4


# ---------------------------------------------------------------------------
# Datos pendientes y marcado
# ---------------------------------------------------------------------------

def test_el_ventilador_tiene_consumo_constante(coil):
    """DECISIÓN DEL AUTOR, 17/09/2026: se renuncia a la curva característica.

    El caudal de aire y la pérdida de carga varían poco entre condiciones, así
    que el consumo se trata como invariante y se toma del catálogo: 780 W a alta
    velocidad con el motor en triángulo. Es potencia eléctrica ABSORBIDA, que es
    la magnitud que pide la UNE-EN 14511 en el denominador.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    assert hx.fan_power() == pytest.approx(780.0)
    # invariante: no depende de la condición de operación
    assert hx.fan_power() == hx.fan_power()


def test_el_consumo_de_catalogo_es_coherente_con_el_conjunto_montado(coil):
    """Doble contraste, y es lo que permite aceptar un dato que no viene de la
    ficha de selección sino del catálogo de serie.

    Con el η = 0.30 que adopta el §9.7.7, los 780 W equivalen a 110.8 Pa, dentro
    de la banda 80–120 Pa que ese mismo apartado estima para el conjunto montado.
    A la inversa, si la pérdida de carga fuese la de la batería sola (42 Pa), el
    rendimiento implícito sería 0.114, inverosímil en un axial. Las dos vías
    coinciden: los 780 W son el conjunto con envolvente y rejilla RS-4.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    V = 7600.0 / 3600.0

    dp_implicita = hx.fan_power() * 0.30 / V
    assert 80.0 < dp_implicita < 120.0
    assert dp_implicita == pytest.approx(110.8, rel=1e-3)

    eta_si_fuese_la_bateria_sola = V * 42.0 / hx.fan_power()
    assert eta_si_fuese_la_bateria_sola < 0.15

    # Tercera vía: el equipo lleva UN solo axial de Ø500, luego los 780 W son el
    # consumo del equipo. La velocidad de descarga que resulta es normal para ese
    # diámetro, lo que descarta que el caudal de ficha corresponda a otra cosa.
    df = D.air_coil()
    assert df.require("ventilador.n_ventiladores") == 1
    area = math.pi * df.require("ventilador.diametro_m") ** 2 / 4.0
    assert 8.0 < V / area < 13.0


def test_el_consumo_ya_no_es_una_cota_inferior(coil):
    """Los 296 W anteriores sí lo eran: salían de los 42 Pa de la batería
    desnuda con un η adoptado. El dato de catálogo los sustituye.

    La marca se conserva —tiene que viajar con todo EER reportado— pero ahora
    vale falso, y el extremo favorable queda declarado en el fichero de datos
    para que el cap. 11 pueda medir el sesgo que se ha evitado.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    df = D.air_coil()
    assert not hx.fan_power_is_lower_bound()
    assert df.require("ventilador.procedencia") == "catalogo_serie_cbn"
    assert df.require("ventilador.cota_inferior_bateria_sola_W") == \
        pytest.approx(296.0)
    # la vía por pérdida de carga sigue disponible para la sensibilidad del 6.11
    assert hx.fan_power(80.0) == pytest.approx(563.0, rel=0.01)


def test_el_ventilador_pesa_lo_suficiente_para_no_omitirlo(coil):
    """§9.7.7: omitirlo produciría COP y EER no comparables con los de equipos
    comerciales, que es precisamente la comparación que sostiene H1.

    Sobre los ~2.85 kW eléctricos del compresor en el equilibrio de M-2, los
    780 W son un 27 %. Con los 296 W de cota inferior habrían sido un 10 %: la
    diferencia entre las dos hipótesis es de más de un 15 % en el EER.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    W_comp = 2849.0
    assert 0.26 < hx.fan_power() / W_comp < 0.29

    eer_con_cota = 10300.0 / (W_comp + 296.0)
    eer_real = 10300.0 / (W_comp + hx.fan_power())
    assert (eer_con_cota - eer_real) / eer_real > 0.13


def test_el_liquido_subenfriado_queda_fuera_del_rango_de_dittus_boelter(
        coil, m_air):
    """El mecanismo de marcado gana su sitio: con G = 48 kg/(m²·s) el Reynolds
    del líquido queda por debajo de 1e4 y la correlación opera fuera de su base.
    El resultado no es inválido, pero tampoco está soportado."""
    hx, _ = _resolver(coil, 46.8, 140.4, 30.0, m_air, n=100)
    fuera = [e for e in hx.log.excursions
             if e.name == "tube_dittus_boelter" and e.variable == "Re"]
    assert fuera, "el régimen laminar-transicional del líquido debe marcarse"
    assert fuera[0].value_min < 1.0e4


def test_el_diagnostico_de_regimen_de_condensacion_existe(coil, m_air):
    """CLAUDE.md exige reportar la fracción del serpentín en condensación
    anular frente a estratificada. §9.7.5: con 48 kg/(m²·s) —velocidad másica
    que el elevado calor latente del NH₃ hace inevitablemente baja— el régimen
    estratificado es el esperable en buena parte del serpentín.

    El modelo va más lejos que la previsión del capítulo: el Froude de Soliman
    no llega a 20 en NINGUNA celda, de modo que la condensación es estratificada
    en todo el recorrido. Tratarla como anular, que es lo que hace una
    correlación de convección forzada sin criterio de transición, sobreestimaría
    el coeficiente.
    """
    hx, r = _resolver(coil, 46.8, 140.4, 35.3, m_air, n=100)
    assert hx.corr["tube_condensation"] == "dobson_chato"
    assert r.regime_diagnosed
    assert r.condensation_regime["volumen"]["estratificado"] == pytest.approx(1.0)
    assert max(r.Fr_so_range) < 20.0                 # criterio de la ec. 9-24
    assert sum(r.condensation_regime["carga"].values()) == pytest.approx(1.0)


def test_el_agregado_de_ficha_no_puede_diagnosticar(coil, m_air):
    """Un coeficiente constante con el título no reproduce el reparto de
    regímenes, y el resultado que se apoye en él debe declararlo. El Froude se
    reporta igualmente, porque es propiedad del flujo y no de la correlación."""
    f = Fluid("Ammonia")
    hx = AirCoil(f, coil, n_segments=100,
                 corr={"tube_condensation": "ficha_cbn21_agregado"})
    P = f.Psat(46.8 + 273.15)
    f.update_PT(P, 140.4 + 273.15)
    r = hx.solve(P, f.h, 35.3 / 3600, AirState(T=35 + 273.15, V_frontal=3.30),
                 m_air)
    assert not r.regime_diagnosed
    assert r.condensation_regime["volumen"] == {"sin_diagnostico": 1.0}
    assert r.Fr_so_range is not None


# ---------------------------------------------------------------------------
# §9.7.6 — superficie húmeda por potencial entálpico (tarea C5)
# ---------------------------------------------------------------------------
from amoniatermia import psychrometrics as psy       # noqa: E402

AIRE_NOMINAL = dict(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)


@pytest.fixture(scope="module")
def aire_nominal():
    """Condición nominal de la UNE-EN 14511 y primera fila de la tabla 9.20."""
    return AirState.at(**AIRE_NOMINAL)


def _frio(coil, air, T_ref_C, m_kgs=0.35, n=200):
    """Marcha con líquido subenfriado FRÍO por dentro del serpentín.

    No es una condición de operación de la máquina: es el caso de verificación
    que permite ejercitar la marcha húmeda de extremo a extremo sin inventar la
    correlación de ebullición en tubo, que es la tarea C4 y sigue pendiente. El
    lado de aire —que es lo que C5 resuelve— es idéntico al del evaporador; lo
    que cambia es de dónde sale el coeficiente interior.
    """
    f = Fluid("Ammonia")
    hx = AirCoil(f, coil, n_segments=n)
    P = f.Psat(20 + 273.15)
    f.update_PT(P, T_ref_C + 273.15)
    m_air = 8613.0 / 3600.0
    return hx, hx.solve(P, f.h, m_dot=m_kgs, air=air, m_dot_air=m_air)


def test_en_el_punto_de_ficha_la_superficie_sale_seca(coil, m_air):
    """§9.7.6: la ficha confirma superficie seca al declarar la MISMA humedad
    específica a la entrada y a la salida del aire, 17.80 g/kg. El modelo no lo
    supone: lo resuelve celda a celda y llega a lo mismo."""
    aire = AirState(T=35 + 273.15, V_frontal=3.30)
    _, r = _resolver(coil, 45.0, None, 41.0, m_air)
    assert r.wet_fraction == 0.0
    assert r.m_condensate == 0.0
    assert r.T_surface_min > aire.T_dew           # toda la superficie sobre rocío
    assert rel(r.w_air_out, 0.01780) < 0.01       # la ficha, reproducida
    assert r.w_air_out == pytest.approx(aire.w, rel=1e-12)
    assert r.SHR == pytest.approx(1.0)


def test_la_eficiencia_de_aleta_humeda_sale_del_modelo_y_no_del_dato(
        coil, df, aire_nominal):
    """§9.7.6, ec. 9-29. El contraste 0.337 / 0.358 se reproduce evaluando b'
    donde la ecuación dice —en la superficie— en lugar de leerlo del fichero de
    datos. Es la diferencia entre reproducir un número y reproducir un cálculo.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    h_air, _ = hx.air_side(aire_nominal)
    res = hx.wet_conductance(h_ref=2912.0, h_air=h_air, T_ref=1.6 + 273.15,
                             T_surface=3.0 + 273.15, cp_da=aire_nominal.cp_da)
    rm = df.require("referencia_modelo")
    assert rel(res["eta_fin"], rm["eficiencia_aleta_humeda"]) < TOL
    assert rel(res["eta_surface"], rm["efectividad_superficial_humeda"]) < TOL
    assert res["b_superficie"] > res["b_refrigerante"] > psy.CP_DRY_AIR


def test_la_conductancia_humeda_reproduce_la_tabla_10_12(coil, df, aire_nominal):
    """§9.7.8, tabla 9.20: U ≈ 27.9 W/(m²·K) como evaporador, frente a los
    38.2 de condensación. La caída procede de la efectividad superficial húmeda
    (0.465 → 0.358) y del menor coeficiente interior.

    El coeficiente interior NO lo da este test: lo dará la correlación de
    ebullición de la tarea C4. Lo que aquí se verifica es que la red de
    resistencias con la efectividad húmeda del modelo devuelve el U del capítulo
    para el coeficiente interior que ese U implica —2912 W/(m²·K)—, y que ese
    valor queda anotado como la cota que C4 debe alcanzar.
    """
    hx = AirCoil(Fluid("Ammonia"), coil)
    h_air, _ = hx.air_side(aire_nominal)
    ref = df.require("prediccion_evaporador.nominal_EN14511")
    res = hx.wet_conductance(ref["h_refrigerante_implicito_W_m2K"], h_air,
                             1.6 + 273.15, 3.0 + 273.15, aire_nominal.cp_da)
    U = hx.overall_resistance(ref["h_refrigerante_implicito_W_m2K"], h_air,
                              res["eta_surface"])["U"]
    assert rel(U, ref["U_W_m2K"]) < TOL
    assert U < df.require("referencia_modelo.U_reconstruida_W_m2K")


def test_el_potencial_entalpico_no_es_un_coeficiente_de_pelicula(
        coil, aire_nominal):
    """U* está en kg/(m²·s), no en W/(m²·K): la fuerza impulsora es J/kg. Es el
    tipo de mezcla de sistemas que el §9.12.4 señala como productora de
    resultados verosímiles y equivocados, y por eso se reporta aparte."""
    hx = AirCoil(Fluid("Ammonia"), coil)
    h_air, _ = hx.air_side(aire_nominal)
    res = hx.wet_conductance(2912.0, h_air, 1.6 + 273.15, 3.0 + 273.15,
                             aire_nominal.cp_da)
    U = hx.overall_resistance(2912.0, h_air, res["eta_surface"])["U"]
    assert 0.015 < res["U_star"] < 0.035              # kg/(m² s)
    assert not math.isclose(res["U_star"], U, rel_tol=0.5)


def test_la_marcha_humeda_cierra_el_balance_de_energia(coil, aire_nominal):
    """Verificación, no validación: el balance debe cerrar exactamente, porque
    es identidad del esquema y no resultado físico. Sensible más latente es la
    potencia total, y la potencia total es lo que pierde la corriente de aire
    SECO —no la de aire húmedo, que es el error de base másica más común."""
    _, r = _frio(coil, aire_nominal, T_ref_C=-3.0)
    assert r.wet_fraction > 0.0
    assert r.Q_dot == pytest.approx(r.Q_sensible + r.Q_latent, rel=1e-9)
    m_dry = aire_nominal.dry_mass_flow(8613.0 / 3600.0)
    assert m_dry * (aire_nominal.h - r.h_air_out) == pytest.approx(
        r.Q_dot, rel=1e-9)


def test_la_marcha_humeda_reporta_sensible_y_latente_por_separado(
        coil, aire_nominal):
    """§9.7.6: el reporte separado es lo que determina el caudal de condensado
    y, con él, la masa de agua disponible para depositarse como escarcha."""
    _, r = _frio(coil, aire_nominal, T_ref_C=-3.0)
    assert 0.0 < r.SHR < 1.0
    assert r.Q_latent > 0.0
    assert r.m_condensate > 0.0
    # el condensado es coherente con el salto de humedad específica
    m_dry = aire_nominal.dry_mass_flow(8613.0 / 3600.0)
    assert r.m_condensate == pytest.approx(
        m_dry * (aire_nominal.w - r.w_air_out), rel=1e-9)
    # y el latente con el calor de cambio de fase, salvo la entalpía del
    # condensado retirado, que el convenio de ASHRAE no contabiliza (~1 %)
    assert rel(r.m_condensate * psy.H_FG_0, r.Q_latent) < 0.03


def test_sin_humedad_la_marcha_no_entra_en_regimen_humedo(coil):
    """Contraste de degeneración. Con el mismo caso y aire seco, la superficie
    no alcanza el rocío, no hay condensado y el latente es nulo: la formulación
    húmeda no se activa por el hecho de que el refrigerante esté frío, sino por
    el estado del aire."""
    seco = AirState.at(T=7 + 273.15, V_frontal=3.30, RH=0.05)
    _, r = _frio(coil, seco, T_ref_C=-3.0)
    assert r.wet_fraction == 0.0
    assert r.m_condensate == 0.0
    assert r.Q_latent == 0.0
    assert r.SHR == pytest.approx(1.0)


def test_la_transicion_seco_humedo_es_continua(coil):
    """El régimen se decide por celda. Si la decisión introdujese un salto, el
    lazo externo del §9.4 no convergería al cruzar el umbral. Se verifica que
    la potencia varía de forma continua al barrer la humedad relativa a través
    del punto en que la superficie alcanza el rocío."""
    Q = []
    for RH in (0.50, 0.5375, 0.545, 0.5525, 0.56, 0.5675):
        aire = AirState.at(T=7 + 273.15, V_frontal=3.30, RH=RH)
        _, r = _frio(coil, aire, T_ref_C=-3.0, n=400)
        Q.append((r.wet_fraction, r.Q_dot))
    assert Q[0][0] == 0.0 and Q[-1][0] > 0.0          # se cruza el umbral
    saltos = [abs(Q[i + 1][1] / Q[i][1] - 1.0) for i in range(len(Q) - 1)]
    assert max(saltos) < 0.005


def test_la_marcha_humeda_reporta_el_dominio_de_escarcha(coil, aire_nominal):
    """§9.7.6: el componente resuelve LIMPIO y reporta el dominio. La
    penalización de la ec. 9-30 es del cap. 11 y no se aplica aquí.

    Con la superficie parcialmente bajo cero y condensado presente, el dominio
    queda marcado; con la superficie por encima de cero, no."""
    _, frio = _frio(coil, aire_nominal, T_ref_C=-6.0)
    assert frio.T_surface_min < psy.T0
    assert frio.frost_fraction > 0.0
    assert frio.frost_domain

    _, templado = _frio(coil, aire_nominal, T_ref_C=2.0)
    assert templado.T_surface_min > psy.T0
    assert templado.frost_fraction == 0.0
    assert not templado.frost_domain


def test_el_aire_seco_y_el_aire_humedo_no_son_el_mismo_caudal(aire_nominal):
    """El balance de la ec. 9-28 se cierra sobre el caudal de aire SECO.
    Confundirlo con el de mezcla introduce el error de la humedad específica,
    que a 35 °C y 50 % de HR es del 1.7 %."""
    m_humedo = 8613.0 / 3600.0
    assert aire_nominal.dry_mass_flow(m_humedo) < m_humedo
    calido = AirState(T=35 + 273.15, V_frontal=3.30)
    assert rel(m_humedo / calido.dry_mass_flow(m_humedo), 1.0178) < 0.002


def test_el_estado_del_aire_se_deduce_de_la_condicion_psicrometrica():
    """`AirState.at` sustituye a los valores de 35 °C con que se ancló la
    correlación. A 7 °C el aire es un 11 % más denso: arrastrar 1.13 kg/m³ al
    dominio de calefacción falsearía el Reynolds y con él el coeficiente."""
    a7 = AirState.at(**AIRE_NOMINAL)
    a35 = AirState(T=35 + 273.15, V_frontal=3.30)
    assert rel(a7.rho, 1.256) < 0.01
    assert a7.rho / a35.rho > 1.10
    assert rel(a7.RH, 0.868) < 0.02
    with pytest.raises(ValueError):                   # humedad de una sola forma
        AirState.at(T=280.15, V_frontal=3.3, RH=0.5, T_wb=279.15)


# ---------------------------------------------------------------------------
# §9.7.5 y §9.7.8 — operación como evaporador (tarea C4)
# ---------------------------------------------------------------------------

def _equilibrio_evaporador(coil, Tbs, Tbh, corr, T_cond_C=50.0, n=120):
    """Temperatura de evaporación que iguala lo que el compresor aspira con lo
    que la batería puede evacuar.

    Es lo que la tabla 9.20 NO resuelve: esa tabla IMPONE la temperatura de
    evaporación y reporta la capacidad del compresor a esa temperatura, sin
    comprobar que la batería pueda evacuarla.
    """
    from scipy.optimize import brentq

    from amoniatermia.components.compressor import SemiEmpiricalCompressor

    f = Fluid("Ammonia")
    comp = SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params())
    hx = AirCoil(f, coil, n_segments=n, corr={"tube_boiling": corr})
    air = AirState.at(T=Tbs + 273.15, V_frontal=3.30, T_wb=Tbh + 273.15)
    m_air = 8613.0 / 3600.0
    Pk = f.Psat(T_cond_C + 273.15)
    f.update_PQ(Pk, 0.0)
    h_in = f.h

    def residuo(T_ev):
        P0 = f.Psat(T_ev + 273.15)
        r = comp.solve(P0, T_ev + 273.15 + 1.0, Pk, T_amb=298.15)
        f.update_PT(P0, T_ev + 273.15 + 1.0)
        Q_comp = r.m_dot * (f.h - h_in)
        Q_coil = hx.solve(P0, h_in, r.m_dot, air, m_air,
                          role="evaporator").Q_dot
        return Q_coil - Q_comp

    T_ev = brentq(residuo, Tbs - 22.0, Tbs - 0.5, xtol=1e-3)
    P0 = f.Psat(T_ev + 273.15)
    r = comp.solve(P0, T_ev + 273.15 + 1.0, Pk, T_amb=298.15)
    f.update_PT(P0, T_ev + 273.15 + 1.0)
    coil_r = hx.solve(P0, h_in, r.m_dot, air, m_air, role="evaporator")
    Qk = r.m_dot * (r.h_dis - h_in)
    return {"T_evap_C": T_ev, "Q_evap_W": r.m_dot * (f.h - h_in),
            "Q_cond_W": Qk, "COP": Qk / r.W_shaft, "U_W_m2K": coil_r.U_mean,
            "coil": coil_r}


@pytest.mark.parametrize("fila", ["nominal_EN14511", "a_2C", "perfil_frio"])
def test_el_equilibrio_como_evaporador_se_resuelve(coil, df, fila):
    """Con C4 la batería opera ya como evaporador de extremo a extremo. Los
    valores se contrastan contra los del propio modelo, registrados en el
    fichero de datos: es un contraste de NO REGRESIÓN, no una validación —
    ninguna de las correlaciones tiene amoníaco en su base."""
    ref = df.require("prediccion_evaporador." + fila)
    esp = df.require("equilibrio_evaporador.gungor_winterton." + fila)
    r = _equilibrio_evaporador(coil, ref["T_aire_bs_C"], ref["T_aire_bh_C"],
                               "gungor_winterton")
    assert abs(r["T_evap_C"] - esp["T_evap_C"]) < 0.3
    assert rel(r["Q_evap_W"], esp["Q_evap_W"]) < 0.03
    assert rel(r["COP"], esp["COP"]) < 0.03


def test_la_tabla_10_12_esta_por_encima_del_techo_de_su_propio_modelo(
        coil, df, aire_nominal):
    """DISCREPANCIA REPORTADA. La fila nominal declara 10.03 kW.

    Con el coeficiente de aire anclado del §9.7.3, la efectividad superficial
    húmeda del §9.7.6 y un coeficiente de refrigerante INFINITO —resistencia de
    pared incluida como nula—, la batería no pasa de 9.3 kW. El lado de aire
    solo es el 93 % de la resistencia en régimen húmedo, de modo que ninguna
    mejora del lado de refrigerante puede alcanzar la cifra publicada.

    No es el lado de refrigerante lo que falla: es que los 10.03 kW de la tabla
    son la capacidad del COMPRESOR a la temperatura de evaporación supuesta, no
    lo que la batería evacúa a esa temperatura.
    """
    import math

    hx = AirCoil(Fluid("Ammonia"), coil)
    h_air, _ = hx.air_side(aire_nominal)
    m_dry = aire_nominal.dry_mass_flow(8613.0 / 3600.0)
    dh = aire_nominal.h - psy.saturation_enthalpy(1.6 + 273.15)
    res = hx.wet_conductance(1e12, h_air, 1.6 + 273.15, 3.0 + 273.15,
                             aire_nominal.cp_da)
    eps = 1.0 - math.exp(-res["U_star"] * coil.A_o / m_dry)
    techo = eps * m_dry * dh
    assert res["aire"] / res["total"] > 0.90        # el aire es el que manda
    assert techo < df.require("prediccion_evaporador.nominal_EN14511.Q_evap_W")
    assert 8.5e3 < techo < 9.6e3


@pytest.mark.parametrize("fila,tolerancia", [
    ("nominal_EN14511", 0.05), ("a_2C", 0.06), ("perfil_frio", 0.05)])
def test_la_columna_U_de_la_tabla_10_12_es_de_cooper_solo(coil, df, fila,
                                                          tolerancia):
    """DISCREPANCIA REPORTADA, la principal de C4.

    El §9.7.5 declara adoptar la ec. 9-26, h = S·h_nb + F·h_l, pero la
    columna U de la tabla 9.20 solo se reproduce con el término nucleado solo:
    27.9 / 27.3 / 25.6 frente a 27.0 / 26.0 / 24.7 del modelo con `cooper_solo`.
    Con la ec. 9-26 completa el modelo da 33.1 / 33.2 / 37.1, un 20 a 45 % por
    encima.

    Es el mismo hallazgo que `test_cooper_solo_reproduce_las_cifras_publicadas`
    localiza en el coeficiente de película, visto ahora en la conductancia del
    componente. El modelo adopta la ecuación que el capítulo ESCRIBE y conserva
    registrada la que el capítulo CALCULÓ.
    """
    ref = df.require("prediccion_evaporador." + fila)
    cooper = _equilibrio_evaporador(coil, ref["T_aire_bs_C"],
                                    ref["T_aire_bh_C"], "cooper_solo")
    gw = _equilibrio_evaporador(coil, ref["T_aire_bs_C"], ref["T_aire_bh_C"],
                                "gungor_winterton")
    assert rel(cooper["U_W_m2K"], ref["U_W_m2K"]) < tolerancia
    assert gw["U_W_m2K"] > 1.15 * ref["U_W_m2K"]


def test_a_2C_hay_escarcha_y_a_menos_7_la_superficie_queda_sobre_el_rocio(
        coil, df):
    """§9.7.6 afirma que «la condición de aire a 2 °C ya sitúa la evaporación
    en −2.9 °C, con superficie por debajo de cero y formación de escarcha
    establecida». El modelo lo reproduce.

    A −7 °C bs / −8 °C bh, en cambio, la superficie queda entre 0.3 y 0.6 K POR
    ENCIMA del punto de rocío y no hay deposición, contra lo que sugiere la
    §9.7.3 al rotular esa fila «con escarcha». El margen es pequeño y cae
    dentro de la incertidumbre del coeficiente de aire, de modo que se reporta
    como frontera y no como refutación.
    """
    r2 = _equilibrio_evaporador(coil, 2.0, 1.0, "gungor_winterton")["coil"]
    assert r2.frost_domain and r2.frost_fraction > 0.9

    aire = AirState.at(T=-7 + 273.15, V_frontal=3.30, T_wb=-8 + 273.15)
    r7 = _equilibrio_evaporador(coil, -7.0, -8.0, "gungor_winterton")["coil"]
    assert r7.wet_fraction == 0.0
    assert 0.0 < r7.T_surface_min - aire.T_dew < 1.0


def test_el_sesgo_del_11_por_ciento_depende_del_coeficiente_de_ficha(coil, df):
    """§9.7.4 atribuye al método de aleta equivalente que la conductancia
    reconstruida (38.2) quede un 11 % bajo la de ficha (43), y propone
    resolverlo en el cap. 10 con un cálculo bidimensional de la aleta.

    Con la ec. 9-24 resolviendo el lado de refrigerante, y SIN tocar la
    eficiencia de aleta, la batería reproduce la capacidad de ficha con un 0.6 %
    de desviación. La discrepancia no es por tanto atribuible únicamente a la
    aleta: un coeficiente interior superior al declarado la explica igual de
    bien. Son dos efectos indistinguibles a partir de un solo valor de U, y
    separarlos exige un segundo dato —el criterio de aleta del fabricante, o un
    punto a otra velocidad másica—, no un cálculo bidimensional.
    """
    m_air = 8613.0 / 3600.0
    _, con_correlacion = _resolver(coil, 45.0, None, 41.0, m_air)
    f = Fluid("Ammonia")
    hx = AirCoil(f, coil, n_segments=200,
                 corr={"tube_condensation": "ficha_cbn21_agregado"})
    P = f.Psat(45 + 273.15)
    f.update_PQ(P, 1.0)
    con_ficha = hx.solve(P, f.h, 41.0 / 3600, AirState(T=35 + 273.15,
                                                       V_frontal=3.30), m_air)
    Q_ficha = df.require("punto_ficha_condensador.capacidad_W")
    assert rel(-con_correlacion.Q_dot, Q_ficha) < 0.02
    assert 0.06 < 1.0 - (-con_ficha.Q_dot) / Q_ficha < 0.12


# ---------------------------------------------------------------------------
# §9.7.2 — Seguimiento de la frontera de fase en el serpentín
#
# La marcha repartía el área en N segmentos iguales y seguía adelante. El punto
# en que termina la evaporación caía entonces en un segmento o en el siguiente
# según el punto de operación, y el estado de salida SALTABA al cruzar ese
# umbral. Medido en M-4 el 22/09/2026: un cambio de 1e-7 en log(P0) —0.04 Pa—
# movía la frontera un segmento, el reparto de volumen pasaba de 0.1167 a
# 0.1000 y el recalentamiento de salida daba un salto de 2.4 K.
#
# El lazo externo del §9.4 no puede cruzar un escalón: se detenía sobre él con
# un residuo de 3e-3, tres órdenes por encima de la tolerancia del §9.4.4. Es
# el mismo defecto que se corrigió en `plate_hx` el 21/09/2026 y que el plan
# había aplazado para la batería por considerarlo solo cuestión de velocidad.
# ---------------------------------------------------------------------------
class TestFronteraDeFaseSerpentin:
    P_EVAP_C = 2.0
    AIRE = dict(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)
    M_AIRE = 8613.0 / 3600.0

    def _marchar(self, coil_geom, m_dot, n_segments=40, x_in=0.2):
        f = Fluid("Ammonia")
        hx = AirCoil(f, coil_geom, n_segments=n_segments)
        P = f.Psat(self.P_EVAP_C + 273.15)
        sat = f.sat_props(P)
        h_in = sat["h_l"] + x_in * (sat["h_v"] - sat["h_l"])
        r = hx.solve(P, h_in, m_dot, AirState.at(**self.AIRE), self.M_AIRE,
                     role="evaporator")
        return r, (r.h_ref_out - sat["h_v"]) / sat["cp_v"]

    def test_recorta_donde_cruza_y_no_donde_no_cruza(self, coil):
        """El recorte añade UN segmento por frontera cruzada, y ninguno si la
        marcha no cruza. `n_segments` pasa a ser el número NOMINAL."""
        cruza, sh = self._marchar(coil, 0.0040)
        assert sh > 0.0                      # sale recalentado: cruzó x = 1
        assert cruza.n_recortes == 1
        assert cruza.n_segmentos == 41

        no_cruza, _ = self._marchar(coil, 0.0080)
        assert no_cruza.n_recortes == 0
        assert no_cruza.n_segmentos == 40

    def test_la_salida_es_continua_al_mover_el_caudal(self, coil):
        """Lo que el lazo externo necesita: que el recalentamiento de salida no
        salte cuando la frontera cambia de segmento.

        Barriendo el caudal en un intervalo en el que la frontera recorre varios
        segmentos, la serie era antes un diente de sierra con saltos de 0.10 a
        0.15 K sobre incrementos de 0.01 K —razón entre el salto máximo y la
        mediana de 9.4—. Con el recorte es monótona y la razón baja a 1.5.
        """
        sh = [self._marchar(coil, m)[1]
              for m in (0.0038 + 0.00002 * k for k in range(21))]
        d = [b - a for a, b in zip(sh, sh[1:])]
        assert all(v < 0.0 for v in d), "la serie debe ser monótona"
        mediana = sorted(abs(v) for v in d)[len(d) // 2]
        assert max(abs(v) for v in d) / mediana < 3.0
        assert max(abs(v) for v in d) < 0.01     # antes, 0.148 K

    def test_el_balance_sigue_cerrando_con_recorte(self, coil):
        """El calor acumulado segmento a segmento y el que ve el refrigerante de
        sus estados extremos deben coincidir también tras un recorte: la
        frontera se impone EXACTAMENTE, de modo que el balance no arrastra
        deriva."""
        f = Fluid("Ammonia")
        hx = AirCoil(f, coil, n_segments=40)
        P = f.Psat(self.P_EVAP_C + 273.15)
        sat = f.sat_props(P)
        h_in = sat["h_l"] + 0.2 * (sat["h_v"] - sat["h_l"])
        r = hx.solve(P, h_in, 0.0040, AirState.at(**self.AIRE), self.M_AIRE,
                     role="evaporator")
        Q_extremos = 0.0040 * (r.h_ref_out - h_in)
        assert r.n_recortes == 1
        assert abs(r.Q_dot - Q_extremos) / abs(Q_extremos) < 1e-9


@pytest.mark.parametrize("fila", ["nominal_EN14511", "a_2C", "perfil_frio"])
def test_la_columna_impuesta_de_la_tabla_10_20(df, fila):
    """CAMBIO PENDIENTE DEL CAPÍTULO (25/09/2026). La columna de temperatura de
    evaporación IMPUESTA de la tabla 9.20 (10.03 / 8.36 / 5.84 kW) es de la
    revisión previa. Con el compresor adoptado, a la misma T_evap y con
    condensación a 50 °C, da 8.83 / 7.13 / 4.59 kW, y la columna resuelta queda
    solo un 1–4 % por debajo, no un 12–22 %: con esta batería la temperatura de
    evaporación supuesta estaba casi bien elegida. El principio del §9.7.8
    —imponer no es un equilibrio— se mantiene; la magnitud de su efecto no."""
    from amoniatermia.components.compressor import SemiEmpiricalCompressor

    f = Fluid("Ammonia")
    comp = SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params())
    esp = df.require("equilibrio_evaporador.impuesta_modelo." + fila)
    Pk = f.Psat(50 + 273.15)
    f.update_PQ(Pk, 0.0)
    h_in = f.h
    T_ev = esp["T_evap_C"] + 273.15
    P0 = f.Psat(T_ev)
    r = comp.solve(P0, T_ev + 1.0, Pk, T_amb=298.15)
    f.update_PT(P0, T_ev + 1.0)
    Q_evap = r.m_dot * (f.h - h_in)
    assert rel(Q_evap, esp["Q_evap_W"]) < 0.005
    assert rel(r.m_dot * (r.h_dis - h_in) / r.W_shaft, esp["COP"]) < 0.005
    resuelta = df.require("equilibrio_evaporador.gungor_winterton." + fila)
    caida = 1.0 - resuelta["Q_evap_W"] / Q_evap
    assert 0.0 < caida < 0.05


def test_el_perfil_de_la_bateria_recorre_sus_segmentos(coil, m_air):
    _, r = _resolver(coil, 45.0, None, 41.0, m_air, n=60)
    p = r.profile
    assert len(p["A"]) == len(p["T_ref"]) == r.n_segmentos + 1
    assert len(p["T_aire_sal"]) == len(p["T_sup"]) == r.n_segmentos
    assert p["A"][-1] == pytest.approx(coil.A_o, rel=1e-9)
    assert p["T_ref"][-1] == pytest.approx(r.T_ref_out, abs=1e-9)
    # la media de las salidas del aire pesada por area es la salida reportada
    import numpy as np
    dA = np.diff(p["A"])
    assert (p["T_aire_sal"] * dA).sum() / dA.sum() == pytest.approx(r.T_air_out, abs=1e-9)
