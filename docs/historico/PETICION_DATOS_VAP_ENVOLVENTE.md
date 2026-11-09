# Puntos del F2 NH3 que barren la envolvente admisible (software VAP de Bock)

15/10/2026. Misma página y procedimiento que `PETICION_DATOS_VAP.md`. Lo genera el autor a mano.

## Para qué

Que el modelo del compresor quede identificado y validado en toda la zona en que el compresor
real puede operar. Así la admisibilidad de un punto depende solo de los límites del compresor
(diagrama del fabricante, 140 °C de descarga, presiones) y no de dónde se ajusta bien el modelo.
Hoy el dominio validado es T₀ de −5 a 5 °C; fuera, un punto admisible es solo tendencia.

## Plantilla

**`data/compresor_bock_f2_vap_envolvente.csv`**, mismo formato que `compresor_bock_f2_vap.csv`.
Rejilla de 5 K en T₀ (−25 a 15 °C) y T_k (10 a 55 °C), 1450 rpm, 5 K de recalentamiento y sin
subenfriamiento:

- **Bloque E**: 49 puntos dentro de la zona sin límites del diagrama (la admisible).
- **Bloque F**: 8 puntos en la zona de refrigeración suplementaria. Opcionales; sirven para la
  sensibilidad del capítulo 12 con tapa de cilindro refrigerada.

23 filas ya traen los resultados del bloque A del 29/09/2026 (columna `observaciones`). Quedan
**34 por generar** (28 del bloque E y 6 del F). Rellenar `Q0_kW`, `W_eje_kW`, `m_dot_kg_s`,
`T_descarga_C` y `zona`; si la herramienta no da resultado, poner `fuera` en `zona` y dejar el
resto vacío. Las celdas vacías son datos que no existen.

Los 46 puntos del catálogo (1 K de recalentamiento, T₀ de 0 a 5 °C) no se repiten.

## Fuera de esta rejilla

- Velocidad variable (H6): los 8 puntos a 960 y 1200 rpm del 29/09/2026 siguen siendo los únicos.
- Recalentamiento: el bloque B del 29/09/2026 (1, 5 y 10 K) sigue valiendo.

## Segunda petición: cuatro velocidades (15/10/2026, tarde)

**DECISIÓN DEL AUTOR (15/10/2026).** El compresor pasa a modelarse con los polinomios de
UNE-EN 12900 ajustados a los puntos de VAP, en lugar del modelo semiempírico. La ampliación del
semiempírico se ensayó sobre los 95 puntos (catálogo y bloque E) y no cumplía N1 dentro de la
propia muestra (potencia hasta un 12.7 %; `herramientas/compresor/ensayo_estructura.py`).

- **Recalentamiento**: los polinomios se ajustan a 5 K. Para otro recalentamiento se conservan el
  rendimiento volumétrico y el isentrópico obtenidos a 5 K, y un rendimiento de descarga para la
  temperatura de descarga. Los 46 puntos del catálogo (1 K) y el bloque B de
  `compresor_bock_f2_vap.csv` (1, 5 y 10 K) validan la regla.
- **Subenfriamiento**: no afecta al compresor.
- **Velocidad**: un juego de polinomios por velocidad, a 960, 1100, 1250 y 1450 rpm, e interpolación
  cuadrática de los rendimientos en la velocidad. Se ajusta con tres velocidades y se comprueba
  con la cuarta.

**Plantilla: `data/compresor_bock_f2_vap_velocidades.csv`**, con la misma rejilla de 57 puntos
(bloques E y F) a cada velocidad. Las 57 filas de 1450 rpm ya están rellenas (copiadas de
`compresor_bock_f2_vap_envolvente.csv`). Quedan **171 por generar** (57 a 960, 1100 y 1250 rpm).

- Anotar la `zona` que dé VAP en cada velocidad: el diagrama de límites puede recortarse a baja
  velocidad, y `zona_esperada` es la de 1450 rpm.
- Si VAP muestra o exporta los **coeficientes del polinomio** para cada velocidad, anotarlos
  también: evitan el error de ajuste. La temperatura de descarga sigue haciendo falta punto a punto,
  porque la norma no la incluye.
- Si las observaciones llevan comas, escribirlas entre comillas (o sin comas): una coma suelta
  parte la fila en columnas de más. Corregido el 15/10/2026 en `compresor_bock_f2_vap_envolvente.csv`.
