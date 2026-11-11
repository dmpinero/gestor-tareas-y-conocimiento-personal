# subtareas-workflow-borrar-tareas

Objetivo: los pasos del workflow se crean como subtareas, las subtareas tienen comentarios, las tareas se pueden borrar con confirmación y el alta se hace en una ventana modal.
Rama: `feature/subtareas-workflow-borrar-tareas` (desde `main` v1.21.1) · Entrega: `stacked-to-main` (PR backend → PR frontend) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "Cuando se cree una tarea a partir de una tarea que tiene un worflow, quiero que lo que se creen automáticamente sean subtareas, y que se comporten como tal."
  - Al crear una tarea de tipo Oportunidad, cada paso del workflow de Ajustes se crea como una subtarea (mismo orden, sin persona ni prioridad, sin resolver). Desaparecen los "pasos de la tarea" como concepto aparte (tabla `pasos_tarea`, campo `pasos_oportunidad` y su endpoint de alternar). El workflow de Ajustes (plantilla) no cambia.
  - El indicador "Oportunidad · x/n" pasa a contar subtareas resueltas / total (supuesto).
- **S2** Conversión de datos (decisión del usuario: "convierte"): los pasos que ya tienen las tareas existentes pasan a ser subtareas, en orden de `numero`, con `resuelta = hecho`. Backup de la base local antes de migrar y verificación de que no se pierde ninguno. La migración inversa recrea la tabla vacía (supuesto: la conversión no es reversible en datos; el backup la cubre).
- **S3** "Además quiero que las subtareas tengan la posibilidad de incluir comentarios." Mismo comportamiento que los comentarios de la tarea: 1–500 caracteres, historial con fecha y hora, editar y borrar con confirmación, marca "(editado)". Se borran con la subtarea.
- **S4** "También quiero poder eliminar las tareas, con un mensaje de confirmación previo." Papelera en la lista y en el detalle; confirmación "¿Eliminar la tarea X?"; se borran también sus subtareas y comentarios.
- **S5** "Por último, quiero que al crear la tarea en vez de aparecer en la barra lateral, que aparezca en una ventana modal como la del detalle." Solo el alta; la edición sigue en el panel lateral.
- **S6** Contrato API (supuesto de diseño):
  - `DELETE /api/v1/tareas/{id}` → 204; 404 si no existe.
  - `GET/POST /api/v1/tareas/{id}/subtareas/{id_subtarea}/comentarios`, `PUT/DELETE .../comentarios/{id_comentario}`: mismos cuerpos y respuestas que los comentarios de la tarea (`{id, texto, creado, editado}`), 404 si la tarea, la subtarea o el comentario no existen o no pertenecen.
  - Cada subtarea de la respuesta de tarea gana `comentarios: int` (número de comentarios). Se quita `pasos_oportunidad` de la respuesta y la ruta `PATCH /tareas/{id}/pasos/{id_paso}` (cambio de contrato pedido).

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1, S2, S3, S4, S6 (backend + migración con conversión) | delegada (writer A, paralelo) | pendiente | — |
| T2 | S1, S3, S4, S5 (frontend) | delegada (writer B, paralelo) | pendiente | — |
| T3 | S1–S6 (e2e contra pila aislada) | inline | pendiente | — |
| T4 | S1–S6 (verificador: migración con datos, contrato; items 1 y 3) | delegada (verificador) | pendiente | — |

## Log

- **L1** (2026-11-11) Pedido original del usuario:
  > Cuando se cree una tarea a partir de una tarea que tiene un worflow, quiero que lo que se creen automáticamente sean subtareas, y que se comporten como tal. Además quiero que las subtareas tengan la posibilidad de incluir comentarios. También quiero poder eliminar las tareas, con un mensaje de confirmación previo. Por último, quiero que al crear la tarea en vez de aparecer en la barra lateral, que aparezca en una ventana modal como la del detalle.
- **L2** (2026-11-11) La base local tiene 5 oportunidades con 8 pasos. Pregunta: ¿convertir los pasos existentes o solo las tareas nuevas? Respuesta: "convierte".
