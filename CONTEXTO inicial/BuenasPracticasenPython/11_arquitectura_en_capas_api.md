# 11. Arquitectura en Capas para APIs REST

En aplicaciones backend profesionales con **FastAPI**, el código debe estructurarse en capas con responsabilidades delimitadas para evitar acoplar la lógica de negocio al framework web.

---

## Flujo de Ejecución y Dependencias

```
HTTP Request ──> [Router / API] ──> [Service] ──> [Domain] ──> [Repository]
                      │                │              │
                   (DTOs)           (DTOs)       (Entidades)
```

1. **Router**: Capa de transporte HTTP (rutas, códigos de estado, parámetros).
2. **Service**: Orquesta los casos de uso y aplica las reglas del flujo.
3. **Domain**: Entidades ricas con lógica pura del negocio (sin FastAPI ni DB).
4. **Schemas (DTOs)**: Modelos Pydantic para validación y serialización de I/O.

---

## Implementación Separada por Capas

### 1. Capa de Dominio: `app/products/domain.py`
```python
import uuid
from typing import List, Optional

class IVA:
    PORCENTAJE = 0.21
    def aplicar(self, precio: float) -> float:
        return round(precio * (1 + self.PORCENTAJE), 2)

class Producto:
    def __init__(self, nombre: str, precio_base: float, iva: IVA):
        self.id = uuid.uuid4()
        self.nombre = nombre
        self.precio_base = precio_base
        self.iva = iva

    def calcular_precio_final(self) -> float:
        return self.iva.aplicar(self.precio_base)
```

### 2. Capa de DTOs / Schemas: `app/products/schemas.py`
```python
from pydantic import BaseModel, Field
from .domain import Producto

class ProductCreateSchema(BaseModel):
    nombre: str = Field(..., min_length=2)
    precio_base: float = Field(..., gt=0)

class ProductDetailSchema(BaseModel):
    id: str
    nombre: str
    precio_base: float
    precio_final: float

    @staticmethod
    def from_domain(producto: Producto) -> "ProductDetailSchema":
        """Transforma una entidad de dominio a un DTO de respuesta seguro."""
        return ProductDetailSchema(
            id=str(producto.id),
            nombre=producto.nombre,
            precio_base=producto.precio_base,
            precio_final=producto.calcular_precio_final()
        )
```

### 3. Capa de Servicio: `app/products/service.py`
```python
from typing import List
from .domain import Producto, IVA
from .schemas import ProductCreateSchema, ProductDetailSchema

class ProductService:
    def __init__(self, repository):
        self._repository = repository

    def crear_producto(self, data: ProductCreateSchema) -> ProductDetailSchema:
        nuevo = Producto(nombre=data.nombre, precio_base=data.precio_base, iva=IVA())
        self._repository.save(nuevo)
        return ProductDetailSchema.from_domain(nuevo)

    def listar_productos(self) -> List[ProductDetailSchema]:
        productos = self._repository.find_all()
        return [ProductDetailSchema.from_domain(p) for p in productos]
```

### 4. Capa de Router / Controlador: `app/products/router.py`
```python
from fastapi import APIRouter, status
from typing import List
from .schemas import ProductCreateSchema, ProductDetailSchema
from .service import ProductService

class ProductRouter:
    def __init__(self, service: ProductService):
        self._service = service
        self.router = APIRouter(prefix="/productos", tags=["Productos"])
        self._registrar_rutas()

    def _registrar_rutas(self):
        self.router.add_api_route(
            "/", self.listar, methods=["GET"], response_model=List[ProductDetailSchema]
        )
        self.router.add_api_route(
            "/", self.crear, methods=["POST"], status_code=status.HTTP_201_CREATED,
            response_model=ProductDetailSchema
        )

    async def listar(self) -> List[ProductDetailSchema]:
        return self._service.listar_productos()

    async def crear(self, body: ProductCreateSchema) -> ProductDetailSchema:
        return self._service.crear_producto(body)
```

---

## Reglas para Agentes de IA

1. **Cero FastAPI en el Dominio**: La carpeta `domain.py` no debe importar nada de `fastapi` ni `pydantic`.
2. **DTOs Separados de Entidades**: Nunca use modelos Pydantic como entidades de dominio con lógica de negocio compleja. Use clases de Python estándar en el Dominio y Pydantic en los Schemas.
3. **Mapeo Explícito**: Emplee métodos fábrica como `@staticmethod from_domain()` para transformar entidades a DTOs de salida.
