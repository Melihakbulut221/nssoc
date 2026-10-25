# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Create additive finite closed-output sealer; no native/capture run."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

S = Path(__file__).resolve().parent
B = S.parent
O = B / "repair14a-preroute-preservation"
O.mkdir(exist_ok=False)
old = B / "repair13-preroute-preservation/seal.py"
before = old.read_text()
text = before.replace("repair13", "repair14a").replace("repair-13", "repair-14a").replace("RX13", "RX14A").replace("candidate13", "candidate14a").replace("repair14a-source", "repair14-source")
text = text.replace("repair12-peer", "repair13-peer").replace("repair12/", "repair13/").replace("pcie-rx-repair12-finite", "pcie-rx-repair13-finite").replace("published RX12", "published RX13")
text = text.replace("'nssoc-rx-prefetch-v2-postroute-repair-14a','nssoc-rx-prefetch-v2-repair14a-equivalence'", "'nssoc-rx-prefetch-v2-postroute-repair-14a','nssoc-rx-prefetch-v2-postroute-repair-14b','nssoc-rx-prefetch-v2-postroute-repair-14a-targeted-01','nssoc-rx-prefetch-v2-postroute-repair-14b-targeted-01','nssoc-rx-prefetch-v2-repair14a-equivalence'")
text = text.replace("(B/'repair14-source').iterdir()", "(B/'repair14-source').rglob('*')")
text = text.replace("p.name not in ['drt-launch.log']", "p.name not in ['drt-launch.log','drt14a.log','detailed-rc.log']")
text = text.replace("files['method/repair14-source/'+p.name]=p", "files['method/repair14-source/'+str(p.relative_to(B/'repair14-source'))]=p")
text = text.replace("'postroute_repair14a.py','normalize_repair14a.py'", "'postroute_repair14a.py','postroute_repair14b.py','postroute_repair14a_targeted01.py','postroute_repair14b_targeted01.py','normalize_repair14a.py'")
text = text.replace("repair14-source/grt-screen.json", "repair14-source/targeted-comparison.json")
text = text.replace("Closed candidate14a/GRT/native gate", "Closed both14a/14bGRT and both targeted-only GRT repetitions (same candidate netlist); selected14a native gate")
# Freeze each closed native result's declared outputs before enumerating files.
anchor = " root=Path('/dev/shm')/name;assert root.is_dir()\n"
addition = """ if 'postroute-repair-' in name:
  native=json.loads((root/'result.json').read_text());assert native['status'].startswith('COMPLETE_') and native['returncode']==0
  assert native['inputs']=={p:pin(p) for p in native['inputs']}
  assert native['outputs']=={p:pin(root/p) for p in native['outputs']}
"""
assert text.count(anchor) == 1
text = text.replace(anchor, anchor + addition)
ast.parse(text)
new = O / "seal.py"
new.write_text(text)


def pin(p):
    p = Path(p)
    with p.open("rb") as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())


ops = []
a, z = before.splitlines(True), text.splitlines(True)
for tag, i, j, k, l in difflib.SequenceMatcher(None, a, z, autojunk=False).get_opcodes():
    ops.append(dict(tag=tag, before="".join(a[i:j]), after="".join(z[k:l])))
assert "".join(x["before"] for x in ops) == before and "".join(x["after"] for x in ops) == text
(O / "source-bridge.json").write_text(json.dumps(dict(before=dict(path=str(old), **pin(old)), after=dict(path=str(new), **pin(new)), opcodes=ops), indent=2) + "\n")
(O / "source-freeze.json").write_text(json.dumps(dict(status="FROZEN_RX14A_FOUR_CLOSED_GRT_AND_PROOF_PORT_PRESERVATION", files={str(p): pin(p) for p in [new, O / "source-bridge.json", Path(__file__)]}, active_DRT_included=False, healthy_elapsed_watchdog=None, archive_limit=70 * 1024**2, scratch_floor=528 * 1024**2), indent=2) + "\n")
print(pin(new))
