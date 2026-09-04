import json

from agri_coscientist.literature import (
    CrossrefAdapter,
    EuropePMCAdapter,
    OpenAlexAdapter,
    PublicationKind,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_europe_pmc_normalizes_original_review_preprint_and_retraction():
    captured = {}
    payload = {
        "hitCount": 3,
        "resultList": {"result": [
            {
                "source": "MED", "id": "1", "pmid": "1",
                "title": "Original plant paper", "abstractText": "<b>Plant</b> abstract",
                "pubYear": "2025", "doi": "https://doi.org/10.1/ABC",
                "journalTitle": "Plant Journal", "citedByCount": 4,
                "pubTypeList": {"pubType": ["Journal Article"]},
            },
            {
                "source": "MED", "id": "2", "title": "A review", "pubYear": "2024",
                "pubTypeList": {"pubType": ["Review", "Journal Article"]},
            },
            {
                "source": "PPR", "id": "3", "title": "A preprint", "pubYear": "2026",
                "isRetracted": True, "pubTypeList": {"pubType": ["Preprint"]},
            },
        ]},
    }

    def opener(request, timeout=60):
        captured["url"] = request.full_url
        return Response(payload)

    result = EuropePMCAdapter(opener=opener).search(
        "plant root signal", from_year=2024, to_year=2026, rows=50
    )
    assert "FIRST_PDATE%3A%5B2024-01-01+TO+2026-12-31%5D" in captured["url"]
    assert result.total_hits == 3
    assert result.exhaustive_for_query is True
    assert result.supports_absence_inference is True
    assert [r.kind for r in result.records] == [
        PublicationKind.ORIGINAL, PublicationKind.REVIEW, PublicationKind.PREPRINT
    ]
    assert result.records[0].doi == "10.1/abc"
    assert result.records[0].abstract == "Plant abstract"
    assert result.records[2].is_retracted is True


def test_crossref_normalizes_metadata_but_is_positive_evidence_only():
    captured = {}
    payload = {
        "message": {
            "total-results": 2,
            "items": [
                {
                    "DOI": "10.2/XYZ",
                    "title": ["Research article"],
                    "abstract": "<jats:p>Abstract text</jats:p>",
                    "published-online": {"date-parts": [[2025, 5, 1]]},
                    "container-title": ["Journal A"],
                    "type": "journal-article",
                    "is-referenced-by-count": 7,
                    "URL": "https://doi.org/10.2/XYZ",
                },
                {
                    "DOI": "10.2/PRE",
                    "title": ["A posted study"],
                    "published": {"date-parts": [[2026]]},
                    "type": "posted-content",
                    "URL": "https://doi.org/10.2/PRE",
                },
            ],
        }
    }

    def opener(request, timeout=60):
        captured["url"] = request.full_url
        return Response(payload)

    result = CrossrefAdapter(opener=opener).search(
        "root signaling", from_year=2024, to_year=2026, rows=25
    )
    assert "from-pub-date%3A2024-01-01%2Cuntil-pub-date%3A2026-12-31" in captured["url"]
    assert result.total_hits == 2
    assert result.exhaustive_for_query is True
    assert result.negative_evidence_eligible is False
    assert result.supports_absence_inference is False
    assert result.records[0].doi == "10.2/xyz"
    assert result.records[0].abstract == "Abstract text"
    assert result.records[0].kind == PublicationKind.ORIGINAL
    assert result.records[1].kind == PublicationKind.PREPRINT


def test_openalex_pages_to_exhaustive_small_result_and_reconstructs_abstract():
    captured = []
    pages = {
        1: {
            "meta": {"count": 2},
            "results": [{
                "id": "https://openalex.org/W1",
                "display_name": "Wheat root signaling",
                "publication_year": 2025,
                "doi": "https://doi.org/10.3/ABC",
                "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345/"},
                "primary_location": {"source": {"display_name": "Plant Journal"}},
                "type": "article",
                "type_crossref": "journal-article",
                "cited_by_count": 9,
                "is_retracted": False,
                "abstract_inverted_index": {"root": [0], "signal": [1]},
            }],
        },
        2: {
            "meta": {"count": 2},
            "results": [{
                "id": "https://openalex.org/W2",
                "display_name": "A plant preprint",
                "publication_year": 2026,
                "type": "preprint",
                "type_crossref": "posted-content",
                "cited_by_count": 0,
                "is_retracted": False,
            }],
        },
    }

    def opener(request, timeout=60):
        captured.append(request.full_url)
        page = 2 if "page=2" in request.full_url else 1
        return Response(pages[page])

    result = OpenAlexAdapter(opener=opener).search(
        'wheat AND root AND "extracellular ATP"',
        from_year=2024, to_year=2026, rows=1, max_records=10,
    )
    assert len(captured) == 2
    assert result.total_hits == 2
    assert result.retrieved == 2
    assert result.supports_absence_inference is True
    assert result.records[0].doi == "10.3/abc"
    assert result.records[0].pmid == "12345"
    assert result.records[0].abstract == "root signal"
    assert result.records[1].kind == PublicationKind.PREPRINT


def test_openalex_truncated_large_result_cannot_support_absence():
    payload = {
        "meta": {"count": 5000},
        "results": [{
            "id": "https://openalex.org/W1",
            "display_name": "Plant result",
            "publication_year": 2025,
            "type": "article",
        }],
    }

    def opener(request, timeout=60):
        return Response(payload)

    result = OpenAlexAdapter(opener=opener).search(
        "plant", from_year=2024, to_year=2026, rows=1, max_records=1
    )
    assert result.total_hits == 5000
    assert result.retrieved == 1
    assert result.exhaustive_for_query is False
    assert result.supports_absence_inference is False
