#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reparse native RX waveforms and retain numerical warnings separately from margins."""

import argparse
import gzip
import hashlib
import json
import itertools
import lzma
from pathlib import Path
import tempfile

import characterize_pcie_rx_v2 as rx


def retained_wave_names(result):
    """One complete waveform: the measured worst original PVT corner."""
    matrix = [row for row in result["cases"] if row["case"]["name"].startswith("hbt_")]
    if len(matrix) != 81:
        raise ValueError("Retained-wave selection requires all81 PVT cases")
    worst = min(
        matrix,
        key=lambda row: (
            row["measurement"]["min_signed_margin_v"],
            row["case"]["name"],
        ),
    )
    return frozenset((worst["case"]["name"],))


def verify(path, digest):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or rx.tx.sha(path) != digest:
        raise ValueError("Native evidence byte pin differs: " + str(path))


def diagnostics(text):
    low = text.lower()
    # Do not erase initial solver failures merely because later samples are finite.
    lines = [
        line
        for line in text.splitlines()
        if any(
            word in line.lower()
            for word in ("warning", "nan", "stepping", "temperature limiting", "spinit")
        )
    ]
    return dict(
        lines=lines,
        thermal_nan_reported="temperature limiting function received nan" in low,
        singular_matrix_reported="singular matrix" in low,
        gmin_recovery_attempted="starting dynamic gmin stepping" in low,
        gmin_recovery_completed="dynamic gmin stepping completed" in low,
        native_resistor_limit_warning=(
            "specified by jmax" in low or "specified by vmax" in low
        ),
        numerical_clean=not any(
            word in low
            for word in (
                "nan",
                "singular matrix",
                "gmin stepping",
                "specified by jmax",
                "specified by vmax",
            )
        ),
    )


def unpack_wave(path, output, expected):
    h = hashlib.sha256()
    count = 0
    opener = lzma.open if Path(path).suffix == ".xz" else gzip.open
    with opener(path, "rb") as source, Path(output).open("xb") as dest:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            count += len(block)
            if count > 64 * 1024**2:
                raise ValueError("Native waveform exceeds bounded replay budget")
            h.update(block)
            dest.write(block)
    if h.hexdigest() != expected:
        raise ValueError("Uncompressed native waveform pin differs")


def ac_contract(result):
    pairs = (
        [("hbt_typ", "res_typ")]
        if result["quick"]
        else list(
            itertools.product(
                ("hbt_typ", "hbt_bcs", "hbt_wcs"), ("res_typ", "res_bcs", "res_wcs")
            )
        )
    )
    actual = [
        (row["case"]["hbt"], row["case"]["resistor"]) for row in result["ac_cases"]
    ]
    if actual != pairs:
        raise ValueError("Native AC process-pair coverage differs")
    for entry in result["ac_cases"]:
        case = entry["case"]
        if case != dict(
            rx.cases(result["quick"])[0],
            hbt=case["hbt"],
            resistor=case["resistor"],
            temp=27,
            supply=1.8,
        ):
            raise ValueError("Native balanced AC bias contract differs")
        if entry["execution"]["returncode"] != 0:
            raise ValueError("Native AC process failed")


def sensitivity(rows):
    measured = {row["case"]["name"]: row["measurement"] for row in rows}
    base = measured["hbt_typ_res_typ_27_1.8"]
    half = measured["half_timestep"]
    delta = abs(base["min_signed_margin_v"] - half["min_signed_margin_v"])
    power = abs(base["analog_supply_power_w"] / half["analog_supply_power_w"] - 1)
    return dict(
        margin_difference_v=delta,
        power_relative_difference=power,
        screen_pass=delta < 0.001 and power < 0.002,
        scope="Two numerical steps, not extrapolated convergence.",
    )


