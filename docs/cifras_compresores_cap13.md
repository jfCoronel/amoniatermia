# Identificación de los compresores del capítulo 13

Generado por `notebooks/09_identificacion_compresores.py`. **No editar a mano**: se vuelve a ejecutar cuando el modelo cambia.

- Revisión del código: `37340a21b6a8362ab2d979b85ca7c0885825a3ca`
- CoolProp 8.0.0
- Generado: 2026-10-15 12:52
- Secciones: polinomios, identificacion

## polinomios

Polinomios de UNE-EN 12900 (diez coeficientes, t0 y tc en °C) a una velocidad, como el F2 (decisión P2 del 15/10/2026). Desviación máxima modelo − fabricante.

| Compresor | Puntos | n | Caudal máx. | Potencia eléctrica máx. | Descarga máx. |
|---|---|---|---|---|---|
| R-290 | ajuste (5 K) | 49 | 0.45 % | 0.25 % | 0.08 K |
| R-290 | regla del recalentamiento (1 y 10 K) | 4 | 0.42 % | 0.31 % | 0.10 K |
| R-32 | ajuste (5 K) | 86 | 1.02 % | 0.40 % | — (semiempírico) |


## identificacion

Multiarranque desde el juego del F2 y los tres arranques neutros del 24/09/2026 (S3-S5). Dominio de uso (T0 de -15 a 10 °C, Tk de 25 a 55 °C); R-290 solo con descarga >= Tk + 20 K. Solo caudal y potencia, pared adiabatica (AU_amb en su cota inferior): las descargas de los fabricantes son la adiabatica (decision 11 del 05/10/2026); la del R-290 se contrasta igual.

| Compresor | Arranque | Coste |  | Tiempo |
|---|---|---|---|---|
| R-290 | F2 | 0.01144 |  | 6 s |
| R-290 | S3 | 0.01144 |  | 10 s |
| R-290 | S4 | 0.01144 | adoptado | 15 s |
| R-290 | S5 | 0.01144 |  | 11 s |
| R-32 | F2 | 0.04686 |  | 9 s |
| R-32 | S3 | 0.04686 |  | 12 s |
| R-32 | S4 | 6000.00000 |  | 0 s |
| R-32 | S5 | 0.04686 | adoptado | 11 s |

### Parámetros adoptados

| Compresor | AU_su_n | AU_ex_n | AU_amb | A_leak | C | alpha_l | W_loss0 | r_v | eta_ic |
|---|---|---|---|---|---|---|---|---|---|
| R-290 | 0.001 | 1 | 1 | 7.113e-26 | 0.08381 | 4.636e-14 | 2.522e-14 | 2.286 | 0.5779 |
| R-32 | 0.001 | 211.4 | 1 | 3.568e-33 | 0.02218 | 0.05493 | 229.3 | 2.062 | 0.7606 |

### Contraste sobre los propios puntos

| Compresor | Puntos | Caudal máx. | Potencia máx. | Descarga máx. | Exceso máx. sobre la cota adiabática |
|---|---|---|---|---|---|
| R-290 | 31 | 1.32 % | 5.13 % | 3.59 K | +2.65 K |
| R-32 | 40 | 10.83 % | 3.64 % | — | +4.53 K |

