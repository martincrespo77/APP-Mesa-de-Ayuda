"""Cliente de comunicación con la API (Paso 6).

`ClienteApi` es el puerto abstracto — mismo patrón que
`RepositorioUsuarios`/`RepositorioRequerimientos` en el backend, aplicado
acá del lado del cliente: `ApiClienteHttp` habla HTTP real con FastAPI vía
`httpx`; `ApiClienteDemo` devuelve datos sintéticos predefinidos sin red,
para el Modo Demostración (doc05). Las vistas de Qt programan contra
`ClienteApi` y nunca preguntan "¿estoy en demo?".
"""

import dataclasses
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from jose import jwt

from desktop.models import (
    CategoriaSolicitud,
    EstadoRequerimiento,
    EventoDTO,
    RequerimientoDTO,
    RolUsuario,
    Severidad,
    TipoEventoRequerimiento,
    TipoRequerimiento,
    UsuarioDTO,
)

_URL_BASE_POR_DEFECTO = "http://localhost:8000"


class ClienteApiError(Exception):
    """Error de comunicación o de negocio devuelto por la API."""


class CredencialesInvalidasError(ClienteApiError):
    """Login rechazado."""


class SesionNoIniciadaError(ClienteApiError):
    """Se intentó una operación que requiere sesión antes de `iniciar_sesion`."""


def _claims_del_token(token: str) -> tuple[uuid.UUID, RolUsuario]:
    """Extrae `(usuario_id, rol)` del payload de un JWT, sin verificar la firma.

    El cliente de escritorio no tiene `SECRET_KEY` (doc05): solo necesita
    leer los claims que la API ya validó al emitir el token.
    """
    claims = jwt.get_unverified_claims(token)
    return uuid.UUID(claims["sub"]), RolUsuario(claims["rol"])


