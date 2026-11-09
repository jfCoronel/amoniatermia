# TESIS DOCTORAL — "AMONIATERMIA"

> **Numeración.** Este documento cita el capítulo 10 en su revisión previa a la v30 y el
> capítulo 7 en su v1. La correspondencia con las versiones vigentes
> (`docs/Capitulos_pdf/`) está en `docs/CORRESPONDENCIA_CAP10.md`. No se renumera: citar la
> versión que se auditaba es parte de lo que el documento registra.

## Guía paso a paso: implementación del modelo

Python + CoolProp + Jupyter. Acompaña al esqueleto de paquete entregado
(`amoniatermia_esqueleto.zip`) y al apartado 10.14 revisado.
Fecha: 3 de septiembre de 2026.

> Este fichero es ahora el documento de referencia. Procede de la conversión de
> `Guia_implementacion_modelo_AMONIATERMIA.docx`, eliminado del árbol de trabajo
> tras la conversión (recuperable en el commit `ed0f9ad`). El texto es el del
> documento original; las adiciones son las notas marcadas como
> **Nota (estado del repo)** y los indicadores de estado.

### Cómo se lleva el estado

Cada fase y cada paso llevan un indicador que se actualiza **en el mismo commit
que hace el trabajo**, nunca después:

| Marca | Significado |
| --- | --- |
| ✅ | Hecho y verificado (test en verde, o decisión escrita) |
| 🟡 | En curso o parcialmente hecho — el detalle está en la nota del paso |
| ⛔ | Bloqueado por una decisión pendiente, no por falta de tiempo |
| ❌ | Pendiente, sin empezar |

El resumen de la última sección es el índice de estado: si una marca de allí y
otra de aquí no coinciden, la del cuerpo del documento manda.

**Última revisión del estado:** 3 de septiembre de 2026.

**Qué contiene el esqueleto entregado.** Paquete instalable con capa de
propiedades, geometría, registro de correlaciones intercambiables, cuatro
correlaciones de fracción de huecos, modelo semiempírico de compresor abierto,
intercambiador de placas por volúmenes finitos con inventario de carga, válvula
de expansión, y 27 tests que se ejecutan en verde. No es un ejemplo ilustrativo:
es código funcional sobre el que construir.

---

## Fase 0. Preparación del entorno ✅

### Paso 1. Crear el repositorio ✅

Antes de escribir nada, el repositorio. El apartado 7.12 promete control de
versiones, y esa promesa debe ser cierta desde la primera línea.

```bash
mkdir amoniatermia && cd amoniatermia
git init
git branch -M main
```

Descomprime el esqueleto entregado dentro de esa carpeta y haz el primer commit.
A partir de ahí, un commit por cada avance con sentido propio, con mensajes
descriptivos. El historial de git será tu registro de trabajo y te servirá para
redactar el capítulo.

### Paso 2. Crear el entorno y comprobar que los tests pasan ✅

```bash
conda env create -f environment.yml
conda activate amoniatermia
pip install -e ".[dev]"
python -m ipykernel install --user --name amoniatermia
pytest -q
```

Deben pasar los 27 tests. Si alguno falla, resuélvelo antes de seguir: es la
línea de base sobre la que vas a construir.

**Por qué `-e` (editable).** Con instalación editable, los cambios en el código
son visibles inmediatamente desde los notebooks sin reinstalar. Sin ella,
acabarías copiando código a las celdas, que es exactamente lo que queremos
evitar.

> **Nota (estado del repo).** ✅ Hecho, pero con `uv` en lugar de conda:
> `environment.yml` fue sustituido por `pyproject.toml` + `uv.lock`, y la versión
> de Python se fija en `.python-version`. Los 27 tests pasan en verde. El
> equivalente es:
>
> ```bash
> uv sync            # crea .venv, instala dependencias + grupo dev, editable
> uv run python -m ipykernel install --user --name amoniatermia
> uv run pytest -q
> ```
>
> `uv sync` instala el paquete en modo editable por defecto, así que la razón
> del `-e` sigue cubierta.

