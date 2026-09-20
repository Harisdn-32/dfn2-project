"""Dual-mic noise subtraction demo.

Primary mic (voice + noise) + reference mic (noise only) -> least-squares
spectral-free time-domain subtraction, then sequential playback.
"""
import numpy as np
import librosa
import sounddevice as sd
import soundfile as sf

PRIMARY_PATH = "/home/hari/Desktop/voice_with_noise.mp3"
REFERENCE_PATH = "/home/hari/Desktop/uncut_noise.mp3"
OUT_PATH = "/home/hari/dfn-prototype/dual_mic_subtracted.wav"
SR = 48000

# 1. Load both MP3s, resample to 48kHz mono
primary, _ = librosa.load(PRIMARY_PATH, sr=SR, mono=True)
reference, _ = librosa.load(REFERENCE_PATH, sr=SR, mono=True)
primary = primary.astype(np.float64)
reference = reference.astype(np.float64)

# 2. Match lengths by trimming the longer to the shorter
n = min(len(primary), len(reference))
primary = primary[:n]
reference = reference[:n]

# 3. Least-squares optimal subtraction scaling
alpha = float(np.sum(primary * reference) / np.sum(reference ** 2))

# 4. Subtracted output
subtracted = primary - alpha * reference


def norm_peak(x, peak=0.9):
    m = np.max(np.abs(x))
    if m > 0:
        return (x / m * peak).astype(np.float32)
    return x.astype(np.float32)


# 5. Normalize: original stays at max clean level (0.9),
# subtracted played back quieter (0.5)
original_primary = norm_peak(primary)
original_reference = norm_peak(reference)
subtracted_n = norm_peak(subtracted, peak=0.5)

# 6. Metrics
input_rms = float(np.sqrt(np.mean(original_primary ** 2)))
output_rms = float(np.sqrt(np.mean(subtracted_n ** 2)))
residual = subtracted_n.astype(np.float64) - original_primary.astype(np.float64)
snr_db = float(
    10 * np.log10(np.sum(subtracted_n.astype(np.float64) ** 2) / np.sum(residual ** 2))
)

print(f"Alpha: {alpha:.6f}")
print(f"Input RMS (primary): {input_rms:.6f}")
print(f"Output RMS (subtracted): {output_rms:.6f}")
print(f"Estimated SNR improvement: {snr_db:.2f} dB")

# 7. Save subtracted output (48kHz, 16-bit PCM)
sf.write(OUT_PATH, subtracted_n, SR, subtype="PCM_16")
print(f"Saved: {OUT_PATH}")

# 8. Sequential playback with 1s silence gap
gap = np.zeros(SR, dtype=np.float32)

print("Playing: Original voice with noise...")
sd.play(original_primary, SR)
sd.wait()

sd.play(gap, SR)
sd.wait()

print("Playing: After dual-mic subtraction...")
sd.play(subtracted_n, SR)
sd.wait()

print("Done.")
