"""Entidad concreta `Solicitud`: pedido planificado de alta o baja de servicio."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import cast

from app.compartido.dominio import ServicioComunicarlos
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento


class CategoriaSolicitud(StrEnum):
    """Naturaleza administrativa de la solicitud sobre un servicio."""

    ALTA_SERVICIO = "ALTA_SERVICIO"
    BAJA_SERVICIO = "BAJA_SERVICIO"


class Solicitud(Requerimiento):
    """Pedido planificado de alta o baja de un servicio de la cooperativa."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        categoria: CategoriaSolicitud,
        servicio: ServicioComunicarlos,
        id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(titulo, descripcion, solicitante_id, id)
        self.categoria = self._validar_categoria(categoria)
        self.servicio = self._validar_servicio(servicio)

    @property
    def tipo(self) -> TipoRequerimiento:
        return TipoRequerimiento.SOLICITUD

    @classmethod
    def reconstruir(
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
        categoria: CategoriaSolicitud,
        servicio: ServicioComunicarlos,
        comentarios: list[Comentario] | None = None,
    ) -> "Solicitud":
        """Reconstruye una `Solicitud` ya persistida (uso exclusivo de repositorios)."""
        instancia = cast(
            "Solicitud",
            cls._reconstruir_base(
                id=id,
                titulo=titulo,
                descripcion=descripcion,
                solicitante_id=solicitante_id,
                estado=estado,
                fecha_creacion=fecha_creacion,
                tecnico_asignado_id=tecnico_asignado_id,
                nota_resolucion=nota_resolucion,
                historial=historial,
                comentarios=comentarios,
            ),
        )
        instancia.categoria = categoria
        instancia.servicio = servicio
        return instancia

    @staticmethod
    def _validar_categoria(categoria: CategoriaSolicitud) -> CategoriaSolicitud:
        if not isinstance(categoria, CategoriaSolicitud):
            raise TypeError("La categoría debe ser una instancia de CategoriaSolicitud.")
        return categoria

    @staticmethod
    def _validar_servicio(servicio: ServicioComunicarlos) -> ServicioComunicarlos:
        if not isinstance(servicio, ServicioComunicarlos):
            raise TypeError("El servicio debe ser una instancia de ServicioComunicarlos.")
        return servicio
