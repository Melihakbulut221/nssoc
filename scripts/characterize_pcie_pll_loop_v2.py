# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Correct native channel-current polarity, preserving v1 capture and verdict.

PSP PMOS/NMOS [ids] observations in the pinned native runtime are positive
channel magnitudes. The sourcing-minus-sinking proxy is P-N, not -P-N.
Two independent native clamp-current captures establish its window-mean sign;
instantaneous channel current is not advertised as complete terminal current.
The exact circuit, simulator, device bounds and startup predicates are reused.
"""

import argparse
import json
from pathlib import Path
import characterize_pcie_pll_loop_v1 as base

n = base.n
BASE_SHA = "f2e8fe57309ee15bb73dffc4954720b635842db333f8df81799ddb29e45f0737"


def verify():
    assert n.common.sha(base.__file__) == BASE_SHA
    base.verify_sources()


def channel_pump(data, prefix):
    return (
        data[f"i(@n.{prefix}.xpenable.nsg13_hv_pmos[ids])"]
        - data[f"i(@n.{prefix}.xnenable.nsg13_hv_nmos[ids])"]
    )


def measure(data, config):
    verify()
    result = base.measure(data, config)
    current = channel_pump(data, "xloop.xdet.xcp")
    old = []
    for window in result["windows"]:
        old.append(window.pop("net_native_pump_mean_a"))
        a, b = window["interval_s"]
        window["native_channel_pump_proxy_mean_a"] = n.common.integrate(
            data["time"], current, a, b
        ) / (b - a)
    phase = result["phase_observation"]
    result["checks"]["feedback_lead_delivers_positive_pump"] = (
        len(phase) >= 2
        and all(x["feedback_minus_reference_s"] < 0 for x in phase)
        and all(
            x["native_channel_pump_proxy_mean_a"] > 0.5e-6
            for x in result["windows"][1:]
        )
    )
    result["passed"] = all(result["checks"].values())
    result["current_observation"] = dict(
        version=2,
        definition="positive PMOS channel magnitude minus positive NMOS channel magnitude",
        scope="Window-mean channel-current proxy; not instantaneous full terminal current",
        superseded_v1_negative_sum_means_a=old,
    )
    return result


def replay(folder, output, wave=None, expected_result_sha=None):
    verify()
    assert not output.exists()
    result_path = folder / "result.json"
    # Bind the externally sealed receipt before trusting its inventories.
    assert expected_result_sha is not None
    assert n.common.sha(result_path) == expected_result_sha
    original = json.loads(result_path.read_text())
    assert original["status"] in [
        "PASS_NATIVE_FINITE_EXPERIMENT",
        "FAIL_NATIVE_FINITE_EXPERIMENT",
    ]
    for path, expected in original["inputs"].items():
        assert n.common.pin(path) == expected, path
    for name, expected in original["outputs"].items():
        actual = wave if name == "wave.raw" and wave is not None else folder / name
        assert n.common.pin(actual) == expected, name
    actual = folder / "wave.raw" if wave is None else wave
    data = n.read_raw(
        actual,
        n.vectors(original["devices"], original["config"]["extra_vectors"]),
        True,
    )
    # Reproduce every original scalar before the separately versioned correction.
    assert base.measure(data, original["config"]) == original["measurement"]
    assert (
        n.safety(data, original["devices"], original["config"]["window_s"])
        == original["safety"]
    )
    assert (
        n.validate_time_grid(
            data["time"], original["config"]["stop_s"], original["config"]["step_s"]
        )
        == original["time_grid"]
    )
    corrected = measure(data, original["config"])
    assert n.common.sha(result_path) == expected_result_sha
    passed = corrected["passed"] and original["safety"]["passed"]
    result = dict(
        status="PASS_CORRECTED_FINITE_STARTUP_REVIEW_NO_LOCK"
        if passed
        else "FAIL_CORRECTED_FINITE_STARTUP_REVIEW",
        method=n.common.pin(__file__),
        base_method=n.common.pin(base.__file__),
        original_result=n.common.pin(result_path),
        original_status_preserved=original["status"],
        wave=original["outputs"]["wave.raw"],
        values=len(data) * len(data["time"]),
        raw_samples_changed=False,
        new_spice_execution=False,
        all_inputs_outputs_rehashed=True,
        original_measurements_safety_time_reproduced=True,
        all_device_safety=original["safety"]["passed"],
        measurement=corrected,
        scope="One short nominal connected transistor-loop startup, not acquisition/lock, PVT, timestep convergence, thermal stationarity, jitter, layout or foundry SOA",
    )
    n.common.atomic(output, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--replay", type=Path)
    p.add_argument("--wave", type=Path)
    p.add_argument("--result-sha")
    a = p.parse_args()
    verify()
    if a.replay:
        r = replay(a.replay, a.out, a.wave, a.result_sha)
        good = r["status"] == "PASS_CORRECTED_FINITE_STARTUP_REVIEW_NO_LOCK"
    else:
        assert a.wave is None
        c = base.config()
        c["method_inputs"] += [str(Path(base.__file__))]
        r = n.run(c, a.out, __file__, measure)
        good = r["status"] == "PASS_NATIVE_FINITE_EXPERIMENT"
    print(r["status"])
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
