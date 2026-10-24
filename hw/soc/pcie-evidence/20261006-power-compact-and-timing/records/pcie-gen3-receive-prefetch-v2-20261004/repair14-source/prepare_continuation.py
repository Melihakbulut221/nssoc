# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""New RX14a downstream sources from closed RX13; no native dispatch."""
from pathlib import Path
import ast
import datetime
import difflib
import hashlib
import json
import os

S = Path(__file__).resolve().parent
B = S.parent
R = B.parents[3]
P = B / "repair14a-peer"
C = B / "repair14a-continuation01"
for p in (P, C):
    p.mkdir(exist_ok=False)


def pin(p):
    p = Path(p)
    with p.open("rb") as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())


def transform(text):
    return text.replace("repair13", "repair14a").replace("repair-13", "repair-14a").replace("RX13", "RX14A").replace("rx13_", "rx14a_").replace("repair14a-source", "repair14-source")


bridges = []
for before, after in [(B / "repair13-peer/review.py", P / "review.py"), (B / "repair13-peer/seal.py", P / "seal.py"), (B / "repair13-continuation01/run.py", C / "run.py")]:
    original = before.read_text()
    text = transform(original)
    if after.parent == P:
        text = text.replace("repair12-peer", "repair13-peer").replace("vs12_ns", "vs13_ns").replace("vs_published12_ns", "vs_published13_ns").replace("pcie-rx-repair12-finite", "pcie-rx-repair13-finite").replace("'prior-published/repair12/'", "'prior-published/repair13/'").replace("Earlier routed12 inputs", "Earlier routed13 inputs")
    ast.parse(text)
    after.write_text(text)
    operations = []
    a, z = original.splitlines(True), text.splitlines(True)
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, z, autojunk=False).get_opcodes():
        operations.append(dict(tag=tag, before="".join(a[i:j]), after="".join(z[k:l])))
    assert "".join(x["before"] for x in operations) == original
    assert "".join(x["after"] for x in operations) == text
    bridges.append(dict(before=dict(path=str(before), **pin(before)), after=dict(path=str(after), **pin(after)), opcodes=operations))
(P / "source-bridge.json").write_text(json.dumps(bridges[:2], indent=2) + "\n")
(C / "source-bridge.json").write_text(json.dumps(bridges[2], indent=2) + "\n")
(P / "source-freeze.json").write_text(json.dumps({str(p): pin(p) for p in [P / "review.py", P / "seal.py", P / "source-bridge.json", Path(__file__)]}, indent=2) + "\n")

# Reuse the exact already executed three lifecycle controls, not new claims.
old_controller = ast.parse((B / "repair13-continuation01/run.py").read_text())
new_controller = ast.parse((C / "run.py").read_text())
for name in ("limits", "run_stage", "pin", "atomic", "require"):
    old = next(n for n in ast.walk(old_controller) if isinstance(n, ast.FunctionDef) and n.name == name)
    new = next(n for n in ast.walk(new_controller) if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast.dump(old) == ast.dump(new)
old_main = next(n for n in old_controller.body if isinstance(n, ast.FunctionDef) and n.name == "main")
new_main = next(n for n in new_controller.body if isinstance(n, ast.FunctionDef) and n.name == "main")
assert ast.dump(old_main.body[-2]) == ast.dump(new_main.body[-2])
control_dir = B / "repair13-continuation01"
control_inputs = [control_dir / "run.py", control_dir / "lifecycle-controls.json", control_dir / "check_lifecycle_boundaries.py", *sorted((control_dir / "lifecycle-controls").rglob("*"))]
control_inputs = [p for p in control_inputs if p.is_file()]
reused = dict(status="REUSED_BYTE_EXACT_ACTUAL_RX13_LIFECYCLE_CONTROLS_NO_RERUN", exact_stage_and_post_context_AST=True, inputs={str(p): pin(p) for p in control_inputs}, controls=3, scope="Existing actual completion SIGTERM, teardown SIGTERM and child nonzero controls reused for unchanged lifecycle bodies. Native paths/labels only changed; no new control execution.")
(C / "lifecycle-controls-reuse.json").write_text(json.dumps(reused, indent=2) + "\n")

old_manifest = json.loads((B / "repair13-continuation01/manifest.json").read_text())
manifest = json.loads(transform(json.dumps(old_manifest)))
route = json.loads(Path("/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01/result.json").read_text())
active = json.loads((S / "active-drt.json").read_text())
assert route["status"] == "RUNNING" and route["pid"] == active["native"]["pid"]
manifest.update(route_owner=active["owner"], route_native=active["native"], route_inputs=route["inputs"], boot_id=active["boot_id"], utc=datetime.datetime.now(datetime.UTC).isoformat())
manifest["stages"][2] = "frozen independent saved-output review vs published RX13"
paths = [Path(p) for p in manifest["inputs"]]
replacements = {
    str(S / "proof-source-only-peer-root.json"): S / "proof-source-peer-root02.json",
    str(S / "route-rc-source-only-peer-root.json"): S / "route-rc-source-only-peer-vco.json",
    str(C / "lifecycle-controls.json"): C / "lifecycle-controls-reuse.json",
    str(C / "check_lifecycle_boundaries.py"): control_dir / "check_lifecycle_boundaries.py",
}
paths = [replacements.get(str(p), p) for p in paths]
paths += control_inputs + [S / "targeted-source-only-peer-pll.json", S / "targeted-comparison.json", S / "route-rc-source-freeze.json", Path(__file__)]
manifest["inputs"] = {str(p): pin(p) for p in paths}
for p, wanted in manifest["route_inputs"].items():
    assert pin(p) == wanted
for row in [manifest["route_owner"], manifest["route_native"]]:
    fields = (Path("/proc") / str(row["pid"]) / "stat").read_text().rsplit(") ", 1)[1].split()
    assert str(fields[19]) == str(row["start_ticks"]) and fields[0] != "Z"
    assert os.sched_getaffinity(row["pid"]) == {8}
(C / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(dict(status="FROZEN_FRESH_RX14A_DEPENDENT_CHAIN_NO_EXECUTION", sources={str(p): pin(p) for p in [P / "review.py", P / "seal.py", C / "run.py", C / "manifest.json"]}, manifest_inputs=len(manifest["inputs"])), indent=2))
