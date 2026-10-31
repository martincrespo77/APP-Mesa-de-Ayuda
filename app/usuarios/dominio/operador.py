"""Entidad concreta `Operador`: mesa de entrada que hace el triage de tickets.

Analiza, asigna técnicos, comenta, da cierre de conformidad y cancela
cualquier ticket. Nunca trabaja técnicamente un ticket (no inicia
progreso ni resuelve). Sus acciones son auditables por un Supervisor.
"""

from typing import TYPE_CHECKING

from app.compartido.dominio import RolUsuario
from app.usuarios.dominio.empleado import Empleado

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento


class Operador(Empleado):
    """Empleado de mesa de ayuda: triage, asignación y seguimiento."""

    @property
    def rol(self) -> RolUsuario:
        return RolUsuario.OPERADOR

    def puede_iniciar_analisis(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_asignar_tecnico(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_cerrar(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_cancelar(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_comentar(self, requerimiento: "Requerimiento") -> bool:
        return True

    def reabre_al_comentar(self) -> bool:
        return True

    def es_supervisable(self) -> bool:
        return True
