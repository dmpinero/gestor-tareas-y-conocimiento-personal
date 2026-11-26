# Tareas relacionadas (vinculadas) entre sí
Objetivo: relacionar tareas entre sí desde el detalle, de forma simétrica. Rama: feat/tareas-vinculadas. Entrega: single-pr.
Tests: backend pytest (unitarios en local; integración SOLO contra MySQL aislado con GESTOR_TESTS_BD_DESECHABLE=1), frontend vitest + playwright.

## Specs
- S1 "en el detalle de una tarea quiero pedir seleccionar una o varias tareas existentes de forma que queden relacionadas".
- S2 Relación "Simple y en ambos sentidos": si se relaciona A con B, B también muestra a A. Sin tipos.
- S3 (supuesto) Desde el detalle se puede quitar una relación; se quita en ambos sentidos.
- S4 (supuesto) Al borrar una tarea desaparecen sus relaciones.
- S5 (supuesto) Pulsar una tarea relacionada abre su detalle.
- Identificadores internos: "vinculadas" (ya existe "tareas relacionadas" para la ventana de píldoras). Texto visible: "Tareas relacionadas".

### Contrato API
- `Tarea` (JSON) añade `vinculadas: number[]` (ids, orden ascendente).
- `POST /api/v1/tareas/{id}/vinculadas` cuerpo `{"ids": [int, ...]}` (≥1) → 200 con la Tarea {id} actualizada. 404 si {id} o algún id no existe; 422 si `ids` incluye {id}; ids ya vinculados se ignoran.
- `DELETE /api/v1/tareas/{id}/vinculadas/{vinculada_id}` → 200 con la Tarea {id}. 404 si alguna de las dos no existe; si no estaban vinculadas, 200 sin cambios.
- Persistencia: tabla `tareas_vinculadas(tarea_id, vinculada_id)` con ambas direcciones, PK compuesta, FKs a tareas.id ON DELETE CASCADE.

## Tasks
- T1 S1-S4 backend (migración, dominio, repositorio, API, tests) — delegado (writer A) — hecho: unitarios 752, suite completa 1657 contra MySQL aislada 3340; migración c4e8a2f6b1d9
- T2 S1-S3,S5 frontend (tipos, store, sección en el detalle, selector, tests) — delegado (writer B) — hecho: vitest 1178, vue-tsc limpio
- T3 integración: inline — hecho: e2e 90 previas OK + 3 nuevas OK tras arreglar el selector (lista con scroll) y dos fallos del propio test

## Log
- L1 (2026-11-26) "quiero poder relacionar tareas entre sí, en el detalle de una tarea quiero pedir seleccionar una o varias tareas existentes de forma que queden relacionadas"
- L2 (2026-11-26) Pregunta tipo de relación → "Simple y en ambos sentidos (Recomendado)".
- L3 Revisión visual: con muchas tareas la lista del selector se salía del diálogo (fieldset con overflow); se cambió por div role=group con scroll y se añadió comprobación e2e.
