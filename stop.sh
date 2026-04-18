#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

echo "═══════════════════════════════════════════"
echo "  Boris — Stopping"
echo "═══════════════════════════════════════════"
echo ""

# ── Kill Boris process(es) ──────────────────────────────────────────
PIDS=$(pgrep -f "python -m boris" 2>/dev/null || true)

if [ -n "$PIDS" ]; then
    for PID in $PIDS; do
        # Send SIGINT first (triggers graceful shutdown + episodic save)
        kill -INT "$PID" 2>/dev/null || true
    done
    ok "Sent SIGINT to Boris (PID: $(echo $PIDS | tr '\n' ' '))"

    # Wait up to 5s for graceful exit
    for i in $(seq 1 10); do
        if ! pgrep -f "python -m boris" >/dev/null 2>&1; then
            ok "Boris stopped gracefully"
            break
        fi
        sleep 0.5
    done

    # Force kill if still alive
    if pgrep -f "python -m boris" >/dev/null 2>&1; then
        pkill -9 -f "python -m boris" 2>/dev/null || true
        warn "Boris force-killed (did not exit in 5s)"
    fi
else
    warn "Boris not running"
fi

echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${GREEN}Done.${NC}"
echo "═══════════════════════════════════════════"
