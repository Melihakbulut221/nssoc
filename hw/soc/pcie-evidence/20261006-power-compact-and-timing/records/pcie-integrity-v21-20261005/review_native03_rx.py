# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
policy=B/'continuation-policy03.json';j=json.loads(policy.read_text());assert pin(policy)==dict(bytes=8258,sha256='d38983b4ec574a354aee36506939170cb37131c8eab273302cdd7fa935b7037d')
for k in ('method_pins','source_pins'):assert j[k]=={p:pin(p)for p in j[k]}
for row in json.loads((B/'native-source-supplement03.json').read_text()):
 a=Path(row['before']['path']).read_text();z=Path(row['after']['path']).read_text();assert a==''.join(x['before']for x in row['opcodes'])and z==''.join(x['after']for x in row['opcodes'])
fun=lambda s:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a=fun((B/'continue_native02.py').read_text());z=fun((B/'continue_native03.py').read_text());assert all(a[k]==z[k]for k in('pin','explicit_stop','verify_sources','stage'))
a=fun((B/'measure_registered_boundary02.py').read_text());z=fun((B/'measure_registered_boundary03.py').read_text());assert a==z
basis=json.loads((B/'native-recovery-basis03.json').read_text())
for k in('map_result','prior_continuation','failure_log'):assert pin(basis[k]['path'])=={n:basis[k][n]for n in('bytes','sha256')}
assert all(not Path('/proc',str(x['pid'])).exists()for x in basis['prior_identities_absent'])
p=Path(basis['map_result']['path']);m=json.loads(p.read_text());assert m['status']=='COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'and m['returncode']==0 and m['cells']==101103
for k,v in m['inputs'].items():assert pin(k)==v
for k,v in m['outputs'].items():assert pin(p.parent/k)==v
mapped=json.loads((p.parent/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v21'];nets=mapped['netnames'];assert len(mapped['cells'])==101103
alias={n:('framer.'+n in nets)for n in('retire','retire_room','retire_pop')};assert not any(alias.values())
assert len(nets['framer.read_ptr']['bits'])==7 and len(nets['framer.retire_valid']['bits'])==1
assert 'KeyError: \'framer.retire\''in Path(basis['failure_log']['path']).read_text()
oldpeer=B/'native-source-only-peer02.json';assert pin(oldpeer)['sha256']=='36170b961a5af8240883011af6fbcef2d1c0c70c3356c3f8fe592b9f2a41c042'
assert not (B/'native-registered-boundary.json').exists()
r=dict(status='PASS_SOURCE_ONLY_V21_MERGED_NATIVE_CONTINUATION',policy=pin(policy),findings=[],method=pin(__file__),detacher=pin(B/'detach_native03.py'),prior_full_source_and345member_peer=pin(oldpeer),completed_map=pin(p),map_inputs_rehashed=len(m['inputs']),map_outputs_rehashed=len(m['outputs']),actual_cells=len(mapped['cells']),actual_removed_aliases=alias,old_failure=pin(basis['prior_continuation']['path']),all_four_prior_PIDs_absent=True,review='Full boundary/controller/detacher deltas read and both fullbyte bridges verified. All recursive graph functions unchanged. Replace absent temporary wire aliases only with actual seven read_ptr FF D plus retire_valid FF D consumer cuts; no original ring or descriptor payloadQ may enter these. Existing corresponding descriptorQ/no direct ringQ outputD checks unchanged. has_dataD intentionally excluded because it captures current readkeep. Exact completed map/source/output pins reused, only map stage removed; remaining import/proof/original4ns lifecycle exact. No process adoption or signals.',scope='Saved completed map and source-only recovery review. No map rerun, boundary execution or new EDA by peer. Fresh actual boundary assertions and STA still pending; original KeyError retained, no DUT failure reclassified as pass.')
(B/'native-source-only-peer03.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
