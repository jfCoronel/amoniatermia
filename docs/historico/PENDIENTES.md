# Pendientes

> **Numeración.** Este documento cita el capítulo 10 en su revisión previa a la v30 y el
> capítulo 7 en su v1. La correspondencia con las versiones vigentes
> (`docs/Capitulos_pdf/`) está en `docs/CORRESPONDENCIA_CAP10.md`. No se renumera: citar la
> versión que se auditaba es parte de lo que el documento registra. Las entradas
> fechadas desde el 24/09/2026 citan ya la v30 y la v3.

## 24/09/2026 — Capítulos nuevos: decisiones y discrepancias que reportar

Llegan las últimas versiones de los capítulos 5 (v13), 7 (v3), 8 (v5), 9 (v4) y 10 (v30)
en `docs/Capitulos_pdf/`, y se retiran `docs/cap10_modelo.md`, `docs/cap7_metodologia.md` y
`docs/secciones/`. El repositorio se realinea con ellos (paso 0): numeración de las citas
(`docs/CORRESPONDENCIA_CAP10.md`), contrato de cifras de los tests y tabla 7.5.

### Decidido

- **Los transitorios quedan fuera del alcance de la tesis.** Decisión del autor del
  24/09/2026. El capítulo 10 ya lo decía (§10.1: «el estudio de las conmutaciones entre
  modos queda fuera del alcance de este trabajo»; hipótesis M1). **Son los capítulos 7, 8 y
  9 los que hay que corregir**, porque siguen asignando al capítulo 13 una formulación
  dinámica de orden reducido:
  - cap. 7: tabla 7.2 (H2, método «simulación de transitorios de conmutación», cap. 12 y
    13), §7.6.1 («formulación dinámica de orden reducido restringida al estudio de las
    conmutaciones… empleada en el capítulo 13») y §7.8.2, último párrafo;
  - cap. 8: la mención a las «conmutaciones entre modos analizadas en el capítulo 13»;
  - cap. 9: §9.8.3, «su comportamiento durante los transitorios se examina en el capítulo
    13»;
  - cap. 5: la referencia al «modelo dinámico del capítulo 13».
  Con ello **H2 pierde la mitad de su método de contraste**: queda la simulación
  estacionaria de los cinco modos. La tabla 7.2 y la formulación de H2 deben decirlo.
- **Cierre de balances en 10⁻³.** Lo fija la v3 del capítulo 7 (§7.7.1). La divergencia que
  `validation.divergencias_con_el_capitulo()` reportaba desde el 21/09/2026 queda cerrada.
- **Criterios de N1 y N3 fijados en la tabla 7.5**, N1 como desviación **máxima**. N2 y N4
  declarados sin fijar por falta de fuente. Zajacs et al. sale de la tabla.

### Reportado, para decisión del autor

- **Validar N1 contra los puntos con que se identificó el compresor es circular.** La v3
  (notas de revisión) pide fijar el criterio de la temperatura de descarga «con la
  desviación medida que el apartado 10.5.3 publica», los ±3.66 K. Pero esa desviación es la
  del ajuste sobre los mismos 46 puntos: un criterio igual a ella se cumple por
  construcción, y el §7.3.1 establece que una fuente empleada para determinar parámetros
  queda consumida para contrastarlos. La objeción alcanza a todo N1, no solo a la
  descarga. Salida propuesta: validación cruzada, identificando sobre un subconjunto y
  contrastando sobre el resto, con el criterio fijado antes de ejecutarla.
- **La ficha de Frimetal también está consumida.** El lado de aire se ancló sobre su único
  punto (§10.7.3, «reproduce el punto de ficha por construcción»). Por la regla del §7.3.1
  queda consumida igual que la del 27-30H, pero el §7.7.3 cuenta una sola fuente consumida
  y el §10.14 nombra solo la de placas. En `data/validacion_tabla_7_5.yaml` sigue como
  `disponible_punto_unico`, con la reserva escrita.
- **Penalización de desescarche: ¿capítulo 12 o 13?** El §10.7.6 la aplica «a nivel de
  agregación estacional, en el capítulo 12»; el §7.8.2 y los capítulos 8 y 9 ponen la
  agregación estacional en el 13.
- **Recuento de la suite.** El §10.12.5 publica 421 contrastes, 418 satisfechos y 3
  pendientes. El repositorio daba 423, 420 y 3 al empezar el 24/09/2026, y tras el
  realineamiento da 426, 423 y 3.

### El contrato de cifras, realineado

El modelo reproduce el equilibrio de M-1 de la v30 cifra a cifra (tabla 10.19: 44.9 °C,
11.73 kW, 9.52 kW, 2.478 kW, 32.58 kg/h, 120.1 °C; RS-5 476 g), la tabla 10.9 en sus dos
columnas y el punto de M-5 de la tabla 8.5 del capítulo 8. Los tests que los trataban como
«discrepancia abierta» con la revisión previa (46.8 °C, 10.3 kW, 515 g, 140.4 °C) los fijan
ahora con tolerancia estrecha, y la discrepancia antigua se conserva como candado. El punto
de M-5 no lo fijaba ningún test.

### Paso 1, 24/09/2026 — el balance de las placas NO era físico

Los modos con placas (M-1 completo, M-3, M-4, M-5) salían no válidos por balances de
placas entre 0.5 y 2.4·10⁻³. **El error era exactamente |cp(T_sal)/cp(T_ent) − 1| del
agua**, coincidente en cuatro cifras: la marcha avanzaba el agua con un cp CONSTANTE
evaluado en un extremo y la comprobación usaba otro cp constante, el de la entrada. No había
desequilibrio. Y el código se apartaba del capítulo: la **ec. 10-11 escribe el balance del
agua en entalpía**, ṁ_w·(h_w,j−1 − h_w,j) = Q_j.

Corregido en `plate_hx`: el agua se marcha en entalpía; la comprobación usa la entalpía del
agua en los extremos; la entropía del agua en `Circuit._entropy` pasa a ser la diferencia
exacta de entropías. Dos ajustes necesarios para ello, ambos declarados en el código:
- **`P_AGUA` = 10 bar** en lugar de 2 bar. El disparo del contracorriente explora
  temperaturas por encima de los 120 °C de saturación a 2 bar; con el cp lineal no se notaba,
  pero `_alpha_sec` ya evaluaba propiedades de VAPOR en esos tanteos sin decirlo.