---

## Fase 1. Cierre de decisiones bloqueantes ✅

Tres decisiones deben cerrarse antes de programar más, porque cambiarlas después
obliga a rehacer trabajo. Ninguna requiere código.

| Estado | Decisión | Dónde se cierra | Por qué bloquea |
| --- | --- | --- | --- |
| ✅ | Configuración del modo M-5 (producción exclusiva de ACS): disipar el calor residual en el intercambiador de climatización, o condensar íntegramente en el desrecalentador ampliado. | Capítulo 8 | Determina la topología del circuito y, por tanto, la estructura de `circuit.py`. Es la decisión más costosa de revertir. |
| ✅ | Inclusión o no del R-744 en el conjunto comparativo. | Apartados 7.8.3 y 6.x | Si se incluye, hay que modelar el ciclo transcrítico con gas cooler y optimización de la presión de alta. Es un módulo entero adicional. |
| ✅ | Número de puntos de prestaciones disponibles del compresor. | Documentación del fabricante | Con menos de ~20 puntos, identificar 7 parámetros está mal condicionado y hay que fijar `AU_amb` y `n_reexp` a priori. El esqueleto ya emite un aviso, pero conviene saberlo antes. |

*Tabla G.1 – Decisiones que bloquean el desarrollo.*

> **Nota (estado del repo).** El aviso de los <20 puntos está implementado en
> `components/compressor.py:211`. Al cerrar cada decisión, escribe abajo **qué**
> se decidió y **dónde** queda registrado, y cambia la marca a ✅.

### Decisiones cerradas

#### D-1. Configuración del modo M-5 — cerrada el 3 de septiembre de 2026

**Se disipa el calor residual en el intercambiador de climatización**, con
control sobre la potencia entregada al circuito de ACS. Se descarta la
alternativa de condensar íntegramente en un desrecalentador ampliado.

*Pendiente de redacción en el capítulo 8; esta entrada es el registro provisional.*

Consecuencias para el modelo:

- **No hay geometría nueva.** El desrecalentador conserva su tamaño, así que
  `plate_hx.py` y `geometry.PlateGeometry` sirven sin cambios. La alternativa
  descartada habría obligado a redimensionar el desrecalentador y a repetir su
  verificación.
- **Topología de M-5:** compresor → intercambiador de ACS (desrecalentamiento y
  condensación parcial) → intercambiador de climatización (condensación restante,
  calor disipado) → válvula de expansión → evaporador de aire → compresor. Son
  dos `PlateHeatExchanger` en serie en el lado de alta.
- **Grado de libertad adicional.** El reparto del calor de condensación entre
  ACS y disipación es precisamente lo que se controla, así que en M-5 el sistema
  de la tabla 10.4 no queda cerrado con las cuatro incógnitas habituales
  (`P0`, `Pk`, `A_ef`, `T_wall`). Ver el punto abierto siguiente.

**Punto abierto (cerrar antes de programar `circuit.py`):** cómo se especifica
ese control. Dos formas, con consecuencias distintas sobre `residuals()`:

1. *Por consigna de ACS* — se impone la temperatura de salida del agua de ACS y
   el reparto sale de ella. El vector de incógnitas sigue siendo de cuatro y el
   control entra por `setpoints`. Es la opción más simple.
2. *Por variable de control explícita* — se impone el caudal (o la temperatura de
   entrada) del secundario de climatización y el reparto es resultado. Añade una
   quinta incógnita y un quinto residuo.

La opción 1 basta si el control se modela como ideal; la 2 es necesaria si el
capítulo 11 tiene que reproducir el comportamiento de un control real.

