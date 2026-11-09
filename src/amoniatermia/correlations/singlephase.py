"""Coeficiente de pelicula en regimen monofasico. Ecuacion 9-14.

    Nu = C Re^m Pr^(1/3) (mu/mu_w)^0.14 ;  alpha = Nu k / D_h

Los coeficientes C y m dependen del angulo de corrugacion. Los valores aqui
recogidos son PROVISIONALES y deben sustituirse por los de la referencia
concreta que se cite en el apartado 9.6.7, con su rango de validez.
"""
from __future__ import annotations

import math

from . import register, Validity


@register(
    "singlephase", "chevron_generic",
    reference="Analogia calor / perdida de carga en placas corrugadas "
              "(referencia general, antigua tabla 10.7). PENDIENTE de fuente primaria.",
    validity=Validity(
        ranges={},
        notes="C y m dependen del angulo de corrugacion de la placa "
              "seleccionada y la antigua tabla 10.7 los declara pendientes. Los "
              "valores de esta funcion son PROVISIONALES, luego no hay base "
              "experimental que declarar. Vease docs/historico/PENDIENTES.md."))
def chevron_generic(Re, Pr, k, D_h, beta_c=math.radians(60.0), mu_ratio=1.0,
                    C=None, m=None, **kw):
    """Correlacion generica tipo chevron, Nu = C Re^m Pr^(1/3) (mu/mu_w)^0.14.

    C y m NO existen: `placas_alfanova.yaml` los declara null (pendientes.
    C_monofasico y m_monofasico). Corregido el 29/09/2026: la funcion los
    llevaba escritos en el codigo (C = 0.20 + 0.15 sin^2(2 beta), m = 0.70),
    marcados como provisionales, que es el valor plausible que la regla de los
    datos que no existen prohibe. Ahora los pide al fichero —o como parametro,
    para una exploracion declarada— y falla si no estan."""
    if C is None or m is None:
        from .. import data as D
        df = D.load("placas_alfanova")
        C = df.require("pendientes.C_monofasico",
                       "Constante de la correlacion chevron generica.") if C is None else C
        m = df.require("pendientes.m_monofasico",
                       "Exponente de la correlacion chevron generica.") if m is None else m
    Nu = C * Re ** m * Pr ** (1.0 / 3.0) * mu_ratio ** 0.14
    return Nu * k / D_h


@register(
    "singlephase", "dittus_boelter",
    reference="Dittus, F.W. y Boelter, L.M.K. (1930). Univ. California "
              "Publ. Eng. 2, 443.",
    validity=Validity(
        ranges={"Re": (1.0e4, None), "Pr": (0.6, 160.0)},
        source="Rango de aplicacion declarado habitualmente para la "
               "correlacion; adicionalmente L/D > 10.",
        notes="Registrada SOLO como caso de verificacion del apartado 6.7.1: "
              "tiene solucion conocida y permite comprobar la cadena "
              "Re -> Nu -> alpha. No es una correlacion de placas."))
def dittus_boelter(Re, Pr, k, D_h, heating=True, **kw):
    """Dittus-Boelter. Solo como caso de VERIFICACION del codigo
    (apartado 6.7.1): tiene solucion conocida y permite comprobar que la
    cadena Re -> Nu -> alpha esta correctamente implementada.
    NO debe emplearse para placas corrugadas en produccion."""
    n = 0.4 if heating else 0.3
    Nu = 0.023 * Re ** 0.8 * Pr ** n
    return Nu * k / D_h


def reynolds(G, D_h, mu):
    """Numero de Reynolds a partir del flujo masico por unidad de area."""
    return G * D_h / mu


@register(
    "singlephase", "tube_dittus_boelter",
    reference="Dittus, F.W. y Boelter, L.M.K. (1930). Univ. California "
              "Publ. Eng. 2, 443. Nu = 0.023 Re^0.8 Pr^n.",
    validity=Validity(
        ranges={"Re": (1.0e4, None), "Pr": (0.6, 160.0)},
        source="Rango de aplicacion declarado habitualmente; ademas L/D > 10.",
        notes="Para el INTERIOR DE TUBO circular, regimen monofasico. Es la "
              "misma forma que el propio capitulo emplea como base de liquido "
              "circulando solo en las ec. 9-24 y 9-27. Registrada aparte de "
              "`dittus_boelter` para que su uso en el serpentin no se confunda "
              "con el caso de verificacion del ap. 6.7.1."))
