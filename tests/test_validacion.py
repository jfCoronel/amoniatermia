"""Plan de verificación y validación. Tabla 6.5, apartados 6.7.1 y 6.7.4.

El módulo `validation` se escribe ANTES que los casos del capítulo 10, y estos
contrastes son la razón: lo que se quiere dejar fechado en el historial de git
es la DECISIÓN sobre los umbrales, no el resultado de aplicarlos.
"""
import math
import pathlib

import pytest

from amoniatermia import data as D
from amoniatermia import validation as V
from amoniatermia.validation import plan


# ---------------------------------------------------------------------------
# §6.7.4 — las cuatro métricas
# ---------------------------------------------------------------------------

def test_las_cuatro_metricas_del_7_7_3_estan_declaradas():
    assert set(V.metrics_required()) == {
        "error_relativo_medio", "error_absoluto_medio", "rmse",
        "fraccion_dentro_de_banda"}


def test_un_modelo_exacto_da_error_nulo_y_banda_completa():
    m = V.compare([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], banda=0.01)
    assert m.error_relativo_medio == pytest.approx(0.0)
    assert m.error_absoluto_medio == pytest.approx(0.0)
    assert m.rmse == pytest.approx(0.0)
    assert m.fraccion_dentro_de_banda == 1.0


def test_el_error_medio_y_el_absoluto_miden_cosas_distintas():
    """Es la razón por la que el §6.7.4 pide los dos, y merece un contraste.

    Un modelo que se pasa en la mitad de los puntos lo que se queda corto en la
    otra mitad tiene error relativo medio NULO —no hay sesgo— y error absoluto
    medio grande. Reportar solo el primero lo daría por perfecto.
    """
    m = V.compare([1.2, 0.8], [1.0, 1.0], banda=0.10)
    assert m.error_relativo_medio == pytest.approx(0.0, abs=1e-12)
    assert m.error_absoluto_medio == pytest.approx(0.20)
    assert not m.sesgo_domina
    assert m.fraccion_dentro_de_banda == 0.0        # ninguno dentro del ±10 %


def test_el_sesgo_se_distingue_de_la_dispersion():
    """Un modelo desplazado y uno ruidoso exigen acciones distintas: el primero
    apunta a un parámetro mal identificado, el segundo a una correlación que no
    captura la física."""
    desplazado = V.compare([1.1, 1.1, 1.1], [1.0, 1.0, 1.0], banda=0.20)
    ruidoso = V.compare([1.3, 0.7, 1.0], [1.0, 1.0, 1.0], banda=0.20)
    assert desplazado.sesgo_domina
    assert not ruidoso.sesgo_domina


def test_el_signo_del_error_dice_si_el_modelo_sobreestima():
    assert V.compare([1.1], [1.0], banda=0.5).error_relativo_medio > 0
    assert V.compare([0.9], [1.0], banda=0.5).error_relativo_medio < 0


def test_el_peor_punto_se_identifica_para_que_la_metrica_sea_accionable():
    m = V.compare([1.0, 1.5, 1.0], [1.0, 1.0, 1.0], banda=0.10,
                  etiquetas=["a", "b", "c"])
    assert m.peor_punto["etiqueta"] == "b"
    assert m.peor_punto["error_relativo"] == pytest.approx(0.5)


def test_el_rmse_se_reporta_en_unidades_y_en_relativo():
    """En unidades porque es lo que se compara con la incertidumbre de la
    medida; en relativo porque es lo que se compara con el umbral."""
    m = V.compare([110.0, 90.0], [100.0, 100.0], banda=0.20)
    assert m.rmse == pytest.approx(10.0)
    assert m.rmse_relativo == pytest.approx(0.10)


@pytest.mark.parametrize("modelo,referencia", [
    ([1.0, 2.0], [1.0]),          # longitudes distintas
    ([], []),                     # sin puntos
    ([1.0], [0.0]),               # referencia nula: el relativo no existe
])
def test_el_contraste_falla_en_lugar_de_devolver_un_numero_sin_sentido(
        modelo, referencia):
    with pytest.raises(ValueError):
        V.compare(modelo, referencia, banda=0.1)


