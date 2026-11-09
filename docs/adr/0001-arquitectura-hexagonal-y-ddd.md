# 1. Arquitectura hexagonal con Domain-Driven Design

- Estado: aceptada
- Fecha: 2026-11-09

## Contexto

El backend del Gestor de Tareas y Conocimiento Personal tiene que cumplir tres condiciones:

- ser mantenible a largo plazo por una única persona desarrolladora;
- permitir sustituir piezas de infraestructura (base de datos, proveedor de autenticación, observabilidad) sin reescribir la lógica de negocio;
- facilitar el testing unitario del dominio sin depender de FastAPI, SQLAlchemy ni de una base de datos real.

La arquitectura se hereda del proyecto `gestor-gastos-personal`, donde ya está validada en producción.

## Decisión

Se adopta una arquitectura hexagonal (puertos y adaptadores) combinada con Domain-Driven Design táctico. Se organiza en cuatro capas dentro de `backend/src/gestor_tareas/`:

- **`dominio/`**: entidades, objetos de valor, excepciones e interfaces de repositorio (puertos). No depende de ninguna otra capa ni de ningún framework.
- **`aplicacion/`**: casos de uso que orquestan el dominio. Solo puede depender de `dominio`.
- **`infraestructura/`**: adaptadores concretos (SQLAlchemy, Sentry, OpenTelemetry...). Puede depender de `dominio` y `aplicacion`.
- **`interfaces/`**: adaptadores de entrada (API REST con FastAPI). Puede depender de las tres capas anteriores.

La regla de dependencias (las capas internas no conocen a las externas) no se deja solo en convención: `import-linter` la hace cumplir en CI. Ver la sección `[tool.importlinter]` de `backend/pyproject.toml`.

## Alternativas consideradas

- **Arquitectura en capas simple (Controller-Service-Repository)**: más rápida de arrancar. Pero a medida que el dominio crece (tareas, proyectos, notas, etiquetas, enlaces entre notas...), mezcla con facilidad las reglas de negocio con detalles de framework y ORM.
- **Sin capa de aplicación explícita (dominio anémico + lógica en los routers)**: se descarta porque acopla la lógica de negocio a FastAPI desde el principio y dificulta el testing unitario puro.

## Consecuencias

- Hay más ficheros y más ceremonia inicial que en un CRUD directo.
- El dominio se puede testear con `pytest` sin base de datos ni HTTP.
- Cambiar de MySQL a otro motor, o añadir autenticación, implica solo escribir nuevos adaptadores en `infraestructura/`, sin tocar `dominio/` ni `aplicacion/`.
- El contrato de `import-linter` hace fallar el PR si alguien introduce una dependencia en la dirección incorrecta.
