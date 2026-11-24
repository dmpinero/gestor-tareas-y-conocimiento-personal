# oportunidades-axas-ms3

Objetivo: segunda opción de alta en el apartado Oportunidades, "Oportunidades AXAS MS3", basada en el script de Oportunidades (ANES), con un catálogo administrable de códigos de servicio.
Rama: `feat/oportunidades-axas-ms3` · Entrega: `single-pr` (una PR, como el resto de peticiones del usuario) · Tests: `uv run pytest` (backend), `pnpm exec vitest run` + `pnpm exec playwright test` (frontend)

## Specs

- **S1** Opción de menú: "Quiero que crees dentro del apartado Oportunidades otra opción llamada Oportunidades AXAS MS3. Básate en el script actual de Oportunidades para ir preguntándome qué cambiar y qué mantener"
  - Segundo enlace en el grupo "Oportunidades" de la barra lateral. Su etiqueta sale del `nombre_menu` del bloque AXAS MS3 de la configuración, como la de ANES (supuesto).
- **S2** Código de servicio: "Se seleccionará primero en un componente tipo "Combobox" el código de servicio, que será administrable, es decir que permitirá crear nuevos elementos. De este campo cogerás los 2 últimos dígitos o letras, lo que tengas."
  - Ejemplos del usuario: "AXAS0024, AXAS0025, AXAS0026".
  - Decisión del usuario (opción 1): se crean desde el combobox (`Crear "…"`) y además se editan y borran en una página de Ajustes "Códigos de servicio", como la de subestados.
  - Validación: al menos 2 caracteres, sin espacios. No se impone el formato AXAS + 4 dígitos.
- **S3** "La descripción será obligatoria". No se busca en Notion.
- **S4** Nombre: "El campo Nombre (lo que ahora muestras en Qué se va a crear) será este literal AXAS-MS3-EV- concatenado por los 2 últimos digitos o letras y concatenado con un guión y la descripción". Ejemplo: `AXAS0024` + "Migración portal" → `AXAS-MS3-EV-24-Migración portal`.
- **S5** Valores fijos (decisión del usuario, opción 1: van como un segundo bloque en el JSON privado `~/.config/gestor-tareas/alta_oportunidad.json`, que el usuario rellena; el ejemplo del repo documenta la estructura con valores ficticios):
  - "El campo Esquema Nacional de Seguridad (ENS) elegido a NO"
  - "El campo RGPD elegido a NO"
  - "El campo Cliente será [AXAS] AXA SEGUROS GENERALES, S.A."
  - "El campo Grupo será Spain"
  - "El campo Tipos será Desarrollo"
  - "El campo Oservaciones será igual que el campo nombre"
  - "El campo Responsable de Operaciones será Carmen María Campomanes De la Huerga"
  - "El campo Responsable será Jose Manuel Viega Cejalvo"
  - "El campo Responsable técnico será Javier Rodriguez Aguilar"
  - "El campo Segmentación será Cliente Nuevo / Nuevo Negocio"
  - "El campo Área MS3 será Desarrollo"
  - "El campo Fase y probabilidad 1 - Cualificación · 50 %"
  - "El campo Tipo de servicio será MS3 Application Management"
  - "El campo ¿Colabora algún otro Delivery Units? será No, solo Spain"
  - "El campo Líneas de negocio será Industrialization (100 %)"
  - "El campo Comunidades Java (80 %), Project Managers (20 %)"
- **S6** Igual que ANES:
  - "El campo Duración como el del script Oportunidades (ANES)"
  - "El campo Importe total previsto será como el del script Oportunidades (ANES)"
  - "El campo Coste total previsto será como el del script Oportunidades (ANES)"
  - "El campo Fecha límite y fecha de inicio con la misma lógica del script Oportunidades (ANES)"
  - Supuesto: "No genera pipeline" desmarcado, como en ANES.
- **S7** Duplicados (decisión del usuario, opción 1): se buscan las oportunidades del cliente y se avisa si ya existe una con el nombre completo `AXAS-MS3-EV-XX-descripción`.
- **S8** Perfil (decisión del usuario, opción 1): el script cambia al perfil delegado de Jose Manuel Viega Cejalvo, que es también el Responsable.
- **S9** Formulario real (verificado con inspecciones de solo lectura, sin guardar):
  - El grupo corporativo se elige antes que el cliente (indicación del usuario: "selecciona antes el grupo corporativo para evitar errores").
  - Cliente, Responsable y Responsable técnico cargan las opciones al escribir: hay que buscar.
  - `comboRespOperacionesG` es Responsable de Operaciones y `comboRespTecnicoG` es Responsable técnico, ambos en "Personas de contactos".
  - `comboAreaMs3` (Área MS3) está en "Más datos" y solo aparece después de añadir el tipo de servicio MS3. Sus opciones son Atlassian, Cloud y Desarrollo, y su contenedor chosen tiene ancho 0.
  - Todos los textos exactos de S5 existen como opción en su desplegable.

