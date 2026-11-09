"""Cambio de fase en el INTERIOR DE TUBO circular. Apartado 9.7.5.

POR QUE ESTE MODULO EXISTE APARTE
---------------------------------
El ap. 9.7.5 abre declarando que «las correlaciones adoptadas en los apartados
9.6.3 y 9.6.4 son especificas de geometria de placas corrugadas y no son
aplicables aqui». Las familias `tube_boiling` y `tube_condensation` recogen esa
declaracion en la estructura del registro: un intercambiador de placas no puede
elegir por nombre ninguna de estas funciones, porque no estan en su familia. Si
pudiera, la banda de incertidumbre del ap. 6.11 dejaria de significar nada —
recorreria formulaciones que no describen la geometria del componente.

LO QUE EL CAPITULO DA Y LO QUE NO
---------------------------------
Las ecuaciones 9-24 a 9-27 estan escritas en el capitulo, pero tres piezas que
necesitan NO lo estan, y se toman de la fuente primaria:

- El numero de Froude modificado Fr_so, del que la ec. 9-24 solo declara el
  umbral (20). La definicion es de Soliman (1982).
- El angulo `theta_l` de la generatriz mojada y el `Nu_fz` de conveccion forzada
  en el remanso de liquido, ambos de Dobson y Chato (1998).

Cada una se declara en la referencia de su correlacion. Rellenarlas con formas
plausibles sin citar la fuente seria exactamente lo que el ap. 9.6.4 pide
evitar.

BASE EXPERIMENTAL
-----------------
Ninguna de las dos correlaciones tiene amoniaco en su base: Dobson y Chato se
desarrollo sobre R-12, R-22, R-134a y mezclas, y Gungor-Winterton sobre agua y
halogenados. El ap. 9.7.5 lo declara y cifra la atenuacion: con el lado de
refrigerante pesando el 23 % de la resistencia total, un error del 30 % en el
coeficiente se traduce en menos del 8 % en la conductancia del componente.
"""
from __future__ import annotations

import math

from . import Validity, register, get
from .boiling import cooper_pool_boiling, martinelli_tt, boiling_number

G_ACC = 9.80665


# ---------------------------------------------------------------------------
# Grupos adimensionales de la ecuacion 9-25
# ---------------------------------------------------------------------------
def galileo(rho_l: float, rho_v: float, d_i: float, mu_l: float) -> float:
    """Numero de Galileo, ec. 9-25.

        Ga = g rho_l (rho_l - rho_v) d_i^3 / mu_l^2
    """
    return G_ACC * rho_l * (rho_l - rho_v) * d_i ** 3 / mu_l ** 2


def jakob(cp_l: float, T_sat: float, T_wall: float, h_lv: float,
          dT_min: float = 0.05) -> float:
    """Numero de Jakob del liquido, ec. 9-25.

        Ja_l = cp_l (T_sat - T_w) / h_lv

    `dT_min` acota el salto pared-saturacion por abajo. La rama estratificada de
    la ec. 9-24 lleva Ja en el denominador de (Ga Pr / Ja)^(1/4) y diverge
    cuando la pared toca la saturacion, situacion que no ocurre en operacion
    —sin salto no hay condensacion— pero si en la primera iteracion del lazo
    interno, antes de que haya un flujo de calor con el que estimar la pared.
    La cota es numerica y se declara como tal: 0.05 K esta dos ordenes por
    debajo de los saltos de esta bateria (del orden de 5 K).
    """
    return cp_l * max(abs(T_sat - T_wall), dT_min) / h_lv


def liquid_reynolds(G: float, x: float, d_i: float, mu_l: float) -> float:
    """Reynolds de la fraccion liquida circulando sola, ec. 9-24 y 9-27.

        Re_l = G (1 - x) d_i / mu_l
    """
    return G * (1.0 - min(max(x, 0.0), 1.0)) * d_i / mu_l


def vapor_only_reynolds(G: float, d_i: float, mu_v: float) -> float:
    """Reynolds del caudal TOTAL con propiedades de vapor, ec. 9-24."""
    return G * d_i / mu_v


