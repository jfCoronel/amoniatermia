# Ejemplo resuelto de M-1 y ficha de evaporador

Generado por `notebooks/04_ejemplo_resuelto_M1.py` el 15/10/2026, revisión `37340a21b6a8362ab2d979b85ca7c0885825a3ca-dirty`, CoolProp 8.0.0, HEOS. No editar a mano.

### Estimación inicial (parámetros agrupados, 10 K en aire y 6 K en agua)

| Magnitud | Valor |
|---|---|
| T_evap (12 − 6) | 6.00 °C |
| T_cond (35 + 10) | 45.00 °C |
| A_ef | 0.4313 mm² |
| Caudal de ACS | 59.0 kg/h |
| Incógnitas efectivas | P0, Pk, m_acs |
| Residuos efectivos | R2, R4, R5 |


### Historia del lazo externo (59 evaluaciones, 15 s; ``xtol` termination condition is satisfied.`)

| Eval. | T_evap °C | T_cond °C | ṁ_ACS kg/h | A_ef mm² | R2 | R4 | R5 | máx |R| |
|---|---|---|---|---|---|---|---|---|
| 0 | 6.000 | 45.000 | 59.04 | 0.4307 | -6.88e-01 | 2.95e-03 | -7.73e-03 | 6.9e-01 |
| 1 | 6.056 | 45.075 | 59.04 | 0.4309 | -6.99e-01 | 4.38e-03 | -7.52e-03 | 7.0e-01 |
| 2 | 6.000 | 45.075 | 59.04 | 0.4295 | -6.92e-01 | 4.90e-03 | -7.51e-03 | 6.9e-01 |
| 4 | 1.237 | 43.281 | 49.97 | 0.3485 | 6.61e-03 | 2.83e-03 | 4.76e-04 | 6.6e-03 |
| 8 | 1.655 | 43.315 | 50.31 | 0.3567 | -1.07e-03 | -4.25e-04 | -4.73e-06 | 1.1e-03 |
| 12 | 1.608 | 43.315 | 50.31 | 0.3557 | -8.78e-05 | 1.12e-04 | 2.08e-08 | 1.1e-04 |
| 16 | 1.605 | 43.310 | 50.30 | 0.3557 | -2.27e-06 | -6.27e-06 | 4.15e-09 | 6.3e-06 |
| 20 | 1.605 | 43.310 | 50.30 | 0.3557 | -3.04e-07 | 7.57e-07 | 5.44e-10 | 7.6e-07 |
| 24 | 1.605 | 43.310 | 50.30 | 0.3557 | 3.50e-09 | -5.19e-08 | -4.55e-12 | 5.2e-08 |
| 28 | 1.605 | 43.310 | 50.30 | 0.3557 | -1.26e-09 | 4.83e-09 | 2.60e-11 | 4.8e-09 |
| 32 | 1.605 | 43.310 | 50.30 | 0.3557 | 7.53e-11 | -4.66e-10 | 3.43e-12 | 4.7e-10 |
| 36 | 1.605 | 43.310 | 50.30 | 0.3557 | -2.81e-11 | 1.22e-10 | -8.70e-12 | 1.2e-10 |
| 44 | 1.605 | 43.310 | 50.30 | 0.3557 | 2.33e-12 | -1.24e-11 | 2.51e-11 | 2.5e-11 |
| 58 | 1.605 | 43.310 | 50.30 | 0.3557 | 7.94e-12 | 3.26e-12 | 2.59e-11 | 2.6e-11 |


### Punto resuelto

| Magnitud | Valor |
|---|---|
| T_evap / T_cond | 1.61 / 43.31 °C |
| Caudal de refrigerante | 31.58 kg/h |
| Caudal de ACS | 50.30 kg/h |
| A_ef (forma cerrada) | 0.3557 mm² |
| Recalentamiento / subenfriamiento | 5.000 / 2.000 K |
| Q evaporador (placas 27-30H) | 9475 W |
| Q desrecalentador (ACS) | 1869 W |
| Q batería | 9770 W |
| T descarga | 123.97 °C |
| W eje / W eléctrico compresor | 2385 / 2704 W |
| η_v / η_is | 0.8413 / 0.7186 |
| T pared ficticia | nan °C |
| Q al ambiente (compresor) | 220.1 W |
| Residuos R2 / R4 / R5 | 7.9e-12 / 3.3e-12 / 2.6e-11 |
| Convergido / válido | True / True |


### Componentes

