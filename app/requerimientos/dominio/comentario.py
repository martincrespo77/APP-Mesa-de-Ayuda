"""Entidad de dominio `Comentario`: seguimiento inmutable sobre un requerimiento.

Se embebe en el agregado `Requerimiento` (igual que `EventoRequerimiento`),
no en una colección aparte: no hay ningún caso de uso que lea comentarios de
forma independiente de su ticket. La validación de contenido vive en
`Requerimiento.agregar_comentario` (Information Expert: la propia entidad ya
valida ahí el estado y el permiso del actor), siguiendo el mismo estilo que
`EventoRequerimiento` (dataclass sin validación propia).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Comentario:
    """Mensaje de seguimiento agregado por un actor autorizado sobre un ticket."""

    requerimiento_id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
