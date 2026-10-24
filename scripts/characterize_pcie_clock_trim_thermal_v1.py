#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate 40 ns thermal trajectory; prior 12 ns failures remain unchanged."""

import argparse
from array import array
from bisect import bisect_left, bisect_right
import json
import lzma
import math
import os
from pathlib import Path
import shutil
import statistics

import characterize_pcie_clock_trim_v1 as prior

driver = prior.driver
old = prior.old
require = prior.require
PRIOR_SHA = "508cb8aa7902b53d7680b93adf572ed3be3220e4687d7c96b4638588e4a9aa44"
PRIOR_RESULT_SHA = "f2138715f5385c325e3d430ea26550ded95326c247f59d2a38771a90cb1d0129"
PRIOR_CASE = "high_supply_res_bcs_cap_bcs_code2_v1.00_halfstep"
PRIOR_CIRCUIT_SHA = "e84c8605c8f147b09731b6b90de8233948ab386519f91370b177fc71faad2566"
STOP_S = 40e-9
FINAL_WINDOW = (32e-9, 40e-9)
FREQUENCY_SPAN_PPM = 100.0
THERMAL_RATE_V_PER_NS = 0.01
RATE_INCREASE_TOLERANCE_V_PER_NS = 1e-5
STEP_AGREEMENT_PPM = 100.0


def cases():
    mods = dict(driver.parent.TUNING)["high_supply_res_bcs_cap_bcs"]
    return [
        dict(
            old.BASE,
            **mods,
            name=f"fast_code2_v1.00_{label}",
            code=2,
            control=1.00,
            step_s=step,
        )
        for label, step in (("halfstep", 0.5e-12), ("quarterstep", 0.25e-12))
    ]


def circuit(case):
    require(old.sha(Path(prior.__file__)) == PRIOR_SHA, "Frozen trim producer differs")
    text = prior.circuit(case, 64, 4)
    import hashlib

    require(
        hashlib.sha256(text.encode()).hexdigest() == PRIOR_CIRCUIT_SHA,
        "Exact prior failed physical circuit required",
    )
    return text


def deck(case, models, osdi, cp, cn, hbts):
    source = prior.deck(case, models, osdi, cp, cn, hbts)
    before = f"tran {case['step_s']:.12g} 12n 0 {case['step_s']:.12g}"
    require(source.count(before) == 1, "Exact frozen 12 ns transient anchor")
    return source.replace(before, before.replace(" 12n ", " 40n "))


def read_wave(path, hbts, case):
    # Contiguous doubles avoid millions of boxed floats; all source columns stay.
    with Path(path).open() as stream:
        header = stream.readline().split()
        require(header == ["time", *prior.vectors(hbts)], "Exact observation order")
        data = {n: array("d") for n in header}
        for line in stream:
            row = [float(x) for x in line.split()]
            require(
                len(row) == len(header) and all(map(math.isfinite, row)),
                "Incomplete/nonfinite native wave",
            )
            for name, value in zip(header, row):
                data[name].append(value)
    ts = data["time"]
    require(
        len(ts) >= 1000 and ts[0] == 0 and STOP_S <= ts[-1] <= STOP_S + 1e-18,
        "Full time0-to40ns native capture required",
    )
    require(
        all(0 < b - a <= case["step_s"] * 1.00001 for a, b in zip(ts, ts[1:])),
        "Native timestep/time order differs",
    )
    return data


def indices(data, start, end):
    ts = data["time"]
    lo, hi = bisect_left(ts, start), bisect_right(ts, end)
    require(hi - lo >= 2, "Missing declared measurement window")
    return lo, hi


