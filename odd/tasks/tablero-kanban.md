# tablero-kanban

Objective: restyle the tasks board view (TableroTareas) to look like the monday.com Kanban screenshot the user shared; the user tests a preview before anything is committed.
Branch: `feat/tablero-kanban` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/tablero-kanban`, based on `feat/mejoras-visuales-tabla`). Delivery: NO commits until the user approves the preview ("muéstrame una versión que pueda probar antes de hacer commit"); then a single PR. Frontend only.
Runners: frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec oxlint src`, `pnpm exec eslint src`, `pnpm exec prettier --check src e2e`.

## Specs

User request (verbatim): "¿podemos hacer la vista tablero más parecida a la captura adjunta?. Hazlo como antes, muéstrame una versión que pueda probar antes de hacer commit". What the screenshot shows, and the scope taken from it:

- **S1 — Columnas con cabecera de color.** Each state column has a solid colored header with the state name and its task count ("Listo 1", "En curso 1", "Detenido 1", "No iniciado 0"), white/contrasting text, and a light gray column body. Assumption: states have no stored color, so the color comes from the same position-based rule as the table's Estado pill (`frontend/src/lib/coloresTarea.ts`), extended if needed to give distinct solid colors; WCAG AA contrast in light and dark mode.
- **S2 — Tarjetas limpias.** White rounded cards with the task name at the top and a footer row of small icons: comments icon and a subtasks button showing the subtask count ("2" + subtasks icon). Assumption: keep the information the cards already show (assignees, due date with countdown, labels, the move menu) but in a compact, secondary style (reuse `AvatarPersona`, `VencimientoCorto`/countdown, label colors and `NombreRelacionado` from the table work); the task has no comment count in the API, so the comments icon opens the task detail (comments live there).
- **S3 — Subtareas desplegables bajo la tarjeta.** Pressing the subtasks button expands the task's subtasks as indented cards below it, joined by a connector line, and a "+ Agregar subtarea" action at the end that creates a subtask with just its name (reuse the existing store action for subtasks). Pressing again collapses them. Assumption: a subtask card shows its name (struck through when resuelta) and its assignee avatar; clicking it opens the parent task detail.
- **S4 — Barra de distribución de estados.** A horizontal bar with the proportion of tasks per state, in the column colors, shown in the board toolbar area (top right in the screenshot). Assumption: it reflects the tasks shown on the board (current filters), with an accessible text summary.
- **S5 — Lo que ya funciona sigue funcionando.** Drag and drop between columns, the "move to" menu, opening the detail from the card name, group selector, filters and the empty states keep working; accessible names already used by tests/e2e stay unless a spec here requires a change.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1–S5 | delegated writer — reason: context backstop (long parent session) | done (RED→GREEN observed) | uncommitted |
| T2 | all | parent: preview on the isolated stack (copy of real data) | done | http://localhost:4174/tareas (board view) |

## Log

- L1 (2026-11-13): "¿podemos hacer la vista tablero más parecida a la captura adjunta?. Hazlo como antes, muéstrame una versión que pueda probar antes de hacer commit" (monday.com Kanban screenshot: colored column headers with counts, clean cards with comments/subtasks icons, expandable nested subtask cards with "+ Agregar subtarea", state distribution bar).
- L2 (2026-11-13): T1 done, uncommitted. New `colorEstadoTablero` (lib/coloresTarea.ts: first gray-600, last emerald-700, intermediates blue/orange/violet/pink/teal-700, white text), `BarraEstados.vue`, subtask-name validation shared in `lib/subtareas.ts` (also used by SubtareasTarea). Board: colored headers, cards with avatars/short due date/colored labels and footer (comments → detail, subtasks count toggle, Mover a…), expandable subtask cards with connector line and "Agregar subtarea" inline form. 10 new/adjusted unit tests + 4 lib tests; full suite 652/652, vue-tsc, oxlint, eslint, prettier clean. E2E selectors unchanged; not run.
- L3 (2026-11-13): preview served at http://localhost:4174/tareas; user: "apruébalo, haz commit, push, PR, merge y rebuild".
- L4: CI playwright failed on axe `label-content-name-mismatch` (subtasks button showed the count but its name was "Subtareas de X") → name is now "N subtareas de X" (RED/GREEN in VistaTareas.spec.ts). `workflow.spec.ts:287` was flaky (passed on retry), not related to the board.
