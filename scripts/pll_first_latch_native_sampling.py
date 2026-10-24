#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve every first-latch edge, including an exact native endpoint."""
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import numpy as np
import cloud_pll_first_latch_sinks as original

ORIGINAL_SHA = "b2977723438ad18c8668713b393686e06d9538f8bbafaaf015365f60c3131c63"
OLD_BLOCK = """     hi=int(np.searchsorted(t,x,'left'));assert 0<hi<len(t)
     snapshots.append(dict(kind=kind,time_s=float(x),bracketing_rows=[hi-1,hi],
       native_times_s=[float(t[hi-1]),float(t[hi])],
       signals={k:float(np.interp(x,t[hi-1:hi+1],v[hi-1:hi+1]))for k,v in signals.items()}))"""
NEW_BLOCK = """     snapshots.append(native_snapshot(t,x,signals,kind))"""

def native_snapshot(t, x, signals, kind):
    """t is already globally finite/strictly increasing in the frozen analyzer.
    Exact sampled edges use that native row; intervening edges retain the old
    two-row linear interpolation. Out-of-range edges are rejected, never clipped.
    """
    x = float(x)
    assert kind in ("rising", "falling") and len(t) >= 2
    assert math.isfinite(x) and float(t[0]) <= x <= float(t[-1])
    hi = int(np.searchsorted(t, x, side="left"))
    assert 0 <= hi < len(t)
    if t[hi] == x:
        rows = [hi]
        mode = "exact_native_sample"
    else:
        assert 0 < hi < len(t) and t[hi-1] < x < t[hi]
        rows = [hi-1, hi]
        mode = "two_native_sample_linear_interpolation"
    values = {}
    for name, signal in signals.items():
        assert len(signal) == len(t)
        assert np.isfinite(signal[rows]).all()
        values[name] = (float(signal[hi]) if len(rows) == 1 else
                       float(np.interp(x, t[hi-1:hi+1], signal[hi-1:hi+1])))
        assert math.isfinite(values[name])
    return dict(kind=kind, time_s=x, bracketing_rows=rows,
                native_times_s=[float(t[i]) for i in rows], signals=values,
                sampling_mode=mode, original_strict_interior_would_reject=(hi == 0))

def patched_analyze(out):
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest() == ORIGINAL_SHA
    source = inspect.getsource(original.analyze)
    assert source.count(OLD_BLOCK) == 1 and NEW_BLOCK not in source
    repaired = source.replace(OLD_BLOCK, NEW_BLOCK)
    assert repaired.count(NEW_BLOCK) == 1
    assert repaired.replace(NEW_BLOCK, OLD_BLOCK) == source
    namespace = dict(vars(original), OUT=Path(out), native_snapshot=native_snapshot)
    exec(compile(repaired, "<exact-first-latch-native-endpoint-adapter>", "exec"), namespace)
    return namespace["analyze"], dict(
        original_module_sha256=ORIGINAL_SHA,
        original_analyze_sha256=hashlib.sha256(source.encode()).hexdigest(),
        adapted_analyze_sha256=hashlib.sha256(repaired.encode()).hexdigest(),
        exactly_one_reversible_sampling_block=True,
        thresholds_changed=False, native_edges_removed=False, extrapolation_allowed=False)

def replay_analyze(data, mapping, chain, analysis, out):
    analyze, source = patched_analyze(out)
    result = analyze(data, mapping, chain, analysis)
    endpoints = []
    exact_count = 0
    interpolated_count = 0
    for threshold, bucket in result["master_events"].items():
        for interval in bucket["anomalous_intervals"]:
            for sample in interval["transition_snapshots"]:
                if sample["sampling_mode"] == "exact_native_sample":
                    exact_count += 1
                else:
                    interpolated_count += 1
                if sample["original_strict_interior_would_reject"]:
                    assert sample["time_s"] == float(data["time"][0])
                    assert sample["bracketing_rows"] == [0]
                    endpoints.append(dict(threshold=threshold, kind=sample["kind"],
                        time_s=sample["time_s"], native_row=0,
                        interval_s=interval["interval_s"]))
    assert endpoints, "No actual native first-sample edge explains the original assertion"
    result["native_sampling_repair"] = dict(source=source,
        exact_native_samples=exact_count, two_sample_interpolations=interpolated_count,
        original_assertion_endpoint_witnesses=endpoints,
        original_acquisition_rejection_preserved=True,
        full_phy_accepted=False)
    assert result["acquisition_accepted"] is False and result["full_phy_accepted"] is False
    return result

def controls():
    t = np.array([0., 1., 2., 3.], dtype="<f8")
    backing = np.zeros((4, 4), dtype="<f8")
    backing[:, 2] = 2*t + 1
    y = backing[:, 2]  # actual strided view, not only contiguous fixtures
    cases = []
    for x in [0., .125, .5, 1., 1.75, 2., 2.875, 3.]:
        q = native_snapshot(t, x, {"affine_v": y, "constant_a": t*0+.01}, "rising")
        assert q["signals"]["affine_v"] == 2*x+1 and q["signals"]["constant_a"] == .01
        i = int(np.searchsorted(t, x, "left"))
        if i:
            assert q["signals"]["affine_v"] == float(np.interp(x, t[i-1:i+1], y[i-1:i+1]))
        else:
            assert q["original_strict_interior_would_reject"]
        assert q["bracketing_rows"] == ([i] if t[i] == x else [i-1, i])
        cases.append(dict(time=x, rows=q["bracketing_rows"], mode=q["sampling_mode"]))
    z = np.array([-0., 0., 1., 2.])
    q = native_snapshot(t, 0., {"signed_zero": z}, "falling")
    assert math.copysign(1., q["signals"]["signed_zero"]) == -1.
    bad = []
    def reject(name, fn):
        try:
            fn()
        except (AssertionError, ValueError, IndexError):
            bad.append(name)
        else:
            raise AssertionError("Accepted fault " + name)
    reject("before_first_sample", lambda: native_snapshot(t, -1e-15, {"v": y}, "rising"))
    reject("after_last_sample", lambda: native_snapshot(t, 3.000000000000001, {"v": y}, "rising"))
    reject("nan_time", lambda: native_snapshot(t, float("nan"), {"v": y}, "rising"))
    reject("infinite_time", lambda: native_snapshot(t, float("inf"), {"v": y}, "rising"))
    reject("wrong_signal_length", lambda: native_snapshot(t, 0., {"v": y[:-1]}, "rising"))
    reject("nonfinite_exact_value", lambda: native_snapshot(t, 0., {"v": np.array([float("nan"),1.,2.,3.])}, "rising"))
    reject("nonfinite_bracket_value", lambda: native_snapshot(t, .5, {"v": np.array([0.,float("nan"),2.,3.])}, "rising"))
    reject("invalid_event_kind", lambda: native_snapshot(t, .5, {"v": y}, "invented"))
    analyze, source = patched_analyze(Path("."))
    assert callable(analyze)
    return dict(status="PASS_EXACT_NATIVE_ENDPOINT_SAMPLING_CONTROLS",
        cases=cases, strided_signal_checked=True, signed_zero_preserved=True,
        original_nonendpoint_values_identical=True, source=source,
        rejected=bad, native_simulation_started=False, full_phy_accepted=False)

if __name__ == "__main__":
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only validation"
    assert __import__("sys").argv[1:] == ["--controls"]
    original.methods()
    print(json.dumps(controls(), indent=2))
