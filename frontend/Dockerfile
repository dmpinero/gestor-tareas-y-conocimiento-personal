FROM node:26-slim AS construccion

# Node ya no incluye corepack preinstalado desde esta version (ver
# https://github.com/nodejs/corepack); hay que instalarlo explicitamente
# antes de poder activarlo.
RUN npm install -g corepack@latest && corepack enable

WORKDIR /aplicacion

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:alpine AS produccion

# URL_BACKEND se sustituye en nginx.conf.template al arrancar el contenedor
# (envsubst, soportado de forma nativa por la imagen oficial de nginx para
# cualquier fichero en /etc/nginx/templates/). El valor por defecto es el
# que resuelve dentro de la red de docker-compose; en despliegues donde
# backend y frontend no comparten red (p. ej. Render, cada uno como
# servicio independiente) hay que sobreescribirla con la URL pública real
# del backend.
ENV URL_BACKEND=http://backend:8000

# Puerto en el que escucha nginx dentro del contenedor. Por defecto 80 (el
# que mapea docker-compose.yml); en plataformas que asignan el puerto
# dinamicamente e inyectan su propia variable PORT (p. ej. Railway), esta
# la sobreescribe automaticamente sin tocar nada mas.
ENV PORT=80

# Activa el script de arranque que detecta el/los resolver(es) DNS locales
# del contenedor (desde /etc/resolv.conf) y los expone como
# NGINX_LOCAL_RESOLVERS, usado en nginx.conf.template para resolver el
# backend de forma dinamica en vez de una sola vez al arrancar.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=construccion /aplicacion/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
