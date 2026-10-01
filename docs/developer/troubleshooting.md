# Troubleshooting

This document explains safe diagnosis of deployment, authentication, playback, and worker failures.

Prerequisites:
- Read `deploy.md`, `env-variables.md`, and `auth.md`.
- Use trusted SSH and the exact current release configuration.
- Keep private diagnostics and configuration outside Git and public reports.

**Warning:** Never remove production volumes or regenerate existing database passwords as an automatic repair.
Do not print resolved Compose configuration or publish `last-error.log` without removing credentials.

## Deployment capacity

| Error | Required action |
|---|---|
| `DEPLOY_DISK_INSUFFICIENT` | Inspect the reported filesystem and provision sufficient free space |
| `DEPLOY_DISK_UNKNOWN` | Run on the Docker host and verify access to its local storage path |
| `DEPLOY_DISK_CONFIG_INVALID` | Set positive integer values for both deployment capacity settings |
| `OMR_MEMORY_INSUFFICIENT` | Provision the configured OMR memory limit plus host reserve |
| `OMR_MEMORY_UNKNOWN` | Use a Linux host with readable `/proc/meminfo` |

1. Inspect free space with `df -h` on the Docker and release filesystems.
2. Inspect Docker storage with `docker system df`.
3. Identify any proposed cleanup resource by its exact ID and references.
4. Preserve current and compatible previous images, database volumes, media, and unrelated services.
5. Retry the same verified bundle after provisioning sufficient capacity.

The rollout never performs automatic cleanup.
Swap does not replace the OMR RAM reserve.
A failed preflight leaves active services and release state unchanged.
Downloaded candidate images can remain after a failed post-pull reserve check.

## Structured logs and rotation

1. Select the current release with the operator inspection procedure in `deploy.md`.
2. Inspect only the named product service with `docker compose ... logs --tail 100 backend`.
3. Repeat for `omr`, `telegram`, or `frontend` when that service fails.
4. Inspect the container's log configuration with `docker inspect --format '{{json .HostConfig.LogConfig}}' <container-id>`.

Replace the command placeholders with the complete current-release Compose arguments and the exact container ID.
Backend and worker records contain timestamp, severity, logger, and stable event.
HTTP records also contain method, route template, status, and duration.
Exception records contain the exception type and frame locations without its values.
nginx access records omit URLs, query strings, and client identities.
Its native error diagnostics remain separate from the JSON access records.

Production uses Docker's `json-file` driver with `DOCKER_LOG_MAX_SIZE=10m` and `DOCKER_LOG_MAX_FILE=3`.
Docker rotates each container's records within these bounds.
Do not manually truncate a running container's log file.
Configuration changes take effect when the targeted rollout recreates the service.

## Worker health

1. Inspect the OMR container's health and restart count.
2. Inspect its structured error event and the manager's recognition status.
3. Keep `OMR_HEALTH_SECONDS` above the engine timeout.
4. Retry recognition through the manager interface after resolving the error.

The OMR worker refreshes its marker after a successful database and processing cycle.
A missing or stale marker fails its healthcheck.
A disabled worker remains alive but leaves recognition pending; this is not successful OMR acceptance.
Java memory exhaustion, invalid output, and unclear images require separate diagnoses.
Read `omr-pipeline.md` before changing engine limits.

1. Inspect Telegram readiness and the import list.
2. Confirm that only the product poller uses the configured bot.
3. Check the token privately when the worker cannot verify the bot.
4. Retry a failed import through the website after resolving the cause.

An empty token explicitly disables polling.
A configured worker requires a current-process marker and a recent database heartbeat.
Do not reset the stored bot identity or update offset to hide an error.
Read `telegram-import.md` for linking, retries, and durable import behavior.

## Authentication and browser errors

1. Verify HTTPS origins and `SESSION_COOKIE_SECURE=true` in production.
2. Verify the trusted proxy headers without exposing cookies.
3. Sign in again after a password reset, deactivation, or expired session.
4. Wait for the reported login budget before retrying a rate-limited login.

An unknown application page returns HTTP 404 with a translated message and home link.
Unknown API endpoints retain JSON errors.
Direct protected-file paths remain inaccessible.
Do not replace these errors with a successful page response.

1. Start audio or speech through an explicit click.
2. Check authenticated Range responses when Safari seeking fails.
3. Check score approval and version before investigating speech failure.
4. Lower the tempo when the page reports that a spoken name does not fit.
5. Obtain a clearer original image when recognition inserts chords, backups, or missing measures.

Retain the existing 66 speech clips.
Do not call the paid generator as a routine troubleshooting step.

## Dependency advisories

1. Run `uv run --locked pip-audit --strict --progress-spinner off`.
2. Run `npm audit --audit-level=low`.
3. Read each advisory and identify the affected direct or transitive package.
4. Update only the required manifests and locks with the existing package managers.
5. Regenerate `requirements.txt` when Python runtime dependencies change.
6. Run all relevant tests, quality hooks, and image checks.

An unavailable audit service is a failed check, not a clean audit.
Do not use automatic forced npm fixes or broad advisory exclusions.
An unavoidable advisory requires an explicit owner-reviewed decision before deployment.