- **Extrapolación lineal fuera del dominio líquido** en la inversión h → T, solo para los
  tanteos no físicos del disparo (agua por debajo de 0 °C); la solución convergida queda
  siempre dentro.

Resultado, con las configuraciones de la auditoría (60 segmentos, 12 volúmenes):

| Caso | Converge | Válido | Residuo | Peor balance |
|---|---|---|---|---|
| M-1 completo | sí | **sí** | 2.8·10⁻¹¹ | 1.8·10⁻¹⁰ |
| M-2, aire húmedo | sí | **sí** | 1.8·10⁻¹⁰ | 1.5·10⁻⁸ |
| M-3, ACS 35 → 67 °C | sí | **sí** | 7.4·10⁻⁷ | 3.6·10⁻¹⁰ |
| M-3, ACS 10 → 60 °C | no (desde la estimación inicial) | — | 9.0·10⁻³ | 4.7·10⁻¹² |
| M-4, ACS 10 → 60 °C | sí | **sí** | 4.0·10⁻¹¹ | 2.7·10⁻⁹ |
| M-4, ACS 35 → 67 °C | no | — | 1.3·10⁻² | 3.6·10⁻¹⁰ |
| M-5 (tabla 8.5) | sí | **sí** | 8.5·10⁻¹⁰ | 3.1·10⁻⁹ |

**Ya no hay ningún modo no válido por balance.** Lo que queda es convergencia:
- **M-3 con ACS 10 → 60 °C** converge a 2.4·10⁻¹² y es válido arrancando cerca de la raíz
  (P0 = 4.54 bar); la estimación inicial por parámetros agrupados lo pone en 5.34 bar y desde
  ahí el método se para con 2.5 K de recalentamiento de menos. Con el código anterior
  convergía desde la misma estimación: el cambio físico desplaza un poco la raíz y el camino
  cambia. Es robustez de la inicialización, no del modelo. La función de residuos es suave
  en el entorno (barrido del 24/09/2026).
- **M-4 con ACS 35 → 67 °C**, la condición de diseño, no converge; tampoco lo hacía antes de
  este cambio. Pendiente de diagnóstico.

Las cifras publicadas se mueven dentro de las tolerancias del contrato (M-1 al 0.2 %, M-5 a
20 W sobre 19.5 kW). **Lo que el capítulo debe cambiar**: la tabla 10.6 y el §10.4.4 («M-4 y
M-5… se marcan como no válidos por el balance interno de uno de sus intercambiadores», el
ejemplo de los 1.37·10⁻³ con que se justifica el criterio de 10⁻³), el §10.13 (limitaciones
del estado actual), la nota de revisión sobre la validez de M-4 y M-5, y la tabla 8.5 y el
§8.4.3 del capítulo 8, que declaran M-5 no válido. **Consecuencia metodológica**: el
ejemplo que el §7.7.1 y el §10.4.4 usan para defender el criterio de 10⁻³ era un artefacto
de la comprobación; el criterio sigue siendo defendible, pero no con ese ejemplo.

### Paso 1, 24/09/2026 — convergencia: los cinco modos resuelven en sus condiciones de diseño

Tras el agua en entalpía quedaban M-3 (ACS 10 → 60 °C) y M-4 (ACS 35 → 67 °C) sin
converger. No era un problema de método sino **tres defectos del modelo que metían ruido o
escalones en los residuos**, más una estimación inicial que no sirve para todos los modos:

1. **El compresor no siempre convergía y nadie lo miraba.** Su sistema interno acotaba T₁
   con `max(T1, T_su)`: por debajo de T_su el residuo de la ec. 10-1 era CONSTANTE, una
   meseta de −AU_su·(T_w − T_su) sobre la que `hybr` se paraba, a veces declarando éxito
   con un residuo de 1.1 W. Con AU_su = 0.0056 W/K la raíz está a 0.04 K de T_su y caía a
   menudo en ella. Resultado: un **ruido relativo de 1.3·10⁻⁴ en el caudal** que era el suelo
   de residuo de TODOS los modos. La cota pasa a la saturación, el arranque a T_su + 0.1 K,
   la convergencia se juzga por los residuos (10⁻⁵ W) con reintentos. El ruido baja a 10⁻¹¹.
   **Corrige un diagnóstico anterior**: el comentario de `circuit.py` y el §10.7.8
   atribuían el R3 de 4.3·10⁻⁴ de la potencia al eje a la identificación («no puede hacerse
   exactamente nulo»). Era esta meseta.
2. **El punto fijo sobre q'' de las placas no convergía en ebullición con título alto**
   (x ≈ 0.93–0.9997): oscilaba entre, por ejemplo, 9.7 y 19.5 kW/m² y se devolvía la última
   iteración sin aviso. El recalentamiento de salida saltaba 1.4 K con milésimas de kelvin
   en el agua. Respaldo con intervalo garantizado (`brentq` sobre φ(q) − q), solo donde el
   punto fijo falla: donde convergía, el resultado no cambia.
3. **El recorte en la frontera de fase de las placas** iteraba A ← A·(h_b − h)/(h_nuevo − h),
   que no es contractivo si el coeficiente depende de q; agotaba sus 6 pasos oscilando entre
   dos áreas. Sustituido por `brentq` sobre el área, con la raíz encerrada.
4. **El disparo del intercambiador de placas aislado** seguía con 10⁻³ K, cuando el del tren
   ya estaba en 10⁻⁷ por la misma razón (el ruido llega al recalentamiento amplificado por
   ṁ_agua·cp/ṁ_ref). Unificados en `Circuit.TOL_DISPARO`.
5. **Arranques alternativos** en el lazo externo: si el arranque por defecto (pinzamientos
   10 K aire / 6 K agua) no converge, se prueban otros y el mensaje dice desde cuál se
   convergió. M-4 en su condición de diseño lo necesita: la estimación pone la evaporación
   en −3 °C, al otro lado de un codo de R4, y la solución está a +0.33 °C.

Resultado, 60 segmentos y 12 volúmenes, todos **convergidos y válidos**:

| Caso | Residuo | Notas |
|---|---|---|
| M-1 completo | 1.5·10⁻¹⁰ | |
| M-2, aire húmedo | 2.4·10⁻¹¹ | |
| M-3, ACS 35 → 67 °C | 3.7·10⁻¹¹ | |
| M-3, ACS 10 → 60 °C | 1.3·10⁻¹¹ | antes no convergía |
| M-4, ACS 10 → 60 °C | 1.1·10⁻¹¹ | |
| M-4, ACS 35 → 67 °C | 1.6·10⁻¹¹ | antes no convergía; arranque alternativo, 346 s |
| M-5, tabla 8.5 | 4.9·10⁻¹⁰ | |

