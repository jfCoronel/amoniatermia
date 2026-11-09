"""Ebullicion en PLACAS corrugadas. Apartado 9.6.3, ec. 9-15 y 9-16.

Familia `plate_boiling`. La ebullicion en interior de tubo esta en `tube.py`,
bajo `tube_boiling`, y no es intercambiable con esta: el ap. 9.7.5 declara
que las correlaciones de placa «no son aplicables» al serpentin. Las funciones
auxiliares de este modulo —Cooper, Martinelli, numero de ebullicion— si son
comunes a las dos geometrias y `tube.py` las importa de aqui.

VACIO V-1 (apartado 4.12.2): las campanas experimentales disponibles sobre
ebullicion de amoniaco en intercambiadores de placas se han desarrollado
mayoritariamente en el rango de flujos masicos propio de la refrigeracion
industrial y con configuraciones inundadas. La aplicacion de expansion directa
en pequena potencia esta mucho menos documentada.

Consecuencia operativa: esta es la mayor fuente de incertidumbre del modelo.
El apartado 6.11 pide que todo resultado que dependa criticamente de esta
magnitud se reporte como banda obtenida con al menos TRES formulaciones. Este
modulo registra DOS —la aditiva de Chen con Cooper y la asintotica— y las dos
comparten el termino nucleado. La tercera seria una correlacion especifica de
NH3 en placas, que no existe en la literatura consultada: se declara como
limitacion (§9.13) y no se rellena con un marcador.
"""
from __future__ import annotations

import math

from . import register, Validity
from .singlephase import martin_vdi, reynolds


def cooper_pool_boiling(p_red, M_kg_mol, q_flux, Rp_um=1.0):
    """Ebullicion en piscina, ecuacion 9-16.

        alpha_nb = 55 p_r^(0.12-0.2 log10 Rp) (-log10 p_r)^(-0.55) M^(-0.5) q''^0.67

    Ventaja para esta tesis: la dependencia con las propiedades del fluido
    queda EXPLICITA (via p_r y M), lo que la hace defendible al comparar
    refrigerantes distintos sobre la misma geometria (protocolo 6.8.3).

    Parameters
    ----------
    p_red : float      Presion reducida [-]
    M_kg_mol : float   Masa molar [kg/mol] (se convierte a g/mol internamente)
    q_flux : float     Flujo de calor [W/m2]
    Rp_um : float      Rugosidad superficial [um]
    """
    M_g = M_kg_mol * 1000.0
    p_red = min(max(p_red, 1e-4), 0.9)
    q_flux = max(q_flux, 1.0)
    return (55.0
            * p_red ** (0.12 - 0.2 * math.log10(Rp_um))
            * (-math.log10(p_red)) ** (-0.55)
            * M_g ** (-0.5)
            * q_flux ** 0.67)


def martinelli_tt(x, rho_l, rho_v, mu_l, mu_v):
    """Parametro de Martinelli turbulento-turbulento."""
    x = min(max(x, 1e-6), 1.0 - 1e-6)
    return ((1.0 - x) / x) ** 0.9 * (rho_v / rho_l) ** 0.5 * (mu_l / mu_v) ** 0.1


def boiling_number(q_flux, G, h_lv):
    return q_flux / max(G * h_lv, 1e-9)


@register(
    "plate_boiling", "asymptotic_cooper",
    reference="Superposicion con agregacion asintotica sobre Cooper (1984). "
              "VARIANTE: el ap. 9.6.3 adopta la superposicion ADITIVA de "
              "Chen (1966) como formulacion principal.",
    validity=Validity(
        ranges={}, fluids=(),
        notes="El apartado 9.6.3 declara que la base experimental de "
              "ebullicion de NH3 en placas es escasa y esta sesgada hacia "
              "refrigeracion industrial inundada (vacio V-1, ap. 4.12.2). No "
              "hay rango publicado que declarar para esta composicion; "
              "declararlo inventado daria la falsa impresion de "
              "identificacion completada que evita el ap. 9.6.4."))
