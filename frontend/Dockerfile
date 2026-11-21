FROM node:22-bookworm-slim AS dependencies
WORKDIR /app
COPY package*.json ./
RUN --mount=type=secret,id=custom_ca \
    if [ -f /run/secrets/custom_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/custom_ca; fi; \
    npm ci

FROM dependencies AS development
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dependencies AS checks
COPY . .
CMD ["npm", "run", "check"]

FROM dependencies AS build
COPY . .
RUN npm run build

FROM mcr.microsoft.com/playwright:v1.65.1-noble AS browser
WORKDIR /app
COPY package*.json ./
RUN --mount=type=secret,id=custom_ca \
    if [ -f /run/secrets/custom_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/custom_ca; fi; \
    npm ci
COPY playwright.config.ts ./
COPY e2e ./e2e
CMD ["npm", "run", "test:e2e"]

FROM nginxinc/nginx-unprivileged:1.28-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
