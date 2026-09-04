from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from agri_coscientist.annotation import BUILD_REGISTRY, EnsemblRestAdapter
from agri_coscientist.enrichment import GProfilerAdapter, GProfilerProfileResponse
from agri_coscientist.scenario import ScenarioError


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def finite_float(value: str | None) -> float | None:
    if value in (None, "", "NA", "NaN"):
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def write_results(path: Path, rows) -> None:
    payload = [
        {
            "term_id": r.term_id,
            "name": r.name,
            "source": r.source,
            "q_value": r.q_value,
            "query_size": r.query_size,
            "background_size": r.background_size,
            "term_size": r.term_size,
            "intersection_size": r.intersection_size,
            "intersection": list(r.intersection),
            "provider": r.provider,
        }
        for r in rows
    ]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def resolve_build_sentinel(background: list[str], build):
    adapter = EnsemblRestAdapter(user_agent="Agriculture-CoScientist-test/0.4")
    failures: list[str] = []
    for gene_id in background[:50]:
        try:
            annotation = adapter.lookup(gene_id, build)
        except Exception as exc:
            failures.append(f"{gene_id}: {type(exc).__name__}")
            continue
        if annotation.assembly != build.assembly:
            raise ScenarioError(
                f"tested-gene sentinel {gene_id} resolved to {annotation.assembly}, expected {build.assembly}"
            )
        return annotation, failures
    raise ScenarioError(
        "none of the first 50 tested genes resolved against the locked Ensembl assembly; "
        f"first failures: {failures[:5]}"
    )


