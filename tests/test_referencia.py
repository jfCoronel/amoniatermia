"""
Valores de referencia del capítulo 9 de la tesis AMONIATERMIA.

Cada test cita el apartado del que sale el valor. Si el modelo los reproduce, está
bien; si no, el fallo está localizado en un submodelo concreto.

Estos son los contrastes que el §9.12.5 exige tener automatizados. Algunos son
puramente geométricos y deberían pasar desde el primer día; otros dependen de que
haya submodelos resueltos y fallarán hasta que existan.

Uso:  pytest tests/test_referencia.py -v
"""
from amoniatermia import data as D
import math
import pytest

TOL = 0.02          # 2 % para magnitudes calculadas
TOL_GEO = 0.005     # 0.5 % para magnitudes puramente geométricas


def rel(calculado, referencia):
    return abs(calculado - referencia) / abs(referencia)


# ---------------------------------------------------------------------------
# §9.7.1 — Reconstrucción geométrica de la batería Frimetal CBN-21 ESPECIAL
#
# Es la verificación previa a todo lo demás: si la geometría no reproduce las
# magnitudes de la ficha, el anclaje de la correlación del §9.7.3 absorbería el
# error geométrico dentro del coeficiente y perdería transferibilidad.
# ---------------------------------------------------------------------------
class TestGeometriaBateriaAire:
    """La geometría se lee del fichero de datos, no se repite aquí.

    Antes estos valores estaban escritos en el test, de modo que comprobaban la
    aritmética del capítulo pero no el dato que el modelo va a consumir. Al
    leerlos de `data/bateria_frimetal_cbn21.yaml` el test verifica además que el
    fichero de datos reproduce la ficha del fabricante, que es la condición
    previa del §9.7.1 para que el anclaje del §9.7.3 tenga sentido.
    """

    @pytest.fixture(autouse=True)
    def _geom(self):
        from amoniatermia import data as D
        g = D.air_coil().require("geometria")
        self.St = g["paso_transversal_m"]
        self.Sl = g["paso_longitudinal_m"]
        self.L = g["longitud_bateria_m"]
        self.Nt = g["tubos_por_rango"]
        self.Nr = g["n_rangos"]
        self.fp = g["paso_aleta_m"]
        self.tf = g["espesor_aleta_m"]
        self.do = g["diametro_exterior_m"]
        self.di = g["diametro_interior_m"]

    def test_tresbolillo_equilatero(self):
        """Sl = St·cos(30°). Necesario para el radio equivalente del §9.7.4."""
        assert rel(self.Sl, self.St * math.cos(math.radians(30))) < TOL_GEO

    def test_longitud_total_tubo(self):
        assert rel(self.Nt * self.Nr * self.L, 32.0) < TOL_GEO

    def test_area_total_frente_a_ficha(self):
        n_aletas = self.L / self.fp
        prof = self.Nr * self.Sl
        ancho = self.Nt * self.St
        a_fin = n_aletas * 2 * (ancho * prof
                                - self.Nt * self.Nr * math.pi / 4 * self.do**2)
        a_tubo = math.pi * self.do * (self.Nt * self.Nr * self.L) * (1 - self.tf / self.fp)
        assert rel(a_fin + a_tubo, 39.31) < 0.01      # ficha: 39.31 m²

    def test_volumen_interno_frente_a_ficha(self):
        v = self.Nt * self.Nr * self.L * math.pi / 4 * self.di**2
        assert rel(v, 3.8e-3) < 0.01                  # ficha: 3.8 L

    def test_velocidad_masica_frente_a_ficha(self):
        m_dot = 41.0 / 3600                           # kg/s, ficha
        a_paso = 2 * math.pi / 4 * self.di**2         # 2 circuitos
        assert rel(m_dot / a_paso, 48.0) < 0.01       # ficha: 48 kg/(m²·s)

    def test_fraccion_area_libre(self):
        sigma = (self.St - self.do) / self.St * (1 - self.tf / self.fp)
        assert rel(sigma, 0.6357) < TOL_GEO


# ---------------------------------------------------------------------------
# §9.7.3 / §9.7.4 — Lado de aire, eficiencia de aleta y reparto de resistencias
# ---------------------------------------------------------------------------
class TestLadoAire:
    def test_reynolds_punto_ficha(self):
        v_max = 3.30 / 0.6357
        rho, mu, d_c = 1.13, 1.89e-5, 0.0133 + 2 * 0.0001
        assert rel(rho * v_max * d_c / mu, 4190) < TOL

    def test_colburn_anclado(self):
        """C1 = 0.507 con C2 = -0.42 fijado a priori."""
        v_max = 3.30 / 0.6357
        rho, cp, pr = 1.13, 1005.0, 0.71
        j = 113.0 / (rho * v_max * cp) * pr ** (2 / 3)
        assert rel(j, 0.01526) < TOL
        assert rel(j / 4190 ** (-0.42), 0.507) < TOL

    @pytest.mark.parametrize("magnitud,referencia", [
        ("eficiencia_aleta_seca", 0.447),
        ("efectividad_superficial_seca", 0.465),
        ("eficiencia_aleta_humeda", 0.337),
        ("efectividad_superficial_humeda", 0.358),
    ])
    def test_eficiencia_aleta(self, magnitud, referencia):
        """Aleta anular equivalente, tresbolillo equilátero (§9.7.4, §9.7.6).

        El valor seco de 0.447 es muy inferior al 0.85 habitualmente supuesto:
        el paso de tubo de 40 mm da una altura de aleta efectiva de 14.6 mm.
        Usar la eficiencia seca en régimen húmedo sobreestima la conductancia
        del evaporador un 28 %.

        Los dos valores húmedos salen de la marcha por potencial entálpico del
        §9.7.6, con b' evaluada en la SUPERFICIE como manda la ec. 9-29 y no
        leída del fichero de datos.
        """
        from amoniatermia import Fluid
        from amoniatermia.components.air_hx import AirCoil, AirState
        from amoniatermia.geometry import FinnedCoilGeometry
        from amoniatermia import data as D

        df = D.air_coil()
        g = df.require("geometria")
        geom = FinnedCoilGeometry(
            S_t=g["paso_transversal_m"], S_l=g["paso_longitudinal_m"],
            L=g["longitud_bateria_m"], n_tubes_row=g["tubos_por_rango"],
            n_rows=g["n_rangos"], n_circuits=g["n_circuitos"],
            fin_pitch=g["paso_aleta_m"], fin_thickness=g["espesor_aleta_m"],
            d_o=g["diametro_exterior_m"], d_i=g["diametro_interior_m"],
            k_tube=df.require("conductividad_tubo_W_mK"),
            k_fin=df.require("conductividad_aleta_W_mK"))
        hx = AirCoil(Fluid("Ammonia"), geom)

        if magnitud.endswith("seca"):
            eta, eta_sa = hx.fin_efficiency(113.0)      # h_a del punto de ficha
        else:
            aire = AirState.at(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)
            h_air, _ = hx.air_side(aire)
            res = hx.wet_conductance(h_ref=2912.0, h_air=h_air,
                                     T_ref=1.6 + 273.15,
                                     T_surface=3.0 + 273.15,
                                     cp_da=aire.cp_da)
            eta, eta_sa = res["eta_fin"], res["eta_surface"]
        calculado = eta if magnitud.startswith("eficiencia") else eta_sa
        assert rel(calculado, referencia) < TOL

    def test_reparto_resistencias(self):
        """§9.7.4, tabla 9.18. Referido al área externa, en m²·K/W."""
        r_aire, r_pared, r_ref = 0.01905, 0.00102, 0.00611
        total = r_aire + r_pared + r_ref
        assert rel(total, 0.02618) < TOL
        assert rel(1 / total, 38.2) < TOL             # ficha: 43 -> sesgo conocido -11 %
        assert rel(100 * r_pared / total, 3.9) < 0.05 # con cobre sería 0.15 %


