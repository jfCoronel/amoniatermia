"""Indicadores energeticos y exergeticos. Apartado 9.11.

QUE ENTRA EN EL DENOMINADOR, Y POR QUE IMPORTA
----------------------------------------------
La potencia que divide es la ELECTRICA absorbida, y comprende el compresor y el
ventilador. El §9.7.7 lo dice sin rodeos: la UNE-EN 14511 exige incluir el
ventilador, «de modo que omitirlo produciria valores de COP y EER no comparables
con los de los equipos comerciales, que es precisamente la comparacion que
sostiene la hipotesis H1». Con 780 W frente a los ~3 kW del compresor, omitirlo
inflaria el EER en torno a un 25 %.

Lo que NO entra, y se declara: las bombas de los circuitos de agua y los
elementos de control. No estan modelados. El §6.8.2 advierte de que omitir la
potencia auxiliar «es una fuente frecuente de sobreestimacion del rendimiento
estacional», de modo que el indicador que este modulo devuelve es una COTA
SUPERIOR mientras las bombas no se incorporen, y `W_el_es_cota_inferior` lo
marca para que la advertencia viaje con el numero.

QUE CUENTA COMO PRODUCTO
------------------------
No se deduce del signo del calor. `ModeSpec.clima` declara si el CIRCUITO de
climatizacion da frio, da calor o no participa: en M-5 el intercambiador de
climatizacion cede calor exactamente igual que en M-4, pero alli lo cede al
circuito de fan-coils —y es el servicio— y aqui lo cede al agua de ACS, porque
en M-5 los dos intercambiadores de placas trabajan para el ACS (tabla 9.3).
Su calor entra por tanto en el producto, pero por la via del ACS y no por la de
climatizacion; contarlo dos veces inflaria el COP.

EL ERROR TERMINOLOGICO QUE EL CAPITULO PIDE NO REPETIR
------------------------------------------------------
El §9.11.2 y el §6.9 lo marcan expresamente: el cociente entre el rendimiento
real y el de Carnot es la EFICIENCIA DE SEGUNDA LEY, no una perdida. La perdida
es su complemento a la unidad. La Rev10 lo llamaba perdida y hay que corregirlo
antes de redactar el cap. 11. `ExergyIndicators` expone las dos magnitudes con
su nombre correcto para que no haya que despejarlo.
"""
from __future__ import annotations

import math

from dataclasses import dataclass, field


class MissingElectricalData(RuntimeError):
    """No se puede formar el denominador: falta la potencia electrica."""


@dataclass(frozen=True)
class EnergyIndicators:
    """Ecuaciones 9-34 y 9-34."""
    servicio: str                     # "frio" | "calor" | "solo_acs"
    W_el: float                       # W, compresor + ventilador
    W_el_compresor: float
    W_fan: float
    Q_util_clima: float               # W, POSITIVO sea frio o calor
    Q_acs: float                      # W
    EER: float | None = None          # solo si el servicio es frio
    COP: float | None = None          # solo si el servicio es calor
    COP_global: float = float("nan")
    W_el_es_cota_inferior: bool = True
    avisos: tuple = ()

    @property
    def por_servicio(self) -> float | None:
        """El indicador que declaran los equipos comerciales, y el unico sobre
        el que el §9.11.1 permite compararse con ellos."""
        return self.EER if self.servicio == "frio" else self.COP

    @property
    def recuperacion_aporta(self) -> float:
        """Cuanto sube el indicador global sobre el de servicio, en tantos por
        uno. Es la magnitud que hace visible el subproducto de M-1."""
        base = self.por_servicio
        if not base:
            return float("nan")
        return self.COP_global / base - 1.0


