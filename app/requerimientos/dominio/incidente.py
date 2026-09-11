"""Entidad concreta `Incidente`: interrupción o degradación de un servicio."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import cast

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento


class Severidad(StrEnum):
    """Nivel de impacto técnico del incidente."""

    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class Incidente(Requerimiento):
    """Corte o degradación anormal de un servicio existente (fibra, IP, TV)."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        severidad: Severidad,
        pasos_reproduccion: str,
        servicio_afectado: str,
        id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(titulo, descripcion, solicitante_id, id)
        self.severidad = self._validar_severidad(severidad)
        self.pasos_reproduccion = self._validar_pasos_reproduccion(pasos_reproduccion)
        self.servicio_afectado = self._validar_servicio_afectado(servicio_afectado)

    @property
    def tipo(self) -> TipoRequerimiento:
        return TipoRequerimiento.INCIDENTE

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
        severidad: Severidad,
        pasos_reproduccion: str,
        servicio_afectado: str,
    ) -> "Incidente":
        """Reconstruye un `Incidente` ya persistido (uso exclusivo de repositorios)."""
        instancia = cast(
            "Incidente",
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
        instancia.severidad = severidad
        instancia.pasos_reproduccion = pasos_reproduccion
        instancia.servicio_afectado = servicio_afectado
        return instancia

    @staticmethod
    def _validar_severidad(severidad: Severidad) -> Severidad:
        if not isinstance(severidad, Severidad):
            raise TypeError("La severidad debe ser una instancia de Severidad.")
        return severidad

    @staticmethod
    def _validar_pasos_reproduccion(pasos_reproduccion: str) -> str:
        if not isinstance(pasos_reproduccion, str):
            raise TypeError("Los pasos de reproducción deben ser una cadena de texto.")
        pasos_normalizados = pasos_reproduccion.strip()
        if not pasos_normalizados:
            raise ValueError("Los pasos de reproducción no pueden estar vacíos.")
        return pasos_normalizados

    @staticmethod
    def _validar_servicio_afectado(servicio_afectado: str) -> str:
        if not isinstance(servicio_afectado, str):
            raise TypeError("El servicio afectado debe ser una cadena de texto.")
        servicio_normalizado = servicio_afectado.strip()
        if not servicio_normalizado:
            raise ValueError("El servicio afectado no puede estar vacío.")
        return servicio_normalizado
