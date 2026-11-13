# mejoras-visuales-tabla

Objective: visual improvements to the tasks list (VistaTareas table), inspired by a monday.com screenshot the user shared, previewed by the user before merging.
Branch: `feat/mejoras-visuales-tabla` (worktree `../gestor-tareas-y-conocimiento-personal-worktrees/mejoras-visuales`). Delivery: single PR after the user approves the preview; frontend only.
Runners: frontend `pnpm vitest run`, `pnpm exec vue-tsc --build`, `pnpm exec oxlint src`, `pnpm exec eslint src`, `pnpm exec prettier --check src`; e2e Playwright only on an isolated stack.

## Specs

User's choice (verbatim): "Quiero las mejoras de los 4 puntos, pero mantén el texto de la cuenta atrás". The four points, as proposed and accepted:

- **S1 — Grupos plegables.** "Tabla dividida en 'Pendientes' y 'Completadas' (cada grupo con su color en el borde izquierdo y plegable), así las completadas no llenan la pantalla de tachados; fila '+ Agregar tarea' al final de cada grupo para crear con solo el nombre; pie con la barra de distribución de prioridades." Assumptions: group headers show the group name and its count; collapsed state is remembered in localStorage per group (like the visible columns); "Completadas" starts collapsed? — no: both start expanded unless remembered. Quick add in "Completadas" creates the task already completed. Sorting, filters, search, export keep working over all rows (export unchanged: flat list). The existing "Estado" filter (Todas/Completadas/No completadas) keeps working (a group with no rows still shows its header).
- **S2 — Celdas de color.** "Prioridad, estado del grupo y tipo como celdas/píldoras de color (1 rojo, 2 naranja, 3 azul…); vencimiento corto ('13 nov') con icono (✓ si completada, ! rojo si vencida)". User correction: keep the countdown text ("mantén el texto de la cuenta atrás"): the existing `ContadorVencimiento` text stays under the short date. Assumptions: priorities 1 red, 2 orange, 3 blue, 4 teal, 5 gray, none "—"; colors meet WCAG AA contrast in light and dark mode; the full date/time stays available (title/tooltip and accessible text); the board and calendar keep their current look except where they share components.
- **S3 — Avatares y etiquetas.** "Personas como círculo con iniciales (tooltip con el nombre, siguen siendo clicables); etiquetas con un color estable derivado de su nombre." The click behavior from `NombreRelacionado` (opens the related tasks modal) must keep working, with the same accessible names ("Ver tareas y subtareas de X", "Ver tareas con la etiqueta X"). Applies to the table; the board may reuse it.
- **S4 — Barra compacta.** "Filtros en una barra de una línea (Buscar, Persona, Filtrar, Columnas, exportar) con el panel de filtros desplegable solo al pedirlo; acciones de fila: casilla de completada al inicio y menú '⋯' en hover en vez de 4 botones." Assumptions: every existing filter stays available in the "Filtrar" panel; "Persona" is a quick shortcut to the existing Asignado a filter; row actions (Editar, Ver detalle, Eliminar) keep their accessible names and remain keyboard reachable (menu button always focusable; visible on hover/focus, always visible on touch/narrow screens); the completada checkbox keeps the toggle behavior and accessible name of the current button.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S4 | delegated writer — reason: context backstop (long parent session); same file as T2–T4, so one writer runs all units sequentially | done | see Log L4 |
| T2 | S1 | same writer | pending | |
| T3 | S2 | same writer | pending | |
| T4 | S3 | same writer | pending | |
| T5 | all | parent: isolated preview stack (copy of real data) for the user | pending | |

## Log

- L1 (2026-11-13): "Te paso un ejemplo de aplicación real para ver si puedes proponerme mejoras visuales y mejorar la aplicación. Antes de aceptar los cambios déjame ver cómo quedaría en la aplicación" (monday.com screenshot).
- L2 (2026-11-13): proposed 4 packages (Grupos plegables, Celdas de color, Avatares y etiquetas, Barra compacta) → user: "Quiero las mejoras de los 4 puntos, pero mantén el texto de la cuenta atrás".
- L3: forecast ~800–1200 authored lines, frontend only; no backend or data changes. Preview against a throwaway MySQL loaded from a fresh dump of the real DB; never the real DB.
- L4 (T1/S4): one-line bar (`data-testid="barra-tareas"`: Buscar, Persona = `FiltroMultiple` bound to the same `asignadosFiltro`, Filtrar = `CollapsibleTrigger` with the panel closed by default, active count + "Limpiar filtros" only when a filter is active, Columnas + export on the right in list view). Row: reka `Checkbox` "Marcar como completada la tarea X" at the start of the Nombre cell; `MenuAccionesTarea` popover "Acciones de la tarea X" with Editar/Ver detalle/Eliminar keeping their accessible names; hover-only visibility via `[data-acciones-fila]` CSS (wide + hover-capable screens only). Focus after delete goes to the next row's menu; cancel returns to the row's menu. RED: 65 failing in VistaTareas.spec.ts → GREEN 609/609.
