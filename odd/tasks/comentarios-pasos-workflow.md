# comentarios-pasos-workflow

Objetivo: comentarios en los pasos de los workflows, copiados a las subtareas cuando el workflow se aplica a una tarea, y modificables de forma independiente en la tarea.
Rama: `feature/comentarios-pasos-workflow`, apilada sobre `feature/workflows-multiples` (`1525d6e`), en el worktree `../gestor-tareas-y-conocimiento-personal-worktrees/comentarios-pasos-workflow` · Entrega: `stacked-to-main`, después de los PRs de workflows-multiples · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "Quiero que los pasos definidos en los distintos workflows tengan posibilidad de escribir comentarios, igual que se hace con las tareas."
  - En Ajustes → Workflows, cada paso tiene su historial de comentarios: añadir, editar y borrar, con las mismas reglas que los comentarios de las tareas y subtareas (texto obligatorio de 1 a 500 caracteres con saltos de línea; `creado` y `editado` los pone la aplicación, en UTC y con precisión de segundos; sin autor).
  - Supuesto: se reutiliza el componente de comentarios existente (`ComentariosTarea.vue`) o se extrae uno genérico a partir de él, en lugar de duplicarlo.
  - Borrar un paso borra sus comentarios.
- **S2** "Estos comentarios se trasladarán cuando se cree una tarea de este tipo de workflow"
  - Al crear una tarea con workflow, cada subtarea que nace de un paso recibe una copia de los comentarios de ese paso, en el mismo orden.
  - Decisión del usuario (L2: "sí"): también se copian cuando, al editar la tarea, se elige un workflow distinto y sus pasos se añaden como subtareas nuevas. En cualquier otro caso no se copia nada.
  - Supuesto: la copia conserva el texto. `creado` es el instante de la copia y `editado` queda vacío.
  - La copia de comentarios usa la misma transacción y el mismo bloqueo que la copia de los pasos (`leer_para_copiar`), para que una edición o un borrado simultáneo de los comentarios del paso no deje una copia a medias.
- **S3** "y será modificable de forma independiente en la tarea."
  - Editar o borrar un comentario copiado en la subtarea no cambia el paso, y editar o borrar el comentario del paso no cambia las subtareas ya creadas.
- **S4** Contrato API (supuesto de diseño; sigue el patrón de `/tareas/{id}/subtareas/{id}/comentarios`):
  - `GET /api/v1/workflows/{id_workflow}/pasos/{id_paso}/comentarios` devuelve 200 con la lista.
  - `POST` con `{texto}` devuelve 201 con el comentario.
  - `PUT .../comentarios/{id_comentario}` con `{texto}` devuelve 200 con el comentario.
  - `DELETE .../comentarios/{id_comentario}` devuelve los mismos códigos que el borrado de comentarios de subtarea.
  - Cada comentario es `{id, texto, creado, editado}`. Workflow o paso inexistente, o comentario de otro paso: 404. Texto inválido: 422.
  - El workflow que devuelve el resto de endpoints puede incluir el número de comentarios de cada paso (`pasos: [{id, numero, nombre, comentarios}]`), igual que las subtareas exponen su número de comentarios.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S4 (backend: dominio, migración de tabla nueva, repositorio, API, copia en `asignar_workflow`) | delegada (writer A, paralelo con T2; superficie `backend/**`) | hecho | `77a754e` |
| T2 | S1, S3, S4 (frontend: comentarios por paso en VistaWorkflows, contador) | delegada (writer B, paralelo con T1; superficie `frontend/src/**`) | hecho | `d08410b` |
| T3 | S1–S3 (e2e contra una pila aislada) | per-action worker | hecho | `bf8e718` |
| T4 | S1–S4 (verificador: migración, contrato, concurrencia de la copia; items 1, 3 y 4) | delegada (verificador) | hecho: PASS, sin bloqueos | sobre `bf8e718` |

Previsión: unas 900 líneas escritas (400 de backend, 350 de frontend y 150 de e2e). Se corta en un PR de backend y otro de frontend + e2e.

