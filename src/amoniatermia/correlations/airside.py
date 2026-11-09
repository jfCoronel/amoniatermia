"""Lado de aire de la bateria de tubo y aleta. Apartado 9.7.3.

El lado de aire concentra el 72.8 % de la resistencia termica del componente
(tabla 9.18), de modo que la exactitud del conjunto depende de una correlacion
cuya incertidumbre es superior a la de todas las del lado de refrigerante. De
ahi que el capitulo no adopte una correlacion general sino que ANCLE una sobre
el unico punto de operacion disponible.
"""
from __future__ import annotations

from . import Validity, register


def max_velocity(V_frontal, sigma):
    """Velocidad en la seccion minima [m/s], ec. 9-21."""
    return V_frontal / sigma


def reynolds_Dc(rho, V_max, d_c, mu):
    """Reynolds referido al diametro con collarin, ec. 9-21."""
    return rho * V_max * d_c / mu


@register(
    "airside", "colburn_anclada_cbn21",
    reference="Anclaje propio sobre el punto de ficha de la bateria Frimetal "
              "CBN-21 ESPECIAL (ap. 9.7.3). Forma j = C1 Re_Dc^C2 de la "
              "familia de correlaciones de bateria de tubo y aleta lisa.",
    validity=Validity(
        ranges={"Re_Dc": (4190.0, 5512.0)},
        fluids=("Air",),
        source="§9.7.3: Re_Dc = 4190 en el punto de ficha (condensacion, "
               "aire a 35 C) y 5512 en la condicion mas fria del perfil de "
               "calefaccion (aire a -7 C), con caudal de ventilador constante "
               "de 7600 m3/h.",
        notes="NO es una identificacion en el sentido del ap. 9.5.3: un unico "
              "punto no permite determinar dos constantes. El exponente C2 se "
              "ha FIJADO A PRIORI desde la literatura (-0.42, valor "
              "caracteristico de la familia de aleta lisa) y solo la constante "
              "multiplicativa se ha ajustado. La correlacion reproduce el punto "
              "de ficha POR CONSTRUCCION, y su fiabilidad al extrapolar depende "
              "de que el exponente adoptado sea representativo. El rango de "
              "extrapolacion es estrecho —un 32 % de variacion en Re— y esa "
              "acotacion es la que hace defendible el procedimiento."))
def colburn_anclada_cbn21(Re_Dc, C1=None, C2=None):
    """Factor de Colburn anclado, ecuacion 9-21.

    C1 = 0.507 resulta de imponer j = 0.01526 a Re_Dc = 4190, que es el factor
    de Colburn correspondiente al coeficiente de pelicula de 113 W/(m2 K)
    declarado por la ficha. C1 y C2 se leen de `correlacion_aire` en el fichero
    de la bateria —una sola fuente, y sustituible para la sensibilidad del
    §6.11— salvo que se pasen expresamente.
    """
    if C1 is None or C2 is None:
        from .. import data as D
        df = D.air_coil()
        C1 = df.require("correlacion_aire.C1") if C1 is None else C1
        C2 = df.require("correlacion_aire.C2") if C2 is None else C2
    return C1 * Re_Dc ** C2


def alpha_from_colburn(j, G_max, cp_a, Pr_a):
    """Coeficiente de pelicula del lado de aire, ecuacion 9-21.

        alpha_a = j G_max cp_a / Pr_a^(2/3)
    """
    return j * G_max * cp_a / Pr_a ** (2.0 / 3.0)
