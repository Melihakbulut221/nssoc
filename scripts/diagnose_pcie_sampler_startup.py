#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Three finite native DC-startup strategies; no model, tolerance or circuit change."""

import argparse
import gzip
import json
from pathlib import Path
import shutil
import tempfile

import characterize_pcie_sampler_v2 as s
import review_pcie_sampler_v2 as review

STRATEGIES = ("more_iterations", "physical_nodeset", "source_homotopy", "half_timestep")
MANUAL = "https://ngspice.sourceforge.io/docs/ngspice-manual.pdf"


def transformed_deck(original, strategy, initial):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown bounded startup strategy")
    text = original
    anchor = ".options reltol=1e-4 abstol=1e-12"
    if text.count(anchor) != 1 or text.count("tran 1e-12 ") != 1:
        raise ValueError("Exact original tolerances/time step required")
    if strategy == "more_iterations":
        text = text.replace(anchor, anchor + " itl1=1000")
    elif strategy == "physical_nodeset":
        # These are initial Newton guesses, released before the final DC solution.
        # They are not .ic values and are never used with UIC or a node clamp.
        old = ".nodeset v(ref)=.85 v(xrx.tail)=.5 v(op)=1.65 v(on)=1.65"
        if text.count(old) != 1 or set(initial) != set(s.NODES):
            raise ValueError("Exact physical node hints required")
        text = text.replace(
            old, ".nodeset " + " ".join(f"v({n})={initial[n]:.12g}" for n in s.NODES)
        )
    elif strategy == "source_homotopy":
        text = text.replace(
            anchor, anchor + " itl1=1000 noopiter gminsteps=0 srcsteps=1"
        )
    else:
        text = text.replace("tran 1e-12 ", "tran 5e-13 ").replace(
            " 0 1e-12\n", " 0 5e-13\n"
        )
    # Explicit independently solved DC result is retained as well as transient data.
    text = text.replace(
        "tran ", "op\nwrdata dc.dat " + " ".join(s.VECTORS) + "\ntran ", 1
    )
    return text


def run(directory, output):
    root, out = Path(directory).resolve(), Path(output).resolve()
    if out.exists() or not out.is_relative_to(Path("/dev/shm")):
        raise ValueError("Fresh /dev/shm output required")
    record = json.loads((root / "result.json").read_text())
    review.source_contract(record)
    name = review.selected_wave(record)
    original = next(r for r in record["cases"] if r["case"]["name"] == name)
    if (
        original["case"]["temp"] != 125
        or original["numerical_diagnostics"]["numerical_clean"]
    ):
        raise ValueError("Expected actual hot numerical-residual case")
    pins = dict(record["source_sha256"])
    for p in (
        Path(__file__).resolve(),
        Path(review.__file__).resolve(),
        root / "result.json",
        root / "r3_cmc.osdi",
    ):
        pins[str(p)] = review.digest(p)
    for f, sha in original["output_sha256"].items():
        review.verify(root / name / f, sha)
    out.mkdir()
    with tempfile.TemporaryDirectory(
        prefix="sampler-initial-", dir="/dev/shm"
    ) as scratch:
        wave = Path(scratch) / "wave.dat"
        s.diagnostics.unpack_wave(
            root / name / "wave.dat.gz", wave, original["wave_sha256"]
        )
        table = s.rx.rx.read_table(wave, ["time", *s.VECTORS])
    initial = {n: table[f"v({n})"][0] for n in s.NODES}
    result = dict(
        status="RUNNING",
        source_sha256=pins,
        baseline_case=original["case"],
        baseline_measurement=original["measurement"],
        baseline_wave_sha256=original["wave_sha256"],
        initial_newton_hints=initial,
        strategies=[],
        reference=MANUAL,
        limitations=[
            "Three nonlinear initialization strategies only; no tolerance, circuit, foundry model or source changes.",
            "Nodeset values are hints derived from the prior converged initial DC branch, not independent physical measurements or forced states.",
            "The standard time step is compared to a separately solved half-step transient; no full PVT clean-startup claim.",
        ],
    )

    def save():
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    save()
    try:
        for strategy in STRATEGIES:
            dest = out / strategy
            dest.mkdir()
            for f in (s.NETLIST.name, s.rx.NETLIST.name):
                shutil.copyfile(root / name / f, dest / f)
            original_deck = (root / name / "bench.cir").read_text()
            (dest / "bench.cir").write_text(
                transformed_deck(original_deck, strategy, initial)
            )
            row = dict(strategy=strategy)
            result["strategies"].append(row)
            save()
            try:
                row["execution"] = s.rx.execute(
                    original["execution"]["command"], dest, dest / "run.log"
                )
            except RuntimeError as exc:
                # The old execution helper deliberately raises on a native error.
                # Preserve that failed strategy and continue to the independent
                # half-step comparator; never synthesize missing measurements.
                row["native_failure"] = str(exc)
                row["attempted_command"] = original["execution"]["command"]
                row["numerical_diagnostics"] = s.diagnostics.diagnostics(
                    (dest / "run.log").read_text()
                )
                row["output_sha256"] = {
                    p.name: review.digest(p) for p in dest.iterdir()
                }
                save()
                print(strategy, "NATIVE_SOLVER_FAILURE_PRESERVED", flush=True)
                continue
            row["measurement"] = s.measure(dest / "wave.dat", original["case"])
            row["numerical_diagnostics"] = s.diagnostics.diagnostics(
                (dest / "run.log").read_text()
            )
            row["wave_sha256"] = review.digest(dest / "wave.dat")
            # DC table has one point and native wr_singlescale; retain raw bytes and check every numeric field.
            lines = (dest / "dc.dat").read_text().splitlines()
            import math

            values = [float(v) for line in lines[1:] for v in line.split()]
            row["dc_finite"] = bool(values) and all(math.isfinite(v) for v in values)
            row["margin_delta_v"] = (
                row["measurement"]["min_signed_margin_v"]
                - original["measurement"]["min_signed_margin_v"]
            )
            row["min_vce_delta_v"] = min(
                d["min_vce_v"] for d in row["measurement"]["devices"].values()
            ) - min(d["min_vce_v"] for d in original["measurement"]["devices"].values())
            with (
                (dest / "wave.dat").open("rb") as src,
                gzip.open(dest / "wave.dat.gz", "wb", compresslevel=1) as dst,
            ):
                shutil.copyfileobj(src, dst)
            (dest / "wave.dat").unlink()
            row["output_sha256"] = {p.name: review.digest(p) for p in dest.iterdir()}
            print(
                strategy,
                row["measurement"]["screen_pass"],
                row["numerical_diagnostics"],
                flush=True,
            )
            save()
        for path, sha in pins.items():
            review.verify(path, sha)
        result["source_bytes_unchanged"] = True
        result["native_failed_strategies"] = [
            r["strategy"] for r in result["strategies"] if "native_failure" in r
        ]
        result["clean_strategies"] = [
            r["strategy"]
            for r in result["strategies"]
            if "measurement" in r
            and r["numerical_diagnostics"]["numerical_clean"]
            and r["dc_finite"]
            and r["measurement"]["screen_pass"]
        ]
        result["status"] = (
            "BOUNDED_CLEAN_STARTUP_OBSERVED_NOT_PVT_QUALIFIED"
            if result["clean_strategies"]
            else "NUMERICAL_RESIDUAL_PRESERVED_AFTER_THREE_STRATEGIES"
        )
    except BaseException as exc:
        result.update(status="ERROR_PRESERVED", error=repr(exc))
        raise
    finally:
        save()
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = run(args.directory, args.out)
    print(result["status"])
    return 0 if result["clean_strategies"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
