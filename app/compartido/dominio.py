"""Shared Kernel: tipos de negocio compartidos entre módulos de dominio.

Centraliza aquí únicamente los conceptos que necesitan ser referenciados por
más de un módulo (`usuarios` y `requerimientos`) para evitar importaciones
circulares entre ambos.
"""

from enum import StrEnum


class RolUsuario(StrEnum):
    """Roles de negocio reconocidos por la Mesa de Ayuda de la cooperativa."""

    SOLICITANTE = "SOLICITANTE"
    OPERADOR = "OPERADOR"
    TECNICO = "TECNICO"
    SUPERVISOR = "SUPERVISOR"


class ServicioComunicarlos(StrEnum):
    """Servicios que presta la cooperativa, a los que un Solicitante se suscribe
    y sobre los que se abre un Incidente/Solicitud."""

    TELEFONIA_CELULAR = "TELEFONIA_CELULAR"
    INTERNET_BANDA_ANCHA = "INTERNET_BANDA_ANCHA"
    TELEVISION = "TELEVISION"
