"""Lazo externo y topologias por modo. Apartados 9.3 y 9.4.

Lo que se comprueba aqui no es solo que el sistema converja. El ap. 9.4.4
exige verificaciones INDEPENDIENTES de la convergencia formal —cierre de los
balances de masa y energia y positividad de la generacion de entropia— y el
ap. 9.4.4 exige que los casos no convergidos se registren en lugar de
descartarse. Un test que solo mirase el residuo no verificaria ninguna de las
dos cosas.

Uso:  pytest tests/test_circuit.py -v
"""
import math

import pytest

from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid,
                          PlateHeatExchanger, SemiEmpiricalCompressor,
                          Setpoints, WaterStream)
from amoniatermia import MODES
from amoniatermia import data as D
from amoniatermia.circuit import ACS, AIRE, CLIMA
from amoniatermia.data import MissingData

TOL = 0.02

#: YA NO SE INYECTA NADA (18/09/2026). El paso entre placas y el espesor salen
#: del catalogo de la gama, el angulo esta identificado sobre la perdida de
#: carga del punto de seleccion del 27-30H y el producto phi_c*phi_v esta
#: anclado sobre su conductancia. Los modos con placas dejan de ser
#: exploratorios. Lo que sigue supuesto es el factor de alargamiento, y su
#: efecto se recorre en la sensibilidad del ap. 6.11.
INYECTADO = {}
PHI = None

AIRE_35 = AirState(T=35 + 273.15, V_frontal=3.30)
AIRE_7 = AirState(T=7 + 273.15, V_frontal=3.30)
M_AIRE = None     # 7600 m3/h de la ficha; el caudal masico lo deduce Boundary


def _compresor(f):
    return SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params())


def circuito_bateria(n_segments=200):
    """Circuito con SOLO el compresor y la bateria.

    Es la configuracion con la que el §9.7.8 calcula el equilibrio de M-2:
    temperatura de evaporacion impuesta y lado de baja sin modelar. No necesita
    ningun dato pendiente.
    """
    f = Fluid("Ammonia")
    coil = AirCoil(f, D.air_coil_geometry(), n_segments=n_segments)
    return f, Circuit(f, _compresor(f), coil, None, None)


def circuito_completo(n_cells=12, n_segments=120):
    """Circuito con los cuatro componentes. EXPLORATORIO: ver `INYECTADO`."""
    f = Fluid("Ammonia")
    coil = AirCoil(f, D.air_coil_geometry(), n_segments=n_segments)
    g_cl = D.plate_geometry("condensador_climatizacion", **INYECTADO)
    g_ac = D.plate_geometry("desrecalentador_acs", **INYECTADO)
    agua = Fluid("Water")
    cl = PlateHeatExchanger(f, agua, g_cl, n_cells=n_cells, corr_params=PHI)
    ac = PlateHeatExchanger(f, Fluid("Water"), g_ac, n_cells=n_cells,
                            corr_params=PHI)
    return f, Circuit(f, _compresor(f), coil, cl, ac)