def tube_dittus_boelter(Re, Pr, k, D, heating=True, **kw):
    """Monofasico en el interior de tubo circular."""
    n = 0.4 if heating else 0.3
    return 0.023 * Re ** 0.8 * Pr ** n * k / D


# ---------------------------------------------------------------------------
# Martin (VDI Heat Atlas) — la correlacion que el ap. 9.6.7 empleo de verdad
# ---------------------------------------------------------------------------

def martin_friction(Re, beta_c):
    """Factor de friccion de Fanning de Martin para placa corrugada.

        1/sqrt(f) = cos(b) / sqrt(0.18 tan b + 0.36 sin b + f0/cos b)
                    + (1 - cos b) / sqrt(3.8 f1)

        f0 = 16/Re                         (Re < 2000)
           = (1.56 ln Re - 3.0)^-2         (Re >= 2000)
        f1 = 149/Re + 0.9625               (Re < 2000)
           = 9.75 / Re^0.289               (Re >= 2000)

    CONVENIO DE ANGULO. `beta_c` se mide desde la DIRECCION DE FLUJO, de modo
    que beta_c = 0 corresponde a corrugacion alineada con el flujo. Con ese
    convenio la expresion degenera correctamente en f = f0 (conducto liso)
    cuando beta_c -> 0, lo que sirve de comprobacion de que el convenio es el
    correcto. Es el mismo que documenta `PlateGeometry.beta_c`.

    La literatura emplea tambien el convenio complementario (medido desde la
    perpendicular al flujo), en el que una placa «de 60 grados» es la misma que
    aqui seria de 30. Debe verificarse contra la ficha de la placa antes de dar
    por buena una geometria concreta.
    """
    Re = max(Re, 1.0)
    if Re < 2000.0:
        f0 = 16.0 / Re
        f1 = 149.0 / Re + 0.9625
    else:
        f0 = (1.56 * math.log(Re) - 3.0) ** -2
        f1 = 9.75 / Re ** 0.289
    cb, sb, tb = math.cos(beta_c), math.sin(beta_c), math.tan(beta_c)
    if cb < 1e-9:                      # beta -> 90 grados
        return 3.8 * f1
    inv = (cb / math.sqrt(0.18 * tb + 0.36 * sb + f0 / cb)
           + (1.0 - cb) / math.sqrt(3.8 * f1))
    return 1.0 / inv ** 2


@register(
    "singlephase", "martin_vdi",
    reference="Martin, H. (1996). Chem. Eng. Process. 35, 301-310; recogida en "
              "el VDI Heat Atlas. Analogia generalizada entre transferencia de "
              "calor y perdida de carga en placas corrugadas (ec. 9-14).",
    validity=Validity(
        ranges={},
        notes="Es la correlacion con la que el ap. 9.6.7 resolvio el punto de "
              "diseno del desrecalentador, marchando en contracorriente con "
              "ella a ambos lados porque en desrecalentamiento seco ninguno de "
              "los dos fluidos cambia de fase. El propio apartado declara una "
              "limitacion: el Reynolds del agua (~242) queda en regimen "
              "laminar, lo que introduce mayor incertidumbre en ese lado y debe "
              "contrastarse con datos del fabricante o con una campana de "
              "sensibilidad en el cap. 10. El rango de validez de Martin no se "
              "declara aqui porque depende del angulo de corrugacion de la "
              "placa, que es un dato PENDIENTE (antigua tabla 10.7)."))
def martin_vdi(Re, Pr, k, D_h, beta_c=math.radians(60.0), mu_ratio=1.0, **kw):
    """Correlacion de Martin, ecuacion 9-14.

        Nu = 0.122 Pr^(1/3) (mu/mu_w)^(1/6) [f Re^2 sin(2 beta)]^0.374

    A diferencia de `chevron_generic`, cuyos C y m son provisionales, esta
    correlacion no tiene coeficientes libres: la dependencia con la geometria
    entra por el angulo de corrugacion a traves del factor de friccion, que es
    lo que la analogia calor / perdida de carga aporta.
    """
    Re = max(Re, 1.0)
    f = martin_friction(Re, beta_c)
    Nu = (0.122 * Pr ** (1.0 / 3.0) * mu_ratio ** (1.0 / 6.0)
          * (f * Re ** 2 * math.sin(2.0 * beta_c)) ** 0.374)
    return Nu * k / D_h
