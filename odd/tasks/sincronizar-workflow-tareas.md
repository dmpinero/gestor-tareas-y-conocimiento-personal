# sincronizar-workflow-tareas

Objective: after editing a workflow in Ajustes → Workflows, leaving the page asks (confirmation modal) whether to update the existing open tasks that use it; on confirmation, new steps are added as subtasks and renamed steps rename their subtask.
Branch: `feat/sincronizar-workflow-tareas` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/sincronizar-workflow`, based on main). Delivery: no commits until the user approves a preview (standing preference); then one PR. Backend + frontend.
Runners: backend `uv run pytest` (+ `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run lint-imports`) ALWAYS with `URL_BASE_DATOS` exported to a throwaway MySQL container — never the real DB; frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec eslint src`, `pnpm exec oxlint src`, `pnpm exec prettier --check src e2e`.

## Specs

User request (verbatim): "he actualizado el workflow de oportunidades, pero no me ha preguntado, al pulsar en Volver a ajustes, si quiero actualizar el workflow para las tareas ya creadas. ¿Puedes implementar todo esto?"
User decision (verbatim, answering which changes to carry over, option 1 = "Añadir y renombrar"): "Quiero el paso 1, pero antes de hacer nada que pida con una modal de confirmación".
Option 1 as presented to the user: "Los pasos nuevos se agregan como subtareas pendientes, con sus comentarios y en su posición. Los pasos renombrados cambian el nombre de su subtarea. Si borrás un paso, su subtarea se conserva (pasa al final), para no perder el trabajo ni los comentarios." Scope as presented: "Solo afecta a las tareas no completadas que usan ese workflow."

- **S1 — Pregunta al salir.** When the user has edited a workflow during the visit to the Workflows page (added, renamed, deleted or reordered a step) and leaves the page by "Volver a Ajustes" (assumption: also any other navigation away, e.g. the sidebar), and at least one open (not completed) task using that workflow would change, a confirmation modal appears BEFORE anything is changed. It says which workflow(s), how many tasks and what will change (subtasks to add, subtasks to rename). Choices: update the tasks (then navigate), leave without updating (navigate, nothing changes), or cancel (stay on the page). If nothing would change, no modal: navigate directly. Nothing is modified without explicit confirmation.
- **S2 — Añadir pasos nuevos.** On confirmation, for every open task with that workflow, each step of the workflow without a subtask linked to it (`subtareas.paso_id`) gets a new pending subtask, no person or priority, named as the step, linked to the step, with a copy of the step's comments (same as `asignar_workflow`). It is shown in its workflow position (existing read-time ordering).
- **S3 — Renombrar.** On confirmation, every subtask of those tasks linked to a step whose name differs from the step's current name takes the step's name.
- **S4 — Pasos borrados y otras tareas.** Subtasks whose step was deleted are kept (unlinked, at the end). Completed tasks, tasks of other workflows and hand-added subtasks are not touched. Running the update twice changes nothing the second time.
- **S5 — API.** A read-only endpoint returns the pending changes for a workflow (tasks affected, subtasks to add, subtasks to rename) and a mutating endpoint applies them and returns what was done. Existing endpoints and bodies unchanged; documented in OpenAPI.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1–S5 | delegated writer — reason: context backstop (long parent session) | done (uncommitted) | none until approval |
| T2 | S1–S5 | independent verifier — Risk item 1 (changes existing stored data) | done: S1–S5 PASS, 0 blockers | |
| T3 | all | parent: preview on a copy of the real data | done | http://localhost:4174/workflows | |

## Log

- L1 (2026-11-16): "he actualizado el workflow de oportunidades, pero no me ha preguntado, al pulsar en Volver a ajustes, si quiero actualizar el workflow para las tareas ya creadas. ¿Puedes implementar todo esto?"
- L2 (2026-11-16): "Quiero el paso 1, pero antes de hacer nada que pida con una modal de confirmación".
- L3: real data (read-only): Workflow Oportunidades (id 1) has 15 steps; steps 14 "Crear oferta técnica" and 15 "Crear oferta económica" are new; open tasks 11, 12, 13, 18, 19, 20 use it and lack them. Hand-added subtasks: task 11 ids 24–26, task 12 id 106.
- L4 (T1, writer): API `GET|POST /api/v1/workflows/{id}/sincronizacion` → `{"tareas":[{"id","nombre","subtareas_a_anadir":[str],"subtareas_a_renombrar":[{"id","nombre_actual","nombre_nuevo"}]}]}` (only open tasks that change; 404 if the workflow does not exist). Step→subtask built by the shared `subtareas_de_pasos` (extracted from `WorkflowPedido`). Lock order on apply: workflow FOR SHARE → open tasks FOR UPDATE → their subtasks FOR UPDATE, one commit. Frontend: `useSincronizarTareasAlSalir` (onBeforeRouteLeave) + `DialogoConfirmacion` with an optional third button. RED observed on a base copy (7/7 backend BDD, 7/8 Vitest; the 8th is the unchanged no-edit path); GREEN in the worktree. Note: S3 as written also renames a subtask the user renamed by hand back to its step's name.
- L5: verifier S1–S5 PASS, 0 blockers (backend 1094 passed, frontend 711 passed). Advisories: S3 also resets a subtask renamed by hand (none in real data today; the modal counts it); a failed GET skips the question; browser reload/close does not ask. Preview on a copy of real data: GET shows tasks 11, 12, 13, 18, 19, 20 each receiving 'Crear oferta técnica' and 'Crear oferta económica'.
