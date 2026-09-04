from __future__ import annotations

import json
from pathlib import Path

from agri_coscientist.feasibility import (
    PublicDataRole,
    RouteProposal,
    feasibility_court,
)
from agri_coscientist.gates import OmicsFitness
from agri_coscientist.state import StudyMode


OUT = Path("feasibility_route_capability.json")


def serialize_report(report):
    return {
        "route_id": report.route_id,
        "mode": report.mode.value,
        "overall": report.overall.value,
        "advancement_allowed": report.advancement_allowed,
        "repair_actions": list(report.repair_actions),
        "dimensions": [
            {
                "dimension": d.dimension.value,
                "grade": d.grade.value,
                "reasons": list(d.reasons),
                "repair_actions": list(d.repair_actions),
            }
            for d in report.dimensions
        ],
    }


def main() -> None:
    # Capability-only route set. The purpose is to test routing logic under the
    # standing constraint that new wet-lab RNA-seq/qPCR is unavailable while
    # public omics reanalysis is permitted with strict provenance and later G3-OMICS.
    routes = [
        RouteProposal(
            route_id="physical_with_new_rnaseq",
            mode=StudyMode.PHYSICAL,
            physical_experiment_required=True,
            core_physical_capabilities_available=True,
            requires_new_wetlab_omics=True,
            new_wetlab_omics_available=False,
            scientific_value=5,
            execution_risk=4,
            resource_burden=5,
        ),
        RouteProposal(
            route_id="public_omics_direct_test",
            mode=StudyMode.PUBLIC_DATA,
            physical_experiment_required=False,
            core_physical_capabilities_available=False,
            public_data_required=True,
            public_data_candidates_found=2,
            best_public_omics_fitness=OmicsFitness.B,
            public_data_role=PublicDataRole.DIRECT_TEST,
            scientific_value=4,
            execution_risk=2,
            resource_burden=2,
        ),
        RouteProposal(
            route_id="hybrid_nonmolecular_plus_public_omics",
            mode=StudyMode.HYBRID,
            physical_experiment_required=True,
            core_physical_capabilities_available=True,
            requires_new_wetlab_omics=False,
            new_wetlab_omics_available=False,
            public_data_required=True,
            public_data_candidates_found=2,
            best_public_omics_fitness=OmicsFitness.C,
            public_data_role=PublicDataRole.MECHANISTIC_SUPPORT,
            scientific_value=5,
            execution_risk=2,
            resource_burden=3,
        ),
    ]

    result = feasibility_court(routes)
    if result.selected_route_id != "hybrid_nonmolecular_plus_public_omics":
        raise RuntimeError(f"unexpected selected route: {result.selected_route_id}")
    if "physical_with_new_rnaseq" not in result.failed_route_ids:
        raise RuntimeError("unavailable wet-lab RNA-seq route was not rejected")
    if "public_omics_direct_test" not in result.conditional_route_ids:
        raise RuntimeError("strongly-compatible public data were incorrectly accepted as an unqualified direct test")

    payload = {
        "scenario": "unavailable_new_wetlab_omics_route_rescue_capability",
        "capability_only": True,
        "court_status": result.status.value,
        "selected_route_id": result.selected_route_id,
        "viable_route_ids": list(result.viable_route_ids),
        "conditional_route_ids": list(result.conditional_route_ids),
        "failed_route_ids": list(result.failed_route_ids),
        "required_actions": list(result.required_actions),
        "reports": [serialize_report(r) for r in result.reports],
        "claim_boundary": {
            "allowed": [
                "demonstrate deterministic route selection under declared resource constraints",
                "reject only the infeasible wet-lab-omics route",
                "select a feasible hybrid route for downstream data-fitness/design evaluation",
            ],
            "prohibited": [
                "claim that preliminary OmicsFitness grading substitutes for G3-OMICS",
                "claim that the selected route is scientifically validated before downstream gates",
                "require unavailable new RNA-seq or qPCR when a valid alternative route exists",
            ],
        },
        "status": "PASS",
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
