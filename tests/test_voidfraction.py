"""Verificacion de las correlaciones de fraccion de huecos. Apartado 9.9."""
import pytest
from amoniatermia.props import Fluid
from amoniatermia.correlations import available, get
from amoniatermia.correlations.voidfraction import charge_range, mean_density


@pytest.fixture
def sat():
    f = Fluid("Ammonia")
    s = f.sat_props(6.0e5)
    s["p_red"] = f.p_reduced(6.0e5)
    return s


def test_all_four_registered():
    names = available("voidfraction")
    for n in ("homogeneous", "zivi", "rouhani_axelsson", "premoli"):
        assert n in names


def test_bounds(sat):
    """La fraccion de huecos debe estar en (0,1) para todo titulo."""
    for name in ("homogeneous", "zivi", "rouhani_axelsson", "premoli"):
        fn = get("voidfraction", name)
        for x in (0.05, 0.3, 0.6, 0.95):
            a = fn(x, rho_l=sat["rho_l"], rho_v=sat["rho_v"], G=50.0,
                   sigma=sat["sigma"], mu_l=sat["mu_l"], mu_v=sat["mu_v"],
                   D_h=0.004)
            assert 0.0 < a < 1.0, f"{name} x={x} -> {a}"


def test_monotonic_in_quality(sat):
    """alpha debe crecer monotonamente con el titulo."""
    for name in ("homogeneous", "zivi"):
        fn = get("voidfraction", name)
        xs = [0.1, 0.3, 0.5, 0.7, 0.9]
        vals = [fn(x, rho_l=sat["rho_l"], rho_v=sat["rho_v"]) for x in xs]
        assert all(b > a for a, b in zip(vals, vals[1:]))


def test_homogeneous_gives_highest_alpha(sat):
    """El modelo homogeneo (S=1) da la fraccion de huecos mas alta y por
    tanto la masa contenida mas baja. Resultado conocido de la literatura."""
    x = 0.4
    kw = dict(rho_l=sat["rho_l"], rho_v=sat["rho_v"], G=50.0,
              sigma=sat["sigma"], mu_l=sat["mu_l"], mu_v=sat["mu_v"],
              D_h=0.004)
    a_hom = get("voidfraction", "homogeneous")(x, **kw)
    a_zivi = get("voidfraction", "zivi")(x, **kw)
    assert a_hom > a_zivi


def test_dispersion_is_significant(sat):
    """La dispersion entre correlaciones debe ser apreciable: es la razon por
    la que el apartado 9.9 exige reportar rango y no valor unico."""
    rr = charge_range(0.4, sat, G=50.0, D_h=0.004)
    rhos = [v["rho_mean"] for v in rr.values()]
    assert max(rhos) / min(rhos) > 1.2
