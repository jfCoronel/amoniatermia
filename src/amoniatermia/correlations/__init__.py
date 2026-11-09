"""Registro de correlaciones intercambiables.

Apartado 9.12.3: las correlaciones se implementan como funciones registradas
bajo un nombre, de modo que sustituir una por otra no requiera modificar el
codigo del componente. Esto es lo que hace operativamente viable el
tratamiento de la incertidumbre del apartado 6.11: la campana de sensibilidad
recorre los nombres registrados.

Cada correlacion declara ademas, junto a la funcion, su REFERENCIA y su BASE
EXPERIMENTAL. CLAUDE.md exige marcar como extrapolado todo resultado en que una
correlacion opere fuera de su base, y eso no puede hacerse si la base no viaja
con la funcion.

Sobre la validez no declarada. La antigua tabla 10.7 del capitulo deja expresamente sin
fijar los coeficientes de varias correlaciones, y `docs/historico/PENDIENTES.md` advierte
de que las constantes de las ecuaciones 9-22 y 9-23 «deben citarse de la
fuente primaria, no darse por buenas». En consecuencia la mayor parte de las
correlaciones registradas hoy tienen `validity=None`, que NO significa «vale en
todo el dominio» sino «base experimental sin declarar». `ExtrapolationLog` las
trata como no certificables: un resultado apoyado en ellas no puede afirmarse
dentro de rango. Rellenar esos rangos con valores plausibles produciria
exactamente la falsa impresion de identificacion completada que el apartado
9.6.4 pide evitar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

_REGISTRY: Dict[str, Dict[str, Callable]] = {
    "singlephase": {},
    # Cambio de fase, SEPARADO POR GEOMETRIA. Las correlaciones de placa
    # corrugada y las de interior de tubo circular gobiernan mecanismos
    # distintos y no son intercambiables entre si: el ap. 9.7.5 lo dice
    # expresamente al abrir el lado de refrigerante de la bateria («no son
    # aplicables aqui»). Mantenerlas en una sola familia permitiria que un
    # intercambiador de placas eligiese POR NOMBRE una correlacion de tubo, y
    # entonces la banda de incertidumbre del ap. 6.11 dejaria de significar
    # nada: recorreria formulaciones que no describen la geometria del
    # componente. La separacion en familias hace que ese error sea un
    # `KeyError` en lugar de un resultado verosimil y equivocado.
    "plate_boiling": {},
    "plate_condensation": {},
    "tube_boiling": {},
    "tube_condensation": {},
    "voidfraction": {},
    "friction": {},
    # Multiplicador bifasico de la perdida de carga (ec. 9-20). Familia aparte
    # de `friction` porque la firma es distinta —toma el titulo y las dos fases,
    # no un solo Reynolds— y mezclarlas romperia el contrato de
    # intercambiabilidad: no se puede sustituir una por otra sin tocar el
    # componente, que es justo lo que el ap. 9.12.3 exige poder hacer.
    "twophase_multiplier": {},
    # Familias del lado de aire (ap. 9.7). Separadas de las de refrigerante
    # porque responden a fenomenos distintos y porque la antigua tabla 10.7 las tabula
    # aparte. El ap. 9.7.4 pide expresamente poder contrastar el metodo de
    # aleta equivalente con un calculo bidimensional, lo que exige que el metodo
    # sea intercambiable y no este codificado en el componente.
    "airside": {},
    "fin": {},
}

_INFO: Dict[str, Dict[str, "CorrelationInfo"]] = {k: {} for k in _REGISTRY}


@dataclass(frozen=True)
class Validity:
    """Base experimental declarada de una correlacion.

    Attributes
    ----------
    ranges : dict
        Variable -> (minimo, maximo) en SI estricto. Un extremo `None` deja ese
        lado sin acotar.
    fluids : tuple
        Fluidos de la base experimental. Vacio = sin declarar. Emplear una
        correlacion con un fluido ausente de esta lista es una extrapolacion en
        si misma, y el capitulo la declara para la ebullicion y la condensacion
        de amoniaco (apartados 9.6.3, 9.7.5).
    source : str
        Referencia bibliografica completa de donde procede el rango.
    notes : str
        Salvedades. Es el lugar donde decir que un rango es del punto de
        anclaje y no de una campana experimental.
    """
    ranges: Dict[str, tuple] = field(default_factory=dict)
    fluids: tuple = ()
    source: str = ""
    notes: str = ""


@dataclass(frozen=True)
class CorrelationInfo:
    family: str
    name: str
    fn: Callable
    reference: str = ""
    validity: Optional[Validity] = None

    @property
    def validity_declared(self) -> bool:
        return self.validity is not None and bool(self.validity.ranges)


def register(family: str, name: str, reference: str = "",
             validity: Optional[Validity] = None):
    """Decorador de registro.

    Parameters
    ----------
    reference : str
        Referencia bibliografica completa. El apartado 9.6.4 exige que cada
        correlacion viaje con su fuente; recopilarlas al final, sobre codigo ya
        escrito, es mas lento y mas propenso a error que anotarlas aqui.
    validity : Validity or None
        Base experimental declarada. `None` significa SIN DECLARAR, no
        «universal»: ver la nota de cabecera del modulo.
    """
    def _wrap(fn):
        if family not in _REGISTRY:
            raise KeyError(f"Familia desconocida: {family}")
        _REGISTRY[family][name] = fn
        _INFO[family][name] = CorrelationInfo(
            family=family, name=name, fn=fn,
            reference=reference, validity=validity)
        fn._family, fn._name = family, name
        return fn
    return _wrap


def get(family: str, name: str) -> Callable:
    try:
        return _REGISTRY[family][name]
    except KeyError as exc:
        disp = list(_REGISTRY.get(family, {}))
        raise KeyError(
            f"Correlacion '{name}' no registrada en '{family}'. "
            f"Disponibles: {disp}") from exc


def info(family: str, name: str) -> CorrelationInfo:
    """Metadatos de una correlacion registrada."""
    try:
        return _INFO[family][name]
    except KeyError as exc:
        disp = list(_INFO.get(family, {}))
        raise KeyError(
            f"Correlacion '{name}' no registrada en '{family}'. "
            f"Disponibles: {disp}") from exc


def available(family: str) -> list:
    return sorted(_REGISTRY[family])


def families() -> list:
    return sorted(_REGISTRY)


# ---------------------------------------------------------------------------
# Marcado de resultados extrapolados
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Excursion:
    """Una correlacion operando fuera de su base experimental declarada.

    `variable` vacia indica el caso distinto de que la base no esta declarada:
    no es que el punto se salga del rango, es que no hay rango contra el que
    compararlo.
    """
    family: str
    name: str
    variable: str
    count: int = 0
    value_min: float = float("nan")
    value_max: float = float("nan")
    low: Optional[float] = None
    high: Optional[float] = None

    @property
    def undeclared(self) -> bool:
        return self.variable == ""

    def __str__(self) -> str:
        if self.undeclared:
            return (f"{self.family}/{self.name}: base experimental SIN DECLARAR "
                    f"({self.count} evaluaciones)")
        lo = "-inf" if self.low is None else f"{self.low:.4g}"
        hi = "+inf" if self.high is None else f"{self.high:.4g}"
        return (f"{self.family}/{self.name}: {self.variable} en "
                f"[{self.value_min:.4g}, {self.value_max:.4g}] fuera de "
                f"[{lo}, {hi}] ({self.count} evaluaciones)")


class OutOfRange(RuntimeError):
    """Se ha operado fuera de la base experimental con `strict=True`."""


class ExtrapolationLog:
    """Acumulador de excursiones fuera de la base experimental.

    CLAUDE.md: «marcar como extrapolado cualquier resultado en que una
    correlacion opere fuera de su base experimental». Este objeto es el
    mecanismo; los componentes lo reciben y lo alimentan, y el resultado de la
    simulacion lo adjunta.

    Agrega por (familia, nombre, variable) en lugar de guardar una entrada por
    evaluacion: con ~1e5 evaluaciones de propiedades por punto resuelto
    (§9.12.4) una lista plana seria inmanejable, y lo que interesa reportar
    es el rango recorrido y el recuento, no cada visita.
    """

    #: Tolerancia relativa al comparar con los limites de la base declarada.
    #: Los limites se publican redondeados —el Re_Dc = 4190 del punto de ficha
    #: de la bateria es 4189.9—, y sin ella el propio punto de anclaje de una
    #: correlacion salia marcado como extrapolado.
    TOL_LIMITES = 1.0e-3

    def __init__(self, strict: bool = False,
                 parent: "ExtrapolationLog | None" = None):
        """`parent` recibe tambien cada anotacion. Es como el circuito da a
        cada componente un registro propio —el que viaja en su resultado— sin
        dejar de acumular el del punto completo."""
        self.strict = strict
        self.parent = parent
        self._agg: Dict[tuple, dict] = {}

    def check(self, family: str, name: str, **values) -> None:
        """Contrasta los valores de las variables contra la base declarada.

        Las variables ausentes de la base declarada se ignoran en silencio: no
        toda correlacion acota toda variable.
        """
        ci = info(family, name)
        if not ci.validity_declared:
            self._bump((family, name, ""), float("nan"), None, None)
            if self.strict:
                raise OutOfRange(
                    f"{family}/{name} no declara base experimental "
                    "(ver antigua tabla 10.7 y docs/historico/PENDIENTES.md)")
            return
        for var, val in values.items():
            rng = ci.validity.ranges.get(var)
            if rng is None or val is None:
                continue
            low, high = rng
            tol = self.TOL_LIMITES
            if ((low is not None and val < low - tol * abs(low))
                    or (high is not None and val > high + tol * abs(high))):
                self._bump((family, name, var), float(val), low, high)
                if self.strict:
                    raise OutOfRange(
                        f"{family}/{name}: {var}={val:.4g} fuera de "
                        f"[{low}, {high}] ({ci.validity.source})")

    def _bump(self, key, value, low, high) -> None:
        if self.parent is not None:
            self.parent._bump(key, value, low, high)
        e = self._agg.get(key)
        if e is None:
            self._agg[key] = {"count": 1, "min": value, "max": value,
                              "low": low, "high": high}
            return
        e["count"] += 1
        if value == value:                      # descarta NaN
            e["min"] = value if e["min"] != e["min"] else min(e["min"], value)
            e["max"] = value if e["max"] != e["max"] else max(e["max"], value)

    @property
    def excursions(self) -> list:
        return [Excursion(family=f, name=n, variable=v, count=e["count"],
                          value_min=e["min"], value_max=e["max"],
                          low=e["low"], high=e["high"])
                for (f, n, v), e in sorted(self._agg.items())]

    @property
    def extrapolated(self) -> bool:
        """Cierto si algun resultado se apoya en una correlacion fuera de rango
        o sin base declarada. Es la marca que debe viajar con la salida."""
        return bool(self._agg)

    def as_dict(self) -> dict:
        return {
            "extrapolado": self.extrapolated,
            "excursiones": [
                {"familia": e.family, "correlacion": e.name,
                 "variable": e.variable or None,
                 "base_sin_declarar": e.undeclared,
                 "n_evaluaciones": e.count,
                 "valor_min": e.value_min, "valor_max": e.value_max,
                 "limite_inf": e.low, "limite_sup": e.high}
                for e in self.excursions],
        }

    def report(self) -> str:
        if not self._agg:
            return "Sin excursiones: todas las correlaciones dentro de su base declarada."
        return "\n".join(str(e) for e in self.excursions)

    def __repr__(self) -> str:
        return f"ExtrapolationLog(excursiones={len(self._agg)}, strict={self.strict})"


from . import (singlephase, boiling, condensation, tube,  # noqa: E402,F401
               voidfraction, friction, airside, fin)  # noqa: E402,F401

__all__ = ["register", "get", "info", "available", "families",
           "Validity", "CorrelationInfo",
           "Excursion", "ExtrapolationLog", "OutOfRange"]
