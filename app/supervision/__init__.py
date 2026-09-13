"""Módulo de dominio: relación de supervisión (N:M) entre Supervisor y
Operador/Técnico.

Vive en su propio módulo (no como atributo de `Usuario`) porque es una
relación con su propia identidad y fecha de asignación, no un dato del
usuario supervisado.
"""

from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import (
    RelacionInvalidaError,
    RelacionYaExisteError,
    RolNoSupervisableError,
    SupervisionError,
)
from app.supervision.repositorio import RepositorioSupervision
from app.supervision.servicios import ServicioSupervision

__all__ = [
    "RelacionSupervision",
    "SupervisionError",
    "RelacionYaExisteError",
    "RolNoSupervisableError",
    "RelacionInvalidaError",
    "RepositorioSupervision",
    "ServicioSupervision",
]
