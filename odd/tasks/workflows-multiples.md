# workflows-multiples

Objetivo: varios workflows con nombre en Ajustes y un campo "Workflow" en la tarea que añade sus pasos como subtareas.
Rama: `feature/workflows-multiples` (desde `main` v1.27.0) · Entrega: `stacked-to-main` (PR backend → PR frontend; el backend quita la ruta actual del workflow, así que si el PR del backend rompe el frontend de `main` se fusiona el PR superior) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "quiero que en los ajustes me permita generar distintos workflows, con un nombre, y poder seleccionar los pasos de cada workflow, como se hace ahora con el workflow existente"
  - Ajustes → "Workflows": crear, renombrar y borrar workflows (nombre 1–50, único sin distinguir mayúsculas); por workflow, añadir, renombrar, borrar y ordenar (arrastrar y Subir/Bajar) sus pasos, igual que hoy. (supuesto: mismas reglas de nombre de paso que hoy)
  - El workflow actual pasa a ser "Workflow Oportunidades" con sus mismos pasos y orden (migración con datos; backup antes de migrar la base local).
  - Decisión del usuario (L8): "sí". Las tareas de tipo Oportunidad que ya existían quedan con el workflow "Workflow Oportunidades" tras la migración, para que elegirlo luego no duplique sus pasos. Las demás tareas quedan sin workflow; las subtareas no cambian.
- **S2** Decisión del usuario (L3): "sí quiero campo "Worflow" en la tarea".
  - Campo opcional "Workflow" en el alta y la edición. Al crear con un workflow, sus pasos se añaden como subtareas en orden (sin persona ni prioridad, sin resolver). Al editar y elegir un workflow distinto del que tenía, sus pasos se añaden como subtareas nuevas y se conservan las existentes. Quitar el workflow o dejar el mismo no toca las subtareas. (supuestos)
  - Resuelve L2: "he editado una subtarea, y al seleccionar que es de tipo oportunidad no me ha creado las subtareas por defecto".
  - El tipo Oportunidad ya no copia pasos por sí mismo (evita duplicados); en el alta, al elegir el tipo Oportunidad con el campo Workflow vacío, el formulario preselecciona "Workflow Oportunidades" si existe. (supuesto)
  - Borrar un workflow deja sus tareas sin workflow y con sus subtareas. (supuesto)
- **S3** Contrato API (supuesto de diseño):
  - `GET/POST /api/v1/workflows`, `PUT/DELETE /api/v1/workflows/{id}`; cada workflow `{id, nombre, pasos: [{id, numero, nombre}]}`.
  - Pasos: `POST /api/v1/workflows/{id}/pasos` `{nombre}` (al final) → 201, `PUT .../pasos/{id_paso}` `{nombre}` → 200, `DELETE .../pasos/{id_paso}` → 200, `PUT /api/v1/workflows/{id}/orden` `{ids}` → 200; todas devuelven el workflow completo (ver L4). Se retira `/api/v1/workflow-oportunidades/...`.
  - Tarea: cuerpo de alta y edición con `workflow_id: int | null` opcional (en la edición, ausente = null, como el grupo de estados); respuesta con `workflow: {id, nombre} | null`. 422 si el workflow no existe.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S3 (backend + migración con datos) | delegada (writer A, paralelo) + cierre inline | hecho | `3b7d19b`, `2abb058` (L8) |
| T2 | S1, S2 (frontend: Ajustes, formulario, detalle) | delegada (writer B, paralelo) | hecho | `1525d6e` |
| T3 | S1–S3 (e2e contra pila aislada) | per-action worker + corrección inline | hecho | `a478daf`, `9225816` |
| T4 | S1–S3 (verificador: migración con datos, contrato, concurrencia; items 1, 3 y 4) | delegada (verificador) | PASS sobre `1525d6e`; la recomprobación de L8 entra en el verificador de comentarios-pasos-workflow | — |

## Log

- **L1** (2026-11-12) Pedido del usuario:
  > quiero que en los ajustes me permita generar distintos workflows, con un nombre, y poder seleccionar los pasos de cada workflow, como se hace ahora con el workflow existente
- **L2** (2026-11-12) Problema reportado por el usuario (comportamiento previsto hasta ahora: los pasos solo se copiaban al crear una oportunidad):
  > he editado una subtarea, y al seleccionar que es de tipo oportunidad no me ha creado las subtareas por defecto
- **L3** (2026-11-12) Pregunta: ¿campo "Workflow" en la tarea (recomendado) o un workflow asociado a cada tipo? Respuesta:
  > sí quiero campo "Worflow" en la tarea
