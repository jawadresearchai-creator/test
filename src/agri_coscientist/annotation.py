from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.parse import quote
from urllib.request import Request, urlopen
import json


class AnnotationError(RuntimeError):
    pass


class BuildMismatchError(AnnotationError):
    pass


@dataclass(frozen=True)
class GenomeBuild:
    species: str
    assembly: str
    provider: str
    provider_release: str
    provider_species: str
    gprofiler_organism: str | None = None
    accession: str | None = None


@dataclass(frozen=True)
class GeneAnnotation:
    gene_id: str
    species: str
    assembly: str
    biotype: str | None
    symbol: str | None
    description: str | None
    seq_region: str | None
    start: int | None
    end: int | None
    strand: int | None
    provider: str
    raw: dict


WHEAT_IWGSC_V1 = GenomeBuild(
    species="Triticum aestivum",
    assembly="IWGSC",
    provider="Ensembl Plants",
    provider_release="63",
    provider_species="Triticum_aestivum",
    gprofiler_organism="taestivum",
    accession="GCA_900519105.1",
)

WHEAT_REFSEQ_V2 = GenomeBuild(
    species="Triticum aestivum",
    assembly="IWGSC_RefSeq_v2.1",
    provider="Ensembl Plants",
    provider_release="63",
    provider_species="Triticum_aestivum_refseqv2",
    gprofiler_organism="tarefseqv2",
    accession="GCA_018294505.1",
)

BUILD_REGISTRY = {
    WHEAT_IWGSC_V1.assembly: WHEAT_IWGSC_V1,
    WHEAT_REFSEQ_V2.assembly: WHEAT_REFSEQ_V2,
}


class GeneAnnotationAdapter(Protocol):
    def lookup(self, gene_id: str, build: GenomeBuild) -> GeneAnnotation: ...


def _as_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalise_species(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _annotation_from_raw(gene_id: str, build: GenomeBuild, raw: dict, provider: str) -> GeneAnnotation:
    observed_assembly = raw.get("assembly_name") or raw.get("assembly")
    if not observed_assembly:
        raise AnnotationError(f"provider returned no assembly for {gene_id}")
    if observed_assembly != build.assembly:
        raise BuildMismatchError(
            f"{gene_id} belongs to assembly {observed_assembly!r}, expected {build.assembly!r}"
        )

    observed_species = str(raw.get("species") or "")
    if observed_species:
        allowed = {
            _normalise_species(build.species),
            _normalise_species(build.provider_species),
        }
        if _normalise_species(observed_species) not in allowed:
            raise BuildMismatchError(
                f"{gene_id} belongs to species {observed_species!r}, expected one of {sorted(allowed)!r}"
            )

    return GeneAnnotation(
        gene_id=str(raw.get("id") or gene_id),
        species=build.species,
        assembly=observed_assembly,
        biotype=raw.get("biotype"),
        symbol=raw.get("display_name") or raw.get("external_name"),
        description=raw.get("description"),
        seq_region=raw.get("seq_region_name"),
        start=_as_int(raw.get("start")),
        end=_as_int(raw.get("end")),
        strand=_as_int(raw.get("strand")),
        provider=provider,
        raw=raw,
    )


class _JsonLookupAdapter:
    def __init__(self, *, opener: Callable = urlopen, timeout: int = 30,
                 user_agent: str = "Agriculture-CoScientist-test/0.4"):
        self.opener = opener
        self.timeout = timeout
        self.user_agent = user_agent

    def _json_get(self, url: str) -> dict:
        request = Request(url, headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        })
        with self.opener(request, timeout=self.timeout) as response:
            payload = response.read()
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AnnotationError("annotation provider returned invalid JSON") from exc


class EnsemblRestAdapter(_JsonLookupAdapter):
    """Authoritative stable-ID lookup using Ensembl REST with species restriction."""

    def __init__(self, *, base_url: str = "https://rest.ensembl.org", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    def lookup(self, gene_id: str, build: GenomeBuild) -> GeneAnnotation:
        gene_id = gene_id.strip()
        if not gene_id:
            raise ValueError("gene_id is required")
        species = quote(build.provider_species.lower(), safe="_")
        url = (
            f"{self.base_url}/lookup/id/{quote(gene_id, safe='')}"
            f"?species={species};content-type=application/json"
        )
        raw = self._json_get(url)
        return _annotation_from_raw(gene_id, build, raw, "Ensembl REST")


class GrameneEnsemblAdapter(_JsonLookupAdapter):
    """Optional Gramene Ensembl-compatible lookup; exact-build matching is mandatory."""

    def __init__(self, *, base_url: str = "https://data.gramene.org/ensembl", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")

    def lookup(self, gene_id: str, build: GenomeBuild) -> GeneAnnotation:
        gene_id = gene_id.strip()
        if not gene_id:
            raise ValueError("gene_id is required")
        url = f"{self.base_url}/lookup/id/{quote(gene_id, safe='')}?content-type=application/json"
        raw = self._json_get(url)
        return _annotation_from_raw(gene_id, build, raw, "Gramene/Ensembl")
