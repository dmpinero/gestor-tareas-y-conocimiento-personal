# hibernar-tarea

Objective: hibernate and resume a task any number of times; while hibernated its due-date countdown is frozen, and resuming shifts the due date by the hibernated time.
Branch: `feat/hibernar-tarea` · Delivery: `single-pr` (one PR per user request, as in previous features) · Tests: `uv run pytest` (backend, throwaway MySQL), `pnpm exec vitest run` + `pnpm exec playwright test` (frontend, isolated stack)

## Specs

- **S1** Hibernate: "quiero tener la posiblidad de hibernar una tarea, por lo que debe dejar de contar el reloj."
  - The clock is the due-date countdown ("Vence en …" / "Vencida hace …"). While hibernated it shows the remaining time frozen at the moment of hibernation.
  - The task shows that it is hibernated (badge "Hibernada") in the list, the board and the detail.
  - Reuse the existing freeze plumbing: the countdown components already take `congeladaEn` (set when a task is completed or DONE). The freeze instant shown is the earliest of `congelada_en` and `hibernada_desde`. A hibernated task gets no overdue alert, the same as a frozen one.
  - `hibernada_desde` is independent of `congelada_en`: completing, uncompleting or moving a hibernated task does not end the hibernation.
- **S2** Comment: "Al hibernar, se podrá poner un comentario que aparecerá como un comentario normal de la lista de comentarios que se tiene en la parte derecha del detalle."
  - The comment is optional. When given, it is stored as a regular task comment, created in the same transaction as the hibernation.
- **S3** Repetition: "Se podrá hibernar/reanudar cuantas veces se quiera"
  - Hibernating an already hibernated task, or resuming one that is not hibernated, is rejected with `409`.
- **S4** Resume shifts the due date. User choice: "Se corre lo hibernado": the due date moves forward by exactly the hibernated time, so the remaining time is preserved. A task without a due date only clears its hibernated state.
- **S5** API (contract):
  - The task response gains `hibernada_desde: ISO UTC instant | null` (additive, optional field).
  - `POST /api/v1/tareas/{id}/hibernar` with body `{ "comentario": str | null }` returns `200` with the task. Unknown task: `404`. Already hibernated: `409`. Comment validation follows the existing comment rules (`422`).
  - `POST /api/v1/tareas/{id}/reanudar` returns `200` with the task (with the shifted due date). Unknown task: `404`. Not hibernated: `409`.
- **S6** Assumptions:
  - Hibernation does not change completion, focus or subtasks.
  - Editing a hibernated task's due date by hand is allowed; resuming still shifts it by the hibernated time.

## Tasks

- [ ] T1 (S1–S5) Backend: migration adding `tarea.hibernada_desde`, domain and use cases `HibernarTarea`/`ReanudarTarea`, endpoints, schema field, tests. Risk: item 1 (migration on an existing table). Route: delegated, writer A, in parallel with T2 (trigger: two independent units with disjoint surfaces, contract fixed in S5).
- [ ] T2 (S1–S3) Frontend: api, store actions, "Hibernar" (dialog with optional comment) / "Reanudar" buttons, frozen countdown, "Hibernada" badge, comment list refresh; unit tests and e2e. Route: delegated, writer B.
- [ ] T3 README, independent verifier (item 1), full e2e, preview.

## Log

- **L1** (2026-11-25) Original request: "quiero tener la posiblidad de hibernar una tarea, por lo que debe dejar de contar el reloj. Al hibernar, se podrá poner un comentario que aparecerá como un comentario normal de la lista de comentarios que se tiene en la parte derecha del detalle. Se podrá hibernar/reanudar cuantas veces se quiera"
- **L2** Question asked: on resume, what happens to the due date? User answer: "Se corre lo hibernado (Recomendado)" — the due date moves forward by the hibernated time.
