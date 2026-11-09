# Plan: compresor F2 por polinomios de UNE-EN 12900

15/10/2026. Decisión y motivo en `DECISIONES_2026_10_15.md`. Primero el modelo y todas las
simulaciones; después la tesis, a partir de una tabla de cambios de cifras.

## Estado de partida

- Datos: `data/compresor_bock_f2_vap_velocidades.csv` (57 puntos × 960, 1100, 1250 y 1450 rpm,
  5 K de recalentamiento) y `compresor_bock_f2_vap_envolvente.csv` (los de 1450 rpm).
- Componente escrito, sin conectar: `src/amoniatermia/components/compressor_en12900.py`.
- Comprobación hecha (`herramientas/compresor/polinomios_en12900.py`): ajuste ≤ 0.8 % en caudal y
  potencia y ≤ 1.7 K en descarga a cada velocidad; la velocidad omitida se predice con el mismo
  error; la regla del recalentamiento reproduce los 46 puntos del catálogo (1 K) con 0.55 %, 0.40 %
  y 1.37 K. Todo dentro de N1 con amplio margen.
- Cambio esperado: en el diseño de M-2 (2/46.8 °C, 5 K) la descarga pasa de 125.5 a 133.3 °C.
  Cambiarán la capacidad (9.52 kW), las descargas, la admisibilidad y todos los indicadores.

## Decisiones del autor (antes de empezar)

| # | Asunto | Opciones | Recomendación |
|---|---|---|---|
| P1 | El semiempírico en la tesis | (a) se retira; (b) se resume en el §9.5 como alternativa ensayada y descartada, con la tabla del ensayo; (c) a un anexo | **(b)**: justifica el cambio y el ensayo ya está hecho |
| P2 | Compresores de R-290 y R-32 (cap. 13, H5) | (a) polinomios también; (b) siguen semiempíricos | **(a) en caudal y potencia**, para que H5 compare con el mismo tipo de modelo. El R-290 tiene 53 puntos con descarga (38 dentro de su envolvente) a una velocidad: basta. El R-32 tiene 86 puntos SIN descarga: o el autor la saca de Select 8, o su descarga se declara con el semiempírico actual |
| P3 | Factor del compresor en la incertidumbre (C10-8) | (a) banda del error de ajuste de los polinomios; (b) se retira | **(a)**, declarando que la incertidumbre propia de los datos del fabricante no se conoce |
| P4 | Velocidad variable | (a) solo se habilita en el modelo; (b) se usa en el estacional para modular capacidad | **DECIDIDO (b)** por el autor (15/10/2026). Detalle en «Velocidad variable en el estacional» |
| P5 | Puntos fuera del diagrama (M-5, M-4 con aire frío) | (a) se calculan extrapolando el polinomio y se marcan; (b) no se calculan | **(a)**, marcados como no admisibles y extrapolados, como hoy |

## Velocidad variable en el estacional (decisión P4 del autor)

Método de UNE-EN 14825 para equipos de capacidad variable. En cada punto de carga parcial (A a D
y los de la TOL y la Tbiv):

1. Si la capacidad a 1450 rpm no cubre la carga: plena velocidad y apoyo eléctrico (como hoy).
2. Si la cubre y la de la velocidad mínima no la supera: se busca la velocidad cuya capacidad
   iguala la carga (secante sobre la velocidad, con el sistema completo resuelto en cada paso).
   Sin ciclos: COPbin = COP a esa velocidad.
3. Si la capacidad a la velocidad mínima supera la carga: velocidad mínima y marcha/paro con
   Cd = 0.9 sobre la relación de capacidad a esa velocidad.

Pdesignh sigue saliendo de la capacidad a plena velocidad en la Tbiv (= TOL). Lo mismo en
refrigeración para el SEER (A a D).

Cuestiones abiertas, con recomendación:

| # | Asunto | Recomendación |
|---|---|---|
| V1 | Velocidad mínima | **960 rpm**, la del fichero del compresor y el límite inferior de los datos de VAP. No se extrapola por debajo |
| V2 | Motor y variador a velocidad reducida | **η_motor·η_trans constante (0.882)** y pérdida del variador declarada como nula, con sensibilidad (p. ej. −3 puntos de η a 960 rpm). No hay dato del motor a carga parcial |
| V3 | Ventilador | **Caudal y consumo constantes** (7600 m³/h, 780 W): son los únicos datos que existen. Declarado como conservador frente al mercado, que modula el ventilador |
| V4 | Comparación de H5 (cap. 13) | **H5 a velocidad fija para los tres fluidos**, en igualdad de condiciones, y el R-717 con velocidad variable como resultado propio y en la referencia de mercado (equipos con inversor). Alternativa: los tres a velocidad variable, lo que exige datos nuevos del R-290 (VAP a varias velocidades) y otro compresor de R-32 (el ZE49KME es de velocidad fija) |
| V5 | ACS recuperada en el balance anual | La fracción en marcha pasa a ser la de la velocidad elegida: con modulación el compresor funciona todo el intervalo, a menor caudal. **Se resuelve M-1 y M-3 a la velocidad de cada intervalo** (no con los mapas a 1450 rpm) |

