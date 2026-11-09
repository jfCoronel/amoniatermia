"""Verificacion del modelo de compresor. Apartados 9.5 y 6.7.1."""
import pytest
from amoniatermia.props import Fluid
from amoniatermia.geometry import CompressorGeometry
from amoniatermia.components.compressor import (
    SemiEmpiricalCompressor, CompressorParams)


@pytest.fixture
def comp():
    f = Fluid("Ammonia")
    g = CompressorGeometry(V_swept=1.2e-4, n_rpm=1450.0)
    p = CompressorParams(AU_su_n=15.0, AU_ex_n=25.0, AU_amb=8.0,
                         A_leak=0.0, C=0.035, alpha_l=0.06, W_loss0=200.0,
                         m_dot_n=0.010)
    return SemiEmpiricalCompressor(f, g, p)


def test_converges_at_nominal(comp):
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(273.15), f.Psat(323.15)
    r = comp.solve(P0, 273.15 + 5.0, Pk, T_amb=298.15)
    assert r.converged
    assert r.m_dot > 0.0
    assert r.W_shaft > 0.0
    # Sin rendimientos declarados, la potencia electrica NO se inventa
    assert r.W_el is None


def test_discharge_temperature_is_high(comp):
    """El exponente isoentropico del NH3 conduce a temperaturas de descarga
    muy superiores a las de fluidos halogenados. Es la base fisica de H3."""
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(273.15), f.Psat(323.15)
    r = comp.solve(P0, 273.15 + 5.0, Pk)
    assert r.T_dis - 273.15 > 80.0, "T_dis demasiado baja para NH3"


def test_volumetric_efficiency_decreases_with_pressure_ratio(comp):
    """Verificacion de consistencia fisica (ap. 6.7.1)."""
    f = Fluid("Ammonia")
    P0 = f.Psat(273.15)
    e1 = comp.eta_v(P0, f.Psat(313.15))
    e2 = comp.eta_v(P0, f.Psat(333.15))
    assert e2 < e1


def test_mass_flow_decreases_with_evaporating_temperature(comp):
    """Menor T0 -> menor densidad de aspiracion -> menor caudal masico."""
    f = Fluid("Ammonia")
    Pk = f.Psat(323.15)
    r_hi = comp.solve(f.Psat(278.15), 278.15 + 5.0, Pk)
    r_lo = comp.solve(f.Psat(263.15), 263.15 + 5.0, Pk)
    assert r_lo.m_dot < r_hi.m_dot


def test_la_potencia_electrica_exige_declarar_los_rendimientos(comp):
    """Ec. 9-9. El paso de potencia al eje a electrica depende del motor
    externo y de la transmision, que no son parametros de la maquina y no
    figuran en el capitulo. Entran en el denominador de COP y EER por exigencia
    de UNE-EN 14511, luego suponerlos contamina el contraste de H1."""
    from amoniatermia.components.compressor import MissingEfficiency

    f = Fluid("Ammonia")
    r = comp.solve(f.Psat(273.15), 278.15, f.Psat(323.15))
    assert r.W_el is None
    with pytest.raises(MissingEfficiency, match="H1"):
        comp.p.eta_electromechanical


def test_electrical_power_exceeds_shaft_power(comp):
    """Compresor ABIERTO: el motor es externo, W_el > W_shaft (ec. 9-9).

    Los rendimientos se declaran aqui EXPLICITAMENTE, que es la diferencia con
    llevarlos como valor por defecto invisible del dataclass."""
    comp.p.eta_motor, comp.p.eta_transm = 0.90, 0.97
    f = Fluid("Ammonia")
    r = comp.solve(f.Psat(273.15), 278.15, f.Psat(323.15))
    assert r.W_el > r.W_shaft


def test_identification_warns_with_few_points(comp):
    """9 parametros con pocos puntos = problema mal condicionado."""
    f = Fluid("Ammonia")
    pts = [{"P_ad": f.Psat(273.15), "T_su": 278.15, "P_ex": f.Psat(323.15),
            "m_dot": 0.01, "W_shaft": 3000.0}]
    with pytest.warns(UserWarning, match="mal condicionado"):
        comp.identify(pts, x0=comp.p.as_vector())


def test_son_nueve_parametros_no_siete(comp):
    """Ap. 9.5.3: los siete de Winandy et al. (2002) mas r_v y eta_ic."""
    from amoniatermia.components.compressor import IDENTIFIED

    assert len(IDENTIFIED) == 9
    assert "r_v" in IDENTIFIED and "eta_ic" in IDENTIFIED
    assert len(comp.p.as_vector()) == 9


def test_eta_ic_unitario_recupera_la_formulacion_de_siete(comp):
    """Ap. 9.5.1: «en compresores donde la relacion de volumenes constructiva
    basta para reproducir la temperatura de descarga publicada, eta_ic = 1
    recupera la formulacion original de siete parametros»."""
    f = Fluid("Ammonia")
    P0, Pk = f.Psat(273.15), f.Psat(323.15)
    comp.p.eta_ic = 1.0
    T_ideal = comp.solve(P0, 278.15, Pk).T_dis
    comp.p.eta_ic = 0.613
    T_real = comp.solve(P0, 278.15, Pk).T_dis
    # eta_ic < 1 representa irreversibilidad interna adicional: calienta mas
    assert T_real > T_ideal + 5.0


def test_la_fuga_interna_esta_bloqueada_en_el_dominio_de_trabajo(comp):
    """Ap. 9.5.1: la tobera se evalua «en regimen critico o subcritico segun la
    relacion de presiones». Con NH3 (gamma ~ 1.34) la relacion critica es ~1.84
    y el compresor opera en M-2 en torno a 3.85, luego la fuga esta bloqueada.
    La forma incompresible anterior sobreestimaba el caudal de fuga."""
    f = Fluid("Ammonia")
    comp.p.A_leak = 1.73e-7
    r = comp.solve(f.Psat(275.15), 276.15, f.Psat(318.15))
    assert r.choked
    assert r.m_leak > 0.0
    # a relacion de presiones baja deja de estar bloqueada
    r2 = comp.solve(f.Psat(283.15), 284.15, f.Psat(293.15))
    assert not r2.choked