def clock_window(data, start, end):
    lo, hi = indices(data, start, end)
    ts = data["time"][lo:hi]
    ps, ns = data["v(clkp)"][lo:hi], data["v(clkn)"][lo:hi]
    diff = [p - n for p, n in zip(ps, ns)]
    up, down = old.crossings(ts, diff), old.crossings(ts, diff, False)
    periods = [b - a for a, b in zip(up, up[1:])]
    duty, bad_order = [], 0
    for a, b in zip(up, up[1:]):
        falls = [f for f in down if a < f < b]
        if len(falls) != 1:
            bad_order += 1
        else:
            duty.append((falls[0] - a) / (b - a))
    mean = statistics.mean(periods) if periods else None
    freq = 1 / mean if mean else None
    spread = (max(periods) - min(periods)) / mean if mean else None
    limits = old.LIMITS
    checks = dict(
        edges=len(up) >= limits["min_edges"],
        edge_order=bad_order == 0,
        differential_swing=min(max(diff), -min(diff)) >= limits["min_diff_peak_v"],
        frequency=freq is not None
        and limits["min_frequency_hz"] <= freq <= limits["max_frequency_hz"],
        deterministic_period_spread=spread is not None
        and spread < limits["max_period_spread"],
        duty=bool(duty)
        and min(duty) >= limits["min_duty"]
        and max(duty) <= limits["max_duty"],
    )
    return dict(
        declared_window_s=[start, end],
        actual_samples_s=[ts[0], ts[-1]],
        rising_edges=len(up),
        frequency_hz=freq,
        period_spread=spread,
        min_diff_v=min(diff),
        max_diff_v=max(diff),
        duty_range=[min(duty), max(duty)] if duty else None,
        checks=checks,
        functional_pass=all(checks.values()),
    )


def trajectory(data, hbts):
    thermal = [n for n in data if n.endswith((".t)", ".dt)"))]
    require(len(thermal) == len(hbts) + 23, "Every HBT and resistor thermal node")
    result = []
    for index in range(20):
        start, end = index * 2e-9, (index + 1) * 2e-9
        lo, hi = indices(data, start, end)
        actual_duration = data["time"][hi - 1] - data["time"][lo]
        nodes = {}
        for name in thermal:
            values = data[name][lo:hi]
            nodes[name] = dict(
                start_v=values[0],
                end_v=values[-1],
                min_v=min(values),
                max_v=max(values),
                mean_v=statistics.mean(values),
                signed_rate_v_per_ns=(values[-1] - values[0]) / actual_duration * 1e-9,
            )
        result.append(dict(**clock_window(data, start, end), thermal_nodes=nodes))
    return result


def convergence(windows):
    require(
        len(windows) == 20
        and all(
            w["declared_window_s"] == [i * 2e-9, (i + 1) * 2e-9]
            for i, w in enumerate(windows)
        ),
        "Complete consecutive2ns trajectory required",
    )
    tail = windows[-4:]
    fs = [w["frequency_hz"] for w in tail]
    finite_clocks = all(x is not None and math.isfinite(x) and x > 0 for x in fs)
    keys = set(tail[0]["thermal_nodes"])
    require(
        bool(keys) and all(set(w["thermal_nodes"]) == keys for w in windows),
        "Identical full thermal census in every window",
    )
    rates = {
        n: [abs(w["thermal_nodes"][n]["signed_rate_v_per_ns"]) for w in tail]
        for n in sorted(keys)
    }
    span = (max(fs) - min(fs)) / statistics.mean(fs) * 1e6 if finite_clocks else None
    checks = dict(
        final_four_frequency_means_within100ppm=span is not None
        and span <= FREQUENCY_SPAN_PPM,
        all_final_thermal_rates_within_limit=all(
            r[-1] <= THERMAL_RATE_V_PER_NS for r in rates.values()
        ),
        all_final_thermal_rates_nonincreasing=all(
            all(b <= a + RATE_INCREASE_TOLERANCE_V_PER_NS for a, b in zip(r, r[1:]))
            for r in rates.values()
        ),
    )
    return dict(
        declared_window_s=list(FINAL_WINDOW),
        frequency_span_ppm=span,
        max_final_thermal_rate_v_per_ns=max(r[-1] for r in rates.values()),
        rates_by_node_v_per_ns=rates,
        checks=checks,
        converged=all(checks.values()),
    )


