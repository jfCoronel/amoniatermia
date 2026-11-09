# Informe para la reescritura de los capítulos

Fecha: 24 de septiembre de 2026. Sustituye a `INFORME_REESCRITURA_CAP10.md`, que sirvió
para escribir la v30 del capítulo 10 y que esta ya ha absorbido casi entero; sigue
recuperable en el historial de git (`git show c6925e0:docs/INFORME_REESCRITURA_CAP10.md`).

**Punto de partida**: las versiones en PDF de `docs/Capitulos_pdf/` —capítulo 5 v13,
7 v3, 8 v5, 9 v4 y 10 v30—. Todas las referencias de apartado, tabla, ecuación y figura
de este informe son de esas versiones. Las cifras «del modelo» son las del código en el
commit que acompaña a este informe; la sección 9 dice cómo reproducirlas.

## 0. Cómo usar este informe

Cada ficha dice **qué dice hoy el capítulo**, **qué hay que escribir** y **por qué**, con
la evidencia. Estados:

| Estado | Significado |
|---|---|
| **CAMBIO** | El modelo ha cambiado desde la versión en PDF y el capítulo debe seguirlo. |
| **ERRATA** | El capítulo se contradice a sí mismo o con otro capítulo; el modelo no cambia. |
| **ALCANCE** | Consecuencia de una decisión del autor sobre el alcance de la tesis. |
| **DECIDIR** | Hace falta una decisión del autor antes de escribir. |
| **ABIERTO** | Asunto sin resolver en el modelo; el capítulo debe declararlo como tal. |

Lo que motiva la mayoría de los cambios, en cinco frentes, del 24/09/2026:

1. **Los transitorios quedan fuera de la tesis** (decisión del autor). El capítulo 10 ya
   lo decía; los capítulos 5, 7, 8 y 9 no.
2. **Las invalideces por balance de los modos con placas eran artefactos** de la
   comprobación: el agua se trataba con calores específicos constantes distintos en la
   marcha y en la comprobación. Con el agua en entalpía, como escribe la ec. 10-11, todos
   los modos son válidos.
3. **El compresor no siempre convergía**, y esa era la fuente del suelo de ruido de
   todos los modos. Corregido, y con otras tres correcciones numéricas, los cinco modos
   convergen en sus condiciones de diseño.
4. **El compresor se ha reidentificado** con el código corregido (decisión del autor):
   nueva tabla 10.8, nuevas tablas 10.9 y 10.10 y nueva figura 10.3.
5. **Erratas internas de la v30** detectadas por una auditoría cifra a cifra.

---

## 1. Capítulo 10 (v30)

### 1.1. §10.4.4 y tabla 10.6 — todos los modos son válidos · CAMBIO

**Dice**: M-3 no alcanza la tolerancia (7.2·10⁻⁵); M-4 y M-5 la alcanzan pero son «no
válidos» por el balance interno de un intercambiador (1.37·10⁻³ en el desrecalentador de
M-4); y usa ese caso para defender el criterio de 10⁻³: «relajarlo al 0.5 % haría válido
a M-4 sin que ese balance mejorase en nada».

**Escribir**: los cinco modos convergen y son válidos en sus condiciones de diseño:

| Caso (60 segmentos, 12 volúmenes) | Residuo | Peor balance de componente |
|---|---|---|
| M-1, circuito completo | 4.5·10⁻¹⁰ | 6.1·10⁻¹¹ |
| M-2, aire húmedo nominal (7 °C bs / 6 °C bh) | 4.5·10⁻¹⁰ | 1.5·10⁻⁸ |
| M-3, ACS 35 → 67 °C (diseño) | 6.1·10⁻¹¹ | 3.6·10⁻¹⁰ |
| M-4, ACS 35 → 67 °C (diseño) | 2.1·10⁻¹⁰ | 2.5·10⁻⁹ |
| M-5, punto de la tabla 8.5 | 8.6·10⁻¹⁰ | 3.2·10⁻⁹ |

(Tabla 10.6 de `docs/cifras_capitulo_10.md`. M-3 y M-4 con ACS de 10 a 60 °C también
convergen y son válidos: 1.3·10⁻¹¹ y 1.1·10⁻¹¹.)

**Por qué**: el balance de las placas que invalidaba los modos era exactamente
|c_p(T_salida)/c_p(T_entrada) − 1| del agua, coincidente en cuatro cifras en todos los
casos. La marcha avanzaba el agua con un c_p constante evaluado en un extremo y la
comprobación usaba otro c_p constante, el de la entrada. No había desequilibrio físico.
Con el agua marchada en entalpía —que es lo que escribe la ec. 10-11— el balance cierra
a 10⁻¹⁰–10⁻¹².

**Consecuencia para el texto**: el ejemplo con que el §10.4.4 (y el §7.7.1) defienden el
criterio de 10⁻³ ya no existe. El criterio sigue siendo defendible —es más exigente que
la literatura y el modelo lo cumple con seis órdenes de holgura—, pero hay que retirar el
ejemplo o sustituirlo. Propuesta: presentar el criterio como exigente y **declarar que el
modelo lo cumple con amplia holgura en los cinco modos**, y contar el artefacto como
lección de verificación (una comprobación mal planteada puede invalidar soluciones buenas,
igual que una bien planteada invalida soluciones malas).

**Y la parte de «converger no es ser válido»** se mantiene como principio, pero sin el
caso de M-4 como ilustración.

### 1.2. §10.4.4 y §10.12.4 — las cuatro correcciones numéricas · CAMBIO

Añadir, en el §10.4.4 o como decisión de implementación del §10.12.4, lo que hizo falta
para que los cinco modos converjan. Es del mismo género que el recorte en la frontera de
fase que el capítulo ya cuenta: defectos que no se manifiestan como error de exactitud
sino como imposibilidad de converger.

