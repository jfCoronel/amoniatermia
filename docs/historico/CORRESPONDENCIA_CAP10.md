# Correspondencia de numeración del capítulo 10

El capítulo 10 se reorganizó en la v30 (`docs/Capitulos_pdf/Cap_10_Modelo_simulacion_AMONIATERMIA_v30.pdf`).
El código, los tests y los ficheros de datos se escribieron citando la versión anterior
(`docs/cap10_modelo.md`, retirado del árbol el 24/09/2026 y recuperable con
`git show 03cc972:docs/cap10_modelo.md`). El 24/09/2026 se renumeraron sus citas con esta
tabla.

**Los documentos de trabajo NO se renumeran**: `INFORME_REESCRITURA_CAP10.md` (retirado
el 24/09/2026 y sustituido por `INFORME_REESCRITURA.md`; sigue en el historial de git),
`PLAN_PUESTA_EN_MARCHA.md`, `guia_implementacion.md` y las entradas fechadas de
`PENDIENTES.md` y del README citan la versión que auditaban, y renumerarlos
falsearía lo que dicen. Para leerlos, esta tabla.

**Los identificadores conservan su nombre histórico**: la variante de parámetros
`tabla_10_4` (el juego anterior del compresor, que la v30 ya no publica como tabla) y la
constante `TABLA_10_13` de `correlations.voidfraction` (hoy tabla 10.21).

## Apartados

| Anterior | v30 | Contenido |
|---|---|---|
| 10.1.1 | 10.1.2 | Arquitectura en tres niveles |
| 10.1.2 | 10.1.2 | Convenios y nomenclatura |
| 10.2, 10.3, 10.3.1 | igual | Hipótesis, modos, trenes extendidos |
| 10.4 | 10.5 | Compresor |
| 10.4.1, 10.4.2 | 10.5.1 | Subprocesos y formulación |
| 10.4.3 | 10.5.2 | Compresor abierto |
| 10.4.4, 10.4.5 | 10.5.3 | Identificación sobre el Bock F2 |
| 10.4.6 | 10.5.4 | Transferibilidad a otros refrigerantes |
| 10.5 | 10.6 | Intercambiadores de placas |
| 10.5.1, 10.5.10 | 10.6.1 | Discretización, frontera de fase, algoritmo |
| 10.5.2 | 10.6.2 | Geometría y convenio de área |
| 10.5.3 | **10.6.7** (desrecalentador, punto de diseño, descarte del 27-30H) o **10.6.2** (geometría de las placas, Φ) | Se decide por contexto |
| 10.5.4, 10.5.5, 10.5.6 | 10.6.3 | Correlaciones constitutivas |
| 10.5.7 | 10.6.5 | Desrecalentamiento con pared húmeda |
| 10.5.8 | 10.6.6 | Pérdida de carga |
| 10.5.9 | 10.6.4 | Coeficientes: anclaje sobre la ficha |
| — | 10.6.8 | Retorno del primario de ACS (nuevo) |
| 10.6 | 10.7 | Batería de aire |
| 10.6.1, 10.6.2 | 10.7.1 | Geometría reconstruida, circuitería, maldistribución |
| 10.6.12 | 10.7.2 | Algoritmo del serpentín y frontera de fase |
| 10.6.3 | 10.7.3 | Lado de aire |
| 10.6.4 | 10.7.4 | Aleta, pared y reparto de resistencias |
| 10.6.5 | 10.7.5 | Lado de refrigerante |
| 10.6.6, 10.6.7 | 10.7.6 | Superficie húmeda y escarcha |
| 10.6.8 | 10.7.7 | Ventilador |
| 10.6.9 | 10.7.8 | Equilibrio de M-1 y operación como evaporador |
| 10.6.10 | 10.9 | Inventario de carga de la batería |
| 10.6.11 | 10.13 | Datos pendientes |
| 10.7, 10.8 | 10.8 | Válvula, valvulería y líneas |
| 10.9, 10.9.1–10.9.3 | 10.9 | Inventario de carga |
| 10.10 | 10.10 | Propiedades |
| 10.11 | 10.4 | Resolución de un punto |
| 10.11.1, 10.11.2 | 10.4.2 | Sistema de residuos |
| 10.11.3 | 10.4.3 | Estructura de lazos |
| 10.11.4, 10.11.5 | 10.4.4 | Convergencia y no convergencia (la inicialización está en 10.4.1) |
| 10.12, 10.12.1, 10.12.2 | 10.11, 10.11.1, 10.11.2 | Indicadores |
| 10.13 | 10.12 | Implementación |
| 10.13.1, 10.13.2 | 10.12.1 | Entorno y separación modelo/experimentación |
| 10.13.3 | 10.12.2 | Arquitectura del paquete |
| 10.13.4 | **10.12.4** (estado reutilizado, backend, unidades, resolución) o **10.12.3** (correlaciones por nombre) | Se decide por contexto |
| 10.13.5, 10.13.6 | 10.12.5 | Verificación automatizada y reproducibilidad |
| — | 10.13 | Alcance y limitaciones (nuevo) |
| 10.14 | 10.14 | Síntesis |