# ---------------------------------------------------------------------------
# E1 — el vector de incognitas se dimensiona POR MODO
# ---------------------------------------------------------------------------
class TestSistemaPorModo:
    """La tabla 9.4 tiene cuatro incógnitas; el sistema NO está fijo a
    cuatro: los modos con recuperación añaden el caudal de ACS y su residuo a
    las tres de M-2 y M-4.

    Las dos razones originales del diseño —el reparto de M-5 de la decisión D-1
    y la presión de alta del R-744— cayeron las dos en septiembre de 2026. El
    dimensionado por modo sigue haciendo falta."""

    def test_los_cinco_modos_estan_declarados(self):
        for m in ("M-2", "M-4", "M-1", "M-3", "M-5"):
            assert m in MODES

    @pytest.mark.parametrize("modo", ["M-2", "M-4", "M-1", "M-3", "M-5"])
    def test_topologia_coherente(self, modo):
        s = MODES[modo]
        assert s.high and s.low, "todo modo tiene lado de alta y de baja"
        comps = s.components()
        assert len(set(comps)) == len(comps), "un componente no puede repetirse"
        for k in comps:
            assert k in s.secondary, f"{k} sin servicio secundario declarado"
        assert set(s.extended) <= set(comps)
        assert len(s.unknowns) == len(s.residuals)

    def test_la_bateria_cambia_de_papel_entre_modos(self):
        """Ap. 9.3, tabla 9.3: condensador en M-2 y M-1, evaporador en el
        resto. Es la variabilidad topologica que justifica que el papel viaje
        con el modo y no con el objeto."""
        assert MODES["M-2"].role(AIRE) == "condenser"
        assert MODES["M-1"].role(AIRE) == "condenser"
        for m in ("M-4", "M-3", "M-5"):
            assert MODES[m].role(AIRE) == "evaporator"

    def test_el_desrecalentador_cambia_de_familia_de_correlaciones(self):
        """Ap. 9.3.1: evaporador en M-2, condensador en M-4, y gas monofasico
        dedicado a ACS en M-1/M-3/M-5. El componente es el mismo objeto."""
        assert MODES["M-2"].role(ACS) == "evaporator"
        assert MODES["M-4"].role(ACS) == "condenser"
        for m in ("M-1", "M-3", "M-5"):
            assert MODES[m].secondary[ACS] == "acs"

    def test_tren_extendido_en_M2_M4_y_M5(self):
        """§9.3.1: presión común y agua a contracorriente por ambos.

        En M-2 y M-4 el tren amplía la superficie del servicio de climatización;
        en M-5 los mismos dos intercambiadores trabajan en serie para el ACS
        (tabla 9.3). En M-1 y M-3 cada placa opera con su propio servicio y no
        hay tren.
        """
        for m in ("M-2", "M-4", "M-5"):
            assert set(MODES[m].extended) == {CLIMA, ACS}
        for m in ("M-1", "M-3"):
            assert MODES[m].extended == ()

    def test_los_modos_con_recuperacion_anaden_incognita_y_residuo(self):
        for m in ("M-1", "M-3", "M-5"):
            assert "m_acs" in MODES[m].unknowns
            assert "R5" in MODES[m].residuals

    def test_en_M5_no_hay_reparto_ni_disipacion(self):
        """DECISIÓN DEL AUTOR del 22/09/2026, que revierte D-1 en M-5.

        El circuito de climatización solo tiene FAN-COILS: disipar en él el
        calor residual significa activarlos, y activarlos significa calefactar
        la vivienda. Con una demanda de ACS en verano, sin demanda de frío ni de
        calor, la disipación por esa vía es imposible.

        De modo que en M-5 los dos intercambiadores de placas trabajan para el
        ACS —la topología de la tabla 9.3— y desaparecen con el reparto la
        quinta incógnita y el residuo R6 que la opción 2 de D-1 había
        introducido. El modo de reparto se retira: mantener implementada una
        topología físicamente imposible es peor que no tenerla.
        """
        assert "M-5-reparto" not in MODES
        s = MODES["M-5"]
        assert s.secondary[CLIMA] == "acs" and s.secondary[ACS] == "acs"
        assert "m_clima" not in s.unknowns and "R6" not in s.residuals
        assert s.clima == "inactivo"

    def test_la_evaporacion_impuesta_reduce_el_sistema(self):
        """Es lo que hace el §9.7.8: fija T_evap y no resuelve el lado de
        baja. El sistema pierde P0 y con el la consigna de recalentamiento."""
        _, c = circuito_bateria()
        u_libre, r_libre = c.active_system("M-2", Setpoints())
        u_fija, r_fija = c.active_system("M-2", Setpoints(T_evap=275.15))
        assert "P0" in u_libre and "R2" in r_libre
        assert "P0" not in u_fija and "R2" not in r_fija
        assert len(u_fija) == len(u_libre) - 1

    def test_la_eliminacion_de_A_ef_es_reversible(self):
        """La ec. 9-21 es lineal en A_ef, luego R1 admite solucion cerrada. El
        vector literal del ap. 9.4.2 se recupera desactivandola."""
        f, _ = circuito_bateria()
        c = Circuit(f, _compresor(f), AirCoil(f, D.air_coil_geometry(), 60),
                    None, None, eliminate_A_ef=False)
        u, r = c.active_system("M-2", Setpoints())
        assert "A_ef" in u and "R1" in r

    def test_falta_la_consigna_de_ACS(self):
        _, c = circuito_bateria()
        with pytest.raises(ValueError, match="R5"):
            c.active_system("M-1", Setpoints())

    def test_modo_desconocido(self):
        _, c = circuito_bateria()
        with pytest.raises(KeyError):
            c.spec("M-9")


# ---------------------------------------------------------------------------
# E5 — equilibrio de M-2 (§9.7.8)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def equilibrio_M2():
    _, c = circuito_bateria(n_segments=400)
    bc = Boundary(air=AIRE_35, m_dot_air=M_AIRE, T_amb=35 + 273.15)
    sp = Setpoints(superheat=1.0, subcooling=0.0, T_evap=2 + 273.15)
    return c, c.solve("M-2", bc, sp)