# ---------------------------------------------------------------------------
# §9.5.3 — Compresor Bock F2 NH3
# ---------------------------------------------------------------------------
class TestCompresor:
    def test_volumen_barrido(self):
        vd = 2 * math.pi / 4 * 0.045**2 * 0.038
        assert rel(vd * 1450 / 60 * 3600, 10.52) < TOL   # m³/h a 1450 rpm

    def test_rendimiento_volumetrico_M2(self):
        """Ec. 9-3 con C = 0.0386 (juego anterior, antigua tabla 10.4), n = 1.30
        y relación de compresión 3.85: 0.930. La v30 ya no publica esta cifra;
        se conserva como verificación de la fórmula. Con el C = 0.08821 del
        juego adoptado (tabla 9.8) sale 0.839."""
        c, n, rp = 0.0386, 1.30, 3.85
        assert rel(1 + c - c * rp ** (1 / n), 0.930) < TOL
        assert rel(1 + 0.08821 - 0.08821 * rp ** (1 / n), 0.839) < 0.005

    @staticmethod
    def _compresor(variant="reidentificacion"):
        from amoniatermia import Fluid, data as D
        from amoniatermia.components.compressor import SemiEmpiricalCompressor
        return SemiEmpiricalCompressor(
            Fluid("Ammonia"), D.compressor_geometry(),
            D.compressor_params(variant=variant))

    def test_temperatura_descarga_M2(self):
        """§9.7.8: con la condensación impuesta a 46.8 °C (T_evap = 2 °C,
        recalentamiento 1 K) el juego adoptado da 125.5 °C, «y ese es el valor
        con el que se juzga la identificación», y el que alimenta el punto de
        diseño del desrecalentador del §9.6.7.

        El juego anterior da en ese punto, según la v30, 142.0 °C frente a los
        140.4 que publicaba la revisión previa. DISCREPANCIA MENOR, REPORTADA:
        el modelo da 141.3 °C con ese juego, entre las dos cifras.
        """
        from amoniatermia import Fluid

        f = Fluid("Ammonia")
        args = (f.Psat(2 + 273.15), 2 + 273.15 + 1.0, f.Psat(46.8 + 273.15))
        adoptado = self._compresor().solve(*args).T_dis - 273.15
        anterior = self._compresor("original").solve(*args).T_dis - 273.15
        assert abs(adoptado - 125.5) < 0.1
        assert 140.4 < anterior < 142.0         # la v30 dice 142.0; el modelo 141.3

    def test_el_juego_anterior_da_la_columna_de_la_tabla_10_9(self):
        """Discrepancia CERRADA en la v30. La revisión previa declaraba ±2.7 %,
        ±6.6 % y ±10.5 K para el juego de la antigua tabla 10.4, y ese juego no
        los alcanzaba. La v30 lo sustituye por la reidentificación y publica
        las dos columnas en la tabla 9.9: el juego anterior da ±4.46 %, ±9.85 %
        y ±16.8 K, con un sesgo de +14.25 K en la descarga, casi constante.
        """
        from amoniatermia import data as D

        rep = self._compresor("original").report(D.compressor_catalog())
        assert rep["n"] == 46
        assert abs(rep["m_dot"]["max_abs_rel"] - 0.0446) < 0.0005
        assert abs(rep["W_shaft"]["max_abs_rel"] - 0.0985) < 0.0005
        assert abs(rep["T_dis"]["max_abs_K"] - 16.8) < 0.1

    def test_la_reidentificacion_si_alcanza_la_exactitud_declarada(self):
        """La misma estructura de nueve parámetros, los mismos 46 puntos y la
        misma función objetivo (peso ×4 en T_dis) sí cumplen lo declarado.

        Es el juego por defecto desde el 16/09/2026, por decisión del autor.

        La consecuencia para H3 es material: en el equilibrio de M-2 predice
        125.5 °C en lugar de 140.4 °C, y el catálogo del fabricante da 122.2 °C
        a T₀ = 2 / T_k = 45.
        """
        from amoniatermia import Fluid, data as D

        c = self._compresor()          # juego por defecto desde el 16/09/2026
        rep = c.report(D.compressor_catalog())
        assert rep["n_resueltos"] == 46
        # tabla 9.9 con el juego adoptado el 24/09/2026 (la v30 publica
        # 2.72 % / 5.18 % / 3.66 K, del juego identificado con el compresor que
        # caía en la meseta de max(T1, T_su))
        assert abs(rep["m_dot"]["max_abs_rel"] - 0.0271) < 0.0005
        assert abs(rep["W_shaft"]["max_abs_rel"] - 0.0472) < 0.0005
        assert abs(rep["T_dis"]["max_abs_K"] - 3.35) < 0.05
        # y sin sesgo: el error de T_dis es dispersión, no desplazamiento
        assert abs(rep["T_dis"]["rmse_K"] - 1.65) < 0.05

        f = Fluid("Ammonia")
        r = c.solve(f.Psat(2 + 273.15), 2 + 273.15 + 1.0, f.Psat(46.8 + 273.15))
        assert 122.0 < r.T_dis - 273.15 < 129.0

    def test_pesos_de_la_ecuacion_9_10(self):
        """§9.4.3.1: w1 = w2 = 1 y w3 = 16 en la ec. 9-10. `identify` recibe
        (1, 1, 4) porque pondera el RESIDUO y `least_squares` minimiza la suma de
        sus cuadrados; el peso de la ecuación es el cuadrado. En el óptimo
        vigente las tres magnitudes aportan el 29, 33 y 38 % del objetivo, y
        1 K de descarga equivale a un 0.28 % a la media del catálogo (363 K)."""
        import inspect
        import numpy as np
        from amoniatermia import data as D
        from amoniatermia.components.compressor import SemiEmpiricalCompressor

        w = inspect.signature(SemiEmpiricalCompressor.identify).parameters["weights"].default
        assert tuple(x ** 2 for x in w) == (1.0, 1.0, 16.0)

        c = self._compresor()
        cat = D.compressor_catalog()
        dm, dW, dT, T = [], [], [], []
        for pt in cat:
            r = c.solve(pt["P_ad"], pt["T_su"], pt["P_ex"], pt.get("T_amb", 298.15))
            dm.append((r.m_dot - pt["m_dot"]) / pt["m_dot"])
            dW.append((r.W_shaft - pt["W_shaft"]) / pt["W_shaft"])
            dT.append((r.T_dis - pt["T_dis"]) / pt["T_dis"])
            T.append(pt["T_dis"])
        partes = np.array([np.sum(np.square(dm)), np.sum(np.square(dW)),
                           16.0 * np.sum(np.square(dT))])
        cuotas = partes / partes.sum()
        assert np.allclose(cuotas, [0.291, 0.332, 0.378], atol=0.005)
        assert abs(np.mean(T) - 363.2) < 0.1

    def test_el_catalogo_contradice_los_140_grados(self):
        """Hecho independiente de cualquier modelo: a T₀ = 2 °C y T_k = 45 °C el
        fabricante publica 122.2 °C. Los 140.4 °C de la revisión previa quedaban 18 K por
        encima, y de esa diferencia depende la potencia recuperable en el
        desrecalentador y con ella H3."""
        from amoniatermia import data as D

        pt = [p for p in D.compressor_catalog()
              if abs(p["T0"] - 275.15) < 0.01 and abs(p["Tc"] - 318.15) < 0.01][0]
        assert rel(pt["T_dis"] - 273.15, 122.2) < 0.01
        assert 140.4 - (pt["T_dis"] - 273.15) > 15.0


