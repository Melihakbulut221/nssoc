#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite native HBT /4 cascade experiment; no PLL or physical signoff."""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import statistics
import subprocess
import types

import characterize_pcie_div2 as old

ROOT = old.ROOT
CIRCUIT = ROOT / "hw/soc/analog/pcie/clock_div4_hbt.spice"
VCO = ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v3.spice"
CONDITIONER = ROOT / "hw/soc/analog/pcie/clock_div2_conditioned_hbt.spice"
PARENT_SHA = "eb479e0ef336532bd56cfc7e5677997394b920b7299573c41711e0d94088509d"
FROZEN = {
    VCO: "0d578a1392a13a9d61013eb5f0592515fccb112eddcee24f643f816b020f10f4",
    CONDITIONER: "6986c012843f603f7ab7769e951ae01314acdbc0c8e8fc62ce8b5c7a9af25ec3",
    old.CIRCUIT: "1b18a732c7736ad8c9805131c77fe1d5e467364ae8d6a2b7eb07061131cea4d7",
    old.LATCH: "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f",
    Path(
        old.__file__
    ): "8dd9818c28d3db09e550b41f70340ea196387bc40e7c691a2ec9f32ef50b28ce",
}
TOP = "nssoc_clock_div4_hbt"
END_S = 20e-9
CONDITIONERS = tuple("xdiv." + n for n in ("xsp", "xsn", "xdp", "xdn"))


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_sources():
    for path, digest in FROZEN.items():
        require(old.sha(path) == digest, "Frozen source changed: " + str(path))
    ports, rows = old.statements(CIRCUIT.read_text(), TOP)
    require(ports == "clkp clkn qp qn avdd avss sub".split(), "Exact top ports")
    require(
        rows
        == [
            s.split()
            for s in (
                "xfirst clkp clkn s1p s1n avdd avss sub nssoc_clock_div2_conditioned_hbt",
                "xsp s1p ckp sub rppd w=2u l=4u b=0 sw_et=1",
                "xsn s1n ckn sub rppd w=2u l=4u b=0 sw_et=1",
                "xdp ckp avss sub rppd w=1u l=3u b=0 sw_et=1",
                "xdn ckn avss sub rppd w=1u l=3u b=0 sw_et=1",
                "xcp s1p ckp cap_cmim w=10u l=10u",
                "xcn s1n ckn cap_cmim w=10u l=10u",
                "xsecond ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt",
            )
        ],
        "Exact two-core / real downward resistor topology",
    )


def cases(suite):
    positive = [dict(old.BASE, name="nominal")]
    if suite != "pilot":
        positive += [
            dict(old.BASE, name="half_step", step_s=0.5e-12),
            dict(old.BASE, name="cold_slow", hbt="hbt_wcs", temp=-40),
            dict(
                old.BASE, name="cold_fast", hbt="hbt_bcs", resistor="res_bcs", temp=-40
            ),
            dict(
                old.BASE, name="hot_slow", hbt="hbt_wcs", resistor="res_wcs", temp=125
            ),
            dict(old.BASE, name="hot_fast", hbt="hbt_bcs", temp=125),
            dict(old.BASE, name="slow_ramp", ramp_s=2e-9),
            dict(old.BASE, name="load100fF", output_load_f=100e-15),
        ]
    negative = [
        dict(old.BASE, name=f, fault=f, role="negative")
        for f in (
            "second_no_toggle",
            "second_same_phase",
            "second_no_bias",
            "second_same_clock",
        )
    ]
    require(suite in ("pilot", "finite", "negative"), "Unknown finite suite")
    return (
        negative
        if suite == "negative"
        else positive + (negative if suite == "finite" else [])
    )