**Hallazgo físico que afecta a H3 y al criterio de dimensionado del §10.6.7**: en los
puntos de diseño con impulsión de 67 °C, el refrigerante sale del desrecalentador con
**5.5 K de margen sobre la saturación en M-3** (pared húmeda 8 %) y con **0.02 K en M-4**
(x = 1.0001, pared húmeda 33 %). En calefacción con ACS el desrecalentador trabaja en el
límite de condensar dentro: el criterio se cumple por los pelos. El §10.6.7 solo evalúa
el punto de verano.

**Lo que el capítulo debe cambiar por estos arreglos**:
- §10.12.4 y tabla 10.25: el suelo de residuo de ~2·10⁻⁶ que se atribuye al backend tabular
  era en su mayor parte el ruido del compresor. Hoy HEOS da 9.7·10⁻¹⁰ y el tabular
  6.3·10⁻⁸: el tabular sigue dos órdenes por encima pero **ya cumple la tolerancia**, y deja
  de ser cierto que «puede marcar como no convergidos puntos cuya respuesta es correcta».
- Tabla 10.19 y §10.4.1: la descarga del equilibrio de M-1 pasa de 120.1 a **120.15 °C**
  (se publicaría 120.2). El resto de la tabla no se mueve.
- §10.7.8: el «R3 de 4.3·10⁻⁴» desaparece; el compresor cierra a 10⁻⁷ W.
- §10.4.4 y tabla 10.6: M-3 alcanza la tolerancia en las dos condiciones de ACS.
- Tabla 10.9: con el compresor corregido, el juego adoptado da ±3.69 K en la descarga
  (±3.66 publicado). El juego se identificó con el compresor defectuoso; la diferencia es
  pequeña, pero una reidentificación con el código corregido es lo riguroso.

**Coste**: la suite pasa de unos 6 a unos 8.5 minutos. Las campañas notarán sobre todo los
puntos que necesiten arranque alternativo; una estimación inicial mejor (pinzamientos por
modo, o continuación desde un punto convergido) lo evitaría.

### Paso 1, 24/09/2026 — el compresor, reidentificado con el código corregido

Decisión del autor. El juego de la tabla 10.8 se identificó con el compresor que caía en
la meseta de max(T₁, T_su). Repetido el protocolo (mismos 46 puntos, cotas y función
objetivo) con cinco arranques, esta vez registrados en `data/compresor_bock_f2.yaml`: tres
llegan al mismo mínimo (coste ≈ 0.0208) con parámetros distintos y predicciones iguales.
Se adopta el que parte del juego anterior (bloque `reidentificacion_2026_09_24`):
±2.71 % en caudal, ±4.72 % en potencia al eje y ±3.35 K en descarga (antes ±2.72 / ±5.18 /
±3.66). El de la v30 queda como `variant="reidentificacion_2026_09_16"`.

Efecto sobre las cifras publicadas: la descarga del equilibrio de M-1 pasa a 120.0 °C y el
punto de M-5 cambia un 2 % en potencia eléctrica (3 993 → 3 914 W; COP global 4.89 →
4.98). **Hallazgo**: M-5 opera fuera del dominio de identificación del compresor (T₀ =
17.6 °C frente a 0–5 °C del catálogo), y ahí los juegos equivalentes divergen; es una
incertidumbre de extrapolación que el capítulo 11 debe acotar. La figura 10.3 está rehecha
en `docs/figuras/`. Todo lo que el capítulo debe cambiar está en
`docs/INFORME_REESCRITURA.md`, ficha 1.10.

### 25/09/2026 — el punto de diseño del desrecalentador, resuelto como sistema

**Decisiones del autor**: (1) el punto de diseño pasa a ser M-3 resuelto como sistema
(aire 35 °C, climatización 12 °C, ACS 35 → 67 °C), en lugar del componente aislado con
40.3 kg/h de NH₃ a 45 °C, caudal que no era el del compresor; (2) en invierno se **acepta
la condensación parcial** del desrecalentador con retorno frío y se declara.

Punto de diseño: 43.4 °C de condensación, 31.6 kg/h, 123.0 °C de descarga, 49.8 kg/h de
ACS, **1 851 W y 5.5 K de margen** (antes 2 371 W y 6.4 K). En verano el criterio se
cumple en todo el barrido del retorno (1.2 K a 25 °C). En invierno (M-4) el refrigerante
condensa dentro con retorno ≤ 30 °C (x = 0.993 a 30 °C, 0.980 a 25 °C) y queda en la
saturación a 35 °C. La tabla 10.15 rehecha sostiene la selección del 16-10H (el 27-30H
condensa el 4 %). Contrastes en `TestPuntoDeDisenoDelDesrecalentador` y
`TestSeleccionEnElPuntoDeDiseno`. Todo lo que cambia en los capítulos 8, 9 y 10, en
`docs/INFORME_REESCRITURA.md`, ficha 1.5.

De paso, dos cotas físicas en `plate_hx._solve_cell`: la salida estimada y el calor del
volumen no pueden llevar al refrigerante más allá de la temperatura del agua. Solo actúan
en estados imposibles; aparecieron al resolver el 27-30H con caudales de ACS extremos.

### 25/09/2026 — las demás tablas del capítulo 10, rehechas

- **Tabla 10.20**: la columna impuesta, con el compresor adoptado, da 8.83 / 7.13 / 4.59 kW
  (la v30 publica 10.03 / 8.36 / 5.84 kW, de la revisión previa). La diferencia entre
  imponer y resolver es del 1–4 %, no del 12–22 %, y la conductancia como evaporador es de
  33–36 W/(m²·K), no ~27. Valores de referencia del equilibrio remedidos en
  `data/bateria_frimetal_cbn21.yaml`.
- **Tabla 10.22**: calculada con el mismo equilibrio de M-1 y subenfriamiento de consigna.
  Con 7.3 K, 364–498 g y el 9.2 % anegado: el **102 %** del presupuesto de RS-5 de esa fila
  (la v30 publica el 90 %, contra 515 g). Las filas publicadas no tenían procedencia.
