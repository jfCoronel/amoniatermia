"""Fraccion de huecos. Apartado 9.9, ecuaciones 9-32 y 9-33.

REQUISITO METODOLOGICO (apartado 9.9): la dispersion entre correlaciones
puede alcanzar un factor superior a dos en la masa predicha. El modelo NO
reporta un valor unico de carga, sino el RANGO obtenido con las cuatro
formulaciones aqui implementadas, y la hipotesis H4 se contrasta frente al
valor mas desfavorable de dicho rango.

Presentar un unico valor de carga seria indefendible ante el tribunal.

FAMILIAS DE LA TABLA 9.21
--------------------------
El apartado 9.9 nombra cuatro familias y la tabla 9.21 da su valor de
referencia para la bateria de aire condensando a 45 C con el titulo recorriendo
de 1 a 0 sobre 3.8 L. Contrastadas las implementaciones de este modulo con
promedio UNIFORME EN TITULO:

    familia (tabla 9.21)  nombre registrado      alpha calc.  alpha tabla
    homogeneo              homogeneous                  0.930        0.930
    deslizamiento          zivi                         0.844        0.844
    Lockhart-Martinelli    lockhart_martinelli          0.880        0.878
    flujo de deriva        rouhani_axelsson             0.824        0.824*

    (*) valor corregido; la tabla daba 0.865, vease la nota 2.

Dos hallazgos que deben trasladarse al capitulo:

1. El promedio de la tabla 9.21 es uniforme en titulo, no ponderado por
   longitud. No es indiferente y conviene declararlo.

2. La fila de flujo de deriva de la tabla 9.21 estaba MAL CALCULADA. Resuelto
   por el autor el 16 de septiembre de 2026: esa fila no se obtuvo con
   Rouhani-Axelsson sino con la correlacion de Smith (1969) con K = 0.4, que es
   un modelo de flujo separado con arrastre y no depende del flujo masico. El
   texto del apartado 9.9 describe la cuarta formulacion como la que
   «incorpora la distribucion radial de fases y el efecto del flujo masico»,
   descripcion que corresponde inequivocamente a Rouhani-Axelsson; el numero
   tabulado no. La tabla 9.21 se corrige a 0.824 / 112.1 kg/m3 / 426 g.

   `smith` queda registrada, porque es el modelo que produjo el valor anterior
   y porque es estructuralmente distinta de las demas.

CONSECUENCIA SOBRE H4
---------------------
La correccion empeora el contraste de forma apreciable. La banda pasa de
200-382 g a 200-426 g y la dispersion de factor 1.9 a 2.1 (tabla 9.21, con el
serpentin bifasico en sus 3.8 L). Sobre el presupuesto de 476 g que fija RS-5
con los 9.52 kW del equilibrio de M-2 (§9.9), eso seria entre el 42 % y el
89 %. Integrada por segmentos la carga de la bateria es menor, y lo que decide
no es la correlacion sino el anegado: con subenfriamiento nulo la banda es de
177-327 g y con 9.5 K ya supera el presupuesto (tabla 9.22).

Y un matiz que refuerza el argumento en lugar de debilitarlo: Rouhani-Axelsson
es la UNICA de las cuatro que depende del flujo masico, y a G = 48 kg/(m2 s)
predice mucha mas retencion de liquido. A G = 200 converge con Smith (338.7 g
frente a 339). Ese flujo masico es bajo precisamente porque el elevado calor
latente del amoniaco reduce el caudal circulante. Es decir: la correlacion
fisicamente mas apropiada para este caso es la que mas carga predice, y lo es
por la misma razon por la que el amoniaco tiene el problema de carga.
`test_referencia.py` verifica esta dependencia con G.
"""
from __future__ import annotations

import math

from . import register, Validity

_EPS = 1e-9


def _clip_x(x):
    return min(max(x, _EPS), 1.0 - _EPS)


@register(
    "voidfraction", "homogeneous",
    reference="Modelo homogeneo, ec. 9-33. Sin parametros (antigua tabla 10.7).",
    validity=Validity(
        ranges={},
        notes="No tiene base experimental: es un limite teorico (S = 1), no "
              "un ajuste. Proporciona sistematicamente la cota superior de "
              "fraccion de huecos y por tanto la INFERIOR de masa contenida."))
