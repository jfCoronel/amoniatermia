"""Carga de los ficheros de datos de componente.

Lee `data/*.yaml` de la raiz del repositorio y construye con ellos los objetos
de geometria y de parametros del modelo.

LA REGLA QUE JUSTIFICA ESTE MODULO
----------------------------------
CLAUDE.md: «los `null` en `data/*.yaml` son datos que NO existen todavia. El
modelo debe fallar de forma explicita si se invocan, nunca rellenarlos con un
valor plausible. Si un calculo los necesita, es que ese calculo no puede
hacerse aun.»

Antes de este modulo la regla no podia cumplirse, porque ningun modulo leia los
ficheros de datos: los nueve parametros identificados del compresor, la
geometria de las placas y la reconstruccion de la bateria estaban escritos en
`data/` y no entraban en el modelo, que corria con los valores por defecto de
los dataclass. Un valor por defecto es exactamente el «valor plausible» que la
regla prohibe, con el agravante de que no se ve.

De ahi el diseno de `DataFile`: el acceso normal es `require()`, que falla si el
dato es `null` o no existe. Obtener un `null` sin fallar exige pedirlo
expresamente con `optional()`, que es una declaracion de intencion visible en el
codigo que lo hace.

SUSTITUCIONES DECLARADAS (28/09/2026)
-------------------------------------
La incertidumbre (§6.11), la comparacion entre fluidos (§6.8.3) y las
sensibilidades necesitan cambiar datos sin editar los ficheros. `sustituciones()`
lo hace con un contexto: dentro de el, `require` y `optional` devuelven el valor
sustituido, tambien dentro de los sub-diccionarios que devuelven, y
`sustituciones_activas()` las enumera para la procedencia. Cada ruta debe existir
en su fichero —una errata no puede pasar por una sustitucion que no hace nada— y
la que rellena un dato `null` queda marcada como tal: es inyectar un dato que no
existe, y un resultado que lo use no es un resultado soportado.
"""
from __future__ import annotations

import copy
import os
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import yaml

from .geometry import (CompressorGeometry, FinnedCoilGeometry,
                       PlateGeometry)


class MissingData(RuntimeError):
    """Se ha invocado un dato que todavia no existe.

    No es un fallo del modelo: es el modelo negandose a inventar. El mensaje
    identifica el fichero, la ruta del dato y, cuando se conoce, el apartado
    del capitulo que lo declara pendiente.
    """


@lru_cache(maxsize=4)
def _data_dir_cached(env: str | None) -> Path:
    return Path(env) if env else Path(__file__).resolve().parents[2] / "data"


def data_dir() -> Path:
    """Directorio de ficheros de datos.

    Se puede redirigir con la variable de entorno `AMONIATERMIA_DATA`, lo que
    permite a las campanas de sensibilidad del apartado 6.11 correr contra un
    juego de datos alternativo sin tocar el arbol de trabajo.
    """
    return _data_dir_cached(os.environ.get("AMONIATERMIA_DATA"))


_UNSET = object()


@dataclass(frozen=True)
class DataFile:
    """Un fichero de datos de componente, con acceso que falla ante los `null`."""

    name: str
    path: Path
    raw: dict

    # ---------------- Acceso ----------------
    def require(self, dotted: str, why: str = "") -> Any:
        """Devuelve el dato, o falla si no existe o es `null`.

        Es el acceso por defecto. Todo calculo que necesite un dato debe pedirlo
        asi, de modo que la ausencia detenga el calculo en lugar de propagarse.
        """
        val = self._walk(dotted)
        if val is _UNSET:
            raise MissingData(
                f"{self.path.name}: la ruta '{dotted}' no existe en el fichero."
                + (f" {why}" if why else ""))
        if val is None:
            raise MissingData(
                f"{self.path.name}: '{dotted}' es un dato PENDIENTE (null). "
                "No puede rellenarse con un valor plausible (CLAUDE.md, "
                "«Datos pendientes»)."
                + (f" {why}" if why else ""))
        return val

    def optional(self, dotted: str, default: Any = None) -> Any:
        """Devuelve el dato, o `default` si no existe o es `null`.

        Uso deliberadamente incomodo: emplearlo es afirmar que el calculo tiene
        sentido sin ese dato. Si no lo tiene, va `require()`.
        """
        val = self._walk(dotted)
        return default if val is _UNSET or val is None else val

    def is_pending(self, dotted: str) -> bool:
        """Cierto si el dato existe en el fichero pero esta declarado `null`."""
        return self._walk(dotted) is None

    def pending(self) -> list:
        """Rutas de todos los datos declarados `null` en el fichero.

        Sirve para que una campana declare por adelantado que datos le faltan,
        en lugar de descubrirlo al fallar a mitad de calculo.
        """
        out: list = []
        _collect_none(self.raw, (), out)
        return sorted(out)

    def _walk(self, dotted: str) -> Any:
        if _ACTIVAS:
            propias = _vigentes().get(self.name)
            if propias:
                return _walk_con_sustituciones(self.raw, dotted, propias)
        return _walk_raw(self.raw, dotted)

    def __repr__(self) -> str:
        return f"DataFile({self.name!r}, {len(self.pending())} pendientes)"


