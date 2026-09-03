from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
import statsmodels.api as sm


def library_qc(counts: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "library_size": counts.sum(axis=0),
        "detected_genes": (counts > 0).sum(axis=0),
        "zero_fraction": (counts == 0).mean(axis=0),
    })


def log_cpm(counts: pd.DataFrame, pseudocount: float = 1.0) -> pd.DataFrame:
    libs = counts.sum(axis=0)
    cpm = counts.divide(libs, axis=1) * 1_000_000
    return np.log2(cpm + pseudocount)


def pca_samples(counts: pd.DataFrame, n_components: int = 2) -> pd.DataFrame:
    x = log_cpm(counts).T
    pcs = PCA(n_components=n_components).fit_transform(x)
    return pd.DataFrame(pcs, index=counts.columns, columns=[f"PC{i+1}" for i in range(n_components)])


def nb_glm_two_group(counts: pd.DataFrame, group: list[int]) -> pd.DataFrame:
    """Software smoke-test NB GLM, not a replacement for DESeq2/edgeR production workflows."""
    if len(group) != counts.shape[1]:
        raise ValueError("group length must equal number of samples")
    X = sm.add_constant(np.asarray(group, dtype=float))
    rows = []
    for gene, y in counts.iterrows():
        model = sm.GLM(y.to_numpy(dtype=float), X, family=sm.families.NegativeBinomial(alpha=1.0))
        fit = model.fit(maxiter=100, disp=0)
        rows.append((gene, float(fit.params[1]), float(fit.pvalues[1])))
    out = pd.DataFrame(rows, columns=["gene", "coef", "pvalue"]).set_index("gene")
    return out.sort_values("pvalue")