@dataclass(frozen=True)
class ExergyIndicators:
    """Ecuaciones 9-35 a 9-36."""
    T_0: float                        # K, estado muerto
    E_D: dict = field(default_factory=dict)          # W, por componente
    E_D_total: float = 0.0
    #: Exergia de los productos utiles [W] y cierre del balance exergetico.
    Ex_productos: dict = field(default_factory=dict)
    #: Exergia que sale del sistema sin ser producto ni destruirse: el aire
    #: que expulsa la bateria, por encima o por debajo del estado muerto [W].
    Ex_perdidas: dict = field(default_factory=dict)
    cierre: float = float("nan")      # (W_el - Ex_prod - Ex_perd - E_D) / W_el
    y_D: dict = field(default_factory=dict)          # ec. 9-36
    #: Reparto entre los COMPONENTES DEL CICLO, que es el de H6 (decision del
    #: autor, 29/09/2026): sin el ventilador, que es un auxiliar (sigue en el
    #: denominador de los indicadores y en `y_D`), y con el compresor agrupado
    #: con su motor y su transmision, que es lo que sustituiria un compresor de
    #: velocidad variable.
    y_D_ciclo: dict = field(default_factory=dict)
    componente_mayor_ciclo: str = ""
    #: Separacion del ap. 9.5.2: irreversibilidad propia de la compresion
    #: frente a perdida de conversion electromecanica del motor externo.
    E_D_compresion: float = 0.0
    E_D_electromecanica: float = 0.0
    eta_II: float | None = None       # EFICIENCIA de segunda ley
    COP_Carnot: float | None = None
    T_foco_frio: float = float("nan")
    T_foco_caliente: float = float("nan")
    avisos: tuple = ()

    @property
    def perdida_segunda_ley(self) -> float | None:
        """Complemento a la unidad de `eta_II`. Se expone para que nadie tenga
        que despejarlo: llamar «perdida» al propio eta_II es el error que el
        §9.11.2 pide corregir de la Rev10."""
        return None if self.eta_II is None else 1.0 - self.eta_II

    @property
    def balance_cierra(self) -> bool:
        """El balance exergetico es una VERIFICACION, no un resultado: la
        exergia electrica que entra tiene que salir como producto o destruirse.
        Si no cierra, falta un componente en el reparto —y eso es exactamente
        lo que delata que el lado de baja no esta modelado."""
        return abs(self.cierre) <= 0.02

    @property
    def y_D_compresor(self) -> float:
        """Metrica de contraste de H6 (tabla 6.2): «cociente de destruccion de
        exergia del compresor sobre el total»."""
        return self.y_D.get("compresor", float("nan"))

    @property
    def margen_velocidad_variable(self) -> float:
        """COTA SUPERIOR del margen recuperable con velocidad variable, en W.

        NO es una prediccion, y el §9.11.2 exige declararlo: «la perdida de
        conversion cuantificada aqui es la del motor externo a velocidad fija
        de este modelo; un variador real introduce sus propias perdidas de
        conmutacion y de armonicos, y la eficiencia del motor a velocidad
        parcial no coincide con la nominal». El cap. 11 no debe presentar esta
        cifra integra como margen capturable.
        """
        return self.E_D_electromecanica


