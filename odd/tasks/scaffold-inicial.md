# scaffold-inicial

Objetivo: crear el esqueleto de la aplicación de tareas y conocimiento personal replicando la arquitectura técnica y la forma de trabajar de `gestor-gastos-personal`, sin su dominio de gastos.
Rama: `feature/scaffold-inicial` · Entrega: `ask-on-risk` → cadena `stacked-to-main` · Tests: `uv run pytest` (backend), `pnpm test:unit run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Propósito: "Quiero crear una aplicación para gestionar todas mis tareas y conocimiento personal."
- **S2** Origen técnico: "toda la arquitectura técnica, forma de trabajar, etc. la obtengas de un proyecto que ya tengo y que está desplegado en https://github.com/dmpinero/gestor-gastos-personal". Se replican el stack, las capas hexagonales, las herramientas de calidad, la estrategia de tests (TDD + BDD, cobertura ≥ 80 %), Docker y Railway.
- **S3** Sin dominio de gastos: "El contexto es diferente, porque lo que quiero aquí es tener control de tareas y conocimiento, no quiero controlar gastos". No se copia ningún contexto de dominio del proyecto de referencia.
- **S4** Igual que el original: "la estructura técnica, iconos en la parte izquierda, modo claro/oscuro, gestión de Pull Request, etc. sí que quiero que sea igual." Esto cubre la barra lateral izquierda de iconos colapsable, el conmutador de tema claro/oscuro sin parpadeo, las plantillas de PR e issues, GitHub Flow, Conventional Commits, pre-commit, CI, semantic-release y dependabot.
- **S5** Seguridad: "de momento sin login". Ningún endpoint exige autenticación.
- **S6** Flujo de trabajo: "vamos con ODD". La documentación de contribución y la plantilla de PR referencian `odd/tasks/` en lugar de SDD u openspec.

Supuestos (a confirmar por el usuario):

- **A1** Identificadores, documentación y textos de UI en español de España, igual que en el proyecto de referencia.
- **A2** Python 3.12 en todo el proyecto, incluido el Dockerfile, para corregir el desajuste de la referencia, que usa 3.14 en Docker.
- **A3** El paquete backend se llama `gestor_tareas`.
- **A4** La barra lateral muestra Inicio, Tareas y Conocimiento, y debajo un grupo Configuración. Las vistas son marcadores vacíos; las funcionalidades de dominio quedan para features posteriores.
- **A5** Crear el repositorio en GitHub, hacer push y desplegar en Railway son decisiones del usuario y quedan fuera de esta feature.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
| --- | --- | --- | --- | --- |
| T1 | S2, S4, S6 | inline | hecho (sin commit) | — |
| T2 | S2, S3, S5 | delegada (writer: unidad paralela con T3, superficie `backend/**`) | en curso | — |
| T3 | S2, S3, S4 | delegada (writer: unidad paralela con T2, superficie `frontend/**`) | en curso | — |
| T4 | S2, S4 | inline | hecho (sin commit) | — |

Contenido de cada tarea:

- **T1** Raíz y forma de trabajar: `.gitignore`, `.gitattributes`, `README.md`, `CONTRIBUTING.md` (adaptado a ODD), `package.json`, `.releaserc.json`, `.pre-commit-config.yaml`, `docs/CicloDesarrollo.md` y `docs/adr/0001-arquitectura-hexagonal-y-ddd.md`.
- **T2** Esqueleto backend: configuración, aplicación FastAPI con `GET /api/v1/salud`, sesión SQLAlchemy, Alembic sin migraciones de dominio, observabilidad, middleware de cabeceras de seguridad, manejadores de errores y excepciones base. Tests: BDD de salud, integración, contrato OpenAPI y unitarios. También `Dockerfile`, `entrypoint.sh` y `railway.json`.
- **T3** Esqueleto frontend: shell (barra lateral, barra superior, barra de estado), `useModoOscuro` con `ConmutadorTema`, componentes `ui/` de shadcn, router con vistas marcador y cliente API. Tests unitarios y e2e (`layout`, `accesibilidad`). También `Dockerfile` con nginx y `railway.json`.
- **T4** GitHub y entorno local: los workflows `ci-backend`, `ci-frontend`, `e2e`, `security-scan` y `release`, las plantillas de PR e issues, `dependabot.yml` y `docker-compose.yml`.

Previsión de entrega: unas 3 000 líneas escritas, sin contar `componentes/ui/` copiados ni lockfiles. Como supera las 400, se aplica la cadena `stacked-to-main`: un commit por PR, y cada PR se fusiona a `main` en orden.

Cortes de PR:

| PR | Contenido | Tareas | Líneas aprox. |
| --- | --- | --- | --- |
| PR1 | Configuración raíz, `CONTRIBUTING`, ADR, documento ODD, plantillas, dependabot, `security-scan`, `release` | T1, parte de T4 | ~440 |
| PR2 | Backend + `ci-backend.yml` | T2 | por medir |
| PR3 | Frontend + `ci-frontend.yml` | T3 | por medir |
| PR4 | `docker-compose.yml`, `e2e.yml`, `README.md` | parte de T1 y de T4 | ~370 |
| PR5 | `docs/CicloDesarrollo.md` | parte de T1 | ~360 |

## Log

- **L1** (2026-11-09) Petición original: "Quiero crear una aplicación para gestionar todas mis tareas y conocimiento personal. Para no partir de cero, quiero que toda la arquitectura técnica, forma de trabajar, etc. la obtengas de un proyecto que ya tengo y que está desplegado en https://github.com/dmpinero/gestor-gastos-personal. El contexto es diferente, porque lo que quiero aquí es tener control de tareas y conocimiento, no quiero controlar gastos, pero la estructura técnica, iconos en la parte izquierda, modo claro/oscuro, gestión de Pull Request, etc. sí que quiero que sea igual."
- **L2** (2026-11-09) Usuario: "tienes bien todo y vamos con ODD?". Se confirma ODD como flujo, sustituye a SDD (gentle-ai 4.4.0).
- **L3** (2026-11-09) Usuario: "de momento sin login".
- **L4** (2026-11-09) El mapa de la referencia está en Engram (`architecture/reference-blueprint`). Clon local de solo lectura en el scratchpad de la sesión. Hallazgos: el Dockerfile usa Python 3.14 frente a 3.12 en el proyecto, y existen helpers JWT que ninguna ruta usa.
- **L5** (2026-11-09) Repositorio git inicializado en `main`. Siguiente paso: crear la rama `feature/scaffold-inicial` y ejecutar T1 inline, con T2 y T3 en paralelo.
- **L6** (2026-11-09) Rama `feature/scaffold-inicial` creada desde `9e16b04`. T2 y T3 se lanzan en paralelo como writers con superficies disjuntas.
- **L7** (2026-11-09) T1 y T4 hechas inline. Decisiones:
  - Se eliminan las menciones a las skills `/revision-clean-code` y `/generar-release-notes`: no existen en el repositorio de referencia ni en los directorios de skills del usuario.
  - `package-lock.json` raíz se copia de la referencia renombrando el proyecto, porque `npm install --package-lock-only` fue rechazado por la política de npm local.
  - Se quitan `RUTA_ADJUNTOS` y el volumen de adjuntos.
  - Las plantillas de PR e issues pasan a referenciar `odd/tasks/`.
  - Comprobación: no queda ninguna referencia a `gasto`, `openspec` ni `SDD` en T1/T4, salvo el enlace al proyecto de referencia.
  - Pendiente: decidir la estrategia de cadena antes del primer commit.
- **L8** (2026-11-09) Usuario: "stacked-to-main". Los cortes se ordenan para que CI quede en verde en cada PR: cada workflow viaja con el código que valida.
