"""Hojas de cifras de los capitulos, con su procedencia. §6.12.

Cada capitulo de resultados tiene un cuaderno que calcula sus cifras y las
escribe en `docs/cifras_capitulo_N.md`: es la fuente unica de numeros para
redactar. Este modulo es lo comun a esos cuadernos, para que ninguno repita los
dos errores que ya se han cometido una vez:

- leer la revision del codigo AL FINAL, cuando el propio cuaderno ya ha escrito
  sus ficheros y el arbol aparece sucio (cuaderno 04, 28/09/2026);
- no escribir nada hasta terminar, de modo que una ejecucion larga interrumpida
  no deja ninguna cifra (cuaderno 03, 25/09/2026).

    hoja = HojaDeCifras("docs/cifras_capitulo_10.md", "Cifras del capítulo 10",
                        "notebooks/05_cifras_capitulo_10.py")
    hoja.seccion("malla", "### Tabla 10.1 ...\\n\\n" + tabla(cab, filas))
"""
from __future__ import annotations

import time
from pathlib import Path

import CoolProp

from .props import git_revision


def tabla(cabecera, filas) -> str:
    """Tabla en Markdown."""
    s = "| " + " | ".join(map(str, cabecera)) + " |\n"
    s += "|" + "---|" * len(cabecera) + "\n"
    return s + "".join("| " + " | ".join(map(str, f)) + " |\n" for f in filas)


class HojaDeCifras:
    """Fichero de cifras que se reescribe tras cada seccion."""

    def __init__(self, ruta, titulo: str, generador: str):
        self.ruta = Path(ruta)
        self.titulo = titulo
        self.generador = generador
        # ANTES de escribir nada: ver la cabecera del modulo.
        self.revision = git_revision()
        self.inicio = time.strftime("%Y-%m-%d %H:%M")
        self.secciones: dict = {}

    @property
    def reproducible(self) -> bool:
        return not self.revision.endswith("-dirty") and self.revision != "desconocida"

    def cabecera(self) -> str:
        L = [f"# {self.titulo}", "",
             f"Generado por `{self.generador}`. **No editar a mano**: se vuelve a "
             "ejecutar cuando el modelo cambia.", "",
             f"- Revisión del código: `{self.revision}`",
             f"- CoolProp {CoolProp.__version__}",
             f"- Generado: {self.inicio}",
             f"- Secciones: {', '.join(self.secciones) or '—'}", ""]
        if not self.reproducible:
            L += ["> **Aviso**: árbol de trabajo con cambios sin confirmar; estas "
                  "cifras no son reproducibles tal cual (§6.12).", ""]
        return "\n".join(L)

    def seccion(self, nombre: str, texto: str) -> None:
        """Añade o sustituye una seccion y reescribe el fichero."""
        self.secciones[nombre] = texto
        cuerpo = "\n\n".join(f"## {k}\n\n{v}" for k, v in self.secciones.items())
        self.ruta.write_text(self.cabecera() + "\n" + cuerpo + "\n", encoding="utf-8")
