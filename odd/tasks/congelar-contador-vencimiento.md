# congelar-contador-vencimiento

Objective: the "Vence en" countdown of a task stops (frozen at the value it had when the task became completed or DONE) and resumes live from the due date when the task is neither completed nor DONE.
Branch: `feat/congelar-contador-vencimiento` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/congelar-contador`, based on main 4fb2496). Delivery: no commits until the user approves a preview (standing preference); then one PR with the migration in its own commit. Backend + migration + frontend.
Runners: backend `uv run pytest` (+ `uv run ruff check`, `uv run ruff format --check`, `uv run lint-imports`, `uv run bandit -r src -q`) ALWAYS with `URL_BASE_DATOS` exported to a throwaway MySQL container — never the real DB; frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec eslint src`, `pnpm exec oxlint src`, `pnpm exec prettier --check src e2e`.

## Specs

User request (verbatim): "quiero que una tarea completado y en estado DONE tenga paralizado el contador de Vence en, si se quitar como completada o se cambia de estado que se vuelva a retomar el contador, teniendo en cuenta la fecha de vencimiento"
User decision (verbatim option chosen): "Completada o DONE (Recomendado)" — described to the user as: "Se congela en cuanto la tarea está completada o en estado DONE. Vuelve a contar solo cuando no está ni completada ni en DONE." The question also told the user: "Al congelarse, quedaría fijo el tiempo que faltaba en el momento en que la tarea pasó a ese estado, por ejemplo \"Vence en 1 d 02 h 10 min\". Al salir de ese estado, vuelve a contar en vivo según la fecha de vencimiento, aunque ya esté vencida."

- **S1 — Congelar.** A task is "frozen" while it is completed (`completada = true`) OR its state is DONE (assumption: the state named `DONE`, compared case-insensitively, in any state group). When a task goes from not frozen to frozen (mark completed, change state to DONE, edit/create/assign group that leaves it so), the instant is stored (new nullable column on `tareas`, e.g. `congelada_en`). While frozen, every countdown of that task ("Vence en …" / "Vencida hace …", in list, board and detail) shows the fixed value computed from the due date and that instant, and does not tick. If it was already overdue at that instant it shows the frozen "Vencida hace …". Changing the due date while frozen recomputes the frozen value from the new date and the same instant. Passing between completed and DONE while staying frozen keeps the original instant.
- **S2 — Reanudar.** When the task becomes neither completed nor DONE, the stored instant is cleared and the countdown runs live again from the due date ("teniendo en cuenta la fecha de vencimiento"), showing "Vencida hace …" if the date has passed.
- **S3 — Señal visual.** A frozen countdown is visibly distinguished as stopped (assumption: a pause icon and muted styling, accessible label saying it is stopped). Bells (`AvisoVencimiento`) and the overdue marker (`VencimientoCorto`) treat frozen tasks as not urgent (assumption: no bells for frozen tasks, consistent with completed tasks today).
- **S4 — Datos existentes (migración).** A new Alembic revision after the current head adds the column. Backfill (assumption): tasks already completed or in DONE get the migration instant, so their counter stops at the value it shows when the change is deployed; others stay NULL. Downgrade drops the column.
- **S5 — API.** Task responses expose the freeze instant as an optional field (adding an optional field is allowed); existing request bodies and fields unchanged; documented in OpenAPI. Tasks without due date are unaffected.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1–S5 | delegated writer — reason: context backstop (long parent session) | done (awaiting T2) | none until approval; RED/GREEN in L4 |
| T2 | S1–S5 | independent verifier — Risk item 1 (migration + backfill of stored data) | done: S1–S5 PASS, 0 blockers | |
| T3 | all | parent: preview on a migrated copy of the real data | done | |

## Log

- L1 (2026-11-17): "quiero que una tarea completado y en estado DONE tenga paralizado el contador de Vence en, si se quitar como completada o se cambia de estado que se vuelva a retomar el contador, teniendo en cuenta la fecha de vencimiento"
- L2 (2026-11-17): user chose "Completada o DONE (Recomendado)".
- L3: real data (read-only): `completada` and state are independent today (tasks 1, 2 completed without state; 7, 9, 12 completed and DONE). State group 1 has TODO, DOING, DONE. Alembic head on main 4fb2496 must be checked by the writer.
- L4 (2026-11-17, T1 writer): column `tareas.congelada_en` (DATETIME, UTC without zone, NULL = not frozen); migration `e2c7a9f4b1d6` (down_revision `c5e1b8f4a2d7`) backfills `UTC_TIMESTAMP()` for tasks with `completada` or state `LOWER(nombre) = 'done'`. Rule in `dominio/tarea/congelacion.py` (`instante_de_congelacion`), applied via `Tarea.ajustar_congelacion` in create/update use cases, in `cambiar_completada`/`cambiar_estado` repository writes, and via `ajustar_congelacion_de_tareas` in the bulk group paths (rename state, delete state moving tasks, delete group) — assumption added: those bulk paths also freeze/unfreeze. API field `congelada_en` ("YYYY-MM-DDTHH:MM:SSZ" or null). Frontend: `congeladaEn` prop on ContadorVencimiento (pause icon, muted, sr-only "(contador detenido)", no ticking), AvisoVencimiento (no bells), VencimientoCorto (no "!" mark). RED observed: new BDD feature 23/23 failing before the column existed; frontend 7 new specs failing before the props existed. GREEN: full suites pass.
- L5: verifier S1–S5 PASS, 0 blockers (backend 1143 passed, TZ=Europe/Madrid vitest 721 passed; migration up/down/up with hashes; 55 API calls identical to baseline except the new field; 12 rejected requests left data unchanged). Preview on a migrated copy of real data (http://localhost:4174): tasks 1, 2, 7, 9, 12 frozen at the migration instant.