# ---------------------------------------------------------------------------
# Validación de la batería como evaporador: ficha de Frimetal del 26/03/2026
#
# DECISIÓN DEL AUTOR, 28/09/2026: la ficha es fuente de VALIDACIÓN (N2 de la
# tabla 6.5) y no interviene en ningún parámetro. Evaporador a bomba, entrada
# líquida, 26 kg/h a 4 °C, aire a 7 °C y 75 %, superficie seca. Estos
# contrastes fijan lo que el modelo predice SIN AJUSTE frente a ella.
# ---------------------------------------------------------------------------
class TestValidacionBateriaEvaporador:

    @staticmethod
    def _bateria(correlacion, n=120):
        from amoniatermia import AirCoil, AirState, Fluid
        from amoniatermia import data as D

        df = D.load("bateria_frimetal_cbn21")
        p = "punto_ficha_evaporador."
        f = Fluid("Ammonia")
        P = f.Psat(df.require(p + "T_evap_C") + 273.15)
        sat = f.sat_props(P)
        aire = AirState.at(df.require(p + "aire.T_in_C") + 273.15,
                           df.require(p + "aire.velocidad_frontal_m_s"),
                           RH=df.require(p + "aire.HR_in"))
        coil = AirCoil(f, D.air_coil_geometry(), n_segments=n,
                       corr={"tube_boiling": correlacion})
        r = coil.solve(P, sat["h_l"], df.require(p + "caudal_refrigerante_kg_h") / 3600,
                       aire, df.require(p + "aire.caudal_masico_kg_h") / 3600,
                       role="evaporator")
        x_out = (r.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
        return r, x_out, df.require(p + "capacidad_W")

    def test_la_ficha_es_de_validacion_y_no_de_anclaje(self):
        from amoniatermia import data as D
        from amoniatermia.validation import plan as V
        assert D.load("bateria_frimetal_cbn21").require(
            "punto_ficha_evaporador.uso") == "validacion"
        assert V.sources()["ficha_frimetal_cbn21_evaporador"].sirve_para_validar

    def test_la_correlacion_principal_reproduce_la_ficha_al_5_por_ciento(self):
        """Gungor-Winterton, la principal del §9.7.5: 3124 W frente a 2999 W,
        +4.2 %, y el mismo título de salida que exige la recirculación 3."""
        r, x_out, Q_ficha = self._bateria("gungor_winterton")
        assert rel(r.Q_dot, 3124.0) < TOL             # la cifra del modelo
        assert 0.0 < r.Q_dot / Q_ficha - 1.0 < 0.05   # la del contraste
        assert rel(x_out, 0.347) < TOL                # ficha: 1/3
        assert rel(r.U_mean, 33.6) < TOL              # ficha: 32

    def test_la_superficie_sale_seca_como_en_la_ficha(self):
        r, _, _ = self._bateria("gungor_winterton")
        assert r.wet_fraction == 0.0 and r.Q_latent == 0.0

    def test_la_ficha_descarta_la_estratificacion_y_el_nucleado_solo(self):
        """Las dos alternativas registradas quedan un 23 y un 29 % por debajo:
        la ficha discrimina entre las correlaciones de la banda."""
        for nombre, Q in (("gungor_winterton_horizontal", 2310.0),
                          ("cooper_solo", 2130.0)):
            r, _, Q_ficha = self._bateria(nombre)
            assert rel(r.Q_dot, Q) < TOL
            assert r.Q_dot / Q_ficha - 1.0 < -0.20


# ---------------------------------------------------------------------------
# §9.7.8 — Equilibrio del sistema en M-2
#
# El punto de ficha NO es el punto de operación: la ficha se calculó con
# entrada de vapor saturado, pero en M-2 la batería recibe el gas directamente
# de la descarga y evacúa además el calor de desrecalentamiento.
# ---------------------------------------------------------------------------
class TestEquilibrioM2:
    """Resuelto el 17/09/2026 con el lazo externo del §9.4 (fase E).

    La configuración es la del propio §9.7.8: temperatura de evaporación
    impuesta a 2 °C, aire exterior a 35 °C y caudal de ficha, sin modelar el
    lado de baja. El equilibrio lo determina la condición de condensación
    completa a la entrada de la válvula.
    """

    @staticmethod
    def _equilibrio(n=400):
        from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid,
                                  SemiEmpiricalCompressor, Setpoints)
        from amoniatermia import data as D

        f = Fluid("Ammonia")
        c = Circuit(f,
                    SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                            D.compressor_params()),
                    AirCoil(f, D.air_coil_geometry(), n_segments=n),
                    None, None)
        bc = Boundary(air=AirState(T=35 + 273.15, V_frontal=3.30),
                      m_dot_air=None, T_amb=35 + 273.15)
        return c.solve("M-2", bc,
                       Setpoints(superheat=1.0, subcooling=0.0,
                                 T_evap=2 + 273.15))

    def test_el_equilibrio_se_resuelve_y_es_valido(self):
        """Lo que la fase E tenía que entregar: el sistema de la tabla 9.4
        anulado, con las verificaciones independientes del §9.4.4 en verde."""
        s = self._equilibrio()
        assert s.converged and s.valid
        assert s.max_residual < 1e-6

    def test_el_equilibrio_de_la_tabla_10_19(self):
        """Tabla 9.19 y §9.4.1: condensación a 44.9 °C, 11.73 kW evacuados,
        9.52 kW frigoríficos, 2.478 kW al eje, 32.58 kg/h y descarga a 120.1 °C.

        Discrepancia CERRADA en la v30 a favor del modelo. La revisión previa
        declaraba 46.8 °C, 13.2 kW y 10.3 kW; la diferencia estaba en el caudal
        del compresor, y el catálogo del fabricante decide (ver
        `test_el_catalogo_no_soporta_la_capacidad_declarada`).
        """
        s = self._equilibrio()
        assert abs(s.T_cond - 273.15 - 44.9) < 0.05
        assert rel(-s.Q_high, 11.73e3) < 0.002
        assert rel(s.Q_evap, 9.52e3) < 0.002
        assert rel(s.W_shaft, 2478.0) < 0.001
        assert rel(s.m_dot * 3600, 32.58) < 0.001
        # CAMBIO PENDIENTE DEL CAPITULO, 24/09/2026: con el compresor corregido
        # y reidentificado la descarga sale 120.0 C, no el 120.1 publicado.
        # Remedido el 29/09/2026 (recorte de frontera corregido): 119.97 C.
        assert abs(s.T_dis - 273.15 - 119.97) < 0.01

    def test_capacidad_frigorifica_y_presupuesto_de_RS5(self):
        """La capacidad es SALIDA del modelo, no dato de entrada, y RS-5 se
        evalúa contra ella (§9.9): con 9.52 kW el presupuesto del sistema es
        de 476 g, un 8 % más estrecho que los 515 g de la revisión previa.

        Primera fila de la tabla 9.22, subenfriamiento nulo: la batería del
        equilibrio contiene 177–327 g. DISCREPANCIA REPORTADA: la tabla la da
        como el 61 % del presupuesto, y 327/476 es el 69 %. Las filas 2 a 4 de
        esa columna (90/108/126 %) están calculadas contra 515 g, no contra 476.
        """
        s = self._equilibrio()
        assert rel(s.charge["_RS5_limite_kg"], 0.476) < 0.002
        assert rel(s.charge["_min"], 0.177) < 0.01
        assert rel(s.charge["_max"], 0.327) < 0.01
        assert abs(s.charge["_RS5_peor_caso"] - 0.686) < 0.005   # tabla: 61 %

    def test_la_tabla_10_22_el_anegado_decide_RS5(self):
        """Tabla 9.22 rehecha el 25/09/2026 con el MISMO equilibrio de M-2 y
        subenfriamiento de consigna creciente. La v30 publicaba 333–464 g con el
        8 % anegado a 7.3 K y porcentajes calculados contra 515 g; sus filas 2 a
        4 no tienen procedencia documentada y no las reproduce el equilibrio.

        Con 7.3 K la batería sola contiene 364–498 g con el 9 % del volumen
        anegado: el 102 % del presupuesto de RS-5 a la capacidad de ESA fila
        (el subenfriamiento sube la capacidad a 9.73 kW y el presupuesto a
        487 g). Con 10.6 K, 528–648 g y el 133 %. La conclusión del §9.9 sale
        reforzada: el anegado, y no la correlación, decide H4."""
        from amoniatermia import (AirCoil, AirState, Boundary, Circuit, Fluid,
                                  SemiEmpiricalCompressor, Setpoints)
        from amoniatermia import data as D

        f = Fluid("Ammonia")
        c = Circuit(f, SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                               D.compressor_params()),
                    AirCoil(f, D.air_coil_geometry(), n_segments=400),
                    None, None)
        bc = Boundary(air=AirState(T=35 + 273.15, V_frontal=3.30),
                      m_dot_air=None, T_amb=35 + 273.15)
        x0, filas = None, {}
        for sc in (7.3, 10.6):
            s = c.solve("M-2", bc, Setpoints(superheat=1.0, subcooling=sc,
                                             T_evap=2 + 273.15), x0=x0)
            assert s.converged and s.valid
            x0 = dict(s.unknowns)
            filas[sc] = s
        s7 = filas[7.3]
        assert abs(s7.components["bateria"].volume_fraction["liquido"]
                   - 0.092) < 0.005
        assert rel(s7.charge["_min"], 0.364) < 0.01
        assert rel(s7.charge["_max"], 0.498) < 0.01
        assert abs(s7.charge["_RS5_peor_caso"] - 1.02) < 0.01
        s10 = filas[10.6]
        assert rel(s10.charge["_max"], 0.648) < 0.01
        assert abs(s10.charge["_RS5_peor_caso"] - 1.33) < 0.01

    def test_el_catalogo_no_soporta_la_capacidad_declarada(self):
        """Hecho independiente de cualquier modelo, como el de los 140.4 °C: a
        T₀ = 2 °C el fabricante publica 9.46 kW a T_k = 45 y 8.97 kW a T_k = 50.
        Interpolando, a 46.8 °C serían 9.28 kW, un 11 % por debajo de los
        10.3 kW de la revisión previa. Aquella capacidad no procedía del
        catálogo; la v30 publica la del modelo, a menos de un 3 % de él."""
        from amoniatermia import data as D

        pts = {p["Tc"]: p for p in D.compressor_catalog()
               if abs(p["T0"] - 275.15) < 0.01}
        q45, q50 = pts[45 + 273.15]["Q0"], pts[50 + 273.15]["Q0"]
        assert rel(q45, 9460.0) < 0.01
        q468 = q45 + (q50 - q45) * (46.8 - 45.0) / 5.0
        assert (10.3e3 - q468) / q468 > 0.10