- **Ejemplo exergético del §10.11.2**: 2 291 W, −5.0 W y +24.0 % en verano; +258.6 W en
  invierno (la v30: 2 238 W, −5 W, 23.5 %, +252 W).
- **`CompressorGeometry.r_v` retirado**: nadie lo leía y arrastraba el 2.0 del juego antiguo.
- **`notebooks/03_cifras_capitulo_10.py`** genera `docs/cifras_capitulo_10.md` con todas las
  cifras del capítulo que produce el modelo y su procedencia.

### Lo que el modelo no reproduce de la v30 — para el paso 1

- **Tabla 10.6: residuos y validez por modo.** *(Las invalideces por balance quedan
  superadas por la corrección del agua en entalpía; ver «Paso 1» arriba. Los residuos
  siguen sin coincidir con la tabla.)* Medido por la auditoría del 24/09/2026 con
  las configuraciones de `test_indicadores` y `test_campana`, porque el capítulo no las
  declara:
  - **M-1** con el circuito completo (placas incluidas) converge, pero **no es válido**: el
    balance de las placas queda en 1.24·10⁻³. La tabla 10.6 lo da como «cumple».
  - **M-3** alcanza la tolerancia (7.5·10⁻⁷ con impulsión de 60 °C, 2.8·10⁻⁷ con 67 °C),
    frente al «7.2·10⁻⁵, no cumple». No es válido: balances entre 1.6 y 2.4·10⁻³.
  - **M-4**: el balance del desrecalentador sale 2.40·10⁻³ (60 °C) o 1.58·10⁻³ (67 °C), no
    los 1.37·10⁻³ del §10.4.4.
  - M-2 y M-5 coinciden con la tabla.
  Hay que fijar las configuraciones de la tabla 10.6 y rehacerla, o declararlas.
- ~~**Posible error del modelo: el balance de la batería ignora el calor latente.**~~
  **CORREGIDO el 24/09/2026** (`Circuit._coil_air_duty`). La comprobación suma el término
  latente ṁ_seco·[(h_sal − h_ent) − cp_da·ΔT], nulo en las celdas secas con cualquier cp
  —de modo que el cp = 1005 del anclaje sigue dando la comprobación sensible exacta— y
  igual a la ec. 10-28 con `AirState.at`. M-2 con aire húmedo nominal pasa a válido, con la
  batería cerrando por debajo de 10⁻⁶ (`TestConvergenciaDeM2::test_m2_con_aire_humedo_es_valido`).
  M-4 con aire húmedo (ACS de 10 a 60 °C) converge a 4.2·10⁻¹² y la batería cierra a
  2.8·10⁻¹⁵; sigue no válido, ya solo por el desrecalentador (2.40·10⁻³). **Observación
  nueva:** con retorno de ACS a 35 °C e impulsión a 67 °C —la condición de diseño— M-4 con
  aire húmedo NO converge (residuo 1.3·10⁻²). Texto original de la entrada:
  **el balance de la batería ignora el calor latente.**
  `circuit.py`, en `_checks`, compara la potencia del serpentín con
  `m_dot_air·cp·ΔT` del aire, que solo es el calor sensible. Con aire húmedo en la
  condición nominal de la UNE-EN 14511 (7 °C bs / 6 °C bh), M-2 y M-4 salen **no válidos
  con un 34 % de error de balance** que no es del componente sino de la comprobación. Los
  tests usan aire seco (`AIRE_7`) y no lo ven. Es el mismo tipo de error que se corrigió en
  la entropía del aire (§10.11.2).
- **La hipótesis oculta del punto de diseño del desrecalentador.** Las tablas 10.13, 10.14
  y 10.16 se calculan con 40.3 kg/h de NH₃ condensando a 45 °C y entrada a 125.5 °C. Pero
  los 125.5 °C son de condensación a 46.8 °C, y ahí el compresor adoptado da 32.2 kg/h
  (32.58 en el equilibrio de M-1). Con 32.2 kg/h a 46.8 °C salen 53.0 kg/h de primario,
  1972 W y 3.1 K de margen, frente a 63.7 kg/h, 2371 W y 6.4 K. El capítulo no declara el
  caudal. **Afecta a H3 y al criterio de no condensación**, que es el que estaba apretado.
- **Columna «impuesta» de la tabla 10.20.** No es reproducible con el compresor adoptado
  (10.03 / 8.36 / 5.84 kW frente a 8.83 / 7.12 / 4.58 del modelo): es de la revisión
  previa. Frente a la columna impuesta del modelo actual, las capacidades resueltas quedan
  solo un 0.4–3.3 % por debajo, no un 12–22 %. La columna resuelta sí se reproduce.
- **Filas 1 y 2 de la tabla 10.13** (~93 / ~80 kg/h, ~2.72 / ~2.32 kW): son del cálculo
  exploratorio del 18/09/2026. Hoy dan 97.8 / 83.4 kg/h y 2.84 / 2.42 kW, y con la
  geometría adoptada 99.2 / 84.8 y 2.88 / 2.46. La caída del 15 % se mantiene.

### Erratas internas de la v30 — para la próxima revisión del capítulo 10

1. **Tabla 10.22**: la columna «% del presupuesto» está calculada contra 515 g en las filas
   2 a 4, y la fila 1 no cuadra con ningún presupuesto. Contra los 476 g del texto debe
   decir 69 / 97 / 117 / 136 %: con 7.3 K de subenfriamiento ya se está en el 97 %.
2. **§10.7.8, tabla 10.20**: la conductancia como evaporador «del orden de 27 W/(m²·K)» es
   la del término nucleado solo (Cooper), que el §10.7.5 abandona; con la correlación
   adoptada el modelo da 33–37. Las caídas de capacidad con los números de la propia tabla
   son 15–22 %, no 12–22 %, y la diferencia de temperaturas llega a 0.72 K.
3. **Tabla 10.12**: dice Φ = 1.20, pero su φc·φv = 1.54 y sus 0.1171 m² son los de
   Φ = 1.15, que es lo que usa el modelo. Los 0.9091 m² no corresponden a ningún Φ (el
   modelo y la tabla 10.15 dan 0.894), y el «hueco b» de 2.42 mm del 27-30H es el paso de
   paquete: el hueco es 2.02 mm.
4. **Tabla 10.13, fila 2** (~2.32 kW) contradice el texto del §10.6.7 para la misma
   condición («de 2463 a 2371 W»).
