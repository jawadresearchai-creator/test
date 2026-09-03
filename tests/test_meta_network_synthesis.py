import numpy as np
import pandas as pd
from agri_coscientist.meta_analysis import random_effects
from agri_coscientist.network import coexpression_graph, hub_degree
from agri_coscientist.synthesis import ClaimEvidence, Direction, synthesize
from agri_coscientist.claims import EvidenceStrength
from agri_coscientist.audit import audit_omics_claim
from agri_coscientist.gates import OmicsFitness


def test_random_effects_meta_analysis_runs():
    r = random_effects([0.2,0.4,0.3],[0.04,0.05,0.03])
    assert 0.2 < r.estimate < 0.4
    assert r.k == 3 and r.se > 0


def test_coexpression_network_finds_correlated_pair():
    x=np.arange(8,dtype=float)
    df=pd.DataFrame([x, x*2+1, np.array([1,0,2,1,0,2,1,0])], index=['g1','g2','noise'])
    g=coexpression_graph(df,0.95)
    assert g.has_edge('g1','g2')
    assert hub_degree(g)[0][1] >= 1


def test_high_quality_contradiction_forces_mixed_verdict():
    items=[
      ClaimEvidence('our_exp',Direction.SUPPORT,EvidenceStrength.DIRECT_CAUSAL),
      ClaimEvidence('public_A',Direction.SUPPORT,EvidenceStrength.SUPPORTING),
      ClaimEvidence('public_B',Direction.CONTRADICT,EvidenceStrength.SUPPORTING),
    ]
    assert synthesize(items)['verdict']=='mixed'


def test_audit_blocks_contextual_omics_as_causal_validation():
    issues=audit_omics_claim(OmicsFitness.C,EvidenceStrength.DIRECT_CAUSAL)
    assert issues
