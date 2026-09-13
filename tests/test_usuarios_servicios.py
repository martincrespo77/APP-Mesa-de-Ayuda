"""Tests de servicios del módulo `app/usuarios/` (con `FakeRepositorioUsuarios`)."""

import uuid

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.usuarios.excepciones import (
    CredencialesInvalidasError,
    EmailCorporativoRequeridoError,
    EmailYaRegistradoError,
    UsuarioNoEncontradoError,
)
from app.usuarios.servicios import ServicioUsuarios
from tests.fakes import FakeRepositorioUsuarios

_UN_SERVICIO = frozenset({ServicioComunicarlos.TELEVISION})


def _verificador_fake(password: str, password_hash: str) -> bool:
    """Simula bcrypt: el hash de una contraseña es `hash-de-<password>`."""
    return password_hash == f"hash-de-{password}"


@pytest.fixture
def repositorio() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def servicio(repositorio: FakeRepositorioUsuarios) -> ServicioUsuarios:
    return ServicioUsuarios(repositorio, _verificador_fake)


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
        usuario = servicio.registrar(
            "Ana Pérez",
            "ana@gmail.com",
            "hash",
            RolUsuario.SOLICITANTE,
            servicios_suscriptos=_UN_SERVICIO,
        )

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


class TestAutenticar:
    def test_autenticar_con_credenciales_validas_registra_el_acceso(
        self, servicio: ServicioUsuarios, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        registrado = servicio.registrar(
            "Ana", "ana@comunicarlos.com.ar", "hash-de-secreta123", RolUsuario.OPERADOR
        )
        assert registrado.ultimo_acceso is None

        # Act
        autenticado = servicio.autenticar("ana@comunicarlos.com.ar", "secreta123")

        # Assert
        assert autenticado.id == registrado.id
        assert autenticado.ultimo_acceso is not None
        assert repositorio.buscar_por_id(registrado.id).ultimo_acceso is not None  # type: ignore[union-attr]

    def test_autenticar_con_password_incorrecta_lanza_error(
        self, servicio: ServicioUsuarios
    ) -> None:
        # Arrange
        servicio.registrar(
            "Ana", "ana@comunicarlos.com.ar", "hash-de-secreta123", RolUsuario.OPERADOR
        )

        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            servicio.autenticar("ana@comunicarlos.com.ar", "incorrecta")

    def test_autenticar_email_inexistente_lanza_error(self, servicio: ServicioUsuarios) -> None:
        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            servicio.autenticar("nadie@comunicarlos.com.ar", "cualquiera")

    def test_autenticar_usuario_inactivo_lanza_error(self, servicio: ServicioUsuarios) -> None:
        # Arrange
        usuario = servicio.registrar(
            "Ana", "ana@comunicarlos.com.ar", "hash-de-secreta123", RolUsuario.OPERADOR
        )
        servicio.desactivar(usuario.id)

        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            servicio.autenticar("ana@comunicarlos.com.ar", "secreta123")
