# Correspondencia de numeración

Vigente desde el 28/09/2026. El código, las pruebas, los datos y los documentos vivos de
`docs/` usan la numeración nueva. Los documentos de `docs/historico/` conservan la que
tenían cuando se escribieron.

## Capítulos

Los capítulos 3 y 4 se han unido en el 3 (estado del arte). Los posteriores bajan un número.

| Antes | Ahora | Contenido |
|---|---|---|
| 1, 2 | 1, 2 | sin cambio |
| 3 + 4 | 3 | Estado del arte |
| 5 | 4 | Estado del arte del modelado |
| 6 | 5 | — |
| 7 | 6 | Metodología (V&V, campañas, incertidumbre) |
| 8 | 7 | Diseño del sistema |
| 9 | 8 | Seguridad y normativa (RS-1 en la tabla 8.7) |
| 10 | **9** | Modelo de simulación |
| 11 | 10 | Verificación y validación |
| 12 | 11 | Resultados: campaña paramétrica |
| 13 | 12 | Resultados: evaluación estacional |
| 14 | 13 | — |

**Apartados, tablas y ecuaciones del capítulo 9.** Las citas del código son las de la
**v31 del antiguo capítulo 10** con el número de capítulo bajado (§10.7.3 → §9.7.3,
tabla 10.19 → tabla 9.19, ec. 10-8 → ec. 9-8). Cuando se redacte el capítulo 9 nuevo con la
estructura de `docs/INFORME_CAPITULO_9.md`, los apartados cambiarán y habrá que añadir aquí
la correspondencia entre la v31 y la versión nueva.

**Citas históricas.** «La antigua tabla 10.4», «la tabla 10.8 de la v30» y similares se
refieren a un documento concreto y **no se han renumerado**.

La correspondencia anterior, de la numeración primitiva del capítulo 10 con la v30, está en
`historico/CORRESPONDENCIA_CAP10.md`.

## Modos de operación

Se adopta la numeración del capítulo 6 (antes 7): primero los dos modos de frío, con y sin
ACS; después los de calor; M-5 aparte.

| Antes | Ahora | Servicio | Batería | Incógnitas |
|---|---|---|---|---|
| M-3 | **M-1** | Climatización (frío) + ACS | Condensador | P0, Pk, ṁ_ACS |
| M-1 | **M-2** | Climatización (frío) | Condensador | P0, Pk |
| M-4 | **M-3** | Calefacción + ACS | Evaporador | P0, Pk, ṁ_ACS |
| M-2 | **M-4** | Calefacción | Evaporador | P0, Pk |
| M-5 | **M-5** | Solo ACS | Evaporador | P0, Pk, ṁ_ACS |

Ojo al cruce: **el M-2 de antes es el M-4 de ahora, y el M-2 de ahora es el M-1 de antes.**
Una cita antigua no puede sustituirse sin esta tabla. En particular:

- el equilibrio de referencia del §9.7.8 (9.52 kW, 44.9 °C, 120.0 °C) es de **M-2**;
- el punto de diseño del desrecalentador (1 851 W, 5.5 K) es de **M-1**;
- el barrido de invierno del retorno de ACS y la condensación parcial aceptada son de **M-3**;
- la tabla 9.20 (batería como evaporador) es de **M-4**.

## Ficheros renombrados

| Antes | Ahora |
|---|---|
| `data/validacion_tabla_7_5.yaml` | `data/validacion_tabla_6_5.yaml` |
| `notebooks/02_figura_10_3_ajuste_compresor.py` | `notebooks/02_figura_9_3_ajuste_compresor.py` |
| `notebooks/03_cifras_capitulo_10.py` | `notebooks/03_cifras_capitulo_9.py` |
| `docs/cifras_capitulo_10.md` | `docs/cifras_capitulo_9.md` |
| `docs/figuras/fig_10_3_ajuste_compresor.*` | `docs/figuras/fig_9_3_ajuste_compresor.*` |

Identificadores: `TABLA_10_13` → `CORRELACIONES_HUECOS`; la variante del compresor
`"tabla_10_4"` → `"original"` (bloque `contraste_juego_original`); claves
`verificacion_6_7_1` y `sensibilidad_6_11`.