def _walk_raw(raw: dict, dotted: str) -> Any:
    node: Any = raw
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _UNSET
        node = node[part]
    return node


def _walk_con_sustituciones(raw: dict, dotted: str, propias: dict) -> Any:
    if dotted in propias:
        return propias[dotted]
    node = _walk_raw(raw, dotted)
    debajo = {r[len(dotted) + 1:]: v for r, v in propias.items()
              if r.startswith(dotted + ".")}
    if debajo and isinstance(node, dict):
        node = copy.deepcopy(node)
        for ruta, v in debajo.items():
            *padres, hoja = ruta.split(".")
            d = node
            for p in padres:
                d = d[p]
            d[hoja] = v
    return node


# ---------------------------------------------------------------------------
# Sustituciones declaradas
# ---------------------------------------------------------------------------

class SustitucionInvalida(ValueError):
    """La ruta de una sustitucion no existe en su fichero de datos."""


#: Pila de sustituciones activas: cada elemento es {fichero: {ruta: valor}}.
_ACTIVAS: list = []
#: Registro, para la procedencia: {"fichero:ruta": {valor, original, ...}}.
_REGISTRO: list = []


def _vigentes() -> dict:
    """Las sustituciones activas fundidas; la mas interna prevalece."""
    out: dict = {}
    for capa in _ACTIVAS:
        for fichero, rutas in capa.items():
            out.setdefault(fichero, {}).update(rutas)
    return out


def _normalizar(mapa: dict) -> tuple:
    capa, registro = {}, {}
    for clave, valor in (mapa or {}).items():
        if ":" not in clave:
            raise SustitucionInvalida(
                f"'{clave}': una sustitucion se escribe 'fichero:ruta.punteada'.")
        fichero, ruta = clave.split(":", 1)
        raw = load(fichero).raw          # falla si el fichero no existe
        original = _walk_raw(raw, ruta)
        if original is _UNSET:
            raise SustitucionInvalida(
                f"{fichero}.yaml: la ruta '{ruta}' no existe. Una sustitucion "
                "sobre una ruta inexistente no haria nada y no se admite.")
        capa.setdefault(fichero, {})[ruta] = valor
        registro[clave] = {"valor": valor, "original": original,
                           "rellena_un_dato_que_no_existe": original is None}
    return capa, registro


@contextmanager
def sustituciones(mapa: dict | None) -> Iterator[dict]:
    """Sustituye datos mientras dure el contexto.

        with D.sustituciones({"compresor_bock_f2:transmision.eta_motor": 0.88}):
            circ, _ = campaign.build_circuit()
            s = circ.solve(...)

    Se pueden anidar; la mas interna prevalece. Los componentes leen buena parte
    de sus datos al construirse, de modo que el contexto debe envolver la
    CONSTRUCCION y la resolucion. `campaign.build_circuit(sustituciones=...)` y
    `Circuit.solve` lo hacen por si mismos.
    """
    capa, registro = _normalizar(mapa)
    _ACTIVAS.append(capa)
    _REGISTRO.append(registro)
    try:
        yield registro
    finally:
        _ACTIVAS.pop()
        _REGISTRO.pop()


def sustituciones_activas() -> dict:
    """Las sustituciones vigentes, para adjuntarlas a la procedencia."""
    out: dict = {}
    for r in _REGISTRO:
        out.update(r)
    return copy.deepcopy(out)


def _collect_none(node: Any, prefix: tuple, out: list) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if v is None:
                out.append(".".join(prefix + (str(k),)))
            else:
                _collect_none(v, prefix + (str(k),), out)


@lru_cache(maxsize=32)
def _parse(path_str: str, mtime: float) -> dict:
    """Analisis del YAML, memorizado por ruta y fecha de modificacion.

    Sin esto, `load()` analiza el fichero en CADA llamada. Mientras los datos se
    leian solo al construir los componentes daba igual; desde que una
    correlacion anclada consulta su coeficiente —y por tanto se invoca dentro
    del lazo por celda— pasa a ser un analisis de YAML por celda y por
    iteracion, del orden de 2000 por `solve()`. Es el mismo error que el
    ap. 9.12.4 persigue con `PropsSI`, cambiando de biblioteca: lo caro no es
    el dato, es volver a leerlo.

    La clave incluye la FECHA DE MODIFICACION para que editar un fichero de
    datos surta efecto sin reiniciar, y la ruta completa para que la redireccion
    por `AMONIATERMIA_DATA` siga funcionando.
    """
    return yaml.safe_load(Path(path_str).read_text(encoding="utf-8")) or {}


