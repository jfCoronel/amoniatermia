"""Propiedades del aire humedo. Apartado 9.7.6.

POR QUE UN MODULO PROPIO Y NO `HAPropsSI`
-----------------------------------------
CLAUDE.md prohibe `PropsSI` en bucle por un factor 163 de penalizacion. La
version de aire humedo, `HAPropsSI`, es todavia peor: resuelve internamente un
equilibrio y cuesta del orden del milisegundo por llamada. La marcha del
ap. 9.7.2 evalua la curva de entalpia de saturacion varias veces por celda y
por iteracion sobre la temperatura superficial —del orden de 10^4 evaluaciones
por punto de operacion resuelto—, de modo que apoyarla en `HAPropsSI` costaria
decenas de segundos por punto.

Se adoptan en su lugar las formulaciones analiticas de ASHRAE (Handbook of
Fundamentals, cap. 1), que son las que emplea la practica del sector y cuestan
un `exp` por llamada. `tests/test_psicrometria.py` las contrasta contra
CoolProp: el acuerdo es de 0.2 % en la pendiente de la curva de saturacion, que
es la magnitud de la que depende la ec. 9-29.

CONVENIO DE BASE MASICA
-----------------------
La humedad especifica `w` y la entalpia `h` estan referidas a **kilogramo de
aire seco**, que es el convenio de ASHRAE y el unico en que la entalpia del aire
es conservativa cuando se retira condensado. El caudal que entra en el balance
entalpico de la ec. 9-28 es por tanto el de aire SECO, no el de aire humedo:
`m_seco = m_humedo / (1 + w)`. Confundirlos introduce un error del orden del 2 %
en el caudal de un aire a 35 C y 50 % de humedad relativa.

La densidad, en cambio, se devuelve por metro cubico de MEZCLA, que es la que
interviene en la velocidad masica del lado de aire.

NUMERO DE LEWIS
---------------
El metodo del potencial entalpico descansa en la analogia entre transferencia de
calor y de masa con numero de Lewis unidad (ap. 9.7.6). Es la hipotesis
estandar y se declara como tal: `LEWIS_NUMBER` esta expuesto como constante del
modulo para que el cap. 10 pueda cuantificar el efecto de relajarla, no porque
el modelo la resuelva.
"""
from __future__ import annotations

import math

# --- Constantes ------------------------------------------------------------
P_ATM = 101325.0            # Pa
R_DRY_AIR = 287.042         # J/(kg K)
R_VAPOR = 461.524           # J/(kg K)
MW_RATIO = 0.621945         # M_agua / M_aire
CP_DRY_AIR = 1006.0         # J/(kg K)
CP_VAPOR = 1860.0           # J/(kg K)
CP_WATER = 4186.0           # J/(kg K)
H_FG_0 = 2.501e6            # J/kg, calor latente a 0 C (datum ASHRAE)
T0 = 273.15                 # K

#: Numero de Lewis adoptado en el metodo del potencial entalpico (ap. 9.7.6).
#: Hipotesis declarada, no resultado. Le != 1 escalaria la contribucion latente
#: por Le^(2/3) y es la via de sensibilidad que el cap. 10 debe recorrer.
LEWIS_NUMBER = 1.0

# Coeficientes ASHRAE de la presion de saturacion (Handbook of Fundamentals,
# cap. 1, ec. 5 sobre hielo y ec. 6 sobre agua liquida).
_C_ICE = (-5.6745359e3, 6.3925247, -9.677843e-3, 6.2215701e-7,
          2.0747825e-9, -9.484024e-13, 4.1635019)
_C_WATER = (-5.8002206e3, 1.3914993, -4.8640239e-2, 4.1764768e-5,
            -1.4452093e-8, 6.5459673)


# --- Presion de saturacion -------------------------------------------------
def p_sat(T: float) -> float:
    """Presion de vapor de saturacion [Pa] a la temperatura T [K].

    Conmuta a la curva sobre HIELO por debajo de 0 C. La distincion no es
    cosmetica en este componente: el ap. 9.7.6 situa la evaporacion en -2.9 C
    con aire a 2 C, esto es, dentro del dominio de escarcha, y es la curva sobre
    hielo la que gobierna el deposito.
    """
    if T < T0:
        c = _C_ICE
        return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T ** 2
                        + c[4] * T ** 3 + c[5] * T ** 4 + c[6] * math.log(T))
    c = _C_WATER
    return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T ** 2
                    + c[4] * T ** 3 + c[5] * math.log(T))


def humidity_ratio(T: float, RH: float, P: float = P_ATM) -> float:
    """Humedad especifica [kg agua / kg aire seco] desde T y humedad relativa."""
    return humidity_ratio_from_pv(RH * p_sat(T), P)


def humidity_ratio_from_pv(p_v: float, P: float = P_ATM) -> float:
    """Humedad especifica desde la presion parcial de vapor."""
    return MW_RATIO * p_v / max(P - p_v, 1e-9)


