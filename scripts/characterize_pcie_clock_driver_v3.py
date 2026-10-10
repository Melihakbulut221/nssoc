#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native parallel clock-driver load screen, explicitly not qualified PEX."""

import argparse
import json
import lzma
import math
import os
from pathlib import Path
import re
import shutil
import statistics

import characterize_pcie_clock_headroom_v2 as parent
import characterize_pcie_clock_fanout_v1 as fanout

old = parent.old
require = parent.require
PARENT_SHA = "00069ff6113f3390e4dcdf0f6778b6d1d199246252345b2bd726c2ba7338217e"
CIRCUIT_SHA = "c55baf3e280bc735c0825e96861150b09c63b4de29ed4241f965f835f3cdb749"
FANOUT_SHA = "c8c4cffde783a8a46663b0836b121abd3f6a1a7febfcfeb0ea00e2aab6a80a5d"
CIRCUIT = old.ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v2.spice"
TOP = "nssoc_clock_vco_hbt_v3"
FILE = "clock_vco_hbt_v3.spice"
COUNTS = (1, 4, 6, 8)
SINK_NX = (1, 2)
FUNCTIONAL_CHECKS = (
    "edges",
    "edge_order",
    "differential_swing",
    "frequency",
    "deterministic_period_spread",
    "duty",
)
BRANCHES = ("xfp", "xfn", "xftp", "xftn")
PVT_NAMES = (
    "nominal",
    "hbt_bcs_mos_ss_125",
    "hbt_wcs_mos_ss_125",
    "hbt_wcs_mos_ff_125",
    "hbt_wcs_mos_ss_-40",
    "hbt_bcs_mos_ff_-40",
    "res_bcs_cap_bcs_2.415",
    "res_wcs_cap_wcs_2.185",
)


def circuit(case, count, sink_nx=1):
    require(sink_nx in SINK_NX, "Explicit sink emitter count only")
    require(count in COUNTS, "Explicit parallel counts only")
    source = CIRCUIT.read_text()
    require(old.sha(CIRCUIT) == CIRCUIT_SHA, "Frozen physical v2 circuit differs")
    expected = parent.revised(old.circuit(case), "4.0")
    source = expected
    for name, node in (("XFTP", "clkp"), ("XFTN", "clkn")):
        before = f"{name} {node} bref avss sub npn13G2 Nx=1"
        require(source.count(before) == 1, "Exact sink geometry anchor required")
        source = source.replace(before, before.replace("Nx=1", f"Nx={sink_nx}"))
    additions = []
    for name in BRANCHES:
        lines = [
            line for line in source.splitlines() if line.lower().startswith(name + " ")
        ]
        require(len(lines) == 1, "Exact original output branch required")
        line = lines[0]
        for index in range(1, count):
            additions.append(
                line.replace(line.split()[0] + " ", line.split()[0] + f"D{index} ", 1)
            )
    source = source.replace(
        ".ends " + parent.NEW_TOP, "\n".join(additions) + "\n.ends " + parent.NEW_TOP
    )
    source = source.replace(".subckt " + parent.NEW_TOP, ".subckt " + TOP).replace(
        ".ends " + parent.NEW_TOP, ".ends " + TOP
    )
    return source


def contract(text, count):
    result = {}
    for line in text.splitlines():
        parts = line.lower().split()
        if len(parts) == 7 and parts[5] == "npn13g2":
            name = parts[0]
            require(name not in result, "Duplicate native device")
            require(
                parts[6].startswith("nx="), "Explicit native emitter count required"
            )
            nx = int(parts[6][3:])
            require(1 <= nx <= 10, "Pinned HBT model only supports Nx1..10")
            result[name] = (parts[1:4], nx)
    require(
        len(result) == 18 + 4 * (count - 1), "Actual parallel device census differs"
    )
    return result


def identities(hbts):
    return ["q.xosc." + name + ".qnpn13g2" for name in hbts]