def energy(sol, spec) -> EnergyIndicators:
    """Indicadores energeticos de un punto resuelto, ec. 9-34 y 9-34.

    `spec` es el `ModeSpec` del modo, del que se toma el papel del circuito de
    climatizacion. Se pide explicitamente en lugar de deducirlo de la solucion
    porque es informacion del MODO y no del punto.
    """
    comp = sol.components.get("compresor")
    if comp is None or getattr(comp, "W_el", None) is None:
        raise MissingElectricalData(
            "El compresor no declara potencia electrica. La ec. 9-9 la "
            "obtiene de la potencia al eje con eta_motor y eta_transm, que son "
            "datos de `data/compresor_bock_f2.yaml`. Sin ellos no hay "
            "denominador y los indicadores no pueden calcularse.")
    W_el = comp.W_el + sol.W_fan
    avisos = []
    # Un indicador calculado sobre un punto no convergido no es un resultado.
    # El §6.12 exige que los casos de no convergencia «se registren y se
    # reporten, en lugar de ser descartados silenciosamente»: se calculan, pero
    # la marca viaja con el numero.
    if not sol.converged:
        avisos.append(
            f"PUNTO NO CONVERGIDO (residuo {sol.max_residual:.1e}). El "
            "indicador se calcula pero NO es un resultado utilizable.")
    elif not sol.valid:
        fallan = [k for k in ("masa", "energia", "R3_pared_compresor")
                  if sol.checks.get(k, 0.0) > 1e-3]
        avisos.append(
            "El punto converge pero NO pasa las verificaciones independientes "
            f"del §9.4.4 ({', '.join(fallan) or 'ver checks'}). El §9.4.4 "
            "lo marca como no valido.")

    # Convenio de signo: Q_clima es el calor cedido AL AGUA. En frio el agua lo
    # cede y sale negativo, de modo que el producto util es su opuesto.
    #
    # Si el intercambiador del servicio no esta instanciado —la configuracion
    # del ap. 9.7.8, con la evaporacion impuesta y el lado de baja sin
    # modelar— Q_clima sale cero y el producto hay que tomarlo del lado de
    # refrigerante. Es lo que el propio apartado reporta como «potencia
    # frigorifica», pero NO es lo mismo: omite el salto del intercambiador que
    # falta, de modo que sobreestima el servicio. Se declara.
    hay_servicio = abs(sol.Q_clima) > 1e-9
    if spec.clima == "frio":
        servicio = "frio"
        Q_util = -sol.Q_clima if hay_servicio else sol.Q_evap
    elif spec.clima == "calor":
        servicio = "calor"
        Q_util = sol.Q_clima if hay_servicio else 0.0
    else:
        servicio, Q_util = "solo_acs", 0.0
        avisos.append(
            "El circuito de climatizacion NO participa en este modo: los dos "
            "intercambiadores de placas trabajan para el ACS (tabla 9.3), de "
            "modo que todo el calor del lado de alta entra en el numerador por "
            "la via del ACS.")
    if spec.clima in ("frio", "calor") and not hay_servicio:
        avisos.append(
            "El intercambiador del servicio de climatizacion NO esta "
            "instanciado. El producto se toma del lado de refrigerante, que "
            "omite el salto termico del intercambiador ausente y por tanto "
            "SOBREESTIMA el servicio." if servicio == "frio" else
            "El intercambiador del servicio de calefaccion NO esta "
            "instanciado: no hay producto util que contabilizar.")

    if Q_util < 0.0:
        avisos.append(
            f"El servicio de climatizacion declarado ({spec.clima}) no coincide "
            f"con el signo del calor: Q_util sale {Q_util:.0f} W. Revise la "
            "topologia del modo.")

    EER = COP = None
    if servicio == "frio":
        EER = Q_util / W_el
    elif servicio == "calor":
        COP = Q_util / W_el
    return EnergyIndicators(
        servicio=servicio, W_el=W_el, W_el_compresor=comp.W_el,
        W_fan=sol.W_fan, Q_util_clima=Q_util, Q_acs=sol.Q_acs,
        EER=EER, COP=COP, COP_global=(Q_util + sol.Q_acs) / W_el,
        W_el_es_cota_inferior=True,
        avisos=tuple(avisos + [
            "W_el no incluye las bombas de agua ni el control, que no estan "
            "modelados (§6.8.2): el indicador es una COTA SUPERIOR."]))


