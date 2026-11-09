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
| T1 | S2, S4, S6 | inline | hecho | `c76ca60`, `60179bd` (README), `19927fd` (CicloDesarrollo) |
| T2 | S2, S3, S5 | delegada (writer: unidad paralela con T3, superficie `backend/**`) | hecho | `8ea305b` |
| T3 | S2, S3, S4 | delegada (writer: unidad paralela con T2, superficie `frontend/**`) | hecho | `04855ab` |
| T4 | S2, S4 | inline | hecho | `c76ca60`, `8ea305b`, `04855ab`, `60179bd` (cada workflow con su código) |

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
| PR2 | Backend + `ci-backend.yml` | T2 | 1 259 (sin `uv.lock`); se recomienda `size:exception` |
| PR3 | Frontend + `ci-frontend.yml` | T3 | 1 680 escritas + 759 de `componentes/ui/` copiados de shadcn (sin lockfile); se recomienda `size:exception` |
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
- **L9** (2026-11-09) El commit `c76ca60` (PR1) se evaluó con `review assess` como riesgo `high` por `security-scan.yml`, `release.yml` y `.pre-commit-config.yaml`. La revisión nativa queda pendiente hasta que el árbol de trabajo deje de cambiar (los writers siguen activos).
- **L10** (2026-11-09) T2 entregada por el writer y commit `8ea305b`.
  - Verificación reportada: ruff, bandit e import-linter OK; 26 tests en verde con 92,39 % de cobertura, usando MySQL 8.4 temporal; `docker build` OK con Python 3.12.
  - Spot check del padre: `lint-imports` OK. `pytest tests/unitarios` da 21 en verde y 1 fallo por falta de MySQL local (test CSP sobre `/salud`), como reportó el writer.
  - Desviaciones: `main.py` en la raíz del paquete, igual que en la referencia; se elimina `python-dateutil`.
  - Advisory para el usuario: el manejador 500 devuelve el traceback en la respuesta, copiado tal cual de la referencia.
  - Slicing: PR2 no tiene un corte cohesivo menor a 400 líneas (`main.py` cablea observabilidad, middleware y manejadores), así que se recomienda `size:exception`. Unas 420 líneas son boilerplate de configuración: alembic, pyproject, CI.
  - Se añaden `.hypothesis` e `.import_linter_cache` a `.gitignore`.
- **L11** (2026-11-09) El usuario renombró `/mnt/c/Users/pw-dmartinez.pinero/AGENTS.md` a `AGENTS.md.bak`: contenía instrucciones SDD obsoletas que se cargaban en cada sesión.
- **L12** (2026-11-09) T3 entregada por el writer.
  - Verificación reportada: lint, prettier y type-check OK; 27 tests unitarios en verde; build OK.
  - E2E: 14/14 en verde, pero contra Chromium 1243 con una configuración temporal. Playwright 1.61 espera 1254, que no está instalado; es un problema del entorno, se resuelve con `pnpm exec playwright install chromium`.
  - RED observado en las specs del router y de `BarraLateral`.
  - Desviaciones: se eliminan driver.js, exceljs, jspdf y marked; se quitan el tour y `ModalChangelog`; el menú se genera a partir de una lista de grupos.
  - Spot check del padre: `pnpm test:unit run` da 27/27.
  - Línea de riesgo del writer: item 5 (dependencias, lockfile y Dockerfile/nginx).
- **L13** (2026-11-09) Commits de la cadena:
  - PR1 `aba80f2`
  - PR2 `ab51390`
  - PR3 `e894f17`
  - PR4 `e271170`
  - PR5 `ae7e471`
  - Con esto quedan hechas todas las tareas.
  - Pendiente: la revisión nativa de los commits con riesgo `high`. Push y PRs quedan a decisión del usuario.
- **L14** (2026-11-09) Revisión nativa de PR1 (`c76ca60`).
  - Riesgo `high`; el usuario respondió "Revisar este cambio" (granted).
  - START terminó en `stop` con `lens_context_budget_exceeded`: la evidencia del candidato (6 210 líneas, 5 713 de ellas de `package-lock.json`) supera el presupuesto de contexto del revisor. No se creó autoridad de revisión.
  - Continuación: reducir el alcance y abrir una transacción nueva, o `gentle-ai review mode disable --scope clone`.
  - PR2 y PR3 tienen el mismo problema por `uv.lock`, `pnpm-lock.yaml` y su tamaño.
  - Pendiente de la decisión del usuario.
- **L15** (2026-11-09) El usuario eligió desactivar la revisión nativa en este repo ("la 2").
  - `gentle-ai review mode disable --scope clone` falló en `/mnt/c`: drvfs está montado sin `metadata` y `chmod 700` no tiene efecto.
- **L16** (2026-11-09) El usuario eligió mover el proyecto a WSL ("1.").
  - Copiado con rsync a `~/proyectos/gestor-tareas-y-conocimiento-personal`, sin cachés ni dependencias instaladas. Permisos normalizados a 644/755; `git status` limpio salvo este documento.
  - `review mode` queda en `off (decided by clone_local)`: la entrega sigue la política ordinaria del repositorio (`disabled/unmanaged`). Reactivar con `gentle-ai review mode enable --scope clone` para las features de dominio.
  - Verificación: backend `ruff` e `import-linter` OK; frontend `pnpm test:unit run` 27/27 en 4,8 s (antes 79,5 s en `/mnt/c`).
  - La copia original en `/mnt/c` se conserva hasta que el usuario decida borrarla.
- **L17** (2026-11-09) Feature cerrada. Todas las tareas hechas.
  - Siguientes pasos, a decisión del usuario: crear el repositorio en GitHub, hacer push de los cortes PR1–PR5 y abrir los PRs encadenados a `main` (se recomienda `size:exception` para PR2 y PR3), e instalar Chromium 1254 para Playwright.
- **L18** (2026-11-09) Repositorio privado creado en GitHub, con los PRs #1–#5 encadenados (`stacked-to-main`) y la etiqueta `size:exception` en #2 y #3.
  - Los workflows de `pull_request` no se dispararon hasta que el repositorio tuvo un workflow registrado. Se resolvió con una rama de prueba temporal, ya borrada, y reabriendo los PRs.
  - Fallo en CI: `gitleaks` devolvía `403 Resource not accessible by integration` al listar los commits del PR. En un repositorio privado hace falta `pull-requests: read`.
  - Usuario: "la 1". El arreglo se integró en el commit de PR1 y la cadena se rebaseó con force-push. Los hashes de L13 están actualizados; L9, L10 y L14 conservan los hashes anteriores al rebase.
