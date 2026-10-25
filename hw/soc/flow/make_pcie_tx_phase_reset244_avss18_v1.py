#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Isolated AVSS trunk 6 -> 18 um candidate; frozen compact circuit and routing."""
import copy, hashlib, inspect, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
import make_pcie_tx_phase_reset244_v1 as q
QUALIFIED = HERE.parent / "make_pcie_tx_phase_reset244_v1.py"
QUALIFIED_SHA = "44d99b1461aee3b9bcec0cb534a8cebd0f7169e476eab7edb71a4116503b5e94"
BASELINE = "docs/evidence/tx-phase-reset334-physical-full-result-20261024.json"
BASELINE_SHA = "5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913"
METHOD = "scripts/tx-phase-reset244-avss18-source-methods.json"
ORIGINAL_EDITS = copy.deepcopy(q.MAIN_EDITS)
OLD_RECT = [109.0, 89.0, 115.0, 2371.0]
NEW_RECT = [103.0, 89.0, 121.0, 2371.0]
TRUNK_EDITS = [
    ('    for net, trunk_x in (("DIV_AVDD", 96.0), ("AVSS", 112.0)):\n',
     '    for net, trunk_x in (("DIV_AVDD", 96.0), ("AVSS", 112.0)):\n'
     '        trunk_half_width = 9.0 if net == "AVSS" else 3.0\n'),
    ('            trunk_x - 3,\n            selected[0]["y_um"] - 3,\n'
     '            trunk_x + 3,\n            selected[-1]["y_um"] + 3,',
     '            trunk_x - trunk_half_width,\n            selected[0]["y_um"] - 3,\n'
     '            trunk_x + trunk_half_width,\n            selected[-1]["y_um"] + 3,'),
    ('            if not (left <= trunk_x - 3 and trunk_x + 3 <= right):',
     '            if not (left <= trunk_x - trunk_half_width and trunk_x + trunk_half_width <= right):'),
]
UNCHANGED = (
    "source_circuit_sha256", "instances", "row_starts_um", "local_buses",
    "additive_power_vias", "peripheral_trunks", "routes", "vias",
    "origin_translation_um", "ports", "bbox_um", "primitive_counts",
    "klayout_version", "preset_polarity", "compact_devices", "finite_body_contacts",
    "actual_expected_LVS_devices", "candidate_source_sha256", "previous_rejected_source_sha256",
    "exactly243_other_compact_devices_unchanged", "sole_device_dimension_delta",
    "explicit_source_device_map", "explicit_row_net_map",
)

def digest(b):
    return hashlib.sha256(b).hexdigest()

def host():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY") == "Melihakbulut221/nssoc"

def methods():
    m = json.loads((ROOT / METHOD).read_text())
    for p, h in m["protected"].items():
        assert digest((ROOT / p).read_bytes()) == h, p
    return m

def baseline():
    b = (ROOT / BASELINE).read_bytes()
    assert digest(b) == BASELINE_SHA
    r = json.loads(b)
    assert r["status"] == "PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET"
    assert r["source_head"] == "2e1f26e9c4fdf37d63433a0c859c2d305db3486b"
    assert set(r["variants"]) == {"p", "n"} and r["validation_errors"] == []
    for polarity in ("p", "n"):
        v = r["variants"][polarity]
        assert v["sources_unchanged"] is True
        old = v["generation"]
        assert old["preset_polarity"] == polarity
        for suffix, h in (("/make_pcie_tx_phase_reset244_v1.py", QUALIFIED_SHA),
                          ("/make_pcie_clock_div4_v10_tail_v1.py", q.BASE_SHA)):
            pins = [x for p, x in old["input_sha256"].items() if p.endswith(suffix)]
            assert pins == [h]
    return r

def derivations():
    assert digest(QUALIFIED.read_bytes()) == QUALIFIED_SHA
    assert digest(q.BASE.read_bytes()) == q.BASE_SHA
    assert q.MAIN_EDITS == ORIGINAL_EDITS and len(ORIGINAL_EDITS) == 8
    flat, original = q.derivations()
    changed = q.exact_replace(original, TRUNK_EDITS)
    # exact_replace verifies single-use substitutions and byte-exact reversal.
    return flat, original, changed, {
        "edits": TRUNK_EDITS,
        "original_main_sha256": digest(original.encode()),
        "candidate_main_sha256": digest(changed.encode()),
        "flatten_sha256": digest(flat.encode()),
        "exact_reversal": True,
    }

