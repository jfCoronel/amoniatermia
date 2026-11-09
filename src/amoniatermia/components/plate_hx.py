"""Intercambiador de placas por volumenes finitos.

Apartado 9.6, ecuaciones 9-11 a 9-20.

Se adopta la formulacion de volumenes finitos y no la de parametros agrupados
por tres razones (apartado 6.6.1):
  - H3 exige resolver la zona de vapor sobrecalentado del desrecalentador de
    forma diferenciada de la zona de condensacion.
  - H4 requiere el inventario de carga por componente, que exige conocer la
    distribucion local del titulo de vapor.
  - H5 solo es defendible si las diferencias de transferencia entre
    refrigerantes se capturan localmente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from .base import Component
from ..geometry import PlateGeometry
from ..props import Fluid
from ..correlations import get, ExtrapolationLog
from ..correlations.condensation import wet_wall_UA
from ..correlations.singlephase import reynolds
from ..correlations.voidfraction import charge_range, mean_density, CORRELACIONES_HUECOS

#: Presion a la que se evaluan las propiedades del AGUA [Pa]. 24/09/2026: era
#: 2 bar, y con el balance del agua en entalpia (ec. 9-11) el lazo de disparo
#: del contracorriente exploraba temperaturas por encima de los 120 C de
#: saturacion a esa presion, donde CoolProp devuelve vapor o falla. Con el cp
#: lineal de antes no se notaba, pero `_alpha_sec` ya evaluaba entonces
#: propiedades de vapor sin decirlo. A 10 bar la saturacion queda en 180 C,
#: por encima de cualquier descarga del dominio, y en liquido comprimido la
#: presion apenas mueve las propiedades (rho +0.04 %, cp -0.05 % de 2 a 10 bar).
P_AGUA = 1.0e6


@dataclass
class HXResult:
    Q_dot: float                 # W (positivo: calor absorbido por el refrigerante)
    h_ref_out: float             # J/kg
    T_sec_out: float             # K
    dP_ref: float                # Pa
    #: Reparto de la perdida de carga por contribuciones (ec. 9-20). El
    #: ap. 9.6.6 conserva la gravitatoria expresamente, de modo que reportar
    #: solo el total impediria comprobar que se ha conservado.
    dP_parts: dict = field(default_factory=dict)
    #: Salto de saturacion [K] equivalente a `dP_ref`: la comprobacion a
    #: posteriori de la hipotesis M8 (presion uniforme a efectos de propiedades).
    dT_sat_equivalente: float = 0.0
    x_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    alpha_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    #: Perfil a lo largo del recorrido del REFRIGERANTE, para representar la
    #: discretizacion: `A` es el area acumulada en los nudos (N+1 valores, de 0
    #: al area total), `T_ref` y `T_sec` las temperaturas en esos nudos, y
    #: `T_pared` la de la pared del lado de refrigerante en cada volumen (N).
    profile: dict = field(default_factory=dict)
    wet_wall_fraction: float = 0.0
    #: Volumenes REALMENTE resueltos. Desde el seguimiento de la frontera de
    #: fase, `n_cells` es el numero NOMINAL: cada frontera cruzada recorta un
    #: volumen hasta ella y pasa el resto al siguiente, de modo que anade uno.
    n_volumenes: int = 0
    #: Fronteras de fase sobre las que se ha recortado. Es diagnostico: dice
    #: cuantas transiciones de regimen atraviesa el componente.
    n_recortes: int = 0
    charge: dict = field(default_factory=dict)
    energy_balance_error: float = 0.0
    converged: bool = True
    #: Cierto si alguna correlacion ha operado fuera de su base experimental
    #: declarada, o carece de base declarada. CLAUDE.md exige marcarlo, no
    #: silenciarlo: un resultado extrapolado no es un resultado invalido, pero
    #: tampoco es un resultado soportado.
    extrapolated: bool = False
    excursions: list = field(default_factory=list)


class PlateHeatExchanger(Component):
    """Intercambiador de placas a contracorriente, marcha por volumenes.

    Parameters
    ----------
    fluid : Fluid            Refrigerante
    sec_fluid : Fluid        Fluido secundario (agua)
    geom : PlateGeometry
    n_cells : int            Numero de volumenes de control
    corr : dict              Nombres de correlaciones a emplear. Cambiar una
                             correlacion NO requiere tocar este codigo: es lo
                             que hace viable la sensibilidad del ap. 6.11.
    """

    #: Tolerancia relativa del punto fijo sobre q'' en cada volumen (ap.
    #: 9.4.3). Se probo 1e-6 el 24/09/2026 por si el salto entre el punto fijo
    #: y el respaldo por intervalo de `_solve_cell` ensuciaba el residuo: no lo
    #: hacia —el ruido venia del compresor— y costaba un 40 % mas de tiempo con
    #: la misma convergencia en todos los modos. Se queda en 1e-3.
    TOL_Q = 1.0e-3

    name = "plate_hx"

    def __init__(self, fluid: Fluid, sec_fluid: Fluid, geom: PlateGeometry,
                 n_cells: int = 30, corr: dict | None = None,
                 phi_md: float = 1.0,
                 void_fraction_names: tuple = CORRELACIONES_HUECOS,
                 extrapolation: ExtrapolationLog | None = None,
                 role: str | None = None,
                 corr_params: dict | None = None,
                 Z_wet: float = 1.0,
                 vertical: bool = True,
                 flow_upward: bool | None = None,
                 dT_mean: str = "lmtd",
                 track_phase: bool = True):
        self.fluid = fluid
        # Seguimiento de la frontera de fase (recorte del volumen en x = 0 o
        # x = 1). Siempre activo en el modelo; desactivarlo solo sirve para
        # medir su efecto sobre la independencia de malla (tabla 9.12).
        self.track_phase = track_phase
        self.sec = sec_fluid
        self.geom = geom
        self.n_cells = n_cells
        self.phi_md = phi_md          # factor de maldistribucion (hipotesis M2)
        # Conjunto de correlaciones de la banda de carga (ap. 9.9). Es
        # configurable y no una tupla escrita en el cuerpo del componente: el
        # ap. 9.12.3 exige que la campana de sensibilidad recorra los nombres
        # registrados, y eso no puede hacerse contra una constante en codigo.
        self.void_fraction_names = tuple(void_fraction_names)
        self.log = extrapolation if extrapolation is not None else ExtrapolationLog()
        # Papel del componente en el modo activo: "condenser", "evaporator" o
        # None. El ap. 9.3 ya fija, para cada uno de los cinco modos, si cada
        # intercambiador condensa o evapora, y esa informacion existe ANTES de
        # iterar. Pertenece al modo y no al objeto —los objetos de componente no
        # cambian entre modos (ap. 9.3)—, de ahi que `solve()` pueda
        # sobreescribirlo: es `circuit.py` quien lo pasara por modo.
        self.role = self._check_role(role)
        # El lazo de disparo del ap. 9.6.1 marcha el intercambiador completo
        # una vez por iteracion de la secante. Registrar esas marchas anotaria
        # la trayectoria de convergencia como si fuera un resultado, igual que
        # hacia la iteracion interna. Se silencia durante el disparo y se
        # habilita para la marcha final, la unica que es un resultado.
        self._log_enabled = True
        # Valores por defecto conformes al capitulo: Martin (ap. 9.6.7),
        # Chen aditivo (ap. 9.6.3) y pelicula de Nusselt (ap. 9.6.3). Los tres
        # sustituyen a los provisionales anteriores; en particular la
        # condensacion ya no usa el enfoque de Reynolds equivalente, que el
        # ap. 9.6.3 descarta expresamente.
        self.corr = {
            "singlephase": "martin_vdi",
            "plate_boiling": "additive_cooper",
            # ANCLADA desde el 18/09/2026. `nusselt_film` seguia siendo la
            # formulacion del ap. 9.6.3, pero fallaba por falta de phi_c y
            # phi_v y obligaba a inyectarlos. Con el producto anclado sobre el
            # punto de seleccion del 27-30H, el submodelo cierra sin inyectar
            # nada. La version sin anclar se conserva registrada para la
            # sensibilidad y para poder pasar los factores a mano.
            "plate_condensation": "nusselt_film_anclada_27_30H",
            # Martin en lugar del generico PROVISIONAL, por coherencia: es la
            # misma correlacion con la que se identifico beta, y no tiene
            # coeficientes libres. `chevron_generic` se conserva como
            # alternativa de la banda del ap. 6.11, y para invocarla hacen falta
            # C y m, que siguen pendientes.
            "friction": "martin_vdi",
            "twophase_multiplier": "lockhart_martinelli_chisholm",
        }
        if corr:
            self.corr.update(corr)
        # Parametros por familia de correlacion, p.ej.
        # {"plate_condensation": {"phi_c": 1.0, "phi_v": 1.0}}.
        # Es la via por la que se INYECTA un dato pendiente para poder explorar
        # sin el. Pasa por aqui y no por un valor por defecto de la funcion a
        # proposito: asi el codigo que explora deja constancia de que el valor
        # no procede de los datos, y la procedencia puede recogerlo.
        self.corr_params = {k: dict(v) for k, v in (corr_params or {}).items()}
        # El producto phi_c*phi_v anclado se resuelve AQUI y no dentro de la
        # correlacion. Consultado en cada invocacion, `data.load` acaba dando
        # un millon de llamadas al sistema de ficheros por punto resuelto —un
        # `stat` y una resolucion de ruta cada vez—, que es el mismo error que
        # el ap. 9.12.4 persigue con `PropsSI`: lo caro no es el dato, es
        # volver a pedirlo. Va por `corr_params`, que es la via declarada para
        # pasar un coeficiente a una correlacion.
        self._resolver_producto_anclado()
        # Fraccion sensible de la carga en el desrecalentamiento con pared
        # humeda (ec. 9-19, §9.4.4). Z = 1 es el limite CONSERVADOR: deja
        # la resistencia de fase vapor integra y le SUMA en serie la del
        # condensado, de modo que el coeficiente queda algo POR DEBAJO del
        # monofasico puro (no igual: el comentario anterior decia que coincidian).
        # Efecto en diseno (13/10/2026): coeficiente -3 a -10 % en los volumenes
        # mojados de M-1 y -1 a -2 % en M-3; Q_acs -0.1 y -0.3 %.
        #
        # No se adopta un valor menor porque el capitulo no proporciona una
        # formulacion de Z valida para un fluido puro: su Z = x cp_v dTsat/dh se
        # anula identicamente a presion constante. Mientras no la haya, el
        # soporte cuantitativo de H3 no esta disponible, y ponerle un numero
        # seria inventarlo. Ver docs/historico/PLAN_PUESTA_EN_MARCHA.md, apartado 8.
        self.Z_wet = Z_wet
        # Disposicion VERTICAL: el ap. 9.6.6 conserva la contribucion
        # gravitatoria por ella, de modo que el modulo del termino es rho g L_p.
        # Lo que el capitulo deja con signo ambiguo («± rho g dz») es el
        # SENTIDO del flujo, que decide si la gravedad se pierde o se recupera.
        # Se deduce del papel en el modo, y ambas deducciones estan escritas en
        # el capitulo: el ap. 9.6.3 describe la pelicula de condensado
        # DESCENDENTE gobernada por gravedad, y el ap. 9.6.6 situa la
        # contribucion no despreciable «en la region bifasica del evaporador»,
        # que asciende. `flow_upward` permite imponerlo cuando el montaje real
        # diga otra cosa.
        self.vertical = vertical
        self.flow_upward = flow_upward
        # Diferencia de temperaturas del volumen de control. La ec. 9-11 del
        # ap. 9.6.1 es Q = UA dT_lm; la version anterior usaba la aritmetica
        # del extremo de entrada, que con discretizacion fina converge a lo
        # mismo pero es una desviacion del capitulo y no estaba declarada.
        # "arithmetic" se conserva para poder MEDIR la diferencia.
        if dT_mean not in ("lmtd", "arithmetic"):
            raise ValueError(
                f"dT_mean debe ser 'lmtd' o 'arithmetic', no {dT_mean!r}")
        self.dT_mean = dT_mean

    # ------------------------------------------------------------------
    @staticmethod
    def _check_role(role):
        if role not in (None, "condenser", "evaporator"):
            raise ValueError(
                f"role debe ser 'condenser', 'evaporator' o None, no {role!r}")
        return role

    def _two_phase_regime(self, T_sat, T_sec, role):
        """Decide si el volumen bifasico evapora o condensa.

        NO se deriva del flujo de calor. La version anterior elegia la rama por
        el signo de `q_flux_guess`, que la iteracion interna inicializa a 0.0:
        con la condicion `>= 0.0` la primera iteracion de CADA celda entraba en
        la rama de evaporacion aunque el componente estuviese condensando.
        Convergia al regimen correcto, pero contaminaba el registro de
        extrapolacion con cientos de entradas espurias, y un registro en el que
        nadie mira no cumple el requisito de reporte de los ap. 9.7.5 y
        9.12.3.

        El problema de fondo era derivar el regimen de una incognita del lazo.
        Se resuelve por dos vias, en este orden:

        1. Por el papel del componente en el modo activo (ap. 9.3), que es dato
           y no resultado.
        2. Si no se ha declarado papel, por el signo de (T_sec - T_sat), que
           esta disponible en la primera iteracion y es fisicamente correcto:
           el secundario por encima de la saturacion cede calor al refrigerante
           y este evapora.
        """
        if role == "condenser":
            return "condensing"
        if role == "evaporator":
            return "boiling"
        return "boiling" if T_sec >= T_sat else "condensing"

    def _resolver_producto_anclado(self) -> None:
        """Carga el producto phi_c*phi_v si la correlacion elegida lo necesita."""
        if self.corr.get("plate_condensation") != "nusselt_film_anclada_27_30H":
            return
        params = self.corr_params.setdefault("plate_condensation", {})
        if "producto" in params:
            return
        from .. import data as D

        params["producto"] = D.load("placas_alfanova").require(
            "producto_phi_c_phi_v.valor")

    def _cp(self, family: str) -> dict:
        return self.corr_params.get(family, {})

    def _cell_state(self, P, h) -> dict:
        """Estado del refrigerante en el volumen. Depende SOLO de (P, h).

        Se separa del coeficiente de pelicula porque el lazo interno sobre q''
        itera hasta veinticinco veces con (P, h) FIJOS: lo unico que cambia
        entre iteraciones es el flujo de calor. Evaluar aqui las propiedades y
        no dentro del lazo quita tres de cada cuatro llamadas a CoolProp del
        camino caliente, que con 2.3 millones por punto resuelto es la mitad
        del tiempo de calculo (ap. 9.12.4, §9.12.4).

        Guarda ademas `T_r` ANTES de pedir las de saturacion, y eso no es un
        detalle: `sat_props` deja el estado del fluido en (P, Q=1), de modo que
        consultar `fluid.T` despues devuelve la temperatura de SATURACION y no
        la del refrigerante. Ver la nota de `_alpha_ref`.
        """
        f = self.fluid
        f.update_PH(P, h)
        T_r = f.T
        sat = f.sat_props(P)
        sat["p_red"] = f.p_reduced(P)
        h_l, h_v = sat["h_l"], sat["h_v"]
        if h <= h_l:
            x, fase = 0.0, "liquid"
        elif h >= h_v:
            x, fase = 1.0, "vapor"
        else:
            x, fase = (h - h_l) / (h_v - h_l), "twophase"
        return {"P": P, "h": h, "T_r": T_r, "sat": sat, "x": x, "fase": fase}

    def _alpha_ref(self, state, G, q_flux_guess, T_sec, role, a_prev=None):
        """Coeficiente de pelicula local del lado refrigerante.

        Recibe el estado ya evaluado: dentro del lazo sobre q'' las propiedades
        no cambian. Devuelve la comprobacion de rango PENDIENTE de anotar, en
        lugar de anotarla aqui, porque el registro de extrapolacion debe
        recoger solo la iteracion convergida.

        CORREGIDO el 21/09/2026, criterio de pared humeda. La temperatura de
        pared se estimaba como `fluid.T + q/alpha`, tomando `fluid.T` DESPUES
        de haber llamado a `sat_props`, que deja el estado en (P, Q=1): el
        valor leido era la temperatura de SATURACION y no la del vapor
        sobrecalentado. El criterio `T_w < Tsat` se reducia entonces a
        `q/alpha < 0`, esto es, a «la celda se enfria», que en un
        desrecalentador es SIEMPRE cierto: la correccion de la ec. 9-19 se
        aplicaba al 100 % de las celdas de vapor en lugar de solo donde la
        pared baja de la saturacion. El diagnostico `wet_wall_fraction` que el
        componente reporta no tenia el fallo —lo calcula la marcha con la
        temperatura buena—, de modo que el modelo declaraba una fraccion y
        corregia otra.
        """
        f = self.fluid
        sat, x, T_r = state["sat"], state["x"], state["T_r"]
        h_l, h_v = sat["h_l"], sat["h_v"]
        h = state["h"]

        if state["fase"] == "liquid":      # liquido subenfriado
            Re = reynolds(G, self.geom.D_h, sat["mu_l"])
            a = get("singlephase", self.corr["singlephase"])(
                Re, sat["Pr_l"], sat["k_l"], self.geom.D_h,
                beta_c=self.geom.beta_c, **self._cp("singlephase"))
            regime = "liquid"
            check = ("singlephase", self.corr["singlephase"],
                     {"Re": Re, "Pr": sat["Pr_l"]})
        elif state["fase"] == "vapor":     # vapor sobrecalentado
            Re = reynolds(G, self.geom.D_h, sat["mu_v"])
            a = get("singlephase", self.corr["singlephase"])(
                Re, sat["Pr_v"], sat["k_v"], self.geom.D_h,
                beta_c=self.geom.beta_c, **self._cp("singlephase"))
            regime = "vapor"
            # Desrecalentamiento con pared humeda (ap. 9.6.5, ec. 9-19). Si
            # la pared cae por debajo de la saturacion, la resistencia de fase
            # vapor deja de actuar sola: se combina con la de condensacion
            # ponderada por la fraccion sensible Z.
            if a_prev is not None and q_flux_guess:
                T_w = T_r + q_flux_guess / max(a_prev, 1e-9)
                if T_w < sat["Tsat"]:
                    try:
                        a_c = get("plate_condensation",
                                  self.corr["plate_condensation"])(
                            1.0, G, sat, self.geom, dT=sat["Tsat"] - T_w,
                            **self._cp("plate_condensation"))
                        a = wet_wall_UA(a_c, a, self.Z_wet)
                    except Exception:
                        pass       # sin phi_c/phi_v no hay correccion posible
            check = ("singlephase", self.corr["singlephase"],
                     {"Re": Re, "Pr": sat["Pr_v"]})
        else:                              # bifasico
            regime = self._two_phase_regime(sat["Tsat"], T_sec, role)
            if regime == "boiling":
                a = get("plate_boiling", self.corr["plate_boiling"])(
                    x, G, abs(q_flux_guess), sat, f.M, self.geom,
                    **self._cp("plate_boiling"))
                check = ("plate_boiling", self.corr["plate_boiling"],
                         {"x": x, "G": G, "p_red": sat["p_red"]})
            else:
                # dT pared-saturacion: la pelicula de Nusselt depende de el,
                # lo que introduce el acoplamiento implicito que resuelve el
                # lazo interno (ap. 9.4.3).
                dT_w = abs(q_flux_guess) / max(a_prev, 1e-9) if a_prev else None
                a = get("plate_condensation",
                        self.corr["plate_condensation"])(
                    x, G, sat, self.geom, dT=dT_w,
                    **self._cp("plate_condensation"))
                check = ("plate_condensation", self.corr["plate_condensation"],
                         {"x": x, "G": G, "p_red": sat["p_red"]})
        return a / self.phi_md, x, sat, regime, check

    def _alpha_sec(self, T_sec, G_sec):
        s = self.sec
        # Acotada al dominio liquido: fuera de el solo caen los tanteos del
        # disparo (ver `_agua_desde_h`), nunca la solucion convergida.
        s.update_PT(P_AGUA, min(max(T_sec, self._T_AGUA_MIN), self._T_AGUA_MAX))
        Re = reynolds(G_sec, self.geom.D_h, s.mu)
        a = get("singlephase", self.corr["singlephase"])(
            Re, s.Pr, s.k, self.geom.D_h, beta_c=self.geom.beta_c,
            **self._cp("singlephase"))
        return a, ("singlephase", self.corr["singlephase"],
                   {"Re": Re, "Pr": s.Pr})

    # ------------------------------------------------------------------
    def _flow_upward(self, role, T_sec, T_ref) -> bool:
        """Sentido del flujo de refrigerante en una placa vertical.

        Decide el signo de la contribucion gravitatoria de la ec. 9-20, que el
        capitulo deja escrito como «±». Las dos deducciones estan en el propio
        capitulo: el ap. 9.6.3 describe la pelicula de condensado DESCENDENTE
        gobernada por gravedad —luego un condensador se recorre hacia abajo y la
        gravedad RECUPERA presion—, y el ap. 9.6.6 situa la contribucion no
        despreciable «en la region bifasica del evaporador», que asciende y por
        tanto la PIERDE.

        Como el regimen bifasico (`_two_phase_regime`), no se deriva de ninguna
        incognita del lazo: papel declarado primero, y si no lo hay, el signo de
        (T_sec - T_ref), que esta disponible antes de iterar.
        """
        if self.flow_upward is not None:
            return self.flow_upward
        if role == "evaporator":
            return True
        if role == "condenser":
            return False
        return T_sec >= T_ref

    def _dT_efectiva(self, dT_a, dT_b) -> float:
        """Diferencia de temperaturas del volumen, ec. 9-11.

        La media logaritmica no existe cuando las dos diferencias tienen signo
        distinto —hay cruce dentro del volumen, que con discretizacion suficiente
        no deberia ocurrir— ni cuando son iguales. En ambos casos se retrocede a
        la aritmetica, que es el limite de la logaritmica cuando dT_a -> dT_b.
        """
        if self.dT_mean == "arithmetic":
            return 0.5 * (dT_a + dT_b)
        if dT_a * dT_b <= 0.0:
            return 0.5 * (dT_a + dT_b)
        if abs(dT_a - dT_b) < 1e-9 * max(abs(dT_a), abs(dT_b)):
            return 0.5 * (dT_a + dT_b)
        return (dT_a - dT_b) / math.log(dT_a / dT_b)

    def _pressure_drop(self, h_in, h_out, x, sat, G, L_cell, P, upward):
        """Perdida de carga del volumen, ec. 9-20 completa.

        Tres contribuciones, y el capitulo las quiere las tres:

        - FRICCIONAL. En el bifasico por multiplicador de fases separadas
          (antigua tabla 10.7), que es una familia registrada aparte para poder
          sustituirla sin tocar este codigo. Fuera del bifasico, el factor de
          friccion monofasico con la viscosidad de la fase presente, y no la
          eleccion por `x < 0.5` que hacia la version anterior.
        - ACELERACION, G^2 d(1/rho). Se evalua con la densidad HOMOGENEA de los
          estados de entrada y salida del volumen, que es lo que escribe la
          ec. 9-20. La forma rigurosa de fases separadas emplearia la densidad
          de cantidad de movimiento con la fraccion de huecos; la diferencia
          esta declarada en docs/historico/PLAN_PUESTA_EN_MARCHA.md, ap. 8.
        - GRAVITATORIA, ± rho g dz, con dz = L_cell si la disposicion es
          vertical. El ap. 9.6.6 la conserva expresamente.

        Devuelve `(dP, reparto, checks)`. `checks` viaja fuera en lugar de
        anotarse aqui por la misma razon que en `_alpha_ref`: el registro de
        extrapolacion solo debe recoger la marcha convergida.
        """
        g = self.geom
        f_fn = get("friction", self.corr["friction"])
        checks = []
        info = {}

        self.fluid.update_PH(P, h_in)
        rho_in = self.fluid.rho
        self.fluid.update_PH(P, h_out)
        rho_out = self.fluid.rho

        if 0.0 < x < 1.0:
            mult_name = self.corr["twophase_multiplier"]
            dP_f, info = get("twophase_multiplier", mult_name)(
                x, G, sat, g.D_h, L_cell, f_fn, beta_c=g.beta_c,
                **self._cp("twophase_multiplier"))
            checks.append((("twophase_multiplier"), mult_name,
                           {"x": x, "G": G}))
            Re = info.get("Re_l", info.get("Re"))
        else:
            mu = sat["mu_v"] if x >= 1.0 else sat["mu_l"]
            Re = reynolds(G, g.D_h, mu)
            dP_f = (f_fn(Re, beta_c=g.beta_c)
                    * (4.0 * L_cell / g.D_h) * G ** 2 / (2.0 * rho_in))
        checks.append(("friction", self.corr["friction"], {"Re": Re}))

        dP_a = G ** 2 * (1.0 / rho_out - 1.0 / rho_in)
        dP_g = 0.0
        if self.vertical:
            rho_m = 0.5 * (rho_in + rho_out)
            dP_g = (1.0 if upward else -1.0) * rho_m * 9.80665 * L_cell
        return dP_f + dP_a + dP_g, {"friccional": dP_f, "aceleracion": dP_a,
                                    "gravitatoria": dP_g, **info}, checks

    # ------------------------------------------------------------------
    def _solve_cell(self, P, h, G, G_sec, T_sec, role, A_cell, m_dot, m_sec,
                    cp_sec, counterflow, a_seed=1000.0, state=None):
        """Resuelve UN volumen de control de area `A_cell`.

        Extraido del lazo de marcha porque la marcha necesita poder resolver el
        mismo volumen con areas distintas: cuando el titulo cruza 0 o 1 dentro
        del volumen, hay que recortarlo hasta la frontera, y eso exige volver a
        resolverlo. Antes el area era una constante del lazo.

        Itera sobre el flujo de calor (ap. 9.6.3) porque el coeficiente depende
        de el: la ebullicion por el numero de ebullicion y la pelicula de
        Nusselt por el salto pared-saturacion.
        """
        g = self.geom
        q_flux = 0.0
        a_r = a_seed
        regime = check_r = check_s = None
        # El estado del refrigerante y el coeficiente del secundario NO
        # dependen de q'': se evaluan una vez y no veinticinco. Tampoco
        # dependen del AREA, de modo que el lazo de recorte de la frontera de
        # fase —que reresuelve el mismo volumen hasta seis veces con otra
        # area— lo recibe hecho en lugar de rehacerlo.
        state = state if state is not None else self._cell_state(P, h)
        x, sat, T_r = state["x"], state["sat"], state["T_r"]
        a_s, check_s = self._alpha_sec(T_sec, G_sec)
        UA_sec_pared = g.t_p / (g.k_p * A_cell) + 1.0 / (a_s * A_cell) \
            + g.R_f / A_cell
        # Entalpia del refrigerante a la temperatura del agua de entrada del
        # volumen: la cota fisica de su estado de salida (ver `phi`).
        try:
            self.fluid.update_PT(P, T_sec)
            h_agua = self.fluid.h
        except ValueError:                     # T_sec justo en la saturacion
            h_agua = state["sat"]["h_l"] if T_sec < T_r else state["sat"]["h_v"]

        def phi(q, a_guess):
            """q'' que devuelve la ec. 9-11 para un q'' supuesto."""
            a_r, x, sat, regime, check_r = self._alpha_ref(
                state, G, q, T_sec, role, a_prev=a_guess)
            UA = 1.0 / (1.0 / (a_r * A_cell) + UA_sec_pared)
            # Ec. 9-11: Q = UA dT_lm. Las dos diferencias son las de los
            # extremos del volumen, y la de salida depende del propio calor
            # intercambiado: es un acoplamiento implicito mas, y lo resuelve
            # la misma iteracion que ya cierra sobre q''.
            dT_a = T_sec - T_r
            Q_prev = q * A_cell
            # La salida estimada del refrigerante no puede cruzar la temperatura
            # del agua: fuera de ahi el estado es imposible y, con volumenes
            # grandes y caudales pequenos, la biblioteca de propiedades aborta
            # (24/09/2026, tabla 9.15 con el 27-30H). Acotada, no cambia nada
            # donde no se alcanzaba ese limite.
            h_b = h + Q_prev / m_dot
            if (Q_prev < 0.0 and h_b < h_agua) or (Q_prev > 0.0 and h_b > h_agua):
                h_b = h_agua
            self.fluid.update_PH(P, h_b)
            T_r_b = self.fluid.T
            T_sec_b = (T_sec + Q_prev / (m_sec * cp_sec) if counterflow
                       else T_sec - Q_prev / (m_sec * cp_sec))
            Q_new = UA * self._dT_efectiva(dT_a, T_sec_b - T_r_b)
            # Y el calor del volumen tampoco puede llevar al refrigerante mas
            # alla de la temperatura del agua (misma cota fisica).
            Q_max = m_dot * abs(h_agua - h)
            if abs(Q_new) > Q_max:
                Q_new = math.copysign(Q_max, Q_new)
            return Q_new / A_cell, a_r, x, sat, regime, check_r

        convergido = False
        for _ in range(25):
            q_new, a_r, x, sat, regime, check_r = phi(q_flux, a_r)
            if abs(q_new - q_flux) < self.TOL_Q * max(abs(q_new), 1.0):
                q_flux = q_new
                convergido = True
                break
            q_flux = 0.5 * q_flux + 0.5 * q_new

        if not convergido:
            # RESPALDO CON INTERVALO GARANTIZADO, 24/09/2026. En ebullicion con
            # titulo alto el coeficiente depende tanto del flujo de calor que
            # el punto fijo amortiguado NO es contractivo: oscilaba, por ejemplo
            # entre 9.7 y 19.5 kW/m2, y se devolvia la ultima iteracion sin
            # aviso. Ese ruido volvia biestable el recalentamiento de salida del
            # evaporador de M-1 —saltos de 1.4 K con milesimas de kelvin en el
            # agua— y el lazo externo no convergia. Se resuelve
            # g(q) = phi(q) - q = 0: en q = 0 el signo es el de la diferencia de
            # temperaturas de entrada y, al crecer |q| en ese sentido, la
            # diferencia de salida se anula y g cambia de signo. Solo se entra
            # aqui si el punto fijo falla, de modo que donde convergia el
            # resultado es identico.
            def g_q(q):
                a = a_r
                for _ in range(4):          # coeficiente coherente con ESE q
                    q_new, a_new, *_ = phi(q, a)
                    if abs(a_new - a) < 1e-6 * a:
                        break
                    a = a_new
                return q_new - q

            g0 = g_q(0.0)
            if g0 != 0.0:
                paso = abs(phi(0.0, a_r)[0]) or 1.0
                lo, hi = 0.0, math.copysign(paso, g0)
                for _ in range(60):
                    try:
                        if g_q(hi) * g0 < 0.0:
                            break
                    except ValueError:
                        hi = 0.5 * (lo + hi)   # fuera del dominio: acercarse
                        continue
                    lo, hi = hi, 2.0 * hi
                a_lo, a_hi = sorted((lo, hi))
                q_flux = brentq(g_q, a_lo, a_hi, xtol=1e-9,
                                rtol=1e-12, maxiter=200)
                _, a_r, x, sat, regime, check_r = phi(q_flux, a_r)
        return {"q_flux": q_flux, "Q": q_flux * A_cell, "a_r": a_r, "x": x,
                "sat": sat, "regime": regime, "T_r": T_r,
                "checks": [c for c in (check_r, check_s) if c is not None]}

    @staticmethod
    def _frontera_interior(h, h_new, sat, margen=1e-4):
        """Entalpia de la frontera de fase que el volumen CRUZA por dentro.

        Devuelve `None` si el volumen no cruza ninguna, o si la cruza tan cerca
        de uno de sus extremos que recortarlo generaria una celda degenerada
        —que es el caso justo despues de un recorte, cuando la marcha arranca
        exactamente sobre la frontera y se aleja de ella.

        Si el volumen cruza LAS DOS —malla muy gruesa, toda la condensacion en
        un volumen— devuelve la primera en el sentido de la marcha. El recorte
        siguiente se ocupara de la otra.
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

    #: Dominio liquido del agua a `P_AGUA` en el que se invierte h -> T.
    _T_AGUA_MIN, _T_AGUA_MAX = 273.16 + 0.05, 453.0

    def _h_agua(self, T):
        """Entalpia del agua a `P_AGUA`, con la misma extrapolacion lineal que
        `_agua_desde_h` fuera del dominio liquido, para que sean inversas."""
        self._agua_desde_h(0.0)                 # inicializa los limites
        (h_lo, T_lo, cp_lo), (h_hi, T_hi, cp_hi) = self._h_agua_lim
        if T < T_lo:
            return h_lo + (T - T_lo) * cp_lo
        if T > T_hi:
            return h_hi + (T - T_hi) * cp_hi
        self.sec.update_PT(P_AGUA, T)
        return self.sec.h

    def _agua_desde_h(self, h_sec):
        """Temperatura y cp del agua a partir de su entalpia, a `P_AGUA`.

        Fuera del dominio liquido se EXTRAPOLA linealmente con el cp del
        extremo. No es un estado fisico: son los tanteos del lazo de disparo
        del contracorriente, que prueba temperaturas de salida del agua por
        debajo de 0 C o por encima de la saturacion antes de encerrar la raiz.
        La solucion convergida cae siempre dentro del dominio, y ahi la
        inversion es exacta. Con el cp constante de antes esos tanteos se
        extrapolaban sin mas, y no pueden hacer fallar la marcha ahora.
        """
        if not hasattr(self, "_h_agua_lim"):
            lim = []
            for T in (self._T_AGUA_MIN, self._T_AGUA_MAX):
                self.sec.update_PT(P_AGUA, T)
                lim.append((self.sec.h, T, self.sec.cp))
            self._h_agua_lim = lim
        (h_lo, T_lo, cp_lo), (h_hi, T_hi, cp_hi) = self._h_agua_lim
        if h_sec < h_lo:
            return T_lo + (h_sec - h_lo) / cp_lo, cp_lo
        if h_sec > h_hi:
            return T_hi + (h_sec - h_hi) / cp_hi, cp_hi
        self.sec.update_PH(P_AGUA, h_sec)
        return self.sec.T, self.sec.cp

    def _march(self, P_in, h_in, m_dot, T_sec_guess, m_sec, counterflow=True,
               role=None):
        """Marcha sobre los volumenes en la direccion del flujo de refrigerante.

        `T_sec_guess` es la temperatura del secundario en el extremo donde
        entra el refrigerante. En contracorriente no es dato, de ahi el lazo
        de disparo del apartado 9.6.6.

        SEGUIMIENTO DE LA FRONTERA DE FASE. La marcha NO reparte el area en `n`
        volumenes iguales y sigue adelante: cuando un volumen cruzaria por
        dentro el titulo 0 o 1, se RECORTA hasta la frontera y el resto del area
        pasa al volumen siguiente. Asi ningun volumen contiene dos regimenes y
        las fronteras caen siempre en un borde.

        No es refinamiento por gusto. Sin el, el salto de coeficiente al pasar
        de desrecalentamiento a condensacion cae en volumenes distintos segun la
        malla, y ese salto domina sobre el error de discretizacion: el estudio
        de independencia de malla del ap. 6.7.1 se quedaba oscilando en el 1 %
        hasta 320 volumenes, mientras que con vapor saturado a la entrada —esto
        es, sin frontera que cruzar— la misma serie convergia a 6e-6. El
        diagnostico aislaba la causa en la discretizacion y no en las
        correlaciones, y esto es la correccion.

        Consecuencia: el numero de volumenes resueltos es `n` mas uno por cada
        frontera cruzada, de modo que `n_cells` pasa a ser el numero NOMINAL.
        Las magnitudes por volumen se promedian por AREA y no por recuento.
        """
        g = self.geom
        n = self.n_cells
        A_cell = g.A_total / n
        G = g.mass_flux(m_dot, "ref")
        G_sec = g.mass_flux(m_sec, "sec")

        h = h_in
        P = P_in
        T_sec = T_sec_guess
        x_prof, a_prof = [], []
        self.fluid.update_PH(P_in, h_in)
        perfil = {"A": [0.0], "T_ref": [self.fluid.T], "T_sec": [T_sec_guess],
                  "T_pared": []}
        A_wet = 0.0
        dP_total = 0.0
        dP_parts = {"friccional": 0.0, "aceleracion": 0.0, "gravitatoria": 0.0}
        Q_total = 0.0
        cells = []
        n_recortes = 0

        # BALANCE DEL AGUA EN ENTALPIA, ec. 9-11: m_w (h_w,j-1 - h_w,j) = Q_j.
        # CORREGIDO el 24/09/2026. Antes el agua avanzaba con un cp CONSTANTE,
        # evaluado en `T_sec_guess`, y la comprobacion de `_package` usaba otro
        # cp constante, el de la entrada del agua: el error de balance de las
        # placas era exactamente cp(T_sal)/cp(T_ent) - 1 —de 0.5 a 2.4e-3 en
        # los modos con ACS— y los marcaba NO VALIDOS sin desequilibrio fisico
        # alguno. Ahora se arrastra la entalpia del agua y la temperatura se
        # deduce de ella. El cp local solo estima, DENTRO de cada volumen, la
        # temperatura de salida del agua para la diferencia media.
        h_sec = self._h_agua(T_sec_guess)
        cp_sec = self._agua_desde_h(h_sec)[1]

        # Sentido del flujo, para el signo de la contribucion gravitatoria de la
        # ec. 9-20. Se fija UNA vez, antes de marchar: es una propiedad del
        # componente en el modo activo, no del volumen de control.
        self.fluid.update_PH(P_in, h_in)
        upward = self._flow_upward(role, T_sec_guess, self.fluid.T)

        A_left = g.A_total
        a_seed = 1000.0
        # Cota de seguridad: cada frontera anade un volumen, y solo hay dos.
        max_vol = n + 8
        while A_left > 1e-12 * g.A_total and len(cells) < max_vol:
            A_try = min(A_cell, A_left)
            state = self._cell_state(P, h)      # depende de (P, h), no del area
            res = self._solve_cell(P, h, G, G_sec, T_sec, role, A_try, m_dot,
                                   m_sec, cp_sec, counterflow, a_seed,
                                   state=state)
            h_new = h + res["Q"] / m_dot

            # --- recorte en la frontera de fase --------------------------
            h_b = (self._frontera_interior(h, h_new, res["sat"])
                   if self.track_phase else None)
            if h_b is not None:
                # El area que lleva el volumen EXACTAMENTE hasta la frontera, por
                # una busqueda con intervalo garantizado. CORREGIDO el
                # 24/09/2026: antes se iteraba A <- A (h_b - h)/(h_new - h), que
                # supone Q proporcional a A. En ebullicion el coeficiente depende
                # del flujo de calor, la iteracion no es contractiva, agotaba sus
                # seis pasos sin converger y oscilaba entre dos areas muy
                # distintas (0.002 y 0.046 m2 en el evaporador de M-1); la
                # frontera se imponia igual y el area sobrante que pasaba al
                # vapor quedaba mal. El recalentamiento de salida saltaba 1.4 K
                # con cambios de milesimas de kelvin en el agua, y el lazo
                # externo se detenia lejos de la raiz. Con area nula el volumen
                # no llega a la frontera y con el area probada la cruza: la
                # raiz esta encerrada.
                sentido = 1.0 if h_b > h else -1.0
                cache = {}

                def falta(A):
                    r = self._solve_cell(P, h, G, G_sec, T_sec, role, A, m_dot,
                                         m_sec, cp_sec, counterflow, a_seed,
                                         state=state)
                    cache[A] = r
                    return sentido * (h + r["Q"] / m_dot - h_b)

                A_min = 1e-9 * g.A_total
                A_max = A_try
                cache[A_max] = res
                if falta(A_min) < 0.0 < sentido * (h_new - h_b):
                    A_try = brentq(falta, A_min, A_max, xtol=1e-12 * g.A_total,
                                   rtol=1e-10, maxiter=100)
                    res = cache.get(A_try) or self._solve_cell(
                        P, h, G, G_sec, T_sec, role, A_try, m_dot, m_sec,
                        cp_sec, counterflow, a_seed, state=state)
                # La frontera se impone EXACTAMENTE, en lugar de dejarla en lo
                # que devuelva la ultima iteracion: asi el volumen siguiente
                # arranca sobre ella y el balance entalpico no arrastra deriva.
                h_new = h_b
                # ...y un paso DESPRECIABLE (1e-9 del calor latente) hacia la fase en la
                # que sigue el proceso. Corregido el 29/09/2026: arrancando EXACTAMENTE sobre
                # h_v, el volumen siguiente de un condensador se clasificaba como vapor
                # (`h >= h_v`) y marchaba entero con el coeficiente monofasico, un error
                # proporcional a 1/N; igual al arrancar sobre h_l un evaporador. En las placas
                # lo tapaba la presion decreciente, que movia h_v por azar; con presion
                # uniforme (M8) aparecio: 7 % con 10 volumenes. La clasificacion la decide
                # ahora el SENTIDO de la marcha, no el redondeo.
                h_new += math.copysign(1e-9 * (res["sat"]["h_v"] - res["sat"]["h_l"]), h_b - h)
                n_recortes += 1

            Q_cell = (h_new - h) * m_dot
            q_flux = Q_cell / A_try
            L_try = g.L_p * A_try / g.A_total
            Q_total += Q_cell
            a_r, x, sat = res["a_r"], res["x"], res["sat"]
            a_seed = a_r

            # El registro de extrapolacion anota SOLO la iteracion convergida.
            # Anotar las intermedias registraria la trayectoria de convergencia
            # como si fuera un resultado, y un registro asi no sirve para lo
            # que exigen los ap. 9.7.5 y 9.12.3.
            if self._log_enabled:
                for c in res["checks"]:
                    self.log.check(c[0], c[1], **c[2])

            # Pared humeda en desrecalentamiento (ap. 9.6.5, ec. 9-18):
            # se compara la temperatura superficial con la de saturacion a la
            # presion local. El signo es el del ap. 9.6.5 con el convenio de
            # Q positivo hacia el refrigerante: al enfriarse, Q_cell < 0 y la
            # pared queda por debajo del fluido.
            T_wall = res["T_r"] + Q_cell / max(a_r * A_try, 1e-9)
            if x >= 1.0 and T_wall < sat["Tsat"]:
                A_wet += A_try

            # Perdida de carga completa, ec. 9-20: friccional con
            # multiplicador bifasico, aceleracion y gravitatoria.
            self.fluid.update_PH(P, h)
            rho = self.fluid.rho
            dP, parts, dp_checks = self._pressure_drop(
                h, h_new, x, sat, G, L_try, P, upward)
            dP_total += dP
            for k in ("friccional", "aceleracion", "gravitatoria"):
                dP_parts[k] += parts[k]
            # El factor de friccion es PROVISIONAL (antigua tabla 10.7) y el
            # multiplicador extrapola geometria y fluido: si no se anotan, la
            # perdida de carga sale del modelo sin marca alguna.
            if self._log_enabled:
                for c in dp_checks:
                    self.log.check(c[0], c[1], **c[2])

            cells.append(dict(P=P, h=h, x=x, rho=rho, sat=sat, G=G,
                              V=g.A_channel * L_try * g.n_channels_ref,
                              A=A_try))
            x_prof.append(x)
            a_prof.append(a_r)
            perfil["T_pared"].append(T_wall)

            # avance
            A_left -= A_try
            h = h_new
            # PRESION UNIFORME (hipotesis M8; decision del autor, 29/09/2026):
            # las propiedades se evaluan a la presion de entrada en todo el
            # intercambiador y la perdida de carga se ACUMULA y se publica, sin
            # aplicarse al ciclo. Aplicarla dentro de la marcha y no en la
            # aspiracion dejaba una recuperacion de presion gratuita entre el
            # evaporador y el compresor (D12).
            # Avance del secundario. En CONTRACORRIENTE la marcha va del
            # extremo de entrada del refrigerante —que es el de SALIDA del
            # agua— hacia el otro, es decir, aguas ARRIBA del agua: su
            # temperatura debe DECRECER a lo largo de la marcha. El agua gana
            # (-Q_cell) en cada celda, luego retrocediendo se le resta:
            #     T_sec(j+1) = T_sec(j) - (-Q_cell)/(m cp) = T_sec(j) + Q_cell/(m cp)
            # En equicorriente la marcha sigue al agua y el signo se invierte.
            # Mismo razonamiento, en ENTALPIA (ec. 9-11).
            h_sec = h_sec + Q_cell / m_sec if counterflow \
                else h_sec - Q_cell / m_sec
            T_sec, cp_sec = self._agua_desde_h(h_sec)
            self.fluid.update_PH(P, h)
            perfil["A"].append(perfil["A"][-1] + A_try)
            perfil["T_ref"].append(self.fluid.T)
            perfil["T_sec"].append(T_sec)

        dP_parts["total"] = dP_total
        dP_parts["upward"] = upward
        # Comprobacion a posteriori de M8: el salto de saturacion que la
        # perdida de carga acumulada supondria si se aplicara.
        dT_sat = self.fluid.Tsat(P_in) - self.fluid.Tsat(max(P_in - dP_total, 1e4))
        return dict(h_out=h, P_out=P, T_sec_end=T_sec, dT_sat=dT_sat,
                    T_sec_start=T_sec_guess, h_sec_end=h_sec, Q=Q_total,
                    dP=dP_total, dP_parts=dP_parts,
                    x_prof=np.array(x_prof), a_prof=np.array(a_prof),
                    profile={k: np.array(v) for k, v in perfil.items()},
                    wet_fraction=A_wet / g.A_total, cells=cells,
                    n_volumenes=len(cells), n_recortes=n_recortes)

    # ------------------------------------------------------------------
    def march(self, P_in, h_in, m_dot, T_sec_at_ref_inlet, m_sec,
              counterflow=True, role=None):
        """Marcha sobre los volumenes SIN cerrar el disparo del secundario.

        Es la interfaz que necesita el tren extendido del ap. 9.3.1: cuando dos
        intercambiadores comparten presion y caudal de agua, la temperatura del
        agua en el punto de union no es dato de ninguno de los dos y el disparo
        debe hacerse sobre el tren completo. `solve()` sigue siendo la interfaz
        del componente aislado.
        """
        return self._march(P_in, h_in, m_dot, T_sec_at_ref_inlet, m_sec,
                           counterflow, self._check_role(role) or self.role)

    def package(self, out, m_dot, m_sec, T_sec_in, counterflow=True,
                h_in=None):
        """Empaqueta una marcha en `HXResult` con su cierre de balance."""
        return self._package(out, m_dot, m_sec, T_sec_in, counterflow, h_in)

    # ------------------------------------------------------------------
    def solve(self, P_in, h_in, m_dot, T_sec_in, m_sec,
              counterflow=True, tol=1e-3, role=None):
        """Resuelve el intercambiador completo.

        En contracorriente se dispara sobre la temperatura del secundario en
        el extremo de entrada del refrigerante y se itera hasta que la
        temperatura calculada en el otro extremo coincida con `T_sec_in`
        (apartado 9.6.6).
        """
        role = self._check_role(role) or self.role

        if not counterflow:
            out = self._march(P_in, h_in, m_dot, T_sec_in, m_sec, False, role)
            return self._package(out, m_dot, m_sec, T_sec_in, counterflow, h_in)

        def shoot(T_guess):
            try:
                out = self._march(P_in, h_in, m_dot, T_guess, m_sec, True, role)
            except ValueError:
                # Una tentativa del disparo puede sacar al secundario de su
                # rango de existencia —agua por debajo del punto de fusion, por
                # ejemplo— y hacer abortar a la biblioteca de propiedades. No es
                # un fallo del modelo sino una tentativa inviable: se devuelve
                # un residuo grande del signo que corresponde, para que el
                # metodo se aleje de ahi en lugar de abortar la resolucion.
                return -1.0e3
            return out["T_sec_end"] - T_sec_in

        self.fluid.update_PH(P_in, h_in)
        T_r_in = self.fluid.T
        # Intervalo de disparo ACOTADO FISICAMENTE: la temperatura de salida del
        # secundario esta necesariamente entre su entrada y la del refrigerante,
        # porque no puede cruzarla. La version anterior abria +-40 K a cada lado,
        # lo que con agua metia el estado por debajo del punto de fusion y hacia
        # abortar a la biblioteca de propiedades en lugar de no converger.
        lo = min(T_sec_in, T_r_in)
        hi = max(T_sec_in, T_r_in)
        margen = max(0.01, 0.001 * (hi - lo))
        lo, hi = lo - margen, hi + margen

        self._log_enabled = False
        try:
            T_star = brentq(shoot, lo, hi, xtol=tol, maxiter=200)
            converged = True
        except (ValueError, RuntimeError):
            # Ap. 9.4.4: no se descarta en silencio. Se devuelve el resultado
            # marcado como no convergido para que el lazo externo lo registre
            # con su condicion de contorno.
            T_star = T_sec_in
            converged = False
        finally:
            self._log_enabled = True

        out = self._march(P_in, h_in, m_dot, T_star, m_sec, True, role)
        res = self._package(out, m_dot, m_sec, T_sec_in, counterflow, h_in)
        res.T_sec_out = T_star
        res.converged = converged
        return res

    # ------------------------------------------------------------------
    def _package(self, out, m_dot, m_sec, T_sec_in, counterflow, h_in=None):
        """Empaqueta el resultado y ejecuta el cierre de balance (ap. 6.7.1).

        El balance se comprueba de forma INDEPENDIENTE de la marcha: se
        contrasta el calor acumulado celda a celda contra el que se deduce de
        los estados extremos de ambos fluidos. Si ambos coincidieran por
        construccion la comprobacion no valdria nada.
        """
        err = float("nan")
        if h_in is not None:
            # calor visto por el refrigerante, de sus estados extremos
            Q_ref = m_dot * (out["h_out"] - h_in)
            # El calor que ve el agua, de las ENTALPIAS de los DOS extremos de
            # la marcha (ec. 9-11). En contracorriente la marcha empieza en la
            # salida del agua, de modo que start - end es su salto. Hasta el
            # 24/09/2026 se tomaba m cp (T_start - T_end) con el cp de la
            # entrada del agua, distinto del que empleaba la marcha, y esa
            # diferencia de cp era todo el error de balance de las placas.
            Q_sec = m_sec * (self._h_agua(out["T_sec_start"])
                             - self._h_agua(out["T_sec_end"]))
            scale = max(abs(Q_ref), abs(Q_sec), 1.0)
            # SIGNADO, no en valor absoluto. Comparar modulos hace la
            # comprobacion ciega al sentido de la marcha, que es exactamente el
            # error que tenia el avance del secundario en contracorriente: el
            # balance cerraba a 1e-15 con el agua evolucionando al reves.
            err = abs(-Q_ref - Q_sec) / scale
        return HXResult(
            Q_dot=out["Q"], h_ref_out=out["h_out"], T_sec_out=out["T_sec_end"],
            dP_ref=out["dP"], dP_parts=out["dP_parts"],
            dT_sat_equivalente=out.get("dT_sat", 0.0),
            x_profile=out["x_prof"],
            alpha_profile=out["a_prof"], profile=out["profile"],
            wet_wall_fraction=out["wet_fraction"],
            n_volumenes=out.get("n_volumenes", 0),
            n_recortes=out.get("n_recortes", 0),
            charge=self._charge_from_cells(out["cells"]),
            energy_balance_error=err, converged=True,
            extrapolated=self.log.extrapolated,
            excursions=self.log.excursions)

    def _charge_from_cells(self, cells) -> dict:
        """Inventario de carga, ecuaciones 9-32 y 9-33.

        Devuelve el RANGO obtenido con las cuatro correlaciones de fraccion de
        huecos, conforme al requisito del apartado 9.9. NUNCA un valor unico.
        """
        names = self.void_fraction_names
        totals = {n: 0.0 for n in names}
        for c in cells:
            if 0.0 < c["x"] < 1.0:
                rr = charge_range(c["x"], c["sat"], c["G"], self.geom.D_h,
                                  names=names)
                for n in names:
                    totals[n] += rr[n]["rho_mean"] * c["V"]
            else:
                for n in names:
                    totals[n] += c["rho"] * c["V"]
        totals["_min"] = min(totals[n] for n in names)
        totals["_max"] = max(totals[n] for n in names)
        totals["_spread"] = (totals["_max"] / totals["_min"]
                             if totals["_min"] > 0 else float("nan"))
        return totals


