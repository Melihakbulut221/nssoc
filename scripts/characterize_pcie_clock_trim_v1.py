#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exploratory real MOS-switched differential MIM bank, not PLL acceptance."""

import argparse
import json
import lzma
import math
import os
from pathlib import Path
import shutil
import statistics

import characterize_pcie_clock_driver_v3 as driver

old = driver.old
require = driver.require
DRIVER_SHA = "510b0c25dc66acc8108f83a9f06dcbb00e6eeb1c1bb782f6f364bac73f483148"
CIRCUIT_SHA = "0d578a1392a13a9d61013eb5f0592515fccb112eddcee24f643f816b020f10f4"
CIRCUIT = old.ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v3.spice"
TOP = "nssoc_clock_vco_mim_trim_experiment_v1"
FILE = "clock_vco_mim_trim_experiment_v1.spice"
SWITCHES = tuple(f"xtsw{s}{b}" for s in range(3) for b in range(2))
PLATES = tuple(f"tp{s}{b}{side}" for s in range(3) for b in range(2) for side in "pn")


def circuit(case, width, bias_factor=1):
    require(width in (32, 64, 128), "Explicit native switch-width trials only")
    require(old.sha(CIRCUIT) == CIRCUIT_SHA, "Frozen driver circuit changed")
    require(bias_factor in (1, 4), "Explicit bias conductance trials only")
    text = driver.circuit(case, 4, 2)
    additions = [
        "* Real resistor midpoint and plate bias; no ideal internal bias source.",
        f"XTBH avdd tmid sub rppd w={2 * bias_factor}u l=7.4u b=0 sw_et=1",
        f"XTBL tmid avss sub rppd w={2 * bias_factor}u l=7.4u b=0 sw_et=1",
    ]
    for stage in range(3):
        for side in "pn":
            name = f"XC{side.upper()}{stage}"
            before = f"{name} {side}{stage} avss cap_cmim w={'12.2' if stage == 0 and side == 'p' else '12'}u l=12u"
            after = f"{name} {side}{stage} avss cap_cmim w={'10.24' if stage == 0 and side == 'p' else '10'}u l=10u"
            require(text.count(before) == 1, "Exact original MIM geometry anchor")
            text = text.replace(before, after)
        for bit in range(2):
            for side in "pn":
                plate = f"tp{stage}{bit}{side}"
                additions += [
                    f"XTC{stage}{bit}{side} {side}{stage} {plate} cap_cmim w=8u l=8u",
                    f"XTR{stage}{bit}{side} {plate} tmid sub rppd w={bias_factor}u l=29u b=0 sw_et=1",
                ]
            additions.append(
                f"XTSW{stage}{bit} tp{stage}{bit}p trim{bit} tp{stage}{bit}n avss sg13_hv_nmos w={width}u l=0.45u ng={width // 8} m=1"
            )
    text = text.replace(
        ".ends " + driver.TOP, "\n".join(additions) + "\n.ends " + driver.TOP
    )
    text = text.replace(
        ".subckt " + driver.TOP + " clkp clkn vctrl avdd avss sub",
        ".subckt " + TOP + " clkp clkn vctrl trim0 trim1 avdd avss sub",
    )
    text = text.replace(".ends " + driver.TOP, ".ends " + TOP)
    require(
        driver.contract(text, 4) == driver.contract(CIRCUIT.read_text(), 4)
        or bool(case["fault"]),
        "Original HBT geometry/topology changed",
    )
    return text


def vectors(hbts):
    extra = ["v(trim0)", "v(trim1)", "v(xosc.tmid)"]
    extra += [f"v(xosc.{n})" for n in PLATES]
    extra += [
        f"v(xosc.{n}.dt)"
        for n in ("xtbh", "xtbl", *["xtr" + plate[2:] for plate in PLATES])
    ]
    extra += [
        f"@n.xosc.{name}.nsg13_hv_nmos[{field}]"
        for name in SWITCHES
        for field in ("ids", "idb", "isb")
    ]
    return driver.vectors(hbts) + extra


def deck(case, models, osdi, cp, cn, hbts):
    require(case["code"] in (0, 1, 2), "Explicit thermometer code only")
    text = driver.deck(case, models, osdi, cp, cn, hbts)
    text = text.replace(f'.include "{driver.FILE}"', f'.include "{FILE}"')
    text = text.replace(
        f"XOSC clkp clkn vctrl avdd 0 0 {driver.TOP}",
        f"XOSC clkp clkn vctrl trim0 trim1 avdd 0 0 {TOP}",
    )
    gates = []
    for bit in range(2):
        level = case["supply"] if case["code"] > bit else 0
        if case.get("trim_fault") == "stuck_off":
            level = 0
        gates.append(
            f"VTRIM{bit} trim{bit} 0 PWL(0 0 {case['ramp_s']:.12g} {level:.12g})"
        )
    text = text.replace("\n.control", "\n" + "\n".join(gates) + "\n.control")
    previous = " ".join(driver.vectors(hbts))
    vs = " ".join(vectors(hbts))
    for prefix in ("save ", "wrdata wave.dat ", "wrdata initial-op.dat "):
        require(text.count(prefix + previous) == 1, "Exact old observations required")
        text = text.replace(prefix + previous, prefix + vs)
    return text