def exergy(sol, spec, ener: EnergyIndicators | None = None) -> ExergyIndicators:
    """Indicadores exergeticos, ec. 9-35 a 9-36.

    La exergia destruida se obtiene de la generacion de entropia por componente
    que el lazo externo ya calcula como verificacion independiente:
    E_D,k = T_0 S_gen,k, que es la forma de la derecha de la ec. 9-35. No se
    recalcula por el balance de flujos de exergia, y conviene decir por que:
    las dos vias son algebraicamente la misma —teorema de Gouy-Stodola— y la
    de la entropia esta ya verificada como positiva en todos los componentes
    por el §9.4.4, de modo que reimplementarla por la otra via anadiria una
    oportunidad de error sin anadir informacion.
    """
    ener = ener or energy(sol, spec)
    comp = sol.components["compresor"]
    T_0 = sol.boundary.T_amb
    S_gen = sol.checks.get("entropia", {})
    avisos = []

    E_D = {k: T_0 * s for k, s in S_gen.items()}

    # Separacion del ap. 9.5.2. La perdida de conversion electromecanica es
    # trabajo electrico que acaba integramente como calor al ambiente: su
    # exergia se destruye por completo, y es ADICIONAL a la irreversibilidad
    # del proceso de compresion, que es la que el balance de entropia recoge.
    E_D_em = max(comp.W_el - comp.W_shaft, 0.0)
    E_D_compresion = E_D.get("compresor", 0.0)
    E_D["compresor_electromecanico"] = E_D_em
    # El ventilador es tambien conversion electromecanica completa: mueve aire
    # que acaba al ambiente, de modo que toda su exergia se destruye.
    if sol.W_fan:
        E_D["ventilador"] = sol.W_fan

    total = sum(E_D.values())
    y_D = {k: v / total for k, v in E_D.items()} if total > 0 else {}

    # Clasificacion de H6: ver `ExergyIndicators.y_D_ciclo`.
    ciclo = {k: v for k, v in E_D.items()
             if k not in ("ventilador", "compresor", "compresor_electromecanico")}
    ciclo["compresor_con_motor"] = (E_D.get("compresor", 0.0)
                                    + E_D.get("compresor_electromecanico", 0.0))
    total_ciclo = sum(ciclo.values())
    y_D_ciclo = ({k: v / total_ciclo for k, v in ciclo.items()}
                 if total_ciclo > 0 else {})
    mayor = max(y_D_ciclo, key=y_D_ciclo.get) if y_D_ciclo else ""
    if total <= 0.0:
        avisos.append("Destruccion de exergia total nula o negativa: el punto "
                      "no es termodinamicamente admisible.")

    # --- cierre del balance exergetico ------------------------------------
    # Verificacion, no resultado. La exergia que entra es electrica y por tanto
    # exergia pura; tiene que salir como producto util o destruirse. Un cierre
    # que no cierra dice que falta un componente en el reparto de la ec. 9-35.
    bc = sol.boundary
    Ex_prod = {}
    if ener.Q_util_clima and bc.clima is not None:
        T_m = _T_media(bc.clima.T_in, sol.Q_clima,
                       bc.clima.m_dot)
        Ex_prod["clima"] = (ener.Q_util_clima * abs(T_0 / T_m - 1.0)
                            if spec.clima == "frio"
                            else ener.Q_util_clima * (1.0 - T_0 / T_m))
    if sol.Q_acs and bc.acs is not None:
        T_m = _T_media(bc.acs.T_in, sol.Q_acs,
                       sol.unknowns.get("m_acs") or bc.acs.m_dot)
        Ex_prod["acs"] = sol.Q_acs * (1.0 - T_0 / T_m)
    # El ACS puede tener energia y casi ninguna exergia, y conviene decirlo.
    if "acs" in Ex_prod and sol.Q_acs:
        if abs(Ex_prod["acs"]) < 0.05 * abs(sol.Q_acs):
            avisos.append(
                f"La exergia del ACS es {Ex_prod['acs']:.0f} W frente a "
                f"{sol.Q_acs:.0f} W de energia: el producto tiene valor "
                "energetico y practicamente ninguno exergetico. Ocurre cuando "
                "la media logaritmica del agua se acerca al estado muerto —con "
                "ambiente a 35 C y agua de 10 a 60 C, la mitad del "
                "calentamiento esta por DEBAJO del ambiente—. El COP global "
                "sube y el rendimiento de segunda ley no.")

    # PERDIDA POR EL AIRE EXPULSADO (28/09/2026). La bateria devuelve al
    # ambiente aire mas caliente (frio) o mas frio (calor) que el estado muerto:
    # esa corriente sale con exergia, que ni es producto ni se destruye dentro
    # del sistema. Sin ella el balance dejaba en torno a un 2 % de la potencia
    # electrica sin repartir, y el orden antiguo del tren de M-2 lo tapaba por
    # casualidad con la presion que la aspiracion recuperaba gratis. Se evalua
    # como gas ideal con el cp del aire humedo de entrada; la exergia quimica
    # del condensado, que solo aparece en calefaccion, no se incluye.
    Ex_perd = {}
    coil = sol.components.get("bateria")
    if coil is not None and sol.boundary.m_dot_air:
        a = sol.boundary.air
        cp = a.cp * (1.0 + a.w)            # por kg de aire seco, aprox.
        m_seco = sol.boundary.m_dot_air / (1.0 + a.w)

        def ex_termica(T):
            return cp * ((T - T_0) - T_0 * math.log(T / T_0))

        Ex_perd["aire_expulsado"] = m_seco * (ex_termica(coil.T_air_out)
                                              - ex_termica(a.T))

    cierre = ((ener.W_el - sum(Ex_prod.values()) - sum(Ex_perd.values())
               - total) / ener.W_el if ener.W_el else float("nan"))
    if abs(cierre) > 0.02:
        avisos.append(
            f"El balance exergetico NO cierra: queda un {100 * cierre:+.1f} % "
            "de la potencia electrica sin repartir entre producto y "
            "destruccion. Falta algun componente en el reparto de la "
            "ec. 9-35 —tipicamente, un intercambiador no instanciado.")

    # --- eta_II = COP/COP_Carnot, ec. 9-36 -------------------------------
    # Los focos son los RESERVORIOS, no las saturaciones del refrigerante.
    # Es una decision de modelado y se declara: tomar las temperaturas del
    # refrigerante ocultaria dentro del Carnot el salto termico de los
    # intercambiadores, que es precisamente una de las irreversibilidades que
    # el analisis quiere localizar.
    T_c, T_h, eta_II, COP_C = float("nan"), float("nan"), None, None
    bc = sol.boundary
    if spec.clima in ("frio", "calor") and bc.clima is not None:
        m = bc.clima.m_dot
        T_in = bc.clima.T_in
        T_out = T_in
        if m:
            cp = 4180.0
            T_out = T_in + sol.Q_clima / (m * cp)
        T_agua = 0.5 * (T_in + T_out)
        if spec.clima == "frio":
            T_c, T_h = T_agua, bc.air.T
            COP_C = T_c / max(T_h - T_c, 1e-9)
        else:
            T_c, T_h = bc.air.T, T_agua
            COP_C = T_h / max(T_h - T_c, 1e-9)
        base = ener.por_servicio
        if base is not None and COP_C > 0.0:
            eta_II = base / COP_C
        if sol.Q_acs:
            avisos.append(
                "El modo produce ACS ademas del servicio de climatizacion. "
                "eta_II se refiere SOLO al servicio: la forma COP/COP_Carnot "
                "no admite dos productos a temperaturas distintas, y para el "
                "conjunto hay que ir al reparto de exergia destruida.")
    else:
        avisos.append(
            "Sin servicio de climatizacion no hay par de focos con el que "
            "formar el Carnot de la ec. 9-36. eta_II no se calcula; el "
            "reparto de exergia destruida si es interpretable.")

    if eta_II is not None and eta_II > 1.0:
        avisos.append(
            f"eta_II = {eta_II:.3f} > 1: imposible. Revise las temperaturas de "
            "foco y el signo del producto util.")

    return ExergyIndicators(
        T_0=T_0, E_D=E_D, E_D_total=total, y_D=y_D, y_D_ciclo=y_D_ciclo,
        componente_mayor_ciclo=mayor,
        Ex_productos=Ex_prod, Ex_perdidas=Ex_perd, cierre=cierre,
        E_D_compresion=E_D_compresion, E_D_electromecanica=E_D_em,
        eta_II=eta_II, COP_Carnot=COP_C,
        T_foco_frio=T_c, T_foco_caliente=T_h, avisos=tuple(avisos))


