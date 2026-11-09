# Cifras del capítulo 9, calculadas por el modelo

Generado por `notebooks/03_cifras_capitulo_9.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `37340a21b6a8362ab2d979b85ca7c0885825a3ca-dirty`
- CoolProp 8.0.0
- Generado: 2026-10-15 12:52
- Secciones: compresor, semiempirico, m2, evaporador, carga, desrecalentador, modos, exergia, tabular, continuacion, malla_placas, residuo_entalpico, tabular_modos

> **Aviso**: árbol de trabajo con cambios sin confirmar; estas cifras no son reproducibles tal cual (§6.12).

## compresor

### Calidad del ajuste de los polinomios a cada velocidad (desviación máxima sobre sus propios puntos, 5 K de recalentamiento)

| Velocidad | Puntos | Caudal | Potencia al eje | Descarga |
|---|---|---|---|---|
| 960 rpm | 57 | ±0.79 % | ±0.72 % | ±1.61 K |
| 1100 rpm | 57 | ±0.52 % | ±0.56 % | ±1.62 K |
| 1250 rpm | 57 | ±0.58 % | ±0.43 % | ±1.57 K |
| 1450 rpm | 57 | ±0.47 % | ±0.36 % | ±1.62 K |

### Rendimientos que se conservan al cambiar el recalentamiento (2 / 46.8 °C)

| Velocidad | Recalentamiento | η_v | η_is (eje) | η_dis | Caudal | Potencia al eje | Descarga | Calor al ambiente |
|---|---|---|---|---|---|---|---|---|
| 960 rpm | 1 K | 0.8422 | 0.7274 | 0.7971 | 21.64 kg/h | 1694 W | 125.78 °C | 148 W |
| 960 rpm | 5 K | 0.8422 | 0.7274 | 0.7971 | 21.22 kg/h | 1694 W | 131.81 °C | 148 W |
| 1450 rpm | 1 K | 0.8272 | 0.7174 | 0.7852 | 32.10 kg/h | 2548 W | 127.28 °C | 220 W |
| 1450 rpm | 5 K | 0.8272 | 0.7174 | 0.7852 | 31.49 kg/h | 2548 W | 133.34 °C | 220 W |

### Punto de referencia del §9.7.8 (2 / 46.8 °C, 1 K, 1450 rpm), con los dos modelos

| Modelo | Caudal | Potencia al eje | Descarga |
|---|---|---|---|
| Polinomios (adoptado) | 32.10 kg/h | 2548 W | 127.28 °C |
| Semiempírico (24/09/2026) | 32.21 kg/h | 2566 W | 125.46 °C |

### Coeficientes de los polinomios (t0 y tc en °C; UNE-EN 12900)

#### 960 rpm (57 puntos)

| Término | Caudal [g/s] | Potencia al eje [W] | Descarga [°C] |
|---|---|---|---|
| c0 (1) | 6.44434 | 943.106 | 61.0871 |
| c1 (t0) | 0.240021 | 3.57827 | -0.676202 |
| c2 (tc) | 0.0253779 | -17.5475 | -1.43396 |
| c3 (t0²) | 0.00306024 | -0.463367 | 0.0087773 |
| c4 (t0·tc) | 0.00177585 | -0.662193 | -0.0700857 |
| c5 (tc²) | -0.00186126 | 1.16425 | 0.100651 |
| c6 (t0³) | 1.68883e-05 | -0.00653445 | -0.00142217 |
| c7 (tc·t0²) | 2.74461e-05 | -0.00336422 | 0.00178199 |
| c8 (t0·tc²) | -2.77049e-05 | 0.0230205 | 1.45488e-05 |
| c9 (tc³) | 1.75396e-05 | -0.00996791 | -0.000732862 |

#### 1100 rpm (57 puntos)

| Término | Caudal [g/s] | Potencia al eje [W] | Descarga [°C] |
|---|---|---|---|
| c0 (1) | 7.29909 | 1081.79 | 61.1062 |
| c1 (t0) | 0.272107 | 4.54948 | -0.665413 |
| c2 (tc) | 0.0375364 | -21.1093 | -1.43066 |
| c3 (t0²) | 0.00343927 | -0.484952 | 0.00929047 |
| c4 (t0·tc) | 0.00238024 | -0.80775 | -0.0710221 |
| c5 (tc²) | -0.00243357 | 1.37667 | 0.100621 |
| c6 (t0³) | 1.66652e-05 | -0.00667732 | -0.00141807 |
| c7 (tc·t0²) | 3.43856e-05 | -0.00549088 | 0.00176646 |
| c8 (t0·tc²) | -3.89021e-05 | 0.0272409 | 2.86939e-05 |
| c9 (tc³) | 2.32663e-05 | -0.0119118 | -0.000732629 |

#### 1250 rpm (57 puntos)

| Término | Caudal [g/s] | Potencia al eje [W] | Descarga [°C] |
|---|---|---|---|
| c0 (1) | 8.26386 | 1222.53 | 61.4067 |
| c1 (t0) | 0.308446 | 4.51445 | -0.66937 |
| c2 (tc) | 0.0399896 | -23.8516 | -1.43872 |
| c3 (t0²) | 0.00374988 | -0.599512 | 0.00931282 |
| c4 (t0·tc) | 0.00248967 | -0.857484 | -0.0714532 |
| c5 (tc²) | -0.00263805 | 1.56408 | 0.100981 |
| c6 (t0³) | 1.37388e-05 | -0.00839304 | -0.00142421 |
| c7 (tc·t0²) | 3.7503e-05 | -0.00439117 | 0.00177329 |
| c8 (t0·tc²) | -3.90017e-05 | 0.0298799 | 3.18877e-05 |
| c9 (tc³) | 2.48566e-05 | -0.0135823 | -0.000734886 |

#### 1450 rpm (57 puntos)

| Término | Caudal [g/s] | Potencia al eje [W] | Descarga [°C] |
|---|---|---|---|
| c0 (1) | 9.51951 | 1395.29 | 62.0086 |
| c1 (t0) | 0.357126 | 4.71298 | -0.684222 |
| c2 (tc) | 0.0446206 | -25.1052 | -1.45872 |
| c3 (t0²) | 0.00438668 | -0.688676 | 0.00918269 |
| c4 (t0·tc) | 0.00268655 | -0.959865 | -0.0715917 |
| c5 (tc²) | -0.00300894 | 1.73142 | 0.101895 |
| c6 (t0³) | 1.66027e-05 | -0.00939149 | -0.00143895 |
| c7 (tc·t0²) | 4.01458e-05 | -0.00574213 | 0.00180032 |
| c8 (t0·tc²) | -4.21266e-05 | 0.0341052 | 2.11442e-05 |
| c9 (tc³) | 2.85079e-05 | -0.0149173 | -0.000741111 |

## semiempirico

### Juego semiempírico del 24/09/2026 frente al catálogo y a la envolvente

| Puntos | Caudal | Potencia al eje | Descarga |
|---|---|---|---|
| Catálogo, 46 (identificación) | ±2.71 % | ±4.72 % | ±3.35 K |
| Envolvente de VAP, 49 (sin límites, 1450 rpm, 5 K) | ±5.71 % | ±13.73 % | ±25.34 K |

### Ensayo de ampliación (15/10/2026): reidentificación sobre los 95 puntos, desviación máxima dentro de la muestra

| Estructura | Parámetros | Caudal | Potencia al eje | Descarga |
|---|---|---|---|---|
| Vigente | 9 | 5.5 % | 12.7 % | 8.6 K |
| + exponente de reexpansión libre | 10 | 5.3 % | 12.5 % | 8.3 K |
| + fuga mezclada en la aspiración | 9 | 5.5 % | 12.7 % | 8.6 K |
| + fuga mezclada y exponente | 10 | 5.3 % | 12.5 % | 8.4 K |
| + las dos y η_ic con la relación de presiones | 11 | 5.2 % | 12.8 % | 8.6 K |
| + las dos y pérdida mecánica con ΔP | 11 | 5.3 % | 12.4 % | 8.2 K |
| Las cuatro | 12 | 5.2 % | 12.9 % | 9.1 K |

## m2

### Tabla 9.19 — equilibrio de M-2 (evaporación a 2 °C, aire a 35 °C)

| Magnitud | Modelo |
|---|---|
| Temperatura de condensación | 44.88 °C |
| Calor evacuado | 11.73 kW |
| Potencia frigorífica | 9.49 kW |
| Potencia al eje | 2.464 kW |
| Caudal másico | 32.48 kg/h |
| Temperatura de descarga | 121.46 °C |
| Presupuesto de RS-5 | 474 g |
| Residuo / válido | 5.8e-12 / True |

### Tabla 9.22 — carga de la batería frente al subenfriamiento

| Subenfriamiento | Volumen anegado | Carga (banda) | Capacidad | % del presupuesto de RS-5 de la fila |
|---|---|---|---|---|
| 0.0 K | 0.0 % | 177 – 327 g | 9.49 kW | 69 % |
| 7.3 K | 9.2 % | 364 – 499 g | 9.70 kW | 103 % |
| 9.5 K | 14.1 % | 465 – 591 g | 9.73 kW | 122 % |
| 10.6 K | 17.3 % | 530 – 650 g | 9.73 kW | 134 % |

## evaporador

### Tabla 9.20 — operación como evaporador (condensación a 50 °C)

| Aire exterior | T_evap impuesta / resuelta | Q impuesta / resuelta | COP impuesto / resuelto | U [W/(m²·K)] | Diferencia |
|---|---|---|---|---|---|
| 7 °C bs / 6 °C bh | 1.6 / 0.93 °C | 8.81 / 8.52 kW | 4.23 / 4.15 | 32.7 | 3.3 % |
| 2 °C bs / 1 °C bh | -2.9 / -3.39 °C | 6.99 / 6.82 kW | 3.77 / 3.73 | 32.8 | 2.6 % |
| −7 °C bs / −8 °C bh | -11.1 / -10.98 °C | 4.39 / 4.42 kW | 3.17 / 3.18 | 36.2 | -0.7 % |

## carga

### Tabla 9.21 — carga de la batería como condensador (45 °C, 3.8 L, promedio uniforme en título, G = 48 kg/(m²·s))

| Correlación | Fracción de huecos | Densidad media | Masa |
|---|---|---|---|
| Homogéneo | 0.930 | 52.7 kg/m³ | 200 g |
| Zivi | 0.844 | 100.7 kg/m³ | 383 g |
| Lockhart-Martinelli | 0.880 | 80.6 kg/m³ | 306 g |
| Rouhani-Axelsson | 0.824 | 112.2 kg/m³ | 426 g |

## desrecalentador

### Tabla 9.16 — barrido del retorno, M-1, impulsión 67 °C

| Retorno | Caudal de ACS | Q recuperado | Margen / título de salida | Pared húmeda | T_cond | Válido |
|---|---|---|---|---|---|---|
| 25 °C | 40.8 kg/h | 1988 W | +1.27 K | 25 % | 42.99 °C | True |
| 30 °C | 44.9 kg/h | 1929 W | +3.42 K | 25 % | 43.16 °C | True |
| 35 °C | 50.3 kg/h | 1869 W | +5.62 K | 8 % | 43.31 °C | True |
| 45 °C | 67.8 kg/h | 1731 W | +10.74 K | 0 % | 43.58 °C | True |
| 55 °C | 113.1 kg/h | 1577 W | +16.59 K | 0 % | 43.80 °C | True |
| 60 °C | 183.7 kg/h | 1495 W | +19.78 K | 0 % | 43.90 °C | True |

### Tabla 9.16 — barrido del retorno, M-3, impulsión 67 °C

| Retorno | Caudal de ACS | Q recuperado | Margen / título de salida | Pared húmeda | T_cond | Válido |
|---|---|---|---|---|---|---|
| 25 °C | 49.6 kg/h | 2421 W | condensa, x = 0.975 | 36 % | 47.69 °C | True |
| 30 °C | 53.2 kg/h | 2285 W | condensa, x = 0.991 | 31 % | 47.81 °C | True |
| 35 °C | 59.0 kg/h | 2194 W | +1.06 K | 33 % | 48.12 °C | True |
| 45 °C | 81.7 kg/h | 2088 W | +5.67 K | 0 % | 48.77 °C | True |
| 55 °C | 139.8 kg/h | 1949 W | +11.42 K | 0 % | 49.25 °C | True |
| 60 °C | 230.2 kg/h | 1873 W | +14.58 K | 0 % | 49.45 °C | True |

### Tabla 9.15 — geometrías candidatas en el punto de diseño

| Geometría | Área | Caudal de ACS | Q | Salida |
|---|---|---|---|---|
| AlfaNova 16-10H | 0.117 m² | 50.2 kg/h | 1866 W | vapor, +5.7 K |
| AlfaNova 27, 10 placas | 0.255 m² | 54.4 kg/h | 2020 W | vapor, +0.7 K |
| AlfaNova 27-30H | 0.894 m² | 65.4 kg/h | 2430 W | bifásico, x = 0.959 |

## modos

### Tabla 9.6 — residuo y validez por modo (60 segmentos, 12 volúmenes, desde la estimación por defecto)

| Modo | Residuo | Peor balance de componente | Converge | Válido | Evaluaciones | Arranque alternativo | Tiempo desde la estimación | p_k/p_0 | Δp placas / salto de saturación (M8) |
|---|---|---|---|---|---|---|---|---|---|
| M-1, ACS 35 → 67 °C | 2.6e-11 | 1.9e-11 | True | True | 59 | no | 12 s | 3.74 | 6.4 kPa / 0.15 K |
| M-2 | 1.6e-11 | 4.1e-11 | True | True | 47 | no | 6 s | 3.69 | 4.6 kPa / 0.26 K |
| M-3, ACS 35 → 67 °C | 2.6e-11 | 3.1e-09 | True | True | 68 | no | 26 s | 4.44 | 4.5 kPa / 0.09 K |
| M-4 | 1.8e-10 | 1.3e-08 | True | True | 49 | no | 17 s | 4.43 | 4.3 kPa / 0.08 K |
| M-5, ACS 15 → 52 °C | 2.2e-10 | 3.3e-11 | True | True | 40 | no | 11 s | 2.75 | 14.3 kPa / 0.26 K |

## exergia

### §9.11.2 — el ACS tiene energía y, en verano, no tiene exergía

| Caso | Calor al ACS | Exergía del ACS | Subida del COP global | η_II |
|---|---|---|---|---|
| M-1, verano, ACS 10 → 60 °C | 2471 W | -5.4 W | 25.9 % | 0.250 |
| M-3, invierno, ACS 10 → 60 °C | 3050 W | +271.1 W | 39.1 % | 0.240 |

## tabular

### §9.12.4 — residuo alcanzado con cada backend (M-2, 120 segmentos)

| Backend de los intercambiadores | Residuo | Tiempo |
|---|---|---|
| HEOS | 1.6e-11 | 6 s |
| BICUBIC&HEOS | 1.7e-12 | 4 s |

## continuacion

### §9.4.4 — coste arrancando del punto convergido vecino (aire exterior +1 K)

| Modo | Evaluaciones | Tiempo | Residuo | Converge |
|---|---|---|---|---|
| M-1, ACS 35 → 67 °C | 60 | 12.3 s | 1.2e-11 | True |
| M-2 | 53 | 6.9 s | 1.4e-11 | True |
| M-3, ACS 35 → 67 °C | 57 | 20.9 s | 9.5e-11 | True |
| M-4 | 50 | 16.7 s | 1.2e-11 | True |
| M-5, ACS 15 → 52 °C | 41 | 11.3 s | 1.3e-10 | True |

## malla_placas

### Tabla 9.12 — variación relativa de la potencia al refinar la malla (condensador 27-30H, entrada a 70 °C, condensación a 50 °C)

| Seguimiento de la frontera | 20 → 40 | 40 → 80 | 80 → 160 | 160 → 320 |
|---|---|---|---|---|
| sin | 3.2e-04 | 1.0e-04 | 5.4e-05 | 3.5e-05 |
| con | 1.4e-03 | 3.1e-04 | 1.3e-04 | 5.8e-05 |

Con seguimiento, 10 volúmenes frente a 320: 0.39 %.

### §9.5.4 — media logarítmica frente a aritmética (mismo caso)

| Volúmenes | Diferencia relativa en la potencia |
|---|---|
| 20 | 1.4e-03 |
| 40 | 3.6e-04 |
| 80 | 8.9e-05 |
| 160 | 2.2e-05 |

## residuo_entalpico

### §9.4.5 — R4 escrito sobre la entalpía de salida (M-2)

| Segmentos de la batería | |R4| alcanzado | Residuo máximo | Converge |
|---|---|---|---|
| 50 | 3.2e-12 | 6.6e-12 | True |
| 100 | 1.7e-11 | 1.7e-11 | True |
| 200 | 9.4e-12 | 9.4e-12 | True |
| 400 | 1.6e-11 | 1.6e-11 | True |

## tabular_modos

### §9.8 — backend tabular en los intercambiadores frente a HEOS (60 / 12)

| Modo | HEOS | Tabular | Factor | Diferencia en el indicador |
|---|---|---|---|---|
| M-1, ACS 35 → 67 °C | 12 s | 4 s | 3.1 | EER 9.2e-08 |
| M-2 | 6 s | 3 s | 2.1 | EER 4.1e-08 |
| M-3, ACS 35 → 67 °C | 26 s | 14 s | 1.8 | COP 3.9e-07 |
| M-4 | 17 s | 11 s | 1.6 | COP 3.2e-07 |
| M-5, ACS 15 → 52 °C | 12 s | 4 s | 2.8 | COP_global 3.7e-07 |

