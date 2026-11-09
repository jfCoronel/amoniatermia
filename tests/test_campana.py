"""Rendimiento, backend tabular y campañas. §6.6.4, §6.8 y §6.12."""
import json

import pytest

from amoniatermia import (AirState, Boundary, Fluid, Setpoints, WaterStream)
from amoniatermia import campaign as C
from amoniatermia import data as D
from amoniatermia.props import (INPUT_PAIRS, backend_deviation_report,
                                backend_is_usable, reference_states)

VERANO = dict(air=AirState(T=35 + 273.15, V_frontal=3.30),
              m_dot_air=None, T_amb=35 + 273.15)
SP = Setpoints(superheat=5.0, subcooling=2.0, T_acs=60 + 273.15)


def _bc(T_C):
    return Boundary(air=AirState(T=T_C + 273.15, V_frontal=3.30),
                    m_dot_air=None,
                    clima=WaterStream(T_in=12 + 273.15, m_dot=0.45),
                    acs=WaterStream(T_in=10 + 273.15), T_amb=T_C + 273.15)


@pytest.fixture(scope="module")
def informe():
    return backend_deviation_report("Ammonia")


# ---------------------------------------------------------------------------
# §6.6.4 — el error del backend tabular, sobre los pares que el modelo usa
# ---------------------------------------------------------------------------

def test_el_informe_recorre_los_seis_pares_y_no_solo_PT(informe):
    """AMPLIADO el 21/09/2026. El informe anterior solo cubría PT, que es
    precisamente el par que el modelo apenas usa: es degenerado dentro de la
    campana. El del camino caliente es PH, con más de un millón de llamadas por
    punto resuelto."""
    assert set(informe) == set(INPUT_PAIRS)
    assert len(INPUT_PAIRS) == 6


def test_la_malla_de_referencia_cubre_el_dominio_de_trabajo():
    """§6.6.4: «un conjunto de estados que cubre el dominio de trabajo»."""
    mono, bif = reference_states("Ammonia")
    f = Fluid("Ammonia")
    assert len(mono) >= 40 and len(bif) >= 40
    P = [p for p, _ in mono]
    assert f.Tsat(min(P)) < 260.0 and f.Tsat(max(P)) > 325.0
    assert {x for _, x in bif} >= {0.0, 0.5, 1.0}


def test_donde_funciona_la_desviacion_es_diminuta(informe):
    """El resultado que importa: en PT, PH, PQ y PS el backend tabular se
    desvía como mucho 3.6e-4, y en PH —el par del camino caliente— 4.4e-6.
    La exactitud NO es el problema."""
    for par in ("PT", "PH", "PQ", "PS"):
        assert "fallos" not in informe[par]
        for mag, v in informe[par].items():
            assert v["max"] < 1e-3, (par, mag, v)
    assert max(v["max"] for v in informe["PH"].values()) < 1e-4


def test_los_pares_DH_y_DS_NO_ESTAN_SOPORTADOS(informe):
    """EL RESULTADO DECISIVO de la fase H, y no es de exactitud.

    El backend tabular de CoolProp no admite las entradas por densidad. El
    compresor las necesita: la ec. 9-4 resuelve la compresión isócora hasta el
    volumen específico interno por DS, y la 10-6 evalúa la presión de esa etapa
    en el estado real por DH.

    La consecuencia es que el ×163 que anuncia la §9.12.4 **no se puede
    aplicar al compresor**, por mucho que la desviación sea despreciable. La
    salida es mixta: HEOS en el compresor y tabular en los intercambiadores.
    """
    for par in ("DH", "DS"):
        assert "fallos" in informe[par]
        assert any("not supported" in f for f in informe[par]["fallos"])


def test_la_tension_superficial_tampoco_la_da_el_tabular():
    """Segunda carencia, encontrada al montar la campaña. Alimenta tres de las
    cuatro correlaciones de fracción de huecos y con ellas el inventario de
    carga, que es lo que contrasta H4. El modelo la toma de un estado HEOS
    auxiliar, y eso debe declararse."""
    heos = Fluid("Ammonia")
    tab = Fluid("Ammonia", "BICUBIC&HEOS")
    P = heos.Psat(45 + 273.15)
    assert tab.sat_props(P)["sigma"] == pytest.approx(
        heos.sat_props(P)["sigma"], rel=1e-3)