1. **El compresor caía en una meseta.** Su sistema interno acotaba T₁ con
   max(T₁, T_su): por debajo de T_su el residuo de la ec. 10-1 era constante,
   −AU_su·(T_w − T_su), y el método se paraba encima, a veces declarando éxito con un
   residuo de 1.1 W. Con AU_su,n = 0.0056 W/K la raíz está a 0.04 K de T_su y caía en ella
   a menudo. El caudal salía con un ruido relativo de 1.3·10⁻⁴ que era el **suelo de
   residuo de todos los modos**. La cota pasa a la saturación y la convergencia se juzga
   por los residuos (10⁻⁵ W), no por el indicador del método. El ruido baja a 10⁻¹¹.
2. **El punto fijo sobre q'' de las placas no convergía** en ebullición con título alto
   (x ≈ 0.93–0.9997): oscilaba, por ejemplo, entre 9.7 y 19.5 kW/m², y se devolvía la
   última iteración. El recalentamiento de salida saltaba 1.4 K con milésimas de kelvin
   en el agua. Se añade un respaldo con intervalo garantizado, que solo actúa donde el
   punto fijo falla.
3. **El recorte en la frontera de fase de las placas** actualizaba el área con
   A·(h_b − h)/(h_nuevo − h), que no es contractivo cuando el coeficiente depende de q'':
   agotaba sus seis pasos oscilando entre dos áreas (0.002 y 0.046 m²). Sustituido por una
   búsqueda con intervalo garantizado.
4. **El disparo del intercambiador de placas aislado** seguía con 10⁻³ K, cuando el del
   tren estaba en 10⁻⁷ K por la misma razón: el ruido del disparo llega al residuo de
   recalentamiento amplificado por ṁ_agua·c_p/ṁ_ref.

Y una de estrategia: **si el arranque por defecto no converge, el lazo externo prueba
arranques con otros pinzamientos** y el resultado registra desde cuál convergió. Lo
necesita M-4 en su condición de diseño: la estimación por parámetros agrupados sitúa la
evaporación en −3 °C, al otro lado de un codo de R₄, y la solución está en +0.33 °C.

### 1.3. §10.7.8 y §10.4.1 — la descarga del equilibrio de M-1 · CAMBIO

**Dice**: 120.1 °C (tabla 10.19 y §10.4.1).

**Escribir**: **120.0 °C**. El resto de la tabla 10.19 no cambia: 44.9 °C, 11.73 kW,
9.52 kW, 2.479 kW al eje, 32.59 kg/h. El cambio sale del compresor corregido y del juego
reidentificado (1.10).

**Y retirar** la frase «los balances cierran por debajo de 10⁻⁵» si se refiere al R₃:
en la v30 el R₃ era 4.3·10⁻⁴ de la potencia al eje, efecto de la meseta del compresor;
hoy cierra a 10⁻⁷ W.

### 1.4. §10.12.4 y tabla 10.25 — el suelo del backend tabular no era del backend · CAMBIO

**Dice**: el ruido de interpolación pone un suelo al residuo del orden de 10⁻⁶, del mismo
orden que la tolerancia, «de modo que una campaña con backend tabular puede marcar como
no convergidos puntos cuya respuesta es correcta a 10⁻⁴»; con 120 segmentos, 2.4·10⁻⁸
(HEOS) frente a 2.0·10⁻⁶ (tabular).

**Escribir**: con el compresor corregido, HEOS llega a **2.6·10⁻¹⁰** y el tabular a
**5.0·10⁻⁸** (34 s frente a 17 s desde la estimación, 120 segmentos). El tabular sigue poniendo un suelo propio, dos órdenes por encima de HEOS,
pero **cumple la tolerancia**: deja de ser cierto que marque como no convergidos puntos
correctos. La mayor parte del «suelo del tabular» era el ruido del compresor.

**Y la regla del capítulo 11** que el apartado enuncia («un suelo de residuo no puede
atribuirse a la biblioteca de propiedades sin haber descartado antes la discretización»)
sale reforzada y ampliada: **ni sin haber descartado los lazos internos de los
componentes**. Es exactamente el error que se cometió aquí.

### 1.5. §10.6.7 y §10.6.8 — el punto de diseño del desrecalentador, resuelto como sistema · CAMBIO

**Dice**: las tablas 10.13, 10.14 y 10.16 se calculan con el componente aislado, **40.3
kg/h de NH₃ condensando a 45 °C y entrada a 125.5 °C**. El punto de diseño publicado es
63.7 kg/h de ACS, 2.37 kW y 6.4 K de margen. Pero los 125.5 °C corresponden a
condensación a 46.8 °C, y ahí el compresor da **32.2 kg/h**, no 40.3. El capítulo no
declara el caudal.

**Decisión del autor del 25/09/2026**: el punto de diseño pasa a ser el de **M-3 resuelto
como sistema**, sin imponer nada: aire a 35 °C, agua de climatización a 12 °C, ACS de 35 a
67 °C. Es lo que el capítulo exige de cualquier otro resultado: imponer la temperatura de
condensación no es un equilibrio.

**Nuevo punto de diseño**: condensación a **43.4 °C**, 31.6 kg/h de NH₃ con descarga a
123.0 °C, **49.8 kg/h de ACS, 1 851 W recuperados y 5.5 K de margen**, con el 8 % de la
pared húmeda. La condensación sale más baja que los 46.8 °C del equilibrio de M-1 porque en
M-3 la batería recibe el gas ya desrecalentado.

**Nueva tabla 10.13** (sustituye a la actual; las dos primeras filas, además, estaban mal,
ver 1.7):

| Condición | Caudal de ACS | Q recuperado | Margen |
|---|---|---|---|
| Entrada a 140.4 °C, agua a 60 °C, 40.3 kg/h a 45 °C (revisión previa) | 99.2 kg/h | 2.88 kW | — |
| Entrada a 125.5 °C, agua a 60 °C, 40.3 kg/h a 45 °C | 84.8 kg/h | 2.46 kW | 4.0 K |
| Ídem, impulsión a 67 °C (**lo que publica la v30**) | 63.7 kg/h | 2.37 kW | 6.4 K |
| Condensación a 46.8 °C con el caudal del compresor (32.2 kg/h), 67 °C | 53.1 kg/h | 1.97 kW | 3.1 K |
| **M-3 resuelto como sistema (punto de diseño adoptado)** | **49.8 kg/h** | **1.85 kW** | **5.5 K** |

