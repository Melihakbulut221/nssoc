#!/usr/bin/env python3
"""Cloud-only fault injection qualification on the immutable native candidate."""
import os,json,hashlib,subprocess,tempfile
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-residual-audit-controls'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(status='PREPARING',source_head=os.environ['GITHUB_SHA'],accepted=False)
 try:
  head='b386cdf9512ce5fe57ed670e4a0ddbae3ed01a19';run=completed(44322374175,head)
  z,m=archive(run,'core-only-residual-electrical-eco-44322374175')
  assert m['id']==14434813194 and m['digest']=='sha256:12cc118f39137f015b74391973efdd0b912f6876959bfb43640544fc13c28669'
  source=json.loads(z.read('result.json'));assert source['source_head']==head and source['sources_unchanged']
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   prefix='/home/runner/work/nssoc/nssoc/';assert p.startswith(prefix)
   relative=p[len(prefix):]
   if not relative.startswith('hw/soc/out/'):assert sha(ROOT/relative)==h,p
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  audit=ROOT/'scripts/audit_core_only_residual_electrical_strict.py';native=ROOT/'scripts/qualify_core_only_residual_audit_native.py'
  protected={str(p):sha(p)for p in [Path(__file__),audit,native,ROOT/'scripts/buffer_core_only_chip_controls.py']}
  r.update(source_artifact=m,protected_inputs=protected,controls=[])
  for mode in ['positive','new_clock_type','source_clock_type','missing_antenna','buffer_power_open','unrelated_orientation','resized_illegal_rotation','clock_sink_crossbranch']:
   with tempfile.TemporaryDirectory(prefix='nssoc-residual-control-')as tmp:
    work=Path(tmp)
    for name in ['core-routed.odb','eco-legalized.odb','eco-plan.json']:(work/name).write_bytes(z.read(name))
    env=dict(os.environ,NSSOC_CORE_TARGETED_ECO_OUT=tmp,NSSOC_CONTROL_BUFFER_OUT=tmp,NSSOC_FAULT_MODE=mode,NSSOC_AUDIT_SCRIPT=str(audit))
    with (OUT/(mode+'.log')).open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(native)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads((work/'control-result.json').read_text());assert result['mode']==mode
    assert result.get('passed')if mode=='positive'else result.get('rejected')
    r['controls'].append(result);print(mode,'verified',flush=True)
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PASS_NATIVE_RESIDUAL_AUDIT_POSITIVE_AND_SEVEN_FAULT_CONTROLS',sources_unchanged=True,timing_qualified=False,manufacturing_approved=False)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
