# 13. Serialización y Reconstrucción Polimórfica en BD

Un problema habitual en sistemas orientados a objetos es **persistir colecciones polimórficas** (por ejemplo, una lista de modificadores de precio de distinto tipo: `IVA`, `RecargoFijo`, `Promocion`) en una base de datos NoSQL y reconstruir los objetos originales con su comportamiento intacto al leerlos.

---

## Estrategia de Schemas de BD Polimórficos

La solución enseñada en el curso separa los **Esquemas de API (Pydantic)** de los **Esquemas de Base de Datos (DbSchemas)**:

1. Guardar un discriminador de tipo explícito en el documento BSON/JSON (`"tipo": "RecargoFijo"`).
2. Usar un contrato de serialización `to_mongo()` y `from_mongo()`.
3. Emplear una fábrica (**SchemaFactory**) para instanciar el schema correspondiente al leer.

---

## Implementación

### Archivo: `products/schemas_db.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from .domain import Modificador, IVA, RecargoFijo, Promocion

class ModificadorDbSchema(ABC):
    """Contrato base para serializar y deserializar modificadores en MongoDB."""
    @abstractmethod
    def to_mongo(self) -> Dict[str, Any]:
        pass

    @staticmethod
    @abstractmethod
    def from_mongo(data: Dict[str, Any]) -> Modificador:
        pass

class IVADbSchema(ModificadorDbSchema):
    def __init__(self, iva: IVA):
        self._iva = iva

    def to_mongo(self) -> Dict[str, Any]:
        return {"tipo": "IVA", "porcentaje": 0.21, "taxfree": self._iva.taxfree}

    @staticmethod
    def from_mongo(data: Dict[str, Any]) -> IVA:
        return IVA(taxfree=data.get("taxfree", False))

class RecargoFijoDbSchema(ModificadorDbSchema):
    def __init__(self, recargo: RecargoFijo):
        self._recargo = recargo

    def to_mongo(self) -> Dict[str, Any]:
        return {"tipo": "RecargoFijo", "monto": self._recargo.monto}

    @staticmethod
    def from_mongo(data: Dict[str, Any]) -> RecargoFijo:
        return RecargoFijo(recargo=data["monto"])

class PromocionDbSchema(ModificadorDbSchema):
    def __init__(self, promo: Promocion):
        self._promo = promo

    def to_mongo(self) -> Dict[str, Any]:
        return {"tipo": "Promocion", "descuento": self._promo.descuento}

    @staticmethod
    def from_mongo(data: Dict[str, Any]) -> Promocion:
        return Promocion(descuento=data["descuento"])
```

### Archivo: `products/factory_db.py`
```python
from typing import Dict, Any
from .schemas_db import ModificadorDbSchema, IVADbSchema, RecargoFijoDbSchema, PromocionDbSchema
from .domain import Modificador

class ModificadorSchemaFactory:
    """Fábrica que asocia nombres de tipo y clases de dominio con sus DbSchemas."""
    _schemas = {
        "IVA": IVADbSchema,
        "RecargoFijo": RecargoFijoDbSchema,
        "Promocion": PromocionDbSchema,
    }

    @classmethod
    def get_schema(cls, modificador: Modificador) -> ModificadorDbSchema:
        nombre_clase = modificador.__class__.__name__
        schema_cls = cls._schemas.get(nombre_clase)
        if not schema_cls:
            raise ValueError(f"No existe schema de persistencia para: {nombre_clase}")
        return schema_cls(modificador)

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> Modificador:
        tipo = data.get("tipo")
        schema_cls = cls._schemas.get(tipo)
        if not schema_cls:
            raise ValueError(f"Tipo de modificador desconocido en base de datos: {tipo}")
        return schema_cls.from_mongo(data)
```

---

## Serialización del Agregado Raíz (Producto)

```python
class ProductoDbSchema:
    @staticmethod
    def from_domain_to_mongo(producto) -> dict:
        return {
            "producto_id": str(producto.id),
            "nombre": producto.nombre,
            "precio_base": producto.precio_base,
            "modificadores": [
                ModificadorSchemaFactory.get_schema(m).to_mongo()
                for m in producto.modificadores
            ],
            "active": True
        }

    @staticmethod
    def from_mongo_to_domain(doc: dict):
        modificadores = [
            ModificadorSchemaFactory.from_mongo(m_doc)
            for m_doc in doc.get("modificadores", [])
        ]
        producto = Producto(
            nombre=doc["nombre"],
            precio_base=doc["precio_base"],
            iva=IVA(),
            modificadores=modificadores
        )
        return producto
```

---

## Directivas para Agentes de IA

1. **No guardar clases binarias con `pickle`**: Almacene diccionarios JSON/BSON legibles con un campo discriminador `"tipo"`.
2. **Reconstruir objetos completos**: Al leer de la base de datos, devuelva instancias de las clases del dominio con sus métodos listos para operar, no diccionarios.
3. **No mezclar Schemas de API con Schemas de BD**: La representación de un objeto hacia el cliente HTTP puede diferir sensiblemente de cómo se almacena en el motor NoSQL.
