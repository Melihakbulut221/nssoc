#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native rppd pole/DC calibration; does not certify the oscillator steady state."""

import argparse
import hashlib
import json
import lzma
import math
import os
from pathlib import Path
import re
import shutil

import characterize_pcie_clock_trim_thermal_v1 as thermal

old = thermal.old
require = thermal.require
THERMAL_SHA = "663d50d2f7efd2f611792d305ce03813f8c1d0ca1f21fd0d52866adb801aa324"
RESULT_SHA = "04a1a8aea7c498633baaaaf34606df794a306dee3ee59525959e97e75bf6e1c8"
RES_SHA = "98fa5436f6df86dc1dd35e9f16383c4eba4c36d478d7eec203a0295dc1259e51"
VA_SHA = "398746f45048a9e075913e85a982258b929c9042257339bf1fc47d7e25303551"
FIELDS = ("rth", "cth", "power")
TIME_S = 1e-6
STEP_S = 1e-10
DC_RELATIVE_LIMIT = 1e-4
ENERGY_RELATIVE_LIMIT = 1e-4


def geometries():
    text = thermal.circuit(thermal.cases()[0])
    rows = []
    for line in text.splitlines():
        if " rppd " not in line:
            continue
        match = re.fullmatch(
            r"(\w+) \w+ \w+ sub rppd w=([0-9.]+)u l=([0-9.]+)u b=0 sw_et=1", line
        )
        require(match is not None, "Exact canonical native resistor source")
        name, w, l = match.groups()
        rows.append(dict(name=name.lower(), w_um=float(w), l_um=float(l)))
    require(len(rows) == 23, "All23 unchanged oscillator resistors")
    unique = sorted({(r["w_um"], r["l_um"]) for r in rows})
    require(len(unique) == 5, "Exact five source geometries")
    return rows, unique


def pole(w, l):
    # Wrapper W=w+0.006um, L=l for b=0. r3 thermal area uses drawn L,W,
    # before electrical mismatch adjustments. c1=c2=1; tegth defaults0.
    width = w + 0.006
    area = width * l
    perimeter = 2 * l + 2 * width
    g = 1e-12 + 6e-6 * area + 2e-6 * perimeter + 2e-12
    c = 594e-15 * area
    return dict(
        area_um2=area,
        perimeter_um=perimeter,
        conductance_w_per_k=g,
        capacitance_j_per_k=c,
        resistance_k_per_w=1 / g,
        tau_s=c / g,
    )


def observations(count):
    return ["v(a)", "i(vdd)"] + [
        v
        for i in range(count)
        for v in (f"v(xr{i}.dt)", *(f"@n.xr{i}.nr1[{f}]" for f in FIELDS))
    ]


