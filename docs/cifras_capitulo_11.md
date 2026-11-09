# Cifras del capítulo 11

Generado por `notebooks/06_cifras_capitulo_11.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `37340a21b6a8362ab2d979b85ca7c0885825a3ca`
- CoolProp 8.0.0
- Generado: 2026-10-15 12:52
- Secciones: factorial, diseno, h4, recalentamiento, h3, h6, modos, exergia, admisibilidad, figuras

## factorial

Niveles (decisión del autor, 30/09/2026). Caudales de agua y consignas de ACS de los puntos de diseño. Los nudos no convergidos y los no válidos se cuentan, no se descartan.

| Factor | Niveles |
|---|---|
| Aire, frío (M-1, M-2) | 20 / 25 / 30 / 35 / 40 °C |
| Aire, calor (M-3, M-4) | -10 / -7 / 2 / 7 / 12 °C |
| Aire, M-5 | -7 / 2 / 7 / 12 / 20 / 35 °C |
| Agua de climatización, entrada (frío) | 10 / 12 / 15 °C |
| Agua de climatización, entrada (calor) | 30 / 35 / 40 °C |
| Recalentamiento | 3 / 5 / 8 K |
| Subenfriamiento | 0 / 2 / 5 K |

| Modo | Nudos | Convergidos | Válidos | Admisibles | Indicador (válidos) |
|---|---|---|---|---|---|
| M-1 | 135 | 134 | 134 | 125 | 2.29 – 4.06 |
| M-2 | 135 | 135 | 135 | 125 | 2.32 – 4.28 |
| M-3 | 135 | 135 | 135 | 52 | 1.14 – 3.35 |
| M-4 | 135 | 134 | 134 | 58 | 1.78 – 3.95 |
| M-5 | 54 | 54 | 54 | 22 | 1.97 – 4.82 |


## diseno

### H4: presupuesto único de RS-5

Equilibrio de refrigeración del §9.7.8 (M-2, evaporación impuesta a 2 °C, aire a 35 °C, recalentamiento 1 K, subenfriamiento 0): 9.49 kW, presupuesto de **474 g** (decisión 1 del 01/10/2026). DISCREPANCIA declarada: el sistema completo en el punto de diseño de M-2 entrega 10.20 kW, que daría 510 g; el capítulo debe decir de cuál de los dos equilibrios se trata.

| Modo | Válido | Componentes | Líneas | Sistema | Fracción del presupuesto único | Fracción con la capacidad del modo (informativa) |
|---|---|---|---|---|---|---|
| M-1 | True | 453 g | 37 g | 490 g | 1.032 | 1.033 |
| M-2 | True | 365 g | 48 g | 413 g | 0.870 | 0.810 |
| M-3 | True | 306 g | 24 g | 329 g | 0.694 | 0.778 |
| M-4 | True | 309 g | 24 g | 333 g | 0.702 | 0.786 |
| M-5 | True | 272 g | 28 g | 298 g | 0.628 | 0.347 |

**Modo más desfavorable: M-1, 1.032 del presupuesto** (H4 NO se cumple en el peor caso de la banda; en M-1 el resultado se publica en el límite, decisión 1 del 30/09/2026: depende de la geometría de líneas, de 0.99 a 1.07).

### H6: destrucción de exergía y margen recuperable en el compresor

Cota técnica: el mismo compresor con el mejor rendimiento isoentrópico de su catálogo, η_is = 0.732 (T₀ = 5 °C, T_k = 40 °C; mediana 0.710). Cota termodinámica: la exergía destruida en el compresor con su motor. Las dos son de primer orden (misma capacidad y mismo ciclo). Un η_is del punto por encima del del catálogo es extrapolación (M-5 está fuera del dominio del compresor) y da margen técnico nulo.

| Modo | y_D del compresor con motor | Mayor del ciclo | Indicador | η_is del punto | Cota termodinámica | Cota técnica |
|---|---|---|---|---|---|---|
| M-1 | 0.530 | compresor_con_motor | 2.720 | 0.719 | 898 W (34.7 %) | 51 W (1.5 %) |
| M-2 | 0.510 | compresor_con_motor | 2.783 | 0.726 | 944 W (34.7 %) | 25 W (0.7 %) |
| M-3 | 0.576 | compresor_con_motor | 2.351 | 0.709 | 916 W (33.3 %) | 93 W (2.6 %) |
| M-4 | 0.566 | compresor_con_motor | 2.953 | 0.709 | 915 W (33.3 %) | 93 W (2.6 %) |
| M-5 | 0.334 | placas_clima | 4.558 | 0.762 | 1110 W (34.0 %) | 0 W (0.0 %) |


## h4

Presupuesto único de RS-5: 474 g (50 g/kW sobre los 9.49 kW del equilibrio de refrigeración del §9.7.8). Peor caso de la banda de fracción de huecos; sistema = componentes + líneas adoptadas (decisión 3b). Es SENSIBILIDAD: el veredicto de H4 se toma en los puntos de diseño (decisión 2 del 01/10/2026, sección `diseno`).

| Modo | Nudos válidos | Carga peor | Fracción del presupuesto | Nudos por encima | Condición del peor |
|---|---|---|---|---|---|
| M-1 | 134 | 633 g | 1.33 | 65 | T_aire_C = 40, T_agua_C = 10, recalentamiento_K = 3, subenfriamiento_K = 5 |
| M-2 | 135 | 504 g | 1.06 | 24 | T_aire_C = 40, T_agua_C = 10, recalentamiento_K = 3, subenfriamiento_K = 5 |
| M-3 | 135 | 462 g | 0.97 | 0 | T_aire_C = -10, T_agua_C = 40, recalentamiento_K = 3, subenfriamiento_K = 5 |
| M-4 | 134 | 466 g | 0.98 | 0 | T_aire_C = -10, T_agua_C = 40, recalentamiento_K = 3, subenfriamiento_K = 5 |
| M-5 | 54 | 316 g | 0.67 | 0 | T_aire_C = 35, recalentamiento_K = 3, subenfriamiento_K = 5 |

### Fracción del presupuesto frente al subenfriamiento

| Modo | Subenfriamiento | Mínima | Máxima |
|---|---|---|---|
| M-1 | 0 K | 0.81 | 1.00 |
| M-1 | 2 K | 0.90 | 1.09 |
| M-1 | 5 K | 1.09 | 1.33 |
| M-2 | 0 K | 0.68 | 0.85 |
| M-2 | 2 K | 0.76 | 0.92 |
| M-2 | 5 K | 0.92 | 1.06 |
| M-3 | 0 K | 0.54 | 0.77 |
| M-3 | 2 K | 0.56 | 0.80 |
| M-3 | 5 K | 0.61 | 0.97 |
| M-4 | 0 K | 0.61 | 0.75 |
| M-4 | 2 K | 0.63 | 0.77 |
| M-4 | 5 K | 0.68 | 0.98 |
| M-5 | 0 K | 0.38 | 0.63 |
| M-5 | 2 K | 0.39 | 0.65 |
| M-5 | 5 K | 0.40 | 0.67 |


## recalentamiento

Cambio frente a 5 K en los mismos nudos (resto de factores igual).

| Modo | Recalentamiento | Pares | Indicador | Carga (peor) | Descarga |
|---|---|---|---|---|---|
| M-1 | 3 K | 45 | 0.9 % … 1.1 % | 0.6 % … 1.7 % | -3.6 … -2.7 K |
| M-1 | 8 K | 44 | -2.5 % … -1.7 % | -3.7 % … -1.2 % | +4.3 … +6.2 K |
| M-2 | 3 K | 45 | 0.6 % … 0.8 % | 1.8 % … 3.3 % | -3.3 … -2.6 K |
| M-2 | 8 K | 45 | -2.8 % … -1.4 % | -8.5 % … -2.2 % | +4.1 … +6.4 K |
| M-3 | 3 K | 45 | 1.4 % … 6.1 % | 1.4 % … 8.1 % | -11.7 … -3.0 K |
| M-3 | 8 K | 45 | -14.4 % … -3.7 % | -14.2 % … 2.3 % | +5.5 … +29.6 K |
| M-4 | 3 K | 45 | 0.9 % … 3.6 % | 1.0 % … 8.9 % | -11.7 … -3.0 K |
| M-4 | 8 K | 44 | -10.6 % … -2.8 % | -12.6 % … 2.7 % | +5.6 … +29.6 K |
| M-5 | 3 K | 18 | 0.3 % … 2.3 % | 1.2 % … 8.7 % | -6.6 … -2.4 K |
| M-5 | 8 K | 18 | -7.9 % … -0.7 % | -21.8 % … -1.9 % | +3.7 … +19.7 K |


## h3

Mismo aire, misma entrada de agua y mismas consignas (recalentamiento 5 K, subenfriamiento 2 K); el ACS sale siempre a la consigna de 67 °C, que impone R3. Los cuatro modos comparten el caudal de climatización (0.45 kg/s, 01/10/2026), de modo que la diferencia es solo la recuperación. ΔCOP global: el del modo con recuperación frente al indicador del modo sin ella.

| Modos | Aire | Agua | ACS recuperado | Margen de no condensación | Δp_k | ΔCOP global |
|---|---|---|---|---|---|---|
| M-1 / M-2 | 20 °C | 10 °C | 944 W / 25.4 kg/h | +19.47 K | -528 mbar | 4.1 % |
| M-1 / M-2 | 20 °C | 12 °C | 929 W / 25.0 kg/h | +19.59 K | -557 mbar | 3.3 % |
| M-1 / M-2 | 20 °C | 15 °C | 903 W / 24.3 kg/h | +19.74 K | -601 mbar | 2.2 % |
| M-1 / M-2 | 25 °C | 15 °C | 1232 W / 33.2 kg/h | +14.52 K | -782 mbar | 6.5 % |
| M-1 / M-2 | 25 °C | 12 °C | 1231 W / 33.1 kg/h | +14.48 K | -713 mbar | 7.5 % |
| M-1 / M-2 | 25 °C | 10 °C | 1230 W / 33.1 kg/h | +14.41 K | -671 mbar | 8.3 % |
| M-1 / M-2 | 30 °C | 10 °C | 1529 W / 41.1 kg/h | +9.79 K | -842 mbar | 12.9 % |
| M-1 / M-2 | 30 °C | 12 °C | 1547 W / 41.6 kg/h | +9.85 K | -901 mbar | 12.1 % |
| M-1 / M-2 | 30 °C | 15 °C | 1573 W / 42.3 kg/h | +9.89 K | -992 mbar | 11.1 % |
| M-1 / M-2 | 35 °C | 15 °C | 1919 W / 51.7 kg/h | +5.75 K | -1243 mbar | 15.9 % |
| M-1 / M-2 | 35 °C | 12 °C | 1869 W / 50.3 kg/h | +5.62 K | -1127 mbar | 17.0 % |
| M-1 / M-2 | 35 °C | 10 °C | 1835 W / 49.4 kg/h | +5.54 K | -1054 mbar | 17.8 % |
| M-1 / M-2 | 40 °C | 10 °C | 2143 W / 57.7 kg/h | +1.70 K | -1320 mbar | 23.0 % |
| M-1 / M-2 | 40 °C | 12 °C | 2191 W / 59.0 kg/h | +1.87 K | -1410 mbar | 22.0 % |
| M-1 / M-2 | 40 °C | 15 °C | 2266 W / 61.0 kg/h | +2.02 K | -1555 mbar | 20.9 % |
| M-3 / M-4 | -10 °C | 30 °C | 1317 W / 35.4 kg/h | +7.33 K | +208 mbar | -0.9 % |
| M-3 / M-4 | -10 °C | 35 °C | 1465 W / 39.4 kg/h | +2.98 K | +111 mbar | -0.4 % |
| M-3 / M-4 | -10 °C | 40 °C | 1635 W / 44.0 kg/h | -2.56 K | -62 mbar | 0.1 % |
| M-3 / M-4 | -7 °C | 40 °C | 1737 W / 46.7 kg/h | -1.33 K | -60 mbar | 0.1 % |
| M-3 / M-4 | -7 °C | 35 °C | 1552 W / 41.8 kg/h | +3.38 K | +140 mbar | -0.5 % |
| M-3 / M-4 | -7 °C | 30 °C | 1380 W / 37.1 kg/h | +7.64 K | +248 mbar | -1.1 % |
| M-3 / M-4 | 2 °C | 30 °C | 1547 W / 41.6 kg/h | +8.23 K | +398 mbar | -1.7 % |
| M-3 / M-4 | 2 °C | 35 °C | 1790 W / 48.2 kg/h | +4.28 K | +251 mbar | -0.9 % |
| M-3 / M-4 | 2 °C | 40 °C | 2028 W / 54.6 kg/h | +0.68 K | +5 mbar | -0.0 % |
| M-3 / M-4 | 7 °C | 40 °C | 2194 W / 59.0 kg/h | +1.06 K | +52 mbar | -0.2 % |
| M-3 / M-4 | 7 °C | 35 °C | 1917 W / 51.6 kg/h | +4.49 K | +328 mbar | -1.2 % |
| M-3 / M-4 | 7 °C | 30 °C | 1635 W / 44.0 kg/h | +8.28 K | +505 mbar | -2.1 % |
| M-3 / M-4 | 12 °C | 30 °C | 1732 W / 46.6 kg/h | +8.11 K | +617 mbar | -2.8 % |
| M-3 / M-4 | 12 °C | 35 °C | 2056 W / 55.3 kg/h | +4.49 K | +409 mbar | -1.6 % |
| M-3 / M-4 | 12 °C | 40 °C | 2372 W / 63.8 kg/h | +1.24 K | +96 mbar | -0.3 % |


## h6

Clasificación de componentes del ciclo con el ventilador como auxiliar (decisión 2 del 29/09/2026). El margen recuperable con velocidad variable queda pendiente del η_is de referencia de esa tecnología.

| Modo | Nudos válidos | y_D del compresor con motor | Nudos en que es el mayor | Mayor en los demás |
|---|---|---|---|---|
| M-1 | 134 | 0.462 – 0.548 | 134 / 134 | — |
| M-2 | 135 | 0.445 – 0.529 | 135 / 135 | — |
| M-3 | 135 | 0.515 – 0.665 | 135 / 135 | — |
| M-4 | 134 | 0.504 – 0.632 | 134 / 134 | — |
| M-5 | 54 | 0.317 – 0.551 | 45 / 54 | placas_clima (9) |


## modos

Criterio (decisión 3 del 30/09/2026): una penalización cuenta si supera la incertidumbre del modelo SOBRE LA DIFERENCIA. Cada alternativa de correlación (C10-7) y cada extremo de parámetro o juego del compresor (C10-8) se aplica a los dos modos a la vez; por grupo, el mayor cambio; los grupos se combinan en raíz de la suma de cuadrados, con la suma lineal como cota conservadora. Puntos de diseño, recalentamiento 5 K y subenfriamiento 2 K.

Dos lecturas, que el capítulo debe distinguir. En frío el ACS es un subproducto y la penalización es la del EER: en M-2 el desrecalentador trabaja como evaporador adicional (tren del §9.3.1) y en M-1 no. En calor el ACS se lleva parte del mismo calor, de modo que el COP de climatización baja por construcción; la penalización de rendimiento es la del COP global.

| Comparación | Magnitud | Diferencia | Banda (RSS) | Banda (lineal) | Significativa | Significativa (conservadora) |
|---|---|---|---|---|---|---|
| Frío, M-1 frente a M-2 | indicador del servicio (EER o COP de climatización) | -2.28 % | ± 1.33 % | ± 2.25 % | sí | sí |
| Frío, M-1 frente a M-2 | COP global con ACS frente al indicador sin ella | 17.00 % | ± 2.24 % | ± 4.12 % | sí | sí |
| Calor, M-3 frente a M-4 | indicador del servicio (EER o COP de climatización) | -20.40 % | ± 1.11 % | ± 2.16 % | sí | sí |
| Calor, M-3 frente a M-4 | COP global con ACS frente al indicador sin ella | -0.16 % | ± 0.18 % | ± 0.24 % | no | no |

#### Frío, M-1 frente a M-2: indicador del servicio

| Fuente | Grupo | Perturbación | Estado | Cambio de la diferencia | Cambio en el primero | Cambio en el segundo |
|---|---|---|---|---|---|---|
| correlacion | bateria/tube_boiling | gungor_winterton_horizontal | evaluada | 0.00 % | 0.00 % | 0.00 % |
| correlacion | bateria/tube_boiling | cooper_solo | evaluada | 0.00 % | 0.00 % | 0.00 % |
| correlacion | bateria/tube_condensation | ficha_cbn21_agregado | evaluada | 0.35 % | -1.67 % | -2.02 % |
| correlacion | placas/plate_boiling | asymptotic_cooper | evaluada | -0.27 % | -1.22 % | -0.94 % |
| correlacion | placas/plate_condensation | nusselt_film | no evaluable: MissingCorrectionFactor | — | — | — |
| correlacion | placas/plate_condensation | equivalent_Re | evaluada | 0.00 % | 0.00 % | 0.00 % |
| correlacion | placas/singlephase | chevron_generic | no evaluable: MissingData | — | — | — |
| parametro | C1_aire | C1_aire = 0.4816 | evaluada | 0.10 % | -0.29 % | -0.38 % |
| parametro | C1_aire | C1_aire = 0.5323 | evaluada | -0.09 % | 0.26 % | 0.35 % |
| parametro | Phi_placas | Phi_placas = 1.1 | evaluada | -0.45 % | -0.98 % | -0.52 % |
| parametro | Phi_placas | Phi_placas = 1.3 | evaluada | 1.23 % | 2.56 % | 1.28 % |
| parametro | phi_md | phi_md = 1.3 | evaluada | 0.18 % | -0.50 % | -0.68 % |
| parametro | eta_electromecanico | eta_electromecanico = 0.82 | evaluada | 0.08 % | -5.54 % | -5.62 % |
| parametro | eta_electromecanico | eta_electromecanico = 0.89 | evaluada | -0.01 % | 0.70 % | 0.71 % |
| parametro | compresor | juego banda_desfavorable | evaluada | 0.04 % | -1.13 % | -1.17 % |
| parametro | compresor | juego banda_favorable | evaluada | -0.04 % | 1.14 % | 1.18 % |


#### Calor, M-3 frente a M-4: indicador del servicio

| Fuente | Grupo | Perturbación | Estado | Cambio de la diferencia | Cambio en el primero | Cambio en el segundo |
|---|---|---|---|---|---|---|
| correlacion | bateria/tube_boiling | gungor_winterton_horizontal | evaluada | -0.25 % | -1.69 % | -1.39 % |
| correlacion | bateria/tube_boiling | cooper_solo | evaluada | -0.40 % | -2.74 % | -2.25 % |
| correlacion | bateria/tube_condensation | ficha_cbn21_agregado | evaluada | -0.00 % | -0.00 % | 0.00 % |
| correlacion | placas/plate_boiling | asymptotic_cooper | evaluada | -0.00 % | -0.00 % | 0.00 % |
| correlacion | placas/plate_condensation | nusselt_film | no evaluable: MissingCorrectionFactor | — | — | — |
| correlacion | placas/plate_condensation | equivalent_Re | evaluada | -0.65 % | -2.14 % | -1.34 % |
| correlacion | placas/singlephase | chevron_generic | no evaluable: MissingData | — | — | — |
| parametro | C1_aire | C1_aire = 0.4816 | evaluada | -0.03 % | -0.18 % | -0.15 % |
| parametro | C1_aire | C1_aire = 0.5323 | evaluada | 0.02 % | 0.17 % | 0.14 % |
| parametro | Phi_placas | Phi_placas = 1.1 | evaluada | -0.00 % | -0.39 % | -0.39 % |
| parametro | Phi_placas | Phi_placas = 1.3 | evaluada | -0.77 % | -0.07 % | 0.91 % |
| parametro | phi_md | phi_md = 1.3 | evaluada | -0.10 % | -0.72 % | -0.59 % |
| parametro | eta_electromecanico | eta_electromecanico = 0.82 | evaluada | -0.00 % | -5.62 % | -5.62 % |
| parametro | eta_electromecanico | eta_electromecanico = 0.89 | evaluada | 0.00 % | 0.71 % | 0.71 % |
| parametro | compresor | juego banda_desfavorable | evaluada | -0.21 % | -1.23 % | -0.97 % |
| parametro | compresor | juego banda_favorable | evaluada | 0.21 % | 1.24 % | 0.98 % |


## exergia

Reparto de la exergía destruida entre los componentes del ciclo (y_D del ciclo, sin el ventilador, decisión 2 del 29/09/2026; el compresor con su motor y su transmisión). Estado muerto: el aire exterior de cada punto.

| Modo | Compresor con motor | Placas de climatización | Batería | Desrecalentador | Válvula | Mayor |
|---|---|---|---|---|---|---|
| M-1 | 53.0 % | 17.4 % | 11.5 % | 9.6 % | 8.5 % | compresor_con_motor |
| M-2 | 51.0 % | 9.9 % | 28.5 % | 2.1 % | 8.5 % | compresor_con_motor |
| M-3 | 57.6 % | 8.7 % | 10.4 % | 13.4 % | 9.8 % | compresor_con_motor |
| M-4 | 56.6 % | 8.4 % | 10.2 % | 15.2 % | 9.6 % | compresor_con_motor |
| M-5 | 33.4 % | 34.7 % | 20.1 % | 6.3 % | 5.6 % | placas_clima |

### Totales

| Modo | Exergía destruida total | Ventilador (fracción del total) | η_II | Cierre exergético |
|---|---|---|---|---|
| M-1 | 2473 W | 31.5 % | 0.246 | -0.01 % |
| M-2 | 2632 W | 29.6 % | 0.253 | -0.01 % |
| M-3 | 2369 W | 32.9 % | 0.263 | +0.49 % |
| M-4 | 2397 W | 32.5 % | 0.335 | +0.49 % |
| M-5 | 4104 W | 19.0 % | — | +0.00 % |

### Compresión frente a conversión electromecánica

Separación del compresor con motor en la irreversibilidad propia de la compresión y la pérdida del motor y la transmisión, en W y en fracción de la exergía destruida en el ciclo (sin ventilador). El cálculo ilustrativo del capítulo 4 (§4.11) no incluye motor.

| Modo | Compresión | Motor y transmisión | Mayor de los demás componentes |
|---|---|---|---|
| M-1 | 579 W (34.2 %) | 319 W (18.8 %) | placas_clima |
| M-2 | 603 W (32.6 %) | 340 W (18.4 %) | bateria |
| M-3 | 575 W (36.2 %) | 341 W (21.5 %) | desrecalentador |
| M-4 | 575 W (35.5 %) | 340 W (21.0 %) | desrecalentador |
| M-5 | 685 W (20.6 %) | 424 W (12.8 %) | placas_clima |


## admisibilidad

Nudos válidos que no son admisibles, por causa (un nudo puede incumplir más de una). Solo la zona sin límites del diagrama del compresor es admisible, y la descarga no puede superar 140 °C (decisiones del 29/09/2026); la presión alta, 25 bar manométricos.

| Modo | Válidos | Admisibles | Fuera de la zona sin límites | Descarga > 140 °C | Presión alta | Descarga máxima | p_k máxima |
|---|---|---|---|---|---|---|---|
| M-1 | 134 | 125 | 1 | 9 | 0 | 148.7 °C | 19.9 bar |
| M-2 | 135 | 125 | 4 | 9 | 0 | 149.1 °C | 21.5 bar |
| M-3 | 135 | 52 | 80 | 80 | 0 | 248.0 °C | 20.5 bar |
| M-4 | 134 | 58 | 74 | 75 | 0 | 248.0 °C | 20.4 bar |
| M-5 | 54 | 22 | 30 | 23 | 0 | 209.8 °C | 22.2 bar |

### Dominio de validez del compresor (capítulo 10): su envolvente

Con los polinomios de UNE-EN 12900 (15/10/2026) el dominio del compresor es la zona del diagrama que cubren los datos del fabricante; un nudo admisible está siempre dentro (la última columna debe ser 0).

| Modo | Dentro del dominio | Fuera del dominio | Admisibles (dentro) | Admisibles fuera del dominio |
|---|---|---|---|---|
| M-1 | 134 | 0 | 125 | 0 |
| M-2 | 135 | 0 | 125 | 0 |
| M-3 | 82 | 53 | 52 | 0 |
| M-4 | 84 | 50 | 58 | 0 |
| M-5 | 33 | 21 | 22 | 0 |

### Recalentamiento 5 K y subenfriamiento 2 K

| Modo | Aire | Agua | Zona del diagrama | Descarga | Indicador | Admisible |
|---|---|---|---|---|---|---|
| M-1 | 20 °C | 10 °C | sin_limites | 89.8 °C | 3.58 | sí |
| M-1 | 20 °C | 12 °C | sin_limites | 87.1 °C | 3.75 | sí |
| M-1 | 20 °C | 15 °C | sin_limites | 83.6 °C | 4.03 | sí |
| M-1 | 25 °C | 10 °C | sin_limites | 101.6 °C | 3.21 | sí |
| M-1 | 25 °C | 12 °C | sin_limites | 98.7 °C | 3.37 | sí |
| M-1 | 25 °C | 15 °C | sin_limites | 94.8 °C | 3.61 | sí |
| M-1 | 30 °C | 10 °C | sin_limites | 114.4 °C | 2.88 | sí |
| M-1 | 30 °C | 12 °C | sin_limites | 111.1 °C | 3.02 | sí |
| M-1 | 30 °C | 15 °C | sin_limites | 106.8 °C | 3.24 | sí |
| M-1 | 35 °C | 10 °C | sin_limites | 127.6 °C | 2.60 | sí |
| M-1 | 35 °C | 12 °C | sin_limites | 124.0 °C | 2.72 | sí |
| M-1 | 35 °C | 15 °C | sin_limites | 119.1 °C | 2.91 | sí |
| M-1 | 40 °C | 10 °C | sin_limites | 140.9 °C | 2.35 | no |
| M-1 | 40 °C | 12 °C | sin_limites | 136.8 °C | 2.46 | sí |
| M-1 | 40 °C | 15 °C | sin_limites | 131.4 °C | 2.63 | sí |
| M-2 | 20 °C | 10 °C | sin_limites | 87.9 °C | 3.76 | sí |
| M-2 | 20 °C | 12 °C | sin_limites | 85.4 °C | 3.95 | sí |
| M-2 | 20 °C | 15 °C | sin_limites | 82.1 °C | 4.25 | sí |
| M-2 | 25 °C | 10 °C | sin_limites | 100.4 °C | 3.35 | sí |
| M-2 | 25 °C | 12 °C | sin_limites | 97.6 °C | 3.51 | sí |
| M-2 | 25 °C | 15 °C | sin_limites | 94.0 °C | 3.77 | sí |
| M-2 | 30 °C | 10 °C | sin_limites | 113.7 °C | 2.98 | sí |
| M-2 | 30 °C | 12 °C | sin_limites | 110.7 °C | 3.12 | sí |
| M-2 | 30 °C | 15 °C | sin_limites | 106.7 °C | 3.34 | sí |
| M-2 | 35 °C | 10 °C | sin_limites | 127.5 °C | 2.66 | sí |
| M-2 | 35 °C | 12 °C | sin_limites | 124.1 °C | 2.78 | sí |
| M-2 | 35 °C | 15 °C | sin_limites | 119.7 °C | 2.97 | sí |
| M-2 | 40 °C | 10 °C | sin_limites | 141.3 °C | 2.39 | no |
| M-2 | 40 °C | 12 °C | sin_limites | 137.5 °C | 2.50 | sí |
| M-2 | 40 °C | 15 °C | sin_limites | 132.6 °C | 2.67 | sí |
| M-3 | -10 °C | 30 °C | fuera | 171.7 °C | 1.70 | no |
| M-3 | -10 °C | 35 °C | fuera | 191.3 °C | 1.52 | no |
| M-3 | -10 °C | 40 °C | fuera | 211.3 °C | 1.37 | no |
| M-3 | -7 °C | 30 °C | refrigeracion_suplementaria | 158.7 °C | 1.90 | no |
| M-3 | -7 °C | 35 °C | fuera | 176.4 °C | 1.70 | no |
| M-3 | -7 °C | 40 °C | fuera | 194.3 °C | 1.54 | no |
| M-3 | 2 °C | 30 °C | sin_limites | 129.6 °C | 2.53 | sí |
| M-3 | 2 °C | 35 °C | refrigeracion_suplementaria | 143.7 °C | 2.27 | no |
| M-3 | 2 °C | 40 °C | refrigeracion_suplementaria | 157.6 °C | 2.05 | no |
| M-3 | 7 °C | 30 °C | sin_limites | 118.6 °C | 2.90 | sí |
| M-3 | 7 °C | 35 °C | sin_limites | 131.2 °C | 2.60 | sí |
| M-3 | 7 °C | 40 °C | refrigeracion_suplementaria | 143.6 °C | 2.35 | no |
| M-3 | 12 °C | 30 °C | sin_limites | 110.0 °C | 3.30 | sí |
| M-3 | 12 °C | 35 °C | sin_limites | 121.5 °C | 2.95 | sí |
| M-3 | 12 °C | 40 °C | sin_limites | 132.6 °C | 2.67 | sí |
| M-4 | -10 °C | 30 °C | fuera | 169.4 °C | 2.23 | no |
| M-4 | -10 °C | 35 °C | fuera | 190.1 °C | 2.07 | no |
| M-4 | -10 °C | 40 °C | fuera | 212.0 °C | 1.96 | no |
| M-4 | -7 °C | 30 °C | refrigeracion_suplementaria | 156.2 °C | 2.43 | no |
| M-4 | -7 °C | 35 °C | fuera | 175.1 °C | 2.26 | no |
| M-4 | -7 °C | 40 °C | fuera | 194.8 °C | 2.13 | no |
| M-4 | 2 °C | 30 °C | sin_limites | 126.5 °C | 3.08 | sí |
| M-4 | 2 °C | 35 °C | sin_limites | 141.8 °C | 2.84 | no |
| M-4 | 2 °C | 40 °C | refrigeracion_suplementaria | 157.6 °C | 2.65 | no |
| M-4 | 7 °C | 30 °C | sin_limites | 115.2 °C | 3.47 | sí |
| M-4 | 7 °C | 35 °C | sin_limites | 129.1 °C | 3.19 | sí |
| M-4 | 7 °C | 40 °C | refrigeracion_suplementaria | 143.3 °C | 2.95 | no |
| M-4 | 12 °C | 30 °C | sin_limites | 106.2 °C | 3.90 | sí |
| M-4 | 12 °C | 35 °C | sin_limites | 119.1 °C | 3.56 | sí |
| M-4 | 12 °C | 40 °C | sin_limites | 132.1 °C | 3.28 | sí |
| M-5 | -7 °C | — | fuera | 189.6 °C | 2.16 | no |
| M-5 | 2 °C | — | refrigeracion_suplementaria | 154.5 °C | 2.68 | no |
| M-5 | 7 °C | — | sin_limites | 140.2 °C | 3.00 | no |
| M-5 | 12 °C | — | sin_limites | 128.4 °C | 3.35 | sí |
| M-5 | 20 °C | — | sin_limites | 119.4 °C | 3.73 | sí |
| M-5 | 35 °C | — | fuera | 103.9 °C | 4.78 | no |


## figuras

Figuras escritas en `docs/figuras` (png y pdf): fig_11_1_indicadores, fig_11_2_margen_H3, fig_11_3_carga_RS5. Recalentamiento 5 K; relleno = admisible, hueco = no admisible.
