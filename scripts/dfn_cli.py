#!/home/hari/dfn-prototype/bin/python -u
"""dfn2 <audio_path> — LavaSR CLI with MP3 output.

  dfn2 <file>          enhance + save MP3, play original -> denoised, then menu
  dfn2 <file> soft     like above but with spectral grain reduction
  dfn2 <file> 1        play original only
  dfn2 <file> 2        play denoised only
"""
import os
import socket
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy.signal import stft, istft

SOCK = "/tmp/dfn2d.sock"
DAEMON = os.path.expanduser("~/dfn-prototype/dfn2d.py")
GAIN = 2.5
MBR = 192
FS = 48000

if len(sys.argv) < 2:
    print("usage: dfn2 <audio_path> [1=original 2=denoised]", file=sys.stderr)
    sys.exit(1)
path = os.path.expanduser(sys.argv[1])
if not os.path.exists(path):
    print(f"File not found: {path}", file=sys.stderr)
    sys.exit(1)

play_mode = sys.argv[2] if len(sys.argv) > 2 else None
soft = play_mode == "soft"


def daemon_up():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(SOCK)
        return True
    except OSError:
        return False


if not daemon_up():
    subprocess.Popen([sys.executable, DAEMON],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        if daemon_up():
            break
        time.sleep(0.2)
    else:
        print("ERROR: could not reach dfn2 daemon", file=sys.stderr)
        sys.exit(1)

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.settimeout(120)
    s.connect(SOCK)
    s.sendall(f"{os.path.abspath(path)}|1".encode())
    reply = s.recv(65536).decode("utf-8", "replace")
if reply.startswith("ERR"):
    print(f"daemon error: {reply[4:]}", file=sys.stderr)
    sys.exit(1)
_, _, ogfile, outfile = reply.split("|", 3)

# Optional spectral grain reduction: suppress noise-like bins, keep voice
if soft:
    d, _ = sf.read(outfile, dtype="float32")
    f, t, X = stft(d.astype(np.float64), fs=FS, nperseg=1024, noverlap=768, window="hann")
    mag = np.abs(X)
    noise = np.median(mag, axis=1)
    gain = 1 - 0.45 * np.minimum(1, noise[:, None] / np.maximum(mag, 1e-9))
    gain = np.clip(gain, 0.35, 1)
    _, out = istft(X * gain, fs=FS, nperseg=1024, noverlap=768)
    out = out[: sf.info(outfile).frames]
    out = out / max(np.abs(out).max(), 1e-9) * 0.9
    outfile = os.path.splitext(outfile)[0] + "_soft.wav"
    sf.write(outfile, out.astype(np.float32), FS)

# MP3 output next to input
mp3file = os.path.splitext(path)[0] + ("_soft.mp3" if soft else "_lavasr.mp3")
subprocess.run(["ffmpeg", "-y", "-i", outfile, "-b:a", f"{MBR}k", mp3file],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
print(f"saved {mp3file}", flush=True)


def play(fp, gain=1.0):
    d, sr = sf.read(fp, dtype="float32")
    if gain != 1.0:
        d = np.clip(d * gain, -1, 1)
    sd.play(d, int(sr))
    sd.wait()


if play_mode == "1":
    print("original:", flush=True)
    play(ogfile)
    sys.exit(0)

if play_mode == "2":
    print("denoised:", flush=True)
    play(outfile, GAIN)
    sys.exit(0)

print("original:", flush=True)
play(ogfile)
print("denoised:", flush=True)
play(outfile, GAIN)

while True:
    choice = input("Play Again? 1=Original 2=Denoised 0=exit: ").strip()
    if choice == "1":
        print("original:", flush=True)
        play(ogfile)
    elif choice == "2":
        print("denoised:", flush=True)
        play(outfile, GAIN)
    else:
        break