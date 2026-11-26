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

## Tasks
- T1 S2-S4 backend (migración, dominio, aplicación, repositorio, API, foco saca de la cola, tests) — delegado (writer A, paralelo con T2: superficies disjuntas)
- T2 S2-S3,S5-S6 frontend (api, tienda, lib de sugerencias, botón, panel, indicador, tests unitarios) — delegado (writer B, paralelo con T1)
- T3 integración: e2e, README, vista previa — inline

## Log
- L1 (2026-11-26) "dime cómo podemos implementar esto. Ahora tengo claro mi tarea actual, con el foco, pero hecho en falta una opción para poder saber en qué debería trabajar luego. ¿Cómo me sugieres que lo implementemos? Me gustaría tener una visión de las próximas tareas que debo abordar"
- L2 (2026-11-26) Propuesta: cola manual + sugerencias automáticas. Respuesta: "vamos con las 2 parts".
- L3 Decisión: completadas se filtran al leer (no se borran) para que reabrir no pierda el sitio; las sugerencias se calculan en el frontend con las tareas ya cargadas.
