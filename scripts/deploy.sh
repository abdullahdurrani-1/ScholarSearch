#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/scholarsearch}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

cd "$APP_DIR"

echo "[deploy] Pulling latest images"
docker compose -f "$COMPOSE_FILE" pull

echo "[deploy] Applying stack"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "[deploy] Current status"
docker compose -f "$COMPOSE_FILE" ps