La potencia recuperada del punto de diseño baja un **22 %** respecto de lo publicado (1 851
frente a 2 371 W). **Afecta a la cifra con que se argumenta H3**, y hay que llevarla a
todos los sitios donde se cite: §10.6.7, §10.6.8, §8.4.4, §9.7.5 y la tabla 8.6.

**Tabla 10.14, dos filas nuevas**:

| Estado del submodelo | Margen |
|---|---|
| (las filas actuales, que se conservan) | … |
| Caudal coherente con el compresor (32.2 kg/h a 46.8 °C) | 3.1 K |
| **Punto de diseño resuelto como sistema (M-3)** | **5.5 K** |

La serie ya no es monótona: la última fila **ensancha** el margen, porque en el sistema
resuelto la condensación queda a 43.4 °C y no a 46.8 °C.

**Nueva tabla 10.16** (y tabla 8.6 del capítulo 8): el barrido del retorno, resuelto como
sistema, en verano y en invierno, con impulsión de 67 °C:

| Retorno | M-3: Q | M-3: margen | M-4: Q | M-4: margen o título de salida |
|---|---|---|---|---|
| 25 °C | 1 968 W | +1.2 K | 2 385 W | **condensa**, x = 0.980 |
| 30 °C | 1 911 W | +3.3 K | 2 280 W | **condensa**, x = 0.993 |
| 35 °C (diseño) | 1 851 W | +5.5 K | 2 237 W | +0.02 K |
| 45 °C | 1 713 W | +10.6 K | 2 115 W | +4.8 K |
| 55 °C | 1 559 W | +16.4 K | 1 981 W | +10.4 K |
| 60 °C | 1 476 W | +19.6 K | 1 906 W | +13.6 K |

**Lectura para el texto**:
- **En verano el criterio se cumple en todo el barrido**, también en el extremo frío de
  verificación de RS-17 (25 °C, 1.2 K). La decisión del suelo de 30 °C sigue siendo
  razonable.
- **En invierno no se cumple con retorno frío.** En M-4 el agua de climatización va de 40
  a 45 °C, se condensa a 49 °C y el margen se agota: con el suelo de 30 °C el refrigerante
  sale con título 0.993, y en diseño queda a 0.02 K de la saturación. Solo con retorno de
  45 °C o más hay margen. **Decisión del autor del 25/09/2026: se acepta la condensación
  parcial en invierno y se declara como limitación.** El criterio de dimensionado del
  §10.6.7 debe reformularse en consecuencia: se cumple en verano y en invierno con retorno
  caliente; con retorno frío en calefacción el desrecalentador condensa entre un 1 y un 2 %.
- Las dos consecuencias del §10.6.8 se mantienen: la potencia recuperada depende del estado
  de carga (en verano, de 1.97 kW con el depósito frío a 1.48 kW casi cargado) y el caudal
  del primario se dispara al final de la carga (182 kg/h en verano a 60 °C de retorno).

**Nueva tabla 10.15** (16-10H frente a 27-30H), en el punto de diseño nuevo:

| Geometría | Área | Caudal de ACS | Q | Salida del refrigerante |
|---|---|---|---|---|
| AlfaNova 16-10H (seleccionado) | 0.117 m² | 49.6 kg/h | 1 844 W | vapor, +5.7 K |
| AlfaNova 27 de 10 placas | 0.255 m² | 53.8 kg/h | 1 999 W | vapor, +0.7 K |
| AlfaNova 27-30H (descartado) | 0.894 m² | 64.7 kg/h | 2 403 W | bifásico, x = 0.960: condensa el 4 % |

La decisión de descartar el 27-30H **se sostiene**, y por el mismo motivo que da la v30:
desrecalienta de más y condensa dentro. El porcentaje condensado baja del 8 al 4 %.

Contrastes: `tests/test_referencia.py::TestPuntoDeDisenoDelDesrecalentador` y
`TestSeleccionEnElPuntoDeDiseno`. La tabla 10.16 de la v30 se conserva reproducida en
`TestRetornoDelPrimarioACS`, marcada como sustituida.

### 1.6. (fusionada en 1.5)

### 1.7. §10.6.7, tabla 10.13 — las filas 1 y 2 · ERRATA

Las filas 1 y 2 (~93 y ~80 kg/h; ~2.72 y ~2.32 kW) eran de un cálculo exploratorio del
18/09/2026 con otra geometría; con la geometría adoptada son 99.2 y 84.8 kg/h, 2.88 y 2.46
kW, y la segunda es la que cita el propio texto («de 2 463 a 2 371 W»). Recogidas ya en la
nueva tabla 10.13 de la ficha 1.5.

### 1.8. §10.9, tabla 10.22 — el anegado · CAMBIO

**Dice**: filas con 0 / 7.3 / 9.5 / 10.6 K de subenfriamiento, 0 / 8 / 13 / 18 % de volumen
anegado, 177–327 / 333–464 / 433–556 / 535–649 g y 61 / 90 / 108 / 126 % del presupuesto.
Los porcentajes de las filas 2 a 4 están calculados contra 515 g, la fila 1 no cuadra con
ningún presupuesto, y las filas 2 a 4 no tienen procedencia documentada.

**Nueva tabla 10.22**, con el mismo equilibrio de M-1 (batería y compresor, evaporación a
2 °C, aire a 35 °C) y subenfriamiento de consigna creciente:

| Subenfriamiento | Volumen anegado | Carga (banda de las cuatro correlaciones) | Capacidad | % del presupuesto de RS-5 |
|---|---|---|---|---|
| 0 K | 0 % | 177 – 327 g | 9.52 kW | 69 % |
| 7.3 K | 9.2 % | 364 – 498 g | 9.73 kW | **102 %** |
| 9.5 K | 14.1 % | 464 – 590 g | 9.76 kW | 121 % |
| 10.6 K | 17.2 % | 528 – 648 g | 9.76 kW | 133 % |