# ---------------------------------------------------------------------------
# §9.9 — Inventario de carga en la batería de aire
#
# El modelo NUNCA debe reportar un valor único de carga: siempre el rango de las
# cuatro correlaciones, con H4 contrastada frente al valor más desfavorable.
# ---------------------------------------------------------------------------
class TestInventarioCarga:
    REFERENCIA = {            # condensación a 45 °C, x: 1 -> 0, sobre 3.8 L
        "homogeneo":           (0.930, 52.6, 0.200),
        "deslizamiento":       (0.844, 100.6, 0.382),
        "lockhart_martinelli": (0.878, 82.1, 0.312),
        # CORREGIDO el 16/09/2026. La tabla 9.21 daba 0.865 / 89.2 / 0.339
        # para esta fila, pero ese valor no se obtuvo con Rouhani-Axelsson sino
        # con Smith (1969, K = 0.4), un modelo de flujo separado con arrastre
        # que no depende del flujo másico. La descripción del §9.9 —«la
        # distribución radial de fases y el efecto del flujo másico»— es
        # inequívocamente Rouhani-Axelsson; el número no lo era.
        "flujo_deriva":        (0.824, 112.1, 0.426),
    }

    #: Valor que figuraba en la tabla 9.21 antes de la corrección, conservado
    #: para verificar de dónde salía. Ver `test_la_fila_antigua_era_smith`.
    FILA_ANTIGUA_SMITH = (0.865, 89.2, 0.339)

    #: Anclas de reproducibilidad de la fila corregida (capítulo v25). Fijarlas
    #: es lo que impide que la misma discrepancia se reabra: sin ellas, dos
    #: cálculos con formas distintas de C₀ o con otro flujo másico dan números
    #: distintos y ninguno de los dos es identificable como el del capítulo.
    ANCLAS = {
        "forma_C0": "1 + 0.12*(1-x)",
        "G_kg_m2s": 48.0,              # §9.7.1, 41 kg/h en 2 circuitos de 12.3 mm
        "sigma_mN_m": 15.98,           # NH₃ a 45 °C
        "promedio": "uniforme en título",
    }

    #: Lo que darían otras elecciones, para que la comparación sea reproducible.
    VARIANTES = {
        ("1 + 0.20*(1-x)", 48.0):  (0.800, 125.4, 0.477),
        ("1 + 0.12*(1-x)", 200.0): (0.865, 89.1, 0.339),   # converge con Smith
    }

    #: Familia de la tabla 9.21 -> nombre registrado en el modelo.
    REGISTRADA = {
        "homogeneo":           "homogeneous",
        "deslizamiento":       "zivi",
        "lockhart_martinelli": "lockhart_martinelli",
        "flujo_deriva":        "rouhani_axelsson",
    }

    @staticmethod
    def _promedio(nombre, n=2001, G=48.0):
        """Promedio UNIFORME EN TÍTULO de α y de la densidad media.

        Que el promedio de la tabla 9.21 sea uniforme en título y no ponderado
        por longitud no lo dice el capítulo: se ha determinado al reproducir los
        valores, y conviene declararlo en él (§9.9).
        """
        import numpy as np
        from amoniatermia.props import Fluid
        from amoniatermia.correlations.voidfraction import charge_range

        f = Fluid("Ammonia")
        sat = f.sat_props(f.Psat(45 + 273.15))
        xs = np.linspace(1e-4, 1 - 1e-4, n)
        # G y D_h de la batería: 48 kg/(m²·s) en tubo de 12.3 mm (§9.7.1)
        vals = [charge_range(x, sat, G, 0.0123, names=(nombre,))[nombre]
                for x in xs]
        alpha = float(np.mean([v["alpha"] for v in vals]))
        rho = float(np.mean([v["rho_mean"] for v in vals]))
        return alpha, rho, rho * 3.8e-3      # α, ρ̄ [kg/m³], masa [kg]

    @pytest.mark.parametrize("familia", list(REFERENCIA))
    def test_carga_por_correlacion(self, familia):
        alpha_ref, rho_ref, masa_ref = self.REFERENCIA[familia]
        alpha, rho, masa = self._promedio(self.REGISTRADA[familia])
        assert rel(alpha, alpha_ref) < TOL
        assert rel(rho, rho_ref) < TOL
        assert rel(masa, masa_ref) < TOL

    def test_las_cuatro_familias_estan_registradas(self):
        """§9.9: la banda de carga son las cuatro familias del §9.9."""
        from amoniatermia.correlations.voidfraction import CORRELACIONES_HUECOS
        assert set(CORRELACIONES_HUECOS) == set(self.REGISTRADA.values())

    def test_anclas_de_reproducibilidad(self):
        """Las condiciones bajo las que la fila corregida es reproducible.

        Si alguna de estas cambia, el 0.824 deja de ser comparable y hay que
        recalcular la tabla, no reinterpretarla.
        """
        from amoniatermia.props import Fluid
        f = Fluid("Ammonia")
        sat = f.sat_props(f.Psat(45 + 273.15))
        assert rel(sat["sigma"] * 1e3, self.ANCLAS["sigma_mN_m"]) < 0.005
        # la forma de C0 que el modelo emplea, leída del propio registro
        from amoniatermia.correlations import info
        notas = info("voidfraction", "rouhani_axelsson").validity.notes
        assert "C0 = 1 + 0.12(1-x)" in notas

    def test_variante_de_C0_y_dependencia_con_G(self):
        """Valores que darían la forma alternativa de C₀ y otros flujos másicos.

        Se tabulan para que la comparación sea reproducible y no se vuelva a
        abrir la misma discrepancia por usar una variante distinta sin decirlo.
        """
        import numpy as np

        from amoniatermia.props import Fluid
        from amoniatermia.correlations.voidfraction import zuber_findlay

        f = Fluid("Ammonia")
        sat = f.sat_props(f.Psat(45 + 273.15))
        xs = np.linspace(1e-4, 1 - 1e-4, 2001)

        for (forma, G), (a_ref, r_ref, m_ref) in self.VARIANTES.items():
            coef = float(forma.split("+")[1].split("*")[0])
            a = np.array([zuber_findlay(
                x, sat["rho_l"], sat["rho_v"], G=G, sigma=sat["sigma"],
                C0=1.0 + coef * (1.0 - x)) for x in xs])
            rho = float((a * sat["rho_v"] + (1 - a) * sat["rho_l"]).mean())
            assert rel(float(a.mean()), a_ref) < TOL, (forma, G)
            assert rel(rho, r_ref) < TOL, (forma, G)
            assert rel(rho * 3.8e-3, m_ref) < TOL, (forma, G)

    def test_la_fila_antigua_era_smith(self):
        """De dónde salía el 0.865 de la tabla 9.21 antes de la corrección.

        No es una variante de Rouhani-Axelsson: es la correlación de Smith
        (1969) con K = 0.4. Este test fija esa trazabilidad, que es lo que
        permite defender la corrección ante el tribunal en lugar de presentarla
        como un cambio de número sin explicación.
        """
        alpha, rho, masa = self._promedio("smith")
        a_ref, r_ref, m_ref = self.FILA_ANTIGUA_SMITH
        assert rel(alpha, a_ref) < TOL
        assert rel(rho, r_ref) < TOL
        assert rel(masa, m_ref) < TOL

    def test_solo_el_flujo_de_deriva_depende_del_flujo_masico(self):
        """§9.9: la cuarta familia «incorpora el efecto del flujo másico».

        Es la propiedad que distingue a Rouhani-Axelsson de las otras tres, y la
        que hace que sea la formulación físicamente más apropiada aquí.
        """
        for nombre in ("homogeneous", "zivi", "lockhart_martinelli", "smith"):
            assert self._promedio(nombre, G=48.0)[0] == pytest.approx(
                self._promedio(nombre, G=400.0)[0], rel=1e-9)
        assert self._promedio("rouhani_axelsson", G=48.0)[0] < \
            self._promedio("rouhani_axelsson", G=400.0)[0]

    def test_a_flujo_masico_alto_el_flujo_de_deriva_converge_con_smith(self):
        """El matiz que refuerza el argumento de H4 en lugar de debilitarlo.

        A G = 48 kg/(m²·s) —el valor de esta batería— Rouhani-Axelsson predice
        426 g frente a los 339 g de Smith. A G = 200 ambas convergen. Ese flujo
        másico es bajo precisamente porque el elevado calor latente del amoníaco
        reduce el caudal circulante: la correlación físicamente más apropiada
        para este caso es la que más carga predice, y lo es por la misma razón
        por la que el amoníaco tiene el problema de carga.
        """
        masa_48 = self._promedio("rouhani_axelsson", G=48.0)[2]
        masa_200 = self._promedio("rouhani_axelsson", G=200.0)[2]
        masa_smith = self._promedio("smith")[2]
        assert rel(masa_48, 0.426) < TOL
        assert rel(masa_200, masa_smith) < TOL       # convergen
        assert masa_48 / masa_smith > 1.25           # 426 / 339

    def test_dispersion_entre_correlaciones(self):
        """Pasa de factor 1.9 a 2.1 con la corrección del flujo de deriva."""
        masas = [v[2] for v in self.REFERENCIA.values()]
        assert rel(max(masas) / min(masas), 2.13) < 0.05

    def test_presupuesto_RS5(self):
        """RS-5: <= 50 g/kW referidos a la capacidad que el modelo calcula
        (§9.9). Con los 9.52 kW del equilibrio de M-2, 476 g para TODO el
        sistema, no los 515 g de la revisión previa.

        Con la batería supuesta bifásica en sus 3.8 L (tabla 9.21), la banda
        de 200–426 g sería entre el 42 % y el 89 % del presupuesto, y en el
        extremo desfavorable quedarían 50 g para todo lo demás. El §9.9 matiza
        que integrada por segmentos la carga es menor y que lo que decide es el
        anegado del condensador (tabla 9.22); el equilibrio lo fija
        `TestEquilibrioM2.test_capacidad_frigorifica_y_presupuesto_de_RS5`.
        """
        capacidad_kW = 9.52
        presupuesto_g = 50 * capacidad_kW
        masas_g = [v[2] * 1000 for v in self.REFERENCIA.values()]
        assert rel(presupuesto_g, 476) < 0.002
        assert 0.41 < min(masas_g) / presupuesto_g < 0.43
        assert 0.88 < max(masas_g) / presupuesto_g < 0.91
        assert 45 < presupuesto_g - max(masas_g) < 55


