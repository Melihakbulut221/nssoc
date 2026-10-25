#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One predeclared12ns full-wire VCTRL diagnostic, with unchanged native bounds."""

import argparse
import json
from pathlib import Path

import diagnose_pcie_local_vco_powered_v1 as p

h = p.h
PARENT = Path("/dev/shm/nssoc-vco-v4-local-powered-01")
METHOD_SHA = "f6f5a07ec912646c98c0cff776f3001eb5f9a2addd7bf2dbe3a99f703132ff82"
PARENT_SHA = "f1721755e08dcfe14b8d49e5ffd70c3e5af01f660655b33b946204e1d4a0082a"
CONTROLS = (0.4, 0.6)


def change_control(text, value):
    h.require(value in CONTROLS, "Undeclared control voltage")
    before = "Vs_vctrl VCTRL 0 PWL(0 0 500p 0.85)"
    h.require(text.count(before) == 1, "Frozen supply waveform changed")
    return text.replace(before, f"Vs_vctrl VCTRL 0 PWL(0 0 500p {value})")


def classify(metrics):
    failed = [
        int(k)
        for k, v in metrics["hbt_bounds"].items()
        if v["min_vce"] < 0.4
        or v["max_vce"] > 1.6
        or v["peak_abs_current_per_emitter_a"] > 0.003
    ]
    sig = metrics["signals"][0]
    return dict(
        failed_hbts=failed,
        postsettling_hbt_bounds_pass=not failed,
        all_time_upper_vce_pass=metrics["full_time_max_vce"] <= 1.6,
        finite_output_clock_screen_pass=sig["rising_edges"] >= 10
        and sig["minimum_differential_v"] <= -0.3
        and sig["maximum_differential_v"] >= 0.3,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vctrl", type=float, choices=CONTROLS, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    h.require(
        h.pin(Path(p.__file__))["sha256"] == METHOD_SHA
        and h.pin(PARENT / "result.json")["sha256"] == PARENT_SHA,
        "Frozen producer/parent changed",
    )
    prior = json.loads((PARENT / "result.json").read_text())
    h.require(
        all(h.pin(k) == v for k, v in prior["inputs"].items()),
        "Frozen native source/model/runtime changed",
    )
    old = PARENT / "distributed_wire"
    c = next(c for c in prior["cases"] if c["mode"] == "distributed_wire")
    for name in ("bank.spice", "bench.cir", "contract.json", "spinit"):
        h.require(
            h.pin(old / name) == c["outputs"][name], "Original native input changed"
        )
    a.out.mkdir(exist_ok=False)
    for name in ("bank.spice", "contract.json", "spinit"):
        (a.out / name).write_bytes((old / name).read_bytes())
    (a.out / "bench.cir").write_text(
        change_control((old / "bench.cir").read_text(), a.vctrl)
    )
    contract = json.loads((a.out / "contract.json").read_text())
    ng = Path("/dev/shm/nssoc-ngspice47-20261004/root/usr/bin/ngspice")
    result = dict(
        status="RUNNING",
        inputs={
            str(x): h.pin(x)
            for x in [
                Path(__file__),
                Path(p.__file__),
                Path(h.__file__),
                PARENT / "result.json",
                *[
                    old / n
                    for n in ("bank.spice", "bench.cir", "contract.json", "spinit")
                ],
            ]
        },
        vctrl=a.vctrl,
        mode="distributed_wire",
        stream={},
        resources=[],
        full_pex_qualified=False,
        external_body_cref="Distinct ideal0V diagnostic sources; actual13 finite contacts retained; no body spreading invented",
        predeclared_screen=dict(
            stop_s=12e-9,
            maxstep_s=1e-12,
            window_s=[6e-9, 12e-9],
            minimum_edges=10,
            minimum_differential_v=-0.3,
            maximum_differential_v=0.3,
            min_vce=0.4,
            max_vce=1.6,
            max_abs_Ic_per_Nx_a=0.003,
        ),
        scope="Identical62-device446R488C native network; only externalVCTRL value changed. No imposed kick, no thermal/PVT/RF qualification.",
    )

    def save():
        q = a.out / "result.tmp"
        q.write_text(json.dumps(result, indent=2) + "\n")
        q.replace(a.out / "result.json")

    save()
    try:
        p.run_native(a.out, ng, a.out, save, result)
        h.require(
            result["returncode"] == 0 and result["resource_stop"] is None,
            "Native process/resource failure",
        )
        h.require(
            result["stream"].get("complete") and not result["stream"].get("error"),
            "Native waveform incomplete",
        )
        result["audit"] = p.audit_native(a.out, contract)
        result.update(classify(result["audit"]["metrics"]))
        result["status"] = "COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE"
    except BaseException as e:
        result.update(status="FAIL_PRESERVED", error=type(e).__name__ + ": " + str(e))
        save()
        if not isinstance(e, Exception):
            raise
    h.require(
        all(h.pin(k) == v for k, v in result["inputs"].items()),
        "Frozen bias diagnostic input changed",
    )
    result["outputs"] = {
        q.name: h.pin(q)
        for q in a.out.iterdir()
        if q.is_file() and q.name not in ("result.json", "result.tmp")
    }
    save()
    print(result["status"])
    if result["status"] == "FAIL_PRESERVED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