def mapping_qc(
    response: GProfilerProfileResponse,
    query: list[str],
    background: list[str],
    *,
    min_query_fraction: float,
    min_background_fraction: float,
) -> dict:
    if not response.results:
        raise ScenarioError(
            "g:Profiler returned no GO result rows with all_results enabled; mapping coverage cannot be established"
        )
    mapped_query = max(r.query_size for r in response.results)
    mapped_background = max(r.background_size for r in response.results)
    query_fraction = min(1.0, mapped_query / len(query))
    background_fraction = min(1.0, mapped_background / len(background))
    if query_fraction < min_query_fraction:
        raise ScenarioError(
            f"g:Profiler candidate-query mapping coverage {query_fraction:.3f} is below locked minimum {min_query_fraction:.3f}"
        )
    if background_fraction < min_background_fraction:
        raise ScenarioError(
            f"g:Profiler background mapping coverage {background_fraction:.3f} is below locked minimum {min_background_fraction:.3f}"
        )
    genes_metadata = response.meta.get("genes_metadata") if isinstance(response.meta, dict) else None
    return {
        "input_query_genes": len(query),
        "mapped_query_genes_effective": mapped_query,
        "query_mapping_fraction": query_fraction,
        "input_background_genes": len(background),
        "mapped_background_genes_effective": mapped_background,
        "background_mapping_fraction": background_fraction,
        "min_query_mapping_fraction": min_query_fraction,
        "min_background_mapping_fraction": min_background_fraction,
        "provider_genes_metadata": genes_metadata,
        "status": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()

    manifest = json.loads((run_dir / "manifest.json").read_text())
    lock = json.loads((run_dir / "analysis_lock.json").read_text())
    marker = json.loads((run_dir / "PRE_OUTCOME_LOCK_COMPLETE.json").read_text())
    if marker.get("pre_outcome_boundary") != "COMPLETE":
        raise ScenarioError("pre-outcome lock is not complete")
    if marker.get("analysis_lock_sha256") != lock.get("analysis_lock_sha256"):
        raise ScenarioError("analysis lock marker mismatch")

    build_name = manifest["genome_build"]["assembly"]
    build = BUILD_REGISTRY.get(build_name)
    if build is None:
        raise ScenarioError(f"unregistered genome build: {build_name}")
    if build.accession != manifest["genome_build"]["accession"]:
        raise ScenarioError("manifest genome accession does not match build registry")
    if build.gprofiler_organism != manifest["genome_build"]["gprofiler_organism"]:
        raise ScenarioError("manifest g:Profiler organism does not match build registry")

    de_path = run_dir / "results" / "deseq2_all_genes.csv"
    if not de_path.exists():
        raise ScenarioError("DESeq2 results are missing")
    rows = read_rows(de_path)
    if not rows:
        raise ScenarioError("DESeq2 results are empty")

    background = [r["Geneid"] for r in rows if r.get("Geneid")]
    if len(background) != len(set(background)):
        raise ScenarioError("DESeq2 tested-gene universe contains duplicate IDs")
    if not background:
        raise ScenarioError("enrichment background is empty")

    annotation, sentinel_failures = resolve_build_sentinel(background, build)

    analysis = manifest["analysis"]
    fdr = float(analysis["fdr_threshold"])
    effect = float(analysis["effect_threshold_for_enrichment"])
    min_query_mapping = float(analysis["min_query_mapping_fraction"])
    min_background_mapping = float(analysis["min_background_mapping_fraction"])
    if analysis.get("enrichment_all_results_for_mapping_qc") is not True:
        raise ScenarioError("mapping-QC all-results policy is not enabled")

    up: list[str] = []
    down: list[str] = []
    for row in rows:
        padj = finite_float(row.get("padj"))
        lfc = finite_float(row.get("log2FoldChange"))
        if padj is None or lfc is None or padj > fdr or abs(lfc) < effect:
            continue
        if lfc > 0:
            up.append(row["Geneid"])
        elif lfc < 0:
            down.append(row["Geneid"])

    out_dir = run_dir / "results" / "enrichment"
    out_dir.mkdir(parents=True, exist_ok=True)
    gp = GProfilerAdapter(user_agent="Agriculture-CoScientist-test/0.4")
    versions = gp.data_versions(build)

    directional = {}
    for direction, query in (("up", up), ("down", down)):
        if query:
            response = gp.profile_response(
                query,
                background,
                build,
                sources=("GO:BP", "GO:MF", "GO:CC"),
                user_threshold=fdr,
                all_results=True,
            )
            qc = mapping_qc(
                response,
                query,
                background,
                min_query_fraction=min_query_mapping,
                min_background_fraction=min_background_mapping,
            )
            significant = [
                r for r in response.results
                if r.q_value <= fdr and (r.raw or {}).get("significant", True) is not False
            ]
            meta_payload = {
                "mapping_qc": qc,
                "provider_meta": response.meta,
                "all_result_rows": len(response.results),
                "significant_result_rows": len(significant),
            }
            (out_dir / f"gprofiler_{direction}_metadata.json").write_text(
                json.dumps(meta_payload, indent=2, sort_keys=True) + "\n"
            )
        else:
            significant = []
            qc = {
                "input_query_genes": 0,
                "status": "NOT_APPLICABLE_NO_CANDIDATES",
                "min_query_mapping_fraction": min_query_mapping,
                "min_background_mapping_fraction": min_background_mapping,
            }
            (out_dir / f"gprofiler_{direction}_metadata.json").write_text(
                json.dumps({"mapping_qc": qc, "provider_meta": None}, indent=2, sort_keys=True) + "\n"
            )
        write_results(out_dir / f"gprofiler_{direction}.json", significant)
        directional[direction] = {
            "query_genes": len(query),
            "mapping_qc": qc,
            "significant_terms": len(significant),
            "top_terms": [
                {"term_id": r.term_id, "name": r.name, "source": r.source, "q_value": r.q_value}
                for r in significant[:10]
            ],
        }

    report = {
        "scenario_id": manifest["scenario_id"],
        "capability_only": True,
        "assembly": build.assembly,
        "assembly_accession": build.accession,
        "gprofiler_organism": build.gprofiler_organism,
        "tested_gene_sentinel": {
            "gene_id": annotation.gene_id,
            "observed_assembly": annotation.assembly,
            "seq_region": annotation.seq_region,
            "failed_candidates_before_success": sentinel_failures,
        },
        "background_genes": len(background),
        "background_definition": "all genes passing locked total-count prefilter",
        "thresholds": {
            "padj": fdr,
            "abs_log2FoldChange": effect,
            "min_query_mapping_fraction": min_query_mapping,
            "min_background_mapping_fraction": min_background_mapping,
        },
        "gprofiler_data_versions": versions,
        "directions": directional,
        "analysis_lock_sha256": lock["analysis_lock_sha256"],
        "status": "PASS",
    }
    (out_dir / "enrichment_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
