# Referencia de mercado

Generado por `notebooks/08_referencia_mercado.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `219e7f047b83151b86835caa139bff7510ed449f`
- CoolProp 8.0.0
- Generado: 2026-10-02 11:43
- Secciones: muestra, distribuciones

## muestra

Fuente: hplib, base de datos de bombas de calor extraída del Heat Pump Keymark, DOI 10.5281/zenodo.5521597, CC BY 4.0; commit d932c52 (10/2024). Criterio: aire-agua exterior, R-32 o R-290, 6–12 kW nominales a baja temperatura; filas duplicadas eliminadas. Limitaciones: Datos del Keymark a octubre de 2024; no recoge certificaciones posteriores.; No distingue monobloc de split ni declara la reversibilidad; el SEER es opcional en el Keymark.; Sin P_designc; EER_c_ref es el del punto A de EN 14825 (35 °C), no el ensayo A35W7 de EN 14511.; SCOP a 55 °C solo vía η_s (SCOP = (η_s + 3)·2.5/100).

| Refrigerante | Modelos | Fabricantes | Con SEER declarado |
|---|---|---|---|
| R32 | 3121 | 128 | 1260 |
| R290 | 555 | 81 | 74 |


## distribuciones

Percentiles de la muestra en el clima medio (el de la clase del 811/2013). El SCOP a 35 y 55 °C se deduce de η_s con CC = 2.5 y F(1) = 3 %. La carga específica se refiere a la potencia nominal de calefacción a 35 °C; la de H4 se refiere a la capacidad frigorífica, de modo que no son directamente comparables sin declararlo.

| Magnitud | Refrigerante | n | P10 | P25 | Mediana | P75 | P90 |
|---|---|---|---|---|---|---|---|
| η_s a 35 °C [%] | R32 | 3121 | 176 | 178 | 183 | 191 | 199 |
| η_s a 35 °C [%] | R290 | 555 | 176 | 185 | 190 | 196 | 203 |
| η_s a 55 °C [%] | R32 | 3121 | 127 | 130 | 133 | 138 | 141 |
| η_s a 55 °C [%] | R290 | 555 | 134 | 139 | 143 | 150 | 154 |
| SCOP a 35 °C (de η_s) | R32 | 3121 | 4.47 | 4.53 | 4.65 | 4.85 | 5.05 |
| SCOP a 35 °C (de η_s) | R290 | 555 | 4.47 | 4.7 | 4.83 | 4.97 | 5.15 |
| SCOP a 55 °C (de η_s) | R32 | 3121 | 3.25 | 3.33 | 3.4 | 3.52 | 3.6 |
| SCOP a 55 °C (de η_s) | R290 | 555 | 3.42 | 3.55 | 3.65 | 3.83 | 3.92 |
| SEER a 7 °C | R32 | 1260 | 4.04 | 4.43 | 5.31 | 5.66 | 5.76 |
| SEER a 7 °C | R290 | 74 | 3.96 | 4.5 | 5.04 | 5.28 | 5.34 |
| EER en el punto A (35 °C) | R32 | 1260 | 2.8 | 2.95 | 3.1 | 3.23 | 3.32 |
| EER en el punto A (35 °C) | R290 | 74 | 2.7 | 2.82 | 3 | 3.06 | 3.61 |
| Carga [kg] | R32 | 3121 | 1.2 | 1.4 | 1.6 | 1.84 | 3.25 |
| Carga [kg] | R290 | 555 | 0.76 | 0.87 | 1.05 | 1.25 | 1.7 |
| Carga específica [g/kW de calor nominal] | R32 | 3121 | 144 | 159 | 188 | 233 | 345 |
| Carga específica [g/kW de calor nominal] | R290 | 555 | 91.5 | 104 | 118 | 147 | 185 |
| TOL declarada [°C] | R32 | 3121 | -20 | -10 | -10 | -10 | -10 |
| TOL declarada [°C] | R290 | 555 | -25 | -10 | -10 | -10 | -10 |
| Tbiv declarada [°C] | R32 | 3121 | -10 | -7 | -7 | -7 | -7 |
| Tbiv declarada [°C] | R290 | 555 | -10 | -7 | -7 | -7 | -7 |

