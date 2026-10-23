#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only diagnosis of the complete rejected actual8088 return64 TX capture."""
import argparse,copy,hashlib,json,os,shutil,subprocess,tarfile,traceback
from pathlib import Path
import numpy as np
import cloud_tx_p4_drive3_builder as tree
from cloud_tx_stream import read_streamed_wave
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-return64-diagnosis'
REPO='repos/Melihakbulut221/nssoc/'
SPEC=dict(run=39957261794,head='e2f80d21ad3f6c0d6bdac34b04e694fbbe3580d5',
 summary_asset=669316431,summary_sha256='ba65085e437628000254c0aad58188d04e1d225a887a584c3840cd7669c1e633',
 parts_asset=669316559,parts_sha256='2edc719c9b21bfb0ac8d46b580e9dd00891bf046f833c0fbabb4ff1e5109970c',
 raw_sha256='71f1ecd5d039747dd357760d5dda67207be6c707a640bb1ccf542b92d22392ae')
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def small(a,h):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
 assert digest(b)==h
 return b
def source_gate(run,d):
 assert run['id']==SPEC['run'] and run['head_sha']==SPEC['head'] and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 assert d['source_head']==SPEC['head'] and d['run_id']==SPEC['run'] and d['case']=='none'
 assert d['status']=='REJECTED_ACTUAL8088_POWER128RETURN64_ORIGINAL_LOADED_GATES'
 assert d['native_exit_code']==0 and d['full_capture'] is True and d['native_process_saved'] is False
 assert d['electrical_screen_passed'] is False and d['sources_unchanged'] is True and d['single_entrypoint'] is True
 assert d['diagnostics']==[]
 assert d['outputs']['work/wave.raw']==SPEC['raw_sha256']
 assert d['review']['all_engineering_gates_passed'] is False
def aggregate(rows,review):
 assert len(rows)==62 and len({r['input'] for r in rows})==62
 for stage,old in review['interfaces'].items():
  selected=[r for r in rows if r['stage']==stage]
  for key in ('samples','wrong_sign_samples','below_150mv_samples'):
   assert sum(r[key] for r in selected)==old[key],(stage,key)
  assert min(r['minimum_margin_v'] for r in selected)==old['minimum_margin_v']
  assert [min(r['common_mode_range_v'][0] for r in selected),max(r['common_mode_range_v'][1] for r in selected)]==old['common_mode_range_v']
def controls():
 d=dict(source_head=SPEC['head'],run_id=SPEC['run'],case='none',
 status='REJECTED_ACTUAL8088_POWER128RETURN64_ORIGINAL_LOADED_GATES',native_exit_code=0,
 full_capture=True,native_process_saved=False,electrical_screen_passed=False,sources_unchanged=True,
 single_entrypoint=True,diagnostics=[],outputs={'work/wave.raw':SPEC['raw_sha256']},
 review={'all_engineering_gates_passed':False})
 run=dict(id=SPEC['run'],head_sha=SPEC['head'],run_attempt=1,status='completed',conclusion='failure')
 source_gate(run,d);faults=[]
 for owner,key,value in [('run','id',1),('run','head_sha','0'*40),('run','run_attempt',2),
 ('run','status','in_progress'),('run','conclusion','success'),('report','case','swap_leaf_select'),
 ('report','native_exit_code',1),('report','full_capture',False),('report','native_process_saved',True),
 ('report','sources_unchanged',False),('report','single_entrypoint',False),
 ('report','diagnostics',['solver warning']),('report','electrical_screen_passed',True)]:
  rr,dd=copy.deepcopy((run,d));(rr if owner=='run' else dd)[key]=value
  try:source_gate(rr,dd)
  except (AssertionError,KeyError):faults.append(owner+'.'+key)
  else:raise AssertionError('Accepted '+key)
 return dict(source_faults_rejected=faults,synthetic_only=True)
