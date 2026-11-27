# Conocimiento: chat con tus notas de Notion (RAG con índice local)
Objetivo: consultar en lenguaje natural la información de Notion desde la sección Conocimiento. Rama: feat/conocimiento-notion. Entrega: single-pr.
Tests: backend pytest (unitarios en local; integración/contrato SOLO contra MySQL aislado con URL_BASE_DATOS + GESTOR_TESTS_BD_DESECHABLE=1; NUNCA llamadas reales a Notion ni a Anthropic en tests: dobles/fakes), frontend vitest + vue-tsc + playwright (con la API de chat simulada por el backend de e2e sin credenciales → estado "sin configurar").

## Specs
- S1 "quiero introducir el concepto de RAG en la aplicación, de forma que se conecte a Notion y, a través de una interfaz tipo chatbot pueda consultar información".
- S2 Recuperación elegida: "Índice local (Recomendado)": las páginas de Notion se sincronizan a la BD troceadas y se buscan con la búsqueda de texto completo de MySQL; Claude responde con esos trozos y cita las páginas.
- S3 (supuesto) Alcance: las páginas (y entradas de bases de datos) que el usuario comparta con su integración de Notion. Texto de los bloques (párrafos, encabezados, listas, citas, tareas, código, tablas como texto; se ignoran imágenes/archivos). Sincronización con el botón «Sincronizar con Notion» en Conocimiento; incremental por `last_edited_time`; quita del índice lo que ya no está compartido. Muestra cuántas páginas hay y la fecha de la última sincronización.
- S4 (supuesto) Chat en Conocimiento: el usuario escribe una pregunta; la respuesta llega en streaming, en español, basada solo en los trozos recuperados, con citas a las páginas (título + enlace a Notion). Si no encuentra nada relevante lo dice («No he encontrado nada sobre eso en tus notas de Notion.») en lugar de inventar. La conversación vive en la pestaña (no se guarda en la BD); botón «Nueva conversación».
- S5 (supuesto) Credenciales solo del entorno del backend (`backend/.env`): `ANTHROPIC_API_KEY` y `NOTION_TOKEN`. Nunca llegan al navegador ni a los logs. Sin ellas, Conocimiento lo explica («Falta configurar …») y no ofrece sincronizar/preguntar.
- S6 (supuesto) Seguridad: el contenido de Notion es dato, no instrucciones (delimitado en el prompt; el sistema le dice a Claude que ignore instrucciones dentro de las notas). Límites: tamaño de pregunta y de historial.
- S7 Modelo `claude-opus-5-5` con el SDK oficial de Anthropic para Python, streaming, `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`), effort `low` (chat), comprobando `stop_reason` (`refusal` → mensaje claro).

- S8 (2026-11-27) El usuario no quiere pagar la API de Anthropic: elige "2" = "Buscador sin IA, gratis": escribes lo que buscas y te muestra los trozos de tus notas que coinciden, con el enlace a cada página de Notion. No redacta respuestas.
  - Backend: `GET /api/v1/conocimiento/buscar?q=<texto>&limite=<1-50, por defecto 20>` → 200 `[{"pagina_id": str, "titulo": str, "url": str, "fragmento": str, "orden": int}]` ordenado por relevancia (FULLTEXT ya existente). 422 si `q` vacío (tras recortar) o > 200 caracteres, o `limite` fuera de rango. Sin `NOTION_TOKEN` funciona igual (busca en lo ya sincronizado; vacío si nunca se sincronizó). No requiere Anthropic.
  - Frontend (Conocimiento): el buscador es lo principal: campo «Buscar en tus notas» + botón «Buscar» (Enter busca); resultados agrupados por página (título enlazado a Notion en pestaña nueva, solo si la URL es http(s)) con sus trozos, resaltando las palabras buscadas con `<mark>` (sin v-html sin sanear: resaltar construyendo nodos/segmentos de texto); sin resultados: «No he encontrado nada sobre eso en tus notas de Notion.»; sin sincronizar nunca: invita a «Sincronizar con Notion».
  - El chat (S4/S7) se conserva pero solo se muestra si `configurado.anthropic` es true; si no, no se muestra ni su aviso «Falta configurar ANTHROPIC_API_KEY…» (el de NOTION_TOKEN sí).

