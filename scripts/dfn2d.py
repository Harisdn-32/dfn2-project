#!/home/hari/dfn-prototype/bin/python -u
"""dfn2d - LavaSR model daemon. Loads the model once at boot, serves requests
over a Unix socket so `dfn2 <path>` runs instantly (no model load cost).

Protocol (line-based over /tmp/dfn2d.sock):
  request : <abs_path>|0|1   (denoise flag, 0/1)
  reply   : OK|<dur_secs>|<original_wav>|<lavasr_wav>
            ERR|<message>
"""
import os, socket, warnings
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

SOCK = "/tmp/dfn2d.sock"

from huggingface_hub import logging as hf_logging
hf_logging.set_verbosity_error()

print("Loading dfn2 model...", flush=True)
from LavaSR.model import LavaEnhance2

_here = os.path.dirname(os.path.abspath(__file__))
_weights = os.path.join(_here, "weights")
model_path = _weights if os.path.isdir(_weights) else "YatharthS/LavaSR"
lava = LavaEnhance2(model_path, device="cpu")
print("dfn2d ready", flush=True)


def enhance(path, denoise):
    a, _ = lava.load_audio(path, input_sr=16000)
    out = lava.enhance(a, denoise=denoise, batch=False).cpu().numpy().squeeze()
    dur = a.shape[-1] / 16000
    base, _ = os.path.splitext(path)
    ogfile = f"{base}_original.wav"
    outfile = f"{base}_lavasr.wav"
    import soundfile as sf
    sf.write(ogfile, a.cpu().numpy().squeeze(), 16000)
    sf.write(outfile, out, 48000)
    return dur, ogfile, outfile


def main():
    try:
        os.unlink(SOCK)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    os.chmod(SOCK, 0o666)
    srv.listen(4)
    print(f"listening on {SOCK}", flush=True)
    while True:
        conn, _ = srv.accept()
        with conn:
            data = conn.recv(65536).decode("utf-8", "replace").strip()
            if not data:
                continue
            try:
                path, df = data.rsplit("|", 1)
                dur, og, out = enhance(path, df == "1")
                conn.sendall(f"OK|{dur:.2f}|{og}|{out}".encode())
            except Exception as e:
                conn.sendall(f"ERR|{e}".encode())


if __name__ == "__main__":
    main()