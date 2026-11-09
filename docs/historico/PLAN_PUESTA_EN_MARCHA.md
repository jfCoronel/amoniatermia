# Plan de puesta en marcha del modelo

> **Numeración.** Este documento cita el capítulo 10 en su revisión previa a la v30 y el
> capítulo 7 en su v1. La correspondencia con las versiones vigentes
> (`docs/Capitulos_pdf/`) está en `docs/CORRESPONDENCIA_CAP10.md`. No se renumera: citar la
> versión que se auditaba es parte de lo que el documento registra.

Auditoría del código existente frente al capítulo 10 y plan de trabajo derivado.
Fecha: 16 de septiembre de 2026.

Complementa a `docs/guia_implementacion.md`, que sigue siendo válida en su
estructura de fases. Este documento añade lo que la guía no recoge: las
**discrepancias entre lo que hace el código y lo que dice el capítulo 10**,
localizadas fichero y línea, y reordena el trabajo en función de ellas.

Criterio de CLAUDE.md aplicado: el capítulo manda sobre el código; las
discrepancias se reportan, no se resuelven en ninguno de los dos sentidos.

---

## 1. Estado de partida

> **Nota.** Este apartado describe el estado en el momento de la auditoría y se
> conserva como tal. Para el estado actual, ver las marcas de estado del
> apartado 3: la fase A está cerrada desde el 16 de septiembre de 2026, de modo
> que los puntos D3, D12, D14, D15, D16, D17 y D18 ya no describen el código.

El paquete instala y los 52 tests pasan (37 verdes, 15 `skip`). Existen y
funcionan: `props`, `units`, `geometry` (placas y compresor), el registro de
correlaciones con cinco familias, cuatro correlaciones de fracción de huecos
más Premoli, el compresor semiempírico, el intercambiador de placas por
volúmenes finitos y la válvula de expansión.

No existe: `air_hx`, `four_way_valve`, líneas de conexión, `circuit`,
indicadores energéticos, indicadores exergéticos, submodelo de ventilador,
`validation/`, memorización de propiedades y desescarche.

Un hecho que condiciona todo lo demás: **ningún módulo lee `data/*.yaml`**. Los
parámetros identificados del compresor, la geometría de las placas y la
reconstrucción de la batería están escritos en los ficheros de datos y no
entran en el modelo. Los `null` de datos pendientes no pueden fallar de forma
explícita, como exige CLAUDE.md, porque nada los invoca.

---

## 2. Discrepancias entre el código y el capítulo 10

### 2.1. De fondo: el código contradice una decisión del capítulo

| # | Discrepancia | Dónde | Apartado |
|---|---|---|---|
| D1 | **Condensación en placas por Reynolds equivalente.** El §10.5.6 descarta expresamente ese enfoque —«y no mediante un enfoque de convección forzada con número de Reynolds equivalente»— en favor de la teoría de película de Nusselt (ec. 10-21) con los factores φc y φv. El código lo tiene como correlación registrada y como **valor por defecto** del componente. | `correlations/condensation.py:24`, `components/plate_hx.py:71` | 10.5.6 |
| D2 | **Compresor de 7 parámetros; el capítulo exige 9.** `η_ic` no existe en ninguna parte del código. `r_v` no es parámetro identificado sino dato geométrico fijo, con valor 2.8 frente al 2.0 identificado. La compresión hasta `v_in` se resuelve isoentrópica pura, sin la corrección `h_ad = h₁ + (h_ad,s − h₁)/η_ic`, y `P_ad` se evalúa en el estado ideal y no en el real. | `components/compressor.py:22-52,114-118`, `geometry.py:116` | 10.4.2, 10.4.5 |
| D3 | **El conjunto de correlaciones de carga no es el de la tabla 10.13.** El componente fija en código `("homogeneous", "zivi", "rouhani_axelsson", "premoli")`: deja fuera Lockhart-Martinelli, que sí está en la tabla, e incluye Premoli, que no. | `components/plate_hx.py:267` | 10.9.2, 10.6.10 |
| D4 | **Ebullición: principal y alternativa invertidas.** El §10.5.5 adopta la superposición **aditiva** de Chen (ec. 10-19). El código registra la asintótica como «formulación PRINCIPAL» y la aditiva como variante, y así entra por defecto en el componente. | `correlations/boiling.py:73,96`, `components/plate_hx.py:70` | 10.5.5 |
| D5 | **La ecuación 10-24 no se aplica.** `bell_ghaly_desuperheat` está registrada pero no la invoca nadie: el componente **cuenta** las celdas con pared húmeda pero resuelve todas como monofásicas. El §10.5.7 es el apartado sobre el que descansa H3. | `correlations/condensation.py:39`, `components/plate_hx.py:170-173` | 10.5.7 |
| D6 | ✅ **RESUELTA** el 17/09/2026. Ec. 10-25 completa, con el reparto en el resultado. Hallazgo: en el condensador la gravitatoria **domina por un factor de 11 e invierte el signo** del total. Ver apartado 8. | `components/plate_hx.py`, `correlations/friction.py` | 10.5.8 |
| D7 | **Correlación monofásica.** El punto de diseño del desrecalentador del §10.5.3 se resolvió con **Martin (VDI Heat Atlas)**. El código tiene un `chevron_generic` con C y m inventados y marcados como provisionales. Martin no está implementada. | `correlations/singlephase.py:17` | 10.5.4, 10.5.3 |
| D8 | ✅ **RESUELTA** el 17/09/2026. ΔT_lm adoptada; la aritmética queda como alternativa registrada. Medida, la diferencia es **< 0.05 % con 20 volúmenes**: era inocua, pero no estaba declarada ni cuantificada. | `components/plate_hx.py` | 10.5.1 |
| D9 | **Fuga interna sin rama crítica.** El §10.4.2 pide tobera equivalente «evaluada en régimen crítico o subcrítico según la relación de presiones». El código implementa solo la forma subcrítica incompresible. | `components/compressor.py:87` | 10.4.2 |

### 2.2. Entre los ficheros de datos y el capítulo

| # | Discrepancia | Detalle |
|---|---|---|
| D10 | ✅ **RESUELTA** el 16/09/2026. Las denominaciones del fichero de datos eran erróneas. Las correctas son **AlfaNova 27-30H** (climatización) y **AlfaNova 16-10H** (desrecalentador), como declara la tabla 10.6. Área, volumen, presión y punto de diseño sí eran correctos. Corregidas en `data/placas_alfanova.yaml` y en `CLAUDE.md`. |
| D11 | **Exponente politrópico de reexpansión.** `data/compresor_bock_f2.yaml:44` da `n_politropico: 1.30`. El código y la guía de implementación lo fijan en 1.20. El capítulo no lo declara en ninguna parte. |
| D12 | **Geometría de placas incompleta en el YAML.** Faltan `b`, `beta_c`, `phi`, `L_w` y `L_p` del condensador; del desrecalentador el capítulo da b = 2.09 mm y Φ = 1.15 (estimado) en el texto del §10.5.3, pero no están en el fichero de datos. Sin ellos `PlateGeometry` se construye con los valores por defecto del dataclass, que son inventados. |
| D13 | ✅ **RESUELTA** el 17/09/2026. No son el mismo número mal calculado: son **área proyectada y área desarrollada**. Convenio adoptado: desarrollada, coherente con D_h = 2b/Φ y con Martin, y es además el que reproduce el punto de diseño del §10.5.3 (−3.5 % frente a −9.0 %). Ver apartado 8. |

### 2.3. Incumplimientos de las reglas de CLAUDE.md

| # | Incumplimiento | Medida |
|---|---|---|
| D14 | **`PropsSI` en el lazo interno.** `Fluid.p_reduced()` llama a `p_crit`, que es una property que ejecuta `CP.PropsSI("pcrit", ...)` en cada invocación. `plate_hx._alpha_ref` la llama una vez por celda y por iteración interna. Medido en este equipo: **131 µs/llamada**, frente a 5.2 µs de un `AbstractState` reutilizado. Es 25× el coste del estado reutilizado y supera al propio `PropsSI` de la tabla 10.16. | `props.py:148-156`, `plate_hx.py:82` |
| D15 | **Los datos pendientes no pueden fallar.** No hay cargador de `data/*.yaml`, luego los `null` de φc, φv, C, m, curva del ventilador y selección como evaporador no se invocan nunca y el modelo no puede fallar de forma explícita ante ellos. | — |
| D16 | **No hay marcado de «fuera de rango».** Ninguna correlación registrada declara su base experimental, y no existe mecanismo para marcar un resultado como extrapolado. El test que lo exige está en `skip`. | `tests/test_referencia.py:196` |
| D17 | **Correlaciones de carga fijadas en código.** El conjunto de la banda de carga está escrito literalmente en el componente, contra el requisito de intercambiabilidad por nombre del §10.13.4. | `plate_hx.py:267` |
| D18 | **Procedencia incompleta.** `PropertyProvenance` registra versión de CoolProp, backend y fluidos. Faltan el hash de git, las correlaciones activas y los parámetros de entrada — tres de los cinco elementos del §10.13.6. | `props.py:162` |

### 2.4. Verificación numérica de la tabla 10.13 — resuelta

Contrastadas las correlaciones implementadas contra los valores de referencia de
la tabla 10.13 (NH₃ condensando a 45 °C, x de 1 a 0, promedio uniforme en x,
3.8 L):

| Correlación | α calculada | α tabla 10.13 | Masa calculada | Masa tabla 10.13 |
|---|---|---|---|---|
| `homogeneous` | 0.930 | 0.930 | 200.3 g | 200 g |
| `zivi` (deslizamiento) | 0.844 | 0.844 | 382.6 g | 382 g |
| `lockhart_martinelli` | 0.880 | 0.878 | 306.4 g | 312 g |
| `rouhani_axelsson` (flujo de deriva) | **0.824** | **0.865** | **426.3 g** | **339 g** |
| `premoli` | 0.837 | — (no está en la tabla) | 397.6 g | — |

Tres de las cuatro reproducen. Dos conclusiones:

- El promedio de la tabla 10.13 es **uniforme en título**, no ponderado por
  longitud. Conviene declararlo en el capítulo, porque no es indiferente.
- La fila de flujo de deriva no coincidía.

**Resuelto por el autor el 16 de septiembre de 2026.** No era una variante de
Rouhani-Axelsson: esa fila no se calculó con Rouhani-Axelsson en absoluto, sino
con la correlación de **Smith (1969) con K = 0.4**, un modelo de flujo separado
con arrastre que no depende del flujo másico. El §10.9.2 describe la cuarta
formulación como la que «incorpora la distribución radial de fases y el efecto
del flujo másico», descripción que corresponde inequívocamente a
Rouhani-Axelsson; el número tabulado no.

| Formulación | α medio | ρ̄ | Carga |
|---|---|---|---|
| Smith K = 0.4 (lo que estaba en la tabla) | 0.865 | 89.2 kg/m³ | 339 g |
| **Rouhani-Axelsson, C₀ = 1 + 0.12(1−x)** (adoptada) | **0.824** | **112.1 kg/m³** | **426 g** |
| Rouhani-Axelsson, C₀ = 1 + 0.2(1−x) | 0.800 | 125.4 kg/m³ | 477 g |

**Efecto sobre H4.** La banda pasa de 200–382 g a **200–426 g**, la dispersión
de factor 1.9 a 2.1, y la batería consume hasta el **83 %** del presupuesto de
515 g. En el extremo desfavorable quedan **89 g** para compresor, los dos
intercambiadores de placas, válvula, valvulería y líneas. Eso ya no es
«ajustado»: probablemente exige un receptor de muy bajo volumen y un rediseño
del inventario.

**Y un matiz que refuerza el argumento en vez de debilitarlo.**
Rouhani-Axelsson es la única de las cuatro que depende del flujo másico, y a
G = 48 kg/(m²·s) predice mucha más retención de líquido; a G = 200 convergería
con Smith (338.7 g frente a 339, verificado). Ese flujo másico es bajo
precisamente porque el elevado calor latente del amoníaco reduce el caudal
circulante. Es decir: **la correlación físicamente más apropiada para este caso
es la que más carga predice, y lo es por la misma razón por la que el amoníaco
tiene el problema de carga.**

**Estado en el capítulo (v25).** La fila de flujo de deriva de la tabla 10.13
pasa a 0.824 / 112.1 kg/m³ / 426 g. El §10.6.10 declara que el cumplimiento de
RS-5 **queda en entredicho** y remite al capítulo 12 tres vías: reducir el
volumen del receptor y de las líneas; elevar la temperatura de condensación
asumiendo el coste de EER que el §10.6.9 ya cuantifica; o revisar la geometría
del serpentín hacia menor volumen interno por unidad de área.

**Consecuencia sobre la selección de la batería.** El §10.6.1 descartó el
microcanal por falta de disponibilidad comercial verificada, pero ese descarte se
hizo con una carga aparente de 339 g, no de 426. La pregunta ya no está cerrada.
Antes de reabrirla conviene tener el dato del modelo y no el de la tabla: ver el
apartado 5.

En el código: `rouhani_axelsson` es la familia de flujo de deriva de la banda;
`smith` queda registrada por trazabilidad del valor anterior y porque es
estructuralmente distinta; `zuber_findlay` permite recorrer C₀ en la
sensibilidad. `test_referencia.py` fija los tres hechos: la tabla corregida, la
procedencia del valor antiguo y la convergencia con G.

### 2.5. Observaciones editoriales sobre el capítulo

- Las ecuaciones 10-43, 10-44 y 10-45 emplean `x` para designar la **fracción de
  huecos** en el miembro izquierdo, colisionando con el título de vapor del
  miembro derecho. La ec. 10-43 escrita literalmente (`ρ̄ = x ρ_v + (1−x) ρ_l`)
  es incorrecta: debe ser α. El código la implementa bien.
- La ecuación 10-9 es ambigua en signos: escrita tal cual exige que `Q̇_su` y
  `Q̇_ex` se midan como calor **hacia la pared**, lo que contradice el convenio
  del §10.1.2. El código resuelve el balance físicamente correcto.
- La tabla 10.7 y el §10.4.4 siguen hablando de «los 7 parámetros» del
  compresor donde el §10.4.5 ya establece 9.

---

## 3. Plan de trabajo

Orden pensado para llegar cuanto antes a un resultado verificable: el punto de
equilibrio de M-1 del §10.6.9 (T_cond = 46.8 °C, 13.2 kW rechazados, 10.3 kW
frigoríficos). Ese número es el criterio de «modelo en marcha».

### Fase A — Saneamiento y cimientos ✅

Completada el 16 de septiembre de 2026. 76 tests en verde, 10 `skip`, 1 `xfail`.

| | Estado | Tarea | Cierra |
|---|---|---|---|
| A1 | ✅ | Módulo `data.py`: carga de `data/*.yaml` y construcción de los objetos de geometría y parámetros. `require()` **lanza `MissingData`** ante un `null`; obtener un pendiente sin fallar exige pedirlo con `optional()`, que es una declaración de intención visible. `pending_report()` enumera los 16 datos pendientes por adelantado. | D15, D12 |
| A2 | ✅ | `p_crit`, `T_crit` y `M` cacheados en la construcción de `Fluid`. **Medido: 425 → 147 ms** por `solve()` del intercambiador de placas, ×2.9. Test de regresión que prohíbe `PropsSI` en el camino caliente por monkeypatch, no por tiempos. | D14 |
| A3 | ✅ | `Validity` y `CorrelationInfo` en el registro; `ExtrapolationLog` agrega excursiones por (familia, nombre, variable) y la marca viaja en `HXResult.extrapolated`. Distingue «fuera de rango» de «base sin declarar», que hoy es el caso mayoritario. | D16 |
| A4 | ✅ | `TABLA_10_13` como conjunto canónico y `void_fraction_names` configurable en el componente. Discrepancia del flujo de deriva localizada y documentada, no resuelta. | D3, D17 |
| A5 | ✅ | `PropertyProvenance` con los cinco elementos del §10.13.6, `is_complete()` que rechaza un árbol de git sucio y `write_json()`. | D18 |
| A6 | ✅ | `test_referencia.py`: la geometría de la batería se lee del fichero de datos en lugar de repetirse en el test, y las cuatro correlaciones de carga se contrastan contra la tabla 10.13 (tres pasan, la de flujo de deriva es `xfail(strict)` con la discrepancia por motivo). | §10.13.5 |

**Hallazgo colateral, ya corregido.** El registro de extrapolación, al
ejecutarse sobre un condensador de placas, revelaba 275 evaluaciones de la
correlación de **ebullición**. La causa estaba en `plate_hx._alpha_ref`: la rama
se elegía por el signo de `q_flux_guess`, que la iteración interna inicializa a
0.0, y la condición `>= 0.0` mandaba la primera iteración de cada celda a la
rama de evaporación aunque el componente estuviese condensando.

No era solo fragilidad: contaminaba el registro de extrapolación, que es un
requisito de reporte de los §10.6.5 y §10.13.4, y un registro con 275 entradas
espurias es un registro en el que ya nadie mira.

La corrección no fue cambiar `>= 0.0` por `> 0.0` —eso solo desplaza el problema
al caso degenerado— sino **dejar de derivar el régimen de una incógnita del
lazo**:

1. Se despacha por el papel del componente en el modo activo. El §10.3 ya fija
   si cada intercambiador condensa o evapora en cada uno de los cinco modos, y
   esa información existe antes de iterar. El papel pertenece al modo y no al
   objeto, de modo que `solve(..., role=...)` lo sobreescribe: será `circuit.py`
   quien lo pase.
2. Sin papel declarado, el respaldo es el signo de (T_sec − T_sat), disponible
   en la primera iteración y físicamente correcto. Da el mismo resultado.

Como salvaguarda añadida, el registro anota **solo la marcha convergida**: ni
las iteraciones internas sobre q″ ni las marchas del lazo de disparo, que si no
quedarían registradas como si fueran resultados. Verificado: exactamente 2N
entradas para N celdas, frente a las ~420 de antes.

