import numpy as np
import pandas as pd
from agri_coscientist.omics_analysis import library_qc, pca_samples, nb_glm_two_group


def fixture_counts():
    rng = np.random.default_rng(42)
    base = rng.negative_binomial(20, 0.5, size=(40, 6))
    base[:5, 3:] += rng.negative_binomial(80, 0.5, size=(5, 3))
    return pd.DataFrame(base, index=[f"g{i}" for i in range(40)], columns=[f"s{i}" for i in range(6)])


def test_qc_and_pca_shapes():
    c = fixture_counts()
    assert library_qc(c).shape == (6, 3)
    assert pca_samples(c).shape == (6, 2)


def test_nb_smoke_finds_spiked_genes():
    c = fixture_counts()
    r = nb_glm_two_group(c, [0,0,0,1,1,1])
    top10 = set(r.head(10).index)
    assert len(top10.intersection({f"g{i}" for i in range(5)})) >= 4