def soliman_froude(x: float, G: float, sat: dict, d_i: float) -> float:
    """Numero de Froude modificado de Soliman, criterio de la ec. 9-24.

    El capitulo declara el umbral —anular por encima de 20, estratificado por
    debajo— pero no la definicion. Es la de Soliman (1982):

        Fr_so = 0.025 Re_l^1.59 [(1 + 1.09 X_tt^0.039)/X_tt]^1.5 / Ga^0.5
                                                        para Re_l <= 1250
        Fr_so = 1.26  Re_l^1.04 [(1 + 1.09 X_tt^0.039)/X_tt]^1.5 / Ga^0.5
                                                        para Re_l >  1250

    Mide la relacion entre la fuerza de cizalladura del vapor, que mantiene la
    pelicula repartida por el perimetro, y la gravedad, que la acumula en la
    generatriz inferior. Por eso el umbral no depende del titulo por si mismo
    sino de la combinacion de titulo y velocidad masica.
    """
    Re_l = liquid_reynolds(G, x, d_i, sat["mu_l"])
    X_tt = martinelli_tt(x, sat["rho_l"], sat["rho_v"], sat["mu_l"], sat["mu_v"])
    Ga = galileo(sat["rho_l"], sat["rho_v"], d_i, sat["mu_l"])
    grupo = ((1.0 + 1.09 * X_tt ** 0.039) / X_tt) ** 1.5 / math.sqrt(Ga)
    if Re_l <= 1250.0:
        return 0.025 * max(Re_l, 1e-9) ** 1.59 * grupo
    return 1.26 * Re_l ** 1.04 * grupo


def stratified_angle_fraction(alpha: float) -> float:
    """Fraccion de perimetro NO ocupada por el remanso, (1 - theta_l/pi).

        1 - theta_l/pi = arccos(2 alpha - 1) / pi

    Dobson y Chato la obtienen suponiendo la interfaz plana y deduciendo el
    angulo de la fraccion de huecos. El capitulo usa theta_l en la ec. 9-24 sin
    declarar como se calcula.
    """
    return math.acos(min(max(2.0 * alpha - 1.0, -1.0), 1.0)) / math.pi


def nusselt_forced_pool(Re_l: float, Pr_l: float, X_tt: float,
                        Fr_l: float) -> float:
    """Nu_fz: conveccion forzada en el remanso de liquido (Dobson y Chato).

        Nu_fz = 0.0195 Re_l^0.8 Pr_l^0.4 sqrt(1.376 + c1 / X_tt^c2)

        0 < Fr_l <= 0.7 : c1 = 4.172 + 5.48 Fr_l - 1.564 Fr_l^2
                          c2 = 1.773 - 0.169 Fr_l
        Fr_l  >  0.7    : c1 = 7.242 ,  c2 = 1.655

    El capitulo escribe `Nu_fz` en la ec. 9-24 sin desarrollarla. Esta es la
    forma de la fuente primaria, con `Fr_l = G^2 / (rho_l^2 g d_i)` el Froude del
    liquido.
    """
    if Fr_l <= 0.7:
        c1 = 4.172 + 5.48 * Fr_l - 1.564 * Fr_l ** 2
        c2 = 1.773 - 0.169 * Fr_l
    else:
        c1, c2 = 7.242, 1.655
    phi_l = math.sqrt(1.376 + c1 / X_tt ** c2)
    return 0.0195 * max(Re_l, 1e-9) ** 0.8 * Pr_l ** 0.4 * phi_l


# ---------------------------------------------------------------------------
# Condensacion: ecuacion 9-24
# ---------------------------------------------------------------------------
_DOBSON_CHATO_VALIDITY = Validity(
    ranges={"G": (25.0, 800.0), "d_i": (3.14e-3, 7.04e-3), "x": (0.1, 0.9)},
    fluids=("R12", "R22", "R134a", "R32/R125"),
    source="Dobson, M.K. y Chato, J.C. (1998). Condensation in smooth "
           "horizontal tubes. J. Heat Transfer 120(1), 193-213. Base: 25 a "
           "800 kg/(m2 s) en tubos de 3.14 a 7.04 mm.",
    notes="SIN AMONIACO en la base, declarado en el ap. 9.7.5. Y el diametro "
          "de esta bateria, 12.3 mm, esta POR ENCIMA del mayor de la base: "
          "12.3 frente a 7.04 mm. Las dos excursiones se marcan. La velocidad "
          "masica de trabajo, 48 kg/(m2 s), si cae dentro del rango, cerca de "
          "su extremo inferior, que es precisamente donde vive la transicion "
          "anular / estratificado que el ap. 9.7.5 quiere resolver.")


