# workflow-oportunidades

Objetivo: definir en Ajustes el workflow de pasos estándar de las oportunidades (con reordenación drag & drop) y generar esos pasos en cada tarea de tipo Oportunidad nueva, con su avance.
Rama: `feature/workflow-oportunidades` (worktree; encadenada sobre `feature/tarea-completada`) · Entrega: `stacked-to-main` (D1 workflow → D2 relación con las tareas) · Tests: `uv run pytest`, `pnpm test:unit run` + `pnpm exec playwright test`

## Specs

- **S1** Opción en Ajustes: "Quiero que dentro de ajustes crees una nueva opción denominada Workflow Oportunidades. Este workflow representará un conjunto de tareas estándar que se realizan en orden secuencial."
  - En `VistaAjustes` aparece un enlace "Workflow Oportunidades" a la ruta `/ajustes/workflow-oportunidades` (vista `VistaWorkflowOportunidades`). Un único workflow (supuesto).
- **S2** Pasos: "Cada una de las tareas de este workflow tendrá los siguientes campos - Nombre del paso: 50 caracteres (obligatorio) - Número del paso: Numérico (autonumérico)". "Cada vez que se cree un paso será continuación del anterior."
  - Nombre recortado (espacios de ECMA-262, `pattern: "\S"` en el contrato, como en `esquemas/tarea.py`), 1–50 caracteres. Número = posición 1..n asignada por el sistema; un paso nuevo va al final.
  - Supuestos (aceptados por el usuario: "Implementa la relación con las tareas tal y como lo has descrito"): los pasos se pueden renombrar y eliminar; al eliminar uno, los siguientes se renumeran.
- **S3** Reordenar: "Me gustaría contar con un sistema Drag & Drop para poder reordenar los pasos dinámicamente."
  - Drag & drop con la API nativa del navegador (sin librerías nuevas) y, por accesibilidad, botones "Subir"/"Bajar" por paso. Al reordenar se recalculan los números y se guarda el nuevo orden.
- **S4** Relación con las tareas (propuesta aceptada: "sí, hazlo así"):
  1. Al crear una tarea de tipo Oportunidad se le copian los pasos del workflow vigente, en el mismo orden y con su número.
  2. Copia fija: cambiar el workflow después no altera las tareas existentes; solo las nuevas usan la versión actualizada.
  3. Cada paso de la tarea se marca hecho/pendiente; el detalle muestra la lista con su estado y la tabla un resumen junto al tipo: "Oportunidad · 3/7".
  4. Las oportunidades existentes no reciben pasos automáticamente.
  5. Si una tarea deja de ser Oportunidad, sus pasos se borran (como sus datos de oportunidad).
- **S5** Contrato API (supuesto de diseño):
  - Workflow: `GET /api/v1/workflow-oportunidades/pasos` → `[{id, numero, nombre}]` por número; `POST .../pasos` `{nombre}` → 201 (al final); `PUT .../pasos/{id}` `{nombre}` → 200; `DELETE .../pasos/{id}` → 204 (renumera); `PUT .../pasos/orden` `{ids: [..]}` → 200 con la lista (debe contener exactamente todos los ids; si no, 422).
  - Tareas: las respuestas incluyen `pasos_oportunidad: [{id, numero, nombre, hecho}]` (vacía si no es oportunidad o no tiene pasos); `PATCH /api/v1/tareas/{id}/pasos/{id_paso}` `{hecho: bool}` (booleano estricto) → 200 con la tarea; 404 si no existen o el paso no es de la tarea.

## Tasks

