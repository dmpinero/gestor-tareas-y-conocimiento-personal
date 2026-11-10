# subtareas-comentarios

Objetivo: subtareas dentro de cada tarea (desde el detalle, parte izquierda) y un histórico de comentarios por tarea (parte derecha del detalle), según la imagen de referencia del usuario.
Rama: `feature/subtareas-comentarios` (desde `main` v1.17.0) · Entrega: `stacked-to-main` (PR backend → PR frontend) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** Subtareas: "Quiero que implementes la posiblidad de crear subtareas dentro de una tarea, para ello se podrá hacer desde el detalle de la tarea, tal y como está en la imagen." Propuesta aceptada ("sí, hazlo así"):
  1. Sección "Subtareas · N sin resolver" en la parte izquierda del detalle.
  2. Campos: Nombre (obligatorio, 1–200 caracteres tras recortar), Persona asignada (opcional, una sola, del catálogo de personas, que se amplía al vuelo), Prioridad (opcional, 1–5).
  3. Un círculo marca la subtarea como resuelta (tachada) y al pulsarlo de nuevo se reabre.
  4. Fila "Añadir subtarea" al final con Guardar y Cancelar; cada subtarea se puede eliminar.
  5. Las subtareas viven solo dentro de su tarea (no aparecen en la tabla principal).
- **S2** Comentarios: "También quiero poder tener un histórico de comentarios en cada tarea, indicando un texto (500 caracteres) como se ve en la parte derecha de la imagen. Esto hazlo en la parte derecha del detalle". Propuesta aceptada:
  1. Historial en orden cronológico agrupado por día con separadores ("miércoles, 1 de abril"); cada comentario muestra la hora (HH:MM) y el texto respetando saltos de línea.
  2. Campo "Escribe un comentario" (1–500 caracteres tras recortar) y botón de enviar; también Ctrl+Enter.
  3. Sin autor (la app no tiene usuarios); la fecha y hora las pone el servidor.
  4. Los comentarios no se editan ni se borran.
- **S3** Detalle en dos columnas: izquierda, los campos de la tarea y las subtareas; derecha, los comentarios (en pantallas estrechas, una debajo de otra).
- **S4** Contrato API (supuesto de diseño):
  - Las respuestas de tarea incluyen `subtareas: [{id, nombre, asignado: str|null, prioridad: int|null, resuelta: bool}]` por orden de alta.
  - `POST /api/v1/tareas/{id}/subtareas` `{nombre, asignado?, prioridad?}` → 201 con la tarea completa (si `asignado` no existe en el catálogo de personas, se crea, como en `asignados`).
  - `PATCH /api/v1/tareas/{id}/subtareas/{id_subtarea}/resuelta` `{resuelta: bool}` (booleano estricto) → 200 con la tarea; `DELETE /api/v1/tareas/{id}/subtareas/{id_subtarea}` → 200 con la tarea. 404 si la tarea o la subtarea no existen o la subtarea es de otra tarea.
  - `GET /api/v1/tareas/{id}/comentarios` → 200 `[{id, texto, creado}]` en orden cronológico; `POST .../comentarios` `{texto}` → 201 con el comentario. `creado` en UTC ISO 8601 con `Z` (el frontend lo muestra en hora local). 404 si la tarea no existe.
  - Borrar una tarea borra sus subtareas y comentarios (ON DELETE CASCADE).

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1, S2, S4 (backend: subtareas y comentarios, dos migraciones encadenadas, endpoints, tests) | delegada (writer A, paralelo) | pendiente | — |
| T2 | S1 (frontend: componente `SubtareasTarea`, tipos, acciones del almacén, specs) | delegada (writer B, paralelo) | pendiente | — |
| T3 | S2 (frontend: componente `ComentariosTarea`, specs) | delegada (writer C, paralelo) | pendiente | — |
| T4 | S3 (integración en `DetalleTarea` en dos columnas) y e2e contra pila aislada | inline | pendiente | — |
| T5 | S1–S4 (verificador independiente: migraciones y contrato, items 1 y 3) | delegada (verificador) | pendiente | — |

## Log

- **L1** (2026-11-10) Pedido original del usuario (con imagen de referencia):
  > Quiero que implementes la posiblidad de crear subtareas dentro de una tarea, para ello se podrá hacer desde el detalle de la tarea, tal y como está en la imagen. También quiero poder tener un histórico de comentarios en cada tarea, indicando un texto (500 caracteres) como se ve en la parte derecha de la imagen. Esto hazlo en la parte derecha del detalle
- **L2** (2026-11-10) Propuesta de diseño (campos de subtarea, comentarios sin autor y sin edición) → usuario: "sí, hazlo así".
