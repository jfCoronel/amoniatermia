"""Plan de verificacion y validacion. Capitulo 6, §6.7, tabla 6.5.

QUE HACE ESTE MODULO Y QUE NO
-----------------------------
Da acceso a los criterios de aceptacion de la tabla 6.5, inventaria los cinco
grupos de verificacion del §6.7.1 con el test que los materializa, y declara el
estatuto de cada fuente de contraste.

No ejecuta los casos de validacion del cap. 10, porque todavia no existen. El
modulo se escribe antes que ellos por la razon que el propio capitulo 6 da en
sus notas de revision: «los criterios de aceptacion de la tabla 6.5 deben
fijarse antes de ejecutar la validacion, no despues de ver los resultados.
Fijarlos a posteriori es una debilidad metodologica grave y detectable». Lo que
se fecha es la decision.

EL ESTADO DE LOS UMBRALES
-------------------------
No es que el capitulo los tenga y aqui falten: EL CAPITULO TAMPOCO LOS TIENE.
Estan marcados «[...]» en la propia tabla 6.5, y la cabecera del borrador
advierte de que «los espacios marcados [...] requieren fijar un valor antes de
cerrar el capitulo». Las notas de revision cuentan trece.

Lo que el capitulo si ofrece son SUGERENCIAS DE PARTIDA. `suggested()` las
devuelve; `threshold()` no las usa y falla, porque una sugerencia no es una
decision y cargarla como umbral seria decidir por el autor. El unico nivel con
criterio fijado es N5, «cumplimiento estricto», que no lleva numero.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import data as D

FICHERO = "validacion_tabla_6_5"

#: Los cinco niveles de la tabla 6.5. NO coinciden con los tres de la tabla
#: 9.1: alli la jerarquia es del MODELO —componente, circuito, sistema— y aqui
#: es la de la VALIDACION, que reparte el nivel de componente en dos por tener
#: fuentes distintas y anade un nivel de subsistema y otro de coherencia.
NIVELES = ("N1", "N2", "N3", "N4", "N5")

#: Criterio de N5, el unico de la tabla que no lleva un «[...]».
ESTRICTO = "estricto"


class NoEsUnaDecision(RuntimeError):
    """Se ha pedido como umbral una SUGERENCIA del capitulo 6."""


@dataclass(frozen=True)
class Nivel:
    id: str
    nombre: str
    fuente: str
    magnitudes: tuple
    criterio: str
    umbral: object
    sugerido: object

    @property
    def umbral_fijado(self) -> bool:
        return self.umbral is not None

    @property
    def lleva_numero(self) -> bool:
        """N5 exige cumplimiento estricto y no admite una tolerancia."""
        return self.umbral != ESTRICTO


@dataclass(frozen=True)
class ItemVerificacion:
    """Uno de los grupos de verificacion del §6.7.1."""
    id: str
    enunciado: str
    test: str
    umbral: object = None
    sugerido: object = None
    fijado: object = None

    @property
    def fichero_de_test(self) -> str:
        return self.test.split("::")[0]


@dataclass(frozen=True)
class Fuente:
    id: str
    tipo: str
    niveles: tuple
    descripcion: str
    estado: str
    reserva: str = ""

    @property
    def es_experimental(self) -> bool:
        return self.tipo == "experimental"

    @property
    def sirve_para_validar(self) -> bool:
        """Una fuente de SIMULACION no valida: compararia simulacion contra
        simulacion, y el §6.7.3 exige fuentes «mutuamente independientes». Y una
        ya consumida como anclaje tampoco, porque el modelo la reproduce por
        construccion."""
        return self.estado not in ("NO_ES_FUENTE_DE_VALIDACION",
                                   "consumido_como_anclaje", "sin_localizar")

    @property
    def tiene_datos(self) -> bool:
        return bool(D.load(FICHERO).optional(f"fuentes.{self.id}.datos"))


def _df():
    return D.load(FICHERO)


def levels() -> dict:
    return {k: Nivel(id=k, nombre=v["nombre"], fuente=v["fuente"],
                     magnitudes=tuple(v["magnitudes"]), criterio=v["criterio"],
                     umbral=v.get("umbral"), sugerido=v.get("sugerido_cap_7"))
            for k, v in _df().require("niveles").items()}


def threshold(nivel: str):
    """Criterio de aceptacion de la tabla 6.5 para un nivel.

    FALLA para N2 y N4, y debe hacerlo: la v3 del capitulo 6 los declara sin
    fijar por falta de fuente utilizable. N1 y N3 los adopto el autor el
    21/09/2026 desde la sugerencia de la v1, y la v3 los fija en la tabla.
    `suggested()` devuelve la sugerencia por separado y esta funcion no la usa.
    """
    if nivel not in NIVELES:
        raise KeyError(f"Nivel desconocido: {nivel!r}. Son {NIVELES}.")
    return _df().require(
        f"niveles.{nivel}.umbral",
        "Criterio de aceptacion de la tabla 6.5. La v3 del capitulo 6 lo "
        "declara sin fijar: no esta fijado tampoco alli. Fijarlo es una "
        "decision del autor y no puede tomarla el codigo.")


def suggested(nivel: str):
    """Sugerencia de partida de las notas de revision del capitulo 6.

    Se devuelve por separado y con nombre distinto a proposito: una sugerencia
    no es un criterio, y confundirlas es exactamente lo que convertiria un
    umbral sin fijar en uno fijado sin decidir.
    """
    if nivel not in NIVELES:
        raise KeyError(f"Nivel desconocido: {nivel!r}. Son {NIVELES}.")
    return _df().optional(f"niveles.{nivel}.sugerido_cap_7")


def adopted_tolerance(clave: str) -> float:
    """Tolerancia ADOPTADA por el repositorio.

    No son la tabla 6.5. El caso historico es `cierre_de_balances`: el
    repositorio adopto 1e-3 frente al 0.5 % que sugeria la v1 del capitulo 6, y
    la v3 hace suyo el 1e-3 (§6.7.1). `divergencias_con_el_capitulo()` vigila
    que sigan coincidiendo, porque decide que soluciones se marcan no validas.
    """
    return _df().require(f"tolerancias_adoptadas.{clave}")


def divergencias_con_el_capitulo() -> list:
    """Donde el repositorio y el capitulo 6 no coinciden.

    Se compara contra lo que el capitulo FIJA (`fijado_cap_7`) y, solo si no
    fija nada, contra lo que sugiere. Se reporta en lugar de alinearse en
    silencio: si el codigo es mas estricto que el capitulo, el capitulo declara
    un criterio que el codigo no aplica; y si es mas laxo, el codigo acepta
    resultados que el capitulo rechazaria. Las dos cosas hay que verlas.

    Con la v3 del capitulo 6 (24/09/2026) la lista esta vacia: el 1e-3 del
    cierre de balances, que era la unica divergencia, lo fija ya el §6.7.1.
    """
    fuera = []
    adoptado = adopted_tolerance("cierre_de_balances")
    for item in verification_items():
        if item.id != "cierre_de_balances":
            continue
        ref = item.fijado if item.fijado is not None else item.sugerido
        if ref is not None and abs(adoptado - ref) > 1e-12:
            fuera.append({
                "concepto": "cierre_de_balances",
                "adoptado": adoptado, "capitulo_7": ref,
                "sentido": ("el repositorio es MAS ESTRICTO"
                            if adoptado < ref
                            else "el repositorio es MAS LAXO")})
    return fuera


def metrics_required() -> tuple:
    """Las cuatro metricas que el §6.7.4 exige reportar."""
    return tuple(_df().require("metricas"))


def parity_band() -> float:
    """Semianchura de la banda de paridad del §6.7.4. Tambien es un «[...]»."""
    return _df().require(
        "banda_paridad.valor",
        "Banda de paridad del §6.7.4. El capitulo la deja en «±[...] %»; las "
        "notas de revision sugieren ±10 %.")


def verification_items() -> tuple:
    """Los grupos de verificacion del §6.7.1."""
    return tuple(ItemVerificacion(
        id=c["id"], enunciado=c["enunciado"], test=c["test"],
        umbral=c.get("umbral"), sugerido=c.get("sugerido_cap_7"),
        fijado=c.get("fijado_cap_7"))
        for c in _df().require("verificacion_6_7_1"))


def sources() -> dict:
    return {k: Fuente(id=k, tipo=v["tipo"], niveles=tuple(v["niveles"]),
                      descripcion=v["descripcion"], estado=v["estado"],
                      reserva=v.get("reserva", "") or "")
            for k, v in _df().require("fuentes").items()}


def sources_for(nivel: str) -> dict:
    if nivel not in NIVELES:
        raise KeyError(f"Nivel desconocido: {nivel!r}. Son {NIVELES}.")
    return {k: f for k, f in sources().items() if nivel in f.niveles}


def missing_tests(raiz: Path | None = None) -> list:
    """Items del §6.7.1 cuyo test no existe en el arbol.

    Si se nombra un nodo concreto se comprueba que el nodo exista, y no solo el
    fichero: un `::nombre` que ya no esta declara una verificacion que no se
    ejecuta. Es ademas un candado sobre los renombrados.
    """
    raiz = raiz or Path(__file__).resolve().parents[3]
    faltan = []
    for c in verification_items():
        ruta = raiz / c.fichero_de_test
        if not ruta.is_file():
            faltan.append(c.id)
            continue
        if "::" in c.test:
            nodo = c.test.split("::")[-1]
            texto = ruta.read_text(encoding="utf-8")
            if f"def {nodo}(" not in texto and f"class {nodo}" not in texto:
                faltan.append(c.id)
    return faltan


def report() -> str:
    """Estado del plan de V&V, para el cap. 10."""
    L = ["Plan de V&V — tabla 6.5", ""]
    L.append("Criterios de aceptacion:")
    for k, n in levels().items():
        if n.umbral_fijado:
            L.append(f"  {k}  {n.nombre:<34} {n.umbral}")
        else:
            s = suggested(k)
            L.append(f"  {k}  {n.nombre:<34} SIN FIJAR"
                     + (f"  (sugerido: {s})" if s else ""))
    L += ["", f"Metricas: {', '.join(metrics_required())}", ""]
    L.append("Verificacion del §6.7.1:")
    faltan = set(missing_tests())
    for c in verification_items():
        L.append(f"  [{'FALTA' if c.id in faltan else '  ok ':^5}] {c.id}")
    L += ["", "Fuentes:"]
    for f in sources().values():
        marca = "valida" if f.sirve_para_validar else "NO valida"
        datos = "con datos" if f.tiene_datos else "SIN datos"
        L.append(f"  [{marca:^9}] {f.id:<24} {','.join(f.niveles):<7} {datos}")
    div = divergencias_con_el_capitulo()
    if div:
        L += ["", "Divergencias con el capitulo 6:"]
        for d in div:
            L.append(f"  {d['concepto']}: {d['adoptado']:g} frente a "
                     f"{d['capitulo_7']:g} — {d['sentido']}")
    else:
        L += ["", "Sin divergencias con el capitulo 6."]
    return "\n".join(L)