def deck(models, osdi, variant):
    require(
        variant in ("cold", "dc", "selfheat_off", "wrong_geometry"),
        "Explicit bounded controls",
    )
    _, shapes = geometries()
    source = "DC 1.2" if variant == "dc" else "PWL(0 0 0.5n 1.2)"
    lines = [
        "Native exact rppd thermal pole and energy calibration",
        f'.lib "{models}/cornerRES.lib" res_bcs',
        f"VDD a 0 {source}",
    ]
    for i, (w, l) in enumerate(shapes):
        if i == 0 and variant == "wrong_geometry":
            w *= 2
        lines.append(
            f"XR{i} a 0 0 rppd w={w:g}u l={l:g}u b=0 sw_et={0 if variant == 'selfheat_off' else 1}"
        )
    vs = " ".join(observations(len(shapes)))
    lines += [
        ".options reltol=1e-4 abstol=1e-12",
        ".control",
        f"pre_osdi {osdi}",
        "set numdgt=12",
        "set wr_vecnames",
        "set wr_singlescale",
        "save " + vs,
        "op",
        "wrdata initial-op.dat " + vs,
    ]
    if variant != "dc":
        lines += ["tran .1n 1u 0 .1n"]
    lines += ["wrdata result.dat " + vs, "quit", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def read(path, dc=False):
    lines = Path(path).read_text().splitlines()
    head = lines[0].split()
    require(
        head == [("a" if dc else "time"), *observations(5)],
        "Exact native observations",
    )
    rows = [[float(x) for x in line.split()] for line in lines[1:]]
    require(
        bool(rows)
        and all(len(r) == len(head) and all(map(math.isfinite, r)) for r in rows),
        "Complete finite native rows",
    )
    if dc:
        require(len(rows) == 1, "Exactly one native DC point")
    else:
        ts = [r[0] for r in rows]
        require(
            len(ts) > 1000 and ts[0] == 0 and TIME_S <= ts[-1] <= TIME_S + 1e-16,
            "Full cold-start1us trajectory",
        )
        require(
            all(0 < b - a <= STEP_S * 1.0001 for a, b in zip(ts, ts[1:])),
            "Time grid differs",
        )
    return dict(zip(head[1:], [[r[i] for r in rows] for i in range(1, len(head))])), [
        r[0] for r in rows
    ]


def audit(data, times, dc):
    _, shapes = geometries()
    rows = []
    for i, (w, l) in enumerate(shapes):
        expected = pole(w, l)
        theta = data[f"v(xr{i}.dt)"]
        power = data[f"@n.xr{i}.nr1[power]"]
        rth = data[f"@n.xr{i}.nr1[rth]"]
        cth = data[f"@n.xr{i}.nr1[cth]"]
        require(
            all(abs(r / expected["resistance_k_per_w"] - 1) <= 1e-10 for r in rth),
            "Native rth/geometry differs",
        )
        require(
            all(abs(c / expected["capacitance_j_per_k"] - 1) <= 1e-10 for c in cth),
            "Native cth/geometry differs",
        )
        require(theta[0] == 0 and power[0] == 0, "Exact zero-source cold thermal state")
        g, c = expected["conductance_w_per_k"], expected["capacitance_j_per_k"]
        heat = sum(
            (b - a) * (p + q) / 2
            for a, b, p, q in zip(times, times[1:], power, power[1:])
        )
        loss = sum(
            (b - a) * g * (p + q) / 2
            for a, b, p, q in zip(times, times[1:], theta, theta[1:])
        )
        stored = c * (theta[-1] - theta[0])
        require(heat > 0, "Positive real heating required")
        energy_error = abs(stored + loss - heat) / heat
        target = dc[f"v(xr{i}.dt)"][0]
        dc_power = dc[f"@n.xr{i}.nr1[power]"][0]
        require(
            target > 0 and abs(g * target / dc_power - 1) < 1e-8,
            "Native powered DC thermal balance",
        )
        dc_error = abs(theta[-1] / target - 1)
        rows.append(
            dict(
                index=i,
                w_um=w,
                l_um=l,
                **expected,
                final_thermal_k=theta[-1],
                dc_thermal_k=target,
                heating_j=heat,
                conducted_j=loss,
                stored_j=stored,
                energy_relative_error=energy_error,
                transient_to_dc_relative_error=dc_error,
                energy_pass=energy_error < ENERGY_RELATIVE_LIMIT,
                transient_to_dc_pass=dc_error < DC_RELATIVE_LIMIT,
            )
        )
    return dict(
        devices=rows,
        pass_native=all(r["energy_pass"] and r["transient_to_dc_pass"] for r in rows),
    )


def run(parent, output):
    parent, output = Path(parent).resolve(), Path(output).resolve()
    require(
        old.sha(Path(thermal.__file__)) == THERMAL_SHA
        and old.sha(parent / "result.json") == RESULT_SHA,
        "Exact frozen40ns producer/capture required",
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM root",
    )
    r = json.loads((parent / "result.json").read_text())
    pins = r["source_sha256"].copy()
    require(
        all(old.sha(Path(p)) == h for p, h in pins.items()),
        "Historical native inputs changed",
    )
    pins[str(parent / "result.json")] = RESULT_SHA
    pins[str(Path(__file__).resolve())] = old.sha(Path(__file__))
    models = next(Path(p).parent for p in pins if Path(p).name == "cornerRES.lib")
    va = next(Path(p) for p in pins if p.endswith("/r3_cmc.va"))
    require(
        old.sha(models / "resistors_mod.lib") == RES_SHA and old.sha(va) == VA_SHA,
        "Exact unchanged thermal equations",
    )
    runtime = next(Path(p) for p in pins if Path(p).name == "ngspice")
    osdi = next(Path(p) for p in pins if Path(p).name == "r3_cmc.osdi")
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(thermal.driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        scope="Five standalone native resistor geometries at independent1.2V excitation. Thermal-model calibration, not oscillator hot-start or periodic steady-state acceptance.",
    )
    save = lambda: thermal.driver.atomic_record(output / "result.json", record)
    prev = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    save()
    native = {}
    try:
        for variant in ("dc", "cold", "selfheat_off", "wrong_geometry"):
            d = output / variant
            d.mkdir()
            (d / "bench.cir").write_text(deck(models, osdi, variant))
            row = dict(variant=variant)
            record["cases"].append(row)
            save()
            row["execution"] = thermal.driver.parent.init.startup.s.rx.execute(
                [str(runtime), "-n", "-b", "bench.cir"], d, d / "run.log"
            )
            row["numerical"] = old.diagnostics((d / "run.log").read_text())
            require(row["numerical"]["clean"], "Native numerical failure")
            data, times = read(d / "result.dat", dc=variant == "dc")
            native[variant] = (data, times)
            if variant != "dc":
                initial, _ = read(d / "initial-op.dat", dc=True)
                require(
                    initial["v(a)"] == [0.0]
                    and all(initial[f"v(xr{i}.dt)"] == [0.0] for i in range(5)),
                    "Native zero initial OP",
                )
                try:
                    row["audit"] = audit(data, times, native["dc"][0])
                    row["expected_outcome"] = row["audit"]["pass_native"] == (
                        variant == "cold"
                    )
                except ValueError as e:
                    row["rejection"] = str(e)
                    row["expected_outcome"] = (
                        variant == "wrong_geometry"
                        and str(e) == "Native rth/geometry differs"
                    )
            else:
                row["expected_outcome"] = True
            for p in tuple(d.glob("*.dat")):
                row.setdefault("raw_sha256", {})[p.name] = old.sha(p)
                with (
                    p.open("rb") as src,
                    lzma.open(str(p) + ".xz", "wb", preset=1) as dst,
                ):
                    shutil.copyfileobj(src, dst)
                with lzma.open(str(p) + ".xz", "rb") as f:
                    require(
                        hashlib.file_digest(f, "sha256").hexdigest()
                        == row["raw_sha256"][p.name],
                        "Exact lossless raw retention",
                    )
                p.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in d.iterdir()}
            save()
        require(all(old.sha(Path(p)) == h for p, h in pins.items()), "Inputs changed")
        record["status"] = (
            "PASS_NATIVE_RPPD_POLE_DC_CALIBRATION"
            if all(r["expected_outcome"] for r in record["cases"])
            else "FAIL_NATIVE_RPPD_POLE_DC_CALIBRATION"
        )
        record["nominal_thermal_pole_upper_bound_s"] = 594e-15 / 6e-6
        record["passive_single_pole_1e4_decay_time_s"] = record[
            "nominal_thermal_pole_upper_bound_s"
        ] * math.log(1e4)
        record["proposed_oscillator_validation_duration_s"] = 1e-6
        record["nonlinear_oscillator_settling_guaranteed"] = False
        save()
    except BaseException as e:
        record.update(status="ERROR", error=repr(e))
        save()
        raise
    finally:
        if prev is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = prev
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("parent", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    a = p.parse_args()
    return int(run(a.parent, a.out)["status"] != "PASS_NATIVE_RPPD_POLE_DC_CALIBRATION")


if __name__ == "__main__":
    raise SystemExit(main())
