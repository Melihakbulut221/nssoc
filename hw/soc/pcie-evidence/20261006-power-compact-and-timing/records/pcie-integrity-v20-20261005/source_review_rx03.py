# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive V20 stimulus-only peer; native/test execution stays with author."""
import ast
import hashlib
import json
from pathlib import Path

R = Path.cwd()
B = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


old = json.loads((B / "source-freeze02.json").read_text())
new = json.loads((B / "source-freeze03.json").read_text())
changed = []
for path, wanted in new["files"].items():
    assert pin(R / path) == wanted
    assert pin(B / "freeze02-sources" / path) == old["files"][path]
    if wanted != old["files"][path]:
        changed.append(path)
assert set(changed) == {
    "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py",
    "sw/tests/test_pcie_gen3_integrity_v20_miter.py",
    "sw/tests/test_pcie_gen3_continuous_rx_integrity_v20.py",
    "sw/tests/test_pcie_gen3_integrity_v20_retire.py",
}
bench = R / changed[0]
# Select by path rather than depending on JSON key order.
bench = R / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py"
previous = (B / "freeze02-sources" / bench.relative_to(R)).read_bytes()
assert bench.read_bytes().startswith(previous)
added = bench.read_bytes()[len(previous):].decode()
assert added.count("@cocotb.test()") == 1
assert "held_cycles >= RING // 2" in added and "witnessed >= RING // 4" in added
assert "assert not int(d.overflow_o.value) and not int(d.halted_o.value)" in added
assert "p.good == p.completed == 1 and p.errors == p.crc_bad == 0" in added
assert "p.ends == 1 and not int(d.active_o.value)" in added
assert "p.expected.append((packet, True))" in added
miter = R / "sw/tests/test_pcie_gen3_integrity_v20_miter.py"
mt = miter.read_text()
assert "reference.framer.read_keep===16'b0" in mt
assert "reference.framer.retire===1'b1" in mt
assert "reference.framer.output_valid===1'b1 && ready_i===1'b0" in mt
assert mt.count('if fault == "retire_never_empty"') == 1
for path in (B / "launch_controls03.py", B / "detach_controls03.py", B / "targeted_controls03.py"):
    ast.parse(path.read_text())
old_launch = ast.parse((B / "launch_controls02.py").read_text())
new_launch = ast.parse((B / "launch_controls03.py").read_text())
for name in ("pin", "limits"):
    a = next(n for n in old_launch.body if isinstance(n, ast.FunctionDef) and n.name == name)
    z = next(n for n in new_launch.body if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast.dump(a) == ast.dump(z)
text = (B / "launch_controls03.py").read_text()
assert "test_actual_miter_fault_is_observed[retire_never_empty]" in text
assert "test_v17_v20_cycle_exact_all_public_outputs[150]" in text
assert "owner.check()" in text and "2*1024**3" in text
assert "start_new_session=True" in (B / "detach_controls03.py").read_text()
receipt = dict(
    status="PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE", freeze=pin(B / "source-freeze03.json"), findings=[],
    method=pin(__file__), source_pins=new["files"], unchanged_product_source_count=5,
    changed_test_paths=changed, all_nine_old_source_snapshots_verified=True,
    previous_full_source_peer=pin(B / "source-only-peer-rx.json"),
    supporting_methods={str(p):pin(p) for p in [B / "launch_controls03.py", B / "detach_controls03.py", B / "targeted_controls03.py"]},
    review="Full four-file diff read. Original14 public cases remain a byte-exact prefix; new15th sends a single six-byte DLLP that fits first beat, keeps that valid beat stalled while committed IDL zero-keep words continue, then releases and checks exact scoreboard, one good/completed packet, one EDS and inactive state. No overflow/halt accepted; minimum held duration and actual reference zero-keep retirement count are mandatory. Reference counter samples real positive-edge retire with committed!=0, read_keep===0, output_valid===1 and ready===0; it does not drive DUT. Only previously undetected retire_never_empty mutant uses new case; other negative stimuli unchanged. Predicate/component proofs and actual passing controls stay retained. Four targeted tests: inverse, failed mutant, full15-case V17 miter, appended direct case. Fresh CPU6/2GiB and original lifecycle retained.",
    earlier_result="Actual initial campaign34PASS/1FAIL is retained. The formerly undetected mutant must now truly fail its selected native test with expected miter diagnostic; source peer does not convert it to PASS. No mapped/timing claim or simulation rerun here.",
    limitations="Source-only approval for targeted tests. Actual held/retirement witnesses, positive scoreboards and fault detection remain unverified until new native controls finish. Two MAX4118 profiles remain outside this campaign.",
)
(B / "source-only-peer-rx03.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(status=receipt["status"], receipt=pin(B / "source-only-peer-rx03.json"))))
