# etiquetas-asignados-fechas

Objetivo: añadir a cada tarea etiquetas y personas asignadas (catálogos compartidos que se crean al vuelo), fecha de creación y fecha de vencimiento, ambas elegibles con un calendario.
Rama: `feature/etiquetas-asignados-fechas` (desde `main` v1.6.0) · Entrega: `stacked-to-main` (PR1 backend, PR2 frontend) · Tests: `uv run pytest` (backend), `pnpm test:unit run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Etiquetas: "Listado de etiquetas (se podrán crear tantas etiquetas como se deseen)". Usuario (catálogo): "1." → catálogo compartido.
  - Tabla `etiquetas` (`id`, `nombre` único sin distinguir mayúsculas) y relación N:M con tareas.
  - En el formulario, al escribir se sugieren las existentes; si no existe, se crea al guardar la tarea.
  - Supuestos: nombre de etiqueta obligatorio, recortado, de 1 a 50 caracteres; duplicadas en la misma tarea se ignoran (sin distinguir mayúsculas); se conserva la grafía de la primera vez que se creó; una tarea puede no tener etiquetas.
- **S2** Asignado a: "Asignado a: Se podrán añadir personas dinámicamente". Usuario: "varias".
  - Tabla `personas` (`id`, `nombre` único sin distinguir mayúsculas) y relación N:M con tareas; mismo patrón que S1 (sugerencias + alta al vuelo).
  - Supuestos: una persona es solo un nombre (sin email ni login); 1 a 100 caracteres recortados; duplicadas ignoradas; una tarea puede no tener personas asignadas.
- **S3** Fecha de creación: "Fecha y hora quiero que sea la fecha y hora de creación". Usuario: "2." → editable.
  - El campo `fecha_hora` pasa a llamarse `fecha_creacion` (API, modelo y columna; migración que renombra conservando los datos). Obligatoria; en alta se rellena con la fecha y hora actuales; editable en alta y edición.
  - Etiqueta en la UI: "Fecha de creación".
- **S4** Fecha de vencimiento: "Añade un nuevo campo para la fecha y hora de vencimiento de la tarea". Usuario: "opcional".
  - Campo `fecha_vencimiento` (nullable), mismo formato que `fecha_creacion`.
  - Supuesto: si se indica, no puede ser anterior a `fecha_creacion` (422 con mensaje; el formulario también lo comprueba).
- **S5** Calendario: "Los campos fecha y hora que al crearse o editarse se puedan hacer mediante un componente tipo calendario".
  - Componente reutilizable `SelectorFechaHora`: campo de texto `dd/mm/aaaa hh:mm:ss` (se mantiene la validación existente) más un botón que abre un calendario (`Popover` + `Calendar` de reka-ui/shadcn-vue) con selector de hora, minutos y segundos. Elegir en el calendario rellena el campo; escribir en el campo actualiza el calendario.
  - Semana empezando en lunes y textos en español (`es-ES`). Accesible por teclado.
  - El de vencimiento permite quedar vacío (botón para borrar).
- **S6** Listado, ordenación y exportación (extiende lo existente): columnas Nombre, Prioridad, Descripción, Etiquetas, Asignado a, Fecha de creación, Fecha de vencimiento, Acciones.
  - Etiquetas y personas se muestran como chips; en la exportación y la ordenación se usan unidas por ", " en orden alfabético.
  - Vencimiento vacío se muestra como "—" y en la ordenación va al final en ambos sentidos.
- **S7** Contrato API:
  - Cuerpo de `POST`/`PUT /api/v1/tareas`: `{nombre, prioridad, descripcion, fecha_creacion, fecha_vencimiento: str | null, etiquetas: [str], asignados: [str]}`; `etiquetas` y `asignados` opcionales (por defecto `[]`).
  - Respuesta: igual, con `id`, y `etiquetas`/`asignados` como listas de nombres ordenadas alfabéticamente.
  - `GET /api/v1/etiquetas` y `GET /api/v1/personas` → `200` con `[{"id": int, "nombre": str}]` ordenado por nombre.
  - Las validaciones de texto siguen el contrato OpenAPI (espacios de ECMA-262, `pattern: "\S"`), como en `esquemas/tarea.py`.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S5 (dependencia `@internationalized/date`) | inline | hecha | `3b0178e` |
| T2 | S1–S4, S7 (backend: catálogos, relaciones, renombrado, vencimiento, migración, endpoints, tests) | delegada (writer A, paralelo) | hecha (+ corrección de concurrencia) | `3ff85a3` + corrección |
| T3 | S5 (componentes `ui/popover`, `ui/calendar`, `SelectorFechaHora` y specs) | delegada (writer B, paralelo) | hecha | `34f3d80` |
| T4 | S1–S2 (componente `SelectorEtiquetas` reutilizable: chips + sugerencias + alta al vuelo, specs) | delegada (writer C, paralelo) | hecha | `34f3d80` |
| T5 | S1–S7 (integración en `VistaTareas`, store, tipos, tabla, ordenación, exportación, e2e) | delegada (writer D, por el límite de contexto) + e2e inline | hecha | `34f3d80` |
| T6 | S1–S7 (verificador independiente: migración y cambio de contrato, items 1 y 3) | delegada (verificador) | hecha (1 blocker corregido) | — |

Evidencia de ruta: T2, T3 y T4 son unidades independientes con superficies disjuntas (`backend/`, `componentes/ui/{popover,calendar}` + `SelectorFechaHora`, `SelectorEtiquetas`), cada una de varios cientos de líneas; `VistaTareas.vue` es compartido y lo integra el padre (T5). Riesgo: migración que renombra una columna con datos (item 1) y cambio del contrato público `fecha_hora` → `fecha_creacion` (item 3, pedido) → verificador.

## Log

- **L1** (2026-11-09) Pedido original del usuario:
  > - Crear y editar tarea (etiquetas)
  >     - Incluye los siguientes campos en cada tarea (alta y edición)
  >         - Listado de etiquetas (se podrán crear tantas etiquetas como se deseen)
  >         - Fecha y hora quiero que sea la fecha y hora de creación
  >         - Añade un nuevo campo para la fecha y hora de vencimiento de la tarea
  >         - Los campos fecha y hora que al crearse o editarse se puedan hacer mediante un componente tipo calendario
  >         - Asignado a: Se podrán añadir personas dinámicamente
- **L2** (2026-11-09) Preguntas y respuestas: fecha de creación automática o editable → "2." (editable); vencimiento obligatorio u opcional → "opcional"; etiquetas catálogo compartido o texto libre → "1." (catálogo); una o varias personas asignadas → "varias".
- **L3** (2026-11-09) T1: `pnpm add @internationalized/date@^3.12.4` (la misma que ya trae `reka-ui`); `pnpm audit --prod` sin novedades (solo el aviso conocido de `uuid`).
- **L4** (2026-11-09) La base local tiene datos del usuario: los e2e se ejecutan contra una pila aislada.
- **L5** (2026-11-09) T2 (backend): 188 tests, 97,72 %; migración `c4e2a7d9f1b3` ida y vuelta con datos y `alembic check` sin deriva. Nombres de catálogo con `utf8mb4_0900_as_ci` (sin distinguir mayúsculas, sí acentos). El test de contrato corrige solo las fechas generadas fuera de orden porque JSON Schema no puede comparar dos campos.
- **L6** (2026-11-09) T3 (`SelectorFechaHora`, 16 tests), T4 (`SelectorEtiquetas`, 18 tests), T5 (integración, 150 tests unitarios). e2e contra una pila aislada: 20/20; el primer fallo era del test (el primer "28" de la cuadrícula era del mes anterior y la app rechazó bien ese vencimiento).
- **L7** (2026-11-10) T6, verificador: S3–S7 en verde. Blocker en S1/S2: dos altas simultáneas de la misma etiqueta nueva → 500 (relectura por nombre con la instantánea antigua de REPEATABLE READ y deadlocks 1213 con nombres en orden cruzado).
- **L8** (2026-11-10) Corrección: se enlazan las filas que devuelve `obtener_o_crear` (guardadas en `Session.info`) sin volver a buscarlas por nombre, los nombres nuevos se insertan ordenados por `casefold` y los deadlocks (1213/1205) se reintentan hasta 3 veces en el caso de uso (`ConflictoDeConcurrenciaError`). RED observado con 8 hilos y nombres cruzados. Recomprobación del blocker con las sondas del verificador: `conc.py` 30×201 en todas las rondas, `conc2.py` 200×201; 213 tests, contrato 5/5. Advisories: dos `PUT` simultáneos sobre la misma tarea no se probaron; contraste del botón "Cancelar" en modo oscuro (2,88), ya presente en la base.
- **L9** (2026-11-10) Usuario: "sí, pushea y abre los PRs". PR1 #17 (backend), PR2 (frontend).