def test_la_decision_de_usar_el_tabular_exige_un_umbral(informe):
    """§6.6.4: «su empleo queda condicionado a que dicha desviación resulte
    inferior al umbral declarado». El umbral no tiene valor por defecto."""
    assert backend_is_usable(informe, 1e-3)["usable"] is False   # DH/DS fallan
    solo_soportados = {k: v for k, v in informe.items()
                       if k in ("PT", "PH", "PQ", "PS")}
    assert backend_is_usable(solo_soportados, 1e-3)["usable"] is True
    assert backend_is_usable(solo_soportados, 1e-7)["usable"] is False


# ---------------------------------------------------------------------------
# La puerta: no se puede tomar el atajo sin dejar constancia
# ---------------------------------------------------------------------------

def test_pedir_el_tabular_sin_umbral_es_un_error():
    with pytest.raises(C.BackendSinUmbral, match="6.6.4"):
        C.build_circuit(backend_hx="BICUBIC&HEOS")


def test_un_umbral_inalcanzable_rechaza_el_backend():
    with pytest.raises(C.BackendFueraDeUmbral):
        C.build_circuit(backend_hx="BICUBIC&HEOS", umbral_backend=1e-7)


def test_el_informe_del_backend_viaja_con_el_circuito():
    _, inf = C.build_circuit(backend_hx="BICUBIC&HEOS", umbral_backend=1e-3)
    assert inf["usable"] and inf["umbral"] == 1e-3
    assert inf["peor"]["max"] < 1e-3


def test_en_HEOS_no_hay_informe_porque_no_hay_nada_que_condicionar():
    _, inf = C.build_circuit(backend_hx="HEOS")
    assert inf is None


# ---------------------------------------------------------------------------
# Que el atajo no cambie el resultado
# ---------------------------------------------------------------------------

def test_el_tabular_da_el_mismo_resultado_que_HEOS():
    """Si el atajo cambiase el resultado no sería un atajo. Dos y media a
    cinco veces más rápido según el modo, con el mismo punto de equilibrio."""
    from amoniatermia import MODES
    from amoniatermia import indicators as I

    bc = _bc(35.0)
    c_h, _ = C.build_circuit(backend_hx="HEOS", n_segments=40, n_cells=8)
    c_t, _ = C.build_circuit(backend_hx="BICUBIC&HEOS", umbral_backend=1e-3,
                             n_segments=40, n_cells=8)
    s_h, s_t = c_h.solve("M-2", bc, SP), c_t.solve("M-2", bc, SP)
    assert s_t.T_cond == pytest.approx(s_h.T_cond, rel=1e-4)
    assert s_t.T_evap == pytest.approx(s_h.T_evap, rel=1e-4)
    e_h = I.energy(s_h, MODES["M-2"])
    e_t = I.energy(s_t, MODES["M-2"])
    # 5e-4 a malla gruesa (n_cells = 8). Con la malla de trabajo, n = 12, la
    # diferencia baja a 4e-7: el ruido de interpolacion se amplifica cuando la
    # malla es corta, y conviene saberlo antes de correr campanas baratas.
    assert e_t.EER == pytest.approx(e_h.EER, rel=5e-4)


