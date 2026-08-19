# TazaBAK EcoFin — frontend.
#
# Сборка отдельным этапом: node_modules весит сотни мегабайт и в финальном
# образе не нужен — наружу уезжает только каталог dist под nginx.
FROM node:20-alpine AS build

WORKDIR /app

# Ставим по package-lock, а не по package.json: жюри должно собрать ровно те
# версии, на которых мы проверяли экраны.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Адрес backend вшивается в бандл на этапе сборки — Vite подставляет
# import.meta.env во время компиляции, менять его в рантайме уже нельзя.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build


FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
