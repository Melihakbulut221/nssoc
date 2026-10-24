# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive review of two immutable failed captures; never rewrites their result."""
from pathlib import Path
import hashlib,json,re,sys,zipfile
R=Path.cwd();sys.path.insert(0,str(R/'scripts'));import run_cloud_npu_evq_trace as m
B=Path(__file__).resolve().parent;C=B/'evq37187157260'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p
api=json.loads((C/'artifacts-api.json').read_text());run=json.loads((C/'run-api.json').read_text())
assert run['headSha']=='3fead2e8288aae9f2b6a8733ca08aef0d9818f0d' and run['status']=='completed' and run['conclusion']=='failure'
assert len(run['jobs'])==2 and all(x['conclusion']=='failure' for x in run['jobs'])
records={};allpins={}
for variant in ('original','candidate'):
 d=C/variant;z=C/(variant+'.zip');a=next(a for a in api['artifacts'] if a['name']==f'npu-evq-trace-final-{variant}-1')
 assert a['workflow_run']['head_sha']==run['headSha'] and a['workflow_run']['id']==37187157260
 check(z,dict(bytes=a['size_in_bytes'],sha256=a['digest'].removeprefix('sha256:')))
 seen=set()
 with zipfile.ZipFile(z) as archive:
  for member in archive.infolist():
   if member.is_dir():continue
   n=member.filename;assert n not in seen and not Path(n).is_absolute() and '..' not in Path(n).parts
   seen.add(n);assert archive.read(n)==(d/n).read_bytes();allpins[str((d/n).relative_to(R))]=pin(d/n)
 assert len(seen)==114
 row=json.loads((d/'result.json').read_text());original_pin=pin(d/'result.json')
 assert row['status']=='NPU_EVQ_FAILED_OR_INCOMPLETE' and row['error']=="ValueError('Invalid prior/new scalar transition')"
 assert row['github_source_commit']==run['headSha'] and row['variant']==variant and row['cycle_bound']==3000000
 assert not any(row[k] for k in ('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted'))
 assert set(row['methods'])==set(m.PINS)|set(m.OWN)
 for name,h in row['methods'].items():
  check(d/'methods'/name,h)
  if name in m.PINS:assert h['sha256']==m.PINS[name]
 for name,h in row['outputs'].items():check(d/name,h)
 binding=json.loads((d/'evq-bindings.json').read_text());assert binding==row['evq_bindings']
 assert m.digest(binding)==m.lock()['variants'][variant]['binding_sha256']
 assert row['methods'][m.MONITOR]['sha256']==pin(R/m.MONITOR)['sha256']
 assert m.instrument((d/'original-qualified-bench.v').read_text(),binding)==(d/'tb_qualification_boot.v').read_text()
 text=(d/'boot.log').read_text();obs=m.parse(text,d,width=len(binding['signals']))
 assert text.count('QUALIFICATION_MBIST PASS cycles=983043')==1
 boot=m.q.passed_boot(row['boot_execution']['returncode'],text)
 assert boot==(variant=='original')
 new=[]
 for event in obs['new_unknown_transitions']:
  s=binding['signals'][event['signal']];cell=binding['cells'][s['instance']]
  new.append(dict(event,signal_binding=s,conductor=cell['ports'].get(s['field'])))
 semantic={x['name']:x['index'] for x in binding['semantic_observations']}
 samples=[]
 for line in (d/'npu-evq-events.log').read_text().splitlines():
  if line.startswith('S '):
   v=line.split(' all=')[1][::-1];cycle=int(re.search(r'cycle=(\d+)',line)[1]);samples.append(dict(cycle=cycle,values={n:v[i] for n,i in semantic.items()}))
 out=dict(status='PASS_ADDITIVE_RECORDED_CHAIN_REVIEW_NOT_CHIP_ACCEPTANCE',variant=variant,artifact=a,archive=pin(z),archive_member_readback=len(seen),historical_result_unchanged=original_pin,original_failure=row['error'],observed_boot_pass=boot,boot_execution=row['boot_execution'],observation=obs,bound_new_unknown_transitions=new,settled_semantic_samples=samples,source_binding_scope=binding['scope'])
 destination=C/(variant+'-review02.json');destination.write_text(json.dumps(out,indent=2)+'\n');check(d/'result.json',original_pin)
 records[variant]=dict(path=str(destination.relative_to(R)),**pin(destination),events=obs['events'],samples=obs['samples'],live_snapshot_disagreements=len(obs['live_snapshot_disagreements']),new_unknowns=len(new),first_new_unknown=new[0],boot_pass=boot,complete_chip_accepted=False)
allpins.update({str(p.relative_to(R)):pin(p) for p in [Path(__file__).resolve(),R/'scripts/run_cloud_npu_evq_trace.py',R/'sw/tests/test_npu_evq_trace.py',R/m.MONITOR,C/'artifacts-api.json',C/'run-api.json',B/'observer-tests01.log']})
result=dict(status='PASS_TWO_IMMUTABLE_CAPTURES_REVIEWED_WITH_CORRECTED_CALLBACK_CONTRACT',inputs=allpins,reviews=records,scope='Only postprocessing is repeated. The original failed jobs and receipts remain failed. Actual original boot passed28, candidate failed24. Every scalar prior chain and all161settled samples reconcile, live disagreement18/6 retained. First candidate captured unknown at write-pointer D cycle1569426 is an observation boundary, not proven root cause. No timing/RTL/PHY/manufacturing acceptance.')
(C/'root-review02.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(records,indent=2))
