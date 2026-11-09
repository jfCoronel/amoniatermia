# Decisiones del autor del 29/09/2026

Tomadas una a una con sus pros y contras (sesión del 29/09/2026). Sustituyen a las
correspondientes «decisiones pendientes» de `PLAN_CAPITULOS_10_13.md` §8 y de
`INFORME_CAPITULO_9.md` §7–8. Las que cambian el código se aplican en bloque al terminar
la ronda.

| # | Asunto | Decisión | Consecuencia |
|---|---|---|---|
| 1 | Pérdida de carga en el evaporador (D12) | **Presión uniforme en cada intercambiador** (M8 tal como está escrita). La pérdida de carga se calcula y se publica como comprobación a posteriori, con su salto de saturación equivalente, y se marca si supera un umbral. Aplicarla de golpe a la salida no mejora nada: obligaría a aspirar a esa presión (opción B) y mantendría la asimetría con la batería | Código: la marcha de placas deja de bajar la presión; el cierre exergético queda exacto. Cambian ligeramente las cifras de los modos con placas |
| 2 | Contabilidad de H6 | **El ventilador es auxiliar** y queda fuera de la clasificación de componentes del ciclo; sigue en el denominador de los indicadores (UNE-EN 14511). El compresor se clasifica con su motor y transmisión. Se publica la cuota del ventilador junto al resultado | En diseño, H6 se cumple en M-1 a M-4 (compresor con motor, 31–35 %; siguiente, ≤ 22 %) y **no en M-5** (placas de condensación 30.4 % frente a 19.9 %), lo que se publica tal cual. El ventilador es el mayor destructor individual en M-1 a M-4 (32–35 %): hallazgo para el cap. 11 |
| 3a | Formulación de la carga | **Subenfriamiento como consigna y carga como salida** (tabla 6.4). H4 con la carga del modo más desfavorable | Se declara la limitación (sin receptor, en la máquina real la carga es fija) y el cap. 11 cuantifica el subenfriamiento que tendría cada modo con esa carga |
| 3b | Dimensiones de las líneas | **Las estima Claude** para un módulo compacto, con diámetros normalizados por velocidad, como valores adoptados y declarados. **Sin sensibilidad** salvo que su aportación sea grande (más de un 10 % de la carga total o más de un 1 % del COP) | Con la decisión 1, las líneas no afectan al COP; su pérdida de carga se publica. No hay receptor (el §7.4.2 lo suprime por RS-5) |
| 4 | Validación de sistema (N3) | **Limitación declarada**: sin fuente independiente de sistema, H1 se contrasta a nivel de componente (N1 y N2) | La redacción de H1 (tabla 1.2) debe recoger que la comparación de sistema no es realizable con las fuentes disponibles |
| 5a | Validación cruzada del compresor | **Por grupos de temperatura de condensación**, dejando fuera cada T_k por turno. Criterio sobre los grupos interiores; los extremos (15 y 50 °C) se publican como extrapolación | — |
| 5b | Criterio de la temperatura de descarga (N1) | **≤ 5 K de desviación máxima**, coherente con el margen de no condensación de H3 (5.5 K en diseño). Caudal y potencia, los de la tabla 6.5 (5 % y 8 %) | Fijado antes de ejecutar la validación, como exige el §6.7.3 |
| 5c | Ficha de condensador de Frimetal | **Consumida** por el anclaje del lado de aire (§6.3.1). Su reproducción al 0.6 % se publica como coherencia, no como validación | Dos fuentes consumidas (esta y la del AlfaNova 27-30H); la ficha de evaporador es la validación independiente de N2 |
| 6a | Reparto anual del ACS | **Separado y normativo**: SCOP y SEER por UNE-EN 14825 para la climatización; ACS como balance anual | Sin simulación horaria (podría añadirse después para H3 anual) |
| 6b | Climas | **Los dos**: los tres de referencia de UNE-EN 14825 (comparación normativa) y los intervalos locales de Sevilla, Madrid y Burgos desde los ficheros climáticos del CTE | **Faltan los ficheros del CTE** (no están en `docs/normas`) |
| 6c | Impulsión en calefacción | **45 °C con impulsión variable** según la temperatura exterior (fan-coils 40/45 °C). Si la UNE-EN 14825:2024 no tiene esa aplicación, se declara como propia | — |
| 6d | Carga de diseño | **Criterio normativo**: carga de diseño declarada a partir de la capacidad en una temperatura bivalente, la misma para los tres fluidos | Sin vivienda de referencia |
| 7a | Desescarche | **Penalización adoptada** de la bibliografía (ec. 9-30), con la fuente citada, solo en los intervalos donde el modelo predice escarcha | — |
| 7b | Choque térmico | **Fuera del caso base** (voluntario en viviendas, RS-15); se calcula aparte la energía anual que costaría con resistencia | — |
| 7c | Consumos auxiliares (P_OFF, P_TO, P_SB, P_CK) | **Cero, declarados**: SCOP como cota superior, como ya se declara por las bombas | Iguales para los tres fluidos |
| 7d | Degradación por ciclado | **C_dh = 0.9** (valor por defecto de la norma) **con sensibilidad 0.75–1.0** | Importa sobre todo en M-5 |
| 8a | Perfil de ACS | **L** de UNE-EN 16147 (valor exacto del texto de la norma) | — |
| 8b | Fracción de ACS recuperada | **Balance por intervalo con acumulación**: en cada intervalo de climatización, lo recuperado es el menor entre la demanda de ACS de esas horas y la potencia de recuperación por la fracción de funcionamiento del compresor; el interacumulador desplaza el calor dentro del día; el resto, M-5 | — |
| 8c | Textos de las normas | En `docs/normas`: UNE-EN 14825:2024 y UNE-EN 16147:2017+A1:2023, **solo en local**. Se versionaron el 29/09/2026 y se retiraron el mismo día: la licencia AENORmás de la Universidad de Sevilla exige autorización de AENOR para su uso en red interna (decisión del autor: retirarlos de git sin reescribir el historial; siguen en el commit `fd62068`) | Las tablas se transcriben a `data/` con su cita |
| 9a | Compresor para R-290 y R-32 | **Datos del software de selección de Bock** para un compresor de tamaño parecido para cada fluido, reidentificado igual que el de NH₃; si no hay equivalente, transferencia declarada | **Los genera el autor** |
| 9b | Igualación de capacidad (tabla 6.6) | **Capacidad frigorífica en A35 / W12-7** (UNE-EN 14511); se publican las capacidades de calefacción que resultan | — |
| 9c | Materiales para R-290 y R-32 | **Adaptados** (tubo de cobre en la batería, misma geometría; placas iguales), con el efecto del material publicado aparte del efecto del fluido | — |
| 10a | Temperatura de descarga admisible | **140 °C**, el límite orientativo del §7.7.1, declarado como tal | `limites.T_descarga_max_K` deja de ser null; la envolvente queda completa |
| 10b | Área máxima de la válvula | **Se quita el límite** (valor por defecto sin fuente) y se **publica el área efectiva necesaria** en cada modo, como dato para seleccionar la válvula (§7.6.4) | — |
| 10c | Penalización significativa entre modos (H2) | **Más del 5 % en el indicador del servicio** (EER de M-1 frente a M-2, COP de M-3 frente a M-4) **y fuera de la banda de incertidumbre** del modelo | Fijado antes de calcular la campaña (§6.7.3). El límite de carga de EN 378-1 de H2 no restringe: la configuración está exenta (cap. 1 y cap. 8) |
| 11a | GWP | **Normativa** (reglamento de gases fluorados, IPCC AR4: R-32 = 675, R-290 = 3, R-717 = 0) en el caso base; **AR6 como sensibilidad** | — |
| 11b | Fugas, recuperación y vida útil | **Propuestos por Claude con fuente** (anexo de UNE-EN 378-1, guía de LCCP del IIR), cada uno con su rango | — |
| 11c | Alcance del coste de ciclo de vida | **Solo las partidas diferenciales** frente al R-290 (compresor y motor, material de la batería, seguridad propia del NH₃, refrigerante), con precios de tarifas públicas declarados | — |
| 11d | Parámetros económicos | **Propuestos por Claude con rango**: tasa de descuento 3 % (1–6 %), precio de la electricidad de fuente oficial con escenario, vida útil 15–20 años | Con la sensibilidad del §6.10.2 |