def test_el_tabular_ya_no_pone_un_suelo_al_residuo():
    """DISCREPANCIA ABIERTA CON EL §9.12.4 (28/09/2026).

    El capitulo sostiene que la interpolacion del backend tabular pone al
    residuo un suelo propio dos ordenes por encima del de HEOS (5.0e-8 frente a
    2.6e-10 con 120 segmentos). La historia de esa cifra ya habia corregido dos
    veces su causa: primero la discretizacion del serpentin, despues el ruido
    del compresor (ver docs/historico/PENDIENTES.md).

    El 28/09/2026 cayo el tercer factor. El jacobiano del lazo externo se
    calculaba con un paso de diferencias finitas trece veces mayor que el
    documentado —`least_squares` lo aplica relativo a |x| y x = log P0 ~ 13—, y
    con el paso absoluto HEOS llega a 2.4e-11 y el tabular a 1.4e-12. Ya no hay
    suelo del tabular medible por encima del de HEOS: los dos quedan varios
    ordenes por debajo de la tolerancia. La conclusion del capitulo cambia de
    signo y debe reescribirse; la leccion —no atribuir un suelo a la
    biblioteca sin descartar antes el metodo— sale reforzada.
    """
    bc = _bc(35.0)
    c_h, _ = C.build_circuit(backend_hx="HEOS", n_segments=120)
    c_t, _ = C.build_circuit(backend_hx="BICUBIC&HEOS", umbral_backend=1e-3,
                             n_segments=120)
    r_h = c_h.solve("M-2", bc, SP).max_residual
    r_t = c_t.solve("M-2", bc, SP).max_residual
    assert r_h < 1e-9 and r_t < 1e-9       # los dos, lejos de la tolerancia
    assert r_t < 10.0 * r_h                # y el tabular sin suelo propio


# ---------------------------------------------------------------------------
# §6.12 — campañas con procedencia, y los no convergidos conservados
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def campana():
    temps = [30.0, 35.0, 40.0]
    return C.run("M-2", [_bc(T) for T in temps], sp=SP,
                 etiquetas=[f"aire {T:.0f} C" for T in temps],
                 backend_hx="BICUBIC&HEOS", umbral_backend=1e-3)


def test_la_campana_devuelve_una_fila_por_caso(campana):
    assert campana.n == 3
    assert [f["caso"] for f in campana.rows] == ["aire 30 C", "aire 35 C",
                                                 "aire 40 C"]


def test_los_casos_no_convergidos_se_conservan_y_se_marcan(campana):
    """§6.12: «se registran y se reportan, en lugar de ser descartados
    silenciosamente». §6.6.6: se excluyen de los resultados «con indicación
    expresa». Las dos cosas a la vez significan conservarlos marcados."""
    assert campana.n_convergidos <= campana.n
    assert len(campana.validos()) == campana.n_validos
    assert all("convergido" in f and "valido" in f and "residuo" in f
               for f in campana.rows)
    if campana.n_validos < campana.n:
        assert "conservados y marcados" in campana.summary()


def test_la_marca_de_extrapolacion_viaja_con_cada_fila(campana):
    """CLAUDE.md lo exige de toda salida."""
    assert all("extrapolado" in f for f in campana.rows)
    assert campana.n_extrapolados >= 1      # d_i de Dobson-Chato, entre otras


def test_la_procedencia_lleva_los_cinco_elementos_del_10_13_6(campana):
    p = campana.provenance
    for k in ("coolprop_version", "backend", "fluids", "correlations",
              "inputs", "code_revision", "package_version"):
        assert p.get(k), k
    assert "BICUBIC&HEOS" in p["backend"] and "HEOS (compresor)" in p["backend"]
    assert "bateria" in p["correlations"]


def test_el_indicador_energetico_acompana_a_cada_fila(campana):
    for f in campana.rows:
        assert "EER" in f and "COP_global" in f and "y_D_compresor" in f
        assert "cierre_exergetico" in f


def test_la_fisica_del_barrido_es_la_esperada(campana):
    """Verificación de tendencia sobre la campaña completa, no sobre un punto:
    al subir el aire exterior sube la condensación y baja el EER."""
    Tk = [f["T_cond_C"] for f in campana.rows]
    EER = [f["EER"] for f in campana.rows]
    assert Tk[0] < Tk[1] < Tk[2]
    assert EER[0] > EER[1] > EER[2]


def test_resultados_y_procedencia_se_escriben_juntos(campana, tmp_path):
    """Un fichero de resultados sin su procedencia no cumple el §6.12."""
    p = tmp_path / "campana.json"
    campana.write(p)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["modo"] == "M-2"
    assert d["procedencia"]["code_revision"]
    assert d["verificacion_backend"]["usable"] is True
    assert len(d["filas"]) == campana.n
    assert d["resumen"]["n"] == campana.n


