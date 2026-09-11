"""Tests de integración del router de requerimientos (TestClient + overrides)."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario
from app.deps import obtener_repositorio_requerimientos, obtener_repositorio_usuarios
from app.main import app
from app.usuarios.dominio import Usuario
from tests.fakes import FakeRepositorioRequerimientos, FakeRepositorioUsuarios

_PASSWORD = "clave-segura-1"


@pytest.fixture
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def repo_requerimientos() -> FakeRepositorioRequerimientos:
    return FakeRepositorioRequerimientos()


@pytest.fixture
def cliente(
    repo_usuarios: FakeRepositorioUsuarios, repo_requerimientos: FakeRepositorioRequerimientos
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo_usuarios
    app.dependency_overrides[obtener_repositorio_requerimientos] = lambda: repo_requerimientos
    with TestClient(app) as cliente_de_prueba:
        yield cliente_de_prueba
    app.dependency_overrides.clear()


def _crear_usuario(repo: FakeRepositorioUsuarios, email: str, rol: RolUsuario) -> Usuario:
    usuario = Usuario(email.split("@")[0], email, obtener_password_hash(_PASSWORD), rol)
    repo.guardar(usuario)
    return usuario


def _token_de(cliente: TestClient, email: str) -> str:
    respuesta = cliente.post("/usuarios/login", data={"username": email, "password": _PASSWORD})
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


_BODY_INCIDENTE = {
    "tipo": "INCIDENTE",
    "titulo": "Corte de fibra",
    "descripcion": "Sin señal en el sector norte.",
    "severidad": "ALTA",
    "pasos_reproduccion": "Reiniciar ONT.",
    "servicio_afectado": "Fibra óptica",
}


class TestCrear:
    def test_crear_incidente_devuelve_201_con_tipo_incidente(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        token = _token_de(cliente, "sol@x.com")

        # Act
        respuesta = cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token))

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["tipo"] == "INCIDENTE"
        assert respuesta.json()["estado"] == "ABIERTO"

    def test_crear_solicitud_devuelve_201_con_tipo_solicitud(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        token = _token_de(cliente, "sol@x.com")
        fecha_limite = (datetime.now(UTC) + timedelta(days=5)).isoformat()

        # Act
        respuesta = cliente.post(
            "/requerimientos",
            json={
                "tipo": "SOLICITUD",
                "titulo": "Alta de servicio",
                "descripcion": "Nueva conexión residencial.",
                "categoria": "NUEVO_SERVICIO",
                "fecha_limite": fecha_limite,
                "impacto_estimado": "Bajo",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["tipo"] == "SOLICITUD"

    def test_crear_sin_token_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.post("/requerimientos", json=_BODY_INCIDENTE)

        # Assert
        assert respuesta.status_code == 401


class TestListarYObtener:
    def test_solicitante_solo_ve_sus_propios_requerimientos(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol1@x.com", RolUsuario.SOLICITANTE)
        _crear_usuario(repo_usuarios, "sol2@x.com", RolUsuario.SOLICITANTE)
        token_1 = _token_de(cliente, "sol1@x.com")
        token_2 = _token_de(cliente, "sol2@x.com")
        cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_1))
        cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_2))

        # Act
        respuesta = cliente.get("/requerimientos", headers=_headers(token_1))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1

    def test_operador_ve_todos_los_requerimientos(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol1@x.com", RolUsuario.SOLICITANTE)
        _crear_usuario(repo_usuarios, "sol2@x.com", RolUsuario.SOLICITANTE)
        _crear_usuario(repo_usuarios, "op@x.com", RolUsuario.OPERADOR)
        token_1 = _token_de(cliente, "sol1@x.com")
        token_2 = _token_de(cliente, "sol2@x.com")
        token_operador = _token_de(cliente, "op@x.com")
        cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_1))
        cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_2))

        # Act
        respuesta = cliente.get("/requerimientos", headers=_headers(token_operador))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 2

    def test_obtener_por_id_inexistente_devuelve_404(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        token = _token_de(cliente, "sol@x.com")

        # Act
        respuesta = cliente.get(f"/requerimientos/{uuid.uuid4()}", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 404


class TestTransicionesViaHttp:
    def test_flujo_completo_hasta_cierre(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        solicitante = _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        tecnico = _crear_usuario(repo_usuarios, "tec@x.com", RolUsuario.TECNICO)
        _crear_usuario(repo_usuarios, "op@x.com", RolUsuario.OPERADOR)
        token_solicitante = _token_de(cliente, solicitante.email)
        token_tecnico = _token_de(cliente, tecnico.email)
        token_operador = _token_de(cliente, "op@x.com")

        creado = cliente.post(
            "/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_solicitante)
        )
        requerimiento_id = creado.json()["id"]

        # Act
        r1 = cliente.post(
            f"/requerimientos/{requerimiento_id}/iniciar-analisis",
            headers=_headers(token_operador),
        )
        r2 = cliente.post(
            f"/requerimientos/{requerimiento_id}/asignar-tecnico",
            json={"tecnico_id": str(tecnico.id)},
            headers=_headers(token_operador),
        )
        r3 = cliente.post(
            f"/requerimientos/{requerimiento_id}/iniciar-progreso",
            headers=_headers(token_tecnico),
        )
        r4 = cliente.post(
            f"/requerimientos/{requerimiento_id}/resolver",
            json={"nota_resolucion": "ONT reemplazado."},
            headers=_headers(token_tecnico),
        )
        r5 = cliente.post(
            f"/requerimientos/{requerimiento_id}/cerrar",
            headers=_headers(token_solicitante),
        )

        # Assert
        assert [r.status_code for r in (r1, r2, r3, r4, r5)] == [200, 200, 200, 200, 200]
        assert r5.json()["estado"] == "CERRADO"

    def test_solicitante_no_puede_iniciar_analisis_devuelve_403(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        token = _token_de(cliente, "sol@x.com")
        creado = cliente.post("/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token))
        requerimiento_id = creado.json()["id"]

        # Act
        respuesta = cliente.post(
            f"/requerimientos/{requerimiento_id}/iniciar-analisis", headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 403

    def test_iniciar_progreso_sin_tecnico_asignado_devuelve_409(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        _crear_usuario(repo_usuarios, "op@x.com", RolUsuario.OPERADOR)
        token_solicitante = _token_de(cliente, "sol@x.com")
        token_operador = _token_de(cliente, "op@x.com")
        creado = cliente.post(
            "/requerimientos", json=_BODY_INCIDENTE, headers=_headers(token_solicitante)
        )
        requerimiento_id = creado.json()["id"]
        cliente.post(
            f"/requerimientos/{requerimiento_id}/iniciar-analisis",
            headers=_headers(token_operador),
        )

        # Act: nadie asignó técnico todavía
        respuesta = cliente.post(
            f"/requerimientos/{requerimiento_id}/iniciar-progreso",
            headers=_headers(token_operador),
        )

        # Assert
        assert respuesta.status_code == 409

    def test_transicion_sobre_id_inexistente_devuelve_404(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "op@x.com", RolUsuario.OPERADOR)
        token = _token_de(cliente, "op@x.com")

        # Act
        respuesta = cliente.post(
            f"/requerimientos/{uuid.uuid4()}/iniciar-analisis", headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 404
