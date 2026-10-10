# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import argparse
from pathlib import Path
import numpy as np
import pcie_pll_native_fixture_v1 as native
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "hw/soc/analog/pcie/pll_feedback_div20_lv_v1.spice"
CIRCUIT_SHA = "b17ab10e219b4005e782a97d6f31877e0c9e8077ceabec756e7704f362c419af"
TOP = "nssoc_pll_feedback_div20_v1"
FAULTS = {
    "freeze_fast0": ("XFAST0 f0b clk", "XFAST0 avss clk"),
    "wrong_modulus": ("XD2N q2b q1 q0 d2b", "XD2N q2b q1 q1 d2b"),
    "invert_hv_output": (
        "XLEVEL count countb fb fbbar",
        "XLEVEL countb count fb fbbar",
    ),
}
CASES = (
    "nominal",
    "half_step",
    "slow_input",
    "fast_input",
    "reset_held",
    "reset_midstream",
    "clock_stopped",
    *FAULTS,
)


def circuit_text(fault=""):
    assert native.common.sha(CIRCUIT) == CIRCUIT_SHA
    text = CIRCUIT.read_text()
    if fault:
        old, new = FAULTS[fault]
        assert text.count(old) == 1
        text = text.replace(old, new)
    return text


def pulse(positive, period=0.5e-9, stopped=False):
    # Explicit external differential-clock stimulus; no source inside the DUT.
    low, high = 2.25, 2.49
    initial = low if positive else high
    rows = [(0, 0), (0.5e-9, initial)]
    for index in range(80):
        start = 1e-9 + index * period
        if stopped and start >= 15e-9:
            break
        before, after = (low, high) if positive else (high, low)
        rows += [
            (start, before),
            (start + 25e-12, after),
            (start + period / 2, after),
            (start + period / 2 + 25e-12, before),
        ]
    return "PWL(" + " ".join(f"{t:.12g} {v:.12g}" for t, v in rows) + ")"


def count_measure(data, config):
    t = data["time"]
    left, right = config["window_s"]
    mask = (t >= left) & (t <= right)
    edges = {}
    signals = [
        ("cml", data["v(cp)"] - data["v(cn)"], 0),
        ("received", data["v(xfb.clk)"], 0.6),
        ("fast0", data["v(xfb.f0)"], 0.6),
        ("fast1", data["v(xfb.f1)"], 0.6),
        ("count", data["v(xfb.count)"], 0.6),
        ("feedback", data["v(fb)"], 1.25),
    ]
    for name, trace, level in signals:
        edges[name] = [
            e for e in native.common.crossings(t, trace, level) if left <= e < right
        ]
    checks, ratios = {}, {}
    for fast, slow, n in [
        ("cml", "received", 1),
        ("received", "fast0", 2),
        ("fast0", "fast1", 2),
        ("fast1", "count", 5),
        ("count", "feedback", 1),
        ("received", "feedback", 20),
    ]:
        counts = [
            sum(a <= e < b for e in edges[fast])
            for a, b in zip(edges[slow][:-1], edges[slow][1:])
        ]
        ratios[fast + "_" + slow] = counts
        checks[fast + "_" + slow] = len(edges[slow]) >= 2 and all(
            x == n for x in counts
        )
    state_samples = []
    checks["state_logic_rails"] = True
    for edge in edges["fast1"]:
        sample = edge + 0.5e-9
        if sample >= right:
            continue
        bits = [
            float(np.interp(sample, t, data["v(" + n + ")"]))
            for n in ("xfb.xcount.q0", "xfb.xcount.q1", "xfb.count")
        ]
        checks["state_logic_rails"] &= all(v < 0.2 or v > 1.0 for v in bits)
        state = sum((v > 0.6) << i for i, v in enumerate(bits))
        state_samples.append(dict(time=sample, state=state, volts=bits))
    checks["modulo_five_sequence"] = (
        len(state_samples) >= config["minimum_states"]
        and all(0 <= x["state"] < 5 for x in state_samples)
        and all(
            b["state"] == (a["state"] + 1) % 5
            for a, b in zip(state_samples[:-1], state_samples[1:])
        )
    )
    checks["feedback_full_swing"] = (
        float(data["v(fb)"][mask].min()) < 0.2
        and float(data["v(fb)"][mask].max()) > 2.3
    )
    checks["receiver_logic_rails"] = (
        float(data["v(xfb.clk)"][mask].min()) < 0.2
        and float(data["v(xfb.clk)"][mask].max()) > 1.0
    )
    falling = native.common.crossings(t, -data["v(fb)"], -1.25)
    widths = []
    for a, b in zip(edges["feedback"][:-1], edges["feedback"][1:]):
        falls = [f for f in falling if a < f < b]
        if len(falls) != 1:
            widths.append(None)
        else:
            widths.append((falls[0] - a) / (b - a))
    checks["feedback_twenty_percent_duty"] = len(widths) >= 1 and all(
        x is not None and 0.17 <= x <= 0.23 for x in widths
    )
    mask = (t >= left) & (t <= right)
    return dict(
        output_period_s=[
            b - a for a, b in zip(edges["feedback"][:-1], edges["feedback"][1:])
        ],
        feedback_duty=widths,
        passed=all(checks.values()),
        checks=checks,
        edge_times=edges,
        edge_ratios=ratios,
        state_samples=state_samples,
        feedback_range=[
            float(data["v(fb)"][mask].min()),
            float(data["v(fb)"][mask].max()),
        ],
    )


