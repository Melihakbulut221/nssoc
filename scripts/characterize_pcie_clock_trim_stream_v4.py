#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive mean/envelope screen; no full waveform stationarity acceptance."""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import struct
import sys

import numpy as np
import characterize_pcie_clock_trim_stream_v3 as previous

lifecycle, base, tiny = previous.lifecycle, previous.base, previous.tiny
sha, require, atomic = previous.sha, previous.require, previous.atomic
PartQueue, STOP, MIN_FREE_BYTES = (
    previous.PartQueue,
    previous.STOP,
    previous.MIN_FREE_BYTES,
)
verify_pins, bind_generated, classify_log = (
    previous.verify_pins,
    previous.bind_generated,
    previous.classify_log,
)
NG47_SHA = previous.NG47_SHA
PREVIOUS_SHA = "2655b9dc54e6cfc5554ee30fc1aa15966d3d9ae94933fb492a75607ac2e32224"
# Filled only after the currently running source-frozen full31part replay seals.
FIRST_REPLAY_SHA = "c4d5ed65ed2677776814450c7c3918256d4e6f3e3663ccb3ba8ef3b9f6662a53"


def envelopes(times, clock, thermal, stop):
    times, clock = np.asarray(times, dtype=float), np.asarray(clock, dtype=float)
    require(
        times.ndim == clock.ndim == 1 and len(times) == len(clock),
        "Complete scalar clock vectors",
    )
    require(
        np.isfinite(times).all()
        and np.isfinite(clock).all()
        and np.all(np.diff(times) > 0),
        "Finite strictly ordered native clock",
    )
    require(
        times[0] <= stop - 8e-9 < stop <= times[-1], "Complete fixed8ns envelope window"
    )
    require(len(thermal) == 53, "All53 thermal envelopes")
    ix = np.flatnonzero((clock[:-1] <= 0) & (clock[1:] > 0))
    edges = times[ix] - clock[ix] * np.diff(times)[ix] / (clock[ix + 1] - clock[ix])
    edges = edges[(edges >= stop - 8e-9) & (edges <= stop)]
    require(len(edges) >= 4, "At least three complete envelope cycles")
    centers = (edges[:-1] + edges[1:]) / 2
    rows = {}
    for name, values in sorted(thermal.items()):
        values = np.asarray(values, dtype=float)
        require(
            values.ndim == 1
            and len(values) == len(times)
            and np.isfinite(values).all(),
            "Complete finite thermal state",
        )
        lows, highs = [], []
        for a, b in zip(edges[:-1], edges[1:]):
            lo, hi = np.searchsorted(times, [a, b], side="right")
            v = np.concatenate(
                (
                    [np.interp(a, times, values)],
                    values[lo:hi],
                    [np.interp(b, times, values)],
                )
            )
            lows.append(float(v.min()))
            highs.append(float(v.max()))
        metrics = {}
        for label, points in [("minima", lows), ("maxima", highs)]:
            points = np.asarray(points)
            rates = np.abs(np.diff(points) / np.diff(centers)) * 1e-9
            blocks = []
            counts = []
            for i in range(4):
                mask = (centers >= stop - 8e-9 + i * 2e-9) & (
                    centers < stop - 8e-9 + (i + 1) * 2e-9
                )
                require(
                    np.count_nonzero(mask) >= 2,
                    "Complete envelope cycles in every fixed2ns block",
                )
                blocks.append(
                    float(
                        np.max(
                            np.abs(np.diff(points[mask]) / np.diff(centers[mask]))
                            * 1e-9
                        )
                    )
                )
                counts.append(int(np.count_nonzero(mask)))
            metrics[label] = dict(
                values_k=points.tolist(),
                max_abs_adjacent_rate_k_per_ns=float(rates.max()),
                fixed2ns_max_rates_k_per_ns=blocks,
                fixed2ns_cycles=counts,
                span_k=float(points.max() - points.min()),
            )
        rows[name] = metrics
    checks = dict(
        all_cycle_extrema_rates_within_original_limit=all(
            m["max_abs_adjacent_rate_k_per_ns"] <= base.THERMAL_RATE_V_PER_NS
            for row in rows.values()
            for m in row.values()
        ),
        all_fixed_block_extrema_rates_nonincreasing_with_original_tolerance=all(
            all(
                b <= a + base.RATE_INCREASE_TOLERANCE_V_PER_NS
                for a, b in zip(
                    m["fixed2ns_max_rates_k_per_ns"],
                    m["fixed2ns_max_rates_k_per_ns"][1:],
                )
            )
            for row in rows.values()
            for m in row.values()
        ),
    )
    return dict(
        declared_window_s=[stop - 8e-9, stop],
        complete_cycle_window_s=[float(edges[0]), float(edges[-1])],
        centers_s=centers.tolist(),
        cycles=len(centers),
        thermal_nodes=rows,
        checks=checks,
        pass_envelope_screen=all(checks.values()),
        rate_limit_k_per_ns=base.THERMAL_RATE_V_PER_NS,
        nonincrease_tolerance_k_per_ns=base.RATE_INCREASE_TOLERANCE_V_PER_NS,
        scope="Saved-sample extrema of complete clock cycles, with interpolated boundaries. Bounds cycle mean and envelope evolution only; not full phase-profile stationarity, infinite-time equilibrium, or between-sample extrema proof.",
    )


