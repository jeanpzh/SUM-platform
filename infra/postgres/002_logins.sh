#!/usr/bin/env bash
set -Eeuo pipefail
: "${BACKEND_DB_PASSWORD:?}"
: "${INDEXER_DB_PASSWORD:?}"
: "${RETRIEVAL_DB_PASSWORD:?}"
: "${AUTH_DB_PASSWORD:?}"
# psql variable quoting keeps passwords out of SQL interpolation and command output.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 \
  --set=backend_password="$BACKEND_DB_PASSWORD" \
  --set=indexer_password="$INDEXER_DB_PASSWORD" \
  --set=retrieval_password="$RETRIEVAL_DB_PASSWORD" <<'SQL'
CREATE USER sum_backend WITH PASSWORD :'backend_password';
CREATE USER sum_indexer WITH PASSWORD :'indexer_password';
CREATE USER sum_retrieval WITH PASSWORD :'retrieval_password';
GRANT sum_backend_access TO sum_backend;
GRANT sum_indexer_access TO sum_indexer;
GRANT sum_retrieval_access TO sum_retrieval;
SQL
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=auth_password="$AUTH_DB_PASSWORD" <<'SQL'
CREATE USER sum_auth WITH PASSWORD :'auth_password';
CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION sum_auth;
GRANT CONNECT ON DATABASE sum TO sum_auth;
ALTER ROLE sum_auth SET search_path TO auth;
SQL
