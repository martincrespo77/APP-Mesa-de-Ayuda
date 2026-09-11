"""Entidad concreta `Incidente`: interrupción o degradación de un servicio."""

import uuid
from enum import StrEnum

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import TipoRequerimiento


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
