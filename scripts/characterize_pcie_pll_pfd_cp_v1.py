#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded native HV-CMOS PFD/pump characterization, not a closed PLL.

All DUT devices use original transistor topology and pinned IHP equations.
Clocks, supply and voltage clamps are explicitly external measurement fixtures.
Every native sample, including all MOS drain currents and terminal voltages,
is retained losslessly. Runs never convert numerical/runtime errors to negative
functional passes. Run at most two cases per preserved scratch batch.
"""

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "hw/soc/analog/pcie/pll_pfd_charge_pump_hv_v1.spice"
PDK = Path(
    "/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/"
    "c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2"
)
NG47_SHA = "eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8"
CIRCUIT_SHA = "194a50048f88614b3f3c0bbbac88cdf8be7f71a8cd62eac3f14914b652d865fc"
MODEL_INVENTORY_SHA = "3e8de67a2358fa6cf181705840b855c8aed08012ed3235e308f8db88feb712b3"
OSDI_PINS = {
    "r3_cmc.osdi": "9b41facf3c49d2266e542406547ed00677304f09c1dd281f3bf90414ee053828",
    "psp103.osdi": "e4a50ec48e3fab3aa7af76f1d0816863c8aa06223e0efcded362ddadb49681a8",
    "psp103_nqs.osdi": "523382d47f1f747c991a938b2f93cc6d9bab27ebf44f708c4e995820dc0bee88",
}
SCRATCH_CAP = 30 * 1024**2
SPACE_FLOOR = 512 * 1024**2
LIMITS = dict(
    max_mos_terminal_difference_v=3.3,
    max_abs_mos_drain_a_per_um=0.002,
    max_relative_zero_phase_charge_error=0.10,
    max_phase_width_error_ns=0.15,
    min_signed_pump_current_a=0.5e-6,
    max_reset_pump_current_a=0.5e-6,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


def atomic(path, record):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(path)


def cases():
    base = dict(
        lag_ns=2.0,
        control_v=1.25,
        supply_v=2.5,
        step_s=20e-12,
        stop_s=80e-9,
        ref_period_ns=10.0,
        fb_period_ns=10.0,
        missing="",
        reset="startup",
        load="clamp",
        mos="mos_tt",
        temp_c=27,
        fault="",
        role="positive",
    )
    variants = [
        ("lead", {}),
        ("lag", dict(lag_ns=-2.0)),
        ("zero", dict(lag_ns=0.0)),
        ("fine_lead", dict(lag_ns=0.25)),
        ("fine_lag", dict(lag_ns=-0.25)),
        ("zero_low", dict(lag_ns=0.0, control_v=0.9)),
        ("zero_high", dict(lag_ns=0.0, control_v=1.5)),
        ("reference_faster", dict(lag_ns=0.0, fb_period_ns=12.0)),
        ("feedback_faster", dict(lag_ns=0.0, fb_period_ns=8.0)),
        ("missing_feedback", dict(missing="fb")),
        ("missing_reference", dict(missing="ref")),
        ("reset_held", dict(reset="held")),
        ("reset_midstream", dict(reset="midstream")),
        ("finite_lead", dict(load="native_rc")),
        ("finite_lag", dict(load="native_rc", lag_ns=-2.0)),
        ("half_step_zero", dict(lag_ns=0.0, step_s=10e-12)),
    ]
    result = [dict(base, name=name, **changes) for name, changes in variants]
    for fault, lag in [
        ("swap_inputs", 2.0),
        ("no_common_reset", 2.0),
        ("no_source", 2.0),
        ("no_sink", -2.0),
        ("unbalanced_source", 0.0),
    ]:
        result.append(
            dict(base, name="fault_" + fault, fault=fault, lag_ns=lag, role="negative")
        )
    return result


def circuit(case):
    require(sha(CIRCUIT) == CIRCUIT_SHA, "Frozen original native circuit")
    text = CIRCUIT.read_text()
    changes = {
        "swap_inputs": ("XPFD ref fb reset up down", "XPFD fb ref reset up down"),
        "no_common_reset": ("XBOTH up down bothb", "XBOTH vss vss bothb"),
        "no_source": ("XCP up down cp avdd", "XCP avss down cp avdd"),
        "no_sink": ("XCP up down cp avdd", "XCP up avss cp avdd"),
        "unbalanced_source": (
            "XPSOURCE source pb vdd vdd sg13_hv_pmos w=6.4u",
            "XPSOURCE source pb vdd vdd sg13_hv_pmos w=8u",
        ),
    }
    if case["fault"]:
        require(case["fault"] in changes, "Known actual transistor mutation")
        old, new = changes[case["fault"]]
        require(text.count(old) == 1, "Exact native fault anchor")
        text = text.replace(old, new)
    return text


def device_contract(text):
    definitions, active = {}, None
    for line in text.lower().splitlines():
        words = line.split()
        if not words or words[0].startswith("*"):
            continue
        if words[0] == ".subckt":
            require(
                active is None and words[1] not in definitions,
                "Unique nonnested subcircuit",
            )
            active = words[1]
            definitions[active] = (words[2:], [])
        elif words[0] == ".ends":
            require(active is not None and words == [".ends", active], "Exact end")
            active = None
        else:
            require(active is not None, "No device outside source subcircuit")
            definitions[active][1].append(words)
    require(active is None, "Closed subcircuits")
    result = []

    def descend(name, path, nodes, stack=()):
        require(name not in stack, "No recursive circuit")
        formal, body = definitions[name]
        require(
            len(formal) == len(nodes) and len(set(formal)) == len(formal),
            "Exact circuit port binding",
        )
        binding, names = dict(zip(formal, nodes)), set()

        def node(n):
            require(re.fullmatch(r"[a-z][a-z0-9_]*", n), "Literal source node")
            return binding.get(n, path + "." + n)

        for words in body:
            require(
                re.fullmatch(r"x[a-z0-9_]+", words[0]) and words[0] not in names,
                "Unique native instance, no ideal devices",
            )
            names.add(words[0])
            here = path + "." + words[0]
            if words[-1] in definitions:
                descend(
                    words[-1], here, [node(n) for n in words[1:-1]], stack + (name,)
                )
                continue
            models = {"sg13_hv_nmos": 4, "sg13_hv_pmos": 4, "rppd": 3}
            found = [
                m for m, n in models.items() if len(words) > n + 1 and words[n + 1] == m
            ]
            require(len(found) == 1, "Only pinned native HV MOS and rppd")
            model, size = found[0], models[found[0]]
            pairs = [p.split("=") for p in words[size + 2 :]]
            require(all(len(p) == 2 for p in pairs), "Literal native parameters")
            params = dict(pairs)
            require(len(params) == len(pairs), "No duplicate parameter")
            needed = (
                {"w", "l", "b", "sw_et"} if model == "rppd" else {"w", "l", "ng", "m"}
            )
            require(set(params) == needed, "Exact native geometry fields")
            require(
                all(
                    re.fullmatch(r"[0-9]+(?:\.[0-9]+)?u", params[p]) for p in ("w", "l")
                ),
                "Literal micron geometry",
            )
            width, length = (float(params[p][:-1]) for p in ("w", "l"))
            if model == "rppd":
                require(
                    params["b"] == "0"
                    and params["sw_et"] == "1"
                    and (width, length) == (1.0, 80.0),
                    "Actual self-heated bias resistor",
                )
            else:
                require(
                    params["ng"] == params["m"] == "1"
                    and 0.3 <= width <= 10
                    and 0.45 <= length <= 10,
                    "Native model geometry range, no hidden multiplier",
                )
            result.append(
                dict(
                    path=here,
                    model=model,
                    nets=[node(n) for n in words[1 : size + 1]],
                    width_um=width,
                    length_um=length,
                    params=params,
                )
            )

    descend(
        "nssoc_pll_pfd_cp_hv_v1",
        "xdut",
        ["ref", "fb", "reset", "up", "down", "cp", "avdd", "0", "0"],
    )
    require(
        len(result) == 112
        and len({d["path"] for d in result}) == 112
        and Counter(d["model"] for d in result)["rppd"] == 1,
        "Exact112 native primitive census",
    )
    return result


def vectors(devices, case):
    nodes = sorted({n for d in devices for n in d["nets"]} - {"0"})
    result = ["v(" + n + ")" for n in nodes] + ["i(vdd)"]
    if case["load"] == "clamp":
        result.append("i(vclamp)")
    result += [
        "@n." + d["path"] + ".n" + d["model"] + "[ids]"
        for d in devices
        if d["model"] != "rppd"
    ]
    result.append("v(xdut.xcp.xrbias.dt)")
    if case["load"] == "native_rc":
        result += ["v(xloadhi.dt)", "v(xloadlo.dt)"]
    require(len(set(result)) == len(result), "Unique saved vectors")
    return result


def deck(case, models, osdi):
    require(case in cases(), "Exact predeclared finite case")
    v, period = case["supply_v"], case["ref_period_ns"]
    lines = ["Original NSSOC HV CMOS PFD and charge pump native test"]
    libs = [("MOShv", case["mos"]), ("RES", "res_typ")]
    if case["load"] == "native_rc":
        libs.append(("CAP", "cap_typ"))
    lines += [f'.lib "{models}/corner{name}.lib" {corner}' for name, corner in libs]
    lines += [
        f'.include "{CIRCUIT.name}"',
        f".temp {case['temp_c']}",
        ".options reltol=1e-4 abstol=1e-12",
        f"VDD avdd 0 PWL(0 0 1n {v})",
    ]
    for name, start, per in [
        ("ref", 10.0, period),
        ("fb", 10.0 + case["lag_ns"], case["fb_period_ns"]),
    ]:
        stimulus = (
            "0"
            if case["missing"] == name
            else (f"PULSE(0 {v} {start:g}n 100p 100p {per / 2 - 0.1:g}n {per:g}n)")
        )
        lines.append(f"V{name} {name} 0 {stimulus}")
    reset = f"PWL(0 0 1n {v} 5n {v} 5.1n 0)"
    if case["reset"] == "held":
        reset = f"PWL(0 0 1n {v})"
    elif case["reset"] == "midstream":
        reset = f"PWL(0 0 1n {v} 5n {v} 5.1n 0 44.9n 0 45n {v} 55n {v} 55.1n 0)"
    lines += [
        "VRST reset 0 " + reset,
        "XDUT ref fb reset up down cp avdd 0 0 nssoc_pll_pfd_cp_hv_v1",
    ]
    if case["load"] == "clamp":
        lines.append(f"VCLAMP cp 0 PWL(0 0 1n {case['control_v']})")
    else:
        lines += [
            "XLOADHI avdd cp 0 rppd w=1u l=80u b=0 sw_et=1",
            "XLOADLO cp 0 0 rppd w=1u l=80u b=0 sw_et=1",
            "XLOAD cp 0 cap_cmim w=20u l=20u",
        ]
    lines += [".control"] + ["pre_osdi " + str(p) for p in osdi]
    lines += [
        "set filetype=binary",
        "set numdgt=12",
        "save " + " ".join(vectors(device_contract(circuit(case)), case)),
        "op",
        "write op.raw all",
        f"tran {case['step_s']:.12g} {case['stop_s']:.12g} 0 {case['step_s']:.12g}",
        "write wave.raw all",
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def read_raw(path, expected, transient):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as stream:
        content = stream.read(SCRATCH_CAP + 1)
    require(
        len(content) <= SCRATCH_CAP and content.count(b"Binary:\n") == 1,
        "Bounded exact binary raw header",
    )
    raw_header, payload = content.split(b"Binary:\n", 1)
    header = raw_header.decode("ascii")
    require("Flags: real\n" in header, "Real native scalar capture")
    size = int(re.search(r"No\. Variables: (\d+)\n", header)[1])
    count = int(re.search(r"No\. Points: (\d+)\n", header)[1])
    require(
        count > 0 and len(payload) == size * count * 8, "Exact declared payload size"
    )
    names = []
    for index, line in enumerate(header.split("Variables:\n")[1].splitlines()):
        fields = line.split()
        require(
            len(fields) == 3 and int(fields[0]) == index, "Exact native variable table"
        )
        names.append(fields[1])
    expected = {"i(" + n + ")" if n.startswith("@") else n for n in expected}
    if transient:
        expected.add("time")
    require(
        len(names) == size == len(set(names)) and set(names) == expected,
        "Exact complete saved terminal/current inventory",
    )
    values = np.frombuffer(payload, dtype="<f8").reshape((count, size))
    require(np.isfinite(values).all(), "All finite native samples")
    return dict(zip(names, values.T))


def crossings(t, value, level):
    edges = []
    for i in range(1, len(t)):
        if value[i - 1] < level <= value[i]:
            edges.append(
                float(
                    t[i - 1]
                    + (t[i] - t[i - 1])
                    * (level - value[i - 1])
                    / (value[i] - value[i - 1])
                )
            )
    return edges


def integrate(t, values, left, right):
    require(t[0] <= left < right <= t[-1], "Complete integration interval")
    interior = (t > left) & (t < right)
    times = np.r_[left, t[interior], right]
    ys = np.r_[
        np.interp(left, t, values), values[interior], np.interp(right, t, values)
    ]
    return float(np.trapezoid(ys, times))


def active_time(t, value, level, left, right):
    # Exact piecewise-linear threshold crossing interpolation, not sample counting.
    interior = (t > left) & (t < right)
    ts = np.r_[left, t[interior], right]
    ys = np.r_[np.interp(left, t, value), value[interior], np.interp(right, t, value)]
    total = 0.0
    for a, b, va, vb in zip(ts[:-1], ts[1:], ys[:-1], ys[1:]):
        if va >= level and vb >= level:
            total += b - a
        elif (va >= level) != (vb >= level):
            edge = a + (b - a) * (level - va) / (vb - va)
            total += edge - a if va >= level else b - edge
    return float(total)


def measure(data, op, devices, case):
    t = data["time"]
    require(
        t[0] == 0
        and abs(t[-1] - case["stop_s"]) <= 4 * np.spacing(case["stop_s"])
        and np.all(np.diff(t) > 0)
        and np.max(np.diff(t)) <= case["step_s"] * (1 + 1e-8),
        "Complete time0-to-stop native bounded timestep",
    )
    require(
        all(len(v) == 1 and float(abs(v[0])) <= 1e-10 for v in op.values()),
        "Exact zero-source initial operating point",
    )
    electrical, density = [], []
    for dev in devices:
        if dev["model"] == "rppd":
            continue
        nodes = [
            data["v(" + n + ")"] if n != "0" else np.zeros_like(t) for n in dev["nets"]
        ]
        peak = max(float(np.max(abs(a - b))) for a in nodes for b in nodes)
        amps = data["i(@n." + dev["path"] + ".n" + dev["model"] + "[ids])"]
        current = float(np.max(abs(amps))) / dev["width_um"]
        electrical.append(dict(path=dev["path"], max_terminal_difference_v=peak))
        density.append(dict(path=dev["path"], max_abs_drain_a_per_um=current))
    safety = dict(
        all_mos_terminal_pairs_within_3p3v=all(
            d["max_terminal_difference_v"] <= LIMITS["max_mos_terminal_difference_v"]
            for d in electrical
        ),
        all_mos_peak_drain_density_within_design_limit=all(
            d["max_abs_drain_a_per_um"] <= LIMITS["max_abs_mos_drain_a_per_um"]
            for d in density
        ),
    )
    left, right = 20e-9, 70e-9
    if case["reset"] == "midstream":
        left, right = 60e-9, 70e-9
    up, down = data["v(up)"], data["v(down)"]
    tup = active_time(t, up, case["supply_v"] / 2, left, right)
    tdown = active_time(t, down, case["supply_v"] / 2, left, right)
    ip = data["i(@n.xdut.xcp.xpenable.nsg13_hv_pmos[ids])"]
    inn = data["i(@n.xdut.xcp.xnenable.nsg13_hv_nmos[ids])"]
    qp, qn = (integrate(t, values, left, right) for values in (ip, inn))
    net_current = integrate(
        t, data["i(vclamp)"] if case["load"] == "clamp" else ip - inn, left, right
    ) / (right - left)
    mismatch = abs(qp - qn) / ((abs(qp) + abs(qn)) / 2) if qp or qn else None
    mean_cp = integrate(t, data["v(cp)"], left, right) / (right - left)
    phases = dict(
        up_active_s=tup,
        down_active_s=tdown,
        active_difference_ns_per_period=(tup - tdown) / (right - left) * 10,
        source_charge_c=qp,
        sink_charge_c=qn,
        relative_charge_imbalance=mismatch,
        net_pump_a=net_current,
        mean_control_v=mean_cp,
    )
    functional = {}
    if case["reset"] == "held":
        functional.update(
            reset_outputs_low=max(
                float(up[(t >= left) & (t <= right)].max()),
                float(down[(t >= left) & (t <= right)].max()),
            )
            < 0.2,
            reset_pump_off=abs(net_current) <= LIMITS["max_reset_pump_current_a"],
        )
    else:
        sign = (
            1
            if case["missing"] == "fb" or case["fb_period_ns"] > 10
            else -1
            if case["missing"] == "ref" or case["fb_period_ns"] < 10
            else int(np.sign(case["lag_ns"]))
        )
        if case["missing"]:
            active, inactive = (tup, tdown) if sign > 0 else (tdown, tup)
            functional.update(
                missing_clock_correct_persistent_request=active > 0.98 * (right - left)
                and inactive < 0.01 * (right - left)
            )
        elif case["ref_period_ns"] == case["fb_period_ns"]:
            error = abs(phases["active_difference_ns_per_period"] - case["lag_ns"])
            functional["phase_width_difference_tracks_input"] = (
                error <= LIMITS["max_phase_width_error_ns"]
            )
            for name, value in [("up", up), ("down", down)]:
                edges = [
                    e
                    for e in crossings(t, value, case["supply_v"] / 2)
                    if left <= e < right
                ]
                functional[name + "_one_rise_each_reference_period"] = len(
                    edges
                ) == round((right - left) / 10e-9)
        else:
            functional["frequency_error_request_has_correct_direction"] = (
                sign * (tup - tdown) > 1e-9
            )
        if sign:
            functional["pump_current_correct_direction"] = (
                sign * net_current > LIMITS["min_signed_pump_current_a"]
            )
        else:
            functional["zero_phase_charge_balance"] = (
                mismatch is not None
                and mismatch <= LIMITS["max_relative_zero_phase_charge_error"]
            )
        if case["reset"] == "midstream":
            reset_mask = (t >= 47e-9) & (t <= 54e-9)
            functional["midstream_reset_outputs_clear"] = (
                float(max(up[reset_mask].max(), down[reset_mask].max())) < 0.2
            )
        if case["load"] == "native_rc":
            functional["finite_load_control_in_screened_range"] = 0.9 <= mean_cp <= 1.5
            functional["finite_load_moves_correctly_from_midrail"] = (
                sign * (mean_cp - case["supply_v"] / 2) > 0.015
            )
    return dict(
        window_s=[left, right],
        samples=len(t),
        zero_op=True,
        all_native_device_voltage_bounds=electrical,
        all_native_mos_currents=density,
        safety_checks=safety,
        phase_and_charge=phases,
        functional_checks=functional,
        safety_pass=all(safety.values()),
        functional_pass=all(functional.values()),
        average_supply_current_a=-integrate(t, data["i(vdd)"], left, right)
        / (right - left),
        resistor_thermal_max_k=float(data["v(xdut.xcp.xrbias.dt)"].max()),
        finite_test_only=True,
    )


def run_case(case, output, runtime, models, osdi):
    output = Path(output).resolve()
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh tmpfs output",
    )
    require(sha(runtime) == NG47_SHA, "Exact native ngspice47 runtime")
    model_pins = {p.name: sha(p) for p in sorted(Path(models).glob("*.lib"))}
    inventory = hashlib.sha256(
        json.dumps(model_pins, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    require(
        inventory == MODEL_INVENTORY_SHA,
        "Exact complete frozen native IHP model inventory",
    )
    require(
        {Path(p).name: sha(p) for p in osdi} == OSDI_PINS, "Exact native OSDI binaries"
    )
    require(
        shutil.disk_usage("/dev/shm").free >= SPACE_FLOOR + SCRATCH_CAP,
        "512MiB reserve plus bounded case space",
    )
    output.mkdir()
    text = circuit(case)
    devices = device_contract(text)
    (output / CIRCUIT.name).write_text(text)
    (output / "spinit").write_text("set num_threads=1\n")
    (output / "bench.cir").write_text(deck(case, models, osdi))
    inputs = {
        str(Path(p).resolve()): pin(p)
        for p in [
            __file__,
            CIRCUIT,
            runtime,
            *osdi,
            *Path(models).glob("*.lib"),
            output / CIRCUIT.name,
            output / "bench.cir",
            output / "spinit",
        ]
    }
    record = dict(
        status="RUNNING",
        case=case,
        inputs=inputs,
        limits=LIMITS,
        native_devices=devices,
        full_phy=False,
        closed_pll=False,
        model_soa_qualification=False,
    )
    atomic(output / "result.json", record)

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (25 * 1024**2, 25 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD")
    }
    env.update(SPICE_SCRIPTS=str(output), OMP_NUM_THREADS="1", RAYON_NUM_THREADS="1")
    process, start = None, time.monotonic()
    minimum = shutil.disk_usage("/dev/shm").free
    try:
        with (output / "run.log").open("x") as log:
            process = subprocess.Popen(
                [str(runtime), "-n", "-b", "bench.cir"],
                cwd=output,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=cap,
                start_new_session=True,
            )
            while process.poll() is None:
                minimum = min(minimum, shutil.disk_usage("/dev/shm").free)
                require(minimum >= SPACE_FLOOR, "Ongoing512MiB shared reserve")
                require(
                    sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
                    <= SCRATCH_CAP,
                    "30MiB native scratch cap",
                )
                time.sleep(0.1)
        record["execution"] = dict(
            returncode=process.returncode,
            seconds=time.monotonic() - start,
            min_free_bytes=minimum,
            address_space_cap_bytes=1024**3,
            elapsed_watchdog=None,
        )
        require(process.returncode == 0, "Actual native process completion")
        log = (output / "run.log").read_text()
        bad = [
            line
            for line in log.splitlines()
            if re.search(
                r"warning|error|failed|singular|timestep too small|gmin stepping|source stepping",
                line,
                re.I,
            )
        ]
        record["native_diagnostics"] = bad
        require(
            not bad and "ngspice-47 done" in log, "Clean complete native diagnostics"
        )
        expected = vectors(devices, case)
        op = read_raw(output / "op.raw", expected, False)
        data = read_raw(output / "wave.raw", expected, True)
        record["measurement"] = measure(data, op, devices, case)
        require(
            all(pin(p) == value for p, value in inputs.items()),
            "Unchanged all native inputs",
        )
        m = record["measurement"]
        record["status"] = (
            "PASS_NATIVE_FUNCTIONAL_NEGATIVE"
            if case["role"] == "negative"
            and m["safety_pass"]
            and not m["functional_pass"]
            else "PASS_NATIVE_PFD_CP_FINITE_SCREEN"
            if case["role"] == "positive" and m["safety_pass"] and m["functional_pass"]
            else "FAIL_NATIVE_PFD_CP_FINITE_SCREEN"
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_CAPTURE", error=repr(error))
        raise
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        record["outputs"] = {
            str(p.relative_to(output)): pin(p)
            for p in output.rglob("*")
            if p.is_file() and p.name != "result.json"
        }
        atomic(output / "result.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[c["name"] for c in cases()], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ngspice", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=PDK / "libs.tech/ngspice/models")
    parser.add_argument("--osdi-dir", type=Path, required=True)
    args = parser.parse_args()
    selected = next(c for c in cases() if c["name"] == args.case)
    result = run_case(
        selected,
        args.out,
        args.ngspice,
        args.models,
        [args.osdi_dir / n for n in ("r3_cmc.osdi", "psp103.osdi", "psp103_nqs.osdi")],
    )
    print(result["status"])
    return 0 if result["status"].startswith("PASS_NATIVE_") else 1


if __name__ == "__main__":
    sys.exit(main())