| ID | Specs | Ruta | Estado | Commit |
|---|---|---|---|---|
| T1 | S2, S3, S5 (backend del workflow: tabla, migración, endpoints, reordenación transaccional, tests) | delegada (writer A, paralelo con T2) | hecha | `a45fa84` |
| T2 | S1–S3 (frontend del workflow: enlace en Ajustes, ruta, vista con alta/renombrar/borrar, drag & drop + Subir/Bajar, specs) | delegada (writer B, paralelo con T1) | hecha | `b0e5408` + corrección de foco |
| T3 | S4, S5 (backend de la relación: tabla de pasos de tarea, copia al crear, borrado al cambiar de tipo, PATCH hecho, tests) | delegada (writer C, paralelo con T4) | hecha | `655cc78` |
| T4 | S4 (frontend de la relación: resumen "Oportunidad · x/n", lista con casillas en el detalle, store, specs) | delegada (writer D, paralelo con T3) | hecha | `da013bb` |
| T5 | S1–S5 (e2e contra pila aislada) | inline | hecha | `81e271c` |
| T6 | S1–S5 (verificador independiente: migraciones, contrato y concurrencia del reordenado, items 1, 3 y 4) | delegada (verificador) | hecha (1 blocker corregido) | — |

Evidencia de ruta: en cada entrega, backend y frontend son unidades independientes con superficies disjuntas y contrato fijado en S5. Riesgo: migraciones nuevas (item 1), contrato ampliado (item 3), reordenación concurrente (item 4) → verificador.

## Log

- **L1** (2026-11-10) Pedido original del usuario:
  > - Quiero que dentro de ajustes crees una nueva opción denominada Workflow Oportunidades. Este workflow representará un conjunto de tareas estándar
  > que se realizan en orden secuencial. Cada una de las tareas de este workflow tendrá los siguientes campos
  >     - Nombre del paso: 50 caracteres (obligatorio)
  >     - Número del paso: Numérico (autonumérico)
  >
  >     Cada vez que se cree un paso será continuación del anterior. Me gustaría contar con un sistema Drag & Drop para poder reordenar los pasos dinámicamente.
- **L2** (2026-11-10) Usuario: "Implementa la relación con las tareas tal y como lo has descrito". Propuesta concreta (copia fija, avance hecho/pendiente, resumen x/n, sin retroactividad, borrado al cambiar de tipo) → usuario: "sí, hazlo así".
- **L3** (2026-11-10) Se trabaja en un worktree aparte para no bloquear correcciones de `feature/tarea-completada`, que está en verificación.
- **L4** (2026-11-10) T1 (writer A): tabla `pasos_workflow_oportunidades` (migración `b6d2f8a4c1e9`), endpoints de S5; alta, borrado y reordenación serializados con un bloqueo con nombre de MySQL + `FOR UPDATE` y renumeración en dos fases (la unicidad de `numero` no choca). El test de concurrencia falla sin los bloqueos. T2 (writer B): enlace en Ajustes, vista con alta, renombrado, borrado con confirmación, drag & drop nativo, Subir/Bajar y anuncio `aria-live`.
- **L5** (2026-11-10) T3 (writer C): tabla `pasos_tarea` (migración `d9a4c2e7f1b5`), copia al crear una oportunidad leyendo el workflow con `FOR SHARE`, borrado al dejar de ser oportunidad, sin generación al pasar a oportunidad (regla 4), `PATCH /tareas/{id}/pasos/{id_paso}`. T4 (writer D): "Oportunidad · x/n" en la tabla y casillas en el detalle. T5: e2e de las dos entregas; Playwright 32/32 dos veces. Backend 469 tests, 98,17 %; Vitest 309.
- **L6** (2026-11-10) T6, verificador: S1, S2, S4 y S5 en verde; migraciones con datos idénticos y esquema idéntico tras el downgrade; cientos de pedidos en paralelo sin 5xx ni copias a medio reordenar. Blocker B1 (S3): tras Subir/Bajar con el teclado el foco caía en el <body> porque el botón pulsado se desactiva mientras se guarda. Corregido: el foco vuelve al botón del paso movido (o al otro en los extremos) y, tras eliminar, al campo de alta; RED observado en 3 tests unitarios y e2e de teclado en Chromium. Vitest 312/312, Playwright 33/33. Advisories sin cambios: un fallo al liberar el bloqueo da 500 (sin datos escritos ni bloqueo retenido); `maxlength` cuenta unidades UTF-16; el error del almacén puede verse en el detalle; sin protección ante doble clic en casillas y arrastres.
