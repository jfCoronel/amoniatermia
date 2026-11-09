# Decisiones del autor del 01/10/2026

| # | Asunto | Decisión | Consecuencia |
|---|---|---|---|
| 1 | Presupuesto de RS-5 (H4) | **Aplicar el texto** del cap. 1 y del §8.5.2: un solo presupuesto, 50 g/kW sobre la capacidad del equilibrio de refrigeración que calcula el modelo. Cada modo compara su carga con ese número. La fracción referida a la capacidad del propio modo se publica aparte, solo como información | `indicators.presupuesto_RS5` recalcula el equilibrio del §9.7.8 (9.52 kW, 476 g). DISCREPANCIA declarada: el sistema completo en el punto de diseño de M-2 entrega 10.18 kW (509 g); el capítulo debe decir de cuál de los dos equilibrios se trata |
| 2 | Alcance de H4 | **Puntos de diseño**, en el modo más desfavorable, como en la decisión 3a. La campaña factorial es **sensibilidad** y no cambia el veredicto | Sección `diseno` del cuaderno 06 (veredicto) y sección `h4` (sensibilidad) |
| 3 | H3 en calor | **M-3 con el caudal de climatización de M-4** (0.5 kg/s) en una subcampaña de 15 nudos, para que la diferencia sea solo la recuperación | Superada por el caudal único (decisión 5): M-3 y M-4 comparten ya 0.45 kg/s y H3 se lee sobre sus dos campañas; la subcampaña se retiró del cuaderno 06 |
| 4 | Margen de H6 | **Cotas propias**. Termodinámica: la exergía destruida en el compresor con su motor. Técnica: el mismo compresor con el mejor η_is de su catálogo (0.732, a 5/40 °C). Ambas de primer orden, sobre la potencia eléctrica | `indicators.margen_compresor` y `eta_is_catalogo` |

C11-8 (penalización entre modos): la banda se calcula sobre la DIFERENCIA, aplicando cada
perturbación de C10-7 y C10-8 a los dos modos a la vez (`uncertainty.bandas_diferencia`).
Se publican dos lecturas:

- **En frío**, la del EER. El ACS es un subproducto, y en M-2 el desrecalentador trabaja
  como evaporador adicional.
- **En calor**, la del COP global. El ACS se lleva parte del mismo calor, de modo que el
  COP de climatización baja por construcción.

## Caudal de climatización único (01/10/2026)

| # | Asunto | Decisión | Consecuencia |
|---|---|---|---|
| 5 | Caudal del circuito de climatización | **0.45 kg/s en M-1 a M-4**, el mismo en todos los modos: el circuito de fancoils tiene una sola bomba. Es el de frío, que da W12/7 en el punto de diseño de M-1. Dato único en `data/circuitos_agua.yaml` (`data.caudal_climatizacion()`) | Antes, 0.35 kg/s en M-3 y 0.5 kg/s en M-4, fijados en cada cuaderno. **Sustituye a la decisión 3**: M-3 y M-4 comparten ya el caudal y la subcampaña de M-3 con el caudal de M-4 repite la de M-3. Cambian las cifras de calefacción de los capítulos 9, 10 y 11 (en M-3 de diseño, el margen del desrecalentador pasa de 0.31 a 1.06 K) |
| 6 | Caudal de aire de la batería | **7 600 m³/h en volumen en todos los modos** (ficha y catálogo del ventilador; `ventilador.caudal_m3_h`). `Boundary` deduce el caudal másico con la densidad psicrométrica del aire de entrada; antes los cuadernos fijaban 8 613 kg/h en todos los modos, que es la masa de esos 7 600 m³/h a 35 °C | En frío no cambia (8 615 kg/h). En calefacción con aire a 7 °C pasa a 9 545 kg/h (+10.8 %); en M-5, a 8 721 kg/h. Cambian las cifras de M-3, M-4 y M-5 |
| 7 | Rendimiento del motor del compresor | **η_motor = 0.90** (antes 0.97), valor usual de un motor asíncrono IE4 de 2.2–3 kW; con η_trans = 0.98, producto **0.882** (antes 0.951). Rango de incertidumbre del producto, **0.82–0.89** (motor IE3 a IE4 de 2.2–3 kW según IEC 60034-30-1, por transmisión de 0.95 a 0.98) | Solo cambia la potencia eléctrica del compresor (×1.078): EER, COP, η_II y el reparto de exergía de H6. El ciclo no cambia |
| 8 | Identificación del compresor en el capítulo 9 | **Un único juego de parámetros**, el adoptado del 24/09/2026; la figura 9.3 deja de mostrar el juego anterior y sus bandas pasan a ser los criterios de N1 | Cuaderno 02 |
