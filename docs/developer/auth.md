# Authentication and recovery

This document explains login sessions, account controls, and emergency manager recovery.

Prerequisites:
- Apply the current Alembic head, which includes `0002_auth`.
- Read `env-variables.md` and `deploy.md`.
- Keep production configuration and passwords private.

## Passwords and sessions

The backend hashes passwords with standard-library scrypt and a random salt.
The fixed cost is `N=32768`, `r=8`, `p=3`; the salt contains 16 bytes.
Stored password hashes do not contain plaintext passwords.
Login performs a dummy hash check for unknown users to reduce username timing differences.
The API uses the same credential error for unknown, inactive, and incorrect-password cases.

The browser receives a random session token in the `solfeo_session` cookie.
PostgreSQL stores only the token's SHA-256 hash.
Production cookies use `Secure`, `httpOnly`, `SameSite=Lax`, and the `/` path, without a domain attribute.
Authenticated requests extend both server expiry and cookie lifetime.
The default sliding lifetime is 90 days.
Browser policies or explicit cookie removal can shorten browser retention.

Each session has an independent CSRF token.
Login requires an exact allowed origin.
Every other mutation requires that origin and `X-CSRF-Token`.
The frontend obtains the CSRF token from login or `/api/auth/me`.
It keeps authenticated state in TanStack Query, not localStorage.
Logout and authorization failures remove protected cached data and cancel obsolete requests.

Changing a password revokes all previous sessions, including sessions on other devices.
The password-change operation issues a new session for its caller.
Manager resets, deactivation, and role changes revoke the target user's sessions.
An obligatory password change blocks settings and manager operations until completion.
Ordinary user sessions survive backend restarts.

## Login limits and proxy trust

PostgreSQL stores independent budgets for normalized usernames and client IP addresses.
Advisory locks prevent concurrent attempts from bypassing those budgets.
Failed username attempts consume the username budget; all login attempts consume the IP budget.
A successful login clears that username's failure count.
Expired budgets and expired sessions are removed during later login attempts.
nginx separately limits the login request rate and burst.

Shared nginx overwrites `X-Real-IP` and `X-Forwarded-Proto`.
The frontend ignores incoming `X-Forwarded-For` and forwards the trusted client address.
The backend trusts forwarded headers only inside its private deployment boundary.
`API_FORWARDED_ALLOW_IPS=*` is safe here only because no backend port is public.
Only the shared TLS proxy and frontend join the dedicated proxy network.
Do not connect untrusted containers or expose the frontend beyond loopback.

## First manager and emergency recovery

Do not paste passwords into chat, Git, shell history, or deployment logs.
Create an ordinary manager before disabling emergency access.

1. Open the server's private `~/solfeo-production/.env.production` file through a trusted SSH session.
2. Set `EMERGENCY_MANAGER_USERNAME` and `EMERGENCY_MANAGER_PASSWORD` together.
3. Set the emergency first and last names if required.
4. Keep the file mode at `0600`.
5. Redeploy the current verified release, or recreate only its backend with the same release configuration.
   Startup creates or updates the emergency manager as active and resets its password.
6. Sign in with those credentials.
7. Create an ordinary manager through the Users page.
8. Sign in as that ordinary manager in a separate browser session.
9. Clear both emergency credentials when recovery access is no longer required.
10. Recreate only the backend with its existing release configuration.
    Startup deactivates the flagged emergency account and revokes its sessions.

Every backend startup repeats emergency synchronization.
The startup fails explicitly if the database or required schema is unavailable.
Supplying only one credential fails configuration validation.
Changing the configured username deactivates the previous emergency account and removes its emergency flag.
The new configured account receives the flag and manager role.
The process does not delete user records.

The manager interface cannot reset, rename, demote, or deactivate an emergency account.
Its own password-change form is unavailable because the environment controls that password.
Emergency accounts can change their language and note naming.
The existing prototype bot token and sender allowlist remain independent.

The first PHASE 1 deployment configures `recovery-manager` with a generated password on the VPS.
The password remains in `~/solfeo-production/.env.production`, readable only by the deployment account.
The automated browser scenarios leave 4 inactive accounts with `check-manager-` or `check-student-` username prefixes.
They do not grant access, and the operator does not need their temporary passwords.

## Deployment compatibility

Revision `0002_auth` follows the empty `0001_initial` baseline.
It adds users, login sessions, and login limits without modifying existing tables.
The production application role receives access through existing default grants.
The migration role remains the only schema owner.

After migration, the PHASE 0 image does not recognize the new schema head.
Automatic rollback therefore refuses that image and leaves application services stopped if verification fails.
Use a tested PHASE 1 forward fix instead of automatically downgrading or deleting account data.