El porcentaje se toma contra el presupuesto de **cada fila** (50 g/kW por la capacidad de
esa fila), que es lo que dice RS-5: el subenfriamiento sube la capacidad y con ella el
presupuesto (476 → 488 g). **La conclusión del apartado sale reforzada**: con 7.3 K la
batería sola agota el presupuesto del sistema entero, no el 90 %. El texto «trece
centésimas de volumen anegado bastan» pasa a «**nueve centésimas**».

Contraste: `tests/test_referencia.py::TestEquilibrioM1::test_la_tabla_10_22_el_anegado_decide_RS5`.

### 1.9. §10.7.8, tabla 10.20 — la columna «impuesta» · CAMBIO

La columna de temperatura de evaporación impuesta (10.03 / 8.36 / 5.84 kW) es de la
revisión previa y no se reproduce con el compresor adoptado. **Nueva tabla 10.20**
(condensación a 50 °C, ventilador a 7 600 m³/h, superficie limpia):

| Aire exterior | T_evap impuesta / resuelta | Q_evap impuesta / resuelta | COP impuesto / resuelto |
|---|---|---|---|
| 7 °C bs / 6 °C bh (nominal EN 14511) | 1.6 / 0.82 °C | 8.83 / 8.52 kW | 4.15 / 4.05 |
| 2 °C bs / 1 °C bh | −2.9 / −3.54 °C | 7.13 / 6.90 kW | 3.59 / 3.52 |
| −7 °C bs / −8 °C bh (perfil frío) | −11.1 / −11.24 °C | 4.59 / 4.55 kW | 2.76 / 2.75 |

**Cambia el argumento del apartado.** La diferencia entre imponer y resolver es del **1 al
4 %** en capacidad y de 0.1 a 0.8 K en la temperatura de evaporación, **no del 12 al 22 %**:
con esta batería, la temperatura de evaporación supuesta estaba casi bien elegida. El
principio —imponer la temperatura no es un equilibrio— sigue siendo correcto y debe
mantenerse, pero sin atribuirle un efecto grande. La conductancia como evaporador es de
**33–36 W/(m²·K)**, no «del orden de 27» (esa es la del término nucleado solo, que el
§10.7.5 abandona); sigue siendo inferior a los 38 de condensación, por la efectividad
superficial húmeda.

Contrastes: `tests/test_air_hx.py::test_la_columna_impuesta_de_la_tabla_10_20` y
`test_el_equilibrio_como_evaporador_se_resuelve`.

### 1.9 bis. §10.11.2 — el ejemplo exergético del ACS · CAMBIO

**Dice**: en verano, el agua calentada de 10 a 60 °C tiene −5 W de exergía frente a 2 238 W
de energía; el COP global sube un 23.5 % y η_II no se mueve; en invierno el mismo salto vale
+252 W.

**Escribir**, remedido con el modelo actual (M-3 en verano y M-4 en invierno, ACS de 10 a
60 °C, discretización de trabajo): **2 338 W** de energía y **−5.1 W** de exergía en
verano; el COP global sube un **24.5 %**; en invierno, **+263.7 W**. La lectura no cambia.
(Los contrastes de la suite usan una malla más gruesa por velocidad y fijan 2 291 W,
−5.0 W, 24.0 % y +258.6 W: la energía del ACS cambia un 2 % entre mallas, dato para la
independencia de discretización del capítulo 11.)

Contrastes: `tests/test_indicadores.py::test_en_verano_el_ACS_tiene_energia_pero_no_exergia`
y `test_en_invierno_el_mismo_ACS_si_tiene_exergia`.

### 1.10. §10.5.3, tablas 10.8, 10.9 y 10.10, figura 10.3 — el compresor reidentificado · CAMBIO

**Decisión del autor del 24/09/2026**: se reidentifica con el compresor corregido y se
adopta la solución a la que se llega desde el juego anterior.

**Protocolo** (mismos 46 puntos, mismas cotas y misma función objetivo, con peso ×4 en la
temperatura de descarga). Multiarranque de cinco puntos, **esta vez registrados**:

| Arranque | Coste | Caudal | Eje | Descarga | T_dis a 2 / 46.8 °C |
|---|---|---|---|---|---|
| S1, desde el juego de la v30 (**adoptado**) | 0.02078 | ±2.71 % | ±4.72 % | ±3.35 K | 125.46 °C |
| S3, intermedio | 0.02078 | ±2.71 % | ±4.75 % | ±3.38 K | 125.49 °C |
| S4, AU altos | 0.02075 | ±2.71 % | ±4.82 % | ±3.20 K | 125.35 °C |
| S5, C alto | 0.02573 | ±2.76 % | ±6.26 % | ±3.85 K | 125.24 °C |
| S2, desde la antigua tabla 10.4 | 0.05776 | ±2.82 % | ±9.65 % | ±6.31 K | 123.91 °C |

Tres de cinco llegan al mismo mínimo con parámetros apreciablemente distintos (η_ic entre
0.90 y 0.97, W_loss,0 entre 461 y 541 W) y predicciones iguales: el mínimo es plano. Los
puntos de partida están en `data/compresor_bock_f2.yaml`.

**Nueva tabla 10.8** (juego adoptado):

| Parámetro | Valor | Unidad | Observación |
|---|---|---|---|
| AU_su,n | 0.0010 | W/K | En su cota inferior: no identificable |
| AU_ex,n | 1.139 | W/K | Débilmente sujeto |
| AU_amb | 1.000 | W/K | En su cota inferior |
| A_leak | 0.0 | m² | No identificable; converge a 10⁻²⁶ |
| C | 0.08806 | — | Bien sujeto; igual en las tres soluciones buenas |
| α | 0.0 | — | No identificable; converge a 10⁻¹⁴ |
| W_loss,0 | 461.1 | W | Bien sujeto |
| r_v | 1.9913 | — | Bien sujeto; la cota de 1.2 no muerde |
| η_ic | 0.8980 | — | Bien sujeto |

**Nueva tabla 10.9** (desviación máxima sobre los 46 puntos):

