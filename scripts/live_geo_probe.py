from __future__ import annotations
import gzip
import hashlib
import io
import json
import urllib.request
from pathlib import Path

LOCK = json.loads(Path("environments/live-geo-probe-lock.json").read_text())
URL = LOCK["url"]
OUT = Path("live_geo_probe.json")

req = urllib.request.Request(URL, headers={"User-Agent": "Agriculture-CoScientist-test/0.2 (public scientific data capability probe)"})
with urllib.request.urlopen(req, timeout=60) as r:
    payload = r.read()
if len(payload) < 100_000:
    raise RuntimeError(f"unexpectedly small GEO payload: {len(payload)} bytes")
text = gzip.GzipFile(fileobj=io.BytesIO(payload)).read(4096).decode("utf-8", errors="replace")
if not text.strip():
    raise RuntimeError("downloaded GEO count file is empty after decompression")
report = {
    "url": URL,
    "bytes": len(payload),
    "sha256": hashlib.sha256(payload).hexdigest(),
    "first_line": text.splitlines()[0] if text.splitlines() else "",
}
for key in ("url", "bytes", "sha256", "first_line"):
    if report[key] != LOCK[key]:
        raise RuntimeError(f"public GEO provenance drift for {key}: expected {LOCK[key]!r}, observed {report[key]!r}")
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