## Log

- **L1** (2026-11-13) Pedido del usuario:
  > Quiero que los pasos definidos en los distintos workflows tengan posibilidad de escribir comentarios, igual que se hace con las tareas. Estos comentarios se trasladarán cuando se cree una tarea de este tipo de workflow, y será modificable de forma independiente en la tarea.
- **L2** (2026-11-13) Pregunta: ¿copiar también los comentarios al asignar el workflow editando la tarea? Respuesta del usuario:
  > sí
- **L3** (2026-11-13) Worktree creado desde `1525d6e`. Lo pendiente de workflows-multiples (T3 e2e y T4 verificador) sigue en el árbol principal. Si T4 encuentra bloqueos, esta rama se rebasa sobre la corrección.
- **L4** (2026-11-13) T2 entregada.
  - Se reutiliza `ComentariosTarea.vue` sin cambios: ya es genérico (prop `ruta`, evento `actualizados`). Por eso no hacen falta funciones nuevas de cliente.
  - `PasoWorkflow.comentarios` pasa a ser obligatorio: T1 debe enviarlo en todos los pasos.
  - RED: 10 specs fallando; GREEN: 545/545. Lint, type-check y build OK.
  - Spot check del padre: type-check OK y 545/545.
  - Riesgo del writer: item 3.
- **L5** (2026-11-13) workflows-multiples recibió `2abb058` (L8 de esa feature): la migración `f3b9d7a2c6e4` asigna "Workflow Oportunidades" a las oportunidades existentes.
  - Esta rama debe rebasarse sobre `2abb058` antes de publicar.
  - T4 de esta feature reverifica también esa migración con datos.
- **L6** (2026-11-13) T1 entregada por el writer.
  - Tabla `comentarios_paso_workflow` (migración `d2a8e5c3f7b1`, aditiva, con vuelta atrás) y API de comentarios del paso.
  - Copia en `leer_para_copiar` con lectura `FOR SHARE`, después de bloquear los pasos. Los cambios en comentarios bloquean la fila del paso.
  - Desviación: el contador de la respuesta tras renombrar o reordenar se lee sin bloqueo (puede desfasarse en uno). La copia sí se lee siempre bajo bloqueo.
  - El padre repitió la suite completa sobre MySQL desechable: 1045 en verde.
  - Commits `77a754e` (T1) y `d08410b` (T2) tras rebasar sin conflictos sobre `c1d05d8`.
  - Tras el rebase: type-check y unitarios del frontend, y unitarios del backend, en verde.
- **L7** (2026-11-13) T3 (`bf8e718`): `workflow.spec.ts` cubre S1 (comentarios del paso, contador y axe en claro/oscuro), S2 (copia al crear y al editar) y S3 (independencia en ambos sentidos). Suite e2e completa 56/56 dos veces contra una pila aislada; prettier y eslint OK; sin defectos de la aplicación.
- **L8** (2026-11-13) Verificador independiente (T4) sobre `bf8e718`, con base `c1d05d8`: S1–S4 en PASS, y también `2abb058` y `d2a8e5c3f7b1`, sin bloqueos.
  - Migraciones: ida y vuelta con datos sembrados; dump idéntico tras la vuelta atrás, salvo la tabla nueva.
  - API: 17 peticiones rechazadas sin cambiar el hash de datos; códigos idénticos a los de los comentarios de subtarea.
  - Las 23 peticiones previas dan la misma respuesta que en la base, salvo la clave `comentarios`.
  - Concurrencia: 53/53 tres veces seguidas y una carga de unas 4 400 peticiones con 6 workers, sin errores 5xx ni deadlocks; 4 722 subtareas copiadas, todas con un estado completo.
  - Advisories: el contador tras renombrar o reordenar se lee sin bloqueo (L6); las copias comparten `creado` y su orden lo decide el id.
  - Feature cerrada. Push y PRs quedan a decisión del usuario.
