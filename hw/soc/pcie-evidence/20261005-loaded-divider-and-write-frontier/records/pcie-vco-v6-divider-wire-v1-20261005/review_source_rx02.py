# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive read-only launcher correction peer, no producer or tests run."""
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent


def pin(path):
    p = Path(path)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def load(path):
    return json.loads(Path(path).read_text())


old = load(B / "source-freeze.json")
new = load(B / "source-freeze02.json")
for p, want in new["pins"].items():
    assert pin(p) == want, p
assert len(new["pins"]) == 173
assert all(new["pins"][p] == want for p, want in old["pins"].items())
assert new["new_sources"] == old["new_sources"]
bridge = load(B / "launcher02-source-bridge.json")
before = (B / "launch_probe01.py").read_text()
after = (B / "launch_probe02.py").read_text()
text = before
for a, z, count in bridge["operations"]:
    assert text.count(a) == count
    text = text.replace(a, z)
assert text == after
for a, z, count in reversed(bridge["operations"]):
    assert text.count(z) == count
    text = text.replace(z, a)
assert text == before
controls = {}
for p in sorted((B / "pytest-handoff02").rglob("handoff-result.json")):
    r = load(p)
    assert r["handlers_restored"] and r["signal"] in ("SIGINT", "SIGTERM")
    assert (r["status"] == "PASS_REAL_SIGNAL_PREVENTED_LAUNCH" and r["launch_attempts"] == []) or (r["status"] == "PASS_REAL_SIGNAL_AFTER_NATIVE_OWNERSHIP_EXIT" and r["child_status"] == "REAPED_NO_LIVE_MEMBERS")
    controls[str(p.relative_to(B))] = dict(pin=pin(p), result=r)
assert len(controls) == 4
for p in (B / "pytest-handoff02").rglob("actual-inner-owner.json"):
    r = load(p)
    assert len(r["processes"]) == 1 and r["processes"][0]["status"] == "REAPED_NO_LIVE_MEMBERS"
    assert r["processes"][0]["returncode"] == 0
assert "4 passed" in (B / "launcher02-controls.log").read_text()
prior = load(B / "source-review-rx01-findings.json")
assert prior["freeze"] == pin(B / "source-freeze.json")
assert prior["status"] == "SOURCE_AND_SAVED_CONTROLS_PASS_LAUNCHER01_CANCELLATION_FIX_REQUIRED"
receipt = dict(
    status="PASS_SOURCE_ONLY_LOADED455_WIRE_MODEL", freeze=pin(B / "source-freeze02.json"), findings=[],
    source_pins=new["new_sources"], all173_inputs_rehashed=True,
    prior_full_source_and_saved_model_review=pin(B / "source-review-rx01-findings.json"),
    prior_review_method=pin(B / "review_source_rx01.py"), method=pin(__file__),
    launcher=pin(B / "launch_probe02.py"), bridge=pin(B / "launcher02-source-bridge.json"),
    actual_saved_handoff_controls=controls,
    corrected_finding="Original empty outer-owner cancellation gap retained in candidate01. Launcher02 installs immediate raising signal handlers before m.run; actual inner native owner temporarily installs graceful handlers, restores raising handlers on exit, and restores caller handlers in finally. Real SIGINT/SIGTERM before entry prevent launch and after actual child reaping propagate. No physics/source/test fixture changes.",
    earlier_peer_diagnostics="Independent reader first assumed logical XD2N is one primitive; raw recipe instead correctly changes the gates of two expanded transistors xpc/xnc. Reader also initially accepted only normal REAPED status, then explicitly validated FAILURE_REAPED plus empty cleanup groups for genuine resource-rejection test. Both failed reader drafts/logs retained; no source or result relaxation.",
    scope="Read-only full source, exact 173 pins, five copied-function forward/inverse, all saved 455-device recipes, 25 component/lifecycle controls and four handoff controls. No native SPICE, model generation, or test replay by reviewer. Source PASS permits finite CPU10 owned probe; no behavior, qualified RC/PEX, full PHY or production claim.",
)
(B / "source-only-peer02-rx.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(status=receipt["status"], receipt=pin(B / "source-only-peer02-rx.json"))))