## Datos que tiene que aportar el autor

- Ficheros climáticos de referencia del CTE de Sevilla, Madrid y Burgos (6b).
- Puntos de selección del software de Bock para un compresor de R-290 y otro de R-32 de
  tamaño parecido al F2, en el mismo formato que `data/compresor_bock_f2_catalogo.csv` (9a).
- La v31 del capítulo del modelo, para `docs/Capitulos_pdf/`.

## Cambios de código aplicados el 29/09/2026

Todos aplicados; la suite pasa entera. Dos hallazgos al aplicarlos:

- **Defecto en el recorte de la frontera de fase** (placas y batería). Tras recortar un
  volumen en h_v, el siguiente de un condensador arrancaba exactamente sobre h_v y se
  clasificaba como vapor, así que marchaba entero con el coeficiente monofásico. Pasaba
  lo mismo con un evaporador que arranca en h_l. Es un error proporcional a 1/N. En las
  placas lo tapaba por azar la presión decreciente, y al pasar a presión uniforme
  apareció (7 % con 10 volúmenes). Corregido: tras el recorte, la entalpía avanza
  10⁻⁹ del calor latente en el sentido de la marcha. La independencia de malla de las
  placas vuelve a ser la de antes (9 880 → 9 842 W de 10 a 320 volúmenes). Las cifras
  que dependían del defecto se han remedido. El mayor cambio es el ACS de una prueba de
  M-1 con agua de 10 a 60 °C y malla gruesa: +6.7 %.