def load(name: str) -> DataFile:
    """Carga `data/<name>.yaml`. El analisis esta memorizado; ver `_parse`."""
    path = data_dir() / f"{name}.yaml"
    if not path.is_file():
        avail = sorted(p.stem for p in data_dir().glob("*.yaml"))
        raise FileNotFoundError(
            f"No existe {path}. Disponibles: {avail}. "
            "El directorio se redirige con AMONIATERMIA_DATA.")
    return DataFile(name=name, path=path,
                    raw=_parse(str(path), path.stat().st_mtime))


def available() -> list:
    return sorted(p.stem for p in data_dir().glob("*.yaml"))


# ---------------------------------------------------------------------------
# Constructores
# ---------------------------------------------------------------------------

def compressor_geometry(df: DataFile | None = None,
                        rpm: float | None = None) -> CompressorGeometry:
    """`CompressorGeometry` del Bock F2 NH3 (§9.5.3).

    `r_v` NO vive aqui: el §9.5.3 lo identifica junto al resto, de modo que
    pertenece a `CompressorParams`.
    """
    df = df or load("compresor_bock_f2")
    return CompressorGeometry(
        V_swept=df.require("geometria.volumen_barrido_m3_rev"),
        n_rpm=rpm if rpm is not None else df.require("operacion.velocidad_nominal_rpm"),
    )


def compressor_params(df: DataFile | None = None,
                      variant: str = "reidentificacion"):
    """Parametros identificados del compresor Bock F2 NH3.

    `variant`:

    - `"reidentificacion"` (POR DEFECTO): el juego del 24/09/2026, reidentificado
      con el compresor corregido (bloque `reidentificacion_2026_09_24`). Misma
      estructura de nueve parametros, mismos 46 puntos y misma funcion objetivo
      (w3 = 16 en T_dis en la ec. 9-10, 4 sobre el residuo). Decision del autor del 24/09/2026.
    - `"reidentificacion_2026_09_16"`: el juego de la tabla 10.8 de la v30,
      identificado con el compresor que caia en la meseta de max(T1, T_su). Se
      conserva para reproducir las cifras publicadas.
    - `"original"`: los valores publicados en el §9.5.3. Se conservan para
      poder reproducir los resultados del capitulo.

    DECISION DEL AUTOR, 16/09/2026. El capitulo manda sobre el codigo, de modo
    que un cambio como este no puede hacerse en silencio: queda fechado aqui, en
    data/compresor_bock_f2.yaml y en docs/historico/PLAN_PUESTA_EN_MARCHA.md §6, y la
    reescritura del capitulo se abordara con un informe propio cuando el modelo
    de simulacion este completo.

    El motivo es que los valores de la antigua tabla 10.4, evaluados sobre los 46
    puntos, exceden las tres tolerancias que el propio §9.5.3 declara, y el
    error en temperatura de descarga es un sesgo sistematico de +14 K y no
    dispersion. La diferencia es material para H3: en el equilibrio de M-2 la
    antigua tabla 10.4 predice 141 C y la reidentificacion 125.5 C, frente a los 122.2 C
    que el fabricante publica a T0=2 / Tc=45.

    Los rendimientos del motor externo y de la transmision se cargan del
    fichero. Son valores ADOPTADOS, no medidos, y estan marcados como tales.
    """
    from .components.compressor import CompressorParams

    df = df or load("compresor_bock_f2")
    if variant == "original":   # referencia del capitulo
        p, keys = "parametros_identificados.", {
            "AU_su_n": "AU_su_n_W_K", "AU_ex_n": "AU_ex_n_W_K",
            "AU_amb": "AU_amb_W_K", "A_leak": "A_leak_m2", "C": "C",
            "alpha_l": "alpha", "W_loss0": "W_loss_0_W", "r_v": "r_v",
            "eta_ic": "eta_ic"}
    elif variant in ("reidentificacion", "reidentificacion_2026_09_16"):
        # Los compresores del cap. 13 declaran su bloque vigente en
        # `identificacion_vigente`; el F2 conserva el nombre historico.
        bloque = ((df.optional("identificacion_vigente") or "reidentificacion_2026_09_24")
                  if variant == "reidentificacion" else variant)
        p, keys = bloque + ".", {
            "AU_su_n": "AU_su_n_W_K", "AU_ex_n": "AU_ex_n_W_K",
            "AU_amb": "AU_amb_W_K", "A_leak": "A_leak_m2", "C": "C",
            "alpha_l": "alpha", "W_loss0": "W_loss_0_W", "r_v": "r_v",
            "eta_ic": "eta_ic"}
    else:
        raise ValueError(
            "variant debe ser 'reidentificacion', 'reidentificacion_2026_09_16' "
            f"o 'original', no {variant!r}")

    return CompressorParams(
        **{k: df.require(p + v) for k, v in keys.items()},
        n_reexp=df.require("parametros_identificados.n_politropico"),
        eta_motor=df.optional("transmision.eta_motor"),
        eta_transm=df.optional("transmision.eta_transmision"),
    )


