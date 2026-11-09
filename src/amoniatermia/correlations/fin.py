"""Eficiencia de aleta y efectividad superficial. Apartados 9.7.4 y 9.7.6.

Se registra como familia intercambiable, y no se codifica en el componente, por
una razon concreta del capitulo: el ap. 9.7.4 declara una discrepancia del 11 %
entre la conductancia global reconstruida (38.2 W/(m2 K)) y la de ficha (43), la
atribuye al metodo de determinacion del radio equivalente de aleta, y propone
resolverla en el cap. 10 CONTRASTANDO el metodo de aleta equivalente frente a un
calculo bidimensional. Ese contraste exige poder sustituir el metodo por otro sin
tocar el componente, que es exactamente lo que da el registro del ap. 9.12.3.

La discrepancia NO se corrige mediante un factor de ajuste: hacerlo enmascararia
en un coeficiente empirico lo que es un desacuerdo identificado y localizado en
un submodelo concreto.
"""
from __future__ import annotations

import math

from . import Validity, register


@register(
    "fin", "schmidt_annular",
    reference="Schmidt, T.E. (1945/1949). Metodo de la aleta anular "
              "equivalente para haces de tubos aleteados. Ap. 9.7.4, "
              "ec. 9-22.",
    validity=Validity(
        ranges={},
        notes="El ap. 9.7.4 identifica este metodo como origen probable de la "
              "discrepancia del 11 % en la conductancia global: reproducir el "
              "valor de ficha exigiria una efectividad superficial de 0.549 en "
              "lugar de 0.465, diferencia compatible con que el programa de "
              "seleccion del fabricante emplee otro criterio de radio "
              "equivalente. El criterio del fabricante es un dato PENDIENTE "
              "(data/bateria_frimetal_cbn21.yaml). Se declara como sesgo "
              "conocido y conservador."))
def schmidt_annular(h_a, k_fin, t_fin, r_collar, r_equivalent, b_prime=None,
                    cp_a=1006.0):
    """Eficiencia de una aleta anular equivalente.

        eta = tanh(m r phi) / (m r phi)
        m   = sqrt(2 h / (k t))
        phi = (r_eq/r - 1) (1 + 0.35 ln(r_eq/r))

    Superficie humeda (ap. 9.7.6, ec. 9-29). Si se pasa `b_prime`, la
    pendiente de la curva de entalpia de saturacion dh_sat/dT en la temperatura
    superficial, el parametro de aleta se corrige:

        m_w = sqrt(2 h / (k t) * b' / cp_a)

    porque en superficie humeda el gradiente que gobierna la transferencia deja
    de ser el de temperatura para ser el de entalpia de saturacion. Con b' del
    orden de 1.77 veces el calor especifico del aire, emplear la eficiencia seca
    en regimen humedo sobreestimaria la conductancia del evaporador un 28 %.
    """
    m = math.sqrt(2.0 * h_a / (k_fin * t_fin))
    if b_prime is not None:
        m *= math.sqrt(b_prime / cp_a)
    ratio = r_equivalent / r_collar
    phi = (ratio - 1.0) * (1.0 + 0.35 * math.log(ratio))
    mrphi = m * r_collar * phi
    return math.tanh(mrphi) / mrphi


def surface_effectiveness(eta_fin, fin_area_fraction):
    """Efectividad global de superficie, ecuacion 9-22.

        eta_sa = 1 - (A_f/A_t) (1 - eta_a)
    """
    return 1.0 - fin_area_fraction * (1.0 - eta_fin)