### Fase B — Compresor a nueve parámetros ✅

Completada el 16/09/2026, con los 46 puntos de catálogo ya en el repositorio.

| | Estado | Tarea | Cierra |
|---|---|---|---|
| B1 | ✅ | `η_ic` y `r_v` son ya parámetros identificados. `h_ad = h₁ + (h_ad,s − h₁)/η_ic` con la presión de la etapa isócora evaluada en el estado **real** (v_in, h_ad) mediante `Fluid.update_DH`. | D2 |
| B2 | ✅ | Tobera de fuga isoentrópica con rama crítica. Con NH₃ (γ ≈ 1.34) la relación crítica es ≈1.84 y el compresor opera en M-1 en torno a 3.85: la fuga está **bloqueada en todo el dominio de trabajo**, de modo que la forma incompresible anterior la sobreestimaba sistemáticamente. | D9 |
| B3 | ✅ | Los nueve valores se cargan del YAML. `n = 1.30`, el del fichero de datos. | D11 |
| B4 | ✅ | `identify()` sobre nueve parámetros, peso ×4 en T_dis y contra **potencia al eje**. `eta_motor` y `eta_transm` pasan al fichero como `null`: el modelo falla al pedir potencia eléctrica. | 10.4.4 |
| B5 | ✅ | Contrastes conectados, y uno de ellos abre una discrepancia (apartado 6). | 10.4.5 |

**Los 46 puntos ya están en el repositorio**, aportados el 16/09/2026 como
`COMPRESOR_BOCK_F2_NH3.xlsx` y transcritos a
`data/compresor_bock_f2_catalogo.csv` para que el historial produzca diferencias
legibles. Con ellos la identificación del §10.4.5 pasa a ser **reproducible**,
que es lo que prometen el §7.12 y el anexo E. El caudal se deduce de la
capacidad con el convenio de ensayo de la hoja LEAME (recalentamiento 1 K,
subenfriamiento nulo), y esa deducción se verifica reproduciendo los 270.9 kJ/kg
del punto de referencia del fabricante.

### Fase C — Intercambiador de aire

El bloque mayor y el que M-1 necesita: en M-1 la batería es el condensador, de
modo que sin ella no hay punto de equilibrio que resolver.

| | Tarea |
|---|---|
| C1 | `geometry.FinnedCoilGeometry` con la reconstrucción del §10.6.1 y su verificación contra la ficha (tabla 10.9). Es la condición previa al anclaje: un ajuste sobre geometría mal reconstruida absorbe el error geométrico dentro del coeficiente. |
| C2 | Familia `airside` en el registro, con la correlación de Colburn anclada (C₁ = 0.507, C₂ = −0.42) y su rango de validez Re ∈ [4190, 5512] declarado y marcado. |
| C3 | Eficiencia de aleta anular equivalente en tresbolillo equilátero, seca y húmeda, y resistencia de pared de inoxidable. Contrastes: 0.447 / 0.465 seca, 0.337 / 0.358 húmeda, U = 38.2 W/(m²·K), reparto 72.8 / 3.9 / 23.3 %. El sesgo del −11 % frente a la ficha se conserva sin factor de ajuste. |
| C4 | Familias de correlaciones **de tubo**, separadas de las de placas: condensación con criterio de transición anular/estratificado (Fr_so ≷ 20, ec. 10-31) y ebullición tipo Gungor-Winterton (ec. 10-33/34). Deben ser inconfundibles con las de placas: si un intercambiador de placas puede elegir por nombre una correlación de tubo, la banda de incertidumbre deja de significar nada. |
| C5 | Superficie húmeda por potencial entálpico, Le = 1, con reporte separado de contribución sensible y latente. |
| C6 | Escarcha: el componente resuelve limpio y **reporta el dominio** de formación (temperatura superficial y caudal de condensado). La penalización de la ec. 10-37 se aplica en la agregación estacional, no aquí. |
| C7 | Submodelo de ventilador. ~~Falla mientras la curva sea `null`~~ → **cerrado 17/09/2026**: consumo constante de 780 W, dato de catálogo de la serie CBN a alta velocidad. La vía por ΔP se conserva para el barrido del ap. 7.11. |
| C8 | `charge()` sobre segmentos, contrastado con la tabla 10.13. |
| C9 | Diagnóstico de régimen: fracción del serpentín en condensación anular frente a estratificada. |

### Fase D — Placas al nivel del capítulo ✅

| | Tarea | Cierra |
|---|---|---|
| D1 | Condensación por película de Nusselt con φc y φv. Ambos son `null` en los datos: el componente debe fallar al invocarlos. `equivalent_Re` se conserva registrada como alternativa para la sensibilidad del cap. 11, pero deja de ser el valor por defecto. | D1 |
| D2 | Chen aditivo como principal; asintótica como alternativa. La correlación específica de NH₃ en placas (vacío V-1) sigue pendiente, y mientras lo esté la banda de ebullición tiene dos formulaciones que comparten Cooper y los factores F y S: hay que declararlo. | D4 |
| D3 | Implementar Martin (VDI) para el régimen monofásico, que es la que se usó en el §10.5.3. C y m de `chevron_generic` son `null` en los datos. | D7 |
| D4 | Aplicar la ec. 10-24 en el desrecalentador, no solo diagnosticarla. Es H3. | D5 |
| D5 | Pérdida de carga completa: friccional, aceleración, gravitatoria y multiplicador bifásico. | D6 |
| D6 | Decidir ΔT_lm frente a ΔT aritmética y declararlo. | D8 |
| D7 | Fijar el convenio de área desarrollada frente a área declarada. | D13 |

### Fase E — Circuito y modos ✅

Cerrada el 17/09/2026. `src/amoniatermia/circuit.py`, contrastes en
`tests/test_circuit.py` y en `TestEquilibrioM1` de `tests/test_referencia.py`.

| | Estado | Tarea | Resultado |
|---|---|---|---|
| E1 | ✅ | Sistema de residuos R₁–R₅ con vector de incógnitas dimensionado por modo. | `ModeSpec` declara incógnitas y residuos; `Circuit.active_system` los compone. M-5 con reparto explícito instancia **cinco** (D-1, opción 2). |
| E2 | ✅ | Topologías de los cinco modos, con el tren extendido de M-1/M-2 y el cambio de familia de correlaciones del desrecalentador. | El disparo del §10.5.8 se hace sobre el **tren completo**: la temperatura del agua en la unión no es dato de ninguno de los dos intercambiadores. |
| E3 | ✅ | Inicialización por parámetros agrupados y continuación sobre el parámetro barrido. | `initial_guess` (pinzamientos supuestos) y `sweep` (arranque en la solución anterior). |
| E4 | ✅ | Verificaciones independientes: balances de masa y energía, entropía positiva, registro de los no convergidos. | `CircuitSolution.checks`; `valid` exige las verificaciones además del residuo. Los fallos quedan en `Circuit.failures` con su contorno y su residuo. |
| E5 | ⚠️ | **Hito.** Reproducir el equilibrio de M-1: 46.8 °C, 13.2 kW, 10.3 kW. | **El equilibrio se resuelve; los tres valores no se reproducen.** El modelo da 45.7 °C, 11.7 kW y 9.4 kW, y coincide con el catálogo del fabricante. Ver apartado 9. |

Tres desviaciones respecto del §10.11 que se declaran y no se resuelven en
silencio:

1. **R₃ no es residuo del lazo externo.** La tabla 10.14 lo lista y el §10.11.1
   lista T_w entre las variables de iteración, pero `SemiEmpiricalCompressor`
   ya resuelve el balance de la pared ficticia en su lazo propio: llevarlo
   también al lazo externo daría un sistema singular. Se conserva como
   **verificación** —`checks["R3_pared_compresor"]`— y debe ser nulo.
2. **R₅ se cierra sobre el caudal de ACS, no sobre su temperatura.** El §10.11.1
   incorpora la temperatura de salida del agua del desrecalentador como
   variable de iteración; esa temperatura es la variable de disparo de la marcha
   en contracorriente del §10.5.8 y el componente ya la resuelve dentro. Lo que
   queda libre en el lazo externo es el caudal que hace que alcance la consigna.
   Misma ecuación de cierre, incógnita distinta.
3. **A_ef se elimina en forma cerrada.** La ec. 10-27 es lineal en el área
   efectiva, de modo que R₁ tiene solución exacta. No es comodidad: con
   subenfriamiento de consigna nulo —la condición del §10.6.9— la entrada de la
   válvula cae **exactamente en la frontera de fase**, donde la densidad de la
   ec. 10-27 es discontinua. Medido en M-1, R₁ recorre 2·10⁻² en 0.01 K de
   temperatura de condensación mientras R₄ recorre 9·10⁻³ en 0.1 K: el jacobiano
   queda mal condicionado aunque el sistema tenga solución. `eliminate_A_ef=False`
   recupera el vector literal del §10.11.1 para poder medir la diferencia.

### Fase F — Indicadores

COP, EER y COP global con el **consumo de ventilador dentro del denominador**,
como exige UNE-EN 14511. Exergía específica, destrucción por componente,
cocientes y_D,k, η_II, y el indicador auxiliar que separa la irreversibilidad de
compresión de la pérdida de conversión electromecánica, que es lo que da
contenido a H6.

### Fase G — `validation/`

Umbrales de la tabla 7.5 escritos **antes** de ejecutar nada. Conviene
adelantarlo a la fase A si el calendario lo permite: el argumento del §7.12 es
que la decisión quede fechada en el historial, y ese valor se pierde si se hace
al final.

### Fase H — Rendimiento y campañas

Backend tabular solo tras cuantificar su error — y sobre los pares de entrada
que el modelo usa de verdad (PH y PQ), no solo PT como hace hoy
`backend_deviation_report`. Memorización de propiedades del §10.10 con su
tolerancia declarada. Campañas parametrizadas con procedencia adjunta.

---

## 5. La cifra de 426 g no era la del modelo — resuelto

La tabla 10.13 integra suponiendo **bifásico en los 3.8 L completos**, con el
título recorriendo de 1 a 0. En M-1 eso no es lo que ocurre: la batería recibe el
gas directamente de la descarga a 140.4 °C (§10.6.9), de modo que una parte del
serpentín desrecalienta, y puede haber subenfriamiento a la salida. Ninguna de
las dos zonas contiene mezcla bifásica, y sus densidades difieren de la media
bifásica en sentidos opuestos.

### Resultado de la integración por segmentos

Ejecutado el 16/09/2026 con `components/air_hx.py` sobre el equilibrio de M-1
del §10.6.9: T_cond = 46.8 °C, entrada a 140.4 °C, aire a 35 °C y 7600 m³/h.
El caudal de refrigerante no se impone: se busca el que hace que la
condensación sea **exactamente completa**, que es la condición que el ciclo
necesita para que la válvula de expansión reciba líquido.

Condensación completa con subenfriamiento nulo: **m = 35.3 kg/h, Q = 13.11 kW**
(el §10.6.9 declara 13.2 kW), con el 21 % del volumen interno desrecalentando.

| | Carga (banda de las cuatro correlaciones) | % del presupuesto de 515 g |
|---|---|---|
| Tabla 10.13 (bifásico en los 3.8 L) | 200 – 426 g | 39 – 83 % |
| **Integración por segmentos, subenfriamiento nulo** | **171 – 316 g** | **33 – 61 %** |

La tabla 10.13 **sobreestima en un 26 %** el peor caso, porque supone mezcla
bifásica en todo el volumen. En M-1 no la hay: la batería recibe el gas
directamente de la descarga a 140.4 °C, sin desrecalentador intermedio, y una
quinta parte del serpentín contiene vapor sobrecalentado a 14 kg/m³.

### Pero el subenfriamiento decide, y no es una propiedad del componente

| Subenfriamiento | Volumen anegado | Carga | % de RS-5 |
|---|---|---|---|
| 0 K | 0 % | 171 – 316 g | 61 % |
| 7.3 K | 8 % | 333 – 464 g | 90 % |
| 9.5 K | 13 % | 433 – 556 g | **108 %** |
| 10.6 K | 18 % | 535 – 649 g | 126 % |

El líquido está a 571 kg/m³: 41 veces la densidad del vapor y 5 veces la media
bifásica. **Trece centésimas de volumen anegado bastan para que la batería sola
agote el presupuesto completo de RS-5.**

### Conclusión sobre la selección de la batería

La pregunta que el §10.6.10 deja abierta no se responde con la geometría del
serpentín. Con la Frimetal tal cual, operando sin líquido acumulado, la carga es
de 316 g en el peor caso de correlación, un 61 % del presupuesto, y RS-5 se
cumple con margen. Lo que lo pone en riesgo es el anegado del condensador, que
depende de la carga total del sistema y de si hay receptor, no del componente.

De las tres vías que el §10.6.10 remite al capítulo 12, esto reordena
prioridades: **la primera —volumen de receptor y líneas— no es una más, es la
que gobierna el resultado**, porque es la que determina si el condensador opera
anegado o drenado. Elevar la temperatura de condensación y revisar la geometría
del serpentín actúan sobre un término que, con subenfriamiento nulo, ya cumple.

Reabrir la selección de la Frimetal frente al microcanal por los 426 g habría
sido actuar sobre la variable equivocada.

### Lo que este resultado todavía no soporta

- **U es un 11 % baja** por el sesgo conocido del §10.6.4, no corregido. El
  modelo da 13.11 kW donde el §10.6.9 da 13.2, y necesita menos caudal para
  condensar por completo. Resolver el método de aleta equivalente (cap. 11)
  moverá el caudal de condensación completa, no la conclusión.
- **La zona bifásica usa el coeficiente agregado de ficha** (5200 W/m²K,
  constante con el título). La ec. 10-31 —criterio anular/estratificado con
  Fr_so— sigue sin implementar, y con ella el diagnóstico de régimen que exige
  CLAUDE.md. Es la tarea C4.
- **El modelo de aire trata los segmentos en paralelo**, no fila a fila como el
  §10.6.12. Con dos rangos y 4.9 K de salto de aire la diferencia es acotada,
  pero el reparto de zonas es una primera estimación.
- **El líquido subenfriado opera fuera del rango de Dittus-Boelter** (Re < 10⁴ a
  G = 48). El registro de extrapolación lo marca, como debe.
- **La marcha húmeda no puede ejercitarse como evaporador** mientras C4 siga
  pendiente: el coeficiente de ebullición en tubo no existe. C5 se contrasta por
  dos vías que no lo necesitan —la red de resistencias con la efectividad
  húmeda, que reproduce el U = 27.9 de la tabla 10.12, y una marcha con líquido
  frío por el interior, que ejercita el esquema de extremo a extremo y cierra
  los balances a 10⁻⁹—. Lo que la tabla 10.12 declara implica un coeficiente
  interior de ≈2900 W/(m²·K): es la cota que C4 debe alcanzar, y queda anotada
  en el fichero de datos.

### Estado de las tareas de la fase C

| | Estado | Tarea |
|---|---|---|
| C1 | ✅ | `FinnedCoilGeometry`, reconstrucción verificada contra la tabla 10.9 (área −0.10 %, volumen +0.06 %, velocidad másica −0.16 %) y radio equivalente de aleta 21.25 mm reproducido. |
| C2 | ✅ | Familia `airside` con la correlación de Colburn anclada y su rango de validez Re ∈ [4190, 5512] declarado y comprobado. Es la única correlación del modelo cuya base procede del capítulo. |
| C3 | ✅ | Familia `fin` con el método de Schmidt de aleta anular equivalente, seco y húmedo, y red de resistencias de la ec. 10-30. Reproduce 0.447 / 0.465 / 0.337 / 0.358 y el reparto 72.8 / 3.9 / 23.4 con U = 38.2. |
| C4 | ✅ | Familias `tube_condensation` y `tube_boiling`, separadas de las de placas: `get()` lanza `KeyError` si un intercambiador de placas nombra una correlación de tubo. Ec. 10-31 con criterio de Soliman y ec. 10-33/34 de Gungor-Winterton, ambas con lazo interno por celda sobre q″ porque dependen del flujo de calor. La batería opera ya en los dos sentidos. **Tres discrepancias abiertas**, apartado 10. |
| C5 | ✅ | Marcha por potencial entálpico, Le = 1 declarado, con reporte separado de sensible y latente y caudal de condensado. El régimen de cada celda se **resuelve** —temperatura superficial frente a punto de rocío—, no se declara por modo: en el punto de ficha sale seco en las 200 celdas, que es lo que el fabricante declara al dar la misma humedad específica a entrada y salida. Módulo `psychrometrics` propio, contrastado contra CoolProp. |
| C6 | 🟡 | El **dominio** de formación ya se reporta —fracción de superficie bajo cero y caudal de condensado, que es el dato que el §10.6.7 pide para saber en qué intervalos aplicar la ec. 10-37—. Falta la penalización en la agregación estacional, que es del cap. 12 y no de este componente. |
| C7 | ✅ | Ventilador: consumo constante de 780 W (catálogo CBN, alta velocidad, triángulo, un axial de Ø500). Corroborado por tres vías: Δp implícita de 110.8 Pa dentro de la banda 80–120 Pa del §10.6.8, η inverosímil si fuese la batería sola, y velocidad de descarga de 10.75 m/s normal para el diámetro. Ya no es cota inferior. |
| C8 | ✅ | Marcha por segmentos e inventario con la banda de las cuatro correlaciones. |
| C9 | ✅ | Diagnóstico de régimen: `CoilResult.condensation_regime` y `Fr_so_range`. A 48 kg/(m²·s) el Froude de Soliman no alcanza 20 en ninguna celda: la condensación es **estratificada en todo el serpentín**. `regime_diagnosed` marca como falso cualquier resultado apoyado en el agregado de ficha, que por ser constante con el título no puede diagnosticar. |

---

## 4. Lo que bloquea de verdad

