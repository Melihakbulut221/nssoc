#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate 1us acquisition screen of the unchanged native 539-device loop.

Preserves both original400ns verdicts. Finite acquisition means consecutive
100ns windows on a10ns grid remain within the original100ppm/50ps bounds,
including fixed800--900ns and900--1000ns windows. It is not PLL signoff.
"""

import argparse
import bisect
import hashlib
import inspect
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

import characterize_pcie_pll_loop_stream_v2 as previous
import run_pcie_pll_loop_stream_v2 as runtime

PREVIOUS_SHA = "79de51fcd210e1141b187a3fc83546e9933b5d5c6c36a9d0bc85aa6a69d2da9d"
RUNTIME_SHA = "3cad570fec4c48e6d43b764810cca60ffc54b44d0ba2405254dbad6b21211fb8"
NG47_SHA = "eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8"
STOP = 1e-6
FREQUENCY_HZ = 1e8
FREQUENCY_RELATIVE_LIMIT = 100e-6
PHASE_RANGE_LIMIT_S = 50e-12
WARNING_SOURCE = {
    "debian_source": "47+ds-1~bpo13+1",
    "archive_sha256": "004b2f7af4c862ed56a89a353e87889b58c21a5a56d13f45a9138d681c3f5dad",
    "file": "src/frontend/outitf.c",
    "file_sha256": "995538492e4549ef42aecc74f3d3c1e95da279c029d959d62b27063c2adaeae2",
    "function": "OUTpBeginPlot",
    "lines": [131, 163],
    "preserved_source_capsule_sha256": "db37bede480cb2981ab003b6f04ac8199af54c70e1c7c4f9d5f270347c8e591c",
    "semantics": "Linux stop/step*columns*8 estimate ignores file/FIFO output; no error return or equation change",
}
require, n = previous.previous.require, previous.n
namespace = dict(previous.namespace)
namespace.update(__file__=__file__, __name__=__name__)
BRIDGES = {}


def verify_parent():
    require(n.common.sha(previous.__file__) == PREVIOUS_SHA, "Frozen stream v2")
    require(n.common.sha(runtime.__file__) == RUNTIME_SHA, "Frozen runtime gate")
    return previous.verify_parent()


def stream_deck(original, step, stop):
    require(stop == STOP and step in (5e-12, 2.5e-12), "Declared acquisition analysis")
    text = previous.previous.stream_deck(original, step, 400e-9)
    old = f".tran {step:.12g} 4e-07 0 {step:.12g}\n"
    require(text.count(old) == 1, "One literal analysis duration bridge")
    return text.replace(old, f".tran {step:.12g} 1e-06 0 {step:.12g}\n")


def rising_edges(times, voltage, threshold=1.25):
    """Independent scalar interpolation; no inherited crossing helper."""
    require(len(times) == len(voltage) and len(times) >= 2, "Complete edge vectors")
    require(
        np.isfinite(times).all() and np.isfinite(voltage).all(), "Finite edge vectors"
    )
    require(np.all(np.diff(times) > 0), "Strict edge time order")
    edges = []
    for i in range(1, len(times)):
        if voltage[i - 1] < threshold <= voltage[i]:
            slope = (voltage[i] - voltage[i - 1]) / (times[i] - times[i - 1])
            edges.append(float(times[i - 1] + (threshold - voltage[i - 1]) / slope))
    return edges


def pair_ordinals(reference, feedback):
    require(len(reference) >= 2, "Actual reference edges")
    pairs = []
    for ordinal, edge in enumerate(feedback):
        position = bisect.bisect_left(reference, edge)
        candidates = [i for i in (position - 1, position) if 0 <= i < len(reference)]
        index = min(candidates, key=lambda i: (abs(edge - reference[i]), i))
        pairs.append(
            dict(
                feedback_ordinal=ordinal,
                feedback_s=edge,
                reference_ordinal=index,
                reference_s=reference[index],
                phase_s=edge - reference[index],
                unambiguous_half_period=abs(edge - reference[index]) < 5e-9,
            )
        )
    slips = []
    for old, new in zip(pairs, pairs[1:]):
        delta = new["reference_ordinal"] - old["reference_ordinal"]
        if delta != 1:
            slips.append(
                dict(
                    feedback_s=new["feedback_s"],
                    reference_ordinal_delta=delta,
                    kind="repeat"
                    if delta == 0
                    else "skip"
                    if delta > 1
                    else "regression",
                    previous=old,
                    current=new,
                )
            )
    return pairs, slips


def window_metrics(times, control, pairs, begin, end):
    selected = [p for p in pairs if begin <= p["feedback_s"] < end]
    edges = [p["feedback_s"] for p in selected]
    periods = np.diff(edges)
    frequency = (len(edges) - 1) / (edges[-1] - edges[0]) if len(edges) > 1 else None
    phases = [p["phase_s"] for p in selected]
    phase_span = max(phases) - min(phases) if phases else None
    indices = [p["reference_ordinal"] for p in selected]
    mask = (times >= begin) & (times <= end)
    require(mask.any(), "Every declared window has actual samples")
    control_range = [float(control[mask].min()), float(control[mask].max())]
    checks = dict(
        frequency_100ppm=frequency is not None
        and abs(frequency / FREQUENCY_HZ - 1) <= FREQUENCY_RELATIVE_LIMIT,
        phase_range_50ps=phase_span is not None and phase_span <= PHASE_RANGE_LIMIT_S,
        unique_successive_reference_no_slip=len(selected) >= 9
        and all(p["unambiguous_half_period"] for p in selected)
        and all(b == a + 1 for a, b in zip(indices, indices[1:])),
        control_development_window=0.4 <= control_range[0] <= control_range[1] <= 1.5,
    )
    return dict(
        interval_s=[begin, end],
        frequency_hz=frequency,
        frequency_error_ppm=None
        if frequency is None
        else (frequency / FREQUENCY_HZ - 1) * 1e6,
        phase_s=phases,
        phase_span_s=phase_span,
        reference_indices=indices,
        control_range_v=control_range,
        observed_period_range_s=[float(periods.min()), float(periods.max())]
        if len(periods)
        else None,
        checks=checks,
        passed=all(checks.values()),
    )


def acquisition(data):
    times, control = data["time"], data["v(vctrl)"]
    require(
        times[0] == 0 and abs(times[-1] - STOP) <= 16 * np.spacing(STOP),
        "Full1us acquisition record",
    )
    reference = rising_edges(times, data["v(reference)"])
    feedback = rising_edges(times, data["v(fb)"])
    pairs, slips = pair_ordinals(reference, feedback)
    rolling = [
        window_metrics(times, control, pairs, start / 1e9, (start + 100) / 1e9)
        for start in range(100, 901, 10)
    ]
    fixed = [rolling[70], rolling[80]]
    suffix_start = None
    for window in reversed(rolling):
        if not window["passed"]:
            break
        suffix_start = window["interval_s"][0]
    final_indices = [i for w in fixed for i in w["reference_indices"]]
    final_no_slip = len(final_indices) >= 18 and all(
        b == a + 1 for a, b in zip(final_indices, final_indices[1:])
    )
    sustained = suffix_start is not None and suffix_start <= 800e-9
    passed = all(w["passed"] for w in fixed) and final_no_slip and sustained
    return dict(
        passed=passed,
        fixed_acceptance_windows=fixed,
        rolling_windows=rolling,
        reference_edges_s=reference,
        feedback_edges_s=feedback,
        all_edge_pairings=pairs,
        ordinal_discontinuities=slips,
        ambiguous_pairings=[p for p in pairs if not p["unambiguous_half_period"]],
        final_two_windows_no_slip=final_no_slip,
        sustained_window_start_s=suffix_start,
        sustained_confirmation_s=None
        if suffix_start is None
        else suffix_start + 100e-9,
        grid_s=10e-9,
        window_s=100e-9,
        semantics="Earliest100ns window on fixed10ns grid whose every later window also qualifies; confirmation is its end, not exact physical lock instant",
        scope="Finite nominal acquisition screen only; no phase-noise/jitter, PVT, thermal-equilibrium, extracted-layout or foundry qualification",
    )


def measurements(data, config):
    observed = dict(data)
    for key, value in data.items():
        if key.startswith("v(xloop.xchain."):
            observed[key.replace("v(xloop.xchain.", "v(xchain.", 1)] = value
    result = previous.previous.loop.base.measure_chain(observed, config)
    result.pop("vctrl_external_v")
    result.pop("closed_pll")
    result["acquisition"] = acquisition(data)
    result["passed"] &= result["acquisition"]["passed"]
    result["lock_demonstrated"] = False
    return result


def classify_advisory(log, columns, step, stop, runtime_sha, returncode):
    """Record only the source-verified ng47 FIFO-unaware memory estimate."""
    require(runtime_sha == NG47_SHA and returncode == 0, "Exact successful native47")
    require(
        columns == 826 and step in (5e-12, 2.5e-12) and stop == STOP,
        "Exact planned native dimensions",
    )
    pattern = (
        r"(?m)^Warning: memory required \(([0-9.]+) ([GMK]?)B\), made of\n"
        r"       (\d+) nodes and approximately ([0-9.e+]+) time steps,\n"
        r"       is more than the DRAM memory available \(([0-9.]+) ([GMK]?)B\)!\n"
        r"       Swapping data to SSD may slow down the simulation\.\n"
    )
    matches = list(re.finditer(pattern, log))
    require(len(matches) <= 1, "At most one exact estimator advisory")
    cleaned, advisories = log, []
    scale = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
    for match in matches:
        size, units, nodes, count, free, free_units = match.groups()
        expected = stop / step * columns * 8
        reported, available = (
            float(size) * scale[units],
            float(free) * scale[free_units],
        )
        require(
            int(nodes) == columns
            and math.isclose(float(count), stop / step, rel_tol=1e-6),
            "Exact advisory columns/time steps",
        )
        # Native eng(...,6,...) rounds the displayed engineering value. Bind
        # its last printed decimal rather than assuming six fractional digits.
        decimals = len(size.split(".")[1]) if "." in size else 0
        require(decimals >= 4, "Native estimator display precision")
        half_display_unit = 0.5 * 10 ** (-decimals) * scale[units]
        require(
            abs(reported - expected) <= half_display_unit + 1e-6
            and 0 < available < reported,
            "Estimator byte calculation within native printed rounding",
        )
        advisories.append(
            dict(
                literal=match.group(),
                estimated_bytes=expected,
                reported_available_bytes=available,
                source=WARNING_SOURCE,
            )
        )
        cleaned = cleaned.replace(match.group(), "", 1)
    require(
        not re.search(
            r"warning|error|failed|singular|timestep too small|gmin stepping|source stepping",
            cleaned,
            re.I,
        ),
        "All other diagnostics remain errors",
    )
    return cleaned, advisories


def retained_op_proof(log, capture):
    require(
        [int(x) for x in re.findall(r"No\. of Data Rows\s*:\s*(\d+)", log)]
        == [1, capture["rows"]],
        "Native OP/stream count agreement",
    )
    require(
        re.search(r"(?m)^Current op1\s", log)
        and not re.search(r"(?m)^\s*(?:Current )?tran\d+\b", log),
        "No retained transient plot",
    )
    displayed = re.findall(r"(?m)^\s+(\S+)\s*:\s+\S+, real, (\d+) long", log)
    names = [
        n[2:-1]
        if n.startswith("v(")
        else n[2:-1] + "#branch"
        if n.startswith("i(")
        else n
        for n in capture["columns"][1:]
    ]
    require(
        len(displayed) == len(names)
        and set(n for n, _ in displayed) == set(names)
        and {length for _, length in displayed} == {"1"},
        "Exact825 one-point native OP vectors",
    )
    peak = re.findall(r"Maximum ngspice program size =\s*([0-9.]+) MB", log)
    require(len(peak) == 1 and float(peak[0]) < 128, "Bounded native stream memory")
    return dict(
        retained_plot="op1_only",
        retained_vector_length=1,
        native_peak_mb=float(peak[0]),
    )


def startup_proof(folder, prior):
    literal = (folder / "run.log").read_text()
    capture = json.loads((folder / "capture/capture.json").read_text())
    analyses = re.findall(
        r"(?m)^\.tran (\S+) (\S+) 0 (\S+)$", (folder / "bench.cir").read_text()
    )
    require(
        len(analyses) == 1 and analyses[0][0] == analyses[0][2],
        "Exact stream native analysis",
    )
    step, stop = map(float, analyses[0][:2])
    execution = json.loads((folder / "execution.json").read_text())
    cleaned, advisories = classify_advisory(
        literal,
        len(capture["columns"]),
        step,
        stop,
        n.common.sha(n.NG),
        execution["returncode"],
    )
    proof = namespace["_strict_startup"](folder, prior, cleaned)
    proof.update(
        clean_diagnostics=not advisories,
        strict_numerical_diagnostics_pass=True,
        informational_memory_advisories=advisories,
        original_log_modified=False,
        original_log_sha256=n.common.sha(folder / "run.log"),
        retained_native_memory=retained_op_proof(literal, capture),
    )
    return proof


def bind_native(path, digest, step, stop, prior, require_functional=False):
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
        record["config"]["step_s"] == step and record["config"]["stop_s"] == stop,
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
    required_inputs = set(prior["inputs"]) | {
        str(Path(previous.__file__).resolve()),
        str(Path(previous.previous.__file__).resolve()),
        str(Path(runtime.__file__).resolve()),
    }
    if stop == STOP:
        required_inputs.add(str(Path(__file__).resolve()))
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
        record["safety"]["passed"]
        and len(record["safety"]["all_device_bounds"]) == 539
        and all(x["passed"] for x in record["safety"]["all_device_bounds"]),
        "All prerequisite electrical screens pass",
    )
    require(
        not record["safety"]["model_geometry_range_issues"],
        "No prerequisite model range waiver",
    )
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
        require(passed, "Recomputed stored prerequisite electrical bounds")
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
    if require_functional:
        require(record["measurement"]["passed"], "First1us merits paired evaluation")
    paths = [str(path)]
    for source, pin in record["inputs"].items():
        require(n.common.pin(source) == pin, "Prerequisite input drift: " + source)
        paths.append(source)
    for name, pin in record["outputs"].items():
        target = path.parent / name
        require(n.common.pin(target) == pin, "Prerequisite output drift: " + name)
        paths.append(str(target))
    require(
        json.loads((path.parent / "execution.json").read_text())["returncode"] == 0,
        "Native prerequisite actually exited0",
    )
    return paths


def prerequisites(manifest, digest, step, prior):
    require(
        n.common.sha(manifest) == digest,
        "Externally pinned acquisition prerequisite manifest",
    )
    record = json.loads(Path(manifest).read_text())
    names = {"first400", "tight400"} | ({"first1000"} if step == 2.5e-12 else set())
    require(set(record) == names, "Exact prerequisite set; no substitutes")
    paths = [str(manifest)]
    for name, required_step, stop, functional in [
        ("first400", 5e-12, 400e-9, False),
        ("tight400", 2.5e-12, 400e-9, False),
        ("first1000", 5e-12, STOP, True),
    ]:
        if name in names:
            item = record[name]
            require(set(item) == {"path", "sha256"}, "Explicit prerequisite identity")
            paths += bind_native(
                item["path"], item["sha256"], required_step, stop, prior, functional
            )
    return dict(paths=sorted(set(paths)), manifest=record)


def derive(name, source, replacements):
    original = source
    for old, new in replacements:
        require(source.count(old) == 1, "Unique private source bridge: " + name)
        source = source.replace(old, new)
    BRIDGES[name] = dict(
        original_sha256=hashlib.sha256(original.encode()).hexdigest(),
        modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
        exact_replacements=replacements,
    )
    exec(compile(source, __file__ + ":" + name, "exec"), namespace)
    return namespace[name]


namespace.update(
    verify_parent=verify_parent,
    stream_deck=stream_deck,
    measurements=measurements,
    startup_proof=startup_proof,
    prerequisites=prerequisites,
)
capture = derive(
    "capture",
    inspect.getsource(previous.previous.capture),
    previous.BRIDGES["capture"]["exact_replacements"],
)
strict = inspect.getsource(previous.previous.startup_proof)
derive(
    "_strict_startup",
    strict,
    [
        (
            "def startup_proof(folder, prior):",
            "def _strict_startup(folder, prior, cleaned_log):",
        ),
        ('log = (folder / "run.log").read_text()', "log = cleaned_log"),
    ],
)
source = inspect.getsource(previous.previous.run)
start = source.index("    if step == 2.5e-12 or stop == 400e-9:\n")
end = source.index("    require(\n        not out.exists()", start)
prerequisite_block = source[start:end]
run = derive(
    "run",
    source,
    [
        (
            prerequisite_block,
            "    require(stop == 1e-6 and step in (5e-12, 2.5e-12), 'Declared acquisition analysis')\n    validated = prerequisites(gate, gate_sha, step, prior)\n",
        ),
        (
            "config.update(step_s=step, stop_s=stop, window_s=[4e-9, stop])",
            "config.update(case='connected_physical_loop_acquisition1us', step_s=step, stop_s=stop, window_s=[4e-9, stop])",
        ),
        (
            "paths += method_inventory() + [str(p) for p in out.iterdir()]",
            "paths += validated['paths']\n    paths += method_inventory() + [str(p) for p in out.iterdir()]",
        ),
    ],
)
# The original equality-only34ns branch is unreachable here. Every physical,
# process, FIFO, source guard and all-sample safety formula remains inherited.


def main():
    runtime.check_runtime(
        sys.version_info, np.__version__, callable(getattr(np, "trapezoid", None))
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--step-ps", type=float, choices=[5, 2.5], required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-sha", required=True)
    parser.add_argument("--prerequisites", type=Path, required=True)
    parser.add_argument("--prerequisites-sha", required=True)
    args = parser.parse_args()
    result = run(
        args.out,
        args.prefix,
        {5: 5e-12, 2.5: 2.5e-12}[args.step_ps],
        STOP,
        args.reference,
        args.reference_sha,
        args.prerequisites,
        args.prerequisites_sha,
    )
    print(result["status"])
    return 0 if result["status"] == "PASS_NATIVE_STREAM_FINITE_SCREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