5. **§10.6.1** dice que el residuo de M-1 «pasa de 3.0·10⁻³ a 2.9·10⁻¹³»; la tabla 10.6
   da 3.9·10⁻⁹ → 3.8·10⁻¹¹, y el 3.0·10⁻³ era de M-2.
6. **§10.7.2**: «entre uno y siete órdenes»; en la tabla 10.6 M-3 no se mueve y M-4 sube dos
   órdenes.
7. **M-5 retirado a medias**: el §10.4.2 dice aún «M-5 con reparto explícito instancia
   cinco», y la «Tercera» decisión del §10.11.1 llama «rechazo del calor residual» al calor
   del intercambiador de climatización en M-5, que el §10.3 dice que no existe.
8. **§10.5.2**: «el eje pide 2.41 kW»; el §10.4.1 da 2.478.
9. **§10.5.3**: «AU_ex,n y r_v quedaron en el límite», pero la tabla 10.8 dice que la cota
   de r_v «apenas mordía» (1.965 frente a 1.2).
10. **Eficiencia de aleta seca**: 0.447 / 0.465 en el §10.7.4 y la tabla 10.18, 0.440 / 0.458
    en el §10.7.6.
11. **§10.7.3**: h_a = 114.6 W/(m²·K) a 35 °C, cuando el anclaje en el punto de ficha, a
    35 °C, es 113.
12. **Hipótesis M8** (tabla 10.2): «2.6 kPa sobre 17.8 bar» en la batería, cuando el §10.13
    dice que la pérdida de carga del lado de refrigerante de la batería se desprecia, y el
    modelo no la calcula.
13. **§10.7.8**: «los balances cierran por debajo de 10⁻⁵»; en ese punto el residuo de la
    pared del compresor (R3) es 4.3·10⁻⁴ de la potencia al eje. El de energía sí es 1.9·10⁻⁷.
14. **Párrafos duplicados**: el rango de velocidad en el §10.5.3 y el «correr hoy con R-290
    o R-32» en el §10.5.4.
15. **Juego anterior a 46.8 °C**: el §10.7.8 dice que daba 142.0 °C; el modelo da 141.3.
17. **Ec. 10-3 y 10-4: el mismo símbolo P_ad para dos presiones.** En el rendimiento
    volumétrico (ec. 10-3) P_ad es la ASPIRACIÓN; en la ec. 10-4 es P(v_in, h_ad), el final
    de la etapa interna. Leída literalmente, la ec. 10-3 daría la reexpansión del espacio
    muerto hasta la presión adaptada, que es físicamente incorrecto (a T₀ = 2 / T_k = 45:
    relación 1.55 y η_v = 0.964, frente a 3.85 y 0.839). **El código usa la aspiración**
    —`Circuit` llama `compressor.solve(P0, ...)` y `eta_v` recibe `P0`; el estado interno
    se llama `P_int`—, de modo que C = 0.088 está identificado con la forma correcta y no
    hay que reidentificar nada. Es errata del texto: escribir P_su en la ec. 10-3.
    Consultado por el autor el 24/09/2026.
    Queda, aparte, una cuestión de interpretación: 8.8 % es alto para un espacio muerto
    real, C figura como «débilmente sujeto» (tabla 10.10) y A_leak se fija en cero por no
    identificable, de modo que C absorbe probablemente otras pérdidas volumétricas. Que el
    §10.5.4 lo declare «geométrico, transfiere directamente» a otros refrigerantes excede lo
    que la identificación sostiene, y afecta al protocolo de H5.
18. **Campo `r_v` de la geometría** del compresor en `data/compresor_bock_f2.yaml`: conserva
    el 2.0 de la antigua tabla 10.4. No lo usa el solver, que toma el del juego de
    parámetros (1.9653), pero debería retirarse o marcarse. Es del código, no del capítulo.

## Datos que faltan (capítulo 10, §10.6.11 y §10.5.9)

| Dato | Apartado | Repercusión |
|---|---|---|
| ~~Curva característica del ventilador~~ | 10.6.8 | **Cerrado el 17/09/2026 por decisión del autor:** se renuncia a la curva y se adopta consumo CONSTANTE. Justificación: caudal y pérdida de carga varían poco entre condiciones |
| ~~Consumo del ventilador~~ | 10.6.8 | **Cerrado el 17/09/2026 con dato de catálogo:** 780 W de la serie CBN a alta velocidad, motor en triángulo, con **un solo axial de Ø500**. Es potencia ABSORBIDA, que es lo que pide la UNE-EN 14511: no hace falta suponer η. Sustituye a los 296 W, que eran cota inferior. Doble contraste: con η = 0.30 equivalen a 110.8 Pa, dentro de la banda 80–120 Pa del §10.6.8; si fuesen los 42 Pa de la batería sola, η saldría 0.114, inverosímil; y el Ø500 da 10.75 m/s de descarga y un SFP de 369 J/m³, normales |
| Pérdida de carga del conjunto montado (envolvente + rejilla RS-4) | 10.6.8 | **Media** (era alta). Ya no condiciona el consumo, que es dato. Sigue haciendo falta para el efecto de la escarcha sobre el caudal en el ciclo de acumulación |
| Selección de la batería Frimetal **como evaporador**, aunque sea un único punto | 10.6.9 | **Alta.** Convertiría la tabla 10.12 de extrapolación en interpolación verificada |
| Coeficientes φc, φv, C y m de las correlaciones de placas | 10.5.9 | Media. Sin ellos el submodelo de placas no cierra |
| Criterio de eficiencia de aleta del programa de selección de Frimetal | 10.6.4 | Media. Explicaría la discrepancia del 11 % en U (38.2 calculada frente a 43 de ficha) |
| Composición y conductividad del inoxidable del tubo | 10.6.4 | Baja. Adoptado 15 W/(m·K), serie austenítica |
| Circuitería y distribuidor en operación como evaporador | 10.6.2 | Baja. Necesaria para acotar la maldistribución φmd |
| Resistencia de contacto aleta-tubo con tubo de acero | 10.6.4 | Baja. Valor nominal nulo, sometido a sensibilidad |

## Retoques hacia atrás

A revisar cuando estén los capítulos 10 a 13. **No tocar antes**: los capítulos anteriores
hacen afirmaciones que solo los resultados pueden respaldar.

