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
| T1 | S1, S2, S3, S4, S6 (backend + migración con conversión) | delegada (writer A, paralelo) | hecha | `aa1f9b1`, corrección B1 |
| T2 | S1, S3, S4, S5 (frontend) | delegada (writer B, paralelo) | hecha | `323ec32`, corrección B2 |
| T3 | S1–S6 (e2e contra pila aislada) | inline | hecha | `323ec32` |
| T4 | S1–S6 (verificador: migración con datos, contrato; items 1 y 3) | delegada (verificador) | hecha; 2 blockers corregidos | — |

## Log

- **L1** (2026-11-11) Pedido original del usuario:
  > Cuando se cree una tarea a partir de una tarea que tiene un worflow, quiero que lo que se creen automáticamente sean subtareas, y que se comporten como tal. Además quiero que las subtareas tengan la posibilidad de incluir comentarios. También quiero poder eliminar las tareas, con un mensaje de confirmación previo. Por último, quiero que al crear la tarea en vez de aparecer en la barra lateral, que aparezca en una ventana modal como la del detalle.
- **L2** (2026-11-11) La base local tiene 5 oportunidades con 8 pasos. Pregunta: ¿convertir los pasos existentes o solo las tareas nuevas? Respuesta: "convierte".
- **L3** (2026-11-11) T1/T2: backend 684 tests (98,73 %), contrato 10/10, migración `b7e4c1d9f2a6` probada con datos; frontend 425 tests. T3: e2e 39/39 dos veces.
- **L4** (2026-11-11) T4, verificador: S1, S2 y S5 en verde; migración sin pérdidas (9 pasos → 9 subtareas, resto de tablas con hash idéntico, downgrade con esquema igual a la base). Blockers: **B1** `PUT /tareas/{id}` o `PATCH /tareas/{id}/completada` a la vez que `DELETE` daba 500 (lectura sin bloqueo); **B2** axe `label-content-name-mismatch` en el botón de comentarios de una subtarea con comentarios. Advisory corregido: nombres accesibles repetidos en la edición de comentarios de subtarea. Otros advisories (Escape en la caja de comentarios cierra el detalle, como en los de la tarea; cambiar el tipo conserva las subtareas) se aceptan.
- **L5** (2026-11-11) Corrección única: B1 lee la tarea con `FOR UPDATE` y responde 404 (test de regresión RED → GREEN; 80 carreras contra la API sin 5xx); B2 el número visible forma parte del nombre ("Comentarios de la subtarea X: 2") y e2e de axe en claro y oscuro con el panel abierto. Backend 686 tests (98,74 %), contrato 10/10, frontend 425, e2e 41/41 dos veces sobre base limpia (una corrida previa sobre la base llena por el contrato falló por el entorno).
