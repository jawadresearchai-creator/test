from __future__ import annotations
import json, platform, shutil, importlib.util
from .gates import OmicsMetadata, grade_omics_fitness


def local_capabilities():
    pkgs=['numpy','pandas','scipy','statsmodels','sklearn','networkx','pytest','Bio','requests']
    return {
        'python': platform.python_version(),
        'R_available': shutil.which('R') is not None,
        'git_available': shutil.which('git') is not None,
        'packages': {p: importlib.util.find_spec(p) is not None for p in pkgs},
    }

def main():
    live_probe=OmicsMetadata(
        species_match=True,tissue_match=True,treatment_match=False,mechanistic_match=True,
        developmental_match=False,time_match=False,replicates_per_group=2,
        metadata_complete=True,provenance_traceable=True,reusable=True,genotype_match=False)
    print(json.dumps({'local':local_capabilities(),'GSE183508_probe_grade':grade_omics_fitness(live_probe).value},indent=2))

if __name__=='__main__': main()