def compressor_model(df: DataFile | None = None) -> str:
    """Modelo del compresor que declara su fichero: `en12900` o `semiempirico`."""
    df = df or load("compresor_bock_f2")
    return df.optional("modelo_compresor") or "semiempirico"


def compressor(df: DataFile | None = None, fluid=None, modelo: str | None = None,
               rpm: float | None = None):
    """El compresor del fichero con el modelo que declara (`modelo_compresor`), o con
    `modelo` ("en12900" o "semiempirico") si se pide otro. `fluid`: el estado del lazo."""
    from .props import Fluid

    df = df or load("compresor_bock_f2")
    modelo = modelo or compressor_model(df)
    f = fluid or Fluid(df.require("fluido"))
    if modelo == "en12900":
        return compressor_en12900(df, fluid=f, rpm=rpm)
    if modelo == "semiempirico":
        from .components.compressor import SemiEmpiricalCompressor
        return SemiEmpiricalCompressor(f, compressor_geometry(df, rpm=rpm), compressor_params(df))
    raise ValueError(f"modelo de compresor desconocido: {modelo!r}")


def compressor_en12900_points(df: DataFile | None = None, fluid=None) -> list:
    """Puntos de los que se ajustan los polinomios de UNE-EN 12900, en SI.

    `modelo_en12900.fuente`: `vap` (`compressor_vap_points` sobre `fichero_puntos`, bloques
    `bloques`) o `catalogo_fichero` (`compressor_catalog_fichero`). Solo los del
    recalentamiento de referencia."""
    from .props import Fluid

    df = df or load("compresor_bock_f2")
    m = df.require("modelo_en12900")
    f = fluid or Fluid(df.require("fluido"))
    sh = float(m["recalentamiento_ref_K"])
    if m["fuente"] == "vap":
        bloques = set(m.get("bloques") or [])
        pts = [p for p in compressor_vap_points(fluid=f, fichero=m["fichero_puntos"])
               if not bloques or p["bloque"] in bloques]
    elif m["fuente"] == "catalogo_fichero":
        pts = compressor_catalog_fichero(m["fichero_puntos"], f)
    else:
        raise ValueError(f"fuente desconocida: {m['fuente']!r}")
    return [p for p in pts if abs(p.get("recalentamiento", sh) - sh) < 1e-9]


def _polinomios_en12900(nombre: str) -> tuple:
    """Polinomios por velocidad del fichero `nombre`, ajustados a sus puntos. Se cachean por
    fichero: no dependen de las sustituciones (los factores de ajuste se aplican aparte)."""
    clave = (nombre, str(data_dir()))
    if clave not in _CACHE_POLINOMIOS:
        from .components.compressor_en12900 import PolinomiosVelocidad, ajusta_polinomio

        df = load(nombre)
        pts = compressor_en12900_points(df)
        con_descarga = df.require("modelo_en12900.descarga") == "polinomio"
        out = []
        for rpm in sorted({p["rpm"] for p in pts}):
            sel = [p for p in pts if p["rpm"] == rpm]
            t0 = [p["T0"] - 273.15 for p in sel]
            tc = [p["Tc"] - 273.15 for p in sel]
            if con_descarga and any("T_dis" not in p for p in sel):
                raise MissingData(f"{nombre}: falta la descarga en puntos de {rpm:.0f} rpm "
                                  "y el modelo declara `descarga: polinomio`.")
            out.append(PolinomiosVelocidad(
                rpm=rpm, n_puntos=len(sel),
                m_dot=ajusta_polinomio(t0, tc, [p["m_dot"] for p in sel]),
                W_eje=ajusta_polinomio(t0, tc, [p["W_shaft"] for p in sel]),
                T_dis_C=(ajusta_polinomio(t0, tc, [p["T_dis"] - 273.15 for p in sel])
                         if con_descarga else None)))
        _CACHE_POLINOMIOS[clave] = tuple(out)
    return _CACHE_POLINOMIOS[clave]


_CACHE_POLINOMIOS: dict = {}


