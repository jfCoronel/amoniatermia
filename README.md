# amoniatermia

Modelo de simulación de una bomba de calor reversible aire-agua de amoníaco (R-717) de baja
carga para vivienda, de unos 10 kW, con recuperación del calor de descarga para agua caliente
sanitaria (ACS) y cinco modos de operación. Es el modelo de la tesis doctoral *Bomba de calor
reversible de R-717 de baja carga para climatización residencial y producción de ACS: diseño,
simulación y retos*, de Ignacio García Sánchez, dirigida por Juan Francisco Coronel Toro
(Universidad de Sevilla, 2026).

## Qué contiene

| Carpeta | Contenido |
|---|---|
| `src/amoniatermia/` | El modelo: propiedades (CoolProp, `AbstractState` reutilizado), correlaciones intercambiables registradas por nombre, componentes (compresor, intercambiadores de placas, batería de aire, válvula, líneas), circuito de los cinco modos y lazo de resolución, indicadores energéticos y exergéticos, envolvente del compresor, validación, incertidumbre, campañas y rendimiento estacional según UNE-EN 14825. |
| `data/` | Geometría y parámetros de los componentes y datos de los fabricantes transcritos a YAML y CSV. Un `null` es un dato que no existe: el modelo falla si un cálculo lo necesita, en lugar de suponer un valor. |
| `notebooks/` | Cuadernos (formato jupytext) que calculan las cifras de cada capítulo de la tesis y las escriben en `docs/cifras_*.md` y `docs/figuras/`. |
| `tests/` | Pruebas automáticas: verificación de balances, valores de referencia del modelo y casos de solución conocida. |
| `docs/` | Hojas de cifras generadas, figuras, decisiones de modelado fechadas (`DECISIONES_*.md`) y documentos de trabajo. |
| `herramientas/compresor/` | Ajuste de los polinomios de UNE-EN 12900 del compresor y ensayo del modelo semiempírico descartado. |

Las unidades son SI estrictas en todo el interior del modelo; la conversión a bar, °C y kW se
hace solo en la frontera.

## Instalación y uso

El proyecto usa [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run pytest -q
uv run python notebooks/03_cifras_capitulo_9.py
```

Los cuadernos de los capítulos 11 a 13 resuelven miles de puntos de operación y tardan horas;
guardan los resultados en `results/` (no incluido en el repositorio) y, con `--reutilizar`,
regeneran las hojas sin volver a resolver.

## Datos de terceros

- **Componentes.** Los datos proceden de las fichas técnicas y del software de selección de
  sus fabricantes (Bock, Copeland, Alfa Laval y Frimetal). El repositorio incluye solo los
  valores numéricos transcritos, con su procedencia en cada fichero de `data/`; los documentos
  originales de los fabricantes no se distribuyen.
- **Muestra de mercado.** `data/mercado/hplib_database.csv` es la base de datos hplib (Tjaden,
  Hoops y Rösken, FZJ-IEK3-VSA; doi:10.5281/zenodo.5521597), extraída del Heat Pump Keymark,
  con licencia CC BY 4.0.
- **Climas.** `data/clima/` contiene los climas de referencia del Código Técnico de la
  Edificación (DB-HE), publicados por el Ministerio.
- **Normas.** Las normas UNE se consultaron con licencia institucional y no se incluyen.

## Uso de inteligencia artificial

El código se desarrolló con el apoyo del asistente de inteligencia artificial Claude
(Anthropic), bajo la supervisión de los autores, que establecieron las decisiones de modelado
y revisaron los resultados. Las cifras son reproducibles a partir del código y los datos, y
las pruebas automáticas verifican los valores de referencia.

## Licencia

El código se distribuye con licencia [MIT](LICENSE). La documentación, las hojas de cifras y las
figuras de `docs/` se distribuyen con licencia CC BY 4.0. Los datos de terceros conservan sus
propias condiciones, indicadas arriba.

## Cómo citar

García Sánchez, I. (2026). *Bomba de calor reversible de R-717 de baja carga para climatización
residencial y producción de ACS: diseño, simulación y retos*. Tesis doctoral, Universidad de
Sevilla. Director: J. F. Coronel Toro.
