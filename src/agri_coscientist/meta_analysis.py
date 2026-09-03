from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class MetaResult:
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    tau2: float
    q: float
    k: int


def random_effects(effects, variances) -> MetaResult:
    y = np.asarray(effects, dtype=float)
    v = np.asarray(variances, dtype=float)
    if y.ndim != 1 or len(y) != len(v) or len(y) < 2 or np.any(v <= 0):
        raise ValueError("need >=2 effects with positive variances")
    w = 1.0 / v
    fixed = np.sum(w*y)/np.sum(w)
    q = float(np.sum(w*(y-fixed)**2))
    df = len(y)-1
    c = np.sum(w) - np.sum(w*w)/np.sum(w)
    tau2 = float(max(0.0, (q-df)/c)) if c > 0 else 0.0
    wr = 1.0/(v+tau2)
    est = float(np.sum(wr*y)/np.sum(wr))
    se = float(np.sqrt(1.0/np.sum(wr)))
    return MetaResult(est,se,est-1.96*se,est+1.96*se,tau2,q,len(y))
