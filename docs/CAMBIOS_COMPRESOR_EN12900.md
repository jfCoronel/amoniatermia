# Cambios de cifras y veredictos por el compresor de UNE-EN 12900 (fase C)

15/10/2026. Ningún veredicto cambia. Antes: compresor semiempírico identificado sobre 46 puntos (hojas en `a426e07`). Ahora:
polinomios de UNE-EN 12900 sobre 228 puntos de VAP a cuatro velocidades y, en el cálculo estacional,
velocidad variable (decisión P4). Hojas regeneradas en esta revisión: `docs/cifras_*.md`.

## Veredictos de las hipótesis

| Hipótesis | Antes | Ahora | ¿Cambia? |
|---|---|---|---|
| H1 | Componente: compresor N1 en su dominio (T₀ −5 a 5 °C); batería +4.2 %; sistema no contrastable | Componente: compresor N1 en toda su envolvente (0.67 %, 0.83 %, 1.65 K frente a puntos no usados); batería +4.2 %; sistema no contrastable | No (se refuerza) |
| H2 | Parcial y geográfica; frío −2.8 % (significativo); calor −0.21 % (no) | Parcial y geográfica; frío −2.3 % (significativo, banda ±1.33/±2.25 %); calor −0.16 % (no) | No |
| H3 | M-1 se cumple (5.63 K); M-3 no concluyente (1.06 K < 3.8 K de error) | M-1 se cumple (5.62 K, error 1.65 K); M-3 no concluyente (1.06 K < 1.65 K) | No |
| H4 | No, en el límite: 489 g, 1.028 de 476 g | No, en el límite: 490 g, 1.032 de 474 g | No |
| H5 | No (SCOP −6 a −32 % en el clima medio; SEER +16 % y +3.8 %) | No, a velocidad fija para los tres fluidos (V4): SCOP −10 a −33 %, todas significativas (la de −10.1 % frente al R-290 por poco, banda ±9.1 %); SEER +15.2 % (significativo) y +2.6 % (dentro de la banda) | No |
| H6 | M-1 a M-4 (51–60 %); no en M-5 | M-1 a M-4 (51–58 %); no en M-5 (placas 34.7 % frente a 33.4 %) | No |
| H7 | No en el clima medio (25–35 % mayor); Sevilla a < 2 % del R-32 | No en el clima medio (25–35 % mayor); Sevilla a < 4 % del R-32; Madrid y Burgos empeoran (TOL +1 K a 45 °C) | No |

## Cifras principales

| Magnitud | Antes | Ahora |
|---|---|---|
| Capacidad del equilibrio de M-2 (§9.7.8) / presupuesto de RS-5 | 9.52 kW / 476 g | 9.49 kW / 474 g |
| Descarga en el equilibrio de M-2 | 120.0 °C | 121.5 °C |
| Diseño M-1: EER / COP global / descarga | 2.713 / 3.238 / 122.3 °C | 2.720 / 3.256 / 124.0 °C |
| Diseño M-2: EER / descarga | 2.791 / 122.9 °C | 2.783 / 124.1 °C |
| Diseño M-3, M-4: descarga | 140.8, 140.5 °C (no admisibles por < 1 K) | 143.6, 143.3 °C (no admisibles por > 3 K, sin depender de Φ) |
| Diseño M-5: COP global (fuera de la envolvente) | 4.70 | 4.56 |
| Dominio de validez del compresor | T₀ de −5 a 5 °C, T_k 15–50 °C, 1450 rpm | Su envolvente (zonas sin límites y refrigeración suplementaria), 960–1450 rpm, 1–10 K |
| Nudos de la campaña válidos / admisibles fuera del dominio | 588 / — | 592 / 0 |
| Incertidumbre: factor dominante | η_motor·η_trans 6.3–6.5 % | η_motor·η_trans 6.3–6.6 % |
| Factor del compresor en la incertidumbre | Juegos S3, S4: ≤ 0.2 % (1.2 % en M-5) | Banda de ajuste: 0.7–1.2 % en el indicador, 1.4 K |
| SEER clima medio | 2.95 | 3.18 (velocidad variable); 2.97 a velocidad fija |
| SCOP clima medio 35 / 45 / 55 °C | 2.65 / 1.86 / 1.55 | 2.59 / 1.88 / 1.56 |
| TOL real clima medio 35 / 45 / 55 °C | −4 / +1 / +3 °C | −3 / +1 / +3 °C |
| Variante con tapa refrigerada | baja la TOL 1–2 K, SCOP +8 % | no cambia nada: manda siempre el límite de 140 °C |
| Margen técnico del compresor (H6) | 0.5–3.8 % | 0.7–2.6 % |
| Cap. 13: factor de cilindrada R-290 / R-32 | 1.074 / 0.939 | 1.077 / 0.939 |
| Cap. 13: R-290 en M-3 y M-5 | no válidos (residuo 2·10⁻⁵) | válidos; M-3 admisible (COP 2.20, ACS 1.82 kW) |
| Cap. 13: puntos estacionales no válidos | 8 (7 R-290, 1 R-32) | 2 (R-290) |
| Cap. 13: SCOP clima medio 35/45/55 °C, R-717 / R-290 / R-32 | 2.65/1.86/1.55 · 2.81/2.55/2.27 · 3.06/2.72/2.27 | 2.57/1.87/1.55 · 2.86/2.56/2.27 · 3.17/2.73/2.33 (velocidad fija) |
| Cap. 13: SEER clima medio R-717 / R-290 / R-32 | 2.95 / 2.53 / 2.84 | 2.97 / 2.58 / 2.89 (velocidad fija; R-717 variable 3.18) |
| Cap. 13: TEWI clima medio, β = 0.15 | 47.0 / 37.5 / 35.2 t | 46.1 / 36.8 / 34.5 t |
| Cap. 13: mayor descarga admisible del R-32 en el estacional | 137 °C | 139 °C |

## Lo que cambia de lectura

- El compresor deja de ser una limitación del modelo: todo punto admisible es predicción.
- En calefacción, la inadmisibilidad del diseño ya no depende del factor de alargamiento de las placas.
- La velocidad variable del compresor seleccionado modula solo entre dos tercios y la plena carga: mejora el
  SEER un 7 % y el SCOP como mucho un 4 %, y no cambia la TOL, que fija la descarga a plena velocidad.
- La TOL empeora 1 K en algunos casos (clima medio a 35 °C, Madrid y Burgos a 45 °C) porque la descarga
  predicha es algo mayor.
