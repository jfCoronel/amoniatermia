"""Perdida de carga. Apartado 9.6.6, ecuacion 9-20."""
from __future__ import annotations

from . import register, Validity


@register(
    "friction", "chevron_generic",
    reference="Factor de friccion generico para geometria corrugada. "
              "PROVISIONAL (antigua tabla 10.7: depende de la geometria de "
              "corrugacion, pendiente de fijar).",
    validity=Validity(
        ranges={},
        notes="Factor de intensificacion por corrugado adoptado sin fuente. "
              "Sustituir por la correlacion de placas corrugadas referenciada "
              "antes de emplear la perdida de carga en resultados."))
def chevron_generic_f(Re, beta_c=None):
    """Factor de friccion generico para geometria corrugada. PROVISIONAL."""
    Re = max(Re, 1.0)
    if Re < 2000.0:
        return 64.0 / Re
    return 0.3164 * Re ** -0.25 * 3.0   # factor de intensificacion por corrugado


@register(
    "friction", "martin_vdi",
    reference="Martin, H. (1996). Chem. Eng. Process. 35, 301-310; VDI Heat "
              "Atlas. Factor de friccion de Fanning para placa corrugada, "
              "funcion del angulo de corrugacion.",
    validity=Validity(
        ranges={},
        notes="Es la MISMA correlacion que `singlephase/martin_vdi` emplea para "
              "la transferencia: la analogia de Martin liga las dos a traves "
              "del angulo de corrugacion. Por eso registrarla aqui no duplica "
              "nada, sino que hace utilizable el unico vinculo que permite "
              "IDENTIFICAR beta a partir de una perdida de carga medida, que es "
              "lo que hace `plate_hx.anchor_from_selection_point`. A "
              "diferencia de `chevron_generic`, no tiene coeficientes libres. "
              "El rango no se declara porque depende del angulo, que es un dato "
              "PENDIENTE (antigua tabla 10.7)."))
def martin_vdi_f(Re, beta_c=None, **kw):
    """Factor de friccion de Fanning de Martin. Envoltorio de registro.

    `beta_c` es obligatorio pese a llevar valor por defecto en la firma: sin
    angulo no hay correlacion de Martin, y aceptar uno implicito seria
    exactamente el tipo de relleno que el ap. 9.6.4 prohibe.
    """
    if beta_c is None:
        raise ValueError(
            "martin_vdi necesita el angulo de corrugacion `beta_c`. Es un dato "
            "PENDIENTE (data/placas_alfanova.yaml); para explorar sin el hay "
            "que pasarlo explicitamente y declararlo.")
    from .singlephase import martin_friction

    return martin_friction(Re, beta_c)


def dp_total(f, L, D_h, G, rho, drho_inv=0.0, dz=0.0, g=9.80665):
    """Ecuacion 9.23: friccional + aceleracion + gravitatoria.

    La contribucion gravitatoria se conserva porque la disposicion vertical de
    los intercambiadores de placas la hace no despreciable en la region
    bifasica del evaporador.
    """
    dp_f = f * (4.0 * L / D_h) * (G ** 2 / (2.0 * rho))
    dp_a = G ** 2 * drho_inv
    dp_g = rho * g * dz
    return dp_f + dp_a + dp_g


# ---------------------------------------------------------------------------
# Multiplicador bifasico (ec. 9-20)
# ---------------------------------------------------------------------------

#: Umbral laminar/turbulento con el que se elige la constante C de Chisholm.
#: Coherente con el que emplea `chevron_generic_f` para cambiar de rama.
RE_TRANSICION = 2000.0

#: Constante C de Chisholm (1967) segun el regimen de cada fase. Los cuatro
#: valores son los que declara la antigua tabla 10.7 como CONOCIDOS: 5 / 10 / 12 / 20.
#: Clave: (liquido_turbulento, vapor_turbulento).
C_CHISHOLM = {
    (True, True): 20.0,    # turbulento-turbulento
    (False, True): 12.0,   # liquido laminar, vapor turbulento
    (True, False): 10.0,   # liquido turbulento, vapor laminar
    (False, False): 5.0,   # laminar-laminar
}


@register(
    "twophase_multiplier", "lockhart_martinelli_chisholm",
    reference="Lockhart y Martinelli (1949); correlacion de C de Chisholm "
              "(1967). Antigua tabla 10.7 declara las cuatro constantes "
              "C = 5/10/12/20 como CONOCIDAS; lo pendiente es el factor de "
              "friccion monofasico, que depende de la geometria de corrugacion.",
    validity=Validity(
        ranges={},
        source="Lockhart, R.W. y Martinelli, R.C. (1949). Chisholm, D. (1967).",
        notes="Base experimental de tubos horizontales con mezclas aire-liquido "
              "a baja presion. Su aplicacion a NH3 en placas corrugadas "
              "verticales es una extrapolacion de geometria Y de fluido, y el "
              "ap. 9.6.4 no fija el factor de friccion monofasico que la "
              "alimenta. Resultado NO soportado mientras siga asi."))
