# Puntos a generar con el software VAP de Bock (F2 NH3)

29/09/2026. Página: https://vap.bock.de/stationaryapplication/Pages/Product.aspx?ItemObjectID=FM_FNH3&Size=F3&PgID=438&ProductID=1139
(elegir **F2 NH3**). Lo genera el autor a mano: los resultados solo salen al rellenar el
formulario.

## Para qué

- **Validar el compresor fuera del catálogo de 46 puntos** (T₀ de 0 a 5 °C), en la zona de
  calefacción, **con temperatura de descarga**: la tabla de prestaciones del PDF no la
  trae, y la salida de cada punto sí.
- **Contrastar el recalentamiento de 5 K** que usa el modelo en diseño (los 46 puntos son a
  1 K).
- **Velocidad variable (H6)**: puntos a 960 rpm, que el §9.5.3 declaraba inexistentes.

Estos puntos **no entran en la identificación**, salvo que se decida otra cosa: son
validación independiente (N1 fuera del dominio de identificación).

## Plantilla

**`data/compresor_bock_f2_vap.csv`**, con las 39 filas ya puestas en sus condiciones de
entrada (bloque, T₀, T_k, recalentamiento, subenfriamiento y rpm). Solo hay que rellenar
`Q0_W`, `W_eje_W`, `m_dot_kg_s`, `T_descarga_C` y `zona`. La columna `zona_esperada` sale
del diagrama y la tabla del PDF, que son a 1 K de recalentamiento; a 5 K el límite puede
moverse algo. Si la herramienta no da resultado en un punto, basta con poner `fuera` en
`zona`. Las celdas vacías son datos que no existen: el modelo no las rellenará.

## Qué anotar de cada punto

Una fila por punto, en `data/compresor_bock_f2_vap.csv`, con estas columnas:

```
T0_C,Tc_C,recalentamiento_K,subenfriamiento_K,rpm,Q0_W,W_eje_W,m_dot_kg_s,T_descarga_C,zona
```

`zona` es la del diagrama de límites: `sin_limites`, `refrigeracion_suplementaria` o
`fuera` (si la herramienta no da resultado, anotar `fuera` y dejar vacío el resto).

## Rejilla propuesta

**A. Calefacción y dominio ampliado, 1450 rpm y 5 K de recalentamiento, sin
subenfriamiento** (unos 30 puntos). Se omiten los que caigan fuera de la envolvente.

| T_k \ T₀ | −20 | −15 | −10 | −5 | 0 | 5 | 10 | 15 |
|---|---|---|---|---|---|---|---|---|
| 25 °C | x | x | x | x | x | x | x | x |
| 35 °C |   | x | x | x | x | x | x | x |
| 45 °C |   |   | x | x | x | x | x | x |
| 50 °C |   |   |   | x | x | x | x | x |

**B. Efecto del recalentamiento**: los puntos T₀ = 0 °C y T_k = 35 y 45 °C, con 1, 5 y 10 K
de recalentamiento (6 puntos, dos repiten la rejilla A).

**C. Velocidad variable (H6)**: T₀ = 0 y 5 °C, T_k = 35 y 45 °C, a **960 rpm** y 5 K
(4 puntos). Si la herramienta admite más velocidades, añadir 1200 rpm.

**D. Comprobación de coherencia con el catálogo actual**: T₀ = 2 °C y T_k = 45 °C, a 1 K y
1450 rpm (debe dar los 9460 W y 122.2 °C del catálogo). Si no coincide, anotar la
versión del software.
