# Cifras del capítulo 10

Generado por `notebooks/05_cifras_capitulo_10.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `37340a21b6a8362ab2d979b85ca7c0885825a3ca`
- CoolProp 8.0.0
- Generado: 2026-10-15 12:52
- Secciones: compresor, malla, intercambiadores, bandas, dominio, incertidumbre

## compresor

### Validación del compresor por polinomios (N1)

Criterio de N1: caudal ≤ 5 %, potencia al eje ≤ 8 %, descarga ≤ 5 K, como desviación máxima. Desviación = modelo − fabricante.

#### Ajuste (no es validación: los puntos están consumidos)

| Conjunto | Puntos | Caudal máx. | Caudal medio | Potencia máx. | Potencia media | Descarga máx. | Descarga media | N1 |
|---|---|---|---|---|---|---|---|---|
| 960 rpm | 57 | 0.79 % | 0.00 % | 0.72 % | 0.00 % | 1.61 K | +0.00 K | sí |
| 1100 rpm | 57 | 0.52 % | 0.00 % | 0.56 % | 0.00 % | 1.62 K | +0.00 K | sí |
| 1250 rpm | 57 | 0.58 % | 0.00 % | 0.43 % | 0.00 % | 1.57 K | +0.00 K | sí |
| 1450 rpm | 57 | 0.47 % | 0.00 % | 0.36 % | 0.00 % | 1.62 K | +0.00 K | sí |

#### Velocidad: la omitida y los puntos del 29/09/2026

| Conjunto | Puntos | Caudal máx. | Caudal medio | Potencia máx. | Potencia media | Descarga máx. | Descarga media | N1 |
|---|---|---|---|---|---|---|---|---|
| 1100 rpm con 960, 1250, 1450 | 57 | 0.67 % | -0.07 % | 0.70 % | -0.09 % | 1.55 K | +0.04 K | sí |
| 1250 rpm con 960, 1100, 1450 | 57 | 0.66 % | 0.09 % | 0.83 % | 0.11 % | 1.65 K | -0.04 K | sí |
| 960 rpm, puntos del 29/09/2026 | 4 | 0.18 % | -0.04 % | 0.33 % | -0.09 % | 0.33 K | -0.22 K | sí |
| 1200 rpm, puntos del 29/09/2026 | 4 | 0.56 % | -0.06 % | 0.24 % | 0.04 % | 0.32 K | -0.24 K | sí |

#### Recalentamiento: regla de conservación de los rendimientos de 5 K

| Conjunto | Puntos | Caudal máx. | Caudal medio | Potencia máx. | Potencia media | Descarga máx. | Descarga media | N1 |
|---|---|---|---|---|---|---|---|---|
| catálogo, 1 K | 46 | 0.55 % | -0.03 % | 0.40 % | -0.01 % | 1.37 K | -0.02 K | sí |
| 1 K, puntos del 29/09/2026 | 2 | 0.12 % | 0.12 % | 0.12 % | -0.02 % | 0.38 K | -0.32 K | sí |
| 10 K, puntos del 29/09/2026 | 2 | 0.21 % | 0.17 % | 0.11 % | -0.02 % | 0.29 K | -0.24 K | sí |
| control del 29/09/2026 (2/45 °C, 1 K) | 1 | 0.19 % | 0.19 % | 0.03 % | -0.03 % | 0.39 K | -0.39 K | sí |

**N1 se cumple** en todas las validaciones. Peor caso: caudal 0.67 %, potencia 0.83 %, descarga 1.65 K. Dominio de validez del compresor: su envolvente (zonas sin límites y de refrigeración suplementaria del diagrama), de 960 a 1450 rpm y de 1 a 10 K de recalentamiento.


## malla

### Discretización de trabajo (60 / 12) frente a la más fina (240 / 48)

| Modo | Q útil | W eléctrica | Indicador | Carga (peor) | Series no monótonas |
|---|---|---|---|---|---|
| M-1 | 0.128 % | 0.054 % | 0.075 % | 0.56 % | — |
| M-2 | 0.084 % | 0.020 % | 0.104 % | 3.31 % | W_el, indicador, T_cond, T_dis |
| M-3 | 0.027 % | 0.030 % | 0.002 % | 3.44 % | Q_util, indicador, T_evap |
| M-4 | 0.003 % | 0.042 % | 0.038 % | 3.21 % | Q_util, indicador, T_evap |
| M-5 | 0.032 % | 0.147 % | 0.116 % | 3.75 % | Q_util |

### M-1

| Segmentos / volúmenes | Q útil | W eléctrica | Indicador | T_evap °C | T_cond °C | T_dis °C | Carga (peor) | Válido | Tiempo |
|---|---|---|---|---|---|---|---|---|---|
| 30 / 6 | 9461.5 W | 3480.6 W | 2.7184 | 1.567 | 43.270 | 123.98 | 452.1 g | True | 9 s |
| 60 / 12 | 9474.9 W | 3483.6 W | 2.7198 | 1.605 | 43.310 | 123.97 | 452.8 g | True | 11 s |
| 120 / 24 | 9482.8 W | 3485.0 W | 2.7210 | 1.626 | 43.326 | 123.94 | 454.1 g | True | 16 s |
| 240 / 48 | 9487.1 W | 3485.5 W | 2.7219 | 1.636 | 43.330 | 123.92 | 455.3 g | True | 34 s |


### M-2

| Segmentos / volúmenes | Q útil | W eléctrica | Indicador | T_evap °C | T_cond °C | T_dis °C | Carga (peor) | Válido | Tiempo |
|---|---|---|---|---|---|---|---|---|---|
| 30 / 6 | 10196.0 W | 3661.6 W | 2.7845 | 3.672 | 45.641 | 124.04 | 360.6 g | True | 5 s |
| 60 / 12 | 10200.8 W | 3665.1 W | 2.7833 | 3.693 | 45.693 | 124.13 | 365.0 g | True | 5 s |
| 120 / 24 | 10205.6 W | 3665.2 W | 2.7844 | 3.703 | 45.691 | 124.09 | 371.6 g | True | 7 s |
| 240 / 48 | 10209.4 W | 3664.3 W | 2.7862 | 3.707 | 45.673 | 124.02 | 377.6 g | True | 15 s |


### M-3

| Segmentos / volúmenes | Q útil | W eléctrica | Indicador | T_evap °C | T_cond °C | T_dis °C | Carga (peor) | Válido | Tiempo |
|---|---|---|---|---|---|---|---|---|---|
| 30 / 6 | 8624.0 W | 3667.4 W | 2.3515 | 0.392 | 48.077 | 143.46 | 294.2 g | True | 24 s |
| 60 / 12 | 8625.5 W | 3669.3 W | 2.3507 | 0.390 | 48.122 | 143.61 | 305.8 g | True | 17 s |
| 120 / 24 | 8624.3 W | 3669.5 W | 2.3503 | 0.386 | 48.130 | 143.66 | 312.9 g | True | 38 s |
| 240 / 48 | 8627.9 W | 3670.4 W | 2.3507 | 0.394 | 48.143 | 143.66 | 316.7 g | True | 51 s |


### M-4

| Segmentos / volúmenes | Q útil | W eléctrica | Indicador | T_evap °C | T_cond °C | T_dis °C | Carga (peor) | Válido | Tiempo |
|---|---|---|---|---|---|---|---|---|---|
| 30 / 6 | 10825.0 W | 3663.6 W | 2.9547 | 0.389 | 47.993 | 143.21 | 296.5 g | True | 13 s |
| 60 / 12 | 10822.6 W | 3664.6 W | 2.9533 | 0.386 | 48.018 | 143.30 | 309.3 g | True | 13 s |
| 120 / 24 | 10820.1 W | 3665.2 W | 2.9521 | 0.382 | 48.034 | 143.37 | 315.9 g | True | 20 s |
| 240 / 48 | 10823.0 W | 3666.1 W | 2.9521 | 0.390 | 48.049 | 143.38 | 319.5 g | True | 55 s |


### M-5

| Segmentos / volúmenes | Q útil | W eléctrica | Indicador | T_evap °C | T_cond °C | T_dis °C | Carga (peor) | Válido | Tiempo |
|---|---|---|---|---|---|---|---|---|---|
| 30 / 6 | 19948.0 W | 4368.3 W | 4.5666 | 17.299 | 52.276 | 106.22 | 263.9 g | True | 11 s |
| 60 / 12 | 19946.3 W | 4376.0 W | 4.5581 | 17.305 | 52.364 | 106.43 | 272.1 g | True | 9 s |
| 120 / 24 | 19950.6 W | 4380.1 W | 4.5548 | 17.316 | 52.410 | 106.52 | 279.1 g | True | 16 s |
| 240 / 48 | 19952.7 W | 4382.5 W | 4.5528 | 17.322 | 52.437 | 106.57 | 282.7 g | True | 38 s |


## intercambiadores

### Fichas de fabricante

`validacion`: la magnitud no intervino en ningún anclaje. `coherencia`: ficha consumida por un anclaje (§6.3.1).

| Ficha | Magnitud | Modelo | Ficha | Desviación | Estatuto |
|---|---|---|---|---|---|
| Frimetal CBN-21, evaporador a bomba (26/03/2026) | Potencia | 3124 | 2999 | 4.2 % | validacion |
| Frimetal CBN-21, evaporador a bomba (26/03/2026) | U global | 33.65 | 32 | 5.2 % | validacion |
| Frimetal CBN-21, evaporador a bomba (26/03/2026) | T aire salida [°C] | 5.834 | 5.9 | -0.07 K | validacion |
| Frimetal CBN-21, evaporador a bomba (26/03/2026) | Fraccion humeda | 0 | 0 | — | validacion |
| Frimetal CBN-21, condensador (16/03/2026) | Potencia | 1.23e+04 | 1.223e+04 | 0.6 % | coherencia |
| Frimetal CBN-21, condensador (16/03/2026) | T aire salida [°C] | 40.12 | 39.9 | +0.22 K | coherencia |
| Alfa Laval AlfaNova 27-30H (23/03/2026) | Potencia | 1.076e+04 | 1.05e+04 | 2.5 % | coherencia |
| Alfa Laval AlfaNova 27-30H (23/03/2026) | T agua salida [°C] | 45.11 | 45 | +0.11 K | coherencia |
| Alfa Laval AlfaNova 27-30H (23/03/2026) | Δp refrigerante por fricción [Pa] | 128.7 | 58 | 121.9 % | validacion |


## bandas

### Banda por modo (correlaciones evaluables dentro de su base)

| Modo | ΔQ útil (mín / máx) | ΔIndicador (mín / máx) |
|---|---|---|
| M-1 | -1.72 % / 0.00 % | -1.67 % / 0.00 % |
| M-2 | -1.39 % / 0.00 % | -2.02 % / 0.00 % |
| M-3 | -4.19 % / 0.00 % | -2.74 % / 0.00 % |
| M-4 | -3.67 % / 0.00 % | -2.25 % / 0.00 % |
| M-5 | -1.94 % / 0.00 % | -1.47 % / 0.00 % |

### M-1

| Componente | Familia | Alternativa | Estado | ΔQ útil | ΔW eléctrica | ΔIndicador | ΔT_evap K | ΔT_cond K |
|---|---|---|---|---|---|---|---|---|
| bateria | tube_boiling | gungor_winterton_horizontal | evaluada | 0.00 % | -0.00 % | 0.00 % | -0.00 | -0.00 |
| bateria | tube_boiling | cooper_solo | evaluada | 0.00 % | -0.00 % | 0.00 % | -0.00 | -0.00 |
| bateria | tube_condensation | ficha_cbn21_agregado | evaluada | -0.57 % | 1.12 % | -1.67 % | +0.05 | +0.75 |
| placas | plate_boiling | asymptotic_cooper | evaluada | -1.72 % | -0.50 % | -1.22 % | -0.39 | -0.14 |
| placas | plate_condensation | nusselt_film | no_evaluable | — | — | — | — | — |
| placas | plate_condensation | equivalent_Re | evaluada | 0.00 % | -0.00 % | 0.00 % | -0.00 | -0.00 |
| placas | singlephase | chevron_generic | no_evaluable | — | — | — | — | — |


Fuera de la banda, por estar fuera de su base geométrica: dittus_boelter en placas daría -19.14 % en el indicador.

### M-2

| Componente | Familia | Alternativa | Estado | ΔQ útil | ΔW eléctrica | ΔIndicador | ΔT_evap K | ΔT_cond K |
|---|---|---|---|---|---|---|---|---|
| bateria | tube_boiling | gungor_winterton_horizontal | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| bateria | tube_boiling | cooper_solo | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| bateria | tube_condensation | ficha_cbn21_agregado | evaluada | -0.68 % | 1.36 % | -2.02 % | +0.05 | +0.90 |
| placas | plate_boiling | asymptotic_cooper | evaluada | -1.39 % | -0.45 % | -0.94 % | -0.33 | -0.14 |
| placas | plate_condensation | nusselt_film | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | plate_condensation | equivalent_Re | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | singlephase | chevron_generic | no_evaluable | — | — | — | — | — |


Fuera de la banda, por estar fuera de su base geométrica: dittus_boelter en placas daría -12.33 % en el indicador.

### M-3

| Componente | Familia | Alternativa | Estado | ΔQ útil | ΔW eléctrica | ΔIndicador | ΔT_evap K | ΔT_cond K |
|---|---|---|---|---|---|---|---|---|
| bateria | tube_boiling | gungor_winterton_horizontal | evaluada | -2.59 % | -0.92 % | -1.69 % | -0.58 | -0.22 |
| bateria | tube_boiling | cooper_solo | evaluada | -4.19 % | -1.49 % | -2.74 % | -0.94 | -0.35 |
| bateria | tube_condensation | ficha_cbn21_agregado | evaluada | -0.00 % | -0.00 % | -0.00 % | -0.00 | -0.00 |
| placas | plate_boiling | asymptotic_cooper | evaluada | -0.00 % | -0.00 % | -0.00 % | -0.00 | -0.00 |
| placas | plate_condensation | nusselt_film | no_evaluable | — | — | — | — | — |
| placas | plate_condensation | equivalent_Re | evaluada | -1.06 % | 1.10 % | -2.14 % | +0.03 | +0.89 |
| placas | singlephase | chevron_generic | no_evaluable | — | — | — | — | — |


Fuera de la banda, por estar fuera de su base geométrica: dittus_boelter en placas daría -11.00 % en el indicador.

### M-4

| Componente | Familia | Alternativa | Estado | ΔQ útil | ΔW eléctrica | ΔIndicador | ΔT_evap K | ΔT_cond K |
|---|---|---|---|---|---|---|---|---|
| bateria | tube_boiling | gungor_winterton_horizontal | evaluada | -2.27 % | -0.90 % | -1.39 % | -0.58 | -0.20 |
| bateria | tube_boiling | cooper_solo | evaluada | -3.67 % | -1.46 % | -2.25 % | -0.93 | -0.33 |
| bateria | tube_condensation | ficha_cbn21_agregado | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | plate_boiling | asymptotic_cooper | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | plate_condensation | nusselt_film | no_evaluable | — | — | — | — | — |
| placas | plate_condensation | equivalent_Re | evaluada | -0.25 % | 1.10 % | -1.34 % | +0.03 | +0.89 |
| placas | singlephase | chevron_generic | no_evaluable | — | — | — | — | — |


Fuera de la banda, por estar fuera de su base geométrica: dittus_boelter en placas daría -14.89 % en el indicador.

### M-5

| Componente | Familia | Alternativa | Estado | ΔQ útil | ΔW eléctrica | ΔIndicador | ΔT_evap K | ΔT_cond K |
|---|---|---|---|---|---|---|---|---|
| bateria | tube_boiling | gungor_winterton_horizontal | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| bateria | tube_boiling | cooper_solo | evaluada | -1.94 % | -0.48 % | -1.47 % | -0.61 | -0.20 |
| bateria | tube_condensation | ficha_cbn21_agregado | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | plate_boiling | asymptotic_cooper | evaluada | 0.00 % | 0.00 % | 0.00 % | +0.00 | +0.00 |
| placas | plate_condensation | nusselt_film | no_evaluable | — | — | — | — | — |
| placas | plate_condensation | equivalent_Re | evaluada | -0.05 % | 0.99 % | -1.03 % | +0.04 | +0.49 |
| placas | singlephase | chevron_generic | no_evaluable | — | — | — | — | — |


Fuera de la banda, por estar fuera de su base geométrica: dittus_boelter en placas daría -40.92 % en el indicador.

## dominio

Compresor por polinomios de UNE-EN 12900 (15/10/2026): el dominio de validez es su envolvente, las zonas del diagrama que cubren los datos de VAP (sin límites y refrigeración suplementaria), de 960 a 1450 rpm y de 1 a 10 K de recalentamiento. Dentro, la admisibilidad la deciden solo los límites del compresor real (zona sin límites, 140 °C y presiones); fuera, el polinomio extrapola y el punto no es admisible.

| Punto | T_evap °C | T_cond °C | Relación de compresión | Zona del diagrama | Dominio del compresor | Válido | Admisible |
|---|---|---|---|---|---|---|---|
| M-1 diseño | 1.61 | 43.31 | 3.74 | sin_limites | dentro | True | True |
| M-2 diseño | 3.69 | 45.69 | 3.69 | sin_limites | dentro | True | True |
| M-3 diseño | 0.39 | 48.12 | 4.44 | refrigeracion_suplementaria | dentro | True | False |
| M-4 diseño | 0.39 | 48.02 | 4.43 | refrigeracion_suplementaria | dentro | True | False |
| M-5 diseño | 17.30 | 52.36 | 2.75 | fuera | fuera | True | False |
| M-4 aire 12 °C | 4.57 | 49.61 | 3.96 | sin_limites | dentro | True | True |
| M-4 aire 7 °C | 0.28 | 47.98 | 4.45 | refrigeracion_suplementaria | dentro | True | False |
| M-4 aire 4 °C | -2.30 | 47.09 | 4.79 | refrigeracion_suplementaria | dentro | True | False |
| M-4 aire 2 °C | -3.96 | 46.54 | 5.03 | refrigeracion_suplementaria | dentro | True | False |
| M-4 aire 0 °C | -5.66 | 46.02 | 5.30 | fuera | fuera | True | False |
| M-4 aire -2 °C | -7.44 | 45.49 | 5.60 | fuera | fuera | True | False |
| M-4 aire -5 °C | -10.18 | 44.75 | 6.13 | fuera | fuera | True | False |
| M-4 aire -7 °C | -12.07 | 44.27 | 6.54 | fuera | fuera | True | False |
| M-4 aire -10 °C | -15.01 | 43.61 | 7.27 | fuera | fuera | True | False |
| M-2 aire 20 °C | 2.74 | 31.10 | 2.54 | sin_limites | dentro | True | True |
| M-2 aire 25 °C | 3.07 | 35.97 | 2.89 | sin_limites | dentro | True | True |
| M-2 aire 30 °C | 3.39 | 40.83 | 3.27 | sin_limites | dentro | True | True |
| M-2 aire 35 °C | 3.69 | 45.69 | 3.69 | sin_limites | dentro | True | True |
| M-2 aire 40 °C | 3.98 | 50.56 | 4.15 | sin_limites | dentro | True | True |


## incertidumbre

| Modo | Factor dominante (indicador) | μ* del indicador | Evaluaciones | No válidas |
|---|---|---|---|---|
| M-1 | eta_electromecanico | 6.28 % | 59 | 0 |
| M-2 | eta_electromecanico | 6.33 % | 59 | 0 |
| M-3 | eta_electromecanico | 6.29 % | 59 | 0 |
| M-4 | eta_electromecanico | 6.31 % | 59 | 0 |
| M-5 | eta_electromecanico | 6.61 % | 59 | 0 |

Rangos (decisión del autor, 29/09/2026). El ventilador no es factor: los 780 W son dato. El compresor entra como factor discreto: los dos extremos de la banda del error de ajuste de sus polinomios (decisión P3 del 15/10/2026): banda_desfavorable: caudal ×0.9921, potencia ×1.0083, descarga +1.65 K; banda_favorable: caudal ×1.0079, potencia ×0.9917, descarga -1.65 K.

| Factor | Nominal | Bajo | Alto | Fuente |
|---|---|---|---|---|
| C1_aire | 0.507 | 0.4816 | 0.5323 | ±5 %: validacion con la ficha de evaporador (+4.2 %) |
| Phi_placas | 1.15 | 1.1 | 1.3 | §9.6.4; arrastra beta y phi_c*phi_v |
| phi_md | 1 | 1 | 1.3 | hipotesis M2 (maldistribucion de la bateria) |
| eta_electromecanico | 0.882 | 0.82 | 0.89 | motor IE3-IE4 de 2.2-3 kW por correa de 0.95-0.98 |


### M-1

Sensibilidad local, cambio frente al nominal:

| Factor | Extremo | Valor | Válido | Q útil | W eléctrica | Indicador | Carga (peor) | T_dis |
|---|---|---|---|---|---|---|---|---|
| C1_aire | bajo | 0.4816 | sí | -0.10 % | +0.19 % | -0.29 % | +0.03 % | +0.36 K |
| C1_aire | alto | 0.5323 | sí | +0.09 % | -0.17 % | +0.26 % | -0.10 % | -0.33 K |
| Phi_placas | bajo | 1.1 | sí | -1.21 % | -0.23 % | -0.98 % | -0.86 % | +0.84 K |
| Phi_placas | alto | 1.3 | sí | +3.10 % | +0.53 % | +2.56 % | +2.07 % | -2.12 K |
| phi_md | alto | 1.3 | sí | -0.17 % | +0.33 % | -0.50 % | +0.79 % | +0.63 K |
| eta_electromecanico | bajo | 0.82 | sí | +0.00 % | +5.87 % | -5.54 % | +0.00 % | -0.00 K |
| eta_electromecanico | alto | 0.89 | sí | +0.00 % | -0.70 % | +0.70 % | +0.00 % | -0.00 K |
| compresor banda_desfavorable | — | — | sí | -0.52 % | +0.62 % | -1.13 % | +0.10 % | +1.36 K |
| compresor banda_favorable | — | — | sí | +0.52 % | -0.62 % | +1.14 % | -0.10 % | -1.36 K |

Morris (r = 10, p = 4, semilla 20260929): μ* / σ del efecto elemental por rango completo del factor, en % del nominal (K para la descarga).

| Factor | Q útil | Indicador | Carga (peor) | T_dis K |
|---|---|---|---|---|
| C1_aire (n = 10) | 0.18 / 0.01 | 0.54 / 0.02 | 0.11 / 0.14 | 0.67 / 0.02 |
| Phi_placas (n = 10) | 4.21 / 0.21 | 3.40 / 0.20 | 2.84 / 0.39 | 2.88 / 0.15 |
| phi_md (n = 10) | 0.17 / 0.00 | 0.49 / 0.02 | 0.58 / 0.06 | 0.61 / 0.01 |
| eta_electromecanico (n = 10) | 0.00 / 0.00 | 6.28 / 0.11 | 0.00 / 0.00 | 0.00 / 0.00 |


### M-2

Sensibilidad local, cambio frente al nominal:

| Factor | Extremo | Valor | Válido | Q útil | W eléctrica | Indicador | Carga (peor) | T_dis |
|---|---|---|---|---|---|---|---|---|
| C1_aire | bajo | 0.4816 | sí | -0.13 % | +0.26 % | -0.38 % | -0.01 % | +0.47 K |
| C1_aire | alto | 0.5323 | sí | +0.12 % | -0.24 % | +0.35 % | +0.01 % | -0.43 K |
| Phi_placas | bajo | 1.1 | sí | -0.77 % | -0.25 % | -0.52 % | -0.43 % | +0.37 K |
| Phi_placas | alto | 1.3 | sí | +1.90 % | +0.61 % | +1.28 % | +1.25 % | -0.89 K |
| phi_md | alto | 1.3 | sí | -0.23 % | +0.46 % | -0.68 % | +1.06 % | +0.84 K |
| eta_electromecanico | bajo | 0.82 | sí | +0.00 % | +5.95 % | -5.62 % | +0.00 % | +0.00 K |
| eta_electromecanico | alto | 0.89 | sí | +0.00 % | -0.71 % | +0.71 % | +0.00 % | +0.00 K |
| compresor banda_desfavorable | — | — | sí | -0.56 % | +0.62 % | -1.17 % | -0.04 % | +1.39 K |
| compresor banda_favorable | — | — | sí | +0.56 % | -0.62 % | +1.18 % | +0.02 % | -1.40 K |

Morris (r = 10, p = 4, semilla 20260929): μ* / σ del efecto elemental por rango completo del factor, en % del nominal (K para la descarga).

| Factor | Q útil | Indicador | Carga (peor) | T_dis K |
|---|---|---|---|---|
| C1_aire (n = 10) | 0.25 / 0.01 | 0.73 / 0.03 | 0.03 / 0.03 | 0.90 / 0.03 |
| Phi_placas (n = 10) | 2.59 / 0.16 | 1.71 / 0.13 | 1.49 / 0.27 | 1.22 / 0.09 |
| phi_md (n = 10) | 0.23 / 0.01 | 0.68 / 0.03 | 0.97 / 0.25 | 0.84 / 0.01 |
| eta_electromecanico (n = 10) | 0.00 / 0.00 | 6.33 / 0.07 | 0.00 / 0.00 | 0.00 / 0.00 |


### M-3

Sensibilidad local, cambio frente al nominal:

| Factor | Extremo | Valor | Válido | Q útil | W eléctrica | Indicador | Carga (peor) | T_dis |
|---|---|---|---|---|---|---|---|---|
| C1_aire | bajo | 0.4816 | sí | -0.28 % | -0.10 % | -0.18 % | +0.13 % | +0.17 K |
| C1_aire | alto | 0.5323 | sí | +0.26 % | +0.09 % | +0.17 % | -0.12 % | -0.16 K |
| Phi_placas | bajo | 1.1 | sí | +0.06 % | +0.45 % | -0.39 % | -1.53 % | +1.10 K |
| Phi_placas | alto | 1.3 | sí | -0.94 % | -0.87 % | -0.07 % | +2.69 % | -2.11 K |
| phi_md | alto | 1.3 | sí | -1.11 % | -0.39 % | -0.72 % | +0.65 % | +0.69 K |
| eta_electromecanico | bajo | 0.82 | sí | -0.00 % | +5.95 % | -5.62 % | -0.00 % | -0.00 K |
| eta_electromecanico | alto | 0.89 | sí | -0.00 % | -0.71 % | +0.71 % | -0.00 % | -0.00 K |
| compresor banda_desfavorable | — | — | sí | -0.62 % | +0.62 % | -1.23 % | +0.10 % | +1.39 K |
| compresor banda_favorable | — | — | sí | +0.61 % | -0.62 % | +1.24 % | -0.10 % | -1.39 K |

Morris (r = 10, p = 4, semilla 20260929): μ* / σ del efecto elemental por rango completo del factor, en % del nominal (K para la descarga).

| Factor | Q útil | Indicador | Carga (peor) | T_dis K |
|---|---|---|---|---|
| C1_aire (n = 10) | 0.54 / 0.01 | 0.35 / 0.02 | 0.23 / 0.01 | 0.34 / 0.01 |
| Phi_placas (n = 10) | 1.14 / 0.42 | 0.52 / 0.64 | 3.90 / 1.37 | 3.00 / 0.58 |
| phi_md (n = 10) | 1.11 / 0.01 | 0.72 / 0.04 | 0.65 / 0.03 | 0.70 / 0.01 |
| eta_electromecanico (n = 10) | 0.00 / 0.00 | 6.29 / 0.05 | 0.00 / 0.00 | 0.00 / 0.00 |


### M-4

Sensibilidad local, cambio frente al nominal:

| Factor | Extremo | Valor | Válido | Q útil | W eléctrica | Indicador | Carga (peor) | T_dis |
|---|---|---|---|---|---|---|---|---|
| C1_aire | bajo | 0.4816 | sí | -0.25 % | -0.10 % | -0.15 % | +0.12 % | +0.18 K |
| C1_aire | alto | 0.5323 | sí | +0.23 % | +0.09 % | +0.14 % | -0.11 % | -0.16 K |
| Phi_placas | bajo | 1.1 | sí | -0.07 % | +0.32 % | -0.39 % | -0.80 % | +0.77 K |
| Phi_placas | alto | 1.3 | sí | +0.17 % | -0.73 % | +0.91 % | +1.41 % | -1.76 K |
| phi_md | alto | 1.3 | sí | -0.97 % | -0.38 % | -0.59 % | +0.60 % | +0.71 K |
| eta_electromecanico | bajo | 0.82 | sí | +0.00 % | +5.95 % | -5.62 % | +0.00 % | +0.00 K |
| eta_electromecanico | alto | 0.89 | sí | +0.00 % | -0.71 % | +0.71 % | +0.00 % | +0.00 K |
| compresor banda_desfavorable | — | — | sí | -0.35 % | +0.63 % | -0.97 % | +0.03 % | +1.41 K |
| compresor banda_favorable | — | — | sí | +0.34 % | -0.63 % | +0.98 % | -0.03 % | -1.42 K |

Morris (r = 10, p = 4, semilla 20260929): μ* / σ del efecto elemental por rango completo del factor, en % del nominal (K para la descarga).

| Factor | Q útil | Indicador | Carga (peor) | T_dis K |
|---|---|---|---|---|
| C1_aire (n = 10) | 0.47 / 0.01 | 0.28 / 0.01 | 0.21 / 0.01 | 0.34 / 0.01 |
| Phi_placas (n = 10) | 0.23 / 0.02 | 1.23 / 0.11 | 2.03 / 0.39 | 2.44 / 0.23 |
| phi_md (n = 10) | 0.98 / 0.00 | 0.59 / 0.03 | 0.61 / 0.03 | 0.71 / 0.01 |
| eta_electromecanico (n = 10) | 0.00 / 0.00 | 6.31 / 0.05 | 0.00 / 0.00 | 0.00 / 0.00 |


### M-5

Sensibilidad local, cambio frente al nominal:

| Factor | Extremo | Valor | Válido | Q útil | W eléctrica | Indicador | Carga (peor) | T_dis |
|---|---|---|---|---|---|---|---|---|
| C1_aire | bajo | 0.4816 | sí | -0.52 % | -0.13 % | -0.39 % | -0.07 % | +0.21 K |
| C1_aire | alto | 0.5323 | sí | +0.48 % | +0.12 % | +0.36 % | +0.07 % | -0.19 K |
| Phi_placas | bajo | 1.1 | sí | -0.05 % | +1.09 % | -1.13 % | +0.50 % | +1.25 K |
| Phi_placas | alto | 1.3 | sí | +0.11 % | -2.50 % | +2.69 % | -0.53 % | -2.91 K |
| phi_md | alto | 1.3 | sí | -0.98 % | -0.24 % | -0.74 % | -0.07 % | +0.40 K |
| eta_electromecanico | bajo | 0.82 | sí | +0.00 % | +6.21 % | -5.85 % | +0.00 % | +0.00 K |
| eta_electromecanico | alto | 0.89 | sí | +0.00 % | -0.74 % | +0.74 % | +0.00 % | +0.00 K |
| compresor banda_desfavorable | — | — | sí | -0.18 % | +0.51 % | -0.68 % | +0.07 % | +1.31 K |
| compresor banda_favorable | — | — | sí | +0.17 % | -0.51 % | +0.69 % | -0.03 % | -1.31 K |

Morris (r = 10, p = 4, semilla 20260929): μ* / σ del efecto elemental por rango completo del factor, en % del nominal (K para la descarga).

| Factor | Q útil | Indicador | Carga (peor) | T_dis K |
|---|---|---|---|---|
| C1_aire (n = 10) | 0.98 / 0.02 | 0.76 / 0.04 | 0.21 / 0.03 | 0.41 / 0.01 |
| Phi_placas (n = 10) | 0.16 / 0.01 | 3.63 / 0.32 | 0.80 / 0.25 | 4.01 / 0.35 |
| phi_md (n = 10) | 0.98 / 0.01 | 0.75 / 0.05 | 0.11 / 0.03 | 0.41 / 0.01 |
| eta_electromecanico (n = 10) | 0.00 / 0.00 | 6.61 / 0.11 | 0.00 / 0.00 | 0.00 / 0.00 |