# ---------------------------------------------------------------------------
# §9.12.4 — Decisiones de implementación con efecto sobre los resultados
# ---------------------------------------------------------------------------
class TestImplementacion:
    """La marca de extrapolación (operar fuera de la base experimental se marca, no se
    silencia) la fijan `test_extrapolacion.py` y `test_circuit.py`. La velocidad del estado
    reutilizado frente a `PropsSI` es una medida de la máquina, no una verificación, y se
    documenta en CLAUDE.md."""

    #: Conversiones a bar o kW admitidas en el núcleo numérico, por su contenido y con motivo.
    PERMITIDAS = {
        "M_g = M_kg_mol * 1000.0": "Cooper (1984) está formulada con la masa molar en g/mol",
        "0.050 * Q_evap / 1000.0": "criterio RS-5, 50 g/kW, expresado en kg/W",
    }

    def test_unidades_SI_en_frontera(self):
        """El núcleo numérico no trabaja en bar ni en kW (§9.1.2): no multiplica ni divide por
        1e5, 1e3 o sus inversos. Las temperaturas en °C sí aparecen fuera de `units`, de forma
        declarada: al leer datos de catálogo y en los polinomios de UNE-EN 12900, que la norma
        formula en °C."""
        import io
        import tokenize
        from pathlib import Path
        raiz = Path(__file__).resolve().parents[1] / "src" / "amoniatermia"
        nucleo = ["components", "correlations", "props.py", "geometry.py", "psychrometrics.py",
                  "circuit.py"]
        ficheros = [p for n in nucleo
                    for p in ((raiz / n).rglob("*.py") if (raiz / n).is_dir() else [raiz / n])]
        omitir = (tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE,
                  tokenize.INDENT, tokenize.DEDENT)
        hallazgos = []
        for f in ficheros:
            texto = f.read_text(encoding="utf-8")
            lineas = texto.splitlines()
            toks = [t for t in tokenize.generate_tokens(io.StringIO(texto).readline)
                    if t.type not in omitir]
            for a, b in zip(toks, toks[1:]):
                if (a.string in ("*", "/") and b.type == tokenize.NUMBER
                        and float(b.string) in (1e5, 1e-5, 1e3, 1e-3)):
                    linea = lineas[b.start[0] - 1]
                    if not any(k in linea for k in self.PERMITIDAS):
                        hallazgos.append(f"{f.relative_to(raiz)}:{b.start[0]}: {linea.strip()}")
        assert not hallazgos, "conversiones de unidades en el núcleo:\n" + "\n".join(hallazgos)


# ---------------------------------------------------------------------------
# §9.6.7 — Punto de diseño del desrecalentador de ACS
#
# Sostiene H3. La revisión previa lo calculó con T_descarga = 140.4 °C; la
# v30 lo rehace con los 125.5 °C del juego adoptado y con la impulsión de
# 67 °C (tabla 9.13). Esta clase conserva el cálculo EXPLORATORIO con β y
# φc·φv supuestos, que es de donde salen las dos primeras filas de esa tabla;
# el punto publicado, con la geometría adoptada, lo fija
# `TestRetornoDelPrimarioACS`.
# ---------------------------------------------------------------------------
class TestDesrecalentador:
    #: φc y φv son datos PENDIENTES (§9.6.4) y β tampoco está declarado.
    #: Inyectarlos permite resolver, pero los resultados son exploratorios.
    PHI = {"plate_condensation": {"phi_c": 1.0, "phi_v": 1.0}}
    BETA_SUPUESTO = 60.0

    def _resolver(self, T_in_C, m_acs_kgh, n=60):
        from amoniatermia import Fluid, data as D
        from amoniatermia.components.plate_hx import PlateHeatExchanger

        geom = D.plate_geometry("desrecalentador_acs",
                                beta_c=math.radians(self.BETA_SUPUESTO),
                                t_p=0.0004)
        f = Fluid("Ammonia")
        P = f.Psat(45 + 273.15)
        hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=n,
                                role="condenser", corr_params=self.PHI)
        f.update_PT(P, T_in_C + 273.15)
        r = hx.solve(P, f.h, m_dot=40.3 / 3600, T_sec_in=35 + 273.15,
                     m_sec=m_acs_kgh / 3600)
        f.update_PH(P, r.h_ref_out)
        return r, f.T - 273.15

    def test_reproduce_el_punto_de_diseno_de_la_revision_previa(self):
        """Revisión previa del §9.6.7: 90.6 kg/h de ACS calientan de 35 a
        60 °C transfiriendo 2.63 kW, con el refrigerante saliendo a 55.9 °C.
        La v30 ya no lo publica; se conserva porque fija de dónde se partió.

        Con Martin a ambos lados —que es la correlación que el apartado dice
        haber empleado— y la entrada a 140.4 °C, el modelo lo reproduce dentro
        de la tolerancia. Es lo que permite usarlo para rehacer el punto.
        """
        r, T_out = self._resolver(140.4, 90.6)
        assert r.converged
        # previa: 60 °C. Remedido el 29/09/2026: 61.8 °C (3.0 %), por el recorte
        # de frontera corregido; se amplía la tolerancia de esta cifra histórica.
        assert rel(r.T_sec_out - 273.15, 60.0) < 0.035
        assert rel(-r.Q_dot, 2630.0) < 0.10                # previa: 2.63 kW
        assert T_out > 45.0                                 # no condensa

    def test_con_la_descarga_corregida_la_potencia_recuperada_cae(self):
        """La consecuencia de la fase B sobre H3: filas 1 y 2 de la tabla 9.13.

        Con 125.5 °C en lugar de 140.4 °C, alcanzar los 60 °C exige bajar el
        caudal de ACS y la potencia recuperada cae un 15 %, caída robusta por
        ser un cociente entre dos puntos de la misma geometría.

        DISCREPANCIA REPORTADA en las cifras absolutas. La tabla publica ~93 y
        ~80 kg/h, ~2.72 y ~2.32 kW, que son las de este cálculo el 18/09/2026.
        Hoy da 97.8 / 83.4 kg/h y 2.84 / 2.42 kW, y con la geometría adoptada
        99.2 / 84.8 kg/h y 2.88 / 2.46 kW. Esa última cifra es la que el propio
        §9.6.7 cita en el texto («de 2463 a 2371 W»), de modo que la fila 2 de
        la tabla contradice al párrafo que la acompaña.
        """
        from scipy.optimize import brentq

        def caudal_para_60C(T_in):
            return brentq(
                lambda m: self._resolver(T_in, m)[0].T_sec_out - 273.15 - 60.0,
                10.0, 200.0, xtol=0.05)

        m_cap, m_corr = caudal_para_60C(140.4), caudal_para_60C(125.5)
        Q_cap = -self._resolver(140.4, m_cap)[0].Q_dot
        Q_corr = -self._resolver(125.5, m_corr)[0].Q_dot

        assert m_corr < m_cap
        # La CAÍDA del 15 % es invariante a la corrección del hueco de canal del
        # 18/09/2026: con 1.72 mm en lugar de 2.09 los caudales suben de 87/74 a
        # 93/80 kg/h y las potencias de 2.53/2.14 a 2.72/2.32 kW, pero el
        # cociente no se mueve. La conclusión sobre H3 es robusta a la geometría.
        assert 0.10 < 1.0 - Q_corr / Q_cap < 0.20          # ≈15 %
        assert 2350 < Q_corr < 2500                        # tabla: ~2320

    def test_el_criterio_de_no_condensar_sigue_cumpliendose(self):
        """§9.6.7 exige que el refrigerante no descienda de T_sat(T_c) dentro
        del desrecalentador, para que en M-1 trabaje siempre en fase vapor.

        El margen se estrecha por tres vías sucesivas, todas en el mismo sentido,
        y conviene seguir la serie completa porque la conclusión sobre H3 depende
        de dónde acabe:

        | | margen catálogo / descarga corregida |
        |---|---|
        | §9.6.7, geometría original | 13.8 / 12.5 K |
        | hueco de canal de catálogo (18/09) | 9.2 / 8.5 K |
        | β identificado y película anclada (18/09) | 7.1 / 6.6 K |
        | criterio de pared húmeda corregido (21/09) | **5.3 / 5.0 K** |

        Cada paso hace el modelo más fiel y el margen más estrecho: el
        intercambiador transfiere más de lo que el capítulo suponía. Sigue
        siendo positivo, de modo que el criterio se cumple y la selección del
        AlfaNova 16-10H no se ve afectada, pero la holgura ha pasado de ~13 K a
        ~5 K: **un 40 % de la declarada**. Es el margen que separa a M-1 de
        condensar dentro del desrecalentador, y a estas alturas merece una
        campaña de sensibilidad en el cap. 10 y una revisión del §9.6.7.
        """
        _, T_cap = self._resolver(140.4, 87.3)
        _, T_corr = self._resolver(125.5, 74.0)
        assert T_cap - 45.0 > 4.0              # era > 10 K, luego 8, luego 5
        assert T_corr - 45.0 > 4.0
        assert T_corr < T_cap

    def test_hay_pared_humeda_aunque_el_refrigerante_no_condense(self):
        """§9.6.5, el apartado sobre el que descansa H3.

        El refrigerante sale sobrecalentado —no condensa en el núcleo, que es el
        criterio de dimensionado del §9.6.7— y sin embargo una parte del
        desrecalentador opera con la PARED por debajo de la saturación. Es
        exactamente el fenómeno que el §9.6.5 describe: «se produce condensación
        sobre la pared simultáneamente al enfriamiento del vapor en el núcleo».

        El capítulo exige reportar esa fracción porque de ella depende la
        potencia recuperable. Aquí sale del orden del 15–20 % del componente.

        AVISO. La magnitud de la corrección NO está soportada: el modelo aplica
        la ec. 9-19 con Z = 1, el límite conservador, porque el capítulo no
        proporciona una formulación de Z válida para un fluido puro (su
        Z = x·cp,v·dTsat/dh se anula idénticamente a presión constante). Lo que
        este test fija es que el diagnóstico existe y es no nulo, no cuánto vale
        la corrección.
        """
        r, _ = self._resolver(125.5, 74.0)
        assert 0.05 < r.wet_wall_fraction < 0.40


