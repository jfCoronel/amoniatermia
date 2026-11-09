# Plan del código para los capítulos 10 a 13

28/09/2026. Qué falta en el código para producir los números y simulaciones de los
capítulos finales, en qué orden y con qué datos. Referencia:
`docs/Capitulos_pdf/Tesis_AMONIATERMIA_Cap1-8_formatoETSI.pdf`. Los criterios de las
hipótesis son los de la **tabla 1.2** y los capítulos, los de la **tabla 1.4**. La tabla 6.2
conserva la numeración antigua (H1 en el 11, H5 y H7 en el 14) y mantiene los transitorios
en H2: es una discrepancia del propio capítulo 6 con el 1, que hay que corregir allí.

## 1. Qué contrasta cada capítulo

| Capítulo | Contenido | Hipótesis | Método (cap. 6) |
|---|---|---|---|
| **10** | Verificación y validación, dominio de validez, incertidumbre | H1 | §6.7, §6.11 |
| **11** | Campaña paramétrica en régimen permanente, exergía | H2, H3, H4, H6 | §6.8.1, §6.9 |
| **12** | Rendimiento estacional (UNE-EN 14825) y ACS (UNE-EN 16147), sin transitorios | H2 | §6.8.2 |
| **13** | Comparación entre fluidos, TEWI, LCCP y coste de ciclo de vida | H5, H7 | §6.8.3, §6.10 |

Criterios de aceptación (tabla 1.2) y lo que exigen del código:

| Hip. | Criterio | Lo que exige |
|---|---|---|
| H1 | Desviación media ≤ ±10 % en COP/EER y ≤ ±15 % en potencia térmica **frente a fuentes independientes** | Una fuente de sistema independiente (N3). Hoy no hay ninguna utilizable (C10-4) |
| H2 | Funcionamiento estable en el equilibrio estacionario de todos los modos; sin penalización significativa entre modos; carga dentro de los límites de EN 378-1 | Convergencia y validez en todo el dominio, envolvente (I-4), comparación entre modos y **límite de carga de EN 378-1** (C11-7) |
| H3 | 60 °C en los modos 1 y 3 sin superar los 25 bar; margen de no condensación positivo en el punto de diseño | Casi todo existe; falta la comprobación de presión en la envolvente (I-4) |
| H4 | m ≤ 50 g/kW sobre la capacidad calculada, peor caso de la banda | Líneas y receptor (C11-1) |
| H5 | SCOP/SEER del R-717 ≥ los del R-290 **y** del R-32 + 5 %, misma arquitectura | Capítulos 12 y 13 para tres fluidos, con banda. **Formulación resuelta** en el §1.3 |
| H6 | La destrucción de exergía del compresor es la mayor entre los componentes, en los puntos de diseño de los cinco modos | Existe, pero ver el aviso siguiente |
| H7 | TEWI y LCCP del R-717 ≤ los de R-290 y R-32 en 0.15 y en 0.36 kgCO₂/kWh | C13-6 |

**Aviso sobre H6, con cifras que ya tenemos.** En el punto de diseño de M-1 el modelo da
como fracciones de exergía destruida: **ventilador 33.8 %**, compresor 25.9 % (más 5.4 %
de pérdida electromecánica), placas de climatización 12.9 %, batería 8.6 %, desrecalentador
7.1 % y válvula 6.3 %. El ventilador se contabiliza como destrucción íntegra de sus 780 W.
Si cuenta como «componente del ciclo», H6 no se cumple en M-1. Si no cuenta, o si la
pérdida electromecánica se suma al compresor (31.3 %), sí. Es una decisión de
contabilidad que debe fijarse **antes** de calcular los cinco modos (§8).

## 2. Lo que ya existe

- Los cinco modos convergen y son válidos en diseño; un punto cuesta 5–19 s desde la
  estimación, y lo mismo por continuación (el corrector afina hasta 10⁻¹¹).
- `campaign.run`: barrido con continuación, procedencia, no convergidos conservados y
  backend tabular condicionado a su umbral. `CampaignResult.write` escribe JSON.
- `indicators`: EER, COP y COP global con el ventilador; exergía destruida por componente,
  η_II y separación entre compresión y pérdida electromecánica.
- `validation`: niveles de la tabla 6.5, métricas (error medio con signo, absoluto, rmse,
  banda de paridad) y series de paridad; inventario de fuentes con su estado.