def test_el_diagrama_de_paridad_lleva_la_diagonal_y_las_bandas():
    """La guía pide que los diagramas se generen desde el módulo, para que
    rehacerlos tras un cambio del modelo sea inmediato. El módulo devuelve los
    datos, no la figura: no dibuja."""
    p = V.parity_series([1.1, 2.1], [1.0, 2.0], banda=0.10)
    assert p["x"] == [1.0, 2.0] and p["y"] == [1.1, 2.1]
    for clave in ("diagonal", "banda_sup", "banda_inf"):
        assert len(p[clave]) == 2


# ---------------------------------------------------------------------------
# Tabla 6.5 — los criterios de aceptación, que es lo que hay que dejar fechado
# ---------------------------------------------------------------------------

def test_la_tabla_7_5_tiene_CINCO_niveles_y_no_los_tres_del_modelo():
    """Corrección del 21/09/2026, al llegar el capítulo 6.

    La jerarquía de la §9.1.2 —componente, circuito, sistema— es la del
    MODELO. La de la tabla 6.5 es la de la VALIDACIÓN, y no coincide: reparte
    el nivel de componente en dos porque tienen fuentes distintas, y añade un
    nivel de subsistema y otro de coherencia global.
    """
    assert plan.NIVELES == ("N1", "N2", "N3", "N4", "N5")
    n = V.levels()
    assert "compresor" in n["N1"].nombre
    assert "intercambiadores" in n["N2"].nombre
    assert n["N3"].magnitudes == ("COP", "potencia_calorifica")
    assert "ACS" in n["N4"].nombre
    assert n["N5"].magnitudes == ("cierre_de_balances",
                                  "generacion_de_entropia")


def test_los_criterios_adoptados_quedan_fechados_antes_de_validar():
    """LA PIEZA CENTRAL DE LA FASE G.

    La v1 del capítulo dejaba N1 a N4 en «[…]» y sus notas de revisión
    proponían valores de partida. DECISIÓN DEL AUTOR del 21/09/2026: se adoptan
    esas sugerencias allí donde existen, y se adoptan AHORA precisamente para
    que la decisión quede fechada en el historial antes de que exista ningún
    resultado de validación que pueda condicionarla. Es lo que el capítulo
    exige: «los criterios de aceptación se fijan antes de ejecutar la
    validación». La v3 (24/09/2026) los recoge ya fijados en la tabla 6.5, y
    precisa que el de N1 es de desviación MÁXIMA.
    """
    # El de la descarga se añadió el 29/09/2026, también antes de ejecutar la
    # validación cruzada (decisión del autor).
    assert V.threshold("N1") == {"caudal": 0.05, "potencia": 0.08,
                                 "temperatura_descarga_K": 5.0}
    assert V.threshold("N3") == {"COP": 0.10, "potencia": 0.15}
    assert V.parity_band() == 0.10
    for nivel in ("N1", "N3"):
        assert V.levels()[nivel].umbral_fijado
    df = D.load(plan.FICHERO)
    assert df.require("niveles.N1.estadistico") == "desviacion_maxima"
    assert "máxima" in V.levels()["N1"].criterio


@pytest.mark.parametrize("nivel", ["N2", "N4"])
def test_los_niveles_sin_sugerencia_siguen_pendientes(nivel):
    """El capítulo no propone valor para N2 —intercambiadores— ni para N4
    —recuperación de ACS—, y la v3 los declara sin fijar por falta de fuente
    utilizable. No se inventan: quedan a `null` y pedirlos falla."""
    assert "Sin fijar" in V.levels()[nivel].criterio
    assert V.suggested(nivel) is None
    with pytest.raises(D.MissingData, match=r"tabla 6.5"):
        V.threshold(nivel)


