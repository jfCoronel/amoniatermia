"""Compresor por polinomios de UNE-EN 12900. Sustituye al semiempírico del §9.5 (15/10/2026).

DECISIÓN DEL AUTOR (15/10/2026, `docs/DECISIONES_2026_10_15.md`). El modelo semiempírico, ni
ampliado, cumple N1 en toda la zona sin límites del diagrama del fabricante. Para que la
admisibilidad de un punto dependa solo de los límites del compresor real, el compresor se
describe con los polinomios de UNE-EN 12900 ajustados a los puntos del software VAP de Bock, que
barren esa zona en rejilla de 5 K a cuatro velocidades.

FORMULACIÓN
-----------
Polinomio de diez coeficientes de la norma, en temperaturas de saturación en °C (t0 de
evaporación, tc de condensación, de rocío; para NH3 puro, las de saturación):

    X = c0 + c1 t0 + c2 tc + c3 t0² + c4 t0 tc + c5 tc² + c6 t0³ + c7 tc t0² + c8 t0 tc² + c9 tc³

Uno para el caudal másico, otro para la potencia al eje y otro para la temperatura de descarga
(este último no lo define la norma; se usa la misma forma), a cada velocidad y con el
recalentamiento de referencia (5 K) y subenfriamiento nulo.

Reglas acordadas con el autor:

- RECALENTAMIENTO. Se conservan los rendimientos obtenidos con el de referencia: volumétrico
  (caudal), isentrópico (potencia al eje) y de descarga (temperatura de descarga). Con otro
  recalentamiento cambian el volumen específico y el salto isentrópico, no los rendimientos.
- SUBENFRIAMIENTO. No afecta al compresor.
- VELOCIDAD. Los tres rendimientos se interpolan con un polinomio de segundo grado en la
  velocidad, ajustado por mínimos cuadrados a los nudos disponibles.

Rendimientos, con su = estado de aspiración (P0, T0 + recalentamiento) y s = isentrópico hasta Pk:

    eta_v   = m v_su / V̇_barrido
    eta_is  = m (h_s − h_su) / W_eje
    eta_dis = (h_s − h_su) / (h_dis − h_su)

El calor cedido al ambiente sale del balance: Q_amb = W_eje − m (h_dis − h_su).

Unidades: SI estricto en la interfaz (Pa, K, W, kg/s); °C solo dentro del polinomio, que es como
lo define la norma.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ..props import Fluid
from .compressor import CompressorResult, MissingEfficiency

K = 273.15


def terminos(t0, tc):
    """Los diez términos del polinomio de UNE-EN 12900, en °C."""
    t0, tc = np.asarray(t0, float), np.asarray(tc, float)
    return np.stack([np.ones_like(t0), t0, tc, t0**2, t0 * tc, tc**2,
                     t0**3, tc * t0**2, t0 * tc**2, tc**3], axis=-1)


def ajusta_polinomio(t0, tc, y):
    """Coeficientes por mínimos cuadrados."""
    c, *_ = np.linalg.lstsq(terminos(t0, tc), np.asarray(y, float), rcond=None)
    return c


def evalua(c, t0, tc):
    return terminos(t0, tc) @ np.asarray(c)


@dataclass
class PolinomiosVelocidad:
    """Polinomios de una velocidad: caudal [kg/s], potencia [W] y descarga [°C].

    `T_dis_C` es None cuando el fabricante no publica la descarga (R-32): el compresor la toma
    entonces de `descarga_ref` (decisión P2 del 15/10/2026)."""
    rpm: float
    m_dot: np.ndarray
    W_eje: np.ndarray
    T_dis_C: np.ndarray | None = None
    n_puntos: int = 0


class VelocidadFueraDeRango(ValueError):
    """Velocidad fuera de los nudos con datos: no se extrapola (decisión V1, 15/10/2026)."""


class EN12900Compressor:
    """Compresor descrito por polinomios de UNE-EN 12900 a una o varias velocidades.

    Misma interfaz que `SemiEmpiricalCompressor` para el lazo externo: `solve`, `eta_v` y
    `geom.V_dot_swept`. La velocidad es la de `geom.n_rpm` y puede cambiarse entre puntos
    (`fija_velocidad`), dentro del rango de los nudos.

    `ajuste`: factores de la incertidumbre del compresor (P3): multiplican el caudal y la
    potencia de los polinomios y desplazan la descarga. Nominal: 1, 1 y 0.
    `descarga_ref`: función (P0, T_su, Pk) -> T_dis [K] para los compresores sin descarga en
    los datos; se evalúa con el recalentamiento de referencia.
    `potencia_electrica`: los herméticos publican potencia eléctrica (motor dentro);
    `eta_motor` y `eta_transm` valen entonces 1 y `W_shaft` es esa potencia.
    """

    def __init__(self, fluid: Fluid, geom, polinomios: list[PolinomiosVelocidad],
                 recalentamiento_ref_K: float = 5.0, eta_motor=None, eta_transm=None,
                 grado_velocidad: int = 2, ajuste: dict | None = None, descarga_ref=None,
                 procedencia: dict | None = None, V_swept_datos: float | None = None):
        self.fluid = fluid
        self.geom = geom
        self.pol = sorted(polinomios, key=lambda p: p.rpm)
        self.sh_ref = recalentamiento_ref_K
        self.eta_motor, self.eta_transm = eta_motor, eta_transm
        self.grado = min(grado_velocidad, len(self.pol) - 1)
        a = ajuste or {}
        self.f_m = float(a.get("factor_caudal", 1.0))
        self.f_W = float(a.get("factor_potencia", 1.0))
        self.dT = float(a.get("desplazamiento_descarga_K", 0.0))
        self.descarga_ref = descarga_ref
        self.procedencia = procedencia or {}
        #: Cilindrada del compresor de los datos [m3/rev]. Con otra en `geom` (igualación de
        #: capacidad del cap. 13) los rendimientos se conservan y el caudal escala.
        self.V_swept_datos = V_swept_datos if V_swept_datos is not None else geom.V_swept
        if any(p.T_dis_C is None for p in self.pol) and descarga_ref is None:
            raise ValueError("Sin polinomio de descarga hace falta `descarga_ref`.")
        self.rpm_min, self.rpm_max = self.pol[0].rpm, self.pol[-1].rpm
        self._cache = {}

    # ------------------------------------------------------------------
    @property
    def rpm(self) -> float:
        return self.geom.n_rpm

    def fija_velocidad(self, rpm: float) -> None:
        """Cambia la velocidad de giro. Fuera de los nudos con datos, falla."""
        tol = 1e-6 * self.rpm_max
        if not (self.rpm_min - tol <= rpm <= self.rpm_max + tol):
            raise VelocidadFueraDeRango(
                f"{rpm:.0f} rpm fuera de los datos ({self.rpm_min:.0f}-{self.rpm_max:.0f} rpm)")
        self.geom = replace(self.geom, n_rpm=float(rpm))

    @property
    def eta_electromechanical(self) -> float:
        if self.eta_motor is None or self.eta_transm is None:
            raise MissingEfficiency(
                "eta_motor y/o eta_transm sin declarar (ec. 9-9). Declararlos en el fichero "
                "del compresor con su procedencia.")
        return self.eta_motor * self.eta_transm

    def _barrido(self, rpm):
        """Caudal barrido del compresor de los DATOS a `rpm`."""
        return self.V_swept_datos * rpm / 60.0

    def _estados(self, P0, Pk, T_su):
        """h_su, v_su, h_s (isentrópico hasta Pk)."""
        f = self.fluid
        f.update_PT(P0, T_su)
        h_su, v_su, s_su = f.h, f.v, f.s
        f.update_PS(Pk, s_su)
        return h_su, v_su, f.h

    def rendimientos_nudo(self, p: PolinomiosVelocidad, P0, Pk):
        """eta_v, eta_is y eta_dis del nudo `p`, con el recalentamiento de referencia."""
        f = self.fluid
        t0, tc = f.Tsat(P0) - K, f.Tsat(Pk) - K
        m = self.f_m * float(evalua(p.m_dot, t0, tc))
        W = self.f_W * float(evalua(p.W_eje, t0, tc))
        T_su = t0 + K + self.sh_ref
        if p.T_dis_C is not None:
            T_dis = float(evalua(p.T_dis_C, t0, tc)) + K
        else:
            T_dis = float(self.descarga_ref(P0, T_su, Pk))
        T_dis += self.dT
        h_su, v_su, h_s = self._estados(P0, Pk, T_su)
        f.update_PT(Pk, T_dis)
        h_dis = f.h
        return (m * v_su / self._barrido(p.rpm), m * (h_s - h_su) / W,
                (h_s - h_su) / (h_dis - h_su))

    def rendimientos(self, P0, Pk, rpm=None):
        """Los tres rendimientos a la velocidad `rpm` (por defecto, la de la geometría)."""
        rpm = self.rpm if rpm is None else rpm
        clave = (P0, Pk)
        nudos = self._cache.get(clave)
        if nudos is None:
            nudos = np.array([self.rendimientos_nudo(p, P0, Pk) for p in self.pol])
            if len(self._cache) > 4096:
                self._cache.clear()
            self._cache[clave] = nudos
        if len(self.pol) == 1:
            return tuple(float(x) for x in nudos[0])
        n = np.array([p.rpm for p in self.pol])
        return tuple(float(np.polyval(np.polyfit(n, nudos[:, j], self.grado), rpm))
                     for j in range(3))

    def eta_v(self, P_ad: float, P_ex: float) -> float:
        return self.rendimientos(P_ad, P_ex)[0]

    # ------------------------------------------------------------------
    def solve(self, P_ad: float, T_su: float, P_ex: float, T_amb: float = 298.15,
              tol: float = 1e-6) -> CompressorResult:
        if P_ex <= P_ad:
            raise ValueError("P_ex debe ser mayor que P_ad")
        if len(self.pol) == 1 and abs(self.rpm - self.pol[0].rpm) > 1e-6 * self.pol[0].rpm:
            raise VelocidadFueraDeRango(
                f"Polinomios a una sola velocidad ({self.pol[0].rpm:.0f} rpm); se pide {self.rpm:.0f}")
        eta_v, eta_is, eta_dis = self.rendimientos(P_ad, P_ex)
        h_su, v_su, h_s = self._estados(P_ad, P_ex, T_su)
        m = eta_v * self.geom.V_dot_swept / v_su
        W = m * (h_s - h_su) / eta_is
        h_dis = h_su + (h_s - h_su) / eta_dis
        self.fluid.update_PH(P_ex, h_dis)
        T_dis = self.fluid.T
        try:
            W_el = W / self.eta_electromechanical
        except MissingEfficiency:
            W_el = None
        return CompressorResult(
            m_dot=m, W_shaft=W, W_el=W_el, T_dis=T_dis, h_dis=h_dis, T_wall=float("nan"),
            eta_v=eta_v, eta_is=eta_is, Q_amb=W - m * (h_dis - h_su), converged=True,
            residuals=(), w_in=W / m)