def compressor_en12900(df: DataFile | None = None, fluid=None, rpm: float | None = None):
    """Compresor por polinomios de UNE-EN 12900 (decisión del autor, 15/10/2026).

    Ajusta los polinomios a los puntos del fichero (una vez por fichero) y aplica los factores
    de `modelo_en12900.ajuste`, que son los de la incertidumbre del compresor y pueden
    sustituirse (`data.sustituciones`). `fluid`: el estado del lazo (HEOS)."""
    from .components.compressor_en12900 import EN12900Compressor
    from .props import Fluid

    df = df or load("compresor_bock_f2")
    nombre = df.path.stem
    m = df.require("modelo_en12900")
    f = fluid or Fluid(df.require("fluido"))
    descarga_ref = None
    if m["descarga"] == "semiempirico":
        from .components.compressor import SemiEmpiricalCompressor

        semi = SemiEmpiricalCompressor(Fluid(df.require("fluido")), compressor_geometry(df),
                                       compressor_params(df))
        descarga_ref = lambda P0, T_su, Pk: semi.solve(P0, T_su, Pk).T_dis   # noqa: E731
    elif m["descarga"] != "polinomio":
        raise ValueError(f"descarga desconocida: {m['descarga']!r}")
    pol = _polinomios_en12900(nombre)
    geom = compressor_geometry(df, rpm=rpm)
    return EN12900Compressor(
        f, geom, list(pol), recalentamiento_ref_K=float(m["recalentamiento_ref_K"]),
        eta_motor=df.optional("transmision.eta_motor"),
        eta_transm=df.optional("transmision.eta_transmision"),
        grado_velocidad=int(m["grado_velocidad"]), ajuste=m.get("ajuste"),
        descarga_ref=descarga_ref,
        V_swept_datos=float(m["volumen_barrido_datos_m3_rev"]),
        procedencia={"modelo": "en12900", "fichero_puntos": m["fichero_puntos"],
                     "velocidades_rpm": [p.rpm for p in pol],
                     "puntos_por_velocidad": [p.n_puntos for p in pol],
                     "descarga": m["descarga"]})


def compressor_catalog(restricted: bool = False, superheat: float = 1.0,
                       subcooling: float = 0.0, fluid=None) -> list:
    """Los 46 puntos de prestaciones publicados por el fabricante (§9.5.3).

    Lee `data/compresor_bock_f2_catalogo.csv`, transcripcion en texto plano de
    `COMPRESOR_BOCK_F2_NH3.xlsx`, y devuelve los puntos en SI ESTRICTO con el
    caudal masico deducido de la capacidad frigorifica.

    El catalogo publica capacidad, potencia AL EJE y temperatura de descarga,
    no caudal. El caudal se deduce del convenio de ensayo declarado en la hoja
    LEAME del fichero de origen —recalentamiento de aspiracion 1 K,
    subenfriamiento nulo—, que es el mismo que declara el §9.5.3:

        m = Q0 / (h1 - h4) ,  h1 = h(P0, Tsat(T0) + 1 K) ,  h4 = h_l(Tc)

    `restricted=True` devuelve los 36 puntos del dominio restringido (Tc >= 25)
    que el fichero de origen marca en su segunda hoja.

    Cada punto lleva `W_shaft`, no `W_el`: el compresor es abierto y lo que el
    fabricante publica es potencia al eje. Confundirlas al identificar
    trasladaria el rendimiento del motor a los parametros de la maquina.
    """
    import csv

    from .props import Fluid

    path = data_dir() / "compresor_bock_f2_catalogo.csv"
    if not path.is_file():
        raise MissingData(
            f"No existe {path}. Sin los puntos de catalogo la identificacion "
            "del §9.5.3 no es reproducible, que es lo que prometen el §6.12 y "
            "el anexo E.")
    f = fluid or Fluid("Ammonia")
    out = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if restricted and int(row["dominio_restringido"]) != 1:
                continue
            T0 = float(row["T0_C"]) + 273.15
            Tc = float(row["Tc_C"]) + 273.15
            P0, Pk = f.Psat(T0), f.Psat(Tc)
            T_su = T0 + superheat
            f.update_PT(P0, T_su)
            h1 = f.h
            f.update_QT(0.0, Tc - subcooling)
            h4 = f.h
            Q0 = float(row["Q0_W"])
            out.append({
                "T0": T0, "Tc": Tc, "P_ad": P0, "P_ex": Pk, "T_su": T_su,
                "Q0": Q0, "m_dot": Q0 / (h1 - h4),
                "W_shaft": float(row["W_shaft_kW"]) * 1.0e3,
                "T_dis": float(row["T_dis_C"]) + 273.15,
                "restringido": bool(int(row["dominio_restringido"])),
            })
    return out


