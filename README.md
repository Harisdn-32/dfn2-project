# dfn2 — offline CPU speech enhancement (LavaSR)

Enhances noisy audio locally with the [LavaSR](https://huggingface.co/YatharthS/LavaSR)
model (Vocos-based BWE + ULULAS denoiser). No GPU needed, model stays warm in a
systemd daemon so runs feel instant.

```bash
dfn2 "file.mp3"          # enhance + save *_lavasr.mp3, play original -> denoised, then menu
dfn2 "file.mp3" soft     # + spectral grain reduction (gentler high-end, saves *_soft.mp3)
dfn2 "file.mp3" 1        # play original only
dfn2 "file.mp3" 2        # play denoised only
```

After the first round the CLI prints `Play Again? 1=Original 2=Denoised 0=exit`.

## Setup (Arch/Linux, Python 3.11, CPU)

```bash
# system deps
sudo pacman -S uv ffmpeg tk   # uv gives a standalone python3.11

python3.11=$(UV_ROOT=~/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11)

# venv + CPU torch
mkdir -p ~/dfn-prototype && $python3.11 -m venv ~/dfn-prototype
~/dfn-prototype/bin/pip install "torch==2.4.1+cpu" "torchaudio==2.4.1+cpu" \
  --index-url https://download.pytorch.org/whl/cpu
~/dfn-prototype/bin/pip install -r config/requirements_pinned.txt

# REQUIRED: patch vocos with the "matcha" branch API
cp patch/*.py ~/dfn-prototype/lib/python3.11/site-packages/vocos/

# LavaSR package (no PyPI package exists)
cp -r LavaSR/LavaSR ~/dfn-prototype/lib/python3.11/site-packages/
~/dfn-prototype/bin/python -c "from LavaSR.model import LavaEnhance2; print('ok')"

# model weights (229MB) -> HF cache, or let it auto-download on first run
mkdir -p ~/.cache/huggingface/hub

# put scripts in place + commands
cp scripts/*.py ~/dfn-prototype/
chmod +x ~/dfn-prototype/dfn_cli.py ~/dfn-prototype/dfn2d.py
ln -sf ~/dfn-prototype/dfn_cli.py ~/.local/bin/dfn2

# warm daemon at boot (edit paths/user in the unit first)
sed "s|/home/USER|$HOME|g; s|User=USER|User=$USER|" config/dfn2d.service.example \
  | sudo tee /etc/systemd/system/dfn2d.service
sudo systemctl daemon-reload && sudo systemctl enable --now dfn2d
```

## Files

| path | what |
|---|---|
| `scripts/dfn_cli.py` | current CLI (`dfn2`): MP3 output, `soft` mode, 1/2/0 menu |
| `scripts/dfn2d.py` | model daemon (loads once, serves `/tmp/dfn2d.sock`) |
| `scripts/lavasr.py` | original client (kept for reference) |
| `scripts/dual_mic_demo.py` | dual-mic least-squares noise subtraction demo |
| `scripts/play_subtracted.py` | subtract reference noise, play result only |
| `scripts/compare_all.py` | original vs subtraction vs LavaSR A/B/C |
| `scripts/process_audio_lavasr.py` | library-style LavaSR helper (in-process) |
| `config/dfn2d.service.example` | systemd unit template for the daemon |
| `config/requirements_pinned.txt` | exact working pip versions |
| `LavaSR/` | LavaSR package source (copy into site-packages — no PyPI pkg) |
| `patch/` | vocos "matcha" branch files (overwrite site-packages/vocos/) |

## Troubleshooting

| symptom | fix |
|---|---|
| `TypeError: ... unexpected keyword 'f_min'` (vocos) | redo the vocos matcha patch (step 3) |
| CUDA/libcublas errors | reinstall `torch==2.4.1+cpu` from the CPU index |
| no `/tmp/dfn2d.sock` | `sudo systemctl restart dfn2d`; client auto-spawns daemon otherwise |
| grain/musical noise in output | use `dfn2 "file" soft` (spectral reduction of noise-like bins) |