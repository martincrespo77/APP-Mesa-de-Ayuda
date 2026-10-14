"""Tests de integración del router de usuarios (TestClient + dependency_overrides).

No requiere MongoDB: `obtener_repositorio_usuarios` se sobreescribe con
`FakeRepositorioUsuarios` para cada test, y el lifespan real de la app
(que sí abre una conexión Mongo, Paso 5) se sobreescribe con un no-op.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.deps import obtener_repositorio_usuarios
from app.main import app
from app.usuarios.dominio import Usuario
from tests.fakes import FakeRepositorioUsuarios
from tests.lifespan import lifespan_vacio

_PASSWORD_SUPERVISOR = "clave-segura-1"
_PASSWORD_TECNICO = "clave-segura-2"


@pytest.fixture
def repositorio() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def cliente(repositorio: FakeRepositorioUsuarios) -> Generator[TestClient, None, None]:
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repositorio
    lifespan_original = app.router.lifespan_context
    app.router.lifespan_context = lifespan_vacio
    with TestClient(app) as cliente_de_prueba:
        yield cliente_de_prueba
    app.dependency_overrides.clear()
    app.router.lifespan_context = lifespan_original


@pytest.fixture
def supervisor(repositorio: FakeRepositorioUsuarios) -> Usuario:
    supervisor = Usuario(
        "Sofía Jefa",
        "sofia@comunicarlos.com.ar",
        obtener_password_hash(_PASSWORD_SUPERVISOR),
        RolUsuario.SUPERVISOR,
    )
    repositorio.guardar(supervisor)
    return supervisor


@pytest.fixture
def tecnico(repositorio: FakeRepositorioUsuarios) -> Usuario:
    tecnico = Usuario(
        "Beto Técnico",
        "beto@comunicarlos.com.ar",
        obtener_password_hash(_PASSWORD_TECNICO),
        RolUsuario.TECNICO,
    )
    repositorio.guardar(tecnico)
    return tecnico


def _token_de(cliente: TestClient, email: str, password: str) -> str:
    respuesta = cliente.post("/usuarios/login", data={"username": email, "password": password})
    assert respuesta.status_code == 200
    return str(respuesta.json()["access_token"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLogin:
    def test_login_exitoso_devuelve_un_token_bearer(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "sofia@comunicarlos.com.ar", "password": _PASSWORD_SUPERVISOR},
        )

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["token_type"] == "bearer"
        assert respuesta.json()["access_token"]

    def test_login_con_password_incorrecta_devuelve_401(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "sofia@comunicarlos.com.ar", "password": "incorrecta"},
        )

        # Assert
        assert respuesta.status_code == 401

    def test_login_con_email_inexistente_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/login", data={"username": "nadie@x.com", "password": "loquesea"}
        )

        # Assert
        assert respuesta.status_code == 401


class TestPerfilPropio:
    def test_me_devuelve_el_perfil_del_usuario_autenticado(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.get("/usuarios/me", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["email"] == "sofia@comunicarlos.com.ar"
        assert "password" not in respuesta.json()

    def test_sin_token_devuelve_401(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.get("/usuarios/me")

        # Assert
        assert respuesta.status_code == 401


class TestCrearUsuario:
    def test_supervisor_puede_crear_usuarios(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "Nuevo Técnico",
                "email": "nuevo@comunicarlos.com.ar",
                "password": "clave12345",
                "rol": "TECNICO",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["rol"] == "TECNICO"
        assert respuesta.json()["activo"] is True

    def test_rol_no_supervisor_devuelve_403(self, cliente: TestClient, tecnico: Usuario) -> None:
        # Arrange
        token = _token_de(cliente, "beto@comunicarlos.com.ar", _PASSWORD_TECNICO)

        # Act
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "otro@x.com",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 403

    def test_email_duplicado_devuelve_409(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: intenta reusar el email del técnico ya existente
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "beto@comunicarlos.com.ar",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 409

    def test_operador_con_email_no_corporativo_devuelve_400(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: Operador/Técnico/Supervisor requieren "@comunicarlos.com.ar"
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "OPERADOR",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 400

    def test_solicitante_con_email_no_corporativo_se_crea_sin_error(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: el Solicitante no está sujeto a la restricción de dominio corporativo
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "SOLICITANTE",
                "servicios_suscriptos": ["TELEVISION"],
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 201

    def test_solicitante_sin_servicios_suscriptos_devuelve_400(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act: el Solicitante debe suscribirse a al menos un servicio
        respuesta = cliente.post(
            "/usuarios",
            json={
                "nombre_completo": "x",
                "email": "nuevo@gmail.com",
                "password": "clave12345",
                "rol": "SOLICITANTE",
            },
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 400


class TestAdministracionDeUsuarios:
    def test_desactivar_usuario_via_endpoint(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(f"/usuarios/{tecnico.id}/desactivar", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["activo"] is False

    def test_desactivar_usuario_inexistente_devuelve_404(
        self, cliente: TestClient, supervisor: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(f"/usuarios/{uuid.uuid4()}/desactivar", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 404

    def test_listar_usuarios_requiere_supervisor(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.get("/usuarios", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 2

    def test_cambiar_rol_via_endpoint(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, "sofia@comunicarlos.com.ar", _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.patch(
            f"/usuarios/{tecnico.id}/rol",
            json={"nuevo_rol": "OPERADOR"},
            headers=_headers(token),
        )

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json()["rol"] == "OPERADOR"


class TestVerificacionDeSalud:
    def test_health_no_requiere_autenticacion(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.get("/health")

        # Assert
        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok"}


class TestListarTecnicos:
    """`GET /usuarios/tecnicos` (selector de asignación y derivación).

    Contrato: solo Técnicos ACTIVOS, payload mínimo (`id` + `nombre_completo`,
    sin email ni fechas), accesible a Operador/Técnico/Supervisor y nunca a
    un Solicitante.
    """

    def test_operador_obtiene_solo_tecnicos_activos(
        self, cliente: TestClient, repositorio: FakeRepositorioUsuarios, tecnico: Usuario
    ) -> None:
        # Arrange: un operador, un técnico de baja y un solicitante no deben figurar
        operador = Usuario(
            "Rosa Molina",
            "rosa@comunicarlos.com.ar",
            obtener_password_hash(_PASSWORD_SUPERVISOR),
            RolUsuario.OPERADOR,
        )
        repositorio.guardar(operador)
        tecnico_de_baja = Usuario(
            "Ex Técnico", "ex@comunicarlos.com.ar", "hash", RolUsuario.TECNICO
        )
        tecnico_de_baja.desactivar()
        repositorio.guardar(tecnico_de_baja)
        token = _token_de(cliente, operador.email, _PASSWORD_SUPERVISOR)

        # Act
        respuesta = cliente.get("/usuarios/tecnicos", headers=_headers(token))

        # Assert
        assert respuesta.status_code == 200
        assert [u["id"] for u in respuesta.json()] == [str(tecnico.id)]

    def test_payload_minimo_sin_datos_sensibles(
        self, cliente: TestClient, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, tecnico.email, _PASSWORD_TECNICO)

        # Act
        respuesta = cliente.get("/usuarios/tecnicos", headers=_headers(token))

        # Assert: es un dropdown, no una vista de administración
        assert respuesta.status_code == 200
        assert set(respuesta.json()[0]) == {"id", "nombre_completo"}

    def test_supervisor_tambien_accede(
        self, cliente: TestClient, supervisor: Usuario, tecnico: Usuario
    ) -> None:
        # Arrange
        token = _token_de(cliente, supervisor.email, _PASSWORD_SUPERVISOR)

        # Act & Assert
        assert cliente.get("/usuarios/tecnicos", headers=_headers(token)).status_code == 200

    def test_solicitante_recibe_403(
        self, cliente: TestClient, repositorio: FakeRepositorioUsuarios
    ) -> None:
        # Arrange
        solicitante = Usuario(
            "Lucía Gómez",
            "lucia@mail.com",
            obtener_password_hash(_PASSWORD_SUPERVISOR),
            RolUsuario.SOLICITANTE,
            servicios_suscriptos=frozenset({ServicioComunicarlos.TELEVISION}),
        )
        repositorio.guardar(solicitante)
        token = _token_de(cliente, solicitante.email, _PASSWORD_SUPERVISOR)

        # Act & Assert
        assert cliente.get("/usuarios/tecnicos", headers=_headers(token)).status_code == 403

    def test_sin_token_devuelve_401(self, cliente: TestClient) -> None:
        assert cliente.get("/usuarios/tecnicos").status_code == 401


class TestAutoRegistroPublico:
    """`POST /usuarios/registro`: único endpoint sin autenticación.

    Siempre crea un SOLICITANTE: el schema no tiene campo `rol`, así que no
    hay forma de auto-registrarse como Operador/Técnico/Supervisor.
    """

    _BODY = {
        "nombre_completo": "Lucía Gómez",
        "email": "lucia.gomez@mail.com",
        "password": "clave-segura-1",
        "servicios_suscriptos": ["TELEVISION"],
    }

    def test_registro_sin_token_crea_un_solicitante(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.post("/usuarios/registro", json=self._BODY)

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["rol"] == "SOLICITANTE"
        assert respuesta.json()["activo"] is True
        assert "password_hash" not in respuesta.json()

    def test_rol_en_el_body_se_ignora_y_no_escala_privilegios(
        self, cliente: TestClient
    ) -> None:
        # Act: intenta auto-registrarse como SUPERVISOR
        respuesta = cliente.post("/usuarios/registro", json={**self._BODY, "rol": "SUPERVISOR"})

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["rol"] == "SOLICITANTE"

    def test_sin_servicios_suscriptos_devuelve_422(self, cliente: TestClient) -> None:
        # Act & Assert: el schema exige al menos uno (min_length=1)
        cuerpo = {**self._BODY, "servicios_suscriptos": []}
        assert cliente.post("/usuarios/registro", json=cuerpo).status_code == 422

    def test_email_ya_registrado_devuelve_409(self, cliente: TestClient) -> None:
        # Arrange
        assert cliente.post("/usuarios/registro", json=self._BODY).status_code == 201

        # Act & Assert
        assert cliente.post("/usuarios/registro", json=self._BODY).status_code == 409

    def test_puede_iniciar_sesion_inmediatamente(self, cliente: TestClient) -> None:
        # Arrange
        cliente.post("/usuarios/registro", json=self._BODY)

        # Act & Assert
        token = _token_de(cliente, self._BODY["email"], self._BODY["password"])
        perfil = cliente.get("/usuarios/me", headers=_headers(token))
        assert perfil.json()["email"] == self._BODY["email"]


class TestEmailCaseInsensitive:
    """El email es la identidad de login y es case-insensitive.

    `Usuario` lo guarda normalizado (minúsculas), así que toda búsqueda por
    email tiene que normalizar antes de consultar al repositorio. Si no, el
    login con otra capitalización da 401 contra una cuenta que SÍ existe, y
    un alta duplicada esquiva el control de `registrar` y estalla contra el
    índice único de Mongo como un 500 en vez de un 409.
    """

    _BODY = {
        "nombre_completo": "Lucía Gómez",
        "email": "lucia.gomez@mail.com",
        "password": "clave-segura-1",
        "servicios_suscriptos": ["TELEVISION"],
    }

    def test_login_con_otra_capitalizacion_funciona(self, cliente: TestClient) -> None:
        # Arrange
        assert cliente.post("/usuarios/registro", json=self._BODY).status_code == 201

        # Act
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "Lucia.Gomez@Mail.com", "password": self._BODY["password"]},
        )

        # Assert
        assert respuesta.status_code == 200

    def test_login_con_espacios_al_borde_funciona(self, cliente: TestClient) -> None:
        # Arrange
        cliente.post("/usuarios/registro", json=self._BODY)

        # Act & Assert
        respuesta = cliente.post(
            "/usuarios/login",
            data={"username": "  lucia.gomez@mail.com  ", "password": self._BODY["password"]},
        )
        assert respuesta.status_code == 200

    def test_registro_duplicado_con_otra_capitalizacion_devuelve_409(
        self, cliente: TestClient
    ) -> None:
        # Arrange
        assert cliente.post("/usuarios/registro", json=self._BODY).status_code == 201

        # Act: mismo email, distinta capitalización
        respuesta = cliente.post(
            "/usuarios/registro", json={**self._BODY, "email": "LUCIA.GOMEZ@mail.com"}
        )

        # Assert: 409 de negocio, no un 500 por el índice único
        assert respuesta.status_code == 409

    def test_el_email_se_persiste_normalizado(self, cliente: TestClient) -> None:
        # Act
        respuesta = cliente.post(
            "/usuarios/registro", json={**self._BODY, "email": "Lucia.Gomez@Mail.com"}
        )

        # Assert
        assert respuesta.status_code == 201
        assert respuesta.json()["email"] == "lucia.gomez@mail.com"