def compressor_catalog_fichero(fichero: str, fluid) -> list:
    """Puntos del software de seleccion de un compresor del cap. 13
    (`data/<fichero>_catalogo.csv`, formato de `docs/historico/PETICION_DATOS_COMPRESORES.md`).

    Columnas: T0_C, Tc_C, recalentamiento_K, subenfriamiento_K, rpm, Q0_W, W_el_W,
    m_dot_kg_s, T_descarga_C, zona, observaciones. Las filas sin Q0 o con zona
    `fuera` no existen y no se devuelven.

    HERMETICO Y SEMIHERMETICO. El software da potencia ELECTRICA, y las perdidas
    del motor calientan la aspiracion: es la formulacion original de Winandy et
    al. (2002), en la que las perdidas electromecanicas forman parte de alpha y
    W_loss0. El punto se devuelve con `W_shaft` = potencia electrica, y el fichero
    del compresor declara eta_motor = eta_transmision = 1 con ese significado.
    La descarga es opcional: el R-32 no la tiene (decision 8 del 05/10/2026) y se
    identifica sin peso en ella."""
    import csv

    path = data_dir() / f"{fichero}_catalogo.csv"
    if not path.is_file():
        raise MissingData(f"No existe {path}: son los puntos que genera el autor "
                          "(docs/historico/PETICION_DATOS_COMPRESORES.md).")
    f = fluid
    out = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            # Solo se descarta lo que no tiene resultado. `zona` es una marca de la
            # envolvente del fabricante (en el R-290, descarga < T_k + 20 K), no de
            # validez de la prestacion calculada (decision 7 del 05/10/2026).
            if not row.get("Q0_W", "").strip() or not row.get("W_el_W", "").strip():
                continue
            T0 = float(row["T0_C"]) + 273.15
            Tc = float(row["Tc_C"]) + 273.15
            sh, sc = float(row["recalentamiento_K"]), float(row["subenfriamiento_K"])
            P0, Pk = f.Psat(T0), f.Psat(Tc)
            f.update_PT(P0, T0 + sh)
            h1 = f.h
            f.update_QT(0.0, Tc - sc) if sc == 0 else f.update_PT(Pk, Tc - sc)
            h4 = f.h
            Q0 = float(row["Q0_W"])
            # El caudal se deduce de la capacidad, como en el F2: el software lo
            # redondea a milesimas de kg/s (±1.5 % a 0.036 kg/s). El del fichero
            # se conserva como comprobacion.
            m = Q0 / (h1 - h4)
            pt = {"T0": T0, "Tc": Tc, "P_ad": P0, "P_ex": Pk, "T_su": T0 + sh,
                  "recalentamiento": sh, "Q0": Q0, "m_dot": m,
                  "m_dot_fichero": (float(row["m_dot_kg_s"]) if row.get("m_dot_kg_s", "").strip()
                                    else None),
                  "W_shaft": float(row["W_el_W"]), "rpm": float(row["rpm"])}
            if row.get("T_descarga_C", "").strip():
                pt["T_dis"] = float(row["T_descarga_C"]) + 273.15
            out.append(pt)
    return out


def compressor_vap_points(fluid=None, incluir_sospechosos: bool = False,
                          fichero: str = "compresor_bock_f2_vap.csv") -> list:
    """Puntos generados por el autor con el software VAP de Bock (29/09/2026).

    `data/compresor_bock_f2_vap.csv`: 39 puntos fuera del catalogo de 46 —T0 de
    -20 a 15 °C, recalentamiento de 1 a 10 K, 960 y 1200 rpm— CON temperatura de
    descarga. Son VALIDACION independiente del compresor fuera de su dominio de
    identificacion: no entran en la identificacion.

    Capacidad y potencia al eje estan en kW en el fichero. El caudal del fichero
    esta redondeado a milesimas de kg/s y se deduce, como en el catalogo, de la
    capacidad: m = Q0 / (h(P0, T0 + recalentamiento) - h(Pk, Tk - subenfriamiento)),
    con h_l(Tk) si el subenfriamiento es nulo. Una fila sin resultado (celdas
    vacias) es un punto que no existe y no se devuelve. Las filas marcadas como
    sospechosas en `observaciones` se excluyen salvo que se pidan.

    `fichero`: otro CSV con el mismo formato. `compresor_bock_f2_vap_envolvente.csv`
    (15/10/2026) barre en rejilla de 5 K la zona sin limites (bloque E, 49 puntos) y la
    de refrigeracion suplementaria (bloque F, 8) del diagrama del fabricante.
    """
    import csv

    from .props import Fluid

    path = data_dir() / fichero
    f = fluid or Fluid("Ammonia")
    out = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row["Q0_kW"].strip():
                continue
            sospechoso = "sospechoso" in row.get("observaciones", "")
            if sospechoso and not incluir_sospechosos:
                continue
            T0 = float(row["T0_C"]) + 273.15
            Tc = float(row["Tc_C"]) + 273.15
            sh, sc = float(row["recalentamiento_K"]), float(row["subenfriamiento_K"])
            P0, Pk = f.Psat(T0), f.Psat(Tc)
            f.update_PT(P0, T0 + sh)
            h1 = f.h
            f.update_QT(0.0, Tc - sc) if sc == 0 else f.update_PT(Pk, Tc - sc)
            h4 = f.h
            Q0 = float(row["Q0_kW"]) * 1.0e3
            out.append({"bloque": row["bloque"], "T0": T0, "Tc": Tc, "P_ad": P0,
                        "P_ex": Pk, "T_su": T0 + sh, "recalentamiento": sh,
                        "rpm": float(row["rpm"]), "Q0": Q0, "m_dot": Q0 / (h1 - h4),
                        "m_dot_fichero": float(row["m_dot_kg_s"]),
                        "W_shaft": float(row["W_eje_kW"]) * 1.0e3,
                        "T_dis": float(row["T_descarga_C"]) + 273.15,
                        "zona_esperada": row["zona_esperada"],
                        "sospechoso": sospechoso})
    return out