Ninguna fase está bloqueada por una decisión pendiente. Lo que sí está acotado
por datos que no existen:

- ~~**El EER declarado**, mientras no haya curva de ventilador.~~ **Resuelto el
  17/09/2026** con el dato de catálogo: 780 W absorbidos, un solo axial de Ø500,
  corroborado por tres vías independientes. Ya no acota nada.
- **La operación como evaporador**, mientras el fabricante no dé un punto. La
  tabla 10.12 es extrapolación y debe declararse como tal en toda salida.
- **El submodelo de placas**, mientras φc, φv, C y m sigan sin valor.

Los tres son datos a solicitar, no decisiones a tomar. El resto del plan avanza
sin ellos siempre que el modelo falle de forma explícita al llegar a ellos, que
es precisamente lo que la tarea A1 construye.

---

## 6. La temperatura de descarga: discrepancia resuelta por decisión del autor

Con los 46 puntos disponibles, el contraste del §10.4.5 se puede hacer en lugar
de creerse. El resultado abre una discrepancia que conviene resolver antes de
apoyar H3 en ella.

### Lo que dice el capítulo y lo que dan los puntos

El §10.4.5 declara, para los parámetros de la tabla 10.4 sobre los 46 puntos:
capacidad dentro de ±2.7 %, potencia al eje dentro de ±6.6 % y temperatura de
descarga dentro de ±10.5 K.

| | Tabla 10.4 | Reidentificación | Declarado |
|---|---|---|---|
| Caudal | ±4.5 % | **±2.6 %** | ±2.7 % |
| Potencia al eje | ±9.8 % | **±5.7 %** | ±6.6 % |
| Temperatura de descarga | ±16.8 K | **±5.4 K** | ±10.5 K |

Los tres se exceden con la tabla 10.4. El de temperatura de descarga, además,
**no es dispersión sino sesgo**: +14 K de media, prácticamente constante entre
T_k = 15 y 50 °C.

La reidentificación emplea la misma estructura de nueve parámetros, los mismos
46 puntos y la misma función objetivo, con el peso ×4 en T_dis que el §10.4.5
declara. Un multiarranque de cuatro puntos de partida converge tres veces a la
misma región —la cuarta cae en un mínimo local identificable por el coste—, de
modo que no es un artefacto del arranque.

### La implementación no es la causa

Con los parámetros de la tabla 10.4, el modelo reproduce los **140.4 °C** que el
§10.6.9 usa en el equilibrio de M-1 (da 141.3 °C a T_evap = 2 °C, T_cond =
46.8 °C, recalentamiento 1 K). Es decir: esta implementación coincide con la del
capítulo, y la discrepancia está en el ajuste, no en el código. Se ha comprobado
además que ni un recalentamiento de aspiración mayor ni la condensación de
equilibrio explican la diferencia por sí solos.

### El dato que no depende de ningún modelo

A T₀ = 2 °C y T_k = 45 °C **el fabricante publica 122.2 °C**. Los 140.4 °C del
§10.6.9 quedan 18 K por encima del catálogo en ese mismo punto. Ninguna
identificación que cumpla el ±10.5 K declarado puede producir 140.4 °C ahí,
porque el dato está a 18.2 K de distancia: las dos afirmaciones del capítulo
—«±10.5 K» y «140.4 °C»— no pueden sostenerse a la vez.

La reidentificación predice 123.4 °C en el equilibrio de M-1, coherente con el
catálogo.

### Por qué importa

El §10.5.3 dimensiona el desrecalentador de ACS **tomando 140.4 °C como
temperatura de entrada**, y de ahí salen los 2.63 kW recuperados y el margen de
10.9 K sobre la saturación. Con ~123 °C el salto disponible de
desrecalentamiento se reduce en torno a un 20 %, y con él la potencia
recuperable, que es la magnitud sobre la que descansa H3.

Hay además un argumento físico que no conviene pasar por alto: la
reidentificación lleva AU_su,n prácticamente a cero, mientras que la tabla 10.4
le da 110.7 W/K. Un valor casi nulo es **lo que predice el propio §10.4.3**,
que justifica que en un compresor abierto «el motor es externo y su calor se
disipa al ambiente, lo que reduce sustancialmente el calentamiento del vapor en
la aspiración respecto a un compresor hermético». 110.7 W/K es un calentamiento
de aspiración fuerte, más propio del caso que ese apartado descarta.

### Decisión del autor, 16 de septiembre de 2026

**La reidentificación pasa a ser el juego de trabajo del modelo**, en sustitución
de la tabla 10.4. El capítulo se reescribirá en consecuencia, y esa reescritura
se abordará con un informe propio cuando el modelo de simulación esté completo.

El cambio no es silencioso —que es lo que CLAUDE.md prohíbe—: queda fechado en
`data/compresor_bock_f2.yaml`, aquí, y en los tests. La tabla 10.4 se conserva
accesible con `data.compressor_params(variant="tabla_10_4")` para poder
reproducir los resultados del capítulo.

### El ajuste adoptado

Multiarranque de cinco puntos de partida; cuatro convergen a la misma región y
uno cae en un mínimo peor. Sobre los 46 puntos, 46 de 46 resueltos:

| | Adoptado | Tabla 10.4 | Declarado en el §10.4.5 |
|---|---|---|---|
| Capacidad | ±2.72 % (rmse 1.62 %) | ±4.5 % | ±2.7 % |
| Potencia al eje | ±5.18 % (rmse 1.79 %) | ±9.8 % | ±6.6 % |
| Temperatura de descarga | ±3.66 K (rmse 1.74 K) | ±16.8 K | ±10.5 K |

Y sin sesgo: el error de T_dis va de −1.8 a +1.8 K según T_k, dispersión y no
desplazamiento, frente a los +14 K constantes de la tabla 10.4.

**T_descarga en el equilibrio de M-1: 125.5 °C**, frente a los 140.4 °C que
usan el §10.6.9 y el §10.5.3. El catálogo da 122.2 °C a T₀ = 2 / T_k = 45.

Una nota sobre r_v: la cota inferior se bajó de 2.0 a 1.2, porque en este
compresor r_v no es una cota geométrica sino un parámetro efectivo que agrega la
dinámica de las válvulas (§10.4.2), de modo que el 2.0 no tiene justificación
física. Relajada, el óptimo queda en **1.965**: la cota apenas mordía, contra lo
que sugiere la anotación «límite inferior» de la tabla 10.4.

### Identificabilidad: el resultado más útil para la reescritura

Sensibilidad de los residuos a una perturbación **relativa** de cada parámetro
(jacobiano escalado en el óptimo, normalizado). Sin escalar la métrica no
significa nada, porque A_leak vale ~1e-15 y W_loss₀ ~348.

| Parámetro | Sensibilidad | |
|---|---|---|
| AU_ex,n | 1.00 | bien sujeto |
| Ẇ_loss,0 | 0.94 | bien sujeto |
| r_v | 0.91 | bien sujeto |
| AU_amb | 0.77 | bien sujeto |
| η_ic | 0.64 | bien sujeto |
| C | 0.082 | débilmente sujeto |
| AU_su,n | 0.0052 | débilmente sujeto |
| α | 2.8×10⁻⁷ | **no identificable** |
| A_leak | 2.9×10⁻¹⁴ | **no identificable** |

Número de condición: 6.7×10¹¹.

Tres consecuencias que conviene llevar al capítulo:

1. **La identificación de nueve parámetros es, en la práctica, de cinco.** Los
   datos de catálogo no determinan α ni A_leak, y sujetan mal C y AU_su,n. La
   tabla 10.4 publica A_leak = 1.73×10⁻⁷ m² como si estuviese identificado; el
   juego adoptado lo escribe como cero exacto, y fijarlo así no altera el ajuste
   en ninguna cifra significativa.
2. **Los valores individuales no deben interpretarse físicamente.** Las cuatro
   soluciones buenas del multiarranque tienen parámetros apreciablemente
   distintos —AU_su,n entre 0.006 y 0.4, Ẇ_loss,0 entre 242 y 348 W— y sin
   embargo predicen casi lo mismo: T_descarga entre 125.2 y 125.7 °C en el
   equilibrio de M-1. El ajuste está mal condicionado pero es predictivamente
   estable, y eso es lo que hay que declarar.
3. **AU_su,n ≈ 0 es lo que predice el propio §10.4.3**, que justifica que en un
   compresor abierto el calentamiento del vapor en aspiración es sustancialmente
   menor que en uno hermético. Los 110.7 W/K de la tabla 10.4 son un
   calentamiento fuerte, más propio del caso que ese apartado descarta.

### Lo que arrastra

El §10.5.3 dimensiona el desrecalentador de ACS tomando 140.4 °C como
temperatura de entrada, y de ahí salen los 2.63 kW recuperados y el margen de
10.9 K sobre la saturación. Con 125.5 °C el salto disponible de
desrecalentamiento se reduce en torno a un 17 %, y con él la potencia
recuperable, que es la magnitud sobre la que descansa H3. **El punto de diseño
del desrecalentador hay que rehacerlo**, y es tarea de la fase D.

---

## 7. Informe para la reescritura del capítulo

> **SUPERADO el 22/09/2026 por `docs/INFORME_REESCRITURA_CAP10.md`.** Esa es
> ahora la fuente para la reescritura: recoge esta lista consolidada, ordenada
> por apartado del capítulo, con el estado final de cada punto y con las
> conclusiones de este plan que hallazgos posteriores invirtieron marcadas como
> tales. Lo que sigue se conserva como registro de lo que se sabía a cada fecha,
> **no como material de redacción**.

Pendiente, a redactar cuando el modelo de simulación esté completo. Debe recoger
al menos lo acumulado hasta ahora:

- Tabla 10.4 y sus tolerancias: el ajuste adoptado y el análisis de
  identificabilidad (apartado 6).
- Tabla 10.13, fila de flujo de deriva: corregida de 339 a 426 g, y el efecto
  sobre H4 (apartado 2.4).
- §10.6.10 y RS-5: la carga integrada por segmentos da 171–316 g con
  condensación completa y subenfriamiento nulo, frente a los 200–426 g de la
  tabla; lo que decide el cumplimiento es el anegado del condensador, no la
  geometría del serpentín (apartado 5).
- Ecuaciones 10-43 a 10-45: colisión de símbolo entre título y fracción de
  huecos (apartado 2.5).
- Ecuación 10-9: ambigüedad de signos. Ecuaciones 10-5 y 10-6: el subíndice
  «ad» con dos significados distintos.
- §10.5.3: el punto de diseño del desrecalentador, a rehacer con la temperatura
  de descarga corregida.
- §5.5: η_sa ≈ 0.85 frente al 0.465 real de la geometría seleccionada.
- §10.5.8, pérdida de carga: la contribución gravitatoria **domina en el
  condensador** por un factor de 11 sobre la friccional e **invierte el signo**
  del resultado (−73.8 Pa netos, ganancia de presión). El apartado la conserva
  citando solo el evaporador; conviene que recoja también el condensador y, sobre
  todo, que declare el **sentido de montaje**, porque impuesto el contrario el
  mismo componente da +87.1 Pa.
- §10.5.1, ec. 10-15: la ΔT_lm y la aritmética difieren menos del 0.05 % con la
  discretización empleada. Útil para justificar la discretización elegida.
- §10.5.3 y tabla 10.6, **convenio de área**: la tabla publica área proyectada y
  el modelo necesita la desarrollada; la diferencia es del 15–17 % y hoy no está
  dicha en ninguna parte. Conviene declararlo junto a la ec. 10.15, porque
  D_h = 2b/Φ ya obliga al convenio desarrollado. Además, en el 27-30H el área
  proyectada reconstruida excede la declarada un 11 %, lo que sugiere que los
  0.250 m son distancia entre puertos y no longitud efectiva de placa.
- §10.6.8, consumo de ventilador: el catálogo de la serie CBN da **780 W** a alta
  velocidad con el motor en triángulo, potencia absorbida. El apartado estima
  530–720 W para 80–120 Pa, de modo que el dato queda un 8 % por encima de su
  extremo alto, pero lo corrobora: con el η = 0.30 que el propio apartado adopta,
  780 W equivalen a 110.8 Pa, dentro de su banda. Dos observaciones para la
  reescritura: (a) las cifras 530–720 W implican η = 0.32 y 0.35, incoherentes
  con el 0.30 que el mismo párrafo declara; (b) con un dato de consumo medido no
  hace falta suponer rendimiento alguno, que es lo que pide la UNE-EN 14511, y el
  párrafo puede simplificarse eliminando la cadena V·Δp/η. El equipo lleva un
  único axial de Ø500: 10.75 m/s de descarga y SFP de 369 J/m³.
- §10.6.6, **dónde se evalúa b'**: el texto declara 1781 J/(kg·K) «con una
  temperatura superficial del orden de 1 °C», y la ec. 10-36 define
  b' = dh_sat/dT|_{T_s}. Pero 1781 no es el valor a 1 °C (1750) sino el de
  **1.6 °C**, que es la T_evap de la primera fila de la tabla 10.12; la
  superficie de ese mismo punto está a ~3 °C, donde b' vale 1854. El factor
  «1.77 veces c_p» es igualmente el de 1.6 °C. **No mueve ningún resultado**
  —η_f pasa de 0.337 a 0.336 y η_sa sigue en 0.358—, de modo que lo que procede
  es corregir la redacción: atribuye a la superficie una temperatura que es la
  del refrigerante. El modelo evalúa b' donde la ecuación dice.
- §10.6.5, **ecuación 10-33 frente a las cifras publicadas**, §10.6.5 **dirección
  del criterio de la ec. 10-31**, §10.6.4 **atribución del −11 %** y §10.6.9
  **tabla 10.12 como equilibrio**: los cuatro se desarrollan en el apartado 10.
- §10.13.3, **tabla 10.15**: la arquitectura publicada no contempla un módulo de
  aire húmedo, y el §10.6.6 lo necesita. El modelo añade `psychrometrics`, con
  las formulaciones analíticas de ASHRAE en lugar de `HAPropsSI` por la misma
  razón por la que el §10.13.4 saca `PropsSI` de los lazos —la marcha evalúa la
  curva de saturación del orden de 10⁴ veces por punto resuelto—, y con el error
  de la sustitución cuantificado contra CoolProp, como el §7.6.4 exige para el
  backend tabular. Es una adición a la tabla, no una desviación de ella, pero
  debe quedar declarada.
- §10.6.9, tabla 10.12: el U de 27.9 W/(m²·K) es la red de resistencias
  ordinaria con la efectividad superficial **húmeda** (0.358), no una
  conductancia en base entálpica. Conviene decirlo, porque la ec. 10-35
  introduce un U* cuyas unidades son kg/(m²·s) y el lector puede confundirlos.
  Ese U implica además un coeficiente de ebullición interior de ≈2900 W/(m²·K),
  cifra que el apartado no declara y que es la única forma de contrastar la
  correlación de la ec. 10-33/34 contra lo que el capítulo ya publica.

---

## 8. Fase D — placas al nivel del capítulo ✅

| | Estado | Tarea |
|---|---|---|
| D1 | ✅ | Condensación por película de Nusselt (ec. 10-21/22) como valor por defecto. `equivalent_Re` se conserva registrada como alternativa declarada para la sensibilidad del cap. 11, pero deja de ser la principal: el §10.5.6 la descarta expresamente. |
| D2 | ✅ | Chen aditivo (ec. 10-19) como formulación principal; la asintótica pasa a variante. |
| D3 | ✅ | Martin (VDI) implementada, con el convenio de ángulo verificado (β → 0 devuelve el conducto liso). |
| D4 | 🟡 | Ec. 10-24 aplicada y fracción de pared húmeda reportada. La magnitud de la corrección no está soportada: ver abajo. |
| D5 | ✅ | Ec. 10-25 completa: friccional con multiplicador bifásico (familia registrada aparte), aceleración y gravitatoria, con el reparto en el resultado. Ver abajo. |
| D6 | ✅ | ΔT_lm adoptada. La desviación que tenía la aritmética resulta ser inferior al 0.05 %: era inocua, pero estaba sin declarar ni medir. |
| D7 | ✅ | Convenio fijado: área **desarrollada**. Ver abajo. |

### El submodelo de placas ya no resuelve sin φc y φv

Consecuencia directa de D1, y es la correcta: el §10.5.9 dice que sin esos
coeficientes el submodelo no cierra, y ahora el modelo lo hace cumplir en lugar
de declararlo. Para explorar sin el dato hay que inyectarlos por `corr_params`,
que es una declaración visible en el código que lo hace, y no un valor por
defecto invisible.

### Tres fallos del componente encontrados al ejercitarlo

1. **Sentido del secundario en contracorriente invertido.** La marcha hacía
   *subir* la temperatura del agua cuando debe bajar, porque va aguas arriba del
   agua. El componente nunca había resuelto un caso real, solo tests con
   tolerancias amplias.
2. **La comprobación de balance no lo detectaba**, porque comparaba módulos:
   cerraba a 10⁻¹⁵ con el agua evolucionando al revés. Es justo el fallo del que
   avisa su propio docstring. Ahora compara signado.
3. **Intervalo de disparo sin acotar físicamente**, que metía al agua por debajo
   del punto de fusión y hacía abortar a la biblioteca de propiedades en lugar
   de no converger. Acotado entre las dos temperaturas de entrada.

### El punto de diseño del desrecalentador, rehecho

Con Martin a ambos lados y β = 60° **supuesto** (dato pendiente), el modelo
reproduce el punto del §10.5.3 con la entrada a 140.4 °C, lo que valida su uso
para rehacerlo:

| T. de descarga | m_ACS para 60 °C | Q recuperado | Salida del refrigerante | Margen |
|---|---|---|---|---|
| 140.4 °C (capítulo) | 87.3 kg/h | 2537 W | 58.5 °C | +13.5 K |
| **125.5 °C (corregida)** | **74.0 kg/h** | **2150 W** | **57.3 °C** | **+12.3 K** |

