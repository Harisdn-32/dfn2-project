"""Subtract reference noise from a noisy clip and play only the result."""
import sys

import numpy as np
import librosa
import sounddevice as sd
import soundfile as sf

PRIMARY_PATH = sys.argv[1] if len(sys.argv) > 1 else "/home/hari/Desktop/new_noised_audio.mp3"
REFERENCE_PATH = "/home/hari/Desktop/uncut_noise.mp3"
OUT_PATH = "/home/hari/dfn-prototype/new_noised_subtracted.wav"
SR = 48000

primary, _ = librosa.load(PRIMARY_PATH, sr=SR, mono=True)
reference, _ = librosa.load(REFERENCE_PATH, sr=SR, mono=True)
primary = primary.astype(np.float64)
reference = reference.astype(np.float64)

n = min(len(primary), len(reference))
primary = primary[:n]
reference = reference[:n]

alpha = float(np.sum(primary * reference) / np.sum(reference ** 2))
subtracted = primary - alpha * reference

m = np.max(np.abs(subtracted))
subtracted_n = (subtracted / m * 0.5).astype(np.float32) if m > 0 else subtracted.astype(np.float32)

print(f"Alpha: {alpha:.6f}")

sf.write(OUT_PATH, subtracted_n, SR, subtype="PCM_16")
print(f"Saved: {OUT_PATH}")

print("Playing: Subtracted version...")
sd.play(subtracted_n, SR)
sd.wait()
print("Done.")