- **En calefacción la descarga supera los 140 °C** en los puntos de diseño: 144.9 °C en
  M-3 y 140.5 °C en M-4 con 5 K de recalentamiento (133.8 °C en M-4 con 1 K). No es un
  error del modelo: **el catálogo de Bock publica 144.2 °C a T₀ = 0 °C y T_k = 50 °C**, y
  el modelo da 142.2 °C. Los 121.9 °C que el §7.7.1 atribuye a los modos 3 y 4 no cuadran
  con el catálogo. Esos puntos salen válidos pero **no admisibles**. Afecta a H2 y al
  §7.7, que debe rehacerse, y hace del recalentamiento de consigna una variable de
  diseño en calefacción.

Detalle de lo aplicado:


1. Presión uniforme en la marcha de las placas; pérdida de carga y salto de saturación
   equivalente publicados por intercambiador (`HXResult.dT_sat_equivalente`,
   `checks["M8_salto_saturacion_K"]`), con marca por encima de 0.5 K (1).
2. `limites.T_descarga_max_K: 413.15` con su procedencia (10a).
3. Quitar `ExpansionValve.A_max` y publicar el área efectiva (`checks["area_efectiva_valvula_m2"]`,
   `envelope["area_efectiva_valvula_m2"]`) (10b).
4. Clasificación de H6 sin ventilador y con el compresor agrupado con su motor
   (`ExergyIndicators.y_D_ciclo`, `componente_mayor_ciclo`; columnas `y_D_ciclo_*` en las
   filas de campaña) (2).
5. Regenerar las cifras del capítulo 9 y del ejemplo de M-1 (cambian con 1).

## Decisión posterior (29/09/2026, tarde): enfoque de H5

**Opción C: modelo y mercado.** H5 se mantiene tal como está en la tabla 1.2: la
comparación en igualdad de condiciones se hace con el modelo, frente a R-290 con un
compresor **semihermético** y R-32 con un **scroll**. Los dos se identifican con datos de
su software de selección. El modelo semiempírico es el de Winandy et al. (2002),
formulado para scroll hermético, así que ambos son casos nativos, y la particularización
a compresor abierto del §9.5.2 es la que se deshace. Esto sustituye a la 9a, que pedía un
compresor de tamaño parecido del mismo fabricante.

Se **añade una referencia de mercado**, que no forma parte del contraste de H5: la
máquina de R-717 se sitúa frente a equipos comerciales completos de R-32, R-290 y R-744
de capacidad comparable, con sus datos publicados (EPREL y catálogos). Se usan los
indicadores normativos (η_s y SCOP en clima medio a 35 y 55 °C, SEER; η_wh con su perfil
en las unidades mixtas) y la carga de refrigerante de catálogo, que alimenta también H7.

