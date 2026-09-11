"""Tests de servicios del módulo `app/usuarios/` (con `FakeRepositorioUsuarios`)."""

import uuid

import pytest

from app.compartido.dominio import RolUsuario
from app.usuarios.excepciones import EmailYaRegistradoError, UsuarioNoEncontradoError
from app.usuarios.servicios import ServicioUsuarios
from tests.fakes import FakeRepositorioUsuarios


@pytest.fixture
def repositorio() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def servicio(repositorio: FakeRepositorioUsuarios) -> ServicioUsuarios:
    return ServicioUsuarios(repositorio)


class TestRegistrar:
    def test_registrar_usuario_nuevo_lo_persiste_en_el_repositorio(
        self, servicio: ServicioUsuarios, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Act
        usuario = servicio.registrar(
            "Ana Pérez", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR
        )

        # Assert
        assert repositorio.buscar_por_id(usuario.id) is usuario

    def test_registrar_con_email_duplicado_lanza_error(self, servicio: ServicioUsuarios) -> None:
        # Arrange
        servicio.registrar("Ana Pérez", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(EmailYaRegistradoError):
            servicio.registrar(
                "Ana Duplicada", "ana@comunicarlos.coop", "hash2", RolUsuario.TECNICO
            )


class TestConsultas:
    def test_obtener_por_id_inexistente_devuelve_none(self, servicio: ServicioUsuarios) -> None:
        # Act
        resultado = servicio.obtener_por_id(uuid.uuid4())

        # Assert
        assert resultado is None

    def test_listar_todos_devuelve_los_usuarios_registrados(
        self, servicio: ServicioUsuarios
    ) -> None:
        # Arrange
        servicio.registrar("Ana", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR)
        servicio.registrar("Beto", "beto@comunicarlos.coop", "hash", RolUsuario.TECNICO)

        # Act
        usuarios = servicio.listar_todos()

        # Assert
        assert len(usuarios) == 2


class TestAdministracion:
    def test_desactivar_persiste_el_cambio_de_estado(
        self, servicio: ServicioUsuarios, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        usuario = servicio.registrar("Ana", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR)

        # Act
        servicio.desactivar(usuario.id)

        # Assert
        assert repositorio.buscar_por_id(usuario.id).activo is False  # type: ignore[union-attr]

    def test_activar_usuario_inexistente_lanza_error(self, servicio: ServicioUsuarios) -> None:
        # Act & Assert
        with pytest.raises(UsuarioNoEncontradoError):
            servicio.activar(uuid.uuid4())

    def test_cambiar_rol_persiste_el_nuevo_rol(
        self, servicio: ServicioUsuarios, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        usuario = servicio.registrar("Ana", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR)

        # Act
        servicio.cambiar_rol(usuario.id, RolUsuario.SUPERVISOR)

        # Assert
        assert repositorio.buscar_por_id(usuario.id).rol == RolUsuario.SUPERVISOR  # type: ignore[union-attr]
