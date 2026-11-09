"""Verificacion del intercambiador de placas. Apartados 9.6 y 6.7.1."""
import math
import pytest
from amoniatermia import data as D
from amoniatermia.props import Fluid
from amoniatermia.geometry import PlateGeometry
from amoniatermia.components.plate_hx import PlateHeatExchanger

#: phi_c y phi_v son datos PENDIENTES (§9.6.4): la condensacion en placas por
#: pelicula de Nusselt, que es la formulacion principal del ap. 9.6.3, FALLA si
#: se invocan sin fijar. Inyectarlos a 1.0 permite ejercitar la mecanica del
#: componente, pero NO es una identificacion: los valores numericos de estos
#: tests no son predicciones del modelo. La inyeccion va por `corr_params`
#: precisamente para que quede a la vista de quien lea el test.
PHI_EXPLORATORIOS = {"plate_condensation": {"phi_c": 1.0, "phi_v": 1.0}}


@pytest.fixture
def hx():
    ref = Fluid("Ammonia")
    water = Fluid("Water")
    g = PlateGeometry(n_plates=40, b=0.0022, L_w=0.10, L_p=0.30,
                      beta_c=math.radians(60.0), phi=1.17, t_p=0.0004,
                      k_p=15.0,
                      provenance={"phi": "ESTIMADO", "b": "catalogo"})
    return PlateHeatExchanger(ref, water, g, n_cells=20,
                              corr_params=PHI_EXPLORATORIOS)


def test_condenser_rejects_heat(hx):
    """Refrigerante caliente entrando, agua fria: Q debe ser negativo
    (calor cedido por el refrigerante)."""
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)          # vapor muy sobrecalentado
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    assert r.Q_dot < 0.0


def test_energy_balance_closes(hx):
    """Cierre de balance como criterio de validez (ap. 6.7.1)."""
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    assert r.energy_balance_error < 0.05


def test_charge_reports_range_not_single_value(hx):
    """Requisito del apartado 9.9: RANGO, nunca valor unico.

    La banda es la de las CUATRO familias del apartado 9.9, que son las que
    tabula la tabla 9.21. Premoli queda fuera a proposito: esta registrada como
    alternativa para la sensibilidad del ap. 6.11, pero no figura entre las
    cuatro familias y meterla en la banda ensancharia el rango con una
    formulacion que el capitulo no declara.
    """
    from amoniatermia.correlations.voidfraction import CORRELACIONES_HUECOS

    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    for k in CORRELACIONES_HUECOS + ("_min", "_max", "_spread"):
        assert k in r.charge
    assert "premoli" not in r.charge
    assert r.charge["_max"] >= r.charge["_min"] > 0.0


def test_charge_set_is_configurable(hx):
    """El conjunto de la banda se elige por nombre, no esta escrito en el
    componente (apartado 9.12.3)."""
    hx.void_fraction_names = ("homogeneous", "premoli")
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    assert "premoli" in r.charge
    assert "zivi" not in r.charge


def test_correlation_is_swappable(hx):
    """Cambiar una correlacion NO debe requerir tocar el codigo del
    componente: es lo que hace viable la sensibilidad del ap. 6.11."""
    f = Fluid("Ammonia")
    P0 = f.Psat(273.15)
    f.update_PQ(P0, 0.15)
    h_in = f.h
    r1 = hx.solve(P0, h_in, 0.008, 285.15, 0.30)   # additive_cooper, ap. 9.6.3
    hx.corr["plate_boiling"] = "asymptotic_cooper"       # variante asintotica
    r2 = hx.solve(P0, h_in, 0.008, 285.15, 0.30)
    assert r1.Q_dot != r2.Q_dot