Consecuencias:
- **Datos del autor**: puntos del software de selección para un semihermético de R-290 y
  un scroll de R-32 de capacidad parecida, en el formato de
  `data/compresor_bock_f2_catalogo.csv`. Si no hay scroll de R-32 utilizable, el R-32 queda
  solo en la referencia de mercado.
- **Criterio de la muestra de mercado**, a fijar antes de mirar los valores. Propuesta:
  bomba de calor aire-agua monobloc, reversible, capacidad declarada en clima medio a
  35 °C entre 6 y 12 kW, en EPREL, por refrigerante. Refrigerante y carga desde el
  catálogo del fabricante cuando EPREL no los da.
- **Código**: el estacional debe calcular también el SCOP a 35 y a 55 °C (además de la
  aplicación de 45 °C decidida en 6c), para comparar con EPREL. El compresor necesita la
  variante hermética o semihermética del balance de la pared (motor refrigerado por la
  aspiración).
- **Texto**: el capítulo 13 tendrá dos partes (contraste de H5 y referencia de mercado),
  y el §6.8.3 debe describir la segunda como tal.

## Referencia de mercado: fuente y alcance (29/09/2026)

- **Fuente de la muestra: Heat Pump Keymark**, porque da a la vez los indicadores
  estacionales, el refrigerante, la carga y el modo frío. EPREL no publica refrigerante,
  carga ni datos de frío (`REFERENCIA_MERCADO.md`).
- **R-744: se nombra y queda fuera** de la referencia de mercado. En el rango de 6 a
  12 kW solo hay bombas de calor de ACS, y la comparación tendría que hacerse en modo
  ACS. La máquina no está diseñada para producir ACS: M-5 es un modo secundario y su
  consigna se ha bajado a 45 °C, así que esa comparación saldría sesgada. Se declara en
  el capítulo 13.
- La referencia de mercado queda con **R-32 y R-290**, bombas de calor aire-agua
  reversibles.

## Compresor: los puntos de VAP como validación, no como identificación (29/09/2026, tarde)

El autor generó 39 puntos con el software VAP de Bock (`data/compresor_bock_f2_vap.csv`),
fuera del catálogo y con temperatura de descarga. El juego adoptado el 24/09/2026,
identificado con T₀ de 0 a 5 °C, se desvía al extrapolar en T₀: a −10 °C y por debajo
sobrestima la potencia al eje entre un 6 y un 16 % y subestima la descarga entre 7 y
19 K.

**Ensayo de reidentificación (descartado).** Mismo protocolo (multiarranque S1–S5, peso
×4 en la descarga) sobre los 46 puntos del catálogo y los 27 de VAP a 1450 rpm dentro de
la envolvente (73 puntos, `data.compressor_extended_points`). Mejor arranque S4, coste
0.1012. Validación cruzada por grupos de T₀ con los criterios de N1:

| T₀ excluida | −15 | −10 | −5 | 0 | 1 | 2 | 3 | 4 | 5 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Potencia máx. | 6.1 % | 6.7 % | 6.6 % | 8.7 % | 9.0 % | 8.4 % | 8.6 % | 2.6 % | 1.9 % | 5.0 % |
| Descarga máx. | 8.2 K | 5.9 K | 3.7 K | 4.7 K | 1.6 K | 2.0 K | 2.4 K | 3.1 K | 3.6 K | 6.2 K |
| N1 | no | no | sí | no | no | no | no | sí | sí | no |

Extremos (−20 y 15 °C): potencia 17.2 y 13.7 %, descarga 14.4 y 8.7 K. Solo 3 de los 10
grupos interiores cumplen. Con más puntos, el ajuste reparte el error: mejora algo los
extremos y empeora el núcleo de 0 a 3 °C (potencia hasta −8.4 % frente a −4.7 %), que es
donde operan los puntos de diseño.

**Decisión: se mantiene el juego del 24/09/2026.** Los puntos VAP se usan como
**validación N1 independiente**, fuera del dominio de identificación
(`validation.compressor_vap`, sección `compresor_vap` del cuaderno 05). Con ellos:

