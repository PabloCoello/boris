#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

echo "═══════════════════════════════════════════"
echo "  Boris — Pre-flight checks"
echo "═══════════════════════════════════════════"

READY=true

# ── 1. Ollama ───────────────────────────────────────────────────────
echo ""
echo "Ollama..."
if systemctl is-active --quiet ollama 2>/dev/null; then
    ok "Ollama service running"
else
    warn "Ollama not running, starting..."
    sudo systemctl start ollama
    sleep 2
    if systemctl is-active --quiet ollama 2>/dev/null; then
        ok "Ollama started"
    else
        fail "Could not start Ollama"
        READY=false
    fi
fi

# Check that the configured model is available
MODEL=$(grep -oP 'model:\s*\K\S+' config.yaml | head -1)
if ollama list 2>/dev/null | grep -q "${MODEL}"; then
    ok "Model '${MODEL}' available"
else
    warn "Model '${MODEL}' not found in ollama list — Boris will fail on first LLM call"
fi

# ── 2. SearXNG (optional) ──────────────────────────────────────────
echo ""
echo "SearXNG..."
SEARX_URL=$(python3 -c "
import yaml
c = yaml.safe_load(open('config.yaml'))
print(c.get('skills',{}).get('search',{}).get('url',''))
" 2>/dev/null || echo "")

if [ -n "$SEARX_URL" ]; then
    if curl -sf "${SEARX_URL}/healthz" >/dev/null 2>&1 || curl -sf "${SEARX_URL}" >/dev/null 2>&1; then
        ok "SearXNG reachable at ${SEARX_URL}"
    else
        # Try to start via docker
        if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qi searx; then
            CONTAINER=$(docker ps -a --format '{{.Names}}' | grep -i searx | head -1)
            warn "SearXNG not reachable, starting container '${CONTAINER}'..."
            docker start "$CONTAINER" >/dev/null 2>&1
            sleep 3
            if curl -sf "${SEARX_URL}" >/dev/null 2>&1; then
                ok "SearXNG started"
            else
                warn "SearXNG still not reachable — search skill will be unavailable"
            fi
        else
            warn "SearXNG not reachable and no container found — search skill will be unavailable"
        fi
    fi
else
    warn "No SearXNG URL configured — search skill disabled"
fi

# ── 3. PipeWire / Audio ────────────────────────────────────────────
echo ""
echo "Audio..."
if systemctl --user is-active --quiet pipewire 2>/dev/null; then
    ok "PipeWire running"
else
    warn "PipeWire not running, starting..."
    systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null
    sleep 1
    if systemctl --user is-active --quiet pipewire 2>/dev/null; then
        ok "PipeWire started"
    else
        fail "Could not start PipeWire"
        READY=false
    fi
fi

# Check microphone
MIC_NAME=$(python3 -c "
import yaml
c = yaml.safe_load(open('config.yaml'))
print(c.get('audio',{}).get('input_device_name','') or '')
" 2>/dev/null || echo "")

if [ -n "$MIC_NAME" ]; then
    if uv run python -c "
import sounddevice as sd
devs = sd.query_devices()
found = any('$MIC_NAME' in (d.get('name','') or '') for d in devs if isinstance(d, dict))
if not found:
    found = any('$MIC_NAME' in str(d) for d in devs)
exit(0 if found else 1)
" 2>/dev/null; then
        ok "Microphone '${MIC_NAME}' found"
    else
        warn "Microphone '${MIC_NAME}' not found — will use system default"
    fi
else
    ok "Using system default microphone"
fi

# ── 4. .env secrets ────────────────────────────────────────────────
echo ""
echo "Secrets..."
if [ -f .env ]; then
    ok ".env file exists"
else
    warn "No .env file — some skills (Garmin, Spotify, Calendar) won't work"
fi

# ── 5. Wake word model ─────────────────────────────────────────────
echo ""
echo "Wake word..."
WW_MODEL=$(python3 -c "
import yaml
c = yaml.safe_load(open('config.yaml'))
print(c.get('assistant',{}).get('wake_word_model','') or '')
" 2>/dev/null || echo "")

if [ -n "$WW_MODEL" ] && [ -f "$WW_MODEL" ]; then
    ok "Wake word model: ${WW_MODEL}"
elif [ -n "$WW_MODEL" ]; then
    warn "Wake word model '${WW_MODEL}' not found — will use pre-trained fallback"
else
    ok "Using pre-trained wake word model"
fi

# ── Launch ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"

if [ "$READY" = false ]; then
    fail "Pre-flight failed. Fix the issues above and retry."
    exit 1
fi

echo -e "  ${GREEN}All checks passed. Launching Boris...${NC}"
echo "═══════════════════════════════════════════"
echo ""

exec uv run python -m boris
