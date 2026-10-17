#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Intrinsic-only pilot of six real smaller MIMs; no inherited physical claim.

Reuse the pinned native solver, complete-wave measurements, external body
boundary and bounded streaming controller. The original 62-device intrinsic
reference and fresh candidate differ only in six literal capacitor geometries.
No elapsed cancellation; no RC network is substituted into this pilot.
"""

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

import diagnose_pcie_local_vco_powered_v8 as base

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v4.spice"
NEW = ROOT / "hw/soc/analog/pcie/clock_vco_hbt_v5.spice"
OLD_SHA = "0f6eaecc4b5ff7eddf992fecfa7d6015ab6a93807ffc56f2c99d4fbb84a0a8e7"
MODEL_RECEIPT_SHA = "a4dd1976bb12df5a03c8061b44400a95026c6ee59594ebe6c97dfb30cd13936e"
NEW_SHA = "c657c4e5205b31da3ee56f1a277b0370a16933d329a78671106adc43d3f48434"
BASE_SHA = "34d7c1c7eb7d57fb19d47c097d9fac2375433ce7855d25499dffbb119b235a59"
CAPS = {"CP0": ("11.7u", "11.5u")}
CAPS.update({n: ("11.5u", "11.5u") for n in ("CN0", "CP1", "CN1", "CP2", "CN2")})
require = base.h.require
pin = base.h.pin


def source_delta(old, new):
    """Require exact ordered statements and named six-device-only delta."""
    before = base.h.statements(old)
    after = base.h.statements(new)
    expected = copy.deepcopy(before)
    expected[0][1] = "nssoc_clock_vco_hbt_v5"
    expected[-1][1] = "nssoc_clock_vco_hbt_v5"
    changes = []
    for row in expected[1:-1]:
        name = row[0][1:]
        if name not in CAPS:
            continue
        width, length = CAPS[name]
        require(row[3] == "cap_cmim", "Named capacitor model changed")
        require(
            row[4:] == ["w=12.2u" if name == "CP0" else "w=12u", "l=12u"],
            "Original capacitor geometry changed",
        )
        changes.append(
            dict(name=name, old=row.copy(), new=row[:4] + ["w=" + width, "l=" + length])
        )
        row[4:] = ["w=" + width, "l=" + length]
    require(
        len(before) == len(after) == 51 and len(changes) == 6,
        "Exact 49-primitive circuit required",
    )
    require(expected == after, "Only six native MIM dimensions and top name may change")
    return changes


def candidate_composition(comp, binding, variant):
    """Create pre-layout simulator records without claiming new native geometry."""
    require(variant in ("original", "candidate"), "Unknown variant")
    require(
        len(comp["records"]) == 62
        and comp["finite_contacts"] == 13
        and comp["body_well_terminals"] == 56,
        "Full intrinsic reference required",
    )
    out = copy.deepcopy(comp)
    names = {d["native_id"]: d["source_name"] for d in binding["devices"]}
    require(
        len(names) == 62
        and len(set(names.values())) == 62
        and len({d["native_id"] for d in comp["records"]}) == 62,
        "Complete unique named reference required",
    )
    seen = set()
    for d in out["records"]:
        name = names[d["native_id"]]
        if name not in CAPS:
            continue
        require(d["model"] == "cap_cmim", "Named capacitor is not native MIM")
        require(
            [t["terminal"] for t in d["terminals"]] == ["mim_top", "mim_btm"],
            "Native MIM terminal order changed",
        )
        original = {"w": "12.2u" if name == "CP0" else "12.0u", "l": "12.0u"}
        require(
            d["simulator_parameters"] == original, "Reference MIM parameters changed"
        )
        tokens = d["line"].split()
        require(
            tokens[0] == f"XD{d['native_id']:04d}"
            and tokens[1:3] == [t["node"] for t in d["terminals"]]
            and tokens[3:] == ["cap_cmim", "w=" + original["w"], "l=" + original["l"]],
            "Reference MIM source bridge changed",
        )
        if variant == "candidate":
            d["baseline_native_parameters"] = d.pop("native_parameters")
            w, l = CAPS[name]
            d["proposed_parameters"] = d["simulator_parameters"] = dict(w=w, l=l)
            d["line"] = " ".join(tokens[:4] + ["w=" + w, "l=" + l])
        seen.add(name)
    require(seen == set(CAPS), "Missing or repeated named MIM")
    out["status"] = "INTRINSIC_ONLY_NAMED_REFERENCE_NO_NEW_GEOMETRY_CLAIM"
    out["candidate_geometry_qualified"] = False
    return out


def cycle_screen(path, contract):
    """All complete rising-to-rising cycles in the original 6..12 ns window."""
    cycles = []
    current = prior = None
    with gzip.open(path, "rt") as stream:
        header = stream.readline().split()
        require(header[1:] == contract["vectors"], "Cycle vector header differs")
        pi, ni = header.index("v(CLKP)"), header.index("v(CLKN)")
        for line in stream:
            row = line.split()
            t = float(row[0])
            value = float(row[pi]) - float(row[ni])
            if prior and prior[1] < 0 <= value:
                cross = prior[0] + (t - prior[0]) * (-prior[1]) / (value - prior[1])
                if cross >= base.BEGIN:
                    if current is not None:
                        current["end_s"] = cross
                        current["both_300mv"] = (
                            current["min_v"] <= -0.3 and current["max_v"] >= 0.3
                        )
                        cycles.append(current)
                    current = dict(start_s=cross, min_v=0.0, max_v=0.0)
            if current is not None:
                current["min_v"] = min(current["min_v"], value)
                current["max_v"] = max(current["max_v"], value)
            prior = (t, value)
    return dict(
        cycles=cycles,
        all_complete_cycles_pass=bool(cycles) and all(c["both_300mv"] for c in cycles),
    )


def classify(audit, cycles):
    m = audit["metrics"]
    failures = [
        int(k)
        for k, v in m["hbt_bounds"].items()
        if v["min_vce"] < 0.4
        or v["max_vce"] > 1.6
        or v["peak_abs_current_per_emitter_a"] > 0.003
    ]
    require(len(m["hbt_bounds"]) == 30, "All 30 HBT measurements required")
    sig = m["signals"][0]
    require(
        len(cycles["cycles"]) == max(0, sig["rising_edges"] - 1),
        "Complete cycle census differs",
    )
    passed = (
        not failures
        and m["full_time_max_vce"] <= 1.6
        and audit["numerical_clean"]
        and sig["rising_edges"] >= 10
        and cycles["all_complete_cycles_pass"]
    )
    return dict(
        status="PASS_FINITE_INTRINSIC_SCREEN_NOT_PHYSICAL_ACCEPTANCE"
        if passed
        else "FAIL_FINITE_INTRINSIC_SCREEN_PRESERVED",
        failed_hbts=failures,
        complete_cycles=len(cycles["cycles"]),
        all_complete_cycles_pass=cycles["all_complete_cycles_pass"],
        frequency_hz=sig["mean_frequency_hz"],
        passed=passed,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in (
        "composition",
        "anchors",
        "source_binding",
        "model_receipt",
        "ngspice",
        "pdk",
        "osdi_root",
        "out",
    ):
        ap.add_argument("--" + n.replace("_", "-"), type=Path, required=True)
    ap.add_argument("--variant", choices=("original", "candidate"), required=True)
    a = ap.parse_args()
    require(
        pin(Path(base.__file__))["sha256"] == BASE_SHA
        and pin(Path(base.h.__file__))["sha256"] == base.METHOD_SHA,
        "Frozen parent method changed",
    )
    require(
        pin(OLD)["sha256"] == OLD_SHA and pin(NEW)["sha256"] == NEW_SHA,
        "Literal circuit pin changed",
    )
    delta = source_delta(OLD.read_text(), NEW.read_text())
    for n in ("composition", "anchors", "source_binding"):
        require(
            pin(getattr(a, n))["sha256"] == base.INPUT_PINS[n],
            "Frozen named reference input differs",
        )
    require(pin(a.ngspice)["sha256"] == base.NG_SHA, "Native runtime differs")
    require(
        a.out.parent == Path("/dev/shm")
        and a.out.name.startswith("nssoc-vco-v4-mim-v5-"),
        "Output must remain in counted owned scratch",
    )
    require(
        base.shared_free() >= 1024**3
        and base.owned_size(a.out) + base.LAUNCH_HEADROOM <= base.OWN_LIMIT,
        "Original 1GiB admission / owned80MiB headroom unavailable",
    )
    binding = json.loads(a.source_binding.read_text())
    comp = candidate_composition(
        json.loads(a.composition.read_text()), binding, a.variant
    )
    anchors = json.loads(a.anchors.read_text())
    mapping = base.physical_to_ideal(comp, anchors)
    models = a.pdk / "libs.tech/ngspice/models"
    osdis = [a.osdi_root / n for n in ("r3_cmc.osdi", "psp103.osdi", "psp103_nqs.osdi")]
    require(
        pin(a.model_receipt)["sha256"] == MODEL_RECEIPT_SHA,
        "Original full model receipt differs",
    )
    receipt = json.loads(a.model_receipt.read_text())
    for p in [*models.glob("*.lib"), *osdis]:
        require(
            str(p) in receipt["inputs"] and pin(p) == receipt["inputs"][str(p)],
            "Original native model/OSDI differs",
        )
    inputs = {
        str(p): pin(p)
        for p in [
            Path(__file__),
            Path(base.__file__),
            Path(base.h.__file__),
            OLD,
            NEW,
            a.composition,
            a.anchors,
            a.source_binding,
            a.model_receipt,
            a.ngspice,
            *models.glob("*.lib"),
            *osdis,
        ]
    }
    a.out.mkdir(exist_ok=False)
    result = dict(
        status="RUNNING",
        variant=a.variant,
        inputs=inputs,
        source_delta=delta,
        cases=[],
        intrinsic_only=True,
        candidate_geometry_qualified=False,
        full_pex_qualified=False,
        body_reference_assumption="Same explicit ideal external BODY_SUBSTRATE/WIRE_CREF; retain13finitecontacts/56body identities. No modeled body spreading R.",
        assumptions=dict(
            vdd=2.3,
            vctrl=0.6,
            temp_c=27,
            load_each_f=50e-15,
            ramp_s=0.5e-9,
            stop_s=base.STOP,
            maxstep_s=base.STEP,
            operating_window_s=[base.BEGIN, base.STOP],
        ),
        scope="Pre-layout intrinsic comparison only. No new GDS, extractedRC, PVT, thermal equilibrium, RF, PLL or PHY acceptance.",
    )

    def save():
        data = (json.dumps(result, indent=2) + "\n").encode()
        require(
            2 * len(data) <= base.RECEIPT_RESERVE
            and base.owned_size(a.out) + len(data) <= base.OWN_LIMIT
            and base.shared_free() - len(data) >= base.SHARED_RESERVE,
            "Atomic receipt resource reserve unavailable",
        )
        p = a.out / "result.tmp"
        p.write_bytes(data)
        p.replace(a.out / "result.json")

    root = a.out / "intrinsic_only"
    root.mkdir()
    contract = base.vector_contract(comp, mapping, "intrinsic_only", binding)
    (root / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    (root / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")
    (root / "bank.spice").write_text(base.circuit(comp, "", mapping, "intrinsic_only"))
    native_deck = base.deck(comp, contract, models, osdis, 0.6).splitlines()
    native_deck[0] = (
        "Intrinsic-only VCOv5 MIM pilot; explicit ideal external body references; variant "
        + a.variant
    )
    (root / "bench.cir").write_text("\n".join(native_deck) + "\n")
    (root / "spinit").write_text("* Explicit native OSDI model loading only.\n")
    row = dict(mode="intrinsic_only", status="RUNNING", stream={}, resources=[])
    result["cases"].append(row)
    save()
    try:
        base.run_native(root, a.ngspice, a.out, save, row)
        require(
            row["returncode"] == 0
            and row["resource_stop"] is None
            and row["stream"].get("complete") is True
            and not row["stream"].get("error"),
            "Native process/resource/capture failure",
        )
        row["audit"] = base.audit_native(root, contract)
        row["cycles"] = cycle_screen(root / "wave.dat.gz", contract)
        row["screen"] = classify(row["audit"], row["cycles"])
        row["status"] = "COMPLETE_NATIVE_INTRINSIC_DIAGNOSTIC"
        result["status"] = row["screen"]["status"]
    except BaseException as e:
        row.update(status="FAIL_PRESERVED", error=type(e).__name__ + ": " + str(e))
        result["status"] = "FAIL_PRESERVED"
        save()
        if not isinstance(e, Exception):
            raise
    row["outputs"] = {p.name: pin(p) for p in root.iterdir() if p.is_file()}
    require(
        all(pin(p) == h for p, h in inputs.items()), "Frozen pilot source/input changed"
    )
    save()
    print(result["status"])
    if not row.get("screen", {}).get("passed", False):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
