#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native fixed-ESD small-signal loading; excludes bondpad/wire/package parasitics."""

import argparse
import itertools
import json
import math
from pathlib import Path
import re
from check_ihp_drc import digest
from check_pcie_rx_cell import execute
from make_pcie_pad_boundary import TOP, reference

NG_SHA = "820658317b0b54035208da41936fd6871ce924036e5ea4113a4168b821b7fc45"
FREQUENCIES = (1e6, 4e9, 8e9)


def model_reference():
    return re.sub(r"^D([PN](?:dd|ss)) ", r"X\1 ", reference(), flags=re.M)


def bench(models, physical, vdd, bias, temp, out, mode="normal"):
    if mode not in ("normal", "known_cap", "wrong_rail"):
        raise ValueError("Unknown model control")
    devices = (
        "Cknown padp 0 50f\n"
        if mode == "known_cap"
        else f"XBOUND padp padn {'0 avdd' if mode == 'wrong_rail' else 'avdd 0'} {TOP}\n"
    )
    lines = [
        "* Native model-only loading; not extracted bondpad RF or ESD rating",
        f'.include "{models}"',
        f'.include "{physical}"',
        f"VDD avdd 0 {vdd:.8g}",
        f"VP padp 0 dc {bias:.8g} ac 1",
        f"VN padn 0 dc {bias:.8g}",
        devices,
        f".temp {temp}",
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        "set numdgt=15",
        "op",
        "print i(VP)",
    ]
    for i, f in enumerate(FREQUENCIES):
        lines += [
            f"ac lin 1 {f:.0f} {f:.0f}",
            "let yr=-real(i(VP))",
            "let yi=-imag(i(VP))",
            f"wrdata {out}/y{i}.dat yr yi",
        ]
    return "\n".join(lines + ["quit", ".endc", ".end", ""])


def parse_case(out, returncode):
    text = (out / "native.log").read_text()
    if returncode != 0 or re.search(r"\b(?:error|fatal|warning|failed)\b", text, re.I):
        raise ValueError("Native model run failed or warned")
    found = re.findall(r"^i\(vp\)\s*=\s*([-+\d.eE]+)\s*$", text, re.M)
    if len(found) != 1:
        raise ValueError("Exactly one native operating-point current required")
    current = float(found[0])
    rows = []
    for i, f in enumerate(FREQUENCIES):
        lines = (out / f"y{i}.dat").read_text().splitlines()
        if len(lines) != 2 or lines[0].split() != ["frequency", "yr", "yi"]:
            raise ValueError("Exact one-frequency native output required")
        nums = [float(x) for x in lines[1].split()]
        if len(nums) != 3 or nums[0] != f or not all(math.isfinite(x) for x in nums):
            raise ValueError("Native frequency or finite-value contract failed")
        _, g, b = nums
        rows.append(
            dict(
                frequency_hz=f,
                conductance_s=g,
                susceptance_s=b,
                capacitance_f=b / (2 * math.pi * f),
            )
        )
    if not math.isfinite(current):
        raise ValueError("Nonfinite native current")
    return dict(leakage_a=current, frequencies=rows)


