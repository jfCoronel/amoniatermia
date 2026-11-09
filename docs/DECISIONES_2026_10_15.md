# Decisiones del autor del 15/10/2026: el compresor F2 pasa a polinomios UNE-EN 12900

## Motivo

La admisibilidad de un punto debe depender solo de los límites del compresor real (zona sin
límites del diagrama del fabricante, 140 °C de descarga, presiones), y no de dónde ajusta bien el
modelo. Hoy el compresor solo está validado con T₀ de −5 a 5 °C: fuera, un punto admisible es
tendencia y no predicción (46 nudos admisibles de M-2 en el capítulo 11, 11 de M-5, 7 de M-3 y 6
de M-4).

## Datos nuevos

`data/compresor_bock_f2_vap_envolvente.csv`: rejilla de 5 K en T₀ (−25 a 15 °C) y T_k (10 a 55 °C),
1450 rpm, 5 K de recalentamiento, generada por el autor con BOCK VAP 11.15.5. Bloque E: 49 puntos
en la zona sin límites; bloque F: 8 en la de refrigeración suplementaria. 23 puntos repiten el
bloque A del 29/09/2026.

## Ensayo de ampliación del modelo semiempírico (descartado)

`herramientas/compresor/ensayo_estructura.py`; resultados en
`results/compresor/ensayo_estructura_2026_10_15.jsonl`. Identificación sobre los 46 puntos del
catálogo y los 49 del bloque E (95 puntos), mismo protocolo que el §9.5.3 (w₃ = 16 en la descarga,
multiarranque S1–S5). Desviación máxima DENTRO de la muestra de identificación; N1 exige 5 % en
caudal, 8 % en potencia y 5 K en descarga.

| Estructura | Parámetros | Caudal | Potencia | Descarga | Potencia, catálogo | Descarga, catálogo | Coste |
|---|---|---|---|---|---|---|---|
| Vigente | 9 | 5.5 % | 12.7 % | 8.6 K | 7.3 % | 4.6 K | 0.1779 |
| + exponente de reexpansión libre | 10 | 5.3 % | 12.5 % | 8.3 K | 7.3 % | 4.6 K | 0.1665 |
| + fuga mezclada en la aspiración | 9 | 5.5 % | 12.7 % | 8.6 K | 7.3 % | 4.6 K | 0.1789 |
| + fuga mezclada y exponente | 10 | 5.3 % | 12.5 % | 8.4 K | 7.3 % | 4.5 K | 0.1666 |
| + las dos y η_ic con la relación de presiones | 11 | 5.2 % | 12.8 % | 8.6 K | 7.9 % | 4.7 K | 0.1615 |
| + las dos y pérdida mecánica con ΔP | 11 | 5.3 % | 12.4 % | 8.2 K | 7.2 % | 4.6 K | 0.1669 |
| Las cuatro | 12 | 5.2 % | 12.9 % | 9.1 K | 7.9 % | 4.6 K | 0.1637 |

Ninguna cumple N1 ni siquiera dentro de la muestra, de modo que no se pasa a validación cruzada.
El ajuste anula la fuga (A_leak → 0) y el término en ΔP en todas las variantes, y lleva el
exponente de reexpansión a su cota inferior. Los errores se concentran en tres zonas: T_k de 10 a
15 °C con T₀ ≥ −15 °C (potencia hasta −13 %), relaciones de presión altas con T₀ de −25 a −15 °C
(+8 a +11 %) y T₀ = 15 °C con T_k bajas (hasta +10 %). Con más datos, el ajuste además empeora el
catálogo (potencia de 4.7 a 7.3 %). Es un límite de la estructura, coherente con el ensayo del
29/09/2026 (73 puntos, 3 de 10 grupos interiores con N1).

## Decisión

El compresor se modela con los **polinomios de UNE-EN 12900** ajustados a los puntos de VAP:

- **Recalentamiento**: polinomios a 5 K. Para otro recalentamiento se conservan el rendimiento
  volumétrico, el isentrópico (potencia al eje) y un rendimiento de descarga, todos a 5 K. Se valida
  con los 46 puntos del catálogo (1 K) y el bloque B de `compresor_bock_f2_vap.csv` (1, 5 y 10 K).
- **Subenfriamiento**: no afecta al compresor.
- **Velocidad**: un juego de polinomios a 960, 1100, 1250 y 1450 rpm e interpolación cuadrática de
  los rendimientos en la velocidad; se ajusta con tres y se comprueba con la cuarta. Datos en
  `data/compresor_bock_f2_vap_velocidades.csv` (171 puntos que genera el autor).

Decisiones del plan (`PLAN_COMPRESOR_EN12900.md`), tomadas por el autor el mismo día: el
semiempírico se resume en el §9.5 como alternativa descartada (P1); R-290 y R-32 también por
polinomios en caudal y potencia (P2); incertidumbre del compresor con la banda del error de
ajuste (P3); **velocidad variable en el cálculo estacional** (P4, en contra de la recomendación,
que era solo habilitarla); puntos fuera del diagrama calculados y marcados (P5).

Abierto (antes de P2): tratar igual los compresores de R-290 y R-32 del capítulo 13 (H5); comprobar si el
diagrama de límites cambia con la velocidad; reescritura del §9.5 y de N1 en el capítulo 10.
