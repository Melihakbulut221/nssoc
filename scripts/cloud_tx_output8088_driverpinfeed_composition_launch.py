#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose exact driver-pinfeed RC after completed two-order native evidence."""
import ast,difflib,hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-composition'
STAGE=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-composition-launch'
REPO='repos/Melihakbulut221/nssoc/'
FRESH_RUN=40071489977
FRESH_HEAD='b00c6f400c60190ff4ddcba200bbe0d6f92c8fe7'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def metadata(group,run,head):
 release=api('releases/tags/cloud-results-'+str(run)+'-1-'+group)
 out={}
 for suffix,key in [('.summary.json','summary'),('.parts.json','parts')]:
  assets=[a for a in release['assets']if a['name']==group+'-'+str(run)+'-1'+suffix]
  assert len(assets)==1
  a=assets[0];b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
  assert a['digest']=='sha256:'+sha(b)
  out[key]=json.loads(b);out[key+'_asset']=a['id'];out[key+'_sha256']=sha(b);out[key+'_bytes']=len(b)
 assert out['summary']['source_head']==head
 return out
def derivation(path,base,new):
 aa=base.splitlines(True);bb=new.splitlines(True);offset=[0]
 for line in aa:offset.append(offset[-1]+len(line))
 changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=aa,b=bb,autojunk=False).get_opcodes():
  if tag!='equal':changes.append(dict(start=offset[i],end=offset[j],replacement=''.join(bb[k:l])))
 return dict(baseline_path=path,baseline_sha256=sha(base.encode()),candidate_sha256=sha(new.encode()),changes=changes,
  scope='Only candidate names, immutable evidence source and exact newly extracted R/C counts. All original intrinsic/terminal/interface/multiset and25-fault gates unchanged.')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 locked=json.loads((ROOT/'scripts/tx-driverpinfeed-composition-launch-methods.json').read_text())
 assert all(digest(ROOT/p)==h for p,h in locked.items())
 STAGE.mkdir(parents=True,exist_ok=False)
 r=dict(status='RESTORING_EXACT_NATIVE_SOURCES',source_head=os.environ['GITHUB_SHA'],
  full_phy_accepted=False,electrical_accepted=False,qualified_pex=False,no_new_simulation=True)
 generated={}
 def save():(STAGE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def write(path,data):
  assert path.startswith(('scripts/','docs/evidence/'))and '..'not in Path(path).parts
  if path.endswith('.py'):ast.parse(data,filename=path)
  if path.endswith('.json'):json.loads(data)
  p=ROOT/path
  if p.exists():assert p.read_bytes()==data,('Checked-in source differs from qualified source',path)
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  generated[path]=sha(data)
 save()
 try:
  pin=json.loads(os.environ['NSSOC_TX_PRECISION_SOURCE'])
  assert set(pin)=={'run','source_head','summary_sha256','parts_sha256'}
  assert isinstance(pin['run'],int)and pin['run']>0
  q=api('actions/runs/'+str(pin['run']))
  assert q['status']=='completed'and q['conclusion']=='success'and q['head_sha']==pin['source_head']and q['run_attempt']==1
  assert q['head_branch']=='codex/tx-via3-rail-diagnosis'
  assert q['path']=='.github/workflows/tx-output8088-driverpinfeed-precision-cloud.yml'
  pr=metadata('tx-output8088-driverpinfeed-precision',pin['run'],pin['source_head'])
  assert all(pr[k]==pin[k]for k in ('summary_sha256','parts_sha256'))
  precision=pr['summary']
  assert precision['status']=='PASS_ACTUAL8088_DRIVERPINFEED_NATIVE_RC_DOUBLE_TOTALS_TWO_ORDERS_AND13_CONTROLS_EACH_NOT_FULL_PHY'
  assert precision['sources_unchanged']and precision['both_native_input_orders_verified']
  assert precision['no_rc_records_changed']and precision['no_geometry_technology_or_threshold_change']
  assert precision['launcher']['generated_sources_unchanged']
  assert precision['launcher']['source_run']==FRESH_RUN and precision['launcher']['source_head']==FRESH_HEAD
  hashes=precision['launcher']['generated_sha256']
  names=['launcher-evidence/generated/'+p for p in hashes]
  assert all(precision['outputs'][n]==hashes[n[len('launcher-evidence/generated/'):]]for n in names)
  reports.OUT=STAGE
  prior,proof=reports.restore_report('tx-output8088-driverpinfeed-precision',pin['run'],pr['summary_sha256'],pr['parts_sha256'],STAGE/'source',names)
  assert prior==precision;r['source_restore']=proof
  for n in names:
   p=n[len('launcher-evidence/generated/'):];b=(STAGE/'source'/n).read_bytes()
   assert sha(b)==hashes[p];write(p,b)
  q=api('actions/runs/'+str(FRESH_RUN))
  assert q['status']=='completed'and q['conclusion']=='success'and q['head_sha']==FRESH_HEAD and q['run_attempt']==1
  combined=metadata('tx-driverpinfeed-followthrough',FRESH_RUN,FRESH_HEAD)['summary']
  assert combined['status']=='PASS_FRESH_DRIVERPINFEED_INTRINSIC_AND_RC_REQUIRES_TWO_ORDER_PRECISION_COMPOSITION_AND_FULLWAVE'
  ip=metadata('tx-output8088-driverpinfeed-intrinsic',FRESH_RUN,FRESH_HEAD);intrinsic=ip['summary']
  assert next(x for x in combined['results']if x['name']=='intrinsic')['report_sha256']==ip['summary_sha256']
  assert intrinsic['status']=='PASS_FULL8088_NATIVE_INTRINSIC_BINDING_65_BODY_NETS_AND19_CONTROLS_REQUIRES_WHOLE_WIRE_RC_AND_LOADED_WAVES'
  assert intrinsic['sources_unchanged']and len(intrinsic['controls'])==19
  audit=precision['variants']['precise']['audit']
  nr=audit['actual_exported_resistors'];nc=audit['actual_exported_capacitors']
  assert type(nr)is type(nc)is int and nr>0 and nc>0
  assert all(precision['variants'][order]['audit']['actual_exported_resistors']==nr and precision['variants'][order]['audit']['actual_exported_capacitors']==nc for order in ('precise','precise_reversed'))
  docs={
   'precision-pass':dict(run=pin['run'],source_head=pin['source_head'],
    summary_asset_id=pr['summary_asset'],summary_sha256=pr['summary_sha256'],summary_bytes=pr['summary_bytes'],
    parts_asset_id=pr['parts_asset'],parts_sha256=pr['parts_sha256'],parts_bytes=pr['parts_bytes']),
   'composition-input':dict(run=pin['run'],source_head=pin['source_head'],workflow_path='.github/workflows/tx-output8088-driverpinfeed-precision-cloud.yml'),
   'intrinsic-pass':dict(run=FRESH_RUN,source_head=FRESH_HEAD,
    summary_asset=ip['summary_asset'],summary_sha256=ip['summary_sha256'],parts_asset=ip['parts_asset'],parts_sha256=ip['parts_sha256'],report=intrinsic)}
  for name,data in docs.items():
   write('docs/evidence/tx-output8088-driverpinfeed-'+name+'-20261024.json',(json.dumps(data,indent=2)+'\n').encode())
  methods={}
  for path in ['scripts/cloud_tx_output8088_power128return64_composition.py','scripts/compose_tx_output8088_power128return64_native.py']:
   b=(ROOT/path).read_bytes();assert sha(b)==locked[path]
   base=b.decode();new=base.replace('power128return64','driverpinfeed').replace('POWER128RETURN64','DRIVERPINFEED')
   new=new.replace('full_tx_output8088_driverpinfeed_wires','full_tx_output8088_driver_pinfeed_wires')
   new=new.replace('20261023','20261024').replace('140222',str(nr)).replace('99906',str(nc)).replace('240128',str(nr+nc))
   if 'cloud_'in path:
    for old,val in [("bp['run']==39901168356","bp['run']=="+str(FRESH_RUN)),('eab4cea794ef2b27d693b0deb92ca7f6dc2b1361',FRESH_HEAD),("'codex/complete-open-work'","'codex/tx-via3-rail-diagnosis'")]:
     assert new.count(old)==1;new=new.replace(old,val)
   candidate=path.replace('power128return64','driverpinfeed')
   methods[candidate]=derivation(path,base,new);write(candidate,new.encode())
  write('scripts/tx-output8088-driverpinfeed-composition-method.json',(json.dumps(methods,indent=2)+'\n').encode())
  r.update(status='COMPOSING_EVERY_ACTUAL_DEVICE_AND_WIRE',generated_sha256=generated,actual_R=nr,actual_C=nc);save()
  with (STAGE/'native.log').open('w')as log:
   p=subprocess.run([sys.executable,ROOT/'scripts/cloud_tx_output8088_driverpinfeed_composition.py'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_returncode']=p.returncode
  assert all(digest(ROOT/n)==h for n,h in generated.items())
  assert p.returncode==0,'Composition or one of25 original corruption controls rejected'
  report=json.loads((OUT/'result.json').read_text())
  assert report['status']=='PASS_ACTUAL_FULL8088_DRIVERPINFEED_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert report['sources_unchanged']and len(report['controls'])==25 and all(x['rejected']for x in report['controls'])
  assert report['counts']==dict(devices=8088,R=nr,C=nc,external_ports=166,physical_ports=165,metal_reference_planes=13370,body_nets=65,conductors=703,terminals=28620)
  # Rail comparison reads exact unchanged archived and newly composed models;
  # it cannot edit either model or start a transient.
  with (STAGE/'rail-comparison.log').open('w')as log:
   p=subprocess.run([sys.executable,ROOT/'scripts/compare_tx_driverpinfeed_rail_access.py','--composition',OUT,'--output',OUT/'rail-comparison'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['rail_comparison_returncode']=p.returncode
  assert p.returncode==0,'Rail access identity or immutable RC comparison failed'
  rail=json.loads((OUT/'rail-comparison/result.json').read_text())
  assert rail['status']=='COMPLETE_EXACT128_DRIVER_AND2_TAIL_RAIL_RESISTANCE_COMPARISON_NOT_ELECTRICAL_ACCEPTANCE'
  assert rail['sources_unchanged']
  r['rail_comparison']=dict(status=rail['status'],summary=rail['summary'],sha256=digest(OUT/'rail-comparison/result.json'))
  assert all(digest(ROOT/p)==h for p,h in locked.items())and all(digest(ROOT/n)==h for n,h in generated.items())
  r.update(status='PASS_FRESH_FULL_PARENT_COMPOSITION_AND_EXACT_RAIL_COMPARISON_REQUIRES_LOADED_NATIVE_WAVES',generated_sources_unchanged=True)
 except BaseException as e:
  r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  for p in generated:
   if (ROOT/p).exists():
    dst=STAGE/'generated'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dst)
  save();OUT.mkdir(parents=True,exist_ok=True);shutil.move(str(STAGE),str(OUT/'launcher-evidence'))
  rp=OUT/'result.json';report=json.loads(rp.read_text())if rp.exists()else dict(status='FAIL_BEFORE_COMPOSITION',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
  report['launcher']=r
  if r['status']=='FAIL_OR_ERROR':report['status']='FAIL_OR_ERROR'
  report['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=rp}
  rp.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