| Magnitud | Juego anterior | Juego de la v30 | Juego adoptado |
|---|---|---|---|
| Caudal másico | ±4.46 % | ±2.72 % | **±2.71 %** (rmse 1.62 %) |
| Potencia al eje | ±9.85 % | ±5.18 % | **±4.72 %** (rmse 1.73 %) |
| Temperatura de descarga | ±16.8 K | ±3.66 K | **±3.35 K** (rmse 1.65 K) |

Error medio de la descarga: −0.11 K (juego anterior: +14.25 K). La columna «juego de la
v30» puede omitirse o conservarse para mostrar que la corrección del compresor apenas
movió el ajuste.

**Nueva tabla 10.10** (sensibilidad a una perturbación relativa, normalizada):

| Parámetro | Sensibilidad | Estado |
|---|---|---|
| η_ic | 1.00 | Bien sujeto |
| r_v | 0.51 | Bien sujeto |
| W_loss,0 | 0.42 | Bien sujeto |
| C | 0.25 | Bien sujeto |
| AU_amb | 0.086 | Débilmente sujeto |
| AU_ex,n | 0.067 | Débilmente sujeto |
| AU_su,n | 1.4·10⁻⁴ | No identificable (en su cota) |
| α | 7.7·10⁻¹³ | No identificable |
| A_leak | 9.1·10⁻²² | No identificable |

El número de condición del jacobiano escalado **sin las dos columnas fijadas a cero** es
3.2·10⁴ (calculado en el óptimo que se alcanza desde los valores redondeados que guarda el
fichero de datos; el mínimo es tan plano que la cifra se mueve con el punto exacto). **No es comparable** con el 6.7·10¹¹ de la v30, que por su orden debía de
incluirlas; conviene publicar el nuevo con su definición.

**Cambios de redacción que arrastra**:
- «AU_ex,n y r_v quedaron en el límite del rango explorado» deja de ser cierto: ahora son
  AU_su,n y AU_amb los que quedan en su cota inferior, y r_v no.
- El ordenamiento de identificabilidad cambia: η_ic, r_v y W_loss,0 pasan por delante de
  AU_ex,n, que queda débilmente sujeto. El argumento del capítulo (cinco bien sujetos,
  dos débiles, dos no identificables) se sostiene con otra lista: **cuatro bien sujetos
  (η_ic, r_v, W_loss,0, C), dos débiles (AU_amb, AU_ex,n) y tres no identificables
  (AU_su,n, α, A_leak)**.
- **La pared ficticia sube a 298 °C** (antes 210 °C), aún más lejos de una temperatura
  física: refuerza lo que el apartado ya dice.
- «AU_su,n ≈ 0 es precisamente lo que anticipa el apartado 10.5.2» se mantiene.
- Borrar el párrafo duplicado sobre el rango de velocidad (aparece dos veces).

**Figura 10.3, rehecha** con el juego adoptado frente al anterior, sobre las bandas que la
revisión previa declaraba:

![Figura 10.3](figuras/fig_10_3_ajuste_compresor.png)

*Figura 10.3 – Contraste frente a los 46 puntos de catálogo del Bock F2 NH₃: juego de
parámetros adoptado (24/09/2026) y juego anterior (antigua tabla 10.4).*

Ficheros: `docs/figuras/fig_10_3_ajuste_compresor.png` (300 ppp, para Word) y `.pdf`
(vectorial). Se regenera con `uv run python notebooks/02_figura_10_3_ajuste_compresor.py`.

### 1.11. §10.5.1, ec. 10-3 — el subíndice de la presión · ERRATA

La ec. 10-3 escribe η_v = 1 + C − C·(P_ex/P_ad)^(1/n) y la ec. 10-4 define
P_ad = P(v_in, h_ad), el final de la etapa interna. Leída literalmente, la reexpansión
del espacio muerto iría hasta la presión adaptada, lo que es incorrecto (a 2 / 45 °C:
relación 1.55 y η_v = 0.964, frente a 3.85 y 0.839). **El código usa la presión de
aspiración** y C está identificado con esa forma: basta con **escribir P_su en la
ec. 10-3**. Consulta del autor del 24/09/2026.

### 1.12. §10.5.4 — la transferibilidad de C · DECIDIR

**Dice**: C «es geométrico y transfiere directamente» a otros refrigerantes.

**Matiz**: un 8.8 % es alto para un espacio muerto real; A_leak se fija en cero por no
identificable, de modo que C probablemente absorbe otras pérdidas volumétricas, como la
fuga. Leerlo como fracción geométrica y declararlo transferible excede lo que la
identificación sostiene, y afecta al protocolo de H5. Propuesta: declararlo «efectivo»,
transferible como hipótesis, y someterlo a la sensibilidad del §7.11. Borrar además el
párrafo duplicado sobre «correr hoy con R-290 o R-32».

### 1.13. §10.6.2, tabla 10.12 — la geometría de placas · ERRATA

- La tabla dice Φ = 1.20, pero su φ_c·φ_v = 1.54 y sus 0.1171 m² son los de **Φ = 1.15**,
  que es lo que usa el modelo (con Φ = 1.20 la propia serie del §10.6.4 da 1.36).
- Los 0.9091 m² del 27-30H no corresponden a ningún Φ; el modelo y la tabla 10.15 dan
  0.894 m².
- El «hueco b» de 2.42 mm del 27-30H es el paso de paquete; el hueco es **2.02 mm**.

### 1.14. Otras erratas menores de la v30 · ERRATA

| Dónde | Dice | Debe decir |
|---|---|---|
| §10.4.2 | «M-5 con reparto explícito instancia cinco» | Retirar: la variante con reparto se retiró (§10.3). |
| §10.11.1, «Tercera» | En M-5 el intercambiador de climatización cede «el rechazo del calor residual» | En M-5 no hay rechazo (§10.3): cede al ACS. |
| §10.5.2 | «el eje pide 2.41 kW» | 2.479 kW (§10.4.1). |
| §10.6.1 | el residuo de M-1 «pasa de 3.0·10⁻³ a 2.9·10⁻¹³» | El 3.0·10⁻³ era de M-2; rehacer con la tabla 10.6 nueva (1.1). |
| §10.7.2 | los residuos bajan «entre uno y siete órdenes» | Rehacer con la tabla 10.6 nueva. |
| §10.7.3 | h_a = 114.6 W/(m²·K) a 35 °C | El anclaje a 35 °C es 113 W/(m²·K). |
| §10.7.4 / tabla 10.18 frente a §10.7.6 | η_f = 0.447 / 0.465 frente a 0.440 / 0.458 | Unificar (el modelo da 0.447 / 0.465 en seco). |
| Tabla 10.2, M8 | «2.6 kPa sobre 17.8 bar» en la batería | El §10.13 dice que esa pérdida de carga se desprecia y el modelo no la calcula: retirar la cifra o calcularla. |
| §10.12.5 | 421 contrastes, 418 satisfechos, 3 pendientes | El recuento que dé la suite al cerrar la redacción (437 el 25/09/2026). |

