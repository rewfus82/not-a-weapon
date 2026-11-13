"""Download the trained Forge weights into models/forge/ (mechanics/ + writer/), verifying the checksum.

  python -m forge.fetch [--url URL] [--force]

The weights (~330 MB, fp32) are not in git; they live on a GitHub release. Retrained models: pack a models/forge-style
directory with `tar czf forge-models-<tag>.tar.gz -C models forge` and update URL + SHA256 below.
"""
import argparse
import hashlib
import io
import shutil
import sys
import tarfile
import urllib.request

from forge.mechanics import MODELS

URL = "https://github.com/InfinityZ25/not-a-weapon/releases/download/forge-v1/forge-models-v1.tar.gz"
SHA256 = "f7bb6e99ad0071b5235c53046b37f7934d5858da34a4ea58df207f0d9524db11"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=URL)
    ap.add_argument("--sha256", default=SHA256)
    ap.add_argument("--force", action="store_true", help="re-download even if models/forge exists")
    a = ap.parse_args()
    if (MODELS / "mechanics").is_dir() and (MODELS / "writer").is_dir() and not a.force:
        print(f"already present: {MODELS} (use --force to re-download)")
        return 0
    print(f"downloading {a.url}")
    buf = io.BytesIO()
    with urllib.request.urlopen(a.url) as r:
        total = int(r.headers.get("Content-Length", 0))
        while chunk := r.read(1 << 20):
            buf.write(chunk)
            if total and sys.stdout.isatty():
                print(f"\r  {buf.tell() / 2**20:.0f} / {total / 2**20:.0f} MB", end="", flush=True)
    print(f"  {buf.tell() / 2**20:.0f} MB")
    digest = hashlib.sha256(buf.getvalue()).hexdigest()
    if digest != a.sha256:
        print(f"checksum mismatch: got {digest}, expected {a.sha256}", file=sys.stderr)
        return 1
    if MODELS.exists():
        shutil.rmtree(MODELS)
    MODELS.parent.mkdir(parents=True, exist_ok=True)
    buf.seek(0)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        tar.extractall(MODELS.parent, filter="data")
    print(f"ok: {MODELS} (sha256 {digest[:12]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
