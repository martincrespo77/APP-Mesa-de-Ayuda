# 10. Unit Testing y Patrón AAA en Python

El testing unitario verifica que cada unidad aislada de código funcione de acuerdo con el diseño previsto. Reduce el temor al cambio y permite refactorizar con total seguridad.

---

## El Patrón de las 3 A (Arrange, Act, Assert)

Cada test debe estructurarse obligatoriamente en tres fases nítidas:

1. **Arrange (Preparar)**: Crear los datos de prueba, instanciar los objetos y configurar dobles de prueba (mocks/stubs).
2. **Act (Actuar)**: Invocar el método o funcionalidad que se desea probar.
3. **Assert (Afirmar)**: Verificar que el resultado obtenido o el cambio de estado coincida exactamente con lo esperado.

---

## Cómo Testear Clases Abstractas

Un desafío común es probar métodos concretos presentes en una clase abstracta (`ABC`). La buena práctica enseñada en la materia consiste en crear una **subclase concreta mínima dentro del `setUp`** del test.

### Archivo: `refugio/rescatados/test_mascota.py`
```python
import unittest
from datetime import datetime
from refugio.rescatados.mascota import Mascota

class TestMascota(unittest.TestCase):
    def setUp(self):
        # 1. Arrange: Subclase concreta mínima para probar la clase base abstracta
        class MascotaConcreta(Mascota):
            def cumplir_maximo(self, mascotas_hogar: list) -> bool:
                return False

            def esta_rehabilitada(self) -> bool:
                return False

        self.fecha_prueba = datetime(2025, 1, 1, 10, 0, 0)
        self.mascota = MascotaConcreta("Firulais", "M001", self.fecha_prueba)

    def tearDown(self):
        # Limpieza de recursos si fuera necesario
        self.mascota = None

    def test_inicializacion_exitosa(self):
        # Assert
        self.assertEqual(self.mascota.apodo, "Firulais")
        self.assertEqual(self.mascota.id_mascota, "M001")
        self.assertEqual(self.mascota.fecha_ingreso, self.fecha_prueba)

    def test_saludar_cuando_no_esta_rehabilitada(self):
        # Act
        mensaje = self.mascota.saludar()
        
        # Assert
        self.assertEqual(mensaje, "Firulais aún no está listo para saludar.")

    def test_saludar_cuando_esta_rehabilitada(self):
        # Arrange: Simulación puntual (stubbing) de método
        self.mascota.esta_rehabilitada = lambda: True

        # Act
        mensaje = self.mascota.saludar()

        # Assert
        self.assertEqual(mensaje, "Firulais te saluda con cariño.")
```

---

## Testeo de Lanzamiento de Excepciones

Para verificar que las reglas defensivas y de negocio disparen las excepciones correctas, utilice el administrador de contexto `assertRaises`:

### Archivo: `refugio/test_adopcion.py`
```python
import unittest
from datetime import datetime
from refugio.rescatados.perro import Perro
from refugio.adoptantes.adoptante import Adoptante
from refugio.adopcion.estrategia_novato import EstrategiaNovato
from refugio.excepciones import LimiteExcedidoError

class TestAdopcionNovato(unittest.TestCase):
    def test_adoptante_novato_no_puede_adoptar_dos_veces(self):
        # Arrange
        adoptante = Adoptante("Laura", EstrategiaNovato())
        p1 = Perro("Toby", "P1", datetime.now())
        p2 = Perro("Rex", "P2", datetime.now())

        # Act 1: Primera adopción permitida
        adoptante.adoptar(p1)
        self.assertEqual(len(adoptante.mascotas), 1)

        # Act 2 & Assert: Segunda adopción debe lanzar LimiteExcedidoError
        with self.assertRaises(LimiteExcedidoError):
            adoptante.adoptar(p2)
```

---

## Principios para Tests de Alta Calidad

1. **Aislamiento Absoluto**: Un test nunca debe depender de que otro test se haya ejecutado previamente.
2. **Sin I/O Lento**: Los unit tests no deben conectarse a bases de datos reales ni internet. Deben correr en milisegundos.
3. **Un Concepto por Test**: Cada método `test_*` debe verificar un único comportamiento específico.
4. **Ejecución Automatizada**: En proyectos gestionados con `uv`, ejecute todos los tests mediante:
   ```bash
   uv run python -m unittest discover
   ```

---

## Directivas para Agentes de IA

- Escriba siempre tests que sigan de manera evidente la estructura visual de las **3 A** con comentarios `# Arrange`, `# Act`, `# Assert`.
- Al encontrar una clase abstracta, pruebe su lógica concreta con una clase mock local mínima dentro de la suite de test.
