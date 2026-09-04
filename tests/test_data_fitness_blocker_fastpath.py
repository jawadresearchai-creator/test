import pytest

from agri_coscientist.blockers import Blocker, BlockerClass, BlockerGate, PhaseBlockedError
from agri_coscientist.data_fitness import data_fitness_court


def test_physical_no_existing_data_fast_path_cannot_bypass_open_blocker():
    gate = BlockerGate([Blocker(
        blocker_id="FEASIBILITY_BLOCKER",
        description="feasibility repair remains open",
        blocker_class=BlockerClass.BLOCKING,
        resolution_criterion="feasibility re-evaluates to PASS",
        verification_method="feasibility evidence",
    )])
    with pytest.raises(PhaseBlockedError):
        data_fitness_court(
            [],
            route_requires_existing_data=False,
            blocker_gate=gate,
        )
