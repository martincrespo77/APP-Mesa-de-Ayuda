"""Tests de dominio del módulo `app/usuarios/` (entidad `Usuario`)."""

import uuid

import pytest

from app.compartido.dominio import RolUsuario
from app.usuarios.dominio import Usuario
from app.usuarios.excepciones import UsuarioYaActivoError, UsuarioYaInactivoError


@pytest.fixture
def usuario() -> Usuario:
    # Arrange: usuario válido recién creado
    return Usuario(
        nombre_completo="Ana Pérez",
        email="ana.perez@comunicarlos.coop",
        password_hash="hash-bcrypt-simulado",
        rol=RolUsuario.OPERADOR,
    )


class TestCreacionDeUsuario:
    def test_usuario_valido_nace_activo_con_id_generado(self, usuario: Usuario) -> None:
        # Assert
        assert usuario.activo is True
        assert usuario.rol == RolUsuario.OPERADOR
        assert isinstance(usuario.id, uuid.UUID)

    def test_email_normalizado_a_minusculas(self) -> None:
        # Act
        usuario = Usuario("Ana", "Ana.Perez@Comunicarlos.Coop", "hash", RolUsuario.OPERADOR)

        # Assert
        assert usuario.email == "ana.perez@comunicarlos.coop"

    def test_email_sin_arroba_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Usuario("Ana", "correo-invalido", "hash", RolUsuario.OPERADOR)

    def test_nombre_vacio_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Usuario("   ", "ana@comunicarlos.coop", "hash", RolUsuario.OPERADOR)

    def test_password_hash_vacio_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Usuario("Ana", "ana@comunicarlos.coop", "   ", RolUsuario.OPERADOR)

    def test_rol_invalido_lanza_type_error(self) -> None:
        # Act & Assert: se pasa un str en lugar de un RolUsuario
        with pytest.raises(TypeError):
            Usuario("Ana", "ana@comunicarlos.coop", "hash", "OPERADOR")  # type: ignore[arg-type]


class TestEstadoDeActivacion:
    def test_desactivar_usuario_activo(self, usuario: Usuario) -> None:
        # Act
        usuario.desactivar()

        # Assert
        assert usuario.activo is False

    def test_desactivar_usuario_ya_inactivo_lanza_error(self, usuario: Usuario) -> None:
        # Arrange
        usuario.desactivar()

        # Act & Assert
        with pytest.raises(UsuarioYaInactivoError):
            usuario.desactivar()

    def test_activar_usuario_inactivo(self, usuario: Usuario) -> None:
        # Arrange
        usuario.desactivar()

        # Act
        usuario.activar()

        # Assert
        assert usuario.activo is True

    def test_activar_usuario_ya_activo_lanza_error(self, usuario: Usuario) -> None:
        # Act & Assert
        with pytest.raises(UsuarioYaActivoError):
            usuario.activar()


class TestCambiosDeRolYPassword:
    def test_cambiar_rol(self, usuario: Usuario) -> None:
        # Act
        usuario.cambiar_rol(RolUsuario.SUPERVISOR)

        # Assert
        assert usuario.rol == RolUsuario.SUPERVISOR

    def test_cambiar_password_hash(self, usuario: Usuario) -> None:
        # Act
        usuario.cambiar_password_hash("nuevo-hash-bcrypt")

        # Assert
        assert usuario.password_hash == "nuevo-hash-bcrypt"
