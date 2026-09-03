from agri_coscientist.provenance import freeze_manifest, verify_manifest, analysis_lock

def test_manifest_detects_tampering(tmp_path):
    p = tmp_path / "counts.tsv"
    p.write_text("gene\tA\nX\t1\n")
    m = freeze_manifest([p])
    assert verify_manifest(m)
    p.write_text("gene\tA\nX\t2\n")
    assert not verify_manifest(m)

def test_analysis_lock_is_deterministic(tmp_path):
    p = tmp_path / "analysis.py"
    p.write_text("print('ok')\n")
    manifest = freeze_manifest([p])
    spec = {"model":"negative_binomial", "fdr":0.05, "contrast":"treated-control"}
    a = analysis_lock(spec, manifest)
    b = analysis_lock(spec, manifest)
    assert a["lock_sha256"] == b["lock_sha256"]