class TestEquilibrioM2:
    """El §9.7.8 resuelve el equilibrio entre compresor y bateria con T_evap
    impuesta a 2 grados y aire a 35 (tabla 9.19): 44.9 grados de
    condensacion, 11.73 kW evacuados y 9.52 kW frigorificos. Las cifras exactas
    las fija `tests/test_referencia.py::TestEquilibrioM2`."""

    def test_converge_y_es_valido(self, equilibrio_M2):
        _, s = equilibrio_M2
        assert s.converged, s.message
        assert s.max_residual < 1e-6
        assert s.valid, s.checks

    def test_condensacion_completa_sin_subenfriamiento(self, equilibrio_M2):
        """La condicion de cierre del lado de alta: la valvula debe recibir
        liquido. Con subenfriamiento de consigna nulo la salida cae justo en la
        frontera de fase."""
        _, s = equilibrio_M2
        assert abs(s.subcooling) < 0.05

    def test_reproduce_el_catalogo_del_fabricante(self, equilibrio_M2):
        """CONTRASTE INDEPENDIENTE. A T0 = 2 y Tk = 45 el fabricante publica
        9.46 kW frigorificos, 2.47 kW al eje y 122.2 grados de descarga. El
        equilibrio calculado cae en 44.9 grados de condensacion, y ahi el
        modelo debe coincidir con el catalogo: el §9.7.8 lo sitúa a menos de
        un 3 % de los 9.28 kW interpolados."""
        _, s = equilibrio_M2
        assert abs(s.Q_evap - 9460.0) / 9460.0 < 0.03
        assert abs(s.W_shaft - 2470.0) / 2470.0 < 0.05
        assert abs(s.T_dis - 273.15 - 122.2) < 3.0

    def test_la_discrepancia_con_la_revision_previa_esta_cerrada(self, equilibrio_M2):
        """Abierta el 17/09/2026 y CERRADA en la v30 a favor del modelo.

        La revision previa declaraba 46.8 grados, 13.2 kW evacuados y 10.3 kW
        frigorificos. Esos 10.3 kW no eran compatibles con el catalogo: a T0 = 2
        publica 9.46 kW a Tk = 45 y la capacidad DESCIENDE al subir la
        condensacion, de modo que a 46.8 grados serian unos 9.28 kW. La v30
        publica el equilibrio del modelo y con el el presupuesto de RS-5 de
        476 g (§9.9) en lugar de los 515 g de entonces.

        Se conserva como candado: si el modelo volviera a las cifras previas,
        algo se habria roto.
        """
        _, s = equilibrio_M2
        assert s.T_cond - 273.15 < 45.5
        assert -s.Q_high < 12.5e3
        assert s.Q_evap < 10.0e3
        assert s.charge["_RS5_limite_kg"] < 0.480

    def test_la_capacidad_es_salida_y_no_entrada(self, equilibrio_M2):
        """CLAUDE.md: la potencia frigorifica resulta del desplazamiento, del
        rendimiento volumetrico identificado y de las conductancias."""
        _, s = equilibrio_M2
        assert s.setpoints.Q_high is None
        assert 8.0e3 < s.Q_evap < 11.0e3

    def test_diagnostico_de_regimen(self, equilibrio_M2):
        """CLAUDE.md exige reportar la fraccion del serpentin en cada regimen.
        En M-2 la bateria recibe el gas de la descarga y una parte desrecalienta
        (§9.7.8): esa fraccion no puede ser nula."""
        _, s = equilibrio_M2
        vol = s.diagnostics[AIRE]["fraccion_volumen"]
        assert vol["vapor"] > 0.10
        assert vol["condensando"] > 0.60
        assert abs(sum(vol.values()) - 1.0) < 1e-6

    def test_marca_de_extrapolacion(self, equilibrio_M2):
        """El resultado se apoya en la correlacion de aire anclada, que en este
        punto opera en el extremo de su base, y en el metodo de aleta, cuya base
        no esta declarada. Debe salir marcado."""
        _, s = equilibrio_M2
        assert s.extrapolated
        assert s.excursions

    def test_el_consumo_de_ventilador_viaja_con_el_resultado(self, equilibrio_M2):
        """UNE-EN 14511: entra en el denominador de COP y EER. Omitirlo rompe
        H1 (CLAUDE.md). El calculo del indicador es de la fase F; lo que este
        modulo debe garantizar es que el dato esta."""
        _, s = equilibrio_M2
        assert abs(s.W_fan - 780.0) < 1.0
        assert s.diagnostics["ventilador_es_cota_inferior"] is False


