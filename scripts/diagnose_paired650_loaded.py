"""Read exact failed paired650 waveform; no new stimulus or acceptance change."""
import os,json,subprocess,hashlib,zipfile,shutil,importlib.util
from pathlib import Path
import numpy as np
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
out=Path('out');out.mkdir();work=Path('/mnt/paired650-wave-audit');work.mkdir(exist_ok=True)
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
r=api('actions/runs/43626358999');assert r['status']=='completed' and r['conclusion']=='failure' and r['head_sha']=='73b781d77b169a4c270bb635197540d3c8f96a9c'
def acquire(aid,digest):
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==r['id'] and m['workflow_run']['head_sha']==r['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
 p=work/(str(aid)+'.zip')
 with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert sha(p)==digest
 return zipfile.ZipFile(p)
safe=acquire(14129935844,'1120b7b95099d7bd4c966b4a5f2bc39b663f18d1ec9ddcc11a3fa29a87ab5f1d')
report_raw=safe.read('loaded-n1-nominal_late.json');prior=json.loads(report_raw)
assert prior['status']=='REJECTED_WHOLE_MIM_ACTUAL650_LOADED'and prior['sources_unchanged']and prior['diagnostics']==[]
z=acquire(14129601477,'0c2aad0a0e0c78ec3dab1be1f9b4e96a57ff9ab41da2df54bba053818c01eee9')
names=[n for n in z.namelist()if n.endswith('/loaded-n1-nominal_late/wave.raw')];assert len(names)==1
raw=work/'wave.raw'
with z.open(names[0])as f,raw.open('xb')as g:shutil.copyfileobj(f,g,1024*1024)
assert sha(raw)==prior['raw_capture']['raw_sha256']=='eb082c14050301a3e7daff0d0f8e284e4d9a0b2b69683a68b078680c3a25e55a'
reader=Path('scripts/cdr_mos650_full650_loaded.py')
expected=[v for k,v in prior['protected_inputs'].items()if k.endswith('/scripts/cdr_mos650_full650_loaded.py')];assert len(expected)==1 and sha(reader)==expected[0]
spec=importlib.util.spec_from_file_location('frozen_loaded',reader);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
t,d,capture=mod.read_streamed_wave(raw,prior['vectors'],mod.STOP,mod.STEP)
bound=prior['binding'];bits=prior['source_bits'];UI=mod.UI;START=mod.START
result={'source_run':r['id'],'source_head':r['head_sha'],'safe_artifact':14129935844,'native_artifact':14129601477,'source_report_sha256':hashlib.sha256(report_raw).hexdigest(),'raw_sha256':sha(raw),'reader_sha256':sha(reader),'rows':capture['header_rows'],'columns':capture['columns'],'accepted':False,'scope':'Diagnostic phase/transition/lag bins on the complete original failed waveform. Original acceptance remains failed; no timing-window or expected-bit replacement.','stages':{},'input_observations':{}}
def v(n):return d['v('+bound['aliases'].get(n,n)+')']
phases=[0,.1,.2,.3,.4,.5,.6,.75,.9]
for tag in 'abcdxy':
 if tag in 'abcd':
  positive='xpd.'+tag+'qp';negative='xpd.'+tag+'qn';expect=prior['expected_samples'][tag];reference=prior['sampler_checks'][tag];official=[.3,.6,.9]
 else:
  positive=tag+'p';negative=tag+'n';expect=prior['expected_comparisons'][tag];reference=prior['comparisons'][tag];official=[.6,.75,.9]
 delta=v(positive)-v(negative);edges=np.array([START+(i+(0 if tag=='b'else .5))*UI for i in range(1,256)])
 expected=np.array(expect);sign=2*expected-1
 def sample(phase):return np.interp(edges+phase*UI,t,delta)
 observed=np.concatenate([sample(p)*sign for p in official])
 assert int(np.sum(observed<=0))==reference['wrong_sign_samples']and int(np.sum(observed<.1))==reference['below_100mv_samples']
 assert abs(float(observed.min())-reference['minimum_signed_margin_v'])<1e-12
 rows={}
 for phase in phases:
  raw_values=sample(phase);signed=raw_values*sign
  byexpected={}
  for bit in [0,1]:
   keep=expected==bit
   if keep.any():byexpected[str(bit)]={'count':int(keep.sum()),'mean_differential_v':float(raw_values[keep].mean()),'minimum_signed_v':float(signed[keep].min()),'wrong_sign':int(np.sum(signed[keep]<=0)),'below_100mv':int(np.sum(signed[keep]<.1))}
  rows[str(phase)]={'minimum_signed_v':float(signed.min()),'wrong_sign':int(np.sum(signed<=0)),'below_100mv':int(np.sum(signed<.1)),'by_expected_bit':byexpected}
 result['stages'][tag]={'original_acceptance_reproduced':True,'original_checks':{k:x for k,x in reference.items()if k!='clock_to_valid_by_bit_s'},'diagnostic_phase_bins':rows}
# Direct internal source/clock differentials; informational, never substituted for expected outputs.
for label,p,n in [('data_a','xpd.adp','xpd.adn'),('data_c','xpd.cdp','xpd.cdn'),('select0','xpd.s0p','xpd.s0n'),('select1','xpd.s1p','xpd.s1n')]:
 delta=v(p)-v(n);edges=np.array([START+(i+.5)*UI for i in range(1,256)])
 result['input_observations'][label]={str(phase):{'min':float(np.interp(edges+phase*UI,t,delta).min()),'max':float(np.interp(edges+phase*UI,t,delta).max()),'mean':float(np.interp(edges+phase*UI,t,delta).mean())}for phase in phases}
result['hbt_failures']={n:x for n,x in prior['device_checks'].items()if x['minimum_active_vce_v']<.4 or x['maximum_alltime_abs_vce_v']>1.6 or x['maximum_alltime_abs_vbe_v']>1 or x['maximum_alltime_abs_ic_per_emitter_a']>=.003}
result['status']='DIAGNOSED_ORIGINAL_FAILED_WAVEFORM_NOT_ACCEPTED'

# Diagnostic transfer/alignment: do not replace the frozen acceptance vectors.
# Every relation below is reported, including uncovered input combinations.
edges=np.array([START+(i+.5)*UI for i in range(1,256)])
pairs={k:('xpd.'+k+'qp','xpd.'+k+'qn')for k in 'abcd'}
pairs.update(ad=('xpd.adp','xpd.adn'),cd=('xpd.cdp','xpd.cdn'),s0=('xpd.s0p','xpd.s0n'),s1=('xpd.s1p','xpd.s1n'),x=('xp','xn'),y=('yp','yn'))
def sampled(tag,phase):
 p,n=pairs[tag];return np.interp(edges+phase*UI,t,v(p)-v(n))
def stats(x):
 return {'n':int(len(x)),'minimum_v':float(x.min()),'maximum_v':float(x.max()),'mean_v':float(x.mean()),'weak_abs_100mv':int(np.sum(np.abs(x)<.1))}
result['transfer_bins']={}
for phase in [.3,.6,.75,.9]:
 values={tag:sampled(tag,phase)for tag in pairs};row={'signals':{},'comparators':{},'sampled_device_headroom':{}}
 for tag in ['ad','cd','s0','s1']:
  raw=values[tag];p,n=pairs[tag];cm=np.interp(edges+phase*UI,t,(v(p)+v(n))/2)
  rr={'differential':stats(raw),'commonmode':stats(cm),'relations':{}}
  for origin in ['a','b','c','d']:
   # Integer lag is diagnostic only, never an allowed expected-data correction.
   for lag in [-1,0,1]:
    ii=np.arange(255);jj=ii+lag;valid=(jj>=0)&(jj<255);aa=raw[ii[valid]];bb=values[origin][jj[valid]]
    strong=(np.abs(aa)>=.1)&(np.abs(bb)>=.1)
    rr['relations'][f'{origin}:lag{lag}']={'pairs':int(len(aa)),'same_sign':int(np.sum((aa>0)==(bb>0))),'opposite_sign':int(np.sum((aa>0)!=(bb>0))),'strong_pairs':int(strong.sum()),'strong_same_sign':int(np.sum(((aa>0)==(bb>0))&strong)),'rms_difference_v':float(np.sqrt(np.mean((aa-bb)**2)))}
  row['signals'][tag]=rr
 for output in ['x','y']:
  rr={}
  for data in ['ad','cd']:
   for select in ['s0','s1']:
    da=values[data];se=values[select];yy=values[output];bins={}
    for db in [0,1]:
     for sb in [0,1]:
      use=((da>0)==bool(db))&((se>0)==bool(sb))
      cell={'n':int(use.sum())}
      if use.any():
       strong=use&(np.abs(da)>=.1)&(np.abs(se)>=.1)
       cell.update(output=stats(yy[use]),data=stats(da[use]),select=stats(se[use]),strong_input_pairs=int(strong.sum()))
       if strong.any():cell['output_for_strong_inputs']=stats(yy[strong])
      bins[f'{db}{sb}']=cell
    rr[data+':'+select]=bins
  row['comparators'][output]=rr
 # Real native device headroom at the same sample instants. Report all HBTs;
 # cannot infer topology from a coincidental net alias or waive the all-time gate.
 for name,device in bound['groups']['npn13g2'].items():
  c,b,e,_=device['nodes'];vce=np.interp(edges+phase*UI,t,v(c)-v(e));vbe=np.interp(edges+phase*UI,t,v(b)-v(e))
  row['sampled_device_headroom'][name]={'minimum_vce_v':float(vce.min()),'maximum_vce_v':float(vce.max()),'maximum_abs_vbe_v':float(np.abs(vbe).max()),'below_400mv_samples':int(np.sum(vce<.4))}
 result['transfer_bins'][str(phase)]=row
result['transfer_scope']='Relations and all candidate comparator input pair bins, without inferred topology, input polarity swaps, retiming, expected-vector replacement or acceptance waiver. Missing combinations stay explicitly n=0.'

(out/'wave-diagnosis.json').write_text(json.dumps(result,indent=2))
