"""Independencia de la discretizacion del SISTEMA (§6.7.1). Capitulo 10.

El §6.7.1 pide incrementar el numero de volumenes «hasta que la variacion
relativa de las magnitudes de salida sea inferior al 1 %», con una serie
MONOTONA: si oscila, la causa probable es una frontera de fase mal tratada. La
tabla 9.11 lo hace para un intercambiador aislado; esto lo hace para el punto
de diseno de cada modo resuelto como sistema, que es lo que usan los capitulos
de resultados.
"""
from __future__ import annotations

import time

from .. import campaign as C
from .. import indicators as I
from ..circuit import MODES

#: (segmentos de la bateria, volumenes por placa). El segundo nivel es la
#: discretizacion de trabajo de la tabla 9.6.
NIVELES = ((30, 6), (60, 12), (120, 24), (240, 48))
TRABAJO = (60, 12)


def _magnitudes(s, spec) -> dict:
    e = I.energy(s, spec)
    util = {"frio": s.Q_evap, "calor": e.Q_util_clima}.get(spec.clima, s.Q_acs)
    ind = e.EER if spec.clima == "frio" else (e.COP if e.COP else e.COP_global)
    return {"Q_util": float(util), "W_el": float(e.W_el), "indicador": float(ind),
            "T_evap": float(s.T_evap), "T_cond": float(s.T_cond),
            "T_dis": float(s.T_dis),
            "carga_max": float(s.charge.get("_max", float("nan")))}


def mesh_series(mode, bc, sp, niveles=NIVELES, pinzamientos=None) -> dict:
    """Resuelve el punto con cada discretizacion, arrancando de la anterior.

    `pinzamientos` = (aire, agua) para la estimacion del primer nivel, cuando el
    modo necesita arranque alternativo (M-3 en diseno)."""
    spec = MODES[mode]
    filas, x0 = [], None
    for nseg, ncel in niveles:
        c, _ = C.build_circuit(n_segments=nseg, n_cells=ncel)
        if x0 is None and pinzamientos:
            x0 = c.initial_guess(mode, bc, sp, pinch_air=pinzamientos[0],
                                 pinch_water=pinzamientos[1])
        t = time.time()
        s = c.solve(mode, bc, sp, x0=x0)
        fila = {"segmentos": nseg, "volumenes": ncel, "valido": bool(s.valid),
                "residuo": float(s.max_residual), "t_s": time.time() - t,
                **_magnitudes(s, spec)}
        filas.append(fila)
        x0 = dict(s.unknowns) if s.converged else None
    claves = ("Q_util", "W_el", "indicador", "carga_max")
    variaciones = []
    for a, b in zip(filas, filas[1:]):
        v = {k: abs(b[k] / a[k] - 1.0) for k in claves}
        v.update({f"d{k}_K": abs(b[k] - a[k]) for k in ("T_evap", "T_cond", "T_dis")})
        v["de"] = (a["segmentos"], a["volumenes"])
        v["a"] = (b["segmentos"], b["volumenes"])
        variaciones.append(v)
    # Monotonia: el signo del cambio de cada magnitud no se invierte al refinar.
    monotona = {}
    for k in claves + ("T_evap", "T_cond", "T_dis"):
        d = [b[k] - a[k] for a, b in zip(filas, filas[1:])]
        monotona[k] = all(x * y >= 0 for x, y in zip(d, d[1:]))
    i = [n for n, f in enumerate(filas) if (f["segmentos"], f["volumenes"]) == TRABAJO]
    trabajo_vs_fina = None
    if i and i[0] + 1 < len(filas):
        a, b = filas[i[0]], filas[-1]
        trabajo_vs_fina = {k: abs(a[k] / b[k] - 1.0) for k in claves}
    return {"modo": mode, "filas": filas, "variaciones": variaciones,
            "monotona": monotona, "trabajo_frente_a_la_mas_fina": trabajo_vs_fina,
            "cumple_1pc": (max(trabajo_vs_fina.values()) < 0.01
                           if trabajo_vs_fina else None)}
