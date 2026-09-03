from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import gzip
import json
import re

from .geo import geo_stub

@dataclass(frozen=True)
class OmicsRecord:
    accession: str
    repository: str
    organism: str
    tissue: str | None
    treatment: str | None
    sample_count: int | None
    raw_available: bool
    processed_available: bool
    metadata: dict = field(default_factory=dict)

class OmicsRepositoryAdapter(Protocol):
    def search(self, query: str) -> list[OmicsRecord]: ...
    def fetch_metadata(self, accession: str) -> OmicsRecord: ...

class InMemoryAdapter:
    """Contract-test adapter."""
    def __init__(self, records: list[OmicsRecord]):
        self.records={r.accession:r for r in records}
    def search(self, query: str) -> list[OmicsRecord]:
        q=query.lower()
        return [r for r in self.records.values() if q in ' '.join(map(str,[r.accession,r.organism,r.tissue,r.treatment])).lower()]
    def fetch_metadata(self, accession: str) -> OmicsRecord:
        return self.records[accession]

class GEOAdapter:
    """Read-only NCBI GEO adapter using E-utilities plus family SOFT.

    Search returns preliminary ESummary records. fetch_metadata retrieves the
    series family SOFT file and extracts sample-level metadata without downloading
    raw sequencing reads. Network I/O is injectable for deterministic tests.
    """
    EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, *, timeout: int = 60, opener: Callable = urlopen,
                 user_agent: str = "Agriculture-CoScientist-test/0.2"):
        self.timeout = timeout
        self.opener = opener
        self.user_agent = user_agent

    def _get(self, url: str) -> bytes:
        req = Request(url, headers={"User-Agent": self.user_agent})
        with self.opener(req, timeout=self.timeout) as response:
            return response.read()

    def _json(self, endpoint: str, params: dict) -> dict:
        url = f"{self.EUTILS}/{endpoint}?{urlencode(params, doseq=True)}"
        return json.loads(self._get(url).decode("utf-8"))

    def search(self, query: str, *, retmax: int = 20) -> list[OmicsRecord]:
        found = self._json("esearch.fcgi", {
            "db": "gds", "term": query, "retmode": "json", "retmax": retmax,
        })
        ids = found.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        summary = self._json("esummary.fcgi", {
            "db": "gds", "id": ",".join(ids), "retmode": "json",
        }).get("result", {})
        records = []
        for uid in summary.get("uids", ids):
            row = summary.get(str(uid), {})
            accession = str(row.get("accession") or row.get("Accession") or "").upper()
            if not accession.startswith("GSE"):
                continue
            sample_count = row.get("n_samples") or row.get("samples")
            try:
                sample_count = int(sample_count) if sample_count is not None else None
            except (TypeError, ValueError):
                sample_count = None
            text = json.dumps(row, ensure_ascii=False)
            records.append(OmicsRecord(
                accession=accession,
                repository="GEO",
                organism=str(row.get("taxon") or row.get("organism") or "unknown"),
                tissue=None,
                treatment=None,
                sample_count=sample_count,
                raw_available="SRA" in text.upper(),
                processed_available=bool(row.get("suppFile") or row.get("suppfile")),
                metadata={"esummary": row},
            ))
        return records

    @staticmethod
    def family_soft_url(accession: str) -> str:
        acc = accession.strip().upper()
        if not re.fullmatch(r"GSE\d+", acc):
            raise ValueError("GEOAdapter.fetch_metadata requires a GSE accession")
        return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_stub(acc)}/{acc}/soft/{acc}_family.soft.gz"

    @staticmethod
    def _parse_soft(text: str) -> dict:
        series: dict[str, list[str]] = {}
        samples: list[dict[str, list[str]]] = []
        current: dict[str, list[str]] | None = None
        for raw in text.splitlines():
            line = raw.rstrip("\n")
            if line.startswith("^SAMPLE = "):
                current = {"geo_accession": [line.split("=", 1)[1].strip()]}
                samples.append(current)
                continue
            if line.startswith("!Series_") and " = " in line:
                key, value = line[1:].split(" = ", 1)
                series.setdefault(key, []).append(value)
            elif current is not None and line.startswith("!Sample_") and " = " in line:
                key, value = line[1:].split(" = ", 1)
                current.setdefault(key, []).append(value)
        return {"series": series, "samples": samples}

    def fetch_metadata(self, accession: str) -> OmicsRecord:
        acc = accession.strip().upper()
        payload = self._get(self.family_soft_url(acc))
        try:
            text = gzip.decompress(payload).decode("utf-8", errors="replace")
        except OSError as exc:
            raise ValueError("GEO family SOFT response is not valid gzip data") from exc
        parsed = self._parse_soft(text)
        series, samples = parsed["series"], parsed["samples"]
        organisms = sorted({v for s in samples for v in s.get("Sample_organism_ch1", []) if v})
        sources = sorted({v for s in samples for v in s.get("Sample_source_name_ch1", []) if v})
        treatments = sorted({v for s in samples for v in s.get("Sample_treatment_protocol_ch1", []) if v})
        relations = series.get("Series_relation", [])
        supplementary = [v for v in series.get("Series_supplementary_file", []) if v and v.upper() != "NONE"]
        organism = organisms[0] if len(organisms) == 1 else ("; ".join(organisms) if organisms else "unknown")
        tissue = sources[0] if len(sources) == 1 else None
        treatment = treatments[0] if len(treatments) == 1 else None
        return OmicsRecord(
            accession=acc,
            repository="GEO",
            organism=organism,
            tissue=tissue,
            treatment=treatment,
            sample_count=len(samples),
            raw_available=any("SRA" in value.upper() for value in relations),
            processed_available=bool(supplementary),
            metadata={
                "series_title": (series.get("Series_title") or [None])[0],
                "series_summary": series.get("Series_summary", []),
                "relations": relations,
                "supplementary_files": supplementary,
                "organisms": organisms,
                "sources": sources,
                "treatments": treatments,
                "sample_accessions": [s.get("geo_accession", [None])[0] for s in samples],
                "family_soft_url": self.family_soft_url(acc),
            },
        )
