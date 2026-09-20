#!/usr/bin/env bash
# dfn2 — one-command setup. Installs everything into ~/dfn-prototype
# (venv, LavaSR, vocos patch, model weights) and optionally the dfn2d daemon.
#
#   ./setup.sh            install + print usage (daemon disabled)
#   ./setup.sh --daemon   also install the systemd warm-daemon
#
# Everything is served from this repo (weights included) — no HuggingFace
# download, no GitHub checkout at runtime.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${HOME}/dfn-prototype"
PY="$VENV/bin/python"
SITE="$VENV/lib/python3.11/site-packages"
INSTALL_DAEMON=0
[[ "${1:-}" == "--daemon" ]] && INSTALL_DAEMON=1

log() { printf '\n[dfn2] %s\n' "$*"; }

# --- 0. System deps -----------------------------------------------------------
log "Checking system packages (python3.11/uv, ffmpeg, tk)..."
missing=()
command -v ffmpeg  >/dev/null || missing+=(ffmpeg)
command -v uv      >/dev/null || missing+=(uv)
command -v python3 || true
if command -v python3.11 >/dev/null 2>&1; then PY311=python3.11
elif command -v uv >/dev/null 2>&1; then uv python install 3.11 >/dev/null; PY311="$(uv python find 3.11)"
else missing+=(python3-venv)
fi
if [ ${#missing[@]} -gt 0 ]; then
    echo "  missing: ${missing[*]}"
    echo "  Install them first. On Arch:  sudo pacman -S uv ffmpeg tk"
    echo "  On Debian/Ubuntu:  sudo apt install python3.11 python3.11-venv ffmpeg python3-tk"
    exit 1
fi
log "Using python: $PY311"

# --- 1. venv + torch CPU + deps ----------------------------------------------
if [ ! -x "$PY" ]; then
    log "Creating venv at $VENV"
    "$PY311" -m venv "$VENV"
    "$PY" -m pip install --upgrade pip -q
    log "Installing PyTorch CPU (torch 2.4.1+cpu)..."
    "$PY" -m pip install -q "torch==2.4.1+cpu" "torchaudio==2.4.1+cpu" \
        --index-url https://download.pytorch.org/whl/cpu
    log "Installing dependencies..."
    "$PY" -m pip install -q -r "$SRC_DIR/config/requirements_pinned.txt"
else
    log "venv already present at $VENV"
fi

# --- 2. Patch vocos (matcha) --------------------------------------------------
if [ -d "$SITE/vocos" ]; then
    log "Patching vocos with matcha branch API"
    cp "$SRC_DIR"/patch/*.py "$SITE/vocos/"
else
    echo "  ERROR: vocos not found in site-packages"; exit 1
fi

# --- 3. LavaSR package --------------------------------------------------------
if [ ! -d "$SITE/LavaSR" ]; then
    log "Installing LavaSR package into site-packages"
    cp -r "$SRC_DIR/LavaSR/LavaSR" "$SITE/"
else
    log "LavaSR package already present"
fi
"$PY" -c "from LavaSR.model import LavaEnhance2; print('  LavaSR import OK')"

# --- 4. Scripts + weights -----------------------------------------------------
log "Copying scripts and model weights to $VENV"
cp "$SRC_DIR"/scripts/*.py "$VENV/"
mkdir -p "$VENV/weights"
cp -r "$SRC_DIR/weights/." "$VENV/weights/"
chmod +x "$VENV/dfn_cli.py" "$VENV/dfn2d.py" "$VENV/lavasr.py"
log "Rewriting script shebangs to $VENV python"
sed -i "1s|^#!.*python.*|#!$PY -u|" "$VENV/dfn_cli.py" "$VENV/dfn2d.py" "$VENV/lavasr.py"

log "Linking ~/.local/bin/dfn2"
mkdir -p "$HOME/.local/bin"
ln -sf "$VENV/dfn_cli.py" "$HOME/.local/bin/dfn2"

# --- 5. Optional systemd daemon -----------------------------------------------
if [ "$INSTALL_DAEMON" = "1" ]; then
    if command -v systemctl >/dev/null && systemctl --version >/dev/null 2>&1; then
        log "Installing dfn2d systemd service"
        sed "s|/home/PLACEHOLDER|$HOME|g; s|User=PLACEHOLDER|User=$USER|g" \
            "$SRC_DIR/config/dfn2d.service.example" | sudo tee /etc/systemd/system/dfn2d.service >/dev/null
        sudo systemctl daemon-reload
        sudo systemctl enable --now dfn2d
        log "dfn2d daemon enabled (socket /tmp/dfn2d.sock)"
    else
        echo "  systemd not available — skip daemon, dfn2 will auto-spawn it per run."
    fi
fi

log "Setup complete. Try it:"
echo "    dfn2 path/to/audio.mp3            # original -> denoised -> menu"
echo "    dfn2 path/to/audio.mp3 soft       # + spectral grain reduction"
echo "    dfn2 path/to/audio.mp3 1          # original only"
echo "    dfn2 path/to/audio.mp3 2          # denoised only"