def test_la_temperatura_de_descarga_tiene_criterio_en_N1():
    """N1 lista TRES magnitudes y la tabla 6.5 solo sugiere DOS tolerancias. La
    descarga, de la que depende H3, tiene criterio desde el 29/09/2026
    (decisión del autor, fijada antes de ejecutar la validación, §6.7.3):
    5 K de desviación máxima, coherente con el margen de no condensación del
    desrecalentador (5.5 K en diseño)."""
    sin = D.load(plan.FICHERO).require("niveles.N1.sin_criterio")
    assert sin == []
    assert "temperatura_de_descarga" in V.levels()["N1"].magnitudes
    assert V.threshold("N1") == {"caudal": 0.05, "potencia": 0.08,
                                 "temperatura_descarga_K": 5.0}
    assert D.load(plan.FICHERO).require("niveles.N1.esquema") == "grupos_Tk"


def test_N5_es_el_unico_nivel_con_criterio_fijado():
    """«Cumplimiento estricto», y no lleva número porque no admite tolerancia:
    el cierre de balances y la positividad de la generación de entropía son el
    primer y el segundo principio."""
    assert V.threshold("N5") == plan.ESTRICTO
    assert not V.levels()["N5"].lleva_numero
    assert V.levels()["N5"].umbral_fijado


def test_las_sugerencias_se_conservan_aparte_de_los_criterios_adoptados():
    """Aunque coincidan hoy, se guardan en campos distintos: el criterio es una
    decisión del autor y la sugerencia es del capítulo. Si mañana se cambia el
    criterio, debe poder verse de qué se apartó."""
    assert V.suggested("N1") == {"caudal": 0.05, "potencia": 0.08}
    assert V.suggested("N3") == {"COP": 0.10, "potencia": 0.15}
    for nivel in ("N1", "N3"):
        proc = D.load(plan.FICHERO).require(f"niveles.{nivel}.procedencia")
        assert proc == "adoptado_de_la_sugerencia_del_cap_7"


def test_un_nivel_inexistente_no_es_lo_mismo_que_un_criterio_pendiente():
    """Errores distintos para causas distintas: `KeyError` si el nivel no
    existe, `MissingData` si existe y su criterio está sin fijar (N2, N4)."""
    with pytest.raises(KeyError):
        V.threshold("N9")
    with pytest.raises(KeyError):
        V.suggested("N9")


def test_las_tolerancias_adoptadas_se_distinguen_de_los_criterios():
    assert V.adopted_tolerance("magnitud_calculada") == 0.02
    assert V.adopted_tolerance("magnitud_geometrica") == 0.005
    assert V.adopted_tolerance("residuo_relativo") == 1e-6
    assert V.adopted_tolerance("cierre_de_balances") == 1e-3


def test_la_tolerancia_de_residuo_declarada_es_la_que_usa_el_circuito():
    """Si el fichero y el código divergen, el plan documenta un criterio que
    nadie aplica. Este sí está declarado en el capítulo (§6.6.6 y §9.4.4)."""
    from amoniatermia import Circuit

    assert Circuit.TOL == V.adopted_tolerance("residuo_relativo")


def test_el_capitulo_7_v3_hace_suyo_el_cierre_de_10_a_la_menos_3():
    """DIVERGENCIA CERRADA el 24/09/2026, y a favor del repositorio.

    El 21/09/2026 se decidió mantener el 10⁻³ de `circuit.py` frente al 0.5 %
    que sugería la v1 del capítulo 6, cinco veces más laxo: relajarlo habría
    hecho válidos modos cuyo balance de componente no mejoraba en nada. La v3
    del capítulo fija 10⁻³ en el §6.7.1 con esa misma justificación, de modo
    que la divergencia desaparece. La sugerencia antigua se conserva en el
    fichero para que pueda verse de qué se apartó.
    """
    assert V.divergencias_con_el_capitulo() == []
    porid = {c.id: c for c in V.verification_items()}
    cierre = porid["cierre_de_balances"]
    assert cierre.fijado == V.adopted_tolerance("cierre_de_balances") == 1e-3
    assert cierre.sugerido == 0.005