def restore(result):
 raw=small(SPEC['summary_asset'],SPEC['summary_sha256'])
 manifest_raw=small(SPEC['parts_asset'],SPEC['parts_sha256'])
 d=json.loads(raw);m=json.loads(manifest_raw);source_gate(api('actions/runs/'+str(SPEC['run'])),d)
 assert m['format']=='ordered-tar-gzip-parts-v1'
 release=api('releases/tags/cloud-results-39957261794-1-tx-output8088-power128return64-native-cross-none')
 assets={a['name']:a for a in release['assets']};packed=OUT/'source.tar.gz'
 total=hashlib.sha256();length=0
 with packed.open('xb')as f:
  for i,row in enumerate(m['parts']):
   assert row['index']==i and row['name']==m['stem']+'.tar.gz.part'+str(i).zfill(4)
   a=assets[row['name']];assert a['size']==row['bytes'] and a['digest']=='sha256:'+row['sha256']
   part_hash=hashlib.sha256();size=0
   p=subprocess.Popen(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'],stdout=subprocess.PIPE)
   while True:
    b=p.stdout.read(1024*1024)
    if not b:break
    f.write(b);part_hash.update(b);total.update(b);size+=len(b);length+=len(b)
   assert p.wait()==0 and size==row['bytes'] and part_hash.hexdigest()==row['sha256']
   print('Verified archive part',i,flush=True)
 assert total.hexdigest()==m['sha256'] and length==m['bytes']
 selected={'work/wave.raw','work/contract.json','work/op.dat','work/bench.cir','work/native.log','work/boots.log'}
 actual={};seen=set();embedded=None
 with tarfile.open(packed,'r|gz')as archive:
  for member in archive:
   path=Path(member.name)
   assert not path.is_absolute() and '..'not in path.parts and path.parts[0]==m['source_directory']
   assert member.name not in seen;seen.add(member.name)
   assert member.isdir() or member.isfile()
   if member.isdir():continue
   name=str(Path(*path.parts[1:]));stream=archive.extractfile(member)
   if name=='result.json':
    b=stream.read();assert digest(b)==SPEC['summary_sha256'];embedded=json.loads(b)
   elif name in selected:
    dest=OUT/'capture'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb')as f:shutil.copyfileobj(stream,f)
    actual[name]=sha(dest)
   else:actual[name]=hashlib.file_digest(stream,'sha256').hexdigest()
 assert embedded==d and actual==d['outputs'] and selected<=set(actual)
 result['archive_verified']=dict(bytes=length,sha256=total.hexdigest(),all_output_hashes=actual)
 (OUT/'source-summary.json').write_bytes(raw);(OUT/'source-parts.json').write_bytes(manifest_raw)
 packed.unlink()
 return d
def diagnose(report,result):
 native=OUT/'capture/work';c=json.loads((native/'contract.json').read_text())
 assert c['streams']==32 and len(c['bits'])==256 and len(c['hbt'])==604 and len(c['mos'])==5376
 assert digest(bytes(c['bits']))==c['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
 review=tree.review(native,c)
 assert review==report['review'],'Original complete electrical review changed'
 result['original_review_exactly_reproduced']=True
 t,values,transport=read_streamed_wave(native/'wave.raw',c['vectors'],tree.STOP,c['condition']['step_ps']*1e-12)
 assert transport['raw_sha256']==SPEC['raw_sha256'] and transport['header_rows']==77706 and transport['columns']==14182
 result['capture_transport']=transport
 zero=np.zeros_like(t)
 def v(n):return zero if n=='0'else values['v('+n+')']
 rows=[];maps=c['interface_probes']
 for key in sorted(k[:-1] for k in maps if k.endswith('p')):
  stride=32 if key.startswith('d')else 2 if key in ('a','b')else int(key.split('_')[0][1:])
  offset=int(key[1:])if key.startswith('d')else ('a','b').index(key)if key in ('a','b')else int(key.split('_')[1])
  group='cmos'if stride==32 else 'final'if stride==2 else 'level_'+str(stride)
  samples=[]
  for i in range(offset,256,stride):
   for phase in (.3,.5,.7):
    at=tree.START+(i+phase)*tree.UI
    for pn in maps[key+'p']:
     for nn in maps[key+'n']:
      pv,nv=(float(np.interp(at,t,v(n)))for n in (pn,nn))
      samples.append(dict(bit_index=i,phase=phase,time_s=at,pnode=pn,nnode=nn,
       margin_v=(pv-nv)*(2*c['bits'][i]-1),common_mode_v=(pv+nv)/2))
  rows.append(dict(input=key,stage=group,samples=len(samples),
   minimum_margin_v=min(x['margin_v']for x in samples),
   wrong_sign_samples=sum(x['margin_v']<=0 for x in samples),
   below_150mv_samples=sum(x['margin_v']<.15 for x in samples),
   common_mode_range_v=[min(x['common_mode_v']for x in samples),max(x['common_mode_v']for x in samples)],
   common_mode_outside_original_1p8_2p05_samples=sum(not 1.8<=x['common_mode_v']<=2.05 for x in samples),
   worst_sample=min(samples,key=lambda x:x['margin_v']),
   failed_samples=[x for x in samples if x['margin_v']<.15 or not 1.8<=x['common_mode_v']<=2.05],
   endpoints={suffix:[dict(node=n,hbts=[name for name,h in c['hbt'].items()if h['terminals'][1]==n])for n in maps[key+suffix]]for suffix in ('p','n')}))
 aggregate(rows,review);result['all62_interface_pairs']=rows
 # Corrupt each independent aggregate decision and require rejection.
 rejected=[]
 for key in ('samples','wrong_sign_samples','below_150mv_samples','minimum_margin_v','common_mode_range_v'):
  bad=copy.deepcopy(rows)
  bad[0][key]=[9.,10.]if key=='common_mode_range_v'else (-99. if key=='minimum_margin_v'else bad[0][key]+1)
  try:aggregate(bad,review)
  except AssertionError:rejected.append(key)
  else:raise AssertionError('Accepted changed aggregate '+key)
 result['actual_aggregate_faults_rejected']=rejected
 active=t>=tree.START;failed={}
 for name in review['failed_hbts']:
  device=c['hbt'][name];vc,vb,ve,_=(v(n)for n in device['terminals'])
  ce=vc-ve;be=vb-ve;current=values['@q.'+name+'.qnpn13g2[ic]']/device['nx']
  masks={'min_post_vce':active&(ce<.4),'max_whole_vce':abs(ce)>1.6,'max_whole_vbe':abs(be)>1.,'max_whole_current':abs(current)>.003}
  detail={}
  for kind,mask in masks.items():
   ids=np.flatnonzero(mask)
   if not len(ids):continue
   array=ce if 'vce'in kind else abs(be)if 'vbe'in kind else abs(current)
   peak=int(ids[np.argmin(array[ids])if kind=='min_post_vce'else np.argmax(abs(array[ids]))])
   detail[kind]=dict(violating_native_rows=len(ids),first_time_s=float(t[ids[0]]),last_time_s=float(t[ids[-1]]),
    post_start_rows=int(np.count_nonzero(mask&active)),peak=dict(time_s=float(t[peak]),vc=float(vc[peak]),
    vb=float(vb[peak]),ve=float(ve[peak]),vce=float(ce[peak]),vbe=float(be[peak]),ic_per_emitter_a=float(current[peak])))
  assert detail
  failed[name]=dict(device=device,original_measurement=review['failed_hbts'][name],violation_times=detail,
   direct_interface_bases=[r['input'] for r in rows if any(name in e['hbts']for leg in r['endpoints'].values()for e in leg)])
 assert len(failed)==85 and len(review['failed_mos'])==0
 result['failed_hbts_at_native_times']=failed
 result['scope_limit']='Direct original probe/terminal identity only; does not infer resistor-connected endpoints or a causal circuit repair. No new simulation, phase fit, sample shift, gate relaxation or PHY acceptance.'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SPEC,accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-return64-diagnosis-methods.json').read_text())
  for p,h in methods.items():assert sha(ROOT/p)==h,('Changed method',p)
  result['methods']=methods;result['controls']=controls()
  report=restore(result);save();diagnose(report,result)
  for p,h in methods.items():assert sha(ROOT/p)==h
  result['status']='COMPLETE_REJECTED_FULL_TX_DIAGNOSIS_NOT_REPAIR_OR_PHY_ACCEPTANCE'
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  # Keep the exact immutable source release. Publish small diagnosis, never a
  # second multi-GB raw copy or temporary partial archive on this read-only job.
  for p in (OUT/'source.tar.gz',OUT/'capture/work/wave.raw'):
   if p.exists():p.unlink()
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true');args=parser.parse_args()
 if args.controls:print(json.dumps(controls()))
 else:main()
