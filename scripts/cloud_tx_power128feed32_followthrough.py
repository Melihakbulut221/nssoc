#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only followthrough from the exact feed32 anchor run to fresh models and RC."""
import argparse,ast,base64,hashlib,json,os,shutil,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-power128feed32-followthrough'
REPO='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def remote(path,ref):
 d=api('contents/'+path+'?ref='+ref)
 if d.get('encoding')!='base64':d=api('git/blobs/'+d['sha'])
 b=base64.b64decode(d['content'])
 assert (ROOT/path).read_bytes()==b,'Checked-out baseline differs from immutable workflow source'
 return b
def plan():
 expected=os.environ['GITHUB_SHA']
 run=39648841180
 live=api('actions/runs/'+str(run));assert live['status']=='completed'and live['conclusion']=='success'
 release=api('releases/tags/cloud-results-39648841180-1-tx-output8088-power128feed32-native-anchors')
 def metadata(ext):
  a=next(a for a in release['assets']if a['name'].endswith(ext))
  b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
  assert a['digest']=='sha256:'+sha(b)
  return a,b,json.loads(b)
 a,b,d=metadata('.summary.json');part,packed,manifest=metadata('.parts.json')
 assert d['source_head']=='1bc1580da8135c4b4b3e064b5d59692f30c35af0'and d['sources_unchanged']
 assert d['status']=='PASS_ALL28620_FULL_PARENT_TERMINALS_WITH20532_METAL8088_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
 assert len(d['binding']['negative_controls'])==6 and all(x['rejected']for x in d['binding']['negative_controls'])
 assert d['binding']['counts']==dict(devices=8088,terminals=28620,metal_terminals=20532,body_terminals=8088,public_ports=165,unique_reference_planes=13370,wire_components=703)
 receipt=dict(run=run,source_head=d['source_head'],summary_asset=a['id'],summary_sha256=sha(b),parts_asset=part['id'],parts_sha256=sha(packed),
  status=d['status'],counts=d['binding']['counts'],negative_controls=d['binding']['negative_controls'],outputs=d['outputs'],sources_unchanged=True,full_phy_accepted=False,electrical_accepted=False)
 files={'docs/evidence/tx-output8088-power128feed32-native-anchors-pass-20261021.json':json.dumps(receipt,indent=2)+'\n'}
 def derivation(basepath,base,candidate,new,scope):
  import difflib
  aa=base.splitlines(True);bb=new.splitlines(True);offsets=[0]
  for line in aa:offsets.append(offsets[-1]+len(line))
  changes=[]
  for tag,i,j,k,l in difflib.SequenceMatcher(a=aa,b=bb,autojunk=False).get_opcodes():
   if tag!='equal':changes.append(dict(start=offsets[i],end=offsets[j],replacement=''.join(bb[k:l])))
  return dict(baseline_path=basepath,baseline_sha256=sha(base.encode()),candidate_path=candidate,candidate_sha256=sha(new.encode()),changes=changes,scope=scope)
 basepath='scripts/cloud_tx_output8088_power128_intrinsic.py';base=remote(basepath,expected).decode()
 new=base.replace('power128','power128feed32')
 for old,val in [('39611514856',str(run)),('1977ced90fb895c5e9ad6963daf56b6613665de31a65d1d07b95a74ec3901034',sha(b))]:
  assert new.count(old)==1;new=new.replace(old,val)
 candidate='scripts/cloud_tx_output8088_power128feed32_intrinsic.py';files[candidate]=new
 files['scripts/tx-output8088-power128feed32-intrinsic-method.json']=json.dumps(derivation(basepath,base,candidate,new,'Only isolated staging paths and immutable actual source pins. All native device/terminal/body/model/19-fault predicates unchanged.'),indent=2)+'\n'
 ctrl=remote('scripts/cloud_tx_output8088_power128_native_rc.py',expected).decode()
 ctrl=ctrl.replace('power128','power128feed32').replace('POWER128','POWER128FEED32')
 source={k:receipt[k]for k in ('run','source_head','summary_sha256','parts_sha256')}
 old=next(l for l in ctrl.splitlines()if l.startswith('SOURCE='))
 ctrl=ctrl.replace(old,'SOURCE='+repr(source))
 files['scripts/cloud_tx_output8088_power128feed32_native_rc.py']=ctrl
 methods={}
 for name,suffix in [('run-rc01.py','run_rc01'),('audit-rc02.py','audit_rc02'),('mutations01.py','mutations01')]:
  basepath='scripts/tx_output8088_power128_'+suffix+'.py';base=remote(basepath,expected).decode()
  old='full_tx_output8088_power128_wires';val='full_tx_output8088_power128feed32_wires'
  count=base.count(old);assert count in (2,4)
  new=base.replace(old,val);candidate='scripts/tx_output8088_power128feed32_'+suffix+'.py'
  files[candidate]=new
  methods[name]=dict(path=candidate,adapted_sha256=sha(new.encode()),baseline_path=basepath,baseline_sha256=sha(base.encode()),
   edits=[dict(before=old,after=val,count=count)],scope='Only new physical conductor-cell name. Same qualified double-total native producer, full raw topology/cap/resistance audit and13 corruptions.')
 files['scripts/tx-output8088-power128feed32-rc-methods.json']=json.dumps(methods,indent=2)+'\n'
 for name in ('intrinsic','native-rc'):
  old='.github/workflows/tx-output8088-power128-'+name+'-cloud.yml'
  files[old.replace('power128','power128feed32')]=remote(old,expected).decode().replace('power128','power128feed32')
 return files,receipt