def test_discretisation_independence(hx):
    """Estudio de independencia de malla (ap. 6.7.1). Al refinar, la variacion
    relativa de Q debe reducirse.

    La serie arranca en n = 20 y no en n = 10 a proposito. Con malla muy gruesa
    la solucion NO es monotona: las fronteras de zona —el paso de
    desrecalentamiento a condensacion— caen en celdas distintas segun la malla,
    y el salto de una celda a otra domina sobre el error de discretizacion. Es
    el comportamiento esperado de un volumen finito sin seguimiento de la
    interfase, y se declara en lugar de ocultarse eligiendo la serie que salga
    bien. A partir de n = 20 el comportamiento ya es asintotico.
    """
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    h_in = f.h
    Qs = []
    for n in (20, 40, 80, 160):
        hx.n_cells = n
        Qs.append(hx.solve(Pk, h_in, 0.010, 313.15, 0.35).Q_dot)
    d1 = abs(Qs[1] - Qs[0]) / abs(Qs[1])
    d3 = abs(Qs[3] - Qs[2]) / abs(Qs[3])
    assert d3 < d1, f"la solucion no converge al refinar: {Qs}"
    assert d3 < 1e-3
    # Y ahora la serie es MONOTONA, que es lo que el docstring decia no poder
    # exigir: con el seguimiento de la frontera del 21/09/2026 ningun volumen
    # contiene dos regimenes, de modo que el salto de coeficiente ya no cambia
    # de volumen segun la malla. Desaparece el motivo por el que la serie tenia
    # que arrancar en n = 20 en lugar de n = 10.
    for i in range(len(Qs) - 2):
        d_i = abs(Qs[i + 1] - Qs[i]) / abs(Qs[i + 1])
        d_j = abs(Qs[i + 2] - Qs[i + 1]) / abs(Qs[i + 2])
        assert d_j < d_i, f"la convergencia no es monotona: {Qs}"


# ---------------------------------------------------------------------------
# Despacho del regimen bifasico (ap. 9.3) y limpieza del registro
# ---------------------------------------------------------------------------

def _condensador(role=None, n_cells=30):
    import math

    from amoniatermia.components.plate_hx import PlateHeatExchanger
    from amoniatermia.geometry import PlateGeometry

    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    hx = PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom,
                            n_cells=n_cells, role=role,
                            corr_params=PHI_EXPLORATORIOS)
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    return hx, hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)


def test_un_condensador_no_evalua_la_correlacion_de_ebullicion():
    """Regresion. La rama se elegia por el signo de `q_flux_guess`, que la
    iteracion interna inicializa a 0.0: con `>= 0.0` la primera iteracion de
    CADA celda entraba en evaporacion aunque el componente condensase.

    Convergia al regimen correcto, pero contaminaba el registro de extrapolacion
    con cientos de entradas espurias, y un registro en el que nadie mira no
    cumple el requisito de reporte de los ap. 9.7.5 y 9.12.3.
    """
    hx, r = _condensador(role="condenser")
    familias = {e.family for e in hx.log.excursions}
    assert "plate_boiling" not in familias
    # `plate_condensation` ya NO aparece en el registro, y es buena señal: desde
    # el anclaje del 18/09/2026 la correlación declara base experimental y el
    # punto cae dentro. El registro solo recoge EXCURSIONES, de modo que una
    # correlación en rango no deja rastro. Lo que se comprueba es lo contrario:
    # que no haya excursión de condensación, no que no se haya evaluado.
    assert "plate_condensation" not in familias
    assert float(r.x_profile.min()) < 1.0           # sí condensó


def test_el_regimen_no_depende_de_una_incognita_del_lazo():
    """Sin papel declarado, el respaldo es el signo de (T_sec - T_sat), que esta
    disponible en la primera iteracion. Debe dar el mismo resultado que declarar
    el papel explicitamente."""
    hx_declarado, r_declarado = _condensador(role="condenser")
    hx_inferido, r_inferido = _condensador(role=None)
    # rel=1e-7 y no 1e-9: desde que el estado del volumen se evalua una vez
    # fuera del lazo sobre q'' (21/09/2026) las operaciones ocurren en otro
    # orden y la ultima cifra del doble baila. Es ruido de coma flotante, no
    # una diferencia de modelo.
    assert r_inferido.Q_dot == pytest.approx(r_declarado.Q_dot, rel=1e-7)
    assert {e.family for e in hx_inferido.log.excursions} == \
           {e.family for e in hx_declarado.log.excursions}


