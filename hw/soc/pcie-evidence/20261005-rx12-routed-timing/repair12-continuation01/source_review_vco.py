# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-byte/bridge audit; never execute reviewed controller."""
from pathlib import Path
import ast
import datetime
import hashlib
import json

C = Path(__file__).resolve().parent
B = C.parent
P = B / "repair12-peer"


def pin(path):
    path = Path(path)
    with path.open("rb") as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, "sha256").hexdigest())


m = json.loads((C / "manifest.json").read_text())
assert pin(C / "run.py") == dict(bytes=10975, sha256="dd538b3d88e5e82695848e85479a4f70650abf25af7798d60747326e2a6aba06")
assert pin(C / "manifest.json") == dict(bytes=13562, sha256="9eca9c1d8a09faec1afbeae1ff80eeb5984bd5ff579e0bf32ad3a968443069df")
assert {p: pin(p) for p in m["inputs"]} == m["inputs"]
assert {p: pin(p) for p in m["route_inputs"]} == m["route_inputs"]
bridges = []
cb = json.loads((C / "source-bridge.json").read_text())
before = Path(cb["source"]["path"]).read_text()
current = before
assert pin(cb["source"]["path"]) == {k: cb["source"][k] for k in ("bytes", "sha256")}
for change in cb["changes"]:
    assert current.count(change["before"]) == change["count"]
    current = current.replace(change["before"], change["after"])
assert current == (C / "run.py").read_text()
for change in reversed(cb["changes"]):
    assert current.count(change["after"]) == change["count"]
    current = current.replace(change["after"], change["before"])
assert current == before
bridges.append(dict(path=str(C / "source-bridge.json"), full_forward_and_inverse_byte_exact=True))

meta = json.loads((P / "source-bridge.json").read_text())
for file, spec in meta["files"].items():
    before = Path(spec["source"]["path"]).read_text()
    current, history = before, []
    assert pin(spec["source"]["path"]) == {k: spec["source"][k] for k in ("bytes", "sha256")}
    assert pin(P / file) == {k: spec["new"][k] for k in ("bytes", "sha256")}
    for change in spec["changes"]:
        prior = current
        assert change["before"] in current
        current = current.replace(change["before"], change["after"], 1 if change["mode"] == "once" else -1)
        positions, start = [], 0
        while True:
            index = prior.find(change["before"], start)
            if index < 0:
                break
            positions.append(index + len(positions) * (len(change["after"]) - len(change["before"])))
            start = index + len(change["before"])
            if change["mode"] == "once":
                break
        assert positions == change["after_offsets"]
        history.append((change, positions, prior))
    assert current == (P / file).read_text()
    for change, positions, prior in reversed(history):
        for pos in reversed(positions):
            assert current[pos:pos + len(change["after"])] == change["after"]
            current = current[:pos] + change["before"] + current[pos + len(change["after"]):]
        assert current == prior
    assert current == before
    bridges.append(dict(path=str(P / file), full_forward_and_inverse_byte_exact=True))

review = (P / "review.py").read_text()
seal = (P / "seal.py").read_text()
run = (C / "run.py").read_text()
for text in (
    "P = N / 'nssoc-rx-prefetch-v2-postroute-repair-12'",
    "D = N / 'nssoc-rx-prefetch-v2-repair12-drt-01'",
    "X = N / 'nssoc-rx-prefetch-v2-repair12-detailed-rc-01'",
    "old = B / 'repair11-peer02/review.json'",
    "'nssoc-rx-prefetch-v2-repair12-equivalence'",
    "'nssoc-rx-prefetch-v2-repair12-physical-replay-01'",
):
    assert text in review
assert "nssoc-rx-prefetch-v2-postroute-repair-11" not in review
root_node = next(node.value for node in ast.parse(seal).body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "roots" for t in node.targets))
roots = ast.literal_eval(root_node)
assert len(roots) == len(set(roots)) == 5
assert all("repair12" in x or "repair-12" in x for x in roots)
assert m["outer_failure_grace_seconds"] == 15 > m["inner_RC_failure_grace_seconds"] == 5
assert m["healthy_elapsed_watchdog_seconds"] is None
assert "elapsed_watchdog_seconds=None" in run

# The reviewed controller is deliberately not launched yet. Inspect only the
# already-existing original route owner, never adopt or signal it.
owner = m["route_owner"]
stat = Path(f"/proc/{owner['pid']}/stat").read_text()
rest = stat[stat.rindex(")") + 2:].split()
assert rest[19] == str(owner["start_ticks"]) and rest[0] != "Z"
native = m["route_native"]
stat = Path(f"/proc/{native['pid']}/stat").read_text()
rest_native = stat[stat.rindex(")") + 2:].split()
assert rest_native[19] == str(native["start_ticks"]) and rest_native[0] != "Z"
paths = [C / "run.py", C / "manifest.json", C / "source-bridge.json", P / "review.py", P / "seal.py",
         P / "source-bridge.json", P / "source-freeze.json", B / "detailed_rc_repair12.py",
         Path(m["lifecycle_source"]), Path.cwd() / "scripts/publish_pcie_native_capture_v3.py"]
record = dict(
    status="PASS_BOUNDED_INDEPENDENT_RX12_SOURCE_ONLY_REVIEW",
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), method=pin(__file__),
    sources={str(p): pin(p) for p in paths}, manifest_input_pins_verified=len(m["inputs"]),
    route_input_pins_verified=len(m["route_inputs"]), independent_source_bridges=bridges,
    candidate_and_capture_roots=roots,
    live_route_snapshot=dict(owner_pid=owner["pid"], owner_start_ticks=rest[19],
                             native_pid=native["pid"], native_start_ticks=rest_native[19], read_only_no_signal=True),
    controller_result_existed=(C / "result.json").exists(), findings=[],
    reviewed_guards=[
        "Existing exact DRT owner/native identities are observed without adopting or signalling the original route. No stale native launch or overwritten output.",
        "Zero-router-DRC successful DRT, exact input/output pins and exact proved RX12 netlist gate the fresh RC directory.",
        "Saved-output review binds repair12 candidate, DRT01 and RC01; the prior timing comparison uses published repair11, with no repair11 candidate substitution.",
        "Saved actual proof execution gate, expanded JSON/gzip pins, ten fault-control outputs, six port XML cases and fully decompressed compiled program are rebound without a new proof run.",
        "Every required repair12 native root must exist. Full native files and additional bound RAM proof inputs enter the capsule. Stable controller source/manifest are archived; the later binding retains the full package member manifest.",
        "All members must remain unchanged and every archive member is rehashed before three immutable V3 assets (archive, finite validation, execution binding). Publisher source and independent peer receipt are manifest-pinned.",
        "Outer 15s failure grace exceeds inner RC 5s cleanup. Exact owned-process lifecycle definitions are reused. No healthy elapsed watchdog; explicit cancellation reaches new dependent stages.",
        "Actual nominal timing FAIL remains publishable evidence; qualified_rc and physical_acceptance remain false.",
    ],
    review_process_correction="Initial read-only audit assumed a running controller and stopped on absent controller result.json. The controller intentionally awaits this source peer; corrected observation checks the existing route owner/native identities. No DUT result or source was changed.",
    scope="Read-only source/byte/bridge review only. No OpenROAD, Icarus, proof, RC, sealer, publisher or controller execution. Future stage success is not inferred.",
)
out = C / "source-only-peer-vco.json"
assert not out.exists()
out.write_text(json.dumps(record, indent=2) + "\n")
print(out, pin(out))