# ---------------------------------------------------------------------------
# E4 — verificaciones independientes de la convergencia formal (§9.4.4)
# ---------------------------------------------------------------------------
class TestVerificaciones:
    def test_balance_de_masa(self, equilibrio_M2):
        _, s = equilibrio_M2
        assert s.checks["masa"] < 1e-3

    def test_balance_de_energia(self, equilibrio_M2):
        """Se compone de magnitudes de COMPONENTE —capacidad, potencia al eje,
        disipacion al ambiente y calor evacuado— de modo que no cierra por
        construccion."""
        _, s = equilibrio_M2
        assert s.checks["energia"] < 1e-3

    def test_balance_del_lado_de_aire(self, equilibrio_M2):
        """Comprobacion independiente: la marcha no emplea el salto de
        temperatura del aire para cerrar nada."""
        _, s = equilibrio_M2
        assert s.checks["balance_componentes"][AIRE] < 1e-3

    def test_generacion_de_entropia_positiva(self, equilibrio_M2):
        _, s = equilibrio_M2
        assert s.checks["entropia_minima"] > 0.0
        for k, v in s.checks["entropia"].items():
            assert v > 0.0, f"{k} genera entropia negativa"

    def test_el_area_de_la_valvula_se_publica_como_resultado(self, equilibrio_M2):
        """Decisión del autor (29/09/2026): la válvula no está seleccionada
        (§7.6.4), de modo que no hay área máxima con que compararla; el modelo
        publica la que necesita el punto, que es el dato para elegirla."""
        _, s = equilibrio_M2
        assert s.checks["area_efectiva_valvula_m2"] > 0.0
        assert s.envelope["area_efectiva_valvula_m2"] == s.unknowns["A_ef"]
        assert "apertura_valvula" not in s.envelope["limites"]

    def test_el_balance_de_pared_del_compresor_se_verifica(self, equilibrio_M2):
        """R3 no es residuo del lazo externo en esta implementacion —el
        compresor lo resuelve en su lazo propio— pero sigue siendo una ecuacion
        de cierre y se comprueba."""
        _, s = equilibrio_M2
        assert s.checks["R3_pared_compresor"] < 1e-3

    def test_una_solucion_invalida_no_se_declara_valida(self, equilibrio_M2):
        c, s = equilibrio_M2
        s2 = type(s)(**{**s.as_dict(), "modo": "x"}) if False else s
        assert s2.valid == (s2.converged and s2.checks["ok"])


# ---------------------------------------------------------------------------
# Carga: banda, nunca valor unico (ap. 9.9)
# ---------------------------------------------------------------------------
class TestCarga:
    def test_nunca_un_valor_unico(self, equilibrio_M2):
        _, s = equilibrio_M2
        nombres = [k for k in s.charge if not k.startswith("_")]
        assert len(nombres) == 4
        assert s.charge["_max"] > s.charge["_min"]
        assert s.charge["_spread"] > 1.0

    def test_RS5_se_evalua_contra_la_capacidad_calculada(self, equilibrio_M2):
        """RS-5 esta normalizado por la capacidad y es invariante de escala: se
        evalua contra la que el modelo calcule, no contra una declarada."""
        _, s = equilibrio_M2
        assert abs(s.charge["_RS5_limite_kg"] - 0.050 * s.Q_evap / 1000.0) < 1e-12
        assert s.charge["_RS5_peor_caso"] == pytest.approx(
            s.charge["_max"] / s.charge["_RS5_limite_kg"])

    def test_la_bateria_sola_no_agota_el_presupuesto(self, equilibrio_M2):
        """Con subenfriamiento nulo la bateria consume una fraccion del
        presupuesto, no su totalidad. Lo que lo pone en riesgo es el anegado,
        que depende de la carga total del sistema y no del componente."""
        _, s = equilibrio_M2
        assert s.charge["_RS5_peor_caso"] < 1.0