def read_wave(path, hbts, case):
    with Path(path).open() as stream:
        header = stream.readline().split()
        require(header == ["time", *vectors(hbts)], "Exact trim observation order")
        data = {n: [] for n in header}
        for line in stream:
            row = [float(x) for x in line.split()]
            require(
                len(row) == len(header) and all(math.isfinite(x) for x in row),
                "Incomplete/nonfinite native wave",
            )
            for name, value in zip(header, row):
                data[name].append(value)
    time = data["time"]
    require(
        len(time) >= 1000 and time[0] == 0 and time[-1] >= 12e-9,
        "Full native capture required",
    )
    require(
        all(0 < b - a <= case["step_s"] * 1.00001 for a, b in zip(time, time[1:])),
        "Native timestep/time order differs",
    )
    return data


def measure(data, hbts, case):
    result = driver.measure(data, hbts)
    start = next(i for i, t in enumerate(data["time"]) if t >= 4e-9)
    switches = {}
    for stage in range(3):
        for bit in range(2):
            name = f"xtsw{stage}{bit}"
            d, s, g = (
                data[f"v(xosc.tp{stage}{bit}p)"],
                data[f"v(xosc.tp{stage}{bit}n)"],
                data[f"v(trim{bit})"],
            )
            switches[name] = dict(
                expected_on=case["code"] > bit and not case.get("trim_fault"),
                full_gate_min_v=min(g),
                full_gate_max_v=max(g),
                full_drain_min_v=min(d),
                full_source_min_v=min(s),
                full_drain_max_v=max(d),
                full_source_max_v=max(s),
                full_max_abs_vgs_v=max(abs(a - b) for a, b in zip(g, s)),
                full_max_abs_vgd_v=max(abs(a - b) for a, b in zip(g, d)),
                full_max_abs_vds_v=max(abs(a - b) for a, b in zip(d, s)),
                full_max_abs_ids_a=max(
                    map(abs, data[f"@n.xosc.{name}.nsg13_hv_nmos[ids]"])
                ),
                full_max_abs_idb_a=max(
                    map(abs, data[f"@n.xosc.{name}.nsg13_hv_nmos[idb]"])
                ),
                full_max_abs_isb_a=max(
                    map(abs, data[f"@n.xosc.{name}.nsg13_hv_nmos[isb]"])
                ),
                active_max_abs_vds_v=max(
                    abs(a - b) for a, b in zip(d[start:], s[start:])
                ),
                active_mean_plate_v=statistics.mean(
                    (a + b) / 2 for a, b in zip(d[start:], s[start:])
                ),
            )
    result["switches"] = switches
    result["checks"]["switch_terminal_voltage"] = all(
        min(x["full_gate_min_v"], x["full_drain_min_v"], x["full_source_min_v"])
        >= -0.05
        and max(
            x["full_gate_max_v"],
            x["full_drain_max_v"],
            x["full_source_max_v"],
            x["full_max_abs_vgs_v"],
            x["full_max_abs_vgd_v"],
            x["full_max_abs_vds_v"],
        )
        <= 3.3
        for x in switches.values()
    )
    result["trim_gate_rail_error_v"] = {
        str(bit): max(
            abs(
                v
                - (
                    case["supply"]
                    if case["code"] > bit and not case.get("trim_fault")
                    else 0
                )
            )
            for v in data[f"v(trim{bit})"][start:]
        )
        for bit in range(2)
    }
    result["checks"]["native_trim_gate_rails"] = (
        max(result["trim_gate_rail_error_v"].values()) <= 1e-10
    )
    result["screen_pass"] = all(result["checks"].values())
    result["eight_ghz_lock_or_coverage_claim"] = False
    return result


def cases(suite):
    corners = driver.parent.TUNING
    if suite == "nominal":
        corners = corners[:1]
    elif suite == "gaps":
        corners = corners[4:]
    else:
        require(suite == "corners", "Explicit trim suite required")
    return [
        dict(
            old.BASE,
            **mods,
            name=f"{name}_code{code}_v{control:.2f}",
            code=code,
            control=control,
        )
        for name, mods in corners
        for code in range(3)
        for control in (0.60, 1.00)
    ]


