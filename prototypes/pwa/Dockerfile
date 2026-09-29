FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_DEFAULT_LANGUAGE=en
ARG VITE_MAX_SHARE_BYTES=26214400
ARG VITE_SW_READY_TIMEOUT_MS=15000
ENV VITE_DEFAULT_LANGUAGE=$VITE_DEFAULT_LANGUAGE \
    VITE_MAX_SHARE_BYTES=$VITE_MAX_SHARE_BYTES \
    VITE_SW_READY_TIMEOUT_MS=$VITE_SW_READY_TIMEOUT_MS
RUN npm run build

FROM nginx:stable-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/prototype-share/