def _T_media(T_in: float, Q: float, m: float | None, cp: float = 4180.0):
    """Temperatura media TERMODINAMICA del agua del servicio.

    Es la media LOGARITMICA, no la aritmetica, y aqui si importa. Para una
    corriente de cp constante la exergia es exactamente

        Ex = m cp [(T_out - T_in) - T_0 ln(T_out/T_in)] = Q (1 - T_0/T_lm)

    con T_lm = (T_out - T_in)/ln(T_out/T_in). Con los 5 K de salto del circuito
    de climatizacion la diferencia frente a la aritmetica es de milesimas, pero
    el ACS va de 10 a 60 C y ahi el salto es de 50 K: usar la aritmetica
    introduciria medio kelvin de error justo donde la exergia del producto pasa
    por cero, y el signo del resultado depende de ese medio kelvin.
    """
    import math

    if not m:
        return T_in
    T_out = T_in + Q / (m * cp)
    if abs(T_out - T_in) < 1e-9:
        return T_in
    return (T_out - T_in) / math.log(T_out / T_in)


def report(sol, spec) -> str:
    """Bloque de indicadores de un punto, para el cap. 11."""
    e = energy(sol, spec)
    x = exergy(sol, spec, e)
    L = [f"Indicadores — {spec.name} ({spec.descripcion})", ""]
    L.append(f"  W_el = {e.W_el:.0f} W  (compresor {e.W_el_compresor:.0f} + "
             f"ventilador {e.W_fan:.0f})")
    L.append(f"  Q_util clima = {e.Q_util_clima:.0f} W    Q_ACS = {e.Q_acs:.0f} W")
    if e.EER is not None:
        L.append(f"  EER = {e.EER:.3f}")
    if e.COP is not None:
        L.append(f"  COP = {e.COP:.3f}")
    L.append(f"  COP global = {e.COP_global:.3f}")
    if e.por_servicio:
        L.append(f"  la recuperacion aporta un {100 * e.recuperacion_aporta:+.1f} %")
    L += ["", f"  Exergia destruida (T_0 = {x.T_0 - 273.15:.1f} C): "
              f"{x.E_D_total:.0f} W"]
    for k, v in sorted(x.y_D.items(), key=lambda kv: -kv[1]):
        L.append(f"    {k:<28} {x.E_D[k]:7.0f} W   y_D = {v:.3f}")
    L.append(f"  compresion {x.E_D_compresion:.0f} W frente a "
             f"electromecanico {x.E_D_electromecanica:.0f} W")
    if x.Ex_productos:
        L.append("  exergia de los productos: " + ", ".join(
            f"{k} {v:.0f} W" for k, v in x.Ex_productos.items()))
    L.append(f"  cierre del balance exergetico: {100 * x.cierre:+.1f} %"
             + ("" if x.balance_cierra else "   <-- NO CIERRA"))
    if x.eta_II is not None:
        L.append(f"  eta_II = {x.eta_II:.3f} (COP_Carnot = {x.COP_Carnot:.2f}); "
                 f"perdida de segunda ley = {x.perdida_segunda_ley:.3f}")
    for a in e.avisos + x.avisos:
        L.append(f"  AVISO: {a}")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# H4: presupuesto unico de RS-5 (decision del autor 1 del 01/10/2026)
