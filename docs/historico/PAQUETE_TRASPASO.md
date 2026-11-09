# Paquete de traspaso — capítulo 10 → implementación

> Nota de procedencia. Este texto era el `README.md` del paquete comprimido con el que se
> trasladó el capítulo 10 al repositorio. Al descomprimirlo en la raíz sustituyó al README
> del proyecto, y se ha recuperado aquí, que es donde encaja: describe el contenido del
> paquete, no el repositorio. El README del repositorio se restauró desde `339d9c3`.
>
> Las denominaciones de los intercambiadores de placas que aparecen más abajo son las
> erróneas del paquete original. Las correctas son **AlfaNova 27-30H** (climatización) y
> **AlfaNova 16-10H** (desrecalentador), conforme a la tabla 10.6. Se conservan tal cual
> por fidelidad al documento de origen.


Contenido para dar a Claude Code el contexto del modelo formulado en el capítulo 10 de la
tesis. Descomprimir en la raíz del repositorio del modelo.

```
CLAUDE.md                        contexto permanente; Claude Code lo lee siempre
docs/
  cap10_modelo.md                el capítulo completo en Markdown
  secciones/                     el capítulo troceado por apartados
    INDICE.md
    10_1.md … 10_14.md
  PENDIENTES.md                  datos que faltan y retoques hacia atrás
data/
  compresor_bock_f2.yaml         geometría + 9 parámetros identificados
  placas_alfanova.yaml           AlfaNova 76 y AlfaNova 16
  bateria_frimetal_cbn21.yaml    geometría reconstruida + punto de ficha
tests/
  test_referencia.py             valores de referencia del capítulo 10
```

## Primeros pasos sugeridos

Abrir Claude Code en la raíz del repositorio y empezar por una **auditoría**, no por escribir
código. La primera versión del modelo es anterior a tres desarrollos del capítulo 10 —la
identificación del compresor (§10.4.5), la selección de los intercambiadores de placas
(§10.5.3) y el §10.6 completo del intercambiador de aire— y puede arrastrar supuestos
superados.

Una primera petición razonable:

> Lee CLAUDE.md y docs/secciones/INDICE.md. Después recorre el código existente y dime, por
> cada módulo: qué apartado del capítulo 10 implementa, qué supuestos contiene que ya no
> coinciden con el capítulo, y qué está sin implementar. No cambies nada todavía.

Después, ejecutar `pytest tests/test_referencia.py -v`. Los tests puramente geométricos y
aritméticos pasan sin el modelo; el resto están marcados como `skip` y van conectándose
conforme existan los submodelos. Son las verificaciones que el §10.13.5 exige automatizadas.

## Lo que no está aquí

Los `null` de `data/*.yaml` son datos que no existen todavía, no huecos que rellenar. El más
importante es la **curva del ventilador**: sin ella el consumo queda indeterminado entre 296
y 720 W, que es una banda demasiado ancha en el denominador del EER para sostener la
comparación con equipos comerciales que exige H1.