def test_una_divergencia_nueva_con_el_capitulo_se_reportaria(monkeypatch):
    """El vigilante sigue activo: si el repositorio y el capítulo vuelven a
    separarse, la divergencia aparece y dice en qué sentido."""
    monkeypatch.setattr(plan, "adopted_tolerance", lambda clave: 5e-4)
    div = V.divergencias_con_el_capitulo()
    assert len(div) == 1
    assert div[0]["capitulo_7"] == 1e-3
    assert "MAS ESTRICTO" in div[0]["sentido"]


# ---------------------------------------------------------------------------
# §6.7.1 — los casos de solución conocida
# ---------------------------------------------------------------------------

def test_los_cinco_grupos_del_7_7_1_estan_inventariados():
    """El apartado enumera cinco: casos de solución conocida, independencia de
    discretización, cierre de balances, positividad de la generación de
    entropía y consistencia física de las tendencias. El último se desglosa en
    sus tres comprobaciones, que NO existían: el §9.12.5 no las recogía y por
    tanto la verificación estaba declarada y no ejecutada."""
    ids = {c.id for c in V.verification_items()}
    assert {"casos_de_solucion_conocida", "independencia_de_discretizacion",
            "cierre_de_balances",
            "positividad_de_la_generacion_de_entropia"} <= ids
    tendencias = {i for i in ids if i.startswith("tendencia_")}
    assert len(tendencias) == 3


def test_la_verificacion_de_tendencias_era_la_que_faltaba():
    """Se añade con esta fase. Son verificación y no validación: no comprueban
    que el modelo acierte un valor sino que se comporte como la física exige."""
    porid = {c.id: c for c in V.verification_items()}
    for clave in ("tendencia_COP_con_temperatura_de_condensacion",
                  "tendencia_subenfriamiento_sobre_produccion_frigorifica",
                  "tendencia_relacion_de_compresion_sobre_descarga"):
        assert porid[clave].test.startswith("tests/test_tendencias.py::")
        assert porid[clave].umbral == plan.ESTRICTO


def test_la_independencia_de_discretizacion_cumple_la_sugerencia():
    """El capítulo sugiere 1 %. Con el seguimiento de la frontera de fase el
    modelo llega a 2·10⁻⁵, tres órdenes por debajo, de modo que la sugerencia
    no acota nada. Conviene saberlo antes de fijarla."""
    porid = {c.id: c for c in V.verification_items()}
    assert porid["independencia_de_discretizacion"].sugerido == 0.01


def test_todo_item_inventariado_apunta_a_un_test_que_existe():
    """§9.12.5: la ejecución de estas pruebas «es la evidencia de que la
    verificación del apartado 6.7.1 se ha realizado efectivamente y no solo se
    ha declarado». Un inventario que apunte a un fichero o a un nodo
    inexistente declara sin verificar, que es justo lo contrario.

    Este test es además un candado: renombrar un test de verificación sin
    actualizar el inventario lo rompe.
    """
    assert plan.missing_tests() == []


def test_el_inventario_detecta_un_nodo_que_ya_no_existe(tmp_path):
    """Comprobación del candado: si el nodo se renombra, debe saltar."""
    raiz = tmp_path
    (raiz / "tests").mkdir()
    for c in V.verification_items():
        f = raiz / c.fichero_de_test
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# fichero sin ninguno de los nodos\n", encoding="utf-8")
    faltan = plan.missing_tests(raiz=raiz)
    con_nodo = [c.id for c in V.verification_items() if "::" in c.test]
    assert set(faltan) == set(con_nodo)


# ---------------------------------------------------------------------------
# Fuentes de contraste
# ---------------------------------------------------------------------------

def test_zajacs_no_es_fuente_de_validacion():
    """`docs/historico/PENDIENTES.md`: es un estudio de diseño por simulación con EES, no
    un trabajo experimental. Compararlo con este modelo sería comparar
    simulación contra simulación.

    Se conserva declarado, y no simplemente borrado, para que la
    reclasificación quede registrada y no se cuele por inercia. La v3 del
    capítulo 6 la retira de la tabla 6.5: ya no pertenece a ningún nivel.
    """
    z = V.sources()["zajacs_2017"]
    assert z.tipo == "simulacion"
    assert not z.sirve_para_validar
    assert not z.es_experimental
    assert z.niveles == ()
    assert "Zajacs" not in V.levels()["N3"].fuente