## Tablas

| Anterior | v30 |
|---|---|
| 10.1 (jerarquía del modelo) | sin tabla; §10.1.2 |
| 10.2, 10.3 | 10.2, 10.3 |
| 10.4 (parámetros del compresor, juego anterior) | 10.8 publica el juego adoptado |
| 10.5 (transferibilidad) | sin tabla; §10.5.4 |
| 10.6 (geometría de placas) | 10.12 |
| 10.7 (coeficientes conocidos y pendientes) | sin tabla; §10.6.4 y §10.13 |
| 10.8 (geometría de la batería) | 10.17 |
| 10.9 (verificación de la reconstrucción) | sin tabla; §10.7.1 |
| 10.10 (coeficiente de aire predicho) | sin tabla; §10.7.3 |
| 10.11 (reparto de resistencias) | 10.18 |
| 10.12 (operación como evaporador) | 10.20 |
| 10.13 (carga de la batería) | 10.21 |
| 10.14 (sistema de residuos) | 10.4 |
| 10.15 (módulos del paquete) | 10.23 |
| 10.16 (coste de las propiedades) | sin tabla; §10.12.4 |
| 10.17 (entradas y salidas) | 10.26 |

Tablas nuevas de la v30: 10.1 (dato, incógnita, salida), 10.5 (lazos), 10.6 (residuo por
modo), 10.7 (salidas por punto), 10.9 (calidad del ajuste), 10.10 (identificabilidad),
10.11 (malla), 10.13 a 10.16 (desrecalentador y retorno), 10.19 (equilibrio de M-1),
10.22 (carga frente a subenfriamiento), 10.24 (familias de correlaciones), 10.25 (backend
tabular).

## Ecuaciones

El código no citaba con una única numeración: las ecuaciones del compresor 10-1
(aspiración) y 10-8 (pared ficticia) ya seguían la de la v30, y el resto la del
Markdown anterior. Esas citas del compresor se revisaron una a una.

| Anterior | v30 | Contenido |
|---|---|---|
| 10-2 (Markdown) / 10-1 (código) | 10-1 | Calentamiento en la aspiración |
| 10-3 | 10-2 | Escalado de AU_su |
| 10-4 | 10-3 | Caudal másico (incluye η_v) |
| 10-5 | 10-3 (η_v) o 10-4 (etapa isócora) | Por contexto |
| 10-6 | 10-5 | Trabajo interno |
| 10-7 | 10-6 | Pérdidas mecánicas |
| 10-9 (Markdown) / 10-8 (código) | 10-8 | Balance de la pared ficticia |
| 10-10 | 10-9 | Potencia eléctrica |
| 10-11 | 10-10 | Función objetivo de la identificación |
| 10-12 | sin ecuación; §10.5.4 | Corrección de AU por Prandtl |
| 10-13, 10-14, 10-15 | 10-11 | Balance del volumen de placa y ΔT_lm |
| 10-16 | 10-12 | Conductancia del volumen |
| 10-17 | 10-13 | D_h y G |
| 10-18 | 10-14 | Monofásico |
| 10-19, 10-20 | 10-15, 10-16 | Ebullición en placa (Chen + Cooper) |
| 10-21, 10-22 | 10-17 | Película de Nusselt y φ_c·φ_v |
| 10-23, 10-24 | 10-18, 10-19 | Pared húmeda y factor Z |
| 10-25 | 10-20 | Pérdida de carga |
| 10-26, 10-27 | 10-21 | Colburn y h_a |
| 10-28, 10-29 | 10-22 | Efectividad superficial |
| 10-30 | 10-23 | Resistencias de la batería |
| 10-31, 10-32 | 10-24, 10-25 | Dobson-Chato con Soliman |
| 10-33, 10-34 | 10-26, 10-27 | Gungor-Winterton |
| 10-35, 10-36 | 10-28, 10-29 | Potencial entálpico y aleta húmeda |
| 10-37 | 10-30 | Penalización de desescarche |
| 10-38, 10-39 | sin ecuación; §10.7.7 | Pérdida de carga del aire, potencia del ventilador |
| 10-40 | 10-31 | Ecuación de orificio |
| 10-41 | sin ecuación; R₂ de la tabla 10.4 | Lazo de recalentamiento |
| 10-42, 10-43 | 10-32 | Inventario |
| 10-44, 10-45 | 10-33 | Fracción de huecos homogénea y de deslizamiento |
| 10-46, 10-47 | 10-34 | COP, EER, COP global |
| 10-48, 10-49 | 10-35 | Exergía de flujo y destruida |
| 10-50 | 10-36 | y_D y η_II |

## Capítulo 7 (v1 → v3)

| Anterior | v3 |
|---|---|
| 7.7.1 | 7.7.1 |
| — | 7.7.2 Convergencia y validez como comprobaciones separadas (nuevo) |
| 7.7.2 Validación multinivel, tabla 7.5 | 7.7.3 |
| 7.7.3 Métricas y dominio de validez | 7.7.4 |
