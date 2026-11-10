# filtros-tareas

Objetivo: añadir debajo del título "Tareas" un panel de filtros por los campos de la tabla, como el de Movimientos en `gestor-gastos-personal`.
Rama: `feature/filtros-tareas` (desde `main` v1.7.1) · Entrega: un PR · Tests: `pnpm test:unit run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Filtro: "Quiero que debajo del literal Tareas pongas un filtro como ya se hace en la aplicación https://github.com/dmpinero/gestor-gastos-personal, para filtrar según los campos existentes en la tabla"
  - Patrón de la referencia (`VistaMovimientos.vue`, panel `Collapsible` "Filtros" con `aria-label` "Contraer filtros"/"Expandir filtros", abierto por defecto; `FiltroMultiple`; "Limpiar filtros").
  - Filtrado en el navegador; el orden y la exportación trabajan sobre las filas filtradas (como en la referencia).
- **S2** Filtros por campo (supuestos sobre cómo filtrar cada campo):
  - **Buscar**: un texto que busca en Nombre y Descripción, sin distinguir mayúsculas ni acentos (`useBusquedaTabla` de la referencia, ampliado a acentos). Placeholder "Buscar tareas…".
  - **Prioridad**: `FiltroMultiple` con 1–5 y "Sin prioridad"; todas marcadas por defecto.
  - **Etiquetas**: `FiltroMultiple` con el catálogo y "Sin etiquetas"; todas marcadas por defecto; una tarea pasa si tiene alguna etiqueta marcada (o no tiene ninguna y "Sin etiquetas" está marcada).
  - **Asignado a**: igual que Etiquetas con el catálogo de personas y "Sin asignar".
  - **Fecha de creación** desde/hasta y **Fecha de vencimiento** desde/hasta (`<input type="date">`, ambos extremos incluidos, por día). Con un rango de vencimiento activo, las tareas sin vencimiento no pasan.
  - **Limpiar filtros**: restablece todos los filtros.
  - Sin resultados: "Ninguna tarea coincide con los filtros." (distinto de "Todavía no hay tareas.").
  - Un elemento del catálogo creado al guardar una tarea aparece marcado en su filtro.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S2 (componentes `ui/collapsible`, `ui/checkbox`, `ui/separator`, `FiltroMultiple`, `useBusquedaTabla`, integración en `VistaTareas`, specs) | delegada (writer, límite de contexto) | hecha | ver L3 |
| T2 | S1–S2 (e2e contra pila aislada, suite) | inline | hecha | ver L3 |

Evidencia de ruta: una sola unidad; se delega por el límite de contexto de la sesión. Riesgo: ninguno de los items 1–5 (solo frontend, sin datos ni contrato).

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > Quiero que debajo del literal Tareas pongas un filtro como ya se hace en la aplicación https://github.com/dmpinero/gestor-gastos-personal, para filtrar según los campos existentes en la tabla
- **L2** (2026-11-10) Mapeo: la referencia tiene dos patrones (buscador simple en Cuentas y panel "Filtros" por campo en Movimientos); "según los campos existentes en la tabla" corresponde al de Movimientos.
- **L3** (2026-11-10) T1 (writer): `ui/collapsible`, `ui/checkbox`, `ui/separator` y `FiltroMultiple` copiados de la referencia (ids de las casillas por posición, porque los nombres de catálogo llevan espacios); `useBusquedaTabla` sin distinguir acentos. RED observado en 13 tests de vista. T2 inline: e2e de filtros; las auditorías de `/tareas` fallaban con `label-content-name-mismatch` (WCAG 2.5.3: el botón mostraba "Todas las prioridades" y se llamaba "Filtrar por prioridad"); el nombre accesible pasa a ser "Filtrar por prioridad: Todas las prioridades" (RED observado en la spec de `FiltroMultiple`). Vitest 181/181; Playwright 23/23 contra una pila aislada.