*El §10.5.3 declara 90.6 kg/h, 2.63 kW y 55.9 °C con 10.9 K de margen.*

**La potencia recuperada cae un 15 %** al corregir la temperatura de descarga.
El criterio de dimensionado —que el refrigerante no descienda de T_sat dentro
del desrecalentador— **sigue cumpliéndose** con margen holgado, de modo que la
decisión de mantener el AlfaNova 16-10H no se ve afectada. Lo que cambia es el
número que sostiene H3.

### Dos discrepancias nuevas en el §10.5.3

**El coeficiente de 1433 W/(m²·K) se calculó con el paso de placa sin corregir.**
El mismo apartado declara b corregido de 1.06 a 2.09 mm «que subestimaba el
diámetro hidráulico», pero el coeficiente publicado corresponde al valor
antiguo: con b = 1.06 mm y β = 60°, Martin da 1411 W/(m²·K); con el b corregido
da **716**, la mitad. Los números de Reynolds publicados (5354 y 1020) no
delatan el problema porque son independientes de b.

**Los 61 W/(m²·K) del contraste con el AlfaNova 27-30H no se reproducen.**
Martin no baja de 178 W/(m²·K) con el b corregido ni de 352 con el antiguo, para
ningún β. El orden de magnitud solo se alcanza conmutando a una correlación
laminar de Nusselt constante a Re ≈ 1020 (Nu = 3.66 con b = 1.06 mm da 70). El
«desplome del 96 %» que cierra la decisión del §10.5.3 es, por tanto, artefacto
del b sin corregir más una discontinuidad de correlación. Con Martin y el b
corregido la caída es de 716 a 215 W/(m²·K), un 70 %: sigue siendo grande y la
decisión probablemente se sostiene, pero los números que la justifican no.

### D5 — la gravedad domina en el condensador, y el capítulo no lo anticipa

El §10.5.8 conserva la contribución gravitatoria porque «la disposición vertical
la hace no despreciable en la región bifásica del **evaporador**». Resuelto el
condensador de climatización en su punto de diseño, el reparto de la ec. 10-25 es:

| Contribución | Condensador climatización | Desrecalentador ACS |
|---|---|---|
| Friccional | +7.4 Pa | +297.4 Pa |
| Aceleración | −0.7 Pa | −9.4 Pa |
| Gravitatoria | **−80.5 Pa** | −18.9 Pa |
| **Total** | **−73.8 Pa** (ganancia) | +269.1 Pa |

En el condensador la gravedad no es que no sea despreciable: **domina por un
factor de 11 sobre la friccional e invierte el signo del resultado**. El
refrigerante gana 74 Pa al recorrer la placa hacia abajo. La causa es el flujo
másico: 40.3 kg/h repartidos en 14 canales dan G ≈ 3.3 kg/(m²·s), que deja la
fricción en unos pocos pascales mientras la columna de 0.25 m pesa lo que pesa.

Dos observaciones sobre la solidez del resultado:

- La gravitatoria es el **único término de la ec. 10-25 que no depende de
  correlación alguna**: es ρ·g·Δz. La conclusión se sostiene aunque el factor de
  fricción siga siendo provisional (tabla 10.7). La fricción tendría que ser 11
  veces mayor para compensarla.
- El «±» de la ecuación no es una indeterminación sino el **sentido del flujo**,
  y el propio capítulo lo fija por dos vías: el §10.5.6 describe la película de
  condensado descendente y el §10.5.8 sitúa el evaporador ascendente. Impuesto
  el sentido contrario, el mismo componente da +87.1 Pa en lugar de −73.8, y en
  horizontal +6.7 Pa. **La orientación de montaje decide el resultado**, y debe
  declararse en el capítulo 12.

El multiplicador bifásico se registra en familia propia, `twophase_multiplier`,
y no dentro de `friction`: la firma es distinta —toma el título y las dos fases,
no un solo Reynolds— y mezclarlas impediría sustituir una sin tocar el
componente. Con Lockhart-Martinelli/Chisholm la fricción del condensador es 7.38
Pa frente a 4.81 Pa del modelo homogéneo, un factor 1.53 coherente con ignorar
el deslizamiento a una relación de densidades de ~50.

### D6 — la desviación aritmética era inocua, pero no estaba medida

Adoptada la ΔT_lm de la ec. 10-15, la diferencia con la aritmética que usaba el
componente es **inferior al 0.05 % ya con 20 volúmenes**, en los dos
intercambiadores. La discrepancia D8 se cierra sin consecuencias numéricas. Lo
que no era admisible es que una desviación de la formulación del capítulo
estuviera sin declarar; ahora la aritmética se conserva como alternativa
registrada, que es lo que permite seguir midiéndola.

Efecto colateral que conviene anotar: con ΔT_lm el resultado de **malla gruesa
mejora sensiblemente** —a n = 10 el error cae del 2.9 % al 1.0 %—, lo que
invalidó el test de independencia de malla que medía la mejora desde n = 10. La
solución no es monótona por debajo de n ≈ 20 porque las fronteras de zona caen
en celdas distintas según la malla; el estudio arranca ahora en n = 20.

### D7 — el área de catálogo y la del modelo son dos magnitudes distintas

No había un error de un 17.7 % entre los 0.0995 m² de la tabla 10.6 y los
0.117 m² del código: son el **área proyectada** y el **área desarrollada**.

| | AlfaNova 16-10H | AlfaNova 27-30H |
|---|---|---|
| Declarada (tabla 10.6) | 0.0995 m² | 0.700 m² |
| Proyectada reconstruida | 0.1018 m² (+2.4 %) | 0.7770 m² (+11.0 %) |
| Desarrollada (Φ) | 0.1171 m² (+17.7 %) | 0.9091 m² (+29.9 %) |

**Convenio adoptado: desarrollada**, por coherencia interna y no por
preferencia. El diámetro hidráulico de la ec. 10.15 es D_h = 2b/Φ, que es la
definición del VDI, y Martin —la correlación que el §10.5.3 dice haber
empleado— está formulada sobre ese diámetro y sobre el área desarrollada.
Emparejar D_h = 2b/Φ con el área proyectada contaría el corrugado una vez en el
diámetro y ninguna en el área.

Contraste independiente del argumento: resuelto el punto de diseño del §10.5.3
con cada convenio, el desarrollado queda a **−3.5 %** de los 2.63 kW del
capítulo y el proyectado a **−9.0 %**. El capítulo empleó el desarrollado.

Queda un residuo que no explica el corrugado: **+2.4 % en el 16-10H y +11.0 % en
el 27-30H** entre el área proyectada reconstruida y la declarada. En el 27-30H
apunta a que los 0.250 m de la tabla son distancia entre puertos y no longitud
efectiva de placa: 0.700/28 = 0.0250 m² frente a 0.111 × 0.250 = 0.0278 m², una
razón de 0.90. Anotado para la reescritura.

**Advertencia operativa**: un U de catálogo viene referido al área proyectada.
Usarlo contra el área desarrollada sobreestimaría la conductancia un 15–17 %.

### La ecuación 10-24 se anula para un fluido puro

`Z = x·cp,v·(dT_sat/dh)`. Para un fluido puro a presión constante T_sat no
depende de la entalpía dentro de la campana: dT_sat/dh = 0 exactamente
—verificado numéricamente—, de modo que Z = 0 y la ecuación no introduce
corrección alguna.

La expresión procede del método de Bell y Ghaly, formulado para mezclas
multicomponente, donde la temperatura de burbuja sí varía con la composición a
lo largo de la condensación. El §10.5.7 describe correctamente el fenómeno para
un fluido puro, pero le adjunta una ecuación que, aplicada a NH₃, se anula.

El modelo implementa la ec. 10-24 con Z como **fracción sensible de la carga**,
que sí toma valores en [0, 1] y recupera los dos límites correctos, y adopta
Z = 1 —el límite conservador, equivalente a tratar el desrecalentamiento como
monofásico puro, que es justo lo que el §10.5.7 dice que sobreestima el área—.
No se adopta un valor menor porque supondría inventar la formulación que falta.

**Consecuencia para H3.** El modelo ya reporta el diagnóstico que el §10.5.7
exige: en el punto de diseño rehecho, en torno al **17 % del desrecalentador
opera con la pared por debajo de la saturación**, aunque el refrigerante no
condense en el núcleo. Pero el soporte *cuantitativo* de H3 sigue sin estar
disponible hasta que exista una formulación de Z válida para un fluido puro.
Va al informe de reescritura.
---

## 9. Fase E — el equilibrio de M-1 se resuelve, pero no da lo que dice el §10.6.9

Cerrada el 17 de septiembre de 2026. `src/amoniatermia/circuit.py`.

### El hito, y lo que sale

El §10.6.9 calcula el equilibrio de M-1 «con el compresor identificado en el
apartado 10.4.5 operando a temperatura de evaporación de 2 °C y aire exterior a
35 °C», sin resolver el lado de baja. Esa es exactamente la configuración que el
modelo reproduce: temperatura de evaporación impuesta, recalentamiento de
consigna 1 K, caudal de aire de ficha, y el equilibrio determinado por la
condición de **condensación completa a la entrada de la válvula**, que es la que
el ciclo necesita para que la válvula reciba líquido.

| | §10.6.9 | Modelo | Diferencia |
|---|---|---|---|
| Temperatura de condensación | 46.8 °C | **45.7 °C** | −1.1 K |
| Calor evacuado | 13.2 kW | **11.69 kW** | −11 % |
| Potencia frigorífica | 10.3 kW | **9.43 kW** | −8 % |
| Potencia al eje | — | 2.52 kW | — |
| Temperatura de descarga | 140.4 °C | 122.5 °C | −18 K |

El sistema de residuos se anula a precisión de máquina (10⁻¹²), los balances de
masa y energía cierran por debajo de 10⁻⁵ y la generación de entropía es positiva
en los tres componentes. No es un problema de convergencia.

### La diferencia no está en la batería: está en el caudal

Se ha descompuesto ejecutando el mismo equilibrio con las dos combinaciones que
podían explicarla:

| Juego de parámetros | U | T_cond | Q evacuado | Q frigorífica | ṁ |
|---|---|---|---|---|---|
| Reidentificado (por defecto) | 38.2 (sesgo del §10.6.4) | 45.73 °C | 11.69 kW | 9.43 kW | 32.4 kg/h |
| Reidentificado | 43 (ficha) | 45.26 °C | 11.71 kW | 9.48 kW | 32.5 kg/h |
| Tabla 10.4 | 38.2 | 46.09 °C | 12.30 kW | 9.60 kW | 33.1 kg/h |
| Tabla 10.4 | 43 (ficha) | 45.61 °C | 12.32 kW | 9.64 kW | 33.1 kg/h |

Dos lecturas, y ninguna de las dos es la que cabría esperar:

- **Corregir el sesgo de U del −11 % no aumenta la potencia**, la baja de
  temperatura. Con la condensación completa como condición de cierre, el calor
  evacuado lo fija el caudal y el salto entálpico del refrigerante, no la
  conductancia: más UA significa condensar con menos diferencia de temperatura,
  esto es, **1.5 K menos de condensación con la misma potencia**. Es un
  resultado favorable —mejor COP— pero no cierra la diferencia con el capítulo.
- **El juego de parámetros del compresor explica la mitad**, por la vía de la
  temperatura de descarga: 139.7 °C frente a 122.5 °C son 0.6 kW más de
  desrecalentamiento que evacuar. La otra mitad es caudal.

### El catálogo del fabricante no soporta los 10.3 kW

Este es el contraste que decide, y no depende de ningún modelo. A T₀ = 2 °C el
fabricante publica:

| T_k | Capacidad | Potencia al eje | T descarga |
|---|---|---|---|
| 45 °C | 9.46 kW | 2.47 kW | 122.2 °C |
| 50 °C | 8.97 kW | 2.68 kW | 137.0 °C |

Interpolando a los 46.8 °C del §10.6.9 salen **9.28 kW**, un 11 % por debajo de
los 10.3 kW declarados. Y el modelo, en su equilibrio de 45.7 °C, da 9.43 kW y
2.52 kW al eje: coincide con el catálogo dentro del 1 %.

Es el mismo patrón que la discrepancia de la temperatura de descarga del
apartado 6, y con la misma estructura: el capítulo declara una cifra que el
catálogo del fabricante contradice, y el modelo se alinea con el catálogo.

### Por qué importa: RS-5 se evalúa contra una capacidad que no es

De los 10.3 kW sale el presupuesto de carga del §10.6.10: 50 g/kW × 10.3 kW =
**515 g para todo el sistema**. Con 9.43 kW el presupuesto baja a **472 g**, un
8 % más estrecho, y todas las fracciones de RS-5 reportadas en ese apartado se
recalculan al alza.

No cambia la conclusión cualitativa —la batería sola, drenada, sigue por debajo
del presupuesto: 316 g son el 67 % de 472 g en lugar del 61 % de 515 g— pero sí
estrecha el margen con el que H4 se contrasta. Y el margen era ya el punto en
que el §10.6.10 pedía «declararlo con esa crudeza y no presentarlo como una
holgura».

El modelo evalúa RS-5 contra la capacidad que él mismo calcula, como exige
CLAUDE.md, de modo que el presupuesto se mueve solo cuando se mueve la capacidad.

### Las cinco topologías, ejecutadas

Los cinco modos de la tabla 10.3 —y la variante de M-5 con reparto explícito—
resuelven de extremo a extremo. Con los intercambiadores de placas a 8 volúmenes,
la batería a 40 segmentos y un presupuesto de 50 evaluaciones por pasada:

| Modo | T₀ | T_k | Q evap | Q alta | Q ACS | ṁ | residuo |
|---|---|---|---|---|---|---|---|
| M-1 refrigeración | 5.1 °C | 47.0 °C | 10.53 kW | 12.84 kW | — | 36.0 kg/h | 6.9·10⁻³ |
| M-2 calefacción | −1.2 °C | 47.9 °C | 8.20 kW | 10.43 kW | — | 27.2 kg/h | 1.8·10⁻² |
| M-3 refrigeración + ACS | 4.9 °C | 45.4 °C | 10.63 kW | 12.93 kW | 1.81 kW | 36.0 kg/h | 1.7·10⁻³ |
| M-4 calefacción + ACS | −1.5 °C | 48.1 °C | 8.01 kW | 10.20 kW | 1.95 kW | 26.7 kg/h | 1.2·10⁻² |
| M-5 solo ACS | −1.5 °C | 38.5 °C | 8.70 kW | 10.55 kW | 1.38 kW | 28.5 kg/h | 3.8·10⁻³ |
| M-5 reparto explícito | −10.2 °C | 37.5 °C | 5.85 kW | 7.37 kW | 1.33 kW | 19.1 kg/h | 4.6·10⁻² |

Condiciones: aire a 35 °C en refrigeración y a 7 °C en calefacción, caudal de
ficha; agua de climatización a 12 °C / 0.5 kg/s en frío y 40 °C / 0.5 kg/s en
calor; ACS entrando a 35 °C con consigna de 60 °C.

**Los seis están declarados NO válidos por el propio modelo**, y es el
comportamiento correcto: ninguno alcanza el ε = 10⁻⁶ del §10.11.4 con esa
discretización y ese presupuesto, de modo que `CircuitSolution.valid` es falso y
los seis quedan registrados en `Circuit.failures` con su condición de contorno.
Refinando —200 segmentos y sin límite de evaluaciones— M-1 baja a 1.9·10⁻³, y el
punto es estable: T₀ entre 6.0 y 6.2 °C, T_k entre 47.3 y 47.9 y capacidad entre
11.04 y 11.15 kW a lo largo de 50, 100, 200 y 400 segmentos. Lo que no se ha
conseguido es cerrar hasta la tolerancia del capítulo en los modos con placas.

Dos salvedades que hay que leer junto a la tabla:

- **Todos son exploratorios.** La geometría de placas lleva β, b y φ inyectados,
  y φc y φv fijados a la unidad. No existe ninguno de esos datos (§10.5.9). El
  modelo deja constancia: `provenance["geometria_inyectada"]` los lista.
- **Las cifras de M-5 responden a la topología de la decisión D-1**, no a la de
  la tabla 10.3. Ver `docs/PENDIENTES.md`.

### Tres reformulaciones de los residuos que el capítulo no anticipa

Ninguna cambia la solución; las tres cambian que el método la encuentre. Se
documentan porque son exactamente el tipo de decisión que el §10.13.4 pide
declarar, y porque las tres se descubrieron al ejercitar el lazo, no al
escribirlo.

1. **El recalentamiento se prolonga al dominio bifásico.** Si la salida del
   evaporador es húmeda, el recalentamiento físico vale cero y el residuo se
   queda **plano**: R₂ se clavaba en −1.000 en todo un tramo de presión de
   condensación, sin gradiente en la dirección en que estaba la solución. Se
   prolonga por el déficit entálpico dividido por c_p del vapor saturado, que es
   la pendiente dT/dh al otro lado de la frontera. Un valor negativo significa
   salida húmeda, y es información útil: la consigna no es alcanzable.

2. **El cierre del lado de alta se escribe sobre el subenfriamiento, no sobre
   el calor.** Completada la condensación, la entalpía de salida **sigue a la
   línea de líquido saturado**: al variar la presión, h_out y h_l(P) se mueven
   juntas y el residuo entálpico queda casi plano. Medido en M-1 con evaporador
   de placas, se estancaba en −2.2·10⁻² y no mejoraba al refinar (50, 100, 200 y
   400 volúmenes dan lo mismo): no era ruido de discretización, era un valle
   plano. Sobre la temperatura, un kelvin son 4.7 kJ/kg frente a los 1100 kJ/kg
   del calor latente: el residuo gana dos órdenes de magnitud de sensibilidad y
   el punto converge. Cuando hay demanda impuesta se conserva la forma en
   potencia de la tabla 10.14.

