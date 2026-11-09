"""Campanas de simulacion con procedencia adjunta. Apartados 6.8 y 6.12.

QUE APORTA SOBRE `Circuit.sweep`
--------------------------------
El barrido con continuacion ya existe en `circuit.sweep`. Lo que falta para que
una campana sea utilizable en los capitulos 11 a 13 es lo de alrededor:

- La PROCEDENCIA, con los cinco elementos del ap. 9.12.5, adjunta al resultado
  y no reconstruida despues.
- Los casos NO CONVERGIDOS conservados y contados. El ap. 6.12 exige que «se
  registren y se reporten, en lugar de ser descartados silenciosamente», y el
  ap. 6.6.6 que se excluyan del conjunto de resultados «con indicacion
  expresa»: las dos cosas a la vez significan conservarlos marcados, que es lo
  que `CampaignResult.rows` hace y `validos()` filtra.
- El BACKEND declarado, y su error cuantificado si es tabular.

LA CONDICION DEL BACKEND TABULAR
--------------------------------
El ap. 6.6.4 no dice «usese el backend tabular»: dice que «su empleo queda
condicionado a que dicha desviacion resulte inferior al umbral declarado». Esta
campana lo hace cumplir: pedir un backend tabular SIN umbral es un error, y con
umbral se ejecuta la verificacion cruzada, se comprueba y el informe viaja en
la procedencia. No se puede usar el atajo sin dejar constancia de que se
comprobo.

QUE SE SABE YA DEL BACKEND TABULAR (medido el 21/09/2026)
---------------------------------------------------------
- En los pares PT, PH, PQ y PS la desviacion maxima frente a HEOS es 3.6e-4, y
  en PH —el del camino caliente, con mas de un millon de llamadas por punto—
  es 4.4e-6.
- Los pares DH y DS NO ESTAN SOPORTADOS por el backend tabular de CoolProp, y
  el compresor los necesita para la compresion isocora de las ec. 9-4 y 9-5.
- La salida es por tanto MIXTA: HEOS en el compresor y tabular en los
  intercambiadores. Da 5.4 veces sobre un punto completo con una diferencia de
  8e-8 en el EER.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import indicators as I
from .circuit import MODES, Circuit
from .props import (Fluid, PropertyProvenance, backend_deviation_report,
                    backend_is_usable)


class BackendSinUmbral(RuntimeError):
    """Se ha pedido un backend tabular sin declarar el umbral del ap. 6.6.4."""


class BackendFueraDeUmbral(RuntimeError):
    """El backend tabular no cumple la condicion del ap. 6.6.4."""


@dataclass
class CampaignResult:
    """Resultado de una campana, con todo lo que el cap. 11 necesita adjuntar."""
    mode: str
    rows: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    backend_hx: str = "HEOS"
    backend_report: dict | None = None
    fluido: str = "Ammonia"
    solutions: list = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def n_convergidos(self) -> int:
        return sum(1 for r in self.rows if r["convergido"])

    @property
    def n_validos(self) -> int:
        return sum(1 for r in self.rows if r["valido"])

    @property
    def n_extrapolados(self) -> int:
        return sum(1 for r in self.rows if r["extrapolado"])

    def validos(self) -> list:
        """Las filas utilizables. Los demas casos NO se borran: siguen en
        `rows` con su marca, que es lo que el ap. 6.12 exige."""
        return [r for r in self.rows if r["valido"]]

    def summary(self) -> str:
        L = [f"Campana {self.mode} con {self.fluido}: {self.n} casos, "
             f"{self.n_convergidos} convergidos, {self.n_validos} validos, "
             f"{self.n_extrapolados} con alguna correlacion fuera de rango",
             f"  backend de intercambiadores: {self.backend_hx}"]
        if self.backend_report:
            peor = self.backend_report["peor"]
            L.append(f"  desviacion maxima frente a HEOS: {peor['max']:.1e} "
                     f"en {peor['par']}/{peor['magnitud']} "
                     f"(umbral {self.backend_report['umbral']:.0e})")
        if self.n_validos < self.n:
            L.append("  casos NO validos, conservados y marcados:")
            for r in self.rows:
                if not r["valido"]:
                    L.append(f"    {r['caso']}: residuo {r['residuo']:.1e}"
                             + ("" if r["convergido"] else ", no convergio"))
        return "\n".join(L)

    def write(self, path) -> None:
        """Escribe filas y procedencia. No se separan: un fichero de resultados
        sin su procedencia no cumple el ap. 6.12."""
        p = Path(path)
        p.write_text(json.dumps(
            {"modo": self.mode, "fluido": self.fluido,
             "procedencia": self.provenance,
             "backend_intercambiadores": self.backend_hx,
             "verificacion_backend": self.backend_report,
             "resumen": {"n": self.n, "convergidos": self.n_convergidos,
                         "validos": self.n_validos,
                         "extrapolados": self.n_extrapolados},
             "filas": self.rows}, indent=2, ensure_ascii=False, default=float),
            encoding="utf-8")

    def to_frame(self):
        """Las filas como `pandas.DataFrame`, una columna por magnitud."""
        import pandas as pd
        return pd.DataFrame(self.rows)

    def write_table(self, base) -> tuple:
        """Escribe `<base>.csv` con las filas y `<base>.json` con la procedencia,
        el resumen y las unidades de cada columna. Es el formato del anexo F:
        legible sin el paquete, y sin separar nunca los datos de su procedencia
        (§6.12). Devuelve las dos rutas."""
        base = Path(base)
        csv_path, meta_path = base.with_suffix(".csv"), base.with_suffix(".json")
        self.to_frame().to_csv(csv_path, index=False, float_format="%.10g")
        meta_path.write_text(json.dumps(
            {"modo": self.mode, "fluido": self.fluido,
             "datos": csv_path.name,
             "unidades": {c: UNIDADES.get(c, "-") for c in self.to_frame().columns},
             "resumen": {"n": self.n, "convergidos": self.n_convergidos,
                         "validos": self.n_validos,
                         "admisibles": sum(1 for r in self.rows if r.get("admisible")),
                         "extrapolados": self.n_extrapolados},
             "procedencia": self.provenance,
             "backend_intercambiadores": self.backend_hx,
             "verificacion_backend": self.backend_report},
            indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return csv_path, meta_path


#: Unidades de las columnas de `fila()`. Las temperaturas se dan en °C y las
#: cargas en g: es la FRONTERA del modelo (`units`), y la tabla es para leerla.
UNIDADES = {
    "T_aire_C": "°C", "HR_aire": "-", "m_aire": "kg/s", "T_amb_C": "°C",
    "T_clima_in_C": "°C", "m_clima": "kg/s", "T_acs_in_C": "°C",
    "recalentamiento_consigna_K": "K", "subenfriamiento_consigna_K": "K",
    "T_acs_consigna_C": "°C", "P0": "Pa", "Pk": "Pa", "A_ef": "m2",
    "m_acs": "kg/s", "T_evap_C": "°C", "T_cond_C": "°C", "m_dot": "kg/s",
    "Q_evap": "W", "Q_alta": "W", "Q_clima": "W", "Q_acs": "W",
    "W_shaft": "W", "W_fan": "W", "W_el": "W", "T_dis_C": "°C",
    "recalentamiento_K": "K", "subenfriamiento_K": "K", "residuo": "-",
    "carga_min_g": "g", "carga_max_g": "g", "carga_RS5_limite_g": "g",
    "carga_RS5_fraccion": "-", "margen_no_condensacion_K": "K",
    "EER": "-", "COP": "-", "COP_global": "-", "eta_II": "-",
    "cierre_exergetico": "-",
}


def fila(s, spec, etiqueta=None) -> dict:
    """Un punto resuelto, aplanado a una fila de magnitudes escalares.

    Lleva TODO lo que el §6.8.1 exige conservar con cada punto: contorno,
    consignas, incognitas, potencias, indicadores, banda de carga, envolvente,
    validez, admisibilidad y marca de extrapolacion. Las temperaturas se
    convierten a °C aqui, que es la frontera."""
    from . import units as U
    bc, sp = s.boundary, s.setpoints
    r = {"caso": etiqueta, "modo": s.mode, "convergido": bool(s.converged),
         "valido": bool(s.valid), "admisible": bool(s.admissible),
         "extrapolado": bool(s.extrapolated), "residuo": float(s.max_residual)}
    if bc is not None:
        r.update(T_aire_C=U.K2C(bc.air.T), HR_aire=bc.air.RH, m_aire=bc.m_dot_air,
                 T_amb_C=U.K2C(bc.T_amb))
        if bc.clima is not None:
            r.update(T_clima_in_C=U.K2C(bc.clima.T_in), m_clima=bc.clima.m_dot)
        if bc.acs is not None:
            r.update(T_acs_in_C=U.K2C(bc.acs.T_in))
    if sp is not None:
        r.update(recalentamiento_consigna_K=sp.superheat,
                 subenfriamiento_consigna_K=sp.subcooling)
        if sp.T_acs is not None:
            r["T_acs_consigna_C"] = U.K2C(sp.T_acs)
    r.update({k: float(v) for k, v in s.unknowns.items()})
    r.update(T_evap_C=U.K2C(s.T_evap), T_cond_C=U.K2C(s.T_cond), m_dot=s.m_dot,
             Q_evap=s.Q_evap, Q_alta=s.Q_high, Q_clima=s.Q_clima, Q_acs=s.Q_acs,
             W_shaft=s.W_shaft, W_fan=s.W_fan, T_dis_C=U.K2C(s.T_dis),
             recalentamiento_K=s.superheat, subenfriamiento_K=s.subcooling)
    ch = s.charge or {}
    for k in ("homogeneous", "zivi", "lockhart_martinelli", "rouhani_axelsson"):
        if k in ch:
            r[f"carga_{k}_g"] = U.kg2g(float(ch[k]))
            UNIDADES.setdefault(f"carga_{k}_g", "g")
    if "_min" in ch:
        r.update(carga_min_g=U.kg2g(float(ch["_min"])),
                 carga_max_g=U.kg2g(float(ch["_max"])))
    if "_RS5_limite_kg" in ch:
        r.update(carga_RS5_limite_g=U.kg2g(float(ch["_RS5_limite_kg"])),
                 carga_RS5_fraccion=float(ch["_RS5_peor_caso"]))
    cs = s.charge_sistema or {}
    if "_min" in cs:
        r.update(carga_sistema_min_g=U.kg2g(float(cs["_min"])),
                 carga_sistema_max_g=U.kg2g(float(cs["_max"])),
                 carga_lineas_max_g=U.kg2g(float(sum(l.charge["_max"]
                                                     for l in s.lines.values()))),
                 dT_sat_lineas_max_K=float(max(l.dT_sat_equivalente
                                               for l in s.lines.values())))
        for k in ("carga_sistema_min_g", "carga_sistema_max_g", "carga_lineas_max_g"):
            UNIDADES.setdefault(k, "g")
        UNIDADES.setdefault("dT_sat_lineas_max_K", "K")
        if "_RS5_peor_caso" in cs:
            r["carga_sistema_RS5_fraccion"] = float(cs["_RS5_peor_caso"])
    env = s.envelope or {}
    for k, v in env.get("limites", {}).items():
        r[f"envolvente_{k}"] = v["estado"]
    if "margen_no_condensacion" in env.get("limites", {}):
        r["margen_no_condensacion_K"] = env["limites"]["margen_no_condensacion"]["valor"]
    if "diagrama_aplicacion" in env.get("limites", {}):
        r["zona_diagrama"] = env["limites"]["diagrama_aplicacion"]["valor"]
    r["fuera_dominio_compresor"] = env.get("fuera_del_dominio_del_compresor")
    try:
        e = I.energy(s, spec)
        x = I.exergy(s, spec, e)
        r.update(W_el=e.W_el, EER=e.EER, COP=e.COP, COP_global=e.COP_global,
                 eta_II=x.eta_II, cierre_exergetico=x.cierre)
        for k, v in x.y_D.items():
            r[f"y_D_{k}"] = float(v)
        for k, v in x.y_D_ciclo.items():
            r[f"y_D_ciclo_{k}"] = float(v)
        r["componente_mayor_ciclo"] = x.componente_mayor_ciclo
    except Exception as exc:                # p.ej. sin datos electricos
        r["indicadores_error"] = str(exc)[:120]
    r["sustituciones"] = len(s.provenance.get("sustituciones", {}))
    return r


#: Conjunto comparativo del protocolo del §6.8.3. El R-744 NO esta: la
#: decision D-2 se reabrio el 21/09/2026 y se retiro del conjunto —queda como
#: tratamiento cualitativo del cap. 5—, de modo que la comparacion estricta en
#: igualdad de condiciones es entre estos tres.
#:
#: Que el fluido sea un PARAMETRO no se cae con esa decision, al contrario: es
#: lo que H5 necesita, y la D-2 ya lo habia marcado como «no aplazable».
FLUIDOS_COMPARATIVOS = ("Ammonia", "Propane", "R32")

#: Compresor de cada fluido (decision del 29/09/2026, opcion C): el Bock F2 abierto
#: para el R-717, un semihermetico para el R-290 y un scroll para el R-32, cada uno
#: con su fichero `data/<nombre>.yaml` y sus puntos `data/<nombre>_catalogo.csv`.
COMPRESOR_POR_FLUIDO = {"Ammonia": "compresor_bock_f2", "Propane": "compresor_r290",
                        "R32": "compresor_r32"}

#: Materiales adaptados (decision 9c del 29/09/2026): fuera del R-717 la bateria
#: lleva tubo de cobre con la misma geometria; las placas no cambian. Cu-DHP
#: (C12200), conductividad a 20 °C: ASM Handbook, vol. 2 (Properties and Selection:
#: Nonferrous Alloys), 1990.
K_COBRE_DHP_W_mK = 339.0
MATERIALES_ADAPTADOS = {"bateria_frimetal_cbn21:conductividad_tubo_W_mK": K_COBRE_DHP_W_mK}


def build_circuit(fluido: str = "Ammonia", backend_hx: str = "HEOS",
                  umbral_backend: float | None = None,
                  n_segments: int = 60, n_cells: int = 12,
                  con_placas: bool = True, sustituciones: dict | None = None,
                  phi_md: float = 1.0, correlaciones: dict | None = None,
                  con_lineas: bool = True, compresor: str | None = None,
                  materiales: str | None = None,
                  modelo_compresor: str | None = None) -> tuple:
    """Monta el circuito completo declarando fluido y backend.

    `fluido` es parametro y no constante porque el protocolo del §6.8.3
    compara R-717, R-290 y R-32 sobre la MISMA geometria: «se mantiene fijo
    [...] la geometria de los intercambiadores», y lo que se adapta es la
    cilindrada del compresor. Cambiar de fluido debe ser pasar un valor.

    AVISO sobre los otros fluidos: la geometria y los parametros identificados
    que el modelo carga son los del amoniaco. Correr con Propane o R32 emplea
    el compresor de NH3 SIN reidentificar y sin adaptar la cilindrada, de modo
    que el punto no es comparable todavia: falta la adaptacion que la tabla 6.6
    exige. El circuito se monta —es lo que permite abordar H5— pero el aviso
    debe viajar con cualquier resultado.

    El compresor y el lazo externo van SIEMPRE en HEOS: las ec. 9-4 y 9-5
    resuelven la compresion isocora por los pares DH y DS, que el backend
    tabular de CoolProp no soporta. Los intercambiadores pueden ir en tabular,
    y ahi esta el grueso del coste.

    `sustituciones` son las de `data.sustituciones` ({"fichero:ruta": valor}):
    el circuito se construye dentro de ellas y las conserva para resolver, y la
    procedencia de cada punto las enumera. `phi_md` es el factor de
    maldistribucion de la bateria (hipotesis M2), que no es un dato de fichero.
    `correlaciones` = {"bateria" | "placas": {familia: nombre}} sustituye
    correlaciones registradas por nombre (§9.12.3); "placas" se aplica a los dos
    intercambiadores de placas. La procedencia de cada punto las enumera.

    `compresor`: fichero de datos del compresor. Por defecto, el de
    `COMPRESOR_POR_FLUIDO`; si ese fichero no existe todavia, el del F2 de NH3,
    marcado en la procedencia como TRANSFERIDO SIN REIDENTIFICAR.

    `modelo_compresor`: "en12900" (polinomios de UNE-EN 12900, decisión del autor del
    15/10/2026) o "semiempirico" (el del §9.5 hasta esa fecha, para reproducir cifras
    anteriores). Por defecto, el que declara el fichero del compresor (`modelo_compresor`).

    `materiales`: "base" (los del R-717: tubo de inoxidable) o "adaptados" (tubo
    de cobre, `MATERIALES_ADAPTADOS`). Por defecto, adaptados fuera del R-717.
    Se aplican como sustituciones declaradas, de modo que viajan con cada punto.

    Devuelve `(circuito, informe_backend)`.
    """
    from . import data as D
    transferido = False
    if compresor is None:
        compresor = COMPRESOR_POR_FLUIDO.get(fluido, "compresor_bock_f2")
        if not (D.data_dir() / f"{compresor}.yaml").is_file():
            compresor, transferido = "compresor_bock_f2", fluido != "Ammonia"
    if materiales is None:
        materiales = "base" if fluido == "Ammonia" else "adaptados"
    if materiales not in ("base", "adaptados"):
        raise ValueError(materiales)
    sus = dict(sustituciones or {})
    if materiales == "adaptados":
        sus = {**MATERIALES_ADAPTADOS, **sus}
    with D.sustituciones(sus or None):
        return _build_circuit(fluido, backend_hx, umbral_backend, n_segments,
                              n_cells, con_placas, sus or None, phi_md,
                              con_lineas,
                              correlaciones or {}, compresor, transferido,
                              modelo_compresor)


def _build_circuit(fluido, backend_hx, umbral_backend, n_segments, n_cells,
                   con_placas, sustituciones, phi_md, con_lineas,
                   correlaciones, compresor="compresor_bock_f2",
                   transferido=False, modelo_compresor=None) -> tuple:
    informe = None
    if backend_hx != "HEOS":
        if umbral_backend is None:
            raise BackendSinUmbral(
                "Pedir un backend tabular exige declarar el umbral del "
                "ap. 6.6.4: «su empleo queda condicionado a que dicha "
                "desviacion resulte inferior al umbral declarado». Pase "
                "`umbral_backend`.")
        informe = backend_is_usable(
            backend_deviation_report(fluido, backend=backend_hx,
                                     pairs=("PT", "PH", "PQ", "PS")),
            umbral_backend)
        if not informe["usable"]:
            raise BackendFueraDeUmbral(
                f"El backend {backend_hx} se desvia {informe['peor']['max']:.1e} "
                f"en {informe['peor']['par']}/{informe['peor']['magnitud']}, "
                f"por encima del umbral {umbral_backend:.0e} declarado.")

    from . import data as D
    from .components.air_hx import AirCoil
    from .components.plate_hx import PlateHeatExchanger

    f = Fluid(fluido)                                  # HEOS: compresor y lazo
    g = Fluid(fluido, backend_hx)                      # intercambiadores
    dfc = D.load(compresor)
    comp = D.compressor(dfc, fluid=f, modelo=modelo_compresor)
    coil = AirCoil(g, D.air_coil_geometry(), n_segments=n_segments,
                   phi_md=phi_md, corr=correlaciones.get("bateria"))
    clima = acs = None
    if con_placas:
        clima = PlateHeatExchanger(
            g, Fluid("Water"), D.plate_geometry("condensador_climatizacion"),
            n_cells=n_cells, corr=correlaciones.get("placas"))
        acs = PlateHeatExchanger(
            g, Fluid("Water"), D.plate_geometry("desrecalentador_acs"),
            n_cells=n_cells, corr=correlaciones.get("placas"))
    lines = None
    if con_lineas:
        from .components.line import RefrigerantLine
        lines = {par: RefrigerantLine(g, geo)
                 for par, geo in D.refrigerant_lines().items()}
    return Circuit(f, comp, coil, clima, acs,
                   sustituciones=sustituciones, lines=lines,
                   compresor_fichero=compresor,
                   compresor_transferido=transferido), informe


def run(mode: str, bc_list, sp=None, sp_list=None, etiquetas=None,
        fluido: str = "Ammonia", backend_hx: str = "HEOS",
        umbral_backend: float | None = None,
        circuito=None, informe_backend=None, **kw) -> CampaignResult:
    """Ejecuta una campana y devuelve las filas con su procedencia.

    Los casos que no convergen NO se descartan: entran en `rows` con
    `convergido=False` y con su residuo, y `validos()` los filtra cuando hace
    falta. Es la lectura conjunta de los ap. 6.6.6 y 6.12.
    """
    spec = MODES[mode]
    if circuito is None:
        circuito, informe_backend = build_circuit(
            fluido=fluido, backend_hx=backend_hx,
            umbral_backend=umbral_backend)

    sols = circuito.sweep(mode, bc_list, sp_list=sp_list, sp=sp, **kw)
    etiquetas = list(etiquetas or range(len(sols)))
    rows = [fila(s, spec, etq) for etq, s in zip(etiquetas, sols)]

    prov = PropertyProvenance(
        backend=f"HEOS (compresor) + {backend_hx} (intercambiadores)",
        fluids=(fluido, "Water"),
        # Las correlaciones activas salen de la procedencia que el propio
        # lazo externo ya adjunta a cada solucion: reconstruirlas aqui seria
        # una segunda fuente de verdad.
        correlations=(sols[0].provenance.get("correlaciones", {})
                      if sols else {}),
        inputs={"modo": mode, "fluido": fluido, "n_casos": len(sols),
                "etiquetas": [str(e) for e in etiquetas],
                "geometria_inyectada": (sols[0].provenance.get(
                    "geometria_inyectada", {}) if sols else {}),
                "sustituciones": (sols[0].provenance.get(
                    "sustituciones", {}) if sols else {}),
                "tolerancia_residuos": Circuit.TOL,
                "tolerancia_balances": Circuit.TOL_BALANCE})
    return CampaignResult(mode=mode, rows=rows, provenance=prov.as_dict(),
                          backend_hx=backend_hx, fluido=fluido,
                          backend_report=informe_backend, solutions=sols)
