"""Puerto `TraductorCriterios`: cómo un adaptador de persistencia ejecuta un criterio.

Es la mitad "visitante" del double dispatch de `CriterioVisibilidad.traducir`:
cada criterio concreto llama al método del traductor que le corresponde, y
cada adaptador (Mongo, SQL...) devuelve su propia representación de consulta
`T`. El dominio define el contrato sin conocer ninguna tecnología.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.usuarios.dominio import Usuario


class TraductorCriterios[T](Protocol):
    """Convierte cada criterio de visibilidad en una consulta de tipo `T`."""

    def todos(self) -> T:
        """Consulta sin restricciones (bandeja completa)."""
        ...

    def abiertos_por(self, solicitante: Usuario) -> T:
        """Consulta de los requerimientos abiertos por `solicitante`."""
        ...
