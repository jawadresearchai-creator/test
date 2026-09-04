from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path

from agri_coscientist.annotation import BUILD_REGISTRY
from agri_coscientist.scenario import ScenarioError, canonical_hash, file_sha256, verify_freeze_file

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    if not path.exists():
        raise ScenarioError(f"missing required artifact: {path}")
    return json.loads(path.read_text())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ScenarioError(f"missing required result: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def finite_float(value: str | None) -> float | None:
    if value in (None, "", "NA", "NaN"):
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def check_hash_map(items: dict[str, str], label: str) -> None:
    if not items:
        raise ScenarioError(f"analysis lock contains no {label} hashes")
    for relative, expected in items.items():
        path = ROOT / relative
        if not path.is_file():
            raise ScenarioError(f"{label} lock input missing: {relative}")
        observed = file_sha256(path)
        if observed != expected:
            raise ScenarioError(f"{label} drift: {relative}: {observed} != {expected}")


def check_execution_context(lock: dict, marker: dict) -> dict:
    locked = lock.get("execution_context") or {}
    if marker.get("execution_context") != locked:
        raise ScenarioError("pre-outcome marker execution context differs from Analysis Lock")
    expected_repo = "jawadresearchai-creator/test"
    if locked.get("github_repository") not in (None, expected_repo):
        raise ScenarioError(f"Analysis Lock belongs to unexpected repository: {locked.get('github_repository')}")
    current = {
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_workflow": os.environ.get("GITHUB_WORKFLOW"),
        "github_workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
        "github_repository": os.environ.get("GITHUB_REPOSITORY"),
        "github_ref": os.environ.get("GITHUB_REF"),
    }
    for key, observed in current.items():
        expected = locked.get(key)
        if observed is not None and expected != observed:
            raise ScenarioError(f"execution-context drift for {key}: {observed!r} != {expected!r}")
    return locked


def validate_conversion_qc(qc: dict, expected_input: int, minimum: float, label: str) -> None:
    if qc.get("method") != "g:Convert->ENSG" or qc.get("status") != "PASS":
        raise ScenarioError(f"{label} g:Convert mapping QC did not pass")
    if int(qc.get("input_genes", -1)) != expected_input:
        raise ScenarioError(f"{label} mapping-QC input size mismatch")
    mapped = int(qc.get("unambiguously_mapped_genes", -1))
    unmapped = int(qc.get("unmapped_count", -1))
    ambiguous = int(qc.get("ambiguous_count", -1))
    if min(mapped, unmapped, ambiguous) < 0 or mapped + unmapped + ambiguous != expected_input:
        raise ScenarioError(f"{label} mapping categories do not partition the input gene list")
    observed_fraction = float(qc.get("mapping_fraction", -1))
    expected_fraction = mapped / expected_input if expected_input else 0.0
    if abs(observed_fraction - expected_fraction) > 1e-12:
        raise ScenarioError(f"{label} mapping fraction is internally inconsistent")
    if observed_fraction < minimum or observed_fraction > 1.0:
        raise ScenarioError(f"{label} mapping coverage is below the locked minimum")
    if float(qc.get("minimum_mapping_fraction", -1)) != minimum:
        raise ScenarioError(f"{label} mapping threshold differs from lock")
    for hash_key in ("unmapped_ids_sha256", "ambiguous_ids_sha256"):
        value = qc.get(hash_key)
        if not isinstance(value, str) or len(value) != 64:
            raise ScenarioError(f"{label} missing deterministic {hash_key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()

    manifest = load_json(run_dir / "manifest.json")
    freeze = load_json(run_dir / "dataset_freeze.json")
    lock = load_json(run_dir / "analysis_lock.json")
    marker = load_json(run_dir / "PRE_OUTCOME_LOCK_COMPLETE.json")
    de_summary = load_json(run_dir / "results" / "deseq2_summary.json")
    enrichment = load_json(run_dir / "results" / "enrichment" / "enrichment_summary.json")
    python_session = load_json(run_dir / "python_session_info.json")
    r_session = load_json(run_dir / "r_session_info.json")

    if manifest.get("capability_only") is not True:
        raise ScenarioError("scenario lost capability-only boundary")
    if file_sha256(run_dir / "manifest.json") != lock.get("manifest_sha256"):
        raise ScenarioError("manifest bytes differ from analysis lock")

    freeze_copy = {k: v for k, v in freeze.items() if k != "freeze_sha256"}
    if canonical_hash(freeze_copy) != freeze.get("freeze_sha256"):
        raise ScenarioError("dataset freeze self-hash is invalid")
    lock_copy = {k: v for k, v in lock.items() if k != "analysis_lock_sha256"}
    if canonical_hash(lock_copy) != lock.get("analysis_lock_sha256"):
        raise ScenarioError("analysis lock self-hash is invalid")

    if marker.get("pre_outcome_boundary") != "COMPLETE" or marker.get("count_rows_inspected") is not False:
        raise ScenarioError("pre-outcome provenance marker is invalid")
    if marker.get("dataset_freeze_sha256") != freeze["freeze_sha256"]:
        raise ScenarioError("marker/dataset-freeze mismatch")
    if marker.get("analysis_lock_sha256") != lock["analysis_lock_sha256"]:
        raise ScenarioError("marker/analysis-lock mismatch")
    execution_context = check_execution_context(lock, marker)

    check_hash_map(lock.get("script_hashes", {}), "code")
    check_hash_map(lock.get("environment_hashes", {}), "environment")

    for asset in freeze.get("assets", []):
        asset_id = asset["asset_id"]
        relative = freeze["asset_paths"].get(asset_id)
        if not relative:
            raise ScenarioError(f"no local path frozen for {asset_id}")
        verify_freeze_file(run_dir / relative, asset["sha256"], int(asset["bytes"]))

    build_name = manifest["genome_build"]["assembly"]
    build = BUILD_REGISTRY.get(build_name)
    if build is None:
        raise ScenarioError(f"unregistered build in final bundle: {build_name}")
    if build.accession != manifest["genome_build"]["accession"]:
        raise ScenarioError("final bundle genome accession/build mismatch")

    if de_summary.get("status") != "PASS" or enrichment.get("status") != "PASS":
        raise ScenarioError("one or more scientific execution stages did not pass")
    if de_summary.get("analysis_lock_sha256") != lock["analysis_lock_sha256"]:
        raise ScenarioError("DE result is not bound to current analysis lock")
    if de_summary.get("dataset_freeze_sha256") != freeze["freeze_sha256"]:
        raise ScenarioError("DE result is not bound to current dataset freeze")
    if enrichment.get("analysis_lock_sha256") != lock["analysis_lock_sha256"]:
        raise ScenarioError("enrichment result is not bound to current analysis lock")
    if enrichment.get("assembly") != build.assembly or enrichment.get("assembly_accession") != build.accession:
        raise ScenarioError("enrichment output is not bound to locked genome build")

    analysis = manifest["analysis"]
    if de_summary.get("independent_filtering") is not False or analysis.get("independent_filtering") is not False:
        raise ScenarioError("independent filtering policy drifted")
    if de_summary.get("cooks_cutoff") is not False or analysis.get("cooks_cutoff") is not False:
        raise ScenarioError("Cook's-distance exclusion policy drifted")
    if de_summary.get("outlier_policy") != "report_not_exclude" or analysis.get("outlier_policy") != "report_not_exclude":
        raise ScenarioError("outlier handling policy drifted")
    if de_summary.get("p_adjust_method") != "BH" or analysis.get("fdr_method") != "BH":
        raise ScenarioError("multiple-testing policy drifted")
    if analysis.get("enrichment_all_results_for_mapping_qc") is not True:
        raise ScenarioError("mapping-QC all-results policy drifted")
    if not (run_dir / "r_session_info.txt").is_file():
        raise ScenarioError("human-readable R session evidence is missing from final bundle")

    python_lock = load_json(ROOT / "environments" / "python-stack-lock.json")
    if python_session.get("python") != python_lock.get("python"):
        raise ScenarioError("executed Python version differs from frozen environment")
    if python_session.get("packages") != python_lock.get("packages"):
        raise ScenarioError("executed Python package versions differ from frozen environment")
    if execution_context.get("github_sha") is not None and python_session.get("github_sha") != execution_context.get("github_sha"):
        raise ScenarioError("Python runtime evidence is bound to a different commit")
    if execution_context.get("github_run_id") is not None and python_session.get("github_run_id") != execution_context.get("github_run_id"):
        raise ScenarioError("Python runtime evidence is bound to a different workflow run")

    r_lock = load_json(ROOT / "environments" / "v04-r-stack-lock.json")
    if r_session.get("r") != r_lock.get("r"):
        raise ScenarioError("executed R version differs from frozen v0.4 environment")
    if r_session.get("packages") != r_lock.get("packages"):
        raise ScenarioError("executed R package versions differ from frozen v0.4 environment")
    if execution_context.get("github_sha") is not None and r_session.get("github_sha") != execution_context.get("github_sha"):
        raise ScenarioError("R runtime evidence is bound to a different commit")
    if execution_context.get("github_run_id") is not None and r_session.get("github_run_id") != execution_context.get("github_run_id"):
        raise ScenarioError("R runtime evidence is bound to a different workflow run")
    if execution_context.get("github_run_attempt") is not None and r_session.get("github_run_attempt") != execution_context.get("github_run_attempt"):
        raise ScenarioError("R runtime evidence is bound to a different workflow attempt")

    rows = read_csv(run_dir / "results" / "deseq2_all_genes.csv")
    if not rows:
        raise ScenarioError("DESeq2 tested-gene table is empty")
    genes = [r.get("Geneid", "") for r in rows]
    if any(not g for g in genes) or len(genes) != len(set(genes)):
        raise ScenarioError("tested-gene universe contains blank or duplicate IDs")
    if int(de_summary["genes_after_prefilter"]) != len(rows):
        raise ScenarioError("DE summary tested-gene count disagrees with result table")
    if int(enrichment["background_genes"]) != len(rows):
        raise ScenarioError("enrichment background is not the locked tested-gene universe")

    fdr = float(analysis["fdr_threshold"])
    effect = float(analysis["effect_threshold_for_enrichment"])
    min_query_mapping = float(analysis["min_query_mapping_fraction"])
    min_background_mapping = float(analysis["min_background_mapping_fraction"])
    thresholds = enrichment.get("thresholds") or {}
    if float(de_summary["fdr_threshold"]) != fdr:
        raise ScenarioError("DE FDR threshold differs from lock")
    if float(de_summary["enrichment_effect_threshold_abs_log2fc"]) != effect:
        raise ScenarioError("DE effect threshold differs from lock")
    if float(thresholds.get("padj", -1)) != fdr or float(thresholds.get("abs_log2FoldChange", -1)) != effect:
        raise ScenarioError("enrichment thresholds differ from lock")
    if float(thresholds.get("min_query_mapping_fraction", -1)) != min_query_mapping:
        raise ScenarioError("query mapping threshold differs from lock")
    if float(thresholds.get("min_background_mapping_fraction", -1)) != min_background_mapping:
        raise ScenarioError("background mapping threshold differs from lock")

    background_qc = enrichment.get("background_mapping_qc") or {}
    background_qc_file = load_json(run_dir / "results" / "enrichment" / "gprofiler_background_mapping_qc.json")
    if background_qc_file != background_qc:
        raise ScenarioError("background mapping QC file differs from enrichment summary")
    validate_conversion_qc(background_qc, len(rows), min_background_mapping, "background")

    expected_up: set[str] = set()
    expected_down: set[str] = set()
    for row in rows:
        padj = finite_float(row.get("padj"))
        lfc = finite_float(row.get("log2FoldChange"))
        if padj is not None and not 0 <= padj <= 1:
            raise ScenarioError(f"invalid adjusted p-value for {row['Geneid']}")
        if padj is None or lfc is None or padj > fdr or abs(lfc) < effect:
            continue
        (expected_up if lfc > 0 else expected_down).add(row["Geneid"])

    if int(de_summary["significant_for_enrichment"]) != len(expected_up | expected_down):
        raise ScenarioError("DE summary significant-candidate count is inconsistent")
    if int(de_summary["up_for_enrichment"]) != len(expected_up):
        raise ScenarioError("DE summary up-candidate count is inconsistent")
    if int(de_summary["down_for_enrichment"]) != len(expected_down):
        raise ScenarioError("DE summary down-candidate count is inconsistent")

    expected_by_direction = {"up": expected_up, "down": expected_down}
    for direction, expected_genes in expected_by_direction.items():
        direction_summary = enrichment["directions"][direction]
        if int(direction_summary["query_genes"]) != len(expected_genes):
            raise ScenarioError(f"{direction}-enrichment query was altered after DE")
        query_qc = direction_summary.get("query_mapping_qc") or {}
        metadata = load_json(run_dir / "results" / "enrichment" / f"gprofiler_{direction}_metadata.json")
        if metadata.get("query_mapping_qc") != query_qc:
            raise ScenarioError(f"{direction} query mapping QC metadata differs from enrichment summary")
        if metadata.get("background_mapping_qc") != background_qc:
            raise ScenarioError(f"{direction} background mapping QC metadata differs from common background QC")
        term_rows = load_json(run_dir / "results" / "enrichment" / f"gprofiler_{direction}.json")
        if len(term_rows) != int(direction_summary["significant_terms"]):
            raise ScenarioError(f"{direction} significant-term count differs from result file")
        if int(metadata.get("significant_result_rows", -1)) != len(term_rows):
            raise ScenarioError(f"{direction} metadata/result significant-term counts differ")
        for term in term_rows:
            q = float(term["q_value"])
            if not 0 <= q <= fdr:
                raise ScenarioError(f"{direction} enrichment contains a term outside locked FDR threshold")
            domain = int(term.get("statistical_domain_size", 0))
            if domain <= 0:
                raise ScenarioError(f"{direction} enrichment term lacks a valid statistical domain size")
        if expected_genes:
            validate_conversion_qc(query_qc, len(expected_genes), min_query_mapping, f"{direction} query")
            if not isinstance(metadata.get("provider_meta"), dict):
                raise ScenarioError(f"{direction} raw g:Profiler enrichment metadata is missing")
            if int(metadata.get("all_result_rows", -1)) < len(term_rows):
                raise ScenarioError(f"{direction} all-results count is smaller than significant result count")
            domains = metadata.get("statistical_domain_sizes")
            if not isinstance(domains, list) or not all(int(x) > 0 for x in domains):
                raise ScenarioError(f"{direction} statistical-domain diagnostics are invalid")
        else:
            if query_qc.get("status") != "NOT_APPLICABLE_NO_CANDIDATES":
                raise ScenarioError(f"{direction} zero-candidate mapping status is invalid")
            if term_rows:
                raise ScenarioError(f"{direction} has enrichment terms despite zero candidate genes")
            if metadata.get("provider_meta") is not None:
                raise ScenarioError(f"{direction} should not have provider enrichment metadata with zero candidates")

    candidate_rows = read_csv(run_dir / "results" / "deseq2_enrichment_candidates.csv")
    candidate_genes = {r["Geneid"] for r in candidate_rows}
    if candidate_genes != expected_up | expected_down:
        raise ScenarioError("candidate export does not exactly match locked thresholds")

    audit = {
        "scenario_id": manifest["scenario_id"],
        "capability_only": True,
        "dataset_freeze_sha256": freeze["freeze_sha256"],
        "analysis_lock_sha256": lock["analysis_lock_sha256"],
        "execution_context": execution_context,
        "genome_build": {"assembly": build.assembly, "accession": build.accession},
        "tested_genes": len(rows),
        "up_candidates": len(expected_up),
        "down_candidates": len(expected_down),
        "checks": {
            "dataset_bytes_and_hashes": "PASS",
            "pre_outcome_lock": "PASS",
            "exact_github_execution_context": "PASS",
            "transitive_code_and_environments_unchanged": "PASS",
            "python_runtime_environment_evidence": "PASS",
            "r_runtime_environment_evidence": "PASS",
            "fixed_prefilter_BH_and_outlier_policy": "PASS",
            "candidate_reconstruction": "PASS",
            "custom_background_identity": "PASS",
            "gconvert_identifier_mapping_coverage": "PASS",
            "gprofiler_provider_metadata": "PASS",
            "statistical_domain_not_used_as_mapping_metric": "PASS",
            "directional_enrichment_integrity": "PASS",
            "genome_build_binding": "PASS",
        },
        "claim_boundary": {
            "allowed": "Capability demonstration and exploratory genotype-associated transcriptomic differences in this public dataset.",
            "prohibited": [
                "novel-study claim based only on this capability run",
                "causal validation",
                "new wet-lab gene-expression measurement",
                "claim that public omics came from the user's own experiment",
            ],
        },
        "status": "PASS",
    }
    audit_path = run_dir / "AUDIT_REPORT.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")

    bundle_files = {}
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file() and p.name != "BUNDLE_MANIFEST.json"):
        relative = str(path.relative_to(run_dir))
        bundle_files[relative] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
    bundle = {
        "scenario_id": manifest["scenario_id"],
        "analysis_lock_sha256": lock["analysis_lock_sha256"],
        "dataset_freeze_sha256": freeze["freeze_sha256"],
        "execution_context": execution_context,
        "files": bundle_files,
        "status": "PASS",
    }
    bundle["bundle_sha256"] = canonical_hash(bundle)
    (run_dir / "BUNDLE_MANIFEST.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", "bundle_sha256": bundle["bundle_sha256"], "files": len(bundle_files)}, indent=2))


if __name__ == "__main__":
    main()
