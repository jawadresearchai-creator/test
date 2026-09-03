from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

from agri_coscientist.scenario import (
    FrozenAsset,
    ScenarioError,
    build_analysis_lock,
    build_dataset_freeze,
    file_sha256,
    read_gzip_header_bytes,
    validate_featurecounts_header,
    validate_scenario_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "scenarios" / "gse235844_rawal87_vs_sonalika_roots.json"
SCRIPT_FILES = (
    "scripts/v04_real_de.R",
    "scripts/v04_enrich.py",
    "scripts/v04_verify_bundle.py",
)
ENV_FILES = (
    "environments/python-stack-lock.json",
    "environments/r-stack-lock.json",
)


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Agriculture-CoScientist-test/0.4 (public scientific data capability scenario)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)
    if destination.stat().st_size < 1000:
        raise ScenarioError(f"downloaded asset is unexpectedly small: {destination}")


def _hash_repo_files(paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise ScenarioError(f"required lock input is missing: {relative}")
        hashes[relative] = file_sha256(path)
    return hashes


def prepare(manifest_path: Path, run_dir: Path) -> tuple[dict, dict]:
    manifest = json.loads(manifest_path.read_text())
    validate_scenario_manifest(manifest)
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    expected_by_asset = {
        group["asset_id"]: int(group["expected_replicates"])
        for group in manifest["contrast"]["groups"]
    }
    frozen_assets: list[FrozenAsset] = []
    asset_paths: dict[str, str] = {}

    # Pre-outcome boundary: only compressed bytes and the first/header line are
    # inspected here. No gene-level count rows or differential outcomes are read.
    for asset in manifest["dataset"]["assets"]:
        asset_id = asset["asset_id"]
        if asset_id not in expected_by_asset:
            raise ScenarioError(f"manifest asset is not assigned to a contrast group: {asset_id}")
        destination = raw_dir / f"{asset_id}.txt.gz"
        _download(asset["url"], destination)
        payload = destination.read_bytes()
        header = read_gzip_header_bytes(payload)
        validate_featurecounts_header(header, expected_by_asset[asset_id], asset_id)
        frozen_assets.append(FrozenAsset(
            asset_id=asset_id,
            url=asset["url"],
            sha256=file_sha256(destination),
            bytes=destination.stat().st_size,
            header=header,
        ))
        asset_paths[asset_id] = str(destination.relative_to(run_dir))

    dataset_freeze = build_dataset_freeze(manifest, frozen_assets)
    dataset_freeze["asset_paths"] = asset_paths
    # Recompute because asset paths are also part of the immutable local run record.
    freeze_without_hash = {k: v for k, v in dataset_freeze.items() if k != "freeze_sha256"}
    from agri_coscientist.scenario import canonical_hash
    dataset_freeze["freeze_sha256"] = canonical_hash(freeze_without_hash)
    (run_dir / "dataset_freeze.json").write_text(
        json.dumps(dataset_freeze, indent=2, sort_keys=True) + "\n"
    )

    script_hashes = _hash_repo_files(SCRIPT_FILES)
    environment_hashes = _hash_repo_files(ENV_FILES)
    analysis_lock = build_analysis_lock(
        manifest,
        dataset_freeze,
        script_hashes,
        environment_hashes,
    )
    analysis_lock["manifest_sha256"] = file_sha256(manifest_path)
    # Include the final lock hash after adding the manifest hash.
    lock_without_hash = {k: v for k, v in analysis_lock.items() if k != "analysis_lock_sha256"}
    analysis_lock["analysis_lock_sha256"] = canonical_hash(lock_without_hash)
    (run_dir / "analysis_lock.json").write_text(
        json.dumps(analysis_lock, indent=2, sort_keys=True) + "\n"
    )
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    marker = {
        "scenario_id": manifest["scenario_id"],
        "dataset_freeze_sha256": dataset_freeze["freeze_sha256"],
        "analysis_lock_sha256": analysis_lock["analysis_lock_sha256"],
        "pre_outcome_boundary": "COMPLETE",
        "count_rows_inspected": False,
    }
    (run_dir / "PRE_OUTCOME_LOCK_COMPLETE.json").write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n"
    )
    return dataset_freeze, analysis_lock


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    freeze, lock = prepare(args.manifest.resolve(), args.run_dir.resolve())
    print(json.dumps({
        "dataset_freeze_sha256": freeze["freeze_sha256"],
        "analysis_lock_sha256": lock["analysis_lock_sha256"],
        "status": "PRE_OUTCOME_LOCK_COMPLETE",
    }, indent=2))


if __name__ == "__main__":
    main()
