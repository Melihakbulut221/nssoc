#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Versioned limiter-only VCO geometry experiment; no PLL or layout acceptance."""

import argparse
import json
import lzma
import os
from pathlib import Path
import shutil

import diagnose_pcie_clock_zero_start_v2 as init

old = init.old
require = init.startup.require
INIT_SHA = "0bab52f600f609d4f0e71849a7df492272c1320066815e9017cd7b67d791a0e4"
INIT_RESULT_SHA = "2694306b6e848bcd5d9a816a93ca7bee482b0cf496fb90bda5cbbf985d797972"
NEW_TOP = "nssoc_clock_vco_hbt_v2"
NEW_FILE = "clock_vco_hbt_v2.spice"
LENGTHS = ("4.0", "3.8")
PILOT = (
    "nominal",
    "half_step",
    "hbt_bcs_mos_ss_125",
    "hbt_wcs_mos_ss_-40",
    "hbt_bcs_mos_ff_-40",
    "hbt_wcs_mos_ff_125",
    "res_bcs_cap_bcs_2.415",
    "res_wcs_cap_wcs_2.185",
    "control_1.30",
    "no_bias",
    "no_feedback",
    "same_clock",
    "overload",
)
TUNING = (
    ("nominal", {}),
    ("hot_bcs_ss", dict(hbt="hbt_bcs", mos="mos_ss", temp=125)),
    ("cold_wcs_ss", dict(hbt="hbt_wcs", mos="mos_ss", temp=-40)),
    ("cold_bcs_ff", dict(hbt="hbt_bcs", mos="mos_ff", temp=-40)),
    ("hot_wcs_ff", dict(hbt="hbt_wcs", mos="mos_ff", temp=125)),
    (
        "low_supply_res_wcs_cap_wcs",
        dict(resistor="res_wcs", cap="cap_wcs", supply=2.185),
    ),
    (
        "high_supply_res_bcs_cap_bcs",
        dict(resistor="res_bcs", cap="cap_bcs", supply=2.415),
    ),
)
CONTROLS = (0.60, 0.70, 0.80, 0.85, 0.90, 1.00, 1.10, 1.20, 1.30)


def revised(original, length):
    require(length in LENGTHS, "Only explicit two limiter trials allowed")
    text = original
    for name, node in (("XBRP", "bo_p"), ("XBRN", "bo_n")):
        before = f"{name} avdd {node} sub rppd w=8u l=4.4u b=0 sw_et=1"
        require(text.count(before) == 1, "Exact native limiter load anchor required")
        text = text.replace(before, before.replace("l=4.4u", f"l={length}u"))
    for prefix in (".subckt ", ".ends "):
        before = prefix + "nssoc_clock_vco_hbt"
        require(text.count(before) == 1, "Unique original subcircuit name required")
        text = text.replace(before, prefix + NEW_TOP)
    require(
        old.device_contract(text) == old.device_contract(original),
        "Device connectivity changed",
    )
    return text


def deck(case, models, osdi):
    text = init.transform(old.deck(case, models, osdi))
    for before, after in (
        (f'.include "{old.CIRCUIT.name}"', f'.include "{NEW_FILE}"'),
        (
            "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt\n",
            f"XOSC clkp clkn vctrl avdd 0 0 {NEW_TOP}\n",
        ),
    ):
        require(text.count(before) == 1, "Exact parent deck binding required")
        text = text.replace(before, after)
    return text


def cases(suite):
    if suite == "full":
        return old.cases(False)
    if suite == "pilot":
        rows = [c for c in old.cases(False) if c["name"] in PILOT]
        require(len(rows) == len(PILOT), "Pilot identity changed")
        return rows
    require(suite == "tuning", "Unknown exact suite")
    return [
        dict(old.BASE, **changes, name=f"{label}_control_{v:.2f}", control=v)
        for label, changes in TUNING
        for v in CONTROLS
    ]


def classify_tuning(rows):
    """Measured brackets are necessary evidence, not interpolated lock claims."""
    results = []
    for label, _ in TUNING:
        group = [r for r in rows if r["case"]["name"].startswith(label + "_control_")]
        if not group:
            continue
        require(len(group) == len(CONTROLS), "Incomplete tuning group")
        passed = [
            r
            for r in group
            if r.get("clean_initialization")
            and r.get("measurement", {}).get("screen_pass")
        ]
        brackets = []
        for a, b in zip(group, group[1:]):
            if a not in passed or b not in passed:
                continue
            fa, fb = (r["measurement"]["frequency_hz"] for r in (a, b))
            if min(fa, fb) <= 8e9 <= max(fa, fb):
                brackets.append(
                    dict(
                        control_v=[a["case"]["control"], b["case"]["control"]],
                        frequency_hz=[fa, fb],
                    )
                )
        results.append(
            dict(
                corner=label,
                passing_control_samples_v=[r["case"]["control"] for r in passed],
                measured_8ghz_brackets=brackets,
                measured_8ghz_bracket_found=bool(brackets),
                interpolation_or_lock_claim=False,
            )
        )
    return results


def inputs(baseline, startup_parent):
    require(old.sha(Path(init.__file__)) == INIT_SHA, "Frozen startup method differs")
    prior, pins = init.inputs(baseline)
    require(
        old.sha(startup_parent / "result.json") == INIT_RESULT_SHA,
        "Exact original OFF campaign required",
    )
    for relative, digest in init.startup.DEPENDENCIES.items():
        path = old.ROOT / relative
        require(
            old.sha(path) == digest, "Frozen transitive source differs: " + relative
        )
        pins[str(path)] = digest
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                Path(__file__).resolve(),
                Path(init.__file__).resolve(),
                startup_parent / "result.json",
            )
        }
    )
    return prior, pins