def test_el_registro_anota_solo_la_marcha_convergida():
    """Ni las iteraciones internas sobre q'' ni las marchas del lazo de disparo.

    Se cuenta por familia, que es mas preciso que un total: cada celda de la
    marcha final anota una evaluacion del lado refrigerante —repartida entre
    monofasico, ebullicion y condensacion segun su regimen—, una del secundario,
    que siempre es monofasico, y una de friccion. El multiplicador bifasico solo
    aparece en las celdas bifasicas, de modo que su cuenta es un diagnostico de
    reparto de zonas y no puede fijarse a priori.
    """
    for n in (10, 30):
        hx, r = _condensador(role="condenser", n_cells=n)
        cuenta = {}
        for e in hx.log.excursions:
            cuenta[e.family] = cuenta.get(e.family, 0) + e.count
        # La condensacion ya no suma: esta dentro de su base declarada desde el
        # anclaje y por tanto no deja excursion. Lo que queda es el monofasico
        # —del secundario en todo volumen, y del refrigerante en los de vapor—
        # mas la friccion, que anota uno por volumen.
        #
        # El recuento se compara contra el numero de VOLUMENES RESUELTOS, no
        # contra `n_cells`, que desde el seguimiento de la frontera del
        # 21/09/2026 es el numero NOMINAL: cada frontera de fase cruzada
        # recorta un volumen y anade otro. Aqui se cruza una, la de
        # desrecalentamiento a condensacion, de modo que salen n + 1.
        n_vol = len(r.x_profile)
        assert n < n_vol <= n + 2
        lado_refrigerante = sum(cuenta.get(f, 0) for f in
                                ("singlephase", "plate_boiling"))
        assert n_vol < lado_refrigerante < 2 * n_vol
        assert cuenta["friction"] == n_vol
        assert 0 < cuenta["twophase_multiplier"] < n_vol


def test_papel_invalido_falla_pronto():
    import math

    from amoniatermia.components.plate_hx import PlateHeatExchanger
    from amoniatermia.geometry import PlateGeometry

    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    with pytest.raises(ValueError, match="condenser"):
        PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom,
                           role="condensador")


def test_el_papel_se_puede_imponer_por_modo_sin_cambiar_el_objeto():
    """Ap. 9.3: la geometria y los parametros identificados permanecen
    invariantes entre modos; solo cambia la topologia. El papel pertenece al
    modo, de ahi que `solve()` pueda sobreescribir el del constructor: sera
    `circuit.py` quien lo pase."""
    hx, _ = _condensador(role=None)
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    hx.log = __import__("amoniatermia").ExtrapolationLog()
    hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35,
             role="condenser")
    assert "plate_boiling" not in {e.family for e in hx.log.excursions}


def test_la_pelicula_sin_anclar_sigue_fallando_sin_phi_c_y_phi_v():
    """§9.6.3 y §9.6.4. El capitulo dice expresamente que «no se fijan aqui
    valores aproximados para no dar la falsa impresion de una identificacion ya
    completada», y `nusselt_film` lo hace cumplir: sin sus dos factores, falla.

    Lo que cambio el 18/09/2026 no es esa regla sino que ya existe un dato con
    el que cumplirla. El producto phi_c*phi_v esta ANCLADO sobre el punto de
    seleccion del 27-30H, y la version anclada es la que el componente usa por
    defecto. La version sin anclar se conserva registrada y sigue exigiendo los
    factores, porque un valor por defecto los ocultaria.
    """
    from amoniatermia.correlations.condensation import MissingCorrectionFactor

    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    hx = PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom,
                            n_cells=10, role="condenser",
                            corr={"plate_condensation": "nusselt_film"})
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    with pytest.raises(MissingCorrectionFactor, match="PENDIENTE"):
        hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)


def test_la_pelicula_anclada_es_la_que_el_componente_usa_por_defecto():
    """Y resuelve sin inyectar nada, que es lo que desatasca los modos con
    placas."""
    geom = D.plate_geometry("condensador_climatizacion")
    hx = PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom,
                            n_cells=20, role="condenser")
    assert hx.corr["plate_condensation"] == "nusselt_film_anclada_27_30H"
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    assert r.converged and r.Q_dot < 0.0


