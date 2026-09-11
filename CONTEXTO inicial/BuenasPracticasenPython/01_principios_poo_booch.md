# 01. Principios Fundamentales de POO según Grady Booch

Basado en *"Object-Oriented Analysis and Design with Applications"* (Grady Booch), la Programación Orientada a Objetos modela el software como una simulación donde **objetos autónomos colaboran enviándose mensajes**.

---

## Los 4 Pilares Conceptuales

### 1. Abstracción
- **Regla**: Enfocar las características esenciales de un objeto ignorando detalles accesorios.
- **Implementación**: Crear clases cohesivas con nombres del dominio en lugar de procedimientos sueltos con parámetros dispersos.

### 2. Encapsulamiento
- **Regla**: Ocultar los detalles de implementación y el estado interno.
- **Implementación**: Usar prefijo `_` para atributos protegidos. El estado solo muta a través de métodos que validan invariantes de negocio.

### 3. Herencia
- **Regla**: Jerarquía de generalización/especialización ("Es-un").
- **Implementación**: Reutilizar estructura y comportamiento común mediante clases base (`super().__init__()`).

### 4. Polimorfismo
- **Regla**: Una misma interfaz u operación con múltiples comportamientos según la clase concreta.
- **Implementación**: Métodos con igual firma pero lógica adaptada en cada subclase.

---

## Ejemplo de Implementación Modular

### Archivo: `biblioteca/socio.py`
```python
class Socio:
    def __init__(self, nombre: str, dni: str):
        self.nombre = nombre
        self.dni = dni
        self._prestamos = []

    def registrar_prestamo(self, libro) -> None:
        self._prestamos.append(libro)

    @property
    def cantidad_prestamos(self) -> int:
        return len(self._prestamos)
```

### Archivo: `biblioteca/libro.py`
```python
from typing import Optional
from .socio import Socio

class Libro:
    def __init__(self, titulo: str, autor: str):
        self.titulo = titulo
        self.autor = autor
        self._socio_actual: Optional[Socio] = None

    @property
    def esta_prestado(self) -> bool:
        return self._socio_actual is not None

    def prestar_a(self, socio: Socio) -> None:
        if self.esta_prestado:
            raise ValueError(f"El libro '{self.titulo}' ya está prestado.")
        self._socio_actual = socio
        socio.registrar_prestamo(self)
```

### Archivo: `biblioteca/biblioteca.py`
```python
from typing import List
from .libro import Libro
from .socio import Socio

class Biblioteca:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self._catalogo: List[Libro] = []

    def agregar_libro(self, libro: Libro) -> None:
        self._catalogo.append(libro)

    def prestar(self, libro: Libro, socio: Socio) -> None:
        if libro not in self._catalogo:
            raise ValueError("El libro no pertenece a esta biblioteca.")
        libro.prestar_a(socio)
```

### Archivo: `main.py`
```python
from biblioteca.libro import Libro
from biblioteca.socio import Socio
from biblioteca.biblioteca import Biblioteca

def main():
    biblio = Biblioteca("Central")
    libro = Libro("El Quijote", "Cervantes")
    socio = Socio("Carlos", "30111222")

    biblio.agregar_libro(libro)
    biblio.prestar(libro, socio)
    print(f"Socio {socio.nombre} tiene {socio.cantidad_prestamos} libro(s).")

if __name__ == "__main__":
    main()
```

---

## Comparativa: Procedural vs POO

| Enfoque Estructurado (Antipatrón) | Enfoque Orientado a Objetos (Booch) |
|---|---|
| `def prestar(biblio, socio_id, libro_id):` | `libro.prestar_a(socio)` |
| Lógica dispersa en funciones utilitarias. | Lógica cohesiva encapsulada en la entidad. |
| Diccionarios planos mutables por cualquiera. | Estado protegido con métodos validadores. |
| Acoplamiento a estructuras internas de datos. | Contratos de mensajes y colaboración. |

---

## Directivas para Agentes de IA

1. **No usar diccionarios planos** cuando se modela un concepto del dominio con ciclo de vida o reglas. Cree clases.
2. **Haga que los objetos colaboren**: Evite controladores gigantes que hacen `get` de todo y modifican atributos ajenos.
3. **Cada clase en su archivo físico**: No agrupar `Socio`, `Libro` y `Biblioteca` en el mismo script.
