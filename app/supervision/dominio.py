"""Entidad de dominio `RelacionSupervision`: quién audita a quién.

Relación N:M entre un Supervisor y los Operadores/Técnicos cuyos eventos
audita. La crea `Supervisor.supervisar(empleado)` (que le pregunta al
empleado si es supervisable) y la propia relación sabe convertir un evento
de su supervisado en la `Notificacion` para su supervisor. Una vez creada,
la única otra operación posible es eliminarla (gestionado por el repositorio).
"""

import uuid
from datetime import UTC, datetime

from app.notificaciones.dominio import Notificacion
from app.requerimientos.eventos import EventoRequerimiento
from app.supervision.excepciones import RelacionInvalidaError


class RelacionSupervision:
    """Vínculo de supervisión entre un `supervisor_id` y un `supervisado_id`."""

    def __init__(
        self,
        supervisor_id: uuid.UUID,
        supervisado_id: uuid.UUID,
        id: uuid.UUID | None = None,
        fecha_asignacion: datetime | None = None,
    ) -> None:
        if supervisor_id == supervisado_id:
            raise RelacionInvalidaError("Un usuario no puede supervisarse a sí mismo.")
        self.id = id or uuid.uuid4()
        self.supervisor_id = supervisor_id
        self.supervisado_id = supervisado_id
        self.fecha_asignacion = fecha_asignacion or datetime.now(UTC)

    def audita_a(self, usuario_id: uuid.UUID) -> bool:
        """¿Esta relación supervisa las acciones de `usuario_id`?"""
        return self.supervisado_id == usuario_id

    def notificar(self, evento: EventoRequerimiento) -> Notificacion:
        """Genera el aviso al supervisor sobre un evento de su supervisado.

        Exige que el evento sea efectivamente de alguien que esta relación
        audita: notificar a un supervisor por acciones de un empleado ajeno
        sería una fuga de información.
        """
        if not self.audita_a(evento.autor_id):
            raise RelacionInvalidaError(
                "El evento no fue generado por el empleado que audita esta relación."
            )
        return Notificacion(
            supervisor_id=self.supervisor_id,
            empleado_supervisado_id=self.supervisado_id,
            requerimiento_id=evento.requerimiento_id,
            tipo_evento=evento.tipo_evento,
            detalle=evento.detalle,
        )
