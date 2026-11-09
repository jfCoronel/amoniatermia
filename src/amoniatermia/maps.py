"""Mapas de prestaciones: rejilla de puntos resueltos e interpolacion.

POR QUE EXISTE
--------------
El rendimiento estacional (cap. 12) necesita cientos de puntos por clima y por
modo; la comparacion entre fluidos (cap. 13) los repite para tres fluidos, y la
campana parametrica (cap. 11) es en si una rejilla. Resolver cada punto cuando
se necesita multiplicaria el coste y, peor, mezclaria en un mismo resultado
puntos resueltos con distinto arranque. Un mapa se resuelve UNA vez, se guarda
con su procedencia y se interpola.

QUE ES Y QUE NO ES
------------------
- Los EJES son condiciones de contorno o consignas (temperatura del aire, del
  agua, caudales...), nunca T_evap ni T_cond: esas son incognitas que el modelo
  resuelve (§6.8.1). Un mapa a temperatura impuesta no es un mapa de equilibrios.
- Cada nudo conserva su fila completa (`campaign.fila`): validez,
  admisibilidad, envolvente, banda de carga, extrapolacion y procedencia.
- La interpolacion es multilineal y devuelve NaN fuera de la rejilla y alli
  donde algun nudo vecino no es valido. NaN es la respuesta correcta: un valor
  interpolado sobre un punto no valido no es un resultado soportado.

CONTINUACION
------------
La rejilla se recorre en serpentin (cada eje alterna de sentido), de modo que
cada nudo arranca del anterior, que es su vecino. Si la continuacion no
converge, se reintenta desde la estimacion por parametros agrupados con sus
arranques alternativos (`Circuit.solve` con `x0=None`), y la fila registra
desde donde convergio.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from . import campaign as C
from .circuit import MODES


def _serpentin(tamanos: tuple) -> list:
    """Indices de la rejilla en serpentin: vecinos consecutivos siempre."""
    if len(tamanos) == 1:
        return [(i,) for i in range(tamanos[0])]
    resto = _serpentin(tamanos[1:])
    out = []
    for i in range(tamanos[0]):
        tramo = resto if i % 2 == 0 else resto[::-1]
        out.extend((i,) + t for t in tramo)
    return out


@dataclass
class PerformanceMap:
    """Rejilla resuelta de un modo, con sus filas y su procedencia."""
    mode: str
    ejes: dict                       # nombre -> valores (crecientes)
    rows: list = field(default_factory=list)   # una fila por nudo, con coordenadas
    provenance: dict = field(default_factory=dict)
    fluido: str = "Ammonia"

    @property
    def shape(self) -> tuple:
        return tuple(len(v) for v in self.ejes.values())

    @property
    def n_validos(self) -> int:
        return sum(1 for r in self.rows if r.get("valido"))

    def grid(self, magnitud: str, solo_validos: bool = True) -> np.ndarray:
        """La magnitud sobre la rejilla, NaN en los nudos no validos."""
        out = np.full(self.shape, np.nan)
        for r in self.rows:
            if solo_validos and not r.get("valido"):
                continue
            v = r.get(magnitud)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[tuple(r["_indice"])] = v
        return out

    def __call__(self, magnitud: str, **coords) -> float:
        """Interpolacion multilineal de `magnitud` en `coords` (una por eje).

        NaN fuera de la rejilla o si algun nudo del entorno no es valido."""
        from scipy.interpolate import RegularGridInterpolator
        faltan = set(self.ejes) - set(coords)
        if faltan:
            raise ValueError(f"Faltan coordenadas: {sorted(faltan)}")
        interp = RegularGridInterpolator(
            [np.asarray(v, float) for v in self.ejes.values()],
            self.grid(magnitud), method="linear", bounds_error=False,
            fill_value=np.nan)
        return float(interp([[coords[k] for k in self.ejes]])[0])

    # -- persistencia -----------------------------------------------------
    def write(self, base) -> tuple:
        """`<base>.csv` con los nudos y `<base>.json` con ejes y procedencia."""
        import pandas as pd
        base = Path(base)
        csv_path, meta_path = base.with_suffix(".csv"), base.with_suffix(".json")
        pd.DataFrame(self.rows).to_csv(csv_path, index=False, float_format="%.10g")
        meta_path.write_text(json.dumps(
            {"modo": self.mode, "fluido": self.fluido, "datos": csv_path.name,
             "ejes": {k: list(map(float, v)) for k, v in self.ejes.items()},
             "resumen": {"nudos": len(self.rows), "validos": self.n_validos,
                         "admisibles": sum(1 for r in self.rows if r.get("admisible"))},
             "unidades": C.UNIDADES, "procedencia": self.provenance},
            indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return csv_path, meta_path

    @classmethod
    def read(cls, base) -> "PerformanceMap":
        import pandas as pd
        base = Path(base)
        meta = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
        df = pd.read_csv(base.with_suffix(".csv"))
        rows = df.to_dict("records")
        for r in rows:
            r["_indice"] = json.loads(r["_indice"]) if isinstance(r["_indice"], str) \
                else r["_indice"]
        return cls(mode=meta["modo"], ejes={k: np.asarray(v) for k, v in meta["ejes"].items()},
                   rows=rows, provenance=meta["procedencia"], fluido=meta["fluido"])


def build(mode: str, ejes: dict, caso: Callable[[dict], tuple],
          circuito=None, fluido: str = "Ammonia", progreso: bool = False,
          **kw_circuito) -> PerformanceMap:
    """Resuelve la rejilla `ejes` del modo `mode`.

    `ejes`: {nombre: valores crecientes}. `caso(coords)` devuelve
    `(Boundary, Setpoints)` para un nudo, con `coords` = {nombre: valor}: es lo
    que traduce los ejes a condiciones de contorno, de modo que un mismo
    mecanismo sirve para T_aire x T_agua, para caudales o para consignas.

    `kw_circuito` va a `campaign.build_circuit` (backend, sustituciones,
    discretizacion...) si no se pasa `circuito`.
    """
    ejes = {k: np.asarray(v, float) for k, v in ejes.items()}
    for k, v in ejes.items():
        if len(v) > 1 and not np.all(np.diff(v) > 0):
            raise ValueError(f"El eje '{k}' debe ser estrictamente creciente.")
    if circuito is None:
        circuito, _ = C.build_circuit(fluido=fluido, **kw_circuito)
    spec = MODES[mode]
    nombres = list(ejes)
    rows, x0, sols = [], None, []
    orden = _serpentin(tuple(len(v) for v in ejes.values()))
    for n, idx in enumerate(orden):
        coords = {k: float(ejes[k][i]) for k, i in zip(nombres, idx)}
        bc, sp = caso(coords)
        s = circuito.solve(mode, bc, sp, x0=x0)
        arranque = "continuacion" if x0 is not None else "estimacion"
        if not s.converged and x0 is not None:
            s = circuito.solve(mode, bc, sp, x0=None)
            arranque = "estimacion_tras_fallo_de_continuacion"
        x0 = dict(s.unknowns) if s.converged else None
        fila = C.fila(s, spec, etiqueta=n)
        fila.update({f"eje_{k}": v for k, v in coords.items()})
        fila["_indice"] = list(idx)
        fila["arranque"] = arranque
        rows.append(fila)
        sols.append(s)
        if progreso:
            print(f"[{n + 1}/{len(orden)}] {coords} valido={s.valid}", flush=True)

    from .props import PropertyProvenance
    prov = PropertyProvenance(
        backend="ver filas", fluids=(fluido, "Water"),
        correlations=sols[0].provenance.get("correlaciones", {}) if sols else {},
        inputs={"modo": mode, "ejes": {k: list(map(float, v)) for k, v in ejes.items()},
                "sustituciones": sols[0].provenance.get("sustituciones", {}) if sols else {},
                "geometria_inyectada": sols[0].provenance.get("geometria_inyectada", {})
                if sols else {}})
    return PerformanceMap(mode=mode, ejes=ejes, rows=rows,
                          provenance=prov.as_dict(), fluido=fluido)


def ejes_producto(ejes: dict) -> list:
    """Todas las combinaciones de los ejes, como lista de diccionarios."""
    nombres = list(ejes)
    return [dict(zip(nombres, c)) for c in itertools.product(*ejes.values())]