def test_la_ficha_del_27_30H_esta_consumida_como_anclaje():
    """No puede servir de contraste independiente: el modelo la reproduce POR
    CONSTRUCCIÓN desde que β y φc·φv se identificaron sobre ella. Usarla como
    validación sería circular."""
    f = V.sources()["ficha_alfanova_27_30h"]
    assert f.estado == "consumido_como_anclaje"
    assert not f.sirve_para_validar


def test_las_tres_fuentes_experimentales_son_del_grupo_de_KTH():
    """Monfared y Palm (2011, 2012) y Palm (2008). Las tres con reserva: las
    fuentes abiertas solo dan especificaciones agregadas, y el §6.7.3 prevé el
    caso —los parámetros no disponibles se estiman y el resultado se presenta
    como BANDA DE PREDICCIÓN, declarando cuáles se han estimado—.

    Palm (2008) es además la única fuente de N4 junto con Monfared y Palm
    (2011), y no aparece en el material del repositorio."""
    exp = {k: f for k, f in V.sources().items() if f.es_experimental}
    assert set(exp) == {"monfared_palm_2011", "monfared_palm_2012",
                        "palm_2008"}
    for f in exp.values():
        assert f.reserva
    assert V.sources()["palm_2008"].estado == "sin_localizar"


def test_el_nivel_N4_se_queda_sin_fuente_utilizable():
    """Consecuencia de lo anterior, y conviene que el capítulo 10 la vea: de
    las dos fuentes de N4, una está sin localizar y la otra sin datos. El nivel
    de subsistema —el de la recuperación de ACS, que es el que sostiene H3— no
    tiene hoy con qué validarse."""
    n4 = V.sources_for("N4")
    assert set(n4) == {"monfared_palm_2011", "palm_2008"}
    assert not any(f.tiene_datos for f in n4.values())


def test_cada_nivel_sabe_cuales_son_sus_fuentes():
    assert set(V.sources_for("N1")) == {"catalogo_bock_f2"}
    assert "zajacs_2017" not in V.sources_for("N3")
    assert set(V.sources_for("N5")) == set()   # N5 no contrasta contra fuentes


def test_ninguna_fuente_experimental_tiene_datos_todavia():
    """Es la acotación honesta del alcance de la fase G: la maquinaria está,
    los datos de contraste externos no."""
    for k, f in V.sources().items():
        if f.es_experimental:
            assert not f.tiene_datos


def test_las_fuentes_de_fabricante_que_si_estan_apuntan_a_ficheros_reales():
    df = D.load(plan.FICHERO)
    raiz = pathlib.Path(__file__).resolve().parents[1]
    for k in ("catalogo_bock_f2", "ficha_frimetal_cbn21",
              "ficha_alfanova_27_30h"):
        ruta = df.require(f"fuentes.{k}.datos")
        assert (raiz / ruta).is_file(), ruta


def test_el_informe_del_plan_dice_lo_que_falta():
    """El capítulo 10 tiene que poder imprimir el estado del plan, no
    reconstruirlo a mano."""
    txt = V.report()
    assert "SIN FIJAR" in txt                    # los criterios N2 y N4
    assert "estricto" in txt                     # N5 sí está fijado
    assert "NO valida" in txt                    # Zajacs y el anclaje
    assert "SIN datos" in txt                    # las fuentes experimentales
    assert "Sin divergencias" in txt             # el cierre, cerrado en la v3
    assert "tendencia_COP" in txt


# ---------------------------------------------------------------------------
# N1 fuera del dominio de identificación: puntos del software VAP de Bock
# (decisión del autor, 29/09/2026, tarde: validación, no identificación)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def contraste_vap():
    from amoniatermia.validation import compressor_vap
    return compressor_vap.contraste()


