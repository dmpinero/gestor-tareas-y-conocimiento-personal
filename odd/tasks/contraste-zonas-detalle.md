# contraste-zonas-detalle

Objective: give the app visual depth (distinct zones, distinguishable table rows) and improve the task detail view; the user tests a preview on its own URL before deciding.
Branch: `feat/contraste-zonas-detalle` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/contraste-zonas`, based on `feat/clic-fila-detalle`). Delivery: NO commits until the user approves the preview; then a single PR. Frontend only.
Runners: frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec oxlint src`, `pnpm exec eslint src`, `pnpm exec prettier --check src e2e`.

## Specs

User request (verbatim): "quiero continuar con las mejoras visuales, en general está todo muy blanco y no se distinguen las distintas zonas de la aplicación, ni las filas en la tabla. ¿Puedes proponer estas mejoras, como siempre en una nueva versión con url propia antes de decidir? También que mejore la visualización de detalles de una tarea"

- **S1 — Zonas de la aplicación.** "está todo muy blanco y no se distinguen las distintas zonas de la aplicación". Proposal: a soft gray app background with the main content on white surfaces (cards with border and subtle shadow); a tinted sidebar clearly separated from content; a header bar with its own background/border; the tasks toolbar (search, filters, columns, export) inside its own surface; board columns and calendar keep standing out against the background. Equivalent hierarchy in dark mode (background darker than surfaces). Prefer changing the theme tokens in `frontend/src/assets/main.css` and layout components over per-view overrides. WCAG AA contrast for text on every surface, light and dark.
- **S2 — Filas de la tabla.** "ni las filas en la tabla". Proposal: alternating row background (zebra), a clearly visible row separator, a stronger hover highlight (rows are clickable), a tinted header row, and group header rows ("Pendientes"/"Completadas") tinted with their group color. Must not break the completed-row strike-through, the bells, the pills or the row click.
- **S3 — Detalle de una tarea.** "que mejore la visualización de detalles de una tarea". Proposal: a header band with the task name, the bells, and pills for priority, state, type and short due date with countdown (reuse the table components: `AvisoVencimiento`, `VencimientoCorto`, `ContadorVencimiento`, color helpers in `lib/coloresTarea.ts`, `AvatarPersona`, `NombreRelacionado`); the fields grouped in labeled cards (e.g. "Planificación": fechas, prioridad, estado; "Personas y etiquetas"; "Descripción" with preserved line breaks; "Oportunidad" when present); subtasks with a progress bar ("n/m resueltas") and comments as clearly separated sections. Keep every existing field, the Editar button and edit mode, delete, the related-tasks modal, comments and subtasks behavior, and the accessible names/test ids used by tests and e2e.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1–S3 | delegated writer — reason: context backstop (long parent session) | done (RED 13 → GREEN 673/673) | uncommitted |
| T2 | all | parent: preview on its own URL (port 4175) over a copy of the real data | done | http://localhost:4175/tareas |

## Log

- L1 (2026-11-13): "quiero continuar con las mejoras visuales, en general está todo muy blanco y no se distinguen las distintas zonas de la aplicación, ni las filas en la tabla. ¿Puedes proponer estas mejoras, como siempre en una nueva versión con url propia antes de decidir? También que mejore la visualización de detalles de una tarea"
- L2 (2026-11-13): T1 implemented by the delegated writer, uncommitted. S1: new `--lienzo` canvas token (light oklch 0.962, dark 0.12) on `SidebarInset`; tinted sidebar; header/status bar on `bg-card`; toolbar, filter panel, table and calendar on white card surfaces; board columns `bg-muted` + border; `--muted` 0.945, `--muted-foreground` 0.48, `--border` 0.885, light `--destructive` 0.55 to keep >= 4.5:1 on canvas and zebra rows (computed). S2: per-row zebra `bg-muted/40` (zebra removed from `TableBody` default, kept explicitly in subtasks table), blue hover, `bg-muted` header row, group rows tinted blue/emerald. S3: header band with pills (Prioridad N, Pendiente/Completada, group state, type, short due date + countdown), fields in cards (Descripción, Planificación, Personas y etiquetas, Datos generales), Oportunidad card, subtasks and comments cards, subtask progress bar "n/m resueltas". The countdown moved from the "Fecha de vencimiento" field to the header (one `timer` only, so the e2e `getByRole('timer')` stays strict). Checks: vitest 673 passed, vue-tsc, oxlint, eslint, prettier clean. e2e not run.
- L3 (2026-11-13): preview at http://localhost:4175/tareas; user: "publica".