def w_saturation(T: float, P: float = P_ATM) -> float:
    """Humedad especifica de saturacion a T."""
    return humidity_ratio_from_pv(p_sat(T), P)


def relative_humidity(T: float, w: float, P: float = P_ATM) -> float:
    return partial_pressure(w, P) / p_sat(T)


def partial_pressure(w: float, P: float = P_ATM) -> float:
    return P * w / (MW_RATIO + w)


def dew_point(w: float, P: float = P_ATM) -> float:
    """Temperatura de rocio [K] del aire de humedad especifica w.

    Es el umbral que decide el regimen de la superficie en el ap. 9.7.2: por
    debajo de el la superficie condensa y la marcha deja de poder hacerse sobre
    diferencia de temperaturas.
    """
    return _invert_monotone(p_sat, partial_pressure(w, P),
                            lo=T0 - 80.0, hi=T0 + 90.0)


# --- Entalpia --------------------------------------------------------------
def enthalpy(T: float, w: float) -> float:
    """Entalpia del aire humedo [J / kg aire SECO], datum ASHRAE (0 C).

        h = cp_a t + w (h_fg0 + cp_v t),   t en grados Celsius
    """
    t = T - T0
    return CP_DRY_AIR * t + w * (H_FG_0 + CP_VAPOR * t)


def temperature_from_enthalpy(h: float, w: float) -> float:
    """Inversa exacta de `enthalpy` en T. Lineal, no requiere iterar."""
    return T0 + (h - w * H_FG_0) / (CP_DRY_AIR + w * CP_VAPOR)


def humidity_from_enthalpy(h: float, T: float) -> float:
    """Humedad especifica que corresponde a (h, T). Inversa exacta en w."""
    t = T - T0
    return (h - CP_DRY_AIR * t) / (H_FG_0 + CP_VAPOR * t)


def saturation_enthalpy(T: float, P: float = P_ATM) -> float:
    """Entalpia del aire SATURADO a la temperatura T. Curva h_sat(T).

    Es el potencial que sustituye a la temperatura en la ec. 9-28: la fuerza
    impulsora del intercambiador humedo es h_aire - h_sat(T_superficie), no una
    diferencia de temperaturas.
    """
    return enthalpy(T, w_saturation(T, P))


def saturation_enthalpy_slope(T: float, P: float = P_ATM,
                              dT: float = 0.05) -> float:
    """Pendiente b' = dh_sat/dT [J/(kg K)] en T, ec. 9-29.

    Es el factor que hace que la eficiencia de aleta humeda no coincida con la
    seca.

    DONDE SE EVALUA, Y UNA IMPRECISION DEL CAPITULO. La ec. 9-29 la define
    explicitamente en la temperatura SUPERFICIAL, b' = dh_sat/dT|_{T_s}, y asi
    la evalua este modelo. El texto del ap. 9.7.6 declara en cambio
    1781 J/(kg K) «con una temperatura superficial del orden de 1 C», y ese
    valor no es el de 1 C: el modelo da 1750 ahi, y 1780.2 —esto es, los 1781
    del capitulo, con el factor 1.770 frente al 1.77 declarado— exactamente a
    1.6 C, que es la temperatura de EVAPORACION de la primera fila de la tabla
    9.20. La superficie de ese mismo punto esta a unos 3 C, donde b' vale 1854.

    Se reporta y no se corrige en ninguno de los dos sentidos. El efecto es
    inmaterial —con 1854 en lugar de 1781 la eficiencia de aleta humeda pasa de
    0.337 a 0.336, y la efectividad superficial sigue siendo 0.358—, de modo que
    ningun resultado del capitulo se mueve; lo que procede es corregir la
    redaccion, que atribuye a la superficie una temperatura que es la del
    refrigerante.

    Se evalua por diferencia centrada en lugar de analiticamente porque la
    derivada de la curva ASHRAE conmuta de rama en 0 C y la forma numerica
    mantiene la continuidad del tratamiento a ambos lados del cambio.
    """
    return (saturation_enthalpy(T + dT, P)
            - saturation_enthalpy(T - dT, P)) / (2.0 * dT)


def saturation_temperature(h_sat: float, P: float = P_ATM) -> float:
    """Inversa de la curva de saturacion: T tal que h_sat(T) = h.

    Devuelve la temperatura de la superficie humeda a partir de la entalpia de
    saturacion que impone el balance de resistencias del ap. 9.7.6.
    """
    return _invert_monotone(lambda T: saturation_enthalpy(T, P), h_sat,
                            lo=T0 - 60.0, hi=T0 + 80.0)


