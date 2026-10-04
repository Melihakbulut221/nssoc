#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native transistor VCO experiment, not a PLL/CDR or jitter qualification.

All rails start at zero and ramp together. No periodic source, initial-condition
override or behavioral gain/delay is used. Save every measured timepoint, retain
failed runs, and report numerical diagnostics independently of oscillation.
"""

import argparse
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "hw/soc/analog/pcie/clock_vco_hbt.spice"
BASE = dict(hbt="hbt_typ", resistor="res_typ", mos="mos_tt", cap="cap_typ",
            temp=27, supply=2.3, control=0.85, load_f=50e-15, ramp_s=500e-12,
            step_s=1e-12, fault="", role="exploration")
LIMITS = dict(min_edges=30, min_diff_peak_v=0.3, min_frequency_hz=1e9,
              max_frequency_hz=20e9, max_period_spread=0.005,
              min_duty=0.4, max_duty=0.6, min_vce_v=0.4,
              max_vce_v=1.6, max_collector_a_per_emitter=0.003)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cases(quick=False):
    result = [dict(BASE, name="nominal", role="required"),
              dict(BASE, name="half_step", step_s=0.5e-12, role="required")]
    result += [dict(BASE, name=f"control_{v:.2f}", control=v)
               for v in ((0.7, 1.0, 1.2) if quick else (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3))]
    if not quick:
        result += [dict(BASE, name=f"{h}_{m}_{t}", hbt=h, mos=m, temp=t)
                   for h, m, t in itertools.product(
                       ("hbt_typ", "hbt_bcs", "hbt_wcs"),
                       ("mos_tt", "mos_ff", "mos_ss"), (-40, 27, 125))]
        result += [dict(BASE, name=f"{r}_{c}_{v}", resistor=r, cap=c, supply=v)
                   for r, c, v in itertools.product(
                       ("res_typ", "res_bcs", "res_wcs"),
                       ("cap_typ", "cap_bcs", "cap_wcs"), (2.185, 2.3, 2.415))]
    result += [dict(BASE, name=f"load_{v:g}fF", load_f=v * 1e-15) for v in (100, 150)]
    result += [dict(BASE, name=f"ramp_{v:g}ns", ramp_s=v * 1e-9) for v in (0.1, 2)]
    result += [dict(BASE, name=f, fault=f, role="negative")
               for f in ("no_bias", "no_feedback", "same_clock", "overload")]
    return result


def device_contract(text):
    hbts, resistors = {}, []
    for line in text.splitlines():
        words = line.lower().split()
        if len(words) >= 7 and words[5] == "npn13g2":
            hbts[words[0]] = (words[1:4], int(words[6].split("=")[1]))
        if len(words) >= 5 and words[4] == "rppd":
            resistors.append(words[0])
    if len(hbts) != 18 or len(resistors) != 9:
        raise ValueError("Native device inventory changed")
    return hbts, resistors


def circuit(case):
    text = CIRCUIT.read_text()
    edits = {
        "no_feedback": [("XP0 p0 p2 t0", "XP0 p0 p0 t0"),
                        ("XN0 n0 n2 t0", "XN0 n0 n0 t0")],
        "same_clock": [("XFN avdd bo_n clkn", "XFN avdd bo_p clkn")],
    }
    for old, new in edits.get(case["fault"], []):
        if text.count(old) != 1:
            raise ValueError("Native mutation anchor changed")
        text = text.replace(old, new)
    return text


def vectors():
    hbts, resistors = device_contract(CIRCUIT.read_text())
    nets = {n for terminals, _ in hbts.values() for n in terminals}
    def net(n):
        return "0" if n == "avss" else n if n in ("avdd", "clkp", "clkn") else "xosc." + n
    nodes = sorted({net(n) for n in nets} - {"0"})
    return (["v(" + n + ")" for n in nodes] + ["v(vctrl)", "i(vdd)", "i(vctrl)"]
            + ["@q.xosc." + n + ".qnpn13g2[ic]" for n in hbts]
            + ["v(xosc." + n + ".dt)" for n in resistors])


def deck(case, models, osdi):
    if case["step_s"] <= 0 or not 0 < case["ramp_s"] <= 2e-9:
        raise ValueError("Unsupported timestep/startup ramp")
    vctrl = case["supply"] if case["fault"] == "no_bias" else case["control"]
    load = 100e-12 if case["fault"] == "overload" else case["load_f"]
    text = ["NSSOC original native voltage-controlled CML ring experiment"]
    for file, corner in (("HBT", case["hbt"]), ("RES", case["resistor"]),
                         ("MOShv", case["mos"]), ("CAP", case["cap"])):
        text.append(f'.lib "{models}/corner{file}.lib" {corner}')
    text += [f'.include "{CIRCUIT.name}"', f'.temp {case["temp"]}',
             ".options reltol=1e-4 abstol=1e-12",
             f'VDD avdd 0 PWL(0 0 {case["ramp_s"]:.12g} {case["supply"]:.12g})',
             f'VCTRL vctrl 0 PWL(0 0 {case["ramp_s"]:.12g} {vctrl:.12g})',
             "XOSC clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt",
             f"CLOADP clkp 0 {load:.12g}", f"CLOADN clkn 0 {load:.12g}", ".control"]
    text += ["pre_osdi " + str(p) for p in osdi]
    text += ["set wr_singlescale", "set wr_vecnames", "set numdgt=12",
             "save " + " ".join(vectors()),
             f'tran {case["step_s"]:.12g} 12n 0 {case["step_s"]:.12g}',
             "wrdata wave.dat " + " ".join(vectors()), "quit", ".endc", ".end"]
    return "\n".join(text) + "\n"


def read_wave(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        header = f.readline().split()
        expected = ["time", *vectors()]
        if header != expected:
            raise ValueError("Native time/vector order changed")
        data = {name: [] for name in header}
        for line in f:
            row = [float(v) for v in line.split()]
            if len(row) != len(header) or not all(math.isfinite(v) for v in row):
                raise ValueError("Incomplete/nonfinite native row")
            for name, value in zip(header, row):
                data[name].append(value)
    times = data["time"]
    if len(times) < 1000 or times[-1] < 12e-9 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Missing or nonmonotonic native time coverage")
    return data


def crossings(times, volts, positive=True):
    out = []
    for i in range(1, len(times)):
        a, b = volts[i-1], volts[i]
        if (a <= 0 < b) if positive else (a >= 0 > b):
            out.append(times[i-1] + (times[i] - times[i-1]) * (-a) / (b - a))
    return out


def measure(data):
    begin = next(i for i, t in enumerate(data["time"]) if t >= 4e-9)
    active = {n: v[begin:] for n, v in data.items()}
    time = active["time"]
    diff = [p - n for p, n in zip(active["v(clkp)"], active["v(clkn)"])]
    up, down = crossings(time, diff), crossings(time, diff, False)
    periods = [b - a for a, b in zip(up, up[1:])]
    duty = []
    edge_order_errors = 0
    for a, b in zip(up, up[1:]):
        fall = [t for t in down if a < t < b]
        if len(fall) != 1:
            edge_order_errors += 1
            continue
        duty.append((fall[0] - a) / (b - a))
    hbts, _ = device_contract(CIRCUIT.read_text())
    def volt(net):
        if net == "avss":
            return [0.] * len(time)
        name = net if net in ("avdd", "clkp", "clkn") else "xosc." + net
        return active["v(" + name + ")"]
    devices = {}
    for name, ((collector, _, emitter), nx) in hbts.items():
        vce = [a - b for a, b in zip(volt(collector), volt(emitter))]
        current = active["@q.xosc." + name + ".qnpn13g2[ic]"]
        devices[name] = dict(nx=nx, min_vce_v=min(vce), max_vce_v=max(vce),
                             max_abs_ic_a=max(abs(i) for i in current))
    mean_period = statistics.mean(periods) if periods else None
    frequency = 1 / mean_period if mean_period else None
    spread = (max(periods) - min(periods)) / mean_period if mean_period else None
    checks = dict(
        edges=len(up) >= LIMITS["min_edges"],
        edge_order=edge_order_errors == 0,
        differential_swing=min(max(diff), -min(diff)) >= LIMITS["min_diff_peak_v"],
        frequency=frequency is not None and LIMITS["min_frequency_hz"] <= frequency <= LIMITS["max_frequency_hz"],
        deterministic_period_spread=spread is not None and spread < LIMITS["max_period_spread"],
        duty=bool(duty) and min(duty) >= LIMITS["min_duty"] and max(duty) <= LIMITS["max_duty"],
        headroom=all(x["min_vce_v"] >= LIMITS["min_vce_v"] for x in devices.values()),
        maximum_vce=all(x["max_vce_v"] <= LIMITS["max_vce_v"] for x in devices.values()),
        current_density=all(x["max_abs_ic_a"] < x["nx"] * LIMITS["max_collector_a_per_emitter"] for x in devices.values()),
    )
    return dict(rows=len(data["time"]), rising_edges=len(up), frequency_hz=frequency,
                edge_order_errors=edge_order_errors,
                min_diff_v=min(diff), max_diff_v=max(diff), period_spread=spread,
                duty_range=[min(duty), max(duty)] if duty else None,
                mean_common_mode_v=statistics.mean((a+b)/2 for a, b in zip(active["v(clkp)"], active["v(clkn)"])),
                mean_supply_power_w=statistics.mean(-v*i for v, i in zip(active["v(avdd)"], active["i(vdd)"])),
                devices=devices, checks=checks, screen_pass=all(checks.values()))


def diagnostics(log):
    tokens = ("warning", "error", "nan", "singular", "stepping", "timestep too small", "aborted")
    lines = [line for line in log.splitlines() if any(t in line.lower() for t in tokens)]
    return dict(clean=not lines, lines=lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "ngspice", "openvaf", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(ROOT / "hw/soc/out") or out.is_relative_to(Path("/dev/shm"))):
        ap.error("Fresh project-output or RAM directory required")
    tech = args.pdk.resolve() / "libs.tech"
    inputs = [CIRCUIT, Path(__file__).resolve(), args.ngspice.resolve(), args.openvaf.resolve()]
    inputs += sorted((tech / "ngspice/models").glob("*.lib"))
    for folder in ("r3_cmc", "psp103"):
        inputs += sorted(p for p in (tech / "verilog-a" / folder).rglob("*") if p.is_file())
    out.mkdir(parents=True)
    record = dict(status="RUNNING", source_sha256={str(p): sha(p) for p in inputs},
                  limits=LIMITS, quick=args.quick, cases=[], pcie_compliance=False,
                  pll_implemented=False, cdr_implemented=False, physical_qualification=False,
                  scope="Native open-loop transistor VCO with external control voltage and coordinated zero-source startup. Deterministic finite transients; period spread is not random jitter, phase noise, lock or recovered-clock performance.")
    def save():
        (out / "result.tmp").write_text(json.dumps(record, indent=2) + "\n")
        (out / "result.tmp").replace(out / "result.json")
    try:
        save()
        (out / "spinit").write_text("* Explicit batch frontend; all models are loaded by the recorded deck.\nset num_threads=1\n")
        osdi = []
        for folder, stem in (("r3_cmc", "r3_cmc"), ("psp103", "psp103"), ("psp103", "psp103_nqs")):
            binary = out / (stem + ".osdi")
            cmd = [str(args.openvaf.resolve()), str(tech / "verilog-a" / folder / (stem + ".va")), "-o", str(binary)]
            with (out / (stem + "-compile.log")).open("w") as log:
                result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            if result.returncode or not binary.is_file():
                raise RuntimeError("Native model compilation failed: " + stem)
            osdi.append(binary)
        record["compiled_models"] = {str(p): sha(p) for p in osdi}
        for case in cases(args.quick):
            directory = out / case["name"]
            directory.mkdir()
            (directory / CIRCUIT.name).write_text(circuit(case))
            (directory / "bench.cir").write_text(deck(case, tech / "ngspice/models", osdi))
            cmd = [str(args.ngspice.resolve()), "-n", "-b", "bench.cir"]
            with (directory / "run.log").open("w") as log:
                run = subprocess.run(cmd, cwd=directory, env=dict(os.environ, SPICE_SCRIPTS=str(out)), stdout=log, stderr=subprocess.STDOUT, timeout=180)
            entry = dict(case=case, command=cmd, returncode=run.returncode,
                         numerical=diagnostics((directory / "run.log").read_text()))
            record["cases"].append(entry)
            if run.returncode or not (directory / "wave.dat").is_file():
                entry["execution_failure"] = True
            else:
                entry["measurement"] = measure(read_wave(directory / "wave.dat"))
                entry["expected_outcome_observed"] = entry["measurement"]["screen_pass"] != bool(case["fault"])
                with (directory / "wave.dat").open("rb") as source, gzip.open(directory / "wave.dat.gz", "wb") as target:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        target.write(block)
                entry["uncompressed_wave_sha256"] = sha(directory / "wave.dat")
                (directory / "wave.dat").unlink()
            entry["outputs"] = {p.name: sha(p) for p in directory.iterdir() if p.is_file()}
            save()
            print(case["name"], entry.get("measurement", {}).get("frequency_hz"), entry.get("expected_outcome_observed"), entry["numerical"]["clean"], flush=True)
        if any(sha(Path(p)) != h for p, h in record["source_sha256"].items()):
            raise RuntimeError("Source/model/runtime changed during native campaign")
        required = [r for r in record["cases"] if r["case"]["role"] in ("required", "negative")]
        good = all(r.get("expected_outcome_observed") is True and r["numerical"]["clean"] for r in required)
        nominal, half = (record["cases"][i]["measurement"] for i in (0, 1))
        record["timestep_frequency_relative_delta"] = abs(nominal["frequency_hz"] / half["frequency_hz"] - 1)
        good = good and record["timestep_frequency_relative_delta"] < 0.001
        record["status"] = "PASS_LIMITED_NOMINAL_VCO_SCREEN_CORNERS_EXPLORATORY" if good else "FAIL_LIMITED_NOMINAL_VCO_SCREEN"
    except BaseException as exc:
        record.update(status="ERROR", error=repr(exc))
        raise
    finally:
        save()
    return 0 if record["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
