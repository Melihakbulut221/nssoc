#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explain saved loaded-CDR sampling failures without modifying their gates.

This reads an existing complete native capture. A query interpolated by the
original checker is never represented as a native row. The original scalar
verdict must be reproduced exactly before any observations are returned.
"""
import numpy as np

UI = 125e-12
START = 2e-9
STOP = START + 258 * UI
STEP = .3125e-12


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def analyze(t, columns, report, witness_vectors=()):
    require(report["case"] in ("nominal_early", "nominal_late"), "nominal case")
    require(report["returncode"] == 0 and report["diagnostics"] == [], "native simulation diagnostics")
    require(report["sources_unchanged"] is True, "native source changed")
    require(report["raw_capture"]["complete_unmodified_rows"] is True, "complete capture required")
    require(report["status"] in (
        "REJECTED_WHOLE_MIM_PD500_LOADED",
        "PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF",
    ), "native scalar verdict")
    t = np.asarray(t)
    require(t.dtype == np.dtype("float64") and t.ndim == 1 and len(t) > 2, "native float64 time")
    require(np.isfinite(t).all() and t[0] == 0 and abs(float(t[-1])-STOP) < 1e-18, "native time extent")
    require((np.diff(t) > 0).all() and float(np.diff(t).max()) <= STEP * 1.00001, "native time order/step")
    require(len(t) == report["raw_capture"]["header_rows"], "native row census")
    require(list(witness_vectors) == sorted(set(witness_vectors)), "unique sorted witness vectors")
    aliases = report["binding"]["aliases"]
    checked = {}

    def vector(name):
        if name not in checked:
            require(name in columns, "missing native vector: " + name)
            a = np.asarray(columns[name])
            require(a.dtype == np.dtype("float64") and a.shape == t.shape, "native vector shape/type: " + name)
            require(np.isfinite(a).all(), "nonfinite native vector: " + name)
            checked[name] = a
        return checked[name]

    def voltage(node):
        node = aliases.get(node, node)
        require(node != "0", "unexpected ideal ground signal")
        name = "v(" + node + ")"
        return name, vector(name)

    for name in witness_vectors:
        vector(name)
    groups = []
    for tag in "abcd":
        groups.append(("sampler_" + tag, "xpd."+tag+"qp", "xpd."+tag+"qn",
                       report["expected_samples"][tag], tag == "b", (.3, .6, .9), .3,
                       report["sampler_checks"][tag]))
    for tag in "xy":
        groups.append(("comparator_" + tag, tag+"p", tag+"n",
                       report["expected_comparisons"][tag], False, (.6, .75, .9), .6,
                       report["comparisons"][tag]))
    queries, windows, replay, native_rows = [], [], {}, set()
    for label, p, n, expected, falling, phases, limit, saved in groups:
        require(len(expected) == 255 and all(type(b) is int and b in (0, 1) for b in expected),
                "255 explicit expected bits")
        pv, positive = voltage(p)
        nv, negative = voltage(n)
        delta = positive - negative
        signed, delays = [], []
        for bit_index, bit in enumerate(expected, 1):
            edge = START + (bit_index if falling else bit_index + .5) * UI
            sign = 2 * bit - 1
            for phase in phases:
                query = edge + phase * UI
                value = float(np.interp(query, t, delta))
                margin = value * sign
                signed.append(margin)
                right = int(np.searchsorted(t, query, side="left"))
                require(0 <= right < len(t), "query outside native capture")
                left = right if t[right] == query else right - 1
                require(left >= 0 and t[left] <= query <= t[right], "native query brackets")
                native_rows.update((left, right))
                queries.append(dict(group=label, bit_index=bit_index, expected_bit=bit,
                    edge_s=edge, phase_ui=phase, query_time_s=query,
                    query_differential_v=value, query_signed_margin_v=margin,
                    below_100mv=margin < .1, wrong_sign=margin <= 0,
                    query_is_interpolated=left != right, left_native_row=left, right_native_row=right,
                    left_time_s=float(t[left]), right_time_s=float(t[right]),
                    positive_vector=pv, negative_vector=nv,
                    left_differential_v=float(delta[left]), right_differential_v=float(delta[right])))
            ids = np.flatnonzero((t >= edge) & (t <= edge + .95 * UI))
            require(len(ids) > 0, "empty native settling window")
            bad = ids[delta[ids] * sign < .1]
            delay = 0. if not len(bad) else float(t[bad[-1]] - edge + STEP)
            delays.append(delay)
            # Preserve every bad native row, including disjoint late regressions.
            bad_rows = list(map(int, bad))
            native_rows.update(bad_rows)
            first_row, last_row = int(ids[0]), int(ids[-1])
            native_rows.update((first_row, last_row))
            windows.append(dict(group=label, bit_index=bit_index, expected_bit=bit, edge_s=edge,
                native_window_start_row=first_row, native_window_end_row=last_row,
                native_window_start_s=float(t[first_row]), native_window_end_s=float(t[last_row]),
                bad_native_rows=bad_rows, last_bad_native_row=bad_rows[-1] if bad_rows else None,
                original_step_added_s=STEP, clock_to_valid_s=delay, limit_s=limit * UI,
                violated=delay > limit * UI, continuous_crossing_time_claimed=False))
        actual = dict(samples=len(signed), minimum_signed_margin_v=min(signed),
            wrong_sign_samples=sum(x <= 0 for x in signed), below_100mv_samples=sum(x < .1 for x in signed),
            maximum_clock_to_valid_s=max(delays), clock_to_valid_by_bit_s=delays,
            passed=min(signed) >= .1 and max(delays) <= limit * UI)
        require(set(saved) == set(actual) and saved == actual, "original scalar mismatch: " + label)
        replay[label] = actual
    require(len(queries) == 6 * 255 * 3 and len(windows) == 6 * 255, "complete query/window census")
    # Sorted row IDs refer to the original capture, without retiming or interpolation.
    frames = [dict(native_row=i, time_s=float(t[i]),
                   values=[float(checked[name][i]) for name in witness_vectors])
              for i in sorted(native_rows)]
    return dict(status="ORIGINAL_SAMPLER_COMPARATOR_GATES_REPLAYED_OBSERVATIONS_ONLY",
        case=report["case"], queries=queries, windows=windows, scalar_replay=replay,
        witness_vectors=list(witness_vectors), native_frames=frames,
        raw_sha256=report["raw_capture"]["raw_sha256"],
        complete_native_rows=len(t), query_count=len(queries), window_count=len(windows),
        native_frames_are_original_rows=True, original_interpolation_explicit=True,
        original_verdict=report["status"], original_verdict_changed=False,
        electrical_accepted=False, physical_accepted=False, full_phy_accepted=False,
        new_simulation=False, complete_dynamic_kcl=False, causality_proven=False)
