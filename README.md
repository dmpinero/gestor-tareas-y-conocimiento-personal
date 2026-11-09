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
  `docker-compose.yml` en local (backend + frontend + MySQL).
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

3. Levantar los tres servicios (MySQL, backend y frontend). La primera vez
   tarda unos minutos porque construye las imágenes:

   ```bash
   docker compose up -d --build
   ```

4. Comprobar que los tres contenedores están sanos (columna `STATUS` con
   `(healthy)`; puede tardar hasta medio minuto):

   ```bash
   docker compose ps
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
uv run pytest --cov=src/gestor_tareas --cov-report=term-missing
```

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
- Endpoint de salud `GET /api/v1/salud` y métricas Prometheus en `/metricas`.
