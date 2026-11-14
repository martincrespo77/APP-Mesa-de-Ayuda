"""Value Objects de creación: un pedido tipado de alta por cada tipo de requerimiento."""

from app.requerimientos.dominio.creacion.base import DatosRequerimiento
from app.requerimientos.dominio.creacion.datos_incidente import DatosIncidente
from app.requerimientos.dominio.creacion.datos_solicitud import DatosSolicitud

__all__ = ["DatosIncidente", "DatosRequerimiento", "DatosSolicitud"]
