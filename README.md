# dfn2 — offline CPU speech enhancement (LavaSR)

Enhances noisy audio locally with the [LavaSR](https://huggingface.co/YatharthS/LavaSR)
model (Vocos-based BWE + ULULAS denoiser). No GPU needed, fully offline — the
model weights ship in this repo, so nothing is downloaded at runtime.

```bash
dfn2 "file.mp3"          # enhance + save *_lavasr.mp3, play original -> denoised, then menu
dfn2 "file.mp3" soft     # + spectral grain reduction (saves *_soft.mp3)
dfn2 "file.mp3" 1        # play original only
dfn2 "file.mp3" 2        # play denoised only
```

After the first round the CLI prints `Play Again? 1=Original 2=Denoised 0=exit`.

## Quick start (one command)

```bash
git clone https://github.com/Harisdn-32/dfn2-project.git && cd dfn2-project
./setup.sh                          # builds ~/dfn-prototype (venv + model + weights)
dfn2 path/to/audio.mp3              # done
```

Add `--daemon` to the setup if you want a systemd service that keeps the model
warm from boot (`./setup.sh --daemon`). Without it the client auto-spawns the
daemon per run (~3 s first load).

**Prerequisites:** Linux with `python3.11` or `uv`, `ffmpeg`, and (for the GUI /
tkinter bits) Tk. On Arch: `sudo pacman -S uv ffmpeg tk`. On Debian/Ubuntu:
`sudo apt install python3.11 python3.11-venv ffmpeg python3-tk`. Playback needs
working audio (PulseAudio/PipeWire).

## What setup.sh does

1. Finds `python3.11` (or `uv python install 3.11`) and creates `~/dfn-prototype`.
2. Installs `torch==2.4.1+cpu` + `torchaudio==2.4.1+cpu` from the CPU index, then
   the pinned deps in `config/requirements_pinned.txt`.
3. Patches `vocos` with the "matcha" branch API (model will not load without it).
4. Installs the `LavaSR` package into site-packages (no PyPI package exists).
5. Copies scripts + model weights (from `weights/`, ~55 MB).
6. Rewrites script shebangs to the local venv and symlinks `~/.local/bin/dfn2`.

## Files

| path | what |
|---|---|
| `setup.sh` | one-command installer (this is all you need) |
| `scripts/dfn_cli.py` | CLI (`dfn2`): MP3 output, `soft` mode, 1/2/0 menu |
| `scripts/dfn2d.py` | model daemon (loads once, serves `/tmp/dfn2d.sock`) |
| `scripts/lavasr.py` | original client (kept for reference) |
| `scripts/dual_mic_demo.py` | dual-mic least-squares noise subtraction demo |
| `scripts/play_subtracted.py` | subtract reference noise, play result only |
| `scripts/compare_all.py` | original vs subtraction vs LavaSR A/B/C |
| `scripts/process_audio_lavasr.py` | library-style LavaSR helper (in-process) |
| `weights/` | LavaSR weights (enhancer_v2 + denoiser) via git-lfs |
| `config/dfn2d.service.example` | systemd unit template for the daemon |
| `config/requirements_pinned.txt` | exact working pip versions |
| `LavaSR/` | LavaSR package source (copy into site-packages) |
| `patch/` | vocos "matcha" branch files (overwrite site-packages/vocos/) |

## Troubleshooting

| symptom | fix |
|---|---|
| `TypeError: ... unexpected keyword 'f_min'` (vocos) | re-run `./setup.sh` (re-patches vocos) |
| CUDA/libcublas errors | reinstall `torch==2.4.1+cpu` from the CPU index |
| no `/tmp/dfn2d.sock` | `sudo systemctl restart dfn2d`; otherwise client auto-spawns daemon |
| grain/musical noise in output | use `dfn2 "file" soft` (spectral reduction of noise-like bins) |
| weights re-download | shouldn't happen — weights ship in this repo (`weights/`) |