- Correlaciones intercambiables por nombre, con registro de extrapolación.
- Carga como banda de cuatro correlaciones; presupuesto de RS-5 contra la capacidad calculada.
- El fluido como parámetro (`build_circuit(fluido=...)`), con el aviso de que el
  compresor es el del NH₃ sin reidentificar.

## 3. Infraestructura común (primero, porque la usan los cuatro capítulos)

**Hecha el 28/09/2026** (pruebas en `tests/test_infraestructura.py`):

- **I-1** `maps.build` / `PerformanceMap`: rejilla en serpentín con continuación y
  recurso a la estimación si falla; interpolación multilineal que da NaN fuera de la
  rejilla o junto a nudos no válidos; escritura y lectura en CSV + JSON.
- **I-2** `campaign.fila` y `CampaignResult.write_table`: una fila por punto con
  contorno, consignas, incógnitas, potencias, indicadores, banda de carga, envolvente,
  validez y extrapolación; CSV con las unidades y la procedencia en un JSON al lado.
- **I-3** `data.sustituciones` y `build_circuit(sustituciones=..., phi_md=...)`:
  sustitución de cualquier ruta de los ficheros de datos, validada y enumerada en la
  procedencia. El C₁ del lado de aire se lee ahora del fichero (una sola fuente).
- **I-4** `envelope.evaluate`, en cada punto (`sol.envelope`, `sol.admissible`):
  presiones máximas (el catálogo las da **manométricas**: 25 bar(g) son 26.01 bar abs.),
  temperatura de descarga (`sin_dato`: el catálogo no la publica), apertura de válvula,
  margen de no condensación del desrecalentador (RS-17) y dominio de identificación del
  compresor.
- **I-5** `reporting.HojaDeCifras` y `tabla`: la revisión se lee al arrancar y el fichero
  se reescribe tras cada sección.

Queda en I-4 un valor que conviene revisar: el área máxima de la válvula
(`ExpansionValve.A_max = 5·10⁻⁶ m²`) es un valor por defecto del código, no un dato.

| Id | Qué | Por qué | Tamaño |
|---|---|---|---|
| **I-1** | **Mapas de prestaciones**: resolver una rejilla por modo (T_aire × T_agua × caudales), guardarla e interpolar con marca de fuera de rejilla | El estacional (cap. 12) necesita cientos de puntos por clima, el cap. 13 los repite para tres fluidos y la campaña (cap. 11) es una rejilla. Resolver una vez e interpolar desacopla el coste | M |
| **I-2** | **Formato de resultados tabular** (CSV o Parquet por campaña + JSON de procedencia), legible sin el paquete | Anexo F exige las tablas en bruto; hoy solo hay JSON por campaña | S |
| **I-3** | **Capa de sustituciones declaradas** (`overrides`): cambiar cualquier parámetro de datos (compresor, anclajes, Φ, φ_md, rendimientos, ventilador, materiales) desde fuera, con la sustitución enumerada en la procedencia | La necesitan la incertidumbre (§6.11), el cap. 13 (materiales, cilindrada) y las sensibilidades. Hoy solo existe para geometría de placas (`INYECTADO`) | M |
| **I-4** | **Envolvente operativa** comprobada en cada punto: presiones máximas del compresor (19/25 bar, dato), temperatura de descarga admisible (**no existe el dato**), apertura de válvula ≤ 1, recalentamiento positivo, dominio de identificación del compresor | Es la métrica de H2 en régimen permanente y la que pide el §7.6.4 (antiguo 8.6.4) | S |
| **I-5** | **Un cuaderno de cifras por capítulo** (`05_cifras_capitulo_10.py` … `08_cifras_capitulo_13.py`), como el 03, y sus contratos en la suite | Fuente única de números, reproducible sobre árbol limpio | S por capítulo |

## 4. Por capítulo

### Capítulo 10 — Verificación, validación e incertidumbre

