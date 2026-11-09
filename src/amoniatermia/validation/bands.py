"""Bandas de correlacion (§6.11, primera fuente de incertidumbre). Capitulo 10.

La incertidumbre dominante del modelo es la de las correlaciones de coeficiente
de pelicula, y el §6.11 la evalua «repitiendo los casos de referencia con
correlaciones alternativas y reportando la banda resultante». Aqui se sustituye
cada alternativa registrada por nombre (§9.12.3) en el componente al que aplica,
se vuelve a resolver el punto y se registra el cambio de las magnitudes.

Dos advertencias del §6.11 que el resultado debe llevar:
- una banda construida con correlaciones que COMPARTEN terminos mide la
  dispersion de lo que difiere, no la incertidumbre del fenomeno (las dos de
  ebullicion en placas comparten el termino nucleado de Cooper);
- una alternativa que no puede evaluarse por falta de un dato se DECLARA como
  no evaluable, no se omite: la banda es entonces mas estrecha de lo que seria.

La fraccion de huecos no entra aqui: la carga ya se reporta siempre como banda
de las cuatro correlaciones. Friccion y multiplicador bifasico tampoco: con la
presion uniforme de la hipotesis M8 no afectan al ciclo.
"""
from __future__ import annotations

from .. import campaign as C
from ..circuit import MODES
from ..data import MissingData
from .mesh import _magnitudes

#: (componente, familia, alternativa) frente a la correlacion principal.
ALTERNATIVAS = (
    ("bateria", "tube_boiling", "gungor_winterton_horizontal"),
    ("bateria", "tube_boiling", "cooper_solo"),
    ("bateria", "tube_condensation", "ficha_cbn21_agregado"),
    ("placas", "plate_boiling", "asymptotic_cooper"),
    ("placas", "plate_condensation", "nusselt_film"),
    ("placas", "plate_condensation", "equivalent_Re"),
    ("placas", "singlephase", "chevron_generic"),
)

#: Registradas pero FUERA de la banda: su base no es la geometria del
#: componente. Dittus-Boelter se registro solo como caso de verificacion del
#: §6.7.1 («no es una correlacion de placas»); aplicada a placas corrugadas
#: mueve el indicador entre un 13 y un 30 % y la banda mediria su
#: inaplicabilidad, no la incertidumbre del fenomeno.
FUERA_DE_BASE = (
    ("placas", "singlephase", "dittus_boelter"),
)


def band(mode, bc, sp, x0=None, alternativas=ALTERNATIVAS) -> dict:
    """Punto de referencia y cada alternativa, con la variacion relativa."""
    spec = MODES[mode]
    c, _ = C.build_circuit()
    base = c.solve(mode, bc, sp, x0=x0)
    ref = _magnitudes(base, spec)
    filas = []
    for comp, fam, nombre in alternativas:
        fila = {"componente": comp, "familia": fam, "alternativa": nombre}
        try:
            ca, _ = C.build_circuit(correlaciones={comp: {fam: nombre}})
            s = ca.solve(mode, bc, sp, x0=dict(base.unknowns))
            if not s.converged:
                s = ca.solve(mode, bc, sp)
            m = _magnitudes(s, spec)
            fila.update(estado="evaluada" if s.valid else "no_valida",
                        **{f"d_{k}": m[k] / ref[k] - 1.0 for k in
                           ("Q_util", "W_el", "indicador", "carga_max")},
                        dT_evap_K=m["T_evap"] - ref["T_evap"],
                        dT_cond_K=m["T_cond"] - ref["T_cond"],
                        dT_dis_K=m["T_dis"] - ref["T_dis"])
        except MissingData as exc:
            fila.update(estado="no_evaluable", motivo=str(exc)[:160])
        except Exception as exc:                    # noqa: BLE001
            fila.update(estado="fallo", motivo=f"{type(exc).__name__}: {exc}"[:160])
        filas.append(fila)
    evaluadas = [f for f in filas if f["estado"] == "evaluada"]
    banda = {k: (min([0.0] + [f[k] for f in evaluadas]),
                 max([0.0] + [f[k] for f in evaluadas]))
             for k in ("d_Q_util", "d_W_el", "d_indicador")}
    return {"modo": mode, "referencia": ref, "valido": bool(base.valid),
            "alternativas": filas, "banda": banda}