def source_texts(case):
    top = CIRCUIT.read_text()
    core = old.CIRCUIT.read_text()
    fault = case["fault"]
    require(
        fault
        in (
            "",
            "second_no_toggle",
            "second_same_phase",
            "second_no_bias",
            "second_same_clock",
        ),
        "Unknown physical fault",
    )
    if fault == "second_same_clock":
        top = top.replace("XSECOND ckp ckn", "XSECOND ckp ckp")
    if fault in ("second_no_toggle", "second_same_phase", "second_no_bias"):
        altered = old.circuit(dict(case, fault=fault.removeprefix("second_")))
        altered = altered.replace("nssoc_clock_div2_hbt", "nssoc_clock_div2_fault_hbt")
        top = top.replace(
            "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt",
            "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_fault_hbt",
        )
        core += "\n" + altered
    return {
        VCO.name: VCO.read_text(),
        old.LATCH.name: old.LATCH.read_text(),
        old.CIRCUIT.name: core,
        CONDITIONER.name: CONDITIONER.read_text(),
        CIRCUIT.name: top,
    }


def device_contract(case):
    definitions = {}
    for text in source_texts(case).values():
        for name in re.findall(r"(?im)^\.subckt\s+(\S+)", text):
            require(name.lower() not in definitions, "Duplicate subcircuit")
            definitions[name.lower()] = old.statements(text, name)
    hbts, resistors, capacitors, mos = {}, [], [], []

    def walk(name, prefix, actual):
        ports, rows = definitions[name]
        require(len(ports) == len(actual), "Exact native port arity")
        bindings = dict(zip(ports, actual))
        node = lambda n: bindings.get(n, prefix + "." + n)
        for w in rows:
            require(w[0].startswith("x"), "Only real native devices/instances")
            path = prefix + "." + w[0]
            if len(w) > 5 and w[5] == "npn13g2":
                require(len(w) == 7 and w[6].startswith("nx="), "Explicit HBT geometry")
                nx = int(w[6][3:])
                require(path not in hbts and 1 <= nx <= 10, "HBT identity/model range")
                hbts[path] = (tuple(node(n) for n in w[1:4]), nx)
            elif len(w) > 4 and w[4] == "rppd":
                resistors.append(path)
            elif len(w) > 3 and w[3] == "cap_cmim":
                capacitors.append(path)
            elif len(w) > 5 and w[5] == "sg13_hv_pmos":
                mos.append(path)
            elif w[-1] in definitions:
                walk(w[-1], path, [node(n) for n in w[1:-1]])
            else:
                raise ValueError("Unrecognized physical statement: " + " ".join(w))

    walk("nssoc_clock_vco_hbt_v3", "xosc", ["clkp", "clkn", "vctrl", "avdd", "0", "0"])
    walk(TOP, "xdiv", ["clkp", "clkn", "qp", "qn", "dvdd", "0", "0"])
    require(
        len(hbts) == 60
        and len(set(resistors)) == len(resistors) == 35
        and len(capacitors) == 12
        and len(mos) == 1,
        "Complete actual native census",
    )
    return hbts, resistors


def electrical_vectors(case):
    hbts, resistors = device_contract(case)
    nets = {n for pins, _ in hbts.values() for n in pins} | {
        "clkp",
        "clkn",
        "qp",
        "qn",
        "avdd",
        "dvdd",
        "vctrl",
        "xdiv.s1p",
        "xdiv.s1n",
        "xdiv.ckp",
        "xdiv.ckn",
        "xdiv.xfirst.ckp",
        "xdiv.xfirst.ckn",
    }
    return (
        ["v(" + n + ")" for n in sorted(nets - {"0"})]
        + ["i(vdd)", "i(vddiv)", "i(vctrl)"]
        + ["@q." + n + ".qnpn13g2[ic]" for n in hbts]
        + ["v(" + n + ".t)" for n in hbts]
        + ["v(" + n + ".dt)" for n in resistors]
    )


def vectors(case):
    return electrical_vectors(case) + [
        "@n." + n + ".nr1[" + f + "]"
        for n in CONDITIONERS
        for f in ("r_dc", "ibody", "power")
    ]