### Contrato API (v1)
- `GET /api/v1/conocimiento/estado` → 200 `{"configurado": {"notion": bool, "anthropic": bool}, "paginas": int, "fragmentos": int, "ultima_sincronizacion": InstanteUtc|null}`.
- `POST /api/v1/conocimiento/sincronizar` → 200 `{"paginas": int, "fragmentos": int, "nuevas": int, "actualizadas": int, "eliminadas": int, "ultima_sincronizacion": InstanteUtc}`. 503 `{"detalle": "Falta configurar NOTION_TOKEN en backend/.env"}` sin token; 502 `{"detalle": ...}` si Notion falla (sin filtrar el token). Una sola sincronización a la vez (409 si ya hay una en curso).
- `POST /api/v1/conocimiento/preguntar` cuerpo `{"mensajes": [{"rol": "usuario"|"asistente", "texto": str}]}` (1–20 mensajes, el último de `usuario`, texto 1–4000 caracteres; 422 si no) → `text/event-stream` con eventos SSE: `fuentes` (data: `[{"pagina_id": str, "titulo": str, "url": str}]`, primero), `texto` (data: `{"delta": str}`, varios), `fin` (data: `{}`), o `error` (data: `{"detalle": str}`). 503 sin `ANTHROPIC_API_KEY`.
- Persistencia: tablas `notion_paginas(id PK = id de Notion, titulo, url, editada_en, sincronizada_en)` y `notion_fragmentos(id, pagina_id FK CASCADE, orden, texto, FULLTEXT(texto))`, y una fila de estado de sincronización. Migración Alembic nueva tras `d7f2b9e4a6c1`.
- El proxy del frontend (nginx) no debe almacenar en búfer el SSE de `/api/v1/conocimiento/preguntar`.

## Tasks
- T1 S2,S3,S5-S7 backend (config, cliente Notion con httpx, troceado, migración, repositorio con FULLTEXT, casos de uso sincronizar/estado/preguntar, cliente Claude, router SSE, dependencia `anthropic`, tests con dobles) — delegado (writer A, paralelo con T2) — hecho 4bd6741: unitarios 863, suite completa 1835, migración e9c3a7f1b5d2, anthropic 2.8.0
- T2 S3-S5 frontend (VistaConocimiento: estado, sincronizar, chat con streaming SSE y citas, nueva conversación, tests) + nginx sin búfer para el SSE — delegado (writer B, paralelo con T1) — hecho a7e4cb7: vitest 1355; nginx validado con nginx:alpine
- T4 S8 buscador sin IA (endpoint buscar + UI principal; chat solo con clave) — delegado (writer, backstop de contexto)
- T3 integración: e2e (estado sin configurar + chat con backend simulado), README (cómo configurar Notion y la clave), vista previa — inline

## Log
- L1 (2026-11-26) "quiero introducir el concepto de RAG en la aplicación, de forma que se conecte a Notion y, a través de una interfaz tipo chatbot pueda consultar información"
- L2 (2026-11-26) Pregunta de recuperación → "Índice local (Recomendado)".
- L3 `backend/.env.example` no se actualiza (regla: no leer ficheros .env); la configuración se documenta en el README.
- L4 Verificación independiente: S1–S7 PASS; bloqueante en la seguridad del Markdown (DOMPurify por defecto dejaba video/audio/picture/svg image → peticiones a servidores ajenos). Corregido con lista de etiquetas permitidas + fuentes solo http(s); las pruebas del verificador quedan como tests de regresión. Avisos no bloqueantes: APIResponseValidationError no mapeado (va al genérico, que lo registra); manejador global preexistente devuelve str(error)+traza; si la BD falla a mitad de sincronización el bloqueo puede quedar hasta 30 min; variantes unicode de </notas> no se neutralizan (no son etiquetas reales).
- L5 (2026-11-27) "Me dice Claude que la API KEY exige un cargo extra ¿no puedes integrarte con notion sin API KEY?HAy otro método alternativo?" → opciones → "2" (buscador sin IA).