> **Estado al 17/09/2026.** `circuit.py` implementa **las dos**: el modo `M-5`
> cierra por consigna de ACS con cuatro incógnitas, y `M-5-reparto` añade el
> caudal de climatización como quinta incógnita y la potencia disipada como
> quinto residuo. El punto abierto **no se cierra por omisión**: la elección
> sigue siendo del capítulo 8, y cambiarla es editar la tabla de modos.
>
> Queda además una discrepancia que el capítulo 8 debe resolver: la tabla 10.3
> del capítulo 10 describe M-5 con los dos intercambiadores de placas **ambos
> dedicados a ACS**, mientras que D-1 disipa el calor residual en el de
> climatización. El modelo sigue a D-1 por ser la decisión posterior y
> explícita, y lo declara en la topología.

#### D-2. Inclusión del R-744 — cerrada el 3/09/2026, **REABIERTA Y REVERTIDA el 21/09/2026**

> **Decisión del 21/09/2026: el R-744 se RETIRA del conjunto comparativo.**
> No se modela el ciclo transcrítico, y probablemente salga de la tesis. Es la
> segunda de las dos opciones que las notas de revisión del capítulo 7 ponían
> sobre la mesa: «retirarse del conjunto comparativo y tratarse solo
> cualitativamente en el capítulo 6». El propio capítulo advertía de que la
> primera opción «cuesta bastante trabajo, porque exige modelar el ciclo
> transcrítico con optimización de la presión de alta», y de que convenía
> decidirlo antes de escribir el capítulo 10 —lo que, tomada ahora, se cumple
> justo a tiempo para el 12 al 14—.
>
> **Lo que la retirada NO deshace.** Las cuatro provisiones que D-2 declaró «no
> aplazables» se quedan, porque ninguna dependía solo del R-744:
>
> - El vector de incógnitas por modo lo exige igualmente el reparto de M-5
>   (D-1), y ya está en `ModeSpec`.
> - La familia de correlaciones nueva llegó por otra vía: la separación
>   `tube_*` frente a `plate_*` de la tarea C4.
> - Que las campañas traten el fluido como **parámetro** es ahora *más*
>   necesario, no menos: ver abajo.
> - Que `plate_hx` no admita presiones supercríticas deja de ser un problema y
>   pasa a ser un límite declarado del componente.
>
> **Lo que sí obliga a revisar en la redacción:**
>
> - El §7.8.3 y su tabla 7.6, con el recuadro «Advertencia sobre el R-744», y
>   la nota de revisión que dejaba la decisión pendiente.
> - El §7.1, que justifica el enfoque de simulación diciendo que H5 «exigiría
>   construir **cuatro** máquinas geométricamente idénticas». Pasan a ser tres.
> - **Y la formulación de H5, que es lo serio.** H5 afirma que el R-717 «supera
>   a las restantes **alternativas naturales** evaluadas en igualdad de
>   condiciones». Las naturales del conjunto eran el R-290 y el R-744; el R-32
>   es un HFC. Retirado el R-744, H5 descansa sobre **una sola** comparación
>   con alternativa natural. O se reformula la hipótesis en términos de
>   «alternativas de bajo PCA» —que incluye al R-32 y la sostiene con dos— o se
>   acepta que el contraste natural es frente al R-290 y se dice así.
>   Conviene resolverlo antes de redactar el capítulo 14.

#### D-2 (registro original). Inclusión del R-744 — cerrada el 3 de septiembre de 2026

**Se incluye el R-744 en el conjunto comparativo, pero por fases:** primero se
completa el trabajo con los otros tres refrigerantes (R-717, R-290 y R-32) y el
R-744 se aborda después, como fase propia.

*Pendiente de redacción en los apartados 7.8.3 y 6.x; esta entrada es el
registro provisional.*

Lo que el escalonamiento **sí** permite aplazar: el componente *gas cooler*, la
optimización de la presión de alta y las correlaciones de enfriamiento
supercrítico.

Lo que **no** permite aplazar, porque rehacerlo después es mucho más caro que
preverlo ahora:

- **El vector de incógnitas de `circuit.py` debe dimensionarse por modo**, no
  fijarse a las cuatro de la tabla 10.4. El ciclo transcrítico añade la presión
  de alta como incógnita con su propio residuo de optimización. Combinado con el
  quinto residuo que puede pedir M-5 (ver D-1), fijar el vector a cuatro
  obligaría a reescribir `residuals()` dos veces.
