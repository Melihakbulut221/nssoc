#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate native bias-settling correction to the frozen switched-MIM experiment."""

import argparse
import json
import lzma
import os
from pathlib import Path
import shutil

import characterize_pcie_clock_trim_v1 as prior

old = prior.old
require = prior.require
PRIOR_SHA = "508cb8aa7902b53d7680b93adf572ed3be3220e4687d7c96b4638588e4a9aa44"
TOP = "nssoc_clock_vco_mim_trim_experiment_v2"
FILE = "clock_vco_mim_trim_experiment_v2.spice"


def circuit(case):
    require(old.sha(Path(prior.__file__)) == PRIOR_SHA, "Frozen trim-v1 method changed")
    original = prior.circuit(case, 64, 4)
    text = original
    changes = [
        ("XTBH avdd tmid sub rppd w=8u", "XTBH avdd tmid sub rppd w=16u"),
        ("XTBL tmid avss sub rppd w=8u", "XTBL tmid avss sub rppd w=16u"),
    ]
    changes += [
        (
            f"XTR{plate[2:]} {plate} tmid sub rppd w=4u",
            f"XTR{plate[2:]} {plate} tmid sub rppd w=8u",
        )
        for plate in prior.PLATES
    ]
    for before, after in changes:
        require(text.count(before) == 1, "Exact bias-resistor geometry anchor required")
        text = text.replace(before, after)
    require(len(changes) == 14, "All and only14 native bias resistor widths")
    restored = text
    for before, after in changes:
        restored = restored.replace(after, before)
    require(restored == original, "Unexpected circuit change")
    return text.replace(".subckt " + prior.TOP, ".subckt " + TOP).replace(
        ".ends " + prior.TOP, ".ends " + TOP
    )


def deck(case, models, osdi, cp, cn, hbts):
    text = prior.deck(case, models, osdi, cp, cn, hbts)
    require(
        text.count(prior.TOP) == 1 and text.count(prior.FILE) == 1,
        "Exact prior circuit binding",
    )
    return text.replace(prior.TOP, TOP).replace(prior.FILE, FILE)


def cases(suite):
    corners = dict(prior.driver.parent.TUNING)
    if suite == "fast_pilot":
        points = [("high_supply_res_bcs_cap_bcs", 2, v) for v in (0.85, 1.0)]
    else:
        require(suite == "seven", "Bounded explicit suite required")
        points = [
            (name, code, control)
            for name, code, controls in [
                ("nominal", 1, (0.60, 1.0)),
                ("hot_bcs_ss", 1, (0.90, 1.0)),
                ("cold_wcs_ss", 1, (0.60, 1.0)),
                ("cold_bcs_ff", 1, (0.80, 1.20)),
                ("hot_wcs_ff", 0, (0.60, 1.10)),
                ("low_supply_res_wcs_cap_wcs", 0, (0.60, 1.0)),
                ("high_supply_res_bcs_cap_bcs", 2, (0.85, 1.0)),
            ]
            for control in controls
        ]
    return [
        dict(
            old.BASE,
            **corners[name],
            name=f"{name}_code{code}_v{v:.2f}_halfstep",
            code=code,
            control=v,
            step_s=0.5e-12,
        )
        for name, code, v in points
    ]


