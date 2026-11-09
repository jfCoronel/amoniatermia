# Cifras del capítulo 13

Generado por `notebooks/10_cifras_capitulo_13.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `2815f4bf5cfddc6df82109063b57f70474093818`
- CoolProp 8.0.0
- Generado: 2026-10-20 15:27
- Secciones: igualacion, diseno, estacional, h5, tewi, lccp, no_validos, sin_envolvente, figuras

## igualacion

Cilindrada escalada hasta igualar la potencia frigorífica del R-717 en A35/W12-7 (10308 W, cap. 12), con sustitución declarada sobre el volumen barrido.

| Fluido | Compresor | Factor de cilindrada | Potencia en A35/W12-7 |
|---|---|---|---|
| R-717 | compresor_bock_f2 | 1.0000 | 10308 W |
| R-290 | compresor_r290 | 1.0774 | 10305 W |
| R-32 | compresor_r32 | 0.9388 | 10307 W |


## diseno

Puntos de diseño del capítulo 11 (recalentamiento 5 K, subenfriamiento 2 K). Indicador: EER en M-1 y M-2, COP en M-3 y M-4, COP global en M-5. Carga: sistema, peor caso de la banda.

| Fluido | Modo | Q útil | Q ACS | W eléctrica | Indicador | Tk | Descarga | pk | Carga | Admisible | Residuo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R-717 | M-1 | 9475 W | 1869 W | 3484 W | 2.720 | 43.3 °C | 124.0 °C | 17.0 bar | 490 g | sí | 2.6e-11 |
| R-717 | M-2 | 10201 W | 0 W | 3665 W | 2.783 | 45.7 °C | 124.1 °C | 18.2 bar | 413 g | sí | 1.6e-11 |
| R-717 | M-3 | 8626 W | 2194 W | 3669 W | 2.351 | 48.1 °C | 143.6 °C | 19.4 bar | 329 g | no: temperatura_descarga, diagrama_aplicacion | 6.9e-11 |
| R-717 | M-4 | 10823 W | 0 W | 3665 W | 2.953 | 48.0 °C | 143.3 °C | 19.3 bar | 333 g | no: temperatura_descarga, diagrama_aplicacion | 1.8e-10 |
| R-717 | M-5 | 0 W | 19946 W | 4376 W | 4.558 | 52.4 °C | 106.4 °C | 21.6 bar | 298 g | no: diagrama_aplicacion | 2.2e-10 |
| R-290 | M-1 | 9542 W | 973 W | 4116 W | 2.318 | 47.8 °C | 71.0 °C | 16.3 bar | 627 g | sí | 2.8e-11 |
| R-290 | M-2 | 10199 W | 0 W | 4289 W | 2.378 | 49.4 °C | 72.0 °C | 16.9 bar | 606 g | sí | 3.0e-11 |
| R-290 | M-3 | 9884 W | 1824 W | 4498 W | 2.197 | 55.7 °C | 82.2 °C | 19.4 bar | 285 g | sí | 5.3e-11 |
| R-290 | M-4 | 11769 W | 0 W | 4454 W | 2.642 | 54.9 °C | 81.1 °C | 19.0 bar | 292 g | sí | 6.6e-11 |
| R-290 | M-5 | 0 W | 19123 W | 5796 W | 3.299 | 62.7 °C | 82.5 °C | 22.4 bar | 319 g | no: diagrama_aplicacion | 2.7e-10 |
| R-32 | M-1 | 9613 W | 2488 W | 3621 W | 2.655 | 45.0 °C | 99.3 °C | 27.9 bar | 1273 g | sí | 4.5e-11 |
| R-32 | M-2 | 10207 W | 0 W | 3785 W | 2.697 | 47.2 °C | 99.9 °C | 29.4 bar | 1163 g | sí | 4.6e-10 |
| R-32 | M-3 | 8527 W | 3249 W | 4045 W | 2.108 | 51.3 °C | 113.8 °C | 32.3 bar | 614 g | sí | 5.2e-11 |
| R-32 | M-4 | 11798 W | 0 W | 3997 W | 2.952 | 50.6 °C | 112.5 °C | 31.9 bar | 632 g | sí | 1.1e-10 |
| R-32 | M-5 | 0 W | 18378 W | 4375 W | 4.200 | 53.3 °C | 92.1 °C | 33.9 bar | 707 g | no: diagrama_aplicacion | 9.4e-11 |


## estacional

H5 a VELOCIDAD FIJA para los tres fluidos (decisión V4 del 15/10/2026): el compresor de R-32 no admite velocidad variable. La última columna es el R-717 con velocidad variable (cap. 12), resultado propio que no entra en H5. Carga de diseño de calefacción COMÚN: la del R-717 con Tbiv = TOL (cap. 12), en cada clima y aplicación (decisión 2 del 05/10/2026). La TOL de cada fluido es la de su compresor (zona sin límites de su diagrama y presiones máximas; el R-290 y el R-32 no tienen límite de descarga publicado). Refrigeración: Pdesignc = potencia en A de cada fluido, igualada.

| Aplicación | Clima | SCOP R-717 | SCOP R-290 | SCOP R-32 | SCOP R-717, velocidad variable |
|---|---|---|---|---|---|
| 35 °C | medio | 2.574 (TOL -3 °C, apoyo 10 %) | 2.864 (TOL -10 °C, apoyo 1 %) | 3.166 (TOL -10 °C, apoyo 1 %) | 2.591 |
| 35 °C | calido | 3.384 (TOL 2 °C, apoyo 0 %) | 2.930 (TOL 2 °C, apoyo 0 %) | 3.372 (TOL 2 °C, apoyo 0 %) | 3.529 |
| 35 °C | frio | 2.186 (TOL -6 °C, apoyo 19 %) | 2.662 (TOL -22 °C, apoyo 4 %) | 2.837 (TOL -19 °C, apoyo 4 %) | 2.191 |
| 35 °C | Sevilla | 3.460 (TOL 3 °C, apoyo 2 %) | 3.030 (TOL 3 °C, apoyo 2 %) | 3.449 (TOL 3 °C, apoyo 2 %) | 3.576 |
| 35 °C | Madrid | 3.068 (TOL -2 °C, apoyo 2 %) | 2.856 (TOL -3 °C, apoyo 1 %) | 3.212 (TOL -3 °C, apoyo 1 %) | 3.132 |
| 35 °C | Burgos | 2.889 (TOL -2 °C, apoyo 5 %) | 2.893 (TOL -4 °C, apoyo 0 %) | 3.232 (TOL -4 °C, apoyo 0 %) | 2.924 |
| 45 °C | medio | 1.865 (TOL 1 °C, apoyo 32 %) | 2.556 (TOL -10 °C, apoyo 5 %) | 2.734 (TOL -8 °C, apoyo 6 %) | 1.875 |
| 45 °C | calido | 2.902 (TOL 5 °C, apoyo 6 %) | 2.828 (TOL 2 °C, apoyo 0 %) | 3.241 (TOL 2 °C, apoyo 0 %) | 2.976 |
| 45 °C | frio | 1.541 (TOL -1 °C, apoyo 48 %) | 2.308 (TOL -21 °C, apoyo 11 %) | 2.328 (TOL -12 °C, apoyo 14 %) | 1.541 |
| 45 °C | Sevilla | 2.958 (TOL 5 °C, apoyo 7 %) | 2.908 (TOL 3 °C, apoyo 2 %) | 3.309 (TOL 3 °C, apoyo 2 %) | 3.032 |
| 45 °C | Madrid | 2.359 (TOL 2 °C, apoyo 16 %) | 2.739 (TOL -3 °C, apoyo 2 %) | 3.046 (TOL -3 °C, apoyo 2 %) | 2.386 |
| 45 °C | Burgos | 1.982 (TOL 2 °C, apoyo 28 %) | 2.649 (TOL -4 °C, apoyo 4 %) | 2.906 (TOL -4 °C, apoyo 4 %) | 1.996 |
| 55 °C | medio | 1.553 (TOL 3 °C, apoyo 48 %) | 2.273 (TOL -10 °C, apoyo 11 %) | 2.332 (TOL -4 °C, apoyo 14 %) | 1.557 |
| 55 °C | calido | 2.083 (TOL 8 °C, apoyo 27 %) | 2.594 (TOL 2 °C, apoyo 6 %) | 2.907 (TOL 3 °C, apoyo 6 %) | 2.104 |
| 55 °C | frio | 1.332 (TOL 1 °C, apoyo 63 %) | 2.053 (TOL -18 °C, apoyo 18 %) | 2.038 (TOL -8 °C, apoyo 22 %) | 1.334 |
| 55 °C | Sevilla | 2.733 (TOL 6 °C, apoyo 11 %) | 2.833 (TOL 3 °C, apoyo 3 %) | 3.126 (TOL 4 °C, apoyo 4 %) | 2.787 |
| 55 °C | Madrid | 2.080 (TOL 3 °C, apoyo 24 %) | 2.587 (TOL -3 °C, apoyo 4 %) | 2.758 (TOL -1 °C, apoyo 6 %) | 2.095 |
| 55 °C | Burgos | 1.722 (TOL 3 °C, apoyo 39 %) | 2.441 (TOL -4 °C, apoyo 6 %) | 2.464 (TOL -1 °C, apoyo 12 %) | 1.730 |

### SEER

| Clima | R-717 | R-290 | R-32 | R-717, velocidad variable |
|---|---|---|---|---|
| medio | 2.967 | 2.575 | 2.891 | 3.179 |
| Sevilla | 2.937 | 2.545 | 2.861 | 3.128 |
| Madrid | 2.959 | 2.565 | 2.883 | 3.157 |
| Burgos | 2.865 | 2.491 | 2.790 | 3.128 |


## h5

Criterio de H5 (tabla 1.2): SCOP y SEER del R-717 iguales o mayores que los de R-290 y R-32 más un 5 %, sobre la misma arquitectura; la diferencia cuenta si sale de la banda de incertidumbre sobre la diferencia (§6.11). La banda se calcula en los puntos de diseño (M-2: EER; M-4: COP), aplicando cada perturbación a los dos fluidos a la vez. El rendimiento electromecánico solo perturba al R-717 (los herméticos llevan el motor dentro de sus parámetros): no se cancela.

| Comparación | Indicador | Diferencia del R-717 | Cumple +5 % |
|---|---|---|---|
| R-717 frente a R-290 | SCOP 35 °C, clima medio | -10.1 % | no |
| R-717 frente a R-290 | SCOP 45 °C, clima medio | -27.0 % | no |
| R-717 frente a R-290 | SCOP 55 °C, clima medio | -31.6 % | no |
| R-717 frente a R-290 | SEER, clima medio | +15.2 % | sí |
| R-717 frente a R-32 | SCOP 35 °C, clima medio | -18.7 % | no |
| R-717 frente a R-32 | SCOP 45 °C, clima medio | -31.8 % | no |
| R-717 frente a R-32 | SCOP 55 °C, clima medio | -33.4 % | no |
| R-717 frente a R-32 | SEER, clima medio | +2.6 % | no |

### Banda de incertidumbre sobre la diferencia (puntos de diseño)

| Comparación | Modo | Diferencia | Banda RSS | Banda lineal | Grupos |
|---|---|---|---|---|---|
| R-717 frente a R-290 | M-2 | +17.03 % | ± 10.88 % | ± 18.84 % | bateria/tube_boiling 0.00 %, bateria/tube_condensation 8.03 %, placas/plate_boiling 0.35 %, placas/plate_condensation 0.00 %, C1_aire 0.14 %, Phi_placas 0.27 %, phi_md 3.22 %, eta_electromecanico 6.57 %, compresor 0.26 % |
| R-717 frente a R-290 | M-4 | +11.77 % | ± 9.14 % | ± 17.52 % | bateria/tube_boiling 1.80 %, bateria/tube_condensation 0.00 %, placas/plate_boiling 0.00 %, placas/plate_condensation 5.75 %, C1_aire 0.09 %, Phi_placas 2.69 %, phi_md 0.20 %, eta_electromecanico 6.28 %, compresor 0.72 % |
| R-717 frente a R-32 | M-2 | +3.22 % | ± 7.46 % | ± 12.48 % | bateria/tube_boiling 0.00 %, bateria/tube_condensation 4.34 %, placas/plate_boiling 0.50 %, placas/plate_condensation 0.00 %, C1_aire 0.07 %, Phi_placas 0.03 %, phi_md 1.70 %, eta_electromecanico 5.80 %, compresor 0.04 % |
| R-717 frente a R-32 | M-4 | +0.05 % | ± 5.86 % | ± 8.74 % | bateria/tube_boiling 1.39 %, bateria/tube_condensation 0.00 %, placas/plate_boiling 0.00 %, placas/plate_condensation 0.67 %, C1_aire 0.03 %, Phi_placas 0.46 %, phi_md 0.16 %, eta_electromecanico 5.62 %, compresor 0.42 % |


## tewi

TEWI con el caso base del IIR (fugas 2.5 %/año, 15 % al fin de vida, 15 años; decisión 4) y el GWP del Reglamento (UE) 2024/573 (decisión 3). Consumo: calefacción a 45 °C y refrigeración por el método de la norma (decisión 12). Carga: el peor modo válido de cada fluido, sistema, peor caso de la banda. Factor de emisión: cota inferior y superior de H7 y el dato de REE de 2024.

| Clima | β [kg/kWh] | R-717 | R-290 | R-32 |
|---|---|---|---|---|
| medio | 0.103 | 31.66 t (0.0 % directo) | 25.25 t (0.0 % directo) | 23.80 t (1.9 % directo) |
| medio | 0.150 | 46.10 t (0.0 % directo) | 36.77 t (0.0 % directo) | 34.45 t (1.3 % directo) |
| medio | 0.360 | 110.64 t (0.0 % directo) | 88.26 t (0.0 % directo) | 82.06 t (0.5 % directo) |
| Sevilla | 0.103 | 18.94 t (0.0 % directo) | 20.54 t (0.0 % directo) | 18.62 t (2.4 % directo) |
| Sevilla | 0.150 | 27.59 t (0.0 % directo) | 29.92 t (0.0 % directo) | 26.92 t (1.7 % directo) |
| Sevilla | 0.360 | 66.21 t (0.0 % directo) | 71.81 t (0.0 % directo) | 63.97 t (0.7 % directo) |
| Madrid | 0.103 | 25.66 t (0.0 % directo) | 24.00 t (0.0 % directo) | 21.96 t (2.1 % directo) |
| Madrid | 0.150 | 37.37 t (0.0 % directo) | 34.95 t (0.0 % directo) | 31.77 t (1.4 % directo) |
| Madrid | 0.360 | 89.68 t (0.0 % directo) | 83.87 t (0.0 % directo) | 75.62 t (0.6 % directo) |
| Burgos | 0.103 | 33.61 t (0.0 % directo) | 26.39 t (0.0 % directo) | 24.45 t (1.8 % directo) |
| Burgos | 0.150 | 48.95 t (0.0 % directo) | 38.44 t (0.0 % directo) | 35.40 t (1.3 % directo) |
| Burgos | 0.360 | 117.49 t (0.0 % directo) | 92.25 t (0.0 % directo) | 84.32 t (0.5 % directo) |

### Caso reglamentario RD 552/2019 (clima medio, β = 0.15)

| Fluido | Carga | TEWI |
|---|---|---|
| R-717 | 490 g | 46.10 t |
| R-290 | 627 g | 36.77 t |
| R-32 | 1273 g | 39.11 t |


## lccp

LCCP (IIR, 2016) con los parámetros del TEWI, la fabricación del refrigerante (IIR, tabla 4.4; NH3, IPCC 2006) y la de los materiales (IIR, tabla 4.2; inoxidable, worldstainless), con las masas de `data/ambiental.yaml` (decisión 13).

| Clima | β [kg/kWh] | R-717 | R-290 | R-32 |
|---|---|---|---|---|
| medio | 0.103 | 31.84 t | 25.49 t | 23.97 t |
| medio | 0.150 | 46.29 t | 37.01 t | 34.62 t |
| medio | 0.360 | 110.83 t | 88.50 t | 82.23 t |
| Sevilla | 0.103 | 19.13 t | 20.78 t | 18.79 t |
| Sevilla | 0.150 | 27.77 t | 30.16 t | 27.09 t |
| Sevilla | 0.360 | 66.40 t | 72.04 t | 64.14 t |
| Madrid | 0.103 | 25.84 t | 24.23 t | 22.13 t |
| Madrid | 0.150 | 37.55 t | 35.18 t | 31.94 t |
| Madrid | 0.360 | 89.87 t | 84.11 t | 75.79 t |
| Burgos | 0.103 | 33.80 t | 26.63 t | 24.62 t |
| Burgos | 0.150 | 49.14 t | 38.67 t | 35.57 t |
| Burgos | 0.360 | 117.67 t | 92.48 t | 84.49 t |

### Desglose en el clima medio con β = 0.15 [kg CO₂e]

| Fluido | Directo | Energía | Materiales | Refrigerante | LCCP |
|---|---|---|---|---|---|
| R-717 | 0 | 46101 | 184 | 1.1 | 46286 |
| R-290 | 0 | 36774 | 237 | 0.0 | 37011 |
| R-32 | 451 | 34003 | 157 | 12.6 | 34624 |


## no_validos

Puntos de carga parcial que no convergen tras el reintento por continuación: se excluyen de la interpolación y no se toman por no admisibles.

| Fluido | Aplicación | Clima | Aire |
|---|---|---|---|
| R-290 | 35 °C | frio | 2 °C |
| R-290 | 45 °C | medio | -10 °C |


## sin_envolvente

Escenario del autor (20/10/2026): un compresor que fuera de la envolvente de su fabricante sigue la tendencia de sus datos. Todo punto válido es admisible —sin diagrama de aplicación ni límite de descarga— y los polinomios de UNE-EN 12900 extrapolan. Misma carga de diseño que el caso base (la del R-717 con su TOL real, la misma vivienda), velocidad fija en los tres fluidos, como H5. El SEER no cambia: todos los puntos de refrigeración ya eran admisibles.

| Aplicación | Clima | SCOP R-717 | SCOP R-290 | SCOP R-32 |
|---|---|---|---|---|
| 35 °C | medio | 2.960 (base 2.574; TOL -10 °C, apoyo 2 %) | 2.864 (base 2.864; TOL -10 °C, apoyo 1 %) | 3.166 (base 3.166; TOL -10 °C, apoyo 1 %) |
| 35 °C | calido | 3.384 (base 3.384; TOL 2 °C, apoyo 0 %) | 2.930 (base 2.930; TOL 2 °C, apoyo 0 %) | 3.372 (base 3.372; TOL 2 °C, apoyo 0 %) |
| 35 °C | frio | 2.558 (base 2.186; TOL -22 °C, apoyo 7 %) | 2.662 (base 2.662; TOL -22 °C, apoyo 4 %) | 2.845 (base 2.837; TOL -22 °C, apoyo 3 %) |
| 35 °C | Sevilla | 3.460 (base 3.460; TOL 3 °C, apoyo 2 %) | 3.030 (base 3.030; TOL 3 °C, apoyo 2 %) | 3.449 (base 3.449; TOL 3 °C, apoyo 2 %) |
| 35 °C | Madrid | 3.143 (base 3.068; TOL -3 °C, apoyo 1 %) | 2.856 (base 2.856; TOL -3 °C, apoyo 1 %) | 3.212 (base 3.212; TOL -3 °C, apoyo 1 %) |
| 35 °C | Burgos | 3.106 (base 2.889; TOL -4 °C, apoyo 1 %) | 2.893 (base 2.893; TOL -4 °C, apoyo 0 %) | 3.232 (base 3.232; TOL -4 °C, apoyo 0 %) |
| 45 °C | medio | 2.513 (base 1.865; TOL -10 °C, apoyo 9 %) | 2.556 (base 2.556; TOL -10 °C, apoyo 5 %) | 2.757 (base 2.734; TOL -10 °C, apoyo 5 %) |
| 45 °C | calido | 3.202 (base 2.902; TOL 2 °C, apoyo 1 %) | 2.828 (base 2.828; TOL 2 °C, apoyo 0 %) | 3.241 (base 3.241; TOL 2 °C, apoyo 0 %) |
| 45 °C | frio | 2.138 (base 1.541; TOL -22 °C, apoyo 17 %) | 2.308 (base 2.308; TOL -22 °C, apoyo 11 %) | 2.391 (base 2.328; TOL -22 °C, apoyo 11 %) |
| 45 °C | Sevilla | 3.265 (base 2.958; TOL 3 °C, apoyo 3 %) | 2.908 (base 2.908; TOL 3 °C, apoyo 2 %) | 3.309 (base 3.309; TOL 3 °C, apoyo 2 %) |
| 45 °C | Madrid | 2.879 (base 2.359; TOL -3 °C, apoyo 4 %) | 2.739 (base 2.739; TOL -3 °C, apoyo 2 %) | 3.046 (base 3.046; TOL -3 °C, apoyo 2 %) |
| 45 °C | Burgos | 2.672 (base 1.982; TOL -4 °C, apoyo 7 %) | 2.649 (base 2.649; TOL -4 °C, apoyo 4 %) | 2.906 (base 2.906; TOL -4 °C, apoyo 4 %) |
| 55 °C | medio | 2.222 (base 1.553; TOL -10 °C, apoyo 16 %) | 2.273 (base 2.273; TOL -10 °C, apoyo 11 %) | 2.428 (base 2.332; TOL -10 °C, apoyo 11 %) |
| 55 °C | calido | 2.817 (base 2.083; TOL 2 °C, apoyo 8 %) | 2.594 (base 2.594; TOL 2 °C, apoyo 6 %) | 2.913 (base 2.907; TOL 2 °C, apoyo 6 %) |
| 55 °C | frio | 1.934 (base 1.332; TOL -22 °C, apoyo 24 %) | 2.060 (base 2.053; TOL -22 °C, apoyo 18 %) | 2.102 (base 2.038; TOL -22 °C, apoyo 18 %) |
| 55 °C | Sevilla | 3.156 (base 2.733; TOL 3 °C, apoyo 4 %) | 2.833 (base 2.833; TOL 3 °C, apoyo 3 %) | 3.214 (base 3.126; TOL 3 °C, apoyo 3 %) |
| 55 °C | Madrid | 2.697 (base 2.080; TOL -3 °C, apoyo 6 %) | 2.587 (base 2.587; TOL -3 °C, apoyo 4 %) | 2.864 (base 2.758; TOL -3 °C, apoyo 4 %) |
| 55 °C | Burgos | 2.455 (base 1.722; TOL -4 °C, apoyo 10 %) | 2.441 (base 2.441; TOL -4 °C, apoyo 6 %) | 2.664 (base 2.464; TOL -4 °C, apoyo 6 %) |

### H5 en el escenario (diferencia del R-717; base y sin envolvente)

| Comparación | Indicador | Base | Sin envolvente | Cumple +5 % |
|---|---|---|---|---|
| R-717 frente a R-290 | SCOP 35 °C, medio | -10.1 % | +3.4 % | no |
| R-717 frente a R-290 | SCOP 35 °C, Sevilla | +14.2 % | +14.2 % | sí |
| R-717 frente a R-290 | SCOP 35 °C, Madrid | +7.4 % | +10.0 % | sí |
| R-717 frente a R-290 | SCOP 35 °C, Burgos | -0.1 % | +7.4 % | sí |
| R-717 frente a R-290 | SCOP 45 °C, medio | -27.0 % | -1.7 % | no |
| R-717 frente a R-290 | SCOP 45 °C, Sevilla | +1.8 % | +12.3 % | sí |
| R-717 frente a R-290 | SCOP 45 °C, Madrid | -13.8 % | +5.1 % | sí |
| R-717 frente a R-290 | SCOP 45 °C, Burgos | -25.2 % | +0.8 % | no |
| R-717 frente a R-290 | SCOP 55 °C, medio | -31.6 % | -2.2 % | no |
| R-717 frente a R-290 | SCOP 55 °C, Sevilla | -3.5 % | +11.4 % | sí |
| R-717 frente a R-290 | SCOP 55 °C, Madrid | -19.6 % | +4.2 % | no |
| R-717 frente a R-290 | SCOP 55 °C, Burgos | -29.5 % | +0.6 % | no |
| R-717 frente a R-32 | SCOP 35 °C, medio | -18.7 % | -6.5 % | no |
| R-717 frente a R-32 | SCOP 35 °C, Sevilla | +0.3 % | +0.3 % | no |
| R-717 frente a R-32 | SCOP 35 °C, Madrid | -4.5 % | -2.2 % | no |
| R-717 frente a R-32 | SCOP 35 °C, Burgos | -10.6 % | -3.9 % | no |
| R-717 frente a R-32 | SCOP 45 °C, medio | -31.8 % | -8.8 % | no |
| R-717 frente a R-32 | SCOP 45 °C, Sevilla | -10.6 % | -1.3 % | no |
| R-717 frente a R-32 | SCOP 45 °C, Madrid | -22.5 % | -5.5 % | no |
| R-717 frente a R-32 | SCOP 45 °C, Burgos | -31.8 % | -8.1 % | no |
| R-717 frente a R-32 | SCOP 55 °C, medio | -33.4 % | -8.5 % | no |
| R-717 frente a R-32 | SCOP 55 °C, Sevilla | -12.6 % | -1.8 % | no |
| R-717 frente a R-32 | SCOP 55 °C, Madrid | -24.6 % | -5.8 % | no |
| R-717 frente a R-32 | SCOP 55 °C, Burgos | -30.1 % | -7.8 % | no |

### Puntos fuera de la envolvente del caso base

| Fluido | Puntos de carga parcial | Fuera de la envolvente | Descarga máxima |
|---|---|---|---|
| R-717 | 72 | 26 | 379 °C |
| R-290 | 72 | 2 | 99 °C |
| R-32 | 72 | 10 | 221 °C |

### TEWI en el escenario (calefacción a 45 °C y refrigeración)

| Clima | β [kg/kWh] | R-717 | R-290 | R-32 |
|---|---|---|---|---|
| medio | 0.15 | 36.14 t | 36.77 t | 34.23 t |
| medio | 0.36 | 86.75 t | 88.26 t | 81.53 t |
| Sevilla | 0.15 | 26.31 t | 29.92 t | 26.92 t |
| Sevilla | 0.36 | 63.13 t | 71.81 t | 63.97 t |
| Madrid | 0.15 | 32.35 t | 34.95 t | 31.77 t |
| Madrid | 0.36 | 77.64 t | 83.87 t | 75.62 t |
| Burgos | 0.15 | 37.49 t | 38.44 t | 35.40 t |
| Burgos | 0.36 | 89.98 t | 92.25 t | 84.32 t |


## figuras

Figuras escritas en `docs/figuras`: fig_13_1_scop_seer, fig_13_2_tewi (png y pdf).
