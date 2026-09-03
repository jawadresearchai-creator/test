from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.annotation import EnsemblRestAdapter, WHEAT_REFSEQ_V2
from agri_coscientist.enrichment import GProfilerAdapter

OUT = Path("live_wheat_annotation_enrichment.json")
SENTINEL = "TraesCS1D03G0909900"


def main() -> None:
    annotation = EnsemblRestAdapter().lookup(SENTINEL, WHEAT_REFSEQ_V2)
    if annotation.assembly != WHEAT_REFSEQ_V2.assembly:
        raise RuntimeError((annotation.assembly, WHEAT_REFSEQ_V2.assembly))
    if annotation.species.lower() != WHEAT_REFSEQ_V2.species.lower():
        raise RuntimeError((annotation.species, WHEAT_REFSEQ_V2.species))

    gp = GProfilerAdapter()
    versions = gp.data_versions(WHEAT_REFSEQ_V2)
    if not versions:
        raise RuntimeError("g:Profiler returned no data-version metadata")

    enrichment = gp.profile(
        [SENTINEL],
        [SENTINEL],
        WHEAT_REFSEQ_V2,
        sources=("GO:BP", "GO:MF", "GO:CC"),
        user_threshold=1.0,
    )

    report = {
        "sentinel_gene": SENTINEL,
        "expected_build": {
            "species": WHEAT_REFSEQ_V2.species,
            "assembly": WHEAT_REFSEQ_V2.assembly,
            "accession": WHEAT_REFSEQ_V2.accession,
            "provider_release": WHEAT_REFSEQ_V2.provider_release,
            "gprofiler_organism": WHEAT_REFSEQ_V2.gprofiler_organism,
        },
        "ensembl_rest": {
            "gene_id": annotation.gene_id,
            "species": annotation.species,
            "assembly": annotation.assembly,
            "biotype": annotation.biotype,
            "seq_region": annotation.seq_region,
            "start": annotation.start,
            "end": annotation.end,
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
