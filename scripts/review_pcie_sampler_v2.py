#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Rebuild sampler stimulus/source bindings and remeasure captured native waves."""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import characterize_pcie_sampler_v2 as sampler

ROOT = sampler.ROOT
ASSUMPTIONS = dict(
    external_clock=True,
    recovered_clock=False,
    separate_sampler_supply_v=2.5,
    rx_supply_v=1.8,
    sampler_reference_a=0.0005,
    rx_reference_a=0.00075,
    clock_vcm_v=1.29,
    clock_amplitude_each_v=0.15,
    clock_rise_s=5e-12,
    clock_source_ohm=10,
    substrate_node_v=0,
    physical_tap_rc_simulated=False,
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or digest(path) != expected:
        raise ValueError("Captured byte pin differs: " + str(path))


def source_contract(result):
    if result["assumptions"] != ASSUMPTIONS or type(result["quick"]) is not bool:
        raise ValueError("External clock/bias/physical assumptions differ")
    if (
        result["source_bytes_unchanged"] is not True
        or result["ui_s"] != sampler.UI
        or result["bits"] != sampler.BITS
    ):
        raise ValueError("Sampler acquisition contract differs")
    if (
        result["limits"] != sampler.LIMITS
        or result["pdk_revision"] != sampler.rx.tx.PDK_REV
    ):
        raise ValueError("Device/margin contract differs")
    if any(
        result[k] is not False
        for k in ("pcie_compliance", "physical_qualification", "manufacturing_approval")
    ):
        raise ValueError("Experiment was relabelled as product qualification")
    if [row["case"] for row in result["cases"]] != sampler.cases(result["quick"]):
        raise ValueError("Exact native campaign differs")
    if result["full_pvt_matrix_cases"] != (1 if result["quick"] else 81):
        raise ValueError("Native PVT census differs")
    sources = result["source_sha256"]
    model_paths = [
        Path(p).parent
        for p in sources
        if p.endswith("/libs.tech/ngspice/models/cornerHBT.lib")
    ]
    if len(model_paths) != 1:
        raise ValueError("Expected one foundry model directory")
    models = model_paths[0]
    command = result["compile"]["command"]
    if len(command) != 4 or command[1:3] != [
        str(models.parent.parent / "verilog-a/r3_cmc/r3_cmc.va"),
        "-o",
    ]:
        raise ValueError("OSDI compile command differs")
    compiler, osdi = Path(command[0]), Path(command[3])
    if osdi.name != "r3_cmc.osdi" or result["compile"]["returncode"] != 0:
        raise ValueError("OSDI compilation incomplete")
    ng = Path(result["cases"][0]["execution"]["command"][0])
    expected = {str(ROOT / p): h for p, h in sampler.FIXED.items()}
    expected.update({str(models / p): h for p, h in sampler.rx.tx.MODEL_HASHES.items()})
    expected.update(
        {
            str(models.parent.parent / p): h
            for p, h in sampler.rx.resistor.RES_HASHES.items()
        }
    )
    expected.update(
        {
            str(sampler.NETLIST): digest(sampler.NETLIST),
            str(Path(sampler.__file__)): digest(Path(sampler.__file__)),
            str(compiler): sampler.OPENVAF_PIN,
            str(ng): sources.get(str(ng)),
        }
    )
    if (
        len(expected) != 19
        or sources != expected
        or expected[str(ng)] not in sampler.RUNTIMES
    ):
        raise ValueError("Exact source/model/runtime inventory differs")
    if result["runtime_version"] != sampler.RUNTIMES[expected[str(ng)]]:
        raise ValueError("Native runtime version differs")
    for path, sha in sources.items():
        p = Path(path)
        if not p.is_absolute() or ".." in p.parts:
            raise ValueError("Noncanonical native input path")
        verify(p, sha)
    for row in result["cases"]:
        if row["execution"]["returncode"] != 0 or row["execution"]["command"] != [
            str(ng),
            "-n",
            "-b",
            "bench.cir",
        ]:
            raise ValueError("Native execution differs")
    return models, osdi


def selected_wave(result):
    matrix = [r for r in result["cases"] if r["case"]["name"].startswith("hbt_")]
    return min(
        matrix,
        key=lambda r: (r["measurement"]["min_signed_margin_v"], r["case"]["name"]),
    )["case"]["name"]


def review(directory, mode="full"):
    if mode not in ("full", "retained", "metadata"):
        raise ValueError("Unknown storage mode")
    root = Path(directory).resolve()
    original_result = digest(root / "result.json")
    result = json.loads((root / "result.json").read_text())
    models, osdi = source_contract(result)
    if mode == "full":
        verify(root / "r3_cmc.osdi", result["osdi_sha256"])
    elif (root / "r3_cmc.osdi").exists():
        raise ValueError(
            "Publication subset must not silently include an unlicensed native binary"
        )
    retained_name = selected_wave(result) if mode == "retained" else None
    rows = []
    reparsed = 0
    with tempfile.TemporaryDirectory(
        prefix="nssoc-sampler-review-", dir="/dev/shm"
    ) as scratch:
        for row in result["cases"]:
            case = row["case"]
            folder = root / case["name"]
            expected = {
                "bench.cir",
                "run.log",
                sampler.NETLIST.name,
                sampler.rx.NETLIST.name,
                "wave.dat.gz",
            }
            if set(row["output_sha256"]) != expected:
                raise ValueError("Original native case inventory differs")
            wanted = expected if mode == "full" else expected - {"wave.dat.gz"}
            if retained_name == case["name"]:
                wanted = wanted | {"wave.dat.xz"}
            if folder.is_symlink() or {p.name for p in folder.iterdir()} != wanted:
                raise ValueError("Retained native case inventory differs")
            for name, sha in row["output_sha256"].items():
                if name != "wave.dat.gz" or mode == "full":
                    verify(folder / name, sha)
            if (folder / "bench.cir").read_text() != sampler.deck(case, models, osdi):
                raise ValueError("Exact native stimulus, loading or model path changed")
            if (folder / sampler.NETLIST.name).read_text() != sampler.circuit(case):
                raise ValueError("Captured sampler device topology differs")
            verify(folder / sampler.rx.NETLIST.name, sampler.RX_PIN)
            measurement = row["measurement"]
            raw = mode == "full" or retained_name == case["name"]
            if raw:
                compressed = folder / (
                    "wave.dat.gz" if mode == "full" else "wave.dat.xz"
                )
                if compressed.is_symlink():
                    raise ValueError("Waveform must be a regular file")
                wave = Path(scratch) / "wave.dat"
                sampler.diagnostics.unpack_wave(compressed, wave, row["wave_sha256"])
                measurement = sampler.measure(wave, case)
                wave.unlink()
                reparsed += 1
                if measurement != row["measurement"]:
                    raise ValueError("Native waveform remeasurement differs")
            numerical = sampler.diagnostics.diagnostics(
                (folder / "run.log").read_text()
            )
            if numerical != row["numerical_diagnostics"]:
                raise ValueError("Native numerical warnings were relabelled")
            expected_outcome = (
                None if case["role"] != "required" else case["fault"] is None
            )
            outcome = (
                None
                if expected_outcome is None
                else measurement["screen_pass"] == expected_outcome
            )
            if (
                row["expected_screen_pass"] != expected_outcome
                or row["expected_outcome_observed"] != outcome
            ):
                raise ValueError("Native required/negative outcome changed")
            rows.append(
                dict(
                    case=case,
                    measurement=measurement,
                    numerical_diagnostics=numerical,
                    expected_outcome_observed=outcome,
                    raw_waveform_reparsed=raw,
                    raw_output_sha256=row["output_sha256"],
                    wave_sha256=row["wave_sha256"],
                )
            )
    status, clean = sampler.disposition(rows)
    if sampler.timestep_sensitivity(rows) != result["timestep_sensitivity"]:
        raise ValueError("Native timestep convergence record differs")
    if status != result["status"] or clean is not result["numerical_clean"]:
        raise ValueError("Producer acceptance or numerical residue differs")
    source_contract(result)
    verify(root / "result.json", original_result)
    pvt = [r for r in rows if r["case"]["name"].startswith("hbt_")]
    phases = [r for r in rows if r["case"]["role"] == "aperture"]
    return dict(
        status="PASS_SAMPLER_CAPTURE_REVIEW_ONLY",
        producer_status=status,
        result_sha256=original_result,
        reviewer_sha256=digest(Path(__file__)),
        source_inventory_count=len(result["source_sha256"]),
        source_sha256=result["source_sha256"],
        storage_mode=mode,
        waveform_count=reparsed,
        total_case_count=len(rows),
        retained_case=retained_name,
        pvt_pass=sum(r["measurement"]["screen_pass"] for r in pvt),
        pvt_cases=len(pvt),
        worst_pvt_margin_v=min(r["measurement"]["min_signed_margin_v"] for r in pvt),
        phase_sweep=[
            dict(phase_ui=r["case"]["phase_ui"], measurement=r["measurement"])
            for r in phases
        ],
        cases=rows,
        numerical_clean=clean,
        no_spice_execution=True,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
        limitations=[
            "A screen uses an external ideal voltage clock behind finite source resistance; no clock recovery or PLL.",
            "Full mode reparses every original wave; retained mode one exact worst-PVT wave; metadata none.",
            "Other subset transient metrics remain producer values. All modes verify exact decks/circuits/raw logs.",
            "The PVT grid couples the two supply rails; independent rail extensions remain separately reported.",
            "This finite deterministic phase sweep is not exhaustive setup/hold, metastability or jitter qualification.",
            "OSDI is omitted from a publication subset; its original compile command/hash remain in the producer receipt.",
            "Actual absolute frozen source/model/runtime inputs must exist with matching bytes.",
        ],
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--mode", choices=("full", "retained", "metadata"), default="full")
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Use a fresh output")
    result = review(args.directory, args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["producer_status"], result["waveform_count"])


if __name__ == "__main__":
    main()