# ---------------------------------------------------------------------------
# §9.6.7 — La decisión de selección del desrecalentador
#
# El apartado descarta un segundo AlfaNova 27-30H como desrecalentador porque
# «el coeficiente de película se desploma un 96 % (de 1.433 a 61 W/(m²·K))».
# Rehecho el 22/09/2026 con la geometría de catálogo del 18/09 (b = 1.72 mm en
# el 16-10H y 2.02 en el 27-30H) y con Martin, que es la correlación que el
# propio apartado declara haber empleado:
#
#   - los 1433 W/(m²·K) proceden del paso de placa SIN corregir;
#   - los 61 W/(m²·K) no se obtienen con Martin bajo ningún ángulo;
#   - el desplome es del 74 %, no del 96 %;
#   - y la DECISIÓN SE SOSTIENE POR EL MOTIVO CONTRARIO: el 27-30H no deja de
#     desrecalentar, desrecalenta de más y el refrigerante condensa dentro.
# ---------------------------------------------------------------------------
class TestSeleccionDelDesrecalentador:
    #: Punto de diseño del §9.6.7: 40.3 kg/h de NH₃ a P_sat(45 °C).
    M_NH3 = 40.3 / 3600.0
    T_SAT_C = 45.0
    T_MEDIA_C = 98.2            # media de la evolución 140.4 -> 55.9 °C

    def _alpha_nh3(self, geom, beta_deg=None):
        """Coeficiente de película del lado de amoníaco con Martin."""
        from amoniatermia import Fluid, data as D           # noqa: F401
        from amoniatermia.correlations import get
        from amoniatermia.correlations.singlephase import reynolds
        from amoniatermia.geometry import PlateGeometry

        if beta_deg is not None:
            geom = PlateGeometry(**{**geom.__dict__,
                                    "beta_c": math.radians(beta_deg)})
        f = Fluid("Ammonia")
        f.update_PT(f.Psat(self.T_SAT_C + 273.15), self.T_MEDIA_C + 273.15)
        G = self.M_NH3 / (geom.n_channels_ref * geom.A_channel)
        Re = reynolds(G, geom.D_h, f.mu)
        alpha = get("singlephase", "martin_vdi")(
            Re, f.Pr, f.k, geom.D_h, beta_c=geom.beta_c)
        return Re, alpha

    def test_el_coeficiente_publicado_procede_del_paso_sin_corregir(self):
        """Los 1433 W/(m²·K) del §9.6.7 salen con b = 1.06 mm, no con el paso
        de catálogo.

        El propio apartado declara el paso corregido «de 1.06 a 2.09 mm», pero
        el coeficiente que publica corresponde al valor antiguo: con b = 1.06 y
        β = 60° Martin da 1411 W/(m²·K), a menos del 2 % del publicado. Con el
        paso de catálogo del 18/09/2026 (1.72 mm) baja a ~870.

        El número de Reynolds NO delata el problema, y por eso el error
        sobrevivió: Re = 2·ṁ/(Φ·L_w·n·μ) es independiente de b.
        """
        from amoniatermia import data as D
        from amoniatermia.geometry import PlateGeometry

        g = D.plate_geometry("desrecalentador_acs")
        g_viejo = PlateGeometry(**{**g.__dict__, "b": 0.00106})

        Re_viejo, a_viejo = self._alpha_nh3(g_viejo, beta_deg=60.0)
        Re_nuevo, a_nuevo = self._alpha_nh3(g, beta_deg=60.0)

        assert rel(a_viejo, 1433.0) < 0.05          # el publicado
        assert rel(Re_viejo, Re_nuevo) < 1e-9       # Re no depende de b
        assert rel(Re_nuevo, 5354.0) < 0.05         # el Re publicado sí sale
        assert 800.0 < a_nuevo < 950.0              # el corregido

    def test_el_desplome_del_96_por_ciento_es_del_74(self):
        """Los 61 W/(m²·K) del 27-30H no se obtienen con Martin.

        Con la geometría de catálogo de las dos unidades, Martin da 223 W/(m²·K)
        con β = 60° y 237 con el β = 71.6° adoptado: la caída es del 74 %, no
        del 96 %. El orden de magnitud de 61 solo aparece conmutando a una
        hipótesis laminar de Nusselt constante (Nu = 3.66 da 37), que no es la
        correlación que el apartado dice haber empleado.

        La conclusión cualitativa —el coeficiente cae mucho al repartir el
        caudal entre 14 canales— se mantiene. El número no.
        """
        from amoniatermia import data as D

        g16 = D.plate_geometry("desrecalentador_acs")
        g27 = D.plate_geometry("condensador_climatizacion")

        for beta in (60.0, 71.6):
            Re16, a16 = self._alpha_nh3(g16, beta_deg=beta)
            Re27, a27 = self._alpha_nh3(g27, beta_deg=beta)
            assert rel(Re27, 1020.0) < 0.05         # el Re publicado sí sale
            assert a27 > 200.0                      # el §9.6.7 declara 61
            caida = 1.0 - a27 / a16
            assert 0.70 < caida < 0.78              # el §9.6.7 declara 0.96

    def test_el_27_30H_se_descarta_por_condensar_no_por_no_desrecalentar(self):
        """La decisión del §9.6.7 se sostiene, y el motivo es el contrario.

        El 27-30H tiene 7.6 veces el área del 16-10H, de modo que a pesar del
        coeficiente un 74 % menor su conductancia es mayor: alcanza la consigna
        de 60 °C de ACS sin dificultad —con 139.5 kg/h en lugar de 99— y lo que
        ocurre es que **el refrigerante llega a saturación y condensa dentro**,
        un 8 % del caudal. Eso incumple el criterio de dimensionado que el
        propio apartado fija: que el refrigerante no descienda de T_sat(T_c)
        dentro del desrecalentador, para que en M-1 trabaje siempre en vapor.

        No es por tanto que «deje de poder desrecalentar de forma eficaz»:
        desrecalienta de más. La selección del 16-10H no se ve afectada; su
        justificación hay que reescribirla.

        Corroboración del propio capítulo: para la variante intermedia —un
        AlfaNova 27 de 10 placas, 4 canales— el apartado declara que el margen
        «se reduce a solo 0.1 K», y el modelo la sitúa igualmente en la
        saturación. La serie completa es coherente.
        """
        from amoniatermia import Fluid, data as D
        from amoniatermia.components.plate_hx import PlateHeatExchanger

        f, agua = Fluid("Ammonia"), Fluid("Water")
        P = f.Psat(self.T_SAT_C + 273.15)
        sat = f.sat_props(P)

        def marchar(unidad, m_acs_kgh):
            geom = D.plate_geometry(unidad)
            hx = PlateHeatExchanger(f, agua, geom, n_cells=60, role="condenser")
            f.update_PT(P, 140.4 + 273.15)
            return hx.solve(P, f.h, m_dot=self.M_NH3,
                            T_sec_in=35 + 273.15, m_sec=m_acs_kgh / 3600.0)

        r16 = marchar("desrecalentador_acs", 99.2)
        r27 = marchar("condensador_climatizacion", 139.5)

        # Los dos alcanzan la consigna de ACS.
        assert abs(r16.T_sec_out - 273.15 - 60.0) < 1.0
        assert abs(r27.T_sec_out - 273.15 - 60.0) < 1.0

        # El seleccionado sale en vapor; el descartado, bifásico.
        assert r16.h_ref_out > sat["h_v"]
        assert r27.h_ref_out < sat["h_v"]
        x27 = (r27.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
        assert 0.85 < x27 < 0.97        # en torno al 8 % condensado


# ---------------------------------------------------------------------------
# §9.6.7 — El retorno del primario de ACS, y dónde muerde el criterio
#
# Decisión del autor del 22/09/2026: 35 °C de diseño, verificación del criterio
# en el extremo frío (25 °C) y suelo de retorno como requisito de la instalación.
# ---------------------------------------------------------------------------
class TestRetornoDelPrimarioACS:
    """REPRODUCE LA TABLA 10.16 DE LA v30, que queda SUSTITUIDA (24/09/2026).

    Aquella tabla se calculó con el componente aislado, 40.3 kg/h de NH₃
    condensando a 45 °C y entrada a 125.5 °C: un caudal que no es el del
    compresor en esa condición (32.2 kg/h a 46.8 °C). Por decisión del autor el
    punto de diseño pasa a ser el de M-1 resuelto como sistema; lo fija
    `TestPuntoDeDisenoDelDesrecalentador`. Esta clase se conserva porque fija
    el cálculo publicado y su lectura cualitativa, que no cambia.

    El retorno NO es un dato de diseño sino una variable que barre.

    Con el depósito estratificado, el agua que vuelve del serpentín arranca fría
    al principio de la carga y sube hasta acercarse a la temperatura del depósito
    al final. Y los dos criterios apuntan en direcciones contrarias: la potencia
    recuperada empeora con el retorno CALIENTE y el criterio de no condensación
    empeora con el FRÍO.
    """

    M_NH3 = 40.3 / 3600.0
    T_DIS_C = 125.5          # descarga reidentificada
    T_SAT_C = 45.0

    def _punto(self, T_retorno_C, T_impulsion_C):
        """Resuelve al caudal de ACS que alcanza la impulsión."""
        from scipy.optimize import brentq

        from amoniatermia import Fluid
        from amoniatermia import data as D
        from amoniatermia.components.plate_hx import PlateHeatExchanger

        f, agua = Fluid("Ammonia"), Fluid("Water")
        P = f.Psat(self.T_SAT_C + 273.15)

        def resolver(m_acs):
            hx = PlateHeatExchanger(f, agua,
                                    D.plate_geometry("desrecalentador_acs"),
                                    n_cells=40, role="condenser")
            f.update_PT(P, self.T_DIS_C + 273.15)
            r = hx.solve(P, f.h, m_dot=self.M_NH3,
                         T_sec_in=T_retorno_C + 273.15, m_sec=m_acs / 3600.0)
            f.update_PH(P, r.h_ref_out)
            return r, f.T - 273.15

        m = brentq(lambda m: resolver(m)[0].T_sec_out - 273.15 - T_impulsion_C,
                   5.0, 600.0, xtol=0.1)
        r, T_ref_out = resolver(m)
        return m, -r.Q_dot, T_ref_out - self.T_SAT_C, r.wet_wall_fraction

    def test_el_criterio_muerde_en_el_extremo_FRIO_y_no_en_el_caliente(self):
        """Lo que decide la verificación, y no es lo que parecía.

        Con la impulsión adoptada de 67 °C, al enfriar el retorno la potencia
        recuperada SUBE y el margen sobre la saturación BAJA. El caso
        desfavorable del criterio de dimensionado del §9.6.7 es por tanto el
        retorno frío —el que sigue a un consumo grande, con el fondo del
        depósito cerca de la temperatura de red— y no el caliente.
        """
        from amoniatermia import CONSIGNA_ACS_K, RETORNO_ACS_K

        T_imp = CONSIGNA_ACS_K["M-1"] - 273.15
        m_d, Q_d, margen_d, humeda_d = self._punto(
            RETORNO_ACS_K["diseno"] - 273.15, T_imp)
        m_f, Q_f, margen_f, humeda_f = self._punto(
            RETORNO_ACS_K["verificacion"] - 273.15, T_imp)

        # Punto de diseño: 35 -> 67 C.
        assert rel(Q_d, 2371.0) < 0.05
        assert 5.5 < margen_d < 7.5

        # Extremo frío: más potencia y MENOS margen. Las dos a la vez.
        assert Q_f > Q_d
        assert margen_f < margen_d
        assert 1.5 < margen_f < 3.5          # 2.3 K medidos: sigue cumpliendo
        assert margen_f > 0.0, "el criterio del §9.6.7 dejaria de cumplirse"
        assert humeda_f > humeda_d           # y más pared húmeda

    def test_el_suelo_de_retorno_es_requisito_de_instalacion(self):
        """La conclusión práctica del barrido: conviene impedir que el retorno
        baje del suelo adoptado. Cuesta poca potencia y protege el criterio."""
        from amoniatermia import CONSIGNA_ACS_K, RETORNO_ACS_K

        assert (RETORNO_ACS_K["verificacion"] < RETORNO_ACS_K["suelo_instalacion"]
                < RETORNO_ACS_K["diseno"])
        T_imp = CONSIGNA_ACS_K["M-1"] - 273.15
        _, Q_suelo, margen_suelo, _ = self._punto(
            RETORNO_ACS_K["suelo_instalacion"] - 273.15, T_imp)
        _, Q_diseno, _, _ = self._punto(RETORNO_ACS_K["diseno"] - 273.15, T_imp)
        assert margen_suelo > 3.5                     # 4.3 K medidos
        assert (Q_suelo - Q_diseno) / Q_diseno < 0.05  # cuesta poco


# ---------------------------------------------------------------------------
# §9.6.7 — El punto de diseño del desrecalentador, resuelto como SISTEMA
#
# DECISIÓN DEL AUTOR, 25/09/2026. Las tablas 10.13, 10.14 y 10.16 de la v30 se
# calcularon con el componente aislado y 40.3 kg/h de NH₃ a 45 °C, caudal que no
# es el del compresor. El punto de diseño pasa a ser el de M-1 resuelto sin
# imponer nada —aire a 35 °C, climatización a 12 °C, ACS de 35 a 67 °C—, que es
# lo que el capítulo pide de cualquier otro resultado: imponer la temperatura
# no es un equilibrio.
#
# Y en invierno (M-3) el criterio de no condensación NO se cumple con retorno
# frío: el refrigerante condensa dentro del desrecalentador. DECISIÓN DEL AUTOR:
# se ACEPTA la condensación parcial y se declara.
# ---------------------------------------------------------------------------
def _circuito_completo():
    from amoniatermia import (AirCoil, Circuit, Fluid, PlateHeatExchanger,
                              SemiEmpiricalCompressor)
    from amoniatermia import data as D

    f = Fluid("Ammonia")
    return Circuit(
        f, SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params()),
        AirCoil(f, D.air_coil_geometry(), n_segments=60),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("condensador_climatizacion"),
                           n_cells=12),
        PlateHeatExchanger(f, Fluid("Water"),
                           D.plate_geometry("desrecalentador_acs"), n_cells=12))