def asymptotic_cooper(x, G, q_flux, sat, fluid_M, geom, n_exp=3.0, Rp_um=1.0):
    """VARIANTE asintotica de la descomposicion nucleada + convectiva.

    NO es la formulacion principal: el ap. 9.6.3 adopta la superposicion
    ADITIVA de Chen (1966), ec. 9-15. Se conserva registrada para que la
    campana de sensibilidad del ap. 6.11 disponga de una alternativa
    estructuralmente distinta.

        alpha_tp = [ (S alpha_nb)^n + (F alpha_l)^n ]^(1/n)

    Nota sobre el acoplamiento implicito: alpha_nb depende del flujo de calor,
    que a su vez depende de alpha_tp. El componente debe iterar internamente
    sobre q'' (apartado 9.6.3).
    """
    rho_l, rho_v = sat["rho_l"], sat["rho_v"]
    mu_l, mu_v = sat["mu_l"], sat["mu_v"]
    k_l, Pr_l = sat["k_l"], sat["Pr_l"]
    h_lv = sat["h_lv"]
    p_red = sat["p_red"]

    # contribucion convectiva: liquido circulando solo
    Re_l = reynolds(G * (1.0 - x), geom.D_h, mu_l)
    # Termino convectivo con MARTIN, la correlacion monofasica del §9.6.3.
    # Corregido el 29/09/2026: usaba `chevron_generic`, cuyos C y m estaban
    # escritos en el codigo sin fuente (el fichero los declara null). Efecto en
    # diseno: <= 0.25 % en capacidad (domina el termino nucleado).
    alpha_l = martin_vdi(max(Re_l, 1.0), Pr_l, k_l, geom.D_h,
                         beta_c=geom.beta_c)

    X_tt = martinelli_tt(x, rho_l, rho_v, mu_l, mu_v)
    F = max(1.0, 2.35 * (1.0 / X_tt + 0.213) ** 0.736)

    Bo = boiling_number(q_flux, G, h_lv)
    S = 1.0 / (1.0 + 2.53e-6 * max(Re_l, 1.0) ** 1.17)
    S = max(S, 0.05)

    alpha_nb = cooper_pool_boiling(p_red, fluid_M, q_flux, Rp_um)

    return ((S * alpha_nb) ** n_exp + (F * alpha_l) ** n_exp) ** (1.0 / n_exp)


@register(
    "plate_boiling", "additive_cooper",
    reference="Chen, J.C. (1966). Ind. Eng. Chem. Process Des. Dev. 5(3), "
              "322-329, con Cooper (1984) para la contribucion nucleada. "
              "Formulacion PRINCIPAL del apartado 9.6.3 (ec. 9-15).",
    validity=Validity(
        ranges={}, fluids=(),
        notes="El apartado 9.6.3 declara que la base experimental de "
              "ebullicion de NH3 en placas es escasa y esta sesgada hacia "
              "refrigeracion industrial inundada (vacio V-1, ap. 4.12.2). No "
              "hay rango publicado que declarar para esta composicion; "
              "declararlo inventado daria la falsa impresion de "
              "identificacion completada que evita el ap. 9.6.4."))
def additive_cooper(x, G, q_flux, sat, fluid_M, geom, Rp_um=1.0):
    """Formulacion PRINCIPAL del ap. 9.6.3, ecuacion 9-15.

        h_tp = S h_nb + F h_l

    Superposicion ADITIVA de Chen (1966) con Cooper (1984) para la contribucion
    nucleada. El factor F se expresa en funcion del parametro de Martinelli y el
    factor de supresion S en funcion del Reynolds de la fraccion liquida, Re_l.
    Chen evalua S con el Reynolds bifasico Re_l F^1.25; en placas con amoniaco
    Re_l no pasa de ~300 y S queda en 0.97-1 con ambas formas (EER de diseno de
    M-1 y M-2: < 0.01 %, comprobado el 13/10/2026). Se declara en el §9.4.4.
    """
    rho_l, rho_v = sat["rho_l"], sat["rho_v"]
    mu_l, mu_v = sat["mu_l"], sat["mu_v"]
    k_l, Pr_l = sat["k_l"], sat["Pr_l"]
    p_red = sat["p_red"]

    Re_l = reynolds(G * (1.0 - x), geom.D_h, mu_l)
    # Termino convectivo con MARTIN, la correlacion monofasica del §9.6.3.
    # Corregido el 29/09/2026: usaba `chevron_generic`, cuyos C y m estaban
    # escritos en el codigo sin fuente (el fichero los declara null). Efecto en
    # diseno: <= 0.25 % en capacidad (domina el termino nucleado).
    alpha_l = martin_vdi(max(Re_l, 1.0), Pr_l, k_l, geom.D_h,
                         beta_c=geom.beta_c)
    X_tt = martinelli_tt(x, rho_l, rho_v, mu_l, mu_v)
    F = max(1.0, 2.35 * (1.0 / X_tt + 0.213) ** 0.736)
    S = max(1.0 / (1.0 + 2.53e-6 * max(Re_l, 1.0) ** 1.17), 0.05)
    alpha_nb = cooper_pool_boiling(p_red, fluid_M, q_flux, Rp_um)
    return S * alpha_nb + F * alpha_l