## Fase A. Modelo (código y pruebas)

1. **Datos.** Bloque `modelo_en12900` en `data/compresor_bock_f2.yaml`: fichero de puntos,
   recalentamiento de referencia, velocidades, grado de la interpolación. Los coeficientes se
   ajustan al cargar (trazables al CSV) y se escriben en un bloque informativo para las tablas de
   la tesis. `data.compressor_en12900()` construye el compresor.
2. **Circuito.** `campaign.build_circuit` usa el compresor por polinomios por defecto, y el
   semiempírico queda seleccionable por nombre para reproducir cifras anteriores.
3. **Envolvente y dominio.** `envelope.dominio_identificacion` y `validation.domain` se simplifican:
   el dominio de validez del compresor pasa a ser la propia envolvente (zona sin límites, 960–1450
   rpm, recalentamiento de 1 a 10 K). Desaparecen las clases interpolado / extremo / validado_VAP.
4. **Validación N1.** Módulo `validation.compressor_en12900` con las comprobaciones de la hoja de
   arriba (sustituye a `compressor_cv` y `compressor_vap` como fuente de N1; estos se conservan
   para documentar el descarte).
5. **Incertidumbre.** Factor del compresor según P3.
6. **Capítulo 13.** Según P2: polinomios del R-290 y del R-32 con su recalentamiento de referencia.
7. **Estacional con velocidad variable.** `seasonal`: velocidad como variable del punto
   (`Evaluador.a_carga`, secante sobre las rpm), los tres casos de arriba, SCOP y SEER con la
   velocidad de cada punto publicada, y el ACS anual según V5. La marcha/paro a 1450 rpm se
   conserva como variante para comparar.
8. **Pruebas.** Unitarias del componente nuevo (ajuste, regla del recalentamiento, interpolación,
   interfaz). `test_referencia.py` y las demás con cifras se actualizan tras la fase B, cada valor
   que cambie anotado con su motivo (§6.12). La suite entera debe pasar.

Estimación: un día de trabajo (medio para el estacional).

## Fase B. Simulaciones (en orden; cada cuaderno escribe su hoja de cifras)

| Cuaderno | Contenido | Tiempo de cálculo |
|---|---|---|
| 02 | Figura 9.3: ajuste del compresor → paridad de los polinomios | minutos |
| 03 | Cifras del cap. 9 (equilibrio de M-2, capacidad, carga, RS-5) | minutos |
| 04 | Ejemplo resuelto de M-1 | minutos |
| 05 | Cap. 10: N1 nueva, malla, intercambiadores, bandas, dominio, incertidumbre | ~1 h |
| 06 | Cap. 11: campaña factorial (594 nudos), H2, H3, H4, H6 | 1–3 h |
| 07 | Cap. 12: estacional con velocidad variable y, para comparar, a velocidad fija | 2–3 h |
| 09 y 10 | Cap. 13: identificación según P2, igualación, estacional de los tres fluidos | ~1.5 h |

Las campañas largas se lanzan en paralelo cuando no dependen entre sí (06, 07 y 10 dependen solo
del modelo). Total: medio día de cálculo.

## Fase C. Tabla de cambios

`docs/CAMBIOS_COMPRESOR_EN12900.md`: cifra anterior y nueva de todo lo que la tesis publica
(capacidad, descarga, EER y COP de diseño, carga y RS-5, nudos admisibles por modo, SEER, SCOP,
TOL, TEWI, márgenes de H3) y, sobre todo, **el veredicto de cada hipótesis H1–H7 antes y
después**. Si algún veredicto cambia, se revisa con el autor antes de redactar.

También se actualizan `CLAUDE.md` (capacidad, presupuesto de carga, compresor),
`docs/ESTADO_DEL_TRABAJO.md` y la memoria.

## Fase D. Tesis (V20 y siguientes, sobre la última versión del disco)

1. **Cap. 9.** §9.5 reescrito: polinomios, rendimientos, regla del recalentamiento, interpolación
   en la velocidad, ecuaciones y tabla de coeficientes; el semiempírico según P1. Fuera las tablas
   de identificación e identificabilidad del semiempírico. Figura 9.3 nueva. Todas las cifras del
   capítulo y del ejemplo de M-1; §9.13 (limitaciones) y tabla 9.23 (módulos).
