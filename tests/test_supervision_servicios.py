"""Tests de servicios del módulo `app/supervision/` (con Fakes en memoria).

Solo cubren orquestación: que el servicio busque, delegue en el dominio,
persista y valide lo que exige al repositorio (existencia del supervisado,
relación duplicada). QUIÉN puede ser supervisado es una regla de dominio y
se prueba en `test_usuarios_dominio.py::TestSupervisor`.
"""

import uuid

import pytest

from app.supervision.excepciones import RelacionYaExisteError, RolNoSupervisableError
from app.supervision.servicios import ServicioSupervision
from app.usuarios.dominio import Supervisor
from app.usuarios.excepciones import UsuarioNoEncontradoError
from tests.actores import un_operador, un_solicitante, un_supervisor, un_tecnico
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


@pytest.fixture
def supervisor() -> Supervisor:
    return un_supervisor()


class TestAsignar:
    def test_asignar_persiste_la_relacion_que_crea_el_supervisor(
        self,
        servicio: ServicioSupervision,
        repositorio: FakeRepositorioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
        supervisor: Supervisor,
    ) -> None:
        # Arrange
        operador = un_operador()
        repo_usuarios.guardar(operador)

        # Act
        relacion = servicio.asignar(supervisor, operador.id)

        # Assert
        assert repositorio.existe(supervisor.id, operador.id)
        assert relacion.supervisor_id == supervisor.id
        assert relacion.supervisado_id == operador.id

    def test_asignar_supervisado_inexistente_lanza_error(
        self, servicio: ServicioSupervision, supervisor: Supervisor
    ) -> None:
        # Act & Assert
        with pytest.raises(UsuarioNoEncontradoError):
            servicio.asignar(supervisor, uuid.uuid4())

    def test_si_el_dominio_rechaza_la_relacion_no_se_persiste_nada(
        self,
        servicio: ServicioSupervision,
        repositorio: FakeRepositorioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
        supervisor: Supervisor,
    ) -> None:
        # Arrange: el error de dominio se propaga tal cual, sin persistir
        solicitante = un_solicitante()
        repo_usuarios.guardar(solicitante)

        # Act & Assert
        with pytest.raises(RolNoSupervisableError):
            servicio.asignar(supervisor, solicitante.id)
        assert not repositorio.existe(supervisor.id, solicitante.id)

    def test_asignar_relacion_duplicada_lanza_error(
        self,
        servicio: ServicioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
        supervisor: Supervisor,
    ) -> None:
        # Arrange
        operador = un_operador()
        repo_usuarios.guardar(operador)
        servicio.asignar(supervisor, operador.id)

        # Act & Assert
        with pytest.raises(RelacionYaExisteError):
            servicio.asignar(supervisor, operador.id)


class TestRemoverYListar:
    def test_remover_elimina_la_relacion(
        self,
        servicio: ServicioSupervision,
        repositorio: FakeRepositorioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
        supervisor: Supervisor,
    ) -> None:
        # Arrange
        operador = un_operador()
        repo_usuarios.guardar(operador)
        servicio.asignar(supervisor, operador.id)

        # Act
        servicio.remover(supervisor.id, operador.id)

        # Assert
        assert not repositorio.existe(supervisor.id, operador.id)

    def test_remover_relacion_inexistente_no_lanza_error(
        self, servicio: ServicioSupervision
    ) -> None:
        # Act & Assert: idempotente, no falla si no existía
        servicio.remover(uuid.uuid4(), uuid.uuid4())

    def test_listar_supervisados_de_devuelve_solo_los_del_supervisor(
        self,
        servicio: ServicioSupervision,
        repo_usuarios: FakeRepositorioUsuarios,
        supervisor: Supervisor,
    ) -> None:
        # Arrange
        operador = un_operador()
        tecnico = un_tecnico()
        otro_tecnico = un_tecnico(email="marta@comunicarlos.com.ar")
        for usuario in (operador, tecnico, otro_tecnico):
            repo_usuarios.guardar(usuario)
        servicio.asignar(supervisor, operador.id)
        servicio.asignar(supervisor, tecnico.id)
        servicio.asignar(un_supervisor(email="otro@comunicarlos.com.ar"), otro_tecnico.id)

        # Act
        supervisados = servicio.listar_supervisados_de(supervisor.id)

        # Assert
        assert {r.supervisado_id for r in supervisados} == {operador.id, tecnico.id}