class ClienteApi(ABC):
    """Puerto abstracto de comunicación con el backend.

    Mantiene el token/usuario de sesión en memoria tras `iniciar_sesion`
    (doc05: "Manejo de Sesión"): los demás métodos no vuelven a pedirlo.
    """

    @property
    @abstractmethod
    def usuario_actual(self) -> UsuarioDTO | None:
        """El usuario autenticado, o `None` si no hay sesión iniciada."""

    @abstractmethod
    def verificar_salud(self) -> bool:
        """True si la API responde (`GET /health`)."""

    @abstractmethod
    def iniciar_sesion(self, email: str, password: str) -> UsuarioDTO:
        """Autentica y deja la sesión activa; devuelve el perfil completo."""

    @abstractmethod
    def cerrar_sesion(self) -> None:
        """Descarta el token/usuario de sesión en memoria."""

    @abstractmethod
    def listar_requerimientos(self) -> list[RequerimientoDTO]:
        """Requerimientos visibles para el usuario actual (matriz de roles)."""

    @abstractmethod
    def crear_incidente(
        self,
        titulo: str,
        descripcion: str,
        severidad: Severidad,
        pasos_reproduccion: str,
        servicio_afectado: str,
    ) -> RequerimientoDTO: ...

    @abstractmethod
    def crear_solicitud(
        self,
        titulo: str,
        descripcion: str,
        categoria: CategoriaSolicitud,
        fecha_limite: datetime,
        impacto_estimado: str,
    ) -> RequerimientoDTO: ...

    @abstractmethod
    def iniciar_analisis(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO: ...

    @abstractmethod
    def asignar_tecnico(
        self, requerimiento_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> RequerimientoDTO: ...

    @abstractmethod
    def iniciar_progreso(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO: ...

    @abstractmethod
    def resolver(self, requerimiento_id: uuid.UUID, nota_resolucion: str) -> RequerimientoDTO: ...

    @abstractmethod
    def cerrar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO: ...

    @abstractmethod
    def cancelar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO: ...


class ApiClienteHttp(ClienteApi):
    """Implementación real: habla HTTP con FastAPI vía `httpx`."""

    def __init__(
        self, base_url: str = _URL_BASE_POR_DEFECTO, cliente_http: httpx.Client | None = None
    ) -> None:
        self._cliente = cliente_http or httpx.Client(base_url=base_url, timeout=10.0)
        self._token: str | None = None
        self._usuario: UsuarioDTO | None = None

    @property
    def usuario_actual(self) -> UsuarioDTO | None:
        return self._usuario

    def verificar_salud(self) -> bool:
        try:
            return self._cliente.get("/health").status_code == httpx.codes.OK
        except httpx.HTTPError:
            return False

    def iniciar_sesion(self, email: str, password: str) -> UsuarioDTO:
        respuesta = self._cliente.post(
            "/usuarios/login", data={"username": email, "password": password}
        )
        if respuesta.status_code == httpx.codes.UNAUTHORIZED:
            raise CredencialesInvalidasError("Email o contraseña incorrectos.")
        respuesta.raise_for_status()
        self._token = respuesta.json()["access_token"]
        self._usuario = UsuarioDTO.desde_json(self._solicitar("GET", "/usuarios/me"))
        return self._usuario

    def cerrar_sesion(self) -> None:
        self._token = None
        self._usuario = None

    def listar_requerimientos(self) -> list[RequerimientoDTO]:
        datos = self._solicitar("GET", "/requerimientos")
        return [RequerimientoDTO.desde_json(item) for item in datos]

    def crear_incidente(
        self,
        titulo: str,
        descripcion: str,
        severidad: Severidad,
        pasos_reproduccion: str,
        servicio_afectado: str,
    ) -> RequerimientoDTO:
        cuerpo = {
            "tipo": "INCIDENTE",
            "titulo": titulo,
            "descripcion": descripcion,
            "severidad": severidad.value,
            "pasos_reproduccion": pasos_reproduccion,
            "servicio_afectado": servicio_afectado,
        }
        return RequerimientoDTO.desde_json(self._solicitar("POST", "/requerimientos", json=cuerpo))

    def crear_solicitud(
        self,
        titulo: str,
        descripcion: str,
        categoria: CategoriaSolicitud,
        fecha_limite: datetime,
        impacto_estimado: str,
    ) -> RequerimientoDTO:
        cuerpo = {
            "tipo": "SOLICITUD",
            "titulo": titulo,
            "descripcion": descripcion,
            "categoria": categoria.value,
            "fecha_limite": fecha_limite.isoformat(),
            "impacto_estimado": impacto_estimado,
        }
        return RequerimientoDTO.desde_json(self._solicitar("POST", "/requerimientos", json=cuerpo))

    def iniciar_analisis(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/iniciar-analisis"
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta))

    def asignar_tecnico(
        self, requerimiento_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/asignar-tecnico"
        cuerpo = {"tecnico_id": str(tecnico_id)}
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta, json=cuerpo))

    def iniciar_progreso(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/iniciar-progreso"
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta))

    def resolver(self, requerimiento_id: uuid.UUID, nota_resolucion: str) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/resolver"
        cuerpo = {"nota_resolucion": nota_resolucion}
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta, json=cuerpo))

    def cerrar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/cerrar"
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta))

    def cancelar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        ruta = f"/requerimientos/{requerimiento_id}/cancelar"
        return RequerimientoDTO.desde_json(self._solicitar("POST", ruta))

    def _solicitar(self, metodo: str, ruta: str, **kwargs: Any) -> Any:
        if self._token is None:
            raise SesionNoIniciadaError("No hay una sesión iniciada.")
        encabezados = {"Authorization": f"Bearer {self._token}"}
        respuesta = self._cliente.request(metodo, ruta, headers=encabezados, **kwargs)
        if respuesta.status_code >= httpx.codes.BAD_REQUEST:
            detalle = respuesta.json().get("detail", respuesta.text)
            raise ClienteApiError(str(detalle))
        return respuesta.json()


# -- Modo Demostración --------------------------------------------------------

_PASSWORD_DEMO = "demo1234"


def _evento(tipo_evento: TipoEventoRequerimiento, autor_id: uuid.UUID, detalle: str) -> EventoDTO:
    return EventoDTO(
        id=uuid.uuid4(),
        tipo_evento=tipo_evento,
        autor_id=autor_id,
        detalle=detalle,
        timestamp=datetime.now(UTC),
    )


def _usuarios_demo() -> dict[str, UsuarioDTO]:
    """Un usuario por cada uno de los 4 roles, indexados por email."""
    datos = (
        ("Lucía Gómez", "solicitante@demo.coop", RolUsuario.SOLICITANTE),
        ("Rosa Molina", "operador@demo.coop", RolUsuario.OPERADOR),
        ("Iván Ríos", "tecnico@demo.coop", RolUsuario.TECNICO),
        ("Sofía Jefa", "supervisor@demo.coop", RolUsuario.SUPERVISOR),
    )
    return {
        email: UsuarioDTO(
            id=uuid.uuid4(), nombre_completo=nombre, email=email, rol=rol, activo=True
        )
        for nombre, email, rol in datos
    }