2. **Cap. 10.** N1 con la validación nueva; dominio de validez = envolvente; incertidumbre;
   recuento de pruebas.
3. **Caps. 11, 12 y 13.** Cifras, tablas y figuras desde las hojas regeneradas; veredictos.
4. **Caps. 1, 6, 7, 8, 14 y 15 y resumen.** Donde citen el compresor semiempírico, su dominio o
   las cifras que cambien (tablas 1.2 y 1.4 si cambia algún veredicto; §7.7.1 y la descarga de
   diseño).
5. Cada cambio en un script `herramientas/tesis/vN.py`, verificado sobre el docx generado.

## Puntos de control con el autor

1. Decisiones P1–P5 (tomadas el 15/10/2026; P4 cambiada a velocidad variable) y V1–V5.
2. Tabla de cambios y veredictos (al terminar la fase C).
3. Texto nuevo del §9.5 (antes de propagar al resto de capítulos).

Conviene un commit de lo que hay ahora antes de empezar, para poder comparar con el estado
anterior.

## Estado de la fase A (15/10/2026)

Hecho:

- `components/compressor_en12900.py`: `EN12900Compressor` con factores de ajuste (incertidumbre),
  descarga externa (R-32), cilindrada de los datos (`volumen_barrido_datos_m3_rev`: escalar la
  cilindrada en la igualación del cap. 13 escala caudal y potencia con los mismos rendimientos)
  y velocidad acotada a los nudos (`fija_velocidad`, `VelocidadFueraDeRango`).
- `data`: bloque `modelo_compresor` / `modelo_en12900` en los tres ficheros de compresor;
  `compressor_model`, `compressor_en12900_points`, `compressor_en12900`, `compressor` (fábrica
  según el modelo declarado); `compressor_vap_points(fichero=...)`.
- `campaign.build_circuit(modelo_compresor=...)`: por defecto el del fichero; "semiempirico"
  reproduce las cifras anteriores. La procedencia de cada punto lleva modelo y velocidad.
- `envelope.dominio_compresor` y `validation.domain`: con polinomios, dominio = zonas del diagrama
  con datos, 960–1450 rpm, recalentamiento de 1 a 10 K. Clases `dentro_del_dominio` /
  `fuera_del_dominio`.
- `validation.compressor_en12900`: N1 del compresor (ajuste, velocidad omitida y puntos del
  29/09, regla del recalentamiento). Cumple con 0.79 % / 0.83 % / 1.65 K en el peor caso.
- `uncertainty`: factor del compresor = extremos `banda_desfavorable` / `banda_favorable` de esa
  banda, por sustitución en `modelo_en12900.ajuste` del compresor de cada fluido.
- `seasonal`: `Evaluador` con velocidad (`resolver(..., rpm)`, `a_carga`), `scop_equipo` y
  `seer_equipo` con `velocidad="variable"` por defecto (guardan también el resultado a velocidad
  fija), `acs_puntos` (M-3 y M-1 a la velocidad de cada punto) y `acs_anual(puntos_acs=...)`.
- Cuadernos 02, 03, 04, 05, 06, 07, 09 y 10 adaptados. El cap. 13 compara H5 a velocidad fija y
  publica aparte el R-717 con velocidad variable (V4); TEWI con los mismos consumos de H5.
- Pruebas: `tests/test_compressor_en12900.py` (12) y las afectadas, actualizadas.

Prueba en el clima medio (45 °C): SEER 2.967 (fija) → 3.179 (variable); SCOP 1.865 → 1.875. En
B, C y D de frío y en 7 y 12 °C de calor la carga queda por debajo de la capacidad a 960 rpm y el
equipo cicla a la mínima: el margen de modulación (66–100 %) es estrecho y el SCOP lo domina el
apoyo bajo la TOL.

Queda para la fase B: las cifras de referencia que cambian con el modelo
(`test_capitulo11::test_el_presupuesto_unico_es_el_del_8_5_2`, 9.52 kW / 476 g, y las de
`test_referencia.py` que dependan del compresor) se actualizan con las hojas regeneradas.

## Estado de las fases B, C y D (15/10/2026, 16:25)

Hechas. Hojas de los caps. 9 a 13 regeneradas (commit `4149706`); tabla de cambios en
`docs/CAMBIOS_COMPRESOR_EN12900.md` (ningún veredicto cambia); V21 de la tesis generada desde la
V20 con `herramientas/tesis/v21.py` (439 cambios; caps. 1 a 8 en rojo). Pendiente: revisión de la
V21 con el autor.