def transient_files(folder, entry, retained, retained_names=frozenset()):
    original = entry["output_sha256"]
    if set(original) != {"bench.cir", "run.log", "rx_hbt_rsil_v2.spice", "wave.dat.gz"}:
        raise ValueError("Producer transient inventory differs")
    selected = entry["case"]["name"] in retained_names
    expected = (set(original) - {"wave.dat.gz"}) if retained else set(original)
    if retained and selected:
        expected.add("wave.dat.xz")
    if {p.name for p in folder.iterdir()} != expected:
        raise ValueError("Native case output inventory differs")
    for name, digest in original.items():
        if name != "wave.dat.gz" or not retained:
            verify(folder / name, digest)
    if retained and not selected:
        return None
    path = folder / ("wave.dat.xz" if retained else "wave.dat.gz")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Native waveform must be a regular file")
    return path


def review(directory, retained=False, metadata_only=False):
    retained = retained or metadata_only
    root = Path(directory).resolve()
    result = json.loads((root / "result.json").read_text())
    if result["status"] not in (
        "PASS_RX_V2_LIMITED_SCREEN",
        "RX_V2_MEASUREMENT_PASS_NUMERICAL_RESIDUAL",
        "FAIL_RX_V2_MEASUREMENT_SCREEN",
    ):
        raise ValueError("Incomplete native RX producer result")
    if result["source_bytes_unchanged"] is not True or result["limits"] != rx.LIMITS:
        raise ValueError("Producer source or screening contract differs")
    for path, digest in result["source_sha256"].items():
        verify(path, digest)
    verify(root / "r3_cmc.osdi", result["osdi_sha256"])
    if [entry["case"] for entry in result["cases"]] != rx.cases(result["quick"]):
        raise ValueError("Native RX case coverage changed")
    ac_contract(result)
    if retained and result["quick"]:
        raise ValueError("Retained subset requires the full original campaign")
    selected_names = (
        retained_wave_names(result) if retained and not metadata_only else frozenset()
    )
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="nssoc-rx-review-", dir="/dev/shm"
    ) as temporary:
        wave = Path(temporary) / "wave.dat"
        for entry in result["cases"]:
            case = entry["case"]
            folder = root / case["name"]
            if entry["execution"]["returncode"] != 0:
                raise ValueError("Missing successful native process")
            wave_path = transient_files(folder, entry, retained, selected_names)
            measured = entry["measurement"]
            if wave_path is not None:
                unpack_wave(wave_path, wave, entry["wave_sha256"])
                measured = rx.measure(wave, case, rx.sequence(case))
                wave.unlink()
                if measured != entry["measurement"]:
                    raise ValueError("Independent native waveform measurement differs")
            expected = case["fault"] is None
            if entry["expected_screen_pass"] != expected or entry[
                "expected_outcome_observed"
            ] != (measured["screen_pass"] == expected):
                raise ValueError("Unexpected screen result was relabelled")
            rows.append(
                dict(
                    case=case,
                    measurement=measured,
                    raw_waveform_reparsed=wave_path is not None,
                    expected_outcome_observed=entry["expected_outcome_observed"],
                    numerical_diagnostics=diagnostics((folder / "run.log").read_text()),
                    raw_output_sha256=entry["output_sha256"],
                    uncompressed_wave_sha256=entry["wave_sha256"],
                )
            )
    for entry in result["ac_cases"]:
        case = entry["case"]
        folder = root / ("ac_" + case["hbt"] + "_" + case["resistor"])
        if {p.name for p in folder.iterdir() if p.is_file()} != set(
            entry["output_sha256"]
        ):
            raise ValueError("Native AC output inventory differs")
        for name, digest in entry["output_sha256"].items():
            verify(folder / name, digest)
        if rx.measure_ac(folder / "ac.dat") != entry["measurement"]:
            raise ValueError("Native input impedance/gain measurement differs")
    matrix = [r for r in rows if r["case"]["name"].startswith("hbt_")]
    negative = [r for r in rows if r["case"]["fault"]]
    numerical = [
        r["case"]["name"]
        for r in rows
        if not r["numerical_diagnostics"]["numerical_clean"]
    ]
    step = sensitivity(rows)
    if step != result["timestep_sensitivity"]:
        raise ValueError("Native timestep sensitivity differs")
    positive_clean = all(
        row["numerical_diagnostics"]["numerical_clean"]
        for row in rows
        if row["case"]["fault"] is None
    )
    if result["numerical_clean"] is not positive_clean:
        raise ValueError("Producer hid positive-case numerical warnings")
    expected_status = rx.disposition(
        all(row["expected_outcome_observed"] for row in rows) and step["screen_pass"],
        positive_clean,
    )
    if result["status"] != expected_status:
        raise ValueError("Producer screen disposition differs")
    return dict(
        schema=1,
        status="REVIEW_NATIVE_RX_V2_PREAMPLIFIER_ONLY",
        positive_case_numerical_clean=positive_clean,
        producer_status=result["status"],
        producer_result_sha256=rx.tx.sha(root / "result.json"),
        producer_directory=str(root),
        producer_source_sha256=result["source_sha256"],
        reviewer_sha256=rx.tx.sha(Path(__file__).resolve()),
        all_captured_transient_and_ac_measurements_reparsed=not retained,
        retained_transient_wave_names=sorted(selected_names),
        replay_scope=(
            "All97 raw logs/decks and9 AC tables; zero transient waves. Transient metrics are captured producer values."
            if metadata_only
            else "One retained worst-PVT raw wave, all97 raw logs/decks and9 AC tables. Other transient metrics are captured producer values."
            if retained
            else "All 97 original raw waves/logs/decks and all nine AC tables (or the explicitly selected quick campaign)."
        ),
        transient_waveforms_reparsed=sum(row["raw_waveform_reparsed"] for row in rows),
        transient_case_count=len(rows),
        ac_case_count=len(result["ac_cases"]),
        pvt_cases=len(matrix),
        pvt_measurement_screens_passed=sum(
            r["measurement"]["screen_pass"] for r in matrix
        ),
        minimum_pvt_margin_v=min(
            r["measurement"]["min_signed_margin_v"] for r in matrix
        ),
        minimum_pvt_vce_v=min(r["measurement"]["min_vce_v"] for r in matrix),
        maximum_pvt_vce_v=max(r["measurement"]["max_vce_v"] for r in matrix),
        negative_controls=len(negative),
        negative_controls_rejected=sum(
            not r["measurement"]["screen_pass"] for r in negative
        ),
        unexpected_screen_cases=[
            r["case"]["name"] for r in rows if not r["expected_outcome_observed"]
        ],
        cases_requiring_numerical_review=numerical,
        numerical_clean=not numerical,
        cases=rows,
        ac_cases=result["ac_cases"],
        timestep_sensitivity=step,
        assumptions=result["assumptions"],
        limitations=[
            "Initial thermal NaN, gmin recovery and model-limit warnings remain visible even when final samples are finite.",
            "No sensitivity, noise, random mismatch, jitter, BER, channel, ESD, pad, clock/slicer/CDR, PEX or PCIe compliance qualification.",
            "Physical substrate tap networks have not been included in these pre-layout waveforms.",
        ],
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--retained-waves",
        action="store_true",
        help="Replay exactly one retained worst-PVT waveform; never claims a full waveform replay.",
    )
    p.add_argument(
        "--metadata-only",
        action="store_true",
        help="Verify all logs/decks/AC but no transient waves; explicitly limited to recorded transient metrics.",
    )
    args = p.parse_args()
    if args.output.exists():
        p.error("Output must be new")
    if args.retained_waves and args.metadata_only:
        p.error("Choose one retention mode")
    row = review(args.directory, args.retained_waves, args.metadata_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(row, indent=2) + "\n")
    print(
        row["status"],
        row["pvt_measurement_screens_passed"],
        "/",
        row["pvt_cases"],
        "PVT measurement screens; numerical_clean=",
        row["numerical_clean"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
