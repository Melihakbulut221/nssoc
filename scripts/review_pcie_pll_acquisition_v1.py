#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Lossless public replay plus independent edge analysis of completed1us captures.

Full-device reductions reuse frozen formulas and are labeled author replay.
The vector edge/monotone ordinal/window calculation below is separate from the
producer. Numeric comparison allowances cover binary64 algebra only; every
physical acceptance predicate must match exactly. No new SPICE is launched.
"""

import argparse
import hashlib
import io
import json
import lzma
from pathlib import Path
import sys
import urllib.request

import numpy as np

import characterize_pcie_pll_acquisition_v1 as producer

PRODUCER_SHA = "ea34d89dc062a515727814b5549d28c4036ca030d39d966aacf605a8691ac649"
require = producer.require
MAX_PART = 16 * 1024**2


def independent_edges(times, voltage):
    require(
        len(times) == len(voltage) and len(times) >= 2, "Complete independent vectors"
    )
    require(
        np.isfinite(times).all() and np.isfinite(voltage).all(),
        "Finite independent vectors",
    )
    require(np.all(np.diff(times) > 0), "Independent strict time order")
    indices = np.flatnonzero((voltage[:-1] < 1.25) & (voltage[1:] >= 1.25))
    fraction = (1.25 - voltage[indices]) / (voltage[indices + 1] - voltage[indices])
    return times[indices] + fraction * (times[indices + 1] - times[indices])


def monotone_ordinals(reference, feedback):
    require(
        len(reference) >= 2 and np.all(np.diff(reference) > 0),
        "Ordered actual reference",
    )
    require(np.all(np.diff(feedback) > 0), "Ordered actual feedback")
    indices = []
    current = 0
    for edge in feedback:
        while current + 1 < len(reference) and abs(reference[current + 1] - edge) < abs(
            reference[current] - edge
        ):
            current += 1
        indices.append(current)
    return np.asarray(indices, dtype=np.int64)


def independent_analysis(data):
    times = data["time"]
    require(
        times[0] == 0 and abs(times[-1] - 1e-6) <= 16 * np.spacing(1e-6),
        "Full independent1us interval",
    )
    reference = independent_edges(times, data["v(reference)"])
    feedback = independent_edges(times, data["v(fb)"])
    indices = monotone_ordinals(reference, feedback)
    phase = feedback - reference[indices]
    windows = []
    for start_ns in range(100, 901, 10):
        start, stop = start_ns / 1e9, (start_ns + 100) / 1e9
        chosen = (feedback >= start) & (feedback < stop)
        edges, ordinal, angles = feedback[chosen], indices[chosen], phase[chosen]
        periods = np.diff(edges)
        frequency = 1 / float(np.mean(periods)) if len(periods) else None
        span = float(np.ptp(angles)) if len(angles) else None
        sampled = (times >= start) & (times <= stop)
        require(sampled.any(), "Actual samples in every independent window")
        control = data["v(vctrl)"][sampled]
        bounds = [float(np.min(control)), float(np.max(control))]
        checks = dict(
            frequency_100ppm=frequency is not None
            and abs(frequency / 1e8 - 1) <= 100e-6,
            phase_range_50ps=span is not None and span <= 50e-12,
            unique_successive_reference_no_slip=len(edges) >= 9
            and bool(np.all(np.abs(angles) < 5e-9))
            and bool(np.all(np.diff(ordinal) == 1)),
            control_development_window=0.4 <= bounds[0] <= bounds[1] <= 1.5,
        )
        windows.append(
            dict(
                interval_s=[start, stop],
                frequency_hz=frequency,
                phase_span_s=span,
                phase_s=angles.tolist(),
                reference_indices=ordinal.tolist(),
                control_range_v=bounds,
                checks=checks,
                passed=all(checks.values()),
            )
        )
    starts = [
        x["interval_s"][0]
        for i, x in enumerate(windows)
        if all(w["passed"] for w in windows[i:])
    ]
    suffix = min(starts) if starts else None
    final_indices = np.r_[
        windows[70]["reference_indices"], windows[80]["reference_indices"]
    ]
    no_slip = len(final_indices) >= 18 and bool(np.all(np.diff(final_indices) == 1))
    passed = (
        windows[70]["passed"]
        and windows[80]["passed"]
        and no_slip
        and suffix is not None
        and suffix <= 800e-9
    )
    return dict(
        passed=passed,
        rolling_windows=windows,
        reference_edges_s=reference.tolist(),
        feedback_edges_s=feedback.tolist(),
        reference_ordinals=indices.tolist(),
        ordinal_deltas=np.diff(indices).tolist(),
        phase_s=phase.tolist(),
        final_two_windows_no_slip=no_slip,
        sustained_window_start_s=suffix,
        sustained_confirmation_s=None if suffix is None else suffix + 100e-9,
    )


def compare_independent(actual, recorded):
    for key in [
        "passed",
        "final_two_windows_no_slip",
        "sustained_window_start_s",
        "sustained_confirmation_s",
    ]:
        require(
            actual[key] == recorded[key], "Independent acquisition predicate: " + key
        )
    require(
        len(actual["rolling_windows"]) == len(recorded["rolling_windows"]) == 81,
        "All independent windows",
    )
    require(
        actual["reference_ordinals"]
        == [x["reference_ordinal"] for x in recorded["all_edge_pairings"]],
        "Every independent ordinal",
    )
    # Reordering mathematically identical interpolation/averaging expressions may
    # differ by a few binary64 ULPs. This comparison never changes physical gates.
    time_tolerance = 64 * np.spacing(1e-6)
    maximum_time_difference = 0.0
    for key in ["reference_edges_s", "feedback_edges_s"]:
        a, b = np.asarray(actual[key]), np.asarray(recorded[key])
        require(a.shape == b.shape, "Independent full edge census")
        delta = float(np.max(np.abs(a - b))) if len(a) else 0.0
        require(delta <= time_tolerance, "Independent edge arithmetic agreement")
        maximum_time_difference = max(maximum_time_difference, delta)
    for a, b in zip(actual["rolling_windows"], recorded["rolling_windows"]):
        for key in [
            "interval_s",
            "reference_indices",
            "control_range_v",
            "checks",
            "passed",
        ]:
            require(a[key] == b[key], "Independent window predicate: " + key)
        if a["frequency_hz"] is None or b["frequency_hz"] is None:
            require(
                a["frequency_hz"] is b["frequency_hz"], "Independent missing frequency"
            )
        else:
            require(
                abs(a["frequency_hz"] - b["frequency_hz"])
                <= 64 * np.spacing(abs(b["frequency_hz"])),
                "Independent frequency arithmetic",
            )
        if a["phase_span_s"] is None or b["phase_span_s"] is None:
            require(a["phase_span_s"] is b["phase_span_s"], "Independent missing phase")
        else:
            require(
                abs(a["phase_span_s"] - b["phase_span_s"]) <= time_tolerance,
                "Independent phase span arithmetic",
            )
        require(
            np.asarray(a["phase_s"]).shape == np.asarray(b["phase_s"]).shape
            and np.all(
                np.abs(np.asarray(a["phase_s"]) - np.asarray(b["phase_s"]))
                <= time_tolerance
            ),
            "Independent all phase samples",
        )
    return dict(
        all_predicates_exact=True,
        maximum_edge_difference_s=maximum_time_difference,
        algebraic_time_tolerance_s=float(time_tolerance),
        scope="Binary64 expression-order comparison only; all100ppm/50ps/control/ordinal decisions must be exactly equal",
    )


def decode_part(packed, part, columns):
    require(0 < part["rows"] <= MAX_PART // (columns * 8), "Bounded native part rows")
    require(
        len(packed) == part["bytes"] <= MAX_PART + 1024
        and hashlib.sha256(packed).hexdigest() == part["sha256"],
        "Compressed part identity",
    )
    decompressor = lzma.LZMADecompressor(memlimit=64 * 1024**2)
    raw = decompressor.decompress(packed, max_length=MAX_PART + 1)
    require(
        decompressor.eof and not decompressor.unused_data,
        "One complete bounded LZMA stream",
    )
    require(
        len(raw) == part["uncompressed_bytes"] == part["rows"] * columns * 8 <= MAX_PART
        and hashlib.sha256(raw).hexdigest() == part["uncompressed_sha256"],
        "Complete raw part identity",
    )
    block = np.frombuffer(raw, "<f8").reshape(part["rows"], columns)
    require(np.isfinite(block).all(), "Every actual raw value finite")
    return raw, block


def bind_completed_capture(path, digest, prior):
    """Audit completed PASS or FAIL without promoting a failed physical screen."""
    n, previous, runtime = producer.n, producer.previous, producer.runtime
    stop = 1e-6
    path = Path(path)
    require(
        n.common.sha(path) == digest, "Externally pinned completed native prerequisite"
    )
    record = json.loads(path.read_text())
    require(
        record["status"]
        in ("PASS_NATIVE_STREAM_FINITE_SCREEN", "FAIL_NATIVE_STREAM_FINITE_SCREEN"),
        "Completed finite native prerequisite",
    )
    require(
        record["config"]["step_s"] in (5e-12, 2.5e-12)
        and record["config"]["stop_s"] == stop,
        "Exact prerequisite analysis",
    )
    require(
        record["devices"] == prior["devices"] and len(record["devices"]) == 539,
        "Unchanged539-device graph",
    )
    require(
        record["config"]["sources"] == prior["config"]["sources"]
        and record["config"]["fixture"] == prior["config"]["fixture"],
        "Exact physical sources and external stimuli",
    )
    expected_config = dict(prior["config"])
    expected_config.update(
        case="connected_physical_loop_acquisition1us",
        step_s=record["config"]["step_s"],
        stop_s=stop,
        window_s=[4e-9, stop],
    )
    require(record["config"] == expected_config, "Exact complete acquisition config")
    original = producer.previous.previous.ORIGINAL
    require(
        (path.parent / "bench.cir").read_text()
        == producer.stream_deck(
            (original / "bench.cir").read_text(), record["config"]["step_s"], stop
        ),
        "Exact regenerated acquisition deck",
    )
    for name in {"spinit"} | {Path(p).name for p in prior["config"]["sources"]}:
        require(
            (path.parent / name).read_bytes() == (original / name).read_bytes(),
            "Exact copied physical circuit/startup file: " + name,
        )
    required_inputs = set(prior["inputs"]) | {
        str(Path(previous.__file__).resolve()),
        str(Path(previous.previous.__file__).resolve()),
        str(Path(runtime.__file__).resolve()),
    }
    if stop == 1e-6:
        required_inputs.add(str(Path(producer.__file__).resolve()))
    require(
        required_inputs <= set(record["inputs"]),
        "Complete required source/model/runtime inventory",
    )
    require(
        all(record["inputs"][p] == v for p, v in prior["inputs"].items()),
        "Inherited source/model/runtime identity",
    )
    required_outputs = {
        "bench.cir",
        "spinit",
        "execution.json",
        "run.log",
        "op.raw",
        "owned-processes.json",
        "capture/capture.json",
        "capture/header.bin",
        "capture/trailer.bin",
        "capture/parts/parts.json",
    } | {Path(p).name for p in prior["config"]["sources"]}
    require(
        required_outputs <= set(record["outputs"]),
        "Complete required native output inventory",
    )
    for name in {"bench.cir", "spinit"} | {
        Path(p).name for p in prior["config"]["sources"]
    }:
        require(
            record["inputs"].get(str((path.parent / name).resolve()))
            == record["outputs"][name],
            "Pre/post-native generated input binding",
        )
    require(
        len(record["safety"]["all_device_bounds"]) == 539,
        "All539 stored electrical records",
    )
    recomputed = []
    for device, bound in zip(prior["devices"], record["safety"]["all_device_bounds"]):
        require(
            (device["path"], device["model"]) == (bound["path"], bound["model"]),
            "Every stored device bound is bound to the graph",
        )
        if device["model"] == "npn13g2":
            passed = (
                bound["min_settled_vce"] >= 0.4
                and bound["max_capture_vce"] <= 1.6
                and bound["max_capture_ic_per_nx"] <= 0.003
            )
        else:
            limit = 1.5 if "_lv_" in device["model"] else 3.3
            passed = (
                bound["voltage_limit"] == limit
                and bound["max_capture_terminal_difference"] <= limit
                and bound.get("max_capture_drain_per_um", 0) <= 0.002
            )
        require(
            type(bound["passed"]) is bool and bound["passed"] == passed,
            "Stored electrical verdict equals recomputed bounds",
        )
        recomputed.append(passed)
    electrical = all(recomputed) and not record["safety"]["model_geometry_range_issues"]
    require(
        type(record["safety"]["passed"]) is bool
        and record["safety"]["passed"] == electrical,
        "Stored aggregate electrical verdict",
    )
    accepted = electrical and record["measurement"]["passed"]
    expected_status = (
        "PASS_NATIVE_STREAM_FINITE_SCREEN"
        if accepted
        else "FAIL_NATIVE_STREAM_FINITE_SCREEN"
    )
    require(
        record["status"] == expected_status, "Original physical verdict remains exact"
    )
    expected_flags = [
        "q." + device["path"] + ".qnpn13g2"
        for device in prior["devices"]
        if device["model"] == "npn13g2"
    ]
    require(
        record["zero_source_op"]
        and len(expected_flags) == 64
        and record["native_off_flags"] == expected_flags
        and record.get(
            "strict_numerical_diagnostics_pass", record.get("clean_diagnostics", False)
        ),
        "Prerequisite OP/OFF/numerics",
    )
    paths = [str(path)]
    for source, pin in record["inputs"].items():
        require(n.common.pin(source) == pin, "Prerequisite input drift: " + source)
        paths.append(source)
    for name, pin in record["outputs"].items():
        target = path.parent / name
        require(
            not Path(name).is_absolute()
            and target.resolve().is_relative_to(path.parent.resolve()),
            "Output remains within capture",
        )
        require(n.common.pin(target) == pin, "Prerequisite output drift: " + name)
        paths.append(str(target))
    require(
        json.loads((path.parent / "execution.json").read_text())["returncode"] == 0,
        "Native prerequisite actually exited0",
    )
    return paths


def review(folder, expected_sha, output):
    producer.runtime.check_runtime(
        sys.version_info, np.__version__, callable(getattr(np, "trapezoid", None))
    )
    require(
        producer.n.common.sha(producer.__file__) == PRODUCER_SHA,
        "Frozen acquisition producer",
    )
    require(not output.exists(), "Fresh independent review output")
    result_path = folder / "result.json"
    record = json.loads(result_path.read_text())
    prior = producer.verify_parent()
    paths = bind_completed_capture(result_path, expected_sha, prior)
    inputs = {
        str(Path(p).resolve()): producer.n.common.pin(p)
        for p in [*paths, __file__, producer.__file__]
    }
    require(record["config"]["step_s"] in [5e-12, 2.5e-12], "Declared native step")
    for key, value in producer.startup_proof(folder, prior).items():
        require(record[key] == value, "Reparsed actual startup/diagnostics: " + key)
    header, trailer = (
        (folder / "capture/header.bin").read_bytes(),
        (folder / "capture/trailer.bin").read_bytes(),
    )
    _, meta = producer.namespace["life"].tiny.parse_header(
        io.BytesIO(header),
        producer.n.vectors(record["devices"], record["config"]["extra_vectors"]),
    )
    columns = meta["columns"]
    require(
        columns == record["columns"] and len(columns) == 826, "Exact full column table"
    )
    ledger = json.loads((folder / "capture/parts/parts.json").read_text())
    require(
        ledger["status"] == "PASS_PUBLISHED_PARTS" and ledger["columns"] == columns,
        "Complete published capture ledger",
    )
    meter = producer.previous.Meter(columns, record["devices"], record["config"])
    order = producer.previous.canonical_indices(columns)
    raw_hash, payload_hash, canonical_hash = (
        hashlib.sha256(header),
        hashlib.sha256(),
        hashlib.sha256(),
    )
    count = 0
    for index, part in enumerate(ledger["parts"]):
        require(
            part["index"] == index
            and part["first_row"] == count
            and part["status"] == "PUBLIC_VERIFIED",
            "Contiguous published parts",
        )
        receipt = folder / "capture/parts" / f"publication-{index:05d}.json"
        require(
            producer.n.common.sha(receipt) == part["receipt_sha256"],
            "Bound publication receipt",
        )
        publication = json.loads(receipt.read_text())
        asset = part["asset"]
        require(
            publication["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
            and publication["assets"] == [asset]
            and asset["authenticated_roundtrip"]
            and asset["anonymous_roundtrip"],
            "Exact dual-roundtrip asset",
        )
        require(
            asset["name"] == part["name"]
            and asset["bytes"] == part["bytes"]
            and asset["sha256"] == part["sha256"],
            "Asset/ledger identity",
        )
        with urllib.request.urlopen(asset["url"], timeout=120) as response:
            packed = response.read(MAX_PART + 1025)
        raw, block = decode_part(packed, part, len(columns))
        raw_hash.update(raw)
        payload_hash.update(raw)
        canonical_hash.update(block.view("<u8")[:, order].tobytes())
        meter.push(block)
        count += len(block)
        print(f"VERIFIED_PART {index} rows={count}", flush=True)
    require(trailer == str(count).encode(), "Exact nonseekable native count trailer")
    raw_hash.update(trailer)
    require(
        raw_hash.hexdigest() == record["raw_sha256"]
        and payload_hash.hexdigest() == record["payload_sha256"]
        and canonical_hash.hexdigest() == record["canonical_payload_sha256"],
        "All original binary64 bits exact",
    )
    safety, data, grid = meter.finish()
    require(
        count == record["rows"] and count * len(columns) == record["values"],
        "Exact full capture size",
    )
    require(
        safety == record["safety"]
        and grid == record["time_grid"]
        and producer.measurements(data, record["config"]) == record["measurement"],
        "All frozen author reductions exact",
    )
    independent = independent_analysis(data)
    agreement = compare_independent(independent, record["measurement"]["acquisition"])
    require(
        all(producer.n.common.pin(p) == pin for p, pin in inputs.items()),
        "Post-replay source/output drift",
    )
    result = dict(
        status="PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC",
        native_result=producer.n.common.pin(result_path),
        native_authoritative_status=record["status"],
        inputs=inputs,
        parts=len(ledger["parts"]),
        rows=count,
        values=count * len(columns),
        all539_author_safety_records_exact=True,
        full_raw_sha256=raw_hash.hexdigest(),
        canonical_payload_sha256=canonical_hash.hexdigest(),
        independent=independent,
        agreement=agreement,
        no_new_native=True,
        scope="Full-device replay reuses frozen safety formulas; independent scope is all actual reference/feedback edges and acquisition windows. Original DUT verdict remains authoritative, no new lock/PVT/jitter/thermal/layout/SOA claim.",
    )
    producer.n.common.atomic(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--result-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = review(args.capture, args.result_sha, args.out)
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
