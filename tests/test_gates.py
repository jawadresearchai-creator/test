from agri_coscientist.gates import OmicsMetadata, OmicsFitness, grade_omics_fitness

def base(**overrides):
    d = dict(species_match=True,tissue_match=True,treatment_match=True,mechanistic_match=True,
             developmental_match=True,time_match=True,replicates_per_group=3,
             metadata_complete=True,provenance_traceable=True,reusable=True,genotype_match=True)
    d.update(overrides)
    return OmicsMetadata(**d)

def test_grade_A_for_full_match():
    assert grade_omics_fitness(base()) is OmicsFitness.A

def test_mechanistic_not_direct_is_C():
    assert grade_omics_fitness(base(treatment_match=False,time_match=False,genotype_match=False)) is OmicsFitness.C

def test_two_replicate_mechanistic_dataset_can_be_contextual_C_not_false_reject():
    m = base(treatment_match=False, developmental_match=False, time_match=False,
             genotype_match=False, replicates_per_group=2, mechanistic_match=True)
    assert grade_omics_fitness(m) is OmicsFitness.C

def test_reject_untraceable_dataset():
    assert grade_omics_fitness(base(provenance_traceable=False)) is OmicsFitness.E

def test_reject_single_replicate_for_inferential_reuse():
    assert grade_omics_fitness(base(replicates_per_group=1)) is OmicsFitness.E