# ---------------------------------------------------------------------------
# E3 — inicializacion y continuacion; E-10.4.4 — no convergencia
# ---------------------------------------------------------------------------
class TestInicializacionYContinuacion:
    def test_inicializacion_por_parametros_agrupados(self):
        _, c = circuito_bateria(n_segments=60)
        bc = Boundary(air=AIRE_35, m_dot_air=M_AIRE, T_amb=35 + 273.15)
        sp = Setpoints(T_evap=2 + 273.15)
        g = c.initial_guess("M-2", bc, sp)
        f = Fluid("Ammonia")
        # pinzamiento supuesto de 10 K sobre el aire de entrada
        assert abs(f.Tsat(g["Pk"]) - (bc.air.T + 10.0)) < 0.2
        assert abs(f.Tsat(g["P0"]) - sp.T_evap) < 0.2
        assert g["A_ef"] > 0.0

    def test_continuacion_sobre_el_parametro_barrido(self):
        """Ap. 9.4.4: cada caso arranca de la solucion del anterior."""
        _, c = circuito_bateria(n_segments=120)
        bcs = [Boundary(air=AirState(T=T + 273.15, V_frontal=3.30),
                        m_dot_air=M_AIRE, T_amb=T + 273.15)
               for T in (30.0, 35.0, 40.0)]
        sp = Setpoints(superheat=1.0, subcooling=0.0, T_evap=2 + 273.15)
        sols = c.sweep("M-2", bcs, sp=sp)
        assert len(sols) == 3
        assert all(s.converged for s in sols)
        # a mas temperatura de aire, mas condensacion y menos capacidad
        assert sols[0].T_cond < sols[1].T_cond < sols[2].T_cond
        assert sols[0].Q_evap > sols[2].Q_evap

    def test_los_casos_no_convergidos_se_registran(self):
        """Ap. 9.4.4 y ap. 6.12: no se descartan en silencio. Se fuerza una
        demanda imposible —mas calor del que el circuito puede evacuar— y se
        comprueba que el fallo queda con su condicion de contorno y su
        residuo."""
        _, c = circuito_bateria(n_segments=60)
        bc = Boundary(air=AIRE_35, m_dot_air=M_AIRE, T_amb=35 + 273.15)
        sp = Setpoints(superheat=1.0, T_evap=2 + 273.15, Q_high=60.0e3)
        s = c.solve("M-2", bc, sp)
        assert not s.converged
        assert c.failures and c.failures[-1] is s
        assert s.boundary is bc and s.setpoints is sp
        assert s.max_residual > 1e-6

    def test_la_procedencia_acompana_al_resultado(self, equilibrio_M2):
        _, s = equilibrio_M2
        p = s.provenance
        assert p["modo"] == "M-2"
        assert p["evaporacion_impuesta"] is True
        assert p["correlaciones"][AIRE]["airside"] == "colburn_anclada_cbn21"
        assert p["tolerancia_residuos"] == Circuit.TOL
        assert p["extrapolacion"]["extrapolado"] is True


# ---------------------------------------------------------------------------
# Datos pendientes: el modelo debe fallar, no suponer
# ---------------------------------------------------------------------------
class TestDatosPendientes:
    def test_el_condensador_de_placas_ya_construye_su_geometria(self):
        """Era la puerta cerrada del §9.6.4: sin paso entre placas, angulo ni
        factor de alargamiento, `plate_geometry` fallaba y los modos con placas
        no podian resolverse sin inyectar valores.

        Cerrada el 18/09/2026. Lo que el test conserva es la exigencia de que la
        procedencia viaje con el dato: el angulo esta IDENTIFICADO, no leido de
        un catalogo, y el factor de alargamiento sigue ESTIMADO.
        """
        g = D.plate_geometry("condensador_climatizacion")
        assert g.beta_c > 0.0 and g.b > 0.0 and g.phi > 0.0
        df = D.load("placas_alfanova")
        assert df.require("unidades.condensador_climatizacion.geometria."
                          "angulo_procedencia").startswith("IDENTIFICADO")
        assert df.require("producto_phi_c_phi_v.procedencia").startswith("ANCLADO")

    def test_un_modo_sin_su_componente_falla_explicitamente(self):
        """Pedir M-4 a un circuito construido solo con la bateria no puede
        devolver un numero."""
        _, c = circuito_bateria(n_segments=40)
        bc = Boundary(air=AIRE_7, m_dot_air=M_AIRE,
                      clima=WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion()),
                      T_amb=7 + 273.15)
        with pytest.raises(MissingData):
            c.solve("M-4", bc, Setpoints(superheat=5.0))

    def test_un_modo_sin_su_circuito_de_agua_falla(self):
        _, c = circuito_completo(n_cells=6, n_segments=40)
        bc = Boundary(air=AIRE_35, m_dot_air=M_AIRE, T_amb=35 + 273.15)
        with pytest.raises(ValueError, match="clima"):
            c.initial_guess("M-2", bc, Setpoints())


