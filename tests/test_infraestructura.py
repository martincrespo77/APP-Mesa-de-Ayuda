"""Tests de integración de la capa de infraestructura (Paso 5).

Usa `mongomock` en vez de un servidor MongoDB real: mismo protocolo que
PyMongo, sin depender de red ni de un contenedor Docker levantado. Valida
que los repositorios concretos cumplen el mismo contrato ABC que ya
prueban los `Fake*` de `tests/fakes.py`, pero con el mapeo real a/desde
documentos BSON.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import mongomock
import pytest
from pymongo.database import Database

from app.compartido.dominio import RolUsuario
from app.infraestructura.repo_usuarios import RepositorioUsuariosMongo
from app.usuarios.dominio import Usuario


@pytest.fixture
def db() -> Iterator[Database[dict[str, Any]]]:
    cliente: mongomock.MongoClient[dict[str, Any]] = mongomock.MongoClient()
    yield cliente["mesa_de_ayuda_test"]
    cliente.close()


@pytest.fixture
def repo_usuarios(db: Database[dict[str, Any]]) -> RepositorioUsuariosMongo:
    return RepositorioUsuariosMongo(db)


@pytest.fixture
def usuario() -> Usuario:
    return Usuario(
        nombre_completo="Ana Pérez",
        email="ana.perez@comunicarlos.coop",
        password_hash="hash-bcrypt-de-prueba",
        rol=RolUsuario.OPERADOR,
    )


class TestRepositorioUsuariosMongoGuardarYBuscar:
    def test_guardar_y_buscar_por_id_devuelve_el_mismo_usuario(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Act
        repo_usuarios.guardar(usuario)
        encontrado = repo_usuarios.buscar_por_id(usuario.id)

        # Assert
        assert encontrado is not None
        assert encontrado.id == usuario.id
        assert encontrado.nombre_completo == usuario.nombre_completo
        assert encontrado.email == usuario.email
        assert encontrado.password_hash == usuario.password_hash
        assert encontrado.rol == usuario.rol
        assert encontrado.activo == usuario.activo

    def test_buscar_por_id_inexistente_devuelve_none(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Act & Assert
        assert repo_usuarios.buscar_por_id(uuid.uuid4()) is None

    def test_buscar_por_email_encuentra_al_usuario(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Arrange
        repo_usuarios.guardar(usuario)

        # Act
        encontrado = repo_usuarios.buscar_por_email(usuario.email)

        # Assert
        assert encontrado is not None
        assert encontrado.id == usuario.id

    def test_buscar_por_email_inexistente_devuelve_none(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Act & Assert
        assert repo_usuarios.buscar_por_email("no-existe@comunicarlos.coop") is None

    def test_guardar_es_upsert_no_duplica_documentos(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Arrange
        repo_usuarios.guardar(usuario)

        # Act: se reactiva y se guarda de nuevo el MISMO id
        usuario.desactivar()
        repo_usuarios.guardar(usuario)

        # Assert: sigue habiendo un solo documento, con el cambio reflejado
        assert len(repo_usuarios.listar_todos()) == 1
        encontrado = repo_usuarios.buscar_por_id(usuario.id)
        assert encontrado is not None
        assert encontrado.activo is False

    def test_listar_todos_devuelve_todos_los_usuarios_guardados(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Arrange
        usuario_a = Usuario(
            nombre_completo="A",
            email="a@comunicarlos.coop",
            password_hash="hash-a",
            rol=RolUsuario.SOLICITANTE,
        )
        usuario_b = Usuario(
            nombre_completo="B",
            email="b@comunicarlos.coop",
            password_hash="hash-b",
            rol=RolUsuario.TECNICO,
        )
        repo_usuarios.guardar(usuario_a)
        repo_usuarios.guardar(usuario_b)

        # Act
        todos = repo_usuarios.listar_todos()

        # Assert
        assert {u.id for u in todos} == {usuario_a.id, usuario_b.id}
