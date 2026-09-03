from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from agri_coscientist.annotation import BUILD_REGISTRY, EnsemblRestAdapter
from agri_coscientist.enrichment import GProfilerAdapter
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

    # Exact-build sentinel check before functional interpretation. This uses a
    # gene from the actual tested universe, not a hard-coded unrelated gene.
    sentinel = background[0]
    annotation = EnsemblRestAdapter(user_agent="Agriculture-CoScientist-test/0.4").lookup(sentinel, build)
    if annotation.assembly != build.assembly:
        raise ScenarioError("tested-gene sentinel does not resolve to locked assembly")

    fdr = float(manifest["analysis"]["fdr_threshold"])
    effect = float(manifest["analysis"]["effect_threshold_for_enrichment"])
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
            results = gp.profile(
                query,
                background,
                build,
                sources=("GO:BP", "GO:MF", "GO:CC"),
                user_threshold=fdr,
            )
        else:
            results = []
        write_results(out_dir / f"gprofiler_{direction}.json", results)
        directional[direction] = {
            "query_genes": len(query),
            "significant_terms": len(results),
            "top_terms": [
                {"term_id": r.term_id, "name": r.name, "source": r.source, "q_value": r.q_value}
                for r in results[:10]
            ],
        }

    report = {
        "scenario_id": manifest["scenario_id"],
        "capability_only": True,
        "assembly": build.assembly,
        "assembly_accession": build.accession,
        "gprofiler_organism": build.gprofiler_organism,
        "tested_gene_sentinel": {
            "gene_id": sentinel,
            "observed_assembly": annotation.assembly,
            "seq_region": annotation.seq_region,
        },
        "background_genes": len(background),
        "background_definition": "all genes passing locked total-count prefilter",
        "thresholds": {"padj": fdr, "abs_log2FoldChange": effect},
        "gprofiler_data_versions": versions,
        "directions": directional,
        "analysis_lock_sha256": lock["analysis_lock_sha256"],
        "status": "PASS",
    }
    (out_dir / "enrichment_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
