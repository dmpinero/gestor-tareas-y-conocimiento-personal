# tarea-en-foco

Objective: mark the one task or subtask the user is working on right now ("en foco") and make it visually obvious everywhere.
Branch: `feat/tarea-en-foco` · Delivery: `single-pr` (one PR per user request, as with every previous feature; forecast ~1000 authored lines) · Tests: `uv run pytest` (backend, `URL_BASE_DATOS` pointed at a throwaway MySQL), `pnpm exec vitest run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Goal: "quiero poder saber con qué tarea estoy en cada momento, de forma que quede destacada."
- **S2** Uniqueness: "En cada momento solo puede haber 1 tarea en la que esté trabajando."
  - The backend guarantees it: a single-row table `foco_trabajo` with fixed `id = 1`.
  - Focusing another item silently replaces the previous one. There is no error and no confirmation.
- **S3** Scope: the focus can be a task or a subtask. User answer: "en tareas o subtareas".
- **S4** Persistence and API contract (proposal accepted by the user):
  - Storage is server-side.
  - `GET /api/v1/foco` returns `200` with `null` when nothing is focused. Otherwise it returns `{ "tarea_id": int, "tarea_nombre": str, "subtarea_id": int|null, "subtarea_nombre": str|null, "desde": ISO datetime }`.
  - `PUT /api/v1/foco` with body `{ "tarea_id": int, "subtarea_id": int|null }` returns `200` with the same shape.
    - Unknown task: `404`.
    - Subtask that does not exist or does not belong to the task: `404`.
    - `desde` is reset to now on every PUT.
  - `DELETE /api/v1/foco` returns `204`, and is idempotent.
  - Deleting the focused task or subtask clears the focus (FK `ON DELETE CASCADE`).
- **S5** Top bar (proposal accepted):
  - A fixed pill, for example `● Trabajando en: Migración portal · 1 h 20 min`, visible from every page.
  - For a subtask it shows `Tarea › Subtarea`.
  - Clicking it opens the task (`/tareas?tarea=<id>` opens its detail), and an ✕ stops working on it.
  - Without a focus the pill is hidden.
  - The timer counts from `desde`: `< 1 min`, `N min`, `N h M min`. It refreshes every minute.
- **S6** Highlight wherever it appears (proposal accepted):
  - A strong violet border, distinct from the amber highlight used for the person filter.
  - A softly pulsing dot and the label "En foco".
  - In the board, the focused card moves to the top of its column, and a card whose subtask is focused auto-expands.
  - Applies to the list row, the board card, the board subtask row, and the subtask row in the detail.
- **S7** Activation (proposal accepted):
  - A "Trabajar en esta" button on the card and in the task detail. Subtasks get the same action in the board and in the detail.
  - On the item already in focus, the button becomes "Dejar de trabajar".
- **S8** Assumption: completing a task does not clear its focus. Only deleting it, or an explicit stop, does.

## Tasks

- [ ] T1 (S2–S4, S8) Backend:
  - Migration `foco_trabajo` and domain `dominio/foco/`, with use cases for get, set and clear.
  - Repository, router `/foco`, and tests. `vaciar_tablas` gets the new table.
  - Bump `_ULTIMA` in the old migration tests.
  - Route: delegated, writer A, in parallel with T2 (trigger: two independent units with disjoint surfaces, contract fixed in S4).
  - Risk: item 1 (new migration that only adds a table). Commit 1.
- [ ] T2 (S1, S3, S5–S7) Frontend: api type, store `useTiendaFoco`, pill in BarraSuperior, highlight in list, board and detail, buttons, and the `?tarea=` query that opens the detail. Unit tests and e2e. Route: delegated, writer B. Commit 2.
- [ ] T3 README section and the independent verifier (item 1). Pending at publish: back up the database before applying the migration locally.

## Log

- **L1** (2026-11-24) Original request: "quiero poder saber con qué tarea estoy en cada momento, de forma que quede destacada. En cada momento solo puede haber 1 tarea en la que esté trabajando. ¿Cómo se te ocurre que podamos hacerlo para que quede visualmente claro?"
- **L2** Proposal sent to the user:
  - a backend-enforced single focus;
  - a top-bar pill with a timer, a click to open the task, and an ✕ to stop;
  - a violet border, pulsing dot and "En foco" label;
  - the "Trabajar en esta" / "Dejar de trabajar" button.

  User answer to the open question: "en tareas o subtareas".
