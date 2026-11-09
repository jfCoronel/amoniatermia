# Puntos a generar para los compresores de R-290 y R-32 (capítulo 13, H5)

05/10/2026. Los genera el autor con el software de selección de cada fabricante (decisión
del 29/09/2026, opción C: semihermético de R-290 y scroll de R-32; Bock no fabrica scroll,
de modo que el de R-32 sale de otro programa, p. ej. Copeland Select). Los resultados
**se identifican** con el mismo protocolo que el F2 (§9.4.3.1): son datos de identificación,
no de validación, y lo que se deje fuera de la rejilla de identificación servirá para
validar como en el capítulo 10.

## Qué compresor elegir

- **Capacidad frigorífica parecida a la del F2 NH₃**: del orden de **9 a 11 kW a T₀ = 2 °C y
  T_k = 45 °C**. El modelo iguala luego la capacidad en A35/W12-7 ajustando la cilindrada
  (decisión 9b), pero partir de un tamaño parecido evita extrapolar mucho.
- **Velocidad fija** a la frecuencia de red (50 Hz), como el F2: la comparación es entre
  fluidos con la misma tecnología de control. Si el software da también puntos a otra
  frecuencia, son bienvenidos aparte (velocidad variable, H6).

## Datos de catálogo de cada compresor (una vez)

Al principio del fichero, o en un `.txt` junto a él:

- Fabricante, modelo exacto, versión del software y fecha.
- **Cilindrada**: volumen barrido [m³/h] a 50 Hz y velocidad [rpm].
- Tipo de motor y si la potencia que da el software es **eléctrica** (lo normal en
  herméticos y semiherméticos) o al eje.
- **Límites de aplicación**: el diagrama de la envolvente (T₀–T_k) y, si lo da, la
  temperatura de descarga máxima y las presiones máximas (PS de alta y de baja).
- Aceite y carga de aceite (para el LCCP, opcional).

## Rejilla

Un fichero por compresor, `data/compresor_r290_catalogo.csv` y `data/compresor_r32_catalogo.csv`,
con estas columnas (las de `data/compresor_bock_f2_vap.csv`):

```
T0_C,Tc_C,recalentamiento_K,subenfriamiento_K,rpm,Q0_W,W_el_W,m_dot_kg_s,T_descarga_C,zona,observaciones
```

`zona`: dentro o fuera de la envolvente del fabricante (`dentro` / `fuera`); si el software
no da resultado, anotar `fuera` y dejar vacío el resto. Las celdas vacías son datos que no
existen: el modelo no las rellenará.

**A. Identificación** — recalentamiento de **5 K**, subenfriamiento **0 K**, velocidad nominal
(unos 40 puntos, se omiten los que caigan fuera):

| T_k \ T₀ | −15 | −10 | −5 | 0 | 5 | 10 |
|---|---|---|---|---|---|---|
| 25 °C | x | x | x | x | x | x |
| 35 °C | x | x | x | x | x | x |
| 45 °C | x | x | x | x | x | x |
| 50 °C |   | x | x | x | x | x |
| 55 °C |   |   | x | x | x | x |

Es más ancha que el catálogo del F2 (T₀ de 0 a 5 °C) a propósito: cubre la calefacción
con aire frío, donde el capítulo 12 mostró que se decide el SCOP.

**B. Efecto del recalentamiento**: T₀ = 0 °C, T_k = 35 y 45 °C con 1 y 10 K (4 puntos).

**C. Coherencia**: el punto T₀ = 2 °C, T_k = 45 °C, 5 K, tal como lo dé el software.

## Para qué se usa cada dato

| Dato | Uso |
|---|---|
| Q0, W_el, m_dot, T_descarga | Identificación de los nueve parámetros (formulación de Winandy para hermético: las pérdidas del motor calientan la aspiración) |
| Cilindrada y rpm | Geometría del modelo y lazo de igualación de capacidad (9b) |
| Envolvente y T_descarga máxima | Admisibilidad: decide la TOL real de cada fluido en el estacional, como en el R-717 |
| PS | Envolvente de presión (el R-32 trabaja a presiones mucho mayores) |
