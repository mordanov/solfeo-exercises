FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS build
WORKDIR /app
RUN npm install --global npm@12.1.0 --no-audit --no-fund
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
RUN npm ci --no-audit --no-fund
COPY frontend frontend
ARG VITE_DEFAULT_LANGUAGE=en
ARG VITE_HEALTH_TIMEOUT_MS=5000
ENV VITE_DEFAULT_LANGUAGE=$VITE_DEFAULT_LANGUAGE VITE_HEALTH_TIMEOUT_MS=$VITE_HEALTH_TIMEOUT_MS
RUN npm run build

FROM nginx:stable-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
COPY deploy/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/nginx-start.sh /usr/local/bin/solfeo-nginx-start.sh
COPY --from=build /app/frontend/dist /usr/share/nginx/html
ENV LOGIN_NGINX_RATE_PER_SECOND=5 LOGIN_NGINX_BURST=10
USER nginx
ENTRYPOINT ["/bin/sh", "/usr/local/bin/solfeo-nginx-start.sh"]