# ---------------------------------------------------------------------------
# Anclaje sobre el punto de seleccion del fabricante (ap. 9.6.4)
# ---------------------------------------------------------------------------

@dataclass
class SelectionAnchor:
    """Resultado del anclaje del condensador de placas sobre su punto de ficha."""
    beta_c: float                 # rad, identificado sobre la perdida de carga
    beta_c_deg: float
    phi_c_phi_v: float            # producto identificado sobre la conductancia
    phi_adoptado: float           # factor de alargamiento SUPUESTO, no resuelto
    UA_limpio: float              # W/K, el dato
    alpha_agua: float             # W/(m2 K)
    alpha_refrigerante: float     # W/(m2 K)
    h_nusselt: float              # W/(m2 K), pelicula sin corregir
    Re_agua: float
    dT_pared: float               # K, salto pared-saturacion
    reparto: dict                 # fraccion de resistencia por lado
    convergio: bool
    avisos: list


def anchor_from_selection_point(fluid, secondary, df=None, unit=None,
                                phi=1.15, area_convention="developed",
                                port_loss_Pa=385.0, n_cells=60,
                                beta_bracket_deg=(20.0, 85.0),
                                **geom_overrides):
    """Identifica beta y el producto phi_c*phi_v sobre el punto de seleccion.

    ESTRATEGIA. Es la misma del ap. 9.7.3 con el lado de aire: no se adopta una
    correlacion general y se acepta su incertidumbre, sino que se ANCLA sobre el
    unico punto de operacion del que se dispone. La diferencia, y es a favor, es
    que aqui el punto trae DOS datos independientes en lugar de uno:

    1. La perdida de carga del agua. La correlacion de Martin liga friccion y
       transferencia a traves del angulo de corrugacion, de modo que una
       perdida de carga medida determina beta. Es el unico vinculo disponible, y
       la razon por la que `friction/martin_vdi` esta registrada.
    2. La conductancia global. Con beta ya fijado, el coeficiente del lado de
       agua sale de Martin, la pared es conocida, y el del refrigerante queda
       por diferencia. Comparado con la pelicula de Nusselt sin corregir da el
       producto phi_c*phi_v de la ec. 9-17.

    LO QUE NO RESUELVE, y hay que declararlo:

    - phi_c y phi_v NO se separan. El punto da su PRODUCTO, que es lo unico que
      interviene en la ec. 9-17. Separarlos exige un segundo punto a otra
      velocidad de vapor, exactamente como C1 y C2 del ap. 9.7.3 no se
      separaron con un solo punto.
    - El FACTOR DE ALARGAMIENTO sigue supuesto. Entra tres veces —en D_h = 2b/phi,
      en el area desarrollada y en el Reynolds— y el punto no basta para
      resolverlo junto a las otras dos incognitas. Se declara con `phi` y la
      sensibilidad se recorre variandolo.
    - La perdida de carga de FICHA incluye las perdidas de puerto, que esta
      funcion descuenta con `port_loss_Pa` a partir de la velocidad de conexion
      declarada. Es del orden del 5 %; su efecto sobre beta se acota variandolo.

    Se trabaja sobre UA y no sobre U porque UA es independiente del convenio de
    area: el catalogo refiere su U al area proyectada y el modelo marcha sobre
    la desarrollada, y confundirlos es justo el error que el ap. 9.6.2 advierte.
    """
    import math

    from scipy.optimize import brentq

    from .. import data as D
    from ..correlations import get
    from ..correlations.singlephase import reynolds

    df = df or D.load("placas_alfanova")
    unit = unit or "condensador_climatizacion"
    base = f"unidades.{unit}."
    pt = df.require(base + "punto_diseno")
    anc = df.require(base + "anclaje")
    geo_d = df.require(base + "geometria")
    avisos = []

    # `geom_overrides` permite recorrer la sensibilidad al recorte efectivo de
    # placa —L_w y L_p—, que es la otra incognita abierta: el area proyectada
    # reconstruida del 27-30H excede la declarada un 11 % y no se sabe si sobra
    # ancho o largo. Entra en la identificacion de beta por la seccion de paso.
    geom = D.plate_geometry(unit, df=df, phi=phi, beta_c=math.radians(45.0),
                            area_convention=area_convention, **geom_overrides)
    UA = anc["U_limpio_W_m2K"] * df.require(base + "area_m2")
    A = geom.A_total

    # --- lado de agua: estado y flujo -------------------------------------
    T_w = 0.5 * (pt["agua_T_in_C"] + pt["agua_T_out_C"]) + 273.15
    secondary.update_PT(P_AGUA, T_w)
    rho_w, mu_w, k_w, cp_w = (secondary.rho, secondary.mu, secondary.k,
                              secondary.cp)
    Pr_w = secondary.Pr
    m_w = pt["agua_caudal_m3_h"] / 3600.0 * rho_w
    G_w = m_w / (geom.n_channels_sec * geom.A_channel)
    Re_w = reynolds(G_w, geom.D_h, mu_w)
    dp_objetivo = pt["dp_agua_Pa"] - port_loss_Pa

    # --- 1. beta desde la perdida de carga --------------------------------
    f_fn = get("friction", "martin_vdi")

    def dp_de_beta(beta):
        f = f_fn(Re_w, beta_c=beta)
        return (f * (4.0 * geom.L_p / geom.D_h) * G_w ** 2 / (2.0 * rho_w)
                - dp_objetivo)

    lo, hi = (math.radians(b) for b in beta_bracket_deg)
    convergio = True
    if dp_de_beta(lo) * dp_de_beta(hi) > 0.0:
        convergio = False
        beta = hi if dp_de_beta(hi) < 0.0 else lo
        avisos.append(
            "La perdida de carga de ficha queda FUERA del rango de beta "
            f"[{beta_bracket_deg[0]}, {beta_bracket_deg[1]}] grados. beta no "
            "esta identificado: se devuelve el extremo mas proximo.")
    else:
        beta = brentq(dp_de_beta, lo, hi, xtol=1e-6)

    # --- 2. phi_c*phi_v desde la conductancia -----------------------------
    alpha_w = get("singlephase", "martin_vdi")(
        Re_w, Pr_w, k_w, geom.D_h, beta_c=beta)
    R_pared = geom.t_p / geom.k_p
    # El ensuciamiento NO se descuenta aqui: `UA` es ya la conductancia LIMPIA,
    # obtenida descontandolo del U de servicio de ficha. Restarlo otra vez lo
    # contaria dos veces, y con 2.7e-4 frente a una resistencia total de 2.8e-4
    # se llevaria por delante el lado de refrigerante entero.
    R_total = A / UA
    R_ref = R_total - 1.0 / alpha_w - R_pared
    if R_ref <= 0.0:
        avisos.append(
            "El lado de agua y la pared AGOTAN la resistencia global: no queda "
            "nada para el refrigerante. El anclaje no es interpretable.")
        return SelectionAnchor(
            beta_c=beta, beta_c_deg=math.degrees(beta), phi_c_phi_v=float("nan"),
            phi_adoptado=phi, UA_limpio=UA, alpha_agua=alpha_w,
            alpha_refrigerante=float("nan"), h_nusselt=float("nan"),
            Re_agua=Re_w, dT_pared=float("nan"), reparto={}, convergio=False,
            avisos=avisos)
    alpha_r = 1.0 / R_ref

    # Pelicula de Nusselt sin corregir. El salto pared-saturacion depende del
    # propio coeficiente, de modo que se itera: es el mismo acoplamiento
    # implicito del lazo interno del ap. 9.6.3.
    P = fluid.Psat(pt["T_cond_C"] + 273.15)
    sat = fluid.sat_props(P)
    q = UA * pt["MTD_K"] / A
    dT = q / alpha_r
    h_nu = get("plate_condensation", "nusselt_film")(
        0.5, 0.0, sat, geom, dT=dT, phi_c=1.0, phi_v=1.0)

    reparto = {"agua": (1.0 / alpha_w) / R_total,
               "pared": R_pared / R_total,
               "refrigerante": R_ref / R_total}
    if Re_w < 400.0:
        avisos.append(
            f"Reynolds del agua {Re_w:.0f}: regimen laminar franco. El "
            "ap. 9.6.7 ya declara esta debilidad para el desrecalentador.")
    return SelectionAnchor(
        beta_c=beta, beta_c_deg=math.degrees(beta),
        phi_c_phi_v=alpha_r / h_nu, phi_adoptado=phi, UA_limpio=UA,
        alpha_agua=alpha_w, alpha_refrigerante=alpha_r, h_nusselt=h_nu,
        Re_agua=Re_w, dT_pared=dT, reparto=reparto, convergio=convergio,
        avisos=avisos)