- **El registro de correlaciones necesitará una familia nueva.** `_REGISTRY`
  (`correlations/__init__.py:13`) tiene hoy cinco familias: `singlephase`,
  `boiling`, `condensation`, `voidfraction` y `friction`. El enfriamiento
  supercrítico no es condensación y no puede colgar de `condensation` sin
  falsear el significado de la banda de incertidumbre. Añadir la familia es
  trivial; descubrirlo con las campañas ya lanzadas, no.
- **`plate_hx.py` no admite presiones supercríticas.** `_alpha_ref` llama a
  `sat_props(P)` incondicionalmente (`plate_hx.py:81`) y CoolProp aborta por
  encima del punto crítico:
  `Pressure to PQ_flash [9000000 Pa] may not be above the numerical critical point of 7377298`
  (comprobado con CO₂ a 90 bar; su presión crítica son 73,77 bar). El *gas
  cooler* será por tanto un componente propio, o `_alpha_ref` necesitará una
  rama supercrítica previa a `sat_props`. No es un ajuste menor.
- **Las campañas y la procedencia deben tratar el fluido como parámetro**, para
  que incorporar el R-744 sea añadir un valor y no reescribir el notebook.

Consecuencia sobre el calendario: la comparación de los tres primeros
refrigerantes es publicable y defendible por sí misma. El R-744 entra como
ampliación, no como requisito de cierre.

#### D-3. Puntos de prestaciones del compresor — cerrada el 3 de septiembre de 2026

**Se asume que siempre se dispondrá de 20 o más puntos de operación**, de modo
que los siete parámetros del apartado 10.4.4 se identifican todos y no se fija
ninguno a priori.

Es una **hipótesis de trabajo, no un dato verificado**, y esa es la diferencia
con D-1 y D-2. Se registra como tal para que quede fechada: si al reunir la
documentación del compresor resultan menos puntos, el plan de contingencia es
fijar `AU_amb` a priori e identificar seis. `n_reexp` no entra en esa
contingencia porque ya está fijo (ver más abajo).

Consecuencias y condiciones:

- **Lo que hay que verificar no es solo el recuento, sino el reparto.** Veinte
  puntos apiñados en un rango estrecho de presiones condicionan mal el problema
  igual que diez bien repartidos lo condicionan bien. Al reunir el catálogo,
  comprobar que los puntos barren el mapa `P_ad`–`P_ex` de los cinco modos.
- **La hipótesis debe cubrir la temperatura de descarga, no solo el recuento
  total.** Un punto sin `T_dis` aporta un residuo nulo (`compressor.py:236`): no
  sesga el ajuste, pero tampoco restringe nada. Si de los 20 puntos solo unos
  pocos publican `T_dis`, `AU_ex_n` y `AU_amb` quedan mal sujetos y con ellos
  H3. Si el catálogo impreso no las da, obtenerlas del software de selección del
  fabricante.
- **`n_reexp` sigue fijo en 1,20 y no se identifica**, aunque el recuento ya no
  lo impida: `as_vector()` (`compressor.py:46`) devuelve siete parámetros y el
  exponente de reexpansión no está entre ellos. Es deliberado —está débilmente
  identificado y acotado físicamente—, pero conviene decirlo en el capítulo 10
  para que no parezca un olvido.
- **`A_leak` arranca en 0,0**, es decir, con la fuga interna desactivada. Con 20
  puntos se identifica sin problema, pero conviene comprobar que el ajuste la
  separa de `C`: ambas reducen el caudal y son la pareja más propensa a
  compensarse entre sí.

---

## Fase 2. Sustitución de los marcadores provisionales ❌

El esqueleto contiene correlaciones con coeficientes marcados como
`PROVISIONAL`. Funcionan y permiten que el código corra, pero no son
defendibles. Sustitúyelas en este orden, que va de mayor a menor impacto sobre
los resultados:

| Orden | Estado | Fichero | Qué sustituir | Impacto |
| --- | --- | --- | --- | --- |
| 1 | ❌ | `correlations/boiling.py` | Implementar la correlación específica de NH₃ en placas (función marcada como `NotImplementedError`). Hasta hacerlo, la banda de incertidumbre solo tiene dos formulaciones. | Alto — es el vacío V-1 |
| 2 | ❌ | `correlations/singlephase.py` | Coeficientes C y m de `chevron_generic` por los de la referencia definitiva, con su rango de validez. | Alto — gobierna el desrecalentador y por tanto H3 |
| 3 | ❌ | `correlations/condensation.py` | Coeficientes C y m de `equivalent_Re`. | Medio |
| 4 | ❌ | `correlations/friction.py` | Factor de fricción por la correlación de placas corrugadas referenciada. | Bajo en NH₃ por su bajo caudal másico |

*Tabla G.2 – Marcadores provisionales, por orden de sustitución.*

> **Nota (estado del repo).** Los cuatro marcadores siguen en pie:
> `boiling.py:112` (`placeholder_nh3_specific`, lanza `NotImplementedError`),
> `singlephase.py:18`, `condensation.py:22` y `friction.py:9`.
> Advertencia sobre la banda de incertidumbre: `asymptotic_cooper` y
> `additive_cooper` comparten `cooper_pool_boiling` y los mismos factores F y S,
> y solo difieren en la agregación. No son formulaciones independientes, así que
> hoy la banda es más estrecha de lo que aparenta. Debe declararse en el cap. 12
> mientras el orden 1 siga en ❌.

**Regla práctica.** Cada vez que sustituyas una correlación, añade en su
docstring la referencia bibliográfica completa y el rango de validez declarado
por sus autores. El capítulo 10 exige esa información y recopilarla al final,
sobre código ya escrito, es mucho más lento y propenso a errores que anotarla en
el momento.

---

## Fase 3. Componentes que faltan ❌

### Paso 1. `components/air_hx.py` ❌

Intercambiador de aire con superficie seca y húmeda por el método del potencial
entálpico (ecuación 10.25), y el modelo simplificado de desescarche por
penalización en intervalos (ecuación 10.26). Sigue el mismo patrón que
`plate_hx.py`: hereda de `Component`, implementa `solve()` y `charge()`.

El desescarche no es opcional: sin él, el SCOP de Burgos saldrá sistemáticamente
alto y la comparación con equipos comerciales de R-290 dejará de ser legítima.

### Paso 2. `components/four_way_valve.py` ❌

Pérdida de carga por coeficiente de caudal y fuga interna según la ecuación
10.29. Es un componente corto pero conviene que exista como objeto propio,
porque el coeficiente de fuga entra en el análisis de sensibilidad.

### Paso 3. `circuit.py` ❌

> **Desbloqueado** el 3 de septiembre de 2026 al cerrarse la decisión D-1. La
> topología de M-5 está fijada (ver Fase 1). Queda un punto abierto menor —cómo
> se especifica el control del reparto de calor— que decide si el vector de
> incógnitas de M-5 es de cuatro o de cinco; conviene cerrarlo antes de escribir
> `residuals()`, pero no bloquea los pasos 1 y 2 de esta fase.

Es el módulo central y el que más se beneficia de que los componentes ya estén
probados por separado. Estructura recomendada:

```python
class Circuit:
    def __init__(self, mode, components, boundary, setpoints): ...

    def residuals(self, u):
        P0, Pk, A_ef, T_wall = u
        # ... resuelve la cadena de componentes segun la topologia
        return np.array([R1, R2, R3, R4])   # tabla 10.4

    def solve(self):
        sol = scipy.optimize.root(self.residuals, self.x0,
                                  method='hybr')
        self._verify_energy_balance()   # ap. 7.7.1
        self._verify_entropy_positive()
        return self._package(sol)
```

La topología por modo se define como un diccionario que mapea cada modo a la
secuencia de componentes y sus conexiones. Los objetos de componente no cambian
entre modos: es el requisito del apartado 10.3.

