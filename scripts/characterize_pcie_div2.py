#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native frozen-VCO-driven HBT prescaler, finite nominal/corner characterization.

Only native IHP circuits generate clock and divide state. Zero-source ramps,
full raw wave/log retention, exact inherited sources and independent edge counts.
No PLL, CDR, phase-noise, random-jitter, extracted-layout or link qualification.
"""

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "hw/soc/analog/pcie/clock_div2_hbt.spice"
VCO = ROOT / "hw/soc/analog/pcie/clock_vco_hbt.spice"
LATCH = ROOT / "hw/soc/analog/pcie/rx_sampler_hbt_v2.spice"
FROZEN = {
    VCO: "b93e478e3d6a766051b82aabd5796d6fa8f2dbac68f25f1c1757d411369d5426",
    LATCH: "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f",
}
BASE = dict(
    hbt="hbt_typ",
    resistor="res_typ",
    mos="mos_tt",
    cap="cap_typ",
    temp=27,
    supply=2.3,
    divider_supply=2.5,
    control=0.85,
    clock_load_f=50e-15,
    output_load_f=50e-15,
    ramp_s=500e-12,
    step_s=1e-12,
    fault="",
    role="required",
)
LIMITS = dict(
    min_input_edges=40,
    min_output_edges=20,
    min_peak_v=0.1,
    nominal_input_min_hz=7.5e9,
    nominal_input_max_hz=8.5e9,
    min_duty=0.4,
    max_duty=0.6,
    max_period_ratio_error=0.005,
    min_vce_v=0.4,
    max_vce_v=1.6,
    max_ic_a_per_nx=0.003,
    observation_begin_s=4e-9,
    observation_end_s=12e-9,
    max_step_relative_excess=0.00001,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cases(quick=False):
    result = [
        dict(BASE, name="nominal"),
        dict(BASE, name="half_step", step_s=0.5e-12),
        dict(BASE, name="slow_ramp", ramp_s=2e-9),
        dict(BASE, name="load100fF", output_load_f=100e-15),
    ]
    if not quick:
        result += [
            dict(BASE, name=n, hbt=h, resistor=r, temp=t, role="exploration")
            for n, h, r, t in [
                ("cold_fast", "hbt_bcs", "res_bcs", -40),
                ("hot_slow", "hbt_wcs", "res_wcs", 125),
                ("cold_slow", "hbt_wcs", "res_typ", -40),
                ("hot_fast", "hbt_bcs", "res_typ", 125),
            ]
        ]
    result += [
        dict(BASE, name=f, fault=f, role="negative")
        for f in ("no_toggle", "same_phase", "no_bias", "same_clock")
    ]
    return result


def circuit(case):
    text = CIRCUIT.read_text()
    edits = {
        "no_toggle": ("XM qn qp mp mn", "XM qp qn mp mn"),
        "same_phase": ("XM qn qp mp mn clkn clkp", "XM qn qp mp mn clkp clkn"),
        "no_bias": ("XBIAS avdd ref sub", "XBIAS avss ref sub"),
    }
    if case["fault"] in edits:
        old, new = edits[case["fault"]]
        if text.count(old) != 1:
            raise ValueError("Native mutation anchor changed")
        text = text.replace(old, new)
    return text


def statements(text, subckt):
    match = re.search(
        r"(?mi)^\.subckt\s+"
        + re.escape(subckt)
        + r"\s+([^\n]+)\n(.*?)^\.ends\s+"
        + re.escape(subckt)
        + r"\s*$",
        text,
        re.S | re.M,
    )
    if not match:
        raise ValueError("Missing exact subcircuit " + subckt)
    return match[1].lower().split(), [
        s.lower().split() for s in match[2].splitlines() if s and not s.startswith("*")
    ]


def device_contract(case):
    # Resolve all HBT terminals from actual frozen subcircuit port lists, not
    # assumed nested names. Mutated connectivity is used for its own metrics.
    hbts = {}
    resistors = []

    def add(text, subckt, prefix, actual):
        ports, body = statements(text, subckt)
        if len(ports) != len(actual):
            raise ValueError("Subcircuit port arity")
        mapping = dict(zip(ports, actual))

        def node(n):
            return mapping.get(n, prefix + "." + n)

        for words in body:
            if words[0].startswith("x") and len(words) >= 6 and words[5] == "npn13g2":
                nx = [w for w in words[6:] if w.startswith("nx=")]
                if len(nx) != 1:
                    raise ValueError("Unbound HBT emitter count")
                hbts[prefix + "." + words[0]] = (
                    tuple(node(n) for n in words[1:4]),
                    int(nx[0][3:]),
                )
            elif words[0].startswith("x") and len(words) >= 5 and words[4] == "rppd":
                resistors.append(prefix + "." + words[0])
            elif words[-1] == "nssoc_cml_latch":
                add(
                    LATCH.read_text(),
                    "nssoc_cml_latch",
                    prefix + "." + words[0],
                    [node(n) for n in words[1:-1]],
                )

    add(
        VCO.read_text(),
        "nssoc_clock_vco_hbt",
        "xosc",
        ["clkp", "clkn", "vctrl", "avdd", "0", "0"],
    )
    add(
        circuit(case),
        "nssoc_clock_div2_hbt",
        "xdiv",
        [
            "clkp",
            "clkp" if case["fault"] == "same_clock" else "clkn",
            "qp",
            "qn",
            "dvdd",
            "0",
            "0",
        ],
    )
    if len(hbts) != 33 or len(resistors) != 18:
        raise ValueError("Exact native inventory changed")
    return hbts, resistors


def vectors(case):
    hbts, resistors = device_contract(case)
    nets = {n for pins, _ in hbts.values() for n in pins} | {
        "clkp",
        "clkn",
        "qp",
        "qn",
        "avdd",
        "dvdd",
        "vctrl",
    }
    return (
        ["v(" + n + ")" for n in sorted(nets - {"0"})]
        + ["i(vdd)", "i(vddiv)", "i(vctrl)"]
        + ["@q." + n + ".qnpn13g2[ic]" for n in hbts]
        + ["v(" + n + ".dt)" for n in resistors]
    )


def deck(case, models, osdi):
    if not 0 < case["step_s"] <= 1e-12 or not 0 < case["ramp_s"] <= 2e-9:
        raise ValueError("Unsupported step/ramp")
    out = ["Native frozen VCO and two-latch HBT prescaler"]
    for kind, corner in [
        ("HBT", case["hbt"]),
        ("RES", case["resistor"]),
        ("MOShv", case["mos"]),
        ("CAP", case["cap"]),
    ]:
        out.append(f'.lib "{models}/corner{kind}.lib" {corner}')
    out += [f'.include "{p.name}"' for p in (VCO, LATCH, CIRCUIT)]
    out += [f".temp {case['temp']}", ".options reltol=1e-4 abstol=1e-12"]
    for name, node, voltage in [
        ("VDD", "avdd", case["supply"]),
        ("VDDIV", "dvdd", case["divider_supply"]),
        ("VCTRL", "vctrl", case["control"]),
    ]:
        out.append(f"{name} {node} 0 PWL(0 0 {case['ramp_s']:.12g} {voltage:.12g})")
    out += [
        "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt",
        "XDIV clkp "
        + ("clkp" if case["fault"] == "same_clock" else "clkn")
        + " qp qn dvdd 0 0 nssoc_clock_div2_hbt",
    ]
    for node, load in [
        ("clkp", case["clock_load_f"]),
        ("clkn", case["clock_load_f"]),
        ("qp", case["output_load_f"]),
        ("qn", case["output_load_f"]),
    ]:
        out.append(f"CLOAD_{node} {node} 0 {load:.12g}")
    out += [".control"] + ["pre_osdi " + str(p) for p in osdi]
    out += [
        "set wr_singlescale",
        "set wr_vecnames",
        "set numdgt=12",
        "save " + " ".join(vectors(case)),
        f"tran {case['step_s']:.12g} 12n 0 {case['step_s']:.12g}",
        "wrdata wave.dat " + " ".join(vectors(case)),
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(out) + "\n"


def read_wave(path, case):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        names = stream.readline().split()
        if names != ["time", *vectors(case)]:
            raise ValueError("Changed vector census/order")
        data = {n: [] for n in names}
        for line in stream:
            row = [float(x) for x in line.split()]
            if len(row) != len(names) or not all(math.isfinite(x) for x in row):
                raise ValueError("Incomplete/nonfinite waveform")
            for n, x in zip(names, row):
                data[n].append(x)
    t = data["time"]
    if (
        len(t) < 1000
        or t[0] != 0
        or t[-1] < 12e-9
        or any(b <= a for a, b in zip(t, t[1:]))
    ):
        raise ValueError("Incomplete/nonmonotonic time coverage")
    if max(b - a for a, b in zip(t, t[1:])) > case["step_s"] * (
        1 + LIMITS["max_step_relative_excess"]
    ):
        raise ValueError("Native maximum step exceeded")
    return data


def crossings(time, values, up=True):
    edges = []
    for i in range(1, len(time)):
        a, b = values[i - 1 : i + 1]
        if (a <= 0 < b) if up else (a >= 0 > b):
            edges.append(time[i - 1] + (time[i] - time[i - 1]) * (-a) / (b - a))
    return edges


def measure(data, case):
    start = next(
        i for i, t in enumerate(data["time"]) if t >= LIMITS["observation_begin_s"]
    )
    active = {n: x[start:] for n, x in data.items()}
    time = active["time"]
    ck = [p - n for p, n in zip(active["v(clkp)"], active["v(clkn)"])]
    q = [p - n for p, n in zip(active["v(qp)"], active["v(qn)"])]
    iu, idown = crossings(time, ck), crossings(time, ck, False)
    ou, odown = crossings(time, q), crossings(time, q, False)
    ip = [b - a for a, b in zip(iu, iu[1:])]
    op = [b - a for a, b in zip(ou, ou[1:])]
    input_order = [len([x for x in idown if a < x < b]) for a, b in zip(iu, iu[1:])]
    output_order = [len([x for x in odown if a < x < b]) for a, b in zip(ou, ou[1:])]
    edge_counts = [len([x for x in iu if a < x < b]) for a, b in zip(ou, ou[1:])]
    duties = [
        (next(x for x in odown if a < x < b) - a) / (b - a)
        for a, b, n in zip(ou, ou[1:], output_order)
        if n == 1
    ]
    # Every output edge must correspond to one successive rising input edge;
    # every output rising-to-rising period must span exactly two such edges.
    output_edges = sorted([(x, 1) for x in ou] + [(x, 0) for x in odown])
    matched = [
        max([i for i, x in enumerate(iu) if x <= edge], default=-1)
        for edge, _ in output_edges
    ]
    interior = [i for i in matched if 0 <= i < len(iu) - 1]
    edge_steps = [b - a for a, b in zip(interior, interior[1:])]
    delays = [
        edge - iu[index]
        for (edge, _), index in zip(output_edges, matched)
        if 0 <= index < len(iu) - 1
    ]
    frequency_i = 1 / statistics.mean(ip) if ip else None
    frequency_o = 1 / statistics.mean(op) if op else None
    ratio = statistics.mean(op) / (2 * statistics.mean(ip)) if op and ip else None
    hbts, resistors = device_contract(case)

    def voltage(n, source):
        return [0.0] * len(source["time"]) if n == "0" else source["v(" + n + ")"]

    devices = {}
    for name, (pins, nx) in hbts.items():
        collector, _, emitter = pins
        vce = [
            a - b for a, b in zip(voltage(collector, active), voltage(emitter, active))
        ]
        full = [a - b for a, b in zip(voltage(collector, data), voltage(emitter, data))]
        current = active["@q." + name + ".qnpn13g2[ic]"]
        devices[name] = dict(
            nx=nx,
            terminals=pins,
            min_operating_vce_v=min(vce),
            max_operating_vce_v=max(vce),
            min_capture_vce_v=min(full),
            max_capture_vce_v=max(full),
            max_abs_ic_a_per_nx=max(abs(x) for x in current) / nx,
            max_capture_abs_ic_a_per_nx=max(
                abs(x) for x in data["@q." + name + ".qnpn13g2[ic]"]
            )
            / nx,
        )
    checks = dict(
        input_edges=len(iu) >= LIMITS["min_input_edges"],
        output_edges=len(ou) >= LIMITS["min_output_edges"],
        input_edge_order=bool(input_order) and all(n == 1 for n in input_order),
        output_edge_order=bool(output_order) and all(n == 1 for n in output_order),
        exactly_two_input_periods=bool(edge_counts)
        and all(n == 2 for n in edge_counts),
        one_output_toggle_each_input_rise=bool(edge_steps)
        and all(n == 1 for n in edge_steps),
        rising_edge_latency=bool(delays)
        and all(
            0 < edge - iu[index] < (iu[index + 1] - iu[index]) / 2
            for (edge, _), index in zip(output_edges, matched)
            if 0 <= index < len(iu) - 1
        ),
        period_ratio=ratio is not None
        and abs(ratio - 1) < LIMITS["max_period_ratio_error"],
        output_swing=min(max(q), -min(q)) >= LIMITS["min_peak_v"],
        input_swing=min(max(ck), -min(ck)) >= LIMITS["min_peak_v"],
        duty=bool(duties)
        and min(duties) >= LIMITS["min_duty"]
        and max(duties) <= LIMITS["max_duty"],
        operating_headroom=all(
            d["min_operating_vce_v"] >= LIMITS["min_vce_v"] for d in devices.values()
        ),
        full_capture_maximum_vce=all(
            d["max_capture_vce_v"] <= LIMITS["max_vce_v"] for d in devices.values()
        ),
        current_density=all(
            d["max_capture_abs_ic_a_per_nx"] < LIMITS["max_ic_a_per_nx"]
            for d in devices.values()
        ),
    )
    return dict(
        rows=len(time),
        input_frequency_hz=frequency_i,
        output_frequency_hz=frequency_o,
        period_ratio_to_exact_two=ratio,
        input_rising_edges=len(iu),
        output_rising_edges=len(ou),
        input_edges_per_output_period=edge_counts,
        output_toggle_input_edge_steps=edge_steps,
        edge_delay_range_s=[min(delays), max(delays)] if delays else None,
        duty_range=[min(duties), max(duties)] if duties else None,
        output_diff_range_v=[min(q), max(q)],
        devices=devices,
        resistor_max_selfheat_k={r: max(data["v(" + r + ".dt)"]) for r in resistors},
        checks=checks,
        functional_divide_pass=all(
            v
            for name, v in checks.items()
            if name
            not in ("operating_headroom", "full_capture_maximum_vce", "current_density")
        ),
        screen_pass=all(checks.values()),
        mean_divider_supply_power_w=statistics.mean(
            -v * i for v, i in zip(active["v(dvdd)"], active["i(vddiv)"])
        ),
        mean_vco_supply_power_w=statistics.mean(
            -v * i for v, i in zip(active["v(avdd)"], active["i(vdd)"])
        ),
    )


def diagnostics(log):
    tokens = (
        "warning",
        "error",
        "nan",
        "singular",
        "stepping",
        "timestep too small",
        "aborted",
    )
    lines = [s for s in log.splitlines() if any(t in s.lower() for t in tokens)]
    return dict(clean=not lines, lines=lines)


def expected_result(entry):
    if (
        entry.get("returncode") != 0
        or entry.get("execution_failure")
        or not entry.get("numerical", {}).get("clean")
    ):
        return False
    measurement = entry.get("measurement")
    if not isinstance(measurement, dict):
        return False
    if entry["case"]["fault"]:
        return measurement.get("functional_divide_pass") is False
    return measurement.get("screen_pass") is True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "ngspice", "openvaf", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not (
        out.is_relative_to(ROOT / "hw/soc/out") or out.is_relative_to(Path("/dev/shm"))
    ):
        parser.error("Fresh project output or RAM path required")
    for p, digest in FROZEN.items():
        if sha(p) != digest:
            parser.error("Frozen native parent changed: " + str(p))
    tech = args.pdk.resolve() / "libs.tech"
    models = tech / "ngspice/models"
    inputs = [
        CIRCUIT,
        VCO,
        LATCH,
        Path(__file__).resolve(),
        args.ngspice.resolve(),
        args.openvaf.resolve(),
    ]
    inputs += sorted(models.glob("*.lib"))
    for folder in ("r3_cmc", "psp103"):
        inputs += sorted(
            p for p in (tech / "verilog-a" / folder).rglob("*") if p.is_file()
        )
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        inputs={str(p): sha(p) for p in inputs},
        limits=LIMITS,
        quick=args.quick,
        cases=[],
        pll_implemented=False,
        cdr_implemented=False,
        physical_qualification=False,
        model_compile_threads=1,
        simulation_address_space_limit_bytes=2 * 1024**3,
        scope="Original two-frozen-latch transistor toggle prescaler driven by actual frozen VCO; finite deterministic nominal screen with exploratory corners. No phase-noise/random-jitter/lock or full PCIe claim.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    try:
        save()
        (out / "spinit").write_text(
            "* Batch frontend; explicit recorded native models only.\nset num_threads=1\n"
        )
        osdi = []
        for folder, stem in [
            ("r3_cmc", "r3_cmc"),
            ("psp103", "psp103"),
            ("psp103", "psp103_nqs"),
        ]:
            binary = out / (stem + ".osdi")
            cmd = [
                str(args.openvaf.resolve()),
                str(tech / "verilog-a" / folder / (stem + ".va")),
                "-o",
                str(binary),
            ]
            with (out / (stem + "-compile.log")).open("w") as f:
                r = subprocess.run(
                    cmd,
                    env={**os.environ, "RAYON_NUM_THREADS": "1"},
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                    preexec_fn=limits,
                )
            if r.returncode or not binary.is_file():
                raise RuntimeError("Native model compile failed " + stem)
            osdi.append(binary)
        record["compiled_models"] = {str(p): sha(p) for p in osdi}
        for case in cases(args.quick):
            d = out / case["name"]
            d.mkdir()
            for p in (VCO, LATCH):
                (d / p.name).write_bytes(p.read_bytes())
            (d / CIRCUIT.name).write_text(circuit(case))
            (d / "bench.cir").write_text(deck(case, models, osdi))
            cmd = [str(args.ngspice.resolve()), "-n", "-b", "bench.cir"]
            entry = dict(case=case, command=cmd)
            record["cases"].append(entry)
            save()
            with (d / "run.log").open("w") as f:
                try:
                    r = subprocess.run(
                        cmd,
                        cwd=d,
                        env={**os.environ, "SPICE_SCRIPTS": str(out)},
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        timeout=180,
                        preexec_fn=limits,
                    )
                    entry["returncode"] = r.returncode
                except subprocess.TimeoutExpired:
                    entry.update(returncode=None, execution_failure="timeout")
            entry["numerical"] = diagnostics((d / "run.log").read_text())
            if entry.get("returncode") != 0 or not (d / "wave.dat").is_file():
                entry["execution_failure"] = entry.get(
                    "execution_failure", "missing complete native output"
                )
            else:
                try:
                    entry["measurement"] = measure(
                        read_wave(d / "wave.dat", case), case
                    )
                except (ValueError, KeyError, StopIteration) as exc:
                    entry["execution_failure"] = repr(exc)
            entry["expected_outcome_observed"] = expected_result(entry)
            if (d / "wave.dat").is_file():
                entry["uncompressed_wave_sha256"] = sha(d / "wave.dat")
                with (
                    (d / "wave.dat").open("rb") as inp,
                    gzip.open(d / "wave.dat.gz", "wb") as dst,
                ):
                    for block in iter(lambda: inp.read(1024 * 1024), b""):
                        dst.write(block)
                (d / "wave.dat").unlink()
            entry["outputs"] = {p.name: sha(p) for p in d.iterdir() if p.is_file()}
            save()
            print(
                case["name"],
                entry.get("measurement", {}).get("output_frequency_hz"),
                entry.get("expected_outcome_observed"),
                entry["numerical"]["clean"],
                flush=True,
            )
        if any(sha(Path(p)) != digest for p, digest in record["inputs"].items()):
            raise ValueError("Source/model/runtime changed during native run")
        required = [
            r for r in record["cases"] if r["case"]["role"] in ("required", "negative")
        ]
        good = all(
            r.get("expected_outcome_observed") is True
            and r["numerical"]["clean"]
            and not r.get("execution_failure")
            for r in required
        )
        n, h = (record["cases"][i].get("measurement", {}) for i in (0, 1))
        if n.get("input_frequency_hz") and h.get("input_frequency_hz"):
            record["half_step_frequency_relative_delta"] = (
                abs(n["output_frequency_hz"] / h["output_frequency_hz"] - 1)
                if n.get("output_frequency_hz") and h.get("output_frequency_hz")
                else None
            )
            good = (
                good
                and LIMITS["nominal_input_min_hz"]
                <= n["input_frequency_hz"]
                <= LIMITS["nominal_input_max_hz"]
                and record["half_step_frequency_relative_delta"] is not None
                and record["half_step_frequency_relative_delta"] < 0.001
            )
        else:
            good = False
        record["status"] = (
            "PASS_LIMITED_NATIVE_DIV2_NOMINAL_CORNERS_EXPLORATORY"
            if good
            else "FAIL_LIMITED_NATIVE_DIV2_SCREEN"
        )
    except BaseException as exc:
        record.update(status="ERROR", error=repr(exc))
    finally:
        save()
    print(record["status"])
    return 0 if record["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