def vectors(hbts):
    # All old electrical/resistor observations remain; add every physical HBT
    # branch's collector/base current and native thermal node individually.
    original = old.vectors()
    extras = [
        f"@q.xosc.{name}.qnpn13g2[ic]"
        for name in hbts
        if f"@q.xosc.{name}.qnpn13g2[ic]" not in original
    ]
    extras += [f"@q.xosc.{name}.qnpn13g2[ib]" for name in hbts]
    extras += [f"v(xosc.{name}.t)" for name in hbts]
    return original + extras


def deck(case, models, osdi, cp, cn, hbts):
    original = old.deck(dict(case, load_f=cp), models, osdi)
    if case["fault"] == "overload":
        cp = cn = 100e-12

    require(
        original.count(f"CLOADN clkn 0 {cp:.12g}") == 1, "Original load anchor differs"
    )
    text = original.replace(f"CLOADN clkn 0 {cp:.12g}", f"CLOADN clkn 0 {cn:.12g}")
    text = text.replace(f'.include "{old.CIRCUIT.name}"', f'.include "{FILE}"')
    text = text.replace(
        "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt\n",
        f"XOSC clkp clkn vctrl avdd 0 0 {TOP}\n",
    )
    require(
        not re.search(r"(?im)^\s*\.ic\b|\buic\b|\balter\b|^\.nodeset", text),
        "No forced state",
    )
    require(
        text.count(".options reltol=1e-4 abstol=1e-12") == 1,
        "Original tolerances required",
    )
    vs = " ".join(vectors(hbts))
    previous = " ".join(old.vectors())
    require(
        text.count("save " + previous) == 1
        and text.count("wrdata wave.dat " + previous) == 1,
        "Exact old observation bindings required",
    )
    text = text.replace("save " + previous, "save " + vs).replace(
        "wrdata wave.dat " + previous, "wrdata wave.dat " + vs
    )
    flags = "".join(
        f"alter @{n}[off] = 1\necho NSSOC_DRIVER_FLAG_BEGIN {n}\nshow {n} : off\necho NSSOC_DRIVER_FLAG_END\n"
        for n in identities(hbts)
    )
    require(text.count("\ntran ") == 1, "Exactly one unchanged transient")
    return text.replace(
        "\ntran ", "\n" + flags + "op\nwrdata initial-op.dat " + vs + "\ntran ", 1
    )


def flags(log, hbts):
    rows = re.findall(
        r"(?ms)^NSSOC_DRIVER_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_DRIVER_FLAG_END\s*$", log
    )
    require(
        [n for n, _ in rows] == identities(hbts),
        "Native initialization coverage differs",
    )
    for name, body in rows:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+(\S+)\s*$", body) == ["1"],
            "Native OFF flag differs",
        )
    return dict.fromkeys(identities(hbts), 1)


def read_wave(path, hbts, case):
    with Path(path).open() as stream:
        header = stream.readline().split()
        require(
            header == ["time", *vectors(hbts)],
            "Exact native observation order required",
        )
        data = {name: [] for name in header}
        for line in stream:
            row = [float(x) for x in line.split()]
            require(
                len(row) == len(header) and all(math.isfinite(x) for x in row),
                "Incomplete/nonfinite native wave",
            )
            for name, x in zip(header, row):
                data[name].append(x)
    ts = data["time"]
    require(
        len(ts) >= 1000
        and ts[0] == 0.0
        and ts[-1] >= 12e-9
        and all(b > a for a, b in zip(ts, ts[1:])),
        "Missing native time coverage",
    )
    require(
        max(b - a for a, b in zip(ts, ts[1:])) <= case["step_s"] * 1.00001,
        "Native timestep bound exceeded",
    )
    return data


def functional_clock_pass(measured):
    require(
        set(FUNCTIONAL_CHECKS).issubset(measured["checks"]),
        "Complete clock predicates required",
    )
    return all(measured["checks"][name] for name in FUNCTIONAL_CHECKS)


