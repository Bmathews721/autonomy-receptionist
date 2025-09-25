#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy.sh <alias> [--no-deploy] [--no-logs] [--message "msg"]

# Map aliases to service IDs
declare -A SERVICES=(
  [ivr1]="srv-d3aom11gv73c739dchdg"
  [ivr2]="srv-d3aom11gv73c739dchcg"
  [ivr3]="srv-d3aom11gv73c739dchd0"
)

ALIAS="${1:-}"
shift || true

if [[ -z "$ALIAS" ]]; then
  echo "Usage: $0 <alias: ivr1|ivr2|ivr3> [--no-deploy] [--no-logs] [--message \"msg\"]"
  exit 1
fi

SERVICE_ID="${SERVICES[$ALIAS]:-}"
if [[ -z "$SERVICE_ID" ]]; then
  echo "❌ Unknown alias '$ALIAS'. Valid options: ${!SERVICES[@]}"
  exit 1
fi

DEPLOY=1
TAIL_LOGS=1
COMMIT_MSG="Update IVR code $(date +%Y-%m-%d_%H:%M:%S)"

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-deploy) DEPLOY=0; shift ;;
    --no-logs)   TAIL_LOGS=0; shift ;;
    --message)   COMMIT_MSG="${2:-$COMMIT_MSG}"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "✅ Targeting $ALIAS → $SERVICE_ID"

# Commit & push only if there are changes
if [[ -n "$(git status --porcelain)" ]]; then
  echo "📦 Changes detected → committing & pushing..."
  git add .
  git commit -m "${COMMIT_MSG}" || true
  git push
else
  echo "ℹ️ No changes detected → skipping commit & push."
fi

# Optional deploy
if [[ "${DEPLOY}" -eq 1 ]]; then
  echo "🚀 Triggering redeploy…"
  render deploys create "${SERVICE_ID}"
else
  echo "⏭️  Skipping redeploy (--no-deploy)."
fi

# Optional log tail
if [[ "${TAIL_LOGS}" -eq 1 ]]; then
  echo "📜 Tailing logs… (Ctrl+C to stop)"
  render logs "${SERVICE_ID}" --live
else
  echo "⏭️  Skipping log tail (--no-logs)."
fi
