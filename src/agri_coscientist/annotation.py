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


# Only builds that have been explicitly verified should enter this registry.
WHEAT_REFSEQ_V2 = GenomeBuild(
    species="Triticum aestivum",
    assembly="IWGSC_RefSeq_v2.1",
    provider="Ensembl Plants",
    provider_release="63",
    provider_species="Triticum_aestivum_refseqv2",
    gprofiler_organism="tarefseqv2",
    accession="GCA_018294505.1",
)

BUILD_REGISTRY = {WHEAT_REFSEQ_V2.assembly: WHEAT_REFSEQ_V2}


class GeneAnnotationAdapter(Protocol):
    def lookup(self, gene_id: str, build: GenomeBuild) -> GeneAnnotation: ...


class GrameneEnsemblAdapter:
    """Plant gene lookup through Gramene's Ensembl-compatible read-only API.

    The caller MUST supply the expected genome build. The adapter rejects a
    response whose assembly does not exactly match that build, preventing silent
    cross-assembly annotation mixing.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://data.gramene.org/ensembl",
        opener: Callable = urlopen,
        timeout: int = 30,
        user_agent: str = "Agriculture-CoScientist-test/0.3",
    ):
        self.base_url = base_url.rstrip("/")
        self.opener = opener
        self.timeout = timeout
        self.user_agent = user_agent

    def _json_get(self, url: str) -> dict:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        with self.opener(request, timeout=self.timeout) as response:
            payload = response.read()
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AnnotationError("annotation provider returned invalid JSON") from exc

    def lookup(self, gene_id: str, build: GenomeBuild) -> GeneAnnotation:
        gene_id = gene_id.strip()
        if not gene_id:
            raise ValueError("gene_id is required")
        url = f"{self.base_url}/lookup/id/{quote(gene_id, safe='')}?content-type=application/json"
        raw = self._json_get(url)
        observed_assembly = raw.get("assembly_name") or raw.get("assembly")
        if not observed_assembly:
            raise AnnotationError(f"provider returned no assembly for {gene_id}")
        if observed_assembly != build.assembly:
            raise BuildMismatchError(
                f"{gene_id} belongs to assembly {observed_assembly!r}, expected {build.assembly!r}"
            )
        observed_species = str(raw.get("species") or "").replace("_", " ")
        if observed_species and observed_species.lower() != build.species.lower():
            raise BuildMismatchError(
                f"{gene_id} belongs to species {observed_species!r}, expected {build.species!r}"
            )

        def as_int(value):
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        return GeneAnnotation(
            gene_id=str(raw.get("id") or gene_id),
            species=build.species,
            assembly=observed_assembly,
            biotype=raw.get("biotype"),
            symbol=raw.get("display_name") or raw.get("external_name"),
            description=raw.get("description"),
            seq_region=raw.get("seq_region_name"),
            start=as_int(raw.get("start")),
            end=as_int(raw.get("end")),
            strand=as_int(raw.get("strand")),
            provider="Gramene/Ensembl",
            raw=raw,
        )
