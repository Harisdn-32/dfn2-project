"""LavaSR enhance helper (CPU, matches this venv's LavaEnhance2 API)."""
import os

import torch
import soundfile as sf
import numpy as np
from LavaSR.model import LavaEnhance2

# --- Setup Model ---
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
lava_model = LavaEnhance2("YatharthS/LavaSR", device=device)


def process_audio(input_file, input_sr=16000, denoise=True, batch=False):
    """Enhance input_file with LavaSR. Returns path of saved 48kHz WAV."""
    if input_file is None:
        raise ValueError("input_file is None — pass a valid audio path")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"File not found: {input_file}")

    audio, _ = lava_model.load_audio(input_file, input_sr=input_sr)
    with torch.inference_mode():
        out = lava_model.enhance(audio, denoise=denoise, batch=batch)
    out_np = out.cpu().numpy().squeeze().astype(np.float32)

    base, _ = os.path.splitext(input_file)
    out_path = f"{base}_lavasr.wav"
    sf.write(out_path, out_np, 48000, subtype="PCM_16")
    print(f"Saved: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dfn2_test_noisy.wav"
    denoise = not (len(sys.argv) > 2 and sys.argv[2] == "0")
    process_audio(src, denoise=denoise)
