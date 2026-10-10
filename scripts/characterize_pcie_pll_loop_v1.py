# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Connected native /80 and bounded physical-loop startup, not lock qualification.

A real biased rppd/MIM low-pass receives the frozen transistor charge pump.
The PFD ports are swapped because the measured VCO tuning slope is negative.
The external reference and supply/reset stimuli are the only ideal sources.
"""

import argparse
from pathlib import Path
import sys
import numpy as np
import characterize_pcie_pll_feedback_v2 as counter
import characterize_pcie_div4_v5 as div

ROOT = Path(__file__).resolve().parents[1]
n = counter.native
SOURCE_PINS = {
    "clock_vco_hbt_v4.spice": "0f6eaecc4b5ff7eddf992fecfa7d6015ab6a93807ffc56f2c99d4fbb84a0a8e7",
    "pll_feedback_chain_v1.spice": "5ba8e8da790a2d393c2fab694fd5df6472ddf3606a087113968a3068a88e0d86",
    "pll_loop_hbt_v1.spice": "2c1d0268da591654679e1c64bc2d811df660de1ca9b8ba0eda271060454233ec",
}


def verify_sources():
    for name, expected in SOURCE_PINS.items():
        assert n.common.sha(ROOT / "hw/soc/analog/pcie" / name) == expected, name


def measure_chain(data, config):
    observed = dict(data)
    for name, value in data.items():
        if name.startswith("v(xchain.xfb."):
            observed[name.replace("v(xchain.xfb.", "v(xfb.", 1)] = value
    observed["v(cp)"] = data["v(qp)"]
    observed["v(cn)"] = data["v(qn)"]
    r = counter.base.count_measure(observed, config)
    t = data["time"]
    left, right = config["window_s"]
    osc = [
        e
        for e in n.common.crossings(t, data["v(clkp)"] - data["v(clkn)"], 0)
        if left <= e < right
    ]
    cml = r["edge_times"]["cml"]
    fb = r["edge_times"]["feedback"]
    r["actual_vco_period_counts"] = {}
    for label, slow, ratio, minimum in [
        ("native_hbt_div4", cml, 4, 10),
        ("whole_native_div80", fb, 80, 3),
    ]:
        counts = [sum(a <= e < b for e in osc) for a, b in zip(slow[:-1], slow[1:])]
        r["actual_vco_period_counts"][label] = counts
        r["checks"][label] = len(slow) >= minimum and all(c == ratio for c in counts)
    r["passed"] = all(r["checks"].values())
    r["vco_frequency_hz"] = 1 / float(np.mean(np.diff(osc))) if len(osc) > 1 else None
    r["feedback_frequency_hz"] = (
        1 / float(np.mean(np.diff(fb))) if len(fb) > 1 else None
    )
    r["vctrl_external_v"] = 0.85
    r["closed_pll"] = False
    return r


def chain_config():
    verify_sources()
    counter.circuit_text()
    div.verify_sources()
    analog = ROOT / "hw/soc/analog/pcie"
    sources = [
        analog / name
        for name in div.source_texts(div.cases("pilot")[0])
        if name != "clock_vco_hbt_v3.spice"
    ]
    sources += [
        analog / "clock_vco_hbt_v4.spice",
        counter.CIRCUIT,
        analog / "pll_feedback_chain_v1.spice",
    ]
    methods = sorted(
        {
            str(Path(mod.__file__).resolve())
            for mod in list(sys.modules.values())
            if getattr(mod, "__file__", None)
            and Path(mod.__file__).resolve().is_relative_to(ROOT / "scripts")
        }
    )
    c = dict(
        case="native_open_loop_div80",
        sources=[str(x) for x in sources],
        method_inputs=methods,
        roots=[
            (
                "nssoc_pll_feedback_chain_v1",
                "xchain",
                [
                    "vctrl",
                    "clearb",
                    "clkp",
                    "clkn",
                    "qp",
                    "qn",
                    "fb",
                    "fbbar",
                    "avdd",
                    "dvdd",
                    "cvdd",
                    "0",
                    "0",
                ],
            )
        ],
        extra_vectors=["i(vdd)", "i(vddiv)", "i(vcore)", "i(vctrl)"],
        step_s=5e-12,
        stop_s=34e-9,
        window_s=[4e-9, 34e-9],
        minimum_states=8,
        fixture=[
            "VDD avdd 0 PWL(0 0 500p 2.3)",
            "VDDIV dvdd 0 PWL(0 0 500p 2.5)",
            "VCORE cvdd 0 PWL(0 0 500p 1.2)",
            "VCTRL vctrl 0 PWL(0 0 500p .85)",
            "VRST clearb 0 PWL(0 0 3n 0 3.1n 1.2)",
        ],
    )
    rows = n.graph({p.name: p.read_text() for p in sources}, c["roots"])
    assert len(rows) == 424 and sum(r["model"] == "npn13g2" for r in rows) == 64
    return c


def measure(d, c):
    observed = dict(d)
    for name, value in d.items():
        if name.startswith("v(xloop.xchain."):
            observed[name.replace("v(xloop.xchain.", "v(xchain.", 1)] = value
    r = measure_chain(observed, c)
    # Remove the old external-control annotation: VCTRL is now physically driven.
    r.pop("vctrl_external_v")
    r.pop("closed_pll")
    t = d["time"]
    a, b = c["window_s"]
    b = min(b, float(t[-1]))
    mask = (t >= a) & (t <= b)
    refs = [x for x in n.common.crossings(t, d["v(reference)"], 1.25) if a <= x < b]
    feedback = r["edge_times"]["feedback"]
    phase = [
        dict(
            feedback_s=x,
            reference_s=min(refs, key=lambda y: abs(y - x)),
            feedback_minus_reference_s=x - min(refs, key=lambda y: abs(y - x)),
        )
        for x in feedback
        if refs and min(abs(y - x) for y in refs) < 5e-9
    ]
    ctrl = d["v(vctrl)"]
    pump = -(
        d["i(@n.xloop.xdet.xcp.xpenable.nsg13_hv_pmos[ids])"]
        + d["i(@n.xloop.xdet.xcp.xnenable.nsg13_hv_nmos[ids])"]
    )
    actual = []
    for start in [4e-9, 14e-9, 24e-9]:
        end = min(start + 10e-9, b)
        if end <= start:
            continue
        z = (t >= start) & (t <= end)
        actual.append(
            dict(
                interval_s=[start, end],
                vctrl_mean_v=n.common.integrate(t, ctrl, start, end) / (end - start),
                vctrl_min_v=float(ctrl[z].min()),
                vctrl_max_v=float(ctrl[z].max()),
                up_active_s=n.common.active_time(t, d["v(up)"], 1.25, start, end),
                down_active_s=n.common.active_time(t, d["v(down)"], 1.25, start, end),
                net_native_pump_mean_a=n.common.integrate(t, pump, start, end)
                / (end - start),
            )
        )
    r["connected_loop"] = True
    r["lock_demonstrated"] = False
    r["physical_filter"] = dict(
        upper_rppd_l_um=80,
        lower_rppd_l_um=47,
        both_w_um=1,
        cmim_w_l_um=10,
        ideal_unloaded_dc_ratio=47 / 127,
        notes="Finite biased first-order RC, actual pump ripple/load; no ideal tuning clamp",
    )
    r["phase_observation"] = phase
    r["unpaired_feedback_edges_s"] = [
        x for x in feedback if not refs or min(abs(y - x) for y in refs) >= 5e-9
    ]
    r["windows"] = actual
    # The final feedback edge can precede the next reference beyond this finite
    # capture. Retain it explicitly; never invent a future reference crossing.
    r["checks"]["real_feedback_and_reference_seen"] = (
        len(feedback) >= 3 and len(phase) >= 2
    )
    r["checks"]["physical_detector_active_after_reset"] = (
        sum(x["up_active_s"] + x["down_active_s"] for x in actual[1:]) > 1e-9
    )
    r["checks"]["feedback_lead_delivers_positive_pump"] = (
        len(phase) >= 2
        and all(x["feedback_minus_reference_s"] < 0 for x in phase)
        and all(x["net_native_pump_mean_a"] > 0.5e-6 for x in actual[1:])
    )
    r["checks"]["finite_control_in_development_window"] = bool(
        np.min(ctrl[mask]) >= 0.4 and np.max(ctrl[mask]) <= 1.5
    )
    r["passed"] = all(r["checks"].values())
    return r


def config():
    c = chain_config()
    pfd = n.common.CIRCUIT
    assert n.common.sha(pfd) == n.common.CIRCUIT_SHA
    source = ROOT / "hw/soc/analog/pcie/pll_loop_hbt_v1.spice"
    c["sources"] += [str(pfd), str(source)]
    c["case"] = "connected_physical_loop_startup34ns"
    c["roots"] = [
        (
            "nssoc_pll_loop_hbt_v1",
            "xloop",
            [
                "reference",
                "reset",
                "clearb",
                "clkp",
                "clkn",
                "qp",
                "qn",
                "fb",
                "fbbar",
                "up",
                "down",
                "vctrl",
                "avdd",
                "dvdd",
                "cvdd",
                "0",
                "0",
            ],
        )
    ]
    c["extra_vectors"] = [
        "i(vdd)",
        "i(vddiv)",
        "i(vcore)",
        "i(vreference)",
        "i(vreset)",
    ]
    c["fixture"] = [x for x in c["fixture"] if not x.startswith("VCTRL")]
    c["fixture"] += [
        # Release before the first real feedback edge (~11ns), so the initial
        # phase comparison does not silently discard that edge.
        "VRESET reset 0 PWL(0 0 500p 2.5 8n 2.5 8.1n 0)",
        "VREFERENCE reference 0 PULSE(0 2.5 14n 25p 25p 4.95n 10n)",
    ]
    rows = n.graph(
        {Path(p).name: Path(p).read_text() for p in c["sources"]}, c["roots"]
    )
    assert len(rows) == 539
    return c


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--case", choices=["open_feedback", "loop_startup"], required=True)
    a = p.parse_args()
    c, callback = (
        (chain_config(), measure_chain)
        if a.case == "open_feedback"
        else (config(), measure)
    )
    r = n.run(c, a.out, __file__, callback)
    print(r["status"])
    return 0 if r["status"] == "PASS_NATIVE_FINITE_EXPERIMENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
