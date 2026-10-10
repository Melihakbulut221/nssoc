#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate VCO-v2 driven prescaler screen with verified native zero-OFF startup.

The divider, latch, device equations, thresholds and source ramps remain frozen.
Only the two VCO limiter loads change, as bound by the exact selected VCO source.
This finite schematic experiment does not implement a PLL or qualify a layout.
"""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess

import characterize_pcie_div2 as old

VCO = old.ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v2.spice"
PINS = {
    "scripts/characterize_pcie_div2.py": "8dd9818c28d3db09e550b41f70340ea196387bc40e7c691a2ec9f32ef50b28ce",
    "hw/soc/analog/pcie/clock_div2_hbt.spice": "1b18a732c7736ad8c9805131c77fe1d5e467364ae8d6a2b7eb07061131cea4d7",
    "hw/soc/analog/pcie/clock_vco_hbt_v2.spice": "c55baf3e280bc735c0825e96861150b09c63b4de29ed4241f965f835f3cdb749",
}
PARENT = "eb479e0ef336532bd56cfc7e5677997394b920b7299573c41711e0d94088509d"
STARTUP_REFERENCE = "https://ngspice.sourceforge.io/docs/ngspice-manual.pdf"
PILOT = ("nominal", "cold_fast", "cold_slow", "hot_slow")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_vco():
    for name, expected in PINS.items():
        require(old.sha(old.ROOT / name) == expected, "Frozen source changed: " + name)
    for path, expected in old.FROZEN.items():
        require(old.sha(path) == expected, "Frozen parent changed")
    expected = old.VCO.read_text().replace(
        "nssoc_clock_vco_hbt", "nssoc_clock_vco_hbt_v2"
    )
    for cell, node in (("XBRP", "bo_p"), ("XBRN", "bo_n")):
        before = f"{cell} avdd {node} sub rppd w=8u l=4.4u b=0 sw_et=1"
        require(expected.count(before) == 1, "Unique limiter source required")
        expected = expected.replace(before, before.replace("l=4.4u", "l=4.0u"))
    require(VCO.read_text() == expected, "Only exact two limiter loads may differ")
    # Thus every actual HBT path/terminal and thermal-vector identity used by the
    # frozen measurement code remains exact; none is inferred from a name alone.


def identities(case):
    hbts, _ = old.device_contract(case)
    return ["q." + name + ".qnpn13g2" for name in hbts]


def deck(case, models, osdi):
    verify_vco()
    text = old.deck(case, models, osdi)
    require(
        not re.search(r"(?im)^\s*\.ic\b|\buic\b|\balter\b|^\s*\.nodeset", text),
        "No prior forced state or parameter alteration",
    )
    before = f'.include "{old.VCO.name}"'
    require(text.count(before) == 1, "Unique VCO include required")
    text = text.replace(before, f'.include "{VCO.name}"')
    before = "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt"
    require(text.count(before) == 1, "Unique native clock instance required")
    text = text.replace(before, before + "_v2")
    for source in ("VDD", "VDDIV", "VCTRL"):
        require(
            len(re.findall(r"(?m)^" + source + r" \S+ 0 PWL\(0 0 [^\n]+\)$", text))
            == 1,
            "Every external source must begin at zero",
        )
    flags = "".join(
        f"alter @{name}[off] = 1\n"
        f"echo NSSOC_DIV2_FLAG_BEGIN {name}\n"
        f"show {name} : off\necho NSSOC_DIV2_FLAG_END\n"
        for name in identities(case)
    )
    require(len(re.findall(r"(?m)^tran ", text)) == 1, "Unique unchanged transient")
    return text.replace(
        "\ntran ",
        "\n"
        + flags
        + "op\nwrdata initial-op.dat "
        + " ".join(old.vectors(case))
        + "\ntran ",
        1,
    )


def read_flags(log, case):
    rows = re.findall(
        r"(?ms)^NSSOC_DIV2_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_DIV2_FLAG_END\s*$", log
    )
    expected = identities(case)
    require([name for name, _ in rows] == expected, "Exact 33-HBT flag census/order")
    for name, body in rows:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+(\S+)\s*$", body) == ["1"],
            "Actual native OFF flag or device identity differs",
        )
    return dict.fromkeys(expected, 1)


def initial_op(path, case):
    lines = [line for line in Path(path).read_text().splitlines() if line.strip()]
    names = old.vectors(case)
    require(len(lines) == 2, "Exactly one native OP row required")
    require(lines[0].split()[1:] == names, "Exact native OP vectors required")
    values = list(map(float, lines[1].split()))
    require(
        len(values) == len(names) + 1 and all(math.isfinite(v) for v in values),
        "Nonfinite or incomplete OP",
    )
    require(
        max(map(abs, values[1:])) <= 1e-10, "Initial electrical/thermal OP is not zero"
    )
    return dict(zip(names, values[1:]))


def accepted(row):
    return (
        row.get("zero_initial_op") is True
        and row.get("flags_verified") is True
        and old.expected_result(row)
    )


def run(parent, output, pilot=False):
    parent, output = Path(parent).resolve(), Path(output).resolve()
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output",
    )
    verify_vco()
    require(
        old.sha(parent / "result.json") == PARENT,
        "Exact original limited capture required",
    )
    prior = json.loads((parent / "result.json").read_text())
    require(
        [x["case"] for x in prior["cases"]] == old.cases(False),
        "Complete original case census",
    )
    require(prior["limits"] == old.LIMITS, "No changed engineering limits")
    pins = dict(prior["inputs"])
    pins.update(prior["compiled_models"])
    pins.update(
        {
            str(p): old.sha(p)
            for p in (parent / "result.json", VCO, Path(__file__).resolve())
        }
    )
    for path, expected in pins.items():
        require(old.sha(Path(path)) == expected, "Input changed: " + path)
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    require(len(runtime) == len(models) == 1, "Unique pinned runtime/models required")
    osdi = [Path(p) for p in prior["compiled_models"]]
    cases = [c for c in old.cases(False) if not pilot or c["name"] in PILOT]
    output.mkdir()
    (output / "spinit").write_text(
        "* Explicit native models and zero-source startup.\nset num_threads=1\n"
    )
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        pilot=pilot,
        limits=old.LIMITS,
        preserved_prior_status=prior["status"],
        startup_reference=STARTUP_REFERENCE,
        unchanged_divider_and_latch=True,
        native_vco_limiter_revision=True,
        no_uic_ic_nodeset_or_equation_changes=True,
        physical_power_sequencer=False,
        full_pvt_qualification=False,
        pll_implemented=False,
        cdr_implemented=False,
        scope="Separate finite VCO-v2/divider experiment. Native OFF is an initial Newton flag; actual foundry equations remain enabled during the unchanged zero-source ramp. No layout, PLL, CDR or PCIe qualification.",
    )

    def save():
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    def bound():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    save()
    try:
        for case in cases:
            folder = output / case["name"]
            folder.mkdir()
            for p in (VCO, old.LATCH):
                shutil.copyfile(p, folder / p.name)
            (folder / old.CIRCUIT.name).write_text(old.circuit(case))
            (folder / "bench.cir").write_text(deck(case, models[0], osdi))
            row = dict(case=case, command=[str(runtime[0]), "-n", "-b", "bench.cir"])
            result["cases"].append(row)
            save()
            with (folder / "run.log").open("w") as log:
                try:
                    execution = subprocess.run(
                        row["command"],
                        cwd=folder,
                        env={**os.environ, "SPICE_SCRIPTS": str(output)},
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=180,
                        preexec_fn=bound,
                    )
                    row["returncode"] = execution.returncode
                except subprocess.TimeoutExpired:
                    row.update(returncode=None, execution_failure="timeout")
            log = (folder / "run.log").read_text()
            row["numerical"] = old.diagnostics(log)
            extra = [
                s
                for s in log.splitlines()
                if re.search(
                    r"(?i)\b(?:fatal|failed|infinity|infinite)\b|no such vector", s
                )
            ]
            row["numerical"]["lines"] += extra
            row["numerical"]["clean"] &= not extra
            try:
                require(row.get("returncode") == 0, "Native execution did not succeed")
                row["flags_observed"] = read_flags(log, case)
                row["flags_verified"] = True
                row["initial_op"] = initial_op(folder / "initial-op.dat", case)
                row["zero_initial_op"] = True
                row["measurement"] = old.measure(
                    old.read_wave(folder / "wave.dat", case), case
                )
            except (ValueError, KeyError, OSError, StopIteration) as exc:
                row["execution_failure"] = row.get("execution_failure", repr(exc))
            row["expected_outcome_observed"] = accepted(row)
            wave = folder / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                with (
                    wave.open("rb") as src,
                    gzip.open(folder / "wave.dat.gz", "wb") as dst,
                ):
                    shutil.copyfileobj(src, dst)
                wave.unlink()
            row["outputs"] = {
                p.name: old.sha(p) for p in folder.iterdir() if p.is_file()
            }
            save()
            print(
                case["name"],
                row["expected_outcome_observed"],
                row.get("execution_failure"),
                flush=True,
            )
        for path, expected in pins.items():
            require(
                old.sha(Path(path)) == expected, "Native input changed during execution"
            )
        result["complete_inputs_rechecked"] = True
        good = all(r["expected_outcome_observed"] for r in result["cases"])
        nominal = next(
            r for r in result["cases"] if r["case"]["name"] == "nominal"
        ).get("measurement", {})
        result["nominal_input_range_pass"] = (
            old.LIMITS["nominal_input_min_hz"]
            <= (nominal.get("input_frequency_hz") or 0)
            <= old.LIMITS["nominal_input_max_hz"]
        )
        good &= result["nominal_input_range_pass"]
        if not pilot:
            half = next(
                r for r in result["cases"] if r["case"]["name"] == "half_step"
            ).get("measurement", {})
            a, b = nominal.get("output_frequency_hz"), half.get("output_frequency_hz")
            result["half_step_frequency_relative_delta"] = (
                abs(a / b - 1) if a and b else None
            )
            good &= (
                result["half_step_frequency_relative_delta"] is not None
                and result["half_step_frequency_relative_delta"] < 0.001
            )
        result["status"] = "PASS_FINITE_DIV2_V2_SCREEN" if good else "FAIL_PRESERVED"
    except BaseException as exc:
        result.update(status="ERROR", error=repr(exc))
    finally:
        save()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    result = run(args.parent, args.out, args.pilot)
    print(result["status"])
    return 0 if result["status"] == "PASS_FINITE_DIV2_V2_SCREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
