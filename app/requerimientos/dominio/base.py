"""Entidad abstracta `Requerimiento`.

Clase base de la jerarquía polimórfica `Incidente` / `Solicitud`. Concentra
los atributos comunes y delega el ciclo de vida en su estado actual
(Patrón State, paquete `estados/`): cada transición le pregunta a
`self._estado` cuál es el estado siguiente, y el estado rechaza
(`TransicionInvalidaError`) lo que no es válido desde sí mismo. La entidad
no contiene conjuntos de estados válidos ni `if self.estado == ...`.

Los permisos se resuelven por double dispatch (Tell, Don't Ask): cada
transición recibe al `Usuario` actor y le pide que exija su propia
autorización (`actor.exigir_autorizacion(actor.puede_cerrar(self), ...)`);
cada subclase de `Usuario` contesta según su rol, consultando a su vez al
ticket lo que necesite saber (`requerimiento.pertenece_a(self)`,
`esta_asignado_a(self)`). Ninguna de las dos clases lee el rol de la otra.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.compartido.excepciones import DatoInvalidoError
from app.compartido.validaciones import texto_obligatorio
from app.requerimientos.dominio.codigos import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.fabrica import FabricaEstados
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)

if TYPE_CHECKING:
    from app.usuarios.dominio import Usuario


class Requerimiento(ABC):
    """Ticket de la Mesa de Ayuda, en su forma de `Incidente` o `Solicitud`."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante: "Usuario",
        id: uuid.UUID | None = None,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.titulo = texto_obligatorio(titulo, "título")
        self.descripcion = texto_obligatorio(descripcion, "descripción")
        self.solicitante_id = solicitante.id
        self._estado: EstadoTicket = FabricaEstados.inicial()
        self.fecha_creacion = datetime.now(UTC)
        self.tecnico_asignado_id: uuid.UUID | None = None
        self.nota_resolucion: str | None = None
        self._historial: list[EventoRequerimiento] = []
        self._comentarios: list[Comentario] = []
        self._registrar_evento(
            TipoEventoRequerimiento.CREACION,
            solicitante,
            f"Requerimiento '{self.titulo}' creado por el solicitante.",
        )

    @property
    def estado(self) -> EstadoRequerimiento:
        """Código del estado actual (persistencia y DTOs; el comportamiento está en `_estado`)."""
        return self._estado.codigo

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
        vino de persistencia, e hidrata el objeto estado desde su código vía
        `FabricaEstados`. Uso exclusivo de los repositorios concretos a
        través de `Incidente.reconstruir`/`Solicitud.reconstruir` y
        `FabricaRequerimientos.reconstruir` — nunca desde servicios.
        """
        instancia = cls.__new__(cls)
        instancia.id = id
        instancia.titulo = titulo
        instancia.descripcion = descripcion
        instancia.solicitante_id = solicitante_id
        instancia._estado = FabricaEstados.desde_codigo(estado)
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
        return self._estado.esta_abierto()

    def exigir_visible_para(self, actor: "Usuario") -> None:
        """Lanza `PermisoDenegadoError` si `actor` no puede consultar este ticket
        (ej. un Solicitante sobre un requerimiento ajeno)."""
        actor.exigir_autorizacion(actor.puede_ver(self), "consultar este requerimiento")

    # -- Transiciones de estado ------------------------------------------------

    def iniciar_analisis(self, actor: "Usuario") -> EventoRequerimiento:
        """ABIERTO -> EN_ANALISIS."""
        siguiente = self._estado.iniciar_analisis()
        actor.exigir_autorizacion(
            actor.puede_iniciar_analisis(self), "iniciar el análisis del requerimiento"
        )
        return self._cambiar_estado(siguiente, TipoEventoRequerimiento.CAMBIO_ESTADO, actor)

    def asignar_tecnico(self, tecnico: "Usuario", actor: "Usuario") -> EventoRequerimiento:
        """Asigna `tecnico` como responsable, si `actor` puede asignar y
        `tecnico` puede recibir requerimientos."""
        self._estado.exigir_admite_asignacion()
        actor.exigir_autorizacion(
            actor.puede_asignar_tecnico(self), "asignar un técnico al requerimiento"
        )
        tecnico.exigir_que_pueda_recibir_requerimientos()
        self.tecnico_asignado_id = tecnico.id
        return self._registrar_evento(
            TipoEventoRequerimiento.ASIGNACION,
            actor,
            f"Técnico '{tecnico.id}' asignado al requerimiento.",
        )

    def iniciar_progreso(self, actor: "Usuario") -> EventoRequerimiento:
        """EN_ANALISIS -> EN_PROGRESO. Exige un técnico asignado."""
        siguiente = self._estado.iniciar_progreso()
        if self.tecnico_asignado_id is None:
            raise TecnicoNoAsignadoError("No se puede iniciar el progreso sin un técnico asignado.")
        actor.exigir_autorizacion(
            actor.puede_iniciar_progreso(self), "iniciar el progreso del requerimiento"
        )
        return self._cambiar_estado(siguiente, TipoEventoRequerimiento.CAMBIO_ESTADO, actor)

    def resolver(self, nota_resolucion: str, actor: "Usuario") -> EventoRequerimiento:
        """EN_PROGRESO -> RESUELTO. Exige una nota de resolución descriptiva."""
        siguiente = self._estado.resolver()
        actor.exigir_autorizacion(actor.puede_resolver(self), "resolver el requerimiento")
        try:
            nota = texto_obligatorio(nota_resolucion, "nota de resolución")
        except (TypeError, DatoInvalidoError):
            raise NotaResolucionRequeridaError(
                "Marcar como RESUELTO exige una nota de resolución descriptiva."
            ) from None
        self.nota_resolucion = nota
        return self._cambiar_estado(
            siguiente,
            TipoEventoRequerimiento.RESOLUCION,
            actor,
            f"Requerimiento resuelto: {nota}",
        )

    def cerrar(self, actor: "Usuario") -> EventoRequerimiento:
        """RESUELTO -> CERRADO (cierre de conformidad)."""
        siguiente = self._estado.cerrar()
        actor.exigir_autorizacion(actor.puede_cerrar(self), "dar cierre de conformidad")
        return self._cambiar_estado(
            siguiente,
            TipoEventoRequerimiento.CIERRE,
            actor,
            "Requerimiento cerrado por conformidad.",
        )

    def cancelar(self, actor: "Usuario") -> EventoRequerimiento:
        """ABIERTO/EN_ANALISIS/EN_PROGRESO -> CANCELADO."""
        siguiente = self._estado.cancelar()
        actor.exigir_autorizacion(
            actor.puede_cancelar(self), "cancelar el requerimiento en este estado"
        )
        return self._cambiar_estado(
            siguiente,
            TipoEventoRequerimiento.CANCELACION,
            actor,
            f"Requerimiento cancelado desde el estado '{self.estado.value}'.",
        )

    def reabrir(self, actor: "Usuario") -> EventoRequerimiento:
        """RESUELTO -> EN_PROGRESO, cuando `actor` puede reabrir este ticket.

        No existe un estado "REABIERTO": la reapertura queda auditada como
        evento. La dispara `EstadoResuelto` al recibir un comentario; la
        exigencia es la misma capacidad atada al ticket (`puede_reabrir`), de
        modo que llamarla directamente no saltea la regla de quién reabre.
        """
        siguiente = self._estado.reabrir()
        actor.exigir_autorizacion(actor.puede_reabrir(self), "reabrir el requerimiento")
        # Vuelve a trabajarse: la nota anterior ya no describe una solución vigente.
        self.nota_resolucion = None
        return self._cambiar_estado(
            siguiente,
            TipoEventoRequerimiento.REAPERTURA,
            actor,
            "Requerimiento reabierto a EN_PROGRESO por un nuevo comentario.",
        )

    def agregar_comentario(self, texto: str, actor: "Usuario") -> Comentario:
        """Agrega un comentario de seguimiento al ticket.

        Los estados terminales (CERRADO/CANCELADO) no admiten comentarios. El
        estado actual reacciona al comentario ya registrado: un RESUELTO
        vuelve a EN_PROGRESO si `actor` es de los que reabren al comentar.
        """
        self._estado.exigir_admite_comentarios()
        actor.exigir_autorizacion(actor.puede_comentar(self), "comentar este requerimiento")
        comentario = Comentario(requerimiento_id=self.id, autor_id=actor.id, texto=texto)
        self._comentarios.append(comentario)
        self._registrar_evento(
            TipoEventoRequerimiento.COMENTARIO,
            actor,
            f"Comentario agregado: {comentario.texto}",
        )
        self._estado.al_recibir_comentario(self, actor)
        return comentario

    def derivar_interconsulta(
        self, tecnico_destino: "Usuario", actor: "Usuario"
    ) -> EventoRequerimiento:
        """Deriva el ticket a otro técnico (interconsulta/colaboración).

        Solo mientras el ticket está EN_ANALISIS o EN_PROGRESO. Reasigna
        `tecnico_asignado_id` (mantiene el invariante de un único técnico
        asignado a la vez) y registra el técnico origen/destino en el evento.
        """
        self._estado.exigir_admite_derivacion()
        actor.exigir_autorizacion(actor.puede_derivar(self), "derivar este requerimiento")
        if self.esta_asignado_a(tecnico_destino):
            raise TransicionInvalidaError(
                "No se puede derivar el requerimiento al mismo técnico asignado."
            )
        tecnico_destino.exigir_que_pueda_recibir_requerimientos()
        tecnico_origen_id = self.tecnico_asignado_id
        self.tecnico_asignado_id = tecnico_destino.id
        return self._registrar_evento(
            TipoEventoRequerimiento.DERIVACION,
            actor,
            f"Derivado del técnico '{tecnico_origen_id}' al técnico '{tecnico_destino.id}'.",
        )

    # -- Helpers privados de invariantes ---------------------------------------

    def _cambiar_estado(
        self,
        siguiente: EstadoTicket,
        tipo_evento: TipoEventoRequerimiento,
        actor: "Usuario",
        detalle: str | None = None,
    ) -> EventoRequerimiento:
        """Aplica el estado que devolvió la transición y audita el cambio."""
        previo = self._estado.codigo
        self._estado = siguiente
        return self._registrar_evento(
            tipo_evento,
            actor,
            detalle or f"Estado cambiado de {previo.value} a {siguiente.codigo.value}.",
        )

    def _registrar_evento(
        self, tipo_evento: TipoEventoRequerimiento, autor: "Usuario", detalle: str
    ) -> EventoRequerimiento:
        evento = EventoRequerimiento(
            requerimiento_id=self.id,
            tipo_evento=tipo_evento,
            autor_id=autor.id,
            detalle=detalle,
        )
        self._historial.append(evento)
        return evento