# ---------------------------------------------------------------------------

#: Equilibrio de refrigeracion del §9.7.8 (tabla 9.19), en SI.
EQUILIBRIO_RS5 = {"modo": "M-2", "T_aire_K": 308.15, "V_frontal": 3.30,
                  "m_aire_kg_s": None, "T_evap_K": 275.15,
                  "recalentamiento_K": 1.0, "subenfriamiento_K": 0.0}


def presupuesto_RS5() -> dict:
    """Presupuesto de carga de RS-5: 50 g/kW sobre la capacidad del EQUILIBRIO
    DE REFRIGERACION que calcula el modelo (cap. 1, H4; §8.5.2, ec. 8-1).

    Es UN numero para la maquina, no uno por modo: sin receptor la carga es
    fija, y cada modo compara la suya con este presupuesto. El equilibrio es el
    del §9.7.8 (tabla 9.19): M-2 con la evaporacion impuesta a 2 °C, aire a
    35 °C, recalentamiento de 1 K y subenfriamiento nulo, el que da los
    9.52 kW y los 476 g del §8.5.2. Se recalcula con el modelo, no se escribe.

    DISCREPANCIA declarada (01/10/2026): el sistema completo en el punto de
    diseno de M-2, con las placas como evaporador, entrega unos 10.2 kW; con esa
    capacidad el presupuesto seria un 7 % mayor. El capitulo debe decir de cual
    de los dos equilibrios se trata; aqui se sigue el texto."""
    from . import campaign as C
    from .circuit import AirState, Boundary, Setpoints

    e = EQUILIBRIO_RS5
    c, _ = C.build_circuit(con_placas=False, con_lineas=False)
    s = c.solve(e["modo"], Boundary(air=AirState(T=e["T_aire_K"], V_frontal=e["V_frontal"]),
                                    m_dot_air=e["m_aire_kg_s"], T_amb=e["T_aire_K"]),
                Setpoints(superheat=e["recalentamiento_K"], subcooling=e["subenfriamiento_K"],
                          T_evap=e["T_evap_K"]))
    if not s.valid:
        raise RuntimeError("El equilibrio de refrigeracion del §9.7.8 no es valido")
    return {"Q_ref_W": float(s.Q_evap), "m_max_kg": 0.050 * float(s.Q_evap) / 1000.0,
            "equilibrio": dict(e), "T_cond_K": float(s.T_cond)}


