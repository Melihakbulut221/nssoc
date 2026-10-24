# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,difflib,hashlib,importlib.util,json,sys,xml.etree.ElementTree as ET
S=Path(__file__).resolve().parent;B=S.parent;N=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04');E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-equivalence');P=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-physical-replay-01');sys.path.insert(0,str(B))
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
spec=importlib.util.spec_from_file_location('rx16one_gate',B/'proof_gate_repair16one.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);binding=gate.verify_binding()
port=json.loads((P/'result.json').read_text());own=json.loads((P/'owned-driver.json').read_text());assert port['status']=='PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING'and port['tests']==dict(passed=6,failed=0,skipped=0);assert own['status']=='PASS_EXACT_PROVED_RX16ONE_SIX_NATIVE_PORT_CASES'
for r in [port,own]:assert r['inputs']=={p:pin(p)for p in r['inputs']}
cases=[]
for p in P.rglob('*.xml'):
 for c in ET.parse(p).getroot().iter('testcase'):assert not any(c.find(k)is not None for k in ('failure','error','skipped'));cases.append(c.attrib)
assert len(cases)==6
proof=json.loads((E/'equivalence.json').read_text());assert proof['states']==1804 and proof['matched']==proof['targets']==5443 and not proof['mismatches'];assert len(json.loads((E/'mutation-controls.json').read_text())['controls'])==10
files={};pairs=[]
for stem in ('drt','detailed_rc'):
 a=B/(stem+'_repair14a.py');z=B/(stem+'_repair16one.py');old=a.read_text();new=old.replace('repair14a','repair16one').replace('RX14A','RX16ONE').replace('rx14a','rx16one').replace('nssoc-rx-prefetch-v2-postroute-repair-14a','nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04').replace('postroute_repair16one.py','postroute_repair16_one04.py')
 new=new.replace('from pathlib import Path','from pathlib import Path\nfrom owned_lifecycle16 import owned_popen, stop_failed_group')
 start=new.index('tree=ast.parse(');end=new.index('save();t=time.monotonic()',start);new=new[:start]+"ns={'stop_failed_group':stop_failed_group}\n"+new[end:]
 new=new.replace('# Exact failure-only helper body is unchanged from the exercised RX11 preflight.','# Exact reviewed WNOWAIT helper owns every child group until descendants close.')
 new=new.replace('files=[Path(__file__),',"files=[Path(__file__),Path(__file__).resolve().parent/'owned_lifecycle16.py',")
 new=new.replace('subprocess.Popen(', 'owned_popen(').replace("r['pid']=p.pid;save()","r['pid']=p.pid;r['owned_identity']=p.nssoc_owned_identity;save()")
 new=new.replace('   complete=True','   assert shutil.disk_usage(\'/dev/shm\').free>=528*1024**2, \'Terminal shared scratch floor\'\n   complete=True')
 if stem=='drt':
  tree=ast.parse(new);rd=next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='r'for t in n.targets));oldscope=next(v.value for k,v in zip(rd.keys,rd.values)if isinstance(k,ast.Constant)and k.value=='scope')
  newscope='RX16one actual-SPEF-first trial from closed RX14A: original critical NOR/buffer strengthened,305resizes/250setupbuffers/1holdbuffer. Mixed WNS-.402 to-.174; cleanGRTsetup-.040985 hold+.108700 is estimates only. Same4ns/full1804state5443function proof,10faults,6nativeportsPASS. Trial selection explicitly supersedes only priorGRTscreen rejection; actualDRT/RC decides, no signoff/PDN/fullchip.'
  assert new.count(oldscope)==1;new=new.replace(oldscope,newscope)
 assert not z.exists();ast.parse(new);z.write_text(new);files[str(z)]=pin(z)
 al=old.splitlines(True);zl=new.splitlines(True);ops=[dict(tag=t,before=''.join(al[i:j]),after=''.join(zl[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,al,zl,autojunk=False).get_opcodes()];assert ''.join(x['before']for x in ops)==old and ''.join(x['after']for x in ops)==new
 pairs.append(dict(before={'path':str(a),**pin(a)},after={'path':str(z),**pin(z)},opcodes=ops))
(S/'route-rc-source-bridge16one.json').write_text(json.dumps(pairs,indent=2)+'\n')
review=dict(status='PASS_RX16ONE_ACTUAL_PROOF_BINDING_AND_SIX_PORT_CASES_REHASHED_BEFORE_DRT',gate_execution_binding=pin(E/'proof-execution-binding.json'),canonical_states=1804,canonical_targets=5443,actual_mutation_controls=10,actual_port_cases=cases,port_receipt=pin(P/'result.json'),port_owner=pin(P/'owned-driver.json'),same_candidate=pin(N/'repaired.v'),scope='Completed exact fresh proof and six native ports; originalgold full byte reuse, no new physical acceptance. GRT screening rejection retained and trial selection additive.')
(S/'pre-drt-proof-port-review16one.json').write_text(json.dumps(review,indent=2)+'\n')
extra=[B/'owned_lifecycle16.py',B/'proof_gate_repair16one.py',S/'route-trial-selection16one.json',S/'proof-source-only-peer-root16one.json',S/'launcher-source-only-peer-root16one.json',S/'proof16one-pipeline01/status.json']
f=dict(status='FROZEN_RX16ONE_ROUTE_RC_SOURCE_BEFORE_NATIVE',files=files,inputs={str(p):pin(p)for p in extra},method=pin(__file__),bridge=pin(S/'route-rc-source-bridge16one.json'),gate_review=pin(S/'pre-drt-proof-port-review16one.json'),limits=dict(cpu=8,address_space=2684354560,entry_free=1073741824,shared_floor=553648128,healthy_elapsed_watchdog=None),scope='Exact old native route/extraction Tcl with new paths and measured candidate scope. Reviewed WNOWAIT ownership replaces unsafe legacy helper; exact native birth stored and terminal shared floor enforced. All original constraints/models and proof+port/zeroDRC/sameV/allhash gates unchanged. No actual route yet.')
(S/'route-rc-source-freeze16one.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
