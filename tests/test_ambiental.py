"""TEWI y LCCP (cap. 13, H7)."""
import pytest

from amoniatermia import ambiental as A, data as D


def test_gwp_del_reglamento_vigente():
    """Reglamento (UE) 2024/573 (decisión 3 del 05/10/2026): R-32 AR4, R-290 y R-717 del anexo VI."""
    assert (A.gwp("Ammonia"), A.gwp("Propane"), A.gwp("R32")) == (0.0, 0.02, 675.0)
    assert A.gwp("R32", "ar6") == 771.0


def test_el_caso_rd552_es_mucho_mas_severo():
    base = A.tewi("R32", 0.5, 3000.0, 0.2)
    rd = A.tewi_rd552("R32", 0.5, 3000.0, 0.2)
    assert rd["L_kg_ano"] / 0.5 > 0.5 and rd["TEWI"] > base["TEWI"]


def test_el_lccp_falla_mientras_falte_el_inoxidable():
    if D.load("ambiental").optional("lccp.materiales_kgCO2e_kg.acero_inoxidable") is None:
        with pytest.raises(D.MissingData):
            A.lccp("Ammonia", 0.5, 3000.0, 0.2, {"acero_inoxidable": 10.0})


def test_formula_del_tewi():
    r = A.tewi("R32", 1.0, 3000.0, 0.2)
    assert r["TEWI"] == pytest.approx(675 * 0.025 * 15 + 675 * 0.15 + 15 * 3000 * 0.2)
    assert A.tewi("Ammonia", 1.0, 3000.0, 0.2)["TEWI"] == pytest.approx(15 * 3000 * 0.2)
