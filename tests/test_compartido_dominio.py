"""Tests de dominio del Shared Kernel (`app/compartido/`)."""

from app.compartido.dominio import RolUsuario
from app.compartido.excepciones import DominioError


class TestRolUsuario:
    def test_contiene_los_cuatro_roles_de_negocio(self) -> None:
        # Act
        valores = {rol.value for rol in RolUsuario}

        # Assert
        assert valores == {"SOLICITANTE", "OPERADOR", "TECNICO", "SUPERVISOR"}


class TestDominioError:
    def test_es_una_excepcion_estandar_de_python(self) -> None:
        # Arrange
        mensaje = "violación de una regla de negocio"

        # Act
        error = DominioError(mensaje)

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == mensaje
