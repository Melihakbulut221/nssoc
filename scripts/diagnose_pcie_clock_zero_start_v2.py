#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add native HBT initial-OFF/zero-OP evidence to the unchanged VCO campaign."""

import argparse
import json
import lzma
import os
from pathlib import Path
import re
import shutil

import characterize_pcie_clock_vco as old
import diagnose_pcie_zero_start_v3 as startup

PARENT_SHA = "2d14f5ddf828203f62bfd8af9e895b687d0962a83f0d82d3c69560f30f689807"
METHOD_SHA = "b7fd696ed658650b5be118dc897db690e6c225250fc334706714dd62256df3f9"
CIRCUIT_SHA = "b93e478e3d6a766051b82aabd5796d6fa8f2dbac68f25f1c1757d411369d5426"
STARTUP_SHA = "7a11136d653663fe0094199510294d6c36f178dc9dba38f5630f47e04875953a"
MODELS = {
    "r3_cmc.osdi": "9b41facf3c49d2266e542406547ed00677304f09c1dd281f3bf90414ee053828",
    "psp103.osdi": "e4a50ec48e3fab3aa7af76f1d0816863c8aa06223e0efcded362ddadb49681a8",
    "psp103_nqs.osdi": "523382d47f1f747c991a938b2f93cc6d9bab27ebf44f708c4e995820dc0bee88",
}
PILOT = (
    "nominal",
    "half_step",
    "hbt_typ_mos_tt_125",
    "hbt_bcs_mos_ss_125",
    "hbt_wcs_mos_ss_125",
    "no_bias",
    "no_feedback",
    "same_clock",
    "overload",
)
SPINIT = "* Explicit batch frontend; all models are loaded by the recorded deck.\nset num_threads=1\n"


def identities():
    hbts, _ = old.device_contract(old.CIRCUIT.read_text())
    return ["q.xosc." + name + ".qnpn13g2" for name in hbts]


def transform(original):
    startup.require(
        original.count(".options reltol=1e-4 abstol=1e-12") == 1,
        "Original tolerances required",
    )
    startup.require(
        not re.search(r"(?im)^\s*\.ic\b|\buic\b|\balter\b|^\.nodeset", original),
        "No forced state or prior alteration",
    )
    # The old VCO already has a coordinated zero-source ramp. Preserve every
    # source, model, physical device and observed vector byte-for-byte.
    for name in ("VDD", "VCTRL"):
        matches = re.findall(r"(?m)^" + name + r" \S+ 0 PWL\(0 0 [^\n]+\)$", original)
        startup.require(len(matches) == 1, "Original zero-source ramp missing")
    flags = "".join(
        f"alter @{name}[off] = 1\necho NSSOC_CLOCK_FLAG_BEGIN {name}\nshow {name} : off\necho NSSOC_CLOCK_FLAG_END\n"
        for name in identities()
    )
    startup.require(
        len(re.findall(r"(?m)^tran ", original)) == 1, "Exactly one original transient"
    )
    return original.replace(
        "\ntran ",
        "\n"
        + flags
        + "op\nwrdata initial-op.dat "
        + " ".join(old.vectors())
        + "\ntran ",
        1,
    )


def read_flags(log):
    rows = re.findall(
        r"(?ms)^NSSOC_CLOCK_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_CLOCK_FLAG_END\s*$", log
    )
    startup.require(
        [name for name, _ in rows] == identities(), "Actual HBT flag coverage differs"
    )
    for name, text in rows:
        devices = re.findall(r"(?m)^\s*device\s+(\S+)\s*$", text)
        values = re.findall(r"(?m)^\s*off\s+(\S+)\s*$", text)
        startup.require(
            devices == [name[:21]] and values == ["1"],
            "Native HBT OFF readback differs",
        )
    return dict.fromkeys(identities(), 1)


def inputs(baseline):
    startup.require(
        old.sha(baseline / "result.json") == PARENT_SHA,
        "Immutable original VCO campaign differs",
    )
    startup.require(
        old.sha(Path(old.__file__)) == METHOD_SHA
        and old.sha(old.CIRCUIT) == CIRCUIT_SHA,
        "Original VCO method or circuit changed",
    )
    startup.require(
        old.sha(Path(startup.__file__)) == STARTUP_SHA, "Audited startup helper changed"
    )
    record = json.loads((baseline / "result.json").read_text())
    startup.require(
        not record["quick"]
        and [x["case"] for x in record["cases"]] == old.cases(False),
        "Exact original72-case identity required",
    )
    startup.require(
        record["limits"] == old.LIMITS, "Original engineering thresholds changed"
    )
    pins = dict(record["source_sha256"])
    for path, digest in pins.items():
        startup.require(
            old.sha(Path(path)) == digest, "Original input differs: " + path
        )
    for name, digest in MODELS.items():
        path = baseline / name
        startup.require(
            record["compiled_models"].get(str(path)) == digest
            and old.sha(path) == digest,
            "Compiled foundry model differs",
        )
        pins[str(path)] = digest
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                baseline / "result.json",
                baseline / "spinit",
                Path(__file__).resolve(),
                Path(startup.__file__).resolve(),
            )
        }
    )
    startup.require(
        (baseline / "spinit").read_text() == SPINIT,
        "Original native frontend configuration differs",
    )
    return record, pins


