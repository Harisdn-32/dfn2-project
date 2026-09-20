"""Compare: original vs dual-mic subtraction vs LavaSR denoise.

Saves all three to ~/Desktop/output/ then plays them in order.
"""
import os
import shutil
import socket

import numpy as np
import librosa
import sounddevice as sd
import soundfile as sf

PRIMARY_PATH = "/home/hari/Desktop/new_noised_audio.mp3"
REFERENCE_PATH = "/home/hari/Desktop/uncut_noise.mp3"
OUT_DIR = "/home/hari/Desktop/output"
SR = 48000
SOCK = "/tmp/dfn2d.sock"


def norm_peak(x, peak=0.9):
    m = np.max(np.abs(x))
    if m > 0:
        return (x / m * peak).astype(np.float32)
    return x.astype(np.float32)


os.makedirs(OUT_DIR, exist_ok=True)

# --- Original (48k mono) ---
primary, _ = librosa.load(PRIMARY_PATH, sr=SR, mono=True)
primary = primary.astype(np.float64)
original_n = norm_peak(primary)
sf.write(os.path.join(OUT_DIR, "original.wav"), original_n, SR, subtype="PCM_16")

# --- Subtracted (dual-mic algorithm) ---
reference, _ = librosa.load(REFERENCE_PATH, sr=SR, mono=True)
reference = reference.astype(np.float64)
n = min(len(primary), len(reference))
p, r = primary[:n], reference[:n]
alpha = float(np.sum(p * r) / np.sum(r ** 2))
subtracted_n = norm_peak(p - alpha * r, peak=0.5)
sf.write(os.path.join(OUT_DIR, "subtracted.wav"), subtracted_n, SR, subtype="PCM_16")
print(f"Alpha: {alpha:.6f}")

# --- Denoised (LavaSR via warm daemon) ---
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.settimeout(120)
    s.connect(SOCK)
    s.sendall(f"{os.path.abspath(PRIMARY_PATH)}|1".encode())
    reply = s.recv(65536).decode("utf-8", "replace")
if reply.startswith("ERR"):
    raise RuntimeError(f"daemon error: {reply[4:]}")
_, dur, _, daemon_out = reply.split("|", 3)
denoised, dnsr = sf.read(daemon_out, dtype="float32")
if dnsr != SR:  # resample to 48k if needed
    denoised = librosa.resample(denoised, orig_sr=dnsr, target_sr=SR)
denoised_n = norm_peak(denoised.astype(np.float64))
sf.write(os.path.join(OUT_DIR, "denoised.wav"), denoised_n, SR, subtype="PCM_16")
print(f"LavaSR enhanced {float(dur):.1f}s audio (daemon output: {daemon_out})")
print(f"Saved all three to: {OUT_DIR}")

# --- Playback in order (playback-only gains; saved files stay clean) ---
ORIGINAL_GAIN = 1.5  # boosted even if it clips, as requested
orig_play = np.clip(original_n * ORIGINAL_GAIN, -1, 1).astype(np.float32)
target_rms = float(np.sqrt(np.mean(orig_play.astype(np.float64) ** 2)))
sub_rms = float(np.sqrt(np.mean(subtracted_n.astype(np.float64) ** 2)))
if sub_rms > 0:
    sub_play = (subtracted_n * (target_rms / sub_rms)).astype(np.float32)
else:
    sub_play = subtracted_n
print(f"Playback RMS matched at: {target_rms:.4f}")

gap = np.zeros(SR, dtype=np.float32)
for label, sig in (
    ("Playing: Original...", orig_play),
    ("Playing: Subtracted (dual-mic algorithm)...", sub_play),
    ("Playing: Denoised (LavaSR)...", denoised_n),
):
    print(label)
    sd.play(sig, SR)
    sd.wait()
    sd.play(gap, SR)
    sd.wait()
print("Done.")
