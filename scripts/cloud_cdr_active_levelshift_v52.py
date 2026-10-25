#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native pre-layout level-shifter screening; never whole-CDR/PHY acceptance."""
import argparse,hashlib,json,os,re,shutil,subprocess,traceback
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_cdr_xor as primitive
import cloud_pll_pump_current as pump
import cloud_cdr_sampler_parallel_drive as parent
import cloud_tx_stream as stream
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/analog/pcie/cdr_active_levelshift_v52.spice'
METHOD=ROOT/'scripts/cdr-active-levelshift-v52-method.json'
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12
CASES=('nominal','hot_low','cold_high','swap_output','bias_off')
def source_check():
 m=json.loads(METHOD.read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 return m
def bind(text,output):
 rows=[l.lower().split()for l in text.splitlines()if l.strip()and not l.lstrip().startswith('*')]
 assert rows[0]=='.subckt nssoc_cdr_active_levelshift_v52 ip inn op on avdd avss sub iref'.split()
 assert rows[-1]=='.ends nssoc_cdr_active_levelshift_v52'.split()
 mapping=dict(zip(rows[0][2:],['ip','inn',*output,'avdd','0','0','iref'],strict=True))
 def node(n):return mapping.get(n,'xgain.'+n)
 devices={};mos={};resistors={}
 expected={
 'xp':['on','ip','tail','sub','npn13g2','nx=4'],
 'xn':['op','inn','tail','sub','npn13g2','nx=4'],
 'xt0':['tail','iref','avss','sub','sg13_lv_nmos','w=36u','l=.3u','ng=1'],
 'xt1':['tail','iref','avss','sub','sg13_lv_nmos','w=36u','l=.3u','ng=1'],
 'xref':['iref','iref','avss','sub','sg13_lv_nmos','w=5.4u','l=.3u','ng=1'],
 'xup':['avdd','op','sub','rppd','w=8u','l=1.8u','b=0','sw_et=1'],
 'xun':['avdd','on','sub','rppd','w=8u','l=1.8u','b=0','sw_et=1'],
 'xdp':['op','avss','sub','rppd','w=4u','l=8.0u','b=0','sw_et=1'],
 'xdn':['on','avss','sub','rppd','w=4u','l=8.0u','b=0','sw_et=1']}
 assert len(rows[1:-1])==9 and len({r[0]for r in rows[1:-1]})==9
 assert {r[0]:r[1:]for r in rows[1:-1]}==expected
 for f in rows[1:-1]:
  name='xgain.'+f[0]
  if f[5]=='npn13g2':devices[name]=dict(nodes=[node(n)for n in f[1:5]],nx=4)
  elif f[5]=='sg13_lv_nmos':mos[name]=dict(nodes=[node(n)for n in f[1:5]],parameters=dict(v.split('=')for v in f[6:]))
  else:
   assert f[4]=='rppd'
   resistors[name]=dict(nodes=[node(n)for n in f[1:4]],parameters=dict(v.split('=')for v in f[5:]))
 assert (len(devices),len(mos),len(resistors))==(2,3,4)
 return devices,mos,resistors
def controls():
 text=SOURCE.read_text();bind(text,('op','on'));bind(text,('on','op'))
 rejected=[]
 for label,old,new in [('wrong-hbt','Nx=4','Nx=11'),('wrong-tail','w=36u','w=72u'),
  ('changed-load','l=1.8u','l=1.4u'),('wrong-polarity','XP on ip tail','XP op ip tail'),
  ('no-shunt','XDP op avss sub','XDP op op sub'),('behavioral-source','XP on ip tail sub npn13G2 Nx=4','BGAIN op on V=1')]:
  bad=text.replace(old,new,1);assert bad!=text
  try:bind(bad,('op','on'))
  except (AssertionError,IndexError):rejected.append(label)
  else:raise AssertionError('Accepted bad native topology '+label)
 return dict(rejected=rejected,physical_primitive_count=9,native_only=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);args=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 source_check()
 out=ROOT/('cloud-cdr-active-levelshift-v52-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,
  accepted=False,cdr_accepted=False,full_phy_accepted=False,physical_layout_matches=False,whole_parent_simulated=False,
  scope='New native active level-shifter component only. Actual parent remains unchanged/rejected. Two HBT, three LVNMOS, four native resistors. 256bits/full34.25ns,60mV differential input at1.48V common mode,10ohm source,150fF on each output. Original HBT/MOS bounds reused; component target100mV by37.5ps is not full-CDR acceptance. Needs real parent loading, no separate new ideal bias in final integration, GDS/DRC/LVS/freshRC/full original CDR gates/PVT/loop.')
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['topology_controls']=controls();r['readback_controls']=readback_controls()
  fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',primitive.SUMMARY,out/'models-pin.json')
  pin=json.loads((out/'models-pin.json').read_text());wanted=[n for n in pin['outputs']if n.startswith('source/model-sources/')]+['source-pin.json','source/runtime/patched-ngspice']
  old,proof=reports.restore_report('pll-pump-current',39029337682,primitive.SUMMARY,primitive.PARTS,out/'source',wanted)
  assert old==pin;r['models_source']=proof
  original=json.loads((out/'source/source-pin.json').read_text());assert sha(out/'source/source-pin.json')==pump.SUMMARY
  lib=out/'models';shutil.copytree(out/'source/source/model-sources',lib)
  assert all(sha(lib/p)==h for p,h in original['preparation']['model_sources'].items())
  engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755)
  assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
  output=('on','op')if args.case=='swap_output'else('op','on')
  devices,mos,resistors=bind(SOURCE.read_text(),output)
  nodes={n for x in [*devices.values(),*mos.values(),*resistors.values()]for n in x['nodes']}|{'avdd','ip','inn','op','on','iref'}
  nodes.discard('0')
  vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in mos]
  corner=args.case if args.case in pump.CORNERS else'nominal';c=pump.CORNERS[corner];scale=c['scale']
  bits=primitive.prbs(0x7f);models=lib/'models/models'
  osdi=[]
  for name in ('psp103.osdi','psp103_nqs.osdi'):
   matches=list(lib.rglob(name));assert len(matches)==1;osdi+=matches
  bias=0 if args.case=='bias_off'else.0005
  deck=['NSSOC native active level-shifter component screen',
   f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',
   f'.lib "{models}/cornerMOSlv.lib" {c["mos"]}',f'.include "{SOURCE}"',f'.temp {c["temperature"]}',
   '.options reltol=1e-4 abstol=1e-12 klu',
   f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})',f'IREF avdd iref PWL(0 0 500p {bias:.12g})',
   'VIP ip0 0 '+parent.data(bits,1.48*scale,.03*scale),
   'VIN inn0 0 '+parent.data([1-b for b in bits],1.48*scale,.03*scale),
   'RIP ip0 ip 10','RIN inn0 inn 10',
   f'XGAIN ip inn {output[0]} {output[1]} avdd 0 0 iref nssoc_cdr_active_levelshift_v52',
   'COP op 0 150f','CON on 0 150f','.control',
   f'pre_osdi {lib/"models/r3_cmc.osdi"}',*[f'pre_osdi {x}'for x in osdi],
   'set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
  for name in devices:
   q='q.'+name+'.qnpn13g2';deck += [f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END']
  deck += ['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}',
   'set filetype=binary','write wave.raw '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
  native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
  protected={str(f):sha(f)for f in [Path(__file__),SOURCE,METHOD,ROOT/'scripts/cloud_cdr_sampler_parallel_drive.py',ROOT/'scripts/cloud_tx_stream.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
  r.update(devices=devices,mos_devices=mos,resistors=resistors,vectors=vectors,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected,corner=corner)
  save()
  env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
  with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
  text=(native/'native.log').read_text();options,notes,_=backend_readback(text,'klu')
  r.update(returncode=proc.returncode,native_options=options,diagnostics=notes);save();assert proc.returncode==0 and not notes
  flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
  assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]
  assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
  r['native_flags_verified']=len(flags)
  op=np.loadtxt(native/'op.dat',skiprows=1)
  assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9
  r['zero_source_op_maximum']=float(abs(op).max())
  t,w,capture=stream.read_streamed_wave(native/'wave.raw',vectors,STOP,STEP);r['raw_capture']=capture
  active=t>=START
  def v(n):return np.zeros(len(t))if n=='0'else w['v('+n+')']
  checks={}
  for name,dev in devices.items():
   vc,vb,ve,_=map(v,dev['nodes']);ic=w['@q.'+name+'.qnpn13g2[ic]']
   checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),
    maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
  safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1 and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
  mos_checks={}
  for name,dev in mos.items():
   vd,vg,vs,vb=map(v,dev['nodes']);current=w['@n.'+name+'.nsg13_lv_nmos[ids]']
   peaks={k:float(abs(x).max())for k,x in [('vds',vd-vs),('vgs',vg-vs),('vgd',vg-vd),('vdb',vd-vb),('vsb',vs-vb)]}
   mos_checks[name]=dict(peaks_v=peaks,minimum_active_vds_v=float((vd-vs)[active].min()),minimum_active_drain_current_a=float(current[active].min()),passed=max(peaks.values())<=1.32 and float((vd-vs)[active].min())>=0)
  tail=sum(w['@n.xgain.xt'+str(i)+'.nsg13_lv_nmos[ids]']for i in range(2))
  safe=safe and all(x['passed']for x in mos_checks.values())and float(tail[active].min())>=.0005
  delta=v('op')-v('on');cm=(v('op')+v('on'))/2;signed=[];delays=[]
  for i,bit in enumerate(bits):
   edge=START+i*UI;sign=2*bit-1
   for phase in (.3,.6,.9):signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
   ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
   delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
  signal=min(signed)>=.1 and max(delays)<=.3*UI
  commonmode=bool(cm[active].min()>=1.8 and cm[active].max()<=2.15)
  fault=args.case in ('swap_output','bias_off')
  r.update(device_checks=checks,mos_checks=mos_checks,devices_passed=safe,minimum_active_tail_current_a=float(tail[active].min()),
   component_signal_passed=signal,component_commonmode_target_passed=commonmode,
   component_commonmode_target_v=[1.8,2.15],output_commonmode_v=[float(cm[active].min()),float(cm[active].max())],
   output_differential_v=[float(delta[active].min()),float(delta[active].max())],samples=len(signed),
   minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below100mv_samples=sum(x<.1 for x in signed),
   maximum_input_to_valid_s=max(delays),input_to_valid_by_bit_s=delays,actual_fault_detected=fault and not signal)
  assert len(signed)==768 and all(sha(Path(p))==h for p,h in protected.items());source_check();r['sources_unchanged']=True
  passed=(not signal)if fault else safe and signal and commonmode
  r['status']=('PASS_NATIVE_ACTIVE_LEVELSHIFT_FAULT_DETECTION_NOT_ACCEPTANCE'if fault else'PASS_NATIVE_ACTIVE_LEVELSHIFT_COMPONENT_ONLY_REQUIRES_PARENT_PHYSICAL_AND_FULL_CDR')if passed else'REJECTED_NATIVE_ACTIVE_LEVELSHIFT_COMPONENT'
  assert passed,'Active level-shifter native component screen failed; preserve full evidence'
 except BaseException as error:
  if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
  r.update(error=repr(error),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
  save();print(r['status'],flush=True)
if __name__=='__main__':main()
