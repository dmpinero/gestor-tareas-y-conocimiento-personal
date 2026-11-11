# editar-borrar-subtareas-comentarios

Objetivo: poder editar y borrar subtareas y comentarios desde el detalle de la tarea, pidiendo confirmación previa.
Rama: `feature/editar-borrar-subtareas-comentarios` (desde `main` v1.19.0) · Entrega: `stacked-to-main` (PR backend → PR frontend) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "quiero poder editar y borrar tanto las subtareas como los comentarios, pidiendo confirmación previa". Cambia la decisión anterior de que los comentarios no se editan ni se borran (`odd/tasks/subtareas-comentarios.md`, S2.4).
- **S2** Confirmación (supuesto: se aplica literalmente a las dos acciones): borrar pide "¿Eliminar …?" con Eliminar/Cancelar; editar abre el elemento en modo edición y al guardar pide "¿Guardar los cambios?" con Guardar/Cancelar. Confirmación en línea dentro del detalle (no un diálogo anidado), Escape cancela sin cerrar el detalle y el foco vuelve a un sitio razonable.
- **S3** Subtareas: se editan nombre, persona asignada y prioridad con las mismas validaciones que el alta (nombre 1–200, persona 1–100 del catálogo que se amplía al vuelo, prioridad 1–5 o vacía). El borrado ya existía con confirmación; se mantiene.
- **S4** Comentarios: se edita el texto (1–500, con saltos de línea); conserva su `creado` y se marca como "(editado)" (supuesto: nuevo campo `editado`, UTC con `Z`, null si nunca se editó); se pueden borrar.
- **S5** Contrato API (supuesto de diseño):
  - `PUT /api/v1/tareas/{id}/subtareas/{id_subtarea}` `{nombre, asignado?, prioridad?}` → 200 con la tarea completa (reemplazo completo: `asignado`/`prioridad` ausentes o null los vacían).
  - `PUT /api/v1/tareas/{id}/comentarios/{id_comentario}` `{texto}` → 200 `{id, texto, creado, editado}`; `DELETE` → 204. La respuesta de listar y crear incluye `editado` (null).
  - 404 si la tarea o el elemento no existen o pertenecen a otra tarea; 422 en datos inválidos sin cambios en la base.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S3–S5 (backend: PUT subtarea, PUT/DELETE comentario, columna `editado` con migración, tests) | delegada (writer A, paralelo) | hecha | `b2ac070` |
| T2 | S2–S4 (frontend: edición en línea y confirmaciones en `SubtareasTarea` y `ComentariosTarea`, specs) | delegada (writer B, paralelo) | hecha | `b68e1d5` |
| T3 | S1–S5 (e2e contra pila aislada) | inline | hecha | `b68e1d5` |
| T4 | S1–S5 (verificador independiente: migración y contrato, items 1 y 3) | delegada (verificador) | hecha (sin blockers) | — |

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > quiero poder editar y borrar tanto las subtareas como los comentarios, pidiendo confirmación previa
- **L2** (2026-11-11) T1 (writer A, retomado tras agotarse el límite de uso): `PUT` de subtarea (reemplazo completo, conserva `resuelta`), `PUT`/`DELETE` de comentario y columna `editado` (migración `a3d9f6b2c8e1`). 630 tests, 98,60 %, contrato 10/10. T2 (writer B): edición en línea y confirmaciones en `SubtareasTarea` y `ComentariosTarea`, marca "(editado)" con la fecha para lectores de pantalla; 403 tests. T3: e2e; dos fallos del propio test (texto completo de la marca y un localizador de texto ambiguo durante la transición) corregidos; Playwright 36/36 dos veces.
- **L3** (2026-11-11) T4, verificador: S1–S5 en verde, sin blockers. Migración con hash y esquema idénticos; 47 sondas de API; carreras edición/borrado sin 5xx; OpenAPI solo con añadidos; axe sin violaciones en claro, oscuro y 390×844. Advisories: en móvil la tabla de subtareas desborda más (ya desbordaba en la base) y en modo edición los campos quedan parcialmente cortados; `POST` en la ruta nueva de un comentario da 405.