def run(
    baseline, startup, capacitance, output, width, suite, selected=None, bias_factor=1
):
    baseline, startup, capacitance, output = (
        Path(p).resolve() for p in (baseline, startup, capacitance, output)
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM directory required",
    )
    require(
        old.sha(Path(driver.__file__)) == DRIVER_SHA
        and old.sha(CIRCUIT) == CIRCUIT_SHA,
        "Frozen native parent differs",
    )
    require(
        old.sha(Path(driver.fanout.__file__)) == driver.FANOUT_SHA,
        "Frozen load derivation changed",
    )
    _, pins = driver.parent.inputs(baseline, startup)
    require(
        old.sha(capacitance) == driver.fanout.CAP_SHA,
        "Exact measured bank load required",
    )
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                Path(__file__).resolve(),
                Path(driver.__file__).resolve(),
                CIRCUIT,
                Path(driver.fanout.__file__).resolve(),
                capacitance,
            )
        }
    )
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    require(len(models) == len(runtime) == 1, "Unique pinned runtime/models")
    cp, cn = driver.fanout.loads(json.loads(capacitance.read_text()))[-1][1]
    rows = selected if selected is not None else cases(suite)
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        width_um=width,
        bias_factor=bias_factor,
        suite=suite,
        cases=[],
        limits=old.LIMITS,
        load_p_f=cp,
        load_n_f=cn,
        limitations=[
            "Real native HV-MOS/MIM/rppd only; external static code rail is not yet a synthesized trim controller.",
            "Finite deterministic schematic and collapsed-load exploration, not qualified PEX/PLL/Gen3 acceptance.",
            "New MIM geometries and switches have no verified physical layout; original frozen v3 layout target is unchanged.",
        ],
    )
    save = lambda: driver.atomic_record(output / "result.json", record)
    save()
    previous = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    try:
        for case in rows:
            d = output / case["name"]
            d.mkdir()
            text = circuit(case, width, bias_factor)
            hbts = driver.contract(text, 4)
            (d / FILE).write_text(text)
            (d / "bench.cir").write_text(
                deck(
                    case,
                    models[0],
                    [baseline / n for n in driver.parent.init.MODELS],
                    cp,
                    cn,
                    hbts,
                )
            )
            row = dict(case=case, actual_hbt_count=len(hbts))
            record["cases"].append(row)
            save()
            try:
                row["execution"] = driver.parent.init.startup.s.rx.execute(
                    [str(runtime[0]), "-n", "-b", "bench.cir"], d, d / "run.log"
                )
                log = (d / "run.log").read_text()
                row["numerical"] = old.diagnostics(log)
                row["flags_observed"] = driver.flags(log, hbts)
                row["initial_op"] = driver.parent.init.startup.initial_op(
                    d / "initial-op.dat", vectors(hbts)
                )
                row["zero_initial_op"] = (
                    max(map(abs, row["initial_op"].values())) <= 1e-10
                )
                data = read_wave(d / "wave.dat", hbts, case)
                row["measurement"] = measure(data, hbts, case)
                del data
                row["clean_initialization"] = (
                    row["execution"]["returncode"] == 0
                    and row["numerical"]["clean"]
                    and row["zero_initial_op"]
                )
            except (ValueError, RuntimeError, FileNotFoundError) as error:
                row.update(error=repr(error), clean_initialization=False)
            wave = d / "wave.dat"
            if wave.exists():
                row["uncompressed_wave_sha256"] = old.sha(wave)
                with (
                    wave.open("rb") as src,
                    lzma.open(d / "wave.dat.xz", "wb", preset=1) as dst,
                ):
                    shutil.copyfileobj(src, dst)
                require(
                    old.sha(wave) == row["uncompressed_wave_sha256"],
                    "Native wave changed during compression",
                )
                wave.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in d.iterdir()}
            save()
            m = row.get("measurement", {})
            print(
                case["name"],
                row.get("error"),
                row["clean_initialization"],
                m.get("screen_pass"),
                m.get("frequency_hz"),
                [k for k, v in m.get("checks", {}).items() if not v],
                flush=True,
            )
        require(
            all(old.sha(Path(p)) == h for p, h in pins.items()), "Native inputs changed"
        )
        record["status"] = "COMPLETE_NATIVE_TRIM_EXPLORATION"
        record["source_bytes_unchanged"] = True
        save()
    finally:
        if previous is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = previous
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "startup", "capacitance", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--width", type=int, choices=(32, 64, 128), default=64)
    parser.add_argument(
        "--suite", choices=("nominal", "gaps", "corners"), default="nominal"
    )
    parser.add_argument("--bias-factor", type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    run(
        args.baseline,
        args.startup,
        args.capacitance,
        args.out,
        args.width,
        args.suite,
        bias_factor=args.bias_factor,
    )


if __name__ == "__main__":
    main()
