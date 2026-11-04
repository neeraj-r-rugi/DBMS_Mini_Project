#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   COUCHDB_URL=http://127.0.0.1:5984 COUCHDB_USER=admin \
#   COUCHDB_PASSWORD=secret ./database/couchdb_schema.sh

: "${COUCHDB_URL:=http://127.0.0.1:5984}"
: "${COUCHDB_USER:=}"
: "${COUCHDB_PASSWORD:=}"
AUTH=()
if [[ -n "$COUCHDB_USER" ]]; then
  AUTH=(-u "$COUCHDB_USER:$COUCHDB_PASSWORD")
fi

create_database() {
  local database="$1"
  local status
  status="$(curl -sS "${AUTH[@]}" -X PUT "$COUCHDB_URL/$database" \
    -o /dev/null -w '%{http_code}')"
  case "$status" in
    201|202|412) echo "database $database: $status" ;;
    *) echo "failed to create database $database (HTTP $status)" >&2; return 1 ;;
  esac
}

create_index() {
  local database="$1"
  local payload="$2"
  curl --fail-with-body -sS "${AUTH[@]}" -X POST \
    -H 'Content-Type: application/json' "$COUCHDB_URL/$database/_index" \
    -d "$payload" >/dev/null
}

create_database "used_car"
create_database "used_car_service_history"

create_index "used_car" \
  '{"index":{"fields":["car_id"]},"name":"car-id","type":"json"}'
create_index "used_car_service_history" \
  '{"index":{"fields":["service_id"]},"name":"service-id","type":"json"}'
create_index "used_car_service_history" \
  '{"index":{"fields":["car_id","service_date"]},"name":"service-car-date","type":"json"}'

echo "CouchDB schema is ready."
