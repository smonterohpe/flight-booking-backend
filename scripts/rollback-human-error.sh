#!/bin/bash
# rollback-human-error.sh — Remove syntax error from backend code and restart
#
# Usage:
#   ./rollback-human-error.sh
#
# Adapted from the Order Simulator reference script:
#   - APP_FILE now points to this project's actual entrypoint
#     (app.main:app, the module Gunicorn imports).
#   - Service name changed from "zerto-backend" to "flight-booking-backend"
#     (matches deploy/flight-booking-backend.service).

APP_FILE="${APP_FILE:-/opt/flight-booking-backend/app/main.py}"
SERVICE_NAME="${SERVICE_NAME:-flight-booking-backend}"

echo ""
echo "=== Rolling back human error ==="

if ! grep -q "this is not valid python syntax" "$APP_FILE"; then
  echo "ERROR: No syntax error found in $APP_FILE. Nothing to rollback."
  exit 1
fi

echo "[1/2] Removing syntax error from $APP_FILE..."
sed -i '/this is not valid python syntax!!!/d' "$APP_FILE"

echo "[2/2] Restarting backend service..."
systemctl restart "$SERVICE_NAME"

echo ""
echo "Done. Backend restored."
