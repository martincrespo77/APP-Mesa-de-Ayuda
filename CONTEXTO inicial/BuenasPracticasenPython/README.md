# Buenas Prácticas en Python: POO, Arquitectura y Patrones

Este compendio reúne las reglas, estándares y patrones de diseño enseñados a lo largo de las clases de **Paradigmas de Programación V**. Su propósito es servir de guía normativa y técnica tanto para desarrolladores como para modelos de Inteligencia Artificial, asegurando implementaciones de alta cohesión, bajo acoplamiento, tipado estricto y diseño modular.

---

## Principios Rectores del Proyecto

1. **Separación de Entidades en Archivos Independientes**: 
   Cada entidad o clase principal debe residir en su propio archivo dentro de un paquete temático. Queda terminantemente desaconsejado agrupar múltiples entidades en un único archivo monolítico.
2. **Modelo de Dominio Rico vs Modelo Anémico**:
   Los objetos no son meras estructuras de datos; encapsulan estado y comportamiento, haciéndose responsables de sus propias validaciones (Principio *Information Expert*).
3. **Manejo Explicito de Errores**:
   Uso riguroso de jerarquías de excepciones de dominio personalizadas y validaciones tempranas en constructores (`__init__`) o métodos estáticos de validación.
4. **Arquitectura por Capas y Desacoplamiento**:
   Separación limpia entre Dominio de Negocio, Esquemas de Entrada/Salida (DTOs), Servicios de Aplicación, Controladores (Routers) y Persistencia (Repositories).
5. **Tipado Estático y Modernidad**:
   Uso sistemático de *type hints*, identificadores únicos inmutables (`UUID`), gestión de dependencias moderna con `uv` y pruebas unitarias aisladas con el patrón AAA.

---

## Índice Temático

Haga clic en cada tema para consultar sus reglas y ejemplos detallados de implementación:

| # | Documento | Tema Principal | Enfoque Clave |
|---|---|---|---|
| 01 | [Principios POO según Booch](01_principios_poo_booch.md) | Fundamentos POO | Abstracción, Encapsulamiento, Herencia y Polimorfismo. |
| 02 | [Responsabilidades e Information Expert](02_separacion_responsabilidades_expert.md) | Asignación de Responsabilidades | Quién valida y quién decide; Inversión de responsabilidad. |
| 03 | [Modularidad y Separación de Entidades](03_modularidad_archivos_entidades.md) | Estructura de Proyectos | Una entidad por archivo, imports limpios y anti-God Object. |
| 04 | [Manejo de Excepciones y Validaciones](04_manejo_excepciones_y_validaciones.md) | Robustez y Dominio | Jerarquías de excepciones de negocio y validación defensiva. |
| 05 | [Patrón Singleton](05_patron_singleton.md) | Patrón Creacional | Instancia única con `__new__` para configuraciones del sistema. |
| 06 | [Patrón Factory Method](06_patron_factory_method.md) | Patrón Creacional | Creación desacoplada y cumplimiento de Open/Closed Principle. |
| 07 | [Patrón Strategy](07_patron_strategy.md) | Patrón de Comportamiento | Familias de algoritmos intercambiables en tiempo de ejecución. |
| 08 | [Patrón Observer](08_patron_observer.md) | Patrón de Comportamiento | Suscripción y notificación desacoplada 1 a N ante cambios de estado. |
| 09 | [Patrones Adapter y Decorator](09_patrones_adapter_y_decorator.md) | Patrones Estructurales | Integración legacy (Adapter) y extensión dinámica (Decorator). |
| 10 | [Unit Testing y Patrón AAA](10_unit_testing_buenas_practicas.md) | Calidad de Software | Pruebas unitarias con `unittest`, patrón Arrange-Act-Assert y mocks. |
| 11 | [Arquitectura en Capas para APIs](11_arquitectura_en_capas_api.md) | Arquitectura de Software | Desacople de Dominio, DTOs (Pydantic), Servicios y Routers (FastAPI). |
| 12 | [Patrón Repository y Persistencia](12_patron_repository_y_persistencia.md) | Acceso a Datos | Abstracción de base de datos (MongoDB) y operaciones CRUD puras. |
| 13 | [Serialización Polimórfica en BD](13_serializacion_polimorfica.md) | Mapeo Objeto-Documento | Mapeo y reconstrucción de jerarquías complejas con Factory. |
| 14 | [Estándares de Python Moderno](14_estandares_python_moderno.md) | Herramientas y Despliegue | Type hinting, empaquetado con `uv` y Dockerfile multi-stage. |

---

## Cómo Consumir esta Guía

- **Para Desarrolladores**: Úselo como referencia de diseño y plantilla para resolver problemas recurrentes de arquitectura y modelado orientado a objetos.
- **Para Agentes IA**: Debe interpretar las directivas de estos documentos como restricciones estrictas al generar o refactorizar código en Python. Priorice siempre la separación en módulos independientes y la claridad semántica sobre soluciones monolíticas.