def normal_gate(result):
    return abs(result["leakage_a"]) < 1e-6 and all(
        0 < r["capacitance_f"] < 1e-12 and r["conductance_s"] >= 0
        for r in result["frequencies"]
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ("layout", "physical-check", "pdk", "out"):
        ap.add_argument("--" + n, type=Path, required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = a.out.resolve()
    layout = a.layout.resolve()
    physical = a.physical_check.resolve()
    pdk = a.pdk.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-pad-")
    ):
        ap.error("Fresh project or /dev/shm/nssoc-pad- output required")
    ng = root / "hw/soc/tools/ngspice-42/usr/bin/ngspice"
    models = pdk / "libs.tech/ngspice/models/sg13g2_esd.lib"
    if digest(ng) != NG_SHA:
        raise ValueError("Native simulator identity changed")
    gen = json.loads((layout / "result.json").read_text())
    checks = json.loads((physical / "result.json").read_text())
    if (
        checks["status"]
        != "PASS_PAD_BOUNDARY_MAIN_DRC_STRICT_LVS_AND_SEVEN_NEGATIVES_NO_ESD_RF_APPROVAL"
    ):
        raise ValueError("Completed exact physical boundary prerequisite missing")
    if (layout / "model.spice").read_text() != model_reference() or (
        layout / "schematic.cir"
    ).read_text() != reference():
        raise ValueError("Literal four-device model binding changed")
    pins = {Path(p): h for p, h in gen["input_sha256"].items()}
    pins.update({Path(p): h for p, h in checks["inputs"].items()})
    for d, rec in ((layout, gen), (physical, checks)):
        pins[d / "result.json"] = digest(d / "result.json")
        for n, h in rec["output_sha256"].items():
            pins[d / n] = h
    for p in (
        Path(__file__).resolve(),
        models,
        ng,
        root / "hw/soc/flow/check_pcie_rx_cell.py",
        root / "hw/soc/flow/check_ihp_drc.py",
    ):
        pins[p] = digest(p)
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError("Source or exact physical input changed")
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        controls={},
        cases=[],
        model_scope="Unmodified native IHP diode models with exact four-device boundary port order, not raw C/B/E LVS writer text. Native fixed model has no alternate process corners; measured voltage/temperature/bias sweep only. Excludes bondpad, interconnect, package, ESD pulse/self-heating qualification and full PHY.",
        qualified_pex=False,
        esd_qualified=False,
        main_chip_integrated=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def run(label, vdd, bias, temp, mode):
        d = out / label
        d.mkdir()
        s = d / "bench.cir"
        s.write_text(bench(models, layout / "model.spice", vdd, bias, temp, d, mode))
        execution = execute([ng, "-b", s], d, "native")
        r = parse_case(d, execution["returncode"])
        r.update(execution=execution, vdd_v=vdd, bias_v=bias, temp_c=temp)
        return r

    try:
        save()
        cap = run("known_cap", 1.8, 1.36, 27, "known_cap")
        if abs(cap["leakage_a"]) > 1e-15 or any(
            abs(r["capacitance_f"] / 50e-15 - 1) > 1e-9 for r in cap["frequencies"]
        ):
            raise ValueError("Known native 50fF calibration failed")
        wrong = run("wrong_rail", 1.8, 1.36, 27, "wrong_rail")
        if normal_gate(wrong) or abs(wrong["leakage_a"]) < 1e-3:
            raise ValueError("Native forward-conduction negative not rejected")
        record["controls"] = dict(
            known_cap=cap, wrong_rail=wrong, wrong_rail_rejected_by_original_gate=True
        )
        save()
        for i, (vdd, bias, temp) in enumerate(
            itertools.product((1.71, 1.8, 1.89), (1.2, 1.36, 1.5), (-40, 27, 125))
        ):
            r = run(f"case{i:02}", vdd, bias, temp, "normal")
            if not normal_gate(r):
                raise ValueError("Native reverse-bias sanity gate failed")
            record["cases"].append(r)
            save()
        if len(record["cases"]) != 27 or any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Native sweep/source closure failed")
        cs = [r["capacitance_f"] for c in record["cases"] for r in c["frequencies"]]
        record.update(
            status="PASS_27_NATIVE_DIODE_LOADING_CASES_AND_TWO_CONTROLS_NOT_PAD_PEX_OR_ESD_QUALIFICATION",
            min_capacitance_f=min(cs),
            max_capacitance_f=max(cs),
            max_abs_leakage_a=max(abs(c["leakage_a"]) for c in record["cases"]),
        )
        record["output_sha256"] = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "result.json"
        }
        save()
    except BaseException as exc:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    main()