**Sobre la inicialización.** El lazo externo es fuertemente no lineal y una mala
inicialización es la causa más frecuente de no convergencia. Implementa el
modelo simplificado de parámetros agrupados del apartado 10.11.5 antes de
necesitarlo, y en las campañas paramétricas usa continuación: la solución del
caso anterior como punto de partida del siguiente. Reduce los fallos de forma
drástica.

---

## Fase 4. Rendimiento 🟡

Cuando el modelo resuelva correctamente, y no antes, ocúpate de la velocidad. El
orden importa: optimizar código que aún cambia es tiempo perdido.

| Estado | Medida | Efecto medido | Cuándo aplicarla |
| --- | --- | --- | --- |
| ❌ | Backend tabular `BICUBIC&HEOS` en lugar de `HEOS` | x21 sobre `AbstractState` reutilizado; x163 sobre `PropsSI` | Solo tras cuantificar su error de interpolación con `backend_deviation_report()` |
| ✅ | Reutilizar el `AbstractState` (ya implementado) | x7,7 sobre `PropsSI` | Ya está hecho en el esqueleto |
| ❌ | Continuación en campañas paramétricas | Reduce iteraciones del lazo externo y fallos de convergencia | Al programar las campañas |
| ❌ | Paralelización por casos con `multiprocessing` | Escala con el número de núcleos | Las campañas son vergonzosamente paralelas: cada punto es independiente |

*Tabla G.3 – Medidas de rendimiento, por orden de aplicación.*

> **Nota (estado del repo).** `backend_deviation_report()` está implementado en
> `props.py:181`, pero **no lo llama ningún test ni notebook**: el error de
> interpolación sigue sin cuantificar, así que el backend tabular no puede
> activarse todavía. Cuantificarlo es un notebook corto y no depende de
> `circuit.py`.

**El orden de magnitud del problema.** Con ~10⁵ llamadas de propiedades por
punto de operación y una campaña de ~10⁵ puntos (cinco modos, cuatro fluidos,
barrido paramétrico, tres climas con intervalos de EN 14825, tres correlaciones
de ebullición, cuatro de fracción de huecos y análisis de sensibilidad), la
diferencia entre usar `PropsSI` y usar el backend tabular es de doce días de
cálculo frente a dos horas. No es una optimización cosmética.

---

## Fase 5. Campañas y resultados 🟡

### Paso 1. Separar experimento de modelo ✅

Los notebooks definen el caso y grafican; nunca contienen lógica del modelo. Si
te encuentras escribiendo una función en una celda, esa función pertenece al
paquete.

### Paso 2. Notebooks versionables ✅

Guarda los notebooks en formato jupytext `py:percent`, no `.ipynb`. Git no
produce diffs legibles de un `.ipynb`, así que el control de versiones que
promete el capítulo 7 sería ficticio. El `.gitignore` del esqueleto ya excluye
los `.ipynb`.

```bash
jupytext --to notebook notebooks/01_verificacion_propiedades.py
jupyter lab
# al terminar, jupytext sincroniza el .py automaticamente
```

### Paso 3. Campañas sin abrir Jupyter ❌

```bash
papermill notebooks/03_campana.ipynb resultados/caso_042.ipynb \
          -p T_evap -10 -p fluido Ammonia -p corr_boiling asymptotic_cooper
```

### Paso 4. Guardar resultados con procedencia 🟡

Todo fichero de resultados debe llevar adjunta la procedencia: versión de
CoolProp, backend empleado, correlaciones activas, versión del código (hash de
git) y parámetros de entrada. La clase `PropertyProvenance` del esqueleto es el
punto de partida. Sin esto, los resultados no son reproducibles y el anexo E no
cumple lo que promete el apartado 7.12.

Formato recomendado: parquet para las tablas de resultados y un JSON adjunto con
los metadatos. Evita CSV para volúmenes grandes.