| Id | Qué | Código | Datos | Tamaño |
|---|---|---|---|---|
| C10-1 | **Independencia de malla del sistema** en los cinco modos (criterio del 1 % del §6.7.1, serie monótona) | Cuaderno; el mecanismo existe | — | S |
| C10-2 | **Validación cruzada del compresor (N1)**: identificar sin un grupo de puntos y predecirlos (por T_k o k-fold); desviación máxima de caudal y potencia contra 5 % / 8 % | Rutina sobre `identify()`; paridad con `metrics` | Catálogo (existe) | M |
| C10-3 | **N2 intercambiadores**: batería frente a la ficha de evaporador (hecho), placas y batería frente a sus fichas con el estatuto de cada una (consumida o no), pérdida de carga del agua y del refrigerante en placas (la ficha del 27-30H da 0.058 kPa de refrigerante, no usada) | Cuaderno; contrastes | Fichas (existen) | S |
| C10-4 | **N3 sistema** (Monfared y Palm 2011/2012): reconstruir su prototipo y dar banda de predicción | Montar sus componentes: otro compresor, otros intercambiadores. **Grande** | **No están en el repositorio** (`datos: null`) | L, o limitación declarada |
| C10-5 | **N4 recuperación de ACS**: sin fuente | — | No existe | Limitación declarada |
| C10-6 | **Dominio de validez**: rango de T₀, T_k, relación de compresión y capacidad donde se cumplen los criterios; M-5 y los tramos de extrapolación marcados | Función sobre I-1 + registro de extrapolación | — | S |
| C10-7 | **Bandas de correlación**: repetir los casos de referencia con cada alternativa registrada (ebullición, condensación, monofásico, fracción de huecos, multiplicador) | Cuaderno sobre el registro | — | S |
| C10-8 | **Sensibilidad local** (elasticidades, un factor cada vez, perturbación relativa) y **cribado de Morris**; Sobol solo sobre los dominantes | Módulo `uncertainty` sobre I-3 | **Rangos de cada parámetro incierto**, a declarar (§7) | M |

### Capítulo 11 — Campaña paramétrica y exergía

| Id | Qué | Código | Datos | Tamaño |
|---|---|---|---|---|
| C11-1 | **Submodelo de líneas y receptor** con volumen propio (líquido, aspiración, descarga, entre placas y batería): carga por tramo y pérdida de carga | Componente nuevo con la interfaz común, en las topologías | **Longitudes, diámetros y volumen de receptor: no existen**; son de diseño (cap. 7) y los tiene que fijar el autor | M |
| C11-2 | **Diseño factorial** sobre T_aire, T y caudal de agua, recalentamiento, subenfriamiento y modo; puntos no convergidos y no válidos contados por separado | Sobre I-1/I-2, con continuación | Niveles de cada factor (decisión) | M |
| C11-3 | **H3**: con frente a sin recuperación (M-1 frente a M-2, M-3 frente a M-4): T de ACS, margen de no condensación, ΔP_k, ΔCOP global, con banda | Cuaderno; lo básico existe | — | S |
| C11-4 | **H4**: carga en el modo más desfavorable con líneas y receptor, peor caso de la banda frente a RS-5 de la capacidad calculada; sensibilidad al subenfriamiento y al recalentamiento | Sobre C11-1 | — | S |
| C11-5 | **H6**: cociente de destrucción de exergía del compresor en todo el dominio; estimación del margen recuperable con velocidad variable (η_is representativo de esa tecnología) como cota | Función nueva en `indicators` | η_is de referencia de la tecnología (bibliografía) | S |
| C11-6 | **Recalentamiento como variable**: compromiso rendimiento–carga–margen frente al retorno de líquido | Cuaderno sobre C11-2 | — | S |
| C11-7 | **Límite de carga de EN 378-1** para H2, con la categoría de sistema del cap. 8 (indirecto, tipo 3) | Función que compare la banda de carga con el límite | El límite o su cálculo (cap. 8) | S |
| C11-8 | **Penalización entre modos** (H2): mismos indicadores en los cinco modos y su diferencia, con banda | Cuaderno sobre C11-2 | Qué es «significativa» (decisión) | S |

### Capítulo 12 — Rendimiento estacional y ACS