def lockhart_martinelli_chisholm(x, G, sat, D_h, L, f_single, **kw):
    """Perdida de carga friccional bifasica por multiplicador de fases separadas.

    Se evalua la perdida de cada fase circulando SOLA por el conducto y se
    combinan:

        dP_tp = dP_l + C sqrt(dP_l dP_v) + dP_v

    que es algebraicamente identica a dP_tp = phi_l^2 dP_l con el multiplicador
    clasico phi_l^2 = 1 + C/X + 1/X^2 y el parametro X^2 = dP_l/dP_v, pero
    numericamente estable en los dos extremos: con x -> 0 tiende a dP_l y con
    x -> 1 a dP_v, mientras que la forma con phi_l^2 divide por cero en ambos.

    `f_single` es la correlacion de friccion monofasica, que se recibe como
    argumento en lugar de resolverse aqui: asi el multiplicador y el factor de
    friccion se pueden sustituir de forma INDEPENDIENTE en la campana del
    ap. 6.11.

    Devuelve `(dP, info)`, donde `info` lleva el reparto por fases, el parametro
    de Martinelli y la constante C empleada, que es lo que permite reportar el
    regimen en lugar de solo el numero.
    """
    from .singlephase import reynolds

    x = min(max(x, 0.0), 1.0)
    G_l, G_v = G * (1.0 - x), G * x

    Re_l = reynolds(G_l, D_h, sat["mu_l"])
    Re_v = reynolds(G_v, D_h, sat["mu_v"])
    turb_l, turb_v = Re_l > RE_TRANSICION, Re_v > RE_TRANSICION
    C = C_CHISHOLM[(turb_l, turb_v)]

    geo = 4.0 * L / D_h
    dP_l = f_single(Re_l, **kw) * geo * G_l ** 2 / (2.0 * sat["rho_l"])
    dP_v = f_single(Re_v, **kw) * geo * G_v ** 2 / (2.0 * sat["rho_v"])

    dP = dP_l + C * (dP_l * dP_v) ** 0.5 + dP_v
    X = (dP_l / dP_v) ** 0.5 if dP_v > 0.0 else float("inf")
    return dP, {"dP_l": dP_l, "dP_v": dP_v, "C": C, "X": X,
                "Re_l": Re_l, "Re_v": Re_v,
                "regimen_l": "turbulento" if turb_l else "laminar",
                "regimen_v": "turbulento" if turb_v else "laminar",
                "phi_l2": dP / dP_l if dP_l > 0.0 else float("inf")}


@register(
    "twophase_multiplier", "homogeneo",
    reference="Modelo homogeneo: el bifasico se trata como un fluido unico de "
              "propiedades ponderadas por el titulo. Alternativa declarada "
              "para la sensibilidad del cap. 10.",
    validity=Validity(
        ranges={},
        notes="Valido cuando las dos fases viajan a la misma velocidad. En "
              "NH3 la relacion de densidades a 45 C es ~ 50, de modo que el "
              "deslizamiento no es despreciable y este modelo SUBESTIMA la "
              "perdida de carga. Se conserva como cota inferior de la banda."))
def homogeneo(x, G, sat, D_h, L, f_single, **kw):
    """Cota inferior de la banda: una sola fase de propiedades ponderadas."""
    from .singlephase import reynolds

    x = min(max(x, 0.0), 1.0)
    v = (1.0 - x) / sat["rho_l"] + x / sat["rho_v"]       # volumen especifico
    mu = 1.0 / ((1.0 - x) / sat["mu_l"] + x / sat["mu_v"])  # McAdams
    Re = reynolds(G, D_h, mu)
    dP = f_single(Re, **kw) * (4.0 * L / D_h) * G ** 2 * v / 2.0
    return dP, {"Re": Re, "rho_h": 1.0 / v, "mu_h": mu}


@register(
    "friction", "churchill_tubo",
    reference="Churchill, S.W. (1977). Friction-factor equation spans all "
              "fluid-flow regimes. Chem. Eng. 84(24), 91-92. Factor de Fanning "
              "en tubo circular, laminar, transicion y turbulento con rugosidad.",
    validity=Validity(
        ranges={},
        source="Churchill (1977), ajuste al diagrama de Moody.",
        notes="Tubo circular recto. Se usa en las lineas de refrigerante "
              "(C11-1), no en los intercambiadores. Las singularidades "
              "(codos, valvula de cuatro vias, conexiones) no estan incluidas."))
def churchill_tubo(Re, rugosidad_relativa=0.0):
    """Factor de friccion de FANNING en tubo circular, Churchill (1977).

        f = 2 [ (8/Re)^12 + (A + B)^(-3/2) ]^(1/12)
        A = [ 2.457 ln( 1 / ((7/Re)^0.9 + 0.27 e/D) ) ]^16
        B = (37530/Re)^16

    En laminar tiende a 16/Re. Mismo convenio que las demas de la familia:
    dP = f (4 L / D) G^2 / (2 rho).
    """
    import math

    Re = max(Re, 1.0)
    A = (2.457 * math.log(1.0 / ((7.0 / Re) ** 0.9 + 0.27 * rugosidad_relativa))) ** 16
    B = (37530.0 / Re) ** 16
    return 2.0 * ((8.0 / Re) ** 12 + (A + B) ** -1.5) ** (1.0 / 12.0)
