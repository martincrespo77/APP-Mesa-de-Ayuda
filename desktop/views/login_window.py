"""Ventana de login: autenticación real o Modo Demostración (doc05)."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from desktop.api_client import (
    ApiClienteDemo,
    ApiClienteHttp,
    ClienteApi,
    ClienteApiError,
    CredencialesInvalidasError,
)

URL_BASE_POR_DEFECTO = "http://localhost:8000"

_AYUDA_DEMO = (
    "Demo: usá cualquiera de estos emails con la contraseña 'demo1234':\n"
    "solicitante@demo.coop, operador@demo.coop, tecnico@demo.coop, supervisor@demo.coop"
)


class LoginWindow(QWidget):
    """Pantalla de autenticación: real (httpx contra la API) o Modo Demostración.

    Emite `sesion_iniciada(cliente, usuario)` una vez autenticado; quien
    la instancie (`desktop/main.py`) decide qué hacer con esa sesión
    (típicamente, abrir `MainWindow`).
    """

    sesion_iniciada = pyqtSignal(object, object)  # (ClienteApi, UsuarioDTO)

    def __init__(
        self,
        url_base: str = URL_BASE_POR_DEFECTO,
        demo_inicial: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._url_base = url_base

        self.setWindowTitle("Mesa de Ayuda - Cooperativa Comunicarlos")
        self.setMinimumWidth(380)

        titulo = QLabel("Mesa de Ayuda")
        titulo.setObjectName("titulo")

        self._campo_email = QLineEdit()
        self._campo_email.setPlaceholderText("Email")

        self._campo_password = QLineEdit()
        self._campo_password.setPlaceholderText("Contraseña")
        self._campo_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._campo_password.returnPressed.connect(self._intentar_ingresar)

        self._checkbox_demo = QCheckBox("Modo Demostración (sin backend)")
        self._checkbox_demo.setChecked(demo_inicial)
        self._checkbox_demo.toggled.connect(self._actualizar_ayuda)

        self._etiqueta_ayuda = QLabel()
        self._etiqueta_ayuda.setObjectName("subtitulo")
        self._etiqueta_ayuda.setWordWrap(True)

        self._etiqueta_error = QLabel()
        self._etiqueta_error.setObjectName("error")
        self._etiqueta_error.setWordWrap(True)
        self._etiqueta_error.hide()

        self._boton_ingresar = QPushButton("Iniciar sesión")
        self._boton_ingresar.clicked.connect(self._intentar_ingresar)

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        layout.addWidget(titulo)
        layout.addWidget(self._campo_email)
        layout.addWidget(self._campo_password)
        layout.addWidget(self._checkbox_demo)
        layout.addWidget(self._etiqueta_ayuda)
        layout.addWidget(self._etiqueta_error)
        layout.addWidget(self._boton_ingresar)
        self.setLayout(layout)

        self._actualizar_ayuda(demo_inicial)

    def _actualizar_ayuda(self, demo_activo: bool) -> None:
        texto = _AYUDA_DEMO if demo_activo else f"Conectando a {self._url_base}"
        self._etiqueta_ayuda.setText(texto)

    def _intentar_ingresar(self) -> None:
        self._etiqueta_error.hide()
        email = self._campo_email.text().strip()
        password = self._campo_password.text()
        if not email or not password:
            self._mostrar_error("Completá email y contraseña.")
            return

        cliente: ClienteApi
        if self._checkbox_demo.isChecked():
            cliente = ApiClienteDemo()
        else:
            cliente = ApiClienteHttp(base_url=self._url_base)
            if not cliente.verificar_salud():
                self._mostrar_error(
                    f"No se pudo conectar a la API en {self._url_base}. "
                    "¿Está corriendo el backend? Podés activar el Modo Demostración."
                )
                return

        try:
            usuario = cliente.iniciar_sesion(email, password)
        except CredencialesInvalidasError as error:
            self._mostrar_error(str(error))
            return
        except ClienteApiError as error:
            self._mostrar_error(f"Error al iniciar sesión: {error}")
            return

        self._campo_password.clear()
        self.sesion_iniciada.emit(cliente, usuario)

    def _mostrar_error(self, mensaje: str) -> None:
        self._etiqueta_error.setText(mensaje)
        self._etiqueta_error.show()
