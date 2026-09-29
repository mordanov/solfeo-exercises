# API

This document describes the endpoints available in the current product slice.

Prerequisites:
- Start the local stand with `docs/developer/setup.md`.

## Health

`GET /api/health` returns status `200` and `{"status":"ok"}`.
`HEAD /api/health` returns the same status without a response body.
Both methods set `Cache-Control: no-store`.
The endpoint needs no authentication and creates no session cookie.

This endpoint checks the FastAPI process only.
It does not establish database readiness, bot operation, or worker health.
The frontend validates both the HTTP status and the JSON body.

## Errors

| HTTP status | Body |
|---|---|
| 404 | `{"error":"NOT_FOUND"}` |
| 405 | `{"error":"METHOD_NOT_ALLOWED"}` |

The API returns codes, not translated messages.
The frontend reports health failures through localized client error codes.
nginx can return a gateway error when the backend stops; the frontend treats that response as a failure.
`/docs`, `/redoc`, and `/openapi.json` are not public routes.
