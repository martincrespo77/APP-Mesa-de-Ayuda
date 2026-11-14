"""Clase abstracta `EstadoTicket`: raíz del Patrón State de `Requerimiento`.

Cada estado del ciclo de vida es una subclase que implementa SOLO las
transiciones válidas desde sí misma; todas las demás heredan el rechazo por
defecto de esta base (`TransicionInvalidaError`). Así `Requerimiento` no
necesita conjuntos de estados válidos ni `if self.estado == ...`: le delega
la pregunta a su estado actual (`self._estado.cerrar()`), que contesta con
el estado siguiente o rechaza la transición.

Los estados son objetos sin datos propios: deciden la TRANSICIÓN, mientras
que el `Requerimiento` sigue siendo el dueño de sus datos (técnico asignado,
nota de resolución, historial) y de los permisos del actor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.excepciones import TransicionInvalidaError

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.usuarios.dominio import Usuario


class EstadoTicket(ABC):
    """Estado del ciclo de vida de un `Requerimiento`.

    Por defecto rechaza toda transición; la única excepción deliberada son los
    comentarios, admitidos salvo en los estados terminales (`EstadoTerminal`).
    """

    @property
    @abstractmethod
    def codigo(self) -> EstadoRequerimiento:
        """Identificador estable del estado (persistencia y DTOs, nunca para decidir)."""

    # -- Transiciones (devuelven el estado siguiente) --------------------------

    def iniciar_analisis(self) -> EstadoTicket:
        raise self._transicion_invalida("iniciar el análisis de")

    def iniciar_progreso(self) -> EstadoTicket:
        raise self._transicion_invalida("iniciar el progreso de")

    def resolver(self) -> EstadoTicket:
        raise self._transicion_invalida("resolver")

    def cerrar(self) -> EstadoTicket:
        raise self._transicion_invalida("cerrar")

    def cancelar(self) -> EstadoTicket:
        raise self._transicion_invalida("cancelar")

    def reabrir(self) -> EstadoTicket:
        raise self._transicion_invalida("reabrir")

    # -- Operaciones que no cambian de estado pero dependen de él -------------

    def exigir_admite_asignacion(self) -> None:
        raise self._transicion_invalida("asignar un técnico a")

    def exigir_admite_derivacion(self) -> None:
        raise self._transicion_invalida("derivar")

    def exigir_admite_comentarios(self) -> None:
        """Por defecto un ticket admite comentarios (los estados terminales no)."""
        return None

    def al_recibir_comentario(self, requerimiento: Requerimiento, actor: Usuario) -> None:
        """Reacción del estado a un comentario ya registrado (por defecto, ninguna)."""
        return None

    def esta_abierto(self) -> bool:
        """¿Todavía nadie tomó el ticket?"""
        return False

    def _transicion_invalida(self, operacion: str) -> TransicionInvalidaError:
        return TransicionInvalidaError(
            f"No se puede {operacion} un requerimiento en estado '{self.codigo.value}'."
        )
