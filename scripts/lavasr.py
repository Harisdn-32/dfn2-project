#!/home/hari/dfn-prototype/bin/python -u
"""dfn2 <audio_path> [denoise]
   dfn2 <audio_path> spectrogram   [denoise 0/1]  after "spectrogram"

Client for the dfn2d (LavaSR) daemon. Model stays loaded in the daemon, so this
runs instantly. Denoised playback is amplified 2.5x; saved wavs stay clean.
Default mode: plays ORIGINAL then DENOISED(2.5x), then Play Again menu (1/2/0).
Spectrogram mode: saves Original+Denoised PNG and opens a Tkinter GUI with
buttons to play the saved audio files.
"""
import os, socket, subprocess, sys, threading, time, warnings
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import numpy as np
import soundfile as sf
import sounddevice as sd

SOCK = "/tmp/dfn2d.sock"
DAEMON = os.path.expanduser("~/dfn-prototype/dfn2d.py")
GAIN = 2.5

if len(sys.argv) < 2:
    print("usage: dfn2 <audio_path> [spectrogram] [denoise 0/1]")
    sys.exit(1)
path = os.path.expanduser(sys.argv[1])
denoise = True
gui = False
for a in sys.argv[2:]:
    la = a.lower()
    if la in ("spectrogram", "spec", "gui"):
        gui = True
    elif la in ("0", "false", "no"):
        denoise = False
    elif la in ("1", "true", "yes"):
        denoise = True
if not os.path.exists(path):
    print(f"File not found: {path}")
    sys.exit(1)


def daemon_up():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(SOCK)
        return True
    except OSError:
        return False


def spawn_daemon():
    subprocess.Popen([sys.executable, DAEMON],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        if daemon_up():
            return True
        time.sleep(0.2)
    return False


if not daemon_up():
    print("starting dfn2 daemon...", flush=True)
    if not spawn_daemon():
        print("ERROR: could not reach dfn2 daemon", file=sys.stderr)
        sys.exit(1)

t0 = time.time()
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.settimeout(120)
    s.connect(SOCK)
    s.sendall(f"{os.path.abspath(path)}|{1 if denoise else 0}".encode())
    reply = s.recv(65536).decode("utf-8", "replace")
dt = time.time() - t0
if reply.startswith("ERR"):
    print("daemon error:", reply[4:], file=sys.stderr)
    sys.exit(1)
_, dur, ogfile, outfile = reply.split("|", 3)
print(f"  {float(dur):.1f}s enhanced in {dt:.2f}s (denoise={denoise})", flush=True)
print(f"saved {outfile}", flush=True)


def play_file(fp, gain=1.0):
    d, sr = sf.read(fp, dtype="float32")
    if gain != 1.0:
        d = np.clip(d * gain, -1, 1)
    sd.play(d, int(sr))
    sd.wait()


def play_og():
    play_file(ogfile)


def play_en():
    play_file(outfile, GAIN)


def spectrogram_png():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    src, sr = sf.read(ogfile, dtype="float32")
    dns = sf.read(outfile, dtype="float32")[0]
    fig, ax = plt.subplots(2, 1, figsize=(14, 6))
    fig.subplots_adjust(hspace=0.5, left=0.06, right=0.97, top=0.92, bottom=0.08)
    for axs, (d, s, t) in zip(ax, ((src, sr, "ORIGINAL"), (dns, 48000, "DENOISED"))):
        axs.specgram(d, NFFT=2048, Fs=s, noverlap=1024, cmap="magma")
        axs.set_title(t); axs.set_xlabel("time (s)"); axs.set_ylabel("Hz")
    spec = os.path.splitext(path)[0] + "_spec.png"
    fig.savefig(spec, dpi=90)
    plt.close(fig)
    return spec


if gui:
    spec = spectrogram_png()
    from PIL import Image, ImageTk
    import tkinter as tk
    import tkinter.ttk as ttk
    root = tk.Tk()
    root.title(f"dfn2 spectrogram - {os.path.basename(path)}")
    img = Image.open(spec)
    maxw, maxh = 1280, 600
    r = min(maxw / img.width, maxh / img.height, 1.0)
    img = img.resize((int(img.width * r), int(img.height * r)))
    ph = ImageTk.PhotoImage(img)
    tk.Label(root, image=ph).pack()
    btns = tk.Frame(root)
    btns.pack(pady=8)

    def og_t():
        threading.Thread(target=play_og, daemon=True).start()

    def en_t():
        threading.Thread(target=play_en, daemon=True).start()

    tk.Button(btns, text="▶ Play Original", command=og_t).pack(side="left", padx=8)
    tk.Button(btns, text="▶ Play Denoised (2.5x)", command=en_t).pack(side="left", padx=8)
    tk.Button(btns, text="✕ Exit", command=root.destroy).pack(side="left", padx=8)
    print(f"spectrogram: {spec}")
    root.mainloop()
    sys.exit(0)

print("▶ Played Original", flush=True)
play_og()
time.sleep(0.4)
print("▶ Played Denoised (2.5x)", flush=True)
play_en()

while True:
    try:
        r = input("\nPlay Again?  1=Original  2=Denoised  0=exit  : ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if r == "1":
        play_file(ogfile)
    elif r == "2":
        play_file(outfile, GAIN)
    elif r == "0":
        break
    else:
        print("enter 1, 2, or 0")