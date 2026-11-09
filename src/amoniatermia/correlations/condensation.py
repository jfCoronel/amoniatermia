"""Condensacion en PLACAS corrugadas. Apartados 9.6.3 a 9.6.5.

Familia `plate_condensation`. Las correlaciones de interior de tubo estan en
`tube.py`, bajo `tube_condensation`, y no son intercambiables con estas: el
ap. 9.7.5 declara que las de placas «no son aplicables» al serpentin.

El apartado 9.6.3 es el que sostiene la hipotesis H3 y por eso recibe
tratamiento diferenciado: cuando la pared esta por debajo de la temperatura de
saturacion, el desrecalentamiento NO es un proceso monofasico puro.
"""
from __future__ import annotations

import math

from . import register, Validity
from .singlephase import reynolds


def equivalent_mass_flux(G, x, rho_l, rho_v):
    """Flujo masico equivalente. Sin ecuacion en la v30: alternativa registrada
    que el §9.6.3 conserva para la banda de incertidumbre."""
    return G * ((1.0 - x) + x * (rho_l / rho_v) ** 0.5)


@register(
    "plate_condensation", "equivalent_Re",
    reference="Enfoque de conveccion forzada con Reynolds equivalente. "
              "DISCREPANCIA: el apartado 9.6.3 lo DESCARTA expresamente en "
              "favor de la teoria de pelicula de Nusselt (ec. 9-17), por la "
              "disposicion vertical de las placas y el elevado calor latente "
              "del NH3. Se conserva registrada como alternativa para la "
              "sensibilidad del cap. 10, no como formulacion principal.",
    validity=Validity(
        ranges={},
        notes="C y m PROVISIONALES. La base bibliografica de condensacion de "
              "NH3 en placas es aun mas escasa que la de ebullicion "
              "(ap. 9.6.3) y debe declararse al fijar el dominio de validez "
              "en el cap. 10."))
def equivalent_Re(x, G, sat, geom, C=4.118, m=0.4, **kw):
    """Correlacion basada en Reynolds equivalente. Sin ecuacion en la v30 (§10.6.3).

    Los coeficientes C y m son PROVISIONALES. La base bibliografica para la
    condensacion de amoniaco en placas es considerablemente mas escasa que
    para la ebullicion, circunstancia que debe declararse en el capitulo 10 al
    establecer el dominio de validez del modelo.
    """
    rho_l, rho_v = sat["rho_l"], sat["rho_v"]
    mu_l, k_l, Pr_l = sat["mu_l"], sat["k_l"], sat["Pr_l"]
    G_eq = equivalent_mass_flux(G, x, rho_l, rho_v)
    Re_eq = reynolds(G_eq, geom.D_h, mu_l)
    return C * Re_eq ** m * Pr_l ** (1.0 / 3.0) * k_l / geom.D_h


def wall_temperature(T_ref, q_dot, alpha_ref, A_ref):
    """Temperatura de pared, ecuacion 9-18."""
    return T_ref - q_dot / max(alpha_ref * A_ref, 1e-9)


@register(
    "plate_condensation", "bell_ghaly_desuperheat",
    reference="Correccion de desrecalentamiento con pared humeda, ec. 9-19 "
              "(ap. 9.6.5). Sostiene la hipotesis H3.",
    validity=Validity(
        ranges={},
        notes="AVISO: registrada pero todavia NO invocada por "
              "components/plate_hx.py, que cuenta las celdas con pared humeda "
              "y las resuelve todas como monofasicas. Discrepancia D5 de "
              "docs/historico/PLAN_PUESTA_EN_MARCHA.md; se cierra en la fase D."))
