"""Tests de servicios del módulo `app/supervision/` (con Fakes en memoria)."""

import uuid

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.supervision.excepciones import RelacionYaExisteError, RolNoSupervisableError
from app.supervision.servicios import ServicioSupervision
from app.usuarios.dominio import Usuario
from app.usuarios.excepciones import UsuarioNoEncontradoError
from tests.fakes import FakeRepositorioSupervision, FakeRepositorioUsuarios


@pytest.fixture
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def repositorio() -> FakeRepositorioSupervision:
    return FakeRepositorioSupervision()


@pytest.fixture
def servicio(
    repositorio: FakeRepositorioSupervision, repo_usuarios: FakeRepositorioUsuarios
) -> ServicioSupervision:
    return ServicioSupervision(repositorio, repo_usuarios)


def _crear_usuario(repo: FakeRepositorioUsuarios, rol: RolUsuario) -> Usuario:
    servicios = (
        frozenset({ServicioComunicarlos.TELEVISION})
        if rol == RolUsuario.SOLICITANTE
        else frozenset()
    )
    sufijo = uuid.uuid4().hex[:8]
    email = (
        f"user{sufijo}@gmail.com"
        if rol == RolUsuario.SOLICITANTE
        else f"user{sufijo}@comunicarlos.com.ar"
    )
    usuario = Usuario(f"User {sufijo}", email, "hash", rol, servicios_suscriptos=servicios)
    repo.guardar(usuario)
    return usuario


class TestAsignar:
    def test_asignar_supervisor_a_operador_persiste_la_relacion(
        self,
        servicio: ServicioSupervision,
        repositorio: FakeRepositorioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        operador = _crear_usuario(repo_usuarios, RolUsuario.OPERADOR)

        # Act
        relacion = servicio.asignar(supervisor_id, operador.id)

        # Assert
        assert repositorio.existe(supervisor_id, operador.id)
        assert relacion.supervisor_id == supervisor_id
        assert relacion.supervisado_id == operador.id

    def test_asignar_a_tecnico_tambien_es_valido(
        self, servicio: ServicioSupervision, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        tecnico = _crear_usuario(repo_usuarios, RolUsuario.TECNICO)

        # Act & Assert: no lanza
        servicio.asignar(uuid.uuid4(), tecnico.id)

    def test_asignar_supervisado_inexistente_lanza_error(
        self, servicio: ServicioSupervision
    ) -> None:
        # Act & Assert
        with pytest.raises(UsuarioNoEncontradoError):
            servicio.asignar(uuid.uuid4(), uuid.uuid4())

    def test_asignar_a_un_solicitante_lanza_rol_no_supervisable(
        self, servicio: ServicioSupervision, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        solicitante = _crear_usuario(repo_usuarios, RolUsuario.SOLICITANTE)

        # Act & Assert
        with pytest.raises(RolNoSupervisableError):
            servicio.asignar(uuid.uuid4(), solicitante.id)

    def test_asignar_a_un_supervisor_lanza_rol_no_supervisable(
        self, servicio: ServicioSupervision, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        otro_supervisor = _crear_usuario(repo_usuarios, RolUsuario.SUPERVISOR)

        # Act & Assert
        with pytest.raises(RolNoSupervisableError):
            servicio.asignar(uuid.uuid4(), otro_supervisor.id)

    def test_asignar_relacion_duplicada_lanza_error(
        self, servicio: ServicioSupervision, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        operador = _crear_usuario(repo_usuarios, RolUsuario.OPERADOR)
        servicio.asignar(supervisor_id, operador.id)

        # Act & Assert
        with pytest.raises(RelacionYaExisteError):
            servicio.asignar(supervisor_id, operador.id)


class TestRemoverYListar:
    def test_remover_elimina_la_relacion(
        self,
        servicio: ServicioSupervision,
        repositorio: FakeRepositorioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        operador = _crear_usuario(repo_usuarios, RolUsuario.OPERADOR)
        servicio.asignar(supervisor_id, operador.id)

        # Act
        servicio.remover(supervisor_id, operador.id)

        # Assert
        assert not repositorio.existe(supervisor_id, operador.id)

    def test_remover_relacion_inexistente_no_lanza_error(
        self, servicio: ServicioSupervision
    ) -> None:
        # Act & Assert: idempotente, no falla si no existía
        servicio.remover(uuid.uuid4(), uuid.uuid4())

    def test_listar_supervisados_de_devuelve_solo_los_del_supervisor(
        self, servicio: ServicioSupervision, repo_usuarios: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        operador = _crear_usuario(repo_usuarios, RolUsuario.OPERADOR)
        tecnico = _crear_usuario(repo_usuarios, RolUsuario.TECNICO)
        otro_tecnico = _crear_usuario(repo_usuarios, RolUsuario.TECNICO)
        servicio.asignar(supervisor_id, operador.id)
        servicio.asignar(supervisor_id, tecnico.id)
        servicio.asignar(uuid.uuid4(), otro_tecnico.id)

        # Act
        supervisados = servicio.listar_supervisados_de(supervisor_id)

        # Assert
        assert {r.supervisado_id for r in supervisados} == {operador.id, tecnico.id}