| Id | Qué | Código | Datos | Tamaño |
|---|---|---|---|---|
| C12-1 | **Método de intervalos de UNE-EN 14825**: SCOP (calefacción) y SEER (refrigeración), línea de carga, temperatura bivalente, carga parcial | Módulo `seasonal` sobre I-1 | Tablas de la norma (condiciones A–F, temperaturas de agua por intervalo según la aplicación) | M |
| C12-2 | **Degradación por ciclado** del compresor de velocidad fija (C_d) y tratamiento de M-5 como capacidad sobredimensionada (19.5 kW) que cicla | En `seasonal` | C_d por defecto de la norma o declarado | S |
| C12-3 | **Climas de Sevilla, Madrid y Burgos**: horas por intervalo | Lector de ficheros climáticos | **No están**: ficheros climáticos del CTE u otra fuente pública | S + datos |
| C12-4 | **Carga de diseño de la vivienda** (P_designh, P_designc) | Parámetro | **No existe**: decisión o dato del cap. 7 | — |
| C12-5 | **Desescarche**: penalización sobre los intervalos donde el modelo predice escarcha (fracción bajo cero y condensado, que ya se reportan) | En `seasonal` | Forma de la penalización (decisión, §9.7.6) | S |
| C12-6 | **ACS según UNE-EN 16147**: perfil de extracciones y reparto anual entre recuperación simultánea (M-1, M-3) y producción exclusiva (M-5 a 45 °C); choque térmico periódico | Lógica de reparto; ver §6 | Perfil (M, L o XL) y acumulador (volumen) | M |
| C12-7 | **η_s del Reglamento 811/2013**: SCOP/CC − correcciones; clase solo para el clima medio | En `seasonal` | Coeficientes del reglamento | S |
| C12-8 | **Consumos auxiliares** de la norma (P_OFF, P_TO, P_SB, P_CK): no modelados | Declararlos a 0 como cota o con valor adoptado | No existen | Decisión |

### Capítulo 13 — Comparación entre fluidos, TEWI, LCCP y coste

| Id | Qué | Código | Datos | Tamaño |
|---|---|---|---|---|
| C13-1 | **Compresor para R-290 y R-32**: reidentificar (tabla 6.6) o transferir parámetros declarando cuáles | `identify()` existe | **Catálogo de un compresor para cada fluido**: no hay y no se piden a fabricantes; valdría un catálogo público (p. ej. el software de selección de Bock) | M + datos |
| C13-2 | **Adaptación de la cilindrada** para igualar la capacidad de referencia | Lazo sobre el desplazamiento (vía I-3) | Qué capacidad y en qué condición se iguala (decisión) | S |
| C13-3 | **Materiales y espesores por fluido** (cobre admisible fuera del NH₃, presión de diseño del R-32): conductividad y espesor de pared en placas y batería | Vía I-3 | Materiales y espesores de las variantes (decisión de diseño) | S |
| C13-4 | **Validez de las correlaciones para otros fluidos**: el anclaje φ_c·φ_v de las placas y el lado de refrigerante están hechos con NH₃ | Marcar y declarar; banda | — | S |
| C13-5 | **SCOP y SEER por fluido** en los tres climas, con banda: la diferencia solo cuenta si sale de la banda (§6.11) | Sobre C12 y C10-8 | — | M (cómputo) |
| C13-6 | **TEWI y LCCP**: fugas anuales, recuperación, vida útil, GWP, consumo anual **del cap. 12**, carga **peor caso de la banda** con líneas; factor de emisión de 0.15 a 0.36 kg CO₂/kWh como escenario | Módulo `environment` | Tasa de fugas, factor de recuperación, vida útil, GWP; para el LCCP, masas de componentes y factores de emisión de materiales (el compresor pesa 18 kg; las placas, por catálogo) | S + datos |
| C13-7 | **Coste de ciclo de vida**, como diferencia frente al R-290, con sensibilidad a tasa de descuento, precio de la energía y vida útil | Módulo `economics` | **Precios de componentes** de las dos variantes, tasa de descuento, escenario de precios | S + datos |

## 5. Orden de ejecución

El camino crítico es infraestructura → V&V → mapas → estacional → fluidos.

1. ~~I-2, I-3, I-4~~ **hechos**.
2. **Capítulo 10**: C10-1, C10-2, C10-3, C10-6, C10-7 y C10-8. C10-4 según la decisión
   sobre N3.
3. ~~I-1~~ **hecho**; ~~C11-1~~ **hecho** (30/09/2026; sin receptor, que el §7.4.2 suprime).
4. **Capítulo 11**: C11-2 a C11-8.
5. **Capítulo 12**: C12-1 a C12-8, cuando estén los datos de clima y de carga de diseño.
6. **Capítulo 13**: C13-1 a C13-7. Depende del 12 (consumo anual) y del 11 (carga con
   líneas).

Cada capítulo se cierra como el 9: cuaderno de cifras sobre árbol limpio, contratos en
la suite y discrepancias fijadas como discrepancias.

## 6. Dos decisiones de método que conviene tomar pronto