def measure(data, hbts):
    measured = old.measure(data)
    begin = next(i for i, t in enumerate(data["time"]) if t >= 4e-9)
    active = {n: a[begin:] for n, a in data.items()}

    def voltage(n, selected=active):
        return (
            [0.0] * len(selected["time"])
            if n == "avss"
            else selected[
                "v(" + (n if n in ("avdd", "clkp", "clkn") else "xosc." + n) + ")"
            ]
        )

    devices = {}
    for name, ((collector, _, emitter), nx) in hbts.items():
        vce = [a - b for a, b in zip(voltage(collector), voltage(emitter))]
        ic = active[f"@q.xosc.{name}.qnpn13g2[ic]"]
        ib = active[f"@q.xosc.{name}.qnpn13g2[ib]"]
        thermal = active[f"v(xosc.{name}.t)"]
        full_vce = [
            a - b for a, b in zip(voltage(collector, data), voltage(emitter, data))
        ]
        devices[name] = dict(
            full_capture_max_vce_v=max(full_vce),
            full_capture_max_abs_ic_a=max(
                map(abs, data[f"@q.xosc.{name}.qnpn13g2[ic]"])
            ),
            full_capture_thermal_node_min_v=min(data[f"v(xosc.{name}.t)"]),
            full_capture_thermal_node_max_v=max(data[f"v(xosc.{name}.t)"]),
            nx=nx,
            min_vce_v=min(vce),
            max_vce_v=max(vce),
            max_abs_ic_a=max(map(abs, ic)),
            mean_ic_a=statistics.mean(ic),
            mean_ib_a=statistics.mean(ib),
            max_abs_ib_a=max(map(abs, ib)),
            thermal_node_min_v=min(thermal),
            thermal_node_max_v=max(thermal),
        )
    measured["devices"] = devices
    measured["checks"].update(
        headroom=all(
            x["min_vce_v"] >= old.LIMITS["min_vce_v"] for x in devices.values()
        ),
        maximum_vce=all(
            x["max_vce_v"] <= old.LIMITS["max_vce_v"] for x in devices.values()
        ),
        current_density=all(
            x["max_abs_ic_a"] < x["nx"] * old.LIMITS["max_collector_a_per_emitter"]
            for x in devices.values()
        ),
    )
    measured["settled_window_s"] = [4e-9, 12e-9]
    measured["full_capture_window_s"] = [data["time"][0], data["time"][-1]]
    measured["checks"].update(
        full_capture_maximum_vce=all(
            d["full_capture_max_vce_v"] <= old.LIMITS["max_vce_v"]
            for d in devices.values()
        ),
        full_capture_current_density=all(
            d["full_capture_max_abs_ic_a"]
            < d["nx"] * old.LIMITS["max_collector_a_per_emitter"]
            for d in devices.values()
        ),
    )
    measured["functional_clock_pass"] = functional_clock_pass(measured)
    measured["screen_pass"] = all(measured["checks"].values())
    bias = ["xbref", "xbt"] + [n for n in hbts if n.startswith(("xftp", "xftn"))]
    measured["bias"] = dict(
        bref_min_v=min(active["v(xosc.bref)"]),
        bref_max_v=max(active["v(xosc.bref)"]),
        bref_mean_v=statistics.mean(active["v(xosc.bref)"]),
        bias_device_names=bias,
        mean_sum_bref_base_current_a=sum(devices[n]["mean_ib_a"] for n in bias),
        reference_mean_ic_a=devices["xbref"]["mean_ic_a"],
        output_sink_mean_ic_a=sum(
            devices[n]["mean_ic_a"] for n in hbts if n.startswith(("xftp", "xftn"))
        ),
        resistor_thermal_nodes={
            n: dict(min_v=min(a), max_v=max(a))
            for n, a in active.items()
            if n.endswith(".dt)")
        },
    )
    return measured