- **L4** (2026-11-12) Decisión de contrato: las operaciones sobre pasos devuelven el workflow completo `{id, nombre, pasos}` (como los grupos de estados), para alinear backend y frontend.
- **L5** (2026-11-13) Reanudación tras la interrupción de los writers. Un chequeo de solo lectura dio:
  - código de producción completo para S1–S3;
  - migración verificada con datos sembrados: ida, vuelta y otra vez ida, conservando ids, números y nombres;
  - frontend: lint, type-check, 535 tests unitarios y build en verde.
  - Cierre de T1 inline:
    - `ruff format`;
    - el test de contrato pasa a usar `/api/v1/workflows/{id_workflow}/orden`, con un hook que envía un `workflow_id` existente;
    - los 3 tests de concurrencia pasan al repositorio y los casos de uso nuevos;
    - `workflow: None` en las respuestas esperadas de `test_tarea.py`.
  - Resultado: 974 tests en verde con 99,17 % de cobertura, sobre MySQL 8.4 desechable.
  - Desviación por confirmar: `DELETE /workflows/{id}` devuelve 204.
- **L6** (2026-11-13) Nuevo pedido del usuario:
  > Quiero que los pasos definidos en los distintos workflows tengan posibilidad de escribir comentarios, igual que se hace con las tareas. Estos comentarios se trasladarán cuando se cree una tarea de este tipo de workflow, y será modificable de forma independiente en la tarea.
  - Se trata como feature aparte (`comentarios-pasos-workflow`), apilada sobre esta rama.
- **L7** (2026-11-13) Verificador independiente (T4) sobre `1525d6e`: S1, S2 y S3 en PASS, sin bloqueos.
  - Migración con datos sembrados: el MD5 del resto de tablas no cambia ni en la ida ni en la vuelta.
  - Todos los rechazos dejan el hash de datos intacto.
  - Concurrencia: 46 tests en verde y una carga propia (uvicorn con 4 workers, 12 hilos × 25 operaciones) sin errores 500 ni copias parciales.
  - `GET /tareas` coincide con la base salvo la clave `workflow: null`.
  - Advisories:
    1. Las oportunidades que ya existían quedan con `workflow: null`; elegir luego "Workflow Oportunidades" duplicaría los pasos.
    2. Un cliente API que cree una Oportunidad sin `workflow_id` ya no recibe subtareas.
    3. `DELETE /workflows/{id}` devuelve 204.
    4. El PR del backend solo rompe el frontend de `main`; ya está previsto en la entrega.
- **L8** (2026-11-13) Pregunta: ¿asignar "Workflow Oportunidades" en la migración a las oportunidades que ya existen (advisory 1 de L7)? Respuesta del usuario:
  > sí
  - Se reabren T1 (migración `f3b9d7a2c6e4`, todavía sin publicar: ninguna rama remota la contiene) y T4.
- **L9** (2026-11-13) Implementación de L8 en `f3b9d7a2c6e4`, commit `2abb058`.
  - Sonda con MySQL desechable: datos sembrados en `c8f3a1d5e7b2` (2 oportunidades y 1 tarea sin tipo). Con la migración anterior quedaban todas con `workflow NULL` (RED); ahora las 2 oportunidades quedan con "Workflow Oportunidades" y la otra con NULL (GREEN).
  - Tras la vuelta atrás, las tareas no cambian (mismo MD5). `alembic check` sin cambios; ruff OK.
  - Al estar en un commit propio después del frontend, al cortar los PRs este commit va con el PR del backend: se reordena con cherry-pick al crear las ramas de los PRs, antes de publicar.
- **L10** (2026-11-13) T3: `e2e/workflow.spec.ts` cubre S1 y S2.
  - Pila aislada (MySQL 8.4 en 33326, uvicorn en 8126, build + preview en 5226): 51/52 dos veces, sin flakiness. Falla `tareas.spec.ts:147`.
  - Causa: defecto de la aplicación. El calendario del vencimiento abre hacia arriba y queda cortado fuera de la ventana; ya estaba mal colocado en `1525d6e~1`, y el campo Workflow lo empujó del todo fuera de la pantalla.
  - Corrección `9225816`: `max-h` a la altura disponible de reka, `overflow-y-auto` y `collision-padding`.
  - Tras la corrección: el test que fallaba pasa, la suite e2e completa da 52/52 y `SelectorFechaHora.spec` 16/16.
  - Tu pila real (3306/8000/5173) no se tocó.