## Tasks

- [x] T1 (S2) Catálogo de códigos de servicio en el backend: migración `d4e8a2c6f1b3`, modelo, repositorio genérico compartido con subestados y CRUD `/codigos-servicio`. Ruta: delegada, writer A, en paralelo con T3 (trigger: dos unidades independientes, más el límite de contexto). Risk: item 1 (migración nueva, solo añade una tabla). Commit 1.
- [x] T2 (S2) Frontend del catálogo: tienda, validador y página de Ajustes "Códigos de servicio". Ruta: delegada, writer A. Commit 3.
- [x] T3 (S3–S9) Automatizador: bloque `axas_ms3` opcional, variante de alta, duplicado por nombre completo, relleno de MS3 (grupo antes que cliente, Área MS3 tras añadir el tipo de servicio) y API `…/axas-ms3/*`. Ruta: delegada, writer B. Risk: item 3 (cambian las firmas de `cambiar_perfil` y `existe_oportunidad`; test de regresión de ANES) e item 6 (el relleno con Playwright no tiene tests, por diseño). Commit 2.
- [x] T4 (S1–S4, S6) Frontend del alta AXAS MS3: `ComboboxCodigoServicio`, `VistaOportunidades` con la prop `variante` (recarga al cambiarla e ignora respuestas tardías), enlace del menú (solo se marca el más específico) y ruta `/tareas/oportunidades/axas-ms3`. Ruta: inline. Commit 3.
- [x] T5 README, ejemplo de configuración y e2e (`oportunidades-axas-ms3.spec.ts`, 5 tests). Pendiente al publicar: backup de la base de datos antes de aplicar la migración en el entorno local. Commit 3.

## Log

- **L1** (2026-11-23) Petición original:
  "Quiero que crees dentro del apartado Oportunidades otra opción llamada Oportunidades AXAS MS3. Básate en el script actual de Oportunidades para ir preguntándome qué cambiar y qué mantener

  De momento lo que cambia es esto.

  Se seleccionará primero en un componente tipo "Combobox" el código de servicio, que será administrable, es decir que permitirá crear nuevos elementos. De este campo cogerás los 2 últimos dígitos o letras, lo que tengas.

  La descripción será obligatoria

  El campo Nombre (lo que ahora muestras en Qué se va a crear) será este literal AXAS-MS3-EV- concatenado por los 2 últimos digitos o letras y concatenado con un guión y la descripción
  El campo Esquema Nacional de Seguridad (ENS) elegido a NO
  El campo RGPD elegido a NO
  El campo Cliente será [AXAS] AXA SEGUROS GENERALES, S.A.
  El campo Grupo será Spain
  El campo Tipos será Desarrollo
  El campo Oservaciones será igual que el campo nombre
  El campo Responsable de Operaciones será Carmen María Campomanes De la Huerga
  El campo Responsable será Jose Manuel Viega Cejalvo
  El campo Responsable técnico será Javier Rodriguez Aguilar
  El campo Segmentación será Cliente Nuevo / Nuevo Negocio
  El campo Área MS3 será Desarrollo
  El campo Fase y probabilidad 1 - Cualificación · 50 %
  El campo Tipo de servicio será MS3 Application Management
  El campo Duración como el del script Oportunidades (ANES)
  El campo Importe total previsto será como el del script Oportunidades (ANES)
  El campo Coste total previsto será como el del script Oportunidades (ANES)
  El campo ¿Colabora algún otro Delivery Units? será No, solo Spain
  El campo Líneas de negocio será Industrialization (100 %)
  El campo Comunidades Java (80 %), Project Managers (20 %)
  El campo Fecha límite y fecha de inicio con la misma lógica del script Oportunidades (ANES)"
- **L2** Decisiones del usuario: valores en el JSON privado (1); duplicados por el nombre completo (1); perfil de Jose Manuel Viega Cejalvo (1); códigos de servicio administrables desde el combobox y desde Ajustes (1). Indicación: "selecciona antes el grupo corporativo para evitar errores".
- **L3** Cinco inspecciones de solo lectura del formulario de Digital Desktop, ejecutadas con el automatizador; el usuario inició sesión en cada una y no se guardó nada. Resultados en S9.
- **L4** Verificación:
  - Backend: 1490 tests contra MySQL desechable, ruff, formato e import-linter limpios.
  - Frontend: 979 tests; vue-tsc, ESLint y Prettier limpios.
  - e2e en stack aislado: 78/78.
  - Verificador independiente: sin bloqueos; ANES idéntico a `main` según una sonda diferencial.
  - Observaciones aplicadas: se ignora la respuesta tardía al cambiar de variante, y el endpoint de lanzar limita el código a 20 caracteres como el catálogo (los dos con test en RED primero).
  - Observación descartada: el catálogo acepta `\x85` dentro de un código, que en la práctica no se da.
