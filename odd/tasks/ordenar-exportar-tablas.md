# ordenar-exportar-tablas

Objetivo: ordenar cualquier tabla de la aplicación por cada uno de sus campos y exportar su listado a Excel o PDF, con piezas reutilizables como en `gestor-gastos-personal`.
Rama: `tablas/pr4-ordenar-exportar` (encadenada sobre `tareas/pr3-fecha-edicion`, #14) · Entrega: `stacked-to-main` · Tests: `pnpm test:unit run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Ordenar: "Quiero poder ordenar las tablas (cualquiera que haya en la aplicación) por cada uno de los campos."
  - Ordenación en el navegador con un composable reutilizable `useOrdenacionTabla(filas, comparadores)` y una cabecera reutilizable `CabeceraOrdenable`, como en la referencia (`src/composables/useOrdenacionTabla.ts`, `src/componentes/compartido/CabeceraOrdenable.vue`).
  - Ciclo: sin orden al empezar (orden original); clic en una columna → ascendente; otro clic en la misma → descendente; clic en otra columna → ascendente en esa. Iconos de `@lucide/vue`: `ChevronsUpDown` inactiva, `ChevronUp` asc, `ChevronDown` desc.
  - La cabecera es un `<button type="button">` cuyo nombre accesible es la etiqueta de la columna; el `<th>` lleva `aria-sort="ascending"`/`"descending"` en la columna activa (supuesto: la referencia no lo tiene; se añade por accesibilidad).
  - No muta el array original.
  - Tareas: todas las columnas de datos son ordenables (Nombre y Descripción con `localeCompare('es')`, Prioridad numérica, Fecha y hora por fecha). La columna Acciones no se ordena.
  - Supuesto: las prioridades vacías van siempre al final, tanto en ascendente como en descendente.
- **S2** Exportar: "quiero poder exportar a Excel o pdf el listado que haya en una tabla, como ya se hace en la aplicación https://github.com/dmpinero/gestor-gastos-personal"
  - Módulo reutilizable `src/lib/exportarTabla.ts` con `exportarTablaExcel(nombreFichero, columnas, filas)` y `exportarTablaPDF(nombreFichero, titulo, columnas, filas)`, que cargan `exceljs`, `jspdf` y `jspdf-autotable` con `import()` dinámico; descarga con `src/lib/descargas.ts` (`descargarBlob`).
  - Componente reutilizable `BotonesExportarTabla` con dos botones de icono: "Exportar a Excel" (`FileSpreadsheet`) y "Exportar a PDF" (`FileText`), con `aria-label` y `title`.
  - Nombre de fichero `<nombreFichero>_ddmmaaaa_hhmmss.xlsx|pdf`.
  - Excel: una hoja "Datos", fila de cabecera en negrita. PDF: título y tabla con `autoTable`; supuesto: orientación apaisada para que quepa la descripción.
  - Se exportan todas las filas en el orden actual de la tabla, con los valores tal como se muestran (prioridad vacía como "—", fecha `dd/mm/aaaa hh:mm:ss`), sin la columna Acciones.
  - Tareas: fichero `Tareas`, título "Tareas".
- **S3** Dependencias como en la referencia: `exceljs ^4.4.0`, `jspdf ^4.2.1`, `jspdf-autotable ^5.0.9`; `core-js: false` en `allowBuilds` y override `dompurify: ">=3.4.17"` en `pnpm-workspace.yaml`.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S3 (dependencias y `pnpm-workspace.yaml`) | inline | hecha (sin commit) | — |
| T2 | S1 (composable `useOrdenacionTabla`, `CabeceraOrdenable` y sus specs) | delegada (writer A, paralelo con T3) | pendiente | — |
| T3 | S2 (`descargas.ts`, `exportarTabla.ts`, `BotonesExportarTabla` y sus specs) | delegada (writer B, paralelo con T2) | pendiente | — |
| T4 | S1–S2 (integración en `VistaTareas`, spec de la vista, e2e de ordenación y descarga) | inline | pendiente | — |
| T5 | S1–S3 (verificador independiente: dependencias nuevas, item 5) | delegada (verificador) | pendiente | — |

Evidencia de ruta: T2 y T3 son unidades independientes con superficies disjuntas (`composables/` + `componentes/compartido/CabeceraOrdenable*` frente a `lib/` + `componentes/compartido/BotonesExportarTabla*`); `VistaTareas.vue` es un fichero compartido y lo integra el padre al final (T4). Las dependencias nuevas son riesgo item 5 → verificador.

## Log

- **L1** (2026-11-09) Pedido original del usuario:
  > Quiero poder ordenar las tablas (cualquiera que haya en la aplicación) por cada uno de los campos. Además, quiero poder exportar a Excel o pdf el listado que haya en una tabla, como ya se hace en la aplicación https://github.com/dmpinero/gestor-gastos-personal
- **L2** (2026-11-09) Mapeo de la referencia: ordenación en cliente con `useOrdenacionTabla` + `CabeceraOrdenable` (asc/desc, sin `aria-sort`); exportación con `exceljs`, `jspdf` y `jspdf-autotable` cargados con `import()`; se exportan todas las filas filtradas y ordenadas, ya formateadas. Usuario: "dale, arrancá con ordenar y exportar".
- **L3** (2026-11-09) T1: `pnpm add` dejó `core-js: set this to true or false` en `pnpm-workspace.yaml`; se corrige a `false` como en la referencia y se añade el override de `dompurify`. `pnpm audit --prod`: 1 moderada en `uuid` (<11.1.1, vía `exceljs`) que solo afecta a v3/v5/v6 con `buf`; `exceljs` usa v4 → no aplica, se deja anotada.
- **L4** (2026-11-09) La base local tiene datos del usuario: los e2e de esta feature se ejecutan contra una pila aislada, nunca contra la base de `docker compose`.
