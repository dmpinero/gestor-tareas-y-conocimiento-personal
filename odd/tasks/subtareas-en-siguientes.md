# Subtareas en la búsqueda de Mi trabajo y en Siguientes
Objetivo: encontrar subtareas desde el buscador de Mi trabajo y poder añadir subtareas (no solo tareas) a A continuación / Sugerencias. Rama: feat/subtareas-en-siguientes. Entrega: single-pr.
Tests: backend pytest (unitarios local; integración/contrato SOLO contra MySQL aislado con URL_BASE_DATOS + GESTOR_TESTS_BD_DESECHABLE=1), frontend vitest + vue-tsc + playwright.

## Specs
- S1 "en el buscador de Mi trabajo y de Siguientes la subtarea Buscar persona fuera de kmm no la encuentra, quiero poder añader tareas o subtareas".
- S2 (supuesto) Buscador de Mi trabajo (vista Tareas: lista y tablero): el texto buscado también coincide con el nombre de las subtareas (sin distinguir mayúsculas ni acentos, como hoy). Se muestra la tarea dueña: en la lista, bajo el nombre de la tarea, una línea «Subtarea: <nombre>» por cada subtarea que coincide; en el tablero, la tarjeta despliega sus subtareas y marca las que coinciden (como hace el filtro de personas). La exportación sigue exportando las filas filtradas.
- S3 (supuesto) Buscador de Siguientes (diálogo «Añadir a siguientes» de Inicio y de la barra superior): ofrece también las subtareas no resueltas de tareas no completadas, mostradas como «Tarea › Subtarea»; la búsqueda encuentra por el nombre de la tarea o de la subtarea; «A continuación (n)» y «Sugerencias (n)» las añaden. «Relacionar tareas» sigue ofreciendo solo tareas.
- S4 (supuesto) Una entrada de A continuación / Sugerencias es una tarea o una subtarea. Se muestran como «Tarea › Subtarea» (contador y prioridad de la tarea dueña). «Trabajar en esta» y «Pasar a la siguiente» ponen en foco la subtarea. Poner en foco una subtarea la saca de las listas y también saca la entrada de su tarea (como hasta ahora); poner en foco una tarea entera saca solo la entrada de la tarea. Las subtareas resueltas, o de tareas completadas, no se ven (si vuelven a estar pendientes vuelven a su sitio). Borrar la subtarea (o la tarea) quita sus entradas. Una entrada está como mucho en una lista. Las sugerencias automáticas siguen siendo solo tareas.

### Contrato API (cambia sobre el v1 publicado; único consumidor: este frontend, se despliegan juntos)
- `TareaSiguiente`: `{"tarea_id": int, "tarea_nombre": str, "subtarea_id": int|null, "subtarea_nombre": str|null}`.
- `POST /api/v1/siguientes` y `POST /api/v1/sugerencias`: cuerpo `{"tarea_id": int, "subtarea_id": int|null (opcional)}`. 404 si la tarea no existe o la subtarea no es de ella; 422 si la tarea está completada o la subtarea resuelta. Mover entre listas igual que hoy.
- `PUT /api/v1/siguientes`: cuerpo `{"entradas": [{"tarea_id": int, "subtarea_id": int|null}, ...]}` (sustituye a `ids`); 422 si no es exactamente la cola visible.
- `DELETE /api/v1/siguientes/{tarea_id}` y `DELETE /api/v1/sugerencias/{tarea_id}`: query opcional `subtarea_id`; sin ella, la entrada de la tarea entera. Idempotentes.
- `PUT /api/v1/foco`: con `subtarea_id` saca de las listas esa subtarea y la tarea entera; sin él, solo la tarea entera.
- Persistencia: `cola_siguientes` gana `subtarea_id INT NULL` (FK a la tabla de subtareas ON DELETE CASCADE) y deja de tener `tarea_id` como PK: id propio autoincremental + unicidad por (tarea_id, subtarea_id) que funcione con NULL (p. ej. columna generada `COALESCE(subtarea_id, 0)`). Migración nueva tras `e9c3a7f1b5d2`, conservando las filas existentes (como entradas de tarea entera).

## Tasks
- T1 S4 backend (migración, dominio, repositorio, API, foco) — delegado (writer A, paralelo con T2) — hecho 784b987: unitarios 899, suite completa 1906, migración a3d8f5c2e7b9 (columna generada VIRTUAL)
- T2 S2-S4 frontend (búsqueda por subtareas en Mi trabajo, diálogo con subtareas, tienda/panel/indicador con entradas de subtarea) — delegado (writer B, paralelo con T1) — hecho 97ca209: vitest 1423
- T3 integración: e2e, README, vista previa — inline

## Log
- L1 (2026-11-27) "en el buscador de Mi trabajo y de Siguientes la subtarea Buscar persona fuera de kmm no la encuentra, quiero poder añader tareas o subtareas"
- L2 Hallazgo: la lista de Mi trabajo ya encontraba subtareas por nombre (sin mostrarlo); el tablero no. Ahora ambos lo muestran.
