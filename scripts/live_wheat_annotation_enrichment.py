from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.annotation import EnsemblRestAdapter, WHEAT_REFSEQ_V2
from agri_coscientist.enrichment import GProfilerAdapter

OUT = Path("live_wheat_annotation_enrichment.json")
LOCK_PATH = Path("environments/wheat-annotation-lock.json")


def main() -> None:
    lock = json.loads(LOCK_PATH.read_text())
    sentinel = lock["sentinel_gene"]

    annotation = EnsemblRestAdapter().lookup(sentinel, WHEAT_REFSEQ_V2)
    expected_ensembl = lock["ensembl_rest"]
    observed_ensembl = {
        "assembly": annotation.assembly,
        "seq_region": annotation.seq_region,
        "start": annotation.start,
        "end": annotation.end,
        "biotype": annotation.biotype,
    }
    if observed_ensembl != expected_ensembl:
        raise RuntimeError(f"Ensembl sentinel drift: {observed_ensembl!r} != {expected_ensembl!r}")

    gp = GProfilerAdapter()
    versions = gp.data_versions(WHEAT_REFSEQ_V2)
    expected_gp = lock["gprofiler"]
    for key in ("organism", "display_name", "taxonomy_id", "genebuild", "biomart", "biomart_version", "gprofiler_version"):
        if str(versions.get(key)) != str(expected_gp[key]):
            raise RuntimeError(f"g:Profiler metadata drift for {key}: {versions.get(key)!r} != {expected_gp[key]!r}")
    go_bp_version = str((versions.get("sources") or {}).get("GO:BP", {}).get("version", ""))
    if expected_gp["go_class_release"] not in go_bp_version:
        raise RuntimeError(f"g:Profiler GO release drift: {go_bp_version!r}")

    enrichment = gp.profile(
        [sentinel],
        [sentinel],
        WHEAT_REFSEQ_V2,
        sources=("GO:BP", "GO:MF", "GO:CC"),
        user_threshold=1.0,
    )
    if not enrichment:
        raise RuntimeError("g:Profiler accepted the request but returned no GO annotations for the sentinel")

    report = {
        "sentinel_gene": sentinel,
        "expected_build": lock["genome"],
        "ensembl_rest": {
            "gene_id": annotation.gene_id,
            "species": annotation.species,
            **observed_ensembl,
        },
        "gprofiler_data_versions": versions,
        "gprofiler_result_count": len(enrichment),
        "gprofiler_first_terms": [
            {
                "term_id": row.term_id,
                "name": row.name,
                "source": row.source,
                "q_value": row.q_value,
            }
            for row in enrichment[:10]
        ],
        "status": "PASS",
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
