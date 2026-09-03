from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re

_GEO = re.compile(r'^(GSM|GSE|GPL)(\d+)$', re.I)

class DataRepresentation(str, Enum):
    RAW_READS = 'raw_reads'
    RAW_COUNTS = 'raw_counts'
    PROCESSED_MATRIX = 'processed_matrix'
    UNAVAILABLE = 'unavailable'


def geo_stub(accession: str) -> str:
    m=_GEO.match(accession.strip())
    if not m:
        raise ValueError('invalid GEO accession')
    prefix,digits=m.group(1).upper(),m.group(2)
    if len(digits) <= 3:
        stub=prefix+'nnn'
    else:
        stub=prefix+digits[:-3]+'nnn'
    return stub


def geo_supplementary_base(accession: str) -> str:
    acc=accession.upper()
    stub=geo_stub(acc)
    kind={'GSM':'samples','GSE':'series','GPL':'platforms'}[acc[:3]]
    return f'https://ftp.ncbi.nlm.nih.gov/geo/{kind}/{stub}/{acc}/suppl/'

@dataclass(frozen=True)
class DataAvailability:
    raw_reads: bool
    raw_counts: bool
    processed_matrix: bool
    raw_reads_size_mb: float | None = None
    raw_counts_size_mb: float | None = None
    processed_size_mb: float | None = None


def choose_representation(a: DataAvailability, need_read_level: bool=False) -> DataRepresentation:
    """Prefer smallest scientifically sufficient representation; size is advisory, not a scientific veto."""
    if need_read_level:
        return DataRepresentation.RAW_READS if a.raw_reads else DataRepresentation.UNAVAILABLE
    if a.raw_counts:
        return DataRepresentation.RAW_COUNTS
    if a.processed_matrix:
        return DataRepresentation.PROCESSED_MATRIX
    if a.raw_reads:
        return DataRepresentation.RAW_READS
    return DataRepresentation.UNAVAILABLE