def cases(suite, loads):
    if suite == "loads":
        bases = [dict(old.BASE, name="nominal")]
    elif suite == "pvt":
        bases = [c for c in old.cases(False) if c["name"] in PVT_NAMES]
    elif suite == "full":
        bases = [
            c
            for c in old.cases(False)
            if c["name"] == "nominal" or c["name"].startswith(("hbt_", "res_"))
        ]
    elif suite == "negative":
        bases = [c for c in old.cases(False) if c["fault"]]
    else:
        raise ValueError("Unknown bounded suite")
    result = []
    for case in bases:
        for label, pair in loads if suite in ("loads", "pvt") else [loads[-1]]:
            result.append((dict(case, name=case["name"] + "__" + label), pair))
    return result


def atomic_record(path, record):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(path)


def run(
    baseline, startup, capacitance, output, count, suite, candidate=None, sink_nx=1
):
    baseline, startup, capacitance, output = (
        Path(p).resolve() for p in (baseline, startup, capacitance, output)
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM output required",
    )
    require(
        old.sha(Path(parent.__file__)) == PARENT_SHA
        and old.sha(Path(fanout.__file__)) == FANOUT_SHA
        and old.sha(capacitance) == fanout.CAP_SHA,
        "Frozen method/capacitance source changed",
    )
    _, pins = parent.inputs(baseline, startup)
    for p in (
        Path(__file__).resolve(),
        CIRCUIT,
        Path(parent.__file__).resolve(),
        Path(fanout.__file__).resolve(),
        capacitance,
    ):
        pins[str(p)] = old.sha(p)
    canonical = circuit(dict(old.BASE), count, sink_nx)
    if candidate:
        candidate = Path(candidate).resolve()
        require(candidate.read_text() == canonical, "Selected circuit differs")
        pins[str(candidate)] = old.sha(candidate)
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    require(len(models) == len(runtime) == 1, "Unique pinned models/runtime required")
    loadrows = fanout.loads(json.loads(capacitance.read_text()))
    selected = cases(suite, loadrows)
    output.mkdir()
    (output / "spinit").write_text(parent.init.SPINIT)
    (output / FILE).write_text(canonical)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        count=count,
        sink_nx=sink_nx,
        suite=suite,
        limits=old.LIMITS,
        loads=loadrows,
        cases=[],
        qualified_pex=False,
        physical_qualification=False,
        pll_implemented=False,
        scope=__doc__,
        limitations=[
            "Each follower Nx4/sinkNx1-or-2 stays inside pinned model Nx1..10. Parallel branches have independent native thermal nodes; mutual device heating/layout/parasitic changes are unvalidated.",
            "Ground/quiet/opposed collapsed capacitive loads omit route R/L, actual aggressor waveforms and receiving devices. Native model/current/thermal results do not establish full PEX or PHY acceptance.",
        ],
    )

    def save():
        atomic_record(output / "result.json", record)

    save()
    previous = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    try:
        for case, (cp, cn) in selected:
            d = output / case["name"]
            d.mkdir()
            text = circuit(case, count, sink_nx)
            hbts = contract(text, count)
            (d / FILE).write_text(text)
            (d / "bench.cir").write_text(
                deck(
                    case,
                    models[0],
                    [baseline / n for n in parent.init.MODELS],
                    cp,
                    cn,
                    hbts,
                )
            )
            row = dict(
                case=case,
                load_p_f=cp,
                load_n_f=cn,
                applied_load_p_f=(100e-12 if case["fault"] == "overload" else cp),
                applied_load_n_f=(100e-12 if case["fault"] == "overload" else cn),
                actual_hbt_count=len(hbts),
            )
            record["cases"].append(row)
            save()
            try:
                row["execution"] = parent.init.startup.s.rx.execute(
                    [str(runtime[0]), "-n", "-b", "bench.cir"], d, d / "run.log"
                )
                log = (d / "run.log").read_text()
                row["numerical"] = old.diagnostics(log)
                row["flags_observed"] = flags(log, hbts)
                row["initial_op"] = parent.init.startup.initial_op(
                    d / "initial-op.dat", vectors(hbts)
                )
                row["zero_initial_op"] = (
                    max(map(abs, row["initial_op"].values())) <= 1e-10
                )
                data = read_wave(d / "wave.dat", hbts, case)
                row["measurement"] = measure(data, hbts)
                del data
                row["clean_initialization"] = (
                    row["execution"]["returncode"] == 0
                    and row["numerical"]["clean"]
                    and row["zero_initial_op"]
                )
                row["expected_negative_rejected"] = (
                    not row["measurement"]["functional_clock_pass"]
                    if case["fault"]
                    else None
                )
            except (ValueError, RuntimeError) as error:
                row.update(
                    error=repr(error),
                    clean_initialization=False,
                    numerical=old.diagnostics((d / "run.log").read_text()),
                )
            wave = d / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                row["wave_retained"] = (
                    bool(case["fault"])
                    or not row.get("measurement", {}).get("screen_pass", False)
                    or (
                        suite == "full"
                        and case["name"]
                        in (
                            "nominal__opposed_aggressor_equivalent",
                            "hbt_bcs_mos_ss_125__opposed_aggressor_equivalent",
                            "hbt_wcs_mos_ss_-40__opposed_aggressor_equivalent",
                            "res_wcs_cap_wcs_2.415__opposed_aggressor_equivalent",
                        )
                    )
                    or (
                        suite == "loads"
                        and case["name"].endswith(
                            ("reference_50fF", "opposed_aggressor_equivalent")
                        )
                    )
                    or (
                        suite == "pvt"
                        and case["name"]
                        == "hbt_bcs_mos_ss_125__opposed_aggressor_equivalent"
                    )
                    or (not row["clean_initialization"])
                )
                if row["wave_retained"]:
                    with (
                        wave.open("rb") as src,
                        lzma.open(d / "wave.dat.xz", "wb", preset=1) as dst,
                    ):
                        shutil.copyfileobj(src, dst)
                wave.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in d.iterdir()}
            save()
            m = row.get("measurement", {})
            print(
                case["name"],
                row["clean_initialization"],
                m.get("screen_pass"),
                m.get("frequency_hz"),
                min(m.get("max_diff_v", 0), -m.get("min_diff_v", 0)),
                flush=True,
            )
        require(
            all(old.sha(Path(p)) == h for p, h in pins.items()), "Native inputs changed"
        )
        record["source_bytes_unchanged"] = True
        record["clean_cases"] = sum(r["clean_initialization"] for r in record["cases"])
        record["positive_failures"] = [
            r["case"]["name"]
            for r in record["cases"]
            if not r["case"]["fault"]
            and not r.get("measurement", {}).get("screen_pass")
        ]
        record["negative_controls_rejected"] = all(
            r.get("expected_negative_rejected")
            for r in record["cases"]
            if r["case"]["fault"]
        )
        record["status"] = (
            "COMPLETE_COLLAPSED_LOAD_SCREEN_WITH_EXPLICIT_FAILURES"
            if record["clean_cases"] == len(selected)
            and record["negative_controls_rejected"]
            else "NUMERICAL_OR_CONTROL_FAILURE_PRESERVED"
        )
    finally:
        if previous is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = previous
        save()
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "startup", "capacitance", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--count", type=int, choices=COUNTS, required=True)
    p.add_argument(
        "--suite", choices=("loads", "pvt", "full", "negative"), required=True
    )
    p.add_argument("--candidate", type=Path)
    p.add_argument("--sink-nx", type=int, choices=SINK_NX, default=1)
    a = p.parse_args()
    r = run(
        a.baseline,
        a.startup,
        a.capacitance,
        a.out,
        a.count,
        a.suite,
        a.candidate,
        a.sink_nx,
    )
    return int(r["status"] != "COMPLETE_COLLAPSED_LOAD_SCREEN_WITH_EXPLICIT_FAILURES")


if __name__ == "__main__":
    raise SystemExit(main())