def homogeneous(x, rho_l, rho_v, **kw):
    """Modelo homogeneo, ecuacion 9-33. Supone igualdad de velocidades entre
    fases (S = 1). Proporciona SISTEMATICAMENTE la estimacion mas alta de
    fraccion de huecos y, por tanto, la mas BAJA de masa contenida.
    """
    x = _clip_x(x)
    return 1.0 / (1.0 + ((1.0 - x) / x) * (rho_v / rho_l))


@register(
    "voidfraction", "zivi",
    reference="Zivi, S.M. (1964). J. Heat Transfer 86(2), 247-251. Modelo de "
              "deslizamiento por minima produccion de entropia, "
              "S = (rho_l/rho_v)^(1/3). Ec. 9-33.",
    validity=Validity(
        ranges={},
        notes="Limite teorico, no ajuste experimental. Es la familia "
              "«deslizamiento» de la tabla 9.21 y reproduce su valor (0.844)."))
def zivi(x, rho_l, rho_v, **kw):
    """Modelo de deslizamiento de Zivi (minima produccion de entropia),
    ecuacion 9-33 con S = (rho_l/rho_v)^(1/3).
    """
    x = _clip_x(x)
    S = (rho_l / rho_v) ** (1.0 / 3.0)
    return 1.0 / (1.0 + ((1.0 - x) / x) * (rho_v / rho_l) * S)


@register(
    "voidfraction", "lockhart_martinelli",
    reference="Basado en el parametro de Martinelli turbulento-turbulento; "
              "forma alpha = (1 + 0.28 Xtt^0.71)^-1. Lockhart, R.W. y "
              "Martinelli, R.C. (1949). Chem. Eng. Prog. 45, 39-48.",
    validity=Validity(
        ranges={},
        notes="Las constantes 0.28 y 0.71 deben citarse de la fuente primaria "
              "(docs/historico/PENDIENTES.md). Reproduce la tabla 9.21 (0.880 frente "
              "a 0.878)."))
def lockhart_martinelli(x, rho_l, rho_v, mu_l=None, mu_v=None, **kw):
    """Basado en el parametro de Martinelli turbulento-turbulento.

        alpha = (1 + 0.28 X_tt^0.71)^-1
    """
    x = _clip_x(x)
    if mu_l is None or mu_v is None:
        raise ValueError("lockhart_martinelli requiere mu_l y mu_v")
    X_tt = (((1.0 - x) / x) ** 0.9
            * (rho_v / rho_l) ** 0.5
            * (mu_l / mu_v) ** 0.1)
    return 1.0 / (1.0 + 0.28 * X_tt ** 0.71)


@register(
    "voidfraction", "rouhani_axelsson",
    reference="Rouhani, S.Z. y Axelsson, E. (1970). Int. J. Heat Mass "
              "Transfer 13, 383-393. Forma modificada, C0 = 1 + 0.12(1-x).",
    validity=Validity(
        ranges={},
        notes="Es la familia «flujo de deriva» del apartado 9.9 y la unica "
              "de las cuatro que depende del flujo masico. Da 0.824 a "
              "G = 48 kg/(m2 s), por debajo de la de deslizamiento: la tabla "
              "9.21 daba 0.865 porque esa fila se calculo en realidad con "
              "Smith (1969), no con esta correlacion (nota 2 de la cabecera). "
              "Se emplea la forma C0 = 1 + 0.12(1-x); la variante "
              "C0 = 1 + 0.2(1-x) predice todavia mas carga (0.800, 477 g)."))
def rouhani_axelsson(x, rho_l, rho_v, G=None, sigma=None, g=9.80665, **kw):
    """Modelo de flujo de deriva de Rouhani-Axelsson (forma modificada).

    Incorpora la distribucion radial de fases y el efecto del flujo masico,
    por lo que a diferencia de las anteriores SI depende de G.
    """
    x = _clip_x(x)
    if G is None or sigma is None:
        raise ValueError("rouhani_axelsson requiere G y sigma")
    G = max(abs(G), 1e-6)
    C0 = 1.0 + 0.12 * (1.0 - x)
    term_hom = x / rho_v + (1.0 - x) / rho_l
    drift = (1.18 * (1.0 - x)
             * (g * sigma * (rho_l - rho_v)) ** 0.25
             / (G * rho_l ** 0.5))
    return (x / rho_v) / (C0 * term_hom + drift)


