# tipo-tarea

Objetivo: añadir el campo Tipo de tarea (por ahora "Oportunidad", con campos propios) y un detalle de la tarea en una modal; Editar pasa a ser un icono.
Rama: `feature/tipo-tarea` (encadenada sobre `feature/filtros-tareas`) · Entrega: `stacked-to-main` (PR filtros → PR backend → PR frontend) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** Tipo de tarea: "Quiero un nuevo campo Tipo de tarea que contenga distintos tipos de valores". Por ahora un único valor, "Oportunidad". Usuario: "habrá nuevos tipos de valores con campos propios, pero aún no los tengo decidido ¿los podemos poner más adelante?" → diseño extensible (cada tipo con sus campos en su propia tabla y su propio bloque de formulario y detalle).
  - Usuario: "1." → el tipo es **opcional**; sin tipo se muestra "—"; las tareas existentes quedan sin tipo.
  - API: `tipo: "oportunidad" | null` (valores en minúsculas como identificador; etiqueta visible "Oportunidad").
- **S2** Oportunidad: "Oportunidad: Si se escoge esta opción se deberán rellenar nuevos campos."
  - "Código de la oportunidad (10 caracteres). Obligatorio" → supuesto: máximo 10 caracteres, recortado, no vacío, no único.
  - "Descripción de la oportunidad (200 caracteres). Opcional"
  - "Observaciones (5000 caracteres, en un textarea). Opcional"
  - Tabla `oportunidades` 1:1 con `tareas` (`tarea_id` PK y FK con `ON DELETE CASCADE`).
  - API: `oportunidad: {codigo, descripcion, observaciones} | null`; obligatorio si `tipo = "oportunidad"` y prohibido (422) si `tipo` es `null`. Supuesto: al cambiar una tarea de Oportunidad a sin tipo, sus datos de oportunidad se borran.
  - Los textos siguen el mismo criterio que el resto (espacios de ECMA-262, `pattern: "\S"` en el contrato para los obligatorios).
- **S3** Listado: "El campo tipo será visualizable en el listado de tareas, el resto no."
  - Columna "Tipo" (ordenable, exportable y filtrable con `FiltroMultiple` incluyendo "Sin tipo", como el resto de columnas: supuesto). Los campos de la oportunidad no aparecen en la tabla ni en la exportación.
- **S4** Detalle: "Todos los campos de una tarea serán visibles en un icono Detalle, junto al botón Editar, que pasará a ser un icono. Al pulsar en detalle toda la info se abrirá en una modal que abarcará el 90% del ancho y del alto del viewport."
  - Botón Editar como icono (lápiz) con nombre accesible "Editar tarea <nombre>" (se mantiene) y botón Detalle como icono (ojo) con nombre accesible "Ver detalle de la tarea <nombre>"; ambos con `title`.
  - Modal (`Dialog` de reka-ui) de 90 vw × 90 vh con scroll interno, título con el nombre de la tarea y todos los campos (incluidos los de la oportunidad si los hay), botón "Cerrar" y cierre con Escape.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S2 (backend: columna `tipo`, tabla `oportunidades`, migración, esquemas, validación cruzada, tests) | delegada (writer A, paralelo) | hecha | `3f6c04e` |
| T2 | S1–S4 (frontend: tipos, store, formulario con bloque de Oportunidad, columna y filtro Tipo, iconos Editar/Detalle, modal de detalle, specs) | delegada (writer B, paralelo) | hecha | `7371034` |
| T3 | S1–S4 (e2e contra pila aislada, suite) | inline | hecha | `7371034` |
| T4 | S1–S4 (verificador independiente: migración y contrato, items 1 y 3) | delegada (verificador) | hecha (sin blockers) | — |

Evidencia de ruta: T1 y T2 son unidades independientes con superficies disjuntas (`backend/` y `frontend/src`) y el contrato fijado en S1–S2. Riesgo: migración nueva (item 1) y ampliación del contrato público (item 3, pedida) → verificador.

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > - Crear y editar tarea (tipo de tarea)
  >     - Quiero un nuevo campo Tipo de tarea que contenga distintos tipos de valores:
  >         - Oportunidad: Si se escoge esta opción se deberán rellenar nuevos campos.
  >             - Código de la oportunidad (10 caracteres). Obligatorio
  >             - Descripción de la oportunidad (200 caracteres). Opcional
  >             - Observaciones (5000 caracteres, en un textarea). Opcional
  >             - El campo tipo será visualizable en el listado de tareas, el resto no.
  >             - Todos los campos de una tarea serán visibles en un icono Detalle, junto al botón Editar, que pasará a ser un icono. Al pulsar en detalle toda la info se abrirá en una modal que abarcará el 90% del ancho y del alto del viewport.
- **L2** (2026-11-10) Preguntas: ¿otros tipos? → "habrá nuevos tipos de valores con campos propios, pero aún no los tengo decidido ¿los podemos poner más adelante?"; ¿tipo opcional o "General" por defecto? → "1." (opcional).
- **L3** (2026-11-10) T1 (backend): `TipoTarea` (`StrEnum`), tabla `oportunidades` 1:1, migración `e5b8d1f3a6c2` (el downgrade quita el CHECK antes que la columna); la regla tipo/oportunidad se publica como `anyOf` a nivel de modelo, así schemathesis solo genera combinaciones válidas. 291 tests, 97,50 %, contrato 10/10. La base no impide una fila de `oportunidades` en una tarea sin tipo (un CHECK de MySQL no mira otra tabla); lo aplica la API.
- **L4** (2026-11-10) T2 (frontend): `ui/dialog` (prop `sinAspa`), `DetalleTarea`, selector de tipo con `<fieldset>` Oportunidad, columna y filtro Tipo, iconos Editar/Detalle. `FiltroMultiple` gana la prop `genero` ("Todos los tipos", "Ningún tipo"; RED observado). Vitest 205/205. T3 inline: e2e de oportunidad y detalle; dos fallos del propio test (código contenido en el nombre; medida durante la animación de entrada) corregidos; Playwright 24/24 dos veces contra una pila aislada.
- **L5** (2026-11-10) T4, verificador (cubre también `filtros-tareas.md`): todo en verde, sin blockers. Migración: hash de datos idéntico y `mysqldump` idéntico tras upgrade/downgrade; OpenAPI frente a `main` solo con añadidos; axe sin violaciones con filtros, panel en modo Oportunidad y detalle abiertos, en claro y oscuro. Advisories: componente `TipoTarea` huérfano en OpenAPI con el docstring del dominio; "Seleccionar todas" fijo en `FiltroMultiple`; mensaje de Pydantic en inglés para un código vacío (como en la base); `maxlength` del navegador cuenta unidades UTF-16 (emoji).
