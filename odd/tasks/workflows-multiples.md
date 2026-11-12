# workflows-multiples

Objetivo: varios workflows con nombre en Ajustes y un campo "Workflow" en la tarea que añade sus pasos como subtareas.
Rama: `feature/workflows-multiples` (desde `main` v1.27.0) · Entrega: `stacked-to-main` (PR backend → PR frontend; el backend quita la ruta actual del workflow, así que si el PR del backend rompe el frontend de `main` se fusiona el PR superior) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "quiero que en los ajustes me permita generar distintos workflows, con un nombre, y poder seleccionar los pasos de cada workflow, como se hace ahora con el workflow existente"
  - Ajustes → "Workflows": crear, renombrar y borrar workflows (nombre 1–50, único sin distinguir mayúsculas); por workflow, añadir, renombrar, borrar y ordenar (arrastrar y Subir/Bajar) sus pasos, igual que hoy. (supuesto: mismas reglas de nombre de paso que hoy)
  - El workflow actual pasa a ser "Workflow Oportunidades" con sus mismos pasos y orden (migración con datos; backup antes de migrar la base local).
- **S2** Decisión del usuario (L3): "sí quiero campo "Worflow" en la tarea".
  - Campo opcional "Workflow" en el alta y la edición. Al crear con un workflow, sus pasos se añaden como subtareas en orden (sin persona ni prioridad, sin resolver). Al editar y elegir un workflow distinto del que tenía, sus pasos se añaden como subtareas nuevas y se conservan las existentes. Quitar el workflow o dejar el mismo no toca las subtareas. (supuestos)
  - Resuelve L2: "he editado una subtarea, y al seleccionar que es de tipo oportunidad no me ha creado las subtareas por defecto".
  - El tipo Oportunidad ya no copia pasos por sí mismo (evita duplicados); en el alta, al elegir el tipo Oportunidad con el campo Workflow vacío, el formulario preselecciona "Workflow Oportunidades" si existe. (supuesto)
  - Borrar un workflow deja sus tareas sin workflow y con sus subtareas. (supuesto)
- **S3** Contrato API (supuesto de diseño):
  - `GET/POST /api/v1/workflows`, `PUT/DELETE /api/v1/workflows/{id}`; cada workflow `{id, nombre, pasos: [{id, numero, nombre}]}`.
  - Pasos: `POST /api/v1/workflows/{id}/pasos` `{nombre}` (al final), `PUT .../pasos/{id_paso}` `{nombre}`, `DELETE .../pasos/{id_paso}`, `PUT /api/v1/workflows/{id}/orden` `{ids}`; mismas respuestas y códigos que hoy el workflow de oportunidades, que se retira (`/api/v1/workflow-oportunidades/...`).
  - Tarea: cuerpo de alta y edición con `workflow_id: int | null` opcional (en la edición, ausente = null, como el grupo de estados); respuesta con `workflow: {id, nombre} | null`. 422 si el workflow no existe.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S3 (backend + migración con datos) | delegada (writer A, paralelo) | pendiente | — |
| T2 | S1, S2 (frontend: Ajustes, formulario, detalle) | delegada (writer B, paralelo) | pendiente | — |
| T3 | S1–S3 (e2e contra pila aislada) | inline | pendiente | — |
| T4 | S1–S3 (verificador: migración con datos, contrato, concurrencia; items 1, 3 y 4) | delegada (verificador) | pendiente | — |

## Log

- **L1** (2026-11-12) Pedido del usuario:
  > quiero que en los ajustes me permita generar distintos workflows, con un nombre, y poder seleccionar los pasos de cada workflow, como se hace ahora con el workflow existente
- **L2** (2026-11-12) Problema reportado por el usuario (comportamiento previsto hasta ahora: los pasos solo se copiaban al crear una oportunidad):
  > he editado una subtarea, y al seleccionar que es de tipo oportunidad no me ha creado las subtareas por defecto
- **L3** (2026-11-12) Pregunta: ¿campo "Workflow" en la tarea (recomendado) o un workflow asociado a cada tipo? Respuesta:
  > sí quiero campo "Worflow" en la tarea