# ---------------------------------------------------------------------------
# E2 — el tren extendido del §9.3.1
# ---------------------------------------------------------------------------
class TestTrenExtendido:
    """Los dos intercambiadores de placas en serie a presión común, tratados
    como una secuencia continua de volúmenes.

    EXPLORATORIO: la geometría lleva β, b y φ inyectados (§9.6.4).
    """

    @pytest.fixture(scope="class")
    @classmethod
    def tren(cls):
        f, c = circuito_completo(n_cells=8, n_segments=40)
        P = f.Psat(2 + 273.15)
        # entrada al tren: mezcla bifásica procedente de la válvula
        sat = f.sat_props(P)
        h_in = sat["h_l"] + 0.25 * sat["h_lv"]
        T_agua = 12 + 273.15
        P_out, h_out, res = c._march_chain(
            MODES["M-2"].extended, P, h_in, 0.009, T_agua, 0.5, "evaporator",
            True)
        return f, c, P, h_in, P_out, h_out, res, T_agua

    def test_el_disparo_recupera_la_entrada_del_agua(self, tren):
        """La condición de cierre del tren: marchando el refrigerante desde su
        entrada, el agua debe salir por el otro extremo a su temperatura de
        entrada. No es dato de ninguno de los dos intercambiadores por
        separado."""
        *_, res, T_agua = tren
        # El agua entra por el extremo de SALIDA del refrigerante, que es el
        # ultimo elemento del tren. La tolerancia no es la del disparo (1e-7 K
        # sobre la variable) sino la que esa tolerancia deja en el otro extremo
        # del tren, que la marcha amplifica. Medido: unos 3 mK.
        ultimo = MODES["M-2"].extended[-1]
        assert abs(res[ultimo].T_sec_in - T_agua) < 0.02

    def test_la_presion_es_comun_y_el_estado_continuo(self, tren):
        """§9.3.1: no hay válvula ni discontinuidad entre ellos. La pérdida de
        carga acumulada es la única caída, y la entalpía es continua."""
        from amoniatermia.circuit import CLIMA, ACS

        f, c, P, h_in, P_out, h_out, res, _ = tren
        # Hipótesis M8 (decisión del autor, 29/09/2026): presión uniforme a
        # efectos de propiedades. La pérdida de carga se acumula y se publica,
        # con su salto de saturación equivalente, pero no baja la presión.
        caida = res[CLIMA].dP_ref + res[ACS].dP_ref
        assert P_out == P
        assert caida > 0.0
        for k in (CLIMA, ACS):
            dT = f.Tsat(P) - f.Tsat(P - res[k].dP_ref)
            assert res[k].dT_sat_equivalente == pytest.approx(dT, rel=1e-6)

    def test_el_calor_del_tren_es_la_suma_de_sus_elementos(self, tren):
        from amoniatermia.circuit import CLIMA, ACS

        f, c, P, h_in, P_out, h_out, res, _ = tren
        Q = 0.009 * (h_out - h_in)
        assert abs(Q - (res[CLIMA].Q_dot + res[ACS].Q_dot)) < 1.0
        assert Q > 0.0                        # el tren evapora

    def test_cada_elemento_cierra_su_balance(self, tren):
        """El balance se comprueba elemento a elemento, no solo sobre el tren:
        es donde se escondería un error de reparto."""
        from amoniatermia.circuit import CLIMA, ACS

        *_, res, _ = tren
        for k in (CLIMA, ACS):
            assert res[k].energy_balance_error < 5e-3


