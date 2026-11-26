# Cola de siguientes tareas ("A continuación")
Objetivo: saber en qué trabajar después del foco actual: cola manual ordenada + sugerencias automáticas. Rama: feat/cola-siguientes. Entrega: single-pr.
Tests: backend pytest (unitarios en local; integración/contrato/bdd SOLO contra MySQL aislado con URL_BASE_DATOS apuntándolo y GESTOR_TESTS_BD_DESECHABLE=1), frontend vitest + vue-tsc + playwright.

## Specs
- S1 "hecho en falta una opción para poder saber en qué debería trabajar luego" / "Me gustaría tener una visión de las próximas tareas que debo abordar". Se implementan las 2 partes propuestas ("vamos con las 2 parts").
- S2 Cola manual: lista ordenada de tareas elegidas por el usuario. Desde una tarea: «Añadir a siguientes» (y, si ya está, «Quitar de siguientes»). Reordenar (subir/bajar) y quitar.
- S3 «Pasar a la siguiente: X»: fija el foco en la primera de la cola y la saca de la cola. Se ofrece en el indicador de foco cuando hay cola.
- S4 Las tareas completadas no aparecen en la cola (si se reabren, vuelven a su sitio). Al borrar una tarea sale de la cola. Al poner en foco una tarea (o una subtarea suya) sale de la cola.
- S5 Sugerencias automáticas debajo de la cola: hasta 5 tareas, ordenadas por vencimiento (más cercano o vencido primero; sin vencimiento al final), después prioridad (1 primero; sin prioridad al final), después fecha de creación (más antigua primero) y id. Excluye completadas, hibernadas, las que están en la cola y la del foco. Un clic («Añadir a siguientes») la sube al final de la cola. Se calculan en el frontend, sin persistir.
- S6 Dónde se ve: panel «A continuación» en Inicio (ruta `/`), con la cola y debajo las sugerencias; y un desplegable en el indicador de foco de la barra superior con las 3 primeras de la cola y «Pasar a la siguiente».

### Contrato API (v1)
- Esquema `TareaSiguiente`: `{"tarea_id": int, "tarea_nombre": str}` (nombre actual).
- `GET /api/v1/siguientes` → 200 `TareaSiguiente[]` en orden de la cola, sin las tareas completadas.
- `POST /api/v1/siguientes` cuerpo `{"tarea_id": int}` → 200 con la cola completa; se añade al final; si ya estaba, no cambia nada. 404 si la tarea no existe; 422 si está completada.
- `PUT /api/v1/siguientes` cuerpo `{"ids": [int, ...]}` → 200 con la cola en el nuevo orden. 422 si `ids` no es exactamente (mismo conjunto, sin repetidos) la cola visible actual. Las entradas ocultas (completadas) quedan detrás.
- `DELETE /api/v1/siguientes/{tarea_id}` → 200 con la cola; idempotente (si no estaba, 200 sin cambios).
- `PUT /api/v1/foco` (existente): además, saca de la cola la tarea puesta en foco, en la misma transacción. Su respuesta no cambia.
- Persistencia: tabla `cola_siguientes(tarea_id INT PK, FK tareas.id ON DELETE CASCADE, posicion INT NOT NULL)`. Migración Alembic nueva con down_revision `c4e8a2f6b1d9`.

