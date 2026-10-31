"""Entidad de dominio `Notificacion`: aviso a un Supervisor sobre un evento
de un empleado (Operador/Técnico) que supervisa.

La genera `ObservadorNotificacionesMongo` (infraestructura) por cada
`EventoRequerimiento` cuyo autor es un supervisado, una por cada supervisor
suyo (relación N:M de `app/supervision/`). Se puede marcar leída, pero
queda como registro permanente: no se borra.
"""

import uuid
from datetime import UTC, datetime

from app.notificaciones.excepciones import NotificacionNoEncontradaError
from app.requerimientos.eventos import TipoEventoRequerimiento


class Notificacion:
    """Aviso persistente de que un supervisado generó un evento sobre un ticket."""

    def __init__(
        self,
        supervisor_id: uuid.UUID,
        empleado_supervisado_id: uuid.UUID,
        requerimiento_id: uuid.UUID,
        tipo_evento: TipoEventoRequerimiento,
        detalle: str,
        id: uuid.UUID | None = None,
        timestamp: datetime | None = None,
        leida: bool = False,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.supervisor_id = supervisor_id
        self.empleado_supervisado_id = empleado_supervisado_id
        self.requerimiento_id = requerimiento_id
        self.tipo_evento = tipo_evento
        self.detalle = detalle
        self.timestamp = timestamp or datetime.now(UTC)
        self._leida = leida

    @property
    def leida(self) -> bool:
        return self._leida

    def es_para(self, supervisor_id: uuid.UUID) -> bool:
        """¿Esta notificación está dirigida a `supervisor_id`?"""
        return self.supervisor_id == supervisor_id

    def marcar_leida(self) -> None:
        """Idempotente: marcar una notificación ya leída no falla ni cambia nada."""
        self._leida = True

    def marcar_leida_por(self, supervisor_id: uuid.UUID) -> None:
        """Marca leída la notificación, si es de `supervisor_id`.

        Una notificación ajena se reporta como inexistente (no como
        "prohibida"): un supervisor no debe poder enterarse de que existe
        un aviso dirigido a otro.
        """
        if not self.es_para(supervisor_id):
            raise NotificacionNoEncontradaError(
                f"No existe una notificación con id '{self.id}' para este supervisor."
            )
        self.marcar_leida()
