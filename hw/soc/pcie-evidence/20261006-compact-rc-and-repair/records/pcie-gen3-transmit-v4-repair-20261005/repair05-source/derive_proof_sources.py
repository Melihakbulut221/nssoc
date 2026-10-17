# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh TX05 normalized proof/controls/ports, preserving the proven kernels."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

B = Path(__file__).resolve().parents[1]
S = Path(__file__).resolve().parent
C = Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05')


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


r = json.loads((C / 'result.json').read_text())
assert r['status'] == 'COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and r['returncode'] == 0
assert r['inputs'] == {p: pin(p) for p in r['inputs']}
assert r['outputs'] == {p.name: pin(p) for p in C.iterdir() if p.is_file() and p.name != 'result.json'}
oldpin = {'bytes': 4175074, 'sha256': '6a284e00cc05f36537fd2b0abfe2854cab433fb41f634989d947a3d987a00c97'}
newpin = pin(C / 'repaired.v')
bridges = []
files = {}


def save(before_path, after_path, after):
    before = before_path.read_text()
    assert not after_path.exists()
    ast.parse(after)
    after_path.parent.mkdir(exist_ok=True)
    after_path.write_text(after)
    a, z = before.splitlines(True), after.splitlines(True)
    opcodes = [dict(tag=t, before=''.join(a[i:j]), after=''.join(z[k:l]))
               for t, i, j, k, l in difflib.SequenceMatcher(None, a, z, autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in opcodes) == before
    assert ''.join(x['after'] for x in opcodes) == after
    bridges.append(dict(before=dict(path=str(before_path), **pin(before_path)), after=dict(path=str(after_path), **pin(after_path)), opcodes=opcodes))
    files[str(after_path)] = pin(after_path)


for oldname, newname in [('normalize_repair03.py', 'normalize_repair05.py'),
                         ('proof_gate_repair03.py', 'proof_gate_repair05.py'),
                         ('replay_repair03.py', 'replay_repair05.py'),
                         ('proof03/compare.py', 'proof05/compare.py'),
                         ('proof03/mutations.py', 'proof05/mutations.py'),
                         ('repair03-source/test_proof_binding.py', 'repair05-source/test_proof_binding.py')]:
    path = B / oldname
    text = path.read_text().replace('repair03', 'repair05').replace('repair-03', 'repair-05').replace('proof03', 'proof05').replace('TX03', 'TX05').replace('tx03', 'tx05').replace('candidate03', 'candidate05').replace(repr(oldpin), repr(newpin))
    if oldname == 'normalize_repair03.py':
        text = text.replace('def on_signal(', 'from owned_lifecycle05 import owned_popen, stop_failed_group\ndef on_signal(', 1)
        start = text.index('def stop_failed_group(')
        end = text.index("for name,net in [('gate'", start)
        text = text[:start] + text[end:]
        text = text.replace('inputs=[pathlib.Path(__file__).resolve(),', "inputs=[pathlib.Path(__file__).resolve(),pathlib.Path(__file__).resolve().parent/'owned_lifecycle05.py',", 1)
    elif oldname == 'proof_gate_repair03.py':
        text = text.replace("B = Path(__file__)", "from owned_lifecycle05 import owned_popen, stop_failed_group\n\nB = Path(__file__)", 1)
        start = text.index("    tree = ast.parse((B / 'postroute_repair05.py')")
        end = text.index('\n    def stop_signal', start)
        text = text[:start] + "    ns = {'stop_failed_group': stop_failed_group}\n" + text[end:]
        text = text.replace("B / 'postroute_repair05.py', NET", "B / 'postroute_repair05.py', B / 'owned_lifecycle05.py', NET")
    elif oldname == 'replay_repair03.py':
        text = text.replace('assert sys.version_info', 'from owned_lifecycle05 import owned_popen, stop_failed_group\n\nassert sys.version_info', 1)
        start = text.index("tree=ast.parse((B/'postroute_repair05.py')")
        end = text.index('\nprocess=None;', start)
        text = text[:start] + "ns={'stop_failed_group':stop_failed_group}" + text[end:]
        text = text.replace("files=[Path(__file__),", "files=[Path(__file__),B/'owned_lifecycle05.py',", 1)
    elif oldname.endswith('test_proof_binding.py'):
        text = text.replace('import pytest\n', "import pytest\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))\n")
        text = text.replace("'postroute_repair05.py']", "'postroute_repair05.py', 'owned_lifecycle05.py']")
    if oldname in ('normalize_repair03.py', 'proof_gate_repair03.py', 'replay_repair03.py'):
        assert 'subprocess.Popen' in text
        text = text.replace('subprocess.Popen(', 'owned_popen(')
    save(path, B / newname, text)
files[str(B / 'owned_lifecycle05.py')] = pin(B / 'owned_lifecycle05.py')
(S / 'proof-source-bridge.json').write_text(json.dumps(bridges, indent=2) + '\n')
freeze = dict(status='TX05_PROOF_PORT_SOURCE_ONLY', candidate=dict(path=str(C / 'repaired.v'), **newpin), candidate_result=pin(C / 'result.json'), files=files,
              method=dict(path=str(Path(__file__)), **pin(Path(__file__))), bridge=pin(S / 'proof-source-bridge.json'),
              scope='Same completed originalgold reused; onlyfreshgate normalized. Identical canonical kernels10faults/binding10controls/3nativeports, oldunsafe teardown replaced withbirth-bound still-alive-only group cleanup. No timeouts or relaxed proof. LaunchparentCPU4; allnative2GiB/floors unchanged.')
(S / 'proof-source-freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
print(json.dumps(dict(candidate=newpin, sources=files), indent=2))
