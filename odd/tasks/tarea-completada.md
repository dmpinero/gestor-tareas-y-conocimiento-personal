# tarea-completada

Objetivo: icono con estado junto al de Detalle que tacha la tarea (completada) y la destacha (pendiente) al pulsarlo de nuevo.
Rama: `feature/tarea-completada` (desde `main` v1.13.0) · Entrega: `stacked-to-main` (PR backend → PR frontend) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** Icono con estados: "Quiero un icono junto al de detalle de una tarea, este icono debe tener estados, de forma que al pulsarlo, la tarea aparecerá como tachada y al volverlo a pulsar, aparecerá sin estar tachada."
  - Botón de alternancia junto a "Ver detalle" en la columna de acciones: `Circle` (pendiente) / `CircleCheck` (completada) de `@lucide/vue`, `aria-pressed` según el estado, nombre accesible "Marcar como completada la tarea <nombre>" y `title` "Completada"/"Pendiente" (supuesto).
  - Completada: el texto de la fila aparece tachado (`line-through`), incluida la cuenta atrás.
- **S2** Persistencia (supuesto: el estado sobrevive a recargar): campo `completada: bool` (por defecto `false`; las tareas existentes quedan pendientes) con migración nueva; `PATCH /api/v1/tareas/{id}/completada` con cuerpo `{"completada": bool}` → `200` con la tarea; id inexistente → `404`; cuerpo inválido → `422`. Las respuestas de `GET`/`POST`/`PUT` incluyen `completada`; `POST`/`PUT` no lo reciben (se cambia solo con el icono) y `PUT` lo conserva.
- **S3** Detalle: la modal muestra "Estado: Completada" o "Estado: Pendiente".
- Fuera de alcance (no pedido): columna, filtro u ordenación por estado y exportación del estado.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S2 (backend: columna, migración, PATCH, respuestas, tests) | delegada (writer A, paralelo) | hecha | `eaf28ed` |
| T2 | S1, S3 (frontend: icono, tachado, store `alternarCompletada`, detalle, specs) | delegada (writer B, paralelo) | hecha | `d898f6a` |
| T3 | S1–S3 (e2e contra pila aislada) | inline | hecha | `e28fe48` |
| T4 | S1–S3 (verificador independiente: migración y contrato, items 1 y 3) | delegada (verificador) | hecha (sin blockers) | — |

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > Quiero un icono junto al de detalle de una tarea, este icono debe tener estados, de forma que al pulsarlo, la tarea aparecerá como tachada y al volverlo a pulsar, aparecerá sin estar tachada.
- **L2** (2026-11-10) T1 (backend): columna `completada` (migración `a7c3e9f2b4d8`, por defecto `false`), `PATCH /api/v1/tareas/{id}/completada` con booleano estricto; `PUT` no escribe el campo (no pisa un `PATCH` concurrente). 324 tests, 97,63 %, contrato 10/10. T2 (frontend): conmutador `Circle`/`CircleCheck` con `aria-pressed`, celdas tachadas, "Estado" en el detalle; 262 tests. T3: e2e de tachar, recargar y destachar; Playwright 30/30 dos veces.
- **L3** (2026-11-10) T4, verificador: S1–S3 en verde, sin blockers. Migración con hash idéntico y esquema idéntico tras downgrade; 12 cuerpos inválidos → 422 sin cambios; 60 carreras PUT/PATCH sin pérdidas; OpenAPI solo con añadidos; axe sin violaciones en claro y oscuro. Advisories: con más de mil tareas la auditoría axe de `/tareas` supera los 30 s (también en la base); comentario de documentación descolocado en `VistaTareas.vue` (corregido); sin protección ante doble clic (inocuo).