- En el dominio del catálogo (T₀ de 0 a 5 °C, con recalentamiento de 1 a 10 K) cumple N1:
  caudal 2.8 %, potencia 3.3 % y descarga 3.5 K como máximo.
- Mantiene N1 hasta **T₀ = −5 °C**. Ese es el **dominio de validez del compresor en T₀:
  de −5 a 5 °C**. A 10 °C falla por la descarga (6.2 K a T_k = 25 °C).
- Por debajo de −5 °C el sesgo se declara como **limitación** (§9.13). Es de estructura,
  no de datos, y ningún juego de parámetros lo corrige: la pérdida mecánica es constante y
  r_v y η_ic son fijos. En calefacción con exterior frío (M-3, M-4) sobrestima la potencia
  y subestima la descarga; el margen frente al límite de descarga resulta por tanto
  optimista.
- A 960 y 1200 rpm el caudal está bien (3.2 %), pero la potencia sale alta (hasta +12.7 %
  a 960 rpm), porque la pérdida mecánica no escala con la velocidad. Esto se reporta como
  contraste de H6, no como N1.
- El punto de control (bloque D) reproduce el catálogo: caudal 0.6 %, potencia 0.5 %,
  descarga −2.2 K.

No cambian las cifras del capítulo 9.

## Envolvente del compresor: el diagrama de límites del fabricante (29/09/2026, tarde)

El diagrama de límites de aplicación del F2 NH3 (VAP 11.15.2, página 2 del PDF del
compresor) tiene tres zonas: aplicación sin límites, refrigeración suplementaria (por
ejemplo, tapa de cilindro refrigerada por agua) y fuera. El fabricante advierte:
*«Compressor application limits should not be chosen for design purposes or continuous
operation»*.

**Decisión: solo la zona sin límites es admisible.** La máquina no lleva tapa de cilindro
refrigerada. El límite de descarga de 140 °C (§7.7.1) **se mantiene además**: el diagrama
no depende del recalentamiento y la descarga sí. Un punto es admisible si cumple los dos.

- **Digitalización.** Se ha hecho sobre la imagen del PDF (7 px/K en T₀, 3 px/K en T_k),
  con una incertidumbre de lectura de ±0.5 K que se toma como tolerancia del borde. Los
  polígonos están en `limites.diagrama_aplicacion` de `compresor_bock_f2.yaml`.
- **Contraste.** Da la misma zona que el VAP en los 39 puntos.
- **Catálogo.** Lo es también de la fila de 50 °C del catálogo, que el propio catálogo
  anota como «Supplementary cooling required» (T₀ de 0 a 2 °C).
- **Frontera.** A T₀ = 0 °C la zona sin límites acaba en T_k ≈ 46.5 °C, y sube unos
  1.2 K por cada K de T₀.

Consecuencias:

- **M-3 y M-4 de diseño** (T₀ ≈ 0.3 °C, T_k de 49.0 y 47.6 °C) caen en refrigeración
  suplementaria: **no admisibles**. Con el modelo actual, la descarga es de 143.9 °C en
  M-3 y de 139.4 °C en M-4. Los 144.9 y 140.5 °C anotados arriba son anteriores a la
  corrección del recorte de fase en las placas. M-4 cumple, por tanto, los 140 °C, y
  queda fuera solo por el diagrama. M-4 con aire a 12 °C queda en la zona sin límites.
- **La calefacción a 40/45 °C de agua con exterior de 7 °C** está fuera de la zona de
  diseño del compresor. Es un resultado para H2 y para el capítulo 7: haría falta menor
  temperatura de impulsión, más área de condensación o una tapa refrigerada, que habría
  que modelar.
- Las filas de campaña llevan `zona_diagrama` y `envolvente_diagrama_aplicacion`.

## Recalentamiento de consigna en calefacción (29/09/2026, tarde)

**Decisión: 5 K en los cinco modos.** Es el valor habitual de control en expansión seca y
deja margen frente a la llegada de líquido a un compresor alternativo abierto. Así la
consigna es la misma en todos los modos.

Datos de la decisión (diseño, modelo actual):