| Qué | Dónde | Motivo |
|---|---|---|
| Potencia nominal de 12 kW | 19 menciones en 7 capítulos; declaración de origen en §8.2.4 | La capacidad pasa a ser salida del modelo, no premisa. Objetivo: "del orden de 10 kW en refrigeración". Valor efectivo con la configuración cerrada: 10.3 kW. El capítulo 10 ya está corregido |
| η_sa ≈ 0.85 en el cálculo ilustrativo del intercambiador de aire | §5.5 | El valor real de la geometría seleccionada es 0.465. La conclusión cualitativa (el aire domina) se mantiene; el número no |
| Zajacs et al. (2017) como fuente de validación | §7.7.2, tabla 7.5, nivel N3 | Es un estudio de diseño por simulación con EES, no un trabajo experimental. Compararía simulación contra simulación, y el propio §7.7.2 exige fuentes «mutuamente independientes». Reclasificar como verificación cruzada de modelos o retirar. **Registrado en `data/validacion_tabla_7_5.yaml` con estado `NO_ES_FUENTE_DE_VALIDACION`** para que no se cuele por inercia |
| Palm (2008), única fuente de N4 junto con Monfared y Palm (2011) | §7.7.2, tabla 7.5 | No aparece en el material del repositorio. Con ella sin localizar y la otra sin datos, **el nivel N4 —el de la recuperación de ACS, que sostiene H3— se queda sin fuente utilizable** |
| Los trece `[…]` del capítulo 7 | Todo el cap. 7 | Casi todos tolerancias, incluidos los cinco criterios de aceptación de la tabla 7.5. El capítulo propone valores de partida en sus notas de revisión, pero **sugerir no es fijar**, y el propio capítulo advierte de que fijarlos a posteriori es una debilidad detectable |
| Referencia colgante a la "figura 10.4" | Notas finales del capítulo 10 | No existe figura 10.4 en el capítulo 10; probablemente apunta al capítulo 8 |
| Colocación de los pies de tabla | Capítulos 5 y 10 | La plantilla ETSI los sitúa encima de la tabla; actualmente están debajo |

## Cuestiones abiertas de modelado

- **Tolerancia de cierre de balances del §7.7.1.** ~~No está en el material
  disponible.~~ **El capítulo 7 llegó el 21/09/2026** (`docs/cap7_metodologia.md`)
  y el apartado 7.7.1 lo deja en «tolerancia inferior al […] %», esto es,
  tampoco fijado. Las notas de revisión del propio capítulo **sugieren 0.5 %**.
  `circuit.py` adopta 10⁻³, cinco veces más estricto.
  **Decisión pendiente, y tiene consecuencia sobre resultados:** con 0.5 % los
  modos M-3 a M-5, cuyo balance de componente queda en 1.5·10⁻³, pasarían de
  no válidos a válidos. Alinearse con la sugerencia sin mirar eso sería relajar
  un criterio por inercia. Ver el apartado 14 del plan.


- **Capacidad frigorífica declarada y presupuesto de RS-5.** El §10.6.9 declara
  10.3 kW en el equilibrio de M-1 y de ahí sale el presupuesto de carga de 515 g
  del §10.6.10. El catálogo del fabricante da 9.46 kW a T₀ = 2 / T_k = 45 y
  8.97 kW a T_k = 50, esto es, unos 9.28 kW interpolados a los 46.8 °C del
  equilibrio: un 11 % menos. El modelo, resuelto el lazo externo, da 9.43 kW y
  coincide con el catálogo. Con esa capacidad el presupuesto baja a **472 g** y
  todas las fracciones de RS-5 del §10.6.10 se recalculan al alza. **Afecta a
  H4.** Ver `docs/PLAN_PUESTA_EN_MARCHA.md`, apartado 9.

- ~~**Configuración de M-5: el capítulo y la decisión D-1 no dicen lo mismo.**~~
  ~~**Cómo se especifica el control de M-5.**~~
  **CERRADOS los dos el 22/09/2026, y a favor del capítulo.** El circuito de
  climatización solo tiene **fan-coils**: disipar en él el calor residual obliga
  a activarlos, y activarlos calefacta la vivienda. Con una demanda de ACS en
  verano, sin demanda de frío ni de calor, la disipación por esa vía es
  imposible. La decisión D-1 queda **revertida en M-5** y la tabla 10.3 no hay
  que tocarla: los dos intercambiadores de placas en serie, ambos para el ACS.
  Con ello desaparece el reparto y queda una sola forma de especificar el
  control —la consigna de ACS, con el caudal como incógnita—, de modo que el
  modo `M-5-reparto`, el residuo R6 y la consigna de potencia disipada se
  retiran del modelo.

- ~~**Consigna de ACS en M-5**~~ — **DECIDIDA el 22/09/2026 por el autor:**
  **60 °C en los modos con recuperación (M-3 y M-4) y 45 °C en M-5.** El
  dimensionado se hace para 60 °C, como exige la prevención de legionelosis, y
  esa exigencia se cubre donde sale barata: en M-3 y M-4 el ACS se produce
  mientras la máquina climatiza, con el desrecalentador recibiendo gas por
  encima de 120 °C, de modo que el calor de alta temperatura es un subproducto.
  M-5 solo entra cuando no hay demanda de climatización y ahí esa temperatura se
  paga entera. Recogida en `circuit.CONSIGNA_ACS_K` y fijada en
  `tests/test_circuit.py`.

  La sensibilidad que la sostiene:
  Sin servicio simultáneo de climatización, la condensación tiene que situarse
  por encima de la temperatura de salida del ACS, y eso se paga. Medido el
  22/09/2026 en verano (aire a 32 °C, ACS desde 15 °C):

  | Consigna | T_cond | Q al ACS | W_el | COP global |
  |---|---|---|---|---|
  | 60 °C | 57.7 °C | 19.32 kW | 4376 W | 4.41 |
  | 50 °C | 50.6 °C | 19.59 kW | 3898 W | 5.03 |
  | 45 °C | 47.4 °C | 19.72 kW | 3700 W | **5.33** |

  Bajar la consigna de 60 a 45 °C en M-5 sube el COP global un **21 %** y baja la
  potencia eléctrica un 15 %.

  **Lo que el capítulo 8 tiene que declarar**, porque la decisión descansa en
  ello: que la acumulación a temperatura sanitaria queda cubierta por los modos
  con recuperación, y con qué medio se cubre el choque térmico periódico.