def test_el_reynolds_equivalente_queda_como_alternativa_declarada():
    """El §9.6.3 lo descarta como formulacion principal, pero se conserva
    registrado para la sensibilidad del cap. 10."""
    from amoniatermia.correlations import available, info

    assert "equivalent_Re" in available("plate_condensation")
    assert "DESCARTA" in info("plate_condensation", "equivalent_Re").reference

    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    hx = PlateHeatExchanger(Fluid("Ammonia"), Fluid("Water"), geom, n_cells=10,
                            role="condenser",
                            corr={"plate_condensation": "equivalent_Re"})
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    assert hx.solve(Pk, f.h, 0.010, 313.15, 0.35).Q_dot < 0.0


# ---------------------------------------------------------------------------
# D5 — perdida de carga completa (ec. 9-20)
# ---------------------------------------------------------------------------

def _condensador_completo(n_cells=80, **kw):
    """Condensador de climatizacion en su punto de diseno, con condensacion
    completa: es donde el bifasico existe de verdad y el multiplicador actua."""
    import math

    from amoniatermia import data as D

    # Ya no se inyecta nada: desde el 18/09/2026 el fichero trae el paso entre
    # placas, el espesor y el angulo identificado.
    geom = D.plate_geometry("condensador_climatizacion")
    f = Fluid("Ammonia")
    P = f.Psat(50 + 273.15)
    hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=n_cells,
                            role="condenser", corr_params=PHI_EXPLORATORIOS,
                            **kw)
    f.update_PT(P, 70 + 273.15)
    return hx, hx.solve(P, f.h, 40.3 / 3600, 40 + 273.15, 1830.0 / 3600)


def test_la_perdida_de_carga_reporta_las_tres_contribuciones():
    """§9.6.6, ec. 9-20: friccional, aceleracion y gravitatoria.

    La version anterior devolvia solo la friccional, y `dp_total()` —que si
    contemplaba las tres— no la usaba nadie. Reportar solo el total tampoco
    bastaria: el apartado conserva la gravitatoria EXPRESAMENTE, de modo que
    hay que poder comprobar que se ha conservado.
    """
    _, r = _condensador_completo()
    for k in ("friccional", "aceleracion", "gravitatoria", "total"):
        assert k in r.dP_parts
    assert r.dP_parts["total"] == pytest.approx(r.dP_ref)
    assert r.dP_ref == pytest.approx(sum(r.dP_parts[k] for k in
                                         ("friccional", "aceleracion",
                                          "gravitatoria")))


def test_en_el_condensador_la_gravedad_domina_y_cambia_el_signo():
    """Resultado que el capitulo no anticipa y que conviene que recoja.

    El §9.6.6 conserva la contribucion gravitatoria porque «la disposicion
    vertical la hace no despreciable en la region bifasica del EVAPORADOR». En
    el condensador de climatizacion no es que no sea despreciable: es que domina
    por un factor de 11 sobre la friccional y, al recorrerse la placa hacia
    abajo, invierte el signo del resultado. El refrigerante GANA presion.

    La causa es el flujo masico: 40.3 kg/h repartidos en 14 canales dan
    G ~ 3.3 kg/(m2 s), que deja la friccion en unos pocos Pa mientras la columna
    de 0.25 m pesa lo que pesa.

    Es ademas el unico termino de la ec. 9-20 que NO depende de ninguna
    correlacion: es rho g dz. Por eso la conclusion se sostiene aunque el factor
    de friccion siga siendo provisional (antigua tabla 10.7).
    """
    _, r = _condensador_completo()
    d = r.dP_parts
    assert d["gravitatoria"] < 0.0           # descendente: resta presion
    # LA CONCLUSION SE REVISA, y conviene seguir la pista completa. El factor de
    # 11 se obtuvo con `chevron_generic`, que la antigua tabla 10.7 declara PROVISIONAL
    # y que no depende del angulo de corrugacion. Con Martin —la correlacion que
    # el ap. 9.6.7 dice haber empleado, sin coeficientes libres— y el angulo
    # identificado, la friccion sale unas quince veces mayor y pasa a DOMINAR:
    # 225 Pa frente a 57 de gravedad en este punto, con caida neta de presion.
    #
    # Lo que sobrevive, y es lo que el ap. 9.6.6 necesita, es que la
    # contribucion gravitatoria NO es despreciable: pesa un cuarto de la
    # friccional y basta para cambiar el signo en los puntos de bajo caudal. El
    # contraste del punto de ficha del 27-30H lo muestra: alli la gravedad si
    # domina y el signo si se invierte, porque el caudal es menor.
    assert abs(d["gravitatoria"]) > 0.15 * abs(d["friccional"])
    assert r.dP_ref > 0.0                    # con Martin, caida neta


