"""Tests de integración del router de usuarios (TestClient + dependency_overrides).

No requiere MongoDB: `obtener_repositorio_usuarios` se sobreescribe con
`FakeRepositorioUsuarios` para cada test, y el lifespan real de la app
(que sí abre una conexión Mongo, Paso 5) se sobreescribe con un no-op.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario
from app.deps import obtener_repositorio_usuarios
from app.main import app
from app.usuarios.dominio import Usuario
from tests.fakes import FakeRepositorioUsuarios
from tests.lifespan import lifespan_vacio

_PASSWORD_SUPERVISOR = "clave-segura-1"
_PASSWORD_TECNICO = "clave-segura-2"


@pytest.fixture
def repositorio() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def cliente(repositorio: FakeRepositorioUsuarios) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repositorio
    lifespan_original = app.router.lifespan_context
    app.router.lifespan_context = lifespan_vacio
    with TestClient(app) as cliente_de_prueba:
        yield cliente_de_prueba
    app.dependency_overrides.clear()
    app.router.lifespan_context = lifespan_original


@pytest.fixture
def supervisor(repositorio: FakeRepositorioUsuarios) -> Usuario:
    supervisor = Usuario(
        "Sofía Jefa",
        "sofia@comunicarlos.com.ar",
        obtener_password_hash(_PASSWORD_SUPERVISOR),
        RolUsuario.SUPERVISOR,
    )
    repositorio.guardar(supervisor)
    return supervisor


@pytest.fixture
def tecnico(repositorio: FakeRepositorioUsuarios) -> Usuario:
    tecnico = Usuario(
        "Beto Técnico",
        "beto@comunicarlos.com.ar",
        obtener_password_hash(_PASSWORD_TECNICO),
        RolUsuario.TECNICO,
    )
    repositorio.guardar(tecnico)
    return tecnico


def _token_de(cliente: TestClient, email: str, password: str) -> str:
    respuesta = cliente.post("/usuarios/login", data={"username": email, "password": password})
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLogin:
    def test_login_exitoso_devuelve_un_token_bearer(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "sofia@comunicarlos.com.ar", "password": _PASSWORD_SUPERVISOR},
        )

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["token_type"] == "bearer"
        assert respuesta.json()["access_token"]

    def test_login_con_password_incorrecta_devuelve_401(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "sofia@comunicarlos.com.ar", "password": "incorrecta"},
        )

        # Assert
        assert respuesta.status_code == 401

    def test_login_con_email_inexistente_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login", data={"username": "nadie@x.com", "password": "loquesea"}
        )

        # Assert
        assert respuesta.status_code == 401


class TestPerfilPropio:
    def test_me_devuelve_el_perfil_del_usuario_autenticado(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.get("/usuarios/me", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["email"] == "sofia@comunicarlos.com.ar"
        assert "password" not in respuesta.json()

    def test_sin_token_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.get("/usuarios/me")

        # Assert
        assert respuesta.status_code == 401


class TestCrearUsuario:
    def test_supervisor_puede_crear_usuarios(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "Nuevo Técnico",
                "email": "nuevo@comunicarlos.com.ar",
                "password": "clave12345",
                "rol": "TECNICO",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["rol"] == "TECNICO"
        assert respuesta.json()["activo"] is True

    def test_rol_no_supervisor_devuelve_403(self, cliente: TestClient, tecnico: Usuario) -> None:
        # Arrange
        token = _token_de(cliente, "beto@comunicarlos.com.ar", _PASSWORD_TECNICO)

        # Act
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "otro@x.com",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 403

    def test_email_duplicado_devuelve_409(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: intenta reusar el email del técnico ya existente
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "beto@comunicarlos.com.ar",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 409

    def test_operador_con_email_no_corporativo_devuelve_400(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: Operador/Técnico/Supervisor requieren "@comunicarlos.com.ar"
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 400

    def test_solicitante_con_email_no_corporativo_se_crea_sin_error(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: el Solicitante no está sujeto a la restricción de dominio corporativo
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "SOLICITANTE",
                "servicios_suscriptos": ["TELEVISION"],
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201

    def test_solicitante_sin_servicios_suscriptos_devuelve_400(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: el Solicitante debe suscribirse a al menos un servicio
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "SOLICITANTE",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 400


class TestAdministracionDeUsuarios:
    def test_desactivar_usuario_via_endpoint(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(f"/usuarios/{tecnico.id}/desactivar", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["activo"] is False

    def test_desactivar_usuario_inexistente_devuelve_404(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(f"/usuarios/{uuid.uuid4()}/desactivar", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 404

    def test_listar_usuarios_requiere_supervisor(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.get("/usuarios", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 2

    def test_cambiar_rol_via_endpoint(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(
            f"/usuarios/{tecnico.id}/rol",
            json={"nuevo_rol": "OPERADOR"},
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["rol"] == "OPERADOR"


class TestVerificacionDeSalud:
    def test_health_no_requiere_autenticacion(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.get("/health")

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok"}
