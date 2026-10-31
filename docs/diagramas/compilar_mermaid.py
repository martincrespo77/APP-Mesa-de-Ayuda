"""Recompila los visores interactivos `.html` a partir de su fuente `.mmd`.

Los visores (`diagrama_clases.html`, `diagrama_secuencia.html`, ...) son una
plantilla fija (HTML + CSS + JS, sin dependencias externas) que lee tres
constantes JSON embebidas: `nodesData`, `connectionsData` y `subgraphsData`.
Este script parsea el subconjunto de Mermaid `graph TD` que usan las fuentes
(subgraphs, nodos `id["label"]`, aristas `-->` / `==>` / `-.->` / `---` con
etiqueta opcional, `classDef` y `class`) y reemplaza SOLO esas tres líneas,
dejando el resto de la plantilla intacto.

Layout: una columna por subgraph (en el orden de la fuente) y un nodo cada
140 px dentro de la columna; los nodos sin subgraph van a "Otros Componentes".
Cada nodo se puede reubicar arrastrándolo en el visor.

Uso (desde la raíz del repo):
    python docs/diagramas/compilar_mermaid.py docs/diagramas/diagrama_clases.mmd
    python docs/diagramas/compilar_mermaid.py docs/diagramas/diagrama_secuencia.mmd
El `.html` destino es el mismo nombre con extensión `.html`.
"""

import html
import json
import re
import sys
from pathlib import Path

_SUBGRAPH = re.compile(r'^subgraph\s+(\w+)\["(.*)"\]\s*$')
_NODO = re.compile(r'^(\w+)\["(.*)"\]\s*$')
_ARISTA = re.compile(r'^(\w+)\s*(==>|-\.->|-->|---)\s*(?:\|"(.*?)"\|)?\s*(\w+)\s*$')
_CLASSDEF = re.compile(r"^classDef\s+(\w+)\s+(.*)$")
_CLASS = re.compile(r"^class\s+([\w,]+)\s+(\w+)\s*$")
_TIPO_ARISTA = {"==>": "thick", "-->": "arrow", "-.->": "dashed", "---": "line"}
_COLOR_DEFAULT = {"bg": "#1f2937", "border": "#6c757d", "text": "#e5e7eb"}

_X0, _Y0, _PASO_COLUMNA, _PASO_NODO = 65, 45, 560, 140


def _parsear(fuente: str) -> tuple[list[dict], list[dict], list[dict]]:
    subgraphs: list[dict] = []
    nodos: dict[str, dict] = {}
    aristas: list[tuple[str, str, str, str]] = []
    estilos: dict[str, dict[str, str]] = {}
    clase_de: dict[str, str] = {}
    actual = "General"
    for cruda in fuente.splitlines():
        linea = cruda.strip()
        if not linea or linea.startswith("%%") or linea.startswith("graph "):
            continue
        if m := _SUBGRAPH.match(linea):
            actual = m.group(1)
            subgraphs.append({"id": actual, "title": m.group(2)})
        elif linea == "end":
            actual = "General"
        elif m := _ARISTA.match(linea):
            aristas.append((m.group(1), m.group(4), _TIPO_ARISTA[m.group(2)], m.group(3) or ""))
        elif m := _NODO.match(linea):
            nodos[m.group(1)] = {"id": m.group(1), "raw_label": m.group(2), "subgraph": actual}
        elif m := _CLASSDEF.match(linea):
            props = dict(p.split(":", 1) for p in m.group(2).split(",") if ":" in p)
            estilos[m.group(1)] = {
                "bg": props.get("fill", _COLOR_DEFAULT["bg"]),
                "border": props.get("stroke", _COLOR_DEFAULT["border"]),
                "text": props.get("color", _COLOR_DEFAULT["text"]),
            }
        elif m := _CLASS.match(linea):
            for nodo_id in m.group(1).split(","):
                clase_de[nodo_id] = m.group(2)
        else:
            raise ValueError(f"Línea Mermaid no soportada: {linea!r}")

    for origen, destino, _, _ in aristas:
        for nodo_id in (origen, destino):
            if nodo_id not in nodos:
                raise ValueError(f"La arista usa el nodo '{nodo_id}', que no está declarado.")

    if any(n["subgraph"] == "General" for n in nodos.values()):
        subgraphs.append({"id": "General", "title": "Otros Componentes"})

    lista_nodos: list[dict] = []
    for columna, sg in enumerate(subgraphs):
        miembros = [n for n in nodos.values() if n["subgraph"] == sg["id"]]
        sg.update(
            x=_X0 + columna * _PASO_COLUMNA,
            y=_Y0,
            width=350,
            height=len(miembros) * _PASO_NODO + 55,
        )
        for fila, nodo in enumerate(miembros):
            color = estilos.get(clase_de.get(nodo["id"], ""), _COLOR_DEFAULT)
            lista_nodos.append(_nodo(nodo, sg["x"] + 25, _Y0 + 35 + fila * _PASO_NODO, color))

    pares: dict[tuple[str, str], list[dict]] = {}
    conexiones: list[dict] = []
    for indice, (origen, destino, tipo, etiqueta) in enumerate(aristas):
        conexion = {
            "from": origen,
            "to": destino,
            "type": tipo,
            "label": etiqueta,
            "id": f"conn_{indice}",
            "is_self": origen == destino,
        }
        pares.setdefault((origen, destino), []).append(conexion)
        conexiones.append(conexion)
    for grupo in pares.values():
        for posicion, conexion in enumerate(grupo):
            conexion["pair_index"] = posicion
            conexion["pair_total"] = len(grupo)
    orden = ["from", "to", "type", "label", "id", "pair_index", "pair_total", "is_self"]
    conexiones = [{k: c[k] for k in orden} for c in conexiones]
    return lista_nodos, conexiones, subgraphs