def identities(case):
    return ["q." + n + ".qnpn13g2" for n in device_contract(case)[0]]


def deck(case, models, osdi):
    require(
        0 < case["step_s"] <= 1e-12 and 0 < case["ramp_s"] <= 2e-9, "Step/ramp contract"
    )
    lines = ["Real native VCO and two-stage HBT /4 cascade"]
    for kind, field in (
        ("HBT", "hbt"),
        ("RES", "resistor"),
        ("MOShv", "mos"),
        ("CAP", "cap"),
    ):
        lines.append(f'.lib "{models}/corner{kind}.lib" {case[field]}')
    lines += [f'.include "{n}"' for n in source_texts(case)]
    lines += [f".temp {case['temp']}", ".options reltol=1e-4 abstol=1e-12"]
    for name, node, voltage in (
        ("VDD", "avdd", case["supply"]),
        ("VDDIV", "dvdd", case["divider_supply"]),
        ("VCTRL", "vctrl", case["control"]),
    ):
        lines.append(f"{name} {node} 0 PWL(0 0 {case['ramp_s']:.12g} {voltage:.12g})")
    lines += [
        "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt_v3",
        "XDIV clkp clkn qp qn dvdd 0 0 " + TOP,
    ]
    for node, load in (
        ("clkp", case["clock_load_f"]),
        ("clkn", case["clock_load_f"]),
        ("qp", case["output_load_f"]),
        ("qn", case["output_load_f"]),
    ):
        lines.append(f"CLOAD_{node} {node} 0 {load:.12g}")
    vs = " ".join(vectors(case))
    lines += [".control"] + ["pre_osdi " + str(p) for p in osdi]
    lines += ["set wr_singlescale", "set wr_vecnames", "set numdgt=12", "save " + vs]
    for name in identities(case):
        lines += [
            f"alter @{name}[off] = 1",
            "echo NSSOC_DIV4_FLAG_BEGIN " + name,
            f"show {name} : off",
            "echo NSSOC_DIV4_FLAG_END",
        ]
    lines += [
        "op",
        "wrdata initial-op.dat " + " ".join(electrical_vectors(case)),
        f"tran {case['step_s']:.12g} {END_S:.12g} 0 {case['step_s']:.12g}",
        "wrdata wave.dat " + vs,
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def read_flags(log, case):
    rows = re.findall(
        r"(?ms)^NSSOC_DIV4_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_DIV4_FLAG_END\s*$", log
    )
    require(
        [n for n, _ in rows] == identities(case), "Exact60 actual native OFF identities"
    )
    for name, body in rows:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+(\S+)\s*$", body) == ["1"],
            "Native OFF readback",
        )
    return dict.fromkeys(identities(case), 1)


def initial_op(path, case):
    lines = path.read_text().splitlines()
    require(
        len(lines) == 2 and lines[0].split()[1:] == electrical_vectors(case),
        "Complete exact initial OP vectors",
    )
    values = list(map(float, lines[1].split()))
    require(
        len(values) == len(electrical_vectors(case)) + 1
        and all(math.isfinite(x) for x in values)
        and max(map(abs, values[1:])) <= 1e-10,
        "Finite zero electrical/thermal initial OP",
    )
    return dict(zip(electrical_vectors(case), values[1:]))


_read = types.FunctionType(
    old.read_wave.__code__, {**old.read_wave.__globals__, "vectors": vectors}
)


def read_wave(path, case):
    data = _read(path, case)
    require(data["time"][-1] >= END_S, "Complete20ns cascade observation")
    return data