### Frontend
- `api/siguientes.ts`, tipo `TareaSiguiente` en `api/tipos.ts`, tienda Pinia `useTiendaSiguientes` (`cola`, `error`, `cargar`, `anadir(id)`, `reordenar(ids)`, `subir(id)`, `bajar(id)`, `quitar(id)`, `estaEnCola(id)`, `pasarALaSiguiente()` que fija el foco en la primera vía la tienda de foco y recarga la cola, `olvidarTarea(id)`), con el mismo patrón `ejecutar` → boolean que `stores/foco.ts`.
- `lib/sugerenciasSiguientes.ts`: función pura con el orden y exclusiones de S5.
- `BotonSiguientes.vue` junto a cada `BotonFoco` de tarea (no de subtarea) en `DetalleTarea.vue` y `TableroTareas.vue`; oculto en tareas completadas. Mismo estilo/props que `BotonFoco` (compacto, nombre accesible).
- Panel en `VistaInicio.vue` (`PanelSiguientes.vue`): título «A continuación»; cada fila: nombre (abre `/tareas?tarea=id`), «Trabajar en esta», subir, bajar, quitar (nombres accesibles con el nombre de la tarea). Vacía: «No hay tareas en la cola.». Sección «Sugerencias» con las de S5 y «Añadir a siguientes»; sin sugerencias: «No hay sugerencias.».
- `IndicadorFoco.vue`: con cola no vacía, botón desplegable «Siguientes» con las 3 primeras y «Pasar a la siguiente: X». Sin foco pero con cola, se muestra igualmente el acceso «Pasar a la siguiente: X».
- Texto visible en español, como el resto de la app. AA de contraste en claro y oscuro.

- S7 "además del nombre de la tarea quiero que muestres el contador para ver cuánto queda para entregar la tarea sugerida (en la opción de Inicio)" / "o que especifiques el criterio por el que propones esas tareas y no otras". Se hacen ambas: contador + prioridad en cada sugerencia y una línea con el criterio.
- S8 "quiero que en A continuación también expliques el criterio y el contador": la cola muestra contador y prioridad por tarea y una línea con su criterio (orden elegido por el usuario).
- S9 "haz que en a continuación y en siguientes también pueda ordenar arrastrando las tareas con el ratón".
- S10 "es bastante fea la tabla de resultados, intenta homogeneizar estilos con el resto de la aplicación" (supuesto: el panel de Inicio): tarjetas como las del tablero, píldora de prioridad, fecha corta + contador, sugerencias en sección propia.
- S11 "pon un buscador para buscar tareas y poder añadir a A continuación o en siguientes. Ponla con el estilo de ventana que pusiste para relacionar tareas".

- S12 "cuando busco una tarea quiero poder pasarla a A continuación o a Sugerencias. Si la añado a A continuación y le doy a la x, que pase a Sugerencias".
  - Sugerencias = primero las **elegidas** por el usuario (en el orden en que se añadieron, sin límite, marcadas «Elegida por ti», cada una con ✕ «Quitar de sugerencias»), después las automáticas de S5 (hasta 5, excluyendo también las elegidas). (supuesto: orden y límite)
  - El buscador tiene dos acciones: «A continuación (n)» y «Sugerencias (n)»; añade al final de la lista elegida, en el orden en que se marcaron. No ofrece completadas ni las que ya están en esa lista de destino (sí las de la otra lista: añadirlas las mueve).
  - La ✕ de una fila de «A continuación» en el panel de Inicio la pasa a las elegidas de Sugerencias (al final). «Quitar de siguientes» del detalle/tablero/menú sigue sacándola del todo.
  - Una tarea está como mucho en una lista: añadirla a una la quita de la otra. Poner en foco la saca de ambas; borrarla también; completadas no se ven en ninguna.

### Contrato API S12 (amplía el v1; nada está publicado aún)
- Tabla `cola_siguientes` gana `lista VARCHAR(20) NOT NULL` con valores `'siguientes'` | `'sugerencias'` (se modifica la migración no publicada `d7f2b9e4a6c1`, sin revisión nueva). `posicion` es por lista. PK sigue siendo `tarea_id` (una lista por tarea).
- `GET /api/v1/siguientes`, `PUT /api/v1/siguientes`, `DELETE /api/v1/siguientes/{tarea_id}`: solo la lista `siguientes` (el PUT valida contra la cola visible de esa lista; DELETE no toca una tarea que está en sugerencias: 200 sin cambios).
- `POST /api/v1/siguientes {"tarea_id"}`: si la tarea está en sugerencias, la mueve al final de siguientes. Respuesta: la cola de siguientes (sin cambios de forma).
- `GET /api/v1/sugerencias` → 200 `TareaSiguiente[]` (elegidas, en orden, sin completadas).
- `POST /api/v1/sugerencias {"tarea_id"}` → 200 con la lista de sugerencias elegidas; al final; si estaba en siguientes la mueve; si ya estaba en sugerencias no cambia. 404 si no existe; 422 si está completada.
- `DELETE /api/v1/sugerencias/{tarea_id}` → 200 con la lista; idempotente; no toca una tarea que está en siguientes.
- `PUT /api/v1/foco`: saca la tarea de la tabla (de cualquiera de las dos listas).