def _requerimientos_demo(usuarios: dict[str, UsuarioDTO]) -> list[RequerimientoDTO]:
    """Incidentes y solicitudes cubriendo varios estados, para el Modo Demo."""
    solicitante = usuarios["solicitante@demo.coop"]
    tecnico = usuarios["tecnico@demo.coop"]
    ahora = datetime.now(UTC)

    incidente_abierto = RequerimientoDTO(
        id=uuid.uuid4(),
        tipo=TipoRequerimiento.INCIDENTE,
        titulo="Corte de fibra en Barrio Centro",
        descripcion="Sin conectividad desde esta mañana.",
        solicitante_id=solicitante.id,
        estado=EstadoRequerimiento.ABIERTO,
        fecha_creacion=ahora,
        tecnico_asignado_id=None,
        nota_resolucion=None,
        historial=(_evento(TipoEventoRequerimiento.CREACION, solicitante.id, "Creado (demo)."),),
        severidad=Severidad.CRITICA,
        pasos_reproduccion="ONT sin luz de señal.",
        servicio_afectado="Fibra óptica residencial",
    )

    incidente_en_progreso = RequerimientoDTO(
        id=uuid.uuid4(),
        tipo=TipoRequerimiento.INCIDENTE,
        titulo="Intermitencia en telefonía IP",
        descripcion="Cortes de llamada cada pocos minutos.",
        solicitante_id=solicitante.id,
        estado=EstadoRequerimiento.EN_PROGRESO,
        fecha_creacion=ahora,
        tecnico_asignado_id=tecnico.id,
        nota_resolucion=None,
        historial=(
            _evento(TipoEventoRequerimiento.CREACION, solicitante.id, "Creado (demo)."),
            _evento(TipoEventoRequerimiento.ASIGNACION, tecnico.id, "Técnico asignado (demo)."),
        ),
        severidad=Severidad.MEDIA,
        pasos_reproduccion="Llamar y esperar 5 minutos.",
        servicio_afectado="Telefonía IP",
    )

    solicitud_abierta = RequerimientoDTO(
        id=uuid.uuid4(),
        tipo=TipoRequerimiento.SOLICITUD,
        titulo="Alta de nuevo servicio de internet",
        descripcion="Cliente nuevo solicita instalación.",
        solicitante_id=solicitante.id,
        estado=EstadoRequerimiento.ABIERTO,
        fecha_creacion=ahora,
        tecnico_asignado_id=None,
        nota_resolucion=None,
        historial=(_evento(TipoEventoRequerimiento.CREACION, solicitante.id, "Creado (demo)."),),
        categoria=CategoriaSolicitud.NUEVO_SERVICIO,
        fecha_limite=ahora + timedelta(days=10),
        impacto_estimado="Bajo",
    )

    return [incidente_abierto, incidente_en_progreso, solicitud_abierta]