def measure(data, case):
    hbts, resistors = device_contract(case)
    stages = {}
    for stage, prefix, cp, cn, qp, qn in (
        (
            "first",
            "xdiv.xfirst.",
            "xdiv.xfirst.ckp",
            "xdiv.xfirst.ckn",
            "xdiv.s1p",
            "xdiv.s1n",
        ),
        ("second", "xdiv.xsecond.", "xdiv.ckp", "xdiv.ckn", "qp", "qn"),
    ):
        selected_hbts = {n: p for n, p in hbts.items() if n.startswith(prefix)}
        selected_res = [n for n in resistors if n.startswith(prefix)]
        require(len(selected_hbts) == 15, "Exact15 HBT per stage")
        f = types.FunctionType(
            old.measure.__code__,
            {
                **old.measure.__globals__,
                "device_contract": lambda _: (selected_hbts, selected_res),
            },
        )
        view = dict(data)
        for alias, actual in (("clkp", cp), ("clkn", cn), ("qp", qp), ("qn", qn)):
            view["v(" + alias + ")"] = data["v(" + actual + ")"]
        stages[stage] = f(view, case)
    start = next(
        i for i, t in enumerate(data["time"]) if t >= old.LIMITS["observation_begin_s"]
    )

    def voltage(n):
        return [0.0] * len(data["time"]) if n == "0" else data["v(" + n + ")"]

    devices = {}
    for n, ((c, _, e), nx) in hbts.items():
        vce = [a - b for a, b in zip(voltage(c), voltage(e))]
        ic = data["@q." + n + ".qnpn13g2[ic]"]
        devices[n] = dict(
            nx=nx,
            min_settled_vce_v=min(vce[start:]),
            max_capture_vce_v=max(vce),
            min_capture_vce_v=min(vce),
            max_capture_ic_a_per_nx=max(map(abs, ic)) / nx,
            max_native_thermal_v=max(data["v(" + n + ".t)"]),
        )
    interfaces = {}
    for name, p, n in (
        ("vco", "clkp", "clkn"),
        ("first_input", "xdiv.xfirst.ckp", "xdiv.xfirst.ckn"),
        ("first_output", "xdiv.s1p", "xdiv.s1n"),
        ("second_input", "xdiv.ckp", "xdiv.ckn"),
        ("second_output", "qp", "qn"),
    ):
        pairs = list(zip(voltage(p)[start:], voltage(n)[start:]))
        diff = [a - b for a, b in pairs]
        cm = [(a + b) / 2 for a, b in pairs]
        interfaces[name] = dict(
            diff_range_v=[min(diff), max(diff)], common_mode_range_v=[min(cm), max(cm)]
        )
    time = data["time"][start:]
    ck = [a - b for a, b in zip(voltage("clkp")[start:], voltage("clkn")[start:])]
    q = [a - b for a, b in zip(voltage("qp")[start:], voltage("qn")[start:])]
    iu = old.crossings(time, ck)
    ou = old.crossings(time, q)
    edgecounts = [sum(a < x < b for x in iu) for a, b in zip(ou, ou[1:])]
    ratio = (
        statistics.mean(b - a for a, b in zip(ou, ou[1:]))
        / (4 * statistics.mean(b - a for a, b in zip(iu, iu[1:])))
        if len(iu) > 1 and len(ou) > 1
        else None
    )
    checks = dict(
        first_divide=stages["first"]["functional_divide_pass"],
        second_divide=stages["second"]["functional_divide_pass"],
        exactly_four_input_periods=bool(edgecounts) and all(x == 4 for x in edgecounts),
        period_ratio=ratio is not None
        and abs(ratio - 1) < old.LIMITS["max_period_ratio_error"],
        vco_swing=min(max(ck), -min(ck)) >= 0.3,
        settled_headroom=all(
            x["min_settled_vce_v"] >= old.LIMITS["min_vce_v"] for x in devices.values()
        ),
        full_capture_maximum_vce=all(
            x["max_capture_vce_v"] <= old.LIMITS["max_vce_v"] for x in devices.values()
        ),
        full_capture_current_density=all(
            x["max_capture_ic_a_per_nx"] < old.LIMITS["max_ic_a_per_nx"]
            for x in devices.values()
        ),
    )
    conditioning = {
        n: {
            field: dict(
                min=min(data["@n." + n + ".nr1[" + field + "]"][start:]),
                max=max(data["@n." + n + ".nr1[" + field + "]"][start:]),
                mean=statistics.mean(data["@n." + n + ".nr1[" + field + "]"][start:]),
            )
            for field in ("r_dc", "ibody", "power")
        }
        for n in CONDITIONERS
    }
    checks["positive_model_resistance"] = all(
        x["r_dc"]["min"] > 0 for x in conditioning.values()
    )
    input_frequency = (
        1 / statistics.mean(b - a for a, b in zip(iu, iu[1:])) if len(iu) > 1 else None
    )
    output_frequency = (
        1 / statistics.mean(b - a for a, b in zip(ou, ou[1:])) if len(ou) > 1 else None
    )
    if case["name"] in ("nominal", "half_step"):
        checks["nominal_vco_frequency"] = (
            input_frequency is not None
            and old.LIMITS["nominal_input_min_hz"]
            <= input_frequency
            <= old.LIMITS["nominal_input_max_hz"]
        )
    return dict(
        stages=stages,
        interfaces=interfaces,
        devices=devices,
        conditioners=conditioning,
        checks=checks,
        screen_pass=all(checks.values()),
        functional_divide_pass=all(
            checks[n]
            for n in (
                "first_divide",
                "second_divide",
                "exactly_four_input_periods",
                "period_ratio",
            )
        ),
        input_edges_per_output_period=edgecounts,
        input_frequency_hz=input_frequency,
        output_frequency_hz=output_frequency,
        period_ratio_to_exact_four=ratio,
        mean_vco_supply_power_w=statistics.mean(
            -v * i for v, i in zip(voltage("avdd")[start:], data["i(vdd)"][start:])
        ),
        mean_two_divider_supply_power_w=statistics.mean(
            -v * i for v, i in zip(voltage("dvdd")[start:], data["i(vddiv)"][start:])
        ),
        resistor_max_selfheat_k={n: max(data["v(" + n + ".dt)"]) for n in resistors},
    )