- **¿La consigna de ACS es del DEPÓSITO o de la IMPULSIÓN?** Abierta el
  22/09/2026, y afecta al punto de diseño del §10.5.3 y a la consigna de M-5.
  El §10.5.3 ajusta «el caudal del bucle cerrado de ACS **hacia el
  interacumulador**», y un interacumulador es por definición un depósito con
  intercambiador interior: si la carga es por serpentín, el agua del primario
  tiene que salir del desrecalentador **por encima** de la consigna del depósito
  en el valor de la aproximación, y los 60 °C del capítulo son de primario, no
  de servicio. Si la carga es por circulación directa del agua del depósito a
  través de la placa, no hay aproximación y la cuestión desaparece. **Es del
  capítulo 8.**

  Medido el 22/09/2026 sobre el desrecalentador, con la descarga corregida:

  | Primario | Salto | ṁ_ACS | Q recuperado | Margen sobre T_sat | Pared húmeda |
  |---|---|---|---|---|---|
  | 35 → 60 °C (capítulo) | 25 K | 84.8 kg/h | 2463 W | 4.0 K | 30 % |
  | 35 → 67 °C (depósito 60 + 7 K) | 32 K | 63.7 kg/h | **2370 W** (−3.8 %) | **6.4 K** | 18 % |
  | 45 → 67 °C (retorno a 45) | 22 K | 85.7 kg/h | **2193 W** (−11 %) | 11.1 K | 0 % |

  Tres lecturas. La corrección de la impulsión **cuesta poco** —un 3.8 %— y en
  cambio **ensancha el margen de no condensación un 60 %**, que es la variable
  apretada: juega a favor del criterio de dimensionado y casi no toca a H3. **La
  temperatura de RETORNO pesa el triple** que la de impulsión (−11 %), de modo
  que es la que hay que fijar primero. Y con una consigna de depósito baja
  —35 → 52 °C, que sería un depósito a 45— la potencia sube un 4 % pero el
  margen cae a **1.4 K con el 45 % de la pared húmeda**: el desrecalentador se
  queda al borde de condensar dentro.

  **CERRADA el 22/09/2026**: la consigna es del **depósito** —60 °C con
  recuperación y 45 en M-5— y la **impulsión** se deriva sumando una aproximación
  de serpentín de **7 K**, esto es 67 y 52 °C. En `circuit.CONSIGNA_DEPOSITO_ACS_K`
  y `APROXIMACION_ACS_K`.

- ~~**Temperatura de RETORNO del primario de ACS**~~ — **DECIDIDA el 22/09/2026,
  y en tres partes, porque los dos criterios apuntan en direcciones contrarias.**

  El retorno no es un dato de diseño sino una **variable que barre**: con el
  depósito estratificado arranca frío y sube hasta acercarse a la temperatura del
  depósito al final de la carga. Barrido con la impulsión adoptada de 67 °C:

  | Retorno | ṁ_ACS | Q recuperado | Margen sobre T_sat | Pared húmeda |
  |---|---|---|---|---|
  | 25 °C | 51.8 kg/h | **2530 W** | **2.3 K** | 35 % |
  | 30 °C | 57.0 kg/h | 2452 W | 4.3 K | 28 % |
  | **35 °C** | 63.7 kg/h | 2371 W | 6.4 K | 18 % |
  | 45 °C | 85.7 kg/h | 2193 W | 11.1 K | 0 % |
  | 55 °C | 142.8 kg/h | 1993 W | 16.6 K | 0 % |
  | 60 °C | 231.8 kg/h | **1887 W** | 19.7 K | 0 % |

  Para la **potencia recuperada** el peor caso es el retorno caliente; para el
  **criterio de no condensación** es el **frío**, y ahí muerde: a 25 °C quedan
  2.3 K de margen y más abajo se anula. El retorno frío es justo el que sigue a
  un consumo grande de ACS.

  **Decisión:** 35 °C en el punto de diseño, **verificación del criterio en el
  extremo frío (25 °C)** y **suelo de retorno de 30 °C como requisito de la
  instalación** —válvula mezcladora o recirculación en el primario—, que cuesta
  un 3 % de potencia recuperada y protege el criterio. En `circuit.RETORNO_ACS_K`
  y fijada en `tests/test_referencia.py::TestRetornoDelPrimarioACS`.

  **Y dos consecuencias que el capítulo debe declarar**: la potencia recuperada
  **no es constante sino función del estado de carga** —2.5 kW con el depósito
  frío y 1.9 kW casi cargado—, de modo que H3 se argumenta sobre el ciclo y no
  sobre el punto de diseño; y el caudal de primario se dispara al final de la
  carga (232 kg/h para 7 K de salto), de modo que **la bomba apaga sola la
  recuperación** cuando el depósito está cargado.

  **Y una observación para el capítulo 13**: con 19.7 kW al ACS la máquina está
  muy sobredimensionada para producir solo ACS. El punto de M-5 es una capacidad
  más que un régimen: la agregación estacional tendrá que tratarlo con carga
  parcial o con ciclado, no como un punto estacionario más.

- ~~**El disparo del tren extendido puede no tener raíz única.**~~
  **CERRADO el 22/09/2026, y la respuesta es que sí la tiene.** Escaneada la
  función de disparo sobre el intervalo físico completo: 25 puntos, un solo
  cambio de signo y monótona. La multiplicidad no está en el tren. Lo que hacía
  que el arranque en caliente cambiase el resultado —0.470 frente a 0.330— era
  el **escalón de la marcha del serpentín**, corregido el mismo día con el
  recorte en la frontera de fase. Ver el apartado 18 del plan.
  Queda abierto si el arranque en caliente puede reactivarse ahora, que es una
  cuestión de velocidad: hoy sigue desactivado por defecto.

- **Por qué el recalentamiento de M-3 es insensible al vector de incógnitas.**
  Con el escalón del serpentín ya corregido, M-3 es el único modo que no alcanza
  la tolerancia del §10.11.4: se queda en 7.2·10⁻⁵, esto es, 0.02 K de
  recalentamiento por debajo de la consigna. Su residuo **ya no es un escalón**:
  R₄ y R₅ responden a las tres incógnitas y R₂ no se mueve. Apretar el disparo
  del secundario de 10⁻³ a 10⁻⁹ K no cambia nada. La sospecha razonable es que
  el evaporador de placas esté pinzado contra el agua de climatización, de modo
  que la consigna de recalentamiento no sea alcanzable en ese punto; si se
  confirma, procede declararlo y no apretar el método. Apartado 18.4 del plan.