def run(baseline, startup_parent, output, length, suite, candidate=None):
    baseline, startup_parent, output = (
        Path(p).resolve() for p in (baseline, startup_parent, output)
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM output required",
    )
    prior, pins = inputs(baseline, startup_parent)
    original = old.CIRCUIT.read_text()
    canonical = revised(original, length)
    if candidate is not None:
        candidate = Path(candidate).resolve()
        require(
            candidate.read_text() == canonical,
            "Selected versioned circuit must match exact measured geometry",
        )
        pins[str(candidate)] = old.sha(candidate)
    runtimes = [Path(p) for p in pins if Path(p).name == "ngspice"]
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    require(
        len(runtimes) == len(models) == 1, "Unique exact runtime and models required"
    )
    selected = cases(suite)
    output.mkdir()
    (output / "spinit").write_text(init.SPINIT)
    (output / NEW_FILE).write_text(canonical)
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        original_limits=old.LIMITS,
        suite=suite,
        limiter_length_um=length,
        cases=[],
        selected_circuit_sha256=old.sha(output / NEW_FILE),
        physical_qualification=False,
        pll_implemented=False,
        cdr_implemented=False,
        scope="Only two limiter rppd lengths differ. All eighteen HBTs, six oscillator loads, capacitance asymmetry, device equations, source ramps, tolerances and functional limits remain unchanged. Characterization failures remain explicit. No circuit or layout adoption.",
    )

    def save():
        (output / "result.tmp").write_text(json.dumps(result, indent=2) + "\n")
        (output / "result.tmp").replace(output / "result.json")

    save()
    previous_env = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    try:
        for case in selected:
            directory = output / case["name"]
            directory.mkdir()
            (directory / NEW_FILE).write_text(revised(old.circuit(case), length))
            (directory / "bench.cir").write_text(
                deck(case, models[0], [baseline / n for n in init.MODELS])
            )
            row = dict(case=case)
            result["cases"].append(row)
            save()
            try:
                row["execution"] = init.startup.s.rx.execute(
                    [str(runtimes[0]), "-n", "-b", "bench.cir"],
                    directory,
                    directory / "run.log",
                )
                log = (directory / "run.log").read_text()
                row["numerical"] = old.diagnostics(log)
                row["flags_observed"] = init.read_flags(log)
                row["initial_op"] = init.startup.initial_op(
                    directory / "initial-op.dat", old.vectors()
                )
                row["zero_initial_op"] = (
                    max(map(abs, row["initial_op"].values())) <= 1e-10
                )
                data = old.read_wave(directory / "wave.dat")
                require(
                    max(b - a for a, b in zip(data["time"], data["time"][1:]))
                    <= case["step_s"] * 1.00001,
                    "Actual maximum native timestep exceeds recorded bound",
                )
                row["measurement"] = old.measure(data)
                del data
                row["clean_initialization"] = (
                    row["execution"]["returncode"] == 0
                    and row["numerical"]["clean"]
                    and row["zero_initial_op"]
                )
                row["expected_negative_rejected"] = (
                    not row["measurement"]["screen_pass"] if case["fault"] else None
                )
            except (RuntimeError, ValueError) as exc:
                row["error"] = repr(exc)
                row["clean_initialization"] = False
                row["numerical"] = old.diagnostics((directory / "run.log").read_text())
            wave = directory / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                row["wave_retained"] = (
                    case["name"]
                    in ("nominal", "half_step", "hbt_bcs_mos_ss_125", "control_1.30")
                    or not row["clean_initialization"]
                    or (
                        not case["fault"]
                        and not row.get("measurement", {}).get("screen_pass")
                    )
                )
                if row["wave_retained"]:
                    with (
                        wave.open("rb") as src,
                        lzma.open(directory / "wave.dat.xz", "wb", preset=1) as dst,
                    ):
                        shutil.copyfileobj(src, dst)
                wave.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in directory.iterdir()}
            save()
            measure = row.get("measurement", {})
            print(
                case["name"],
                row["clean_initialization"],
                measure.get("screen_pass"),
                measure.get("frequency_hz"),
                min(
                    (d["min_vce_v"] for d in measure.get("devices", {}).values()),
                    default=None,
                ),
                flush=True,
            )
        require(
            all(old.sha(Path(p)) == h for p, h in pins.items()),
            "Native input bytes changed",
        )
        result["source_bytes_unchanged"] = True
        result["clean_cases"] = sum(r["clean_initialization"] for r in result["cases"])
        result["positive_characterization_failures"] = [
            r["case"]["name"]
            for r in result["cases"]
            if not r["case"]["fault"]
            and not r.get("measurement", {}).get("screen_pass")
        ]
        result["negative_controls_rejected"] = all(
            r.get("expected_negative_rejected")
            for r in result["cases"]
            if r["case"]["fault"]
        )
        result["tuning"] = classify_tuning(result["cases"]) if suite == "tuning" else []
        result["status"] = (
            "CLEAN_CHARACTERIZATION_WITH_EXPLICIT_LIMITS"
            if result["clean_cases"] == len(selected)
            and result["negative_controls_rejected"]
            else "NUMERICAL_OR_CONTROL_FAILURE_PRESERVED"
        )
    finally:
        if previous_env is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = previous_env
        save()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "startup-parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--length", choices=LENGTHS, required=True)
    parser.add_argument("--suite", choices=("pilot", "full", "tuning"), required=True)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    result = run(
        args.baseline,
        args.startup_parent,
        args.out,
        args.length,
        args.suite,
        args.candidate,
    )
    return int(result["status"] != "CLEAN_CHARACTERIZATION_WITH_EXPLICIT_LIMITS")


if __name__ == "__main__":
    raise SystemExit(main())