def measure(data, hbts, case):
    full = prior.measure(data, hbts, case)
    # Correct the frozen parent's historical label; no old result is rewritten.
    del full["settled_window_s"]
    full["operating_window_s"] = [4e-9, STOP_S]
    safety = {
        k: v for k, v in full["checks"].items() if k not in driver.FUNCTIONAL_CHECKS
    }
    history = clock_window(data, 4e-9, 12e-9)
    final = clock_window(data, *FINAL_WINDOW)
    windows = trajectory(data, hbts)
    conv = convergence(windows)
    return dict(
        full_capture=full,
        safety_checks=safety,
        original_4_to12ns_clock_window=history,
        final_clock_window=final,
        consecutive2ns_windows=windows,
        convergence=conv,
        limited_thermal_screen_pass=all(safety.values())
        and final["functional_pass"]
        and conv["converged"],
        prior12ns_results_superseded=False,
        frequency_lock_or_pcie_acceptance=False,
        earliest_proven_settled_time_s=None,
        scope="Fixed40ns experiment, final32-to40ns window; no minimum startup duration inferred.",
    )


def pair_agreement(rows):
    require(
        len(rows) == 2 and [r["case"] for r in rows] == cases(), "Exact timestep pair"
    )
    fs = [r["measurement"]["final_clock_window"]["frequency_hz"] for r in rows]
    finite_clocks = all(f is not None and math.isfinite(f) and f > 0 for f in fs)
    delta = abs(fs[0] / fs[1] - 1) * 1e6 if finite_clocks else None
    return dict(
        frequency_delta_ppm=delta,
        limit_ppm=STEP_AGREEMENT_PPM,
        pass_pair=delta is not None and delta <= STEP_AGREEMENT_PPM,
    )


def previous_failure(root):
    root = Path(root).resolve()
    result = root / "result.json"
    require(old.sha(result) == PRIOR_RESULT_SHA, "Exact prior12ns result required")
    record = json.loads(result.read_text())
    rows = [r for r in record["cases"] if r["case"]["name"] == PRIOR_CASE]
    require(len(rows) == 1, "Unique prior failure")
    row = rows[0]
    require(
        row["measurement"]["checks"]["deterministic_period_spread"] is False
        and row["clean_initialization"] is True,
        "Actual clean prior period failure",
    )
    require(
        {k: v for k, v in row["case"].items() if k != "name"}
        == {k: v for k, v in cases()[0].items() if k != "name"},
        "Prior case parameters differ",
    )
    pins = {str(result): PRIOR_RESULT_SHA}
    for name in ("bench.cir", prior.FILE, "run.log", "initial-op.dat"):
        p = root / PRIOR_CASE / name
        require(old.sha(p) == row["outputs"][name], "Prior native input/output changed")
        pins[str(p)] = old.sha(p)
    return row, pins


