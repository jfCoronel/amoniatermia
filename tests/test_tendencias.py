"""Consistencia física de las tendencias. §6.7.1, quinto grupo.

El apartado lo pide con estas palabras: «verificación de consistencia física de
las tendencias frente a comportamientos conocidos: efecto del aumento de la
temperatura de condensación sobre el COP, efecto del subenfriamiento sobre la
producción frigorífica específica y efecto de la relación de compresión sobre
la temperatura de descarga».

Los tres faltaban. El §9.12.5 enumera los casos de solución conocida del
§6.7.1 pero no recoge este grupo, de modo que la verificación estaba declarada
en el capítulo 6 y no ejecutada en ninguna parte.

Son verificación, no validación: no comprueban que el modelo acierte un valor
sino que se comporte como la física exige. Un modelo que invierta cualquiera de
estas tres tendencias está mal, independientemente de lo bien que reproduzca un
punto de contraste.
"""
import pytest

from amoniatermia import Fluid
from amoniatermia import data as D
from amoniatermia.components.compressor import SemiEmpiricalCompressor


@pytest.fixture(scope="module")
def f():
    return Fluid("Ammonia")


@pytest.fixture(scope="module")
def comp(f):
    return SemiEmpiricalCompressor(f, D.compressor_geometry(),
                                   D.compressor_params())


def _ciclo(f, comp, T_evap_C, T_cond_C, recalentamiento=5.0, subenfr=0.0):
    """Ciclo simple resuelto con el compresor identificado.

    No es el lazo externo del §9.4: aquí las presiones se imponen, porque lo
    que se verifica es una TENDENCIA y no un punto de equilibrio. Resolverlo
    con el circuito mezclaría el efecto que se quiere aislar con el
    desplazamiento del equilibrio.
    """
    P0, Pk = f.Psat(T_evap_C + 273.15), f.Psat(T_cond_C + 273.15)
    r = comp.solve(P0, T_evap_C + 273.15 + recalentamiento, Pk, T_amb=298.15)
    if subenfr > 0.0:
        f.update_PT(Pk, T_cond_C + 273.15 - subenfr)
    else:
        f.update_PQ(Pk, 0.0)
    h_liq = f.h
    f.update_PT(P0, T_evap_C + 273.15 + recalentamiento)
    h_asp = f.h
    Q_0 = r.m_dot * (h_asp - h_liq)
    Q_k = r.m_dot * (r.h_dis - h_liq)
    return {"m_dot": r.m_dot, "W": r.W_shaft, "T_dis": r.T_dis,
            "Q_0": Q_0, "Q_k": Q_k, "COP": Q_k / r.W_shaft,
            "EER": Q_0 / r.W_shaft, "q_0": h_asp - h_liq,
            "rp": Pk / P0}


# ---------------------------------------------------------------------------

@pytest.mark.parametrize("T_evap_C", [-10.0, 0.0, 5.0])
def test_el_COP_cae_al_subir_la_condensacion(f, comp, T_evap_C):
    """Subir la condensación aumenta el trabajo específico y reduce el caudal:
    las dos actúan en el mismo sentido sobre el COP. Se comprueba a tres
    temperaturas de evaporación para que no pase por casualidad a una sola."""
    cops = [_ciclo(f, comp, T_evap_C, Tk)["COP"] for Tk in (35.0, 45.0, 55.0)]
    assert cops[0] > cops[1] > cops[2], cops
    # y la caída es apreciable, no ruido numérico
    assert cops[0] / cops[2] > 1.2


@pytest.mark.parametrize("T_evap_C,T_cond_C", [(0.0, 45.0), (-10.0, 50.0)])
def test_el_subenfriamiento_sube_la_produccion_especifica(f, comp, T_evap_C,
                                                          T_cond_C):
    """El subenfriamiento adelanta el estado de entrada a la válvula hacia
    entalpías menores, y como la expansión es isoentálpica, la producción
    frigorífica específica crece en la misma cantidad.

    Es la tendencia que justifica tratar el subenfriamiento como parámetro de
    estudio en la tabla 6.4 —«0–5 ºC (parámetro de estudio)»— en lugar de
    fijarlo.
    """
    q = [_ciclo(f, comp, T_evap_C, T_cond_C, subenfr=s)["q_0"]
         for s in (0.0, 2.0, 5.0)]
    assert q[0] < q[1] < q[2], q
    # el incremento es el cp del líquido por el salto, dentro de un margen
    f.update_PQ(f.Psat(T_cond_C + 273.15), 0.0)
    assert (q[2] - q[0]) / 5.0 == pytest.approx(f.cp, rel=0.10)


@pytest.mark.parametrize("T_evap_C", [-15.0, -5.0, 5.0])
def test_la_descarga_sube_con_la_relacion_de_compresion(f, comp, T_evap_C):
    """A mayor relación de compresión, mayor temperatura de descarga. En
    amoníaco es la tendencia que decide el límite operativo: el §9.5.3 sitúa
    la descarga en el entorno de los 120 °C ya en el punto nominal."""
    pts = [_ciclo(f, comp, T_evap_C, Tk) for Tk in (35.0, 45.0, 55.0)]
    rp = [p["rp"] for p in pts]
    T_dis = [p["T_dis"] for p in pts]
    assert rp[0] < rp[1] < rp[2], rp
    assert T_dis[0] < T_dis[1] < T_dis[2], T_dis


def test_el_caudal_cae_al_bajar_la_evaporacion(f, comp):
    """No está en la lista del §6.7.1 pero sí en la del §9.12.5, y se
    reproduce aquí junto a las demás para que las tendencias vivan en un solo
    sitio. El mecanismo es la densidad de aspiración."""
    m = [_ciclo(f, comp, T0, 45.0)["m_dot"] for T0 in (-15.0, -5.0, 5.0)]
    assert m[0] < m[1] < m[2], m


def test_las_tres_tendencias_estan_inventariadas_en_el_plan():
    """Candado: el plan de V&V debe apuntar a estos tests y no a otros."""
    from amoniatermia import validation as V

    ids = {c.id for c in V.verification_items()}
    assert {"tendencia_COP_con_temperatura_de_condensacion",
            "tendencia_subenfriamiento_sobre_produccion_frigorifica",
            "tendencia_relacion_de_compresion_sobre_descarga"} <= ids
    assert V.missing_tests() == []