| Punto | Recal. | T₀ / T_k (°C) | Descarga | COP | Zona del diagrama |
|---|---|---|---|---|---|
| M-3 | 5 / 3 / 1 K | 0.31 / 49.04 → 0.75 / 49.37 | 143.9 → 137.4 °C | 2.401 → 2.471 | suplementaria en los tres |
| M-4 | 5 K | 0.25 / 47.64 | 139.4 °C | 3.096 | suplementaria |
| M-4 | 3 K | 0.53 / 47.78 | 135.9 °C | 3.128 | sin límites, a 0.4 K del borde (dentro de ±0.5 K) |
| M-4 | 1 K | 0.68 / 47.89 | 132.8 °C | 3.150 | sin límites |

Bajar el recalentamiento de 5 a 1 K mejora el COP un 2–3 %. M-4 entra en la zona sin
límites por debajo de unos 3 K; M-3 no entra con ninguno, porque lo que lo limita es la
condensación. El capítulo 11 publica la sensibilidad de 1 a 5 K en calefacción.

## Rangos del estudio de incertidumbre, C10-8 (29/09/2026, tarde)

**Decisión: rangos mixtos, fundados en la evidencia propia donde la hay.** Cada rango se
publica con su fuente.

| Parámetro | Valor | Rango | Fuente |
|---|---|---|---|
| Parámetros del compresor | juego del 24/09/2026 | los juegos equivalentes del multiarranque | §9.5.3; la validación VAP da ±3.3 % en potencia y ±3.5 K en descarga en el dominio |
| C₁ del lado de aire | 0.507 | **±5 %** | validación con la ficha de evaporador (+4.2 %) |
| Φ (alargamiento de placas) | 1.15 | 1.10–1.30 | §9.6.4 |
| φ_c·φ_v | 1.54 | la que resulte de Φ | §9.6.4 |
| φ_md | 1.0 | 1.0–1.3 | M2 |
| η_motor·η_trans | 0.951 | 0.85–0.951 | §9.5.2 |
| Ventilador | 780 W | **fijo** (dato del conjunto montado) | ficha; los 296 W son la batería sola, no un valor posible |
| Fracción de huecos, ebullición, condensación | principal | alternativas registradas | bandas de C10-7 |

## Líneas de refrigerante, C11-1 (30/09/2026): aplicación de la decisión 3b

Implementado el submodelo (`components/line.py`, `data/lineas_refrigerante.yaml`).

- **Geometría adoptada**, no de diseño: gas en tubo de 19 × 1.5 mm, con el diámetro
  interior de 16 mm y las conexiones de ø19 mm del compresor; lados de la válvula en
  10 × 1 mm (interior 8 mm). Longitudes de 0.5 a 1.5 m.
- **Convenio**: adiabáticas y a presión uniforme, de modo que no cambian el ciclo. La
  carga lleva la banda de fracción de huecos, y la pérdida de carga se publica con su
  salto de saturación.
- **Solo las líneas activas.** Cada línea es un par de componentes físicos, igual en los
  dos sentidos de flujo.

**Resultado en diseño** (peor caso de la banda):

| Modo | Componentes | Sistema | Líneas | RS-5 (sistema) |
|---|---|---|---|---|
| M-1 | 452 g | 489 g | 8 % | **1.03** |
| M-2 | 365 g | 413 g | 12 % | 0.81 |
| M-3 | 306 g | 329 g | 7 % | 0.78 |
| M-4 | 313 g | 336 g | 7 % | 0.79 |
| M-5 | 273 g | 299 g | 9 % | 0.36 |

La línea de líquido domina: 29 g en 1 m de tubo de 8 mm. Las pérdidas de carga son de
0.26 K de saturación equivalente como mucho.

**Sensibilidad** (obligada por la decisión 3b: las líneas superan el 10 % de la carga en
M-2). RS-5 del peor caso en M-1:

| Geometría | RS-5 en M-1 |
|---|---|
| Líquido en 6 mm | 1.00 |
| Base | 1.03 |
| Líquido en 10 mm | 1.07 |
| Longitudes × 0.5 | 0.99 |
| Longitudes × 1.5 | 1.07 |

**Consecuencia para H4**: en M-1 el contraste queda en el límite y lo decide la
geometría de las líneas, que no es dato de diseño. El capítulo 7 debería fijarla, o el
capítulo 11 debe presentarlo así.
