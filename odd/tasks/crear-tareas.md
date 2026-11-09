# crear-tareas

Objetivo: permitir crear tareas desde la opción Tareas mediante un panel lateral derecho y verlas en un listado simple.
Rama: `feature/crear-tareas` · Entrega: `ask-on-risk` → cadena `stacked-to-main` (preferencia del scaffold) · Tests: `uv run pytest` (backend), `pnpm test:unit run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Crear desde Tareas: "Dentro de la opción de Tareas quiero poder crear tareas". Un botón "Crear tarea" en `VistaTareas` (ruta `/tareas`).
- **S2** Panel lateral: "cuando la cree abre un menú lateral derecho (igual que lo hacías en la aplicación https://github.com/dmpinero/gestor-gastos-personal". Se replica el patrón de `VistaCuentas.vue` de la referencia: `Sheet` de shadcn con `side="right"`, formulario en línea, botones "Guardar" (`success`) y "Cancelar" (`destructive`), error en `<p role="alert">`; al guardar con éxito el panel se cierra y la tarea aparece en el listado.
- **S3** Nombre: "Nombre: Obligatorio: Máximo 200 caracteres". Backend: `Field(min_length=1, max_length=200)`; frontend: `required` y `maxlength="200"`.
- **S4** Prioridad: "Prioridad: Campo de tipo numérico. Irá desde el 1 (más prioritario) hasta el 5. Campo opcional". Backend: `int | None`, `ge=1`, `le=5`; columna nullable con `CheckConstraint` 1–5. Frontend: `<input type="number" min="1" max="5">` sin `required`; vacío se envía como `null`.
- **S5** Descripción: "Descripción: Obligatorio: Máximo 500 caracteres. Campo tipo textarea." Backend: `Field(min_length=1, max_length=500)`; frontend: componente `Textarea` con `required` y `maxlength="500"`.
- **S6** Listado: "incluye listado simple de tareas". Endpoint `GET /api/v1/tareas` y tabla en `VistaTareas` con columnas Nombre, Prioridad y Descripción; prioridad vacía se muestra como "—". Sin tareas se muestra "Todavía no hay tareas.".
- **S7** Contrato API (fijado para que backend y frontend se construyan en paralelo):
  - `POST /api/v1/tareas` cuerpo `{"nombre": str, "prioridad": int | null, "descripcion": str}` → `201` con `{"id": int, "nombre": str, "prioridad": int | null, "descripcion": str}`; datos inválidos → `422`.
  - `GET /api/v1/tareas` → `200` con lista de ese mismo objeto, ordenada por `id` ascendente.
- **Supuestos** (no pedidos; se marcan como supuestos): sin edición ni borrado; nombres duplicados permitidos; un nombre o descripción solo con espacios se rechaza (se recorta antes de validar); los mensajes de validación de Pydantic se dejan como vienen.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S3–S7 (backend: dominio, casos de uso crear/listar, puerto, adaptador, modelo, migración, esquemas, enrutador, tests unitarios, integración y BDD) | delegada (writer A, paralelo con T2) | hecha | `2f406fa` |
| T2 | S1–S6 (frontend: componentes `input`/`label`/`textarea`, `api/tipos.ts`, store `tareas`, `VistaTareas` con panel y tabla, specs Vitest) | delegada (writer B, paralelo con T1) | hecha | `d33662e` |
| T3 | S1–S7 (seam: e2e Playwright `e2e/tareas.spec.ts`, suite completa, docker compose) | inline | hecha | `d33662e` |
| T4 | S1–S7 (verificador independiente por la migración, item 1) | delegada (verificador) | hecha (1 blocker corregido) | `d33662e` |

Evidencia de ruta: T1 y T2 son unidades independientes con superficies disjuntas (`backend/` y `frontend/src`), cada una de varios cientos de líneas, lanzadas juntas → disparador de escritura (a) paralelismo. El contrato S7 las desacopla. T1 incluye una migración → riesgo item 1 → commit propio y verificador (T4).

Previsión: ~1 100 líneas escritas (backend ~650, frontend ~450) → por encima de 400; se aplica la cadena `stacked-to-main`: PR1 = T1, PR2 = T2 + T3.

## Log

- **L1** (2026-11-09) Pedido original del usuario:
  > - Dentro de la opción de Tareas quiero poder crear tareas, cuando la cree abre un menú lateral derecho (igual que lo hacías en la aplicación https://github.com/dmpinero/gestor-gastos-personal. Cada tarea tiene los siguientes campos
  >     - Nombre: Obligatorio: Máximo 200 caracteres
  >     - Prioridad: Campo de tipo numérico. Irá desde el 1 (más prioritario) hasta el 5. Campo opcional
  >     - Descripción: Obligatorio: Máximo 500 caracteres. Campo tipo textarea.
- **L2** (2026-11-09) Mapeo: la ruta `/tareas`, la entrada de la barra lateral, `ui/sheet`, las variantes `success`/`destructive` de `Button`, Pinia y `clienteApi.crear` ya existen. Faltan `Input`, `Label`, `Textarea`, `src/stores`, `src/api/tipos.ts` y todo el dominio backend. La referencia no usa librería de formularios ni toasts.
- **L3** (2026-11-09) Pregunta: ¿listado o solo creación? Usuario: "incluye listado simple de tareas".
- **L4** (2026-11-09) T1 entregada por el writer A. Verificación reportada: ruff, lint-imports y bandit OK; 65 tests con 96,28 % de cobertura sobre MySQL 8.4 temporal; `alembic upgrade`/`downgrade`/`upgrade` OK. El padre actualizó `test_aplicacion.py`, que fijaba como única ruta `/api/v1/salud`.
  - RED observado en casos de uso, esquemas y BDD. En MySQL una violación del CHECK llega como `OperationalError` (3819), no como `IntegrityError`.
- **L5** (2026-11-09) T2 entregada por el writer B: 38 tests unitarios, type-check, lint y build OK. RED observado en el store y la vista. Aviso de reka-ui por la falta de `SheetDescription`, igual que en la referencia.
- **L6** (2026-11-09) T3 inline: `e2e/tareas.spec.ts` (crear con y sin prioridad). Pila `docker compose` reconstruida: la migración `3f1c2a9d7b10` se aplica al arrancar; Playwright 16/16.
- **L7** (2026-11-09) T4, verificador independiente: S1–S7 y supuestos en verde; `alembic check` sin deriva; `/api/v1/salud` idéntico a la base.
  - Blocker B1: con un nombre válido de 130 o más caracteres la tabla desbordaba en horizontal y axe marcaba `scrollable-region-focusable` en `/tareas`. Corregido con `whitespace-normal [overflow-wrap:anywhere]` en las celdas de nombre y descripción, con un test de regresión e2e de longitud máxima (RED observado, después 17/17). Se integró en el commit del frontend.
  - Advisories, sin cambios: Pydantic en modo laxo acepta `true`, `"2"` y `2.0` como prioridad; los fixtures de integración y BDD vacían `tareas` en la base de `URL_BASE_DATOS`; el e2e deja filas en la base local; si falla la carga inicial se ven a la vez la alerta y "Todavía no hay tareas.".
- **L8** (2026-11-09) Rama rebasada sobre `main` (`5204a0d`). Entrega `stacked-to-main`: PR1 = `2f406fa` (T1), PR2 = `d33662e` y este cierre (T2–T4).
