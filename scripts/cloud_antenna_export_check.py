#!/usr/bin/env python3
import json,os,subprocess,hashlib,zipfile,io,re
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/core-only-antenna-export-check'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING')
 try:
  run=api('actions/runs/44382891924');assert run['conclusion']=='success'and run['head_sha']=='508bb46d0366363d7e79a001ab8a68b230f4fd96'and run['run_attempt']==1
  digest='d5864cb7b9575155444b2ca063010f889c9203ab7bf1a8867b86dba19254c4b3';meta=api('actions/artifacts/14464567635');assert meta['digest']=='sha256:'+digest and meta['workflow_run']['id']==run['id']
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14464567635/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));prefix='core-only-posteco-antenna-reaudit/';src=json.loads(z.read(prefix+'result.json'));assert src['sources_unchanged']and src['status']=='DIODES_INSERTED_AND_IDENTITY_AUDITED_REQUIRES_DETAILED_ROUTING_AND_SIGNOFF'
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(prefix+n)).hexdigest()==h
  tmp=Path(os.environ['RUNNER_TEMP'])/'antenna-power-contact';tmp.mkdir();odb=tmp/'candidate.odb';odb.write_bytes(z.read(prefix+'core-antennas-inserted-unrouted.odb'));assert sha(odb)=='2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750'
  inv=tmp/'inventory.json';inv.write_bytes(z.read(prefix+'insertion-audit.json'));script=OUT/'export.tcl';script.write_text('read_db {'+str(odb)+'}\nwrite_verilog {'+str(OUT/'candidate.v')+'}\nwrite_def {'+str(OUT/'candidate.def')+'}\nputs NSSOC_EXPORT_COMPLETE\n');protected={str(p):sha(p)for p in [Path(__file__),script,inv,odb]}
  r.update(protected_inputs=protected,source_admission=dict(run=run['id'],artifact=meta['id'],digest=digest,verified_outputs=len(src['outputs'])))
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:proc=subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT)
  r['returncode']=proc.returncode;assert proc.returncode==0 and 'NSSOC_EXPORT_COMPLETE'in(OUT/'native.log').read_text()
  cells=json.loads(inv.read_text())['new_cells'];text=(OUT/'candidate.v').read_text();matches={};missing=[];mismatches=[]
  for name,cell in cells.items():
   match=re.search(r'\b'+re.escape(cell['master'])+r'\s+'+re.escape(name)+r'\s*\((.*?)\);',text,re.S)
   if not match:missing.append(name);continue
   terms=dict(re.findall(r'\.([A-Za-z_][A-Za-z0-9_$]*)\s*\(\s*([^()]+?)\s*\)',match.group(1)))
   expected={t['pin']:t['net']for t in cell['signal_terms']}
   actual={k:v for k,v in terms.items()if k in expected}
   if actual!=expected:mismatches.append(dict(instance=name,expected=expected,actual=actual))
   matches[name]=terms
  r.update(new_diodes_expected=len(cells),new_diodes_exported=len(matches),missing_diodes=missing,signal_connection_mismatches=mismatches,netlist_sha256=sha(OUT/'candidate.v'),def_sha256=sha(OUT/'candidate.def'),odb_sha256=sha(odb))
  assert len(cells)==800 and not missing and not mismatches,'Native exported netlist does not represent all added antenna signal terminals'
  assert all(sha(p)==h for p,h in protected.items());r.update(status='ADDED_DIODE_SIGNAL_TERMINALS_PRESENT_IN_NATIVE_EXPORT_NOT_ROUTED_TIMING',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