def compressor_extended_points(fluid=None) -> list:
    """Conjunto AMPLIADO del ensayo de reidentificacion del 29/09/2026, que el
    autor DESCARTO (`docs/DECISIONES_2026_09_29.md`): los 46 puntos del catalogo
    y los puntos VAP a la velocidad nominal dentro de la envolvente del
    fabricante. Se conserva para reproducir el ensayo; el compresor sigue
    identificado sobre los 46 del catalogo. Quedan fuera los puntos VAP marcados
    `fuera` en el diagrama de limites, el de control del bloque D (repite uno
    del catalogo) y los de 960 y 1200 rpm."""
    pts = [dict(p, fuente="catalogo") for p in compressor_catalog(fluid=fluid)]
    for p in compressor_vap_points(fluid=fluid):
        if (p["rpm"] == 1450.0 and p["bloque"] in ("A", "B")
                and p["zona_esperada"] != "fuera"):
            pts.append(dict(p, fuente="vap"))
    return pts


def plate_geometry(unit: str, df: DataFile | None = None,
                   **overrides) -> PlateGeometry:
    """`PlateGeometry` de una de las unidades de `placas_alfanova.yaml`.

    `unit` es "condensador_climatizacion" o "desrecalentador_acs".

    Falla con `MissingData` mientras falten datos: hoy ninguna de las dos
    unidades tiene declarado el angulo de corrugacion, y el condensador tampoco
    el paso entre placas ni el factor de alargamiento (D12). Es el
    comportamiento correcto: sin ellos el submodelo de placas no cierra
    (§9.6.4), y un valor por defecto lo ocultaria.

    `overrides` permite inyectar un valor a proposito —para una campana de
    sensibilidad, o para explorar antes de tener el dato— dejando constancia en
    el codigo que lo hace de que ese valor no procede de los datos.
    """
    df = df or load("placas_alfanova")
    base = f"unidades.{unit}.geometria."
    if df._walk(f"unidades.{unit}") is _UNSET:
        raise MissingData(
            f"{df.path.name}: no existe la unidad '{unit}'. "
            f"Disponibles: {sorted(df.raw.get('unidades', {}))}")

    def pick(key, dotted, why=""):
        if key in overrides:
            return overrides[key]
        return df.require(base + dotted, why)

    return PlateGeometry(
        n_plates=pick("n_plates", "n_placas"),
        b=pick("b", "paso_entre_placas_m",
               "Paso entre placas: §9.6.2 solo lo declara para el AlfaNova 16."),
        L_w=pick("L_w", "placa_ancho_m"),
        L_p=pick("L_p", "placa_largo_m"),
        beta_c=pick("beta_c", "angulo_corrugacion_rad",
                    "Angulo de corrugacion: no publicado por el fabricante. "
                    "De el dependen C y m del regimen monofasico (antigua tabla 10.7)."),
        phi=pick("phi", "factor_alargamiento",
                 "Factor de alargamiento: §9.6.2 advierte de que rara vez se "
                 "publica y de que su estimacion entra en la sensibilidad "
                 "del ap. 6.11."),
        t_p=pick("t_p", "espesor_placa_m"),
        # Ensuciamiento: la ficha del 27-30H lo declara (2.7e-4 m2 K/W) y es
        # parte del U de catalogo, no un anadido del modelador. Se lee con
        # `optional` porque la del 16-10H no se tiene y un evaporador limpio a
        # cero es el valor correcto, no un dato inventado.
        R_f=overrides.get("R_f", df.optional(
            base + "resistencia_ensuciamiento_m2K_W", 0.0)),
        # El convenio de area NO es un dato del fabricante sino una decision de
        # modelado (D13), de ahi que no se lea del fichero: se toma el valor por
        # defecto de `PlateGeometry` salvo que se pida otro expresamente.
        area_convention=overrides.get("area_convention", "developed"),
        provenance={"fichero": df.path.name, "unidad": unit,
                    "inyectados": sorted(overrides)},
    )


