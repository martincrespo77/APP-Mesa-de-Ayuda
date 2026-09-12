"""Hoja de estilos QSS: tema oscuro global de la aplicación (doc05).

Se inyecta una única vez en `QApplication` (`desktop/main.py`). Las
funciones `color_para_*` exponen los mismos colores semánticos para
pintar badges puntuales (estado, severidad) donde QSS por selector no
alcanza (p. ej. el texto de una celda de `QTableWidget`).
"""

from desktop.models import EstadoRequerimiento, Severidad

# -- Paleta (doc05: fondos oscuros, acentos violeta/azul) ---------------------

_FONDO = "#1e1e2e"
_TARJETA = "#252538"
_ACENTO_VIOLETA = "#7c3aed"
_ACENTO_VIOLETA_HOVER = "#6d28d9"
_ACENTO_AZUL = "#3b82f6"
_TEXTO = "#e2e2f0"
_TEXTO_SECUNDARIO = "#9a9ab0"
_BORDE = "#3a3a52"

_VERDE = "#22c55e"
_NARANJA = "#f59e0b"
_ROJO = "#ef4444"
_GRIS = "#6b7280"

HOJA_DE_ESTILOS = f"""
QWidget {{
    background-color: {_FONDO};
    color: {_TEXTO};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {_BORDE};
    background-color: {_TARJETA};
}}

QTabBar::tab {{
    background-color: {_FONDO};
    color: {_TEXTO_SECUNDARIO};
    padding: 8px 18px;
    border: 1px solid {_BORDE};
    border-bottom: none;
}}

QTabBar::tab:selected {{
    background-color: {_TARJETA};
    color: {_TEXTO};
    border-top: 2px solid {_ACENTO_VIOLETA};
}}

QPushButton {{
    background-color: {_ACENTO_VIOLETA};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {_ACENTO_VIOLETA_HOVER};
}}

QPushButton:disabled {{
    background-color: {_BORDE};
    color: {_TEXTO_SECUNDARIO};
}}

QPushButton#botonSecundario {{
    background-color: transparent;
    border: 1px solid {_ACENTO_AZUL};
    color: {_ACENTO_AZUL};
}}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {{
    background-color: {_TARJETA};
    border: 1px solid {_BORDE};
    border-radius: 4px;
    padding: 6px;
    color: {_TEXTO};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {{
    border: 1px solid {_ACENTO_AZUL};
}}

QTableWidget {{
    background-color: {_TARJETA};
    gridline-color: {_BORDE};
    border: 1px solid {_BORDE};
    selection-background-color: {_ACENTO_VIOLETA};
}}

QHeaderView::section {{
    background-color: {_FONDO};
    color: {_TEXTO_SECUNDARIO};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {_BORDE};
}}

QLabel#titulo {{
    font-size: 20px;
    font-weight: 700;
}}

QLabel#subtitulo {{
    color: {_TEXTO_SECUNDARIO};
}}

QLabel#error {{
    color: {_ROJO};
}}
"""

_COLOR_POR_ESTADO: dict[EstadoRequerimiento, str] = {
    EstadoRequerimiento.ABIERTO: _ACENTO_AZUL,
    EstadoRequerimiento.EN_ANALISIS: _NARANJA,
    EstadoRequerimiento.EN_PROGRESO: _NARANJA,
    EstadoRequerimiento.RESUELTO: _VERDE,
    EstadoRequerimiento.CERRADO: _VERDE,
    EstadoRequerimiento.CANCELADO: _GRIS,
}

_COLOR_POR_SEVERIDAD: dict[Severidad, str] = {
    Severidad.BAJA: _VERDE,
    Severidad.MEDIA: _NARANJA,
    Severidad.ALTA: _ROJO,
    Severidad.CRITICA: _ROJO,
}


def color_para_estado(estado: EstadoRequerimiento) -> str:
    """Color semántico del estado (doc05: verde=resuelto/cerrado, naranja=en progreso)."""
    return _COLOR_POR_ESTADO[estado]


def color_para_severidad(severidad: Severidad) -> str:
    """Color semántico de la severidad (doc05: rojo=alta/crítica)."""
    return _COLOR_POR_SEVERIDAD[severidad]
