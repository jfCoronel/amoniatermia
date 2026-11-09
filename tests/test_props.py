"""Verificacion de la capa de propiedades. Apartado 6.7.1."""
import math
import pytest
from amoniatermia.props import Fluid, backend_deviation_report


def test_ammonia_saturation_reference_point():
    """Punto de referencia conocido: NH3 a 0 C satura en ~4,29 bar."""
    f = Fluid("Ammonia")
    p = f.Psat(273.15)
    assert 4.20e5 < p < 4.40e5


def test_roundtrip_PT_PH():
    """h(P,T) y luego T(P,h) deben devolver la misma temperatura."""
    f = Fluid("Ammonia")
    P, T = 8.0e5, 310.0
    f.update_PT(P, T)
    h = f.h
    f.update_PH(P, h)
    assert f.T == pytest.approx(T, rel=1e-9)


def test_isentropic_compression_is_reversible():
    """Caso de solucion conocida: comprimir isoentropicamente y expandir
    de vuelta debe recuperar la entalpia inicial."""
    f = Fluid("Ammonia")
    f.update_PT(3.0e5, 268.0)
    h0, s0 = f.h, f.s
    f.update_PS(15.0e5, s0)
    s1 = f.s
    f.update_PS(3.0e5, s1)
    assert f.h == pytest.approx(h0, rel=1e-6)


def test_two_phase_density_between_phases():
    f = Fluid("Ammonia")
    sat = f.sat_props(6.0e5)
    assert sat["rho_v"] < sat["rho_l"]
    assert sat["h_lv"] > 1.0e6      # NH3 tiene calor latente muy alto


def test_backend_tabular_deviation_is_documented():
    """El backend tabular interpola: su error debe cuantificarse
    (verificacion cruzada del apartado 6.6.4).

    El informe pasó el 21/09/2026 de cubrir solo el par PT a cubrir los seis
    que el modelo usa; aquí se conserva el contraste sobre PT, que es el que
    este test comprobaba, y el resto vive en `tests/test_campana.py`.
    """
    from amoniatermia.props import deviation_report_PT

    states = [(p, t) for p in (4e5, 8e5, 15e5) for t in (280.0, 320.0, 360.0)]
    rep = deviation_report_PT("Ammonia", states, "BICUBIC&HEOS")
    assert rep["rho"]["max"] < 1e-2      # < 1 %
    assert rep["s"]["max"] < 1e-2


# ---------------------------------------------------------------------------
# §9.12.4 — Reutilizacion del estado termodinamico
# ---------------------------------------------------------------------------

def test_no_hay_PropsSI_en_el_camino_caliente(monkeypatch):
    """Regresion. `p_reduced()` llamaba a `PropsSI("pcrit", ...)` en cada
    invocacion, y el lazo interno del ap. 9.6.3 la invoca una vez por celda y
    por iteracion: 131 us/llamada medidos, frente a 5.2 us de un `AbstractState`
    reutilizado. Es decir, peor que el propio PropsSI de la §9.12.4, que es
    justo lo que el capitulo declara haber evitado.

    El test no mide tiempos —seria fragil— sino que prohibe la llamada: si
    alguien reintroduce `PropsSI` en el camino caliente, esto falla.
    """
    import math

    import CoolProp.CoolProp as CP

    from amoniatermia.components.plate_hx import PlateHeatExchanger
    from amoniatermia.geometry import PlateGeometry

    f = Fluid("Ammonia")
    sec = Fluid("Water")
    geom = PlateGeometry(n_plates=30, b=0.0022, L_w=0.111, L_p=0.250,
                         beta_c=math.radians(60.0))
    # phi_c y phi_v inyectados: son datos pendientes y la condensacion por
    # pelicula falla sin ellos. Aqui solo interesa ejercitar el camino caliente.
    hx = PlateHeatExchanger(f, sec, geom, n_cells=10,
                            corr_params={"plate_condensation": {"phi_c": 1.0,
                                                          "phi_v": 1.0}})

    Pk = f.Psat(323.15)
    f.update_PT(Pk, 380.0)
    h_in = f.h

    def _prohibido(*a, **kw):
        raise AssertionError(
            "PropsSI en el camino caliente: usar el AbstractState reutilizado "
            "(CLAUDE.md, «Propiedades termofisicas»; ap. 9.12.4)")

    monkeypatch.setattr(CP, "PropsSI", _prohibido)
    hx.solve(Pk, h_in, m_dot=0.010, T_sec_in=313.15, m_sec=0.35)


def test_las_constantes_del_fluido_se_cachean():
    f = Fluid("Ammonia")
    assert f.p_crit == f._p_crit
    assert f.T_crit == f._T_crit
    assert f.M == f._M
    # no cambian al actualizar el estado
    p0, t0, m0 = f.p_crit, f.T_crit, f.M
    f.update_PT(1.0e6, 300.0)
    assert (f.p_crit, f.T_crit, f.M) == (p0, t0, m0)
    assert f.p_reduced(f.p_crit) == 1.0


# ---------------------------------------------------------------------------
# §9.12.5 — Reproducibilidad
# ---------------------------------------------------------------------------

def test_la_procedencia_lleva_los_cinco_elementos_del_10_13_6():
    """Version de la biblioteca, backend, correlaciones activas, version del
    codigo y parametros de entrada. Faltaban tres de los cinco."""
    from amoniatermia.props import PropertyProvenance

    prov = PropertyProvenance(
        backend="HEOS", fluids=("Ammonia", "Water"),
        correlations={"plate_boiling": "additive_cooper"},
        inputs={"T_evap_K": 275.15})
    d = prov.as_dict()
    for k in ("coolprop_version", "backend", "correlations", "inputs",
              "code_revision", "package_version"):
        assert k in d and d[k] not in (None, "")


def test_la_procedencia_detecta_el_arbol_sucio():
    """Un hash de un arbol con cambios sin confirmar no identifica el codigo que
    produjo el resultado. `is_complete()` lo rechaza."""
    from amoniatermia.props import PropertyProvenance, git_revision

    rev = git_revision()
    assert rev == "desconocida" or len(rev.split("-")[0]) == 40
    sucia = PropertyProvenance(
        fluids=("Ammonia",), correlations={"x": "y"}, inputs={"a": 1},
        code_revision="abc-dirty")
    assert not sucia.is_complete()
    limpia = PropertyProvenance(
        fluids=("Ammonia",), correlations={"x": "y"}, inputs={"a": 1},
        code_revision="0" * 40)
    assert limpia.is_complete()


def test_la_procedencia_se_escribe_en_json(tmp_path):
    import json

    from amoniatermia.props import PropertyProvenance

    p = tmp_path / "procedencia.json"
    PropertyProvenance(fluids=("Ammonia",)).write_json(p)
    assert json.loads(p.read_text())["backend"] == "HEOS"