> **Nota (estado del repo, 16/09/2026).** ✅ Resuelto. `PropertyProvenance`
> registra ya los cinco elementos del §10.13.6: versión de CoolProp, backend,
> fluidos, correlaciones activas, parámetros de entrada, revisión de git y
> versión del paquete. `is_complete()` rechaza una procedencia cuyo hash
> corresponda a un árbol de trabajo sucio, porque no identifica el código que
> produjo el resultado. `write_json()` la deja junto al fichero de resultados.
> Queda pendiente el formato parquet de las tablas.

---

## Fase 6. Enlace con el capítulo 11 ❌

La validación es el capítulo que decide si el tribunal acepta el trabajo, y
conviene programarla como parte del paquete y no como un análisis manual:

- Un módulo `validation/` con un caso por cada nivel de la tabla 7.5.
- Cada caso reconstruye la geometría y las condiciones de la fuente de contraste
  y devuelve las métricas del apartado 7.7.3: error relativo medio, error
  absoluto medio, RMSE y porcentaje de puntos dentro de la banda.
- Los diagramas de paridad se generan desde ese módulo, de modo que rehacerlos
  tras un cambio en el modelo sea inmediato.

**Fijar los criterios ANTES.** Los umbrales de aceptación de la tabla 7.5 deben
estar escritos en el código de validación antes de ejecutarlo por primera vez.
Fijarlos después de ver los resultados es una debilidad metodológica grave y
perfectamente detectable en el historial de git, que en este caso jugaría en tu
contra.

> **Nota (estado del repo).** El módulo `validation/` no existe. Por el argumento
> del párrafo anterior conviene adelantarlo: crear `validation/` con los umbrales
> de la tabla 7.5 escritos —aunque todavía sin casos— deja fechada la decisión en
> el historial de git, que es justo la defensa que este apartado busca. Hacerlo
> en el orden 8 del resumen la desaprovecha.

---

## Resumen del orden de trabajo

|  | Estado | Tarea | Requiere código |
| --- | --- | --- | --- |
| 1 | ✅ | Repositorio, entorno, tests en verde | No |
| 2 | ✅ | ~~Cerrar modo M-5~~ (D-1), ~~decisión sobre R-744~~ (D-2), ~~puntos del compresor~~ (D-3) | No |
| 3 | ❌ | Sustituir correlaciones provisionales, empezando por la ebullición | Sí |
| 4 | ❌ | `air_hx.py` con desescarche | Sí |
| 5 | ❌ | `four_way_valve.py` | Sí |
| 6 | ❌ | `circuit.py` con el lazo externo y las verificaciones | Sí |
| 7 | ❌ | Backend tabular con su error cuantificado | Sí |
| 8 | ❌ | Módulo de validación con umbrales fijados de antemano | Sí |
| 9 | ❌ | Campañas de simulación con procedencia adjunta | Sí |
| 10 | ❌ | Figuras para los capítulos 5, 11, 12, 13 y 14 | Sí |
| 11 | ⛔ | ~~**Segunda fase (D-2): R-744.**~~ **RETIRADA el 21/09/2026.** El R-744 sale del conjunto comparativo; ver D-2 | — |

### Sobre el orden

La numeración es en serie, pero la única dependencia real era la de la tarea 6
respecto de la 2, y quedó resuelta al cerrar D-1. **Con D-1, D-2 y D-3 cerradas
no queda ninguna tarea bloqueada:** las 3 a 7 pueden avanzar en cualquier orden,
y solo el criterio de impacto —el de la tabla G.2— aconseja empezar por la
correlación de ebullición. La 8 conviene adelantarla por el motivo explicado en
la Fase 6.

La única decisión que conserva riesgo abierto es D-3, por ser una hipótesis y no
un dato: si el catálogo del compresor da menos de 20 puntos, o menos
temperaturas de descarga de las previstas, hay que reabrirla y aplicar el plan
de contingencia allí descrito.

Las tareas 3 a 10 corresponden a la primera fase de D-2, la de los tres
refrigerantes sin R-744. La 11 es la segunda fase y se aborda al cerrar la
primera, pero condiciona desde ya cómo se escriben la 6 y la 9 (ver D-2).