@register(
    "voidfraction", "smith",
    reference="Smith, S.L. (1969). Proc. Inst. Mech. Eng. 184(1), 647-664. "
              "Modelo de flujo separado con arrastre de liquido en el nucleo "
              "de vapor, fraccion de arrastre K.",
    validity=Validity(
        ranges={"K": (0.0, 1.0)},
        source="K es la fraccion masica de liquido arrastrada; K = 0.4 es el "
               "valor recomendado por el autor y el empleado en la tabla 9.21 "
               "original.",
        notes="Es la correlacion con la que se calculo en realidad la fila de "
              "«flujo de deriva» de la tabla 9.21 (0.865, 89.2 kg/m3, 339 g), "
              "etiquetada por error como Rouhani-Axelsson. Se registra por eso "
              "y porque es estructuralmente distinta de las otras cuatro, pero "
              "NO pertenece a las familias del apartado 9.9: no depende del "
              "flujo masico y no puede sostener la descripcion que el texto "
              "hace de la cuarta formulacion."))
def smith(x, rho_l, rho_v, K=0.4, **kw):
    """Flujo separado con arrastre, de Smith (1969).

        alpha = [1 + (rho_v/rho_l) r (K + (1-K) sqrt((rho_l/rho_v + K r)
                                                     / (1 + K r)))]^-1
        r = (1-x)/x

    K es la fraccion de liquido arrastrada como gotas en el nucleo de vapor.
    K = 0 recupera el flujo completamente separado; K = 1 el homogeneo.
    """
    x = _clip_x(x)
    r = (1.0 - x) / x
    inner = (rho_l / rho_v + K * r) / (1.0 + K * r)
    S_eff = K + (1.0 - K) * math.sqrt(inner)
    return 1.0 / (1.0 + (rho_v / rho_l) * r * S_eff)


@register(
    "voidfraction", "premoli",
    reference="Premoli, A., Francesco, D. y Prina, A. (1970). Correlacion de "
              "deslizamiento con numeros de Reynolds y Weber.",
    validity=Validity(
        ranges={},
        notes="QUINTA correlacion: NO figura en la tabla 9.21 ni entre las "
              "cuatro familias del apartado 9.9. Se conserva registrada "
              "como alternativa para la sensibilidad del ap. 6.11, pero no "
              "debe formar parte de la banda de carga que reporta el "
              "apartado 9.9 sin declararlo."))
def premoli(x, rho_l, rho_v, G=None, sigma=None, mu_l=None, D_h=None, **kw):
    """Correlacion de deslizamiento de Premoli et al.

        S = 1 + E1 (y/(1+y E2) - y E2)^0.5
        y = beta/(1-beta), beta = fraccion de huecos homogenea
        E1 = 1.578 Re^-0.19 (rho_l/rho_v)^0.22
        E2 = 0.0273 We Re^-0.51 (rho_l/rho_v)^-0.08
    """
    x = _clip_x(x)
    for nm, v in (("G", G), ("sigma", sigma), ("mu_l", mu_l), ("D_h", D_h)):
        if v is None:
            raise ValueError(f"premoli requiere {nm}")
    G = max(abs(G), 1e-6)
    Re = G * D_h / mu_l
    We = G ** 2 * D_h / (sigma * rho_l)
    E1 = 1.578 * Re ** -0.19 * (rho_l / rho_v) ** 0.22
    E2 = 0.0273 * We * Re ** -0.51 * (rho_l / rho_v) ** -0.08

    beta = homogeneous(x, rho_l, rho_v)
    y = beta / max(1.0 - beta, _EPS)
    # restriccion conocida de la correlacion: el radicando debe ser positivo
    if E2 > _EPS and y > 1.0 / E2:
        y = 1.0 / E2
    rad = y / (1.0 + y * E2) - y * E2
    S = 1.0 + E1 * math.sqrt(max(rad, 0.0))
    return 1.0 / (1.0 + ((1.0 - x) / x) * (rho_v / rho_l) * S)


