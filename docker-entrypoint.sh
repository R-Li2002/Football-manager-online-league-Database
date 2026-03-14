#!/bin/sh
set -eu

mkdir -p /app/data /app/imports /app/data/backups

db_path="${DATABASE_PATH:-/app/data/fm_league.db}"
db_dir="$(dirname "$db_path")"
mkdir -p "$db_dir"

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec python -m uvicorn main1:app --host 0.0.0.0 --port "${PORT:-8080}"
