"""Download pinned BGE-M3 ONNX INT8 artifacts to D-drive project storage."""
import hashlib
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = "onnx-community/bge-m3-ONNX"
REVISION = "25b9af8e87a38eb120cfe87125383677b9cd309e"
DEST = ROOT / "models" / "bge-m3-onnx-int8"
FILES = ["config.json", "tokenizer.json", "tokenizer_config.json", "onnx/model_int8.onnx"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    provenance = {"repo": REPO, "revision": REVISION, "base_model": "BAAI/bge-m3", "format": "ONNX INT8", "files": []}
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=20)) as client:
        response = client.get(f"https://huggingface.co/api/models/{REPO}/tree/{REVISION}?recursive=true&expand=false")
        response.raise_for_status()
        metadata = {item["path"]: item for item in response.json()}
        for name in FILES:
            info = metadata[name]
            target = DEST / name
            target.parent.mkdir(parents=True, exist_ok=True)
            expected = info.get("lfs", {}).get("oid")
            if not (target.exists() and target.stat().st_size == info["size"] and (not expected or sha256(target) == expected)):
                partial = target.with_suffix(target.suffix + ".part")
                print(f"Downloading {name}: {info['size'] / 1024 / 1024:.1f} MiB", flush=True)
                with client.stream("GET", f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}") as download:
                    download.raise_for_status()
                    last = time.monotonic()
                    written = 0
                    with partial.open("wb") as handle:
                        for block in download.iter_bytes(1024 * 1024):
                            handle.write(block)
                            written += len(block)
                            if time.monotonic() - last > 15:
                                print(f"  {written / 1024 / 1024:.1f} MiB received", flush=True)
                                last = time.monotonic()
                if partial.stat().st_size != info["size"] or (expected and sha256(partial) != expected):
                    raise RuntimeError(f"Artifact validation failed: {name}")
                partial.replace(target)
            digest = sha256(target)
            provenance["files"].append({"path": name, "size": target.stat().st_size, "sha256": digest, "upstream_lfs_sha256": expected})
            print(f"Verified {name}", flush=True)
    (ROOT / "docs" / "embedding-model.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print("Local embedding model ready.", flush=True)


if __name__ == "__main__":
    main()