def accepted(row):
    case = row["case"]
    measurement = row.get("measurement", {})
    if (
        row.get("returncode") != 0
        or row.get("execution_failure")
        or row.get("numerical", {}).get("clean") is not True
        or row.get("flags_observed") != dict.fromkeys(identities(case), 1)
    ):
        return False
    op = row.get("zero_initial_op", {})
    if set(op) != set(electrical_vectors(case)) or not all(
        math.isfinite(x) and abs(x) <= 1e-10 for x in op.values()
    ):
        return False
    if case["fault"]:
        stages = measurement.get("stages", {})
        return (
            stages.get("first", {}).get("functional_divide_pass") is True
            and stages.get("second", {}).get("functional_divide_pass") is False
            and measurement.get("functional_divide_pass") is False
        )
    return measurement.get("screen_pass") is True


def atomic(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


def run(parent, out, suite):
    parent, out = Path(parent).resolve(), Path(out).resolve()
    require(
        not out.exists() and out.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output required",
    )
    verify_sources()
    require(old.sha(parent / "result.json") == PARENT_SHA, "Exact native model parent")
    prior = json.loads((parent / "result.json").read_text())
    pins = {**prior["inputs"], **prior["compiled_models"]}
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                *FROZEN,
                CIRCUIT,
                Path(__file__).resolve(),
                parent / "result.json",
            )
        }
    )
    for p, h in pins.items():
        require(old.sha(Path(p)) == h, "Input changed:" + p)
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    require(len(runtime) == len(models) == 1, "Unique pinned native runtime/model")
    out.mkdir()
    (out / "spinit").write_text("* Explicit native models only.\nset num_threads=1\n")
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        suite=suite,
        cases=[],
        limits={**old.LIMITS, "observation_end_s": END_S},
        observation_window_s=[4e-9, END_S],
        hbt_count=60,
        resistor_count=35,
        capacitor_count=12,
        mos_count=1,
        qualified_pex=False,
        pll_implemented=False,
        scope=__doc__,
        limitations=[
            "Finite schematic cases only; no full Cartesian PVT, mismatch, jitter, extracted RC or layout qualification.",
            "Per-stage common mode is observed at actual pins; safe acceptance requires all60 actual HBT VCE/current limits, rather than an ideal level shifter or prescribed clock state.",
            "The0.4V minimum VCE is a4–20ns operating guard; maximum1.6V and3mA/Nx are checked across the full0–20ns capture.",
            "Two native10x10um MIM feed-forward capacitors alter AC loading while four real rppd devices establish second-stage DC bias. Physical capacitor/resistor parasitics remain unextracted.",
        ],
    )

    def save():
        atomic(out / "result.json", result)

    def bound():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    save()
    try:
        for case in cases(suite):
            require(
                shutil.disk_usage(out).free > 220 * 1024**2,
                "Need220MiB free for bounded native wave",
            )
            folder = out / case["name"]
            folder.mkdir()
            for name, text in source_texts(case).items():
                (folder / name).write_text(text)
            (folder / "bench.cir").write_text(
                deck(case, models[0], [Path(p) for p in prior["compiled_models"]])
            )
            row = dict(case=case, command=[str(runtime[0]), "-n", "-b", "bench.cir"])
            result["cases"].append(row)
            save()
            with (folder / "run.log").open("w") as log:
                try:
                    execution = subprocess.run(
                        row["command"],
                        cwd=folder,
                        env={**os.environ, "SPICE_SCRIPTS": str(out)},
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=240,
                        preexec_fn=bound,
                    )
                    row["returncode"] = execution.returncode
                except subprocess.TimeoutExpired:
                    row.update(returncode=None, execution_failure="timeout")
            log = (folder / "run.log").read_text()
            row["numerical"] = old.diagnostics(log)
            try:
                require(row.get("returncode") == 0, "Native execution failed")
                row["flags_observed"] = read_flags(log, case)
                row["zero_initial_op"] = initial_op(folder / "initial-op.dat", case)
                row["measurement"] = measure(read_wave(folder / "wave.dat", case), case)
            except (ValueError, KeyError, OSError, StopIteration) as exc:
                row["execution_failure"] = row.get("execution_failure", repr(exc))
            m = row.get("measurement", {})
            row["expected_outcome_observed"] = accepted(row)
            wave = folder / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                with (
                    wave.open("rb") as src,
                    gzip.open(folder / "wave.dat.gz", "wb", compresslevel=3) as dst,
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
                [k for k, v in m.get("checks", {}).items() if not v],
                flush=True,
            )
        for p, h in pins.items():
            require(old.sha(Path(p)) == h, "Input changed after native:" + p)
        result["complete_inputs_rechecked"] = True
        good = all(r["expected_outcome_observed"] for r in result["cases"])
        if suite == "finite":
            measured = {
                r["case"]["name"]: r.get("measurement", {}) for r in result["cases"]
            }
            a = measured["nominal"].get("output_frequency_hz")
            b = measured["half_step"].get("output_frequency_hz")
            delta = abs(a / b - 1) if a and b else None
            result["half_step_frequency_relative_delta"] = delta
            good &= delta is not None and delta < 0.001
        result["status"] = "PASS_FINITE_DIV4_SCREEN" if good else "FAIL_PRESERVED"
    except BaseException as exc:
        result.update(status="ERROR_PRESERVED", error=repr(exc))
    finally:
        save()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--suite", choices=("pilot", "finite", "negative"), default="pilot")
    args = p.parse_args()
    r = run(args.parent, args.out, args.suite)
    print(r["status"])
    return 0 if r["status"] == "PASS_FINITE_DIV4_SCREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
