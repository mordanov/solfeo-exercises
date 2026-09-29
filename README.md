# Solfège Trainer

This repository contains a solfège web application and its risk prototypes.

Prerequisites:
- Use Docker with Compose v2 for the local stand.
- Read [the current status](docs/STATUS.md) before changing the code.

PHASE 0.5 is complete.
PHASE 0 provides the deployed health page, PostgreSQL, and targeted CI/CD.
PHASE 1 adds cookie authentication, manager user administration, persisted settings, and emergency recovery.
PHASE 2 adds exercise management, protected original images, and converted AAC audio with seeking.
PHASE 3 adds student listening, saved sequence position, random selection, and the manager listening journal.
Product Telegram import remains in PHASE 4.

## Start locally

Do not replace an existing `.env` file.
The following commands assume a new checkout.

```sh
umask 077
cp .env.example .env
printf '\nDATABASE_PASSWORD=%s\n' "$(openssl rand -hex 32)" >> .env
docker compose --env-file .env -f deploy/compose.yaml up --build --wait
```

Open `http://127.0.0.1:18080/`.
The page checks the backend through nginx.
Compose runs migrations before starting the backend.
Keep the generated password private and unchanged when reusing the database volume.
The shutdown command preserves database and media volumes.

```sh
docker compose --env-file .env -f deploy/compose.yaml down
```

Use `docker-compose` instead of `docker compose` if the standalone v2 executable is installed.
These commands do not change the existing VPS.

## Checks before commits

Install the repository hook after preparing developer dependencies.
The [setup guide](docs/developer/setup.md#enable-checks-before-commits) lists prerequisites and correction commands.

```sh
uv run --locked pre-commit install --install-hooks
uv run --locked pre-commit run --all-files
```

The same hooks run in CI.
Database tests and application builds remain separate checks.
Successful main-branch CI authorizes the product publication workflow.
The publication workflow calls targeted CD after verifying the release bundle.

## Documentation

- [Developer setup](docs/developer/setup.md)
- [Environment variables](docs/developer/env-variables.md)
- [Architecture](docs/developer/architecture.md)
- [API](docs/developer/api.md)
- [Authentication and emergency recovery](docs/developer/auth.md)
- [Database and migrations](docs/developer/data-model.md)
- [Uploads and protected storage](docs/developer/storage.md)
- [Listening and journal events](docs/developer/listening.md)
- [Production configuration and deployment boundaries](docs/developer/deploy.md)
- [CI and deployment scope](docs/developer/ci-cd.md)
- [Manager checks](docs/user/manager.md)
- [Student checks](docs/user/student.md)
- [Product requirements](docs/PRODUCT_BRIEF.md)
- [Phase plan](docs/PHASES.md)
- [Decisions](docs/DECISIONS.md)

The `prototypes/` directory contains independent, disposable implementations.
The active Telegram prototype stores audio but does not create exercises.