class ApiClienteDemo(ClienteApi):
    """Implementación sintética: sin red, para evaluar la interfaz (doc05).

    No reimplementa la máquina de estados ni la matriz de permisos del
    dominio (eso vive en `app/`, y a propósito no se importa acá): aplica
    las transiciones de forma permisiva, solo para que la interfaz tenga
    algo que mostrar al interactuar con los botones.
    """

    def __init__(self) -> None:
        self._usuarios = _usuarios_demo()
        self._requerimientos: dict[uuid.UUID, RequerimientoDTO] = {
            req.id: req for req in _requerimientos_demo(self._usuarios)
        }
        self._usuario: UsuarioDTO | None = None

    @property
    def usuario_actual(self) -> UsuarioDTO | None:
        return self._usuario

    def verificar_salud(self) -> bool:
        return True

    def iniciar_sesion(self, email: str, password: str) -> UsuarioDTO:
        usuario = self._usuarios.get(email.strip().lower())
        if usuario is None or password != _PASSWORD_DEMO:
            raise CredencialesInvalidasError(
                f"Credenciales de demo inválidas. Usá la contraseña '{_PASSWORD_DEMO}' "
                f"con alguno de los emails de demo (ver login)."
            )
        self._usuario = usuario
        return usuario

    def cerrar_sesion(self) -> None:
        self._usuario = None

    def listar_requerimientos(self) -> list[RequerimientoDTO]:
        usuario = self._exigir_sesion()
        todos = list(self._requerimientos.values())
        if usuario.rol is RolUsuario.SOLICITANTE:
            return [req for req in todos if req.solicitante_id == usuario.id]
        return todos

    def crear_incidente(
        self,
        titulo: str,
        descripcion: str,
        severidad: Severidad,
        pasos_reproduccion: str,
        servicio_afectado: str,
    ) -> RequerimientoDTO:
        usuario = self._exigir_sesion()
        nuevo = RequerimientoDTO(
            id=uuid.uuid4(),
            tipo=TipoRequerimiento.INCIDENTE,
            titulo=titulo,
            descripcion=descripcion,
            solicitante_id=usuario.id,
            estado=EstadoRequerimiento.ABIERTO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=None,
            nota_resolucion=None,
            historial=(_evento(TipoEventoRequerimiento.CREACION, usuario.id, "Creado (demo)."),),
            severidad=severidad,
            pasos_reproduccion=pasos_reproduccion,
            servicio_afectado=servicio_afectado,
        )
        self._requerimientos[nuevo.id] = nuevo
        return nuevo

    def crear_solicitud(
        self,
        titulo: str,
        descripcion: str,
        categoria: CategoriaSolicitud,
        fecha_limite: datetime,
        impacto_estimado: str,
    ) -> RequerimientoDTO:
        usuario = self._exigir_sesion()
        nuevo = RequerimientoDTO(
            id=uuid.uuid4(),
            tipo=TipoRequerimiento.SOLICITUD,
            titulo=titulo,
            descripcion=descripcion,
            solicitante_id=usuario.id,
            estado=EstadoRequerimiento.ABIERTO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=None,
            nota_resolucion=None,
            historial=(_evento(TipoEventoRequerimiento.CREACION, usuario.id, "Creado (demo)."),),
            categoria=categoria,
            fecha_limite=fecha_limite,
            impacto_estimado=impacto_estimado,
        )
        self._requerimientos[nuevo.id] = nuevo
        return nuevo

    def iniciar_analisis(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.CAMBIO_ESTADO,
            "Estado cambiado a EN_ANALISIS (demo).",
            nuevo_estado=EstadoRequerimiento.EN_ANALISIS,
        )

    def asignar_tecnico(
        self, requerimiento_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.ASIGNACION,
            f"Técnico '{tecnico_id}' asignado (demo).",
            tecnico_asignado_id=tecnico_id,
        )

    def iniciar_progreso(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.CAMBIO_ESTADO,
            "Estado cambiado a EN_PROGRESO (demo).",
            nuevo_estado=EstadoRequerimiento.EN_PROGRESO,
        )

    def resolver(self, requerimiento_id: uuid.UUID, nota_resolucion: str) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.RESOLUCION,
            f"Requerimiento resuelto (demo): {nota_resolucion}",
            nuevo_estado=EstadoRequerimiento.RESUELTO,
            nota_resolucion=nota_resolucion,
        )

    def cerrar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.CIERRE,
            "Requerimiento cerrado (demo).",
            nuevo_estado=EstadoRequerimiento.CERRADO,
        )

    def cancelar(self, requerimiento_id: uuid.UUID) -> RequerimientoDTO:
        return self._transicionar(
            requerimiento_id,
            TipoEventoRequerimiento.CANCELACION,
            "Requerimiento cancelado (demo).",
            nuevo_estado=EstadoRequerimiento.CANCELADO,
        )

    def _exigir_sesion(self) -> UsuarioDTO:
        if self._usuario is None:
            raise SesionNoIniciadaError("No hay una sesión iniciada.")
        return self._usuario

    def _transicionar(
        self,
        requerimiento_id: uuid.UUID,
        tipo_evento: TipoEventoRequerimiento,
        detalle: str,
        nuevo_estado: EstadoRequerimiento | None = None,
        **cambios: Any,
    ) -> RequerimientoDTO:
        usuario = self._exigir_sesion()
        actual = self._requerimientos.get(requerimiento_id)
        if actual is None:
            raise ClienteApiError(f"No existe el requerimiento '{requerimiento_id}'.")
        evento = _evento(tipo_evento, usuario.id, detalle)
        actualizado = dataclasses.replace(
            actual,
            estado=nuevo_estado if nuevo_estado is not None else actual.estado,
            historial=(*actual.historial, evento),
            **cambios,
        )
        self._requerimientos[requerimiento_id] = actualizado
        return actualizado