### 1.15. §10.7.6 — el desescarche, ¿capítulo 12 o 13? · DECIDIR

El §10.7.6 aplica la penalización de la ec. 10-30 «a nivel de agregación estacional, en
el capítulo 12»; el §7.8.2 y los capítulos 8 y 9 ponen la agregación estacional en el 13.
Unificar en el 13.

### 1.16. §10.13 — limitaciones del estado actual · CAMBIO

**Retirar**: «El modo M-3 no alcanza la tolerancia… y M-4 y M-5, que sí la alcanzan, se
marcan como no válidos…». **Añadir**:
- **M-5 opera fuera del dominio de identificación del compresor** (T₀ = 17.6 °C frente al
  rango de catálogo de 0–5 °C; T_k = 52 °C frente a 15–50 °C). Dentro del dominio los
  juegos de parámetros equivalentes predicen lo mismo; fuera divergen: la potencia
  eléctrica de M-5 cambió un 2 % al pasar del juego de la v30 al adoptado (3 993 → 3 914 W).
  Es una incertidumbre de extrapolación que el capítulo 11 debe acotar.
- La condensación parcial del desrecalentador en invierno con retorno frío, aceptada por
  decisión del autor (1.5).

### 1.17. Notas de revisión del capítulo 10 · CAMBIO

- **Figura 10.3**: rehecha (1.10).
- **Figura 10.2** (lazos anidados): sigue pendiente de rehacer con cinco niveles; no la
  genera el código.
- **Validez de M-4 y M-5**: la nota queda resuelta (1.1).

---

## 2. Capítulo 7 (v3)

### 2.1. Los transitorios, fuera de la tesis · ALCANCE

Decisión del autor del 24/09/2026. Corregir:
- **Tabla 7.2**, fila H2: el método pasa a ser solo «simulación estacionaria de los cinco
  modos»; la métrica, «convergencia a punto admisible y cierre de las verificaciones
  independientes; ausencia de violación de límites operativos»; el capítulo, solo el 12.
  **Consecuencia**: H2 pierde la mitad de su método de contraste, y su enunciado en el
  capítulo 1 debe decirlo.
- **§7.6.1**: retirar la «formulación dinámica de orden reducido restringida al estudio de
  las conmutaciones» y el párrafo que la declara exploratoria para el capítulo 13.
  Mantener la justificación de por qué el modelo dinámico queda fuera (coste de
  desarrollo y escasez de datos transitorios).
- **§7.8.2**: retirar el último párrafo («Las simulaciones dinámicas se limitan a las
  transiciones…»).

### 2.2. §7.7.1 — el ejemplo del criterio de cierre · CAMBIO

**Dice**: «uno de los modos anula el sistema de residuos hasta 10⁻¹¹ y se marca sin
embargo como no válido, porque el balance interno de uno de sus componentes queda en
1.37·10⁻³».

**Escribir**: ese ejemplo era un artefacto de la comprobación (1.1). Mantener el criterio
de 10⁻³ y justificarlo por su exigencia, declarando que el modelo lo cumple con seis
órdenes de holgura. Y añadir la lección simétrica a la que el apartado ya enuncia: igual
que un suelo de residuo no debe atribuirse a las propiedades sin descartar la
discretización, **una invalidez no debe atribuirse al componente sin verificar la propia
comprobación**.

### 2.3. §7.7.3 y notas de revisión — N1 contra los puntos de la identificación · DECIDIR

La v3 pide fijar el criterio de la temperatura de descarga en N1 «con la desviación
medida que el apartado 10.5.3 publica». Esa desviación (hoy ±3.35 K) es la del ajuste
sobre los **mismos 46 puntos** con que se identificó el compresor: un criterio igual a
ella se cumple por construcción, y el §7.3.1 establece que una fuente empleada para
determinar parámetros queda consumida para contrastarlos. La objeción alcanza a todo N1.
**Propuesta**: validación cruzada —identificar sobre un subconjunto y contrastar sobre el
resto— con el criterio fijado antes de ejecutarla.

### 2.4. §7.7.3 — la ficha de Frimetal también está consumida · DECIDIR

El §7.7.3 cuenta una sola fuente consumida como anclaje. La correlación del lado de aire
se ancló sobre el único punto de la ficha de Frimetal (§10.7.3: «reproduce el punto de
ficha por construcción»), de modo que por la regla del §7.3.1 esa ficha también queda
consumida para contrastar el lado de aire. Son dos, y el §10.14 debe nombrar las dos.

---

## 3. Capítulo 8 (v5)

### 3.1. Tablas 8.4 y 8.5 y §8.4.3 — el punto de M-5 · CAMBIO

**Dice**: el punto de referencia de M-5 converge pero «no está todavía marcado como
válido», por el balance del intercambiador de climatización.

**Escribir**: **el punto es válido** (1.1). Y con el compresor reidentificado sus cifras
cambian:

| Magnitud | Tabla 8.5 (v5) | Modelo |
|---|---|---|
| Temperatura de evaporación | 17.6 °C | 17.60 °C |
| Temperatura de condensación | 52.0 °C | 52.09 °C |
| Temperatura de descarga | 109.1 °C | **107.8 °C** |
| Caudal de refrigerante | 57.2 kg/h | 57.2 kg/h |
| Caudal del primario de ACS | 455 kg/h | **453 kg/h** |
| Calor cedido al ACS | 19.54 kW | **19.47 kW** |
| Potencia eléctrica | 3 993 W | **3 914 W** |
| COP global | 4.89 | **4.98** |
| Residuo | 6.8·10⁻¹¹ | 2.0·10⁻⁹ |