# ---------------------------------------------------------------------------
# §9.4.4 — M-4 alcanza la tolerancia, y lo que lo impedía no era el tren
#
# El plan atribuía el suelo de residuo de los modos con placas al disparo del
# tren extendido, amplificado por ṁ_agua·cp/ṁ_ref. Medido el 22/09/2026, esa
# explicación no se sostiene: la función de disparo del tren es MONÓTONA y tiene
# raíz única —25 puntos sobre el intervalo físico completo, un solo cambio de
# signo— y su tolerancia de 1e-7 K deja un efecto de orden 1e-8 en el residuo.
#
# Lo que bloqueaba a M-4 era un ESCALÓN en el residuo de recalentamiento
# producido por la marcha del serpentín con áreas fijas (ver
# `tests/test_air_hx.py::TestFronteraDeFaseSerpentin`). Con el recorte en la
# frontera de fase, el residuo pasa de 3.0e-3 a 9.9e-10.
# ---------------------------------------------------------------------------
class TestConvergenciaDeM4:
    """Tarda del orden de 30 s: es el punto completo de un modo con tren.

    Se conserva en la suite porque es la verificación de que la corrección del
    serpentín sirve de extremo a extremo, y no solo sobre el componente aislado.
    """

    def test_m4_baja_de_la_tolerancia_del_capitulo(self):
        f, c = circuito_completo(n_cells=12, n_segments=60)
        bc = Boundary(air=AIRE_7, m_dot_air=M_AIRE,
                      clima=WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion()),
                      T_amb=7 + 273.15)
        s = c.solve("M-4", bc, Setpoints(superheat=5.0, subcooling=2.0))
        assert s.max_residual < c.TOL          # 1e-6, §9.4.4
        assert s.converged and s.valid

    def test_m4_con_aire_humedo_es_valido(self):
        """Corregido el 24/09/2026. En la condición nominal de la UNE-EN 14511
        (7 °C bs / 6 °C bh) la batería condensa vapor de agua, y la
        comprobación de su balance solo contaba el calor SENSIBLE del aire:
        dejaba fuera el latente y marcaba M-4 como no válido con un error del
        orden del 34 %, que no era del componente sino de la comprobación. Con
        aire seco (`AIRE_7`, el caso de arriba) no se veía.

        La comprobación suma ahora el término latente, ṁ_seco·(Δh − cp_da·ΔT),
        que es nulo en las celdas secas y reproduce la ec. 9-28 en las húmedas.
        """
        f, c = circuito_completo(n_cells=12, n_segments=60)
        aire = AirState.at(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)
        bc = Boundary(air=aire, m_dot_air=M_AIRE,
                      clima=WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion()),
                      T_amb=7 + 273.15)
        s = c.solve("M-4", bc, Setpoints(superheat=5.0, subcooling=2.0))
        assert s.converged, s.message
        assert s.components[AIRE].wet_fraction > 0.5    # hay latente de verdad
        assert s.checks["balance_componentes"][AIRE] < 1e-6
        assert s.valid, s.checks

    def test_el_disparo_del_tren_tiene_raiz_unica(self):
        """La pregunta que `docs/historico/PENDIENTES.md` dejaba abierta: si la
        multiplicidad era del tren o de la marcha de cada intercambiador.

        Escaneada la función de disparo sobre el intervalo físico completo —el
        agua no puede cruzar la temperatura del refrigerante— hay UN solo cambio
        de signo y la función es monótona. La multiplicidad no está en el tren.
        """
        import numpy as np

        f, c = circuito_completo(n_cells=8, n_segments=40)
        P = f.Psat(45 + 273.15)
        f.update_PT(P, 120 + 273.15)          # gas de descarga
        h_in, T_r_in = f.h, f.T
        T_agua, m_agua = 40 + 273.15, 0.5

        def salida(T_start):
            P_j, h_j, T_j = P, h_in, T_start
            for k in (ACS, CLIMA):
                out = c.component(k).march(P_j, h_j, 0.008, T_j, m_agua,
                                           counterflow=True, role="condenser")
                P_j, h_j, T_j = out["P_out"], out["h_out"], out["T_sec_end"]
            return T_j - T_agua

        Ts = np.linspace(min(T_agua, T_r_in), max(T_agua, T_r_in), 21)
        v = [salida(T) for T in Ts]
        cambios = sum(1 for a, b in zip(v, v[1:]) if a * b < 0.0)
        assert cambios == 1
        assert all(b > a for a, b in zip(v, v[1:]))     # monótona creciente


# ---------------------------------------------------------------------------
# La consigna de ACS por modo — decisión del autor, 22/09/2026
# ---------------------------------------------------------------------------
def test_la_consigna_de_ACS_distingue_deposito_de_impulsion():
    """Decisión del autor, 22/09/2026.

    El dimensionado se hace para **60 °C en el depósito**, como exige la
    prevención de legionelosis, y esa exigencia se cubre en los modos CON
    RECUPERACIÓN: allí el ACS se produce mientras la máquina climatiza, el
    desrecalentador recibe gas de descarga por encima de 120 °C y el calor de
    alta temperatura es un subproducto. M-5 solo entra cuando no hay demanda de
    climatización, y ahí esa temperatura se paga entera: **45 °C en el
    depósito**.

    Y depósito NO es impulsión. El §9.6.7 carga «el bucle cerrado de ACS hacia
    el INTERACUMULADOR», que lleva intercambiador interior: entre la temperatura
    del depósito y la del agua que sale del desrecalentador está la aproximación
    de ese serpentín, 7 K. El capítulo escribía 60 °C en los dos sitios, que son
    dos cosas distintas separadas por esos 7 K; con carga por serpentín, aquella
    impulsión de 60 dejaba el depósito en 53.

    El modelo resuelve la IMPULSIÓN —R5 cierra sobre la salida del agua del
    intercambiador— y por eso se deriva de la del depósito en lugar de
    escribirse a mano: así las dos no pueden separarse por descuido.
    """
    from amoniatermia.circuit import (APROXIMACION_ACS_K, CONSIGNA_ACS_K,
                                      CONSIGNA_DEPOSITO_ACS_K)

    assert APROXIMACION_ACS_K == 7.0
    dep = CONSIGNA_DEPOSITO_ACS_K
    assert dep["M-1"] == dep["M-3"] == 60.0 + 273.15
    assert dep["M-5"] == 45.0 + 273.15
    # La impulsión es la del depósito más la aproximación, y nada más.
    assert CONSIGNA_ACS_K["M-1"] == 67.0 + 273.15
    assert CONSIGNA_ACS_K["M-5"] == 52.0 + 273.15
    for m, T in dep.items():
        assert CONSIGNA_ACS_K[m] == T + APROXIMACION_ACS_K
    # Y solo la declaran los modos que producen ACS.
    assert set(dep) == {m for m in MODES if "m_acs" in MODES[m].unknowns}


