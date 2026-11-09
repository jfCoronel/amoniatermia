"""Comparacion entre fluidos en igualdad de condiciones (§6.8.3, tabla 6.6; cap. 13, H5).

Lo que se mantiene, lo que se adapta y lo que resulta (tabla 6.6):

- FIJO: la geometria de los intercambiadores, las lineas, el ventilador, las
  consignas y el metodo estacional (cap. 12), con la MISMA carga de diseno para
  los tres fluidos (decision 2 del 05/10/2026).
- ADAPTADO: el compresor, con sus parametros identificados sobre los datos de su
  fabricante (opcion C del 29/09/2026), y su CILINDRADA, escalada para igualar la
  capacidad frigorifica en A35/W12-7 (decision 9b); los materiales de la bateria
  (tubo de cobre fuera del R-717, decision 9c).
- RESULTA: todo lo demas (presiones, descarga, TOL, SCOP, SEER, carga).

La cilindrada se escala con una sustitucion declarada sobre
`geometria.volumen_barrido_m3_rev` del fichero del compresor, de modo que viaja en
la procedencia de cada punto.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: Condicion de igualacion (decision 9b): A35 con agua 12/7 °C (UNE-EN 14511),
#: ventiloconvector, M-2.
T_AIRE_IGUALACION_C = 35.0
AGUA_IGUALACION_C = (12.0, 7.0)


@dataclass
class Igualacion:
    fluido: str
    compresor: str
    V_swept_catalogo: float
    V_swept: float
    factor: float
    Q_objetivo: float
    Q: float
    iteraciones: list = field(default_factory=list)
    sustituciones: dict = field(default_factory=dict)
    transferido: bool = False


def _ruta_cilindrada(compresor: str) -> str:
    return f"{compresor}:geometria.volumen_barrido_m3_rev"


def capacidad_igualacion(fluido: str, sustituciones: dict | None = None, **kw) -> tuple:
    """Potencia frigorifica de M-2 en A35/W12-7 con el caudal que da 12/7 °C."""
    from . import campaign as C
    from . import seasonal as S
    c, _ = C.build_circuit(fluido=fluido, sustituciones=sustituciones, **kw)
    ev = S.Evaluador(circuito=c)
    m, p = ev.caudal_nominal("M-2", T_AIRE_IGUALACION_C, *AGUA_IGUALACION_C)
    return p.P, m, p, c


def igualar_cilindrada(fluido: str, Q_objetivo: float, tol_rel: float = 2e-3,
                       max_it: int = 6, **kw) -> Igualacion:
    """Escala la cilindrada hasta que la capacidad en A35/W12-7 iguala
    `Q_objetivo` [W]. La capacidad crece con la cilindrada, de modo
    que el primer paso es V <- V Q_obj / Q; luego, secante, porque los
    intercambiadores limitan la capacidad y la relacion no es proporcional."""
    from . import campaign as C
    from . import data as D
    c0, _ = C.build_circuit(fluido=fluido, con_placas=False, con_lineas=False, **kw)
    comp = c0.compresor_fichero
    V0 = D.load(comp).require("geometria.volumen_barrido_m3_rev")
    V = V0
    its = []
    for _ in range(max_it):
        sus = {_ruta_cilindrada(comp): V}
        Q, m, p, c = capacidad_igualacion(fluido, sustituciones=sus, **kw)
        its.append({"V_swept": V, "Q": Q, "m_agua": m, "valido": p.valido})
        if abs(Q / Q_objetivo - 1.0) < tol_rel:
            break
        if len(its) == 1:
            V = V * Q_objetivo / Q
        else:                                   # secante: la capacidad no es
            a, b = its[-2], its[-1]             # proporcional (la limitan los
            V = b["V_swept"] + (Q_objetivo - b["Q"]) * (b["V_swept"] - a["V_swept"]) / (b["Q"] - a["Q"])
    return Igualacion(fluido, comp, V0, its[-1]["V_swept"], its[-1]["V_swept"] / V0,
                      Q_objetivo, its[-1]["Q"], its, {_ruta_cilindrada(comp): its[-1]["V_swept"]},
                      c.compresor_transferido)