def measure(data, config):
    case = config["case"]
    t = data["time"]
    if case in ("reset_held", "clock_stopped"):
        left = 5e-9 if case == "reset_held" else 18e-9
        mask = (t >= left) & (t <= config["stop_s"])
        names = [
            "xfb.f0",
            "xfb.f1",
            "xfb.xcount.q0",
            "xfb.xcount.q1",
            "xfb.count",
            "fb",
        ]
        spans = {
            n: [
                float(data["v(" + n + ")"][mask].min()),
                float(data["v(" + n + ")"][mask].max()),
            ]
            for n in names
        }
        checks = {
            n: (
                b < 0.2
                if case == "reset_held"
                else b - a < 0.05 and (b < 0.2 or a > (2.3 if n == "fb" else 1.0))
            )
            for n, (a, b) in spans.items()
        }
        if case == "clock_stopped":
            early = count_measure(
                data, dict(config, window_s=[6e-9, 14.9e-9], minimum_states=3)
            )
            checks["clock_worked_before_stop"] = len(
                early["edge_times"]["received"]
            ) >= 12 and all(
                early["checks"][k]
                for k in (
                    "cml_received",
                    "received_fast0",
                    "fast0_fast1",
                    "state_logic_rails",
                    "modulo_five_sequence",
                )
            )
        return dict(passed=all(checks.values()), checks=checks, settled_spans=spans)
    result = count_measure(data, config)
    if case == "reset_midstream":
        mask = (t >= 15.0e-9) & (t <= 16.8e-9)
        result["reset_spans"] = {
            n: float(abs(data["v(" + n + ")"][mask]).max())
            for n in [
                "xfb.f0",
                "xfb.f1",
                "xfb.xcount.q0",
                "xfb.xcount.q1",
                "xfb.count",
                "fb",
            ]
        }
        result["checks"]["midstream_reset_clears"] = all(
            v < 0.2 for v in result["reset_spans"].values()
        )
        result["passed"] = all(result["checks"].values())
    return result


def config_for(case, source):
    assert case in CASES
    period = (
        0.525e-9
        if case == "slow_input"
        else 0.475e-9
        if case == "fast_input"
        else 0.5e-9
    )
    reset = "PWL(0 0 3n 0 3.1n 1.2)"
    if case == "reset_held":
        reset = "0"
    elif case == "reset_midstream":
        reset = "PWL(0 0 3n 0 3.1n 1.2 14n 1.2 14.1n 0 17n 0 17.1n 1.2)"
    return dict(
        case=case,
        sources=[str(source)],
        method_inputs=[str(CIRCUIT)],
        roots=[
            (
                TOP,
                "xfb",
                ["cp", "cn", "clearb", "fb", "fbbar", "avdd", "cvdd", "0", "0"],
            )
        ],
        extra_vectors=["i(vdd)", "i(vcore)", "i(vp)", "i(vn)"],
        step_s=5e-12 if case == "half_step" else 10e-12,
        stop_s=38e-9 if case == "reset_midstream" else 34e-9,
        window_s=[22e-9, 38e-9] if case == "reset_midstream" else [6e-9, 34e-9],
        minimum_states=5 if case == "reset_midstream" else 8,
        fixture=[
            "VDD avdd 0 PWL(0 0 500p 2.5)",
            "VCORE cvdd 0 PWL(0 0 500p 1.2)",
            "VP cp 0 " + pulse(True, period, case == "clock_stopped"),
            "VN cn 0 " + pulse(False, period, case == "clock_stopped"),
            "VRST clearb 0 " + reset,
        ],
    )


def main():
    parser = argparse.ArgumentParser(
        description="Native CMOS /20 prerequisite; external CML test clock, no closed PLL"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    args = parser.parse_args()
    # Keep the exact tested mutation/source in the native input inventory.
    scratch = Path(
        tempfile.mkdtemp(prefix="nssoc-pll-feedback-source-", dir="/dev/shm")
    )
    source = scratch / CIRCUIT.name
    source.write_text(circuit_text(args.case if args.case in FAULTS else ""))
    try:
        result = native.run(config_for(args.case, source), args.out, __file__, measure)
        healthy = result["safety"]["passed"]
        functional = result["measurement"]["passed"]
        accepted = healthy and (not functional if args.case in FAULTS else functional)
        result["accepted"] = accepted
        result["case_role"] = (
            "actual_native_fault" if args.case in FAULTS else "positive"
        )
        result["acceptance_status"] = (
            "PASS_FINITE_FEEDBACK_PREREQUISITE"
            if accepted
            else "FAIL_FINITE_FEEDBACK_PREREQUISITE"
        )
        result["limitations"] = [
            "External differential clock in this component fixture; no connected /80 or closed PLL.",
            "Nominal models only; no PVT, extracted layout, jitter or foundry SOA qualification.",
            "Receiver, counter and HV level-shifter delays distort the nominal 20% duty cycle.",
            "Full-capture per-device development voltage/current bounds and model geometry ranges remain mandatory.",
        ]
        native.common.atomic(args.out / "result.json", result)
        print(result["acceptance_status"])
        return 0 if accepted else 1
    finally:
        # Only generated, source-identical tiny input copy; all bytes in output.
        if (args.out / CIRCUIT.name).is_file() and (
            args.out / CIRCUIT.name
        ).read_bytes() == source.read_bytes():
            shutil.rmtree(scratch)


if __name__ == "__main__":
    raise SystemExit(main())
