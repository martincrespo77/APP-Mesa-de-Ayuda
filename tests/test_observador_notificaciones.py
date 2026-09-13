"""Tests de `ObservadorNotificacionesMongo` (con Fakes en memoria).

A pesar del nombre (coherente con el resto de `app/infraestructura/`), el
observador solo orquesta las interfaces `RepositorioUsuarios`/
`RepositorioSupervision`/`RepositorioNotificaciones`: se puede probar por
completo con los `Fake*` de `tests/fakes.py`, sin mongomock.
"""

import uuid

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.infraestructura.observador_notificaciones import ObservadorNotificacionesMongo
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.supervision.dominio import RelacionSupervision
from app.usuarios.dominio import Usuario
from tests.fakes import (
    FakeRepositorioNotificaciones,
    FakeRepositorioSupervision,
    FakeRepositorioUsuarios,
)


@pytest.fixture
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def repo_supervision() -> FakeRepositorioSupervision:
    return FakeRepositorioSupervision()


@pytest.fixture
def repo_notificaciones() -> FakeRepositorioNotificaciones:
    return FakeRepositorioNotificaciones()


@pytest.fixture
def observador(
    repo_usuarios: FakeRepositorioUsuarios,
    repo_supervision: FakeRepositorioSupervision,
    repo_notificaciones: FakeRepositorioNotificaciones,
) -> ObservadorNotificacionesMongo:
    return ObservadorNotificacionesMongo(repo_usuarios, repo_supervision, repo_notificaciones)


def _evento(autor_id: uuid.UUID) -> EventoRequerimiento:
    return EventoRequerimiento(
        requerimiento_id=uuid.uuid4(),
        tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
        autor_id=autor_id,
        detalle="Estado cambiado.",
    )


class TestObservadorNotificaciones:
    def test_evento_de_operador_supervisado_genera_una_notificacion_por_supervisor(
        self,
        observador: ObservadorNotificacionesMongo,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_supervision: FakeRepositorioSupervision,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange
        operador = Usuario("Op", "op@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR)
        repo_usuarios.guardar(operador)
        supervisor_1_id = uuid.uuid4()
        supervisor_2_id = uuid.uuid4()
        repo_supervision.asignar(RelacionSupervision(supervisor_1_id, operador.id))
        repo_supervision.asignar(RelacionSupervision(supervisor_2_id, operador.id))

        # Act
        observador.actualizar(_evento(operador.id))

        # Assert
        notificados = {
            n.supervisor_id
            for n in repo_notificaciones.listar_por_supervisor(supervisor_1_id)
            + repo_notificaciones.listar_por_supervisor(supervisor_2_id)
        }
        assert notificados == {supervisor_1_id, supervisor_2_id}

    def test_evento_de_supervisado_sin_supervisores_no_genera_notificaciones(
        self,
        observador: ObservadorNotificacionesMongo,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange: técnico sin ninguna relación de supervisión asignada
        tecnico = Usuario("Tec", "tec@comunicarlos.com.ar", "hash", RolUsuario.TECNICO)
        repo_usuarios.guardar(tecnico)

        # Act
        observador.actualizar(_evento(tecnico.id))

        # Assert
        assert repo_notificaciones.listar_por_supervisor(uuid.uuid4()) == []

    def test_evento_de_solicitante_no_genera_notificaciones(
        self,
        observador: ObservadorNotificacionesMongo,
        repo_usuarios: FakeRepositorioUsuarios,
        repo_notificaciones: FakeRepositorioNotificaciones,
    ) -> None:
        # Arrange: un Solicitante nunca es supervisado (rol no supervisable)
        solicitante = Usuario(
            "Sol",
            "sol@gmail.com",
            "hash",
            RolUsuario.SOLICITANTE,
            servicios_suscriptos=frozenset({ServicioComunicarlos.TELEVISION}),
        )
        repo_usuarios.guardar(solicitante)

        # Act
        observador.actualizar(_evento(solicitante.id))

        # Assert
        assert repo_notificaciones.listar_por_supervisor(uuid.uuid4()) == []

    def test_evento_de_autor_inexistente_no_lanza_error(
        self, observador: ObservadorNotificacionesMongo
    ) -> None:
        # Act & Assert: no debe lanzar, solo no genera notificaciones
        observador.actualizar(_evento(uuid.uuid4()))