class Meter(previous.Meter):
    def finish(self):
        value = super().finish()
        d = self.phase_data
        envelope = envelopes(
            d["time"],
            np.asarray(d["v(clkp)"]) - np.asarray(d["v(clkn)"]),
            {n: d[n] for n in self.phase_names[3:]},
            self.stop,
        )
        value["thermal_envelope"] = envelope
        value["bounded_mean_envelope_screen_pass"] = (
            value["phase_invariant_screen_pass"] and envelope["pass_envelope_screen"]
        )
        return value


def capture_stream(
    stream,
    output,
    expected,
    hbts,
    case,
    prefix,
    stop=STOP,
    publisher=None,
    rows_per_part=previous.previous.PART_ROWS,
    reclaim=True,
    min_free_bytes=MIN_FREE_BYTES,
):
    require(sys.byteorder == "little", "Pinned x86 binary format")
    output = Path(output)
    output.mkdir()
    header, meta = tiny.parse_header(stream, expected)
    require(meta["declared_points"] == 0, "Native nonseekable zero-count header")
    (output / "header.bin").write_bytes(header)
    meter = Meter(meta["columns"], hbts, case, stop)
    queue = PartQueue(
        output / "parts",
        prefix,
        meta["columns"],
        publisher,
        rows_per_part,
        reclaim,
        min_free_bytes,
    )
    decoder = struct.Struct("<" + "d" * len(meta["columns"]))
    pending, raw_hash = bytearray(), hashlib.sha256(header)
    try:
        while data := stream.read(65536):
            raw_hash.update(data)
            pending.extend(data)
            count = len(pending) // decoder.size
            for i in range(count):
                sample = bytes(pending[i * decoder.size : (i + 1) * decoder.size])
                meter.push(decoder.unpack(sample))
                queue.append(sample)
            del pending[: count * decoder.size]
        trailer = bytes(pending)
        (output / "trailer.bin").write_bytes(trailer)
        require(
            trailer == str(queue.rows).encode(), "Exact completed native count trailer"
        )
        measurement = meter.finish()
        ledger = queue.finish()
        result = dict(
            **meta,
            rows=queue.rows,
            stop_s=stop,
            step_s=case["step_s"],
            raw_sha256=raw_hash.hexdigest(),
            payload_sha256=ledger["payload_sha256"],
            header_sha256=sha(output / "header.bin"),
            trailer_sha256=sha(output / "trailer.bin"),
            ledger_sha256=sha(output / "parts/parts.json"),
            measurement=measurement,
            status="PASS_COMPLETE_CAPTURE",
            live_release_publication=type(publisher) is lifecycle.OwnedPublisher,
            semantic_screen_pass=measurement["bounded_mean_envelope_screen_pass"],
        )
        atomic(output / "capture.json", result)
        return result
    except BaseException as error:
        atomic(
            output / "failure.json",
            dict(
                status="INCOMPLETE_OR_INVALID_CAPTURE",
                error=repr(error),
                observed_rows=queue.rows,
                completed_parts=len(queue.parts),
            ),
        )
        raise


