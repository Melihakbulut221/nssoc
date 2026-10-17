# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure a saved PLL response without turning nominal waveforms into signoff.

Feedback phase is a continuous edge count evaluated at reference edges. It is
never reduced modulo one cycle: frequency drift and cycle slips remain visible.
Static phase offset is reported, not mistaken for failure to track frequency.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from compare_pcie_pump_boundary import pin, read_trace, require


COLUMNS = ["time", "v(reference)", "v(fb)", "v(clkp)", "v(clkn)", "v(vctrl)"]


def crossings(time, voltage):
    indices = np.flatnonzero((voltage[:-1] < 0) & (voltage[1:] >= 0))
    return time[indices] + np.diff(time)[indices] * (
        -voltage[indices] / np.diff(voltage)[indices]
    )


def analyze(samples, window):
    require(samples.ndim == 2 and samples.shape[1] == len(COLUMNS), "trace shape")
    require(len(samples) >= 3 and np.isfinite(samples).all(), "finite samples")
    time = samples[:, 0]
    require(np.all(np.diff(time) > 0), "time order")
    lo, hi = window
    require(time[0] <= lo < hi <= time[-1], "window coverage")
    edges = {
        "reference": crossings(time, samples[:, 1] - 1.25),
        "feedback": crossings(time, samples[:, 2] - 1.25),
        "vco": crossings(time, samples[:, 3] - samples[:, 4]),
    }
    metrics = {}
    for name, values in edges.items():
        selected = values[(values >= lo) & (values < hi)]
        require(len(selected) >= 3, "insufficient " + name + " edges")
        periods = np.diff(selected)
        metrics[name] = {
            "edges": len(selected), "frequency_hz": float(1 / periods.mean()),
            "period_min_s": float(periods.min()),
            "period_max_s": float(periods.max()),
            "period_std_s": float(periods.std()),
        }
    reference, feedback = edges["reference"], edges["feedback"]
    # Interpolate only inside observed feedback edge coverage; never extrapolate.
    mask = ((reference >= lo) & (reference < hi)
            & (reference >= feedback[0]) & (reference <= feedback[-1]))
    reference_times = reference[mask]
    require(len(reference_times) >= 3, "insufficient shared edge coverage")
    phase = np.interp(reference_times, feedback, np.arange(len(feedback))) - np.flatnonzero(mask)
    centered_time = reference_times - reference_times[0]
    slope, intercept = np.polyfit(centered_time, phase, 1)
    residual = phase - (intercept + slope * centered_time)
    grid = np.r_[lo, time[(time > lo) & (time < hi)], hi]
    control = np.interp(grid, time, samples[:, 5])
    mean = np.sum(np.diff(grid) * (control[:-1] + control[1:]) / 2) / (hi - lo)
    return {
        "window_s": [lo, hi], "signals": metrics,
        "feedback_frequency_error_ppm": float(
            (metrics["feedback"]["frequency_hz"] / metrics["reference"]["frequency_hz"] - 1) * 1e6),
        "vco_to_feedback_ratio": float(metrics["vco"]["frequency_hz"] / metrics["feedback"]["frequency_hz"]),
        "phase": {
            "reference_times_s": reference_times.tolist(), "unwrapped_cycles": phase.tolist(),
            "slope_cycles_per_s": float(slope), "change_cycles": float(phase[-1] - phase[0]),
            "detrended_peak_to_peak_cycles": float(np.ptp(residual)),
            "static_offset_is_not_a_lock_criterion": True,
        },
        "control_voltage": {"min_v": float(control.min()), "max_v": float(control.max()), "mean_v": float(mean)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--window", nargs=2, type=float, required=True)
    parser.add_argument("--max-rows", type=int, default=2_000_000)
    args = parser.parse_args()
    samples, provenance = read_trace(args.capture, COLUMNS, max_rows=args.max_rows)
    result = {
        "status": "COMPLETE_FINITE_RESPONSE_MEASUREMENT_NOT_LOCK_ACCEPTANCE",
        "capture": provenance, "analysis": analyze(samples, args.window),
        "reader": pin(Path(__file__).with_name("compare_pcie_pump_boundary.py")),
        "reviewer": pin(__file__), "pll_lock_accepted": False, "serial_phy_complete": False,
        "scope": "Nominal saved response only; reported period spread is not qualified phase noise, jitter, BER, PVT or extracted-layout verification.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
