#!/usr/bin/env bash
# Publish the demo to static hosting.
#
# The demo is a separate website from anything else you host: it is four static
# HTML files with relative links and no backend, so it drops into any directory
# and needs no PHP, no database and no Python on the server.
#
# Credentials come from demo/.env.local (gitignored) or the environment:
#
#     DEMO_HOST=srv1234.krystal.co.uk
#     DEMO_USER=your_cpanel_username
#     DEMO_PORT=722                          # Krystal SSH/SFTP port
#     DEMO_PATH=public_html/ledgerforge-demo
#
# Usage:
#     ./demo/deploy.sh              # rebuild + dry run (shows what would change)
#     ./demo/deploy.sh --live       # rebuild + publish

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
SITE="$HERE/site"

# ── Credentials (never committed) ─────────────────────────────────────────────
ENV_LOCAL="$HERE/.env.local"
if [[ -f "$ENV_LOCAL" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_LOCAL"
fi

DEMO_PORT="${DEMO_PORT:-722}"
DEMO_PATH="${DEMO_PATH:-public_html/ledgerforge-demo}"

# ── Always rebuild, so we never publish a stale or local-mode build ──────────
# A --local build wires the Save buttons to a dev server that will not exist on
# the far end, so publishing one would ship dead buttons. Rebuilding plain
# guarantees static mode.
PY="$(command -v python3 || true)"
for candidate in "$REPO/../.venv/bin/python" "$REPO/.venv/bin/python"; do
  [[ -x "$candidate" ]] && PY="$candidate" && break
done

echo "→ Rebuilding demo in static mode ($PY)"
( cd "$REPO" && "$PY" demo/build_demo.py )

if grep -rq 'fetch("/save' "$SITE"/*.html; then
  echo "ERROR: built pages still POST to /save — refusing to publish a build"
  echo "       that needs a server. Rebuild without --local."
  exit 1
fi
echo "  verified: no server calls in the built pages"

# ── Publish ───────────────────────────────────────────────────────────────────
if [[ "${1:-}" != "--live" ]]; then
  echo
  echo "DRY RUN — pass --live to publish."
  echo "  would sync: $SITE/"
  if [[ -n "${DEMO_HOST:-}" && -n "${DEMO_USER:-}" ]]; then
    echo "          to: ${DEMO_USER}@${DEMO_HOST}:${DEMO_PATH}/  (port ${DEMO_PORT})"
    rsync -avzn --delete -e "ssh -p ${DEMO_PORT}" \
      "$SITE/" "${DEMO_USER}@${DEMO_HOST}:${DEMO_PATH}/"
  else
    echo "          to: (set DEMO_HOST and DEMO_USER in demo/.env.local)"
    echo
    echo "  Locally you can serve it right now with no dependencies:"
    echo "    python3 -m http.server 8791 --directory demo/site"
  fi
  exit 0
fi

: "${DEMO_HOST:?Set DEMO_HOST in demo/.env.local}"
: "${DEMO_USER:?Set DEMO_USER in demo/.env.local}"

echo "→ Publishing to ${DEMO_USER}@${DEMO_HOST}:${DEMO_PATH}/"
rsync -avz --delete -e "ssh -p ${DEMO_PORT}" \
  "$SITE/" "${DEMO_USER}@${DEMO_HOST}:${DEMO_PATH}/"

echo "✅ Published."
echo "   Remember the linking site should point at the demo's public URL."