def run(output, suite):
    output = Path(output).resolve()
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM directory required",
    )
    baseline = Path("/dev/shm/nssoc-clock-vco-full-20261004")
    startup = Path("/dev/shm/nssoc-vco-zero-v2-full")
    cap = (
        old.ROOT
        / "hw/soc/out/pcie-clocked-bank-v3-20261004/capacitance-and-rc-review.json"
    )
    require(
        old.sha(Path(prior.__file__)) == PRIOR_SHA
        and old.sha(Path(prior.driver.__file__)) == prior.DRIVER_SHA,
        "Frozen methods changed",
    )
    require(
        old.sha(cap) == prior.driver.fanout.CAP_SHA
        and old.sha(Path(prior.driver.fanout.__file__)) == prior.driver.FANOUT_SHA,
        "Frozen native load changed",
    )
    _, pins = prior.driver.parent.inputs(baseline, startup)
    pins.update(
        {
            str(p): old.sha(p)
            for p in (
                Path(__file__).resolve(),
                Path(prior.__file__).resolve(),
                Path(prior.driver.__file__).resolve(),
                Path(prior.driver.fanout.__file__).resolve(),
                prior.CIRCUIT,
                cap,
            )
        }
    )
    modelroot = next(Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib")
    runtime = next(Path(p) for p in pins if Path(p).name == "ngspice")
    cp, cn = prior.driver.fanout.loads(json.loads(cap.read_text()))[-1][1]
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(prior.driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        suite=suite,
        cases=[],
        load_p_f=cp,
        load_n_f=cn,
        limits=old.LIMITS,
        physical_qualification=False,
        pll_implemented=False,
        scope="Only14 native bias resistor widths double; all capacitors, six realMOS switches,30HBTs, driver, tolerances, windows and electrical limits unchanged. External static code rails, collapsed load and finite PVT samples only.",
    )
    save = lambda: prior.driver.atomic_record(output / "result.json", record)
    save()
    previous = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    try:
        for case in cases(suite):
            require(
                shutil.disk_usage("/dev/shm").free >= 200 * 1024**2,
                "Insufficient RAM scratch; preserve partial run",
            )
            d = output / case["name"]
            d.mkdir()
            text = circuit(case)
            hbts = prior.driver.contract(text, 4)
            (d / FILE).write_text(text)
            (d / "bench.cir").write_text(
                deck(
                    case,
                    modelroot,
                    [baseline / n for n in prior.driver.parent.init.MODELS],
                    cp,
                    cn,
                    hbts,
                )
            )
            row = dict(case=case)
            record["cases"].append(row)
            save()
            row["execution"] = prior.driver.parent.init.startup.s.rx.execute(
                [str(runtime), "-n", "-b", "bench.cir"], d, d / "run.log"
            )
            log = (d / "run.log").read_text()
            row["numerical"] = old.diagnostics(log)
            row["flags_observed"] = prior.driver.flags(log, hbts)
            row["initial_op"] = prior.driver.parent.init.startup.initial_op(
                d / "initial-op.dat", prior.vectors(hbts)
            )
            row["zero_initial_op"] = max(map(abs, row["initial_op"].values())) <= 1e-10
            data = prior.read_wave(d / "wave.dat", hbts, case)
            row["measurement"] = prior.measure(data, hbts, case)
            del data
            row["clean_initialization"] = (
                row["execution"]["returncode"] == 0
                and row["numerical"]["clean"]
                and row["zero_initial_op"]
            )
            wave = d / "wave.dat"
            row["uncompressed_wave_sha256"] = old.sha(wave)
            with (
                wave.open("rb") as src,
                lzma.open(d / "wave.dat.xz", "wb", preset=1) as dst,
            ):
                shutil.copyfileobj(src, dst)
            wave.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in d.iterdir()}
            save()
            print(
                case["name"],
                row["clean_initialization"],
                row["measurement"]["screen_pass"],
                row["measurement"]["frequency_hz"],
                row["measurement"]["period_spread"],
                [k for k, v in row["measurement"]["checks"].items() if not v],
                flush=True,
            )
        require(
            all(old.sha(Path(p)) == h for p, h in pins.items()), "Native inputs changed"
        )
        record["status"] = "COMPLETE_NATIVE_BIAS_REVISION"
        record["source_bytes_unchanged"] = True
        save()
    finally:
        if previous is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = previous
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--suite", choices=("fast_pilot", "seven"), default="fast_pilot"
    )
    args = parser.parse_args()
    run(args.out, args.suite)