def first_evidence(replay, part):
    """Bind fulltime v3 replay to an additional exact raw final-tail envelope."""
    replay, part = Path(replay).resolve(), Path(part).resolve()
    require(sha(previous.__file__) == PREVIOUS_SHA, "Frozen previous reducer")
    require(
        sha(replay / "result.json") == FIRST_REPLAY_SHA,
        "Exact completed full31part replay",
    )
    record = json.loads((replay / "result.json").read_text())
    require(
        record["status"] == "PASS_V3_FIRST_CAPTURE_REPLAY"
        and record["rows"] == 2000011
        and len(record["parts"]) == 31,
        "Complete first mean-only replay",
    )
    pins = dict(record["source_sha256"])
    verify_pins(pins)
    require(
        pins[str(Path(previous.__file__).resolve())] == PREVIOUS_SHA,
        "Previous reducer source binding",
    )
    original = Path(record["original_result_path"])
    prior = json.loads(original.read_text())
    row = prior["cases"][0]
    cap = row["capture"]
    folder = original.parent / row["case"]["name"]
    ledger_path = folder / "capture/parts/parts.json"
    require(sha(ledger_path) == cap["ledger_sha256"], "Exact original ledger")
    ledger = json.loads(ledger_path.read_text())
    p = ledger["parts"][-1]
    require(
        p["index"] == 30
        and p["first_row"] + p["rows"] == record["rows"]
        and p["rows"] == 33931,
        "Exact final part coverage",
    )
    require(
        part.stat().st_size == p["bytes"] and sha(part) == p["sha256"],
        "Exact compressed last part",
    )
    with lzma.open(part, "rb") as f:
        raw = f.read(p["uncompressed_bytes"] + 1)
    require(
        len(raw) == p["uncompressed_bytes"] == p["rows"] * 167 * 8
        and hashlib.sha256(raw).hexdigest() == p["uncompressed_sha256"],
        "Exact last-part raw payload",
    )
    columns = ledger["columns"]
    require(
        columns == cap["columns"] and len(set(columns)) == len(columns) == 167,
        "Exact167-column native interface",
    )
    matrix = np.frombuffer(raw, dtype="<f8").reshape((p["rows"], 167))
    require(np.isfinite(matrix).all(), "All finite last-part native values")
    data = dict(zip(columns, matrix.T))
    times = data["time"]
    clock = data["v(clkp)"] - data["v(clkn)"]
    require(
        times[-1] == STOP
        and times[0] < STOP - 8e-9
        and np.all(
            (np.diff(times) > 0) & (np.diff(times) <= 0.5e-12 + 4 * np.spacing(STOP))
        ),
        "Exact native tail time grid",
    )
    thermal = {n: data[n] for n in columns if n.endswith(".t)") or n.endswith(".dt)")}
    old_measurement = record["first_case"]["measurement"]
    phase = previous.phase_convergence(
        times, clock, thermal, STOP, old_measurement["convergence"]
    )
    require(
        phase == old_measurement["phase_convergence"],
        "Actual tail exactly reproduces full-replay cycle means",
    )
    envelope = envelopes(times, clock, thermal, STOP)
    measurement = dict(
        old_measurement,
        thermal_envelope=envelope,
        bounded_mean_envelope_screen_pass=old_measurement["phase_invariant_screen_pass"]
        and envelope["pass_envelope_screen"],
    )
    newrow = dict(record["first_case"], measurement=measurement)
    pins.update(
        {
            str(replay / "result.json"): FIRST_REPLAY_SHA,
            str(part): p["sha256"],
            str(Path(__file__).resolve()): sha(__file__),
        }
    )
    verify_pins(pins)
    return dict(
        status="PASS_V4_FIRST_MEAN_ENVELOPE_REVIEW"
        if measurement["bounded_mean_envelope_screen_pass"]
        else "FAIL_V4_FIRST_MEAN_ENVELOPE_SCREEN",
        source_sha256=pins,
        full_replay_path=str(replay),
        tail_part_path=str(part),
        first_case=newrow,
        fulltime_raw_replay_rows=record["rows"],
        first_replay_sha256=FIRST_REPLAY_SHA,
        additional_raw_tail=dict(
            rows=p["rows"], sha256=p["uncompressed_sha256"], local_hash_replay=True
        ),
        original_v2_status_preserved=record["original_v2_status_preserved"],
        v3_mean_only_result_preserved=True,
        second_native_started=False,
        scope="Source-bound fulltime electrical/clock coverage plus fixed final8ns mean and saved-sample cycle-extrema checks. No full phase-profile stationarity, infinite-time equilibrium,8GHz lock,PLL/CDR/PCIe or fullPEX acceptance.",
    )


def review_first(replay, part, output):
    output = Path(output).resolve()
    require(not output.exists(), "Fresh additive first review")
    result = first_evidence(replay, part)
    output.mkdir(parents=True)
    atomic(output / "result.json", result)
    return result


def bind_first(first):
    path = Path(first) / "result.json"
    record = json.loads(path.read_text())
    require(
        record["status"] == "PASS_V4_FIRST_MEAN_ENVELOPE_REVIEW",
        "Passing mean/envelope first review required",
    )
    expected = first_evidence(record["full_replay_path"], record["tail_part_path"])
    require(
        record == expected,
        "Exact regenerated first review including all bounds and source identities",
    )
    return record


