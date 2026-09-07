# web - the operator console (Vite dev server).
#
# Deliberately the DEV server, not an nginx-served production build: the
# console is a demo and debugging surface for the next several months, and
# hot reload inside the stack is worth more than a marginally smaller
# image. Swap for a multi-stage nginx build when there is something to
# deploy. See docs/OFFLINE_MODE.md — no CDN references, everything bundled.
#
# Build context is ./web (see docker-compose.yml), not the repo root.

FROM node:20-slim

WORKDIR /app

# Copy manifests first so `npm ci` is cached independently of source
# changes — a source edit should not reinstall node_modules.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# --host binds 0.0.0.0; without it Vite listens on loopback inside the
# container and the published port answers nothing.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