def test_el_sentido_del_flujo_decide_el_signo_y_se_puede_imponer():
    """El «±» de la ec. 9-20 no es indeterminacion: es el sentido del flujo.

    Se deduce del papel en el modo —el §9.6.3 describe la pelicula de
    condensado descendente, el §9.6.6 el evaporador ascendente— y se puede
    imponer cuando el montaje real diga otra cosa. La horizontal anula el
    termino y sirve de referencia.
    """
    _, r_cond = _condensador_completo()
    _, r_asc = _condensador_completo(flow_upward=True)
    _, r_hor = _condensador_completo(vertical=False)

    assert r_hor.dP_parts["gravitatoria"] == 0.0
    assert r_asc.dP_parts["gravitatoria"] > 0.0
    assert r_cond.dP_parts["gravitatoria"] < 0.0
    # La orientacion pesa la MITAD que la friccion, no veinte veces mas: es la
    # misma revision que el test anterior documenta. Sigue siendo una magnitud
    # que hay que declarar —cambia el resultado un 50 %— pero ya no lo domina.
    assert 0.3 < abs(r_asc.dP_ref - r_cond.dP_ref) / abs(r_hor.dP_ref) < 1.0


def test_el_multiplicador_bifasico_es_intercambiable_por_nombre():
    """Ap. 9.12.3. Familia propia y no dentro de `friction` porque la firma es
    distinta: mezclarlas impediria sustituir una sin tocar el componente.

    El homogeneo subestima, como debe: con una relacion de densidades de ~50 en
    NH3 a 50 C, ignorar el deslizamiento deja la perdida por debajo.
    """
    from amoniatermia.correlations import available

    assert "lockhart_martinelli_chisholm" in available("twophase_multiplier")
    _, r_lm = _condensador_completo()
    _, r_h = _condensador_completo(
        corr={"twophase_multiplier": "homogeneo"})
    assert r_h.dP_parts["friccional"] < r_lm.dP_parts["friccional"]


def test_la_constante_C_de_chisholm_es_la_de_la_tabla_10_7():
    """La antigua tabla 10.7 declara C = 5/10/12/20 como CONOCIDAS, a diferencia del
    factor de friccion monofasico, que sigue pendiente de la geometria."""
    from amoniatermia.correlations.friction import C_CHISHOLM

    assert sorted(C_CHISHOLM.values()) == [5.0, 10.0, 12.0, 20.0]


def test_la_perdida_de_carga_no_sale_sin_marca():
    """El factor de friccion es PROVISIONAL y el multiplicador extrapola
    geometria Y fluido: tubos horizontales con aire-agua frente a NH3 en placas
    corrugadas verticales. Antes la perdida de carga salia del componente sin
    dejar rastro en el registro."""
    hx, r = _condensador_completo()
    familias = {e.family for e in hx.log.excursions}
    assert "friction" in familias
    assert "twophase_multiplier" in familias
    assert r.extrapolated


# ---------------------------------------------------------------------------
# D6 — diferencia de temperaturas del volumen (ec. 9-11)
# ---------------------------------------------------------------------------

def test_la_diferencia_de_temperaturas_es_la_logaritmica():
    """La ec. 9-11 del §9.6.1 es Q = UA dT_lm. El componente usaba la
    diferencia aritmetica del extremo de entrada del volumen."""
    hx, _ = _condensador_completo()
    assert hx.dT_mean == "lmtd"
    with pytest.raises(ValueError, match="lmtd"):
        _condensador_completo(dT_mean="media")


