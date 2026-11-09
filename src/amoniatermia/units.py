"""Conversion de unidades. USO EXCLUSIVO EN LA FRONTERA DEL MODELO.

Regla del apartado 9.1.2: dentro del modelo todo es SI estricto.
"""
def C2K(t_c): return t_c + 273.15
def K2C(t_k): return t_k - 273.15
def bar2Pa(p): return p * 1.0e5
def Pa2bar(p): return p / 1.0e5
def kW2W(q):  return q * 1.0e3
def W2kW(q):  return q / 1.0e3
def m3h2m3s(v): return v / 3600.0
def m3s2m3h(v): return v * 3600.0
def g2kg(m): return m / 1000.0
def kg2g(m): return m * 1000.0
