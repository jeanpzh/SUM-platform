#!/bin/sh
set -eu
: "${MINIO_ROOT_USER:?}"
: "${MINIO_ROOT_PASSWORD:?}"
: "${BACKEND_S3_SECRET:?}"
: "${INDEXER_S3_SECRET:?}"
attempt=0
until mc alias set local http://storage:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        printf '%s\n' 'No se pudo inicializar el almacenamiento.' >&2
        exit 1
    fi
    sleep 2
done
mc mb --ignore-existing local/sum-documents >/dev/null
mc admin policy create local backend-upload /policies/backend-policy.json >/dev/null
mc admin policy create local indexer-files /policies/indexer-policy.json >/dev/null
mc admin user add local sum-backend "$BACKEND_S3_SECRET" >/dev/null
mc admin user add local sum-indexer "$INDEXER_S3_SECRET" >/dev/null
mc admin policy attach local backend-upload --user sum-backend >/dev/null
mc admin policy attach local indexer-files --user sum-indexer >/dev/null
