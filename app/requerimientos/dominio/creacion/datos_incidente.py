"""Value Object `DatosIncidente`: pedido de alta de un `Incidente`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.compartido.validaciones import instancia_de, texto_obligatorio
from app.requerimientos.dominio.creacion.base import DatosRequerimiento
from app.requerimientos.dominio.incidente import CategoriaIncidente, Incidente, UrgenciaIncidente

if TYPE_CHECKING:
    from app.usuarios.dominio import Usuario


@dataclass(frozen=True)
class DatosIncidente(DatosRequerimiento):
    """Datos validados para reportar un corte o degradación de servicio."""

    urgencia: UrgenciaIncidente
    categoria: CategoriaIncidente
    pasos_reproduccion: str

    def __post_init__(self) -> None:
        super().__post_init__()
        instancia_de(self.urgencia, UrgenciaIncidente, "urgencia")
        instancia_de(self.categoria, CategoriaIncidente, "categoría")
        object.__setattr__(
            self,
            "pasos_reproduccion",
            texto_obligatorio(self.pasos_reproduccion, "pasos de reproducción"),
        )

    def construir_para(self, solicitante: Usuario) -> Incidente:
        return Incidente(
            titulo=self.titulo,
            descripcion=self.descripcion,
            solicitante=solicitante,
            urgencia=self.urgencia,
            categoria=self.categoria,
            servicio=self.servicio,
            pasos_reproduccion=self.pasos_reproduccion,
        )
