from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol

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
    """Contract-test adapter. Production adapters will wrap GEO/SRA/Expression Atlas APIs."""
    def __init__(self, records: list[OmicsRecord]):
        self.records={r.accession:r for r in records}
    def search(self, query: str) -> list[OmicsRecord]:
        q=query.lower()
        return [r for r in self.records.values() if q in ' '.join(map(str,[r.accession,r.organism,r.tissue,r.treatment])).lower()]
    def fetch_metadata(self, accession: str) -> OmicsRecord:
        return self.records[accession]
