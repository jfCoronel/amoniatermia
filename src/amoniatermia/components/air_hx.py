"""Intercambiador de aire de tubo y aleta. Apartado 9.7.

ALCANCE DE ESTA VERSION
-----------------------
Cubre las tareas C1 a C5, C7, C8 y C9 del plan
(`docs/historico/PLAN_PUESTA_EN_MARCHA.md`): geometria verificada, lado de aire anclado,
eficiencia de aleta seca y humeda, resistencia de pared, correlaciones de tubo
con criterio de transicion, marcha por segmentos con superficie humeda,
diagnostico de regimen e inventario de carga. El componente opera ya en los dos
sentidos: como condensador y como evaporador.

NO cubre todavia, y lo declara:

- Perdida de carga del lado de refrigerante, ec. 9-20 completa con multiplicador
  bifasico y perdidas localizadas en los codos de retorno. La ficha declara
  2622 Pa y es el contraste disponible. Aqui se desprecia, y es defendible
  mientras la presion se trate como uniforme —2.6 kPa sobre 17.8 bar es un
  0.15 %— pero no lo sera para el barrido de circuiteria del cap. 11.
- Escarcha (C6). La marcha REPORTA el dominio de formacion —temperatura
  superficial bajo cero y caudal de condensado, que es el dato que el ap. 9.7.6
  necesita para saber en que intervalos aplicar la ec. 9-30— pero resuelve el
  serpentin LIMPIO, sin capa depositada. La penalizacion es del cap. 11.
- Curva caracteristica del ventilador (C7): se adopta consumo constante de
  catalogo (780 W); ver `fan_power`.

LADO DE REFRIGERANTE (C4, ap. 9.7.5)
-------------------------------------
Familias `tube_condensation` y `tube_boiling`, separadas de las de placas. La
zona bifasica despacha por el papel del componente en el modo activo: condensa
con la ec. 9-24 —criterio de Soliman, anular por encima de Fr_so = 20 y
estratificado por debajo— y evapora con la ec. 9-26/27.

Las dos dependen del propio flujo de calor: la ec. 9-27 por el numero de
ebullicion y la rama estratificada de la ec. 9-24 por el numero de Jakob. Cada
celda itera por tanto sobre q'' hasta convergencia (ap. 9.7.2).

Dos hallazgos que el capitulo debe recoger, ambos declarados en
`correlations/tube.py` y contrastados en `tests/test_tube.py`:

- Las cifras de ebullicion que el ap. 9.7.5 publica —3100 y 1900 W/(m2 K)— y la
  columna U de la tabla 9.20 son de COOPER SOLO, no de la ec. 9-26 que el
  mismo apartado declara adoptar. Esta registrada como `cooper_solo`.
- A 48 kg/(m2 s) la rama anular da MENOS que la estratificada, no mas: el
  ap. 9.7.5 justifica el criterio en la direccion contraria a la que sus
  propias ecuaciones producen.

SUPERFICIE HUMEDA (C5, ap. 9.7.6)
---------------------------------
Cada celda decide su regimen comparando la temperatura superficial con el punto
de rocio del aire. En seco marcha sobre diferencia de TEMPERATURAS; en humedo,
sobre diferencia de ENTALPIAS del aire (ec. 9-28), con la eficiencia de aleta
corregida por la pendiente de la curva de saturacion (ec. 9-29) y el numero de
Lewis adoptado igual a la unidad. El componente reporta separadamente la
contribucion sensible y la latente, y con ella el caudal de condensado.

El regimen no se declara desde fuera ni se supone por el modo: se resuelve. Con
la bateria operando como condensador en M-2 la superficie sale seca en todas las
celdas, que es lo que la ficha declara al dar la misma humedad especifica de
17.80 g/kg a la entrada y a la salida del aire.

SOBRE EL MODELO DE AIRE
-----------------------
La marcha discretiza el area externa en N segmentos iguales a lo largo del
camino del refrigerante y trata el aire como N corrientes en PARALELO, cada una
con su parte del caudal y todas entrando a la temperatura exterior. No es la
marcha fila a fila del ap. 9.7.2, que reparte el aire en serie entre rangos.
Con dos rangos, un salto de aire de 4.9 K y una LMTD de 7.28 K, la diferencia es
acotada, pero se declara: el reparto de zonas que este modulo calcula es una
primera estimacion, no el resultado del ap. 9.7.2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .base import Component
from ..correlations import ExtrapolationLog, get
from ..correlations.airside import (alpha_from_colburn, max_velocity,
                                    reynolds_Dc)
from ..correlations.fin import surface_effectiveness
from ..correlations.singlephase import reynolds
from ..correlations.tube import soliman_froude
from ..correlations.voidfraction import CORRELACIONES_HUECOS, charge_range
from ..geometry import FinnedCoilGeometry
from ..props import Fluid
from .. import psychrometrics as psy


@dataclass
class AirState:
    """Condiciones del aire a la entrada. SI estricto.

    Los valores por defecto de `rho`, `mu`, `cp` y `Pr` son los que el ap. 9.7.3
    empleo para ANCLAR la correlacion de aire sobre el punto de ficha: aire a
    35 C. Se conservan como defecto porque cambiarlos moveria el anclaje, que es
    el unico dato experimental del componente. Para cualquier otra condicion
    —y en particular para la operacion como evaporador, donde el aire esta 30 K
    mas frio— debe usarse `AirState.at()`, que las deduce de la temperatura y de
    la humedad en lugar de arrastrar las de 35 C.

    `w` es la humedad especifica por kg de aire SECO. Si no se da, se deduce de
    `RH`. El estado psicrometrico completo lo dan `w`, `h` y `T_dew`.
    """
    T: float                  # K
    V_frontal: float          # m/s
    rho: float = 1.13         # kg/m3
    mu: float = 1.89e-5       # Pa s
    cp: float = 1005.0        # J/kg/K
    Pr: float = 0.71          # -
    RH: float = 0.50          # -
    P: float = psy.P_ATM      # Pa
    w: float | None = None    # kg agua / kg aire seco

    def __post_init__(self):
        if self.w is None:
            self.w = psy.humidity_ratio(self.T, self.RH, self.P)

    @classmethod
    def at(cls, T: float, V_frontal: float, RH: float | None = None,
           T_wb: float | None = None, w: float | None = None,
           P: float = psy.P_ATM) -> "AirState":
        """Estado con propiedades DEDUCIDAS de la condicion psicrometrica.

        La humedad se declara de una de tres maneras y solo una: humedad
        relativa, temperatura de bulbo humedo o humedad especifica. La segunda
        es la que usan la tabla 9.20 y la UNE-EN 14511 (7 C bs / 6 C bh).
        """
        dados = [x is not None for x in (RH, T_wb, w)]
        if sum(dados) != 1:
            raise ValueError(
                "Declare la humedad de UNA sola forma: RH, T_wb o w.")
        if T_wb is not None:
            w = psy.wet_bulb_humidity_ratio(T, T_wb, P)
        elif RH is not None:
            w = psy.humidity_ratio(T, RH, P)
        return cls(T=T, V_frontal=V_frontal, P=P, w=w,
                   RH=psy.relative_humidity(T, w, P),
                   rho=psy.density(T, w, P), mu=psy.viscosity(T),
                   cp=psy.cp_moist(w) / (1.0 + w), Pr=psy.prandtl(T, w))

    @property
    def h(self) -> float:
        """Entalpia del aire [J / kg aire SECO]. Potencial de la ec. 9-28."""
        return psy.enthalpy(self.T, self.w)

    @property
    def cp_da(self) -> float:
        """Calor especifico por kg de aire SECO: cp_a + w cp_v."""
        return psy.cp_moist(self.w)

    @property
    def T_dew(self) -> float:
        """Temperatura de rocio [K]. Umbral del regimen de superficie."""
        return psy.dew_point(self.w, self.P)

    def dry_mass_flow(self, m_dot_humid: float) -> float:
        """Caudal de aire SECO a partir del de mezcla: el balance entalpico de
        la ec. 9-28 se cierra sobre el primero, no sobre el segundo."""
        return m_dot_humid / (1.0 + self.w)


@dataclass
class CoilResult:
    Q_dot: float                      # W (negativo: calor cedido al aire)
    h_ref_out: float                  # J/kg
    T_ref_out: float                  # K
    T_air_out: float                  # K
    U_mean: float                     # W/(m2 K), referido al area externa
    h_air: float                      # W/(m2 K)
    eta_fin: float
    eta_surface: float
    subcooling: float                 # K a la salida
    volume_fraction: dict = field(default_factory=dict)   # por regimen
    duty_fraction: dict = field(default_factory=dict)
    charge: dict = field(default_factory=dict)
    x_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    #: Perfil a lo largo del recorrido del REFRIGERANTE: `A` es el area externa
    #: acumulada en los nudos (N+1 valores) y `T_ref` la temperatura del
    #: refrigerante en ellos; `T_aire_sal` y `T_sup` son, por segmento (N), la
    #: temperatura del aire que lo atraviesa a la salida y la de la superficie.
    #: El aire entra a todos los segmentos a la misma temperatura (flujo cruzado
    #: con los segmentos en paralelo, §9.13).
    profile: dict = field(default_factory=dict)
    extrapolated: bool = False
    excursions: list = field(default_factory=list)
    # --- Superficie humeda, ap. 9.7.6 (tarea C5) ---
    Q_sensible: float = 0.0           # W, misma convencion de signo que Q_dot
    Q_latent: float = 0.0             # W
    m_condensate: float = 0.0         # kg/s
    w_air_out: float = 0.0            # kg/kg aire seco
    h_air_out: float = 0.0            # J/kg aire seco
    wet_fraction: float = 0.0         # fraccion del AREA con pared humeda
    frost_fraction: float = 0.0       # fraccion del area con T_s < 0 C
    #: Segmentos REALMENTE resueltos. Con el seguimiento de la frontera de fase
    #: `n_segments` es el numero NOMINAL: cada frontera cruzada recorta un
    #: segmento hasta ella y pasa el resto al siguiente, de modo que anade uno.
    n_segmentos: int = 0
    #: Fronteras de fase sobre las que se ha recortado. Es diagnostico: dice
    #: cuantas transiciones de regimen atraviesa el serpentin.
    n_recortes: int = 0
    T_surface_min: float = 0.0        # K
    T_surface_max: float = 0.0        # K
    eta_fin_wet: float | None = None
    eta_surface_wet: float | None = None
    U_star_mean: float = 0.0          # kg/(m2 s), potencial entalpico (10-35)
    # --- Diagnostico de regimen de condensacion, ap. 9.7.5 (tarea C9) ---
    condensation_regime: dict = field(default_factory=dict)
    Fr_so_range: tuple | None = None  # (min, max) del Froude de Soliman

    @property
    def regime_diagnosed(self) -> bool:
        """Cierto si la correlacion elegida distingue anular de estratificado.

        CLAUDE.md lo exige como salida. Con el agregado de ficha es falso: un
        coeficiente constante con el titulo no puede reproducir el reparto, y
        todo resultado apoyado en el debe declararlo."""
        return bool(self.condensation_regime.get("diagnosticado"))

    @property
    def SHR(self) -> float:
        """Factor de calor sensible. Vale 1 en superficie seca."""
        return self.Q_sensible / self.Q_dot if self.Q_dot else float("nan")

    @property
    def frost_domain(self) -> bool:
        """Cierto si alguna parte de la superficie esta bajo cero con el aire
        por encima de su rocio. Es el dato que el ap. 9.7.6 necesita para saber
        en que intervalos procede la penalizacion de la ec. 9-30; el serpentin
        se ha resuelto LIMPIO."""
        return self.frost_fraction > 0.0 and self.m_condensate > 0.0


class AirCoil(Component):
    """Serpentin aleteado de tubo de acero inoxidable y aleta de aluminio.

    La construccion aluminio / inoxidable responde a la restriccion RS-1 de la
    tabla 8.7, y es la razon por la que la resistencia de pared NO se desprecia
    (ap. 9.7.4): representa el 3.9 % del total frente al 0.15 % que
    correspondería a un tubo de cobre de la misma geometria.
    """

    name = "air_hx"

    def __init__(self, fluid: Fluid, geom: FinnedCoilGeometry,
                 n_segments: int = 200, corr: dict | None = None,
                 void_fraction_names: tuple = CORRELACIONES_HUECOS,
                 extrapolation: ExtrapolationLog | None = None,
                 phi_md: float = 1.0):
        self.fluid = fluid
        self.geom = geom
        self.n_segments = n_segments
        self.phi_md = phi_md
        self.void_fraction_names = tuple(void_fraction_names)
        self.log = extrapolation if extrapolation is not None else ExtrapolationLog()
        self.corr = {
            "airside": "colburn_anclada_cbn21",
            "fin": "schmidt_annular",
            "singlephase": "tube_dittus_boelter",
            # Familias de TUBO. Separadas de las de placas por el ap. 9.7.5,
            # que declara que las de placa corrugada «no son aplicables aqui».
            # `get()` lanza KeyError si se nombra una de placas: la separacion
            # no es documental, es estructural.
            "tube_condensation": "dobson_chato",
            "tube_boiling": "gungor_winterton",
        }
        if corr:
            self.corr.update(corr)

    # ------------------------------------------------------------------
    def air_side(self, air: AirState) -> tuple:
        """Coeficiente de pelicula del lado de aire, ec. 9-21 y 9-21."""
        g = self.geom
        V_max = max_velocity(air.V_frontal, g.sigma)
        Re = reynolds_Dc(air.rho, V_max, g.d_c, air.mu)
        self.log.check("airside", self.corr["airside"], Re_Dc=Re)
        j = get("airside", self.corr["airside"])(Re)
        return alpha_from_colburn(j, air.rho * V_max, air.cp, air.Pr), Re

    @staticmethod
    def two_phase_regime(T_sat: float, T_air: float,
                         role: str | None = None) -> str:
        """Ebullicion o condensacion en el volumen de control bifasico.

        Se despacha por el PAPEL del componente en el modo activo cuando el
        circuito lo declara: el ap. 9.3 fija si la bateria condensa o evapora
        en cada uno de los cinco modos, y esa informacion existe antes de
        iterar. Sin papel declarado, el respaldo es el signo de (T_aire - T_sat),
        disponible en la primera iteracion y fisicamente correcto.
        """
        if role in ("evaporator", "evaporador"):
            return "ebullicion"
        if role in ("condenser", "condensador"):
            return "condensando"
        return "ebullicion" if T_air >= T_sat else "condensando"

    def fin_efficiency(self, h_air: float, b_prime: float | None = None,
                       cp_a: float = 1006.0) -> tuple:
        """Eficiencia de aleta y efectividad superficial, ec. 9-22 y 9-29."""
        g = self.geom
        eta = get("fin", self.corr["fin"])(
            h_air, g.k_fin, g.fin_thickness, g.r_collar, g.r_equivalent,
            b_prime=b_prime, cp_a=cp_a)
        return eta, surface_effectiveness(eta, g.fin_area_fraction)

    def overall_resistance(self, h_ref: float, h_air: float,
                           eta_surface: float) -> dict:
        """Reparto de resistencias referido al area externa, ec. 9-23.

        Reproduce la tabla 9.18. La resistencia de pared se conserva
        explicitamente: omitirla seria incoherente con el nivel de resolucion
        adoptado en el resto del capitulo, siendo del orden de la sexta parte de
        la del lado de refrigerante.
        """
        g = self.geom
        R_air = 1.0 / (eta_surface * h_air)
        R_wall = (math.log(g.d_o / g.d_i)
                  / (2.0 * math.pi * g.k_tube * g.L_tube) * g.A_o)
        R_ref = g.area_ratio / max(h_ref, 1e-9)
        total = R_air + g.R_contact + R_wall + R_ref
        return {"aire": R_air, "contacto": g.R_contact, "pared": R_wall,
                "refrigerante": R_ref, "total": total, "U": 1.0 / total,
                "peso_aire": R_air / total, "peso_pared": R_wall / total,
                "peso_refrigerante": R_ref / total}

    # ------------------------------------------------------------------
    # Superficie humeda por potencial entalpico. Ap. 9.7.6, tarea C5.
    # ------------------------------------------------------------------
    def wet_conductance(self, h_ref: float, h_air: float, T_ref: float,
                        T_surface: float, cp_da: float,
                        P: float = psy.P_ATM) -> dict:
        """Conductancia global en base ENTALPICA, ec. 9-28.

        Devuelve U* en kg/(m2 s), no en W/(m2 K): la fuerza impulsora es una
        diferencia de entalpias del aire en J/kg, de modo que U* Dh da W/m2. Es
        el cambio de potencial que caracteriza al metodo, y por eso las unidades
        cambian; tratar U* como si fuese un coeficiente de pelicula es el error
        que el ap. 9.12.4 advierte que produce resultados verosimiles y
        equivocados.

        Cada resistencia se pondera por la pendiente de la curva de saturacion
        del tramo que atraviesa (metodo de Threlkeld):

            1/U* = c_p,a/(eta_sa,w h_a) + b'_w (R_pared + R_contacto) + b'_r R_ref

        con b'_w evaluada en la temperatura superficial y b'_r en la del
        refrigerante. Con la pared pesando el 3.9 % del total, la eleccion entre
        una y otra en ese termino es inmaterial; se declara por precision.

        La eficiencia de aleta se recalcula con `b_prime = b'_w`, que es la
        correccion de la ec. 9-29: usar la eficiencia SECA aqui sobreestimaria
        la conductancia del evaporador un 28 % (ap. 9.7.6).
        """
        g = self.geom
        b_w = psy.saturation_enthalpy_slope(T_surface, P)
        b_r = psy.saturation_enthalpy_slope(T_ref, P)
        eta_f, eta_sa = self.fin_efficiency(h_air, b_prime=b_w, cp_a=cp_da)
        R_air = cp_da / (eta_sa * h_air)
        R_wall = (math.log(g.d_o / g.d_i)
                  / (2.0 * math.pi * g.k_tube * g.L_tube) * g.A_o)
        R_metal = b_w * (R_wall + g.R_contact)
        R_ref = b_r * g.area_ratio / max(h_ref, 1e-9)
        total = R_air + R_metal + R_ref
        return {"aire": R_air, "metal": R_metal, "refrigerante": R_ref,
                "total": total, "U_star": 1.0 / total,
                "b_superficie": b_w, "b_refrigerante": b_r,
                "eta_fin": eta_f, "eta_surface": eta_sa,
                "R_metal_seca": R_wall + g.R_contact,
                "R_ref_seca": g.area_ratio / max(h_ref, 1e-9)}

    def dry_surface_temperature(self, air_T: float, T_ref: float,
                                res: dict) -> float:
        """Temperatura de la superficie externa suponiendola seca.

        Se toma como temperatura de la BASE de la aleta: el extremo esta mas
        cerca del aire y por tanto mas caliente en evaporacion, de modo que el
        criterio es conservador en el sentido de declarar humeda la superficie
        algo antes de lo que lo haria un calculo bidimensional. La eleccion se
        arrastra al cap. 10 junto con el metodo de aleta equivalente.
        """
        f = (res["refrigerante"] + res["pared"] + res["contacto"]) / res["total"]
        return T_ref + (air_T - T_ref) * f

    def _wet_cell(self, h_ref: float, h_air: float, T_ref: float,
                  air: AirState, dm_dry: float, dA: float,
                  T_surface_0: float, C_ref: float | None,
                  tol: float = 1e-4, it_max: int = 40) -> dict:
        """Resuelve una celda de superficie humeda.

        Itera sobre la temperatura superficial porque de ella dependen a la vez
        la pendiente b' y la eficiencia de aleta, exactamente como el lazo
        interno del ap. 9.6.3 itera sobre la temperatura de pared. `C_ref` es
        la capacidad calorifica del refrigerante en base entalpica —None cuando
        cambia de fase y el potencial de saturacion es por tanto invariante.
        """
        cp_da = air.cp_da
        h_a_in = air.h
        h_s_ref = psy.saturation_enthalpy(T_ref, air.P)
        T_s = T_surface_0
        res = dQ = q = 0.0
        for _ in range(it_max):
            res = self.wet_conductance(h_ref, h_air, T_ref, T_s, cp_da, air.P)
            if C_ref is None:
                Cr, C_min = 0.0, dm_dry
            else:
                C_eq = C_ref / res["b_refrigerante"]      # kg/s equivalentes
                C_min, C_max = min(C_eq, dm_dry), max(C_eq, dm_dry)
                Cr = C_min / C_max
            eps = self._effectiveness(res["U_star"] * dA / C_min, Cr)
            dQ = eps * C_min * (h_a_in - h_s_ref)
            q = dQ / dA
            h_s_w = h_s_ref + q * (res["metal"] + res["refrigerante"])
            T_new = psy.saturation_temperature(h_s_w, air.P)
            if abs(T_new - T_s) < tol:
                T_s = T_new
                break
            T_s += 0.7 * (T_new - T_s)

        # Estado de salida del aire. La temperatura tiende a la de la
        # superficie, no a la del refrigerante: es la superficie la que fija la
        # linea de condicion del aire en regimen humedo.
        NTU_a = res["eta_surface"] * h_air * dA / (dm_dry * cp_da)
        T_a_out = T_s + (air.T - T_s) * math.exp(-NTU_a)
        h_a_out = h_a_in - dQ / dm_dry
        w_out = psy.humidity_from_enthalpy(h_a_out, T_a_out)
        w_out = min(w_out, psy.w_saturation(T_a_out, air.P), air.w)
        dQ_sens = dm_dry * cp_da * (air.T - T_a_out)
        return {"dQ": dQ, "dQ_sens": dQ_sens, "dQ_lat": dQ - dQ_sens,
                "T_s": T_s, "T_a_out": T_a_out, "h_a_out": h_a_out,
                "w_out": w_out, "dm_cond": dm_dry * (air.w - w_out),
                "res": res, "U_star": res["U_star"]}

    # ------------------------------------------------------------------
    def _h_ref(self, P: float, h: float, G: float, q_flux: float = 0.0,
               T_wall: float | None = None, T_air: float | None = None,
               role: str | None = None) -> tuple:
        """Coeficiente del lado de refrigerante, regimen local y diagnostico.

        Devuelve `(alpha, x, sat, regimen, diag, check)`. NO anota el registro
        de extrapolacion: devuelve la comprobacion pendiente en `check` para que
        la anote el lazo de `solve()` UNA VEZ CONVERGIDO. Anotarla aqui
        registraria la trayectoria de convergencia como si fuera un resultado,
        que es justo lo que el ap. 9.7.5 no puede usar.

        `q_flux` es el flujo de calor referido al AREA INTERNA, que es la de las
        correlaciones de tubo, y `T_wall` la temperatura de la pared interior.
        Los dos cierran el acoplamiento implicito: la ec. 9-27 depende de q''
        por el numero de ebullicion y la rama estratificada de la ec. 9-24
        depende de la pared por el numero de Jakob.
        """
        f = self.fluid
        sat = f.sat_props(P)
        sat["p_red"] = f.p_reduced(P)
        h_l, h_v = sat["h_l"], sat["h_v"]
        g = self.geom
        diag = {}

        if h >= h_v:                                     # vapor sobrecalentado
            Re = reynolds(G, g.d_i, sat["mu_v"])
            a = get("singlephase", self.corr["singlephase"])(
                Re, sat["Pr_v"], sat["k_v"], g.d_i, heating=False)
            return a, 1.0, sat, "vapor", diag, [
                ("singlephase", self.corr["singlephase"],
                 {"Re": Re, "Pr": sat["Pr_v"]})]
        if h <= h_l:                                     # liquido subenfriado
            Re = reynolds(G, g.d_i, sat["mu_l"])
            a = get("singlephase", self.corr["singlephase"])(
                Re, sat["Pr_l"], sat["k_l"], g.d_i, heating=False)
            return a, 0.0, sat, "liquido", diag, [
                ("singlephase", self.corr["singlephase"],
                 {"Re": Re, "Pr": sat["Pr_l"]})]

        x = (h - h_l) / (h_v - h_l)                      # bifasico
        modo = self.two_phase_regime(sat["Tsat"], T_air if T_air is not None
                                     else sat["Tsat"], role)
        # El numero de Froude de Soliman se evalua SIEMPRE, tambien en
        # ebullicion y tambien si la correlacion elegida no lo usa: es una
        # propiedad del flujo (ec. 9-25), no de la correlacion, y el ap. 9.7.5
        # lo pide como magnitud de diagnostico.
        diag["Fr_so"] = soliman_froude(x, G, sat, g.d_i)

        if modo == "ebullicion":
            name = self.corr["tube_boiling"]
            a = get("tube_boiling", name)(
                x, G, q_flux, sat, f.M, g)
            check = [("tube_boiling", name,
                      {"G": G, "x": x, "p_red": sat["p_red"], "d_i": g.d_i})]
            return a / self.phi_md, x, sat, "ebullicion", diag, check

        name = self.corr["tube_condensation"]
        fn = get("tube_condensation", name)
        con_regimen = getattr(fn, "regime", None)
        if con_regimen is not None:
            a, sub, _ = con_regimen(x, G, sat, g, T_wall=T_wall)
        else:
            # La correlacion elegida no distingue regimenes. El diagnostico se
            # reporta igualmente, porque Fr_so lo determina, pero se marca que
            # el coeficiente NO lo honra.
            a = fn(x, G, sat, g)
            sub = "sin_diagnostico"
        diag["subregimen"] = sub
        check = [("tube_condensation", name,
                  {"T_sat": sat["Tsat"], "G": G, "x": x, "d_i": g.d_i})]
        return a / self.phi_md, x, sat, "condensando", diag, check

    @staticmethod
    def _effectiveness(NTU: float, Cr: float) -> float:
        """Efectividad en flujo cruzado, ambos fluidos no mezclados.

            eps = 1 - exp[ NTU^0.22 / Cr (exp(-Cr NTU^0.78) - 1) ]

        Con Cr = 0 (refrigerante isotermo en cambio de fase) degenera en
        1 - exp(-NTU), que es el limite correcto.
        """
        if NTU <= 0.0:
            return 0.0
        if Cr < 1e-6:
            return 1.0 - math.exp(-NTU)
        return 1.0 - math.exp(NTU ** 0.22 / Cr
                              * (math.exp(-Cr * NTU ** 0.78) - 1.0))

    # ------------------------------------------------------------------
    @staticmethod
    def _frontera_interior(h, h_new, sat, margen=1e-4):
        """Entalpia de la frontera de fase que el segmento CRUZA por dentro.

        Misma logica que en `plate_hx`: devuelve `None` si no cruza ninguna, o
        si la cruza tan cerca de un extremo que recortar generaria un segmento
        degenerado —el caso justo despues de un recorte, cuando la marcha
        arranca sobre la frontera y se aleja de ella—. Si cruzase las dos,
        devuelve la primera en el sentido de la marcha.
        """
        salto = h_new - h
        if salto == 0.0:
            return None
        candidatas = []
        for h_b in (sat["h_l"], sat["h_v"]):
            frac = (h_b - h) / salto
            if margen < frac < 1.0:
                candidatas.append((frac, h_b))
        if not candidatas:
            return None
        return min(candidatas)[1]

    def _solve_segment(self, P, h, m_dot, G, dA, dm_air, dm_dry, air, T_dew,
                       h_air, eta_sa, role, a_seed=3000.0):
        """Un segmento de area `dA`, con su lazo interno sobre q'' (ap. 9.7.2).

        Esta extraido del marchador porque el recorte en la frontera de fase
        necesita reresolver el MISMO segmento con otra area, y el caudal de aire
        que le corresponde es proporcional a ella: la marcha reparte el aire en
        corrientes paralelas, de modo que un segmento que ocupa la mitad del
        area recibe la mitad del caudal.
        """
        g = self.geom
        q_i = 0.0                     # W/m2 referidos al AREA INTERNA
        T_wall = None
        a_ref = a_seed
        cell = None
        for _ in range(30):
            a_ref, x, sat, regime, diag, checks = self._h_ref(
                P, h, G, q_flux=q_i, T_wall=T_wall, T_air=air.T, role=role)
            res = self.overall_resistance(a_ref, h_air, eta_sa)
            U = res["U"]

            self.fluid.update_PH(P, h)
            T_r, rho = self.fluid.T, self.fluid.rho

            C_air = dm_air * air.cp
            if regime in ("condensando", "ebullicion"):
                Cr, C_min, C_ref = 0.0, C_air, None
            else:
                C_ref = m_dot * self.fluid.cp
                C_min, C_max = min(C_ref, C_air), max(C_ref, C_air)
                Cr = C_min / C_max
            eps = self._effectiveness(U * dA / C_min, Cr)
            dQ = eps * C_min * (air.T - T_r)    # negativo: el gas se enfria
            T_s = self.dry_surface_temperature(air.T, T_r, res)

            cell = None
            if T_s < T_dew:                      # ec. 9-28, pared humeda
                cell = self._wet_cell(a_ref, h_air, T_r, air, dm_dry, dA,
                                      T_s, C_ref)
                dQ, T_s = cell["dQ"], cell["T_s"]

            q_new = dQ / dA * g.area_ratio
            T_wall = T_r + q_new / max(a_ref, 1e-9)
            if abs(q_new - q_i) < 1e-3 * max(abs(q_new), 1.0):
                q_i = q_new
                break
            q_i = 0.5 * q_i + 0.5 * q_new

        return {"dQ": dQ, "T_s": T_s, "cell": cell, "U": U, "a_ref": a_ref,
                "x": x, "sat": sat, "regime": regime, "diag": diag,
                "checks": checks, "T_r": T_r, "rho": rho, "C_air": C_air}

    def solve(self, P: float, h_in: float, m_dot: float, air: AirState,
              m_dot_air: float, role: str | None = None) -> CoilResult:
        """Marcha por segmentos a lo largo del camino del refrigerante.

        Se marcha sobre el AREA REAL del componente, no sobre un area requerida:
        el estado de salida —y con el el subenfriamiento, que es el que mas pesa
        en el inventario— resulta de la marcha en lugar de imponerse. Es la
        diferencia entre calcular la carga y suponerla.

        La perdida de carga del lado de refrigerante se desprecia aqui: la ficha
        declara 2.62 kPa frente a los 17.8 bar de la condensacion, esto es un
        0.15 %. La ec. 9-20 completa corresponde a la tarea C4.

        REGIMEN DE LA SUPERFICIE (ap. 9.7.6, tarea C5). Cada celda se resuelve
        primero en seco; si la temperatura superficial que resulta cae por
        debajo del punto de rocio del aire, la celda se vuelve a resolver por
        potencial entalpico. La decision es por celda y no por componente: en el
        dominio de calefaccion la parte final del serpentin puede estar seca
        mientras la inicial condensa, y agregarlas bajo un solo regimen es
        exactamente lo que el reporte separado de sensible y latente permite
        evitar.

        LAZO INTERNO POR CELDA (ap. 9.7.2, tarea C4). Con las correlaciones de
        tubo el coeficiente del lado de refrigerante deja de ser explicito: la
        ec. 9-27 depende del flujo de calor por el numero de ebullicion y la
        rama estratificada de la ec. 9-24 depende de la temperatura de pared
        por el numero de Jakob. Cada celda itera por tanto sobre q'' hasta
        convergencia, como el lazo interno del ap. 9.6.3, y solo entonces se
        anota el registro de extrapolacion.

        `role` declara el papel del componente en el modo activo —'evaporator' o
        'condenser'— y lo pasa `circuit.py`. Sin el, el respaldo es el signo de
        (T_aire - T_sat), que da el mismo resultado.
        """
        g = self.geom
        n = self.n_segments
        dA_nom = g.A_o / n
        m_dry_total = air.dry_mass_flow(m_dot_air)
        G = g.mass_flux(m_dot)
        T_dew = air.T_dew

        h_air, _ = self.air_side(air)
        eta_fin, eta_sa = self.fin_efficiency(h_air)
        self.log.check("fin", self.corr["fin"])

        h = h_in
        Q_total = Q_sens = Q_lat = m_cond = 0.0
        T_air_out_acc = h_air_out_acc = w_air_out_acc = 0.0
        A_wet = A_frost = 0.0
        eta_fin_acc = eta_sa_acc = 0.0
        T_s_min, T_s_max = math.inf, -math.inf
        cells, x_prof, U_acc = [], [], 0.0
        self.fluid.update_PH(P, h_in)
        perfil = {"A": [0.0], "T_ref": [self.fluid.T], "T_aire_sal": [],
                  "T_sup": []}
        U_star_acc = 0.0
        n_recortes = 0
        vol = {"vapor": 0.0, "condensando": 0.0, "ebullicion": 0.0,
               "liquido": 0.0}
        duty = {"vapor": 0.0, "condensando": 0.0, "ebullicion": 0.0,
                "liquido": 0.0}
        # Diagnostico de regimen de condensacion (ap. 9.7.5, tarea C9): que
        # fraccion del serpentin condensa en anular y cual en estratificado.
        sub_vol, sub_duty = {}, {}
        Fr_min, Fr_max = math.inf, -math.inf
        checks, diag = [], {}

        # SEGUIMIENTO DE LA FRONTERA DE FASE. Igual que en `plate_hx` desde el
        # 21/09/2026: cuando un segmento cruzaria por dentro el titulo 0 o 1 se
        # RECORTA hasta la frontera y el resto del area pasa al siguiente.
        #
        # No es refinamiento por gusto. Con areas fijas, el punto en que termina
        # la evaporacion cae en un segmento o en el siguiente segun el punto de
        # operacion, y el estado de salida SALTA al cruzar ese umbral. Medido en
        # M-4 con 60 segmentos: un cambio de 1e-7 en log(P0) —0.04 Pa— mueve la
        # frontera un segmento, el reparto de volumen pasa de 0.1167 a 0.1000 y
        # el recalentamiento de salida da un salto de 2.4 K. El lazo externo del
        # ap. 9.4 no puede cruzar ese escalon: se detiene sobre el con un
        # residuo de 3e-3, tres ordenes por encima de la tolerancia del
        # ap. 9.4.4.
        #
        # El caudal de aire de cada segmento es PROPORCIONAL a su area: la
        # marcha trata el aire como corrientes paralelas (ver la cabecera del
        # modulo), de modo que un segmento recortado recibe la parte que le
        # corresponde y el caudal total se conserva.
        A_left = g.A_o
        a_seed = 3000.0
        # Cota de seguridad: cada frontera anade un segmento, y solo hay dos.
        max_seg = n + 8
        while A_left > 1e-12 * g.A_o and len(cells) < max_seg:
            dA = min(dA_nom, A_left)
            frac = dA / g.A_o
            res_seg = self._solve_segment(
                P, h, m_dot, G, dA, m_dot_air * frac, m_dry_total * frac,
                air, T_dew, h_air, eta_sa, role, a_seed)
            h_new = h + res_seg["dQ"] / m_dot

            # --- recorte en la frontera de fase --------------------------
            h_b = self._frontera_interior(h, h_new, res_seg["sat"])
            if h_b is not None:
                for _ in range(6):
                    salto = h_new - h
                    if abs(salto) < 1e-9:
                        break
                    dA = max(min(dA * (h_b - h) / salto, A_left),
                             1e-9 * g.A_o)
                    frac = dA / g.A_o
                    res_seg = self._solve_segment(
                        P, h, m_dot, G, dA, m_dot_air * frac,
                        m_dry_total * frac, air, T_dew, h_air, eta_sa, role,
                        a_seed)
                    h_new = h + res_seg["dQ"] / m_dot
                    if abs(h_new - h_b) < 1e-6 * max(abs(h_b - h), 1.0):
                        break
                # La frontera se impone EXACTAMENTE, para que el segmento
                # siguiente arranque sobre ella y el balance no arrastre deriva.
                h_new = h_b
                # ...y un paso DESPRECIABLE (1e-9 del calor latente) hacia la fase en la
                # que sigue el proceso. Corregido el 29/09/2026: arrancando EXACTAMENTE sobre
                # h_v, el volumen siguiente de un condensador se clasificaba como vapor
                # (`h >= h_v`) y marchaba entero con el coeficiente monofasico, un error
                # proporcional a 1/N; igual al arrancar sobre h_l un evaporador. En las placas
                # lo tapaba la presion decreciente, que movia h_v por azar; con presion
                # uniforme (M8) aparecio: 7 % con 10 volumenes. La clasificacion la decide
                # ahora el SENTIDO de la marcha, no el redondeo.
                h_new += math.copysign(1e-9 * (res_seg["sat"]["h_v"] - res_seg["sat"]["h_l"]), h_b - h)
                n_recortes += 1

            dV = g.V_internal * frac
            dQ_seg = res_seg["dQ"]
            dQ = (h_new - h) * m_dot
            # Al imponer la frontera, el calor del segmento cambia en la ultima
            # cifra. Las contribuciones sensible y latente se reescalan en la
            # misma proporcion para que su suma siga siendo el calor del
            # segmento: si no, el reparto SHR deja de cerrar tras un recorte.
            escala = dQ / dQ_seg if dQ_seg != 0.0 else 1.0
            a_ref, x, sat = res_seg["a_ref"], res_seg["x"], res_seg["sat"]
            regime, diag, checks = (res_seg["regime"], res_seg["diag"],
                                    res_seg["checks"])
            cell, T_s, U = res_seg["cell"], res_seg["T_s"], res_seg["U"]
            C_air, rho = res_seg["C_air"], res_seg["rho"]
            a_seed = a_ref

            # El registro anota SOLO la iteracion convergida.
            for c in checks:
                self.log.check(c[0], c[1], **c[2])
            sub = diag.get("subregimen")
            if sub:
                sub_vol[sub] = sub_vol.get(sub, 0.0) + dV
                sub_duty[sub] = sub_duty.get(sub, 0.0) + dQ
            if "Fr_so" in diag:
                Fr_min = min(Fr_min, diag["Fr_so"])
                Fr_max = max(Fr_max, diag["Fr_so"])

            if cell is not None:                     # pared humeda
                # U_mean conserva SIEMPRE el significado de conductancia global
                # sobre diferencia de temperaturas —la magnitud de la tabla
                # 9.20 y la comparable con los 38.2 de condensacion—, pero con
                # la efectividad superficial HUMEDA de la celda. El potencial
                # entalpico se reporta aparte, en `U_star_mean`, porque sus
                # unidades son otras: kg/(m2 s), no W/(m2 K).
                # Desde el recorte en la frontera de fase los segmentos NO son
                # iguales, de modo que todo lo que antes se promediaba por
                # recuento se acumula ahora pesado por AREA. Con segmentos
                # iguales da exactamente lo mismo.
                U_acc += self.overall_resistance(
                    a_ref, h_air, cell["res"]["eta_surface"])["U"] * dA
                U_star_acc += cell["U_star"] * dA
                A_wet += dA
                Q_sens += cell["dQ_sens"] * escala
                Q_lat += cell["dQ_lat"] * escala
                m_cond += cell["dm_cond"] * escala
                # Los estados de salida del aire se reescalan sobre su SALTO
                # respecto de la entrada, no en valor absoluto.
                T_a_out = air.T + (cell["T_a_out"] - air.T) * escala
                T_air_out_acc += T_a_out * dA
                h_air_out_acc += (air.h + (cell["h_a_out"] - air.h)
                                  * escala) * dA
                w_air_out_acc += (air.w + (cell["w_out"] - air.w)
                                  * escala) * dA
                eta_fin_acc += cell["res"]["eta_fin"] * dA
                eta_sa_acc += cell["res"]["eta_surface"] * dA
                if T_s < psy.T0:
                    A_frost += dA
            else:                                    # marcha en seco
                U_acc += U * dA
                T_a_out = air.T - dQ / C_air
                Q_sens += dQ
                T_air_out_acc += T_a_out * dA
                h_air_out_acc += psy.enthalpy(T_a_out, air.w) * dA
                w_air_out_acc += air.w * dA

            T_s_min, T_s_max = min(T_s_min, T_s), max(T_s_max, T_s)
            Q_total += dQ
            vol[regime] += dV
            duty[regime] += dQ
            cells.append({"x": x, "rho": rho, "sat": sat, "V": dV,
                          "regime": regime, "A": dA})
            x_prof.append(x)
            A_left -= dA
            h = h_new
            self.fluid.update_PH(P, h)
            perfil["A"].append(perfil["A"][-1] + dA)
            perfil["T_ref"].append(self.fluid.T)
            perfil["T_aire_sal"].append(T_a_out)
            perfil["T_sup"].append(T_s)

        x_prof = np.array(x_prof)

        self.fluid.update_PH(P, h)
        T_out = self.fluid.T
        sat = self.fluid.sat_props(P)
        subcooling = max(sat["Tsat"] - T_out, 0.0) if h < sat["h_l"] else 0.0

        return CoilResult(
            Q_dot=Q_total, h_ref_out=h, T_ref_out=T_out,
            T_air_out=T_air_out_acc / g.A_o, U_mean=U_acc / g.A_o, h_air=h_air,
            eta_fin=eta_fin, eta_surface=eta_sa, subcooling=subcooling,
            volume_fraction={k: v / g.V_internal for k, v in vol.items()},
            duty_fraction={k: v / Q_total for k, v in duty.items()},
            charge=self._charge_from_cells(cells), x_profile=x_prof,
            profile={k: np.array(v) for k, v in perfil.items()},
            extrapolated=self.log.extrapolated, excursions=self.log.excursions,
            condensation_regime={
                "volumen": {k: v / max(sum(sub_vol.values()), 1e-30)
                            for k, v in sub_vol.items()},
                # La carga de la zona bifasica es NEGATIVA al condensar, de
                # modo que el reparto se toma en valor absoluto: lo que se
                # reporta es que fraccion de la carga pasa por cada regimen, no
                # su signo, que es el mismo para todos.
                "carga": {k: abs(v) / max(sum(abs(u) for u in
                                              sub_duty.values()), 1e-30)
                          for k, v in sub_duty.items()},
                "diagnosticado": bool(sub_vol) and "sin_diagnostico" not in sub_vol},
            Fr_so_range=((Fr_min, Fr_max) if Fr_max > -math.inf else None),
            Q_sensible=Q_sens, Q_latent=Q_lat, m_condensate=m_cond,
            w_air_out=w_air_out_acc / g.A_o, h_air_out=h_air_out_acc / g.A_o,
            wet_fraction=A_wet / g.A_o, frost_fraction=A_frost / g.A_o,
            n_segmentos=len(cells), n_recortes=n_recortes,
            T_surface_min=T_s_min, T_surface_max=T_s_max,
            # Las magnitudes de regimen humedo se promedian sobre el AREA
            # humeda, no sobre el componente entero: promediarlas sobre toda la
            # superficie diluiria la efectividad humeda con segmentos secos.
            eta_fin_wet=(eta_fin_acc / A_wet) if A_wet > 0.0 else None,
            eta_surface_wet=(eta_sa_acc / A_wet) if A_wet > 0.0 else None,
            U_star_mean=(U_star_acc / A_wet) if A_wet > 0.0 else 0.0)

    # ------------------------------------------------------------------
    def _charge_from_cells(self, cells) -> dict:
        """Inventario por integracion, ec. 9-32 y 9-32.

        Devuelve el RANGO de las correlaciones configuradas, nunca un valor
        unico (ap. 9.9). A diferencia de la tabla 9.21, que integra
        suponiendo bifasico en todo el volumen, aqui cada segmento aporta la
        densidad de SU regimen: vapor sobrecalentado y liquido subenfriado
        entran con su densidad monofasica.
        """
        names = self.void_fraction_names
        totals = {nm: 0.0 for nm in names}
        for c in cells:
            if c["regime"] in ("condensando", "ebullicion"):
                rr = charge_range(c["x"], c["sat"], self.geom.mass_flux(1.0),
                                  self.geom.d_i, names=names)
                for nm in names:
                    totals[nm] += rr[nm]["rho_mean"] * c["V"]
            else:
                for nm in names:
                    totals[nm] += c["rho"] * c["V"]
        totals["_min"] = min(totals[nm] for nm in names)
        totals["_max"] = max(totals[nm] for nm in names)
        totals["_spread"] = (totals["_max"] / totals["_min"]
                             if totals["_min"] > 0 else float("nan"))
        return totals

    # ------------------------------------------------------------------
    def fan_power(self, dp_total_Pa: float | None = None, df=None) -> float:
        """Consumo del ventilador. Entra en el denominador de COP y EER (§9.7.7).

        MODELO DE CONSUMO CONSTANTE, decision del autor del 17/09/2026. Se
        renuncia a resolver el ventilador sobre su curva caracteristica: el
        caudal de aire y la perdida de carga varian poco entre condiciones de
        operacion, de modo que el consumo se trata como invariante y se toma de
        los datos del fabricante.

        Devuelve 780 W, consumo de la serie CBN a alta velocidad con el motor en
        triangulo. Es potencia electrica ABSORBIDA, que es justo la magnitud que
        pide la UNE-EN 14511: no hay que suponer ningun rendimiento para
        llevarla al denominador.

        El dato se corrobora por dos vias independientes. Con el eta = 0.30 que
        adopta el §9.7.7 equivale a 110.8 Pa, dentro de la banda 80-120 Pa que
        ese apartado estima para el conjunto montado; y a la inversa, si la
        perdida de carga fuese la de la bateria sola (42 Pa) el rendimiento
        implicito seria 0.114, inverosimil en un axial. Las dos dicen lo mismo:
        los 780 W son el conjunto con envolvente y rejilla RS-4.

        Ya NO es una cota inferior. Los 296 W anteriores si lo eran, y se
        conservan en el fichero de datos como extremo favorable de la banda.

        `dp_total_Pa` recalcula por la §9.7.7, W = V dp / eta, para la campana
        de sensibilidad del ap. 6.11. Esa via si depende del eta adoptado.

        Queda fuera de este modelo, y se declara: el efecto de la escarcha sobre
        la perdida de carga, que en un ventilador de caudal no regulado reduce
        el caudal a lo largo del ciclo de acumulacion (§9.7.7).
        """
        from .. import data as D

        df = df or D.air_coil()
        if dp_total_Pa is None:
            return df.require("ventilador.potencia_W")
        V = df.require("ventilador.caudal_m3_h") / 3600.0
        return V * dp_total_Pa / df.require("ventilador.rendimiento_conjunto")

    def fan_power_is_lower_bound(self, df=None) -> bool:
        """Cierto mientras el consumo proceda de la perdida de carga de la
        bateria sola, sin envolvente ni rejilla. Es la marca que debe acompanar
        a todo EER reportado.

        Falso desde el 17/09/2026: el consumo es dato de catalogo del conjunto.
        El metodo se conserva porque la marca tiene que seguir viajando con el
        resultado, y porque la sensibilidad del ap. 6.11 puede volver a poner el
        modelo sobre los 296 W de la bateria desnuda."""
        from .. import data as D

        return bool((df or D.air_coil()).require("ventilador.es_cota_inferior"))
