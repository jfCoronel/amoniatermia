"""Carga de los ficheros de datos y fallo explícito ante los datos pendientes.

CLAUDE.md, «Datos pendientes»: los `null` de `data/*.yaml` son datos que no
existen todavía. El modelo debe fallar de forma explícita si se invocan, nunca
rellenarlos con un valor plausible.

Estos tests son la evidencia de que la regla se cumple y no solo se declara.
"""
import warnings

import pytest

from amoniatermia import data as D


# ---------------------------------------------------------------------------
# Fallo explícito ante los datos pendientes
# ---------------------------------------------------------------------------

def test_require_falla_ante_un_null():
    df = D.load("bateria_frimetal_cbn21")
    with pytest.raises(D.MissingData, match="PENDIENTE"):
        df.require("pendientes.perdida_carga_conjunto_montado_Pa")


def test_require_falla_ante_una_ruta_inexistente():
    df = D.load("compresor_bock_f2")
    with pytest.raises(D.MissingData, match="no existe"):
        df.require("parametros_identificados.parametro_inventado")


def test_optional_devuelve_none_sin_fallar():
    """Obtener un pendiente sin fallar exige pedirlo expresamente."""
    df = D.load("bateria_frimetal_cbn21")
    assert df.optional("pendientes.ventilador.rendimiento_conjunto") is None
    assert df.optional("pendientes.ventilador.rendimiento_conjunto", 0.30) == 0.30


def test_el_ventilador_es_de_consumo_constante():
    """DECISIÓN DEL AUTOR, 17/09/2026: se renuncia a la curva característica y
    se adopta consumo invariante, tomado del catálogo de la serie CBN: 780 W a
    alta velocidad con el motor en triángulo.

    El equipo lleva UN SOLO ventilador de Ø500, de modo que los 780 W son el
    consumo del equipo y no una cifra por unidad a multiplicar.

    Lo único que sigue pendiente es la pérdida de carga del conjunto montado,
    que hace falta para el efecto de la escarcha sobre el caudal.
    """
    df = D.load("bateria_frimetal_cbn21")
    assert df.require("ventilador.modelo") == "consumo_constante"
    assert df.require("ventilador.potencia_W") == pytest.approx(780.0)
    assert df.require("ventilador.es_cota_inferior") is False
    assert df.require("ventilador.procedencia") == "catalogo_serie_cbn"
    assert df.require("ventilador.n_ventiladores") == 1
    assert df.is_pending("pendientes.perdida_carga_conjunto_montado_Pa")


def test_los_coeficientes_de_placas_siguen_pendientes():
    """§9.6.4: sin φc, φv, C y m el submodelo de placas no cierra."""
    df = D.load("placas_alfanova")
    for k in ("phi_c", "phi_v", "C_monofasico", "m_monofasico"):
        assert df.is_pending(f"pendientes.{k}")


def test_pending_report_enumera_todos_los_pendientes():
    rep = D.pending_report()
    assert set(rep) == set(D.available())
    todos = [r for rutas in rep.values() for r in rutas]
    assert "pendientes.perdida_carga_conjunto_montado_Pa" in todos
    # El compresor no tiene datos pendientes: los rendimientos
    # electromecánicos se adoptaron el 16/09/2026 y la temperatura de descarga
    # admisible, 140 °C del §7.7.1, el 29/09/2026 (decisión del autor).
    assert rep["compresor_bock_f2"] == []


# ---------------------------------------------------------------------------
# Constructores
# ---------------------------------------------------------------------------

def test_r_v_es_parametro_identificado_y_no_geometria():
    """r_v es uno de los nueve parámetros identificados (§9.5.3), no un dato
    de geometría. La geometría llevaba un campo `r_v = 2.0` del juego antiguo
    que nadie leía; se retiró el 25/09/2026. El compresor emplea el del juego
    de parámetros: 1.99134 en el adoptado el 24/09/2026."""
    g = D.compressor_geometry()
    assert not hasattr(g, "r_v")
    assert g.n_rpm == 1450
    assert D.compressor_params().r_v == pytest.approx(1.99134)


def test_volumen_barrido_coincide_con_la_geometria_declarada():
    """§9.5.3: 2 cilindros, alesaje 45 mm, carrera 38 mm."""
    import math
    df = D.load("compresor_bock_f2")
    g = df.require("geometria")
    vd = (g["n_cilindros"] * math.pi / 4
          * g["diametro_cilindro_m"] ** 2 * g["carrera_m"])
    assert abs(vd - g["volumen_barrido_m3_rev"]) / vd < 0.005
    # 10.52 m³/h a 1450 rpm
    assert abs(vd * 1450 / 60 * 3600 - 10.52) / 10.52 < 0.02