def test_la_desviacion_aritmetica_era_inocua_y_ahora_esta_medida():
    """Cierre honesto de D8.

    La discrepancia se anoto como «defendible con discretizacion fina, pero es
    una desviacion no declarada». Medida, la diferencia entre ambas
    formulaciones es inferior al 0.05 % ya con 20 volumenes: la desviacion era
    inocua. Lo que no era admisible es que estuviese sin declarar ni medir.

    Se conserva "arithmetic" precisamente para poder seguir midiendolo.
    """
    # Con el seguimiento de la frontera del 21/09/2026 la desviacion vuelve a
    # ser MONOTONA en la malla —1.4e-3, 3.6e-4, 9.0e-5 y 2.2e-5 a n = 20, 40,
    # 80 y 160—, de modo que la medida vuelve a decir lo que pretende decir. El
    # artefacto de frontera, que a malla gruesa la hacia saltar hasta 1.9e-2 y
    # no converger, ha desaparecido.
    #
    # El umbral se evalua desde n = 40: a n = 20 la desviacion es 1.4e-3, mayor
    # que el 5e-4 original, y no por un artefacto sino porque la pelicula
    # anclada da un coeficiente un 54 % mas alto y con el un perfil mas curvado.
    # La conclusion de D8 no se mueve: la eleccion de convenio es inocua frente
    # a la incertidumbre de las correlaciones, que es de otro orden.
    for n in (40, 160):
        _, r_lm = _condensador_completo(n_cells=n)
        _, r_ar = _condensador_completo(n_cells=n, dT_mean="arithmetic")
        assert abs(r_ar.Q_dot - r_lm.Q_dot) / abs(r_lm.Q_dot) < 5e-4


def test_la_media_logaritmica_no_revienta_si_las_diferencias_se_cruzan():
    """No existe con dT de signos distintos ni con dT iguales. En ambos casos
    se retrocede a la aritmetica, que es el limite cuando dT_a -> dT_b."""
    hx, _ = _condensador_completo(n_cells=10)
    assert hx._dT_efectiva(5.0, -5.0) == pytest.approx(0.0)
    assert hx._dT_efectiva(4.0, 4.0) == pytest.approx(4.0)
    assert hx._dT_efectiva(10.0, 5.0) == pytest.approx(5.0 / math.log(2.0))


# ---------------------------------------------------------------------------
# D7 — convenio de area desarrollada frente a declarada
# ---------------------------------------------------------------------------

def _geom_desrecalentador(**kw):
    from amoniatermia import data as D

    return D.plate_geometry("desrecalentador_acs", beta_c=math.radians(60.0),
                            t_p=0.0004, **kw)


def test_el_convenio_de_area_es_explicito_y_por_defecto_desarrollada():
    """D13. `A_total` multiplicaba por phi sin decir que lo hacia, de modo que
    el 0.0995 m2 de la tabla 9.12 y los 0.117 m2 del codigo parecian el mismo
    numero mal calculado cuando son DOS MAGNITUDES DISTINTAS.

    El convenio adoptado es el desarrollado por coherencia interna, no por
    preferencia: el diametro hidraulico de la ec. 9-13 es D_h = 2b/phi, que es
    la definicion del VDI, y la correlacion de Martin del §9.6.7 esta formulada
    sobre ese diametro y sobre el area desarrollada. Emparejar D_h = 2b/phi con
    el area proyectada contaria el corrugado una vez en el diametro y ninguna en
    el area.
    """
    g = _geom_desrecalentador()
    assert g.area_convention == "developed"
    assert g.A_total == pytest.approx(g.A_total_developed)
    assert g.A_total_developed == pytest.approx(g.A_total_projected * g.phi)
    with pytest.raises(ValueError, match="projected"):
        _geom_desrecalentador(area_convention="desarrollada")


def test_el_area_de_catalogo_es_la_proyectada():
    """La comprobacion que resuelve D13. Los 0.0995 m2 de la tabla 9.12 casan
    con el area PROYECTADA dentro de un 2.4 %, y quedan un 17.7 % por debajo de
    la desarrollada. No hay error en ninguna de las dos: el fabricante publica
    la proyectada y el modelo necesita la desarrollada.

    El residuo del 2.4 % que queda frente a la proyectada es geometrico —zonas
    de puerto, marco de junta, longitud efectiva frente a distancia entre
    puertos— y no tiene nada que ver con el corrugado.
    """
    rep = _geom_desrecalentador().area_report(declared=0.0995)
    assert abs(rep["desv_proyectada"]) < 0.025
    assert rep["desv_desarrollada"] == pytest.approx(0.177, abs=0.005)
    assert rep["razon_desarrollada_proyectada"] == pytest.approx(1.15)


