#!/bin/sh
set -eu

if [ "$DATABASE_USER" = "$MIGRATION_DATABASE_USER" ] ||
   [ "$DATABASE_USER" = postgres ] ||
   [ "$MIGRATION_DATABASE_USER" = postgres ]; then
    echo "DATABASE_ROLES_MUST_BE_DISTINCT" >&2
    exit 1
fi
case "$PRODUCTION_MIGRATION_SCHEMA" in
    public|pg_*|information_schema|"")
        echo "MIGRATION_SCHEMA_MUST_BE_PRIVATE" >&2
        exit 1
        ;;
esac

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<'SQL'
\set VERBOSITY terse
-- Bootstrap DDL contains passwords; retain errors without logging their SQL text.
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
SET log_error_verbosity = 'terse';
\getenv database_name POSTGRES_DB
\getenv app_user DATABASE_USER
\getenv app_password DATABASE_PASSWORD
\getenv owner_user MIGRATION_DATABASE_USER
\getenv owner_password MIGRATION_DATABASE_PASSWORD
\getenv version_schema PRODUCTION_MIGRATION_SCHEMA
BEGIN;
CREATE ROLE :"owner_user" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'owner_password';
CREATE ROLE :"app_user" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
ALTER DATABASE :"database_name" OWNER TO :"owner_user";
REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO :"app_user";
ALTER SCHEMA public OWNER TO :"owner_user";
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"app_user";
CREATE SCHEMA :"version_schema" AUTHORIZATION :"owner_user";
REVOKE ALL ON SCHEMA :"version_schema" FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";
COMMIT;
SQL