def test_los_parametros_del_capitulo_siguen_disponibles():
    """Juego anterior, antigua tabla 10.4. Ya no es el de por defecto, pero se
    conserva para reproducir los resultados previos, como declara el §9.5.3."""
    p = D.compressor_params(variant="original")
    assert p.AU_su_n == pytest.approx(110.7)
    assert p.AU_ex_n == pytest.approx(1.00)
    assert p.AU_amb == pytest.approx(1.07)
    assert p.A_leak == pytest.approx(1.73e-7)
    assert p.C == pytest.approx(0.0386)
    assert p.alpha_l == pytest.approx(0.0)
    assert p.W_loss0 == pytest.approx(12.2)
    assert p.r_v == pytest.approx(2.0)
    assert p.eta_ic == pytest.approx(0.613)


def test_el_juego_por_defecto_es_la_reidentificacion():
    """DECISIÓN DEL AUTOR, 16/09/2026. El capítulo manda sobre el código, así
    que un cambio como este queda fechado en el fichero de datos, aquí y en
    docs/historico/PLAN_PUESTA_EN_MARCHA.md §6. La reescritura del capítulo se abordará
    con un informe propio cuando el modelo esté completo."""
    p = D.compressor_params()
    # juego adoptado el 24/09/2026, reidentificado con el compresor corregido
    # (bloque `reidentificacion_2026_09_24`); sustituye a la tabla 10.8 de la v30
    assert p.AU_su_n == pytest.approx(0.0010002, rel=1e-3)
    assert p.AU_ex_n == pytest.approx(1.13865, rel=1e-4)
    assert p.AU_amb == pytest.approx(1.00006, rel=1e-5)
    assert p.C == pytest.approx(0.088060, rel=1e-4)
    assert p.W_loss0 == pytest.approx(461.14, rel=1e-4)
    assert p.r_v == pytest.approx(1.99134)
    assert p.eta_ic == pytest.approx(0.89803)
    assert len(p.as_vector()) == 9
    # y el de la v30 sigue accesible para reproducir las cifras publicadas
    v30 = D.compressor_params(variant="reidentificacion_2026_09_16")
    assert v30.r_v == pytest.approx(1.9653)
    assert v30.eta_ic == pytest.approx(0.8075)


def test_los_parametros_no_identificables_valen_cero_exacto():
    """A_leak y α no los determinan los datos de catálogo: el jacobiano escalado
    da sensibilidades de 3e-14 y 3e-7. Ambos convergen a cero, y fijarlos a cero
    exacto no altera el ajuste en ninguna cifra significativa.

    La antigua tabla 10.4 publica A_leak = 1.73e-7 m² como si estuviese identificado.
    Escribirlo como cero es más honesto que arrastrar un número que los datos no
    sostienen.
    """
    p = D.compressor_params()
    assert p.A_leak == 0.0
    assert p.alpha_l == 0.0
    df = D.load("compresor_bock_f2")
    assert set(df.require("identificabilidad.no_identificables")) == {"alpha",
                                                                      "A_leak"}


def test_los_rendimientos_electromecanicos_son_adoptados_no_medidos():
    """ADOPTADOS por decisión del autor: 0.90 (motor, reestimado el 01/10/2026;
    antes 0.97) y 0.98 (transmisión). No proceden de una ficha de fabricante.

    El fichero lo declara así con `procedencia: adoptado_sin_fuente`, y ese
    marcado es lo que impide que un valor de trabajo pase por dato medido al
    llegar al capítulo 11. Entran en el denominador de COP y EER por
    UNE-EN 14511, luego en H1, y su separación es lo que da contenido a H6.
    """
    p = D.compressor_params()
    assert p.eta_motor == pytest.approx(0.90)
    assert p.eta_transm == pytest.approx(0.98)
    assert p.eta_electromechanical == pytest.approx(0.882, rel=1e-3)

    df = D.load("compresor_bock_f2")
    assert df.require("transmision.procedencia") == "adoptado_sin_fuente"
    assert df.require("transmision.sensibilidad_6_11") is True


