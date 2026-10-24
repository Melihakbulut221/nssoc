#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit frozen RX v2 capture sources and decks; never run SPICE or qualify a PHY."""

import argparse
import hashlib
import json
from pathlib import Path

import characterize_pcie_rx_v2 as rx
import review_pcie_rx_v2 as reviewer

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PINS = {
    "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice": "d02827087e0cb43f447fc46fda05dbd23dcee13ad68755fd31ba738404332a4e",
    "scripts/characterize_pcie_rx_v2.py": "087ac0d41235f11fb64c532da0d4d9f13f85deea596652951d83d365e51ef1ef",
    "scripts/characterize_pcie_rx.py": "74d192ab7c95b8113cafbc0202f219c52f2ae9a1e07b410ba72b7512cceb4a99",
    "scripts/review_pcie_rx.py": "93485e70a1a2fd72e5cc76542f48b5fb27bf580edfbb463217348fac9fce8417",
    "scripts/characterize_pcie_tx.py": "fdd6d927350d459ee68b7491047d0ceb976868bf93d6ff144a4339719d472f0c",
    "scripts/characterize_pcie_tx_rsil.py": "0028468eda30911b157bc650c78745c43a36f52437da61a1cfcc40972301e92e",
}
REVIEWER_SHA = "0d3548490df7f908722106624002713528e2d578b2b994660ec836d9bb4237cf"
NGSPICE_PINS = {
    "820658317b0b54035208da41936fd6871ce924036e5ea4113a4168b821b7fc45": "42",
    "eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8": "47",
}
OPENVAF_SHA = "6918195bc6cca54016095923bea190f7a1d96dd8b062104c602e8c28578cb5e3"
ASSUMPTIONS = dict(
    vcm_v=1.36,
    ideal_reference_a=0.00075,
    source_impedance_each_ohm=50,
    output_load_each_f=150e-15,
    substrate_model_node_v=0,
    simulated_physical_substrate_tap_rc=False,
    clock_or_slicer_present=False,
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or digest(path) != expected:
        raise ValueError("Frozen byte pin differs: " + str(path))


def absolute_path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError("Noncanonical captured path")
    return path


def source_contract(result):
    """Require the complete inventory, not merely the entries a receipt supplies."""
    if (
        result["quick"] is not False
        or result["complete_pvt_cross_product"] is not True
        or result["source_bytes_unchanged"] is not True
        or result["limits"] != rx.LIMITS
        or result["ui_s"] != rx.UI
        or result["bits"] != rx.BITS
        or result["pdk_revision"] != rx.tx.PDK_REV
        or result["assumptions"] != ASSUMPTIONS
        or any(
            result[k] is not False
            for k in (
                "pcie_compliance",
                "physical_qualification",
                "manufacturing_approval",
            )
        )
    ):
        raise ValueError("Frozen full-campaign contract differs")
    if [row["case"] for row in result["cases"]] != rx.cases(False):
        raise ValueError("Exact 97-case coverage differs")
    reviewer.ac_contract(result)
    sources = result["source_sha256"]
    models = [
        absolute_path(p).parent
        for p in sources
        if p.endswith("/libs.tech/ngspice/models/cornerHBT.lib")
    ]
    if len(models) != 1:
        raise ValueError("Expected one foundry model directory")
    models = models[0]
    compiler = result["compile"]
    command = compiler["command"]
    if len(command) != 4:
        raise ValueError("OSDI compiler command differs")
    openvaf = absolute_path(command[0])
    osdi = absolute_path(command[3])
    if (
        compiler["returncode"] != 0
        or osdi.name != "r3_cmc.osdi"
        or command[1:3]
        != [str(models.parent.parent / "verilog-a/r3_cmc/r3_cmc.va"), "-o"]
    ):
        raise ValueError("OSDI compiler command differs")
    ngspice = absolute_path(result["cases"][0]["execution"]["command"][0])
    runtime_sha = sources.get(str(ngspice))
    if runtime_sha not in NGSPICE_PINS:
        raise ValueError("Unqualified captured ngspice binary")
    expected = {
        **{str(ROOT / p): h for p, h in SOURCE_PINS.items()},
        **{str(models / p): h for p, h in rx.tx.MODEL_HASHES.items()},
        **{str(models.parent.parent / p): h for p, h in rx.resistor.RES_HASHES.items()},
        str(openvaf): OPENVAF_SHA,
        str(ngspice): runtime_sha,
    }
    if len(expected) != 14 or sources != expected:
        raise ValueError("Exact source/model/runtime inventory differs")
    for path in sources:
        absolute_path(path)
    for row in [*result["cases"], *result["ac_cases"]]:
        execution = row["execution"]
        if execution["returncode"] != 0 or execution["command"] != [
            str(ngspice),
            "-n",
            "-b",
            "bench.cir",
        ]:
            raise ValueError("Native case runtime command differs")
    return dict(models=models, osdi=osdi, runtime_version=NGSPICE_PINS[runtime_sha])


def case_bridge(folder, row, context, ac=False):
    """Rebuild the actual stimulus, load, model paths and copied circuit bytes."""
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Case folder must be a real directory")
    expected, _ = rx.deck(row["case"], context["models"], context["osdi"], ac=ac)
    bench = folder / "bench.cir"
    if bench.is_symlink() or bench.read_text() != expected:
        raise ValueError("Regenerated bench differs: " + str(folder))
    circuit = folder / rx.NETLIST.name
    verify(circuit, SOURCE_PINS["hw/soc/analog/pcie/rx_hbt_rsil_v2.spice"])
    verify(bench, row["output_sha256"]["bench.cir"])
    verify(circuit, row["output_sha256"][rx.NETLIST.name])


def audit(directory, mode="full"):
    if mode not in ("full", "retained", "metadata"):
        raise ValueError("Unknown replay storage mode")
    root = Path(directory).resolve()
    for path, expected in SOURCE_PINS.items():
        verify(ROOT / path, expected)
    verify(Path(reviewer.__file__), REVIEWER_SHA)
    result_path = root / "result.json"
    if result_path.is_symlink():
        raise ValueError("Producer receipt must be a regular file")
    original_digest = digest(result_path)
    result = json.loads(result_path.read_text())
    context = source_contract(result)
    for path, expected in result["source_sha256"].items():
        verify(path, expected)
    for ac, rows in ((False, result["cases"]), (True, result["ac_cases"])):
        for row in rows:
            case = row["case"]
            name = "ac_" + case["hbt"] + "_" + case["resistor"] if ac else case["name"]
            case_bridge(root / name, row, context, ac)
    replay = reviewer.review(
        root, retained=mode == "retained", metadata_only=mode == "metadata"
    )
    # Recheck complete source closure and receipt after potentially long full-wave replay.
    verify(result_path, original_digest)
    for path, expected in result["source_sha256"].items():
        verify(path, expected)
    verify(Path(reviewer.__file__), REVIEWER_SHA)
    return dict(
        status="PASS_RX_V2_CAPTURE_INTEGRITY_AUDIT_ONLY",
        producer_directory=str(root),
        producer_result_sha256=original_digest,
        auditor_sha256=digest(Path(__file__)),
        reviewer_sha256=REVIEWER_SHA,
        complete_source_inventory_verified=14,
        regenerated_decks=106,
        copied_circuit_bridges_verified=106,
        runtime_version=context["runtime_version"],
        storage_mode=mode,
        source_bytes_rechecked_after_replay=True,
        producer_status=replay["producer_status"],
        positive_case_numerical_clean=replay["positive_case_numerical_clean"],
        replay=replay,
        no_spice_execution=True,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
        limitations=[
            "PASS describes capture integrity, not a clean numerical simulation or PHY acceptance.",
            "Full mode reparses 97 captured transient waves; retained mode only one worst-PVT wave; metadata mode none.",
            "The frozen reviewer still requires captured absolute source/model/runtime paths to exist with exact bytes.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--mode", choices=("full", "retained", "metadata"), default="full"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Audit output must be new")
    result = audit(args.directory, args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        result["status"],
        result["producer_status"],
        result["replay"]["transient_waveforms_reparsed"],
    )


if __name__ == "__main__":
    main()