3. **Los residuos de temperatura se normalizan por la temperatura absoluta.** El
   §10.11.4 fija la tolerancia sobre el «residuo relativo de cada ecuación de
   cierre». Una consigna de recalentamiento de 1 K normalizada por sí misma
   convierte ε = 10⁻⁶ en **un microkelvin**, por debajo de lo que resuelve la
   propia biblioteca de propiedades. Referido a la temperatura absoluta son
   0.3 mK: exigente y alcanzable.

### Lo que la fase E deja abierto

- **La singularidad de la válvula en la frontera de fase.** Con subenfriamiento
  de consigna nulo, la ec. 10-27 se evalúa exactamente donde su densidad de
  entrada es discontinua. El modelo lo sortea eliminando A_ef en forma cerrada,
  pero el hecho es del modelo de válvula, no del método: cualquier formulación
  que itere sobre A_ef con la salida del condensador en saturación encontrará el
  mismo mal condicionamiento. Conviene declarar un subenfriamiento de consigna
  mínimo, que además es lo que hace una instalación real.
- **La pared ficticia del compresor perdió su significado físico.** El juego
  reidentificado deja `AU_su_n` = 0.0056 W/K —prácticamente en su cota inferior—
  y `AU_amb` = 1.51 W/K, con lo que el calentamiento en la aspiración se anula y
  la pared se sitúa en **210 °C**, por encima de la propia descarga: el modelo
  predice que la pared *calienta* el gas de descarga en 83 W. La ec. 10-8 cierra
  y la temperatura de descarga coincide con el catálogo, de modo que no afecta a
  ningún resultado energético; lo que ya no puede hacerse es interpretar T_w como
  una temperatura física, ni apoyar en ella la hipótesis M4 sobre la pérdida de
  calor de la línea de descarga. Es un hallazgo sobre la identificación de la
  fase B, no sobre el lazo externo.
- **El coste de los modos con placas.** El equilibrio de M-1 en la configuración
  del §10.6.9 se resuelve en 1.4 s. Con el evaporador extendido de dos placas,
  el mismo punto cuesta 24 s, y la razón es el disparo del tren: la temperatura
  del agua en la unión no es dato de ninguno de los dos intercambiadores y se
  amplifica en el residuo de recalentamiento por el cociente ṁ_agua·c_p/ṁ_ref,
  del orden de 2·10⁵, lo que obliga a un `xtol` de 10⁻⁷ K. El arranque en
  caliente entre iteraciones ya lo ha bajado de 4 minutos a 24 s; la
  memorización de propiedades de la fase H es lo que queda.

---

## 10. Fase C cerrada — el lado de refrigerante del serpentín y tres discrepancias

Cerrada el 18/09/2026. `src/amoniatermia/correlations/tube.py`, contrastes en
`tests/test_tube.py` y en el bloque de evaporador de `tests/test_air_hx.py`.

La separación de familias es lo primero, porque es estructural y no documental.
`condensation` y `boiling` pasan a llamarse `plate_condensation` y
`plate_boiling`, y aparecen `tube_condensation` y `tube_boiling`. El §10.6.5
abre declarando que las correlaciones de placa «no son aplicables aquí», y ahora
intentar usarlas en el serpentín —o al revés— es un `KeyError`, no un resultado
verosímil y equivocado. Si estuviesen en la misma familia, la banda de
incertidumbre del §7.11 recorrería formulaciones que no describen la geometría
del componente y dejaría de significar nada.

Con ellas la batería opera en los dos sentidos y la tabla 10.12 deja de ser
inalcanzable. Tres discrepancias salen del contraste, y ninguna se resuelve en
el código.

### 10.1. La ecuación 10-33 no es la que produjo las cifras del §10.6.5

El apartado declara adoptar la superposición de la ec. 10-33,
`h_tp = S·h_nb + F·h_l`, y a continuación publica «coeficientes del orden de
3100 W/(m²·K) en la condición nominal de calefacción, descendiendo a
1900 W/(m²·K) en la condición del perfil frío».

Esas dos cifras son **Cooper solo**, el término nucleado sin superposición. El
modelo las reproduce a menos del 1.5 % con `cooper_solo` (3133 y 1895) y da
entre 5300 y 7800 con `gungor_winterton`, porque el término convectivo no es
despreciable: `F` llega a 11 a título alto.

La columna U de la tabla 10.12 confirma la lectura, y es la comprobación
independiente que cierra el argumento:

| Condición | U tabla 10.12 | modelo, `cooper_solo` | modelo, ec. 10-33 |
|---|---|---|---|
| 7 °C bs / 6 °C bh | 27.9 | 27.0 | 33.1 |
| 2 °C bs / 1 °C bh | 27.3 | 26.0 | 33.2 |
| −7 °C bs / −8 °C bh | 25.6 | 24.7 | 37.1 |

El modelo adopta la ecuación que el capítulo **escribe** —el capítulo manda
sobre el código— y conserva registrada la que el capítulo **calculó**. La
consecuencia es que la conductancia como evaporador sube del orden del 20 % y
con ella la predicción de calefacción.

Se añade además `gungor_winterton_horizontal`, la variante con la corrección de
estratificación de la fuente original que la ec. 10-34 omite. No es académica:
con G = 48 kg/(m²·s) esta batería opera en Fr_l = 0.047, justo bajo el umbral de
0.05 en que la corrección entra. Que la ec. 10-34 la omita es una asimetría del
capítulo, que trata la estratificación al condensar (ec. 10-31) y la ignora al
evaporar.

### 10.2. El criterio de la ec. 10-31 se justifica en la dirección contraria

El §10.6.5 motiva el criterio de transición diciendo que «tratar toda la
condensación como anular sobreestimaría el coeficiente». Con las correlaciones
que el propio apartado prescribe ocurre lo contrario: a 48 kg/(m²·s) la rama
anular da entre el 34 % y el 66 % de la estratificada.

La razón es física y conviene que el capítulo la recoja. La rama anular es
convección forzada gobernada por la cizalladura del vapor, y a Re_l ≈ 2000
transfiere poco. La rama estratificada incorpora una película descendente
gobernada por la **gravedad** sobre la generatriz superior, muy eficaz a
velocidad másica baja; lo que transfiere mal es el remanso inferior, y ese pesa
solo por (1 − θ_l/π). Es el mismo argumento que el §10.5.6 usa para descartar el
Reynolds equivalente en placas en favor de la película de Nusselt, aplicado al
tubo horizontal.

El criterio sigue siendo imprescindible —cambia el coeficiente por un factor de
hasta tres— pero su justificación debe reescribirse.

Diagnóstico resultante (tarea C9): el Froude de Soliman no alcanza 20 en
**ninguna** celda, de modo que la condensación es estratificada en todo el
serpentín. El capítulo lo anticipaba como «esperable en buena parte».

### 10.3. El −11 % del §10.6.4 no es atribuible solo a la aleta

El §10.6.4 declara que la conductancia reconstruida, 38.2 W/(m²·K), queda un
11 % por debajo de los 43 de ficha, lo atribuye al método de aleta equivalente
—reproducir la ficha exigiría η_sa = 0.549 en lugar de 0.465— y propone
resolverlo en el cap. 11 contrastando contra un cálculo bidimensional de la
aleta.

Esa reconstrucción se apoya en los 5200 W/(m²·K) que la ficha declara del lado
de refrigerante. La ec. 10-31 predice del orden de 9000, y con ese valor la
batería reproduce la capacidad de ficha —12228 W— con un 0.6 % de desviación,
**sin tocar la eficiencia de aleta**.

Los dos efectos son indistinguibles a partir de un solo valor de U: una aleta
mejor de lo que Schmidt predice y un coeficiente interior mayor que el declarado
cierran la discrepancia igual de bien. Separarlos exige un **segundo dato** —el
criterio de aleta del fabricante, o un punto de selección a otra velocidad
másica—, no un cálculo bidimensional de la aleta, que solo puede pronunciarse
sobre uno de los dos. Es una corrección al plan de trabajo del cap. 11.

### 10.4. La tabla 10.12 no es un equilibrio

Los 10.03 kW de la fila nominal están **por encima del techo del propio modelo
del capítulo**. Con el coeficiente de aire anclado del §10.6.3, la efectividad
superficial húmeda del §10.6.6 y un coeficiente de refrigerante *infinito* con
resistencia de pared nula, la batería no pasa de 9.3 kW: en régimen húmedo el
lado de aire es más del 90 % de la resistencia y ninguna mejora del lado de
refrigerante alcanza la cifra publicada.

La explicación es que esos 10.03 kW son la capacidad del **compresor** a la
temperatura de evaporación supuesta, no lo que la batería evacúa a esa
temperatura. La tabla impone T_evap en lugar de resolverla.

Resuelto el equilibrio entre los dos componentes, con la ec. 10-33 y
condensación a 50 °C:

| Condición | T_evap tabla / modelo | Q_evap tabla / modelo | COP tabla / modelo |
|---|---|---|---|
| 7 °C bs / 6 °C bh | 1.6 / **0.88** | 10.03 / **8.54** kW | 4.16 / **4.06** |
| 2 °C bs / 1 °C bh | −2.9 / **−3.51** | 8.36 / **6.91** kW | 3.79 / **3.55** |
| −7 °C bs / −8 °C bh | −11.1 / **−11.18** | 5.84 / **4.56** kW | 3.27 / **2.80** |

Las temperaturas de evaporación coinciden dentro de 0.7 K y el COP nominal
dentro del 2.5 %; las capacidades quedan entre el 12 y el 22 % por debajo. Es la
**misma desviación, en el mismo sentido y de tamaño parecido**, que el apartado 9
localizó en M-1 (9.4 kW frente a 10.3) y que allí se atribuyó al caudal del
compresor, corroborado contra el catálogo del fabricante. C4 no la mueve: el
equilibrio de M-1 pasa de 45.7 a 44.9 °C y la capacidad de 9.43 a 9.52 kW. La
discrepancia no está en el submodelo de condensación.

### 10.5. Un punto donde el modelo no reproduce el capítulo, y es frontera

El §10.6.7 afirma que «la condición de aire a 2 °C ya sitúa la evaporación en
−2.9 °C, con superficie por debajo de cero y formación de escarcha
establecida». El modelo lo reproduce: superficie húmeda y bajo cero en el 99 %
del área.

A −7 °C bs / −8 °C bh, en cambio, la superficie queda entre 0.3 y 0.6 K **por
encima** del punto de rocío y no hay deposición, contra lo que sugiere la tabla
10.10 al rotular esa fila «con escarcha». El margen es de décimas de kelvin y
cae dentro de la incertidumbre del coeficiente de aire, de modo que se reporta
como condición de frontera, no como refutación. Lo que sí conviene es que el
capítulo no la dé por establecida.

### 10.6. Lo que queda del serpentín

La **pérdida de carga del lado de refrigerante**, ec. 10-25 completa con
multiplicador bifásico y pérdidas localizadas en los codos de retorno. La ficha
declara 2622 Pa y es el contraste disponible; el §10.6.8 señala que con 40 tubos
y 2 circuitos los codos no son despreciables frente a los tramos rectos. Hoy se
desprecia, y es defendible mientras la presión se trate como uniforme —2.6 kPa
sobre 17.8 bar es un 0.15 %— pero no lo será para el barrido de circuitería del
cap. 12, que es justo donde la pérdida de carga decide.

---

## 11. Documentación de Alfa Laval — qué cierra y qué no

Aportada el 18/09/2026: los folletos de las gamas AlfaNova 16 y 27, el plano de
la unidad 27-30H y su ficha de selección. Cierra tres de los diez datos
pendientes de `placas_alfanova.yaml`, **corrige uno que estaba mal** y abre la
vía de identificación que hasta ahora no existía.

### 11.1. Lo que cierra

**El paso del paquete, y con él el hueco de canal.** La cota A de cada gama
crece un paso fijo por placa: `A = 11 + 2.42·n` mm en el AlfaNova 27 y
`A = 7 + 2.06·n` en el 16. El plano del 27-30H da A = 83.6 mm con 30 placas, y
11 + 2.42·30 = 83.6 exactamente. Ese paso es b + t, de modo que el hueco de
canal se sigue del espesor.

**El espesor de placa, acotado.** El catálogo no lo publica, pero sí el peso por
placa —0.13 kg en el 27, 0.05 en el 16—. Con la densidad del inoxidable, el peso
fija el **producto Φ·t**, no t: es una ecuación entre las dos incógnitas. Lo
útil es que Φ solo se mueve en una banda estrecha, con lo que t queda acotado a
±5 % y **b = paso − t queda determinado a ±1 %**, que es lo que de verdad
importa porque es lo que entra en D_h y en la sección de paso.

**La resistencia de ensuciamiento** del 27-30H: 2.7·10⁻⁴ m²·K/W, declarada en la
ficha. `PlateGeometry` la tenía por defecto en cero, que para un dato de
catálogo no es lo mismo que ausente.

Además, el volumen por canal del catálogo (0.0500 L) queda **verificado por dos
vías independientes** de la ficha: 0.70 dm³/14 canales y 0.75 dm³/15 canales.

### 11.2. Lo que corrige, y no es menor

El hueco de canal del desrecalentador estaba en **2.09 mm**, deducido el
17/09/2026 del volumen por canal. El paso del paquete es 2.06 mm, y **2.09
excede el paso**: el hueco entre dos placas no puede ser mayor que la distancia
entre ellas. El valor viejo absorbía en b el volumen de los puertos, que la
cifra de ficha incluye. El correcto es **1.72 mm**.

La sección de paso baja un 18 % y D_h con ella. Consecuencias medidas:

| | con b = 2.09 | con b = 1.72 | §10.5.3 |
|---|---|---|---|
| Punto de diseño | 2539 W (−3.5 %) | 2707 W (**+2.9 %**) | 2630 W |
| Salida del refrigerante | 58.5 °C | **53.9 °C** | 55.9 °C |
| Margen sobre T_sat, catálogo / descarga corregida | 13.8 / 12.5 K | **9.2 / 8.5 K** | — |
| Caída de potencia recuperada con la descarga corregida | −15 % | **−15 %** | — |

Dos lecturas. La primera es que **la conclusión sobre H3 es robusta**: la caída
del 15 % en potencia recuperada al corregir la temperatura de descarga no se
mueve, porque es un cociente entre dos puntos de la misma geometría.

La segunda es que **el margen de no condensación se estrecha un tercio**, de
~13 K a ~9 K. Sigue siendo positivo y la selección del 16-10H no se ve afectada,
pero es el margen que separa a M-3 de condensar dentro del desrecalentador y ya
no es el que el capítulo declara.

**Y se cae una corroboración.** El 17/09 se adoptó el convenio de área
desarrollada con dos argumentos: la coherencia interna —D_h = 2b/Φ es la
definición del VDI y Martin está formulada sobre ella— y un contraste numérico
—desarrollada a −3.5 % del capítulo, proyectada a −9.0 %—. Con el hueco
corregido los dos convenios caen dentro del ±3 %: **+2.9 % la desarrollada y
−2.3 % la proyectada**. El contraste ya no discrimina. El convenio se mantiene,
pero apoyado solo en el argumento de coherencia, que era el fuerte; conviene que
el capítulo no invoque el otro.

### 11.3. Lo que NO cierra

**El ángulo de corrugación.** Ninguno de los cuatro documentos lo publica. Lo
que sí aportan es la designación de canal —`1*14H / 1*15H`—, que dice que las
dos corrientes van por canales **H**, de alta transferencia, y descarta la placa
L y los paquetes mixtos. Acota al extremo alto de la gama, no fija el número.

**El factor de alargamiento.** Tampoco, y no puede deducirse del área declarada
porque las dos unidades no se reconcilian bajo una misma lectura: el área
proyectada reconstruida del 27-30H, 28 × 0.111 × 0.250 = 0.777 m², **excede** los
0.7 m² declarados en un 11 %, mientras que la del 16-10H queda a solo +2.4 % de
la suya. O el largo efectivo del 27 no son los 250 mm entre puertos, o el ancho
efectivo no son los 111 mm de la envolvente. Hace falta el plano de la placa.

**φc, φv, C y m** no son datos de fabricante y nunca lo serán.

### 11.4. Lo que abre: el anclaje del condensador de placas

La ficha del 27-30H es un **punto de operación completo**, y es al condensador
de placas lo que el punto de ficha de la batería es al serpentín: el único dato
del que se dispone, y por tanto el único anclaje posible.

De él sale el coeficiente global. El U de servicio, Q/(A·MTD) = 10500/(0.7·7.3)
= 2055 W/(m²·K), lleva dentro el ensuciamiento que la propia ficha declara;
descontándolo, **U limpio = 4615 W/(m²·K)**. La comprobación de que el reparto
es el correcto es independiente: el margen que ese U limpio implica sale 125 %
frente al **122 % declarado**. Y el balance del lado de agua cierra la capacidad:
1.83 m³/h × 4.18 × 5 K = 10.5 kW.

Lo decisivo es que la ficha trae **dos datos independientes**, no uno: el térmico
(U) y el hidráulico (Δp del agua, 7.93 kPa a 1.83 m³/h). La correlación de
Martin liga transferencia y fricción a través del ángulo de corrugación, de modo
que hay dos ecuaciones para dos incógnitas: **β desde la pérdida de carga, y
φc·φv desde el coeficiente global**. Es la misma estrategia con que el §10.6.3
ancló el lado de aire, y es la salida del atasco de las placas.

Dos salvedades antes de intentarlo. El Reynolds del agua queda en torno a 800,
en régimen transicional, que es la misma debilidad que el §10.5.3 ya declara
para el desrecalentador; y la Δp de ficha incluye las pérdidas de puerto, del
orden del 5 %. Con un solo punto se identifica **una** constante por relación,
no dos: φc y φv seguirán sin poder separarse, igual que C₁ y C₂ en el lado de
aire.

### 11.5. Hallazgo colateral: ocho números que se leían como texto

