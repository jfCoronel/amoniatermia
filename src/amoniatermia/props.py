"""Capa de propiedades termofisicas.

Apartado 9.10 de la tesis.

Decision de diseno critica: NUNCA se emplea `CoolProp.CoolProp.PropsSI` dentro
de un bucle. Se instancia un `AbstractState` por fluido y se reutiliza mediante
`update()`. La medida realizada sobre amoniaco en el rango de trabajo del ciclo
arroja los siguientes tiempos por llamada:

    PropsSI (alto nivel)              ~108 us
    AbstractState HEOS reutilizado     ~14 us   (x7,7)
    AbstractState BICUBIC&HEOS         ~0,66 us (x163)

Con ~1e5 llamadas por punto de operacion resuelto, la diferencia entre la
primera y la tercera opcion es de ~11 s frente a ~0,07 s por punto.

El backend tabular BICUBIC interpola y por tanto introduce un error propio.
La funcion `backend_deviation_report` cuantifica ese error frente a HEOS puro,
como exige la verificacion cruzada del apartado 6.6.4.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import CoolProp
import CoolProp.CoolProp as CP

Backend = Literal["HEOS", "BICUBIC&HEOS", "TTSE&HEOS"]

# Entradas de CoolProp empleadas por el modelo
PT = CoolProp.PT_INPUTS
PQ = CoolProp.PQ_INPUTS
PH = CoolProp.HmassP_INPUTS
PS = CoolProp.PSmass_INPUTS
DS = CoolProp.DmassSmass_INPUTS
DH = CoolProp.DmassHmass_INPUTS
QT = CoolProp.QT_INPUTS


class Fluid:
    """Envoltorio de un `AbstractState` reutilizable.

    Todas las magnitudes en SI estricto: P [Pa], T [K], h [J/kg], s [J/kg/K],
    rho [kg/m3], mu [Pa s], k [W/m/K], sigma [N/m], cp [J/kg/K].

    Parameters
    ----------
    name : str
        Nombre CoolProp del fluido, p.ej. "Ammonia", "Propane", "R32", "CO2".
    backend : Backend
        "HEOS" para la ecuacion de estado de referencia (exacta, lenta).
        "BICUBIC&HEOS" para el backend tabular (rapido, interpolado).
    """

    def __init__(self, name: str, backend: Backend = "HEOS"):
        self.name = name
        self.backend = backend
        self._st = CP.AbstractState(backend, name)
        self._warm_up()
        # Constantes del fluido: se resuelven UNA vez en la construccion.
        # No son propiedades de estado y no cambian con `update()`, de modo que
        # consultarlas en cada evaluacion es coste puro. La version anterior
        # llamaba a `PropsSI("pcrit", ...)` desde `p_reduced()`, que el lazo
        # interno del ap. 9.6.3 invoca una vez por celda y por iteracion:
        # 131 us/llamada medidos, frente a 5.2 us de este estado reutilizado.
        # Es decir, peor que el propio PropsSI de la §9.12.4.
        self._p_crit = self._st.p_critical()
        self._T_crit = self._st.T_critical()
        self._M = self._st.molar_mass()

    def _warm_up(self) -> None:
        """Fuerza la construccion/carga de tablas en los backends tabulares."""
        if "HEOS" != self.backend:
            self._st.update(PT, 1.0e6, 300.0)
            _ = self._st.hmass()

    # ---------------- Actualizacion de estado ----------------
    def update_PT(self, P: float, T: float) -> "Fluid":
        self._st.update(PT, P, T)
        return self

    def update_PQ(self, P: float, Q: float) -> "Fluid":
        self._st.update(PQ, P, Q)
        return self

    def update_PH(self, P: float, H: float) -> "Fluid":
        self._st.update(PH, H, P)
        return self

    def update_PS(self, P: float, S: float) -> "Fluid":
        self._st.update(PS, P, S)
        return self

    def update_DS(self, D: float, S: float) -> "Fluid":
        """Estado a densidad y entropia dadas. Necesario para la compresion
        isoentropica hasta el volumen especifico interno (ec. 9-4)."""
        self._st.update(DS, D, S)
        return self

    def update_DH(self, D: float, H: float) -> "Fluid":
        """Estado a densidad y entalpia dadas.

        Necesario para evaluar el estado REAL al final de la compresion interna
        del compresor: el ap. 9.5.1 exige que la presion de la etapa a volumen
        constante (ec. 9-5) se evalue en (v_in, h_ad) real y no en el ideal.
        """
        self._st.update(DH, D, H)
        return self

    def update_QT(self, Q: float, T: float) -> "Fluid":
        self._st.update(QT, Q, T)
        return self

    # ---------------- Propiedades ----------------
    @property
    def P(self) -> float: return self._st.p()
    @property
    def T(self) -> float: return self._st.T()
    @property
    def h(self) -> float: return self._st.hmass()
    @property
    def s(self) -> float: return self._st.smass()
    @property
    def rho(self) -> float: return self._st.rhomass()
    @property
    def v(self) -> float: return 1.0 / self._st.rhomass()
    @property
    def Q(self) -> float: return self._st.Q()
    @property
    def cp(self) -> float: return self._st.cpmass()
    @property
    def cv(self) -> float: return self._st.cvmass()
    @property
    def gamma(self) -> float:
        """Razon de calores especificos. Gobierna la relacion critica de
        presiones de la tobera de fuga del ap. 9.5.1."""
        return self._st.cpmass() / self._st.cvmass()
    @property
    def mu(self) -> float: return self._st.viscosity()
    @property
    def k(self) -> float: return self._st.conductivity()
    @property
    def Pr(self) -> float: return self._st.Prandtl()
    @property
    def sigma(self) -> float:
        """Tension superficial [N/m].

        El backend TABULAR no siempre puede darla: CoolProp la define solo
        dentro de la campana y el estado interpolado no siempre queda marcado
        como bifasico, con lo que lanza «surface tension is only defined within
        the two-phase region». Como es una propiedad de saturacion y depende
        solo de la temperatura, se toma entonces de un estado HEOS auxiliar.

        Se declara porque significa que el atajo tabular NO cubre todas las
        magnitudes que el modelo necesita, y esa es informacion que el ap. 6.6.4
        pide tener antes de adoptarlo: la tension superficial alimenta tres de
        las correlaciones de fraccion de huecos y con ellas el inventario de
        carga, que es lo que contrasta H4.
        """
        try:
            return self._st.surface_tension()
        except ValueError:
            aux = self._heos_para_saturacion()
            aux.update(QT, 0.0, self.T)
            return aux.surface_tension()

    def _heos_para_saturacion(self):
        """Estado HEOS auxiliar, creado solo si el backend tabular se queda
        corto. Se instancia una vez y se reutiliza, como el principal."""
        st = getattr(self, "_st_heos", None)
        if st is None:
            st = CP.AbstractState("HEOS", self.name)
            self._st_heos = st
        return st

    # ---------------- Magnitudes de saturacion ----------------
    def Tsat(self, P: float) -> float:
        self._st.update(PQ, P, 0.0)
        return self._st.T()

    def Psat(self, T: float) -> float:
        self._st.update(QT, 0.0, T)
        return self._st.p()

    def sat_props(self, P: float) -> dict:
        """Propiedades de liquido y vapor saturados a la presion dada."""
        out = {}
        self._st.update(PQ, P, 0.0)
        out.update(rho_l=self.rho, h_l=self.h, mu_l=self.mu, k_l=self.k,
                   cp_l=self.cp, Pr_l=self.Pr, sigma=self.sigma, Tsat=self.T)
        self._st.update(PQ, P, 1.0)
        out.update(rho_v=self.rho, h_v=self.h, mu_v=self.mu, k_v=self.k,
                   cp_v=self.cp, Pr_v=self.Pr)
        out["h_lv"] = out["h_v"] - out["h_l"]
        return out

    # ---------------- Constantes del fluido ----------------
    @property
    def M(self) -> float:
        """Masa molar [kg/mol]. Cacheada en la construccion."""
        return self._M

    @property
    def p_crit(self) -> float:
        """Presion critica [Pa]. Cacheada en la construccion."""
        return self._p_crit

    @property
    def T_crit(self) -> float:
        """Temperatura critica [K]. Cacheada en la construccion."""
        return self._T_crit

    def p_reduced(self, P: float) -> float:
        return P / self._p_crit

    def __repr__(self) -> str:
        return f"Fluid({self.name!r}, backend={self.backend!r})"


def git_revision(repo_root: str | None = None) -> str:
    """Hash de la revision de git, con sufijo `-dirty` si el arbol de trabajo
    tiene cambios sin confirmar.

    El apartado 9.12.5 exige registrar «la version del codigo empleada» junto a
    cada conjunto de resultados. Un hash de un arbol sucio no identifica el
    codigo que produjo el resultado, de ahi el sufijo: es la diferencia entre
    una procedencia y una apariencia de procedencia.

    Devuelve "desconocida" si no hay repositorio o git no esta disponible, en
    lugar de fallar: la ausencia de trazabilidad debe quedar registrada en el
    fichero de resultados, no impedir el calculo.
    """
    import subprocess
    root = repo_root or str(Path(__file__).resolve().parents[2])
    try:
        rev = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", root, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        return f"{rev}-dirty" if dirty else rev
    except Exception:
        return "desconocida"


@dataclass
class PropertyProvenance:
    """Trazabilidad de una ejecucion (apartados 6.12 y 9.12.5).

    Debe adjuntarse a todo fichero de resultados para que la campana sea
    reproducible y auditable. El apartado 9.12.5 enumera cinco elementos:
    version de la biblioteca de propiedades, backend empleado, identificadores
    de las correlaciones activas, version del codigo y la totalidad de los
    parametros de entrada. Los cinco estan aqui.
    """
    coolprop_version: str = field(default_factory=lambda: CoolProp.__version__)
    backend: str = "HEOS"
    fluids: tuple = ()
    correlations: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)
    code_revision: str = field(default_factory=git_revision)
    package_version: str = ""
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def __post_init__(self):
        if not self.package_version:
            from . import __version__
            self.package_version = __version__

    def as_dict(self) -> dict:
        return {
            "coolprop_version": self.coolprop_version,
            "backend": self.backend,
            "fluids": list(self.fluids),
            "correlations": dict(self.correlations),
            "inputs": dict(self.inputs),
            "code_revision": self.code_revision,
            "package_version": self.package_version,
            "created_utc": self.created_utc,
        }

    def is_complete(self) -> bool:
        """Cierto si la procedencia identifica inequivocamente la ejecucion.

        Un resultado cuya procedencia no sea completa no cumple el compromiso
        del apartado 6.12 y no debe archivarse como definitivo.
        """
        return bool(
            self.fluids and self.correlations and self.inputs
            and self.code_revision != "desconocida"
            and not self.code_revision.endswith("-dirty"))

    def write_json(self, path) -> None:
        """Escribe la procedencia junto al fichero de resultados."""
        Path(path).write_text(
            json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8")


def deviation_report_PT(name: str, states, backend: Backend = "BICUBIC&HEOS"):
    """Verificacion cruzada sobre el par PT UNICAMENTE.

    Es el informe que habia antes del 21/09/2026. Se conserva porque el par PT
    sigue interviniendo, pero NO basta: ver `backend_deviation_report`.

    Parameters
    ----------
    name : str
        Fluido CoolProp.
    states : iterable of (P, T)
        Estados de referencia en Pa y K.
    backend : Backend
        Backend tabular a contrastar.

    Returns
    -------
    dict
        Desviacion relativa maxima y media en h, s y rho.
    """
    ref = Fluid(name, "HEOS")
    tab = Fluid(name, backend)
    dev = {"h": [], "s": [], "rho": []}
    for P, T in states:
        ref.update_PT(P, T)
        tab.update_PT(P, T)
        # la entalpia puede cruzar cero: se normaliza con el propio valor de
        # referencia solo si no es despreciable, en caso contrario en absoluto
        for key, a, b in (("h", ref.h, tab.h),
                          ("s", ref.s, tab.s),
                          ("rho", ref.rho, tab.rho)):
            denom = abs(a) if abs(a) > 1e-8 else 1.0
            dev[key].append(abs(a - b) / denom)
    return {
        k: {"max": max(v), "mean": sum(v) / len(v)} for k, v in dev.items()
    }


#: Pares de entrada que el modelo emplea de verdad. `backend_deviation_report`
#: los recorre TODOS y no solo PT, porque el error de interpolacion del backend
#: tabular no es el mismo en cada uno: PT apenas se usa dentro de la campana
#: —es degenerado en la region bifasica— mientras que PH es el par del camino
#: caliente de los intercambiadores, con mas de un millon de llamadas por punto.
INPUT_PAIRS = ("PT", "PH", "PQ", "PS", "DH", "DS")


def reference_states(name: str, n: int = 12,
                     x_levels=(0.0, 0.25, 0.5, 0.75, 1.0),
                     dT_levels=(-20.0, -5.0, 5.0, 40.0, 100.0)):
    """Malla de estados de referencia que cubre el dominio de trabajo.

    Devuelve `(monofasicos, bifasicos)`: los primeros son pares (P, T) con
    subenfriamiento o recalentamiento suficiente para no caer en la campana;
    los segundos, pares (P, x) sobre la saturacion.

    El dominio es el del ciclo —evaporacion desde -15 C, condensacion hasta
    55 C, y hasta 100 K de recalentamiento en la descarga—, que es lo que el
    ap. 6.6.4 pide: «un conjunto de estados que cubre el dominio de trabajo».
    """
    ref = Fluid(name, "HEOS")
    P_lo, P_hi = ref.Psat(258.15), ref.Psat(328.15)
    presiones = [P_lo * (P_hi / P_lo) ** (i / (n - 1)) for i in range(n)]
    mono, bif = [], []
    for P in presiones:
        Tsat = ref.Tsat(P)
        mono += [(P, Tsat + dT) for dT in dT_levels]
        bif += [(P, x) for x in x_levels]
    return mono, bif


def backend_deviation_report(name: str, states=None, states_2ph=None,
                             backend: Backend = "BICUBIC&HEOS",
                             pairs=INPUT_PAIRS):
    """Verificacion cruzada HEOS frente al backend tabular (ap. 6.6.4).

    AMPLIADA el 21/09/2026. Antes recorria SOLO el par PT, y eso deja fuera lo
    que importa: el apartado condiciona el empleo del backend tabular a que su
    desviacion sea inferior al umbral declarado, y la desviacion no es la misma
    en todos los pares de entrada. PT es ademas el unico que el modelo apenas
    usa; PH es el del camino caliente.

    Devuelve, por par de entrada y por magnitud, la desviacion relativa maxima
    y media. Las magnitudes contrastadas son las que el par NO fija: pedir un
    estado por PH y comprobar h seria comprobar que el backend recuerda lo que
    se le ha dado.
    """
    if states is None:
        states, states_2ph = reference_states(name)
    states_2ph = states_2ph or []

    ref, tab = Fluid(name, "HEOS"), Fluid(name, backend)
    salida = {}

    def anota(acc, aplica, magnitudes):
        aplica(ref)
        objetivo = {k: getattr(ref, k) for k in magnitudes}
        try:
            aplica(tab)
        except Exception as exc:
            acc.setdefault("fallos", []).append(str(exc)[:70])
            return
        for k, v in objetivo.items():
            denom = abs(v) if abs(v) > 1e-8 else 1.0
            acc.setdefault(k, []).append(abs(v - getattr(tab, k)) / denom)

    for par in pairs:
        acc = {}
        if par == "PT":
            for P, T in states:
                anota(acc, lambda f, P=P, T=T: f.update_PT(P, T),
                      ("h", "s", "rho"))
        elif par == "PQ":
            for P, x in states_2ph:
                anota(acc, lambda f, P=P, x=x: f.update_PQ(P, x),
                      ("h", "s", "rho", "T"))
        else:
            for tipo, P, y in ([("m", P, T) for P, T in states]
                               + [("b", P, x) for P, x in states_2ph]):
                ref.update_PT(P, y) if tipo == "m" else ref.update_PQ(P, y)
                h, sm, d = ref.h, ref.s, ref.rho
                if par == "PH":
                    aplica, mags = (lambda f, P=P, h=h: f.update_PH(P, h),
                                    ("T", "s", "rho"))
                elif par == "PS":
                    aplica, mags = (lambda f, P=P, sm=sm: f.update_PS(P, sm),
                                    ("T", "h", "rho"))
                elif par == "DH":
                    aplica, mags = (lambda f, d=d, h=h: f.update_DH(d, h),
                                    ("T", "s", "P"))
                else:
                    aplica, mags = (lambda f, d=d, sm=sm: f.update_DS(d, sm),
                                    ("T", "h", "P"))
                anota(acc, aplica, mags)
        salida[par] = {k: {"max": max(v), "mean": sum(v) / len(v),
                           "n": len(v)}
                       for k, v in acc.items() if k != "fallos"}
        if "fallos" in acc:
            salida[par]["fallos"] = acc["fallos"][:3]
    return salida


def backend_is_usable(reporte: dict, umbral: float) -> dict:
    """Decide si el backend tabular puede emplearse, ap. 6.6.4.

    «El empleo del backend tabular queda condicionado a que dicha desviacion
    resulte inferior al umbral declarado». El umbral NO tiene valor por
    defecto: quien decida usar el backend tiene que pasarlo expresamente, y esa
    es la decision que el apartado quiere ver declarada.
    """
    peor = {"max": -1.0}
    fallos = {}
    for par, mags in reporte.items():
        if "fallos" in mags:
            fallos[par] = mags["fallos"]
        for k, v in mags.items():
            if k == "fallos":
                continue
            if v["max"] > peor["max"]:
                peor = {"max": v["max"], "par": par, "magnitud": k}
    return {"usable": peor["max"] <= umbral and not fallos,
            "umbral": umbral, "peor": peor, "fallos": fallos}
