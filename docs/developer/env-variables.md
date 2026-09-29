# Environment variables

This document lists every setting used by the current product slice.

Prerequisites:
- Copy the root `.env.example` into `.env` for a new checkout.
- Read `docs/developer/setup.md`.

Never commit `.env` or copy prototype tokens into it.
The backend uses one `Settings` class from `backend/app/settings.py`.
Environment variables override `.env` values.
Frontend build values are public; never put a secret in `VITE_*`.

| Variable | Default | Use |
|---|---|---|
| `API_HOST` | `127.0.0.1` | Native backend bind address |
| `API_PORT` | `18081` | Native backend port; integer from 1 to 65535 |
| `API_LOG_LEVEL` | `info` | Backend logging: critical, error, warning, info, debug, or trace |
| `FRONTEND_HOST` | `127.0.0.1` | Vite development bind address |
| `FRONTEND_PORT` | `18080` | Vite development port; integer from 1 to 65535 |
| `API_PROXY_TARGET` | `http://127.0.0.1:18081` | Native backend origin for the Vite proxy |
| `VITE_DEFAULT_LANGUAGE` | `en` | Initial page language: en, ru, or es |
| `VITE_HEALTH_TIMEOUT_MS` | `5000` | Request deadline in milliseconds; integer from 1 to 2147483647 |
| `WEB_BIND_ADDRESS` | `127.0.0.1` | Local Compose host bind address |
| `WEB_PORT` | `18080` | Local Compose host port |

Compose fixes the internal backend address to `0.0.0.0:8000` and nginx to port `8080`.
Those internal ports form the container network contract; `API_HOST` and `API_PORT` apply to native execution.
Compose passes `API_LOG_LEVEL` to the backend and frontend build values as build arguments.
Change `WEB_PORT` to select another published port.
Keep the host bind addresses on loopback for local development.

The language selector changes only the current page.
The application does not save a user language until PHASE 1 implements user settings.
Database, authentication, storage, and product bot variables will accompany their implementation.
The prototype environment files remain separate.