def bell_ghaly_Z(x, cp_v, dTsat_dh):
    """Parametro Z de la ecuacion 9-19, en la forma LITERAL del capitulo.

        Z = x cp_v (dT_sat/dh)

    AVISO. Para un fluido PURO a presion constante, T_sat no depende de la
    entalpia dentro de la campana: dT_sat/dh = 0 exactamente, y por tanto Z = 0
    y la ec. 9-19 no introduce correccion alguna. La expresion procede del
    metodo de Bell y Ghaly, formulado para MEZCLAS multicomponente, donde la
    temperatura de burbuja si varia con la composicion a lo largo de la
    condensacion y ese gradiente es el que genera la resistencia adicional en
    fase vapor.

    El ap. 9.6.5, en cambio, describe el fenomeno correcto para un fluido puro
    —vapor fuertemente sobrecalentado sobre pared por debajo de la saturacion,
    con condensacion y enfriamiento simultaneos— pero le adjunta una ecuacion
    que, aplicada a NH3 puro, se anula. La discrepancia se reporta y no se
    resuelve (CLAUDE.md): ver docs/historico/PLAN_PUESTA_EN_MARCHA.md, apartado 8.

    Para un fluido puro la formulacion equivalente emplea Z como FRACCION
    SENSIBLE de la carga, Z = q_sensible/q_total, que si toma valores entre 0 y
    1 y recupera los dos limites correctos: Z = 0 da condensacion pura y Z = 1
    la resistencia de fase vapor en serie. `wet_wall_UA` la admite por eso como
    parametro explicito.
    """
    return x * cp_v * dTsat_dh


@register(
    "plate_condensation", "bell_ghaly_desuperheat",
    reference="Correccion de desrecalentamiento con pared humeda, ec. 9-19 "
              "(ap. 9.6.5). Metodo de Bell, K.J. y Ghaly, M.A. (1973). "
              "Sostiene la hipotesis H3.",
    validity=Validity(
        ranges={"Z": (0.0, 1.0)},
        notes="Formulada para MEZCLAS multicomponente. Aplicada a un fluido "
              "puro con el Z literal de la ec. 9-19 se anula: ver la nota de "
              "`bell_ghaly_Z`. Aqui Z entra como parametro explicito."))
def wet_wall_UA(alpha_cond, alpha_vap, Z):
    """Coeficiente EFECTIVO con pared humeda, ecuacion 9-19.

        1/U_ef = 1/alpha_cond + Z/alpha_vap

    Referido al area del lado refrigerante, de modo que el area se simplifica.
    Limites: Z = 0 -> condensacion pura; Z = 1 -> las dos resistencias en serie,
    que es el caso de enfriamiento sensible sobre pared humeda.
    """
    Z = min(max(Z, 0.0), 1.0)
    return 1.0 / (1.0 / max(alpha_cond, 1e-9) + Z / max(alpha_vap, 1e-9))


def is_wet_wall(T_wall, T_sat):
    """Criterio del apartado 9.6.3.

    El capitulo 11 debe reportar que fraccion del desrecalentador opera con
    pared humeda en cada condicion, porque de ello depende la potencia
    recuperable y por tanto el contraste de H3.
    """
    return T_wall < T_sat


# ---------------------------------------------------------------------------
# Formulacion PRINCIPAL del ap. 9.6.3: teoria de pelicula de Nusselt
# ---------------------------------------------------------------------------

from ..data import MissingData


class MissingCorrectionFactor(MissingData):
    """Se ha invocado la condensacion en placas sin fijar phi_c o phi_v.

    Es un dato que no existe, y desde el 29/09/2026 lo dice su tipo: al heredar
    de `MissingData`, el lazo externo lo propaga en lugar de tomarlo por un
    fallo numerico y devolver un punto no convergido."""


@register(
    "plate_condensation", "nusselt_film",
    reference="Nusselt, W. (1916). Teoria de pelicula descendente, ec. 9-17, "
              "con los factores de correccion de corrugacion y de velocidad "
              "residual de vapor de la ec. 9-17.",
    validity=Validity(
        ranges={},
        notes="FORMULACION PRINCIPAL del ap. 9.6.3, que descarta expresamente "
              "el enfoque de conveccion forzada con Reynolds equivalente por "
              "dos razones fisicas: la disposicion vertical de las placas "
              "favorece una pelicula descendente gobernada por gravedad, y el "
              "elevado calor latente del NH3 reduce el caudal circulante "
              "respecto a un halogenado de capacidad equivalente, lo que atenua "
              "la contribucion de cizalladura del vapor. La constante 0.943 es "
              "la base laminar de Nusselt y no tiene ajuste; phi_c y phi_v son "
              "datos PENDIENTES (antigua tabla 10.7) y la funcion FALLA si se invocan "
              "sin fijar. La base bibliografica de condensacion de NH3 en "
              "placas es mas escasa que la de ebullicion (ap. 9.6.3)."))
