#!/bin/bash
# simulate-human-error.sh — Introduce a syntax error in the backend code
#
# Usage:
#   ./simulate-human-error.sh
#
# Adapted from the Order Simulator reference script:
#   - APP_FILE now points to this project's actual entrypoint
#     (app.main:app, the module Gunicorn imports).
#   - Service name changed from "zerto-backend" to "flight-booking-backend"
#     (matches deploy/flight-booking-backend.service).

APP_FILE="${APP_FILE:-/opt/flight-booking-backend/app/main.py}"
SERVICE_NAME="${SERVICE_NAME:-flight-booking-backend}"

echo ""
echo "=== Simulating human error ==="

if grep -q "this is not valid python syntax" "$APP_FILE"; then
  echo "ERROR: Syntax error already present. Run rollback-human-error.sh first."
  exit 1
fi

echo "[1/2] Introducing syntax error in $APP_FILE..."
echo "this is not valid python syntax!!!" >> "$APP_FILE"

echo "[2/2] Restarting backend service..."
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
#echo "Done. Backend is now broken."
#echo "Run rollback-human-error.sh to fix it."
