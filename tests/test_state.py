import pytest
from agri_coscientist.state import ProjectState, Stage

def test_forward_and_repair_transitions():
    p = ProjectState("test")
    p.transition(Stage.DISCOVERY, "start")
    p.transition(Stage.NOVELTY, "candidates ready")
    p.transition(Stage.FEASIBILITY, "novelty passed")
    p.transition(Stage.DATA_FITNESS, "feasible")
    p.transition(Stage.DESIGN, "data fit")
    p.transition(Stage.DISCOVERY, "design exposed a stronger question")
    assert p.stage is Stage.DISCOVERY

def test_invalid_jump_rejected():
    p = ProjectState("test")
    with pytest.raises(ValueError):
        p.transition(Stage.ANALYSIS, "skip gates")