def run_second(first, parent, output, prefix):
    first, parent, output = map(lambda p: Path(p).resolve(), (first, parent, output))
    prior_replay = bind_first(first)
    pins = dict(prior_replay["source_sha256"])
    verify_pins(pins)
    require(
        pins[str(Path(__file__).resolve())] == sha(__file__),
        "Same frozen v4 source as additive first review",
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh second-case output",
    )
    require(
        shutil.disk_usage("/dev/shm").free >= 1024**3, "Initial1GiB free-space gate"
    )
    previous_parent, old_pins = lifecycle.verify_parent(parent)
    for name, digest in old_pins.items():
        require(
            name in pins and pins[name] == digest,
            "Exact original40ns parent/source closure",
        )
    pins[str(first / "result.json")] = sha(first / "result.json")
    case = previous_parent["cases"][1]["case"]
    require(
        case["step_s"] == 0.25e-12
        and [prior_replay["first_case"]["case"], case] == base.cases(),
        "Original exact timestep pair",
    )
    runtime = next(
        Path(n) for n, h in pins.items() if Path(n).name == "ngspice" and h == NG47_SHA
    )
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(base.driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING_V4_SECOND_CASE",
        source_sha256=pins,
        cases=[prior_replay["first_case"]],
        original_v2_status="ERROR_INCOMPLETE",
        prior_failure_superseded=False,
    )
    atomic(output / "result.json", record)
    folder = output / case["name"]
    folder.mkdir()
    source = parent / case["name"]
    circuit = (source / base.prior.FILE).read_text()
    (folder / base.prior.FILE).write_text(circuit)
    (folder / "bench.cir").write_text(
        lifecycle.long_deck((source / "bench.cir").read_text(), case["step_s"])
    )
    expected_deck = lifecycle.long_deck(
        (source / "bench.cir").read_text(), case["step_s"]
    )
    pins.update(
        bind_generated(
            {
                folder / "bench.cir": expected_deck,
                folder / base.prior.FILE: circuit,
                output / "spinit": base.driver.parent.init.SPINIT,
                output / "producer.py": Path(__file__).read_text(),
            }
        )
    )
    verify_pins(pins)
    hbts = base.driver.contract(circuit, 4)
    expected = base.prior.vectors(hbts)
    row = dict(case=case, status="NATIVE_RUNNING")
    record["cases"].append(row)
    atomic(output / "result.json", record)
    try:
        cap, execution = lifecycle.native_wait(
            runtime,
            folder,
            folder / "run.log",
            lambda f, owner: capture_stream(
                f,
                folder / "capture",
                expected,
                hbts,
                case,
                prefix,
                publisher=lifecycle.OwnedPublisher(owner),
            ),
        )
        row.update(capture=cap, execution=execution, measurement=cap["measurement"])
        require(
            cap["live_release_publication"] is True, "Live public retention required"
        )
        row["native"] = classify_log(
            (folder / "run.log").read_text(),
            cap,
            hbts,
            sha(runtime),
            case["step_s"],
            execution["returncode"],
        )
        row["initial_op"] = base.driver.parent.init.startup.initial_op(
            folder / "initial-op.dat", expected
        )
        require(
            max(map(abs, row["initial_op"].values())) <= 1e-10,
            "Exact zero-source initialOP",
        )
        verify_pins(pins)
        row.update(
            status="COMPLETE",
            outputs={
                str(p.relative_to(folder)): sha(p)
                for p in folder.rglob("*")
                if p.is_file()
            },
        )
        record["pair_agreement"] = base.pair_agreement(record["cases"])
        record["status"] = (
            "PASS_V4_LIMITED_MEAN_ENVELOPE1US_PAIR"
            if all(
                c["measurement"]["bounded_mean_envelope_screen_pass"]
                for c in record["cases"]
            )
            and record["pair_agreement"]["pass_pair"]
            else "FAIL_V4_LIMITED_MEAN_ENVELOPE1US_PAIR"
        )
        record["scope"] = (
            "New finite mean/envelope pair only; no full phase-profile stationarity; no replacement of historicalFAIL, infinite-time equilibrium,8GHz lock,PLL/CDR/PCIe/fullPEX acceptance"
        )
        atomic(output / "result.json", record)
    except BaseException as error:
        record.update(status="ERROR_V4_INCOMPLETE", error=repr(error))
        atomic(output / "result.json", record)
        raise
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("review-first")
    for name in ("replay", "part", "out"):
        r.add_argument("--" + name, type=Path, required=True)
    n = sub.add_parser("run-second")
    for name in ("first", "parent", "out"):
        n.add_argument("--" + name, type=Path, required=True)
    n.add_argument("--release-prefix", required=True)
    a = ap.parse_args()
    result = (
        review_first(a.replay, a.part, a.out)
        if a.command == "review-first"
        else run_second(a.first, a.parent, a.out, a.release_prefix)
    )
    if result["status"] not in (
        "PASS_V4_FIRST_MEAN_ENVELOPE_REVIEW",
        "PASS_V4_LIMITED_MEAN_ENVELOPE1US_PAIR",
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