def run(baseline, output, pilot=False):
    baseline, output = Path(baseline).resolve(), Path(output).resolve()
    startup.require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded native output required",
    )
    prior, pins = inputs(baseline)
    runtimes = [Path(p) for p in prior["source_sha256"] if Path(p).name == "ngspice"]
    startup.require(
        len(runtimes) == 1 and old.sha(runtimes[0]) in startup.s.RUNTIMES,
        "Pinned original runtime required",
    )
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    startup.require(len(models) == 1, "Unique foundry models required")
    selected = [x for x in prior["cases"] if not pilot or x["case"]["name"] in PILOT]
    startup.require(
        len(selected) == (9 if pilot else 72), "Exact bounded case set required"
    )
    output.mkdir()
    (output / "spinit").write_text(SPINIT)
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        original_status=prior["status"],
        pilot=pilot,
        limits=old.LIMITS,
        cases=[],
        source_waveforms_unchanged=True,
        circuit_unchanged=True,
        models_unchanged=True,
        tolerances_unchanged=True,
        pcie_compliance=False,
        pll_implemented=False,
        cdr_implemented=False,
        physical_qualification=False,
        scope="Documented native HBT OFF-initialization experiment only. Original physical asymmetry, zero-source ramp, VCO circuit, all engineering limits and exploratory cases remain unchanged. This is not a PLL, recovered clock or all-corner oscillator acceptance.",
    )

    def save():
        (output / "result.tmp").write_text(json.dumps(result, indent=2) + "\n")
        (output / "result.tmp").replace(output / "result.json")

    save()
    previous_env = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    try:
        for original in selected:
            case = original["case"]
            directory = output / case["name"]
            directory.mkdir()
            for name, digest in original["outputs"].items():
                startup.require(
                    old.sha(baseline / case["name"] / name) == digest,
                    "Original case capture changed",
                )
            original_deck = old.deck(
                case, models[0], [baseline / name for name in MODELS]
            )
            startup.require(
                (baseline / case["name"] / "bench.cir").read_text() == original_deck,
                "Original deck reproduction differs",
            )
            startup.require(
                (baseline / case["name"] / old.CIRCUIT.name).read_text()
                == old.circuit(case),
                "Original physical negative differs",
            )
            (directory / old.CIRCUIT.name).write_text(old.circuit(case))
            (directory / "bench.cir").write_text(transform(original_deck))
            row = dict(
                case=case,
                original_numerical=original["numerical"],
                original_screen_pass=original.get("measurement", {}).get("screen_pass"),
            )
            result["cases"].append(row)
            save()
            try:
                row["execution"] = startup.s.rx.execute(
                    [str(runtimes[0]), "-n", "-b", "bench.cir"],
                    directory,
                    directory / "run.log",
                )
                log = (directory / "run.log").read_text()
                row["numerical"] = old.diagnostics(log)
                row["flags_observed"] = read_flags(log)
                op = startup.initial_op(directory / "initial-op.dat", old.vectors())
                row["initial_op"] = op
                row["zero_initial_op"] = max(map(abs, op.values())) <= 1e-10
                row["measurement"] = old.measure(old.read_wave(directory / "wave.dat"))
                row["clean_initialization"] = (
                    row["numerical"]["clean"] and row["zero_initial_op"]
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
                    case["name"] in ("nominal", "hbt_bcs_mos_ss_125")
                    or not row["clean_initialization"]
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
            print(
                case["name"],
                row["clean_initialization"],
                row.get("measurement", {}).get("screen_pass"),
                row.get("measurement", {}).get("frequency_hz"),
                flush=True,
            )
        startup.require(
            all(old.sha(Path(p)) == h for p, h in pins.items()), "Native inputs changed"
        )
        result["source_bytes_unchanged"] = True
        result["clean_cases"] = sum(x["clean_initialization"] for x in result["cases"])
        result["positive_characterization_failures"] = [
            x["case"]["name"]
            for x in result["cases"]
            if not x["case"]["fault"]
            and not x.get("measurement", {}).get("screen_pass")
        ]
        result["negative_controls_rejected"] = all(
            x.get("expected_negative_rejected")
            for x in result["cases"]
            if x["case"]["fault"]
        )
        result["status"] = (
            "CLEAN_NATIVE_STARTUP_WITH_CHARACTERIZATION_LIMITS"
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--pilot", action="store_true")
    a = p.parse_args()
    result = run(a.baseline, a.out, a.pilot)
    return int(result["status"] != "CLEAN_NATIVE_STARTUP_WITH_CHARACTERIZATION_LIMITS")


if __name__ == "__main__":
    raise SystemExit(main())
