"""Entidad de dominio `RelacionSupervision`: quién audita a quién.

Relación N:M entre un Supervisor y los Operadores/Técnicos cuyos eventos
audita (dispara una `Notificacion` por cada acción del supervisado, ver
`app/notificaciones/`). No tiene métodos de transición: una vez creada, la
única operación posible es eliminarla (gestionado por el repositorio).
"""

import uuid
from datetime import UTC, datetime

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
