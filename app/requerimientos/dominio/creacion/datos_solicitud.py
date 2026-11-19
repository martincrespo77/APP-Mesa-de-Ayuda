"""Value Object `DatosSolicitud`: pedido de alta de una `Solicitud`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.compartido.validaciones import instancia_de
from app.requerimientos.dominio.creacion.base import DatosRequerimiento
from app.requerimientos.dominio.solicitud import CategoriaSolicitud, Solicitud

if TYPE_CHECKING:
    from app.usuarios.dominio import Usuario


@dataclass(frozen=True)
class DatosSolicitud(DatosRequerimiento):
    """Datos validados para pedir el alta o la baja de un servicio."""

    categoria: CategoriaSolicitud

    def __post_init__(self) -> None:
        super().__post_init__()
        instancia_de(self.categoria, CategoriaSolicitud, "categoría")

    def construir_para(self, solicitante: Usuario) -> Solicitud:
        return Solicitud(
            titulo=self.titulo,
            descripcion=self.descripcion,
            solicitante=solicitante,
            categoria=self.categoria,
            servicio=self.servicio,
        )