- **La pared ficticia del compresor ya no es una temperatura física.** Con el
  juego reidentificado, `AU_su_n` = 0.0056 W/K y `AU_amb` = 1.51 W/K, ambos
  prácticamente en su cota inferior: el calentamiento en la aspiración se anula
  y la pared se sitúa en 210 °C, por encima de la descarga, de modo que el
  modelo predice que la pared calienta el gas de descarga en 83 W. El balance
  de la ec. 10-8 cierra y la temperatura de descarga coincide con el catálogo,
  pero T_w no puede interpretarse ya como temperatura de una pared real, ni
  apoyarse en ella la hipótesis M4.


- **Ecuación 10-24, parámetro Z.** `Z = x·cp,v·(dT_sat/dh)` se anula
  idénticamente para un fluido puro a presión constante, de modo que la
  corrección de pared húmeda del §10.5.7 no hace nada aplicada a NH₃. Procede
  del método de Bell-Ghaly, formulado para mezclas. Hace falta una formulación
  de Z válida para un fluido puro; hasta entonces el soporte cuantitativo de H3
  no está disponible. El modelo adopta Z = 1, el límite conservador.

- **Ángulo de corrugación de las placas.** Identificado en 71.6° sobre la pérdida
  de carga del punto de selección del 27-30H, y **adoptado** para el 16-10H como
  hipótesis de familia: misma gama AlfaNova, misma designación H de canal. Es la
  hipótesis razonable y es la que el modelo aplica, pero sigue siendo hipótesis:
  el 16-10H no tiene ficha de selección y por tanto no hay pérdida de carga sobre
  la que identificarlo.

  **Lo que depende de él, medido el 22/09/2026** sobre el punto de diseño del
  §10.5.3, recorriendo el ángulo:

  | β | ṁ_ACS para 60 °C | Q recuperado | Margen sobre T_sat |
  |---|---|---|---|
  | 45° | 92.0 kg/h | 2673 W | **9.8 K** |
  | 60° | 97.8 kg/h | 2844 W | 5.3 K |
  | 71.6° (adoptado) | 99.2 kg/h | 2883 W | **4.3 K** |

  La potencia recuperada varía un 8 % en toda la banda —H3 es robusta por ese
  lado— pero **el margen de no condensación se duplica largamente**. Es el
  parámetro que más pesa sobre ese margen y debe recorrerse en la sensibilidad
  del cap. 11.

- **DATOS DEL Alfa Laval CB16-10H: NO son de este equipo.** Consultados el
  22/09/2026 y **rechazados**, y se registran aquí para que no vuelvan a entrar
  por inercia. La gama **CB es soldada por COBRE** —la propia descripción habla
  de puntos de contacto soldados por cobre— y **RS-1 la excluye**: es exactamente
  la razón por la que la tesis selecciona la gama AlfaNova, soldada por fusión y
  100 % inoxidable. Sus cifras difieren además de las del catálogo AlfaNova que
  el repositorio sí tiene: paso 2.16 mm frente a **2.06**, volumen por canal
  0.027 L frente a **0.0235**. El ángulo de 45° que se le atribuye contradice
  también el 71.6° identificado sobre el 27-30H de la misma gama y designación,
  que procede de una pérdida de carga medida. No se adopta nada de ahí.

- **§10.5.3, coeficiente de 1433 W/(m²·K).** Calculado con el paso de placa sin
  corregir (1.06 mm); con el corregido (2.09 mm) Martin da 716. Y los
  61 W/(m²·K) del contraste con el AlfaNova 27-30H no se reproducen con Martin
  bajo ningún β. Ver `docs/PLAN_PUESTA_EN_MARCHA.md`, apartado 8.

- **Temperatura de descarga del compresor y tolerancias del §10.4.5.** Con los
  46 puntos de catálogo ya en el repositorio, los parámetros de la tabla 10.4
  dan ±4.5 % en caudal, ±9.8 % en potencia al eje y ±16.8 K en temperatura de
  descarga, frente al ±2.7 % / ±6.6 % / ±10.5 K declarados. El error de T_dis es
  un sesgo sistemático de +14 K, no dispersión. Una reidentificación con la
  misma estructura y la misma función objetivo cumple los tres. El fabricante
  publica 122.2 °C a T₀ = 2 / T_k = 45, frente a los 140.4 °C que el §10.6.9
  usa y el §10.5.3 toma como entrada del desrecalentador. **Afecta a H3.** Ver
  `docs/PLAN_PUESTA_EN_MARCHA.md`, apartado 6.

- **Rendimientos del motor externo y de la transmisión.** No figuran en el
  capítulo ni se han localizado. **Adoptados** el 16/09/2026 por decisión del
  autor: η_motor = 0.97, η_transmisión = 0.98, marcados en el fichero de datos
  como `procedencia: adoptado_sin_fuente`. Entran en el denominador de COP y EER
  por la ec. 10-10 y por exigencia de UNE-EN 14511, luego en H1, y su separación
  es lo que da contenido cuantitativo a H6. El producto adoptado (0.951) supone
  un 4.9 % de pérdida electromecánica, frente al 12–15 % típico de un motor
  asíncrono de la gama que corresponde a 2.4 kW al eje (IE3/IE4 de 2.2–3 kW,
  0.87–0.90). Diferencia en el denominador: ~11 %. Deben entrar en la
  sensibilidad del §7.11 y declararse como hipótesis, no como dato, al reportar
  EER y COP en el capítulo 12. Lo que resolvería el punto es la ficha del motor
  y de la transmisión efectivamente seleccionados.

- **Coherencia de correlaciones de ebullición.** El §10.5.5 adopta Chen (1966) para placas y
  el §10.6.5 una formulación tipo Gungor-Winterton para tubos. Son de la misma familia de
  superposición pero con factores F y S distintos. Debe declararse explícitamente en el
  texto, o unificarse.
- **Constantes numéricas de las ecuaciones 10-29 y 10-30.** Las formas estructurales son las
  estándar de sus familias, pero las constantes deben citarse de la fuente primaria
  (Dobson y Chato 1998; Gungor y Winterton 1986), no darse por buenas.
- **Sesgo conocido en U de la batería.** El modelo reconstruye 38.2 W/(m²·K) frente a los 43
  de la ficha. Declarado como conservador y sin corregir mediante factor de ajuste. El
  capítulo 11 debe resolverlo por contraste del método de aleta equivalente.
