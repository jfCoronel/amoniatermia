"""Geometria de los componentes. Apartados 9.5, 9.6.2 y 9.7.1.

Todas las magnitudes en SI estricto. Los parametros marcados como ESTIMADO
en el campo `provenance` deben incorporarse al analisis de sensibilidad del
apartado 6.11.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlateGeometry:
    """Geometria de un intercambiador de placas corrugadas (ap. 9.6.2).

    Attributes
    ----------
    n_plates : int
        Numero total de placas.
    b : float
        Paso entre placas (amplitud de corrugacion) [m].
    L_w : float
        Anchura efectiva de placa [m].
    L_p : float
        Longitud efectiva de placa [m].
    beta_c : float
        Angulo de corrugacion respecto a la direccion de flujo [rad].
    phi : float
        Factor de alargamiento superficial [-]. Rara vez publicado por los
        fabricantes: si se estima, declararlo en `provenance`.
    t_p : float
        Espesor de placa [m].
    k_p : float
        Conductividad del material de placa [W/m/K]. Acero inoxidable ~15.
    R_f : float
        Resistencia de ensuciamiento [m2 K/W].
    area_convention : str
        "developed" o "projected". Ver `A_total`.
    provenance : dict
        Origen de cada parametro: "catalogo", "medido" o "ESTIMADO".
    """
    n_plates: int
    b: float
    L_w: float
    L_p: float
    beta_c: float
    phi: float = 1.17
    t_p: float = 0.0004
    k_p: float = 15.0
    R_f: float = 0.0
    #: Convenio de area de transferencia. Ver `A_total` para por que el valor
    #: por defecto es el area desarrollada y no la de catalogo.
    area_convention: str = "developed"
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.area_convention not in ("developed", "projected"):
            raise ValueError(
                "area_convention debe ser 'developed' o 'projected', no "
                f"{self.area_convention!r}")

    @property
    def n_channels_total(self) -> int:
        return self.n_plates - 1

    @property
    def n_channels_ref(self) -> int:
        """Canales del lado refrigerante (reparto alterno)."""
        return (self.n_plates - 1) // 2

    @property
    def n_channels_sec(self) -> int:
        return self.n_channels_total - self.n_channels_ref

    @property
    def D_h(self) -> float:
        """Diametro hidraulico, ec. 9-13: D_h = 2 b / phi."""
        return 2.0 * self.b / self.phi

    @property
    def A_channel(self) -> float:
        """Seccion de paso de un canal [m2]."""
        return self.b * self.L_w

    @property
    def n_plates_active(self) -> int:
        """Placas que transfieren: las dos extremas tienen fluido por una cara."""
        return self.n_plates - 2

    @property
    def A_plate_projected(self) -> float:
        """Area PROYECTADA de una placa [m2]: Lw x Lp, sin corrugar."""
        return self.L_w * self.L_p

    @property
    def A_plate(self) -> float:
        """Area de transferencia DESARROLLADA por placa [m2]: phi x Lw x Lp."""
        return self.phi * self.A_plate_projected

    @property
    def A_total_projected(self) -> float:
        """Area proyectada total [m2]. Es el convenio de los catalogos."""
        return self.n_plates_active * self.A_plate_projected

    @property
    def A_total_developed(self) -> float:
        """Area desarrollada total [m2], con el factor de alargamiento."""
        return self.n_plates_active * self.A_plate

    @property
    def A_total(self) -> float:
        """Area de transferencia segun el convenio declarado [m2].

        CONVENIO ADOPTADO: DESARROLLADA. La razon no es de preferencia sino de
        coherencia interna. El diametro hidraulico de la ec. 9-13 es
        D_h = 2b/phi, que es la definicion del VDI Heat Atlas, y la correlacion
        de Martin que el ap. 9.6.7 emplea esta formulada sobre ESE diametro y
        sobre el area desarrollada. Emparejar D_h = 2b/phi con el area proyectada
        mezcla dos convenios y contabiliza el corrugado una vez en el diametro y
        ninguna en el area.

        El area que declaran los catalogos es la proyectada: la tabla 9.12 da
        0.0995 m2 para el AlfaNova 16-10H, frente a los 0.117 m2 desarrollados
        con phi = 1.15. La discrepancia es del 17.7 % y NO es un error de
        ninguno de los dos: son dos magnitudes distintas. Lo que seria un error
        es usar un U de catalogo, referido al area proyectada, contra el area
        desarrollada.

        `area_convention="projected"` esta disponible precisamente para ese caso
        y para la sensibilidad del ap. 6.11.
        """
        return (self.A_total_developed if self.area_convention == "developed"
                else self.A_total_projected)

    def area_report(self, declared: float | None = None) -> dict:
        """Contraste de los dos convenios contra el area declarada.

        `declared` es el area de catalogo (`area_m2` en el fichero de datos).
        Se compara contra la PROYECTADA, que es el convenio con el que los
        fabricantes la publican; el residuo que quede mide lo que la geometria
        reconstruida no explica —zonas de puerto, marco de junta o una
        diferencia entre la longitud entre puertos y la longitud efectiva de
        placa— y no debe confundirse con el efecto del corrugado.
        """
        out = {
            "convenio": self.area_convention,
            "proyectada_m2": self.A_total_projected,
            "desarrollada_m2": self.A_total_developed,
            "en_uso_m2": self.A_total,
            "phi": self.phi,
            "razon_desarrollada_proyectada": (self.A_total_developed
                                              / self.A_total_projected),
        }
        if declared is not None:
            out["declarada_m2"] = declared
            out["desv_proyectada"] = (self.A_total_projected - declared) / declared
            out["desv_desarrollada"] = (self.A_total_developed - declared) / declared
        return out

    def mass_flux(self, m_dot: float, side: str = "ref") -> float:
        """Flujo masico por unidad de area, ec. 9-13."""
        n = self.n_channels_ref if side == "ref" else self.n_channels_sec
        return m_dot / (n * self.A_channel)

    @staticmethod
    def phi_from_corrugation(b: float, pitch: float) -> float:
        """Estimacion de phi por la aproximacion de tres puntos.

        X = 2 pi b / pitch ; phi ~ (1 + sqrt(1+X^2) + 4 sqrt(1+X^2/2)) / 6
        """
        X = 2.0 * math.pi * b / pitch
        return (1.0 + math.sqrt(1.0 + X ** 2)
                + 4.0 * math.sqrt(1.0 + X ** 2 / 2.0)) / 6.0


@dataclass(frozen=True)
class CompressorGeometry:
    """Geometria del compresor alternativo abierto (ap. 9.5).

    Attributes
    ----------
    V_swept : float
        Volumen barrido por revolucion [m3].
    n_rpm : float
        Velocidad de giro [rpm]. Fija en el compresor sin variador.

    La relacion de volumenes interna NO es geometria aqui: es uno de los nueve
    parametros identificados (`CompressorParams.r_v`, §9.5.3). El campo que
    tenia este dataclass se retiro el 25/09/2026: nadie lo leia y arrastraba el
    2.0 del juego antiguo.
    """
    V_swept: float
    n_rpm: float

    @property
    def V_dot_swept(self) -> float:
        """Caudal volumetrico barrido [m3/s]."""
        return self.V_swept * self.n_rpm / 60.0


@dataclass(frozen=True)
class FinnedCoilGeometry:
    """Geometria de un serpentin de tubo y aleta (ap. 9.7.1).

    Reconstruida a partir de la ficha del fabricante. El ap. 9.7.1 exige
    verificar la reconstruccion ANTES de emplearla: si la geometria no reproduce
    las magnitudes agregadas declaradas, el anclaje de la correlacion de aire del
    ap. 9.7.3 absorberia el error geometrico dentro del coeficiente y destruiria
    su transferibilidad al regimen de evaporacion, que es justamente lo que el
    capitulo necesita predecir. `verification_report()` es esa comprobacion.

    Attributes
    ----------
    S_t, S_l : float
        Paso transversal y longitudinal [m]. Con S_l = S_t cos(30) la
        disposicion es de tresbolillo equilatero, lo que fija el radio
        equivalente de aleta del ap. 9.7.4.
    L : float             Longitud de bateria [m].
    n_tubes_row : int     Tubos por rango.
    n_rows : int          Numero de rangos (filas en el sentido del aire).
    n_circuits : int      Circuitos de refrigerante en paralelo.
    fin_pitch : float     Paso de aleta [m].
    fin_thickness : float Espesor de aleta [m].
    d_o, d_i : float      Diametro exterior e interior de tubo [m].
    k_fin, k_tube : float Conductividad de aleta y tubo [W/m/K].
    R_contact : float     Resistencia de contacto aleta-tubo [m2 K/W] referida
                          al area externa. Valor nominal nulo, sometido a
                          sensibilidad (docs/historico/PENDIENTES.md).
    """
    S_t: float
    S_l: float
    L: float
    n_tubes_row: int
    n_rows: int
    n_circuits: int
    fin_pitch: float
    fin_thickness: float
    d_o: float
    d_i: float
    k_fin: float = 200.0
    k_tube: float = 15.0
    R_contact: float = 0.0
    provenance: dict = field(default_factory=dict)

    # ---------------- Magnitudes basicas ----------------
    @property
    def n_tubes(self) -> int:
        return self.n_tubes_row * self.n_rows

    @property
    def L_tube(self) -> float:
        """Longitud total de tubo [m]."""
        return self.n_tubes * self.L

    @property
    def d_c(self) -> float:
        """Diametro con collarin [m]: el de referencia del Reynolds de aire."""
        return self.d_o + 2.0 * self.fin_thickness

    @property
    def n_fins(self) -> int:
        return int(round(self.L / self.fin_pitch))

    @property
    def is_equilateral_staggered(self) -> bool:
        """Tresbolillo equilatero: S_l = S_t cos(30)."""
        return abs(self.S_l - self.S_t * math.cos(math.radians(30.0))) < 1e-4

    # ---------------- Areas ----------------
    @property
    def A_fin(self) -> float:
        """Area de aleta, dos caras, descontando los taladros de paso [m2]."""
        ancho = self.n_tubes_row * self.S_t
        prof = self.n_rows * self.S_l
        taladros = self.n_tubes * math.pi / 4.0 * self.d_o ** 2
        return self.n_fins * 2.0 * (ancho * prof - taladros)

    @property
    def A_tube_bare(self) -> float:
        """Area de tubo desnudo entre aletas [m2]."""
        return (math.pi * self.d_o * self.L_tube
                * (1.0 - self.fin_thickness / self.fin_pitch))

    @property
    def A_o(self) -> float:
        """Area externa total de intercambio [m2]."""
        return self.A_fin + self.A_tube_bare

    @property
    def A_i(self) -> float:
        """Area interna (lado refrigerante) [m2]."""
        return math.pi * self.d_i * self.L_tube

    @property
    def area_ratio(self) -> float:
        """Relacion entre area externa e interna."""
        return self.A_o / self.A_i

    @property
    def V_internal(self) -> float:
        """Volumen interno [m3]. Es el que fija el inventario del ap. 9.9."""
        return math.pi / 4.0 * self.d_i ** 2 * self.L_tube

    @property
    def A_flow_ref(self) -> float:
        """Seccion de paso de refrigerante [m2], repartida entre circuitos."""
        return self.n_circuits * math.pi / 4.0 * self.d_i ** 2

    @property
    def A_frontal(self) -> float:
        return self.n_tubes_row * self.S_t * self.L

    @property
    def sigma(self) -> float:
        """Fraccion de area libre de paso del aire (ap. 9.7.3)."""
        return ((self.S_t - self.d_o) / self.S_t
                * (1.0 - self.fin_thickness / self.fin_pitch))

    # ---------------- Aleta anular equivalente (ap. 9.7.4) ----------------
    @property
    def r_collar(self) -> float:
        return self.d_c / 2.0

    @property
    def r_equivalent(self) -> float:
        """Radio de aleta anular equivalente por el metodo de Schmidt.

            r_eq/r = 1.27 psi (beta - 0.3)^0.5
            psi = X_M/r ,  beta = X_L/X_M

        con X_M = S_t/2 y X_L = 0.5 sqrt((S_t/2)^2 + S_l^2) en tresbolillo.

        El ap. 9.7.4 declara una discrepancia del 11 % en la conductancia
        global atribuible precisamente a este metodo, y propone resolverla en el
        cap. 10 contrastandolo con un calculo bidimensional de la aleta. Por eso
        el metodo se registra como correlacion intercambiable y no se codifica
        aqui de forma unica: ver `correlations.fin`.
        """
        X_M = self.S_t / 2.0
        X_L = 0.5 * math.sqrt(X_M ** 2 + self.S_l ** 2)
        r = self.r_collar
        psi, beta = X_M / r, X_L / X_M
        return r * 1.27 * psi * math.sqrt(beta - 0.3)

    @property
    def fin_height(self) -> float:
        """Altura de aleta efectiva [m]."""
        return self.r_equivalent - self.r_collar

    @property
    def fin_area_fraction(self) -> float:
        """A_f/A_t, el peso de la aleta en la efectividad superficial."""
        return self.A_fin / self.A_o

    # ---------------- Verificacion (ap. 9.7.1, §9.7.1) ----------------
    def verification_report(self, declared: dict) -> dict:
        """Contrasta la reconstruccion con las magnitudes declaradas en ficha.

        `declared` admite las claves `area_intercambio_m2`, `volumen_interno_m3`
        y `velocidad_masica_kg_m2s` (esta ultima junto a `caudal_kg_h`).
        Devuelve la desviacion relativa de cada una.
        """
        out = {}
        if "area_intercambio_m2" in declared:
            ref = declared["area_intercambio_m2"]
            out["area"] = {"reconstruido": self.A_o, "declarado": ref,
                           "desviacion": (self.A_o - ref) / ref}
        if "volumen_interno_m3" in declared:
            ref = declared["volumen_interno_m3"]
            out["volumen"] = {"reconstruido": self.V_internal, "declarado": ref,
                              "desviacion": (self.V_internal - ref) / ref}
        if "velocidad_masica_kg_m2s" in declared and "caudal_kg_h" in declared:
            G = declared["caudal_kg_h"] / 3600.0 / self.A_flow_ref
            ref = declared["velocidad_masica_kg_m2s"]
            out["velocidad_masica"] = {"reconstruido": G, "declarado": ref,
                                       "desviacion": (G - ref) / ref}
        return out

    def mass_flux(self, m_dot: float) -> float:
        """Velocidad masica de refrigerante [kg/(m2 s)], repartida entre
        circuitos. Con 41 kg/h y 2 circuitos de 12.3 mm resulta 48, valor bajo
        que sitúa la condensacion en la frontera anular/estratificado y
        condiciona la correlacion aplicable (ap. 9.7.1)."""
        return m_dot / self.A_flow_ref