def test_el_efecto_de_los_rendimientos_sobre_el_denominador_es_material():
    """Documenta la magnitud de la hipótesis, para que no se pierda de vista.

    El producto adoptado (0.882, 01/10/2026) es el de un motor IE4 de 2.2-3 kW
    con una buena transmisión. El extremo bajo del rango de incertidumbre, 0.82
    (motor IE3 y correa de 0.95), sube la potencia eléctrica un 7.6 %.
    """
    from amoniatermia import Fluid
    from amoniatermia.components.compressor import SemiEmpiricalCompressor

    f = Fluid("Ammonia")
    c = SemiEmpiricalCompressor(f, D.compressor_geometry(), D.compressor_params())
    P0, Pk = f.Psat(275.15), f.Psat(46.8 + 273.15)
    W_adoptado = c.solve(P0, 276.15, Pk).W_el

    c.p.eta_motor, c.p.eta_transm = 0.82 / 0.95, 0.95   # extremo bajo del rango
    W_bajo = c.solve(P0, 276.15, Pk).W_el

    assert W_bajo / W_adoptado == pytest.approx(0.882 / 0.82, rel=1e-6)


def test_las_dos_variantes_de_parametros_estan_disponibles():
    """La reidentificación es el juego adoptado (tabla 9.8); el anterior se
    conserva accesible para reproducir los resultados previos (§9.5.3)."""
    cap = D.compressor_params(variant="original")
    rei = D.compressor_params(variant="reidentificacion")
    assert cap.AU_su_n == pytest.approx(110.7)
    assert rei.AU_su_n < 1.0          # ~0, coherente con el §9.5.2
    with pytest.raises(ValueError, match="original"):
        D.compressor_params(variant="inventada")


def test_exponente_politropico_procede_del_fichero():
    """Discrepancia D11: el fichero de datos da 1.30 y el valor por defecto del
    dataclass es 1.20. El capítulo no lo declara en ninguna parte."""
    assert D.compressor_params().n_reexp == pytest.approx(1.30)


# ---------------------------------------------------------------------------
# §9.5.3 — los 46 puntos de catálogo
# ---------------------------------------------------------------------------

def test_el_catalogo_tiene_los_46_puntos_del_dominio_declarado():
    """§9.5.3: 46 puntos a 1450 rpm, T₀ 0–5 °C, T_k 15–50 °C. Sin ellos la
    identificación no es reproducible, que es lo que prometen el §6.12 y el
    anexo E."""
    pts = D.compressor_catalog()
    assert len(pts) == 46
    T0 = [p["T0"] - 273.15 for p in pts]
    Tc = [p["Tc"] - 273.15 for p in pts]
    assert min(T0) == pytest.approx(0) and max(T0) == pytest.approx(5)
    assert min(Tc) == pytest.approx(15) and max(Tc) == pytest.approx(50)
    assert len(D.compressor_catalog(restricted=True)) == 36


def test_el_punto_de_referencia_del_fabricante():
    """§9.5.3: «270.9 kJ/kg a T₀ = 0 °C, T_k = 45 °C».

    Es el salto entálpico REAL h_dis − h_asp que se deduce de la temperatura de
    descarga publicada, y reproducirlo verifica de paso que la deducción del
    caudal a partir de la capacidad es la correcta.
    """
    from amoniatermia import Fluid

    f = Fluid("Ammonia")
    ref = [p for p in D.compressor_catalog()
           if abs(p["T0"] - 273.15) < 0.01 and abs(p["Tc"] - 318.15) < 0.01][0]
    f.update_PT(ref["P_ad"], ref["T_su"])
    h_su = f.h
    f.update_PT(ref["P_ex"], ref["T_dis"])
    assert (f.h - h_su) / 1e3 == pytest.approx(270.9, rel=0.01)


def test_el_catalogo_publica_potencia_al_eje():
    """Compresor ABIERTO: lo que el fabricante publica es potencia al eje.
    Confundirla con la eléctrica trasladaría el rendimiento del motor a los
    parámetros de la máquina, que es la separación que el §9.5.2 exige."""
    pts = D.compressor_catalog()
    assert all("W_shaft" in p and "W_el" not in p for p in pts)
    assert 1.3e3 < min(p["W_shaft"] for p in pts) < 3.0e3


@pytest.mark.parametrize("unidad", ["condensador_climatizacion",
                                    "desrecalentador_acs"])
def test_la_geometria_de_placas_ya_no_falla_por_datos_pendientes(unidad):
    """D12 CERRADA el 18/09/2026. Este test comprobaba lo contrario: que
    `plate_geometry` fallase por falta del ángulo de corrugación y del factor de
    alargamiento, que era el comportamiento correcto mientras no existiesen.

    El ángulo está ahora IDENTIFICADO sobre la pérdida de carga del punto de
    selección del 27-30H y el paso entre placas es dato de catálogo. Los modos
    con placas dejan de ser exploratorios.

    Lo que el test conserva es la exigencia de procedencia: un ángulo
    identificado no es un ángulo de catálogo, y el fichero debe decirlo.
    """
    g = D.plate_geometry(unidad)
    assert g.beta_c > 0.0 and g.phi > 0.0 and g.b > 0.0
    proc = D.load("placas_alfanova").require(
        f"unidades.{unidad}.geometria.angulo_procedencia")
    assert proc.startswith(("IDENTIFICADO", "ADOPTADO"))


