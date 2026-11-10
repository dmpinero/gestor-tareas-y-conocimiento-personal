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
| T1 | S3–S5 (backend: PUT subtarea, PUT/DELETE comentario, columna `editado` con migración, tests) | delegada (writer A, paralelo) | pendiente | — |
| T2 | S2–S4 (frontend: edición en línea y confirmaciones en `SubtareasTarea` y `ComentariosTarea`, specs) | delegada (writer B, paralelo) | pendiente | — |
| T3 | S1–S5 (e2e contra pila aislada) | inline | pendiente | — |
| T4 | S1–S5 (verificador independiente: migración y contrato, items 1 y 3) | delegada (verificador) | pendiente | — |

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > quiero poder editar y borrar tanto las subtareas como los comentarios, pidiendo confirmación previa
