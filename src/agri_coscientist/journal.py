from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class JournalPolicy:
    name: str
    accepts_original_research: bool = True
    public_data_reanalysis_allowed: bool = True
    requires_data_provenance: bool = True
    requires_claim_calibration: bool = True
    scope_terms: tuple[str, ...] = ()

@dataclass(frozen=True)
class StudySummary:
    article_type: str
    mode: str
    keywords: tuple[str, ...]
    public_data_provenance_complete: bool


def journal_fit(policy: JournalPolicy, study: StudySummary) -> tuple[bool, list[str]]:
    issues=[]
    if study.article_type == 'original_research' and not policy.accepts_original_research:
        issues.append('article type not accepted')
    if study.mode == 'public_data' and not policy.public_data_reanalysis_allowed:
        issues.append('public-data-only research not allowed by configured policy')
    if policy.requires_data_provenance and study.mode in {'public_data','hybrid'} and not study.public_data_provenance_complete:
        issues.append('public data provenance incomplete')
    if policy.scope_terms:
        keys={k.lower() for k in study.keywords}
        if not any(term.lower() in keys for term in policy.scope_terms):
            issues.append('no configured scope-term match')
    return (not issues, issues)
