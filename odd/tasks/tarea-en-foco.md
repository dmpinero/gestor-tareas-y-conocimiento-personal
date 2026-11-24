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

- **S9** Focus history: "Cuando vaya cambiando el foco quiero tener una opción para ver el historial de cambios de foco, de forma que pueda navegar a esas tareas".
  - Each focus period is one history entry, holding the task, the subtask (optional), `desde` and `hasta`. The duration is `hasta - desde`.
  - An entry opens when the focus is set (PUT) and closes, with `hasta = now`, when the focus is replaced, removed, or its task or subtask is deleted.
  - The current focus appears as an open entry ("en curso", with a live duration).
  - Deleted tasks keep their entry with the last known name, shown greyed and without a link. This is the accepted proposal.
  - The current name is shown while the task or subtask still exists. On deletion the entry keeps the last name it had: the snapshot is refreshed in the delete transaction.
- **S10** Page: "página aparte con todo el historial, navegable por días. También quiero una lista ordenada con todo el historial en esa página aparte"
  - A separate page (route `/foco/historial`), opened from a clock button next to the top-bar pill. The button is visible even without a focus.
  - The "Por día" view shows the entries of one local day, with previous and next day, a date picker, "Hoy", and the day's total time.
  - The "Todo" view is an ordered list of the whole history, newest first (assumption). It shows date, start, end, duration and `Tarea › Subtarea`.
  - Clicking an entry whose task still exists navigates to `/tareas?tarea=<id>`.
- **S11** API (contract):
  - `GET /api/v1/foco/historial` takes optional `desde` and `hasta` (ISO UTC instants; it returns the entries whose `desde` falls in `[desde, hasta)`). It returns `200` with an array, newest first, of `{ "id": int, "tarea_id": int|null, "tarea_nombre": str, "subtarea_id": int|null, "subtarea_nombre": str|null, "desde": ISO, "hasta": ISO|null }`.
    - `tarea_id`/`subtarea_id` are `null` when the item was deleted.
    - An invalid `desde`/`hasta`, or `desde >= hasta`, returns `422`.
  - The existing `/api/v1/foco` responses stay unchanged.

## Tasks

- [x] T1 (S2–S4, S8) Backend:
  - Migration `foco_trabajo` and domain `dominio/foco/`, with use cases for get, set and clear.
  - Repository, router `/foco`, and tests. `vaciar_tablas` gets the new table.
  - Bump `_ULTIMA` in the old migration tests.
  - Route: delegated, writer A, in parallel with T2 (trigger: two independent units with disjoint surfaces, contract fixed in S4).
  - Risk: item 1 (new migration that only adds a table). Commit 1 `9159cd3` (rev `e6a1c9d3f5b7`; 1533 backend tests green).
- [x] T2 (S1, S3, S5–S7) Frontend: api type, store `useTiendaFoco`, pill in BarraSuperior, highlight in list, board and detail, buttons, and the `?tarea=` query that opens the detail. Unit tests and e2e. Route: delegated, writer B. Commit 2 `8df567a` (1036 vitest green, vue-tsc/eslint/prettier clean).
- [x] T3 README section and the independent verifier (item 1). Pending at publish: back up the database before applying the migration locally.

- [x] T4 (S9, S11) Backend history:
  - New migration `historial_foco` with FKs `ON DELETE SET NULL` and name snapshots.
  - Open and close entries in `FijarFoco`/`QuitarFoco`. Deleting the focused task or subtask closes the entry, through the existing delete use cases (shared code, item 3).
  - Endpoint `GET /foco/historial`.
  - Route: delegated, writer C, in parallel with T5. Risk: items 1 and 3. Commit 4 `24e0dc8` (rev `483e78c30e26`).
- [x] T5 (S9, S10) Frontend history page: clock button, the `/foco/historial` route with "Por día" and "Todo", navigation to the task, deleted entries greyed. Unit tests and e2e. Route: delegated, writer D. Commit 5 `41ad180`; mobile overflow fix `e5f37ac`.
- [x] T6 README update, independent verifier (items 1 and 3), full e2e, refreshed preview.

## Log

- **L1** (2026-11-24) Original request: "quiero poder saber con qué tarea estoy en cada momento, de forma que quede destacada. En cada momento solo puede haber 1 tarea en la que esté trabajando. ¿Cómo se te ocurre que podamos hacerlo para que quede visualmente claro?"
- **L2** Proposal sent to the user:
  - a backend-enforced single focus;
  - a top-bar pill with a timer, a click to open the task, and an ✕ to stop;
  - a violet border, pulsing dot and "En foco" label;
  - the "Trabajar en esta" / "Dejar de trabajar" button.

  User answer to the open question: "en tareas o subtareas".
- **L3** Writer deviations accepted: aria-labels include the item name (`Trabajar en esta (X)`) for unique names; deleting the focused item clears focus locally; a card with a focused subtask also moves first. Preview with a copy of the real data at http://localhost:4960 (DB 3320, API 8960).
- **L4** Independent verifier on `9159cd3`: no blockers, S2/S3/S4/S8 met. Migration keeps the checksums of existing tables through upgrade, downgrade and upgrade; the differential check of existing endpoints against `cafb6b2` is identical. Two of its probes were added as regression tests: a rejected PUT keeps the focus, and resolving the subtask keeps it. The e2e suite on the isolated stack passed 79/79. Commit 3 holds the README and the probes. Pending: user approval on the preview, then publish with a DB backup before the migration.
- **L5** (2026-11-24) User: "queda muy bien, pero hay algo que quiero añadir. Cuando vaya cambiando el foco quiero tener una opción para ver el historial de cambios de foco, de forma que pueda navegar a esas tareas". Proposal sent: entries with duration, a clock button, grouping by day, deleted tasks greyed. User: "página aparte con todo el historial, navegable por días. También quiero una lista ordenada con todo el historial en esa página aparte".
- **L6** Integration of the history work:
  - The schemathesis contract test got a hook for the `desde >= hasta` rule.
  - The e2e suite first failed 6 board tests, because the new clock button made the top bar overflow at 390 px. The fix is `shrink-0` on the actions group, plus an e2e regression test. After it, e2e passed 81/81.
  - The verifier on `24e0dc8` found no blockers.
  - Advisories applied with RED tests first: deleted items keep their last name (the snapshot is refreshed on delete), and out-of-range filter instants return 422 instead of 500.
  - Backend: 1593 tests green.