| Tabla 8.4 | Impulsión | T_cond | Calor al ACS | Potencia eléctrica | COP global |
|---|---|---|---|---|---|
| Depósito 60 °C (v5) | 67 °C | 62.4 °C | 19.14 kW | 4 713 W | 4.06 |
| Depósito 60 °C (modelo) | 67 °C | **62.5 °C** | **19.07 kW** | **4 631 W** | **4.12** |
| Depósito 45 °C (v5) | 52 °C | 52.0 °C | 19.54 kW | 3 993 W | 4.89 |
| Depósito 45 °C (modelo) | 52 °C | **52.1 °C** | **19.47 kW** | **3 914 W** | **4.98** |

La conclusión del apartado no cambia: la consigna reducida sube el COP global un 21 % y
baja la potencia un 15 %; la de 60 °C sigue condensando por encima de los 25 bar
admisibles. **Añadir** que M-5 opera fuera del dominio de identificación del compresor
(1.16) y que sus cifras absolutas llevan una incertidumbre de extrapolación del orden del
2 %.

### 3.2. Tablas del equilibrio de M-1 (líneas de la tabla 8.x y su comentario) · CAMBIO

El capítulo 8 cita «120.1 °C» como descarga del equilibrio resuelto (tabla de contraste
con el catálogo y el párrafo que la sigue). Pasa a **120.0 °C** (1.3).

### 3.2 bis. §8.4.4 y tabla 8.6 — el retorno del primario · CAMBIO

La tabla 8.6 reproduce la tabla 10.16 de la v30, calculada con el caudal oculto. Sustituirla
por la nueva tabla 10.16 de la ficha 1.5, con las dos columnas de verano e invierno, y
reescribir la «decisión en tres partes»: el punto de diseño de 35 °C y el suelo de 30 °C se
mantienen; la verificación en el extremo frío se cumple en verano (1.2 K) y **no en
invierno**, donde se acepta la condensación parcial por decisión del autor. La potencia
recuperada pasa a 1.97 → 1.48 kW (verano) en lugar de 2.5 → 1.9 kW.

### 3.3. Las conmutaciones en el capítulo 13 · ALCANCE

«…conmutaciones entre modos analizadas en el capítulo 13» (§8.3.5 o su entorno): retirar.

### 3.4. El choque térmico periódico · DECIDIR

Sigue sin decidirse con qué se cubre —modos con recuperación o apoyo eléctrico—, y el
capítulo 9 pide cerrarlo antes de redactar el 13, porque su penalización entra en el
rendimiento estacional.

---

## 4. Capítulo 9 (v4)

### 4.1. §9.8.3 — la cadena de seguridad durante los transitorios · ALCANCE

«…su comportamiento durante los transitorios se examina en el capítulo 13»: retirar, o
remitir a líneas futuras del capítulo 16.

### 4.2. §9.7.5 y RS-17 — los márgenes, y la condensación en invierno · CAMBIO

El apartado justifica RS-17 con los márgenes de la tabla 10.16 de la v30 (6.4 / 4.3 / 2.3 K
con retorno de 35 / 30 / 25 °C), calculados con el caudal oculto. Con el punto de diseño
resuelto como sistema (ficha 1.5): **en verano 5.5 / 3.3 / 1.2 K**, y la verificación en
el extremo frío sigue cumpliéndose. **En invierno (M-4) el refrigerante condensa dentro con
retorno de 30 °C o menos**, y queda en la saturación a 35 °C. Por decisión del autor se
acepta y se declara. Hay que reescribir el párrafo «Por qué esto es materia de este
capítulo»: la condensación en invierno degrada el componente por ciclado térmico, y la
integridad de esa barrera es la premisa del §9.7.3, de modo que la aceptación debe ir
acompañada de su justificación (fracción condensada pequeña, 1–2 %, y solo en calefacción
con el depósito frío).

Y la cifra de potencia recuperada que el recuadro final cita («entre unos 2.5 kW con el
depósito frío y 1.9 kW casi cargado») pasa a **1.97 y 1.48 kW** en verano.

---

## 5. Capítulo 5 (v13)

### 5.1. La formulación dinámica del capítulo 13 · ALCANCE

Retirar las menciones a la parte dinámica del capítulo 13: la introducción del apartado de
niveles de modelado («modelo estacionario para el grueso del análisis y una formulación
dinámica de orden reducido…»), la referencia al «modelo dinámico del capítulo 13» y la
fila de la tabla que asigna al capítulo 13 la «parte dinámica». Mantener la exposición del
estado del arte de los modelos dinámicos, que es correcta; lo que cambia es que esta tesis
no los usa.

---

## 6. Tabla maestra: cifras que cambian

