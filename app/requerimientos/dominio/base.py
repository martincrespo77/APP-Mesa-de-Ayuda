"""Entidad abstracta `Requerimiento`.

Clase base de la jerarquía polimórfica `Incidente` / `Solicitud`. Concentra
los atributos comunes y la máquina de estados (Information Expert: la
propia entidad decide si una transición es válida desde su estado actual).

Los permisos se resuelven por double dispatch: cada transición recibe al
`Usuario` actor y le PREGUNTA si puede ejecutarla
(`actor.puede_cerrar(self)`); cada subclase de `Usuario` contesta según su
rol, consultando a su vez al ticket lo que necesite saber
(`requerimiento.pertenece_a(self)`, `esta_asignado_a(self)`). Ninguna de
las dos clases lee el rol ni compara ids de la otra.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.compartido.validaciones import texto_obligatorio
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    TecnicoInvalidoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)

if TYPE_CHECKING:
    from app.usuarios.dominio import Usuario

_ESTADOS_CANCELABLES = {
    EstadoRequerimiento.ABIERTO,
    EstadoRequerimiento.EN_ANALISIS,
    EstadoRequerimiento.EN_PROGRESO,
}
_ESTADOS_SIN_COMENTARIOS = {EstadoRequerimiento.CERRADO, EstadoRequerimiento.CANCELADO}
_ESTADOS_DERIVABLES = {EstadoRequerimiento.EN_ANALISIS, EstadoRequerimiento.EN_PROGRESO}


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
        self.titulo = texto_obligatorio(titulo, "título")
        self.descripcion = texto_obligatorio(descripcion, "descripción")
        self.solicitante_id = solicitante_id
        self.estado = EstadoRequerimiento.ABIERTO
        self.fecha_creacion = datetime.now(UTC)
        self.tecnico_asignado_id: uuid.UUID | None = None
        self.nota_resolucion: str | None = None
        self._historial: list[EventoRequerimiento] = []
        self._comentarios: list[Comentario] = []
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
    def comentarios(self) -> list[Comentario]:
        """Copia defensiva de los comentarios de seguimiento (inmutable desde afuera)."""
        return list(self._comentarios)

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
        comentarios: list[Comentario] | None = None,
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
        instancia._comentarios = list(comentarios or [])
        return instancia

    # -- Preguntas que le hacen los actores al ticket --------------------------

    def pertenece_a(self, usuario: "Usuario") -> bool:
        """¿`usuario` es quien abrió este requerimiento?"""
        return self.solicitante_id == usuario.id

    def esta_asignado_a(self, usuario: "Usuario") -> bool:
        """¿`usuario` es el técnico actualmente responsable de este requerimiento?"""
        return self.tecnico_asignado_id == usuario.id

    def esta_abierto(self) -> bool:
        """¿Todavía nadie lo tomó (sigue en ABIERTO)?"""
        return self.estado == EstadoRequerimiento.ABIERTO

    def exigir_visible_para(self, actor: "Usuario") -> None:
        """Lanza `PermisoDenegadoError` si `actor` no puede consultar este ticket
        (ej. un Solicitante sobre un requerimiento ajeno)."""
        self._exigir_permiso(actor.puede_ver(self), actor, "consultar este requerimiento")

    # -- Transiciones de estado ------------------------------------------------

    def iniciar_analisis(self, actor: "Usuario") -> EventoRequerimiento:
        """ABIERTO -> EN_ANALISIS."""
        self._exigir_estado(EstadoRequerimiento.ABIERTO)
        self._exigir_permiso(
            actor.puede_iniciar_analisis(self), actor, "iniciar el análisis del requerimiento"
        )
        self.estado = EstadoRequerimiento.EN_ANALISIS
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            autor_id=actor.id,
            detalle="Estado cambiado de ABIERTO a EN_ANALISIS.",
        )

    def asignar_tecnico(self, tecnico: "Usuario", actor: "Usuario") -> EventoRequerimiento:
        """Asigna `tecnico` como responsable, si `actor` puede asignar y
        `tecnico` puede recibir requerimientos."""
        self._exigir_estado(EstadoRequerimiento.EN_ANALISIS)
        self._exigir_permiso(
            actor.puede_asignar_tecnico(self), actor, "asignar un técnico al requerimiento"
        )
        self._exigir_que_pueda_recibirlo(tecnico)
        self.tecnico_asignado_id = tecnico.id
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.ASIGNACION,
            autor_id=actor.id,
            detalle=f"Técnico '{tecnico.id}' asignado al requerimiento.",
        )

    def iniciar_progreso(self, actor: "Usuario") -> EventoRequerimiento:
        """EN_ANALISIS -> EN_PROGRESO. Exige un técnico asignado."""
        self._exigir_estado(EstadoRequerimiento.EN_ANALISIS)
        if self.tecnico_asignado_id is None:
            raise TecnicoNoAsignadoError("No se puede iniciar el progreso sin un técnico asignado.")
        self._exigir_permiso(
            actor.puede_iniciar_progreso(self), actor, "iniciar el progreso del requerimiento"
        )
        self.estado = EstadoRequerimiento.EN_PROGRESO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
            autor_id=actor.id,
            detalle="Estado cambiado de EN_ANALISIS a EN_PROGRESO.",
        )

    def resolver(self, nota_resolucion: str, actor: "Usuario") -> EventoRequerimiento:
        """EN_PROGRESO -> RESUELTO. Exige una nota de resolución descriptiva."""
        self._exigir_estado(EstadoRequerimiento.EN_PROGRESO)
        self._exigir_permiso(actor.puede_resolver(self), actor, "resolver el requerimiento")
        nota_normalizada = nota_resolucion.strip() if isinstance(nota_resolucion, str) else ""
        if not nota_normalizada:
            raise NotaResolucionRequeridaError(
                "Marcar como RESUELTO exige una nota de resolución descriptiva."
            )
        self.nota_resolucion = nota_normalizada
        self.estado = EstadoRequerimiento.RESUELTO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.RESOLUCION,
            autor_id=actor.id,
            detalle=f"Requerimiento resuelto: {nota_normalizada}",
        )

    def cerrar(self, actor: "Usuario") -> EventoRequerimiento:
        """RESUELTO -> CERRADO (cierre de conformidad)."""
        self._exigir_estado(EstadoRequerimiento.RESUELTO)
        self._exigir_permiso(actor.puede_cerrar(self), actor, "dar cierre de conformidad")
        self.estado = EstadoRequerimiento.CERRADO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CIERRE,
            autor_id=actor.id,
            detalle="Requerimiento cerrado por conformidad.",
        )

    def cancelar(self, actor: "Usuario") -> EventoRequerimiento:
        """ABIERTO/EN_ANALISIS/EN_PROGRESO -> CANCELADO."""
        estado_previo = self.estado
        if estado_previo not in _ESTADOS_CANCELABLES:
            raise TransicionInvalidaError(
                f"No se puede cancelar un requerimiento en estado '{estado_previo.value}'."
            )
        self._exigir_permiso(
            actor.puede_cancelar(self), actor, "cancelar el requerimiento en este estado"
        )
        self.estado = EstadoRequerimiento.CANCELADO
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.CANCELACION,
            autor_id=actor.id,
            detalle=f"Requerimiento cancelado desde el estado '{estado_previo.value}'.",
        )

    def agregar_comentario(self, texto: str, actor: "Usuario") -> Comentario:
        """Agrega un comentario de seguimiento al ticket.

        No se puede comentar un ticket CERRADO/CANCELADO. Si `actor` es de
        los que reabren al comentar (`actor.reabre_al_comentar()`), un
        comentario sobre un RESUELTO lo devuelve a EN_PROGRESO (no hay un
        estado "REABIERTO": la reapertura queda auditada como evento).
        """
        if self.estado in _ESTADOS_SIN_COMENTARIOS:
            raise TransicionInvalidaError(
                f"No se pueden agregar comentarios a un requerimiento en estado "
                f"'{self.estado.value}'."
            )
        self._exigir_permiso(actor.puede_comentar(self), actor, "comentar este requerimiento")
        texto_normalizado = texto_obligatorio(texto, "texto del comentario")
        comentario = Comentario(
            requerimiento_id=self.id, autor_id=actor.id, texto=texto_normalizado
        )
        self._comentarios.append(comentario)
        self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.COMENTARIO,
            autor_id=actor.id,
            detalle=f"Comentario agregado: {texto_normalizado}",
        )
        if self.estado == EstadoRequerimiento.RESUELTO and actor.reabre_al_comentar():
            self.estado = EstadoRequerimiento.EN_PROGRESO
            self._registrar_evento(
                tipo_evento=TipoEventoRequerimiento.REAPERTURA,
                autor_id=actor.id,
                detalle="Requerimiento reabierto a EN_PROGRESO por un nuevo comentario.",
            )
        return comentario

    def derivar_interconsulta(
        self, tecnico_destino: "Usuario", actor: "Usuario"
    ) -> EventoRequerimiento:
        """Deriva el ticket a otro técnico (interconsulta/colaboración).

        Solo mientras el ticket está EN_ANALISIS o EN_PROGRESO. Reasigna
        `tecnico_asignado_id` (mantiene el invariante de un único técnico
        asignado a la vez) y registra el técnico origen/destino en el evento.
        """
        if self.estado not in _ESTADOS_DERIVABLES:
            raise TransicionInvalidaError(
                f"No se puede derivar un requerimiento en estado '{self.estado.value}'."
            )
        self._exigir_permiso(actor.puede_derivar(self), actor, "derivar este requerimiento")
        if self.esta_asignado_a(tecnico_destino):
            raise TransicionInvalidaError(
                "No se puede derivar el requerimiento al mismo técnico asignado."
            )
        self._exigir_que_pueda_recibirlo(tecnico_destino)
        tecnico_origen_id = self.tecnico_asignado_id
        self.tecnico_asignado_id = tecnico_destino.id
        return self._registrar_evento(
            tipo_evento=TipoEventoRequerimiento.DERIVACION,
            autor_id=actor.id,
            detalle=(
                f"Derivado del técnico '{tecnico_origen_id}' al técnico '{tecnico_destino.id}'."
            ),
        )

    # -- Helpers privados de invariantes ---------------------------------------

    def _exigir_estado(self, estado_requerido: EstadoRequerimiento) -> None:
        if self.estado != estado_requerido:
            raise TransicionInvalidaError(
                f"La operación requiere estado '{estado_requerido.value}', "
                f"pero el requerimiento está en '{self.estado.value}'."
            )

    def _exigir_permiso(self, tiene_permiso: bool, actor: "Usuario", accion: str) -> None:
        """Traduce la respuesta del actor ("¿podés?") en la excepción de dominio."""
        if not tiene_permiso:
            raise PermisoDenegadoError(f"El rol '{actor.rol.value}' no puede {accion}.")

    def _exigir_que_pueda_recibirlo(self, tecnico: "Usuario") -> None:
        if not tecnico.puede_recibir_requerimientos():
            raise TecnicoInvalidoError(
                f"El usuario '{tecnico.id}' no es un Técnico activo: solo se puede asignar "
                "o derivar un requerimiento a un Técnico activo."
            )

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
