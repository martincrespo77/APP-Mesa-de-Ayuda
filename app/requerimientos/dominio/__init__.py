"""Dominio puro de requerimientos: `Requerimiento`, `Incidente`, `Solicitud`.

Cada entidad vive en su propio archivo físico (regla de cátedra de una
entidad por archivo); este `__init__.py` los reexporta para que el resto
del sistema pueda importar `from app.requerimientos.dominio import Incidente`
sin conocer el layout interno del subpaquete.
"""

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.incidente import CategoriaIncidente, Incidente, UrgenciaIncidente
from app.requerimientos.dominio.solicitud import CategoriaSolicitud, Solicitud

__all__ = [
    "Requerimiento",
    "Comentario",
    "Incidente",
    "Solicitud",
    "EstadoRequerimiento",
    "TipoRequerimiento",
    "UrgenciaIncidente",
    "CategoriaIncidente",
    "CategoriaSolicitud",
]
