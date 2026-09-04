from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping
import gzip
import json


class ScenarioError(RuntimeError):
    pass


FEATURECOUNTS_ANNOTATION_COLUMNS = {
    "Geneid",
    "Chr",
    "Start",
    "End",
    "Strand",
    "Length",
}


@dataclass(frozen=True)
class FrozenAsset:
    asset_id: str
    url: str
    sha256: str
    bytes: int
    header: tuple[str, ...]


def canonical_hash(value: Mapping | list) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_gzip_header_bytes(payload: bytes) -> tuple[str, ...]:
    try:
        with gzip.GzipFile(fileobj=__import__("io").BytesIO(payload)) as fh:
            line = fh.readline().decode("utf-8").rstrip("\r\n")
    except Exception as exc:
        raise ScenarioError("count asset is not a readable gzip text file") from exc
    header = tuple(line.split("\t"))
    if len(header) < 2 or header[0] != "Geneid":
        raise ScenarioError(f"unexpected featureCounts header: {header[:6]!r}")
    return header


def count_columns(header: Iterable[str]) -> tuple[str, ...]:
    return tuple(c for c in header if c not in FEATURECOUNTS_ANNOTATION_COLUMNS)


def validate_featurecounts_header(header: Iterable[str], expected_replicates: int, label: str) -> tuple[str, ...]:
    header = tuple(header)
    if not header or header[0] != "Geneid":
        raise ScenarioError(f"{label}: featureCounts header must begin with Geneid")
    cols = count_columns(header)
    if len(cols) != expected_replicates:
        raise ScenarioError(
            f"{label}: expected {expected_replicates} count columns, found {len(cols)}: {cols!r}"
        )
    if len(set(cols)) != len(cols):
        raise ScenarioError(f"{label}: duplicate replicate columns")
    return cols


def validate_scenario_manifest(manifest: Mapping) -> None:
    required = {"scenario_id", "capability_only", "dataset", "genome_build", "contrast", "analysis"}
    missing = required - set(manifest)
    if missing:
        raise ScenarioError(f"manifest missing fields: {sorted(missing)}")
    if manifest["capability_only"] is not True:
        raise ScenarioError("v0.4 scenario must remain explicitly capability-only")
    if manifest["dataset"].get("representation") != "featurecounts_integer_counts":
        raise ScenarioError("DESeq2 scenario requires genuine integer count representation")
    groups = manifest["contrast"].get("groups") or []
    if len(groups) != 2:
        raise ScenarioError("v0.4 differential-expression contrast requires exactly two groups")
    for group in groups:
        if int(group.get("expected_replicates", 0)) < 3:
            raise ScenarioError("each comparison group requires at least three biological replicates")
    analysis = manifest["analysis"]
    if analysis.get("de_method") != "DESeq2" or analysis.get("design") != "~ genotype":
        raise ScenarioError("v0.4 confirmatory DE method/design is locked to DESeq2 with ~ genotype")
    if int(analysis.get("prefilter_total_count", -1)) != 10:
        raise ScenarioError("v0.4 prefilter is locked at total count >= 10")
    if analysis.get("independent_filtering") is not False:
        raise ScenarioError("v0.4 requires DESeq2 independent filtering disabled")
    if analysis.get("cooks_cutoff") is not False:
        raise ScenarioError("v0.4 requires Cook's-distance result exclusion disabled")
    if analysis.get("outlier_policy") != "report_not_exclude":
        raise ScenarioError("v0.4 outlier policy is report_not_exclude")
    if analysis.get("fdr_method") != "BH" or float(analysis.get("fdr_threshold", 2)) != 0.05:
        raise ScenarioError("v0.4 FDR policy must be BH at 0.05")
    if float(analysis.get("effect_threshold_for_enrichment", -1)) != 1.0:
        raise ScenarioError("v0.4 enrichment effect threshold is locked at |log2FC| >= 1")
    if analysis.get("enrichment_direction") != "separate_up_down":
        raise ScenarioError("v0.4 enrichment must keep up/down genes separate")
    if analysis.get("enrichment_background") != "all_genes_passing_locked_prefilter":
        raise ScenarioError("v0.4 enrichment background must be the locked tested-gene universe")
    if analysis.get("enrichment_provider") != "g:Profiler":
        raise ScenarioError("v0.4 enrichment provider is locked to g:Profiler")
    if analysis.get("enrichment_domain_scope") != "custom" or analysis.get("enrichment_correction") != "fdr":
        raise ScenarioError("v0.4 enrichment requires custom background with FDR correction")
    if analysis.get("enrichment_all_results_for_mapping_qc") is not True:
        raise ScenarioError("v0.4 requires all-result g:Profiler retrieval for mapping QC")
    if float(analysis.get("min_query_mapping_fraction", -1)) != 0.90:
        raise ScenarioError("v0.4 candidate-query mapping threshold is locked at 0.90")
    if float(analysis.get("min_background_mapping_fraction", -1)) != 0.90:
        raise ScenarioError("v0.4 background mapping threshold is locked at 0.90")


def build_dataset_freeze(manifest: Mapping, assets: Iterable[FrozenAsset]) -> dict:
    validate_scenario_manifest(manifest)
    rows = [
        {
            "asset_id": a.asset_id,
            "url": a.url,
            "sha256": a.sha256,
            "bytes": int(a.bytes),
            "header": list(a.header),
        }
        for a in assets
    ]
    if len(rows) != 2:
        raise ScenarioError("exactly two frozen count assets are required")
    freeze = {
        "scenario_id": manifest["scenario_id"],
        "dataset_accession": manifest["dataset"]["accession"],
        "representation": manifest["dataset"]["representation"],
        "assets": rows,
    }
    freeze["freeze_sha256"] = canonical_hash(freeze)
    return freeze


def build_analysis_lock(
    manifest: Mapping,
    dataset_freeze: Mapping,
    script_hashes: Mapping[str, str],
    environment_hashes: Mapping[str, str],
) -> dict:
    validate_scenario_manifest(manifest)
    lock = {
        "scenario_id": manifest["scenario_id"],
        "dataset_freeze_sha256": dataset_freeze["freeze_sha256"],
        "genome_build": manifest["genome_build"],
        "contrast": manifest["contrast"],
        "analysis": manifest["analysis"],
        "script_hashes": dict(sorted(script_hashes.items())),
        "environment_hashes": dict(sorted(environment_hashes.items())),
    }
    lock["analysis_lock_sha256"] = canonical_hash(lock)
    return lock


def verify_freeze_file(path: Path, expected_sha256: str, expected_bytes: int) -> None:
    observed_bytes = path.stat().st_size
    observed_hash = file_sha256(path)
    if observed_bytes != int(expected_bytes) or observed_hash != expected_sha256:
        raise ScenarioError(
            f"frozen asset drift: bytes={observed_bytes}/{expected_bytes}, sha256={observed_hash}/{expected_sha256}"
        )