@register(
    "voidfraction", "zuber_findlay",
    reference="Zuber, N. y Findlay, J.A. (1965). J. Heat Transfer 87(4), "
              "453-468. Marco general de flujo de deriva con parametro de "
              "distribucion C0 y velocidad de deriva explicitos.",
    validity=Validity(
        ranges={},
        notes="C0 es parametro de entrada, no una eleccion cerrada. Permite "
              "recorrer las variantes de Rouhani-Axelsson (C0 = 1 + 0.12(1-x) "
              "y C0 = 1 + 0.2(1-x)) en la sensibilidad del ap. 6.11 sin "
              "duplicar codigo. AVISO: con C0 = 1 da 0.863, cerca del 0.865 "
              "que figuraba en la tabla 9.21, pero es una COINCIDENCIA "
              "numerica con el valor de Smith y no una reproduccion del "
              "flujo de deriva: C0 = 1 suprime la distribucion radial de fases "
              "que el ap. 9.9 dice que este modelo incorpora."))
def zuber_findlay(x, rho_l, rho_v, G=None, sigma=None, C0=1.0, g=9.80665, **kw):
    """Flujo de deriva general, con C0 como parametro explicito.

        alpha = (x/rho_v) / [ C0 (x/rho_v + (1-x)/rho_l) + v_gj / G ]

    con la velocidad de deriva en la forma de Rouhani-Axelsson:

        v_gj / G = 1.18 (1-x) [g sigma (rho_l - rho_v)]^0.25 / (G rho_l^0.5)

    C0 = 1 suprime la distribucion radial de fases y deja solo el termino de
    deriva. C0 = 1 + 0.12(1-x) recupera `rouhani_axelsson`.
    """
    x = _clip_x(x)
    if G is None or sigma is None:
        raise ValueError("zuber_findlay requiere G y sigma")
    G = max(abs(G), 1e-6)
    term_hom = x / rho_v + (1.0 - x) / rho_l
    drift = (1.18 * (1.0 - x)
             * (g * sigma * (rho_l - rho_v)) ** 0.25
             / (G * rho_l ** 0.5))
    return (x / rho_v) / (C0 * term_hom + drift)


#: Las cuatro familias que nombra el apartado 9.9 y cuyos valores de
#: referencia da la tabla 9.21, en el orden de la tabla. Es el conjunto que el
#: apartado 9.9 exige reportar como banda. Premoli y zuber_findlay quedan
#: fuera a proposito: son alternativas para la sensibilidad del ap. 6.11, no
#: miembros de la banda.
CORRELACIONES_HUECOS = ("homogeneous", "zivi", "lockhart_martinelli", "rouhani_axelsson")


def mean_density(alpha, rho_l, rho_v):
    """Densidad media bifasica.

    NOTA SOBRE LA EC. 9-32. La revision previa del capitulo la escribia como
    `rho = x rho_v + (1-x) rho_l`, con el TITULO, y sus ecuaciones 9-44 y
    9-45 llamaban `x_hom` y `x_des` a lo que son alpha_hom y alpha_des. Era un
    error de simbolo: la ponderacion volumetrica corresponde a la FRACCION DE
    HUECOS. La v30 lo corrige (ec. 9-32 y 9-33, con alpha), y el codigo
    implementa esa forma desde el principio.
    """
    return alpha * rho_v + (1.0 - alpha) * rho_l


def charge_range(x, sat, G, D_h, names=CORRELACIONES_HUECOS):
    """Devuelve la densidad media segun cada correlacion disponible.

    Es la funcion que emplea el inventario del apartado 9.9 para reportar el
    RANGO exigido, en lugar de un valor unico. `names` es configurable: fijarlo
    en codigo contradiria el requisito de intercambiabilidad por nombre del
    apartado 9.12.3.
    """
    from . import get
    out = {}
    kwargs = dict(rho_l=sat["rho_l"], rho_v=sat["rho_v"], G=G,
                  sigma=sat["sigma"], mu_l=sat["mu_l"], mu_v=sat["mu_v"],
                  D_h=D_h)
    for nm in names:
        fn = get("voidfraction", nm)
        a = fn(x, **kwargs)
        out[nm] = {"alpha": a,
                   "rho_mean": mean_density(a, sat["rho_l"], sat["rho_v"])}
    return out