def wet_bulb_humidity_ratio(T: float, T_wb: float, P: float = P_ATM) -> float:
    """Humedad especifica desde bulbo seco y bulbo humedo (ASHRAE).

    Necesaria porque las condiciones de la tabla 9.20 y de la UNE-EN 14511 se
    declaran en bulbo seco / bulbo humedo (7 C bs / 6 C bh), no en humedad
    relativa.
    """
    w_s = w_saturation(T_wb, P)
    t, t_wb = T - T0, T_wb - T0
    if T_wb >= T0:
        num = (2501e3 - 2326.0 * t_wb) * w_s - 1006.0 * (t - t_wb)
        den = 2501e3 + 1860.0 * t - 4186.0 * t_wb
    else:                                    # bulbo humedo sobre hielo
        num = (2830e3 - 176.0 * t_wb) * w_s - 1006.0 * (t - t_wb)
        den = 2830e3 + 1860.0 * t - 2090.0 * t_wb
    return max(num / den, 0.0)


def wet_bulb(T: float, w: float, P: float = P_ATM) -> float:
    """Temperatura de bulbo humedo [K]. Inversa de `wet_bulb_humidity_ratio`."""
    return _invert_monotone(lambda T_wb: wet_bulb_humidity_ratio(T, T_wb, P), w,
                            lo=T0 - 60.0, hi=T + 1e-6)


# --- Propiedades de transporte --------------------------------------------
def density(T: float, w: float, P: float = P_ATM) -> float:
    """Densidad de la MEZCLA [kg/m3]. Es la que entra en la velocidad masica."""
    v_da = R_DRY_AIR * T * (1.0 + w / MW_RATIO) / P     # m3 / kg aire seco
    return (1.0 + w) / v_da


def cp_moist(w: float) -> float:
    """Calor especifico por kg de aire SECO [J/(kg K)]: cp_a + w cp_v.

    Es el c_p,a que aparece en la ec. 9-29 y en la conversion de la conductancia
    del lado de aire a base entalpica. No es el calor especifico por kg de
    mezcla, que seria este dividido por (1 + w).
    """
    return CP_DRY_AIR + w * CP_VAPOR


def viscosity(T: float) -> float:
    """Viscosidad dinamica del aire [Pa s], ley de Sutherland."""
    return 1.458e-6 * T ** 1.5 / (T + 110.4)


def conductivity(T: float) -> float:
    """Conductividad termica del aire [W/(m K)], ajuste polinomico."""
    return (1.5207e-11 * T ** 3 - 4.8574e-8 * T ** 2
            + 1.0184e-4 * T - 3.9333e-4)


def prandtl(T: float, w: float = 0.0) -> float:
    return viscosity(T) * cp_moist(w) / (1.0 + w) / conductivity(T)


# --- Utilidad --------------------------------------------------------------
def _invert_monotone(f, target: float, lo: float, hi: float,
                     tol: float = 1e-9, it_max: int = 80) -> float:
    """Biseccion sobre una funcion monotona creciente.

    Se emplea biseccion y no Newton porque la curva de saturacion conmuta de
    rama en 0 C: la derivada es discontinua ahi y un Newton puede oscilar
    justamente en el entorno que mas importa, el del dominio de escarcha.
    """
    f_lo, f_hi = f(lo), f(hi)
    if target <= f_lo:
        return lo
    if target >= f_hi:
        return hi
    for _ in range(it_max):
        mid = 0.5 * (lo + hi)
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


# --- Entropia --------------------------------------------------------------
#: Entropia del vapor de agua a 0 C referida al liquido saturado a 0 C
#: [J/(kg K)]: s_fg = h_fg0 / T0.
S_VAPOR_0 = H_FG_0 / T0


def entropy(T: float, w: float, P: float = P_ATM) -> float:
    """Entropia del aire humedo [J/(kg aire SECO K)], mezcla de gases ideales.

        s = cp_a ln(T/T0) - R_a ln(p_a/P_atm)
            + w [ s_v0 + cp_v ln(T/T0) - R_v ln(p_v/p_sat(T0)) ]

    Referencia: aire seco a 0 C y 1 atm, y agua liquida saturada a 0 C.

    POR QUE HACE FALTA. El balance de entropia del ap. 9.4.4 trataba el lado
    de aire del serpentin como si solo hubiese cambio SENSIBLE,
    m cp ln(T_out/T_in). Con la superficie humeda eso deja fuera la entropia
    que se lleva el vapor condensado, que en la condicion nominal de
    calefaccion es un tercio del calor intercambiado: la disminucion de
    entropia del aire sale muy corta y la generacion, que es la suma con la del
    refrigerante, sale muy larga. El error lo delato el cierre del balance
    exergetico del ap. 9.11.2, que daba mas exergia destruida que potencia
    electrica consumida.
    """
    p_v = max(partial_pressure(w, P), 1e-9)
    p_a = max(P - p_v, 1e-9)
    s = CP_DRY_AIR * math.log(T / T0) - R_DRY_AIR * math.log(p_a / P_ATM)
    if w > 0.0:
        s += w * (S_VAPOR_0 + CP_VAPOR * math.log(T / T0)
                  - R_VAPOR * math.log(p_v / p_sat(T0)))
    return s


def entropy_liquid_water(T: float) -> float:
    """Entropia del agua liquida [J/(kg K)], referida al liquido a 0 C."""
    return CP_WATER * math.log(T / T0)
