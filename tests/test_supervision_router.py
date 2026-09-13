"""Tests de integración del router de supervisión (TestClient + overrides).

No requiere MongoDB: los repositorios concretos se sobreescriben con
`Fake*` para cada test, y el lifespan real de la app se sobreescribe con
un no-op (mismo patrón que `test_usuarios_router.py`).
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.deps import obtener_repositorio_supervision, obtener_repositorio_usuarios
from app.main import app
from app.usuarios.dominio import Usuario
from tests.fakes import FakeRepositorioSupervision, FakeRepositorioUsuarios
from tests.lifespan import lifespan_vacio

_PASSWORD = "clave-segura-1"


@pytest.fixture
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def repo_supervision() -> FakeRepositorioSupervision:
    return FakeRepositorioSupervision()


@pytest.fixture
def cliente(
    repo_usuarios: FakeRepositorioUsuarios, repo_supervision: FakeRepositorioSupervision
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo_usuarios
    app.dependency_overrides[obtener_repositorio_supervision] = lambda: repo_supervision
    lifespan_original = app.router.lifespan_context
    app.router.lifespan_context = lifespan_vacio
    with TestClient(app) as cliente_de_prueba:
        yield cliente_de_prueba
    app.dependency_overrides.clear()
    app.router.lifespan_context = lifespan_original


def _crear_usuario(repo: FakeRepositorioUsuarios, email: str, rol: RolUsuario) -> Usuario:
    servicios = (
        frozenset({ServicioComunicarlos.INTERNET_BANDA_ANCHA})
        if rol == RolUsuario.SOLICITANTE
        else frozenset()
    )
    usuario = Usuario(
        email.split("@")[0],
        email,
        obtener_password_hash(_PASSWORD),
        rol,
        servicios_suscriptos=servicios,
    )
    repo.guardar(usuario)
    return usuario


def _token_de(cliente: TestClient, email: str) -> str:
    respuesta = cliente.post("/usuarios/login", data={"username": email, "password": _PASSWORD})
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAsignarSupervision:
    def test_supervisor_puede_asignar_un_operador(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        operador = _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.post(
            "/supervisiones",
            json={"supervisado_id": str(operador.id)},
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["supervisado_id"] == str(operador.id)

    def test_rol_no_supervisor_devuelve_403(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        operador = _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "op@comunicarlos.com.ar")

        # Act
        respuesta = cliente.post(
            "/supervisiones",
            json={"supervisado_id": str(operador.id)},
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 403

    def test_asignar_a_un_solicitante_devuelve_400(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        solicitante = _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.post(
            "/supervisiones",
            json={"supervisado_id": str(solicitante.id)},
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 400

    def test_asignar_duplicado_devuelve_409(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        operador = _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")
        cliente.post(
            "/supervisiones", json={"supervisado_id": str(operador.id)}, headers=_headers(token)
        )

        # Act
        respuesta = cliente.post(
            "/supervisiones", json={"supervisado_id": str(operador.id)}, headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 409


class TestListarYRemover:
    def test_listar_mis_supervisados(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        operador = _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")
        cliente.post(
            "/supervisiones", json={"supervisado_id": str(operador.id)}, headers=_headers(token)
        )

        # Act
        respuesta = cliente.get("/supervisiones", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1

    def test_remover_supervision(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        operador = _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")
        cliente.post(
            "/supervisiones", json={"supervisado_id": str(operador.id)}, headers=_headers(token)
        )

        # Act
        respuesta = cliente.delete(f"/supervisiones/{operador.id}", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 204
        listado = cliente.get("/supervisiones", headers=_headers(token))
        assert listado.json() == []

    def test_sin_token_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.get("/supervisiones")

        # Assert
        assert respuesta.status_code == 401

    def test_asignar_supervisado_inexistente_devuelve_404(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.post(
            "/supervisiones", json={"supervisado_id": str(uuid.uuid4())}, headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 404