@register(
    "tube_condensation", "dobson_chato",
    reference="Dobson, M.K. y Chato, J.C. (1998). J. Heat Transfer 120(1), "
              "193-213, con el criterio de transicion de Soliman, H.M. (1982), "
              "Can. J. Chem. Eng. 60, 475-481. Ecuaciones 9-24 y 9-25.",
    validity=_DOBSON_CHATO_VALIDITY)
def dobson_chato(x, G, sat, geom, T_wall=None, alpha=None, Fr_so_c=20.0, **kw):
    """Condensacion en tubo horizontal con criterio anular / estratificado.

    Devuelve solo el coeficiente; `dobson_chato_regime` devuelve ademas el
    regimen, que es lo que el diagnostico del ap. 9.7.5 necesita reportar.
    """
    return dobson_chato_regime(x, G, sat, geom, T_wall, alpha, Fr_so_c)[0]


def dobson_chato_regime(x, G, sat, geom, T_wall=None, alpha=None,
                        Fr_so_c=20.0) -> tuple:
    """Ecuacion 9-24 completa. Devuelve (h, regimen, Fr_so).

    Rama anular (Fr_so > 20), dominada por la cizalladura del vapor:

        h = (k_l/d_i) 0.023 Re_l^0.8 Pr_l^0.4 (1 + 2.22 / X_tt^0.89)

    Rama estratificada (Fr_so < 20), con el liquido acumulado abajo:

        h = (k_l/d_i) [ 0.23 Re_vo^0.12 / (1 + 1.11 X_tt^0.58)
                        (Ga Pr_l / Ja_l)^(1/4)
                        + (1 - theta_l/pi) Nu_fz ]

    El primer sumando es la pelicula que condensa en la parte superior del tubo;
    el segundo, la conveccion forzada en el remanso inferior, que transfiere
    mucho menos. De ahi que el ap. 9.7.5 advierta que tratar todo el serpentin
    como anular sobreestimaria el coeficiente.

    `T_wall` entra por Ja_l y hace que el coeficiente dependa del propio flujo de
    calor: es el acoplamiento implicito que obliga al lazo interno por celda del
    ap. 9.7.2. Sin `T_wall` se usa la cota `dT_min` de `jakob`.
    """
    d_i = geom.d_i
    k_l, Pr_l = sat["k_l"], sat["Pr_l"]
    Re_l = liquid_reynolds(G, x, d_i, sat["mu_l"])
    X_tt = martinelli_tt(x, sat["rho_l"], sat["rho_v"], sat["mu_l"], sat["mu_v"])
    Fr_so = soliman_froude(x, G, sat, d_i)

    if Fr_so > Fr_so_c:                                   # anular
        h = (k_l / d_i) * 0.023 * Re_l ** 0.8 * Pr_l ** 0.4 \
            * (1.0 + 2.22 / X_tt ** 0.89)
        return h, "anular", Fr_so

    Ga = galileo(sat["rho_l"], sat["rho_v"], d_i, sat["mu_l"])
    T_w = sat["Tsat"] if T_wall is None else T_wall
    Ja = jakob(sat["cp_l"], sat["Tsat"], T_w, sat["h_lv"])
    Re_vo = vapor_only_reynolds(G, d_i, sat["mu_v"])
    if alpha is None:
        alpha = get("voidfraction", "zivi")(x, sat["rho_l"], sat["rho_v"])
    Fr_l = G ** 2 / (sat["rho_l"] ** 2 * G_ACC * d_i)

    pelicula = (0.23 * Re_vo ** 0.12 / (1.0 + 1.11 * X_tt ** 0.58)
                * (Ga * Pr_l / Ja) ** 0.25)
    remanso = stratified_angle_fraction(alpha) \
        * nusselt_forced_pool(Re_l, Pr_l, X_tt, Fr_l)
    return (k_l / d_i) * (pelicula + remanso), "estratificado", Fr_so


