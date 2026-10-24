#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay source, raw diagnostics and retained native startup/KCL waveforms."""

import argparse
import json
import lzma
from pathlib import Path
import tempfile

import diagnose_pcie_zero_start_v3 as d
import check_pcie_startup_kcl_v3 as k


def pins(items):
    for name, digest in items.items():
        p = Path(name)
        d.require(
            p.is_file() and not p.is_symlink() and d.s.rx.tx.sha(p) == digest,
            "Input pin differs: " + name,
        )


def outputs(directory, inventory):
    d.require(
        {p.name for p in directory.iterdir()} == set(inventory),
        "Captured native case inventory differs",
    )
    pins({str(directory / n): h for n, h in inventory.items()})


def unpack(source, dest, expected):
    with lzma.open(source, "rb") as src, dest.open("xb") as dst:
        count = 0
        for block in iter(lambda: src.read(1024 * 1024), b""):
            count += len(block)
            d.require(
                count <= 96 * 1024**2, "Waveform exceeds native bounded replay scope"
            )
            dst.write(block)
    d.require(d.s.rx.tx.sha(dest) == expected, "Original native waveform bytes differ")


def review(root):
    root = Path(root).resolve()
    record = json.loads((root / "result.json").read_text())
    pins(record["source_sha256"])
    model_sources = [
        Path(p) for p in record["source_sha256"] if Path(p).name == "cornerHBT.lib"
    ]
    osdi_sources = [
        Path(p) for p in record["source_sha256"] if Path(p).name == "r3_cmc.osdi"
    ]
    d.require(
        len(model_sources) == len(osdi_sources) == 1,
        "Unique pinned model and OSDI source required",
    )
    models, osdi = model_sources[0].parent, osdi_sources[0]
    checked, failures = [], []
    with tempfile.TemporaryDirectory(
        prefix="nssoc-zero-review-", dir="/dev/shm"
    ) as scratch:
        wave = Path(scratch) / "wave.dat"
        if "leaf_map" in record:
            inventory = dict(record["output_sha256"])
            outputs(
                root, {**inventory, "result.json": d.s.rx.tx.sha(root / "result.json")}
            )
            texts, leaves = k.instrumentation()
            d.require(
                leaves == record["leaf_map"],
                "Original terminal probe identities differ",
            )
            for name, text in texts.items():
                d.require(
                    (root / name).read_text() == text,
                    "Instrumented source contraction differs",
                )
            expected_deck, expected_vectors = k.constant_deck(
                record["case"], models, osdi, leaves
            )
            d.require(
                (root / "bench.cir").read_text() == expected_deck,
                "Native KCL recipe differs",
            )
            observed = [
                line.removeprefix("save ").split()
                for line in (root / "bench.cir").read_text().splitlines()
                if line.startswith("save ")
            ]
            d.require(
                observed == [expected_vectors], "Exact native observation set required"
            )
            initial = d.initial_op(root / "initial-op.dat", expected_vectors)
            d.require(
                initial == record["initial_op"]
                and max(map(abs, initial.values())) <= 1e-10,
                "Actual KCL zero-source operating point differs",
            )
            unpack(root / "wave.dat.xz", wave, record["wave_sha256"])
            table = d.s.rx.rx.read_table(wave, ["time", *observed[0]])
            actual = k.analyze(table, leaves, record["case"])
            d.require(actual == record["analysis"], "Actual KCL replay differs")
            d.require(record["execution"]["returncode"] == 0, "Native process failed")
            diag = d.diagnostics((root / "run.log").read_text())
            d.require(
                diag == record["diagnostics"] and diag["numerical_clean"],
                "Actual native numerical diagnostics differ",
            )
            d.require(
                d.flags_observed((root / "run.log").read_text(), "sampler", "zero_off")
                == record["flags_observed"],
                "Native flags differ",
            )
            d.require(
                actual["pass_kcl"]
                and actual["pass_active"]
                and actual["pass_settling"],
                "KCL/active/settling failed",
            )
            d.require(
                record["status"] == "PASS_NATIVE_SETTLED_KCL", "KCL verdict differs"
            )
            checked = ["actual_settled_KCL_waveform"]
        else:
            d.require(
                [r["case"] for r in record["cases"]]
                == d.cases(record["kind"], record["matrix"]),
                "Exact original PVT/negative coverage differs",
            )
            for row in record["cases"]:
                directory = root / row["case"]["name"]
                outputs(directory, row["output_sha256"])
                original = (
                    d.s.deck(row["case"], models, osdi)
                    if record["kind"] == "sampler"
                    else d.s.rx.deck(row["case"], models, osdi)[0]
                )
                d.require(
                    (directory / "bench.cir").read_text()
                    == d.transform(original, record["kind"], record["strategy"]),
                    "Native startup recipe differs",
                )
                d.require(
                    (directory / d.s.rx.NETLIST.name).read_bytes()
                    == d.s.rx.NETLIST.read_bytes(),
                    "RX circuit differs",
                )
                expected_circuit = (
                    d.s.circuit(row["case"])
                    if record["kind"] == "sampler"
                    else d.s.NETLIST.read_text()
                )
                d.require(
                    (directory / d.s.NETLIST.name).read_text() == expected_circuit,
                    "Sampler circuit differs",
                )
                log = (directory / "run.log").read_text()
                d.require(
                    d.diagnostics(log) == row["diagnostics"],
                    "Actual numerical diagnostics differ",
                )
                if "error" in row:
                    d.require(
                        row["protocol_pass"] is False
                        and not row["diagnostics"]["numerical_clean"],
                        "A failed native command cannot be relabelled clean",
                    )
                    d.flags_observed(log, record["kind"], record["strategy"])
                    failures.append(row["case"]["name"])
                    continue
                d.require(
                    d.flags_observed(log, record["kind"], record["strategy"])
                    == row["flags_observed"],
                    "Actual flag census differs",
                )
                op = d.initial_op(
                    directory / "initial-op.dat", d.vectors(record["kind"])
                )
                d.require(
                    op == row["initial_op"]
                    and (max(map(abs, op.values())) <= 1e-10) == row["zero_initial_op"],
                    "Initial OP differs",
                )
                if row["wave_retained"]:
                    unpack(directory / "wave.dat.xz", wave, row["wave_sha256"])
                    actual = (
                        d.s.measure(wave, row["case"])
                        if record["kind"] == "sampler"
                        else d.s.rx.measure(
                            wave, row["case"], d.s.rx.sequence(row["case"])
                        )
                    )
                    d.require(
                        actual == row["measurement"],
                        "Retained native waveform measurement differs",
                    )
                    wave.unlink()
                    checked.append(row["case"]["name"])
                expected = row["case"]["fault"] is None
                passed = row["measurement"]["screen_pass"] == expected
                d.require(
                    row["expected_functional_pass"] == expected
                    and row["expected_function_observed"] == passed,
                    "Functional negative control differs",
                )
                d.require(row["execution"]["returncode"] == 0, "Native process failed")
                d.require(
                    row["protocol_pass"]
                    == (
                        passed
                        and row["diagnostics"]["numerical_clean"]
                        and row["zero_initial_op"]
                    ),
                    "Native protocol disposition differs",
                )
            expected_status = (
                "PASS_BOUNDED_ZERO_START_PROTOCOL"
                if all(x["protocol_pass"] for x in record["cases"])
                else "FAIL_PRESERVED"
            )
            d.require(
                record["status"] == expected_status, "Aggregate disposition differs"
            )
    return dict(
        status="PASS_RETAINED_RAW_REPLAY",
        original_status=record["status"],
        result_sha256=d.s.rx.tx.sha(root / "result.json"),
        independently_replayed_waves=checked,
        raw_native_failures_preserved=failures,
        unretained_measurements_not_independently_replayed=True,
        producer_inputs_rehashed=len(record["source_sha256"]),
        scope="All retained raw logs/OP/flags and complete case identity checked; only explicitly listed retained waves were remeasured. No native simulation repeated.",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    a = p.parse_args()
    print(json.dumps(review(a.directory), indent=2))


if __name__ == "__main__":
    main()
