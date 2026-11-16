# orden-pasos-subtareas

Objective: subtasks inherited from a workflow are shown in the same order as the steps defined in that workflow.
Branch: `feat/orden-pasos-subtareas` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/orden-pasos`, based on main). Delivery: no commits until the user approves a preview (user's standing preference); then a PR with the migration in its own commit. Backend + migration; frontend only if needed.
Runners: backend `uv run pytest` (+ `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run lint-imports`) ALWAYS with `URL_BASE_DATOS` exported to a throwaway MySQL container — never the real DB; frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec eslint src`, `pnpm exec oxlint src`, `pnpm exec prettier --check src e2e`.

## Specs

User request (verbatim): "las tareas del workflow hereadas en una tarea tienen que verse en el mismo orden que las definidas en el workflow, es decir implementa lo que indicaste". Context: the parent had just added 4 new workflow steps to 3 open tasks via the API; they appeared at the end because subtasks are ordered by id (`modelos.py` `order_by=SubtareaModelo.id`) and have no position, and the parent said the app needs a way to keep the workflow order.

- **S1 — Orden del workflow.** A task's subtasks that come from a step of its workflow are listed in the order of those steps in the workflow (step `posicion`), everywhere the subtasks are returned (`GET /tareas`, `GET /tareas/{id}` and any response embedding subtasks) and therefore in the UI (detail, board). Assumption: subtasks that do not come from a workflow step (added by hand) are listed after the workflow ones, in creation order (id). Assumption: the order follows the workflow dynamically — reordering the workflow's steps reorders the inherited subtasks of every task that uses it.
- **S2 — Vínculo con el paso.** Each inherited subtask remembers the workflow step it came from (new nullable column, e.g. `subtareas.paso_id` → `pasos_workflow.id`, `ON DELETE SET NULL`). Applying a workflow to a task (create or change workflow, existing use case `aplicacion/tarea/asignar_workflow.py` and the repository code that copies steps and their comments) sets that link. Deleting a step from the workflow keeps the subtask, which then counts as a hand-added one (goes to the end). Renaming a step or a subtask does not break the link.
- **S3 — Datos existentes (migración).** A new Alembic revision after the current head adds the column and backfills it: for every task with a workflow, each subtask whose name exactly matches a step name of that workflow is linked to that step (if several subtasks of the same task match the same step, link only the lowest id; the rest stay unlinked). Downgrade drops the column (order goes back to id). This must make the user's real open tasks show "Crear estimaciones", "Copiar hoja estimaciones en Business Case", "Crear Business Case" and "Validar Business Case" between "Asignar técnicos a la preventa" and "Solicitar aprobación PMO", with hand-added subtasks (e.g. "Aplicar comentarios de María Bagán") after the workflow ones.
- **S4 — Sin cambios de contrato innecesarios.** Existing request bodies and response fields keep working. Assumption: exposing the link in the API (e.g. an optional `paso_id` on subtasks) is allowed only if needed; document any OpenAPI change.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1–S4 | delegated writer — reason: context backstop (long parent session) | done (uncommitted) | none until approval; migration `c5e1b8f4a2d7` |
| T2 | S1–S4 | independent verifier — Risk item 1 (migration changes stored data) | done: S1–S4 PASS, 0 blockers | |
| T3 | all | parent: preview on a migrated copy of the real data | done | http://localhost:4174/tareas |

## Log

- L1 (2026-11-16): "las tareas del workflow hereadas en una tarea tienen que verse en el mismo orden que las definidas en el workflow" / "es decir implementa lo que indicaste".
- L2: real data before the change (read-only): Workflow Oportunidades has 13 steps; open opportunities 11, 12, 13 got the 4 missing steps appended (ids at the end); task 11 has 3 hand-added subtasks. Backup `~/backups/gestor-tareas/gestor_tareas_20261116_095954_antes_pasos_workflow.sql.gz`.
- L3 (T1, writer): `subtareas.paso_id` (FK `fk_subtareas_paso` → `pasos_workflow.id`, ON DELETE SET NULL) + migration `c5e1b8f4a2d7` (after `a9c4e1f7b3d2`) with backfill per step in `numero` order → lowest-id unlinked subtask with exactly the same name (case/accent sensitive). Order is computed on read in `repositorio_tareas_sqlalchemy._ordenar_subtareas`: subtasks linked to a step of the task's *current* workflow by step `numero`, then the rest by id (assumption: subtasks from a previous workflow count as "the rest"). No API field added; only OpenAPI descriptions changed. RED observed (6 BDD scenarios, 1 unit, 2 migration tests), then GREEN. Full suite: 1084 passed, 1 failed `test_migracion_comentarios_con_formato` (environmental: the throwaway MySQL on 3308 has `collation_server=utf8mb4_unicode_ci`, so re-created TEXT columns report `COLLATE utf8mb4_unicode_ci`; it fails on its first assertion when run alone and the code path is untouched).
- L4: the L3 failure of test_migracion_comentarios_con_formato came from the throwaway DB started with --collation-server; recreated with default collation → backend 1085 passed. Verifier: S1–S4 PASS (probes on 3308: order, dynamic reorder, link/rename/delete, migration with SHA-256 invariants up/down/up, OpenAPI identical except descriptions); advisory: subtasks from a previous workflow mix with hand-added ones by id (documented assumption). Preview on a migrated copy of real data: tasks 11–13 in workflow order.
- L5 (2026-11-16): user: "sí, publica".
