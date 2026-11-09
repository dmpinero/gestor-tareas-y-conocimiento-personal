# Guía de contribución

## Idioma del código: español de España

Todo esto se escribe en español de España:

- clases, funciones y métodos, variables y comentarios;
- la documentación (README, ADRs, PRs, issues);
- el cuerpo de los mensajes de commit.

**Excepciones**, porque no son "nuestro código" sino contratos de herramientas:

- Prefijos de Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`, `ci:`, `build:`. La descripción que sigue sí va en español: `feat: añadir endpoint para crear tareas`.
- Convenciones obligatorias de frameworks y gestores de paquetes: `src/`, `tests/`, `main.py`, `package.json`, `docker-compose.yml`, `.github/`, `Dockerfile` y las claves de configuración YAML/JSON.
- Términos técnicos sin traducción natural asentada: `middleware`, `router`, `token`, `hash`, `commit`, `pipeline`, `endpoint`.
- Nombres de librerías y APIs de terceros: `SQLAlchemy`, `FastAPI`, `Pinia`...

Vocabulario de dominio de referencia: `Tarea`, `Nota`, `Etiqueta`, `Proyecto`, `RepositorioTareas`, `crear_tarea`, `listar_notas`.

## Arquitectura: hexagonal + DDD

El backend se organiza en capas: `dominio` → `aplicacion` → `infraestructura` → `interfaces`. Ver [docs/adr/0001-arquitectura-hexagonal-y-ddd.md](docs/adr/0001-arquitectura-hexagonal-y-ddd.md).

`import-linter` comprueba la regla de dependencias automáticamente en CI: `dominio` no puede importar nada de las otras capas.

## Metodología: ODD → BDD → TDD

1. **ODD (Organic Driven Development)**: el trabajo pequeño se hace directamente.
   - Una funcionalidad grande se especifica primero en un documento de feature, `odd/tasks/<nombre-feature>.md`, con tres secciones:
     - `## Specs`: requisitos numerados `S#` que citan literalmente la petición.
     - `## Tasks`: tareas con su ruta y su commit.
     - `## Log`: la bitácora; la primera entrada es la petición original.
   - Ese documento es la especificación que se referencia en el PR.
2. **BDD**: los escenarios de aceptación se traducen a Gherkin en español, en `backend/tests/bdd/caracteristicas/*.feature` con `# language: es`, y se ejecutan con `pytest-bdd`.
3. **TDD**: cada paso se implementa escribiendo primero un test unitario en `backend/tests/unitarios/`: rojo → verde → refactor.

## Clean Code

- Nombres expresivos y una sola responsabilidad por función o clase, aunque estén en español.
- En el backend, `ruff` (con `pep8-naming`) e `import-linter` bloquean el PR si se rompen las convenciones de nombres o las capas de la arquitectura.
- En el frontend, `ESLint` hace lo mismo con la regla `naming-convention`.

## Git

- Estrategia de ramas: GitHub Flow. `main` siempre es desplegable y no admite pushes directos.
- Una rama por funcionalidad o corrección: `feature/<slug>` o `fix/<slug>`, con el slug en español (p. ej. `feature/crear-tarea`).
- Commits en formato [Conventional Commits](https://www.conventionalcommits.org/es/), en unidades revisables de unas 400 líneas con sus tests y su documentación.
- Todo cambio entra por Pull Request, con la plantilla de `.github/PULL_REQUEST_TEMPLATE.md` y los checks de CI en verde.

## Releases

Al fusionar a `main`, `semantic-release` calcula la versión y publica un release de GitHub agrupado por categorías: `✨ Novedades`, `🐛 Corregido`, `🔧 Mejoras` y `⚙️ Cambios internos`.

No actualiza ningún fichero del repositorio, porque `main` es una rama protegida sin pushes directos.

La aplicación lee la versión y el historial de cambios en vivo desde la API de GitHub (`frontend/src/api/github.ts`), así que siempre coinciden con la última release publicada.