def test_la_geometria_de_placas_admite_inyeccion_declarada():
    """Se puede explorar con otro valor, dejando constancia de que no procede de
    los datos. Es la vía de la sensibilidad del ap. 6.11."""
    import math
    g = D.plate_geometry("desrecalentador_acs",
                         beta_c=math.radians(60.0), t_p=0.0004)
    assert g.n_plates == 10
    # 1.72 mm = 2.06 de paso de catálogo menos 0.34 de espesor. El 2.09 mm
    # anterior excedía el paso del paquete, que es imposible.
    assert g.b == pytest.approx(0.00172)     # catálogo AlfaNova 16, 18/09/2026
    assert g.phi == pytest.approx(1.15)      # §9.6.2, ESTIMADO
    assert g.provenance["inyectados"] == ["beta_c", "t_p"]


def test_unidad_inexistente_da_un_mensaje_util():
    with pytest.raises(D.MissingData, match="Disponibles"):
        D.plate_geometry("no_existe")


# ---------------------------------------------------------------------------
# Documentación del fabricante aportada el 18/09/2026
# ---------------------------------------------------------------------------

def test_el_paso_de_catalogo_verifica_el_plano_de_la_unidad():
    """La cota A de la gama AlfaNova crece un paso fijo por placa. Para el
    AlfaNova 27, A = 11 + 2.42·n mm; el plano del 27-30H la da en 83.6 mm con
    30 placas, y 11 + 2.42·30 = 83.6 exactamente.

    Es lo que convierte el paso de suposición en dato: no se deduce del volumen
    por canal —que incluye los puertos— sino de una dimensión medida.
    """
    from amoniatermia import data as D

    df = D.load("placas_alfanova")
    p = df.require("unidades.condensador_climatizacion.geometria."
                   "paso_placas_catalogo_m")
    n = df.require("unidades.condensador_climatizacion.geometria.n_placas")
    A = df.require("unidades.condensador_climatizacion.dimensiones_m."
                   "largo_paquete")
    assert abs((0.011 + p * n) - A) < 1e-4


@pytest.mark.parametrize("unidad", ["condensador_climatizacion",
                                    "desrecalentador_acs"])
def test_el_hueco_de_canal_no_puede_exceder_el_paso_del_paquete(unidad):
    """La comprobación que descalifica el valor anterior del 16-10H.

    Entre dos placas contiguas hay el paso menos el espesor de una placa. Un
    hueco mayor que el paso es geométricamente imposible, y 2.09 mm frente a un
    paso de 2.06 lo era.
    """
    from amoniatermia import data as D

    g = D.load("placas_alfanova").require(f"unidades.{unidad}.geometria")
    assert g["paso_entre_placas_m"] < g["paso_placas_catalogo_m"]
    t = g["paso_placas_catalogo_m"] - g["paso_entre_placas_m"]
    assert 0.0003 < t < 0.0005            # espesor de placa plausible


@pytest.mark.parametrize("unidad,masa,ancho,alto", [
    ("condensador_climatizacion", 0.13, 0.111, 0.310),
    ("desrecalentador_acs", 0.05, 0.074, 0.210),
])
def test_el_peso_de_catalogo_acota_el_espesor_de_placa(unidad, masa, ancho,
                                                       alto):
    """El catálogo no publica el espesor, pero sí el peso por placa. Con la
    densidad del inoxidable, eso fija el PRODUCTO Φ·t, no t por separado: es una
    ecuación entre las dos incógnitas, no un valor.

    Lo útil es que Φ solo puede moverse en una banda estrecha, de modo que t
    queda acotado a ±5 % y el hueco de canal b = paso − t, que es lo que entra
    en D_h y en la sección de paso, queda determinado a ±1 %.
    """
    from amoniatermia import data as D

    g = D.load("placas_alfanova").require(f"unidades.{unidad}.geometria")
    phi_t = masa / 7900.0 / (ancho * alto)
    assert abs(phi_t - g["phi_por_espesor_m"]) / phi_t < 0.02
    b = [g["paso_placas_catalogo_m"] - phi_t / phi for phi in (1.15, 1.25)]
    assert (max(b) - min(b)) / min(b) < 0.02          # b es insensible a Φ
    assert min(b) <= g["paso_entre_placas_m"] <= max(b)


