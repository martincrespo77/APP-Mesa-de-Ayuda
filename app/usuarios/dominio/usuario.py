"""Entidad abstracta `Usuario`: raíz de la jerarquía polimórfica por rol.

Cada rol de negocio es una subclase (`Solicitante`, `Operador`, `Tecnico`,
`Supervisor`) que responde por sí misma qué puede y qué no puede hacer
según la matriz de roles. Así, ni los servicios ni `Requerimiento`
preguntan "¿qué rol tenés?" para decidir: le preguntan al usuario
"¿podés cerrar este ticket?" y cada subclase contesta (polimorfismo en
lugar de `if rol == ...`).

La base responde `False` a todas las preguntas de permiso: un permiso solo
existe si la subclase lo declara explícitamente. Cuando una operación exige
un permiso, el propio usuario lo hace cumplir (`exigir_autorizacion`, Tell,
Don't Ask): nadie más lee su rol para armar el mensaje de error. La
visibilidad de tickets es una Specification pura (`criterio_visibilidad`),
sin acoplar la entidad al repositorio. El hashing real de
contraseñas (`bcrypt`) es responsabilidad de infraestructura (`app/auth.py`);
la entidad recibe la función de verificación por inyección.
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.compartido.validaciones import texto_obligatorio
from app.requerimientos.excepciones import PermisoDenegadoError, TecnicoInvalidoError
from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import RolNoSupervisableError, SupervisionNoPermitidaError
from app.usuarios.dominio.email import Email
from app.usuarios.excepciones import (
    CredencialesInvalidasError,
    UsuarioYaActivoError,
    UsuarioYaInactivoError,
)

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.dominio.criterios.base import CriterioVisibilidad


class Usuario(ABC):
    """Persona registrada en el sistema, con un rol de negocio y un estado."""

    def __init__(
        self,
        nombre_completo: str,
        email: str,
        password_hash: str,
        servicios_suscriptos: frozenset[ServicioComunicarlos] | None = None,
        id: uuid.UUID | None = None,
        activo: bool = True,
        fecha_creacion: datetime | None = None,
        ultimo_acceso: datetime | None = None,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.nombre_completo = texto_obligatorio(nombre_completo, "nombre completo")
        self._email = Email(email)
        self._exigir_email_admitido(self._email)
        self._password_hash = texto_obligatorio(
            password_hash, "hash de contraseña", recortar=False
        )
        self._activo = activo
        self._servicios_suscriptos = frozenset(servicios_suscriptos or ())
        self._exigir_suscripciones_admitidas(self._servicios_suscriptos)
        self._fecha_creacion = fecha_creacion or datetime.now(UTC)
        self._ultimo_acceso = ultimo_acceso

    # -- Identidad y estado ----------------------------------------------------

    @property
    @abstractmethod
    def rol(self) -> RolUsuario:
        """Discriminador del rol (para persistencia, JWT y DTOs; nunca para decidir permisos)."""

    @property
    def email(self) -> str:
        return str(self._email)

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def servicios_suscriptos(self) -> frozenset[ServicioComunicarlos]:
        return self._servicios_suscriptos

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @property
    def ultimo_acceso(self) -> datetime | None:
        return self._ultimo_acceso

    # -- Comportamiento de cuenta ----------------------------------------------

    def autenticar(self, password: str, verificador: Callable[[str, str], bool]) -> None:
        """Valida la contraseña y que la cuenta esté activa; registra el acceso.

        `verificador` es la función de infraestructura (bcrypt) que compara
        el texto plano con el hash: la entidad decide CUÁNDO un login es
        válido, infraestructura solo sabe CÓMO comparar hashes.
        """
        if not self._activo or not verificador(password, self._password_hash):
            raise CredencialesInvalidasError("Email o contraseña incorrectos.")
        self.registrar_acceso()

    def registrar_acceso(self) -> None:
        """Marca este instante como el último acceso exitoso del usuario."""
        self._ultimo_acceso = datetime.now(UTC)

    def activar(self) -> None:
        """Reactiva a un usuario previamente desactivado."""
        if self._activo:
            raise UsuarioYaActivoError(f"El usuario '{self.email}' ya está activo.")
        self._activo = True

    def desactivar(self) -> None:
        """Da de baja lógica a un usuario (ej. egreso de la cooperativa)."""
        if not self._activo:
            raise UsuarioYaInactivoError(f"El usuario '{self.email}' ya está inactivo.")
        self._activo = False

    def cambiar_password_hash(self, nuevo_password_hash: str) -> None:
        """Reemplaza el hash de contraseña por uno nuevo ya calculado en infraestructura."""
        self._password_hash = texto_obligatorio(
            nuevo_password_hash, "hash de contraseña", recortar=False
        )

    def cambiar_rol(self, nuevo_rol: RolUsuario) -> "Usuario":
        """Devuelve este mismo usuario (mismo id y datos) encarnado en el nuevo rol.

        Con un rol por subclase, cambiar de rol es cambiar de clase: no se
        muta `self`, se construye la instancia del rol destino, cuyo propio
        constructor valida lo que ese rol exige (email corporativo para un
        empleado, al menos un servicio suscripto para un Solicitante).
        """
        # Import diferido: la fábrica conoce a todas las subclases, que a su
        # vez heredan de este módulo.
        from app.usuarios.dominio.fabrica import FabricaUsuarios

        return FabricaUsuarios.crear(
            nuevo_rol,
            id=self.id,
            nombre_completo=self.nombre_completo,
            email=self.email,
            password_hash=self._password_hash,
            servicios_suscriptos=self._servicios_suscriptos,
            activo=self._activo,
            fecha_creacion=self._fecha_creacion,
            ultimo_acceso=self._ultimo_acceso,
        )

    # -- Invariantes propias de cada rol (Template Method) ---------------------

    @abstractmethod
    def _exigir_email_admitido(self, email: Email) -> None:
        """Cada rol decide qué emails admite (ej. los empleados, solo el corporativo)."""

    @abstractmethod
    def _exigir_suscripciones_admitidas(
        self, servicios: frozenset[ServicioComunicarlos]
    ) -> None:
        """Cada rol decide si puede (o debe) tener servicios suscriptos."""

    # -- Preguntas de la matriz de roles (por defecto: no puede) ---------------

    @abstractmethod
    def criterio_visibilidad(self) -> "CriterioVisibilidad":
        """Specification de los tickets que este usuario puede ver.

        Cada rol declara SU criterio (el Solicitante, los que abrió; un
        empleado, la bandeja completa) y el servicio se lo entrega al
        repositorio, que sabe ejecutarlo: la entidad no conoce la persistencia.
        """

    def puede_ver(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_iniciar_analisis(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_asignar_tecnico(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_iniciar_progreso(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_resolver(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_cerrar(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_cancelar(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_comentar(self, requerimiento: "Requerimiento") -> bool:
        return False

    def reabre_al_comentar(self) -> bool:
        """¿Un comentario suyo sobre un ticket RESUELTO lo reabre a EN_PROGRESO?"""
        return False

    def puede_reabrir(self, requerimiento: "Requerimiento") -> bool:
        """¿Puede reabrir ESTE ticket? Solo quien puede comentarlo y reabre al comentar."""
        return self.reabre_al_comentar() and self.puede_comentar(requerimiento)

    def puede_derivar(self, requerimiento: "Requerimiento") -> bool:
        return False

    def puede_recibir_requerimientos(self) -> bool:
        """¿Se le puede asignar o derivar un ticket?"""
        return False

    def puede_consultar_tecnicos(self) -> bool:
        """¿Necesita ver el listado de técnicos (para asignar o derivar)?"""
        return False

    def es_supervisable(self) -> bool:
        """¿Un Supervisor puede auditar sus acciones?"""
        return False

    def puede_administrar_usuarios(self) -> bool:
        return False

    def puede_administrar_supervisiones(self) -> bool:
        return False

    def recibe_notificaciones(self) -> bool:
        return False

    # -- Exigencias: el propio usuario hace cumplir sus respuestas ------------

    def exigir_autorizacion(self, autorizado: bool, accion: str) -> None:
        """Lanza `PermisoDenegadoError` si la respuesta a un `puede_*` fue negativa.

        Uso: `actor.exigir_autorizacion(actor.puede_cerrar(ticket), "dar cierre")`.
        """
        if not autorizado:
            raise PermisoDenegadoError(f"El rol '{self.rol.value}' no puede {accion}.")

    def exigir_que_pueda_recibir_requerimientos(self) -> None:
        """Lanza `TecnicoInvalidoError` si no se le puede asignar ni derivar un ticket."""
        if not self.puede_recibir_requerimientos():
            raise TecnicoInvalidoError(
                f"El usuario '{self.id}' no es un Técnico activo: solo se puede asignar "
                "o derivar un requerimiento a un Técnico activo."
            )

    def exigir_supervisable(self) -> None:
        """Lanza `RolNoSupervisableError` si un Supervisor no puede auditarlo."""
        if not self.es_supervisable():
            raise RolNoSupervisableError(f"El rol '{self.rol.value}' no puede ser supervisado.")

    def supervisar(self, empleado: "Usuario") -> RelacionSupervision:
        """Solo un `Supervisor` puede supervisar (lo sobrescribe); el resto, no."""
        raise SupervisionNoPermitidaError(
            f"El rol '{self.rol.value}' no puede supervisar a otros usuarios."
        )
