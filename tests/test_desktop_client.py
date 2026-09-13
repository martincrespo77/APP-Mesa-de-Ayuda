"""Tests de `desktop/api_client.py` (Paso 6).

Cubre `ApiClienteHttp` (con `httpx.MockTransport`, sin red ni servidor
real), `ApiClienteDemo` (Modo Demostración, en memoria) y la decodificación
de claims del JWT sin verificar firma.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from jose import jwt

from desktop.api_client import (
    ApiClienteDemo,
    ApiClienteHttp,
    ClienteApiError,
    CredencialesInvalidasError,
    SesionNoIniciadaError,
    _claims_del_token,
)
from desktop.models import (
    CategoriaIncidente,
    CategoriaSolicitud,
    EstadoRequerimiento,
    RolUsuario,
    ServicioComunicarlos,
    UrgenciaIncidente,
)

_EMAIL_VALIDO = "sol@comunicarlos.com"
_PASSWORD_VALIDA = "clave-segura-1"
_USUARIO_ID = uuid.uuid4()


def _token_de_prueba(
    usuario_id: uuid.UUID = _USUARIO_ID, rol: RolUsuario = RolUsuario.SOLICITANTE
) -> str:
    """Un JWT con forma válida, firmado con una clave arbitraria.

    `_claims_del_token` no verifica la firma (doc05: el cliente no tiene
    `SECRET_KEY`), así que cualquier clave sirve para el test.
    """
    payload = {"sub": str(usuario_id), "rol": rol.value}
    return jwt.encode(payload, "clave-de-prueba-cualquiera", algorithm="HS256")


def _perfil_json(usuario_id: uuid.UUID = _USUARIO_ID) -> dict[str, Any]:
    return {
        "id": str(usuario_id),
        "nombre_completo": "Sol de Prueba",
        "email": _EMAIL_VALIDO,
        "rol": "SOLICITANTE",
        "activo": True,
    }


def _requerimiento_json(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "titulo": "Corte de fibra",
        "descripcion": "Sin señal.",
        "solicitante_id": str(_USUARIO_ID),
        "estado": "ABIERTO",
        "fecha_creacion": datetime.now(UTC).isoformat(),
        "tecnico_asignado_id": None,
        "nota_resolucion": None,
        "historial": [],
        "tipo": "INCIDENTE",
        "urgencia": "IMPORTANTE",
        "categoria": "SERVICIO_INACCESIBLE",
        "servicio": "INTERNET_BANDA_ANCHA",
        "pasos_reproduccion": "p",
    }
    base.update(overrides)
    return base


def _handler_api_falsa(request: httpx.Request) -> httpx.Response:
    """Simula lo esencial de la API real para probar `ApiClienteHttp`."""
    ruta = request.url.path
    metodo = request.method

    if metodo == "GET" and ruta == "/health":
        return httpx.Response(200, json={"status": "ok"})

    if metodo == "POST" and ruta == "/usuarios/login":
        form = parse_qs(request.content.decode())
        email = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        if email == _EMAIL_VALIDO and password == _PASSWORD_VALIDA:
            token = _token_de_prueba()
            return httpx.Response(200, json={"access_token": token, "token_type": "bearer"})
        return httpx.Response(401, json={"detail": "Email o contraseña incorrectos."})

    if metodo == "GET" and ruta == "/usuarios/me":
        return httpx.Response(200, json=_perfil_json())

    if metodo == "GET" and ruta == "/requerimientos":
        return httpx.Response(200, json=[_requerimiento_json()])

    if metodo == "POST" and ruta == "/requerimientos":
        cuerpo = json.loads(request.content)
        return httpx.Response(201, json=_requerimiento_json(**cuerpo))

    if metodo == "POST" and ruta.endswith("/iniciar-analisis"):
        return httpx.Response(200, json=_requerimiento_json(estado="EN_ANALISIS"))

    if metodo == "POST" and ruta.endswith("/cancelar"):
        return httpx.Response(409, json={"detail": "No se puede cancelar en este estado."})

    raise AssertionError(f"Ruta no simulada en el test: {metodo} {ruta}")


@pytest.fixture
def cliente() -> ApiClienteHttp:
    transporte = httpx.MockTransport(_handler_api_falsa)
    cliente_http = httpx.Client(base_url="http://testserver", transport=transporte)
    return ApiClienteHttp(cliente_http=cliente_http)


class TestClaimsDelToken:
    def test_extrae_id_y_rol_sin_verificar_firma(self) -> None:
        # Arrange
        token = _token_de_prueba(rol=RolUsuario.TECNICO)

        # Act
        usuario_id, rol = _claims_del_token(token)

        # Assert
        assert usuario_id == _USUARIO_ID
        assert rol == RolUsuario.TECNICO


class TestApiClienteHttpSalud:
    def test_verificar_salud_true_si_responde_200(self, cliente: ApiClienteHttp) -> None:
        assert cliente.verificar_salud() is True

    def test_verificar_salud_false_si_hay_error_de_red(self) -> None:
        # Arrange: transporte que siempre lanza un error de conexión
        def _handler_roto(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sin servidor", request=request)

        cliente_roto = ApiClienteHttp(
            cliente_http=httpx.Client(
                base_url="http://testserver", transport=httpx.MockTransport(_handler_roto)
            )
        )

        # Act & Assert
        assert cliente_roto.verificar_salud() is False


class TestApiClienteHttpSesion:
    def test_iniciar_sesion_exitoso_guarda_usuario_actual(self, cliente: ApiClienteHttp) -> None:
        # Act
        usuario = cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Assert
        assert usuario.email == _EMAIL_VALIDO
        assert usuario.rol == RolUsuario.SOLICITANTE
        assert cliente.usuario_actual == usuario

    def test_iniciar_sesion_credenciales_invalidas_lanza_error(
        self, cliente: ApiClienteHttp
    ) -> None:
        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            cliente.iniciar_sesion(_EMAIL_VALIDO, "password-incorrecta")
        assert cliente.usuario_actual is None

    def test_operacion_sin_sesion_lanza_sesion_no_iniciada(self, cliente: ApiClienteHttp) -> None:
        # Act & Assert
        with pytest.raises(SesionNoIniciadaError):
            cliente.listar_requerimientos()

    def test_cerrar_sesion_limpia_token_y_usuario(self, cliente: ApiClienteHttp) -> None:
        # Arrange
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act
        cliente.cerrar_sesion()

        # Assert
        assert cliente.usuario_actual is None
        with pytest.raises(SesionNoIniciadaError):
            cliente.listar_requerimientos()


class TestApiClienteHttpRequerimientos:
    def test_listar_requerimientos_devuelve_dtos(self, cliente: ApiClienteHttp) -> None:
        # Arrange
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act
        requerimientos = cliente.listar_requerimientos()

        # Assert
        assert len(requerimientos) == 1
        assert requerimientos[0].estado == EstadoRequerimiento.ABIERTO

    def test_historial_con_eventos_de_comentario_derivacion_y_reapertura(self) -> None:
        """Regresión: un ticket con comentarios/derivación (solo API, sin UI en
        desktop/) igual aparece en su `historial` y no debe romper el parseo,
        aunque el cliente no tenga pantallas para generarlos."""

        # Arrange
        def _handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/usuarios/login":
                return httpx.Response(
                    200, json={"access_token": _token_de_prueba(), "token_type": "bearer"}
                )
            if request.method == "GET" and request.url.path == "/usuarios/me":
                return httpx.Response(200, json=_perfil_json())
            if request.method == "GET" and request.url.path == "/requerimientos":
                return httpx.Response(
                    200,
                    json=[
                        _requerimiento_json(
                            historial=[
                                {
                                    "id": str(uuid.uuid4()),
                                    "tipo_evento": "COMENTARIO",
                                    "autor_id": str(_USUARIO_ID),
                                    "detalle": "Un comentario.",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                                {
                                    "id": str(uuid.uuid4()),
                                    "tipo_evento": "DERIVACION",
                                    "autor_id": str(_USUARIO_ID),
                                    "detalle": "Derivado a otro técnico.",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                                {
                                    "id": str(uuid.uuid4()),
                                    "tipo_evento": "REAPERTURA",
                                    "autor_id": str(_USUARIO_ID),
                                    "detalle": "Reabierto.",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                            ]
                        )
                    ],
                )
            raise AssertionError(f"Ruta no simulada: {request.method} {request.url.path}")

        cliente = ApiClienteHttp(
            cliente_http=httpx.Client(
                base_url="http://testserver", transport=httpx.MockTransport(_handler)
            )
        )
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act
        requerimientos = cliente.listar_requerimientos()

        # Assert
        tipos = [e.tipo_evento.value for e in requerimientos[0].historial]
        assert tipos == ["COMENTARIO", "DERIVACION", "REAPERTURA"]

    def test_crear_incidente_envia_datos_y_parsea_la_respuesta(
        self, cliente: ApiClienteHttp
    ) -> None:
        # Arrange
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act
        creado = cliente.crear_incidente(
            titulo="Router no enciende",
            descripcion="Sin luces.",
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.PERDIDA_O_DESTRUCCION_DE_EQUIPO,
            servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
            pasos_reproduccion="Ver led.",
        )

        # Assert
        assert creado.titulo == "Router no enciende"
        assert creado.urgencia == UrgenciaIncidente.MENOR

    def test_iniciar_analisis_devuelve_requerimiento_actualizado(
        self, cliente: ApiClienteHttp
    ) -> None:
        # Arrange
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act
        actualizado = cliente.iniciar_analisis(uuid.uuid4())

        # Assert
        assert actualizado.estado == EstadoRequerimiento.EN_ANALISIS

    def test_transicion_rechazada_lanza_cliente_api_error_con_el_detalle(
        self, cliente: ApiClienteHttp
    ) -> None:
        # Arrange
        cliente.iniciar_sesion(_EMAIL_VALIDO, _PASSWORD_VALIDA)

        # Act & Assert
        with pytest.raises(ClienteApiError, match="No se puede cancelar"):
            cliente.cancelar(uuid.uuid4())


class TestApiClienteDemo:
    def test_verificar_salud_siempre_true(self) -> None:
        assert ApiClienteDemo().verificar_salud() is True

    def test_login_con_password_incorrecta_lanza_error(self) -> None:
        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            ApiClienteDemo().iniciar_sesion("solicitante@demo.coop", "cualquier-cosa")

    def test_login_con_email_desconocido_lanza_error(self) -> None:
        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            ApiClienteDemo().iniciar_sesion("no-existe@demo.coop", "demo1234")

    def test_login_exitoso_por_cada_rol(self) -> None:
        # Arrange
        emails_por_rol = {
            RolUsuario.SOLICITANTE: "solicitante@demo.coop",
            RolUsuario.OPERADOR: "operador@demo.coop",
            RolUsuario.TECNICO: "tecnico@demo.coop",
            RolUsuario.SUPERVISOR: "supervisor@demo.coop",
        }
        for rol, email in emails_por_rol.items():
            # Act
            usuario = ApiClienteDemo().iniciar_sesion(email, "demo1234")
            # Assert
            assert usuario.rol == rol

    def test_solicitante_ve_solo_sus_propios_requerimientos(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("solicitante@demo.coop", "demo1234")

        # Act
        visibles = cliente.listar_requerimientos()

        # Assert: el dataset demo solo tiene tickets del solicitante de demo
        assert len(visibles) >= 1
        assert all(r.solicitante_id == cliente.usuario_actual.id for r in visibles)  # type: ignore[union-attr]

    def test_operador_ve_todos_los_requerimientos(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("operador@demo.coop", "demo1234")

        # Act
        visibles = cliente.listar_requerimientos()

        # Assert
        assert len(visibles) == 3

    def test_crear_incidente_lo_agrega_a_la_lista(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("solicitante@demo.coop", "demo1234")
        cantidad_previa = len(cliente.listar_requerimientos())

        # Act
        nuevo = cliente.crear_incidente(
            titulo="Nuevo incidente",
            descripcion="d",
            urgencia=UrgenciaIncidente.IMPORTANTE,
            categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
            servicio=ServicioComunicarlos.TELEVISION,
            pasos_reproduccion="p",
        )

        # Assert
        assert len(cliente.listar_requerimientos()) == cantidad_previa + 1
        assert nuevo.estado == EstadoRequerimiento.ABIERTO
        assert len(nuevo.historial) == 1

    def test_crear_solicitud_queda_visible(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("solicitante@demo.coop", "demo1234")

        # Act
        nueva = cliente.crear_solicitud(
            titulo="Cambio de plan",
            descripcion="d",
            categoria=CategoriaSolicitud.BAJA_SERVICIO,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
        )

        # Assert
        assert nueva in cliente.listar_requerimientos()

    def test_transicion_actualiza_estado_y_agrega_evento_al_historial(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("operador@demo.coop", "demo1234")
        objetivo = next(
            r for r in cliente.listar_requerimientos() if r.estado == EstadoRequerimiento.ABIERTO
        )
        eventos_previos = len(objetivo.historial)

        # Act
        actualizado = cliente.iniciar_analisis(objetivo.id)

        # Assert
        assert actualizado.estado == EstadoRequerimiento.EN_ANALISIS
        assert len(actualizado.historial) == eventos_previos + 1

    def test_asignar_tecnico_no_cambia_el_estado(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("operador@demo.coop", "demo1234")
        objetivo = next(
            r for r in cliente.listar_requerimientos() if r.estado == EstadoRequerimiento.ABIERTO
        )
        tecnico_id = uuid.uuid4()

        # Act
        actualizado = cliente.asignar_tecnico(objetivo.id, tecnico_id)

        # Assert
        assert actualizado.estado == objetivo.estado
        assert actualizado.tecnico_asignado_id == tecnico_id

    def test_resolver_exige_transicion_previa_no_falla_por_estado(self) -> None:
        # Arrange: el dataset demo ya trae un incidente en EN_PROGRESO
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("operador@demo.coop", "demo1234")
        objetivo = next(
            r
            for r in cliente.listar_requerimientos()
            if r.estado == EstadoRequerimiento.EN_PROGRESO
        )

        # Act
        resuelto = cliente.resolver(objetivo.id, "Se solucionó (demo).")

        # Assert
        assert resuelto.estado == EstadoRequerimiento.RESUELTO
        assert resuelto.nota_resolucion == "Se solucionó (demo)."

    def test_operacion_sobre_id_inexistente_lanza_cliente_api_error(self) -> None:
        # Arrange
        cliente = ApiClienteDemo()
        cliente.iniciar_sesion("operador@demo.coop", "demo1234")

        # Act & Assert
        with pytest.raises(ClienteApiError):
            cliente.cerrar(uuid.uuid4())

    def test_operacion_sin_sesion_lanza_sesion_no_iniciada(self) -> None:
        # Act & Assert
        with pytest.raises(SesionNoIniciadaError):
            ApiClienteDemo().listar_requerimientos()

    def test_dos_instancias_de_demo_no_comparten_estado(self) -> None:
        # Arrange
        cliente_a = ApiClienteDemo()
        cliente_a.iniciar_sesion("solicitante@demo.coop", "demo1234")
        cliente_b = ApiClienteDemo()
        cliente_b.iniciar_sesion("solicitante@demo.coop", "demo1234")

        # Act
        cliente_a.crear_incidente(
            titulo="Solo en A",
            descripcion="d",
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            pasos_reproduccion="p",
        )

        # Assert
        titulos_b = {r.titulo for r in cliente_b.listar_requerimientos()}
        assert "Solo en A" not in titulos_b