**Cómo se reparte el ACS a lo largo del año (C12-6).** El método de intervalos de la
UNE-EN 14825 no tiene coincidencia temporal entre demandas, y la recuperación simultánea
de M-1 y M-3 depende precisamente de que haya demanda de ACS mientras se climatiza.
Opciones:

- **(a) Normativa y separada.** SCOP y SEER por UNE-EN 14825 para la climatización; ACS
  como balance anual con una fracción cubierta por recuperación estimada con una regla
  declarada, y el resto con M-5. Comparable con equipos comerciales, que es lo que piden H1
  y H5.
- **(b) Simulación horaria cuasiestacionaria.** Clima horario, cargas horarias y perfil de
  ACS, con el modo de cada hora elegido por reglas de control y las prestaciones tomadas de
  los mapas (I-1). Da la recuperación real, pero no es un indicador normativo y necesita
  cargas horarias de la vivienda.

Recomendación: **(a) para los indicadores** (SCOP, SEER, η_s, que sostienen H5) y **(b)
solo si H3 debe cuantificarse en términos anuales**.

**Formulación con receptor (C11-1).** Con receptor, el subenfriamiento deja de ser una
consigna libre. Se puede (i) mantener la formulación actual, con consigna de
subenfriamiento y la carga como salida, y añadir el volumen de líneas y receptor al
inventario; o (ii) imponer la carga y dejar el subenfriamiento como resultado. La (i) es un
cambio pequeño y coherente con que la carga es salida. La (ii) es otro sistema de
residuos. Recomendación: **(i)**.

## 7. Datos que hacen falta y no están

No se piden más datos a fabricantes (decisión del 28/09/2026). Todo lo de esta lista es
de diseño, normativo o público:

| Dato | Para | Quién o de dónde |
|---|---|---|
| Longitudes y diámetros de líneas; volumen del receptor | C11-1, H4, TEWI | Autor (diseño, cap. 7) |
| Rangos de los parámetros inciertos | C10-8 | Autor; propuesta de partida en la tabla de abajo |
| Niveles de los factores de la campaña | C11-2 | Autor (tabla 6.4 como base) |
| Carga de diseño de la vivienda | C12-4 | Autor (cap. 7) o criterio de la norma |
| Horas por intervalo de Sevilla, Madrid y Burgos | C12-3 | Ficheros climáticos públicos (CTE) |
| Aplicación de UNE-EN 14825 (temperatura de impulsión y ley de compensación) | C12-1 | Decisión: fancoils a 45 °C, ¿media o baja temperatura? |
| Perfil de ACS y volumen de acumulación | C12-6 | UNE-EN 16147 y cap. 7 |
| Temperatura de descarga admisible del compresor | I-4, H2 | **No existe** en el catálogo de Bock; valor adoptado y declarado |
| Catálogo de compresor para R-290 y R-32 | C13-1 | Público, o transferencia declarada |
| Parámetros de TEWI/LCCP y masas de componentes | C13-6 | Normas (UNE-EN 378), IIR, catálogos |
| Precios, tasa de descuento, precio de la energía | C13-7 | Autor |
| Datos de Monfared y Palm | C10-4 | Autor, desde los artículos, o limitación |

Propuesta de partida para los rangos de C10-8. **Decidido el 29/09/2026** con dos cambios
(C₁ ±5 % y ventilador fijo): ver `DECISIONES_2026_09_29.md`.

| Parámetro | Valor | Rango propuesto | Fundamento |
|---|---|---|---|
| Parámetros del compresor | juego adoptado | los tres juegos equivalentes del multiarranque | §9.5.3 |
| C₁ del lado de aire | 0.507 | ±15 % | dispersión de correlaciones generales |
| Φ (alargamiento de placas) | 1.15 | 1.10–1.30 | §9.6.4 |
| φ_c·φ_v | 1.54 | la que resulte de Φ | §9.6.4 |
| φ_md | 1.0 | 1.0–1.3 | M2 |
| η_motor·η_trans | 0.951 | 0.85–0.951 | §9.5.2 |
| Ventilador | 780 W | 296–780 W | `sensibilidad_6_11` |
| Fracción de huecos, ebullición, condensación | principal | alternativas registradas | registro |

## 8. Decisiones del autor

**Resueltas el 29/09/2026**: ver `DECISIONES_2026_09_29.md`, que recoge cada una con su
consecuencia, los datos que aporta el autor y los cambios de código que se derivan.
