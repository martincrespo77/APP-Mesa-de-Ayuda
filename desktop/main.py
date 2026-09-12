"""Punto de entrada del cliente de escritorio (doc05).

Uso:
    uv run python -m desktop.main          # modo conectado (localhost:8000)
    uv run python -m desktop.main --demo   # Modo Demostración offline
"""

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from desktop.api_client import ClienteApi
from desktop.models import UsuarioDTO
from desktop.styles import HOJA_DE_ESTILOS
from desktop.views.login_window import URL_BASE_POR_DEFECTO, LoginWindow
from desktop.views.main_window import MainWindow


def _parsear_argumentos(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mesa de Ayuda - Cliente de escritorio")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Arranca en Modo Demostración (sin backend, datos sintéticos).",
    )
    parser.add_argument(
        "--url",
        default=URL_BASE_POR_DEFECTO,
        help=f"URL base de la API en Modo Conectado (por defecto: {URL_BASE_POR_DEFECTO}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Arranca la aplicación Qt. Devuelve el código de salida del event loop."""
    argumentos = _parsear_argumentos(sys.argv[1:] if argv is None else argv)

    app = QApplication(sys.argv)
    app.setStyleSheet(HOJA_DE_ESTILOS)

    login = LoginWindow(url_base=argumentos.url, demo_inicial=argumentos.demo)
    # Sin padre Qt, MainWindow necesita una referencia externa que la
    # mantenga viva: si no, Python la recolecta apenas termina `_al_iniciar_sesion`.
    ventana_principal: list[MainWindow] = []

    def _al_iniciar_sesion(cliente: ClienteApi, usuario: UsuarioDTO) -> None:
        principal = MainWindow(cliente, usuario)
        ventana_principal.append(principal)
        principal.show()
        login.close()

    login.sesion_iniciada.connect(_al_iniciar_sesion)
    login.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
