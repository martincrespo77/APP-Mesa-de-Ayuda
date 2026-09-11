"""Entidad concreta `Solicitud`: pedido planificado de servicio o consulta."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento


class CategoriaSolicitud(StrEnum):
    """Naturaleza administrativa de la solicitud."""

    NUEVO_SERVICIO = "NUEVO_SERVICIO"
    CAMBIO_ABONO = "CAMBIO_ABONO"
    CONSULTA_ADMINISTRATIVA = "CONSULTA_ADMINISTRATIVA"
    FACTURACION = "FACTURACION"


class Solicitud(Requerimiento):
    """Pedido planificado de nuevo servicio, cambio de abono o consulta administrativa."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        categoria: CategoriaSolicitud,
        fecha_limite: datetime,
        impacto_estimado: str,
        id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(titulo, descripcion, solicitante_id, id)
        self.categoria = self._validar_categoria(categoria)
        self.fecha_limite = self._validar_fecha_limite(fecha_limite)
        self.impacto_estimado = self._validar_impacto_estimado(impacto_estimado)

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
        fecha_limite: datetime,
        impacto_estimado: str,
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
            ),
        )
        instancia.categoria = categoria
        instancia.fecha_limite = fecha_limite
        instancia.impacto_estimado = impacto_estimado
        return instancia

    @staticmethod
    def _validar_categoria(categoria: CategoriaSolicitud) -> CategoriaSolicitud:
        if not isinstance(categoria, CategoriaSolicitud):
            raise TypeError("La categoría debe ser una instancia de CategoriaSolicitud.")
        return categoria

    @staticmethod
    def _validar_fecha_limite(fecha_limite: datetime) -> datetime:
        if not isinstance(fecha_limite, datetime):
            raise TypeError("La fecha límite debe ser una instancia de datetime.")
        fecha_normalizada = (
            fecha_limite if fecha_limite.tzinfo else fecha_limite.replace(tzinfo=UTC)
        )
        if fecha_normalizada <= datetime.now(UTC):
            raise ValueError("La fecha límite debe ser posterior al momento actual.")
        return fecha_normalizada

    @staticmethod
    def _validar_impacto_estimado(impacto_estimado: str) -> str:
        if not isinstance(impacto_estimado, str):
            raise TypeError("El impacto estimado debe ser una cadena de texto.")
        impacto_normalizado = impacto_estimado.strip()
        if not impacto_normalizado:
            raise ValueError("El impacto estimado no puede estar vacío.")
        return impacto_normalizado
