"""Tests de integración del router de notificaciones (TestClient + overrides).

No requiere MongoDB: los repositorios concretos se sobreescriben con
`Fake*`. El caso end-to-end (`TestGeneracionEndToEnd`) también sobreescribe
`obtener_despachador_eventos` con un `DespachadorEventos` real suscripto a
`ObservadorNotificacionesMongo` construido sobre los `Fake*`, para probar
el pipeline completo (evento de un supervisado -> notificación real) sin
mongomock.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.deps import (
    obtener_despachador_eventos,
    obtener_repositorio_notificaciones,
    obtener_repositorio_requerimientos,
    obtener_repositorio_supervision,
    obtener_repositorio_usuarios,
)
from app.infraestructura.observador_notificaciones import ObservadorNotificacionesMongo
from app.main import app
from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.dominio import Notificacion
from app.requerimientos.eventos import TipoEventoRequerimiento
from app.supervision.dominio import RelacionSupervision
from app.usuarios.dominio import Usuario
from tests.fakes import (
    FakeRepositorioNotificaciones,
    FakeRepositorioRequerimientos,
    FakeRepositorioSupervision,
    FakeRepositorioUsuarios,
)
from tests.lifespan import lifespan_vacio

_PASSWORD = "clave-segura-1"


@pytest.fixture
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def repo_notificaciones() -> FakeRepositorioNotificaciones:
    return FakeRepositorioNotificaciones()


@pytest.fixture
def cliente(
    repo_usuarios: FakeRepositorioUsuarios, repo_notificaciones: FakeRepositorioNotificaciones
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo_usuarios
    app.dependency_overrides[obtener_repositorio_notificaciones] = lambda: repo_notificaciones
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


class TestListarYMarcarLeida:
    def test_listar_mis_notificaciones(
        self,
        cliente: TestClient,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange
        supervisor = _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        repo_notificaciones.guardar(
            Notificacion(
                supervisor_id=supervisor.id,
                empleado_supervisado_id=uuid.uuid4(),
                requerimiento_id=uuid.uuid4(),
                tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
                detalle="Cambió de estado.",
            )
        )
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.get("/notificaciones", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1
        assert respuesta.json()[0]["leida"] is False

    def test_rol_no_supervisor_devuelve_403(
        self, cliente: TestClient, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR)
        token = _token_de(cliente, "op@comunicarlos.com.ar")

        # Act
        respuesta = cliente.get("/notificaciones", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 403

    def test_marcar_leida(
        self,
        cliente: TestClient,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange
        supervisor = _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        notificacion = Notificacion(
            supervisor_id=supervisor.id,
            empleado_supervisado_id=uuid.uuid4(),
            requerimiento_id=uuid.uuid4(),
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            detalle="Cambió de estado.",
        )
        repo_notificaciones.guardar(notificacion)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.patch(
            f"/notificaciones/{notificacion.id}/leida", headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["leida"] is True

    def test_marcar_leida_ajena_devuelve_404(
        self,
        cliente: TestClient,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR)
        notificacion = Notificacion(
            supervisor_id=uuid.uuid4(),
            empleado_supervisado_id=uuid.uuid4(),
            requerimiento_id=uuid.uuid4(),
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            detalle="Cambió de estado.",
        )
        repo_notificaciones.guardar(notificacion)
        token = _token_de(cliente, "sup@comunicarlos.com.ar")

        # Act
        respuesta = cliente.patch(
            f"/notificaciones/{notificacion.id}/leida", headers=_headers(token)
        )

        # Assert
        assert respuesta.status_code == 404


class TestGeneracionEndToEnd:
    """El pipeline completo: un evento de un Operador supervisado genera una
    `Notificacion` real para su Supervisor, vía `DespachadorEventos` +
    `ObservadorNotificacionesMongo` (sobre Fakes, sin mongomock)."""

    @pytest.fixture
    def repo_requerimientos(self) -> FakeRepositorioRequerimientos:
        return FakeRepositorioRequerimientos()

    @pytest.fixture
    def repo_supervision(self) -> FakeRepositorioSupervision:
        return FakeRepositorioSupervision()

    @pytest.fixture
    def cliente_con_observer(
        self,
        cliente: TestClient,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_requerimientos: FakeRepositorioRequerimientos,
        repo_supervision: FakeRepositorioSupervision,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> Generator[TestClient, None, None]:
        despachador = DespachadorEventos()
        despachador.suscribir(
            ObservadorNotificacionesMongo(repo_usuarios, repo_supervision, repo_notificaciones)
        )
        app.dependency_overrides[obtener_repositorio_requerimientos] = lambda: repo_requerimientos
        app.dependency_overrides[obtener_repositorio_supervision] = lambda: repo_supervision
        app.dependency_overrides[obtener_despachador_eventos] = lambda: despachador
        yield cliente

    def test_iniciar_analisis_notifica_al_supervisor_del_operador(
        self,
        cliente_con_observer: TestClient,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_supervision: FakeRepositorioSupervision,
    ) -> None:
        # Arrange
        _crear_usuario(repo_usuarios, "sol@x.com", RolUsuario.SOLICITANTE)
        operador = _crear_usuario(
            repo_usuarios, "op@comunicarlos.com.ar", RolUsuario.OPERADOR
        )
        supervisor = _crear_usuario(
            repo_usuarios, "sup@comunicarlos.com.ar", RolUsuario.SUPERVISOR
        )
        repo_supervision.asignar(RelacionSupervision(supervisor.id, operador.id))
        token_solicitante = _token_de(cliente_con_observer, "sol@x.com")
        token_operador = _token_de(cliente_con_observer, "op@comunicarlos.com.ar")
        token_supervisor = _token_de(cliente_con_observer, "sup@comunicarlos.com.ar")
        creado = cliente_con_observer.post(
            "/requerimientos",
            json={
                "tipo": "INCIDENTE",
                "titulo": "Corte de fibra",
                "descripcion": "Sin señal.",
                "urgencia": "IMPORTANTE",
                "categoria": "SERVICIO_INACCESIBLE",
                "servicio": "INTERNET_BANDA_ANCHA",
                "pasos_reproduccion": "Reiniciar ONT.",
            },
            headers=_headers(token_solicitante),
        )
        requerimiento_id = creado.json()["id"]

        # Act: el operador (supervisado) inicia el análisis
        cliente_con_observer.post(
            f"/requerimientos/{requerimiento_id}/iniciar-analisis",
            headers=_headers(token_operador),
        )

        # Assert: su supervisor recibe una notificación por ese evento
        respuesta = cliente_con_observer.get(
            "/notificaciones", headers=_headers(token_supervisor)
        )
        assert respuesta.status_code == 200
        detalles = [n["tipo_evento"] for n in respuesta.json()]
        assert "CAMBIO_ESTADO" in detalles
