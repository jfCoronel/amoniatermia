"""Ensayo de estructuras ampliadas del compresor semiempírico (15/10/2026).

DECISIÓN DEL AUTOR (15/10/2026): la admisibilidad de un punto debe depender solo de los
límites del compresor real. Para ello el modelo del compresor tiene que cumplir N1 en toda la
zona sin límites del diagrama del fabricante. Se intenta primero AMPLIAR el modelo
semiempírico; si no basta, se pasa a los polinomios de UNE-EN 12900.

Este script NO cambia el modelo vigente: define una subclase con extensiones activables y
mide cada una sobre el conjunto de identificación ampliado: los 46 puntos del catálogo y los 49
del bloque E de `data/compresor_bock_f2_vap_envolvente.csv` (rejilla de 5 K sobre la zona sin
límites del diagrama, 1450 rpm, 5 K de recalentamiento; generados por el autor el 15/10/2026).

Extensiones (cada una con su motivo físico):

- `mezcla`: la fuga interna vuelve a la aspiración y se MEZCLA con el gas que entra, como en
  Winandy et al. (2002). El cilindro desplaza el caudal útil más la fuga, que se comprime dos
  veces: reduce el caudal, aumenta la potencia por kg útil y sube la temperatura de aspiración
  y de descarga, más cuanto mayor es la relación de presiones. El modelo vigente solo resta la
  fuga del caudal.
- `n`: el exponente de reexpansión del espacio muerto se identifica en lugar de fijarse en 1.30.
- `dp`: pérdida mecánica con un término proporcional a la diferencia de presiones (carga de los
  cojinetes y de los segmentos): W_loss = W_loss0 + alpha·W_in + k_dp·V̇s·(P_ex − P_ad).
- `ic`: rendimiento interno dependiente de la relación de presiones:
  eta_ic = eta_ic0 + b_ic·ln(r_p / 3.7). r_p = 3.7 es la del diseño de M-1 y M-2.

Uso (desde la raíz del repositorio):
    uv run python herramientas/compresor/ensayo_estructura.py muestra [variantes...]
    uv run python herramientas/compresor/ensayo_estructura.py cruzada variante
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
from scipy.optimize import least_squares, root

from amoniatermia import data as D
from amoniatermia.components.compressor import SemiEmpiricalCompressor, IDENTIFIED
from amoniatermia.props import Fluid
from amoniatermia.validation import plan

RP_REF = 3.7
EXTRA = {"n": ("n_reexp", (1.0, 1.6), 1.30),
         "dp": ("k_dp", (0.0, 0.3), 0.0),
         "ic": ("b_ic", (-0.5, 0.5), 0.0)}


class Ampliado(SemiEmpiricalCompressor):
    def __init__(self, flags=(), **kw):
        super().__init__(Fluid("Ammonia"), D.compressor_geometry(), D.compressor_params())
        self.flags = set(flags)
        self.k_dp = 0.0
        self.b_ic = 0.0

    # nombres del vector de ajuste
    def nombres(self):
        out = list(IDENTIFIED)
        for f in ("n", "dp", "ic"):
            if f in self.flags:
                out.append(EXTRA[f][0])
        return out

    def cotas(self):
        lo, hi = [], []
        for k in self.nombres():
            b = self.BOUNDS.get(k) or next(v[1] for v in EXTRA.values() if v[0] == k)
            lo.append(b[0]); hi.append(b[1])
        return lo, hi

    def get(self, k):
        return getattr(self.p, k) if hasattr(self.p, k) else getattr(self, k)

    def set(self, vec):
        for k, v in zip(self.nombres(), vec):
            (setattr(self.p, k, float(v)) if hasattr(self.p, k) else setattr(self, k, float(v)))

    def vector(self):
        return np.array([self.get(k) for k in self.nombres()])

    # ------------------------------------------------------------------
    def _residuals(self, unknowns, P_ad, T_su, P_ex, T_amb):
        T1, T_wall = unknowns
        f, p = self.fluid, self.p
        T_sat_min = f.Tsat(P_ad) + 1e-3
        f.update_PT(P_ad, T_su)
        h_su = f.h
        f.update_PT(P_ad, max(T1, T_sat_min))
        h_su1 = f.h                                   # tras el calentamiento
        rp = P_ex / P_ad
        eta_ic = p.eta_ic + (self.b_ic * np.log(rp / RP_REF) if "ic" in self.flags else 0.0)
        eta_ic = min(max(eta_ic, 0.2), 1.0)
        eta_v = self.eta_v(P_ad, P_ex)

        h_mix, m_leak, choked = h_su1, 0.0, False
        for _ in range(60 if "mezcla" in self.flags else 1):
            f.update_PH(P_ad, h_mix)
            h1, v1, s1 = f.h, f.v, f.s
            m_in = eta_v * self.geom.V_dot_swept / v1
            v_in = v1 / p.r_v
            f.update_DS(1.0 / v_in, s1)
            h_ad_s = f.h
            h_ad = h1 + (h_ad_s - h1) / max(eta_ic, 1e-6)
            f.update_DH(1.0 / v_in, h_ad)
            P_int = f.P
            w_in = (h_ad - h1) + v_in * (P_ex - P_int)
            h2 = h1 + w_in
            m_leak_n, choked = self._leakage(P_ad, P_ex, h2)
            if "mezcla" not in self.flags:
                m_leak = m_leak_n
                break
            m_leak_n = min(m_leak_n, 0.5 * m_in)
            m_util = m_in - m_leak_n
            h_mix_n = (m_util * h_su1 + m_leak_n * h2) / m_in
            if abs(h_mix_n - h_mix) < 1e-6 and abs(m_leak_n - m_leak) < 1e-12:
                h_mix, m_leak = h_mix_n, m_leak_n
                break
            h_mix, m_leak = h_mix_n, m_leak_n

        m_dot = max(m_in - m_leak, 1e-8)
        W_in = (m_in if "mezcla" in self.flags else m_dot) * w_in
        W_loss = p.alpha_l * W_in + p.W_loss0
        if "dp" in self.flags:
            W_loss += self.k_dp * self.geom.V_dot_swept * (P_ex - P_ad)

        scale = (m_dot / max(p.m_dot_n, 1e-9)) ** 0.8
        AU_su, AU_ex = p.AU_su_n * scale, p.AU_ex_n * scale
        Q_su = m_dot * (h_su1 - h_su)
        r1 = Q_su - AU_su * (T_wall - T_su)
        f.update_PH(P_ex, h2)
        T2 = f.T
        Q_ex = AU_ex * (T2 - T_wall)
        Q_amb = p.AU_amb * (T_wall - T_amb)
        r2 = W_loss + Q_ex - Q_su - Q_amb
        # `solve` calcula W_shaft = m_dot*w_in + W_loss: se le pasa el trabajo
        # interno POR KG ÚTIL para que la potencia salga W_in + W_loss.
        cache = dict(m_dot=m_dot, w_in=W_in / m_dot, h1=h1, h2=h2, T2=T2, s1=s1,
                     W_loss=W_loss, Q_su=Q_su, Q_ex=Q_ex, Q_amb=Q_amb, eta_v=eta_v,
                     h_su=h_su, AU_ex=AU_ex, P_int=P_int, m_leak=m_leak, choked=choked,
                     h_ad=h_ad, h_ad_s=h_ad_s)
        return np.array([r1, r2]), cache

    # ------------------------------------------------------------------
    def ajusta(self, puntos, x0, w=(1.0, 1.0, 4.0)):
        def res(vec):
            self.set(vec)
            out = []
            for pt in puntos:
                try:
                    r = self.solve(pt["P_ad"], pt["T_su"], pt["P_ex"], pt.get("T_amb", 298.15))
                except Exception:
                    out += [10.0, 10.0, 10.0]
                    continue
                out += [w[0] * (r.m_dot / pt["m_dot"] - 1), w[1] * (r.W_shaft / pt["W_shaft"] - 1),
                        w[2] * (r.T_dis - pt["T_dis"]) / pt["T_dis"]]
            return np.array(out)
        lo, hi = self.cotas()
        x0 = np.clip(np.asarray(x0, float), lo, hi)
        sol = least_squares(res, x0, bounds=(lo, hi), method="trf")
        self.set(sol.x)
        return sol

    def desviaciones(self, puntos):
        dm, dW, dT = [], [], []
        for pt in puntos:
            r = self.solve(pt["P_ad"], pt["T_su"], pt["P_ex"], pt.get("T_amb", 298.15))
            dm.append(r.m_dot / pt["m_dot"] - 1); dW.append(r.W_shaft / pt["W_shaft"] - 1)
            dT.append(r.T_dis - pt["T_dis"])
        return np.array(dm), np.array(dW), np.array(dT)


# Arranques: los cuatro independientes de la validación cruzada (S2–S5) y el adoptado (S1).
def arranques(c: Ampliado, incluir_S1=True):
    base = {"S2": list(D.compressor_params(variant="original").as_vector()),
            "S3": [5.0, 5.0, 5.0, 1e-7, 0.05, 0.1, 200.0, 2.5, 0.7],
            "S4": [50.0, 20.0, 2.0, 0.0, 0.03, 0.2, 100.0, 3.5, 0.9],
            "S5": [1.0, 2.0, 10.0, 5e-7, 0.10, 0.05, 400.0, 1.5, 0.6]}
    if incluir_S1:
        base["S1"] = list(D.compressor_params().as_vector())
    extra = [EXTRA[f][2] for f in ("n", "dp", "ic") if f in c.flags]
    out = {k: v + extra for k, v in base.items()}
    # arranque con fuga apreciable, para que la mezcla tenga dónde actuar
    if "mezcla" in c.flags:
        out["SF"] = [0.01, 1.2, 1.0, 2e-7, 0.06, 0.0, 300.0, 2.0, 0.85] + extra
    return out


def mejor_ajuste(flags, puntos, incluir_S1=True):
    mejor = None
    for nombre, x0 in arranques(Ampliado(flags), incluir_S1).items():
        c = Ampliado(flags)
        try:
            sol = c.ajusta(puntos, x0)
        except Exception as exc:                       # noqa: BLE001
            print("  arranque", nombre, "falla:", exc, flush=True)
            continue
        if mejor is None or sol.cost < mejor[1]:
            mejor = (nombre, float(sol.cost), c)
    return mejor


def puntos_identificacion():
    cat = [dict(p, fuente="catalogo") for p in D.compressor_catalog()]
    env = [dict(p, fuente="envolvente") for p in
           D.compressor_vap_points(fichero="compresor_bock_f2_vap_envolvente.csv") if p["bloque"] == "E"]
    return cat + env


def resumen(dm, dW, dT):
    return {"caudal_max": float(np.max(np.abs(dm))), "potencia_max": float(np.max(np.abs(dW))),
            "descarga_max_K": float(np.max(np.abs(dT)))}


def muestra(variantes):
    pts = puntos_identificacion()
    u = plan.threshold("N1")
    for v in variantes:
        flags = [] if v == "base" else v.split("+")
        t = time.time()
        nombre, coste, c = mejor_ajuste(flags, pts)
        dm, dW, dT = c.desviaciones(pts)
        s = resumen(dm, dW, dT)
        cat = [i for i, p in enumerate(pts) if p["fuente"] == "catalogo"]
        sc = resumen(dm[cat], dW[cat], dT[cat])
        ok = (s["caudal_max"] <= u["caudal"] and s["potencia_max"] <= u["potencia"]
              and s["descarga_max_K"] <= u["temperatura_descarga_K"])
        print(json.dumps({"variante": v, "arranque": nombre, "coste": round(coste, 5),
                          "todos": {k: round(x, 4) for k, x in s.items()},
                          "catalogo": {k: round(x, 4) for k, x in sc.items()},
                          "N1_en_muestra": ok,
                          "parametros": dict(zip(c.nombres(), map(float, c.vector()))),
                          "s": round(time.time() - t)}, ensure_ascii=False), flush=True)


def cruzada(v):
    """Validación cruzada por grupos de T0, como el ensayo del 29/09/2026: sin el arranque S1,
    que ha visto los puntos. Extremos: −25 y 15 °C."""
    pts = puntos_identificacion()
    u = plan.threshold("N1")
    flags = [] if v == "base" else v.split("+")
    grupo = lambda p: round(p["T0"] - 273.15)          # noqa: E731
    for g in sorted({grupo(p) for p in pts}):
        fuera = [p for p in pts if grupo(p) == g]
        dentro = [p for p in pts if grupo(p) != g]
        nombre, coste, c = mejor_ajuste(flags, dentro, incluir_S1=False)
        s = resumen(*c.desviaciones(fuera))
        ok = (s["caudal_max"] <= u["caudal"] and s["potencia_max"] <= u["potencia"]
              and s["descarga_max_K"] <= u["temperatura_descarga_K"])
        print(json.dumps({"variante": v, "T0_excluida": g, "n": len(fuera), "extremo": g in (-25, 15),
                          **{k: round(x, 4) for k, x in s.items()}, "N1": ok}), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "muestra":
        muestra(sys.argv[2:] or ["base"])
    else:
        cruzada(sys.argv[2])
