# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare finite paired captures; retain rejected controls and all limits."""
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / "pcie-vco-v6-feedback-bias-v1-20261005"


def pin(path):
    with path.open("rb") as f:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())


def summary(result, review):
    hbt = [x for x in result["safety"]["all_device_bounds"] if x["model"] == "npn13g2"]
    critical = min(hbt, key=lambda x: x["min_settled_vce"])
    return dict(status=result["status"], safety_passed=result["safety"]["passed"],
        accepted_actual_fault=result["accepted_actual_fault"],
        failed_device_screens=[x for x in result["safety"]["all_device_bounds"] if not x["passed"]],
        critical_hbt=critical, nominal_headroom_margin_v=critical["min_settled_vce"] - 0.4,
        failed_functional_checks=[k for k, v in result["measurement"]["checks"].items() if not v],
        vco_frequency_hz=result["measurement"]["vco_frequency_hz"],
        feedback_frequency_hz=result["measurement"]["feedback_frequency_hz"],
        actual_vco_period_counts=result["measurement"]["actual_vco_period_counts"],
        complete_public_cycles=len(review["descriptive_clock_cycles"]),
        all_complete_public_cycles_signed300mV=review["descriptive_all_complete_cycles_signed300mV"],
        rows=result["rows"], values=result["values"])


pairs = {}
for name, old_name in (("085-01", "085-01"), ("06-01", "06-01"), ("disconnect-01", "disconnect-01"), ("modulus-01", "modulus-02")):
    prior_root = OLD if name != "modulus-01" else B.parent / "pcie-vco-v6-feedback-v1-20261005"
    prior_prefix = "bias-v1" if name != "modulus-01" else "v1"
    old_file = Path("/dev/shm/nssoc-vco-v6-feedback-" + prior_prefix + "-" + old_name) / "result.json"
    new_file = Path("/dev/shm/nssoc-vco-v6-feedback-bias-v2-" + name) / "result.json"
    old, new = [json.loads(p.read_text()) for p in (old_file, new_file)]
    assert old["limits"] == new["limits"]
    differences = {key for key in set(old["config"]) | set(new["config"]) if old["config"].get(key) != new["config"].get(key)}
    assert differences <= {"case", "conditioner_change", "method_inputs", "roots", "sources"}
    assert len(old["devices"]) == len(new["devices"]) == 437
    before = {x["path"]: x for x in old["devices"]}
    after = {x["path"]: x for x in new["devices"]}
    deltas = {name for name in before if before[name] != after[name]}
    assert deltas == {"xchain.xdiv.xfirst.xup", "xchain.xdiv.xfirst.xun"}
    for path in deltas:
        assert after[path] == dict(before[path], params=dict(before[path]["params"], l="4u"))
    old_review = json.loads((prior_root / f"review-{old_name}.json").read_text())
    new_review = json.loads((B / f"review-{name}.json").read_text())
    before_summary, after_summary = summary(old, old_review), summary(new, new_review)
    pairs[name] = dict(before=before_summary, after=after_summary,
        previous_pullup_l_um=6.4 if name != "modulus-01" else 8.0, candidate_pullup_l_um=4.0,
        worst_vce_improvement_v=after_summary["critical_hbt"]["min_settled_vce"] - before_summary["critical_hbt"]["min_settled_vce"],
        prior_result=pin(old_file), candidate_result=pin(new_file),
        identical_numeric_config_and_limits=True, only_two_declared_resistor_geometry_changes=True)
result = dict(status="FINITE_MATCHED_GEOMETRY_COMPARISON_COMPLETE", cases=pairs,
    product_acceptance=False, foundry_soa_qualification=False,
    limitations=[
        "Four fixed-control finite native probes; no PVT, thermal, jitter or closed-loop lock qualification.",
        "The 0.4 V HBT screen is a declared speed/headroom development criterion, not a foundry damage limit.",
        "Prior failed captures remain unchanged; each new actual capture retains its own electrical and functional classification.",
        "Only VCO has frozen distributed physical wiring; the changed divider geometry has no routed layout here."])
(B / "paired-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: {"status": v["after"]["status"], "vce_improvement_v": v["worst_vce_improvement_v"], "margin_v": v["after"]["nominal_headroom_margin_v"]} for k,v in pairs.items()}))