def validate_generation(before, after, polarity):
    assert polarity in ("p", "n")
    assert before["preset_polarity"] == after["preset_polarity"] == polarity
    assert len(before["instances"]) == len(after["instances"]) == 334
    assert before["primitive_counts"] == dict(hbt=106, rppd=130, cmim=8, physical_ptap=90)
    assert before["candidate_source_sha256"] == q.CIRCUIT_SHA
    assert before["origin_translation_um"] == [-0.0, -3.97]
    assert before["bbox_um"] == [0, 0, 1440.0, 2413.03]
    for key in UNCHANGED:
        assert before[key] == after[key], ("Changed frozen generation field", key)
    old, new = before["additive_power_straps"], after["additive_power_straps"]
    assert len(old) == len(new) == 32
    changed = [(i, a, b) for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    assert len(changed) == 1
    i, a, b = changed[0]
    assert a == dict(net="AVSS", layer="TopMetal1", role="cross_row_trunk", rect_um=OLD_RECT)
    assert b == dict(net="AVSS", layer="TopMetal1", role="cross_row_trunk", rect_um=NEW_RECT)
    recovered = copy.deepcopy(new); recovered[i] = copy.deepcopy(a)
    assert recovered == old
    for key in ("native_DRC_passed", "native_LVS_passed", "native_wire_ownership_passed",
                "fresh_MIM_RC_passed", "real_selector_load_accepted", "physical_reset_qualified",
                "all31_clock_tree_accepted", "PLL_connected", "full_PHY_accepted"):
        assert after[key] is False
    dx, dy = before["origin_translation_um"]
    return dict(polarity=polarity, changed_strap_index=i,
                source_old_rect_um=OLD_RECT, source_new_rect_um=NEW_RECT,
                native_old_rect_um=[OLD_RECT[0]+dx, OLD_RECT[1]+dy, OLD_RECT[2]+dx, OLD_RECT[3]+dy],
                native_new_rect_um=[NEW_RECT[0]+dx, NEW_RECT[1]+dy, NEW_RECT[2]+dx, NEW_RECT[3]+dy],
                added_source_area_um2=27384.0, all_other_report_geometry_equal=True,
                native_material_difference_proved=False, DRC_LVS_RC_or_electrical_accepted=False)

def main():
    host(); m = methods()
    assert m["native_generation_authorized"] is True, "Source-only candidate; native generation not authorized"
    assert m["simulation_authorized"] is m["extraction_authorized"] is False
    original = baseline()
    flat, old_main, new_main, proof = derivations()
    assert dict(original_main_sha256=proof["original_main_sha256"], candidate_main_sha256=proof["candidate_main_sha256"], flatten_sha256=proof["flatten_sha256"], edit_count=3) == m["source_derivation"]
    # Preserve qualified implementation, top cell names, device/ref construction,
    # native PCells and all pin/via/escape code. Only the declared main edits change.
    saved = copy.deepcopy(q.MAIN_EDITS)
    try:
        q.MAIN_EDITS = saved + copy.deepcopy(TRUNK_EDITS)
        assert q.derivations() == (flat, new_main)
        q.main()
    finally:
        q.MAIN_EDITS = saved
    out = Path(sys.argv[sys.argv.index("--out") + 1]); path = out / "result.json"
    r = json.loads(path.read_text()); polarity = r["preset_polarity"]
    r["avss18_report_comparison"] = validate_generation(original["variants"][polarity]["generation"], r, polarity)
    r["input_sha256"].update({str(HERE): digest(HERE.read_bytes()), str(QUALIFIED): QUALIFIED_SHA,
                              str(ROOT / BASELINE): BASELINE_SHA})
    r["avss18_derivation"] = proof
    r["scope"] = ("Only AVSS TopMetal1 cross-row source trunk 6 to 18 um; all compact circuit, "
                  "instances, finite taps, buses, vias, ports and other route fields unchanged. "
                  "Report equality is not a GDS material proof. Fresh native material comparison, "
                  "ownership, 560 DRC, unsimplified deep/flat LVS, two-order RC and unchanged "
                  "loaded electrical gates remain required. Original electrical rejection remains.")
    path.write_text(json.dumps(r, indent=2, allow_nan=False) + "\n")
    methods()

if __name__ == "__main__":
    main()
