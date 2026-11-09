"""Topologia por modo y lazo externo de resolucion. Apartados 9.3 y 9.4.

Este modulo es el que trata a los componentes de forma indiferenciada: recibe
los mismos objetos en los cinco modos y solo cambia COMO estan conectados, que
es la decision de implementacion del ap. 9.3 —geometria y parametros
identificados invariantes entre modos— y lo que hace consistente la comparacion
entre ellos.

Lo que conviene leer antes de usarlo:

1. **El vector de incognitas se dimensiona por modo.** Cada `ModeSpec` declara
   sus incognitas y sus residuos, y `Circuit.solve` construye el sistema a
   partir de esa declaracion: (P0, Pk) con R2 y R4 en todos los modos, mas el
   caudal de ACS con R5 en los modos con recuperacion (M-1, M-3 y M-5). Se
   itera sobre log P0, log(Pk/P0) y log m_acs, de modo que la relacion de
   compresion no puede invertirse.

2. **A_ef no se itera.** La ecuacion de orificio es lineal en ella: se despeja
   en forma cerrada y R1 queda nulo por construccion (`eliminate_A_ef=False`
   recupera el vector literal de la tabla 9.4, solo para medir la diferencia).

3. **R3 no es residuo del lazo externo.** `SemiEmpiricalCompressor.solve`
   cierra el balance de la pared ficticia (ec. 9-8) en un lazo propio; llevarlo
   tambien aqui daria un sistema singular. Viaja como VERIFICACION.

4. **R5 se cierra sobre el caudal de ACS**, no sobre su temperatura de salida,
   que es la variable de disparo que el propio componente resuelve.

5. **Metodo**: `least_squares` de region de confianza reflectiva (`trf`), con
   escalado por el jacobiano y hasta tres pasadas con paso de diferencias
   finitas decreciente; si no converge, arranques con otros pinzamientos
   (`ARRANQUES_ALTERNATIVOS`). La convergencia se juzga por los residuos, no
   por el indicador del metodo, y la validez por las verificaciones
   independientes de `_checks`.

Unidades: SI estricto (Pa, K, J/kg, kg/s, m, W). La conversion ocurre solo en
la frontera, en `units`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq, least_squares

from . import psychrometrics as psy
from .components.air_hx import AirCoil, AirState
from .components.compressor import SemiEmpiricalCompressor
from .components.expansion_valve import ExpansionValve
from .components.plate_hx import P_AGUA, PlateHeatExchanger
from .correlations import ExtrapolationLog
from .data import MissingData
from .props import Fluid


#: Claves de componente empleadas por las topologias. Son las mismas en los
#: cinco modos: lo que cambia es donde aparecen.
AIRE = "bateria"
CLIMA = "placas_clima"
ACS = "desrecalentador"


#: APROXIMACION DEL SERPENTIN DEL INTERACUMULADOR [K].
#:
#: El ap. 9.6.7 carga «el bucle cerrado de ACS hacia el INTERACUMULADOR», y un
#: interacumulador es por definicion un deposito con intercambiador interior: el
#: agua del primario tiene que salir del desrecalentador POR ENCIMA de la
#: consigna del deposito en el valor de esta aproximacion.
#:
#: Distinguirlas no es pedanteria. El capitulo escribia 60 C como salida del agua
#: del desrecalentador y 60 C como consigna de ACS, que son dos cosas distintas
#: separadas por estos 7 K; con la carga por serpentin, aquellos 60 de impulsion
#: dejaban el deposito en 53.
APROXIMACION_ACS_K = 7.0

#: CONSIGNA DEL DEPOSITO DE ACS POR MODO. Decision del autor del 22/09/2026.
#:
#: El dimensionado se hace para 60 C, como exige la prevencion de legionelosis, y
#: esa exigencia se cubre en los modos CON RECUPERACION: M-1 y M-3 producen el
#: ACS mientras la maquina hace climatizacion, de modo que el desrecalentador
#: recibe gas de descarga por encima de 120 C y el calor de alta temperatura es
#: un SUBPRODUCTO. Ahi los 60 C salen practicamente gratis.
#:
#: M-5 es otra cosa. Solo entra cuando NO hay demanda de climatizacion, y
#: entonces la condensacion tiene que situarse por encima de la impulsion y se
#: paga entera. Medido el 22/09/2026 en verano, con aire a 32 C y ACS desde
#: 15 C, sobre la IMPULSION:
#:
#:     impulsion   T_cond    Q al ACS    W_el    COP global
#:        60 C     57.7 C    19.32 kW    4376 W     4.41
#:        50 C     50.6 C    19.59 kW    3898 W     5.03
#:        45 C     47.4 C    19.72 kW    3700 W     5.33
#:
#: Las cifras publicadas son las de la tabla 7.4 del capitulo 7 (v5), sobre la
#: consigna del DEPOSITO y con 45 % de humedad: 60 C (impulsion 67) da 62.4 C,
#: 19.14 kW, 4713 W y COP global 4.06; 45 C (impulsion 52) da 52.0 C, 19.54 kW,
#: 3993 W y 4.89. Las fija `tests/test_circuit.py::TestPuntoDeReferenciaM5`.
#:
#: De ahi la consigna mas baja en M-5. Que el deposito se quede en 45 en ese modo
#: es admisible porque la temperatura sanitaria la cubren los modos con
#: recuperacion; el cap. 7 debe declarar con que medio se cubre ademas el choque
#: termico periodico.
CONSIGNA_DEPOSITO_ACS_K = {
    "M-1": 60.0 + 273.15,     # con recuperacion: exigencia sanitaria
    "M-3": 60.0 + 273.15,     # con recuperacion: exigencia sanitaria
    "M-5": 45.0 + 273.15,     # solo ACS: la alta temperatura no la cubre nadie
}

#: CONSIGNA DE IMPULSION, que es la que el modelo resuelve: el residuo R5 cierra
#: sobre la temperatura de SALIDA DEL AGUA del intercambiador. Se deriva de la
#: del deposito en lugar de escribirse a mano, para que las dos no puedan
#: separarse por descuido.
#:
#: NO ES UNA CONSTANTE DEL MODELO sino la consigna de control que el capitulo 7
#: adopta, y por eso vive aqui y no en `Setpoints`: quien resuelve un punto la
#: pasa expresamente. Se recoge en un solo sitio para que las campanas y los
#: contrastes citen la decision en lugar de repetir un numero.
CONSIGNA_ACS_K = {modo: T + APROXIMACION_ACS_K
                  for modo, T in CONSIGNA_DEPOSITO_ACS_K.items()}

#: RETORNO DEL PRIMARIO DE ACS. Decision del autor del 22/09/2026.
#:
#: NO ES UN DATO DE DISENO SINO UNA VARIABLE QUE BARRE. Con el deposito
#: estratificado, el agua que vuelve del serpentin arranca fria al principio de
#: la carga y va subiendo hasta acercarse a la temperatura del deposito al final.
#: Elegir «un» valor es elegir un punto de esa trayectoria.
#:
#: Y los dos criterios apuntan en direcciones CONTRARIAS. REMEDIDO el
#: 25/09/2026 con el punto de diseno resuelto como SISTEMA (decision del autor;
#: la tabla de antes usaba 40.3 kg/h de NH3, un caudal que no es el del
#: compresor), impulsion de 67 C:
#:
#:     retorno    M-1 (verano)            M-3 (invierno)
#:              Q       margen          Q       margen / titulo de salida
#:       25 C   1968 W  +1.2 K          2385 W  CONDENSA, x = 0.980
#:       30 C   1911 W  +3.3 K          2280 W  CONDENSA, x = 0.993
#:       35 C   1851 W  +5.5 K          2237 W  +0.02 K
#:       45 C   1713 W  +10.6 K         2115 W  +4.8 K
#:       60 C   1476 W  +19.6 K         1906 W  +13.6 K
#:
#: En invierno el criterio NO se cumple con retorno frio, ni siquiera con el
#: suelo de 30 C: el agua de climatizacion va de 40 a 45 C, se condensa a 49 C
#: y el margen se agota. DECISION DEL AUTOR del 25/09/2026: se ACEPTA la
#: condensacion parcial en invierno y se declara como limitacion.
#:
#: Para la POTENCIA RECUPERADA el peor caso es el retorno caliente —un 25 % menos
#: en todo el barrido—. Para el CRITERIO DE DIMENSIONADO del ap. 9.6.7 —que el
#: refrigerante no baje de saturacion dentro del desrecalentador— el peor caso es
#: el retorno FRIO, y ahi es donde muerde: a 25 C el margen se queda en 2.3 K.
#: Mas abajo se anula y el desrecalentador empieza a condensar dentro.
#:
#: El retorno frio no es hipotetico: es lo que ocurre despues de un consumo
#: grande, con el fondo del deposito cerca de la temperatura de red. De ahi la
#: tercera parte de la decision, que es de instalacion y no de modelo: PONER UN
#: SUELO AL RETORNO —valvula mezcladora o recirculacion en el primario— que no lo
#: deje bajar de unos 30 C. Cuesta un 3 % de potencia recuperada y protege el
#: criterio que sostiene la seleccion del desrecalentador.
RETORNO_ACS_K = {
    "diseno": 35.0 + 273.15,        # el valor del capitulo; carga con estratificacion
    "verificacion": 25.0 + 273.15,  # extremo frio: donde el criterio muerde
    "suelo_instalacion": 30.0 + 273.15,   # requisito de la instalacion
}


# ---------------------------------------------------------------------------
# Condiciones de contorno y consignas
# ---------------------------------------------------------------------------

@dataclass
class WaterStream:
    """Circuito de agua secundario. `m_dot` a None significa INCOGNITA."""
    T_in: float                       # K
    m_dot: float | None = None        # kg/s


def caudal_masico_aire(air: AirState) -> float:
    """Caudal masico de aire humedo [kg/s] que mueve el ventilador con el aire
    `air`: los 7 600 m3/h de la ficha por la densidad psicrometrica del aire de
    entrada (decision del autor, 01/10/2026)."""
    from . import data as D
    from . import psychrometrics as psy
    return psy.density(air.T, air.w, air.P) * D.caudal_aire_m3_h() / 3600.0


@dataclass
class Boundary:
    """Condiciones de contorno de un punto de operacion.

    `clima` y `acs` pueden ser None en los modos que no los usan. Pedirlos
    cuando el modo los necesita y no estan es un error explicito, no un valor
    por defecto.

    `m_dot_air`: caudal MASICO de aire humedo [kg/s]. Si no se da, se deduce del
    caudal en VOLUMEN del ventilador (7 600 m3/h de la ficha, el mismo en todos
    los modos; decision del autor, 01/10/2026) con la densidad psicrometrica del
    aire de entrada. El ventilador mueve un volumen casi constante: fijar la
    masa daria en calefaccion un caudal un 10 % menor que el real.
    """
    air: AirState
    m_dot_air: float | None = None    # kg/s
    clima: WaterStream | None = None
    acs: WaterStream | None = None
    T_amb: float = 298.15             # K

    def __post_init__(self):
        if self.m_dot_air is None:
            self.m_dot_air = caudal_masico_aire(self.air)

    def stream(self, servicio: str) -> WaterStream:
        s = {"clima": self.clima, "acs": self.acs}[servicio]
        if s is None:
            raise ValueError(
                f"El modo activo necesita el circuito de agua '{servicio}' y "
                f"no se ha declarado en las condiciones de contorno.")
        return s


@dataclass
class Setpoints:
    """Consignas del control (ap. 9.4.2).

    `T_evap` merece explicacion. Fijarla sustituye al modelo de evaporador: es
    exactamente lo que hace el ap. 9.7.8 al calcular el equilibrio de M-2
    «con el compresor operando a temperatura de evaporacion de 2 grados», sin
    resolver el lado de baja. Con ella el vector de incognitas pierde P0 y el
    sistema pierde R2. Es una variante de contorno declarada, no un atajo: el
    lado de baja no se modela y la capacidad frigorifica sale del balance
    entalpico, que es lo que el capitulo reporta.
    """
    superheat: float = 1.0            # K, consigna del lazo de recalentamiento
    subcooling: float = 0.0           # K a la salida del lado de alta
    T_acs: float | None = None        # K, consigna de ACS (R5)
    Q_high: float | None = None       # W entregados por el lado de alta (R4)
    T_evap: float | None = None       # K impuesta; ver arriba

    # NO hay consigna de potencia disipada. La tuvo —`Q_dissipated`, que cerraba
    # el residuo R6 de la opcion 2 de la decision D-1— y se retiro el 22/09/2026
    # con el reparto de M-5: si el calor residual no puede disiparse en el
    # circuito de climatizacion, no hay reparto que imponer. Ver `_TREN_M5`.


# ---------------------------------------------------------------------------
# Topologias de los cinco modos (ap. 9.3, tabla 9.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModeSpec:
    """Una topologia. Es DATO, no codigo: de ahi que anadir un modo o una
    incognita no obligue a tocar el lazo de resolucion."""
    name: str
    descripcion: str
    #: Componentes del lado de alta, en el orden que recorre el refrigerante.
    high: tuple
    #: Componentes del lado de baja, idem. Vacio si la evaporacion se impone.
    low: tuple
    #: Servicio secundario de cada componente.
    secondary: dict
    #: Componentes que forman un TREN de secundario compartido (ap. 9.3.1):
    #: presion comun y el mismo caudal de agua a contracorriente por todos.
    extended: tuple = ()
    unknowns: tuple = ("P0", "Pk", "A_ef")
    residuals: tuple = ("R1", "R2", "R4")
    #: Que hace el CIRCUITO de climatizacion en este modo, y por tanto si su
    #: calor cuenta como producto. Es informacion del modo, como la topologia, y
    #: no puede deducirse del signo del calor: en M-5 el intercambiador de
    #: climatizacion cede calor exactamente igual que en M-4, pero alli lo cede
    #: al circuito de fan-coils —y es el servicio— y aqui lo cede al agua de
    #: ACS, porque el circuito de climatizacion no participa.
    #:
    #: `inactivo` significa eso ultimo: el CIRCUITO no presta servicio y el
    #: INTERCAMBIADOR se presta al ACS. Su calor no se pierde ni se tira: entra
    #: en el producto por la via del ACS, que es donde de verdad va.
    clima: str = "frio"               # "frio" | "calor" | "inactivo"
    notas: str = ""

    def role(self, key: str) -> str:
        if key in self.high:
            return "condenser"
        if key in self.low:
            return "evaporator"
        raise KeyError(f"{key} no participa en {self.name}")

    def components(self) -> tuple:
        return tuple(self.high) + tuple(self.low)


#: ORDEN DEL TREN EXTENDIDO EN M-2. DECISION DEL AUTOR, 28/09/2026: el
#: refrigerante sale de la valvula y recorre valvula -> desrecalentador (placas
#: pequeno) -> climatizacion (placas grande) -> compresor, y el agua de los
#: fan-coils recorre fan-coil -> placas grande -> placas pequeno -> fan-coil, a
#: contracorriente. Es el MISMO sentido de agua que en M-4 y M-5 (grande y luego
#: pequeno), de modo que el circuito de agua no se reconecta entre modos; el
#: recalentamiento cae en el intercambiador grande, en el extremo por el que
#: entra el agua de retorno de los fan-coils, que es el mas caliente.
#:
#: Sustituye al orden valvula -> climatizacion -> desrecalentador que adoptaba
#: el §9.3.1 de la v31 (y el §7.5.2), con el agua en sentido inverso al de los
#: demas modos. CONSECUENCIA DE DISENO, reportada: en M-1 el desrecalentador
#: esta en la descarga y en M-2 en la aspiracion, lo que exige conmutarlo
#: tambien por el lado de refrigerante; el §7.4.5 dice hoy que la conmutacion se
#: hace solo en el lado de agua y el §7.4.2 lo situa entre el compresor y la
#: valvula de cuatro vias.
_TREN_M2 = (ACS, CLIMA)
#: En M-4 el orden si esta fijado por la fisica: el gas de descarga entra por el
#: desrecalentador, que es el extremo caliente del tren.
_TREN_M4 = (ACS, CLIMA)
#: M-5 EMPLEA LOS DOS INTERCAMBIADORES PARA EL ACS, en serie y con el agua a
#: contracorriente por ambos, que es lo que describe la tabla 9.3.
#:
#: DECISION DEL AUTOR del 22/09/2026, que REVIERTE la decision D-1 (3/09/2026)
#: en lo que a M-5 se refiere, y lo hace por una razon fisica que no admite
#: replica: el circuito de climatizacion solo tiene FAN-COILS. Disipar en el el
#: calor residual significa activarlos, y activarlos significa CALEFACTAR la
#: vivienda. Basta imaginar una demanda de ACS en verano, sin demanda de frio ni
#: de calor, para ver que la disipacion por esa via es imposible.
#:
#: Con ello desaparece el reparto entre ACS y disipacion, y con el la quinta
#: incognita y el residuo R6 que la opcion 2 de D-1 habia introducido: en M-5
#: TODO el calor del lado de alta va al ACS.
#:
#: El orden lo fija la fisica igual que en M-4: el gas de descarga entra por el
#: desrecalentador —extremo caliente— y termina de condensar y subenfriarse en
#: el de climatizacion, mientras el agua de ACS recorre el camino inverso.
_TREN_M5 = (ACS, CLIMA)


MODES: dict[str, ModeSpec] = {
    "M-1": ModeSpec(
        name="M-1", descripcion="Climatizacion (frio) con recuperacion para ACS",
        high=(ACS, AIRE), low=(CLIMA,),
        secondary={ACS: "acs", AIRE: "aire", CLIMA: "clima"},
        clima="frio",
        unknowns=("P0", "Pk", "A_ef", "m_acs"),
        residuals=("R1", "R2", "R4", "R5"),
        notas="Los dos intercambiadores de placas operan independientes, cada "
              "uno con su servicio."),
    "M-2": ModeSpec(
        name="M-2", descripcion="Climatizacion (frio)",
        high=(AIRE,), low=_TREN_M2,
        secondary={AIRE: "aire", CLIMA: "clima", ACS: "clima"},
        extended=_TREN_M2,
        clima="frio",
        unknowns=("P0", "Pk", "A_ef"), residuals=("R1", "R2", "R4"),
        notas="Bateria como condensador; evaporador extendido de dos placas a "
              "presion comun con el agua de climatizacion (ap. 9.3.1)."),
    "M-3": ModeSpec(
        name="M-3", descripcion="Calefaccion con recuperacion para ACS",
        high=(ACS, CLIMA), low=(AIRE,),
        secondary={ACS: "acs", CLIMA: "clima", AIRE: "aire"},
        clima="calor",
        unknowns=("P0", "Pk", "A_ef", "m_acs"),
        residuals=("R1", "R2", "R4", "R5"),
        notas="Desrecalentador dedicado a ACS; placas de climatizacion como "
              "condensador unico; bateria como evaporador."),
    "M-4": ModeSpec(
        name="M-4", descripcion="Calefaccion",
        high=_TREN_M4, low=(AIRE,),
        secondary={ACS: "clima", CLIMA: "clima", AIRE: "aire"},
        extended=_TREN_M4,
        clima="calor",
        unknowns=("P0", "Pk", "A_ef"), residuals=("R1", "R2", "R4"),
        notas="Condensador extendido de dos placas; bateria como evaporador. "
              "El desrecalentador cambia de familia de correlaciones respecto "
              "de M-1/M-3/M-5: aqui condensa, alli es gas monofasico."),
    "M-5": ModeSpec(
        name="M-5", descripcion="Produccion exclusiva de ACS",
        high=_TREN_M5, low=(AIRE,),
        secondary={ACS: "acs", CLIMA: "acs", AIRE: "aire"},
        extended=_TREN_M5,
        clima="inactivo",
        unknowns=("P0", "Pk", "A_ef", "m_acs"),
        residuals=("R1", "R2", "R4", "R5"),
        notas="Los DOS intercambiadores de placas en serie, ambos dedicados a "
              "ACS, con el agua a contracorriente por los dos. Es la topologia "
              "de la tabla 9.3, y el circuito de climatizacion NO participa."),
}


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass
class CircuitSolution:
    """Lo que el modelo reporta de un punto de operacion.

    No solo el punto: tambien las comprobaciones independientes del ap. 9.4.4,
    el diagnostico de regimen, la banda de carga y la marca de extrapolacion.
    Un resultado sin ellas no es utilizable para contrastar ninguna hipotesis.
    """
    mode: str
    converged: bool
    unknowns: dict = field(default_factory=dict)
    residuals: dict = field(default_factory=dict)
    max_residual: float = float("nan")
    boundary: Boundary | None = None
    setpoints: Setpoints | None = None
    #: Magnitudes del punto
    T_evap: float = float("nan")
    T_cond: float = float("nan")
    m_dot: float = 0.0
    Q_evap: float = 0.0               # W absorbidos por el refrigerante
    Q_high: float = 0.0               # W cedidos por el refrigerante (negativo)
    Q_acs: float = 0.0                # W al circuito de ACS
    Q_clima: float = 0.0              # W al circuito de climatizacion
    W_shaft: float = 0.0
    W_fan: float = 0.0
    T_dis: float = float("nan")
    subcooling: float = 0.0
    superheat: float = 0.0
    #: Resultados de componente, por clave
    components: dict = field(default_factory=dict)
    #: Comprobaciones independientes de la convergencia formal (ap. 9.4.4)
    checks: dict = field(default_factory=dict)
    charge: dict = field(default_factory=dict)
    #: Lineas activas del modo {par: LineResult} y carga del sistema
    #: (componentes + lineas), con la misma banda y el contraste de RS-5. Vacios
    #: si el circuito se monto sin lineas (C11-1).
    lines: dict = field(default_factory=dict)
    charge_sistema: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    extrapolated: bool = False
    excursions: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    #: Envolvente operativa (`envelope.evaluate`): limites del compresor y de la
    #: instalacion, con estado cumple / incumple / sin_dato.
    envelope: dict = field(default_factory=dict)
    message: str = ""

    @property
    def valid(self) -> bool:
        """Ap. 9.4.4: una solucion que satisfaga los residuos pero incumpla
        las verificaciones independientes se marca como NO valida."""
        return bool(self.converged and self.checks.get("ok", False))

    @property
    def admissible(self) -> bool:
        """Valido y sin ningun limite incumplido de los que pueden comprobarse.

        No es «dentro de la envolvente»: un limite `sin_dato` no se incumple,
        pero tampoco se ha comprobado (`envelope["completa"]` lo dice)."""
        return bool(self.valid
                    and self.envelope.get("dentro_de_lo_comprobable", False))

    def as_dict(self) -> dict:
        return {
            "modo": self.mode, "convergido": self.converged,
            "valido": self.valid,
            "incognitas": self.unknowns, "residuos": self.residuals,
            "residuo_maximo": self.max_residual,
            "T_evap": self.T_evap, "T_cond": self.T_cond,
            "m_dot": self.m_dot, "Q_evap": self.Q_evap, "Q_alta": self.Q_high,
            "Q_acs": self.Q_acs, "Q_clima": self.Q_clima,
            "W_eje": self.W_shaft, "W_ventilador": self.W_fan,
            "T_descarga": self.T_dis, "subenfriamiento": self.subcooling,
            "recalentamiento": self.superheat,
            "comprobaciones": self.checks, "carga": self.charge,
            "diagnostico": self.diagnostics,
            "admisible": self.admissible, "envolvente": self.envelope,
            "extrapolado": self.extrapolated,
            "excursiones": [str(e) for e in self.excursions],
            "procedencia": self.provenance, "mensaje": self.message,
        }


# ---------------------------------------------------------------------------
# Circuito
# ---------------------------------------------------------------------------

class Circuit:
    """Lazo externo del ap. 9.4 sobre una topologia del ap. 9.3.

    Los componentes se construyen UNA vez y se reutilizan en todos los modos:
    es el requisito del ap. 9.3 y la razon por la que la comparacion entre
    modos es consistente.
    """

    #: Ap. 9.4.4: tolerancia sobre el residuo relativo de cada ecuacion de
    #: cierre, la misma que emplea la resolucion del compresor.
    TOL = 1.0e-6
    #: Cierre de los balances de masa y energia, exigido por el ap. 9.4.4 como
    #: verificacion INDEPENDIENTE de la convergencia formal.
    #:
    #: Fijado en 1e-3 por el §6.7.1 de la v3 del capitulo 6, que hace suyo el
    #: valor que el repositorio ya aplicaba.
    TOL_BALANCE = 1.0e-3

    #: Tolerancia [K] de los disparos sobre la temperatura del agua en
    #: contracorriente, tanto del tren extendido como de un intercambiador de
    #: placas aislado. El ruido del disparo llega al residuo de recalentamiento
    #: amplificado por m_agua cp / m_ref, del orden de 2e5 en climatizacion. El
    #: 24/09/2026 se vio que el intercambiador AISLADO seguia con los 1e-3 K
    #: por defecto de `PlateHeatExchanger.solve`: en M-1 con ACS de 10 a 60 C
    #: el recalentamiento saltaba 1.6 K entre evaporaciones separadas 0.05 K
    #: —un ruido de 0.01 K en el agua— y el lazo externo se detenia a 0.4 K de
    #: la raiz. Es la misma leccion que ya se habia aplicado al tren.
    TOL_DISPARO = 1.0e-7
    #: Salto de saturacion equivalente a la perdida de carga de un
    #: intercambiador por encima del cual la hipotesis M8 se marca [K].
    UMBRAL_M8_K = 0.5

    #: Pinzamientos (aire, agua) [K] de los arranques alternativos del lazo
    #: externo, que solo se prueban si falla el arranque por defecto (10, 6).
    ARRANQUES_ALTERNATIVOS = ((6.0, 4.0), (6.0, 10.0), (14.0, 10.0),
                              (14.0, 4.0), (3.0, 3.0))

    def __init__(self, fluid: Fluid, compressor,
                 air_coil: AirCoil, plate_clima: PlateHeatExchanger | None,
                 plate_acs: PlateHeatExchanger | None,
                 valve: ExpansionValve | None = None,
                 extrapolation: ExtrapolationLog | None = None,
                 eliminate_A_ef: bool = True,
                 sustituciones: dict | None = None,
                 lines: dict | None = None,
                 compresor_fichero: str = "compresor_bock_f2",
                 compresor_transferido: bool = False):
        self.fluid = fluid
        #: Fichero de datos del compresor (`data/<compresor_fichero>.yaml`): de el
        #: salen la envolvente y el diagrama de aplicacion. `compresor_transferido`
        #: marca que se usa el compresor de otro fluido sin reidentificar (cap. 13).
        self.compresor_fichero = compresor_fichero
        self.compresor_transferido = compresor_transferido
        #: Sustituciones declaradas de datos (`data.sustituciones`). `solve`
        #: vuelve a entrar en ellas, porque algunos datos se leen al resolver;
        #: los componentes, que leen el resto al construirse, deben haberse
        #: construido dentro del mismo contexto (`campaign.build_circuit`).
        self.sustituciones = dict(sustituciones or {})
        self.compressor = compressor
        self.valve = valve or ExpansionValve(fluid)
        self._comp = {AIRE: air_coil, CLIMA: plate_clima, ACS: plate_acs}
        #: Lineas de refrigerante {par: RefrigerantLine} (C11-1). Opcionales:
        #: con presion uniforme y adiabaticas no cambian la solucion, y el
        #: capitulo 9 inventaria solo los componentes. Si estan, la solucion
        #: lleva `lines` y la carga del SISTEMA (`charge_sistema`).
        self.lines = dict(lines or {})
        # ELIMINACION EXACTA DE A_ef. La ec. 9-21 es LINEAL en el area
        # efectiva, de modo que R1 admite solucion cerrada: dado el caudal del
        # compresor y el estado a la entrada de la valvula, A_ef es el que hace
        # continuo el caudal, y el residuo sale identicamente nulo. Se conserva
        # y se reporta, pero sale del vector de iteracion.
        #
        # No es una simplificacion de comodidad. Con subenfriamiento de consigna
        # nulo —que es la condicion con la que el ap. 9.7.8 calcula el
        # equilibrio de M-2— la entrada de la valvula queda EXACTAMENTE en la
        # frontera de fase, donde la densidad que aparece en la ec. 9-21 es
        # discontinua: la derivada cruzada dR1/dPk se dispara y el jacobiano
        # queda mal condicionado aunque el sistema tenga solucion. Medido en
        # M-2: R1 recorre 2e-2 en 0.01 K de temperatura de condensacion,
        # mientras R4 recorre 9e-3 en 0.1 K.
        #
        # `eliminate_A_ef=False` recupera literalmente el vector de incognitas
        # del ap. 9.4.2, con A_ef dentro, para poder MEDIR la diferencia.
        self.eliminate_A_ef = bool(eliminate_A_ef)
        self.log = extrapolation or ExtrapolationLog()
        self._attach_log(self.log)
        #: Ap. 9.4.4: los casos no convergidos se REGISTRAN con su condicion
        #: de contorno y su residuo, no se descartan en silencio.
        self.failures: list = []

    # -- infraestructura ------------------------------------------------
    def component(self, key: str):
        c = self._comp.get(key)
        if c is None:
            raise MissingData(
                f"El modo activo necesita el componente '{key}' y no se ha "
                f"construido. Si falta porque faltan datos de geometria, el "
                f"modelo debe fallar aqui y no suponerlos (CLAUDE.md).")
        return c

    def _attach_log(self, log: ExtrapolationLog) -> None:
        """Cada componente anota en un registro PROPIO que reenvia al del
        punto: asi el resultado de un componente lleva solo sus excursiones y
        el del punto, todas."""
        for c in self._comp.values():
            if c is not None:
                c.log = ExtrapolationLog(strict=log.strict, parent=log)
        self.log = log

    @staticmethod
    def spec(mode: str) -> ModeSpec:
        try:
            return MODES[mode]
        except KeyError as exc:
            raise KeyError(
                f"Modo desconocido: {mode!r}. Disponibles: "
                f"{sorted(MODES)}") from exc

    def active_system(self, mode: str, sp: Setpoints) -> tuple:
        """Incognitas y residuos EFECTIVOS del modo (tarea E1).

        Es la funcion que materializa el dimensionado por modo: el sistema no
        esta fijo a cuatro incognitas y se reduce ademas si la temperatura de
        evaporacion se impone como condicion de contorno.
        """
        s = self.spec(mode)
        unknowns, residuals = list(s.unknowns), list(s.residuals)
        if self.eliminate_A_ef and "A_ef" in unknowns:
            unknowns.remove("A_ef")
            residuals.remove("R1")
        if sp.T_evap is not None:
            # La evaporacion impuesta sustituye al modelo de evaporador: P0 deja
            # de ser incognita y con ella desaparece la consigna de
            # recalentamiento como ecuacion de cierre.
            unknowns.remove("P0")
            residuals.remove("R2")
        if "m_acs" in unknowns and sp.T_acs is None:
            raise ValueError(
                "Los modos con recuperacion cierran R5 sobre la consigna de "
                "ACS: declara `T_acs` en las consignas.")
        if len(unknowns) != len(residuals):
            raise RuntimeError(
                f"Sistema mal planteado en {mode}: {len(unknowns)} incognitas "
                f"y {len(residuals)} residuos.")
        return tuple(unknowns), tuple(residuals)

    # -- empaquetado de incognitas --------------------------------------
    #
    # Se itera sobre LOGARITMOS de las presiones, y sobre log(Pk/P0) en lugar de
    # log(Pk): asi Pk > P0 se cumple por construccion y el metodo no puede
    # proponer una relacion de compresion invertida, que haria abortar al
    # compresor en lugar de devolver un residuo.
    def _pack(self, vals: dict, unknowns: tuple) -> np.ndarray:
        x = []
        for u in unknowns:
            if u == "P0":
                x.append(math.log(vals["P0"]))
            elif u == "Pk":
                x.append(math.log(vals["Pk"] / vals["P0"]))
            elif u == "A_ef":
                x.append(math.log(vals["A_ef"]))
            else:
                x.append(math.log(vals[u]))
        return np.array(x, dtype=float)

    def _unpack(self, x, unknowns: tuple, bc: Boundary, sp: Setpoints) -> dict:
        vals = {}
        if sp.T_evap is not None:
            vals["P0"] = self.fluid.Psat(sp.T_evap)
        for u, xi in zip(unknowns, x):
            if u == "P0":
                vals["P0"] = math.exp(xi)
            elif u == "Pk":
                vals["_ratio"] = math.exp(xi)
            else:
                vals[u] = math.exp(xi)
        vals["Pk"] = vals["P0"] * vals.pop("_ratio")
        if "m_acs" not in vals and bc.acs is not None:
            vals["m_acs"] = bc.acs.m_dot
        return vals

    # -- marcha de un lado del circuito ---------------------------------
    def _groups(self, keys: tuple, spec: ModeSpec) -> list:
        """Agrupa los componentes consecutivos que forman tren extendido."""
        out, buf = [], []
        for k in keys:
            if k in spec.extended:
                buf.append(k)
            else:
                if buf:
                    out.append(tuple(buf))
                    buf = []
                out.append((k,))
        if buf:
            out.append(tuple(buf))
        return out

    def _water(self, key: str, spec: ModeSpec, bc: Boundary,
               vals: dict) -> tuple:
        servicio = spec.secondary[key]
        stream = bc.stream(servicio)
        m = vals.get(f"m_{servicio}")
        if m is None:
            m = stream.m_dot
        if m is None:
            raise ValueError(
                f"Caudal del circuito '{servicio}' sin declarar y sin ser "
                f"incognita del modo {spec.name}.")
        return stream.T_in, m

    def _march_side(self, keys: tuple, spec: ModeSpec, P_in: float,
                    h_in: float, m_dot: float, bc: Boundary, vals: dict,
                    role: str, final: bool) -> tuple:
        """Recorre un lado del circuito. Devuelve (P, h, resultados)."""
        P, h, res = P_in, h_in, {}
        for group in self._groups(keys, spec):
            if len(group) == 1:
                k = group[0]
                if k == AIRE:
                    coil = self.component(AIRE)
                    # El papel pertenece al MODO, no al objeto: el ap. 9.3
                    # ya fija si la bateria condensa o evapora en cada uno de
                    # los cinco modos, y esa informacion existe antes de
                    # iterar. Sin el, el componente cae al respaldo por el
                    # signo de (T_aire - T_sat), que da el mismo resultado.
                    r = coil.solve(P, h, m_dot, bc.air, bc.m_dot_air,
                                   role=role)
                    h = r.h_ref_out
                    res[k] = r
                else:
                    hx = self.component(k)
                    T_sec, m_sec = self._water(k, spec, bc, vals)
                    r = hx.solve(P, h, m_dot, T_sec, m_sec, role=role,
                                 tol=self.TOL_DISPARO)
                    # M8: presion uniforme; la perdida de carga se publica.
                    h = r.h_ref_out
                    res[k] = r
            else:
                T_sec, m_sec = self._water(group[0], spec, bc, vals)
                P, h, rs = self._march_chain(group, P, h, m_dot, T_sec, m_sec,
                                             role, final)
                res.update(rs)
        return P, h, res

    def _march_chain(self, keys: tuple, P_in: float, h_in: float,
                     m_dot: float, T_sec_in: float, m_sec: float,
                     role: str, final: bool) -> tuple:
        """Tren de intercambiadores a presion comun con secundario compartido.

        Ap. 9.3.1: el refrigerante evoluciona a una presion comun a lo largo de
        los dos componentes —no hay valvula ni discontinuidad entre ellos— y el
        modelo los trata como una secuencia continua de volumenes de control.
        Por eso el disparo del ap. 9.6.6 se hace sobre el TREN completo y no
        sobre cada intercambiador por separado: la temperatura del agua en el
        punto de union no es dato de ninguno de los dos.
        """
        hxs = [self.component(k) for k in keys]

        def marcha(T_start: float):
            P, h, T = P_in, h_in, T_start
            outs = []
            for hx in hxs:
                out = hx.march(P, h, m_dot, T, m_sec, counterflow=True,
                               role=role)
                outs.append(out)
                P, h, T = out["P_out"], out["h_out"], out["T_sec_end"]
            return T, outs

        def shoot(T_start: float) -> float:
            try:
                return marcha(T_start)[0] - T_sec_in
            except ValueError:
                # Tentativa inviable del disparo (el secundario sale de su
                # rango de existencia). Se devuelve un residuo grande del signo
                # que aleja al metodo, en lugar de abortar la resolucion.
                return -1.0e3

        self.fluid.update_PH(P_in, h_in)
        T_r_in = self.fluid.T
        # Intervalo ACOTADO FISICAMENTE: la temperatura del agua en el extremo
        # de entrada del refrigerante esta entre su propia entrada y la del
        # refrigerante, porque no puede cruzarla.
        lo, hi = min(T_sec_in, T_r_in), max(T_sec_in, T_r_in)
        margen = max(0.01, 0.001 * (hi - lo))
        lo, hi = lo - margen, hi + margen

        for hx in hxs:
            hx._log_enabled = False
        try:
            # xtol FINO. El ruido de este disparo se propaga al residuo del
            # lazo externo amplificado por m_sec*cp/m_ref, que en climatizacion
            # es del orden de 2e5: un xtol de 1e-3 K deja el residuo de
            # recalentamiento con un suelo de ruido de 2e-2, muy por encima de
            # la tolerancia del ap. 9.4.4.
            T_star = brentq(shoot, lo, hi, xtol=self.TOL_DISPARO, maxiter=200)
            converged = True
        except (ValueError, RuntimeError):
            # El disparo del tren no cierra. Durante la iteracion del lazo
            # externo eso NO puede devolverse como si fuera una marcha valida:
            # el residuo resultante es ficticio y el metodo lo interpreta como
            # relieve del problema, se aparta de la solucion y se detiene. Se
            # senala como tentativa inviable y el lazo lo trata como tal.
            # En la evaluacion final se degrada con elegancia y se marca no
            # convergida, para que el ap. 9.4.4 pueda registrarla.
            if not final:
                raise _Unfeasible(
                    "el disparo del tren extendido no cierra") from None
            T_star, converged = T_sec_in, False
        finally:
            for hx in hxs:
                hx._log_enabled = bool(final)

        _, outs = marcha(T_star)
        for hx in hxs:
            hx._log_enabled = True

        res, P, h = {}, P_in, h_in
        for k, hx, out in zip(keys, hxs, outs):
            # Cada elemento se empaqueta con SU entrada: el balance de energia
            # del ap. 6.7.1 se comprueba entonces elemento a elemento y no solo
            # sobre el tren, que es donde un error de reparto se escondaria.
            r = hx.package(out, m_dot, m_sec, out["T_sec_end"], True, h)
            r.T_sec_out = out["T_sec_start"]
            # La entrada de secundario de un elemento del tren NO es la del
            # circuito: es la salida del elemento contiguo. Sin esto el balance
            # de entropia de la ec. del ap. 9.4.4 se calcularia contra la
            # entrada del circuito y daria generacion negativa en el elemento
            # aguas abajo del agua.
            r.T_sec_in = out["T_sec_end"]
            r.converged = converged
            res[k] = r
            P, h = out["P_out"], out["h_out"]
        return P, h, res

    # -- evaluacion del sistema -----------------------------------------
    def evaluate(self, x, mode: str, bc: Boundary, sp: Setpoints,
                 unknowns: tuple, residuals: tuple,
                 final: bool = False) -> dict:
        """Una marcha completa del circuito y el vector de residuos."""
        spec = self.spec(mode)
        vals = self._unpack(x, unknowns, bc, sp)
        P0, Pk = vals["P0"], vals["Pk"]
        f = self.fluid

        if Pk > 0.98 * f.p_crit:
            raise _Unfeasible(f"Pk = {Pk:.4g} Pa por encima del punto critico")

        # 1. Compresor. El balance de la pared ficticia (R3) se resuelve dentro.
        T_sat0 = f.Tsat(P0)
        T_su = T_sat0 + sp.superheat
        comp = self.compressor.solve(P0, T_su, Pk, T_amb=bc.T_amb)
        f.update_PT(P0, T_su)
        h_su, s_su = f.h, f.s

        # 2. Lado de alta, en el orden que recorre el refrigerante.
        P_hi, h_hi, res_hi = self._march_side(
            spec.high, spec, Pk, comp.h_dis, comp.m_dot, bc, vals,
            "condenser", final)

        # 3. Valvula de expansion, isoentalpica (hipotesis M3). Si A_ef se ha
        # eliminado, se obtiene en forma cerrada de la ec. 9-21 y R1 queda
        # satisfecho por construccion; si no, viene del vector de iteracion.
        if "A_ef" not in vals:
            vals["A_ef"] = self.valve.area_for_flow(comp.m_dot, P_hi, h_hi, P0)
        m_valve = self.valve.mass_flow(vals["A_ef"], P_hi, h_hi, P0)

        # 4. Lado de baja. Si la evaporacion se impone, no se modela.
        res_lo, h_lo = {}, None
        if sp.T_evap is None:
            _, h_lo, res_lo = self._march_side(
                spec.low, spec, P0, h_hi, comp.m_dot, bc, vals,
                "evaporator", final)

        # --- residuos (tabla 9.4) ---
        #
        # Se calculan TODOS los que el punto permite evaluar, aunque el vector
        # de iteracion no los use: un residuo eliminado por sustitucion sigue
        # siendo una ecuacion de cierre y debe poder comprobarse. `solve` toma
        # del diccionario solo los activos.
        r = {}
        r["R1"] = (comp.m_dot - m_valve) / max(comp.m_dot, 1e-9)
        if h_lo is not None:
            # Los residuos de temperatura se normalizan por la temperatura
            # ABSOLUTA de consigna, no por el salto. El ap. 9.4.4 fija la
            # tolerancia sobre el «residuo relativo de cada ecuacion de cierre»,
            # y una consigna de recalentamiento de 1 K normalizada por si misma
            # convierte el criterio en 1 microkelvin: por debajo de lo que
            # resuelve la propia biblioteca de propiedades, y por tanto
            # inalcanzable por el metodo. Referido a la temperatura absoluta,
            # 1e-6 son 0.3 mK, que si es exigente y si es alcanzable.
            sh = self._superheat(P0, h_lo)
            T_ref = f.Tsat(P0) + sp.superheat
            r["R2"] = (sh - sp.superheat) / max(T_ref, 1.0)
        if sp.Q_high is not None:
            # Demanda impuesta: la forma de la tabla 9.4 tal cual.
            Q_side = comp.m_dot * (h_hi - comp.h_dis)
            r["R4"] = (Q_side + abs(sp.Q_high)) / abs(sp.Q_high)
        else:
            # Cierre por SUBENFRIAMIENTO de consigna. Es la misma ecuacion de
            # cierre —anular Q_calculado menos Q_requerido equivale a situar la
            # entalpia de salida en su objetivo— escrita sobre la temperatura en
            # lugar de sobre la entalpia, y esa reescritura no es cosmetica.
            #
            # Completada la condensacion, la entalpia de salida SIGUE a la linea
            # de liquido saturado: al variar la presion de condensacion, h_out y
            # h_l(P) se mueven juntas y el residuo entalpico se queda casi
            # plano. Medido en M-2 con evaporador de placas, se estancaba en
            # -2.2e-2 y no mejoraba al refinar la discretizacion (50, 100, 200 y
            # 400 volumenes dan lo mismo): no era ruido, era un valle plano.
            #
            # Sobre la temperatura el problema desaparece: en la zona de liquido
            # un kelvin son unos 4.7 kJ/kg frente a los 1100 kJ/kg del calor
            # latente, de modo que el residuo gana dos ordenes de magnitud de
            # sensibilidad. Se prolonga al dominio bifasico por el exceso
            # entalpico dividido por el cp del liquido saturado, igual que el
            # recalentamiento, para no perder el gradiente cuando la
            # condensacion aun no ha terminado.
            sc = self._subcooling(P_hi, h_hi)
            T_ref = f.Tsat(P_hi) - sp.subcooling
            r["R4"] = (sc - sp.subcooling) / max(T_ref, 1.0)
        if ACS in res_hi and sp.T_acs is not None:
            T_acs_out = res_hi[ACS].T_sec_out
            r["R5"] = (T_acs_out - sp.T_acs) / max(sp.T_acs, 1.0)
        falta = [k for k in residuals if k not in r]
        if falta:
            raise RuntimeError(
                f"Residuos declarados y no evaluables en {spec.name}: {falta}")

        return {"vals": vals, "comp": comp, "res_hi": res_hi, "res_lo": res_lo,
                "h_hi": h_hi, "P_hi": P_hi, "h_lo": h_lo, "h_su": h_su,
                "s_su": s_su, "m_valve": m_valve, "residuals": r,
                "T_su": T_su, "spec": spec}

    def _superheat(self, P: float, h: float) -> float:
        """Recalentamiento a la salida del evaporador, PROLONGADO al dominio
        bifasico.

        Si la salida es vapor sobrecalentado es la definicion habitual,
        T - T_sat. Si no lo es, el recalentamiento fisico vale cero, y un
        residuo construido sobre el cero se queda PLANO: el metodo pierde el
        gradiente justo en la direccion en la que esta la solucion. Medido en
        M-2 con evaporador de placas, R2 se clavaba en -1.000 en todo un tramo
        de presion de condensacion y el lazo se detenia ahi.

        Se prolonga por el deficit entalpico dividido por el calor especifico
        del vapor saturado, que es la pendiente dT/dh del otro lado de la
        frontera: la funcion es continua y su derivada tambien lo es en primer
        orden. Un valor negativo significa salida humeda, y es informacion util
        —la consigna de recalentamiento no es alcanzable— y no un fallo.
        """
        f = self.fluid
        sat = f.sat_props(P)
        if h >= sat["h_v"]:
            f.update_PH(P, h)
            return f.T - sat["Tsat"]
        return (h - sat["h_v"]) / max(sat["cp_v"], 1e-6)

    def _subcooling(self, P: float, h: float) -> float:
        """Subenfriamiento a la salida del lado de alta, PROLONGADO al dominio
        bifasico: negativo cuando la condensacion no ha terminado."""
        f = self.fluid
        sat = f.sat_props(P)
        if h <= sat["h_l"]:
            f.update_PH(P, h)
            return sat["Tsat"] - f.T
        return (sat["h_l"] - h) / max(sat["cp_l"], 1e-6)

    def _h_target(self, P: float, sp: Setpoints) -> float:
        """Entalpia de salida del lado de alta que impone el subenfriamiento."""
        f = self.fluid
        sat = f.sat_props(P)
        if sp.subcooling <= 0.0:
            return sat["h_l"]
        f.update_PT(P, sat["Tsat"] - sp.subcooling)
        return f.h

    # -- inicializacion --------------------------------------------------
    def initial_guess(self, mode: str, bc: Boundary, sp: Setpoints,
                      pinch_air: float = 10.0, pinch_water: float = 6.0) -> dict:
        """Modelo simplificado de parametros agrupados (ap. 9.4.4).

        Presiones a partir de las temperaturas de los fluidos secundarios y de
        unas diferencias de pinzamiento supuestas; caudal del desplazamiento y
        el rendimiento volumetrico; area de la valvula, del caudal.
        """
        spec = self.spec(mode)
        f = self.fluid

        def T_sec_de(keys, extremo):
            k = keys[0] if extremo == "first" else keys[-1]
            if k == AIRE:
                return bc.air.T, pinch_air
            servicio = spec.secondary[k]
            # Con CONSIGNA de ACS, la temperatura que el refrigerante tiene que
            # batir en el lado de alta no es la de entrada del agua sino la de
            # salida, que es la consigna. La diferencia no es de matiz: en M-5,
            # donde los dos intercambiadores trabajan para el ACS, el agua entra
            # a 15 C y sale a 60, y estimar la condensacion sobre los 15
            # proponia una presion de alta POR DEBAJO de la de baja.
            if servicio == "acs" and sp.T_acs is not None:
                return sp.T_acs, pinch_water
            return bc.stream(servicio).T_in, pinch_water

        T_hi, d_hi = T_sec_de(spec.high, "last")
        Pk = f.Psat(T_hi + d_hi)
        if sp.T_evap is not None:
            P0 = f.Psat(sp.T_evap)
        else:
            T_lo, d_lo = T_sec_de(spec.low, "first")
            P0 = f.Psat(T_lo - d_lo)

        eta_v = self.compressor.eta_v(P0, Pk)
        f.update_PT(P0, f.Tsat(P0) + sp.superheat)
        m_est = self.compressor.geom.V_dot_swept * eta_v * f.rho

        vals = {"P0": P0, "Pk": Pk}
        vals["A_ef"] = self.valve.area_for_flow(
            m_est, Pk, self._h_target(Pk, sp), P0)

        if "m_acs" in spec.unknowns:
            f.update_PT(P0, f.Tsat(P0) + sp.superheat)
            h_dis = self.compressor.solve(
                P0, f.Tsat(P0) + sp.superheat, Pk, T_amb=bc.T_amb).h_dis
            # Hasta donde enfria el ACS al refrigerante depende de CUANTOS
            # intercambiadores tiene dedicados. Con el desrecalentador solo
            # —M-1 y M-3— llega al vapor saturado; con los dos en serie —M-5,
            # tabla 9.3— se lleva tambien la condensacion y el subenfriamiento,
            # que es del orden de cuatro veces mas calor. Estimar aqui lo
            # primero para el caso segundo daba un caudal de arranque cuatro
            # veces corto.
            solo_acs = [k for k, v in spec.secondary.items() if v == "acs"]
            h_fin = (self._h_target(Pk, sp) if CLIMA in solo_acs
                     else f.sat_props(Pk)["h_v"])
            Q_est = m_est * (h_dis - h_fin)
            dT = max(sp.T_acs - bc.stream("acs").T_in, 1.0)
            vals["m_acs"] = max(Q_est / (4180.0 * dT), 1e-4)
        return vals

    # -- lazo externo -----------------------------------------------------
    def solve(self, mode: str, bc: Boundary, sp: Setpoints,
              x0: dict | None = None, tol: float | None = None,
              max_nfev: int = 200, diff_step: float = 2.0e-3,
              verbose: int = 0) -> CircuitSolution:
        """Anula el sistema de residuos de la tabla 9.4; ver `_solve`.

        Envuelve la resolucion en las sustituciones declaradas del circuito,
        de modo que un dato sustituido lo sea tambien en lo que se lee al
        resolver, y que la procedencia las enumere."""
        from . import data as D
        with D.sustituciones(self.sustituciones):
            return self._solve(mode, bc, sp, x0=x0, tol=tol, max_nfev=max_nfev,
                               diff_step=diff_step, verbose=verbose)

    def _solve(self, mode: str, bc: Boundary, sp: Setpoints,
              x0: dict | None = None, tol: float | None = None,
              max_nfev: int = 200, diff_step: float = 2.0e-3,
              verbose: int = 0) -> CircuitSolution:
        """Anula el sistema de residuos de la tabla 9.4.

        Metodo: region de confianza reflectiva sobre los residuos (`least_squares`,
        `trf`), que es la familia que el ap. 9.4.3 pide —descenso por gradiente
        con region de confianza— por su robustez frente a la no linealidad.

        SOBRE `diff_step`. Los residuos no son suaves: el lado de alta se marcha
        sobre un numero finito de volumenes, de modo que cuando la frontera
        entre dos regimenes cruza el borde de un volumen el residuo salta. Un
        paso de diferencias finitas MENOR que ese escalon no mide la pendiente
        del residuo sino el ruido de la discretizacion, y el metodo encoge la
        region de confianza hasta detenerse lejos de la solucion. El valor por
        defecto, 2e-3 en la variable logaritmica, corresponde a unos 0.05 K de
        temperatura de saturacion, que es el orden del escalon con las
        discretizaciones de trabajo. Conviene subirlo si se marcha con pocos
        volumenes.

        SOBRE EL ESCALADO. Los residuos no son comparables entre si: en M-2 con
        evaporador de placas, R2 recorre 5 unidades por kelvin de evaporacion
        mientras R4 recorre 0.06 por kelvin de condensacion. Sin escalar, la
        region de confianza la gobierna el residuo mas sensible y el otro se
        queda sin resolver. `x_scale="jac"` normaliza por las columnas del
        jacobiano en cada iteracion, que es lo que corresponde a un sistema con
        incognitas de sensibilidad tan dispar.
        """
        spec = self.spec(mode)
        unknowns, residuals = self.active_system(mode, sp)
        tol = self.TOL if tol is None else tol
        vals0 = x0 or self.initial_guess(mode, bc, sp)
        x_init = self._pack(vals0, unknowns)

        # Durante la iteracion el registro de extrapolacion se manda a un
        # acumulador de usar y tirar: anotar la trayectoria del lazo externo
        # registraria como resultado cada tentativa del metodo, que es el mismo
        # error que ya se corrigio en los lazos interno e intermedio.
        provisional = ExtrapolationLog()
        self._attach_log(provisional)
        state = {}

        def fun(x):
            try:
                st = self.evaluate(x, mode, bc, sp, unknowns, residuals)
            except _Unfeasible:
                return np.full(len(residuals), 1.0e3)
            except MissingData:
                raise
            except (ValueError, RuntimeError):
                return np.full(len(residuals), 1.0e3)
            state["last"] = st
            return np.array([st["residuals"][k] for k in residuals])

        # Pasadas sucesivas con el paso de diferencias finitas cada vez mas
        # fino. La primera cruza los escalones de la discretizacion y lleva la
        # solucion a su entorno; las siguientes afinan. Hacerlo al reves —paso
        # fino desde el principio— mide ruido en lugar de pendiente y detiene el
        # metodo lejos de la solucion.
        def intento(x_ini):
            x_star, msg, best = x_ini, "", float("inf")
            for factor in (1.0, 0.1, 0.01):
                # PASO ABSOLUTO en la variable logaritmica. `least_squares`
                # aplica `diff_step` RELATIVO a max(1, |x|), y con x = log P0
                # ~ 13 el paso era trece veces el documentado arriba: ~0.7 K
                # de evaporacion, un jacobiano impreciso y convergencia lineal.
                # Corregido el 28/09/2026: misma solucion en los cinco modos y
                # de 3 a 5 veces menos evaluaciones (M-1 en diseno, de 284 a 56).
                paso = diff_step * factor / np.maximum(1.0, np.abs(x_star))
                try:
                    sol = least_squares(fun, x_star, method="trf",
                                        xtol=1e-14, ftol=1e-14, gtol=1e-14,
                                        x_scale="jac",
                                        diff_step=paso,
                                        max_nfev=max_nfev, verbose=verbose)
                except Exception as exc:                # noqa: BLE001
                    if isinstance(exc, MissingData):
                        raise
                    msg = f"fallo del metodo: {exc}"
                    break
                r_max = float(np.max(np.abs(sol.fun)))
                if r_max < best:
                    best, x_star, msg = r_max, sol.x, sol.message
                if best <= tol:
                    break
            return best, x_star, msg

        best, x_star, msg = intento(x_init)

        # ARRANQUES ALTERNATIVOS, 24/09/2026. La estimacion inicial supone
        # pinzamientos fijos (10 K en aire, 6 K en agua) y ningun par fijo sirve
        # para todos los modos: en la solucion, M-1 con ACS de 10 a 60 C tiene
        # 10.5 K en el evaporador de placas y M-3 en su condicion de diseno
        # 6.7 K en la bateria. Desde la estimacion por defecto el metodo caia
        # al otro lado de un codo o de un salto del residuo y se detenia; desde
        # un arranque del lado bueno convergen a 1e-11. Solo se entra aqui si
        # el primer intento falla, y el mensaje dice desde que arranque se
        # convergio: la solucion se verifica igual, por sus residuos y sus
        # comprobaciones.
        if best > tol and x0 is None:
            for p_aire, p_agua in self.ARRANQUES_ALTERNATIVOS:
                alt = self._pack(self.initial_guess(
                    mode, bc, sp, pinch_air=p_aire, pinch_water=p_agua),
                    unknowns)
                b_alt, x_alt, m_alt = intento(alt)
                if b_alt < best:
                    best, x_star = b_alt, x_alt
                    msg = (f"{m_alt} [arranque alternativo: pinzamientos "
                           f"{p_aire:g} K aire / {p_agua:g} K agua]")
                if best <= tol:
                    break

        # Evaluacion final, la unica que se registra como resultado.
        final_log = ExtrapolationLog()
        self._attach_log(final_log)
        try:
            st = self.evaluate(x_star, mode, bc, sp, unknowns, residuals,
                               final=True)
        except (MissingData,):
            raise
        except Exception as exc:                        # noqa: BLE001
            return self._failed(mode, bc, sp, unknowns, {}, float("inf"),
                                f"la evaluacion final aborto: {exc}")

        res = st["residuals"]
        max_res = max(abs(v) for v in res.values())
        converged = max_res <= tol
        out = self._report(mode, bc, sp, st, unknowns, converged, max_res,
                           final_log, msg)
        if not out.valid:
            # Ap. 9.4.4: se registra, no se descarta.
            self.failures.append(out)
        return out

    def _failed(self, mode, bc, sp, unknowns, res, max_res, msg):
        out = CircuitSolution(mode=mode, converged=False, residuals=res,
                              max_residual=max_res, boundary=bc, setpoints=sp,
                              message=msg)
        self.failures.append(out)
        return out

    # -- informe -----------------------------------------------------------
    def _report(self, mode, bc, sp, st, unknowns, converged, max_res,
                log, msg) -> CircuitSolution:
        f = self.fluid
        spec, comp, vals = st["spec"], st["comp"], st["vals"]
        P0, Pk = vals["P0"], vals["Pk"]
        res_hi, res_lo = st["res_hi"], st["res_lo"]

        Q_high = sum(r.Q_dot for r in res_hi.values())
        if res_lo:
            Q_evap = sum(r.Q_dot for r in res_lo.values())
        else:
            # Evaporacion impuesta: la capacidad sale del balance entalpico
            # entre la salida de la valvula y la aspiracion, que es como la
            # reporta el ap. 9.7.8.
            Q_evap = comp.m_dot * (st["h_su"] - st["h_hi"])

        sat_k = f.sat_props(st["P_hi"])
        subcooling = self._subcooling(st["P_hi"], st["h_hi"])
        if st["h_lo"] is not None:
            superheat = self._superheat(P0, st["h_lo"])
        else:
            superheat = sp.superheat

        Q_acs = sum(-r.Q_dot for k, r in res_hi.items()
                    if spec.secondary.get(k) == "acs")
        Q_clima = sum(-r.Q_dot for k, r in {**res_hi, **res_lo}.items()
                      if spec.secondary.get(k) == "clima")

        sol = CircuitSolution(
            mode=mode, converged=converged,
            unknowns={k: vals[k] for k in ("P0", "Pk", "A_ef") if k in vals}
                     | {k: vals[k] for k in ("m_acs",) if k in unknowns},
            residuals=dict(st["residuals"]), max_residual=max_res,
            boundary=bc, setpoints=sp,
            T_evap=f.Tsat(P0), T_cond=sat_k["Tsat"], m_dot=comp.m_dot,
            Q_evap=Q_evap, Q_high=Q_high, Q_acs=Q_acs, Q_clima=Q_clima,
            W_shaft=comp.W_shaft, T_dis=comp.T_dis,
            subcooling=subcooling, superheat=superheat,
            components={"compresor": comp, **res_hi, **res_lo},
            message=msg)

        coil = self._comp.get(AIRE)
        sol.W_fan = coil.fan_power() if coil is not None else 0.0
        sol.charge = self._charge(res_hi, res_lo, Q_evap)
        # Con la evaporacion impuesta no hay lado de baja y el inventario del
        # sistema no puede hacerse: no se inventan las lineas que faltan.
        if self.lines and res_lo:
            sol.lines = self._lines(spec, st)
            sol.charge_sistema = self._charge(
                res_hi, {**res_lo, **{f"linea {k}": r for k, r in sol.lines.items()}},
                Q_evap)
        sol.diagnostics = self._diagnostics(spec, res_hi, res_lo, coil)
        sol.checks = self._checks(st, sol, bc, sp)
        sol.extrapolated = log.extrapolated
        sol.excursions = log.excursions
        sol.provenance = self._provenance(spec, sp, log)
        from . import envelope
        sol.envelope = envelope.evaluate(self, sol)
        return sol

    def _lines(self, spec, st) -> dict:
        """Lineas ACTIVAS del modo, con el estado que llevan (C11-1).

        El recorrido es descarga -> alta -> valvula -> baja -> aspiracion, en el
        orden de la topologia. Cada tramo entre dos elementos consecutivos es
        la linea que une esos dos componentes fisicos; su estado es el de
        salida del de aguas arriba, porque es adiabatica y a presion uniforme.
        Una linea que la topologia pide y el fichero no declara es un dato que
        no existe: se falla, no se omite."""
        comp, vals = st["comp"], st["vals"]
        Pk, P0 = vals["Pk"], vals["P0"]
        tramos = []                        # (desde, hasta, P, h)
        prev, P, h = "descarga", Pk, comp.h_dis
        for k in spec.high:
            tramos.append((prev, k, P, h))
            prev, h = k, st["res_hi"][k].h_ref_out
        tramos.append((prev, "valvula", P, h))
        prev, P, h = "valvula", P0, st["h_hi"]
        for k in spec.low:
            tramos.append((prev, k, P, h))
            prev, h = k, st["res_lo"][k].h_ref_out
        tramos.append((prev, "aspiracion", P, st["h_lo"] if st["h_lo"] is not None
                       else st["h_su"]))
        out = {}
        for a, b, P, h in tramos:
            par = "--".join(sorted((a, b)))
            if par not in self.lines:
                raise MissingData(
                    f"lineas_refrigerante.yaml: el modo {spec.name} recorre la "
                    f"linea '{par}', que no esta declarada")
            out[par] = self.lines[par].solve(P, h, comp.m_dot)
        return out

    def _charge(self, res_hi, res_lo, Q_evap) -> dict:
        """Inventario del circuito. NUNCA un valor unico (ap. 9.9): la banda
        se compone sumando CADA correlacion sobre todos los componentes, no
        sumando los extremos de cada uno."""
        total = {}
        for r in list(res_hi.values()) + list(res_lo.values()):
            ch = getattr(r, "charge", None) or {}
            for k, v in ch.items():
                if k.startswith("_"):
                    continue
                total[k] = total.get(k, 0.0) + v
        if not total:
            return {}
        out = dict(total)
        out["_min"], out["_max"] = min(total.values()), max(total.values())
        out["_spread"] = out["_max"] / out["_min"] if out["_min"] > 0 else float("nan")
        # RS-5, tabla 8.7: <= 50 g/kW referidos a la capacidad que el modelo
        # calcule, no a una capacidad declarada a priori.
        if Q_evap > 0:
            out["_RS5_limite_kg"] = 0.050 * Q_evap / 1000.0
            out["_RS5_peor_caso"] = out["_max"] / out["_RS5_limite_kg"]
        return out

    def _diagnostics(self, spec, res_hi, res_lo, coil) -> dict:
        """Lo que CLAUDE.md exige reportar y no solo calcular."""
        d = {}
        for k, r in {**res_hi, **res_lo}.items():
            if hasattr(r, "volume_fraction"):
                d[k] = {"fraccion_volumen": r.volume_fraction,
                        "reparto_potencia": r.duty_fraction,
                        "U_media": r.U_mean}
            else:
                d[k] = {"fraccion_pared_humeda": r.wet_wall_fraction,
                        "dP": r.dP_ref, "dP_partes": r.dP_parts,
                        "balance": r.energy_balance_error}
        if coil is not None:
            d["ventilador_es_cota_inferior"] = coil.fan_power_is_lower_bound()
        return d

    def _checks(self, st, sol, bc, sp) -> dict:
        """Verificaciones INDEPENDIENTES de la convergencia formal (ap. 9.4.4).

        Cierre de los balances de masa y de energia sobre el conjunto del
        sistema y positividad de la generacion de entropia en todos los
        componentes. Una solucion que satisfaga los residuos pero incumpla estas
        verificaciones se marca como no valida.
        """
        comp = st["comp"]
        chk = {}

        # Masa: continuidad compresor / valvula.
        chk["masa"] = abs(comp.m_dot - st["m_valve"]) / max(comp.m_dot, 1e-12)

        # Energia sobre el conjunto: lo absorbido mas el trabajo al eje, menos
        # lo disipado al ambiente por el compresor, debe salir por el lado de
        # alta. Se compone de magnitudes de COMPONENTE, de modo que no cierra
        # por construccion.
        entra = sol.Q_evap + comp.W_shaft - comp.Q_amb
        sale = -sol.Q_high
        escala = max(abs(sale), abs(entra), 1.0)
        chk["energia"] = abs(entra - sale) / escala

        # Balance del compresor: R3 de la tabla 9.4, que aqui es verificacion
        # y no ecuacion del lazo externo (ver cabecera del modulo). Se reporta
        # en W y referido a la potencia al eje.
        #
        # El indicador de validez es el residuo relativo. CORREGIDO el
        # 24/09/2026: aqui se decia que, con AU_su_n = 0.0056 W/K, el residuo
        # de la ec. 9-1 «no puede hacerse exactamente nulo» y que el R3 de
        # 4e-4 de la potencia al eje era un hallazgo sobre la identificacion.
        # No lo era: el compresor acotaba T1 con max(T1, T_su) y se detenia en
        # la meseta que eso crea. Corregido en `SemiEmpiricalCompressor`, el
        # balance cierra a 1e-7 W.
        r3 = max(abs(v) for v in comp.residuals) if comp.residuals else 0.0
        chk["R3_pared_compresor_W"] = r3
        chk["R3_pared_compresor"] = r3 / max(abs(comp.W_shaft), 1.0)
        chk["compresor_metodo_convergido"] = bool(comp.converged)

        # Entropia por componente.
        chk["entropia"] = self._entropy(st, sol, bc)
        chk["entropia_minima"] = min(chk["entropia"].values())

        # Balance interno de cada intercambiador. En las placas lo calcula el
        # propio componente contra los estados extremos de ambos fluidos; en la
        # bateria se comprueba aqui contra el lado de aire, que la marcha no
        # emplea para cerrar nada y es por tanto una comprobacion independiente.
        comp_bal = {k: r.energy_balance_error
                    for k, r in {**st["res_hi"], **st["res_lo"]}.items()
                    if hasattr(r, "energy_balance_error")}
        coil_res = st["res_hi"].get(AIRE) or st["res_lo"].get(AIRE)
        if coil_res is not None:
            comp_bal[AIRE] = (abs(self._coil_air_duty(coil_res, bc)
                                  + coil_res.Q_dot)
                              / max(abs(coil_res.Q_dot), 1.0))
        chk["balance_componentes"] = comp_bal

        # Valvula: el area de la ec. 9-21 no puede exceder la del dispositivo.
        # Si lo hace, la consigna es inalcanzable con esa valvula, y eso es un
        # resultado del modelo, no un fallo numerico.
        chk["area_efectiva_valvula_m2"] = st["vals"]["A_ef"]

        # Comprobacion a posteriori de M8 (decision del autor, 29/09/2026): el
        # salto de saturacion que supondria la perdida de carga de cada
        # intercambiador de placas. Es informativa y no entra en la validez: la
        # hipotesis se declara, y se marca donde deja de ser despreciable.
        chk["M8_salto_saturacion_K"] = {
            k: float(r.dT_sat_equivalente)
            for k, r in {**st["res_hi"], **st["res_lo"]}.items()
            if hasattr(r, "dT_sat_equivalente")}
        chk["M8_supera_umbral"] = sorted(
            k for k, v in chk["M8_salto_saturacion_K"].items()
            if v > self.UMBRAL_M8_K)

        # Convergencia de los lazos intermedios: un intercambiador cuya marcha
        # no cerro no puede sostener una solucion del lazo externo.
        chk["componentes_convergidos"] = {
            k: bool(getattr(r, "converged", True))
            for k, r in {**st["res_hi"], **st["res_lo"]}.items()}

        chk["ok"] = bool(
            all(chk["componentes_convergidos"].values())
            and chk["masa"] <= self.TOL_BALANCE
            and chk["energia"] <= self.TOL_BALANCE
            and chk["entropia_minima"] > -1e-9
            and chk["R3_pared_compresor"] <= self.TOL_BALANCE
            and max(comp_bal.values(), default=0.0) <= self.TOL_BALANCE)
        return chk

    @staticmethod
    def _coil_air_duty(r, bc) -> float:
        """Potencia ganada por la corriente de aire [W], para el balance.

        CORREGIDO el 24/09/2026. Antes se tomaba solo la parte SENSIBLE,
        m cp (T_out - T_in), y con la superficie humeda eso deja fuera el calor
        latente: en la condicion nominal de la UNE-EN 14511 (7 C bs / 6 C bh)
        M-4 y M-3 salian NO VALIDOS con un 34 % de error de balance que no era
        del componente sino de esta comprobacion. Es el mismo error que el
        21/09/2026 se corrigio en la entropia del aire (`_dS_aire`).

        Se suma el termino latente, m_seco [(h_out - h_in) - cp_da (T_out -
        T_in)], y la forma no es indiferente. Tiene que ser COHERENTE CON LA
        ENERGIA QUE EL COMPONENTE CALCULA, por la misma razon que en la
        entropia: la marcha seca emplea `bc.air.cp`, que con el `AirState` por
        defecto es el cp = 1005 del anclaje (ap. 9.7.3) y no el de la entalpia
        psicrometrica, un 1.6 % mayor. Con esta forma:

        - en las celdas SECAS el termino latente es nulo sea cual sea el cp,
          porque `h_air_out` es lineal en T a humedad constante, y queda la
          comprobacion sensible de siempre, exacta;
        - con `AirState.at`, donde m cp = m_seco cp_da, el total es
          m_seco (h_out - h_in), que es la ec. 9-28 que cierra la marcha
          humeda. Sin la entalpia del condensado retirado, como el convenio de
          ASHRAE que el componente adopta.

        Solo queda inexacta la parte sensible de las celdas HUMEDAS si se usa el
        `AirState` por defecto como evaporador, que la clase ya advierte que no
        debe hacerse.
        """
        dT = r.T_air_out - bc.air.T
        sensible = bc.m_dot_air * bc.air.cp * dT
        m_seco = bc.air.dry_mass_flow(bc.m_dot_air)
        latente = m_seco * ((r.h_air_out - bc.air.h) - bc.air.cp_da * dT)
        return sensible + latente

    @staticmethod
    def _dS_aire(r, bc) -> float:
        """Variacion de entropia de la corriente de aire [W/K].

        CORREGIDO el 21/09/2026. Antes se tomaba solo la parte SENSIBLE,
        m cp ln(T_out/T_in). Es exacto con la superficie seca —el caso del
        condensador en M-2— y falso en cuanto condensa: deja fuera la entropia
        que se lleva el vapor al pasar a liquido, que en la condicion nominal
        de calefaccion es un tercio del calor intercambiado. La disminucion de
        entropia del aire salia corta y la generacion del serpentin, que es la
        SUMA con la del refrigerante, salia larga por un factor de veinte.

        Lo delato el cierre del balance exergetico del ap. 9.11.2: daba mas
        exergia destruida que potencia electrica consumida, que es imposible.

        El termino que faltaba es el del condensado. El vapor que abandona la
        corriente lo hace como liquido, y se lleva la diferencia de entropia
        entre las dos fases a la temperatura de la superficie donde condensa:

            dS_latente = - m_cond (h_fg / T_superficie)

        SOBRE EL CALOR ESPECIFICO. Se emplea `bc.air.cp`, el mismo con el que
        el componente ha calculado la ENERGIA, y no la entropia de mezcla
        exacta de `psychrometrics.entropy`. La razon es de coherencia y no de
        comodidad: el ap. 9.7.3 anclo el lado de aire con cp = 1005 J/(kg K)
        por kg de MEZCLA, y la entropia de mezcla equivale a 1039 por kg de
        aire SECO, un 1.6 % mas. Calcular la energia con uno y la entropia con
        el otro es lo que rompe el cierre exergetico.

        Y conviene anotar la sensibilidad, porque es grande: ese 1.6 % en la
        entropia del aire se traduce en un 38 % en la generacion del serpentin,
        porque esta es la DIFERENCIA entre dos numeros veinticinco veces
        mayores que ella. La generacion de entropia del serpentin es una
        magnitud fragil, y cualquier resultado que descanse en ella —el reparto
        de exergia destruida, sin ir mas lejos— hereda esa fragilidad.
        """
        dS = bc.m_dot_air * bc.air.cp * math.log(
            max(r.T_air_out, 1.0) / bc.air.T)
        m_cond = getattr(r, "m_condensate", 0.0)
        if m_cond:
            T_sup = 0.5 * (getattr(r, "T_surface_min", r.T_air_out)
                           + getattr(r, "T_surface_max", r.T_air_out))
            T_sup = max(T_sup, 250.0)
            dS -= m_cond * psy.H_FG_0 / T_sup
        return dS

    def _entropy(self, st, sol, bc) -> dict:
        """Generacion de entropia por componente [W/K].

        Se recorre el circuito en el orden del refrigerante, arrastrando su
        estado de un componente al siguiente: es la unica forma de que el
        estado de entrada de cada uno sea el de salida del anterior tambien en
        los trenes de dos intercambiadores.
        """
        f, out = self.fluid, {}
        comp, spec = st["comp"], st["spec"]
        res = {**st["res_hi"], **st["res_lo"]}
        m = comp.m_dot

        f.update_PT(st["vals"]["P0"], st["T_su"])
        s_su = f.s
        f.update_PH(st["vals"]["Pk"], comp.h_dis)
        s_dis = f.s
        # Compresor ABIERTO: el calor sale al ambiente, no al refrigerante.
        out["compresor"] = m * (s_dis - s_su) + comp.Q_amb / bc.T_amb

        def recorre(keys, P, h):
            for k in keys:
                r = res.get(k)
                if r is None:
                    continue
                f.update_PH(P, h)
                s_in = f.s
                P_out = P                  # presion uniforme, hipotesis M8
                f.update_PH(P_out, r.h_ref_out)
                s_out = f.s
                if k == AIRE:
                    dS_sec = self._dS_aire(r, bc)
                else:
                    servicio = spec.secondary[k]
                    T_in = (getattr(r, "T_sec_in", None)
                            or bc.stream(servicio).T_in)
                    m_sec = (st["vals"].get(f"m_{servicio}")
                             or bc.stream(servicio).m_dot)
                    # Entropia del agua EXACTA, coherente con la marcha en
                    # entalpia de la ec. 9-11 (24/09/2026). Antes
                    # m cp(T_in) ln(T_out/T_in), con el mismo cp constante que
                    # desajustaba el balance de las placas.
                    f_sec = self.component(k).sec
                    f_sec.update_PT(P_AGUA, T_in)
                    s_w_in = f_sec.s
                    f_sec.update_PT(P_AGUA, max(r.T_sec_out, 1.0))
                    dS_sec = m_sec * (f_sec.s - s_w_in)
                out[k] = m * (s_out - s_in) + dS_sec
                P, h = P_out, r.h_ref_out
            return P, h

        P, h = recorre(spec.high, st["vals"]["Pk"], comp.h_dis)

        # Valvula, isoentalpica: toda su generacion es la expansion.
        f.update_PH(P, h)
        s3 = f.s
        f.update_PH(st["vals"]["P0"], h)
        out["valvula"] = m * (f.s - s3)

        recorre(spec.low, st["vals"]["P0"], h)
        return out

    def _provenance(self, spec, sp, log) -> dict:
        prov = {
            "modo": spec.name, "topologia_alta": spec.high,
            "topologia_baja": spec.low, "tren_extendido": spec.extended,
            "incognitas_declaradas": spec.unknowns,
            "residuos_declarados": spec.residuals,
            "notas_topologia": spec.notas,
            "tolerancia_residuos": self.TOL,
            "tolerancia_balances": self.TOL_BALANCE,
            "evaporacion_impuesta": sp.T_evap is not None,
            "correlaciones": {},
            "geometria_inyectada": {},
            "sustituciones": {},
            "parametros_de_componente": {},
        }
        from . import data as D
        prov["sustituciones"] = D.sustituciones_activas()
        for k, c in self._comp.items():
            if c is None:
                continue
            prov["correlaciones"][k] = dict(c.corr)
            if getattr(c, "phi_md", 1.0) != 1.0:
                prov["parametros_de_componente"][k] = {"phi_md": c.phi_md}
            g = getattr(c, "geom", None)
            inj = getattr(g, "provenance", None)
            if inj:
                prov["geometria_inyectada"][k] = inj
        prov["extrapolacion"] = log.as_dict()
        prov["compresor"] = {"fichero": self.compresor_fichero,
                             "transferido_sin_reidentificar": self.compresor_transferido,
                             "modelo": getattr(self.compressor, "procedencia", {}).get(
                                 "modelo", "semiempirico"),
                             "velocidad_rpm": self.compressor.geom.n_rpm}
        return prov

    # -- continuacion ------------------------------------------------------
    def sweep(self, mode: str, bc_list, sp_list=None, sp: Setpoints | None = None,
              **kw) -> list:
        """Campana parametrica con CONTINUACION sobre el parametro barrido.

        Ap. 9.4.4: se toma como inicializacion la solucion del caso
        inmediatamente anterior, lo que reduce sustancialmente los fallos de
        convergencia. Un caso que falla no interrumpe el barrido ni desaparece:
        se devuelve en la lista y queda ademas en `self.failures`.
        """
        sps = list(sp_list) if sp_list is not None else [sp or Setpoints()] * len(bc_list)
        out, x0 = [], None
        for bci, spi in zip(bc_list, sps):
            s = self.solve(mode, bci, spi, x0=x0, **kw)
            out.append(s)
            x0 = dict(s.unknowns) if s.converged else None
        return out


class _Unfeasible(RuntimeError):
    """Tentativa del lazo externo fuera del dominio fisico."""
