# 12. Patrón Repository y Persistencia de Datos

El patrón **Repository** media entre la capa de dominio/servicios y la capa de acceso a datos (por ejemplo, MongoDB), simulando una colección de objetos en memoria y encapsulando los detalles de almacenamiento.

---

## Principio de Desacoplamiento de Persistencia

- **El Servicio** no conoce sentencias SQL ni operadores NoSQL (`$set`, `insert_one`, etc.). Solo le pide al repositorio que guarde u obtenga entidades.
- **El Repositorio** recibe y devuelve **entidades de dominio puras**, no diccionarios crudos ni cursores directos del driver.

---

## Implementación Modular del Repositorio

### Archivo: `internal/database.py`
```python
from pymongo import MongoClient

class DatabaseConnection:
    """Gestiona la conexión centralizada a MongoDB."""
    def __init__(self, uri: str = "mongodb://root:example@localhost:27017"):
        self._client = MongoClient(uri)
        self.db = self._client["ecommerce_db"]

    def get_collection(self, nombre: str):
        return self.db[nombre]
```

### Archivo: `products/repository.py`
```python
from typing import List, Optional
from pymongo.collection import Collection
from .domain import Producto
from .schemas import ProductoDbSchema

class ProductRepository:
    def __init__(self, db):
        self._collection: Collection = db["products"]

    def add(self, producto: Producto) -> None:
        documento = ProductoDbSchema.from_domain_to_mongo(producto)
        self._collection.insert_one(documento)

    def get_by_id(self, product_id: str) -> Optional[Producto]:
        data = self._collection.find_one({"producto_id": product_id})
        if not data:
            return None
        return ProductoDbSchema.from_mongo_to_domain(data)

    def list_all(self) -> List[Producto]:
        productos = []
        for doc in self._collection.find({"active": True}):
            productos.append(ProductoDbSchema.from_mongo_to_domain(doc))
        return productos

    def update(self, producto: Producto) -> bool:
        documento = ProductoDbSchema.from_domain_to_mongo(producto)
        resultado = self._collection.update_one(
            {"producto_id": str(producto.id)},
            {"$set": documento}
        )
        return resultado.modified_count > 0

    def remove(self, product_id: str) -> bool:
        # Borrado lógico o físico
        resultado = self._collection.delete_one({"producto_id": product_id})
        return resultado.deleted_count > 0
```

---

## Integración con la Capa de Servicios

### Archivo: `products/service.py`
```python
from typing import List, Optional
from .repository import ProductRepository
from .schemas import ProductCreateSchema, ProductDetailSchema
from .domain import Producto, IVA

class ProductService:
    def __init__(self, repository: ProductRepository):
        self._repo = repository

    def crear(self, dto: ProductCreateSchema) -> ProductDetailSchema:
        producto = Producto(nombre=dto.nombre, precio_base=dto.precio_base, iva=IVA())
        self._repo.add(producto)
        return ProductDetailSchema.from_domain(producto)

    def obtener_por_id(self, product_id: str) -> Optional[ProductDetailSchema]:
        producto = self._repo.get_by_id(product_id)
        if not producto:
            return None
        return ProductDetailSchema.from_domain(producto)
```

---

## Ventajas para el Software y las Pruebas

1. **Sustitución Trivial en Tests**: En los tests unitarios del Servicio, se puede inyectar un repositorio mock en memoria (`InMemoryProductRepository`) sin necesidad de levantar contenedores Docker con MongoDB.
2. **Cambio de Motor de BD Seguro**: Si se migra de MongoDB a PostgreSQL, la capa de dominio, los schemas y los servicios permanecen 100% inalterados.

---

## Directivas para Agentes de IA

- **Nunca filtrar datos con `_id` de Mongo en el dominio**: Use identificadores del dominio como UUIDs en formato string (`producto_id`).
- **Convertir a entidades**: La salida de `find()` o `find_one()` debe pasar siempre por un deserializador hacia la entidad de dominio antes de salir del repositorio.
