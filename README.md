# Solfège Trainer

This repository contains a solfège web application and its risk prototypes.

Prerequisites:
- Use Docker with Compose v2 for the local stand.
- Read [the current status](docs/STATUS.md) before changing the code.

PHASE 0.5 is complete.
PHASE 0 currently provides a local FastAPI health endpoint and a translated React health page.
Authentication, exercises, database access, and product Telegram import are not available yet.

## Start locally

Do not replace an existing `.env` file.
The following commands assume a new checkout.

```sh
cp .env.example .env
docker compose --env-file .env -f deploy/compose.yaml up --build --wait
```

Open `http://127.0.0.1:18080/`.
The page checks the backend through nginx.

```sh
docker compose --env-file .env -f deploy/compose.yaml down
```

Use `docker-compose` instead of `docker compose` if the standalone v2 executable is installed.
These commands do not change the existing VPS.

## Documentation

- [Developer setup](docs/developer/setup.md)
- [Environment variables](docs/developer/env-variables.md)
- [Architecture](docs/developer/architecture.md)
- [API](docs/developer/api.md)
- [CI and deployment scope](docs/developer/ci-cd.md)
- [Manager checks](docs/user/manager.md)
- [Student checks](docs/user/student.md)
- [Product requirements](docs/PRODUCT_BRIEF.md)
- [Phase plan](docs/PHASES.md)
- [Decisions](docs/DECISIONS.md)

The `prototypes/` directory contains independent, disposable implementations.
The active Telegram prototype stores audio but does not create exercises.