Al contrastar el punto de selección salió que `Q_W: 10.5e3` no es un número.
YAML 1.1 exige signo en el exponente: `3.0e6` es una **cadena** y `3.0e+6` un
número. Ocho valores estaban así —cinco presiones y capacidades en el fichero de
placas, tres en el del compresor—, y ninguno había roto nada porque ninguno se
había usado todavía en un cálculo.

Es exactamente el fallo que el §10.13.4 describe: no rompe al cargar, rompe al
primer cálculo que lo use, y hasta entonces el dato parece estar. Corregidos, y
con un contraste que recorre los tres ficheros para que no vuelva.

---

## 12. El anclaje del condensador de placas — se rompe el atasco del §10.5.9

Cerrado el 18/09/2026. `plate_hx.anchor_from_selection_point`, contrastes en
`tests/test_anclaje_placas.py`.

La ficha del AlfaNova 27-30H trae **dos datos independientes** —el térmico y el
hidráulico— y la correlación de Martin los liga a través del ángulo de
corrugación. Dos ecuaciones, dos incógnitas. Es la misma estrategia con la que
el §10.6.3 ancló el lado de aire, con la ventaja de que allí había un solo dato
y aquí hay dos.

### 12.1. β, identificado y robusto

De la pérdida de carga del agua —7.93 kPa a 1.83 m³/h, descontadas las pérdidas
de puerto— sale **β = 71.6°**. Lo que lo hace utilizable es que apenas se mueve
con lo que sigue supuesto:

| variación | β |
|---|---|
| Φ de 1.10 a 1.30 | 72.7° → 68.7° |
| pérdida de puerto del 0 al 10 % | 72.7° → 70.4° |
| recorte efectivo de placa, sus dos lecturas | 67.4° → 73.9° |

En total **71 ± 4°**, y toda la banda está en la zona de placa de alta
transferencia.

**Y hay corroboración independiente.** La ficha designa los 29 canales como
`1*14H / 1*15H`, esto es, canales H. Un ángulo de 71° es de placa H. Las dos
informaciones no tienen nada que ver entre sí —una es una pérdida de carga
medida, la otra una designación comercial— y coinciden.

### 12.2. φc·φv, anclado pero no robusto

Con β fijado, el coeficiente del agua sale de Martin, la pared es conocida y el
del refrigerante queda por diferencia: **α_NH₃ = 11 391 W/(m²·K)**, frente a una
película de Nusselt sin corregir de 7 411. El cociente es **φc·φv = 1.54**.

A diferencia de β, **no es robusto**, y el número no significa nada solo:

| | φc·φv |
|---|---|
| Φ = 1.10 / 1.20 / 1.30 | 1.78 / 1.36 / 1.12 |
| área desarrollada / proyectada | 1.54 / 2.37 |

Debe viajar siempre con el Φ y el convenio con que se obtuvo. Y lo identificado
es el **producto**: φc y φv por separado exigen un segundo punto a otra
velocidad de vapor, igual que C₁ y C₂ del §10.6.3 no se separaron con un solo
punto.

Reparto de resistencias resultante: **agua 59 %, pared 10 %, refrigerante 32 %**.
La pared de inoxidable vuelve a pesar lo que RS-1 obliga a que pese.

### 12.3. Lo que desatasca

`plate_geometry` ya no falla, el componente resuelve sin inyectar nada y **los
cinco modos corren de extremo a extremo**. Dejan de ser exploratorios. Lo que
sigue abierto de ellos es la tolerancia del §10.11.4 a discretizaciones
asequibles, que es el problema del apartado 9 y no tiene que ver con los datos.

Verificación de que el anclaje está bien conectado y no solo bien hecho: marchado
el componente completo en las condiciones de ficha, da **10 780 W frente a los
10 500 declarados (+2.7 %)** y el agua sale a 45.1 °C frente a 45.0. El residuo
es del método —el anclaje se hizo con la MTD agregada y la marcha resuelve celda
a celda— y se declara.

### 12.4. Una conclusión anterior que se invierte

El apartado 7 recogía, para la reescritura del §10.5.8, que «la contribución
gravitatoria **domina en el condensador** por un factor de 11 sobre la
friccional e **invierte el signo** del resultado».

Ese factor se obtuvo con `chevron_generic`, que la tabla 10.7 declara PROVISIONAL
y que ni siquiera depende del ángulo de corrugación. Con **Martin** —la
correlación que el §10.5.3 dice haber empleado, sin coeficientes libres— y el
ángulo identificado, la fricción sale unas quince veces mayor y **pasa a
dominar**: 225 Pa frente a 57 de gravedad en el punto del contraste, con caída
neta de presión en lugar de ganancia.

Lo que sobrevive, y es lo que el §10.5.8 necesita, es que la gravedad **no es
despreciable**: pesa un cuarto de la friccional y basta para cambiar el signo en
los puntos de bajo caudal. En el propio punto de ficha del 27-30H sí domina —264
Pa frente a 129— y el signo sí se invierte, porque el caudal es menor. La
conclusión correcta no es «la gravedad domina» sino «las dos son del mismo orden
y cuál manda depende del punto de operación», que sigue obligando a declarar el
sentido de montaje.

Hay además un contraste débil a favor de Martin: la ficha declara 58 Pa en el
lado de amoníaco, y la contribución friccional que el modelo calcula es de 129
Pa con Martin y de 8.5 Pa con la provisional. Ninguna acierta —el multiplicador
bifásico es a su vez una extrapolación declarada— pero Martin está en el orden
correcto y la provisional un factor 7 por debajo.

### 12.5. Dos tareas que el anclaje deja abiertas

**La frontera de zona en la discretización.** Con la película anclada el
coeficiente de condensación sube un 54 %, el salto de α a través de la frontera
desrecalentamiento-condensación se agranda, y el estudio de independencia de
malla deja de converger: se queda oscilando en el 1 % hasta n = 320.

El diagnóstico aísla la causa sin ambigüedad. Con vapor **saturado** a la
entrada, esto es sin zona monofásica y por tanto sin frontera que cruzar, la
misma serie converge a 6·10⁻⁶. No es la correlación: es el volumen finito sin
seguimiento de la interfase. La solución es **partir la celda donde el título
cruza 0 o 1**, y es una tarea acotada del marchador.

Tiene una consecuencia de medida que conviene no perder: el contraste entre
ΔT_lm y ΔT aritmética (D8) **solo puede hacerse con la malla convergida**. A
n = 20/40/80/160 la desviación da 3.1·10⁻³, 2.0·10⁻³, 1.9·10⁻² y 4.1·10⁻⁶: a
malla gruesa ya no mide el convenio, mide en qué celda ha caído la frontera. Con
n = 160 la conclusión de D8 se sostiene intacta.

**El factor de alargamiento** sigue estimado, y es lo que impide convertir
φc·φv en un número y no en una banda. Sigue siendo dato a pedir: el plano de la
placa, o el criterio del configurador.

### 12.6. Hallazgo colateral: el fichero de datos se analizaba en el lazo

Al anclar, la correlación pasa a consultar su coeficiente en cada invocación, y
por tanto **dentro del lazo por celda**: del orden de 2 000 análisis de YAML por
`solve()`. La suite pasó de 100 s a más de 400.

Es el mismo error que el §10.13.4 persigue con `PropsSI`, cambiando de
biblioteca: lo caro no es el dato, es volver a leerlo. `data.load` memoriza ahora
el análisis por ruta y fecha de modificación —la fecha, para que editar un
fichero siga surtiendo efecto sin reiniciar—. Dos mil lecturas bajan de minutos
a 0.07 s.

---

## 13. Seguimiento de la frontera de fase — cerrado

Cerrado el 21/09/2026. `plate_hx._march` y `plate_hx._solve_cell`, contrastes al
final de `tests/test_plate_hx.py`.

Era la tarea que el apartado 12.5 dejó abierta. La marcha ya no reparte el área
en `n` volúmenes iguales y sigue adelante: cuando un volumen cruzaría por dentro
el título 0 o 1, se **recorta hasta la frontera** y el resto del área pasa al
volumen siguiente. Ningún volumen contiene dos regímenes y las fronteras caen
siempre en un borde.

La frontera se impone **exactamente** en lugar de dejarla en lo que devuelva la
última iteración del recorte, de modo que el volumen siguiente arranca sobre
ella y el balance entálpico no arrastra deriva. `n_cells` pasa a ser el número
**nominal**: los volúmenes resueltos son `n` más uno por frontera cruzada, y las
magnitudes por volumen se promedian por área y no por recuento. `n_volumenes` y
`n_recortes` viajan en el resultado, y el segundo es además diagnóstico: dice
cuántas transiciones de régimen atraviesa el componente.

### 13.1. Lo que arregla

El estudio de independencia de malla del §7.7.1, sobre el condensador con
entrada sobrecalentada:

| n | 20 → 40 | 40 → 80 | 80 → 160 | 160 → 320 |
|---|---|---|---|---|
| antes | 1.9·10⁻³ | 1.3·10⁻² | 5.1·10⁻³ | — |
| ahora | 2.3·10⁻⁴ | 1.0·10⁻⁴ | 4.2·10⁻⁵ | 2.0·10⁻⁵ |

Pasa de oscilar en el 1 % sin converger a ser **monótona** y caer dos órdenes.
Desaparece con ello el motivo por el que la serie del test tenía que arrancar en
n = 20 en lugar de n = 10.

Con ello vuelven a sus umbrales originales los dos contrastes que llevaban
dentro una nota de límite: la independencia de malla a 10⁻³ y el contraste D8
entre ΔT_lm y aritmética a 5·10⁻⁴. Este último recupera además la monotonía
—1.4·10⁻³, 3.6·10⁻⁴, 9.0·10⁻⁵ y 2.2·10⁻⁵ a n = 20, 40, 80 y 160— y se evalúa
desde n = 40: a n = 20 queda en 1.4·10⁻³, y no por un artefacto sino porque la
película anclada da un coeficiente un 54 % más alto y con él un perfil más
curvado. La conclusión de D8 no se mueve.

### 13.2. Lo que desbloquea

**M-1 con placas converge.** El residuo del lazo externo pasa de 3.0·10⁻³ a
**2.9·10⁻¹³**, esto es, de no alcanzar la tolerancia del §10.11.4 a superarla
por siete órdenes. Era el problema que el apartado 9 dejó abierto.

**La malla gruesa ya sirve.** Con n = 10 volúmenes el resultado queda a menos
del 0.5 % del de malla fina, y con n = 20 a menos del 0.2 %. Es lo que hace
asequibles las campañas estacionales del cap. 12.

### 13.3. Lo que NO arregla, medido

De los cinco modos, solo M-1 alcanza la tolerancia. Con `n_cells` 12 y 24:

| modo | residuo |
|---|---|
| M-1 | 2.9·10⁻¹³ ✅ |
| M-2 | 3.8·10⁻² |
| M-3 | 1.9·10⁻³ |
| M-4 / M-5 | 1.3·10⁻³ a 2.0·10⁻³ |

Refinar la malla no los mueve —M-2 da 3.8·10⁻² con 12 y con 24 volúmenes—, de
modo que **lo que queda no es discretización**: es el disparo del tren extendido
del §10.3.1 que el apartado 9 describe, donde la temperatura del agua en la
unión no es dato de ninguno de los dos intercambiadores y se amplifica en el
residuo de recalentamiento por el cociente ṁ_agua·c_p/ṁ_ref. Es la tarea
siguiente de esa línea.

Y dos verificaciones independientes siguen en rojo en la configuración completa,
ambas anteriores a este cambio: `compresor_metodo_convergido` y el balance de
componente de las dos unidades de placas, en 1.5·10⁻³. El balance del componente
aislado no se mueve con el recorte —1.59·10⁻⁴ frente a 1.53·10⁻⁴ antes—, de modo
que el residuo es del cierre en el circuito y no del marchador.

### 13.4. La batería tiene el mismo defecto, más leve

Medido, para no dejarlo supuesto. El serpentín marcha igual, con áreas fijas, y
su estudio de malla también pierde la monotonía en M-1: 4.6·10⁻⁴, 1.1·10⁻³,
6.8·10⁻⁴ y 1.6·10⁻⁴ al pasar de 50 a 800 segmentos.

Es el mismo mecanismo, un orden de magnitud más débil, y por una razón que
conviene anotar: el lado de aire se lleva el 73 % de la resistencia, de modo que
el salto de coeficiente del lado de refrigerante al cruzar la frontera queda
amortiguado. Converge, no bloquea nada y por eso no se ha tocado en este cambio.

Hacerlo tiene valor, y es de velocidad más que de exactitud: el circuito evalúa
el serpentín en cada iteración del lazo externo, y poder bajar de 200 a 50
segmentos con la misma exactitud es un factor cuatro en el componente que más se
repite. Queda como tarea acompañante, con el aviso de que el marchador de la
batería es hoy más complejo que el de placas —regímenes seco y húmedo,
diagnóstico anular/estratificado, inventario— y el recorte toca todos los
acumuladores.

---

## 14. Fase G — el plan de V&V, fechado antes de ejecutarlo

Abierta el 21/09/2026. `src/amoniatermia/validation/`, contrastes en
`tests/test_validacion.py`, datos en `data/validacion_tabla_7_5.yaml`.

La razón de hacerla ahora y no al final está en la guía de implementación, y no
es de comodidad: «los umbrales de aceptación de la tabla 7.5 deben estar
escritos en el código de validación **antes** de ejecutarlo por primera vez.
Fijarlos después de ver los resultados es una debilidad metodológica grave y
perfectamente detectable en el historial de git, que en este caso jugaría en tu
contra». Lo que se fecha es la decisión, no el resultado.

### 14.1. Lo que queda cerrado

**Las cuatro métricas del §7.7.3**, en `validation.metrics`: error relativo
medio, error absoluto medio, RMSE y fracción de puntos dentro de la banda. Dos
decisiones que conviene declarar:

- El error se define como `modelo − referencia`, de modo que un error relativo
  medio positivo significa que el modelo **sobreestima**.
- El error relativo medio y el absoluto miden cosas distintas y el apartado pide
  los dos precisamente por eso. Un modelo que se pasa en la mitad de los puntos
  lo que se queda corto en la otra tiene sesgo **nulo** y dispersión grande;
  reportar solo el primero lo daría por perfecto. `sesgo_domina` separa los dos
  casos, porque la acción que procede es distinta: un sesgo apunta a un
  parámetro mal identificado y una dispersión a una correlación que no captura
  la física.

El contraste **falla** en lugar de devolver un número sin sentido cuando las
series no se corresponden punto a punto, cuando no hay puntos, o cuando la
referencia es nula y el error relativo no está definido. Y devuelve el **peor
punto** identificado, que es lo que convierte una métrica agregada en algo
accionable.

**Los ocho casos de solución conocida del §7.7.1**, que el §10.13.5 enumera
literalmente, quedan inventariados con el test que los materializa. El
inventario se verifica: `missing_tests()` comprueba que el fichero existe y,
cuando se nombra un nodo concreto, que el nodo existe. Es además un candado —
renombrar un test de verificación sin actualizar el inventario lo rompe—, y
responde a lo que el §10.13.5 exige: que la ejecución «sea la evidencia de que
la verificación se ha realizado efectivamente y no solo se ha declarado».

**El estatuto de cada fuente de contraste.** Dos merecen mención:

- **Zajacs et al. (2017) NO es fuente de validación.** Es un estudio de diseño
  por simulación con EES; compararlo sería comparar simulación contra
  simulación. Se conserva **declarado** y no simplemente borrado, para que la
  reclasificación quede registrada y no se cuele por inercia si alguien vuelve a
  la tabla 7.5 del capítulo 7 sin haberla corregido.
- **La ficha del AlfaNova 27-30H está consumida como anclaje.** Desde que β y
  φc·φv se identificaron sobre ella, el modelo la reproduce por construcción y
  usarla como validación sería circular. Queda marcada como tal.

Las únicas fuentes experimentales son Monfared y Palm (2011, 2012), las dos con
reserva: las fuentes abiertas solo dan especificaciones agregadas, de modo que
sirven para contrastar capacidad y COP, no para validar un submodelo.

**Las tolerancias adoptadas**, recogidas en un solo sitio en lugar de repartidas
por los tests: 2 % en magnitud calculada y 0.5 % en geométrica, 10⁻⁶ de residuo
del §10.13.4 y 10⁻³ de cierre de balances. Llevan un nombre distinto del de los
umbrales —`adopted_tolerance` frente a `threshold`— a propósito: no son la tabla
7.5, son decisiones ya en vigor. Un contraste comprueba que el 10⁻⁶ declarado es
el que `circuit.py` aplica de verdad, porque si divergen el plan documenta un
criterio que nadie usa.

### 14.2. Llegó el capítulo 7, y corrige el apartado anterior

Aportado el 21/09/2026 y transcrito en `docs/cap7_metodologia.md`. Dos
correcciones, y la segunda es la que importa.

**La tabla 7.5 tiene CINCO niveles, no tres.** La jerarquía de la tabla 10.1
—componente, circuito, sistema— es la del **modelo**; la de la tabla 7.5 es la
de la **validación**, y no coincide: reparte el nivel de componente en dos
porque tienen fuentes distintas, añade un nivel de subsistema para la
recuperación de ACS y otro de coherencia global.

| Nivel | Fuente | Magnitudes | Criterio |
|---|---|---|---|
| N1. Componente — compresor | Prestaciones y software de selección del fabricante | Caudal, potencia al eje, T de descarga | Desviación media ≤ […] % |
| N2. Componente — intercambiadores | Software de selección y correlaciones publicadas | U, potencia, pérdida de carga | Desviación media ≤ […] % en potencia |
| N3. Sistema — literatura | Monfared y Palm (2011, 2012); Zajacs et al. (2017) | COP y potencia calorífica | ≤ ±[…] % en COP y ±[…] % en potencia |
| N4. Subsistema — ACS | Palm (2008); Monfared y Palm (2011) | Potencia recuperada y T de ACS | Tendencia y desviación ≤ […] % |
| N5. Coherencia global | Primer y segundo principio | Cierre de balances y entropía | **Cumplimiento estricto** |