def refrigerant_lines(df: DataFile | None = None) -> dict:
    """Geometria de las lineas de refrigerante {par: LineGeometry} (C11-1).

    Valores ADOPTADOS (decision 3b del autor, 29/09/2026), no de diseno: ver la
    cabecera de `lineas_refrigerante.yaml`. La clave es el par de extremos en
    orden alfabetico unido por «--»; el compresor aporta dos extremos,
    `descarga` y `aspiracion`."""
    from .components.line import LineGeometry

    df = df or load("lineas_refrigerante")
    rug = df.require("rugosidad_m")
    out = {}
    for par in df.require("lineas"):
        base = f"lineas.{par}."
        out[par] = LineGeometry(nombre=par, longitud=df.require(base + "longitud_m"),
                                D_i=df.require(base + "diametro_interior_m"),
                                rugosidad=rug)
    return out


def caudal_climatizacion(df: DataFile | None = None) -> float:
    """Caudal nominal del circuito de climatizacion [kg/s], el mismo en M-1 a
    M-4 (decision del autor, 01/10/2026; `circuitos_agua.yaml`)."""
    df = df or load("circuitos_agua")
    return float(df.require("climatizacion.caudal_kg_s"))


def caudal_aire_m3_h(df: DataFile | None = None) -> float:
    """Caudal en VOLUMEN del ventilador de la bateria [m3/h], el mismo en todos
    los modos (ficha; decision del autor, 01/10/2026). El caudal masico lo
    deduce `Boundary` con la densidad del aire de cada condicion."""
    df = df or load("bateria_frimetal_cbn21")
    return float(df.require("ventilador.caudal_m3_h"))


def air_coil(df: DataFile | None = None) -> DataFile:
    """Datos de la bateria Frimetal CBN-21 ESPECIAL (§9.7).

    Devuelve el `DataFile` en bruto: la clase de geometria de serpentin aleteado
    vive en `geometry.FinnedCoilGeometry`, que consume estos mismos datos.

    El consumo de ventilador dejo de ser un pendiente el 17/09/2026: se adopta
    el dato de catalogo de la serie CBN, 780 W a alta velocidad con el motor en
    triangulo, en lugar de la horquilla 296-720 W que dejaba abierta el §9.7.7
    y que impedia sostener la comparacion de H1.
    """
    return df or load("bateria_frimetal_cbn21")


def air_coil_geometry(df: DataFile | None = None,
                      **overrides) -> FinnedCoilGeometry:
    """`FinnedCoilGeometry` de la bateria Frimetal, leida del fichero de datos.

    La reconstruccion del §9.7.1 esta verificada contra la ficha (§9.7.1),
    de modo que esta geometria no lleva ningun dato pendiente. `overrides` se
    conserva por simetria con `plate_geometry` y para la sensibilidad del
    ap. 6.11.
    """
    df = df or air_coil()
    g = df.require("geometria")

    def pick(key, dotted):
        return overrides[key] if key in overrides else g[dotted]

    return FinnedCoilGeometry(
        S_t=pick("S_t", "paso_transversal_m"),
        S_l=pick("S_l", "paso_longitudinal_m"),
        L=pick("L", "longitud_bateria_m"),
        n_tubes_row=pick("n_tubes_row", "tubos_por_rango"),
        n_rows=pick("n_rows", "n_rangos"),
        n_circuits=pick("n_circuits", "n_circuitos"),
        fin_pitch=pick("fin_pitch", "paso_aleta_m"),
        fin_thickness=pick("fin_thickness", "espesor_aleta_m"),
        d_o=pick("d_o", "diametro_exterior_m"),
        d_i=pick("d_i", "diametro_interior_m"),
        k_tube=overrides.get("k_tube", df.require("conductividad_tubo_W_mK")),
        k_fin=overrides.get("k_fin", df.require("conductividad_aleta_W_mK")))


def pending_report() -> dict:
    """Todos los datos pendientes, por fichero.

    Conviene invocarlo al comienzo de una campana: declara por adelantado que
    no se tiene, en lugar de descubrirlo al fallar a mitad de calculo.
    """
    return {n: load(n).pending() for n in available()}