def run(baseline, startup, capacitance, output, prior12):
    baseline, startup, capacitance, output = map(
        lambda p: Path(p).resolve(), (baseline, startup, capacitance, output)
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output required",
    )
    require(
        old.sha(Path(prior.__file__)) == PRIOR_SHA
        and old.sha(Path(driver.__file__)) == prior.DRIVER_SHA,
        "Frozen native producers changed",
    )
    require(
        old.sha(Path(driver.fanout.__file__)) == driver.FANOUT_SHA
        and old.sha(capacitance) == driver.fanout.CAP_SHA,
        "Frozen measured load differs",
    )
    _, pins = driver.parent.inputs(baseline, startup)
    previous_row, previous_pins = previous_failure(prior12)
    pins.update(previous_pins)
    previous_deck = (Path(prior12) / PRIOR_CASE / "bench.cir").read_text()
    for p in (
        Path(__file__).resolve(),
        Path(prior.__file__).resolve(),
        Path(driver.__file__).resolve(),
        Path(driver.fanout.__file__).resolve(),
        prior.CIRCUIT,
        capacitance,
    ):
        pins[str(p)] = old.sha(p)
    models = [Path(p).parent for p in pins if Path(p).name == "cornerHBT.lib"]
    runtime = [Path(p) for p in pins if Path(p).name == "ngspice"]
    require(len(models) == len(runtime) == 1, "Unique runtime/model binding")
    cp, cn = driver.fanout.loads(json.loads(capacitance.read_text()))[-1][1]
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        limits=old.LIMITS,
        load_p_f=cp,
        load_n_f=cn,
        declared_duration_s=STOP_S,
        final_window_s=list(FINAL_WINDOW),
        prior12ns_results_superseded=False,
        previous12ns_native_failure=previous_row,
        previous12ns_full_wave_replayed_by_this_method=False,
        convergence_limits=dict(
            frequency_span_ppm=FREQUENCY_SPAN_PPM,
            thermal_rate_v_per_ns=THERMAL_RATE_V_PER_NS,
            rate_increase_tolerance_v_per_ns=RATE_INCREASE_TOLERANCE_V_PER_NS,
            timestep_agreement_ppm=STEP_AGREEMENT_PPM,
        ),
        scope="Unchanged native trim-v1 physical devices and collapsed load. No trimming controller, PLL, PEX or PCIe frequency acceptance.",
    )
    save = lambda: driver.atomic_record(output / "result.json", record)
    previous = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    save()
    try:
        for case in cases():
            require(
                shutil.disk_usage("/dev/shm").free >= 1100 * 1024**2,
                "Need1100MiB RAM filesystem before each40ns case",
            )
            d = output / case["name"]
            d.mkdir()
            text = circuit(case)
            hbts = driver.contract(text, 4)
            (d / prior.FILE).write_text(text)
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
            old_tran = "tran 5e-13 12n 0 5e-13"
            new_tran = f"tran {case['step_s']:.12g} 40n 0 {case['step_s']:.12g}"
            require(
                previous_deck.count(old_tran) == 1
                and (d / "bench.cir").read_text()
                == previous_deck.replace(old_tran, new_tran),
                "Native prior-to-new deck differs beyond stop/time step",
            )
            row = dict(
                case=case, actual_hbt_count=len(hbts), prior12ns_deck_bridge=True
            )
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
                    d / "initial-op.dat", prior.vectors(hbts)
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
                with lzma.open(d / "wave.dat.xz", "rb") as src:
                    import hashlib

                    h = hashlib.sha256()
                    for block in iter(lambda: src.read(1024**2), b""):
                        h.update(block)
                require(
                    h.hexdigest() == row["uncompressed_wave_sha256"],
                    "Lossless native wave compression",
                )
                wave.unlink()
            row["outputs"] = {p.name: old.sha(p) for p in d.iterdir() if p.is_file()}
            save()
            print(
                case["name"],
                row.get("error"),
                row.get("measurement", {}).get("limited_thermal_screen_pass"),
                flush=True,
            )
        require(
            all(old.sha(Path(p)) == h for p, h in pins.items()), "Native inputs changed"
        )
        record["pair_agreement"] = pair_agreement(record["cases"])
        good = (
            all(
                r.get("clean_initialization")
                and r.get("measurement", {}).get("limited_thermal_screen_pass")
                for r in record["cases"]
            )
            and record["pair_agreement"]["pass_pair"]
        )
        record["status"] = (
            "PASS_LIMITED40NS_THERMAL_SCREEN"
            if good
            else "FAIL_LIMITED40NS_THERMAL_SCREEN"
        )
        record["source_bytes_unchanged"] = True
        save()
    except BaseException as error:
        record.update(status="INCOMPLETE_OR_ERROR", error=repr(error))
        save()
        raise
    finally:
        if previous is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = previous
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "startup", "capacitance", "out", "prior12"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.baseline, args.startup, args.capacitance, args.out, args.prior12)
    return int(result["status"] != "PASS_LIMITED40NS_THERMAL_SCREEN")


if __name__ == "__main__":
    raise SystemExit(main())
