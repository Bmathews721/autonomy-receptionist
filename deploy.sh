#!/usr/bin/env bash
set -e

SERVICE_NAME="$1"
if [ -z "$SERVICE_NAME" ]; then
  echo "Usage: $0 <service-name>"
  exit 1
fi

# Find service ID using new CLI output format
SERVICE_ID=$(render services list -o json | jq -r ".[] | select(.service.name==\"$SERVICE_NAME\") | .service.id")

if [ -z "$SERVICE_ID" ] || [ "$SERVICE_ID" == "null" ]; then
  echo "❌ Could not find service ID for $SERVICE_NAME"
  exit 1
fi

echo "✅ Found service ID: $SERVICE_ID"

# Commit & push
git add .
git commit -m "Update IVR code $(date +%Y-%m-%d_%H:%M:%S)" || true
git push

# Trigger redeploy
render deploys create "$SERVICE_ID"

# Tail logs
render logs "$SERVICE_ID" --live