| Componente | Q | Volúmenes resueltos | Recortes | Salida secundario | Δp refrigerante | Balance |
|---|---|---|---|---|---|---|
| Desrecalentador 16-10H | -1869 W | 12 | 0 | 67.00 °C | 6021 Pa | 1.9e-11 |
| Batería CBN-21 | -9770 W | 62 | 2 | 39.06 °C (aire) | nan Pa | 1.7e-14 |
| Evaporador 27-30H | 9475 W | 13 | 1 | 6.98 °C | 387 Pa | 8.0e-12 |


### Diagnóstico por componente

| Magnitud | Valor |
|---|---|
| Batería: fracción de volumen vapor / bifásico / líquido | 0.056 / 0.920 / 0.024 |
| Batería: régimen de condensación | {'estratificado': 1.0} |
| Batería: h_aire, η_aleta, η_superficie, U medio | 113.1 W/(m²K), 0.451, 0.468, 41.9 W/(m²K) |
| Desrecalentador: pared húmeda | 0.083 |
| Desrecalentador: α refrigerante (vapor) | 748–792 W/(m²K) |
| Evaporador: título de entrada | 0.1509 |
| Evaporador: α refrigerante (bifásico → vapor) | 5835 → 19826 → 173 W/(m²K) |


### Verificaciones independientes

| Verificación | Valor |
|---|---|
| Masa | 2.0e-16 |
| Energía del sistema | 1.6e-12 |
| R3 pared del compresor | 0.0e+00 W |
| Entropía generada (mín.) | 0.464 W/K |
| Entropía por componente | compresor 1.879, desrecalentador 0.530, bateria 0.629, valvula 0.464, placas_clima 0.957 |
| Área efectiva de válvula (resultado) | 0.3557 mm² |
| Salto de saturación por Δp (M8) | desrecalentador 0.131 K, placas_clima 0.023 K |
| ok | True |


### Salidas

| Magnitud | Valor |
|---|---|
| W eléctrico total (compresor + ventilador) | 3484 W |
| EER / COP global | 2.720 / 3.256 |
| η_II / cierre exergético | 0.246 / -0.000 |
| H6: reparto entre componentes del ciclo (sin ventilador) | compresor_con_motor 53.0 %, placas_clima 17.4 %, bateria 11.5 %, desrecalentador 9.6 %, valvula 8.5 % |
| Cuota del ventilador sobre el total destruido | 31.5 % |
| Carga: homogéneo / Zivi / L-M / Rouhani-Axelsson | 236 g / 425 g / 363 g / 453 g |
| Presupuesto RS-5 (único) / peor caso de los componentes | 474 g / 95.4 % |
| Extrapolado | True |


### Marca de extrapolación

- fin/schmidt_annular: base experimental SIN DECLARAR (1 evaluaciones)
- friction/martin_vdi: base experimental SIN DECLARAR (25 evaluaciones)
- plate_boiling/additive_cooper: base experimental SIN DECLARAR (11 evaluaciones)
- singlephase/martin_vdi: base experimental SIN DECLARAR (39 evaluaciones)
- singlephase/tube_dittus_boelter: Re en [4105, 4105] fuera de [1e+04, +inf] (2 evaluaciones)
- tube_condensation/dobson_chato: d_i en [0.0123, 0.0123] fuera de [0.00314, 0.00704] (56 evaluaciones)
- tube_condensation/dobson_chato: x en [0.002865, 1] fuera de [0.1, 0.9] (12 evaluaciones)
- twophase_multiplier/lockhart_martinelli_chisholm: base experimental SIN DECLARAR (11 evaluaciones)


### Batería frente a la ficha de evaporador (ficha: 2999 W, U = 32, aire a 5.9 °C, x_salida = 1/3, seca)

| Ebullición en tubo | Segmentos | Q | Desv. | U W/(m²K) | T aire salida | x salida | Fracción húmeda |
|---|---|---|---|---|---|---|---|
| gungor_winterton | 120 | 3124 W | +4.2 % | 33.6 | 5.83 °C | 0.347 | 0.00 |
| gungor_winterton | 400 | 3137 W | +4.6 % | 33.8 | 5.83 °C | 0.348 | 0.00 |
| gungor_winterton_horizontal | 120 | 2310 W | -23.0 % | 23.2 | 6.14 °C | 0.256 | 0.00 |
| gungor_winterton_horizontal | 400 | 2318 W | -22.7 % | 23.3 | 6.13 °C | 0.257 | 0.00 |
| cooper_solo | 120 | 2130 W | -29.0 % | 21.0 | 6.20 °C | 0.236 | 0.00 |
| cooper_solo | 400 | 2135 W | -28.8 % | 21.1 | 6.20 °C | 0.237 | 0.00 |

