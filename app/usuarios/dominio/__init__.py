"""Dominio puro de usuarios: jerarquía polimórfica por rol.

    Usuario (abstracta)
    ├── Solicitante
    └── Empleado (abstracta: email corporativo, sin suscripciones)
        ├── Operador
        ├── Tecnico
        └── Supervisor

Una entidad por archivo (igual que `app/requerimientos/dominio/`); este
`__init__.py` las reexporta para importar `from app.usuarios.dominio import
Tecnico` sin conocer el layout interno del subpaquete.
"""

from app.usuarios.dominio.email import Email
from app.usuarios.dominio.empleado import DOMINIO_CORPORATIVO, Empleado
from app.usuarios.dominio.fabrica import FabricaUsuarios
from app.usuarios.dominio.operador import Operador
from app.usuarios.dominio.solicitante import Solicitante
from app.usuarios.dominio.supervisor import Supervisor
from app.usuarios.dominio.tecnico import Tecnico
from app.usuarios.dominio.usuario import Usuario

__all__ = [
    "DOMINIO_CORPORATIVO",
    "Email",
    "Empleado",
    "FabricaUsuarios",
    "Operador",
    "Solicitante",
    "Supervisor",
    "Tecnico",
    "Usuario",
]
