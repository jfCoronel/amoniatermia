"""Rendimiento estacional, UNE-EN 14825:2024 (cap. 12; decisiones 4 a 11 del 02/10/2026)."""
import pytest

from amoniatermia import seasonal as S


def test_las_horas_son_las_de_la_norma():
    """Totales de la tabla B.1 y de la tabla D.1."""
    assert sum(S.BINS_CALOR_NORMA["medio"].values()) == 4910
    assert sum(S.BINS_CALOR_NORMA["calido"].values()) == 3590
    assert sum(S.BINS_CALOR_NORMA["frio"].values()) == 6446
    assert sum(S.BINS_FRIO_NORMA.values()) == 2602
    assert S.BINS_CALOR_NORMA["medio"][-10] == 1 and S.BINS_CALOR_NORMA["frio"][-22] == 1


def test_la_salida_variable_es_la_de_las_tablas():
    c = S.clima_norma("medio")
    assert S.salida_variable(35, c, -10) == 35 and S.salida_variable(35, c, 2) == 30
    assert S.salida_variable(55, c, -7) == 52 and S.salida_variable(45, c, 7) == 33
    assert S.salida_variable(35, c, -8.5) == pytest.approx(34.5)


def test_el_ciclo_marcha_paro_degrada_el_cop():
    assert S.cop_bin(4.0, 1.0) == pytest.approx(4.0)
    assert S.cop_bin(4.0, 0.5) == pytest.approx(4.0 * 0.5 / (0.9 * 0.5 + 0.1))


def test_scop_con_una_maquina_sintetica():
    """Potencia y COP constantes: el SCOP sale de la formula (16) a mano."""
    bins = {-2: 100, 2: 100, 10: 100}
    pts = {-2: {"P": 6000.0, "COP": 3.0}, 10: {"P": 6000.0, "COP": 3.0}}
    r = S.scop(bins, -10, 8000.0, pts, TOL=0)
    Ph = {T: 8000.0 * (T - 16) / (-26) for T in bins}
    cons = Ph[-2]                                              # bajo la TOL: apoyo
    for T in (2, 10):
        CR = Ph[T] / 6000.0
        cb = S.cop_bin(3.0, CR) if CR < 1 else 3.0
        elbu = max(0.0, Ph[T] - 6000.0)
        cons += (Ph[T] - elbu) / cb + elbu
    assert r["SCOPon"] == pytest.approx(sum(Ph.values()) / cons)
    assert r["eta_s"] == pytest.approx(100 * (r["SCOP"] / 2.5 - 0.03))


def test_los_climas_cte_reparten_las_8760_horas():
    for ciudad in ("Sevilla", "Madrid", "Burgos"):
        c = S.clima_cte(ciudad)
        T = S.leer_met(__import__("amoniatermia").data.data_dir() / "clima" /
                       {"Sevilla": "zonaB4.met", "Madrid": "zonaD3.met", "Burgos": "zonaE1.met"}[ciudad])
        en16 = int((__import__("numpy").rint(T) == 16).sum())
        assert sum(c.bins_calor.values()) + sum(c.bins_frio.values()) + en16 == 8760
        assert c.TOL_max is None and c.ley_salida == "medio"
    assert S.clima_cte("Burgos").Tdesignh < S.clima_cte("Madrid").Tdesignh < S.clima_cte("Sevilla").Tdesignh


class _EvFalso:
    """Maquina sintetica admisible solo con aire >= 3 °C."""
    def caudal_nominal(self, modo, T, Tin, Tout, **kw):
        return 0.45, None

    def a_salida(self, modo, T, T_out, m):
        return S.Punto(modo, T, T_out - 5, T_out, m, 8000.0 + 100 * T, 3000.0,
                       (8000.0 + 100 * T) / 3000.0, 120.0, "sin_limites", True,
                       {"base": T >= 3, "refrigeracion_suplementaria": T >= 1})


def test_la_tol_real_es_la_primera_temperatura_admisible():
    r = S.scop_equipo(_EvFalso(), S.clima_norma("medio"), 35)
    assert r["TOL"] == 3 and r["cumple_TOL_norma"] is False and r["Tbiv"] == 3
    assert r["fraccion_apoyo"] > 0
    r2 = S.scop_equipo(_EvFalso(), S.clima_norma("medio"), 35, variante="refrigeracion_suplementaria")
    assert r2["TOL"] == 1 and r2["Tbiv"] == 1 and r2["SCOP"] > r["SCOP"]
    assert r2["sensibilidad_tbiv_max"]["Tbiv"] == 2


def test_la_carga_de_diseno_se_fija_en_la_tbiv():
    """Tbiv = TOL (decision 7 corregida); con la Tbiv maxima, la carga es mayor y
    el apoyo pesa mas."""
    r = S.scop_equipo(_EvFalso(), S.clima_norma("medio"), 35)
    s = r["sensibilidad_tbiv_max"]
    assert s["Tbiv"] == 3 == r["Tbiv"]
    r = S.scop_equipo(_EvFalso(), S.clima_norma("medio"), 35, variante="refrigeracion_suplementaria")
    s = r["sensibilidad_tbiv_max"]
    assert s["Pdesignh"] > r["Pdesignh"] and s["SCOP"] < r["SCOP"]
    P_tbiv = 8000.0 + 100 * r["Tbiv"]
    assert r["Pdesignh"] == pytest.approx(P_tbiv * (-10 - 16) / (r["Tbiv"] - 16))
