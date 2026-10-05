# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve the bounded resistor experiment and every rejected electrical screen."""
from pathlib import Path
import hashlib
import json
import tarfile

R = Path.cwd()
B = Path(__file__).resolve().parent
OLD = B.parent / "pcie-vco-v6-feedback-bias-v1-20261005"
BASE = B.parent / "pcie-vco-v6-feedback-v1-20261005"


def pin(p):
    with p.open("rb") as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())


freeze = dict(json.loads((BASE / "source-freeze-observer-v2.json").read_text()),
              **json.loads((OLD / "source-freeze.json").read_text()),
              **json.loads((B / "source-freeze.json").read_text()))
assert len(freeze) == 19 and all(pin(R / n) == p for n, p in freeze.items())
files = {"project/" + n: R / n for n in freeze}
comparison = json.loads((B / "paired-comparison.json").read_text())
assert comparison["status"] == "FINITE_MATCHED_GEOMETRY_COMPARISON_COMPLETE"
cases = {}
for case in ("085-01", "06-01", "disconnect-01", "modulus-01"):
    peer = json.loads((B / f"root-wave-peer-{case}.json").read_text())
    result_file = Path("/dev/shm/nssoc-vco-v6-feedback-bias-v2-" + case) / "result.json"
    result = json.loads(result_file.read_text())
    assert peer["status"] == "PASS_INDEPENDENT_ALL_RAW_VALUES_AND_437_DEVICE_REDUCTION"
    assert peer["source_native_status_unchanged"] == result["status"]
    assert len(peer["all_device_bounds"]) == 437 and peer["native_off_flags"] == 64
    assert peer["complete_cycles"] and peer["all_complete_cycles_signed300mV"]
    release = json.loads((B / f"release-{case}.json").read_text())
    assert release["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
    assert all(a["authenticated_roundtrip"] and a["anonymous_roundtrip"] for a in release["assets"])
    transport = Path(release["transport_directory"])
    assert pin(transport / "attempts.json") == {k: release["transport_journal"][k] for k in ("bytes", "sha256")}
    for path in sorted(transport.rglob("*")):
        if path.is_file():
            assert path.stat().st_size < 2 * 1024 * 1024
            files[f"transport/{case}/" + str(path.relative_to(transport))] = path
    cases[case] = dict(status=result["status"], safety_passed=result["safety"]["passed"],
        accepted_actual_fault=result["accepted_actual_fault"], values=result["values"],
        independent_peer=pin(B / f"root-wave-peer-{case}.json"),
        release=pin(B / f"release-{case}.json"), comparison=comparison["cases"][case])
    files[f"native-results/{case}/result.json"] = result_file
    for name in (f"root-wave-peer-{case}.json", f"root-wave-peer-{case}.log", f"validation-{case}.json",
                 f"review-{case}.json", f"members-{case}.json", f"release-{case}.json", f"cleanup-{case}.json"):
        files["review/" + name] = B / name
assert all(cases[n]["status"] == "PASS_NATIVE_LOADED_FEEDBACK_SCREEN" for n in ("085-01", "06-01"))
for fault in ("disconnect-01", "modulus-01"):
    assert cases[fault]["status"] == "FAIL_NATIVE_LOADED_FEEDBACK_SCREEN"
    assert cases[fault]["safety_passed"] and cases[fault]["accepted_actual_fault"]
ready = dict(status="FINITE_L4_NOMINAL_AND_ACTUAL_FAULT_SCREENS_READY", source_pins=freeze, cases=cases,
    independently_replayed_values=sum(c["values"] for c in cases.values()),
    product_acceptance=False, original_fault_failures_preserved=True, no_native_rerun=True,
    limitations=comparison["limitations"])
(B / "finite-ready.json").write_text(json.dumps(ready, indent=2) + "\n")
for name in ("source-freeze.json", "source-only-peer.json", "source_peer_review.py", "predeclared-campaign.json", "source-controls01.log", "compare_cases.py", "paired-comparison.json",
             "finite-ready.json", "seal_case.py", "seal_bias_peer.py", "root_wave_peer.py", "root-wave-peer-bridge.json", "cleanup_public_wave.py", "NOTICES.txt"):
    files["review/" + name] = B / name
for name in ("source-freeze.json", "finite-ready.json", "release-bias-peer.json", "bias-peer-members.json", "bias-peer-validation.json"):
    files["prior-review/" + name] = OLD / name
for name in ("Apache-2.0", "CERN-OHL-W-2.0", "CC-BY-4.0"):
    files["licenses/" + name + ".txt"] = R / "LICENSES" / (name + ".txt")
members = {n: pin(p) for n, p in files.items()}
cap = B / "pcie-vco-v6-loaded-feedback-bias-v2-peers.tar.xz"
assert not cap.exists()
with tarfile.open(cap, "w:xz", preset=1) as arc:
    for name, path in files.items():
        arc.add(path, arcname=name, recursive=False)
seen = {}
with tarfile.open(cap, "r|xz") as arc:
    for item in arc:
        assert item.isfile() and item.name not in seen
        seen[item.name] = dict(bytes=item.size, sha256=hashlib.file_digest(arc.extractfile(item), "sha256").hexdigest())
assert seen == members and all(pin(p) == members[n] for n, p in files.items())
(B / "bias-peer-members.json").write_text(json.dumps(members, indent=2) + "\n")
validation = dict(status="SEALED_BOUNDED_L4_EXPERIMENT_AND_INDEPENDENT_NATIVE_REPLAYS",
    archive=dict(path=str(cap), **pin(cap)), members=len(members), finite_ready=pin(B / "finite-ready.json"),
    source_pins=freeze, no_native_rerun=True, product_acceptance=False)
(B / "bias-peer-validation.json").write_text(json.dumps(validation, indent=2) + "\n")
print(json.dumps(validation))
