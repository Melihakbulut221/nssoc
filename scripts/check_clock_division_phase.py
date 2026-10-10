#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check finite clock division with a causal, fixed input-phase reference.

Counting input edges between delayed output edges is ambiguous when an output
edge crosses the input phase origin. Anchor to the final output edge BEFORE
the measurement window, then associate every later output with an input cycle
relative to that fixed anchor. No fit or phase adjustment uses measured outputs.
This is a finite functional test, not a frequency-accuracy or jitter mask test.
"""

from bisect import bisect_right
import math


def check_division(source_edges, output_edges, *, factor, start_s, stop_s, minimum_intervals):
    if not isinstance(factor, int) or factor < 1 or minimum_intervals < 1:
        raise ValueError("Positive integer division and interval count required")
    if not math.isfinite(start_s) or not math.isfinite(stop_s) or start_s >= stop_s:
        raise ValueError("Invalid measurement window")
    for edges in (source_edges, output_edges):
        if len(edges) < 2 or not all(math.isfinite(t) for t in edges):
            raise ValueError("Insufficient or nonfinite edges")
        if any(b <= a for a, b in zip(edges[:-1], edges[1:])):
            raise ValueError("Edges must be strictly increasing")
    preceding = [t for t in output_edges if t < start_s]
    if not preceding:
        raise ValueError("A pre-window output anchor is required")
    anchor = preceding[-1]
    selected = [t for t in output_edges if start_s <= t <= stop_s]

    def phase(t):
        i = bisect_right(source_edges, t) - 1
        if not 0 <= i < len(source_edges) - 1:
            raise ValueError("Output edge lacks bracketing input edges")
        return i + (t - source_edges[i]) / (source_edges[i + 1] - source_edges[i])

    origin = phase(anchor)
    rows = []
    previous = 0
    for index, t in enumerate(selected, 1):
        relative = phase(t) - origin
        cycle = math.floor(relative + .5)
        rows.append(dict(time_s=t, input_phase_from_anchor=relative,
                         assigned_input_cycle=cycle, expected_input_cycle=factor * index,
                         cycle_increment=cycle - previous,
                         residual_cycles=relative - factor * index,
                         passed=cycle == factor * index and cycle - previous == factor))
        previous = cycle
    return dict(passed=len(rows) >= minimum_intervals and all(r["passed"] for r in rows),
                factor=factor, anchor_s=anchor, anchor_input_phase=origin,
                minimum_intervals=minimum_intervals, intervals=rows,
                anchor_selected_before_window=True, adaptive_phase_fit=False,
                scope="Finite cycle association within half an input cycle of a fixed pre-window anchor; no jitter or frequency-accuracy qualification.")
