# 04. Manejo de Excepciones y Validaciones Defensivas

El control de errores en un modelo orientado a objetos debe ser explícito, semántico y defensivo. El sistema debe fallar tempranamente (*fail-fast*) cuando se violan las invariantes del modelo.

---

## 1. Jerarquía de Excepciones de Dominio

Nunca utilice excepciones genéricas como `Exception` o `RuntimeError` para reglas de negocio. Cree una jerarquía específica para el dominio:

### Archivo: `refugio/excepciones.py`
```python
class RefugioError(Exception):
    """Excepción base para todos los errores del dominio del refugio."""
    pass

class MascotaNoDisponibleError(RefugioError):
    """Lanzada cuando la mascota aún está en rehabilitación."""
    pass

class LimiteExcedidoError(RefugioError):
    """Lanzada cuando el adoptante superó la cantidad máxima permitida."""
    pass

class TipoIncompatibleError(RefugioError):
    """Lanzada cuando la política prohíbe mezclar especies."""
    pass
```

---

## 2. Validación Defensiva en Constructores con `@staticmethod`

Los objetos deben nacer en un estado válido. No permita instancias incompletas o corruptas.

### Archivo: `refugio/rescatados/mascota.py`
```python
from abc import ABC, abstractmethod
from datetime import datetime

class Mascota(ABC):
    def __init__(self, apodo: str, id_mascota: str, fecha_ingreso: datetime):
        self.apodo = self._validar_apodo(apodo)
        self.id_mascota = self._validar_id(id_mascota)
        self.fecha_ingreso = self._validar_fecha(fecha_ingreso)

    @staticmethod
    def _validar_apodo(apodo: str) -> str:
        if not isinstance(apodo, str):
            raise TypeError("El apodo debe ser una cadena de texto.")
        if not apodo.strip():
            raise ValueError("El apodo no puede estar vacío.")
        return apodo.strip()

    @staticmethod
    def _validar_id(id_mascota: str) -> str:
        if not isinstance(id_mascota, str) or not id_mascota.isalnum():
            raise ValueError("El identificador debe ser alfanumérico.")
        return id_mascota

    @staticmethod
    def _validar_fecha(fecha: datetime) -> datetime:
        if not isinstance(fecha, datetime):
            raise TypeError("La fecha de ingreso debe ser una instancia de datetime.")
        if fecha > datetime.now():
            raise ValueError("La fecha de ingreso no puede ser en el futuro.")
        return fecha
```

---

## 3. Reglas de Negocio con Excepciones Semánticas

### Archivo: `refugio/adopcion/estrategia_novato.py`
```python
from refugio.excepciones import LimiteExcedidoError

class EstrategiaNovato:
    def validar_adopcion(self, adoptante, mascota) -> None:
        if len(adoptante.mascotas) >= 1:
            raise LimiteExcedidoError(
                f"El adoptante novato '{adoptante.nombre}' no puede tener más de una mascota."
            )
```

---

## Buenas Prácticas vs Antipatrones

| Práctica Correcta ✅ | Antipatrón a Evitar ❌ |
|---|---|
| Crear una clase base de error por módulo/paquete. | Lanzar `raise Exception("algo falló")`. |
| Lanzar la excepción exacta en el punto de fallo. | Retornar `None` o `False` para indicar errores graves. |
| Capturar solo las excepciones esperadas (`except LimiteExcedidoError:`). | Silenciar errores con `except: pass` o `except Exception:`. |
| Validar tipos y rangos en el `__init__`. | Permitir objetos inválidos y validarlos en tiempo de uso. |

---

## Directivas para Agentes de IA

1. **Separar errores técnicos de errores de negocio**:
   - Para tipos de datos o parámetros inválidos: usar `TypeError` o `ValueError`.
   - Para restricciones del dominio de negocio: usar clases derivadas de su excepción base (ej. `RefugioError`).
2. **Métodos estáticos de validación**: Use `@staticmethod` privados (`_validar_*`) en la clase para desacoplar las reglas de formato de la lógica de instancia.
