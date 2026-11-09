# Cifras del capítulo 12

Generado por `notebooks/07_cifras_capitulo_12.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `1b8a86aad86f69ffd55f3d01b96ac909f7151f6b`
- CoolProp 8.0.0
- Generado: 2026-10-20 15:15
- Secciones: climas, frio, calor, variante, acs, desescarche, sin_envolvente, figuras

## climas

Horas por intervalo de 1 K. Los climas de la norma, de las tablas B.1 y D.1 (la refrigeración solo tiene clima medio); las ciudades, de todas las horas del clima de referencia CTE de su zona, por debajo de 15.5 °C en calefacción y desde 16.5 °C en refrigeración. Tdesignh de las ciudades: percentil 99.6 % (decisión 8); Tbiv máxima, la del clima medio. La norma no fija TOL para las ciudades.

| Clima | Fuente | Tdesignh | Tbiv máxima | TOL exigida | Horas de calefacción | Horas de refrigeración |
|---|---|---|---|---|---|---|
| medio | UNE-EN 14825:2024, tablas B.1 y D.1, §6.3 | -10 °C | 2 °C | ≤ -7 °C | 4910 | 2602 |
| calido | UNE-EN 14825:2024, tablas B.1 y D.1, §6.3 | 2 °C | 7 °C | ≤ 2 °C | 3590 | — |
| frio | UNE-EN 14825:2024, tablas B.1 y D.1, §6.3 | -22 °C | -7 °C | ≤ -15 °C | 6446 | — |
| Sevilla | CTE DB-HE, clima de referencia B4 (zonaB4.met) | 3 °C | 3 °C | — | 3785 | 4503 |
| Madrid | CTE DB-HE, clima de referencia D3 (zonaD3.met) | -3 °C | 2 °C | — | 5347 | 3105 |
| Burgos | CTE DB-HE, clima de referencia E1 (zonaE1.met) | -4 °C | 2 °C | — | 6380 | 2027 |


## frio

Velocidad variable (decisión P4 del 15/10/2026): A a la velocidad máxima; B, C y D a la velocidad cuya capacidad iguala la carga parcial de la norma, o a la mínima (960 rpm) con marcha/paro si aun así la supera. Caudal fijo del ensayo A (12/7 °C): 0.4926 kg/s. Pdesignc = potencia en A, 10340 W. Cd = 0.9; sin auxiliares (cota superior); η_s,c = SEER/2.5 − 3 %. Ventilador a caudal y consumo constantes (decisión V3).

| Condición | Aire | Agua entrada / salida | Potencia frigorífica | EER | Velocidad | Régimen | Descarga | Zona | Admisible |
|---|---|---|---|---|---|---|---|---|---|
| A | 35 °C | 12.00 / 7.00 °C | 10340 W | 2.809 | 1450 rpm | plena | 123.5 °C | sin_limites | sí |
| B | 30 °C | 10.73 / 7.00 °C | 7709 W | 3.191 | 960 rpm | minima | 98.0 °C | sin_limites | sí |
| C | 25 °C | 10.90 / 7.00 °C | 8070 W | 3.598 | 960 rpm | minima | 85.3 °C | sin_limites | sí |
| D | 20 °C | 11.07 / 7.00 °C | 8422 W | 4.039 | 960 rpm | minima | 73.8 °C | sin_limites | sí |

| Clima | SEER | η_s,c | Demanda anual | SEER a velocidad fija (marcha/paro a 1450 rpm) |
|---|---|---|---|---|
| medio | 3.179 | 124.2 % | 9864 kWh | 2.967 |
| Sevilla | 3.128 | 122.1 % | 18147 kWh | 2.937 |
| Madrid | 3.157 | 123.3 % | 12583 kWh | 2.959 |
| Burgos | 3.128 | 122.1 % | 5807 kWh | 2.865 |


## calor

Velocidad variable (decisión P4 del 15/10/2026): TOL real, Tbiv y Pdesignh con los puntos a la velocidad máxima; en cada punto de la norma por encima de la TOL, el equipo a la velocidad cuya capacidad iguala la carga parcial, o a la mínima (960 rpm) con marcha/paro si aun así la supera. Motor y transmisión con rendimiento constante y ventilador a caudal y consumo constantes (decisiones V2 y V3). TOL real: la temperatura entera más baja desde la que todos los puntos son admisibles (solo la zona sin límites del diagrama y descarga ≤ 140 °C). Por debajo, apoyo eléctrico con COP 1. Pdesignh con Tbiv = TOL real, como declara el mercado (decisión 7 corregida el 02/10/2026); la Tbiv máxima de la norma, como sensibilidad. Cd = 0.9; sin desescarche ni auxiliares: cota superior. η_s,h = SCOP/2.5 − 3 %. Caudales fijos del ensayo nominal A7/6: 35 °C 0.5342 kg/s, 45 °C 0.5178 kg/s, 55 °C 0.3189 kg/s.

| Aplicación | Clima | TOL real | TOL de la norma | Tbiv | Pdesignh | SCOP | η_s,h | Calor del apoyo | SCOP con Tbiv máxima (velocidad máxima) | SCOP a velocidad fija |
|---|---|---|---|---|---|---|---|---|---|---|
| 35 °C | medio | -3 °C | no | -3 °C | 10.77 kW | 2.591 | 101 % | 10.4 % | 2.427 (Tbiv 2 °C) | 2.574 |
| 35 °C | calido | 2 °C | sí | 2 °C | 9.39 kW | 3.529 | 138 % | 0.0 % | 3.477 (Tbiv 7 °C) | 3.384 |
| 35 °C | frio | -6 °C | no | -6 °C | 12.22 kW | 2.191 | 85 % | 18.7 % | 2.186 (Tbiv -6 °C) | 2.186 |
| 35 °C | Sevilla | 3 °C | — | 3 °C | 9.73 kW | 3.576 | 140 % | 1.7 % | 3.460 (Tbiv 3 °C) | 3.460 |
| 35 °C | Madrid | -2 °C | — | -2 °C | 8.56 kW | 3.132 | 122 % | 2.2 % | 3.129 (Tbiv 2 °C) | 3.068 |
| 35 °C | Burgos | -2 °C | — | -2 °C | 9.04 kW | 2.924 | 114 % | 4.7 % | 2.805 (Tbiv 2 °C) | 2.889 |
| 45 °C | medio | 1 °C | no | 1 °C | 15.50 kW | 1.875 | 72 % | 31.7 % | 1.860 (Tbiv 2 °C) | 1.865 |
| 45 °C | calido | 5 °C | no | 5 °C | 12.96 kW | 2.976 | 116 % | 5.8 % | 2.903 (Tbiv 7 °C) | 2.902 |
| 45 °C | frio | -1 °C | no | -1 °C | 18.79 kW | 1.541 | 59 % | 48.0 % | 1.541 (Tbiv -1 °C) | 1.541 |
| 45 °C | Sevilla | 5 °C | — | 5 °C | 12.14 kW | 3.032 | 118 % | 7.4 % | 2.958 (Tbiv 5 °C) | 2.958 |
| 45 °C | Madrid | 2 °C | — | 2 °C | 12.63 kW | 2.386 | 92 % | 16.4 % | 2.359 (Tbiv 2 °C) | 2.359 |
| 45 °C | Burgos | 2 °C | — | 2 °C | 13.29 kW | 1.996 | 77 % | 27.9 % | 1.982 (Tbiv 2 °C) | 1.982 |
| 55 °C | medio | 3 °C | no | 3 °C | 19.05 kW | 1.557 | 59 % | 47.9 % | 1.553 (Tbiv 3 °C) | 1.553 |
| 55 °C | calido | 8 °C | no | 8 °C | 19.79 kW | 2.104 | 81 % | 26.7 % | 2.083 (Tbiv 8 °C) | 2.083 |
| 55 °C | frio | 1 °C | no | 1 °C | 22.71 kW | 1.334 | 50 % | 63.3 % | 1.332 (Tbiv 1 °C) | 1.332 |
| 55 °C | Sevilla | 6 °C | — | 6 °C | 13.80 kW | 2.787 | 108 % | 11.3 % | 2.733 (Tbiv 6 °C) | 2.733 |
| 55 °C | Madrid | 3 °C | — | 3 °C | 13.92 kW | 2.095 | 81 % | 24.1 % | 2.080 (Tbiv 3 °C) | 2.080 |
| 55 °C | Burgos | 3 °C | — | 3 °C | 14.66 kW | 1.730 | 66 % | 38.6 % | 1.722 (Tbiv 3 °C) | 1.722 |

### Puntos del clima medio a 35 °C

| Aire | Agua entrada / salida | Carga | Potencia | COP | Velocidad | Régimen | Descarga | Zona | Admisible |
|---|---|---|---|---|---|---|---|---|---|
| -3 °C | 28.70 / 32.22 °C | 7868 W | 7868 W | 2.794 | 1450 rpm | plena | 135.3 °C | sin_limites | sí |
| 2 °C | 26.94 / 29.98 °C | 5797 W | 6793 W | 3.150 | 960 rpm | minima | 104.6 °C | sin_limites | sí |
| 7 °C | 23.31 / 27.00 °C | 3727 W | 8248 W | 3.891 | 960 rpm | minima | 84.6 °C | sin_limites | sí |
| 12 °C | 19.57 / 24.00 °C | 1656 W | 9888 W | 4.835 | 960 rpm | minima | 68.7 °C | sin_limites | sí |

### Puntos del clima medio a 55 °C

| Aire | Agua entrada / salida | Carga | Potencia | COP | Velocidad | Régimen | Descarga | Zona | Admisible |
|---|---|---|---|---|---|---|---|---|---|
| 3 °C | 33.65 / 40.80 °C | 9526 W | 9526 W | 2.901 | 1450 rpm | plena | 139.7 °C | sin_limites | sí |
| 7 °C | 30.04 / 36.00 °C | 6595 W | 7943 W | 3.338 | 960 rpm | minima | 106.5 °C | sin_limites | sí |
| 12 °C | 22.74 / 30.00 °C | 2931 W | 9680 W | 4.362 | 960 rpm | minima | 80.4 °C | sin_limites | sí |


## variante

Sensibilidad (decisión 6): la misma máquina con tapa de cilindro refrigerada, en que la zona de refrigeración suplementaria del diagrama también es admisible; se mantiene el límite de 140 °C.

| Aplicación | Clima | TOL real | TOL de la norma | Tbiv | Pdesignh | SCOP | η_s,h | Calor del apoyo | SCOP con Tbiv máxima (velocidad máxima) | SCOP a velocidad fija |
|---|---|---|---|---|---|---|---|---|---|---|
| 35 °C | medio | -3 °C | no | -3 °C | 10.77 kW | 2.591 | 101 % | 10.4 % | 2.427 (Tbiv 2 °C) | 2.574 |
| 35 °C | calido | 2 °C | sí | 2 °C | 9.39 kW | 3.529 | 138 % | 0.0 % | 3.477 (Tbiv 7 °C) | 3.384 |
| 35 °C | frio | -6 °C | no | -6 °C | 12.22 kW | 2.191 | 85 % | 18.7 % | 2.186 (Tbiv -6 °C) | 2.186 |
| 35 °C | Sevilla | 3 °C | — | 3 °C | 9.73 kW | 3.576 | 140 % | 1.7 % | 3.460 (Tbiv 3 °C) | 3.460 |
| 35 °C | Madrid | -2 °C | — | -2 °C | 8.56 kW | 3.132 | 122 % | 2.2 % | 3.129 (Tbiv 2 °C) | 3.068 |
| 35 °C | Burgos | -2 °C | — | -2 °C | 9.04 kW | 2.924 | 114 % | 4.7 % | 2.805 (Tbiv 2 °C) | 2.889 |
| 45 °C | medio | 1 °C | no | 1 °C | 15.50 kW | 1.875 | 72 % | 31.7 % | 1.860 (Tbiv 2 °C) | 1.865 |
| 45 °C | calido | 5 °C | no | 5 °C | 12.96 kW | 2.976 | 116 % | 5.8 % | 2.903 (Tbiv 7 °C) | 2.902 |
| 45 °C | frio | -1 °C | no | -1 °C | 18.79 kW | 1.541 | 59 % | 48.0 % | 1.541 (Tbiv -1 °C) | 1.541 |
| 45 °C | Sevilla | 5 °C | — | 5 °C | 12.14 kW | 3.032 | 118 % | 7.4 % | 2.958 (Tbiv 5 °C) | 2.958 |
| 45 °C | Madrid | 2 °C | — | 2 °C | 12.63 kW | 2.386 | 92 % | 16.4 % | 2.359 (Tbiv 2 °C) | 2.359 |
| 45 °C | Burgos | 2 °C | — | 2 °C | 13.29 kW | 1.996 | 77 % | 27.9 % | 1.982 (Tbiv 2 °C) | 1.982 |
| 55 °C | medio | 3 °C | no | 3 °C | 19.05 kW | 1.557 | 59 % | 47.9 % | 1.553 (Tbiv 3 °C) | 1.553 |
| 55 °C | calido | 8 °C | no | 8 °C | 19.79 kW | 2.104 | 81 % | 26.7 % | 2.083 (Tbiv 8 °C) | 2.083 |
| 55 °C | frio | 1 °C | no | 1 °C | 22.71 kW | 1.334 | 50 % | 63.3 % | 1.332 (Tbiv 1 °C) | 1.332 |
| 55 °C | Sevilla | 6 °C | — | 6 °C | 13.80 kW | 2.787 | 108 % | 11.3 % | 2.733 (Tbiv 6 °C) | 2.733 |
| 55 °C | Madrid | 3 °C | — | 3 °C | 13.92 kW | 2.095 | 81 % | 24.1 % | 2.080 (Tbiv 3 °C) | 2.080 |
| 55 °C | Burgos | 3 °C | — | 3 °C | 14.66 kW | 1.730 | 66 % | 38.6 % | 1.722 (Tbiv 3 °C) | 1.722 |


## acs

Perfil L (Qref = 11.655 kWh/día, UNE-EN 16147), demanda repartida por igual en las 8760 h. La recuperación de M-3 (calefacción a 45 °C) y de M-1 (frío) aporta su potencia de ACS por la fracción de tiempo en marcha, con el tope de la demanda de cada hora; el resto lo produce M-5 a 45 °C sin apoyo eléctrico (RS-15). La recuperación se resuelve en los puntos de carga parcial, a la velocidad de cada uno (decisión V5), e interpola entre ellos como la norma con el COP; M-5, de los mapas del capítulo 11 (recalentamiento 5 K, subenfriamiento 2 K). La electricidad de la recuperación es el incremento de M-1/M-3 sobre M-2/M-4 en el mismo punto, negativo en frío porque el desrecalentador baja la condensación. Lectura estacionaria de orden de magnitud: no es un η_wh declarable.

| Clima | Demanda | Recuperada | Por M-5 | COP medio de M-5 | Electricidad de la recuperación | Electricidad del ACS | SPF del ACS | Puntos de recuperación no válidos (excluidos) |
|---|---|---|---|---|---|---|---|---|
| medio | 4254 kWh | 51.2 % | 2075 kWh | 3.55 | +14 kWh | 598 kWh | 7.11 | — |
| calido | 4254 kWh | 29.5 % | 3000 kWh | 3.51 | +58 kWh | 912 kWh | 4.66 | calor 7 °C |
| frio | 4254 kWh | 41.0 % | 2509 kWh | 3.52 | +65 kWh | 778 kWh | 5.47 | — |
| Sevilla | 4254 kWh | 55.9 % | 1876 kWh | 3.53 | -4 kWh | 527 kWh | 8.07 | — |
| Madrid | 4254 kWh | 61.9 % | 1621 kWh | 3.53 | +24 kWh | 484 kWh | 8.80 | — |
| Burgos | 4254 kWh | 56.0 % | 1872 kWh | 3.52 | +59 kWh | 591 kWh | 7.20 | — |


## desescarche

COP de los intervalos con aire ≤ 5 °C multiplicado por 0.9: pérdida de un ciclo de escarcha y desescarche frente al régimen seco, 7.25 a 9.85 % según la impulsión (Wang et al., Building and Environment, 2024, doi:10.1016/j.buildenv.2024.112258). La potencia no se penaliza.

| Aplicación | Clima | SCOP sin desescarche | SCOP con desescarche | Cambio |
|---|---|---|---|---|
| 35 °C | medio | 2.591 | 2.453 | -5.3 % |
| 35 °C | calido | 3.529 | 3.489 | -1.1 % |
| 35 °C | frio | 2.191 | 2.075 | -5.3 % |
| 35 °C | Sevilla | 3.576 | 3.536 | -1.1 % |
| 35 °C | Madrid | 3.132 | 2.972 | -5.1 % |
| 35 °C | Burgos | 2.924 | 2.758 | -5.7 % |
| 45 °C | medio | 1.875 | 1.826 | -2.6 % |
| 45 °C | calido | 2.976 | 2.963 | -0.4 % |
| 45 °C | frio | 1.541 | 1.507 | -2.2 % |
| 45 °C | Sevilla | 3.032 | 3.019 | -0.4 % |
| 45 °C | Madrid | 2.386 | 2.317 | -2.9 % |
| 45 °C | Burgos | 1.996 | 1.947 | -2.4 % |
| 55 °C | medio | 1.557 | 1.536 | -1.3 % |
| 55 °C | calido | 2.104 | 2.104 | +0.0 % |
| 55 °C | frio | 1.334 | 1.318 | -1.2 % |
| 55 °C | Sevilla | 2.787 | 2.787 | +0.0 % |
| 55 °C | Madrid | 2.095 | 2.052 | -2.1 % |
| 55 °C | Burgos | 1.730 | 1.703 | -1.5 % |


## sin_envolvente

Escenario del autor (20/10/2026): un compresor que, fuera de la envolvente del fabricante, sigue la tendencia de sus datos. Todo punto válido es admisible —sin diagrama de aplicación ni límite de 140 °C— y los polinomios de UNE-EN 12900 extrapolan. Misma carga de diseño que el caso base (la misma vivienda) y velocidad variable; la columna de velocidad fija es la que entra en H5 (cap. 13). Los puntos fuera de la envolvente son los de la velocidad máxima fuera de la zona sin límites o por encima de 140 °C, con la mayor descarga entre ellos.

| Aplicación | Clima | TOL base / sin envolvente | Pdesignh | SCOP base | SCOP sin envolvente | Diferencia | η_s,h | Calor del apoyo (base / sin env.) | SCOP a velocidad fija | Puntos fuera (descarga máx.) |
|---|---|---|---|---|---|---|---|---|---|---|
| 35 °C | medio | -3 / -10 °C | 10.77 kW | 2.591 | 2.867 | +10.6 % | 112 % | 10.4 / 4.1 % | 2.960 | 2 (178 °C) |
| 35 °C | calido | 2 / 2 °C | 9.39 kW | 3.529 | 3.529 | +0.0 % | 138 % | 0.0 / 0.0 % | 3.384 | 0 (nan °C) |
| 35 °C | frio | -6 / -22 °C | 12.22 kW | 2.191 | 2.556 | +16.6 % | 99 % | 18.7 / 6.9 % | 2.558 | 2 (274 °C) |
| 35 °C | Sevilla | 3 / 3 °C | 9.73 kW | 3.576 | 3.576 | +0.0 % | 140 % | 1.7 / 1.7 % | 3.460 | 0 (nan °C) |
| 35 °C | Madrid | -2 / -3 °C | 8.56 kW | 3.132 | 3.190 | +1.9 % | 125 % | 2.2 / 1.2 % | 3.143 | 1 (145 °C) |
| 35 °C | Burgos | -2 / -4 °C | 9.04 kW | 2.924 | 3.065 | +4.8 % | 120 % | 4.7 / 2.1 % | 3.106 | 1 (149 °C) |
| 45 °C | medio | 1 / -10 °C | 15.50 kW | 1.875 | 2.440 | +30.2 % | 95 % | 31.7 / 11.3 % | 2.513 | 2 (222 °C) |
| 45 °C | calido | 5 / 2 °C | 12.96 kW | 2.976 | 3.156 | +6.1 % | 123 % | 5.8 / 2.8 % | 3.202 | 1 (159 °C) |
| 45 °C | frio | -1 / -22 °C | 18.79 kW | 1.541 | 1.956 | +26.9 % | 75 % | 48.0 / 23.7 % | 2.138 | 2 (337 °C) |
| 45 °C | Sevilla | 5 / 3 °C | 12.14 kW | 3.032 | 3.241 | +6.9 % | 127 % | 7.4 / 4.0 % | 3.265 | 1 (155 °C) |
| 45 °C | Madrid | 2 / -3 °C | 12.63 kW | 2.386 | 2.919 | +22.3 % | 114 % | 16.4 / 4.2 % | 2.879 | 1 (180 °C) |
| 45 °C | Burgos | 2 / -4 °C | 13.29 kW | 1.996 | 2.697 | +35.1 % | 105 % | 27.9 / 7.0 % | 2.672 | 1 (185 °C) |
| 55 °C | medio | 3 / -10 °C | 19.05 kW | 1.557 | 2.204 | +41.6 % | 85 % | 47.9 / 16.8 % | 2.222 | 3 (264 °C) |
| 55 °C | calido | 8 / 2 °C | 19.79 kW | 2.104 | 2.811 | +33.6 % | 109 % | 26.7 / 8.2 % | 2.817 | 2 (188 °C) |
| 55 °C | frio | 1 / -22 °C | 22.71 kW | 1.334 | 1.868 | +40.1 % | 72 % | 63.3 / 27.1 % | 1.934 | 2 (379 °C) |
| 55 °C | Sevilla | 6 / 3 °C | 13.80 kW | 2.787 | 3.130 | +12.3 % | 122 % | 11.3 / 5.1 % | 3.156 | 1 (183 °C) |
| 55 °C | Madrid | 3 / -3 °C | 13.92 kW | 2.095 | 2.686 | +28.2 % | 104 % | 24.1 / 7.0 % | 2.697 | 2 (214 °C) |
| 55 °C | Burgos | 3 / -4 °C | 14.66 kW | 1.730 | 2.443 | +41.3 % | 95 % | 38.6 / 11.0 % | 2.455 | 2 (220 °C) |


## figuras

Figuras escritas en `docs/figuras`: fig_12_1_potencia_carga, fig_12_2_mercado (png y pdf).