def test_el_contraste_de_area_ya_no_discrimina_entre_convenios():
    """REVISADO el 18/09/2026, y el resultado se invierte.

    Este contraste se ofrecia como corroboracion independiente de que el
    §9.6.7 habia empleado area desarrollada: con ella el modelo quedaba a
    -3.5 % de los 2.63 kW del capitulo y con la proyectada a -9.0 %.

    Descansaba en un hueco de canal de 2.09 mm deducido del volumen por canal.
    El catalogo de la gama AlfaNova 16 da ahora el paso del paquete —2.06 mm por
    placa— y 2.09 lo EXCEDE, lo que es imposible. Con el valor correcto, 1.72 mm,
    los dos convenios caen dentro del +-9 %: +8.6 % el desarrollado y +3.2 % el
    proyectado. El contraste ya no separa una hipotesis de la otra, y ademas
    los dos han subido con la correccion del criterio de pared humeda del
    21/09/2026, que dejo de aplicar la ec. 9-19 al 100 % de las celdas de
    vapor.

    El convenio adoptado sigue siendo el DESARROLLADO, pero apoyado solo en el
    argumento de coherencia interna, que es el fuerte: D_h = 2b/Phi es la
    definicion del VDI y Martin esta formulada sobre ella. Lo que se pierde es
    la corroboracion numerica, y conviene que el capitulo no la invoque.
    """
    def Q(conv):
        geom = _geom_desrecalentador(area_convention=conv)
        f = Fluid("Ammonia")
        P = f.Psat(45 + 273.15)
        hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=80,
                                role="condenser", corr_params=PHI_EXPLORATORIOS)
        f.update_PT(P, 140.4 + 273.15)
        return -hx.solve(P, f.h, 40.3 / 3600, 35 + 273.15, 90.6 / 3600).Q_dot

    assert abs(Q("developed") - 2630.0) / 2630.0 < 0.10
    assert abs(Q("projected") - 2630.0) / 2630.0 < 0.10      # antes: > 0.08
    assert Q("developed") > Q("projected")                   # el orden si se mantiene


# ---------------------------------------------------------------------------
# Seguimiento de la frontera de fase (21/09/2026)
# ---------------------------------------------------------------------------

def _condensador_por_caudal(m_kgh, n_cells=20):
    """Condensador de climatizacion con entrada sobrecalentada. Bajando el
    caudal se recorre el componente: sin condensar del todo, condensando
    exactamente, y con liquido subenfriado a la salida."""
    f = Fluid("Ammonia")
    geom = D.plate_geometry("condensador_climatizacion")
    hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=n_cells,
                            role="condenser")
    P = f.Psat(50 + 273.15)
    f.update_PT(P, 70 + 273.15)
    return f, P, hx.solve(P, f.h, m_kgh / 3600, 40 + 273.15, 1830.0 / 3600)


@pytest.mark.parametrize("m_kgh,recortes_esperados", [
    (40.3, 1),      # cruza h_v y se queda en bifasico
    (20.0, 2),      # cruza h_v y h_l: sale liquido subenfriado
])
def test_se_recorta_un_volumen_por_cada_frontera_cruzada(m_kgh,
                                                         recortes_esperados):
    """El numero de recortes es el de transiciones de regimen, y sirve de
    diagnostico: dice cuantas zonas atraviesa el componente."""
    _, _, r = _condensador_por_caudal(m_kgh)
    assert r.n_recortes == recortes_esperados
    assert r.n_volumenes >= 20


def test_sin_frontera_que_cruzar_no_se_recorta_nada():
    """Entrando con vapor saturado y sin llegar a condensar del todo, no hay
    ninguna frontera interior: la marcha debe ser la de siempre, con
    exactamente los volumenes nominales."""
    f = Fluid("Ammonia")
    geom = D.plate_geometry("condensador_climatizacion")
    hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=20,
                            role="condenser")
    P = f.Psat(50 + 273.15)
    f.update_PQ(P, 1.0)
    r = hx.solve(P, f.h, 200.0 / 3600, 40 + 273.15, 1830.0 / 3600)
    assert r.n_recortes == 0
    assert r.n_volumenes == 20


