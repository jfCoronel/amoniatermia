# Decisiones del autor del 02/10/2026

Tomadas sobre `docs/cifras_capitulo_11.md` (revisión `7360337`), antes de redactar el
capítulo 11.

| # | Asunto | Decisión | Consecuencia |
|---|---|---|---|
| 1 | Capacidad de RS-5 (H4) | **9.52 kW, 476 g**: el equilibrio del §9.7.8 que ya publica el capítulo 9, fijado antes de ver la carga | M-1, 489 g de sistema, 1.028 del presupuesto: **H4 no se cumple** en el peor caso de la banda. Con la capacidad del punto de diseño de M-2 (10.18 kW, 509 g) quedaría en 0.961; se publica como sensibilidad, no como veredicto |
| 2 | Veredicto de H3 | **M-1 se cumple; M-3 no concluyente sobre el criterio (b), sin consecuencia de diseño** (precisado el mismo día) | M-1: margen de 5.63 K, mayor que el error de la descarga de N1 (≤ 3.8 K). M-3: margen de 1.06 K, menor que ese error, y punto de diseño no admisible. Los márgenes negativos con agua a 40 °C y aire ≤ −7 °C (−2.16 y −0.74 K) se publican como límite de operación de la recuperación. Que el criterio no se cumpla no es crítico: hay condensador aguas abajo a la misma presión, y la condensación parcial (título 0.98–0.99 con el depósito frío) es la que el §7.5.5 ya acepta como limitación declarada. Propuesta para el cap. 14: relajar (b) a título de salida ≥ 0.98 |
| 3 | Penalización entre modos (H2) | **Por servicio**: EER en frío, COP global en calor | Frío: −2.76 %, significativa (banda ±1.38 % RSS, ±2.45 % lineal); H2 no se cumple en frío en sentido estricto, aunque el COP global sube un 16 %. Calor: −0.21 %, no significativa. H2 queda parcial; el capítulo 12 completa la lectura estacional. La no admisibilidad de los puntos de diseño de calefacción se declara aparte |

## Capítulo 12: rendimiento estacional (UNE-EN 14825:2024) y ACS

| # | Asunto | Decisión | Consecuencia |
|---|---|---|---|
| 4 | Climas | **Los tres de la norma** (medio, más cálido, más frío; horas por intervalo de la propia norma) **y Sevilla, Madrid y Burgos** con los climas de referencia del CTE (B4, D3, E1; `data/clima/`) | La clase del 811/2013 y la comparación con Keymark/EPREL usan el clima medio; las ciudades, el rendimiento en España. Los ficheros CTE son el clima de referencia de la zona, no registros de la ciudad |
| 5 | Aplicaciones | **35, 45 y 55 °C** de salida de agua, con la ley de salida variable de las tablas 8 a 10 de la norma y caudal fijo | 35 y 55 °C son las que publica el mercado; 45 °C, la del diseño (fancoils). Cada intervalo se resuelve como equilibrio, no se interpola en los mapas del cap. 11 (no cubren entradas de 19 a 47 °C) |
| 6 | Intervalos no admisibles | **TOL real del equipo** (la temperatura más baja con punto admisible) y **apoyo eléctrico con COP 1** por debajo, el mecanismo de la norma | La norma exige TOL ≤ −7 °C en el clima medio, ≤ −15 °C en el frío y ≤ +2 °C en el cálido. La máquina no es admisible a −7 °C ni a 35 °C: **en el clima medio y en el frío no puede declararse según la norma**, y la clase del 811/2013 no puede asignarse. El SCOP se publica como resultado de la tesis, no como valor declarable. Sensibilidad con la variante de diseño que admite refrigeración suplementaria |
| 7 | Carga de diseño | **Pdesignh con Tbiv = TOL real** (corregida el mismo día: la propuesta inicial, la Tbiv máxima de la norma, +2 °C en el clima medio, no es la práctica del mercado, cuya mediana es Tbiv −7 °C con TOL −10 °C; `docs/cifras_mercado.md`). Pdesignc: capacidad a 35 °C con salida a 7 °C (fancoils) | Una Pdesignh por clima y aplicación, como en EPREL. La Tbiv máxima se publica como sensibilidad: da la mayor carga declarable y el mayor peso del apoyo |
| 8 | Tdesignh de las ciudades | **Percentil 99.6 %** de la temperatura horaria del clima CTE de cada zona, redondeado al entero | Criterio de diseño habitual (ASHRAE, UNE 100001) |
| 9 | ACS | **Perfil L** (Qref = 11.655 kWh/día, UNE-EN 16147), acumulador de unos 200 L a 60 °C. Lectura estacionaria: la recuperación de M-1/M-3 cubre lo que permite su potencia en cada intervalo con demanda de climatización; el resto, M-5 | COP anual de ACS y efecto sobre el COP global. No es un η_wh declarable (el ensayo de extracciones es transitorio, fuera de la tesis) |
| 10 | Desescarche | **Sin penalización** en el cálculo principal, declarado como cota superior, más una **sensibilidad** con una penalización de la literatura, citada | No se inventa un dato inexistente |
| 11 | Auxiliares (P_OFF, P_TO, P_SB, P_CK) | **Cero**, declarado como cota superior, como las bombas | — |
| 12 | ACS producida por M-5 | **M-5 a 45 °C, sin apoyo eléctrico ni choque térmico** (RS-15, cap. 7): los 60 °C los dan M-1 y M-3 cuando funcionan | El reparto anual se calcula sobre los mapas del cap. 11; la electricidad de la recuperación es el incremento de M-1/M-3 sobre M-2/M-4 en el mismo punto |

Coeficiente de degradación: el valor por defecto de la norma para aire-agua, **Cd = 0.9** (§3.1.30), sin decisión.
Nota: la norma disponible es la UNE-EN 14825:2024; el capítulo 6 cita la edición de 2022.
