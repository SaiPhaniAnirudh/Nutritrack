#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  NutriTrack — setup.sh
#  One-time local dev setup (no Docker required)
#
#  Usage (from project root):
#    chmod +x setup.sh && ./setup.sh
#
#  What it does:
#    1. Checks Python 3.10+
#    2. Creates .venv and installs pip deps
#    3. Checks Ollama installation
#    4. Pulls llava-phi3 if not already present
#    5. Copies .env.example → .env if missing
#    6. Prints how to start both servers
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() { echo -e "${CYAN}$1${NC}"; }
ok()     { echo -e "${GREEN}  ✅ $1${NC}"; }
warn()   { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail()   { echo -e "${RED}  ❌ $1${NC}"; }

echo ""
banner "══════════════════════════════════════════════"
banner "  NutriTrack — First-Run Setup"
banner "══════════════════════════════════════════════"
echo ""

# ── 1. Python version ──────────────────────────────────────────────────────
banner "→ Checking Python..."
PY=$(python3 --version 2>&1 || python --version 2>&1 || echo "not found")
echo "  Found: $PY"
MAJOR=$(echo "$PY" | grep -oP '\d+' | head -1)
MINOR=$(echo "$PY" | grep -oP '\d+' | sed -n '2p')
if [[ "$MAJOR" -lt 3 || ("$MAJOR" -eq 3 && "$MINOR" -lt 10) ]]; then
    fail "Python 3.10+ required. Install from https://python.org"
    exit 1
fi
ok "Python $PY"

# ── 2. Virtual environment ─────────────────────────────────────────────────
banner "→ Setting up Python virtual environment..."
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok ".venv already exists"
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Python dependencies installed"

# ── 3. .env file ───────────────────────────────────────────────────────────
banner "→ Checking .env..."
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    warn ".env created from .env.example — edit it to add your API keys (optional)"
else
    ok ".env already exists"
fi

# ── 4. Ollama ──────────────────────────────────────────────────────────────
banner "→ Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    fail "Ollama not installed."
    echo ""
    echo "  Install it from: https://ollama.com/download"
    echo ""
    echo "  macOS:   brew install ollama"
    echo "  Linux:   curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Windows: Download the installer from https://ollama.com/download"
    echo ""
    warn "Skipping model pull — install Ollama then run: ollama pull llava-phi3"
else
    ok "Ollama found: $(ollama --version)"

    # Check if Ollama server is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        warn "Ollama server not running — starting it..."
        ollama serve &>/dev/null &
        sleep 3
    fi

    # Pull llava-phi3
    MODEL="llava-phi3"
    MODELS=$(ollama list 2>/dev/null || echo "")
    if echo "$MODELS" | grep -q "llava-phi3"; then
        ok "Model $MODEL already pulled"
    else
        banner "→ Pulling $MODEL (~2.9 GB, this takes a while on first run)..."
        ollama pull "$MODEL"
        ok "Model $MODEL pulled successfully"
    fi
fi

# ── 5. Done ────────────────────────────────────────────────────────────────
echo ""
banner "══════════════════════════════════════════════"
banner "  Setup complete! How to start NutriTrack:"
banner "══════════════════════════════════════════════"
echo ""
echo "  Terminal 1 — Start Ollama (if not already running):"
echo -e "    ${CYAN}ollama serve${NC}"
echo ""
echo "  Terminal 2 — Start AI inference server:"
echo -e "    ${CYAN}source .venv/bin/activate && python llm/Llm_server.py${NC}"
echo ""
echo "  Terminal 3 — Start Flask API:"
echo -e "    ${CYAN}source .venv/bin/activate && python backend/App.py${NC}"
echo ""
echo "  Open in browser:"
echo -e "    ${CYAN}http://localhost:5000${NC}"
echo ""
banner "══════════════════════════════════════════════"
echo ""
