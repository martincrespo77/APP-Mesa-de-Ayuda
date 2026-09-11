"""Entidad abstracta `Requerimiento`.

Clase base de la jerarquía polimórfica `Incidente` / `Solicitud`. Concentra
los atributos comunes, la máquina de estados y las reglas de permisos por
rol para cada transición (Information Expert: la propia entidad decide si
una transición es válida y quién puede ejecutarla).
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.compartido.dominio import RolUsuario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)

_ROLES_ASIGNACION = {RolUsuario.OPERADOR, RolUsuario.SUPERVISOR}
_ROLES_CIERRE = {RolUsuario.OPERADOR, RolUsuario.SUPERVISOR}
_ROLES_CANCELACION_AMPLIA = {RolUsuario.OPERADOR, RolUsuario.SUPERVISOR}


class Requerimiento(ABC):
    """Ticket de la Mesa de Ayuda, en su forma de `Incidente` o `Solicitud`."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        id: uuid.UUID | None = None,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.titulo = self._validar_titulo(titulo)
        self.descripcion = self._validar_descripcion(descripcion)
        self.solicitante_id = solicitante_id
        self.estado = EstadoRequerimiento.ABIERTO
        self.fecha_creacion = datetime.now(UTC)
        self.tecnico_asignado_id: uuid.UUID | None = None
        self.nota_resolucion: str | None = None
        self._historial: list[EventoRequerimiento] = []
        self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CREACION,
            autor_id=self.solicitante_id,
            detalle=f"Requerimiento '{self.titulo}' creado por el solicitante.",
        )

    @property
    def historial(self) -> list[EventoRequerimiento]:
        """Copia defensiva del historial de auditoría (inmutable desde afuera)."""
        return list(self._historial)

    @property
    @abstractmethod
    def tipo(self) -> TipoRequerimiento:
        """Discriminador polimórfico: `INCIDENTE` o `SOLICITUD`."""

    @classmethod
    def _reconstruir_base(
        cls,
        *,
        id: uuid.UUID,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        estado: EstadoRequerimiento,
        fecha_creacion: datetime,
        tecnico_asignado_id: uuid.UUID | None,
        nota_resolucion: str | None,
        historial: list[EventoRequerimiento],
    ) -> "Requerimiento":
        """Reconstruye los campos comunes de un requerimiento ya existente.

        A diferencia de `__init__` (reservado a requerimientos NUEVOS), no
        registra un evento `CREACION`: restaura el historial real tal como
        vino de persistencia. Uso exclusivo de los repositorios concretos
        (Paso 5) a través de `Incidente.reconstruir`/`Solicitud.reconstruir`
        y `FabricaRequerimientos.reconstruir` — nunca desde servicios.
        """
        instancia = cls.__new__(cls)
        instancia.id = id
        instancia.titulo = titulo
        instancia.descripcion = descripcion
        instancia.solicitante_id = solicitante_id
        instancia.estado = estado
        instancia.fecha_creacion = fecha_creacion
        instancia.tecnico_asignado_id = tecnico_asignado_id
        instancia.nota_resolucion = nota_resolucion
        instancia._historial = list(historial)
        return instancia

    # -- Transiciones de estado ------------------------------------------------

    def iniciar_analisis(self, autor_id: uuid.UUID, rol_actor: RolUsuario) -> EventoRequerimiento:
        """ABIERTO -> EN_ANALISIS. Reservado a Operador/Supervisor."""
        self._exigir_estado(EstadoRequerimiento.ABIERTO)
        self._exigir_rol(rol_actor, _ROLES_ASIGNACION, "iniciar el análisis del requerimiento")
        self.estado = EstadoRequerimiento.EN_ANALISIS
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            autor_id=autor_id,
            detalle="Estado cambiado de ABIERTO a EN_ANALISIS.",
        )

    def asignar_tecnico(
        self, tecnico_id: uuid.UUID, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> EventoRequerimiento:
        """Asigna un técnico responsable. Reservado a Operador/Supervisor."""
        self._exigir_estado(EstadoRequerimiento.EN_ANALISIS)
        self._exigir_rol(rol_actor, _ROLES_ASIGNACION, "asignar un técnico al requerimiento")
        self.tecnico_asignado_id = tecnico_id
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.ASIGNACION,
            autor_id=autor_id,
            detalle=f"Técnico '{tecnico_id}' asignado al requerimiento.",
        )

    def iniciar_progreso(self, autor_id: uuid.UUID, rol_actor: RolUsuario) -> EventoRequerimiento:
        """EN_ANALISIS -> EN_PROGRESO. Exige técnico asignado; solo el técnico
        asignado o un Supervisor pueden ejecutarla."""
        self._exigir_estado(EstadoRequerimiento.EN_ANALISIS)
        if self.tecnico_asignado_id is None:
            raise TecnicoNoAsignadoError("No se puede iniciar el progreso sin un técnico asignado.")
        self._exigir_rol_o_asignado(autor_id, rol_actor, "iniciar el progreso del requerimiento")
        self.estado = EstadoRequerimiento.EN_PROGRESO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            autor_id=autor_id,
            detalle="Estado cambiado de EN_ANALISIS a EN_PROGRESO.",
        )

    def resolver(
        self, nota_resolucion: str, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> EventoRequerimiento:
        """EN_PROGRESO -> RESUELTO. Exige nota descriptiva; solo el técnico
        asignado o un Supervisor pueden ejecutarla."""
        self._exigir_estado(EstadoRequerimiento.EN_PROGRESO)
        self._exigir_rol_o_asignado(autor_id, rol_actor, "resolver el requerimiento")
        nota_normalizada = nota_resolucion.strip() if isinstance(nota_resolucion, str) else ""
        if not nota_normalizada:
            raise NotaResolucionRequeridaError(
                "Marcar como RESUELTO exige una nota de resolución descriptiva."
            )
        self.nota_resolucion = nota_normalizada
        self.estado = EstadoRequerimiento.RESUELTO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.RESOLUCION,
            autor_id=autor_id,
            detalle=f"Requerimiento resuelto: {nota_normalizada}",
        )

    def cerrar(self, autor_id: uuid.UUID, rol_actor: RolUsuario) -> EventoRequerimiento:
        """RESUELTO -> CERRADO. Conformidad final: solicitante propio,
        Operador o Supervisor (nunca Técnico)."""
        self._exigir_estado(EstadoRequerimiento.RESUELTO)
        es_solicitante_propio = (
            rol_actor == RolUsuario.SOLICITANTE and autor_id == self.solicitante_id
        )
        if not (es_solicitante_propio or rol_actor in _ROLES_CIERRE):
            raise PermisoDenegadoError(
                f"El rol '{rol_actor.value}' no puede dar cierre de conformidad."
            )
        self.estado = EstadoRequerimiento.CERRADO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CIERRE,
            autor_id=autor_id,
            detalle="Requerimiento cerrado por conformidad.",
        )

    def cancelar(self, autor_id: uuid.UUID, rol_actor: RolUsuario) -> EventoRequerimiento:
        """ABIERTO/EN_ANALISIS/EN_PROGRESO -> CANCELADO. El solicitante solo
        puede cancelar mientras el ticket está ABIERTO; Operador y Supervisor
        pueden cancelar en cualquiera de los tres estados; Técnico nunca."""
        estados_cancelables = (
            EstadoRequerimiento.ABIERTO,
            EstadoRequerimiento.EN_ANALISIS,
            EstadoRequerimiento.EN_PROGRESO,
        )
        estado_previo = self.estado
        if estado_previo not in estados_cancelables:
            raise TransicionInvalidaError(
                f"No se puede cancelar un requerimiento en estado '{estado_previo.value}'."
            )
        es_solicitante_en_abierto = (
            rol_actor == RolUsuario.SOLICITANTE
            and autor_id == self.solicitante_id
            and estado_previo == EstadoRequerimiento.ABIERTO
        )
        if not (es_solicitante_en_abierto or rol_actor in _ROLES_CANCELACION_AMPLIA):
            raise PermisoDenegadoError(
                f"El rol '{rol_actor.value}' no puede cancelar el requerimiento en este estado."
            )
        self.estado = EstadoRequerimiento.CANCELADO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CANCELACION,
            autor_id=autor_id,
            detalle=f"Requerimiento cancelado desde el estado '{estado_previo.value}'.",
        )

    # -- Helpers privados de validación e invariantes --------------------------

    def _exigir_estado(self, estado_requerido: EstadoRequerimiento) -> None:
        if self.estado != estado_requerido:
            raise TransicionInvalidaError(
                f"La operación requiere estado '{estado_requerido.value}', "
                f"pero el requerimiento está en '{self.estado.value}'."
            )

    @staticmethod
    def _exigir_rol(rol_actor: RolUsuario, roles_permitidos: set[RolUsuario], accion: str) -> None:
        if rol_actor not in roles_permitidos:
            raise PermisoDenegadoError(f"El rol '{rol_actor.value}' no puede {accion}.")

    def _exigir_rol_o_asignado(
        self, autor_id: uuid.UUID, rol_actor: RolUsuario, accion: str
    ) -> None:
        es_tecnico_asignado = (
            rol_actor == RolUsuario.TECNICO and autor_id == self.tecnico_asignado_id
        )
        if not (es_tecnico_asignado or rol_actor == RolUsuario.SUPERVISOR):
            raise PermisoDenegadoError(f"El rol '{rol_actor.value}' no puede {accion}.")

    def _registrar_evento(
        self, tipo_evento: TipoEventoRequerimiento, autor_id: uuid.UUID, detalle: str
    ) -> EventoRequerimiento:
        evento = EventoRequerimiento(
            requerimiento_id=self.id,
            tipo_evento=tipo_evento,
            autor_id=autor_id,
            detalle=detalle,
        )
        self._historial.append(evento)
        return evento

    @staticmethod
    def _validar_titulo(titulo: str) -> str:
        if not isinstance(titulo, str):
            raise TypeError("El título debe ser una cadena de texto.")
        titulo_normalizado = titulo.strip()
        if not titulo_normalizado:
            raise ValueError("El título no puede estar vacío.")
        return titulo_normalizado

    @staticmethod
    def _validar_descripcion(descripcion: str) -> str:
        if not isinstance(descripcion, str):
            raise TypeError("La descripción debe ser una cadena de texto.")
        descripcion_normalizada = descripcion.strip()
        if not descripcion_normalizada:
            raise ValueError("La descripción no puede estar vacía.")
        return descripcion_normalizada
