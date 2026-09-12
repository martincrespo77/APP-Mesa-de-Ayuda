"""Tests de servicios del módulo `app/usuarios/` (con `FakeRepositorioUsuarios`)."""

import uuid

import pytest

from app.compartido.dominio import RolUsuario
from app.usuarios.excepciones import (
    EmailCorporativoRequeridoError,
    EmailYaRegistradoError,
    UsuarioNoEncontradoError,
)
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
            "Ana Pérez", "ana@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR
        )

        # Assert
        assert repositorio.buscar_por_id(usuario.id) is usuario

    def test_registrar_con_email_duplicado_lanza_error(self, servicio: ServicioUsuarios) -> None:
        # Arrange
        servicio.registrar("Ana Pérez", "ana@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(EmailYaRegistradoError):
            servicio.registrar(
                "Ana Duplicada", "ana@comunicarlos.com.ar", "hash2", RolUsuario.TECNICO
            )

    def test_registrar_operador_con_email_no_corporativo_lanza_error(
        self, servicio: ServicioUsuarios
    ) -> None:
        # Act & Assert
        with pytest.raises(EmailCorporativoRequeridoError):
            servicio.registrar("Ana Pérez", "ana@gmail.com", "hash", RolUsuario.OPERADOR)

    def test_registrar_solicitante_con_cualquier_email_no_lanza_error(
        self, servicio: ServicioUsuarios
    ) -> None:
        # Act
        usuario = servicio.registrar("Ana Pérez", "ana@gmail.com", "hash", RolUsuario.SOLICITANTE)

        # Assert
        assert usuario.email == "ana@gmail.com"


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
        servicio.registrar("Ana", "ana@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR)
        servicio.registrar("Beto", "beto@comunicarlos.com.ar", "hash", RolUsuario.TECNICO)

        # Act
        usuarios = servicio.listar_todos()

        # Assert
        assert len(usuarios) == 2


class TestAdministracion:
    def test_desactivar_persiste_el_cambio_de_estado(
        self, servicio: ServicioUsuarios, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        usuario = servicio.registrar("Ana", "ana@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR)

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
        usuario = servicio.registrar("Ana", "ana@comunicarlos.com.ar", "hash", RolUsuario.OPERADOR)

        # Act
        servicio.cambiar_rol(usuario.id, RolUsuario.SUPERVISOR)

        # Assert
        assert repositorio.buscar_por_id(usuario.id).rol == RolUsuario.SUPERVISOR  # type: ignore[union-attr]