def test_ningun_volumen_contiene_dos_regimenes():
    """Es la propiedad que da nombre a la tarea, y la que arregla la
    convergencia de malla: si un volumen empieza en vapor y acaba en bifasico,
    el salto de coeficiente entre los dos regimenes se promedia dentro de el y
    el resultado depende de donde haya caido la malla.
    """
    _, _, r = _condensador_por_caudal(20.0)
    # Se comprueba sobre el perfil de titulo, que es lo que el componente
    # expone. Los recortes dejan los bordes de zona EXACTAMENTE en 1.0 y 0.0:
    # si un volumen contuviese la frontera, su titulo de entrada estaria
    # estrictamente entre los dos regimenes y esos valores exactos no
    # apareceria­n.
    x = r.x_profile
    interiores = [v for v in x if 0.0 < v < 1.0]
    assert interiores, "el caso de prueba debe tener zona bifasica"
    # el perfil es monotono decreciente y pasa por 1.0 y 0.0 exactos, que son
    # precisamente los bordes que el recorte ha creado
    assert x[0] == pytest.approx(1.0)
    assert min(x) == pytest.approx(0.0, abs=1e-9)
    assert all(x[i] >= x[i + 1] - 1e-12 for i in range(len(x) - 1))



def test_el_recorte_conserva_el_area_y_la_entalpia():
    """Verificacion, no validacion: son identidades del esquema. El area de los
    volumenes debe sumar la del componente, y el calor total debe ser el salto
    de entalpia del refrigerante."""
    f = Fluid("Ammonia")
    geom = D.plate_geometry("condensador_climatizacion")
    hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=20,
                            role="condenser")
    P = f.Psat(50 + 273.15)
    f.update_PT(P, 70 + 273.15)
    h_in, m_dot = f.h, 20.0 / 3600
    out = hx.march(P, h_in, m_dot, 40 + 273.15, 1830.0 / 3600)
    assert sum(c["A"] for c in out["cells"]) == pytest.approx(
        geom.A_total, rel=1e-12)
    assert sum(c["V"] for c in out["cells"]) == pytest.approx(
        geom.A_channel * geom.L_p * geom.n_channels_ref, rel=1e-12)
    assert out["Q"] == pytest.approx((out["h_out"] - h_in) * m_dot, rel=1e-9)


def test_la_malla_gruesa_ya_sirve():
    """Consecuencia practica, y es la que importa para el cap. 11. Antes del
    seguimiento de la frontera, resolver con pocos volumenes daba un error de
    varios por ciento y errático; ahora n = 10 queda a menos del 0.5 % de la
    solucion de malla fina, de modo que las campanas estacionales pueden
    correrse a coste razonable."""
    Qs = {}
    for n in (10, 20, 320):
        f = Fluid("Ammonia")
        geom = D.plate_geometry("condensador_climatizacion")
        hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=n,
                                role="condenser")
        P = f.Psat(50 + 273.15)
        f.update_PT(P, 70 + 273.15)
        Qs[n] = hx.solve(P, f.h, 40.3 / 3600, 40 + 273.15, 1830.0 / 3600).Q_dot
    assert abs(Qs[10] / Qs[320] - 1.0) < 5e-3
    assert abs(Qs[20] / Qs[320] - 1.0) < 2e-3


def test_el_perfil_recorre_los_nudos_de_la_discretizacion(hx):
    """El perfil que representan las figuras de discretizacion del cap. 9: N+1
    nudos de area acumulada, del 0 al area total, con las temperaturas de los
    dos fluidos coherentes con los extremos del componente."""
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    r = hx.solve(Pk, f.h, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)
    p = r.profile
    assert len(p["A"]) == len(p["T_ref"]) == len(p["T_sec"]) == r.n_volumenes + 1
    assert len(p["T_pared"]) == r.n_volumenes
    assert p["A"][0] == 0.0
    assert p["A"][-1] == pytest.approx(hx.geom.A_total, rel=1e-9)
    assert p["T_ref"][0] == pytest.approx(380.0, abs=1e-6)
    # contracorriente: el agua sale por el extremo de entrada del refrigerante
    # y entra por el otro, con la tolerancia del disparo del componente aislado
    assert p["T_sec"][0] == pytest.approx(r.T_sec_out, abs=1e-9)
    assert p["T_sec"][-1] == pytest.approx(313.15, abs=1e-3)