@register(
    "tube_condensation", "ficha_cbn21_agregado",
    reference="Coeficiente agregado declarado por la ficha de seleccion de la "
              "bateria Frimetal CBN-21 ESPECIAL: 5200 W/(m2 K) en condensacion "
              "a 45 C (§9.7.5, tabla 9.18).",
    validity=Validity(
        ranges={"T_sat": (316.0, 320.0)},
        fluids=("Ammonia",),
        source="Un unico punto de ficha: NH3 condensando a 45 C, 41 kg/h, "
               "G = 48 kg/(m2 s), desrecalentamiento y subenfriamiento nulos.",
        notes="NO es una correlacion: es el valor agregado de CONTRASTE del "
              "ap. 9.7.5, constante con el titulo. Es el unico dato de "
              "condensacion en tubo del que dispone el modelo, y su papel es "
              "verificar el promedio que `dobson_chato` predice, no sustituirlo: "
              "al ser constante NO puede reproducir el diagnostico de regimen "
              "que exige CLAUDE.md, y todo resultado apoyado en ella debe "
              "declararlo."))
def ficha_cbn21_agregado(x, G, sat, geom, h=5200.0, **kw):
    """Coeficiente agregado de ficha, constante con el titulo."""
    return h


# ---------------------------------------------------------------------------
# Ebullicion: ecuaciones 9-26 y 9-27
# ---------------------------------------------------------------------------
_GW_VALIDITY = Validity(
    ranges={"G": (12.4, 61518.0), "p_red": (0.0023, 0.895), "x": (0.0, 1.0),
            "d_i": (2.95e-3, 32.0e-3)},
    fluids=("Water", "R11", "R12", "R22", "R113", "R114", "Ethylene glycol"),
    source="Gungor, K.E. y Winterton, R.H.S. (1986). A general correlation for "
           "flow boiling in tubes and annuli. Int. J. Heat Mass Transfer "
           "29(3), 351-358. Banco de 4300 puntos.",
    notes="SIN AMONIACO en la base, declarado en el ap. 9.7.5. El diametro y "
          "la velocidad masica de esta bateria si caen dentro del rango, este "
          "ultimo muy cerca del extremo inferior.")


@register(
    "tube_boiling", "gungor_winterton",
    reference="Gungor, K.E. y Winterton, R.H.S. (1986). Int. J. Heat Mass "
              "Transfer 29(3), 351-358, con Cooper (1984) para la contribucion "
              "nucleada. Ecuaciones 9-26 y 9-27, en su forma LITERAL.",
    validity=_GW_VALIDITY)
def gungor_winterton(x, G, q_flux, sat, fluid_M, geom, Rp_um=1.0, **kw):
    """Ebullicion en tubo, ecuaciones 9-26 y 9-27, tal como el capitulo las
    escribe.

        h_tp = S h_nb + F h_l
        h_l  = 0.023 (k_l/d_i) Re_l^0.8 Pr_l^0.4 ,  Re_l = G(1-x) d_i / mu_l
        F    = 1 + 24000 Bo^1.16 + 1.37 (1/X_tt)^0.86
        S    = [1 + 1.15e-6 F^2 Re_l^1.17]^-1 ,     Bo = q''/(G h_lv)

    `h_nb` es Cooper en funcion de la presion reducida, que es lo que el
    ap. 9.7.5 declara («coherente con la adoptada en el apartado 9.6.3»).

    OMISION DECLARADA. La formulacion original incorpora ademas una correccion
    de estratificacion para tubo horizontal cuando el Froude del liquido baja de
    0.05 —multiplica F por Fr_l^(0.1-2Fr_l) y S por sqrt(Fr_l)—, que el capitulo
    no recoge. No es indiferente aqui: con G = 48 kg/(m2 s) esta bateria opera
    en Fr_l = 0.053, justo sobre el umbral. La variante con la correccion esta
    registrada aparte como `gungor_winterton_horizontal` para que la banda del
    ap. 6.11 pueda medir la diferencia en lugar de suponerla.
    """
    return _gungor_winterton(x, G, q_flux, sat, fluid_M, geom, Rp_um,
                             horizontal=False)