def _salida_desrecalentador(c, s):
    """Margen sobre la saturación [K] y título a la salida del desrecalentador."""
    f = c.fluid
    d = s.components["desrecalentador"]
    # Presion uniforme en el intercambiador (M8, decision del 29/09/2026): la
    # referencia es la presion de descarga, como en `envelope`.
    P = s.unknowns["Pk"]
    T_sat, sat = f.Tsat(P), f.sat_props(P)
    f.update_PH(P, d.h_ref_out)
    x = (d.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
    return f.T - T_sat, x, d.wet_wall_fraction


@pytest.fixture(scope="module")
def desrecalentador_en_sistema():
    from amoniatermia import AirState, Boundary, Setpoints, WaterStream

    m_aire = None     # 7600 m3/h; el caudal masico lo deduce Boundary
    sp = Setpoints(superheat=5.0, subcooling=2.0, T_acs=67 + 273.15)
    verano = AirState(T=35 + 273.15, V_frontal=3.30)
    invierno = AirState.at(T=7 + 273.15, V_frontal=3.30, T_wb=6 + 273.15)

    def bc(aire, clima, T_amb, T_ret):
        return Boundary(air=aire, m_dot_air=m_aire, clima=clima,
                        acs=WaterStream(T_in=T_ret + 273.15), T_amb=T_amb)

    out = {}
    c = _circuito_completo()
    b = lambda T: bc(verano, WaterStream(T_in=12 + 273.15, m_dot=0.45),
                     308.15, T)
    s35 = c.solve("M-1", b(35), sp)
    out["M-1", 35] = (c, s35)
    out["M-1", 25] = (c, c.solve("M-1", b(25), sp, x0=dict(s35.unknowns)))

    c4 = _circuito_completo()
    b4 = lambda T: bc(invierno, WaterStream(T_in=40 + 273.15, m_dot=D.caudal_climatizacion()),
                      280.15, T)
    # Arranque del lado bueno del codo de R4 (ver `Circuit.ARRANQUES_...`).
    x0 = c4.initial_guess("M-3", b4(35), sp, pinch_air=6.0, pinch_water=4.0)
    s4 = c4.solve("M-3", b4(35), sp, x0=x0)
    out["M-3", 35] = (c4, s4)
    out["M-3", 30] = (c4, c4.solve("M-3", b4(30), sp, x0=dict(s4.unknowns)))
    return out


class TestPuntoDeDisenoDelDesrecalentador:
    """Tardan del orden de cuatro minutos: son cuatro puntos de sistema."""

    def test_el_punto_de_diseno_es_M1_resuelto(self, desrecalentador_en_sistema):
        """Nuevo punto de diseño (sustituye a la fila 3 de la tabla 9.13):
        condensación a 43.4 °C, 31.6 kg/h de NH₃ con descarga a 123.0 °C,
        49.8 kg/h de ACS de 35 a 67 °C, 1 851 W recuperados y 5.5 K de margen.
        La v30 publicaba 63.7 kg/h, 2 371 W y 6.4 K con el caudal oculto."""
        c, s = desrecalentador_en_sistema["M-1", 35]
        assert s.converged and s.valid, s.checks
        # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: antes 43.43 C, 123.0 C, 49.8 kg/h, 1851 W, 5.50 K.
        assert abs(s.T_cond - 273.15 - 43.33) < 0.05
        assert abs(s.m_dot * 3600 - 31.65) < 0.1
        assert abs(s.T_dis - 273.15 - 122.39) < 0.1
        assert abs(s.unknowns["m_acs"] * 3600 - 49.43) < 0.3
        assert abs(s.Q_acs - 1836.6) < 10.0
        margen, x, humeda = _salida_desrecalentador(c, s)
        assert abs(margen - 5.65) < 0.05
        assert x > 1.0
        assert abs(humeda - 0.08) < 0.03

    def test_en_verano_el_criterio_se_cumple_en_el_extremo_frio(
            self, desrecalentador_en_sistema):
        """RS-17: la verificación se hace con retorno a 25 °C, no en diseño.
        En verano se cumple con 1.2 K de margen y 1 968 W."""
        c, s = desrecalentador_en_sistema["M-1", 25]
        assert s.converged and s.valid
        margen, x, _ = _salida_desrecalentador(c, s)
        # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: antes 1.22 K y 1968 W.
        assert abs(margen - 1.31) < 0.05
        assert margen > 0.0
        assert abs(s.Q_acs - 1955.3) < 10.0

    def test_en_invierno_el_diseno_queda_en_la_saturacion(
            self, desrecalentador_en_sistema):
        """M-3, calefacción con ACS a 67 °C: condensación a 49.4 °C porque el
        agua de climatización va de 40 a 45 °C. El refrigerante sale del
        desrecalentador a 0.02 K de la saturación, con un tercio de la pared
        húmeda: el criterio se cumple por los pelos."""
        c, s = desrecalentador_en_sistema["M-3", 35]
        assert s.converged and s.valid, s.checks
        margen, x, humeda = _salida_desrecalentador(c, s)
        # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: el margen pasa de 0.02 a 0.31 K y el calor de
        # 2237 a 2210 W. Sigue «por los pelos», ya no en la saturación misma.
        # Remedido el 01/10/2026: caudal de climatización único de 0.45 kg/s
        # (antes 0.35 en M-3). La condensación baja a 48.2 °C y el margen sube
        # a 1.06 K; el calor recuperado, a 2148 W.
        assert 0.0 < margen < 1.5
        assert abs(margen - 1.06) < 0.05
        assert abs(s.Q_acs - 2147.7) < 15.0
        assert humeda > 0.25

    def test_en_invierno_con_retorno_frio_condensa_dentro(
            self, desrecalentador_en_sistema):
        """HALLAZGO ACEPTADO Y DECLARADO (decisión del autor, 25/09/2026). Con
        retorno a 30 °C —el suelo de RS-17— el refrigerante sale con título
        0.993: condensa dentro del desrecalentador y el criterio de
        dimensionado del §9.6.7 no se cumple. Se acepta como limitación de la
        operación en invierno; el punto converge y es válido."""
        c, s = desrecalentador_en_sistema["M-3", 30]
        assert s.converged and s.valid
        margen, x, _ = _salida_desrecalentador(c, s)
        assert x < 1.0
        # Remedido el 29/09/2026: presion uniforme (M8, D12) y recorte de frontera corregido: título 0.9853 (antes 0.9926), condensa un 1.5 %.
        # Remedido el 01/10/2026, con el caudal único de 0.45 kg/s: título 0.9917, condensa un 0.8 %.
        assert abs(x - 0.9917) < 0.002


class TestSeleccionEnElPuntoDeDiseno:
    """Tabla 9.15 rehecha en el punto de diseño nuevo (25/09/2026): 31.6 kg/h
    de NH₃ condensando a 43.43 °C, entrada a 123.0 °C y ACS de 35 a 67 °C. La
    decisión se sostiene: el 16-10H sale en vapor con 5.7 K de margen y el
    27-30H condensa el 4 % (8 % en la v30)."""

    def _resolver(self, unidad, **ov):
        from scipy.optimize import brentq

        from amoniatermia import Fluid, data as D
        from amoniatermia.components.plate_hx import PlateHeatExchanger

        f, agua = Fluid("Ammonia"), Fluid("Water")
        P = f.Psat(43.43 + 273.15)
        geom = D.plate_geometry(unidad, **ov)

        def res(m):
            hx = PlateHeatExchanger(f, agua, geom, n_cells=60, role="condenser")
            f.update_PT(P, 123.0 + 273.15)
            return hx.solve(P, f.h, m_dot=31.6 / 3600, T_sec_in=35 + 273.15,
                            m_sec=m / 3600)

        m = brentq(lambda m: res(m).T_sec_out - 273.15 - 67.0, 20, 900,
                   xtol=0.05)
        r = res(m)
        sat = f.sat_props(P)
        x = (r.h_ref_out - sat["h_l"]) / (sat["h_v"] - sat["h_l"])
        f.update_PH(P, r.h_ref_out)
        return m, -r.Q_dot, x, f.T - sat["Tsat"]

    def test_el_16_10H_sale_en_vapor_y_el_27_30H_condensa(self):
        m16, Q16, x16, margen16 = self._resolver("desrecalentador_acs")
        m27, Q27, x27, _ = self._resolver("condensador_climatizacion")
        assert abs(m16 - 49.6) < 0.5 and abs(Q16 - 1844.0) < 15.0
        assert x16 > 1.0 and abs(margen16 - 5.7) < 0.1
        assert abs(m27 - 64.7) < 0.5 and abs(Q27 - 2403.0) < 20.0
        assert abs(x27 - 0.960) < 0.003          # condensa el 4 %

    def test_la_variante_intermedia_queda_al_borde(self):
        _, Q, x, margen = self._resolver("condensador_climatizacion",
                                         n_plates=10)
        assert x > 1.0 and abs(margen - 0.7) < 0.1
        assert abs(Q - 1999.0) < 15.0