def collect():
 OUT.mkdir(parents=True,exist_ok=True)
 for name in ('intrinsic','native-rc'):
  src=ROOT/('hw/soc/out/cloud-tx-output8088-power128feed32-'+name)
  dst=OUT/name
  if src.exists():
   assert not dst.exists()
   shutil.move(str(src),str(dst))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 OUT.mkdir(parents=True,exist_ok=False)
 r=dict(status='WAITING_FOR_EXACT_ANCHOR',source_head=os.environ['GITHUB_SHA'],anchor_run=39648841180,
  accepted=False,electrical_accepted=False,full_phy_accepted=False,qualified_pex=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  start=time.monotonic();previous=None
  while True:
   source=api('actions/runs/39648841180')
   assert source['head_sha']=='1bc1580da8135c4b4b3e064b5d59692f30c35af0'and source['run_attempt']==1
   key=(source['status'],source['conclusion'])
   if key!=previous:
    r['anchor_live']=dict(status=key[0],conclusion=key[1]);save()
    print('Exact anchor run',key,flush=True);previous=key
   if source['status']=='completed':
    assert source['conclusion']=='success','Do not consume a failed native source'
    break
   assert time.monotonic()-start<180*60,'Anchor still pending; no cancellation or native restart'
   time.sleep(60)
  files,receipt=plan();r['anchor_receipt']=receipt
  generated=OUT/'generated';generated.mkdir()
  protected={}
  for path,text in files.items():
   if path.endswith('.py'):ast.parse(text,filename=path)
   elif path.endswith('.json'):json.loads(text)
   p=generated/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   if not path.startswith('.github/'):
    target=ROOT/path;assert not target.exists(),('Unexpected existing generated source',path)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text);protected[path]=file_sha(target)
  r['generated_sha256']={p:file_sha(generated/p)for p in files};r['status']='RUNNING_FRESH_NATIVE_INTRINSIC_AND_RC';save()
  def run(name,script):
   log=OUT/(name+'.log')
   with log.open('w')as stream:
    p=subprocess.run([sys.executable,ROOT/script],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
   result_path=ROOT/('hw/soc/out/cloud-tx-output8088-power128feed32-'+name+'/result.json')
   report=json.loads(result_path.read_text())if result_path.is_file()else {}
   return dict(name=name,returncode=p.returncode,status=report.get('status'),sources_unchanged=report.get('sources_unchanged',False),
    report_sha256=file_sha(result_path)if result_path.is_file()else None,log_sha256=file_sha(log),error=report.get('error'))
  tasks=[('intrinsic','scripts/cloud_tx_output8088_power128feed32_intrinsic.py'),('native-rc','scripts/cloud_tx_output8088_power128feed32_native_rc.py')]
  with ThreadPoolExecutor(max_workers=2)as pool:
   futures=[pool.submit(run,*t)for t in tasks];results=[f.result()for f in futures]
  r['results']=results;save()
  assert all(file_sha(ROOT/p)==h for p,h in protected.items()),'Generated pinned source changed during native work'
  assert all(x['returncode']==0 and x['sources_unchanged']for x in results),results
  assert results[0]['status']=='PASS_FULL8088_NATIVE_INTRINSIC_BINDING_65_BODY_NETS_AND19_CONTROLS_REQUIRES_WHOLE_WIRE_RC_AND_LOADED_WAVES'
  assert results[1]['status']=='PASS_FRESH_TX_OUTPUT8088_POWER128FEED32_PRECISE_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
  r.update(status='PASS_FRESH_FEED32_INTRINSIC_AND_RC_REQUIRES_TWO_ORDER_PRECISION_COMPOSITION_AND_FULLWAVE',
   generated_sources_unchanged=True,source_native_process_not_restarted=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  collect()
  r['outputs']={str(p.relative_to(OUT)):file_sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');a=p.parse_args()
 if a.collect:collect()
 else:main()