# ---------------------------------------------------------------------------
# Regresión de rendimiento: que la redundancia no vuelva
# ---------------------------------------------------------------------------

def test_el_estado_del_volumen_no_se_reevalua_dentro_del_lazo(monkeypatch):
    """§9.4.3. El lazo interno sobre q'' itera hasta veinticinco veces con
    (P, h) FIJOS: lo único que cambia es el flujo de calor. Evaluar las
    propiedades dentro del lazo daba 2.3 millones de llamadas a CoolProp por
    punto, la mitad del tiempo de cálculo.

    Este test cuenta las llamadas de UNA celda: deben ser una del estado más
    una por iteración —la del estado aguas abajo, que sí depende de q''— y no
    cuatro por iteración.
    """
    from amoniatermia.components.plate_hx import PlateHeatExchanger
    from amoniatermia.props import Fluid as F

    f = Fluid("Ammonia")
    geom = D.plate_geometry("condensador_climatizacion")
    hx = PlateHeatExchanger(f, Fluid("Water"), geom, n_cells=12,
                            role="condenser")
    n = {"ph": 0, "sat": 0}
    orig_ph, orig_sat = F.update_PH, F.sat_props
    monkeypatch.setattr(F, "update_PH",
                        lambda self, P, H: (n.__setitem__("ph", n["ph"] + 1),
                                            orig_ph(self, P, H))[1])
    monkeypatch.setattr(F, "sat_props",
                        lambda self, P: (n.__setitem__("sat", n["sat"] + 1),
                                         orig_sat(self, P))[1])
    P = f.Psat(50 + 273.15)
    f.update_PT(P, 70 + 273.15)
    n["ph"] = n["sat"] = 0
    out = hx.march(P, f.h, 40.3 / 3600, 40 + 273.15, 1830.0 / 3600)
    n_vol = out["n_volumenes"]

    # UNA evaluacion de saturacion por volumen. Es el invariante que se
    # rompería si el estado volviese al lazo sobre q'' o al de recorte.
    assert n["sat"] <= n_vol + 1, (
        f"sat_props {n['sat']} veces para {n_vol} volumenes: el estado ha "
        "vuelto a algun lazo")
    # Y como mucho dos `update_PH` por iteracion: la del estado aguas abajo,
    # que si depende de q'', y las de la perdida de carga. Antes eran cuatro.
    assert n["ph"] <= 2 * n_vol * 25 + 4 * n_vol


# ---------------------------------------------------------------------------
# D-2 revertida: el R-744 sale, pero el fluido sigue siendo parámetro
# ---------------------------------------------------------------------------

def test_el_conjunto_comparativo_no_lleva_R744():
    """Decisión del autor del 21/09/2026: el R-744 se retira del conjunto y
    probablemente de la tesis. Queda la comparación estricta del §6.8.3 entre
    R-717, R-290 y R-32."""
    assert C.FLUIDOS_COMPARATIVOS == ("Ammonia", "Propane", "R32")
    assert not any("CO2" in f or "744" in f for f in C.FLUIDOS_COMPARATIVOS)


@pytest.mark.parametrize("fluido", C.FLUIDOS_COMPARATIVOS)
def test_el_fluido_es_un_parametro_y_no_una_constante(fluido):
    """La provisión que D-2 declaró «no aplazable» NO se cae con la retirada
    del R-744: se refuerza, porque H5 sigue comparando tres fluidos sobre la
    misma geometría. Antes estaba «Ammonia» escrito a mano."""
    circ, _ = C.build_circuit(fluido=fluido, con_placas=False)
    assert circ.fluid.name == fluido


def test_correr_con_otro_fluido_no_es_todavia_comparable():
    """El aviso que tiene que viajar: la geometría y los parámetros
    identificados son los del amoníaco. Correr con R-290 emplea el compresor de
    NH₃ sin reidentificar y sin adaptar la cilindrada, que es lo que la tabla
    6.6 exige adaptar. El circuito se monta —es lo que permite abordar H5— pero
    el punto no es comparable todavía."""
    doc = C.build_circuit.__doc__
    assert "SIN reidentificar" in doc
    assert "cilindrada" in doc and "tabla 6.6" in doc
