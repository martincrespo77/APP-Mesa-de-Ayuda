"""Tests de las utilidades de autenticación (`app/auth.py`)."""

import uuid

import pytest

from app.auth import (
    TokenInvalidoError,
    crear_token_acceso,
    decodificar_token,
    obtener_password_hash,
    verificar_password,
)
from app.compartido.dominio import RolUsuario


class TestHashingDeContrasena:
    def test_verificar_password_correcta(self) -> None:
        # Arrange
        password_hash = obtener_password_hash("clave-super-secreta")

        # Act & Assert
        assert verificar_password("clave-super-secreta", password_hash) is True

    def test_verificar_password_incorrecta(self) -> None:
        # Arrange
        password_hash = obtener_password_hash("clave-super-secreta")

        # Act & Assert
        assert verificar_password("otra-clave", password_hash) is False

    def test_dos_hashes_de_la_misma_password_son_distintos(self) -> None:
        # Act
        hash_1 = obtener_password_hash("misma-clave")
        hash_2 = obtener_password_hash("misma-clave")

        # Assert: el salt aleatorio de bcrypt evita hashes idénticos
        assert hash_1 != hash_2


class TestTokenJWT:
    def test_decodificar_token_devuelve_los_mismos_claims_emitidos(self) -> None:
        # Arrange
        usuario_id = uuid.uuid4()
        token = crear_token_acceso(usuario_id, RolUsuario.SUPERVISOR)

        # Act
        id_decodificado, rol_decodificado = decodificar_token(token)

        # Assert
        assert id_decodificado == usuario_id
        assert rol_decodificado == RolUsuario.SUPERVISOR

    def test_token_manipulado_lanza_token_invalido(self) -> None:
        # Arrange
        token = crear_token_acceso(uuid.uuid4(), RolUsuario.OPERADOR)
        token_manipulado = token[:-2] + "xx"

        # Act & Assert
        with pytest.raises(TokenInvalidoError):
            decodificar_token(token_manipulado)

    def test_token_con_texto_arbitrario_lanza_token_invalido(self) -> None:
        # Act & Assert
        with pytest.raises(TokenInvalidoError):
            decodificar_token("esto-no-es-un-jwt")
