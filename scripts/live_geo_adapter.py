from __future__ import annotations
import json
from pathlib import Path
from agri_coscientist.repositories import GEOAdapter

record = GEOAdapter().fetch_metadata("GSE183508")
if record.accession != "GSE183508":
    raise RuntimeError(f"unexpected accession: {record.accession}")
if record.sample_count != 4:
    raise RuntimeError(f"unexpected sample count: {record.sample_count}")
if "wheat" not in str(record.metadata.get("series_title", "")).lower():
    raise RuntimeError("GSE183508 title no longer identifies wheat")
out = {
    "accession": record.accession,
    "organism": record.organism,
    "sample_count": record.sample_count,
    "raw_available": record.raw_available,
    "processed_available": record.processed_available,
    "series_title": record.metadata.get("series_title"),
    "family_soft_url": record.metadata.get("family_soft_url"),
}
Path("live_geo_adapter.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
