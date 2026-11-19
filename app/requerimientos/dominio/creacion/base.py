"""Clase abstracta `DatosRequerimiento`: pedido tipado de alta de un ticket.

Reemplaza al `ServicioRequerimientos.crear(tipo, **atributos)`, donde el
router inyectaba `solicitante_id=usuario.id` dentro de un `**kwargs` opaco.
Cada tipo de requerimiento tiene su propio Value Object de creación, que se
autovalida al construirse y sabe construir la entidad concreta para el
`Usuario` que la pide (`construir_para(solicitante)`): ni el router ni el
servicio eligen la clase con `if` / `isinstance`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.compartido.dominio import ServicioComunicarlos
from app.compartido.validaciones import instancia_de, texto_obligatorio

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.usuarios.dominio import Usuario


@dataclass(frozen=True)
class DatosRequerimiento(ABC):
    """Datos comunes a todo requerimiento nuevo, ya validados."""

    titulo: str
    descripcion: str
    servicio: ServicioComunicarlos

    def __post_init__(self) -> None:
        object.__setattr__(self, "titulo", texto_obligatorio(self.titulo, "título"))
        object.__setattr__(self, "descripcion", texto_obligatorio(self.descripcion, "descripción"))
        instancia_de(self.servicio, ServicioComunicarlos, "servicio")

    @abstractmethod
    def construir_para(self, solicitante: Usuario) -> Requerimiento:
        """Construye el requerimiento concreto abierto por `solicitante`."""