def fraccion_RS5(sol, presupuesto: dict, sistema: bool = True) -> float:
    """Carga del peor caso de la banda frente al presupuesto UNICO de RS-5."""
    ch = sol.charge_sistema if sistema else sol.charge
    return float(ch["_max"]) / presupuesto["m_max_kg"]


# ---------------------------------------------------------------------------
# H6: margen recuperable en el compresor (decision del autor 4 del 01/10/2026)
# ---------------------------------------------------------------------------

def eta_is_catalogo() -> dict:
    """Rendimiento isoentropico global (sobre la potencia al eje) en los 46
    puntos del catalogo: eta = m (h_is - h_su) / W_eje. El maximo es la
    referencia de la cota tecnica de H6: el mismo compresor en su mejor punto."""
    from .props import Fluid
    from . import data as D

    f = Fluid("Ammonia")
    etas = []
    for p in D.compressor_catalog(fluid=f):
        f.update_PT(p["P_ad"], p["T_su"])
        h_su, s_su = f.h, f.s
        f.update_PS(p["P_ex"], s_su)
        etas.append((p["m_dot"] * (f.h - h_su) / p["W_shaft"], p))
    eta_max, p_max = max(etas, key=lambda t: t[0])
    return {"max": eta_max, "mediana": float(sorted(e for e, _ in etas)[len(etas) // 2]),
            "min": min(e for e, _ in etas), "n": len(etas),
            "punto_max": {"T0_C": p_max["T0"] - 273.15, "Tk_C": p_max["Tc"] - 273.15}}


def margen_compresor(sol, spec, eta_is_ref: float) -> dict:
    """Cotas del margen recuperable sobre la potencia ELECTRICA (H6, OH6).

    - termodinamica: la exergia destruida en el compresor con su motor y su
      transmision. Es el maximo que una compresion reversible podria ahorrar
      (Gouy-Stodola), a igualdad de estados de entrada y salida.
    - tecnica: el mismo compresor con el rendimiento isoentropico `eta_is_ref`
      (el mejor de su catalogo), con el mismo rendimiento electromecanico.

    Las dos son de PRIMER ORDEN: mantienen la capacidad y el ciclo del punto
    resuelto. Una compresion mejor baja la descarga y cambia algo el resto del
    ciclo; ese efecto no se incluye y se declara."""
    e = energy(sol, spec)
    x = exergy(sol, spec, e)
    comp = sol.components["compresor"]
    eta_em = comp.W_shaft / comp.W_el
    util = e.por_servicio or e.COP_global
    Q = util * e.W_el

    def con_ahorro(dW):
        return {"dW_el_W": float(dW), "dW_rel": float(dW / e.W_el),
                "indicador": float(Q / (e.W_el - dW)),
                "d_indicador": float(e.W_el / (e.W_el - dW) - 1.0)}

    termo = con_ahorro(x.E_D.get("compresor", 0.0)
                       + x.E_D.get("compresor_electromecanico", 0.0))
    W_shaft_ref = comp.W_shaft * comp.eta_is / eta_is_ref
    tecnica = con_ahorro(max(comp.W_shaft - W_shaft_ref, 0.0) / eta_em)
    return {"indicador": float(util), "eta_is": float(comp.eta_is),
            "eta_is_ref": float(eta_is_ref), "termodinamica": termo, "tecnica": tecnica}
