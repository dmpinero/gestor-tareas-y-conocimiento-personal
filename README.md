# Gestor de Tareas y Conocimiento Personal

## URLs

| Recurso | Enlace |
| --- | --- |
| Código fuente | Repositorio en GitHub: [github.com/dmpinero/gestor-tareas-y-conocimiento-personal](https://github.com/dmpinero/gestor-tareas-y-conocimiento-personal) |
| Documentación del proyecto | Carpeta [`docs/`](docs) |
| Información del despliegue | Sección [Infraestructura y despliegue](#infraestructura-y-despliegue) de este mismo archivo |

## a. Descripción general del proyecto

Gestor de Tareas y Conocimiento Personal es una aplicación web para
organizar en un único sitio las tareas pendientes y el conocimiento
personal (notas, apuntes y referencias).

Su arquitectura técnica y su forma de trabajar se heredan del proyecto
[gestor-gastos-personal](https://github.com/dmpinero/gestor-gastos-personal):
arquitectura hexagonal con DDD en el backend, barra lateral de iconos y
modo claro/oscuro en el frontend, y el mismo ciclo de calidad (CI, tests,
Pull Requests y releases automáticos).

> Estado actual: esqueleto inicial. Las secciones Tareas y Conocimiento
> existen en la navegación, pero sus funcionalidades se añadirán en
> features posteriores (ver `odd/tasks/`).

## b. Stack tecnológico utilizado

### Backend

| Área | Tecnología |
|---|---|
| Lenguaje / runtime | Python ≥ 3.12 |
| Framework API | FastAPI + Uvicorn |
| Gestor de dependencias | [uv](https://docs.astral.sh/uv/) |
| Base de datos | MySQL 8.4 |
| ORM / migraciones | SQLAlchemy + Alembic |
| Autenticación | Ninguna de momento (los helpers JWT + Argon2 están preparados pero no se usan) |
| Observabilidad | logs JSON estructurados, Sentry, Prometheus, OpenTelemetry |
| Calidad | Ruff (lint + formato), Bandit (SAST), import-linter (capas), pytest + pytest-bdd + pytest-cov, Schemathesis (contrato OpenAPI) |

### Frontend

| Área | Tecnología |
|---|---|
| Framework | Vue 3 (Composition API) + TypeScript |
| Build tool | Vite |
| Estado | Pinia |
| Enrutado | Vue Router |
| Estilos | Tailwind CSS v4 |
| Componentes UI | Reka UI, Lucide (iconos) |
| Gestor de paquetes | pnpm |
| Calidad | ESLint + oxlint, Prettier, vue-tsc (tipos), Vitest (unitarios), Playwright + axe-core (E2E y accesibilidad WCAG 2.1 AA) |

### Infraestructura y despliegue

- **Docker** (multi-stage) para backend y frontend, orquestados con
  `docker-compose.yml` en local (backend + frontend + MySQL + automatizador).
- **Automatizador** (`backend/Dockerfile.automatizador`): servicio aparte con
  Playwright y Chromium para el alta automática de oportunidades (ver
  [Alta de oportunidades](#alta-de-oportunidades)). Solo existe en
  docker-compose; el frontend le reenvía `/api/v1/alta-oportunidades`.
- **nginx** sirve el build estático del frontend y actúa de reverse proxy
  hacia el backend (`/api/v1/*`), con resolución del hostname del backend
  parametrizable por variable de entorno — preparado para desplegarse como
  servicios independientes en plataformas como Railway o Render, además de
  en docker-compose.
- **GitHub Actions**: CI de backend, CI de frontend, tests E2E, análisis de
  seguridad y publicación automática de releases (`semantic-release`).
- **Dependabot** para mantenimiento de dependencias.

#### Despliegue en Railway

El backend y el frontend se despliegan como **dos servicios independientes**
del mismo repositorio (Railway no soporta `docker-compose.yml` de forma
nativa), más una base de datos MySQL gestionada. Cada carpeta ya incluye su
`railway.json` (build con Dockerfile + healthcheck), así que solo hay que
configurar lo siguiente desde el panel:

1. **Crear el proyecto**: "+ New Project" → "Empty project".

2. **Añadir MySQL**: "+ New" → "Database" → MySQL. Railway genera y expone
   sus propias variables de conexión (host, puerto, usuario, contraseña,
   nombre de la base de datos) — visibles en la pestaña **Variables** de
   ese servicio.

3. **Servicio backend**: "+ New" → "GitHub Repo" → este repositorio.
   - **Settings → Service Name**: `backend` (el nombre importa: de él
     depende el hostname interno `backend.railway.internal` que usará el
     frontend).
   - **Settings → Build → Root Directory**: `backend` (ahí detecta
     `backend/railway.json` y el `Dockerfile`).
   - **Variables**:
     - `URL_BASE_DATOS` → referenciando las variables del servicio MySQL,
       p. ej. `mysql+pymysql://${{MySQL.MYSQLUSER}}:${{MySQL.MYSQLPASSWORD}}@${{MySQL.MYSQLHOST}}:${{MySQL.MYSQLPORT}}/${{MySQL.MYSQLDATABASE}}?charset=utf8mb4`
       (usar los nombres reales del paso 2, con el picker de referencias de
       Railway en vez de escribirlos a mano).
     - `ENTORNO=produccion`
     - `CLAVE_SECRETA_JWT` → un valor propio, no el de `.env.example`.
   - No necesita dominio público: solo lo consume el frontend por red
     privada.

4. **Servicio frontend**: "+ New" → "GitHub Repo" → el mismo repositorio.
   - **Settings → Service Name**: `frontend`.
   - **Settings → Build → Root Directory**: `frontend`.
   - **Variables**: `URL_BACKEND=http://backend:8000` (debe coincidir con
     el Service Name del paso 3; nginx lo resuelve de forma dinámica, no
     solo al arrancar, y el puerto público lo asigna Railway automáticamente
     vía la variable `PORT`, que el `Dockerfile` ya respeta).
   - **Settings → Networking**: "Generate Domain" para obtener la URL
     pública (`*.up.railway.app`).

5. **Migraciones**: se aplican solas al arrancar el backend (ver
   `backend/entrypoint.sh`), no requieren ningún paso manual.

## c. Información sobre su instalación y ejecución

### Requisito previo

Tener [Docker](https://www.docker.com/products/docker-desktop/) instalado y
en ejecución (incluye Docker Compose). No es necesario instalar Python, Node
ni MySQL de forma local: todo corre dentro de los contenedores.

### Puesta en marcha con Docker (recomendado)

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/dmpinero/gestor-tareas-y-conocimiento-personal.git
   cd gestor-tareas-y-conocimiento-personal
   ```

2. Crear los ficheros de configuración a partir de los ejemplos (los valores
   por defecto ya sirven para evaluar la aplicación en local):

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. Levantar los servicios (MySQL, backend, automatizador y frontend). La
   primera vez tarda unos minutos porque construye las imágenes:

   ```bash
   docker compose up -d --build
   ```

4. Comprobar que los cuatro contenedores están sanos (columna `STATUS` con
   `(healthy)`; puede tardar hasta medio minuto):

   ```bash
   docker compose ps
   ```

Todos los puertos se publican solo en `127.0.0.1`: la aplicación no tiene
autenticación y el automatizador usa la sesión corporativa del navegador, así
que no se puede abrir desde otros equipos de la red.

### Alta de oportunidades

La primera entrada de la sección **Oportunidades** del menú (`/oportunidades/anes`) da de alta una
oportunidad en Digital Desktop: rellenas los campos variables (código PRJ,
descripción, duración, importe y coste), revisas el resumen y pulsas
«Crear oportunidad». El servicio `automatizador` abre una ventana de Chromium,
rellena el formulario paso a paso y te pregunta en la página todo lo que
necesite (si ya existe una oportunidad con ese PRJ, si hace falta que actúes
en el navegador, y al final si guardar o no). **Nada se guarda sin pulsar
«Guardar»**; después la página muestra la captura del resultado.

Requisitos:

- **Configuración local fuera de git.** La URL, la persona responsable, el
  cliente y el resto de valores fijos son datos corporativos y no están en el
  repositorio. Crea tu archivo a partir del ejemplo y rellénalo con los
  valores reales:

  ```bash
  mkdir -p ~/.config/gestor-tareas
  cp config/alta_oportunidad.ejemplo.json ~/.config/gestor-tareas/alta_oportunidad.json
  # edita ~/.config/gestor-tareas/alta_oportunidad.json
  ```

  Se monta en el servicio en solo lectura (`/config`) y se lee en cada alta,
  así que los cambios no necesitan reiniciar nada. Si falta o no es válido,
  la página explica el motivo y no deja lanzar el alta. Nunca la copies dentro
  del repositorio (`config/*.json` está ignorado salvo el ejemplo). El campo
  opcional `nombre_menu` da nombre a la entrada del alta dentro de la sección
  **Oportunidades** del menú (y al título de la página); si falta,
  se usa «Alta de oportunidades».
- **WSLg** (Windows 11 con WSL 2): la ventana del navegador se muestra en
  Windows a través de la pantalla de WSL (`DISPLAY=:0` y `/tmp/.X11-unix`
  montado en el servicio). Lanza `docker compose` desde WSL.
- **VPN corporativa activa.** Sin ella Digital Desktop responde «Forbidden» y
  la página lo indica.
- **Primer inicio de sesión.** La primera vez inicia sesión en Digital Desktop
  (y en Notion, si dejas la descripción vacía) en la ventana que se abre; la
  página espera hasta 5 minutos. La sesión se guarda en el volumen
  `perfil_navegador`, así que no hay que repetirlo.

#### Alta AXAS MS3

La segunda entrada de la sección, **Oportunidades → Oportunidades AXAS MS3**
(`/oportunidades/axas-ms3`), usa el mismo seguimiento con estas
diferencias:

- En lugar del PRJ se elige un **código de servicio** (p. ej. `AXAS0024`) en un
  combobox. Si no existe, se escribe y se crea desde el propio combobox; la
  página **Ajustes → Códigos de servicio** permite renombrarlos y borrarlos.
  Un código tiene de 2 a 20 caracteres, sin espacios.
- La **descripción es obligatoria** (no se busca en Notion).
- El nombre de la oportunidad (y sus observaciones) es
  `AXAS-MS3-EV` + los 2 últimos caracteres del código (sin guion entre medias) + `-` + la descripción:
  `AXAS0024` y «Migración portal» dan `AXAS-MS3-EV24-Migración portal`.
  Antes de rellenar se busca entre las oportunidades del cliente si ya existe
  una con ese nombre.
- Sus valores fijos van en el bloque opcional `axas_ms3` del mismo archivo de
  configuración (mira el ejemplo): perfil delegado (que también es el
  Responsable), cliente, grupo, tipo, responsables de operaciones y técnico,
  segmentación, área MS3, fase y probabilidad, tipo de servicio, líneas de
  negocio y comunidades. Los campos `*_busqueda` son el texto que se escribe en
  los desplegables que cargan sus opciones al buscar. Si el bloque falta, la
  página lo explica y no deja lanzar el alta; el alta de ANES no cambia.

Solo puede haber un alta a la vez. Los tests y la CI nunca abren un navegador
contra Digital Desktop ni Notion: la automatización se sustituye por dobles.

**Si la página dice «No existe el archivo de configuración» y el archivo sí
existe** en `~/.config/gestor-tareas/alta_oportunidad.json`: con Docker Desktop
y WSL, el montaje de esa carpeta en el contenedor puede quedar vacío. Recrea
solo el servicio (no toca la base de datos ni la sesión guardada del
navegador) y vuelve a cargar la página:

```bash
docker compose up -d --force-recreate automatizador
```

Para comprobar que el contenedor ya ve el archivo, sin mostrar su contenido:

```bash
docker compose exec automatizador test -r /config/alta_oportunidad.json && echo visible
```


### Desarrollo sin Docker

**Backend:**

```bash
cd backend
uv sync
cp .env.example .env   # ajustar URL_BASE_DATOS si no se usa Docker para MySQL
uv run alembic upgrade head
uv run uvicorn gestor_tareas.main:app --reload
```

Calidad y tests:

```bash
uv run ruff check .                              # lint
uv run ruff format .                             # formato
uv run bandit -r src                             # análisis de seguridad estático
uv run lint-imports                              # contrato de capas (arquitectura hexagonal)
uv run pytest tests/unitarios                    # tests unitarios (no tocan la base)
```

> **Cuidado:** los tests de integración, BDD y contrato vacían **todas** las
> tablas de la base de `URL_BASE_DATOS`, que por defecto es la de
> `docker compose`, con los datos reales. Por eso solo arrancan si
> `GESTOR_TESTS_BD_DESECHABLE=1`; sin esa variable, pytest se niega a ejecutarlos.
> El CI la define porque usa su propia base. En local, defínela solo con
> `URL_BASE_DATOS` apuntando a un MySQL aislado:
>
> ```bash
> URL_BASE_DATOS="mysql+pymysql://gestor:gestor@127.0.0.1:3330/gestor_tareas?charset=utf8mb4" \
>   GESTOR_TESTS_BD_DESECHABLE=1 \
>   uv run pytest --cov=src/gestor_tareas --cov-report=term-missing
> ```

**Frontend:**

```bash
cd frontend
pnpm install
cp .env.example .env
pnpm dev
```

Calidad y tests:

```bash
pnpm exec eslint .                               # lint
pnpm type-check                                  # comprobación de tipos
pnpm test:unit run                                # tests unitarios (Vitest)
pnpm exec playwright install --with-deps chromium
pnpm exec playwright test                         # tests E2E + accesibilidad
pnpm build
```

## Git y calidad

- Ramas: GitHub Flow (`feature/<slug>`, `fix/<slug>` desde `main`).
- Commits: [Conventional Commits](https://www.conventionalcommits.org/es/) en español.
- `pre-commit` instalado en el repo (gitleaks, ruff, ESLint, Prettier):
  ```bash
  uv tool install pre-commit   # una sola vez
  pre-commit install
  ```
- Ver [CONTRIBUTING.md](CONTRIBUTING.md) para la convención de idioma, Clean
  Code y el flujo ODD → BDD → TDD.

## Observabilidad

- **Logs**: estructurados en JSON (`infraestructura/observabilidad/registro_logs.py`).
- **Errores**: Sentry (configurable con `SENTRY_DSN`).
- **Métricas**: Prometheus en `/metricas`.
- **Trazas**: OpenTelemetry (configurable con `OTEL_ENDPOINT_EXPORTADOR`).

## Releases

Al fusionar a `main`, `semantic-release` calcula la versión y publica
directamente el release de GitHub agrupado por categorías (sin comitear de
vuelta a `main`, que es una rama protegida). La aplicación lee la versión y el
historial de cambios en vivo desde la API de GitHub. Ver [CONTRIBUTING.md](CONTRIBUTING.md#releases).

## d. Estructura del proyecto

```text
.
├── backend/              API REST (FastAPI) con arquitectura hexagonal
│   ├── src/gestor_tareas/
│   │   ├── dominio/          entidades, puertos y excepciones
│   │   ├── aplicacion/       casos de uso
│   │   ├── infraestructura/  persistencia, observabilidad, seguridad
│   │   └── interfaces/api/   enrutadores, esquemas y middleware
│   ├── alembic/          migraciones
│   └── tests/            unitarios, integración, BDD y contrato
├── frontend/             SPA en Vue 3 + Vite + Tailwind + shadcn-vue
│   ├── src/              componentes, composables, vistas y router
│   └── e2e/              tests Playwright y de accesibilidad
├── docs/                 ciclo de desarrollo y ADRs
├── odd/tasks/            documentos de feature (Specs, Tasks, Log)
└── .github/              workflows de CI/CD y plantillas
```

Ver [docs/adr/0001-arquitectura-hexagonal-y-ddd.md](docs/adr/0001-arquitectura-hexagonal-y-ddd.md)
y [docs/CicloDesarrollo.md](docs/CicloDesarrollo.md).

## e. Funcionalidades principales

- Barra lateral de navegación con iconos, colapsable: Inicio, Tareas,
  Conocimiento y Ajustes.
- Modo claro/oscuro con preferencia persistida y sin parpadeo al cargar.
- Tarea en foco: solo una tarea o subtarea a la vez es la que tienes entre
  manos. Se marca con "Trabajar en esta" (tablero, detalle, subtareas y menú
  "⋯" del listado) y se quita con "Dejar de trabajar"; marcar otra sustituye a
  la anterior. La barra superior muestra en todas las páginas
  `● Trabajando en: Tarea › Subtarea · 1 h 20 min` (al pulsarla se abre la
  tarea; ✕ deja de trabajar en ella), y la tarea o subtarea en foco se resalta
  en violeta con la etiqueta "En foco" y sube al principio de su columna del
  tablero y de su grupo del listado, con cualquier orden (aunque venza más
  tarde). Se guarda en el servidor (tabla `foco_trabajo`, de una sola fila);
  completar la tarea no quita el foco y borrarla sí. API: `GET`/`PUT`/`DELETE
  /api/v1/foco`.
- Historial de foco: cada periodo de foco (inicio, fin y duración) queda
  guardado en la tabla `historial_foco`. El reloj de la barra superior abre
  `/foco/historial`, con dos vistas: **Por día** (día anterior/siguiente,
  selector de fecha, "Hoy" y el total del día) y **Todo** (lista ordenada del
  más reciente al más antiguo). Al pulsar una entrada se abre su tarea; el
  periodo actual aparece "en curso" y las tareas borradas se conservan en gris,
  con el último nombre que tuvieron. API: `GET /api/v1/foco/historial`, con
  `desde` y `hasta` opcionales (instantes ISO con zona; `[desde, hasta)`).
- Conocimiento (chat con tus notas de Notion): en **Conocimiento**, «Sincronizar
  con Notion» copia a la base de datos, en trozos, el texto de las páginas (y
  entradas de bases de datos) que compartas con tu integración de Notion; las
  siguientes veces solo trae lo que cambió y quita lo que ya no compartes. Luego
  preguntas en el chat: el backend busca los trozos más relevantes (búsqueda de
  texto completo de MySQL) y Claude (`claude-opus-5-5`) responde en español solo
  con ellos, en streaming y citando las páginas con enlace a Notion; si no
  encuentra nada lo dice. El contenido de las notas se trata como datos, no
  como instrucciones. La conversación vive en la pestaña («Nueva conversación»
  la vacía). Cada pregunta es una llamada de pago a la API de Anthropic.
  - Configuración: crea una integración interna en
    <https://www.notion.so/my-integrations>, comparte con ella las páginas que
    quieras consultar (menú «⋯» de la página → Conexiones) y pon en
    `backend/.env` `NOTION_TOKEN=<secreto de la integración>` y
    `ANTHROPIC_API_KEY=<tu clave de la API de Anthropic>`; después
    `docker compose up -d --build backend`. Sin ellas, Conocimiento indica qué
    falta. Las claves nunca llegan al navegador.
  - API: `GET /api/v1/conocimiento/estado`, `POST /api/v1/conocimiento/sincronizar`
    y `POST /api/v1/conocimiento/preguntar` (respuesta `text/event-stream` con los
    eventos `fuentes`, `texto`, `fin` o `error`). Tablas `notion_paginas`,
    `notion_fragmentos` (índice FULLTEXT) y `notion_sincronizacion`.
- Vista de red (botón «Ver como red» de Tareas): un grafo con las tareas que
  pasan la búsqueda y los filtros. Cada tarea es un círculo con el color de su
  prioridad; cada etiqueta, persona, subestado u oportunidad que comparten dos o
  más tareas es un nodo propio unido a ellas, y las tareas relacionadas se unen
  directamente. Las casillas eligen qué uniones se ven (se recuerdan). Pasar el
  ratón o enfocar un nodo resalta sus vecinos (con más de 25 tareas, sus
  nombres solo se ven al resaltarlas o al acercar con el zoom, para que no se
  pisen); un clic en una tarea abre su
  detalle y en un nodo propio fija el resaltado de sus tareas. Zoom con botones
  o la rueda, y se arrastra el fondo para moverse. La disposición la calcula
  `d3-force`.
- A continuación y Sugerencias: para saber en qué trabajar después del foco.
  - **A continuación** es la cola de tareas que eliges, en el orden en que
    quieres abordarlas. "Añadir a siguientes" (detalle, tablero y menú "⋯" del
    listado) pone la tarea al final; si ya está, "Quitar de siguientes" la saca.
    Se reordena con las flechas o arrastrando las tareas.
  - **Sugerencias** muestra primero las que has elegido tú ("Elegida por ti",
    en el orden en que las añadiste) y después hasta 5 automáticas: las
    pendientes que vencen antes (las sin vencimiento al final), luego por
    prioridad y por antigüedad, sin las hibernadas, las que están en DONE, las
    de las dos listas ni la del foco.
  - En Inicio, cada tarea es una tarjeta con su prioridad, su fecha y la cuenta
    atrás hasta el vencimiento, y cada sección explica su criterio. La ✕ de una
    tarea de A continuación la pasa a Sugerencias; la ✕ de una elegida la quita
    de Sugerencias.
  - "Buscar tareas" (Inicio) y "Buscar y añadir tareas" (desplegable
    «Siguientes» de la barra superior) abren un buscador para añadir varias a
    **A continuación** o a **Sugerencias**, en el orden en que se marcan. Una
    tarea está como mucho en una de las dos listas: añadirla a una la mueve.
  - El desplegable «Siguientes» enseña las 3 primeras de la cola (también se
    reordenan arrastrando) y "Pasar a la siguiente: X", que la pone en foco.
    Poner en foco una tarea la saca de las listas, borrarla también, y las
    completadas no se ven (si se reabren vuelven a su sitio).
  - Se guarda en la tabla `cola_siguientes` (columna `lista`). API: `GET`/`POST`/
    `PUT /api/v1/siguientes`, `DELETE /api/v1/siguientes/{tarea_id}`,
    `GET`/`POST /api/v1/sugerencias` y `DELETE /api/v1/sugerencias/{tarea_id}`.
- Hibernar una tarea: el botón "Hibernar" (en el detalle, en la tarjeta del
  tablero y en el menú "⋯" del listado) detiene su cuenta atrás
  hasta el vencimiento y pide un comentario opcional, que se guarda como un
  comentario más de la tarea. La tarea muestra la insignia "Hibernada" en el
  listado, el tablero y el detalle, y no avisa de vencimiento mientras duerme.
  "Reanudar" corre la fecha de vencimiento tanto como duró la hibernación, así
  que conserva el tiempo que quedaba. Se puede hibernar y reanudar cuantas
  veces se quiera. API: `POST /api/v1/tareas/{id}/hibernar` (cuerpo
  `{"comentario": ... | null}`) y `POST /api/v1/tareas/{id}/reanudar`; el
  estado hibernado se devuelve en `hibernada_desde`.
- Píldoras pulsables: en el listado, el tablero y el detalle, pulsar una
  etiqueta, una persona, el subestado, la prioridad, el estado del grupo, el
  tipo, "Completada"/"Pendiente" o la insignia "Hibernada" abre una ventana con
  todas las tareas que lo comparten y cuántas son. Las personas y la prioridad
  también listan las subtareas que coinciden. Al pulsar una tarea de la
  ventana, se abre su detalle.
- Tareas relacionadas: en la sección «Tareas relacionadas» del detalle, el botón
  «Relacionar tareas» abre un buscador para elegir una o varias tareas
  existentes. La relación va en ambos sentidos: cada tarea ve a la otra. Pulsar
  una tarea relacionada abre su detalle, y el botón de quitar deshace la
  relación en las dos. Al borrar una tarea desaparece de las relaciones de las
  demás. En el tablero, junto a «Hibernar», el botón 🔗 con el número de
  relacionadas despliega bajo la tarjeta un árbol con ellas, como el de las
  subtareas (aunque sean de otro grupo); pulsar una abre su detalle. API: `POST /api/v1/tareas/{id}/vinculadas` (cuerpo `{"ids": [...]}`)
  y `DELETE /api/v1/tareas/{id}/vinculadas/{vinculada_id}`. Cada tarea devuelve
  sus relaciones en `vinculadas`, una lista de ids.
- Vistas legibles:
  - **Listado:** las insignias van bajo el nombre y la columna "Nombre" se
    queda fija al desplazar la tabla en horizontal. La descripción se corta en
    dos líneas, la fecha de creación se ve corta ("16 nov") y el subestado no
    parte línea; el texto completo sale al pasar el ratón. En pantallas de
    menos de 640 px el listado se muestra en tarjetas.
  - **Tablero:** las tarjetas completadas se atenúan y no muestran la cuenta
    atrás. Comentarios, foco e hibernar aparecen al pasar el ratón o al
    enfocar la tarjeta, salvo con la tarea en foco o hibernada. El subestado
    lleva contorno e icono, y la barra de colores, el título "Tareas por
    estado".
  - **Calendario:** el botón "Ocultar completadas" se recuerda entre visitas.
    Las semanas sin tareas son más bajas y cada tarea lleva el color de su
    prioridad a la izquierda. Pulsar "N tareas sin fecha de vencimiento" las
    lista en una ventana. En la agenda de pantallas estrechas, la navegación
    usa flechas.
  - **Barra superior:** en el móvil, la píldora del foco muestra el nombre de
    la tarea.
- Endpoint de salud `GET /api/v1/salud` y métricas Prometheus en `/metricas`.
- Comentarios de tareas, subtareas y pasos de los workflows con formato
  (negrita, cursiva, subrayado, tachado, color, resaltado, listas y enlaces)
  y capturas de pantalla: se pegan (Ctrl+V), se sueltan o se eligen con el
  botón "Imagen" del editor. Se admiten PNG, JPEG, GIF y WebP de hasta 5 MB,
  reconocidas por su contenido; se guardan en MySQL (tabla `imagenes`, así
  entran en las copias de seguridad) y se sirven en `GET /api/v1/imagenes/{id}`.
  El HTML de los comentarios se sanea en la API y en el navegador: solo se
  admiten imágenes subidas a la propia aplicación. Cada comentario admite de 1
  a 5000 caracteres de texto visible (las imágenes no cuentan) y como mucho
  50000 caracteres de HTML saneado.
- Subestado opcional de cada tarea (como mucho uno), elegido de un catálogo que
  funciona como el de las etiquetas: se escribe en el formulario de la tarea
  (si no existe, se crea al guardar) y se gestiona en **Ajustes → Subestados**
  (`/ajustes/subestados`: crear, renombrar y eliminar; al eliminarlo, sus
  tareas quedan sin subestado). Se muestra como una píldora de color en la
  tabla (columna "Subestado", que se puede ocultar, ordenar, filtrar y
  exportar), en el detalle y en el tablero. "Agrupar por subestado" divide la
  lista en secciones plegables y cada columna del tablero en grupos plegables;
  el botón de la cabecera de cada grupo de la lista (o de cada carril del
  tablero) contrae o expande todos sus subestados a la vez. API: `GET`/`POST
  /api/v1/subestados`, `PUT`/`DELETE /api/v1/subestados/{id}` y el campo
  `subestado` de las tareas.
