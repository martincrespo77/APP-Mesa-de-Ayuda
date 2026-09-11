"""Shared Kernel: tipos y excepciones comunes a todos los módulos de dominio."""

from app.compartido.dominio import RolUsuario
from app.compartido.excepciones import DominioError

__all__ = ["RolUsuario", "DominioError"]