def _nodo(nodo: dict, x: int, y: int, color: dict[str, str]) -> dict:
    partes = [p.strip() for p in nodo["raw_label"].split("<br/>")]
    nombre, subtitulo = partes[0], " · ".join(partes[1:])

    def e(texto: str) -> str:
        return html.escape(texto, quote=False).replace('"', "&quot;")

    bloque_subtitulo = (
        f'<div class="comp-subtitle" title="{e(subtitulo)}">{e(subtitulo)}</div>'
        if subtitulo
        else ""
    )

    tarjeta = f"""
            <div class="comp-card shape-rect" style="border-color:{color['border']};">
                <div class="comp-header" style="background:{color['bg']};">
                    <span class="comp-icon">📦</span>
                    <div class="comp-title-group">
                        <span class="comp-id">{nodo['id']}</span>
                        <span class="comp-name" title="{e(nombre)}">{e(nombre)}</span>
                    </div>
                </div>
                <div class="comp-body">
                    {bloque_subtitulo}
                    <div class="comp-meta-row">
                        <span class="comp-sub">{nodo['subgraph']}</span>
                        <span class="comp-tag">rect</span>
                    </div>
                </div>
            </div>
            """
    return {
        "id": nodo["id"],
        "title": " · ".join(partes),
        "raw_label": nodo["raw_label"],
        "shape": "rect",
        "subgraph": nodo["subgraph"],
        "custom_style": dict(color),
        "x": x,
        "y": y,
        "meta": {},
        "color": {"border": color["border"], "bg": color["bg"], "text": color["text"]},
        "html": tarjeta,
    }


def compilar(ruta_mmd: Path) -> Path:
    nodos, conexiones, subgraphs = _parsear(ruta_mmd.read_text(encoding="utf-8"))
    ruta_html = ruta_mmd.with_suffix(".html")
    # newline="" lee sin traducir saltos; al escribir se usa el fin de línea
    # que ya tenía la plantilla (LF en git, CRLF en un checkout con autocrlf).
    with ruta_html.open(encoding="utf-8", newline="") as archivo:
        contenido = archivo.read()
    salto = "\r\n" if "\r\n" in contenido else "\n"
    lineas = contenido.replace("\r\n", "\n").split("\n")
    datos = {"nodesData": nodos, "connectionsData": conexiones, "subgraphsData": subgraphs}
    reemplazadas = set()
    for i, linea in enumerate(lineas):
        for nombre, valor in datos.items():
            if linea.startswith(f"const {nombre} = "):
                lineas[i] = f"const {nombre} = {json.dumps(valor, ensure_ascii=False)};"
                reemplazadas.add(nombre)
    if reemplazadas != set(datos):
        raise ValueError(f"{ruta_html}: no se encontraron {set(datos) - reemplazadas}.")
    with ruta_html.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(salto.join(lineas))
    print(f"{ruta_html}: {len(nodos)} nodos, {len(conexiones)} conexiones, {len(subgraphs)} grupos")
    return ruta_html


if __name__ == "__main__":
    for argumento in sys.argv[1:]:
        compilar(Path(argumento))