## Tasks
- T1 S2-S4 backend (migración, dominio, aplicación, repositorio, API, foco saca de la cola, tests) — delegado (writer A, paralelo con T2: superficies disjuntas) — hecho 2d86e4e: unitarios 773; suite completa 1708 ok + 1 contrato arreglado (re-verificado solo contrato/API de siguientes y foco); migración d7f2b9e4a6c1
- T2 S2-S3,S5-S6 frontend (api, tienda, lib de sugerencias, botón, panel, indicador, tests unitarios) — delegado (writer B, paralelo con T1) — hecho 4788bf7 (+ opción en MenuAccionesTarea inline): vitest 1223, vue-tsc limpio
- T4 S7 contador, prioridad y criterio en las sugerencias; excluir DONE — inline
- T5 S8 contador, prioridad y criterio en la cola — inline
- T6 S9 arrastrar en panel y desplegable — inline — d7c46ce
- T7 S10 estilos homogéneos en Inicio — inline
- T8 S11 buscador (DialogoElegirTareas común con Relacionar tareas) — inline
- T9 S12 backend (lista en cola_siguientes, /sugerencias, mover entre listas) — delegado (writer C, paralelo con T10)
- T10 S12 frontend (tienda, buscador con dos destinos, ✕ pasa a sugerencias, elegidas en Sugerencias) — delegado (writer D, paralelo con T9)
- T3 integración: e2e, README, vista previa — inline — hecho 7112d17 + arreglo e2e: 4 e2e nuevos ok; suite e2e 96+1, el fallo (historial-foco) era una aserción de URL dependiente del tiempo, corregida (3/3 ok)

## Log
- L1 (2026-11-26) "dime cómo podemos implementar esto. Ahora tengo claro mi tarea actual, con el foco, pero hecho en falta una opción para poder saber en qué debería trabajar luego. ¿Cómo me sugieres que lo implementemos? Me gustaría tener una visión de las próximas tareas que debo abordar"
- L2 (2026-11-26) Propuesta: cola manual + sugerencias automáticas. Respuesta: "vamos con las 2 parts".
- L3 Decisión: completadas se filtran al leer (no se borran) para que reabrir no pierda el sitio; las sugerencias se calculan en el frontend con las tareas ya cargadas.
- L4 E2E historial-foco: Inicio ahora carga las tareas, así que /tareas?tarea=<id> abre el detalle y quita el parámetro al instante; el test comprobaba la URL intermedia. Se comprueba el diálogo y la URL final.
- L5 (2026-11-26) "además del nombre de la tarea quiero que muestres el contador para ver cuánto queda para entregar la tarea sugerida (en la opción de Inicio)" + "o que especifiques el criterio por el que propones esas tareas y no otras".
- L6 En la vista previa una tarea en DONE (no completada, contador congelado) salía sugerida; se excluyen las que tienen congelada_en.
- L7 (2026-11-26) "quiero que en A continuación también expliques el criterio y el contador".
- L8 (2026-11-26) "haz que en a continuación y en siguientes también pueda ordenar arrastrando las tareas con el ratón".
- L9 (2026-11-26) "Por cierto, es bastante fea la tabla de resultados, intenta homogeneizar estilos con el resto de la aplicación".
- L10 (2026-11-26) "pon un buscador para buscar tareas y poder añadir a A continuación o en siguientes. Ponla con el estilo de ventana que pusiste para relacionar tareas". Se extrae DialogoElegirTareas y lo usan ambos selectores.
- L11 (2026-11-26) "cuando busco una tarea quiero poder pasarla a A continuación o a Sugerencias. Si la añado a A continuación y le doy a la x, que pase a Sugerencias".
