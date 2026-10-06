# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only V20 predicate review; no HDL or pytest execution."""
from pathlib import Path
import ast
import hashlib
import json

R = Path.cwd()
B = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


freeze = json.loads((B / "source-freeze02.json").read_text())
for p, wanted in freeze["files"].items():
    assert pin(R / p) == wanted, p
generator = (R / "scripts/generate_pcie_integrity_retire_v20.py").read_text()
tree = ast.parse(generator)
replacements = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REPLACEMENTS" for t in n.targets))
parent = R / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v19.v"
target = R / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v20.v"
before, after = parent.read_text(), target.read_text()
assert pin(parent)["sha256"] == "f9025c41e9c2aa5f6208f852e30286384bbc9462b164923485d0498600f9daea"
text = before
for a, z in replacements:
    assert text.count(a) == 1
    text = text.replace(a, z)
assert text.replace("integrity_v19", "integrity_v20") == after
text = after.replace("integrity_v20", "integrity_v19")
for a, z in reversed(replacements):
    assert text.count(z) == 1
    text = text.replace(z, a)
assert text == before and len(replacements) == 5
bridges = []
for p in ("hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v19.v", "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v19", "scripts/check_pcie_gen3_continuous_rx_integrity_v19.py", "sw/tests/test_pcie_gen3_continuous_rx_integrity_v19.py"):
    new = p.replace("_v19", "_v20")
    assert (R / new).read_text().replace("integrity_v20", "integrity_v19") == (R / p).read_text()
    bridges.append(dict(parent=p, parent_pin=pin(R / p), candidate=new, candidate_pin=pin(R / new)))
public19 = R / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py"
public20 = R / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v20.py"
assert public19.read_bytes() == public20.read_bytes()
miter = R / "sw/tests/test_pcie_gen3_integrity_v20_miter.py"
old_freeze = json.loads((B / "source-freeze01.json").read_text())
changed = [p for p in freeze["files"] if freeze["files"][p] != old_freeze["files"][p]]
assert changed == ["sw/tests/test_pcie_gen3_integrity_v20_miter.py"]
source = miter.read_text()
slot_branch = source[source.index('    elif fault in ('):source.index('    elif fault in ("retire_always_empty"')]
assert '"retire_always_empty"' not in slot_branch and '"retire_never_empty"' not in slot_branch
assert source.count('"retire_always_empty"') == 3 and source.count('"retire_never_empty"') == 2
assert 'OLD_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v17"' in source
assert '"passed": 14' in source
for p in [B / "launch_controls02.py", B / "detach_controls02.py"]:
    ast.parse(p.read_text())
assert 'resource.RLIMIT_AS,(2*1024**3,2*1024**3)' in (B / "launch_controls02.py").read_text()
assert 'start_new_session=True' in (B / "detach_controls02.py").read_text()
record = dict(
    status="PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE", freeze=pin(B / "source-freeze02.json"), findings=[],
    method=pin(__file__), source_pins=freeze["files"], parent_pin=pin(parent),
    exact_full_source_forward_inverse=True, replacement_count=5, unchanged_wrapper_bridges=bridges,
    public_oracle_byte_equal=dict(old=pin(public19), new=pin(public20)),
    corrected_dispatch="Initial freeze01 listed both retire mutants in the preceding slot-fault branch but not its edits dictionary, causing KeyError before native mutation. Final freeze02 removes only those two first-branch entries; dedicated actual predicate edits and final parameterized tests remain. Historical freeze01 retained; no controls run before correction.",
    four_state_reasoning="Each procedural leaf defaults eligible=0 and only a known-true equality/keep!=0/verdict conjunction sets1. Therefore any eligible keep includes at least one known1; unknown-only keep is masked. At most one constant slot matches a lane address. Known0/1 tree flags select literal payloads without converting Z. Identical procedural lane<count gate masks root eligibility and payload together, including unknown count comparisons. A masked selected lane guarantees a known1 in concatenated read_keep; no lane means literal zero. Thus (read_keep==0) and !read_any are equal known booleans at settled combinational values for all four-state inputs, including unknown pointer bits. The existing enabled/active/committed/output-ready gates stay exact.",
    test_review="Read full literal test, generator, actual leaf RTL, miter changes and launchers. Planned 12288 random literal cases,9216 exhaustive local keep/verdict/count/address patterns,59 selected X/Z cases,31 isolated input events,9 actual read_any mutants plus payload-OR Z mutant; full14 public and V17-reference miter cases preserve quarantine relation, two new actual retire mutants. Tests remain unrun at source review; no functional PASS inferred. Same CPU6/2GiB applies to pytest and literal children; native map separately gated.",
    launchers={str(p):pin(p) for p in [B / "launch_controls02.py", B / "detach_controls02.py"]},
    limitations="Source-only compositional argument and fixed test dispatch, not exhaustive whole-DUT formal or physical timing. No native/compiler/test execution by peer. Two MAX4118 cases excluded from this finite campaign; unchanged4ns/native profile required if controls pass.",
)
(B / "source-only-peer-rx.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(dict(status=record["status"], receipt=pin(B / "source-only-peer-rx.json"))))