@register(
    "tube_boiling", "gungor_winterton_horizontal",
    reference="Gungor y Winterton (1986), con la correccion de estratificacion "
              "para tubo horizontal que la ec. 9-27 del capitulo omite.",
    validity=_GW_VALIDITY)
def gungor_winterton_horizontal(x, G, q_flux, sat, fluid_M, geom, Rp_um=1.0,
                                **kw):
    """Variante CON la correccion de tubo horizontal de la fuente original.

    Para Fr_l < 0.05, con Fr_l = G^2/(rho_l^2 g d_i):

        F <- F Fr_l^(0.1 - 2 Fr_l) ,   S <- S sqrt(Fr_l)

    Representa el mismo fenomeno que la rama estratificada de la ec. 9-24 en
    condensacion —el liquido acumulado en la generatriz inferior deja la parte
    superior mal mojada— y su ausencia de la ec. 9-27 es una asimetria del
    capitulo: trata la estratificacion al condensar y la ignora al evaporar.
    """
    return _gungor_winterton(x, G, q_flux, sat, fluid_M, geom, Rp_um,
                             horizontal=True)


@register(
    "tube_boiling", "cooper_solo",
    reference="Cooper, M.G. (1984). Ebullicion NUCLEADA EN PISCINA en funcion "
              "de la presion reducida. Ec. 9-14, sin la superposicion de la "
              "ec. 9-26.",
    validity=Validity(
        ranges={"p_red": (0.001, 0.9)},
        fluids=(),
        source="Cooper, M.G. (1984). Adv. Heat Transfer 16, 157-239.",
        notes="Es la contribucion NUCLEADA SOLA, sin termino convectivo y sin "
              "factor de supresion. Se registra porque es la formulacion con "
              "la que el ap. 9.7.5 obtuvo de hecho las cifras que publica "
              "—3100 W/(m2 K) en la condicion nominal y 1900 en el perfil "
              "frio—, que NO son las que la ec. 9-26 completa produce. Sirve "
              "por tanto de contraste con el capitulo, no como formulacion "
              "defendible: omitir el termino convectivo no esta justificado "
              "por ningun argumento del apartado."))
def cooper_solo(x, G, q_flux, sat, fluid_M, geom, Rp_um=1.0, **kw):
    """Cooper sin superposicion. Reproduce las cifras publicadas en el
    ap. 9.7.5; ver la nota de validez."""
    return cooper_pool_boiling(sat["p_red"], fluid_M, abs(q_flux), Rp_um)


def _gungor_winterton(x, G, q_flux, sat, fluid_M, geom, Rp_um, horizontal):
    d_i = geom.d_i
    Re_l = max(liquid_reynolds(G, x, d_i, sat["mu_l"]), 1.0)
    X_tt = martinelli_tt(x, sat["rho_l"], sat["rho_v"], sat["mu_l"], sat["mu_v"])
    Bo = boiling_number(abs(q_flux), G, sat["h_lv"])

    h_l = 0.023 * (sat["k_l"] / d_i) * Re_l ** 0.8 * sat["Pr_l"] ** 0.4
    F = 1.0 + 24000.0 * Bo ** 1.16 + 1.37 * (1.0 / X_tt) ** 0.86
    S = 1.0 / (1.0 + 1.15e-6 * F ** 2 * Re_l ** 1.17)

    if horizontal:
        Fr_l = G ** 2 / (sat["rho_l"] ** 2 * G_ACC * d_i)
        if Fr_l < 0.05:
            F *= Fr_l ** (0.1 - 2.0 * Fr_l)
            S *= math.sqrt(Fr_l)

    h_nb = cooper_pool_boiling(sat["p_red"], fluid_M, abs(q_flux), Rp_um)
    return S * h_nb + F * h_l


# El componente pregunta por el regimen a traves de este atributo. Una
# correlacion que no lo exponga —como el agregado de ficha— sigue siendo
# utilizable, pero el diagnostico del ap. 9.7.5 queda marcado como no honrado.
dobson_chato.regime = dobson_chato_regime