def test_los_puntos_vap_no_entran_en_la_identificacion():
    """El juego adoptado sigue siendo el del 24/09/2026 sobre los 46 puntos
    del catálogo: el ensayo con 73 puntos se descartó."""
    cat = D.compressor_catalog()
    assert len(cat) == 46
    assert {round(p["T0"] - 273.15) for p in cat} <= set(range(0, 6))


def test_el_punto_de_control_vap_reproduce_el_catalogo(contraste_vap):
    m = contraste_vap["resumen"]["control"]
    assert m["caudal_max"] < 0.01 and m["potencia_max"] < 0.01
    assert m["descarga_max_K"] < 2.5


def test_N1_se_cumple_con_vap_en_el_dominio_del_catalogo(contraste_vap):
    """T0 de 0 a 5 °C con recalentamiento de 1 a 10 K."""
    assert contraste_vap["resumen"]["dominio"]["cumple_N1"]


def test_dominio_de_validez_del_compresor_en_T0(contraste_vap):
    """Fijado el 29/09/2026: N1 se mantiene hasta T0 = -5 °C; a 10 °C falla
    por la descarga."""
    assert contraste_vap["dominio_N1_T0_C"] == (-5, 5)


def test_DISCREPANCIA_sesgo_a_T0_bajo_declarado_como_limitacion(contraste_vap):
    """Limitación de estructura (§9.13), no de datos: pérdida mecánica
    constante, r_v y eta_ic fijos. A -20 °C la potencia sale alta y la
    descarga baja, es decir, el margen de descarga en calefacción con exterior
    frío resulta optimista."""
    p = next(f for f in contraste_vap["puntos"]
             if f["T0_C"] == -20 and f["rpm"] == 1450.0)
    assert p["d_potencia"] > 0.10 and p["d_descarga_K"] < -10.0
    assert not contraste_vap["resumen"]["extrapolacion_T0"]["cumple_N1"]


def test_DISCREPANCIA_potencia_alta_a_velocidad_reducida(contraste_vap):
    """Contraste de H6: el caudal escala bien con la velocidad y la potencia
    no, porque la pérdida mecánica es constante."""
    v = contraste_vap["resumen"]["velocidad"]
    assert v["caudal_max"] < 0.05
    assert v["potencia_max"] > 0.10


def test_el_dominio_de_validez_incluye_el_tramo_validado_con_vap():
    """29/09/2026: fuera del catálogo pero dentro del tramo en que los puntos
    VAP cumplen N1, un punto es `validado_VAP`; más allá, tendencia."""
    from amoniatermia.validation import domain
    K = 273.15
    assert domain.dominio_validado() == {"T0": (-5 + K, 5 + K), "Tc": (25 + K, 50 + K)}
    semi = dict(modelo="semiempirico")
    assert domain.clasifica(1.6 + K, 43.3 + K, **semi) == "interpolado"
    assert domain.clasifica(-4.1 + K, 46.3 + K, **semi) == "validado_VAP"
    assert domain.clasifica(-5.9 + K, 45.9 + K, **semi) == "fuera_del_dominio"
    assert domain.clasifica(17.6 + K, 52.1 + K, **semi) == "fuera_del_dominio"


def test_con_polinomios_el_dominio_del_compresor_es_su_envolvente():
    """15/10/2026: los datos de VAP cubren las zonas sin limites y de refrigeracion
    suplementaria; fuera de ellas el polinomio extrapola."""
    from amoniatermia.validation import domain
    K = 273.15
    assert domain.clasifica(1.6 + K, 43.3 + K) == "dentro_del_dominio"
    assert domain.clasifica(-4.1 + K, 46.3 + K) == "dentro_del_dominio"   # refrig. suplementaria
    assert domain.clasifica(-12.0 + K, 44.5 + K) == "fuera_del_dominio"
    assert domain.clasifica(17.6 + K, 52.1 + K) == "fuera_del_dominio"