| Dónde | Magnitud | Publicado | Modelo |
|---|---|---|---|
| Tabla 10.6, §10.4.4 | Validez de M-3, M-4, M-5 | No válidos | **Válidos** |
| Tabla 10.19, §10.4.1, cap. 8 | Descarga del equilibrio de M-1 | 120.1 °C | **120.0 °C** |
| Tabla 10.8 | Parámetros del compresor | Juego de la v30 | **Juego del 24/09/2026** (1.10) |
| Tabla 10.9 | Descarga, desviación máxima | ±3.66 K | **±3.35 K** |
| Tabla 10.9 | Potencia al eje, desviación máxima | ±5.18 % | **±4.72 %** |
| Tabla 10.10 | Número de condición | 6.7·10¹¹ | **3.2·10⁴** (sin columnas nulas) |
| §10.5.3 | Pared ficticia a 2 / 46.8 °C | 210 °C | **298 °C** |
| §10.7.8 | R₃ del compresor | 4.3·10⁻⁴ de la potencia al eje | **10⁻⁷ W** |
| §10.12.4, tabla 10.25 | Residuo con tabular / HEOS, 120 segmentos | 2.0·10⁻⁶ / 2.4·10⁻⁸ | **5.0·10⁻⁸ / 2.6·10⁻¹⁰** |
| Tabla 10.22 | Carga con 7.3 K de subenfriamiento | 333–464 g, 8 % anegado | **364–498 g, 9.2 % anegado** |
| Tabla 10.22 | % del presupuesto de RS-5 | 61 / 90 / 108 / 126 % | **69 / 102 / 121 / 133 %** (presupuesto de cada fila) |
| Tabla 10.13, fila 2 | Potencia recuperada | ~2.32 kW | **2.46 kW** |
| Tabla 10.20 | Capacidad impuesta (nominal / 2 °C / −7 °C) | 10.03 / 8.36 / 5.84 kW | **8.83 / 7.13 / 4.59 kW** |
| Tabla 10.20 | Caída de capacidad, resuelta frente a impuesta | 12–22 % | **1–4 %** |
| §10.7.8 | Conductancia como evaporador | ~27 W/(m²·K) | **33–36 W/(m²·K)** |
| Tabla 8.5 | Potencia eléctrica / COP global de M-5 | 3 993 W / 4.89 | **3 914 W / 4.98** |
| Tabla 8.4 | Ídem con depósito a 60 °C | 4 713 W / 4.06 | **4 631 W / 4.12** |
| §10.6.7, tabla 10.13 | Punto de diseño del desrecalentador | 63.7 kg/h, 2.37 kW, 6.4 K | **49.8 kg/h, 1.85 kW, 5.5 K** (M-3 resuelto) |
| §10.6.8, tabla 10.16, tabla 8.6 | Margen con retorno 35 / 30 / 25 °C, verano | 6.4 / 4.3 / 2.3 K | **5.5 / 3.3 / 1.2 K** |
| Tabla 10.16 (nuevo) | Ídem en invierno (M-4) | — | **0.02 K / condensa (x 0.993) / condensa (x 0.980)** |
| Tabla 10.15 | Fracción condensada en el 27-30H | 8 % | **4 %** |
| §10.6.8, §9.7.5 | Potencia recuperada, depósito frío → cargado | 2.5 → 1.9 kW | **1.97 → 1.48 kW** (verano) |
| §10.11.2 | Ejemplo exergético: energía / exergía del ACS / subida del COP global | 2 238 W / −5 W / 23.5 % | **2 338 W / −5.1 W / 24.5 %** |
| §10.11.2 | Exergía del ACS en invierno | +252 W | **+263.7 W** |
| §10.12.5 | Contrastes de la suite | 421 / 418 / 3 | **437 contrastes** (25/09/2026) |

---

## 7. Decisiones pendientes del autor

1. **N1 validado sobre los puntos de la identificación** (2.3): ¿validación cruzada?
2. **Ficha de Frimetal consumida** (2.4): ¿se declara como segunda fuente consumida?
3. **Desescarche en el capítulo 12 o en el 13** (1.15).
4. **Transferibilidad de C** (1.12): ¿parámetro efectivo, sometido a sensibilidad?
5. **Choque térmico periódico** (3.4): ¿modos con recuperación o apoyo eléctrico?
6. **Formulación de H5** tras la retirada del R-744: ya está en el capítulo 7 v3 como
   decisión del capítulo 15, a cerrar antes de redactar el 14.
7. **Fuente experimental independiente** (§7.7.3, notas de revisión): ¿limitación
   declarada o búsqueda antes de cerrar el capítulo 11?

---

## 8. Lo que no conviene escribir todavía

- **El dominio de validez** que cierra el capítulo 11: la extrapolación de M-5 (1.16) y el
  margen de M-4 (1.5) entran en él.
- **Los tiempos de cálculo del §10.4.3** (5.2 s por punto de M-3): con las correcciones de
  convergencia cambian. Con HEOS y desde la estimación inicial (tabla 10.6 de
  `docs/cifras_capitulo_10.md`): M-1 28 s, M-2 47 s, M-3 48 s, M-5 32 s y M-4 289 s (este
  último, con arranque desde pinzamientos de 6 / 4 K). La ejecución mixta divide el tiempo
  por dos (M-1: 17 s frente a 34 s con 120 segmentos). **Arrancando de un punto
  convergido, cualquier modo cuesta 1–2 s**, que es lo que hace una campaña con
  continuación: es la cifra que conviene publicar para el coste de las campañas.

---

## 9. Procedencia

- **Todas las cifras del capítulo 10 que produce el modelo**, tabla por tabla y con la
  procedencia adjunta: `docs/cifras_capitulo_10.md`, generado por
  `notebooks/03_cifras_capitulo_10.py` (unos 30 minutos). **Es la fuente única de números
  para la redacción**: si alguna cifra de este informe difiere de ese documento, manda el
  documento generado.
- **Código**: rama `main` del repositorio, en el commit que acompaña a este informe.
- **Suite**: 427 contrastes, 424 satisfechos, 3 pendientes (`uv run pytest`).
- **Cifras de los cinco modos**: configuración de las pruebas (60 segmentos, 12
  volúmenes; aire de verano a 35 °C, aire de invierno a 7 °C bs / 6 °C bh; agua de
  climatización 12 °C a 0.45 kg/s en frío y 40 °C a 0.35–0.5 kg/s en calor; ACS según la
  fila; recalentamiento 5 K, subenfriamiento 2 K).
- **Equilibrio de M-1 (tabla 10.19)**: `tests/test_referencia.py::TestEquilibrioM1`.
- **Punto de M-5 (tabla 8.5)**: `tests/test_circuit.py::TestPuntoDeReferenciaM5`.
- **Reidentificación**: `data/compresor_bock_f2.yaml`, bloque
  `reidentificacion_2026_09_24`, con los cinco arranques registrados.
- **Figura 10.3**: `notebooks/02_figura_10_3_ajuste_compresor.py`.
- **Historial detallado de cada hallazgo**: `docs/PENDIENTES.md`, sección del 24/09/2026.
- **Correspondencia de numeración** con la versión anterior del capítulo 10:
  `docs/CORRESPONDENCIA_CAP10.md`.