def test_el_punto_de_seleccion_del_27_30H_separa_el_ensuciamiento():
    """El U de servicio que da la ficha, Q/(A·MTD), lleva dentro la resistencia
    de ensuciamiento que ella misma declara. Separarlos da el U limpio, que es
    el que el modelo debe reproducir.

    La comprobación de que el reparto es el correcto es independiente: el margen
    que ese U limpio implica sale 125 % frente al 122 % declarado.
    """
    from amoniatermia import data as D

    df = D.load("placas_alfanova")
    pd_ = df.require("unidades.condensador_climatizacion.punto_diseno")
    A = df.require("unidades.condensador_climatizacion.area_m2")
    anc = df.require("unidades.condensador_climatizacion.anclaje")
    R_f = df.require("unidades.condensador_climatizacion.geometria."
                     "resistencia_ensuciamiento_m2K_W")

    U_serv = pd_["Q_W"] / (A * pd_["MTD_K"])
    U_limpio = 1.0 / (1.0 / U_serv - R_f)
    assert abs(U_serv - anc["U_servicio_W_m2K"]) / U_serv < 0.01
    assert abs(U_limpio - anc["U_limpio_W_m2K"]) / U_limpio < 0.01

    margen = U_limpio * A / (pd_["Q_W"] / pd_["MTD_K"]) - 1.0
    assert abs(margen - pd_["margen_declarado"]) < 0.05
    # y el balance del lado de agua cierra la capacidad declarada
    Q_agua = pd_["agua_caudal_m3_h"] * 990.0 / 3600.0 * 4180.0 * (
        pd_["agua_T_out_C"] - pd_["agua_T_in_C"])
    assert abs(Q_agua - pd_["Q_W"]) / pd_["Q_W"] < 0.02


def test_el_angulo_no_lo_publica_el_fabricante_sino_que_se_identifica():
    """Distinción que no puede perderse: la documentación aportada NO trae el
    ángulo de corrugación. Lo que trae es la designación de canal, «1*14H /
    1*15H», que dice que las dos corrientes van por canales H y descarta la
    placa L y los paquetes mixtos; acota, no fija.

    El valor que el fichero lleva está IDENTIFICADO sobre la pérdida de carga
    del punto de selección, no leído de un catálogo, y su procedencia debe
    decirlo. Ver `tests/test_anclaje_placas.py`.
    """
    from amoniatermia import data as D

    df = D.load("placas_alfanova")
    g = df.require("unidades.condensador_climatizacion.geometria")
    assert g["angulo_procedencia"] == "IDENTIFICADO_sobre_perdida_de_carga"
    assert "H" in g["nomenclatura_H"]
    # el del desrecalentador ni siquiera está identificado: se traslada
    assert df.require("unidades.desrecalentador_acs.geometria."
                      "angulo_procedencia") == "ADOPTADO_del_27_30H"
    # y el factor de alargamiento sigue siendo una ESTIMACIÓN
    assert df.require("producto_phi_c_phi_v.phi_adoptado") == 1.15


def test_lo_que_la_documentacion_no_cierra_sigue_sin_cerrar():
    """φc y φv por separado, y C y m de la correlación provisional."""
    from amoniatermia import data as D

    df = D.load("placas_alfanova")
    for clave in ("phi_c", "phi_v", "C_monofasico", "m_monofasico"):
        with pytest.raises(D.MissingData):
            df.require(f"pendientes.{clave}")


def test_ningun_numero_de_los_ficheros_se_lee_como_texto():
    """YAML 1.1 exige signo en el exponente: `3.0e6` es una CADENA y `3.0e+6` un
    número. Cinco presiones y capacidades del fichero de placas y tres del
    compresor se estaban leyendo como texto.

    Es el fallo que el §9.12.4 describe: no rompe nada al cargar, rompe al
    primer cálculo que las use, y hasta entonces el dato parece estar.
    """
    import pathlib

    import yaml

    malos = []

    def recorre(obj, ruta):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recorre(v, f"{ruta}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                recorre(v, f"{ruta}[{i}]")
        elif isinstance(obj, str):
            try:
                float(obj.strip())
            except ValueError:
                return
            malos.append(ruta)

    for f in sorted(pathlib.Path(__file__).parent.parent.glob("data/*.yaml")):
        recorre(yaml.safe_load(f.read_text(encoding="utf-8")), f.name)
    assert not malos, f"números leídos como texto: {malos}"