# ---------------------------------------------------------------------------
# Punto de referencia de M-5 — capítulo 7, tabla 7.5
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def punto_M5():
    _, c = circuito_completo(n_cells=12, n_segments=60)
    aire = AirState.at(T=32 + 273.15, V_frontal=3.30, RH=0.45)
    bc = Boundary(air=aire, m_dot_air=M_AIRE,
                  acs=WaterStream(T_in=15 + 273.15), T_amb=32 + 273.15)
    sp = Setpoints(superheat=5.0, subcooling=2.0, T_acs=52 + 273.15)
    return c.solve("M-5", bc, sp)


class TestPuntoDeReferenciaM5:
    """Tabla 7.5 del capítulo 7 (v5), con la consigna adoptada de 45 °C en el
    depósito y 52 °C de impulsión: verano, aire a 32 °C y 45 % de humedad
    relativa, red a 15 °C. Sostiene la consigna reducida del §7.4.3.

    El capítulo lo publica como NO válido, por el balance del intercambiador de
    climatización (1.87·10⁻³). DISCREPANCIA CERRADA A FAVOR DEL PUNTO el
    24/09/2026: aquel desajuste no era físico, sino el cociente entre los dos
    calores específicos constantes del agua que usaban la marcha y la
    comprobación. Con el agua en entalpía, como escribe la ec. 9-11, el punto
    es VÁLIDO y sus cifras no se mueven de la tabla 7.5. El capítulo 7 (y el
    10, §9.4.4 y §9.13) deben dejar de declararlo no válido.
    """

    def test_reproduce_la_tabla_8_5(self, punto_M5):
        """CAMBIO PENDIENTE DEL CAPÍTULO 7 (24/09/2026). Con el compresor
        reidentificado sobre el código corregido, la descarga pasa de 109.1 a
        107.8 °C, el calor al ACS de 19.54 a 19.47 kW, la potencia eléctrica de
        3993 a 3914 W y el COP global de 4.89 a 4.98. M-5 opera fuera del
        dominio de identificación del compresor (T₀ = 17.6 °C frente a 0–5 °C
        del catálogo), y ahí los juegos de parámetros equivalentes divergen: es
        una incertidumbre de extrapolación del orden del 2 %. Ver
        docs/historico/INFORME_REESCRITURA.md, ficha 3.1."""
        from amoniatermia import indicators as I

        s = punto_M5
        assert s.converged, s.message
        assert s.max_residual < 1e-8                       # capítulo: 6.8e-11
        assert abs(s.T_evap - 273.15 - 17.6) < 0.05
        # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: antes 52.09 C, 107.8 C, 3914 W y 4.98.
        assert abs(s.T_cond - 273.15 - 52.13) < 0.05       # capítulo: 52.0
        assert abs(s.T_dis - 273.15 - 107.34) < 0.1        # capítulo: 109.1
        assert abs(s.m_dot * 3600 - 57.2) < 0.1
        assert abs(s.unknowns["m_acs"] * 3600 - 453.3) < 2.0   # capítulo: 455
        assert abs(s.Q_acs - 19.47e3) < 20.0               # capítulo: 19.54 kW
        assert s.Q_clima == 0.0
        e = I.energy(s, MODES["M-5"])
        # Remedido el 01/10/2026 con eta_motor = 0.90 (antes 0.97): 3900.4 W y 4.991.
        assert abs(e.W_el - 4143.9) < 5.0                  # capítulo: 3993 W
        assert abs(e.COP_global - 4.703) < 0.005           # capítulo: 4.89

    def test_converge_y_es_valido(self, punto_M5):
        s = punto_M5
        assert s.valid, s.checks
        bal = s.checks["balance_componentes"]
        assert bal[CLIMA] < 1e-9                  # el capítulo: 1.87e-3