**Y los criterios siguen sin fijar, pero por otra razón.** No es que el capítulo
los tenga y aquí faltasen: **el capítulo tampoco los tiene**. Los cuatro
primeros llevan «[…]» en la propia tabla, y la cabecera del borrador advierte de
que «los espacios marcados […] requieren fijar un valor antes de cerrar el
capítulo». Las notas de revisión cuentan trece en todo el capítulo, casi todos
tolerancias.

El único criterio fijado es el de N5, «cumplimiento estricto», y no lleva número
porque no admite tolerancia: es el primer y el segundo principio.

Lo que el capítulo sí ofrece son **sugerencias de partida**, en sus notas de
revisión: independencia de discretización 1 %, cierre de balances 0.5 %,
compresor 5 % en caudal y 8 % en potencia, sistema ±10 % en COP y ±15 % en
potencia, banda de paridad ±10 %. Se recogen en el fichero de datos bajo
`sugerido_cap_7`, **separadas de `umbral`**, y `threshold()` no las usa: una
sugerencia no es una decisión, y cargarla como criterio sería decidir por el
autor. `suggested()` las devuelve para que la decisión pueda tomarse a la vista
de ellas.

### 14.3. Tres cosas que el capítulo 7 pone al descubierto

**La verificación de tendencias del §7.7.1 no existía.** El apartado pide
«consistencia física de las tendencias frente a comportamientos conocidos:
efecto del aumento de la temperatura de condensación sobre el COP, efecto del
subenfriamiento sobre la producción frigorífica específica y efecto de la
relación de compresión sobre la temperatura de descarga». El §10.13.5 enumera
los casos de solución conocida pero **no recoge este grupo**, de modo que la
verificación estaba declarada en el capítulo 7 y no ejecutada en ninguna parte.
Se añade en `tests/test_tendencias.py`, y las tres tendencias se cumplen.

**El repositorio es más estricto que el capítulo en el cierre de balances.**
`circuit.py` adopta 10⁻³ y la sugerencia es 0.5 %, cinco veces más laxa. No fue
un descuido: se adoptó cuando el §7.7.1 no estaba disponible. Pero tiene
consecuencia y hay que verla antes de decidir: **con 0.5 % los modos M-3 a M-5,
cuyo balance de componente queda en 1.5·10⁻³, pasarían de no válidos a
válidos**. Alinear el código con el capítulo sin mirar eso sería relajar un
criterio por inercia. `divergencias_con_el_capitulo()` lo reporta.

**El nivel N4 se queda sin fuente utilizable.** Sus dos fuentes son Palm (2008),
que no aparece en el material del repositorio, y Monfared y Palm (2011), que no
tiene datos transcritos. N4 es el nivel de la recuperación de ACS, esto es, **el
que sostiene H3**. Conviene que el capítulo 11 lo diga.

### 14.4. Los criterios, fijados el 21/09/2026

**Decisión del autor, y tomada hoy a propósito**: adoptar las sugerencias de las
notas de revisión allí donde el capítulo las da. El momento importa. Tomada
ahora, queda fechada en el historial **antes de que exista ningún resultado de
validación que pueda condicionarla**, que es exactamente lo que el capítulo
pide. Tomada después, no habría forma de demostrarlo.

| | Criterio adoptado | Procedencia |
|---|---|---|
| N1 | 5 % en caudal, 8 % en potencia al eje | sugerencia del cap. 7 |
| N2 | **sin fijar** — el capítulo no sugiere valor | — |
| N3 | ±10 % en COP, ±15 % en potencia | sugerencia del cap. 7 |
| N4 | **sin fijar** — el capítulo no sugiere valor | — |
| N5 | cumplimiento estricto | fijado en la tabla 7.5 |
| Banda de paridad (§7.7.3) | ±10 % | sugerencia del cap. 7 |
| Independencia de discretización (§7.7.1) | 1 % | sugerencia del cap. 7 |
| Cierre de balances (§7.7.1) | **10⁻³**, no el 0.5 % sugerido | decisión, más estricto |

Dos decisiones merecen justificarse.

**El cierre de balances se mantiene en 10⁻³**, cinco veces más estricto que la
sugerencia. Ser más exigente que el criterio declarado no es una debilidad
metodológica; relajarlo sí lo sería, porque el efecto inmediato sería que los
modos M-3 a M-5 pasasen de no válidos a válidos **sin que su residuo haya
mejorado en nada**. La divergencia se conserva reportada, y el capítulo 11 debe
decir que el modelo se juzga con un criterio más exigente que el que declara.

**La independencia de discretización, 1 %, no acota nada.** Desde el
seguimiento de la frontera de fase el modelo llega a 2·10⁻⁵, tres órdenes por
debajo. Se adopta igualmente por coherencia con el capítulo, y se declara que
está holgadamente cumplido en lugar de presentarlo como un ajuste apretado.

**Hallazgo al cargar la tabla:** N1 lista **tres** magnitudes —caudal, potencia
al eje y temperatura de descarga— y el capítulo sugiere **dos** tolerancias. La
temperatura de descarga se queda sin criterio propio, y no es menor: de ella
depende H3, y la fase B ya abrió una discrepancia de 18 K entre los 140.4 °C
del §10.6.9 y los 122.2 del catálogo. Queda anotado en el fichero de datos.

### 14.5. Lo que sigue sin poder cerrarse

**Los criterios de N2 y N4**, porque el capítulo no sugiere valor para ellos.
Quedan a `null` y pedirlos falla.

**Los datos de las tres fuentes experimentales**, que es la acotación honesta
del alcance: la maquinaria está, los datos de contraste externos no.

### 14.6. Una anomalía del propio plan de validación

Merece anotarse para el capítulo 11. De las siete fuentes inventariadas, **tres
no sirven para validar** —Zajacs por ser simulación, el 27-30H por estar
consumido como anclaje, Palm (2008) por estar sin localizar—, **tres no tienen
datos** —las de KTH— y **tres son de fabricante**, esto es, reproducen el
resultado de otro modelo y no una medida.

El plan de validación del capítulo 7 debe revisarse con eso delante: hoy no hay
ninguna fuente experimental con datos utilizables, y conviene que el capítulo 11
lo diga en lugar de presentar un plan cuyas fuentes no están disponibles.

---

## 15. Fase F — indicadores energéticos y exergéticos

Cerrada el 21/09/2026. `src/amoniatermia/indicators.py`, contrastes en
`tests/test_indicadores.py`. Implementa las ecuaciones 10-46 a 10-50 y con
ellas las métricas de decisión que la tabla 7.2 asigna a **H1** —desviación en
COP y potencia térmica— y a **H6** —cociente de destrucción de exergía del
compresor sobre el total—.

### 15.1. Cinco decisiones declaradas

**El ventilador va en el denominador**, como exige la UNE-EN 14511 y repite el
§10.6.8. No es contabilidad menor: con 780 W frente a ~2.7 kW de compresor,
omitirlo inflaría el EER un 30 % y haría los resultados incomparables con
equipos comerciales, que es la comparación que sostiene H1.

**Las bombas no van, porque no están modeladas.** El §7.8.2 avisa de que
omitir la potencia auxiliar «es una fuente frecuente de sobreestimación del
rendimiento estacional». El indicador es por tanto una **cota superior**, y la
marca viaja con el número en lugar de quedarse en una nota.

**Qué cuenta como producto no se deduce del signo del calor.** En M-5 el
intercambiador de climatización cede calor exactamente igual que en M-2, pero
allí es el servicio y aquí es el rechazo del calor residual (decisión D-1).
Contarlo inflaría el COP de M-5 con lo que se tira. `ModeSpec` gana un campo
`clima` —`frio`, `calor` o `disipacion`— porque es información del **modo**, no
del punto, igual que la topología.

**El Carnot se forma con los focos, no con el refrigerante.** Tomar las
saturaciones ocultaría dentro del Carnot el salto térmico de los
intercambiadores, que es precisamente una de las irreversibilidades que el
análisis quiere localizar. Se usa la media logarítmica del agua del servicio y
la temperatura del aire exterior.

**η_II es una eficiencia, no una pérdida.** El §10.12.2 y el §7.9 lo marcan
como error a corregir de la Rev10. `ExergyIndicators` expone las dos magnitudes
con su nombre —`eta_II` y `perdida_segunda_ley`— para que nadie tenga que
despejarlo y se equivoque al hacerlo.

### 15.2. El cierre exergético, y lo que encontró

La exergía eléctrica que entra tiene que salir como producto útil o destruirse.
Se añade ese cierre como **verificación**, al lado del balance de energía del
§10.11.4, y se reporta con el resultado.

Encontró un error a la primera. En M-4 daba **−82 %**: más exergía destruida
que potencia eléctrica consumida, que es imposible. La causa estaba en
`circuit._entropy`, que tomaba la variación de entropía del aire como
**solo la parte sensible**, `m·cp·ln(T_out/T_in)`. Es exacto con la superficie
seca —el condensador de M-1— y falso en cuanto condensa: dejaba fuera la
entropía que se lleva el vapor al pasar a líquido, que en la condición nominal
de calefacción es **un tercio del calor intercambiado**. La generación de
entropía del serpentín salía en 11.0 W/K cuando la real es 0.65.

Y deja una lección que conviene anotar: la generación de entropía del serpentín
es la **diferencia entre dos números veinticinco veces mayores que ella**. Al
corregir el término latente se probó también la entropía de mezcla exacta, que
difiere de la sensible un 1.6 % —el modelo ancló el aire con cp = 1005 J/(kg·K)
por kg de mezcla y la de mezcla equivale a 1039 por kg de aire seco—, y ese
1.6 % movía la generación del serpentín un **38 %**. Se adopta el cp del
anclaje, por coherencia con la energía que el componente calcula, y se declara
la fragilidad: cualquier resultado que descanse en la entropía del serpentín
—el reparto de exergía destruida, sin ir más lejos— la hereda.

Con la corrección, los tres modos cierran al 1 %.

### 15.3. Resultados

Circuito completo, consignas de 5 K de recalentamiento y 2 K de
subenfriamiento, ACS a 60 °C desde red a 10 °C.

| | servicio | global | W_el | y_D compresor | η_II | cierre |
|---|---|---|---|---|---|---|
| M-1 (verano) | EER 2.96 | 2.96 | 3452 W | 0.245 | 0.270 | +1.2 % |
| M-3 (verano + ACS) | EER 2.91 | **3.60** | 3274 W | 0.247 | 0.263 | +0.9 % |
| M-4 (invierno + ACS)\* | COP 2.24 | 3.04 | 3517 W | 0.272 | 0.253 | +1.1 % |

\* M-4 **no converge** (residuo 3.3·10⁻³, apartado 13.3). Los indicadores se
calculan y se marcan; no son resultado utilizable.

La recuperación aporta un **+23.5 %** al indicador global en M-3, que es la
magnitud con la que H3 se sostiene por el lado energético.

### 15.4. Un hallazgo que tensiona H3

**En verano, el ACS tiene energía y no tiene exergía.** Con el estado muerto en
el ambiente simulado —35 °C en refrigeración— el agua de 10 a 60 °C tiene una
exergía de **−5 W frente a 2238 W de energía**. La razón es que la mitad del
calentamiento ocurre *por debajo* del ambiente, y el agua a 10 °C está tan lejos
del estado muerto como la de 60 °C.

En invierno, con el ambiente a 7 °C, el mismo salto sí tiene valor: **+252 W**.
No es una propiedad del ACS, es del estado muerto.

La consecuencia es que **la lectura energética y la exergética dicen cosas
opuestas del mismo subproducto**: el COP global sube un 23.5 % por la
recuperación y el rendimiento de segunda ley no se mueve. El capítulo 12 tiene
que elegir con cuál argumenta H3, y declararlo.

Obliga además a matizar el §7.9, que dice que «la elección del estado muerto
afecta a los valores absolutos de exergía pero no a la ordenación relativa de
las irreversibilidades entre componentes». Es cierto para las
irreversibilidades. **No lo es para la exergía de los productos**, que aquí
cambia de signo con el ambiente.

### 15.5. Lo que queda

El **SCOP y el SEER** del §7.8.2 —agregación estacional por el método de
intervalos de la UNE-EN 14825, con los tres perfiles climáticos— son de la fase
H, no de esta: necesitan campañas, no indicadores de punto. Lo que la fase F
deja listo es el indicador de punto sobre el que esas campañas agregan.

---

## 16. Fase H — rendimiento, backend tabular y campañas

Cerrada el 21/09/2026. `src/amoniatermia/campaign.py`, ampliación de
`props.backend_deviation_report`, contrastes en `tests/test_campana.py`.

Se empezó por medir, y la medida decidió el trabajo: un punto de M-3 con el
circuito completo costaba **108.6 s**, de los que `update_PH` se llevaba 47.4 s
en **2.3 millones de llamadas**. El §10.10 estima ~10⁵ evaluaciones de
propiedades por punto; estábamos veintitrés veces por encima.

### 16.1. De 108.6 s a 5.2 s, y sin cambiar el resultado

Tres cosas, ninguna de ellas una aproximación:

**El estado del volumen se evaluaba dentro del lazo sobre q''.** El lazo itera
hasta veinticinco veces con (P, h) **fijos** —lo único que cambia entre
iteraciones es el flujo de calor— y reevaluaba las propiedades cada vez. Se
extrae a `_cell_state`, que se calcula una vez por volumen. También se saca del
lazo de recorte de la frontera de fase, que reresuelve el mismo volumen hasta
seis veces con otra área pero con el mismo estado. **108.6 → 35.0 s.**

**Un millón de llamadas al sistema de ficheros por punto.** La película de
condensación anclada consultaba su coeficiente en `data.load` en cada
invocación, y aunque el análisis del YAML ya estaba memorizado, seguía haciendo
un `stat` y una resolución de ruta cada vez. El componente lo resuelve ahora una
vez, en la construcción, y lo pasa por `corr_params`, que es la vía declarada.
Es el mismo error que el §10.13.4 persigue con `PropsSI`, cambiando de
biblioteca: **lo caro no es el dato, es volver a pedirlo.** → 30.5 s.

**El backend tabular en los intercambiadores.** → **5.2 s.** Ver abajo.

La suite completa pasa de 261 s a 215 s pese a haberle añadido 20 contrastes.

### 16.2. El backend tabular: la respuesta es que sí, pero solo a medias

El §7.6.4 condiciona su empleo «a que dicha desviación resulte inferior al
umbral declarado», y el informe que había solo cubría el par **PT**, que es
justo el que el modelo apenas usa: es degenerado dentro de la campana. El
informe cubre ahora los **seis pares** que el modelo emplea de verdad.

| par | desviación máxima frente a HEOS |
|---|---|
| PT | 3.6·10⁻⁴ en ρ |
| **PH** (el del camino caliente) | **4.4·10⁻⁶** |
| PQ | 1·10⁻¹¹ (pasa a HEOS sobre la saturación) |
| PS | 5.9·10⁻⁶ |
| **DH** | **NO SOPORTADO** |
| **DS** | **NO SOPORTADO** |

**La exactitud no es el problema; la cobertura sí.** El backend tabular de
CoolProp no admite las entradas por densidad, y el compresor las necesita: la
ec. 10-5 resuelve la compresión isócora hasta el volumen específico interno por
DS y la 10-6 evalúa la presión de esa etapa en el estado real por DH. El ×163
que anuncia la tabla 10.16 **no es aplicable al compresor**.

Segunda carencia, encontrada al montar la campaña: **tampoco da la tensión
superficial**. Alimenta tres de las cuatro correlaciones de fracción de huecos y
con ellas el inventario de carga, que es lo que contrasta H4. El modelo la toma
ahora de un estado HEOS auxiliar, y queda declarado.

La salida es por tanto **mixta**: HEOS en el compresor y en el lazo externo,
tabular en los intercambiadores. Da 2.5 a 5 veces según el modo, con el mismo
punto de equilibrio: a la malla de trabajo la diferencia en el EER es de
**4·10⁻⁷**.

**Y hay una contrapartida que hay que declarar.** El ruido de interpolación pone
un **suelo al residuo** que el lazo externo puede alcanzar: queda en el entorno
de 10⁻⁶, esto es, del mismo orden que la tolerancia de 10⁻⁶ que el §10.13.4
declara, mientras que en HEOS el mismo punto baja a 10⁻¹⁰. Una campaña con
backend tabular puede marcar como no convergidos puntos cuya respuesta es
correcta a 10⁻⁴, y eso hay que saberlo antes de interpretar su recuento.

### 16.3. La puerta del §7.6.4, hecha cumplir

`campaign.build_circuit` no deja tomar el atajo sin dejar constancia: pedir un
backend tabular **sin umbral es un error**, y con umbral se ejecuta la
verificación cruzada, se comprueba y **el informe viaja en la procedencia**. Si
la desviación excede el umbral, se rechaza.

### 16.4. Campañas

`campaign.run` compone lo que faltaba alrededor de `circuit.sweep`:

- La **procedencia** con los cinco elementos del §10.13.6, adjunta al resultado
  y no reconstruida después. `write()` escribe filas y procedencia en el mismo
  fichero, porque un resultado sin su procedencia no cumple el §7.12.
- Los casos **no convergidos conservados y contados**. El §7.12 exige que «se
  registren y se reporten, en lugar de ser descartados silenciosamente» y el
  §7.6.6 que se excluyan «con indicación expresa»: las dos cosas a la vez
  significan conservarlos marcados, que es lo que `rows` hace y `validos()`
  filtra.
- La **marca de extrapolación** por fila, y los indicadores de la fase F.

Barrido de comprobación, aire exterior de 25 a 45 °C en M-1:

| aire | T_cond | EER | η_II | carga máx. | W_el |
|---|---|---|---|---|---|
| 25 °C | 36.1 °C | 3.68 | 0.208 | 442 g | 2980 W |
| 35 °C | 45.7 °C | 2.96 | 0.270 | 451 g | 3452 W |
| 45 °C | 55.2 °C | 2.38 | 0.299 | 465 g | 3961 W |

Las tendencias son las que deben ser, y η_II **sube** con el ambiente mientras
el EER baja: el Carnot se degrada más deprisa que la máquina.

### 16.5. Lo que esta fase no cubre

**SCOP y SEER** del §7.8.2 —agregación por intervalos de la UNE-EN 14825 con
los tres perfiles climáticos— son del capítulo 13. Lo que queda listo es la
campaña sobre la que agregan y el indicador de punto que agregan.


---

## 17. El R-744 sale del conjunto comparativo

Decisión del autor del 21/09/2026. No se modela el ciclo transcrítico, y el
R-744 probablemente salga de la tesis; quedaría como tratamiento cualitativo
del capítulo 6. Es la segunda de las dos opciones que las notas de revisión del
capítulo 7 ponían sobre la mesa, y la que ese capítulo señalaba como la barata.

**El código no pierde nada.** Las cuatro provisiones que D-2 declaró «no
aplazables» se quedan todas, porque ninguna dependía solo del R-744: el vector
de incógnitas por modo lo exige el reparto de M-5, la familia de correlaciones
nueva llegó por la separación tubo/placa de C4, y que `plate_hx` no admita
presiones supercríticas pasa de problema a límite declarado del componente.

**La cuarta se refuerza en lugar de caerse.** «Las campañas deben tratar el
fluido como parámetro» sigue siendo necesario, porque H5 compara igualmente
R-717 con R-290 y R-32 sobre la misma geometría. `campaign.build_circuit` lo
hacía con «Ammonia» escrito a mano: ahora el fluido es parámetro,
`FLUIDOS_COMPARATIVOS` declara el conjunto, y los tres montan circuito.

Con un aviso que viaja en el propio módulo: la geometría y los parámetros
identificados que el modelo carga son los del amoníaco, de modo que correr con
R-290 o R-32 emplea el compresor de NH₃ **sin reidentificar y sin adaptar la
cilindrada**. Falta la adaptación que la tabla 7.6 exige, y hasta entonces el
punto no es comparable.

### 17.1. Lo que obliga a revisar en la redacción

- El §7.8.3 y su tabla 7.6, con el recuadro «Advertencia sobre el R-744», y la
  nota de revisión que dejaba la decisión pendiente.
- El §7.1, que justifica el enfoque de simulación diciendo que H5 «exigiría
  construir **cuatro** máquinas geométricamente idénticas». Pasan a ser tres.
- **La formulación de H5, y esto es lo serio.** H5 afirma que el R-717 supera a
  «las restantes **alternativas naturales** evaluadas en igualdad de
  condiciones». Las naturales del conjunto eran el R-290 y el R-744; el R-32 es
  un HFC. Retirado el R-744, **H5 descansa sobre una sola comparación con
  alternativa natural**.

  Dos salidas, y hay que elegir una antes de redactar el capítulo 14:
  reformular la hipótesis en términos de alternativas de **bajo PCA**, que
  incluye al R-32 y la sostiene con dos comparaciones; o aceptar que el
  contraste natural es frente al R-290 y decirlo así, apoyando el resto en el
  R-32 como referencia de mercado.

---

## 18. El suelo de residuo de los modos con placas — no era el tren

Cerrado el 22/09/2026. `air_hx._solve_segment` y el recorte en
`air_hx.solve`; contrastes en `tests/test_air_hx.py::TestFronteraDeFaseSerpentin`
y `tests/test_circuit.py::TestConvergenciaDeM2`.

El apartado 13.3 dejó abierto que M-2 a M-5 no alcanzan la tolerancia del
§10.11.4 y lo atribuyó al disparo del tren extendido del §10.3.1, «donde la
temperatura del agua en la unión no es dato de ninguno de los dos
intercambiadores y se amplifica en el residuo de recalentamiento por el cociente
ṁ_agua·c_p/ṁ_ref». `docs/PENDIENTES.md` añadía la sospecha de que ese disparo
pudiera no tener raíz única.

**Medido, ninguna de las dos cosas se sostiene.**

### 18.1. El disparo del tren tiene raíz única y es monótono

Escaneada la función de disparo sobre el intervalo físico completo —el agua no
puede cruzar la temperatura del refrigerante— en el punto convergido de M-2:
**25 puntos, un solo cambio de signo, y la función es monótona** con pendiente
≈ 1 K por K. Su tolerancia, 10⁻⁷ K, deja un efecto de orden 10⁻⁸ en el residuo,
cuatro órdenes por debajo del suelo observado.

La sospecha de multiplicidad procedía de que el arranque en caliente daba un
residuo distinto (0.470 frente a 0.330). Con el escaneo delante, la explicación
es otra: el arranque en caliente partía de un intervalo estrecho **alrededor de
la solución anterior**, y lo que cambiaba no era la raíz sino dónde se detenía
la marcha del serpentín, que es el escalón del apartado siguiente.

### 18.2. Lo que bloqueaba era un escalón, y estaba en la batería

Cortando el residuo alrededor de la solución de M-2, R₂ —el recalentamiento a la
salida del evaporador, que en M-2 es la batería— **salta de 2.98·10⁻³ a
1.16·10⁻² al mover log P₀ en 10⁻⁷**, esto es, 0.04 Pa. R₄, que va por el tren,
es liso en la misma dirección. El método se detiene sobre el escalón con
«xtol termination», que es lo que se venía leyendo como falta de convergencia.

Qué cambia exactamente al cruzarlo:

| | δ = −10⁻⁷ | δ = +10⁻⁷ |
|---|---|---|
| Segmentos bifásicos / sobrecalentados | 53 / 7 | **54 / 6** |
| Reparto de volumen (vapor) | 0.1167 | **0.1000** |
| Temperatura de salida | 4.90 °C | **7.29 °C** |

Un segmento pasa de sobrecalentado a bifásico y la salida da un salto de 2.4 K.
Es **el mismo defecto que se corrigió en `plate_hx` el 21/09** —la marcha
repartía el área en segmentos iguales y seguía adelante— y que el apartado 13.4
había aplazado para la batería por considerarlo solo cuestión de velocidad. No
lo era.

El escalón se reduce al refinar, pero despacio: 8.6·10⁻³ con 60 segmentos,
3.1·10⁻³ con 120 y 2.1·10⁻³ con 240. Refinar no es la salida.

### 18.3. La corrección, y lo que cuesta

El serpentín recorta ahora en la frontera igual que las placas: cuando un
segmento cruzaría por dentro el título 0 o 1, se recorta hasta ella y el resto
del área pasa al siguiente. El caudal de aire de cada segmento pasa a ser
**proporcional a su área** —la marcha trata el aire como corrientes paralelas— y
todo lo que antes se promediaba por recuento se promedia ahora por área.

| Modo | Residuo antes | Residuo ahora | Coste antes → ahora |
|---|---|---|---|
| M-1 | 3.9·10⁻⁹ | **3.8·10⁻¹¹** | 13.3 → 12.6 s |
| M-2 | 3.0·10⁻³ | **9.9·10⁻¹⁰** | 19.8 → 31.5 s |
| M-3 | 7.3·10⁻⁵ | 7.2·10⁻⁵ | 25.0 → 21.3 s |
| M-4 / M-5 | 2.7·10⁻¹³ | 9.4·10⁻¹¹ | 10.0 → 51.9 s |

**M-2 pasa de no alcanzar la tolerancia a superarla por tres órdenes.** Sobre el
componente aislado el recorte cuesta un **3–5 %** por marcha y da el mismo
resultado cuando no hay frontera que cruzar —6553.7 W en los dos casos, cifra a
cifra—. El encarecimiento de M-4 y M-5 no es del componente sino del lazo: con
el residuo ya liso, el método deja de detenerse pronto y sigue descendiendo.

Y la continuidad, que es lo que el lazo necesita, medida directamente: barriendo
el caudal en un intervalo donde la frontera recorre varios segmentos, la serie
del recalentamiento de salida era un **diente de sierra con saltos de hasta
0.148 K** sobre incrementos de 0.01 K; ahora es **monótona y el salto máximo es
de 0.003 K**.

**Dependencia de la malla.** M-2 alcanza la tolerancia con 12 volúmenes de
placas y 60 segmentos de serpentín; con 8 y 40 se queda en 9.6·10⁻³. El recorte
elimina el escalón, no el error de discretización.

### 18.4. M-3 sigue sin cerrar, y es otro fenómeno

M-3 no se mueve: 7.2·10⁻⁵. Pero su residuo ya **no es un escalón**. Cortado
alrededor de la solución, R₄ y R₅ responden con normalidad a las tres incógnitas
y **R₂ es insensible a todas ellas**: se mueve del orden de 10⁻⁶ mientras R₄
recorre 2·10⁻⁵ en el mismo intervalo. El recalentamiento se queda 0.02 K por
debajo de la consigna y ninguna combinación de P₀, P_k y ṁ_ACS lo corrige.

Se probó también apretar el disparo del secundario de cada intercambiador, que
`PlateHeatExchanger.solve` tiene en 10⁻³ K por defecto: de 10⁻³ a 10⁻⁹ K el
residuo de M-3 pasa de 7.16·10⁻⁵ a 7.29·10⁻⁵, esto es, **no cambia**. La
hipótesis de la tolerancia del disparo queda descartada igual que la del tren, y
el cambio se revirtió por no tener efecto medible.

Queda por tanto una tarea acotada y distinta de la que se creía: **averiguar por
qué el recalentamiento de M-3 es insensible al vector de incógnitas**. La
sospecha razonable es que el evaporador de placas de M-3 esté pinzado contra el
agua de climatización, de modo que su salida la fije el secundario y no la
presión; si es así, la consigna de recalentamiento no es alcanzable en ese punto
y lo que procede no es apretar el método sino declararlo.

### 18.5. Un contraste que hubo que remedir: el suelo del backend tabular

La fase H (apartado 16.2) estableció que el ruido del backend tabular pone un
suelo al residuo, «en el entorno de 10⁻⁶, mientras que en HEOS el mismo punto
baja a 10⁻¹⁰». Con el escalón del serpentín corregido, ese contraste **deja de
verse a la discretización de trabajo**:

| Segmentos del serpentín | HEOS | Tabular | Razón |
|---|---|---|---|
| 60 | 7.3·10⁻⁷ | 5.3·10⁻⁸ | **0.1** |
| 120 | 2.4·10⁻⁸ | 2.0·10⁻⁶ | 86 |

A 60 segmentos el suelo lo pone la marcha, no la biblioteca, y cuál de los dos
backends acaba más bajo es cuestión de suerte. A 120 el efecto vuelve a verse
limpio y la conclusión de la fase H se sostiene.

**La lección va al capítulo 11**: un suelo de residuo solo puede atribuirse a la
biblioteca de propiedades después de haber descartado la discretización. El
contraste automatizado se ha remedido y ahora se ejecuta con 120 segmentos, con
la condición declarada en su propio enunciado.

---

## 19. M-5 vuelve a la tabla 10.3, y la consigna de ACS deja de ser única

Decisiones del autor del 22/09/2026. `circuit.MODES["M-5"]` y
`circuit.CONSIGNA_ACS_K`; contrastes en `tests/test_circuit.py`.

### 19.1. El calor residual no puede disiparse donde D-1 suponía

La decisión D-1, de 3/09/2026, apartó a M-5 de la tabla 10.3 y adoptó **disipar
el calor residual en el intercambiador de climatización**. El modelo implementaba
esa topología y dejaba abierta, además, la forma de especificar su control.

**Revertida, y por una razón física que no admite réplica**: el circuito de
climatización solo tiene **fan-coils**. Disipar en él significa activarlos, y
activarlos significa **calefactar la vivienda**. Basta imaginar una demanda de
ACS en verano, sin demanda de frío ni de calor, para ver que esa vía no existe.

De modo que **el capítulo tenía razón desde el principio**: en M-5 los dos
intercambiadores de placas trabajan en serie para el ACS, con el agua a
contracorriente por ambos, que es lo que la tabla 10.3 describe. El refrigerante
se desrecalienta en el pequeño y termina de condensar y subenfriarse en el
grande; el agua recorre el camino inverso.

**Y con la disipación cae el punto de control que quedaba abierto.** Sin reparto
no hay nada que repartir: queda la consigna de ACS con el caudal como incógnita.
El modo `M-5-reparto`, el residuo R6 y la consigna `Q_dissipated` **se retiran
del modelo**. Mantener implementada una topología físicamente imposible es peor
que no tenerla: alguien la habría usado.

### 19.2. La consigna de ACS depende del modo

Sin servicio simultáneo de climatización, la condensación tiene que situarse por
encima de la temperatura de salida del ACS, y eso se paga entero. Medido en
verano, con aire a 32 °C y 45 % de humedad relativa y ACS desde 15 °C:

| Consigna | T_cond | Q al ACS | W_el | COP global |
|---|---|---|---|---|
| 60 °C | 57.7 °C | 19.32 kW | 4376 W | 4.41 |
| 50 °C | 50.6 °C | 19.59 kW | 3898 W | 5.03 |
| **45 °C** | 47.4 °C | 19.72 kW | **3700 W** | **5.33** |

**Decisión del autor: 60 °C de DEPÓSITO en los modos con recuperación y 45 °C en
M-5**, con la impulsión 7 K por encima —67 y 52 °C— porque el interacumulador se
carga por serpentín y el capítulo confundía las dos (apartado 19.5). El
dimensionado se hace para 60 °C, como exige la prevención de legionelosis, y esa
exigencia se cubre donde sale barata: en M-3 y M-4 el ACS se produce **mientras
la máquina climatiza**, con el desrecalentador recibiendo gas de descarga por
encima de 120 °C, de modo que el calor de alta temperatura es un subproducto.
M-5 solo entra cuando no hay demanda de climatización, y ahí esa temperatura se
paga entera: bajar a 45 °C sube el COP global un **21 %**.

Es un argumento de arquitectura y no un apaño: **la máquina produce ACS de grado
sanitario precisamente cuando está haciendo climatización**. Refuerza H3.

### 19.3. El punto de referencia de M-5

Con la topología y la consigna adoptadas:

| | |
|---|---|
| Residuo | 6.8·10⁻¹¹ |
| Evaporación / condensación | 17.6 / 52.0 °C |
| Temperatura de descarga | 109.1 °C |
| Calor al ACS | 19.54 kW |
| Calor al circuito de climatización | **0 W** |
| Potencia eléctrica | 3993 W |
| COP global | 4.89 |
| Agua de ACS | 455 kg/h; 15 → 46.8 °C en el de climatización y 46.8 → 52 °C en el desrecalentador |

*Depósito a 45 °C, impulsión a 52 °C.*

**No es válido todavía**: converge, pero el balance interno del intercambiador de
climatización queda en 2.1·10⁻³, por encima del criterio de 10⁻³. Es el mismo
patrón que M-4 (apartado 18.3).

**Y hay una observación que conviene no perder**, porque condiciona al capítulo
13: con 19.7 kW al ACS la máquina está **muy sobredimensionada** para producir
solo ACS. El punto de M-5 es una capacidad más que un régimen, y la agregación
estacional tendrá que tratarlo con carga parcial o con ciclado, no como un punto
estacionario más.

### 19.4. Lo que el capítulo 8 tiene que declarar

Dos cosas, porque la decisión de la consigna descansa en ellas: que la
acumulación a temperatura sanitaria **queda cubierta por los modos con
recuperación**, y **con qué medio se cubre el choque térmico periódico**.

### 19.5. Depósito no es impulsión, y el capítulo los confunde

Decisión del autor del 22/09/2026, y corrige una confusión de fondo.

El §10.5.3 ajusta «el caudal del bucle cerrado de ACS hacia el
**interacumulador**». Un interacumulador es por definición un depósito con
intercambiador interior, de modo que entre la temperatura del depósito y la del
agua que sale del desrecalentador está la **aproximación de ese serpentín**. El
capítulo escribe 60 °C en los dos sitios —consigna de ACS y salida del agua del
desrecalentador— y son dos cosas distintas: con carga por serpentín, aquella
impulsión de 60 dejaba el depósito en unos 53.

**Adoptada una aproximación de 7 K**, la impulsión pasa a ser 67 °C en los modos
con recuperación y 52 °C en M-5. Se expresa así en el código: el depósito y la
aproximación son las decisiones, y la impulsión se **deriva** de ellas, para que
no puedan volver a separarse por descuido.

Lo que cuesta, medido sobre el desrecalentador con la descarga corregida:

| Primario | Salto | ṁ_ACS | Q recuperado | Margen sobre T_sat | Pared húmeda |
|---|---|---|---|---|---|
| 35 → 60 °C (capítulo) | 25 K | 84.8 kg/h | 2463 W | 4.0 K | 30 % |
| **35 → 67 °C** (adoptada) | 32 K | 63.7 kg/h | **2370 W** (−3.8 %) | **6.4 K** | 18 % |
| 45 → 67 °C (si el retorno fuese 45) | 22 K | 85.7 kg/h | 2193 W (−11 %) | 11.1 K | 0 % |

Tres lecturas que conviene no confundir entre sí:

1. **La corrección cuesta poco**: un 3.8 % de potencia recuperada, no el vuelco
   que cabía temer. H3 apenas se mueve por esta vía.
2. **Y alivia lo que estaba apretado**: el margen de no condensación se ensancha
   un 60 %, de 4.0 a 6.4 K. Era la variable que cuatro correcciones sucesivas
   habían ido estrechando.
3. **La temperatura de RETORNO pesa el triple que la de impulsión** (−11 %
   frente a −3.8 %). Sigue sin fijarse: el capítulo 10 usa 35 °C y la tabla 8.1
   declaraba 45. **Es lo siguiente que hay que cerrar**, y es del capítulo 8.
