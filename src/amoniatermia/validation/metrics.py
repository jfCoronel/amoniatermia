"""Metricas de contraste del apartado 6.7.4.

Las cuatro que la guia de implementacion enumera: error relativo medio, error
absoluto medio, RMSE y fraccion de puntos dentro de la banda.

CONVENIO DE SIGNO. El error se define como `modelo - referencia`, de modo que
un error relativo medio POSITIVO significa que el modelo sobreestima. Se dice
aqui porque el error relativo MEDIO —con signo— y el error absoluto medio miden
cosas distintas y confundirlos es facil: el primero detecta sesgo y puede salir
nulo con errores grandes que se compensan; el segundo mide dispersion y nunca
lo hace. El ap. 6.7.4 pide los dos precisamente por eso.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Sequence


@dataclass(frozen=True)
class Metrics:
    """Resultado del contraste de una serie de puntos contra su referencia."""
    n: int
    error_relativo_medio: float       # con signo: mide SESGO
    error_absoluto_medio: float       # sin signo: mide DISPERSION
    rmse: float                       # en unidades de la magnitud
    rmse_relativo: float
    fraccion_dentro_de_banda: float
    banda: float
    peor_punto: dict = field(default_factory=dict)

    @property
    def sesgo_domina(self) -> bool:
        """Cierto si el error es mayoritariamente sistematico y no disperso.

        Distingue un modelo desplazado de uno ruidoso, y la accion que procede
        es distinta: un sesgo apunta a un parametro mal identificado, una
        dispersion a una correlacion que no captura la fisica.
        """
        if self.error_absoluto_medio == 0.0:
            return False
        return abs(self.error_relativo_medio) / self.error_absoluto_medio > 0.8

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (f"n={self.n}  sesgo={100 * self.error_relativo_medio:+.2f} %  "
                f"|error|={100 * self.error_absoluto_medio:.2f} %  "
                f"RMSE={self.rmse:.4g} ({100 * self.rmse_relativo:.2f} %)  "
                f"dentro de +-{100 * self.banda:.0f} %: "
                f"{100 * self.fraccion_dentro_de_banda:.0f} %")


def compare(modelo: Sequence[float], referencia: Sequence[float],
            banda: float = 0.10, etiquetas: Sequence | None = None) -> Metrics:
    """Contrasta una serie del modelo contra su referencia, ap. 6.7.4.

    `banda` es la semianchura relativa dentro de la cual se cuenta un punto como
    acertado. El 0.10 por defecto ya no es arbitrario: es la banda de paridad
    del §6.7.4, adoptada el 21/09/2026 y devuelta por `plan.parity_band()`. Se
    conserva como parametro explicito porque los criterios POR NIVEL de la
    tabla 6.5 son otros —N1 y N3 tienen los suyos— y quien reporte un resultado
    debe pasar el que corresponda a su nivel.

    `etiquetas` identifica los puntos para poder senalar el peor, que es lo que
    convierte una metrica agregada en algo accionable.
    """
    if len(modelo) != len(referencia):
        raise ValueError(
            f"Series de distinta longitud: {len(modelo)} frente a "
            f"{len(referencia)}. El contraste exige correspondencia punto a "
            "punto.")
    if not modelo:
        raise ValueError("No hay puntos que contrastar.")

    rel, absol, cuad, dentro = [], [], [], 0
    peor = {"indice": -1, "error_relativo": 0.0}
    for i, (m, r) in enumerate(zip(modelo, referencia)):
        if r == 0.0:
            raise ValueError(
                f"Referencia nula en el punto {i}: el error relativo no esta "
                "definido. Contraste esa magnitud en valor absoluto.")
        e = m - r
        e_rel = e / r
        rel.append(e_rel)
        absol.append(abs(e_rel))
        cuad.append(e * e)
        if abs(e_rel) <= banda:
            dentro += 1
        if abs(e_rel) > abs(peor["error_relativo"]):
            peor = {"indice": i, "error_relativo": e_rel, "modelo": m,
                    "referencia": r,
                    "etiqueta": etiquetas[i] if etiquetas else None}

    n = len(rel)
    rmse = math.sqrt(sum(cuad) / n)
    media_ref = sum(abs(r) for r in referencia) / n
    return Metrics(
        n=n,
        error_relativo_medio=sum(rel) / n,
        error_absoluto_medio=sum(absol) / n,
        rmse=rmse,
        rmse_relativo=rmse / media_ref,
        fraccion_dentro_de_banda=dentro / n,
        banda=banda,
        peor_punto=peor)


def parity_series(modelo: Sequence[float], referencia: Sequence[float],
                  banda: float) -> dict:
    """Series listas para un diagrama de paridad, ap. 6.7.4.

    Devuelve los datos, no la figura: el modulo de validacion no dibuja. Lleva
    la diagonal y las dos lineas de banda para que rehacer el diagrama tras un
    cambio del modelo sea inmediato, que es lo que la guia pide.
    """
    lo = min(min(modelo), min(referencia))
    hi = max(max(modelo), max(referencia))
    return {"x": list(referencia), "y": list(modelo),
            "diagonal": [(lo, lo), (hi, hi)],
            "banda_sup": [(lo, lo * (1.0 + banda)), (hi, hi * (1.0 + banda))],
            "banda_inf": [(lo, lo * (1.0 - banda)), (hi, hi * (1.0 - banda))],
            "banda": banda}