def nusselt_film(x, G, sat, geom, dT=None, L=None, phi_c=None, phi_v=None, **kw):
    """Condensacion en pelicula, ecuaciones 9-17 y 9-17.

        h_p    = 0.943 [k_l^3 rho_l (rho_l - rho_v) g h_lg / (mu_l L dT)]^(1/4)
        h_cond = phi_c phi_v h_p

    `dT` es la diferencia entre la saturacion y la pared, y `L` la longitud de
    la pelicula (por defecto, la longitud de placa). Ambas hacen que el
    coeficiente dependa del propio flujo de calor, de ahi que el componente deba
    iterar sobre el (lazo interno del ap. 9.4.3).

    `phi_c` y `phi_v` NO tienen valor por defecto. El ap. 9.6.3 dice
    expresamente que «no se fijan aqui valores aproximados para no dar la falsa
    impresion de una identificacion ya completada», y CLAUDE.md prohibe
    rellenar un dato pendiente con un valor plausible.
    """
    if phi_c is None or phi_v is None:
        raise MissingCorrectionFactor(
            "phi_c y phi_v son datos PENDIENTES (data/placas_alfanova.yaml, "
            "ap. 9.6.4). La forma funcional phi_c(beta) y phi_v(Re_v) esta sin "
            "fijar y depende de la geometria de placa seleccionada. No pueden "
            "suponerse: sin ellos la condensacion en placas no cierra. Para "
            "explorar sin el dato, pasarlos explicitamente y declararlo.")
    dT = 5.0 if dT is None else max(abs(dT), 0.1)
    L = geom.L_p if L is None else L
    g = 9.80665
    h_p = 0.943 * ((sat["k_l"] ** 3 * sat["rho_l"]
                    * (sat["rho_l"] - sat["rho_v"]) * g * sat["h_lv"])
                   / (sat["mu_l"] * L * dT)) ** 0.25
    return phi_c * phi_v * h_p


@register(
    "plate_condensation", "nusselt_film_anclada_27_30H",
    reference="Pelicula de Nusselt (ec. 9-17) con el producto phi_c*phi_v de "
              "la ec. 9-17 ANCLADO sobre el punto de seleccion del AlfaNova "
              "27-30H (ficha Alfa Laval del 23/03/2026). Procedimiento en "
              "`components/plate_hx.anchor_from_selection_point`.",
    validity=Validity(
        ranges={"T_sat": (318.0, 328.0), "dT": (0.5, 8.0)},
        fluids=("Ammonia",),
        source="Un unico punto: NH3 condensando a 50 C, 35.73 kg/h, titulo de "
               "1 a 0, agua de 40 a 45 C, 10.5 kW sobre 0.7 m2 con MTD 7.3 K.",
        notes="Lo identificado es el PRODUCTO phi_c*phi_v, no cada factor: es "
              "lo unico que interviene en la ec. 9-17, y separarlos exigiria "
              "un segundo punto a otra velocidad de vapor, igual que C1 y C2 "
              "del ap. 9.7.3 no se separaron con un solo punto de ficha. "
              "El valor NO es robusto: su banda, 1.12 a 2.06, la domina el "
              "factor de alargamiento, que sigue estimado, y el convenio de "
              "area. Debe viajar siempre con el Phi y el convenio con que se "
              "obtuvo (1.15 y area desarrollada). Anclada en CONDENSACION a "
              "50 C: emplearla lejos de ahi es extrapolar el anclaje, no solo "
              "la correlacion."))
def nusselt_film_anclada(x, G, sat, geom, dT=None, L=None, producto=None, **kw):
    """Pelicula de Nusselt con el factor de correccion anclado sobre ficha.

    Reproduce el punto de seleccion POR CONSTRUCCION, igual que la correlacion
    de aire del ap. 9.7.3 reproduce el suyo. Lo que hace util el anclaje no es
    ese punto sino la extrapolacion a su entorno, y su fiabilidad depende de que
    la forma funcional de Nusselt sea la correcta: el anclaje solo corrige la
    constante multiplicativa.
    """
    if producto is None:
        from .. import data as D
        producto = D.load("placas_alfanova").require(
            "producto_phi_c_phi_v.valor",
            "Producto phi_c*phi_v: se obtiene anclando sobre el punto de "
            "seleccion con `plate_hx.anchor_from_selection_point`.")
    return nusselt_film(x, G, sat, geom, dT=dT, L=L,
                        phi_c=producto, phi_v=1.0)
