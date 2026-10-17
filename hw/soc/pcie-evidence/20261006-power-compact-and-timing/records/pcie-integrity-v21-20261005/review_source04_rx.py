# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
fpath=B/'source-freeze04.json';f=json.loads(fpath.read_text());assert pin(fpath)==dict(bytes=3341,sha256='48be11f969876f9738a70f993e31eea6ff63a425a3b26227dfcdc2e55a33d6df')
old=json.loads((B/'source-freeze03.json').read_text())
assert f['sources']=={p:pin(R/p)for p in f['sources']}
assert old['sources']=={p:pin(B/'source-candidate03'/p)for p in old['sources']}
changes=[p for p in f['sources']if f['sources'][p]!=old['sources'][p]]
assert changes==['hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py']
a=(B/'source-candidate03'/changes[0]).read_text();z=(R/changes[0]).read_text();before='raw = wire_dllp(items[0][0]) + bytes(32)';after='raw = wire_dllp(items[0][0]) + bytes(128)';assert a.count(before)==1 and a.replace(before,after)==z
q=(B/'source-candidate03'/changes[1]).read_text();t=(R/changes[1]).read_text();assert t.startswith(q)
extra=t[len(q):];node=ast.parse('def reviewed():\n'+extra).body[0]
assert len(node.body)==2 and isinstance(node.body[0],ast.Assign) and isinstance(node.body[1],ast.If)
mapping=ast.literal_eval(node.body[0].value)
assert mapping=={'fault_descriptor_survives':'AssertionError: V21_OLD_DESCRIPTOR_OWNERSHIP','restart_descriptor_survives':'AssertionError: V21_OLD_DESCRIPTOR_OWNERSHIP','empty_descriptor_blocks':'AssertionError: V21_EMPTY_DRAIN_FAULT','full_descriptor_overwrite':'AssertionError: real finite ring overflow required'}
methods={str(B/n):pin(B/n)for n in ('targeted_controls04.py','launch_controls04.py','detach_controls04.py')}
validation=B/'failed-witness01-validation.json';v=json.loads(validation.read_text());assert pin(validation)==f['actual_failure_correction']['preserved_validation'];assert pin(v['archive']['path'])=={k:v['archive'][k]for k in ('bytes','sha256')}
assert v['pytest_observed_pass']==26 and v['pytest_observed_fail']==1 and v['unqualified_negative'].startswith('fault_descriptor_survives')
assert not Path('/dev/shm/nssoc-integrity-v21-public-controls02').exists()
r=dict(status='PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE',freeze=pin(fpath),findings=[],method=pin(__file__),support_methods=methods,actual_previous_failure=pin(validation),unchanged_source_files=7,delta='Only DLLP kind0 pre-fault idle32 to128 bytes; four expected semantic diagnostic assertions appended. All RTL/generator and strict real fault-edge/handshake/ownership witnesses unchanged. Original15 other positive cases retained; only affected positive, exactinverse and4whole-DUT negatives selected.',lifecycle='Whole launch/detach bodies read: sameCPU6/2GiB inherited bypytest, frozen ProcessOwner post-wait and post-context guards, exclusive marker and detached DEVNULL/file/newsession, no healthy elapsed timeout.',limits='Source-only correction peer; actual positive and meaningful matching negative remain pending. Prior26pytestPASS includes one explicitly invalidated stage-witness negative; not semantic closure. No native mapping authorized until corrected controls and exact merged recount pass.')
(B/'source-only-peer-rx04.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
