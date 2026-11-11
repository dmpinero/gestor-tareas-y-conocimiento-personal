# grupos-estados-tablero

Objetivo: grupos de estados definidos en Ajustes, asignables a las tareas, y un tablero por estados donde mover las tareas.
Rama: `feature/grupos-estados-tablero` (desde `main` v1.23.0) · Entrega: `stacked-to-main` (PR backend → PR frontend; si el backend rompe el frontend de `main`, se fusiona el PR superior) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** "quiero que crees una nueva opción dentro de ajustes, que permita crear un grupo de estados. Cada grupo tendrá un nombre y un conjunto de estados."
  - Ajustes → "Grupos de estados": crear, renombrar y borrar grupos; añadir, renombrar, borrar y ordenar (arrastrar y Subir/Bajar, como el workflow) sus estados. El orden solo define el orden de las columnas.
  - Nombres de grupo y de estado: 1–50 caracteres, únicos (grupo entre grupos; estado dentro de su grupo, sin distinguir mayúsculas). (supuesto)
- **S2** "A diferencia del workflow de oportunidades, no hay una secuencia de pasos, sino que se podrá transitar entre cada uno de los pasos definidos en los estados." Cualquier estado del grupo es alcanzable desde cualquier otro.
- **S3** "Cada tarea tendrá asignado uno de los grupo de estados definidos, de forma que heredarán estos estados". Decisión del usuario (L2): la tarea **apunta** al grupo (no copia): cambios en Ajustes se reflejan en sus tareas.
  - Campo opcional "Grupo de estados" en el alta y la edición; al asignar un grupo, la tarea queda en su primer estado; al cambiar de grupo, en el primer estado del nuevo; al quitarlo, sin estado. Las tareas existentes quedan sin grupo. No se puede asignar un grupo sin estados. (supuesto)
  - Borrar un estado con tareas exige elegir a qué otro estado del grupo moverlas; borrar un grupo deja sus tareas sin grupo, avisando cuántas son. (supuesto)
- **S4** "La idea es que luego se puedan visualizar las tareas según los estados, como aparece en la foto, y poder mover las tareas entre estados"
  - En Tareas, alternar Lista / Tablero con dos botones de icono en la barra del listado ("Ver como lista", "Ver como tablero"; ver L3). Tablero: elegir un grupo; una columna por estado con su nombre y contador; tarjetas con nombre, asignados, vencimiento y etiquetas; "Añadir tarea" en cada columna abre el alta con ese grupo y estado. (supuesto, a partir de la imagen)
  - Mover: arrastrar y soltar entre columnas y alternativa de teclado ("Mover a…"). Los filtros y la búsqueda se aplican también al tablero. (supuesto)
- **S6** "quiero un icono para poder ver las tareas en un calendario, cada tarea irá en su día según su fecha de vencimiento"
  - Tercer botón de icono "Ver como calendario" junto a lista y tablero. Vista mensual (semana de lunes a domingo, nombres en español), "Mes anterior", "Mes siguiente", "Hoy"; cada tarea en el día local de su `fecha_vencimiento`, abre el detalle; "+N más" en días con muchas; aviso "N tareas sin fecha de vencimiento"; aplica filtros y búsqueda; en pantallas estrechas, agenda por días. (supuestos; solo frontend)
- **S5** Contrato API (supuesto de diseño):
  - `GET/POST /api/v1/grupos-estados`, `PUT/DELETE /api/v1/grupos-estados/{id}`; cada grupo `{id, nombre, tareas, estados: [{id, nombre, posicion, tareas}]}` (`tareas` = número de tareas).
  - `POST /api/v1/grupos-estados/{id}/estados` `{nombre}` (al final), `PUT .../estados/{id_estado}` `{nombre}`, `DELETE .../estados/{id_estado}?mover_a={id}` (409 si tiene tareas y falta o no vale `mover_a`), `PUT /api/v1/grupos-estados/{id}/orden` `{ids}`.
  - Tarea: cuerpo de alta y edición con `grupo_estados_id: int | null` opcional; respuesta con `grupo_estados: {id, nombre} | null` y `estado: {id, nombre} | null`. `PATCH /api/v1/tareas/{id}/estado` `{estado_id}` → 200 con la tarea; 422 si el estado no es de su grupo o la tarea no tiene grupo.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S1–S3, S5 (backend + migración aditiva) | delegada (writer A, paralelo) | hecha | `39af431` |
| T2 | S1, S3, S4, S6 (frontend: Ajustes, formulario, tablero, calendario) | delegada (writer B, paralelo) | hecha | `28d8fc8`, `05af2c5` |
| T3 | S1–S5 (e2e contra pila aislada) | inline | hecha | `28d8fc8`, `05af2c5` |
| T4 | S1–S5 (verificador: migración, contrato y concurrencia; items 1, 3 y 4) | delegada (verificador) | hecha (sin blockers) | — |

## Log

- **L1** (2026-11-11) Pedido original del usuario (con una captura de un tablero con columnas "PENDIENTE 0", "AXA - ACLARACIÓN DUDAS 0", "EN CURSO 1", tarjetas y "Añadir Tarea"):
  > quiero que en base a la imagen que te he pasado implementes la posibilidad de mover tareas entre estados. Para ello quiero que crees una nueva opción dentro de ajustes, que permita crear un grupo de estados. Cada grupo tendrá un nombre y un conjunto de estados. A diferencia del workflow de oportunidades, no hay una secuencia de pasos, sino que se podrá transitar entre cada uno de los pasos definidos en los estados. Cada tarea tendrá asignado uno de los grupo de estados definidos, de forma que heredarán estos estados (igual que con las tareas y los workflows). La idea es que luego se puedan visualizar las tareas según los estados, como aparece en la foto, y poder mover las tareas entre estados
- **L2** (2026-11-11) Pregunta: ¿la tarea apunta al grupo (recomendado) o guarda una copia fija de los estados, como el workflow? Respuesta: "sí" (a la recomendación: apunta al grupo).
- **L3** (2026-11-11) Precisión del usuario sobre el cambio de vista (afecta a S4):
  > quiero que pongas un icono en la lista de tareas para poder visualizar los estados como si fuera un tablero, o como la lista que se tiene actualmente
  S4 queda: el cambio Lista / Tablero son dos botones de icono ("Ver como lista", "Ver como tablero") en la barra del listado de tareas, con `aria-pressed` en el activo.
- **L4** (2026-11-11) Pedido nuevo del usuario (S6):
  > quiero un icono para poder ver las tareas en un calendario, cada tarea irá en su día según su fecha de vencimiento
- **L5** (2026-11-11) T1: backend 908 tests (98,99 %), contrato 10/10, migración `c8f3a1d5e7b2` aditiva probada con datos; las pruebas de concurrencia encontraron y se corrigieron interbloqueos (orden de bloqueo: grupo antes que tarea). T2: frontend 510 tests. T3: el e2e encontró que el tablero desbordaba la página a 390 px (textos sr-only absolutos fuera del contenedor con scroll); corregido en `05af2c5`. Playwright 47/47 dos veces.
- **L6** (2026-11-11) T4, verificador: S1–S6 en verde, sin blockers. Migración con hashes idénticos y esquema igual tras downgrade; 78 sondas de API; 140 rondas de concurrencia sin 5xx y con el invariante intacto; axe sin violaciones en claro, oscuro y 390 px. Advisories: `mover_a` inválido en un estado sin tareas da 409; el "hoy" del calendario no cambia si la página sigue abierta pasada la medianoche; un downgrade tras usarlo pierde los grupos (documentado).
