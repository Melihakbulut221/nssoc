#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Full native loaded waveform of the actual v51 leaf wire/device model."""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,traceback
from collections import Counter
import build_pcie_local_vco_hybrid_v6 as parser
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
PIN=ROOT/'docs/evidence/cdr-active-levelshift-v51-composition-pass-20261024.json'
MODEL='nssoc_cdr_active_levelshift_v51_wire'
METHOD=ROOT/'scripts/cdr-active-levelshift-v51-extracted-method.json'
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12
CASES=('nominal','hot_low','cold_high','swap_output','bias_off')
def source_check():
 m=json.loads(METHOD.read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 cp=json.loads(PIN.read_text())
 assert cp['report']['status']=='PASS_V51_LEAF18_ALL354_WIRE_ELEMENTS_AND14_COMPOSITION_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
 assert cp['report']['composition']['interface']==['sub', 'ip', 'inn', 'avdd', 'on', 'op', 'avss', 'iref', 'wire_cref']
 return m

def bind(text,contract,output):
 rows=parser.statements(text)
 interface=contract['interface']
 assert interface==['sub', 'ip', 'inn', 'avdd', 'on', 'op', 'avss', 'iref', 'wire_cref']
 assert rows[0]==['.subckt',MODEL,*interface] and rows[-1]==['.ends',MODEL]
 assert contract['counts']==dict(devices=18,R=181,C=173)
 mapping=dict(sub='0',ip='ip',on=output[1],inn='inn',op=output[0],avdd='avdd',avss='0',iref='iref',wire_cref='0')
 def node(n):return mapping.get(n,'xgain.'+n.lower())
 body=rows[1:-1];by={r[0].lower():r for r in body}
 assert len(body)==len(by)==372
 records=contract['device_records']
 assert Counter(d['model']for d in records)==dict(npn13g2=2,sg13_lv_nmos=3,rppd=4,ptap1=9)
 orders={'npn13g2':['C','B','E','S'],'sg13_lv_nmos':['D','G','S','B'],'rppd':['rppd_1','rppd_2','rppd_sub'],'ptap1':['TIE','WELL']}
 devices={};mos={};resistors={};contacts={}
 for d in records:
  row=by[d['instance'].lower()]
  assert [t['terminal']for t in d['terminals']]==orders[d['model']]
  expected=[d['instance'],*[t['node']for t in d['terminals']],d['model'],*[k+'='+v for k,v in d['parameters'].items()]]
  assert row==expected,(d['instance'],row,expected)
  name='xgain.'+d['instance'].lower()
  value=dict(nodes=[node(t['node'])for t in d['terminals']],parameters=d['parameters'],native_id=d['native_id'])
  if d['model']=='npn13g2':value['nx']=int(d['parameters']['nx']);devices[name]=value
  elif d['model']=='sg13_lv_nmos':mos[name]=value
  elif d['model']=='rppd':resistors[name]=value
  else:
   assert parser.number(d['parameters']['r'])>0
   assert value['nodes'][0]!=value['nodes'][1] and value['nodes'][1].startswith('xgain.body_')
   contacts[name]=value
 wires=[r for r in body if r[0][0]in 'RC']
 assert Counter(r[0][0]for r in wires)==dict(R=181,C=173)
 for row in wires:
  assert len(row)==4 and row[1]!=row[2]
  assert parser.number(row[3])>0 if row[0][0]=='R'else parser.number(row[3])>=0
 wire_nodes={n for row in wires for n in row[1:3]}
 assert wire_nodes==set(contract['wire_node_map'].values())
 nodes={node(n)for n in wire_nodes}|{n for group in (devices,mos,resistors,contacts)for d in group.values()for n in d['nodes']}
 tails=[name for name,d in mos.items()if parser.number(d['parameters']['w'])==parser.number('36u')]
 assert len(tails)==2 and all(d['nx']==4 for d in devices.values())
 return dict(devices=devices,mos=mos,resistors=resistors,contacts=contacts,nodes=nodes,ports=[mapping[n]for n in interface],tails=tails)

def controls(text,contract):
 bind(text,contract,('op','on'));bind(text,contract,('on','op'))
 rejected=[]
 for label in ('missing_hbt','wrong_tail_width','swapped_mos_gate_source','short_body','wrong_contact','changed_interface','missing_wire','wire_node_alias'):
  rows=copy.deepcopy(parser.statements(text))
  if label=='changed_interface':rows[0][2],rows[0][3]=rows[0][3],rows[0][2]
  elif label in ('missing_wire','wire_node_alias'):
   i=next(i for i,row in enumerate(rows)if row[0].startswith('R'))
   if label=='missing_wire':del rows[i]
   else:rows[i][1]='unknown_wire_point'
  else:
   model='npn13g2'if label=='missing_hbt'else'ptap1'if label=='wrong_contact'else'sg13_lv_nmos'
   i=next(i for i,row in enumerate(rows)if model in row)
   if label=='missing_hbt':del rows[i]
   elif label=='swapped_mos_gate_source':rows[i][2],rows[i][3]=rows[i][3],rows[i][2]
   elif label=='short_body':rows[i][4]='avss'
   else:
    key='r='if label=='wrong_contact'else'w='
    k=next(k for k,x in enumerate(rows[i])if x.startswith(key));rows[i][k]=key+'999'
  mutant='\n'.join(' '.join(row)for row in rows)+'\n'
  try:bind(mutant,contract,('op','on'))
  except (AssertionError,KeyError,ValueError):rejected.append(label)
  else:raise AssertionError('Accepted broken model binding '+label)
 assert len(rejected)==8
 return dict(rejected=rejected,physical_primitive_count=18,wire_R=181,wire_C=173,native_only=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);args=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 source_check()
 out=ROOT/('cloud-cdr-active-levelshift-v51-extracted-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,
  accepted=False,cdr_accepted=False,full_phy_accepted=False,physical_layout_matches=False,whole_parent_simulated=False,
  qualified_pex=False,closed_loop=False,scope='Actual LVS-bound18primitive leaf+fresh181R173C. All wire/device/body terminal voltages and native HBT/MOS currents preserved for full34.25ns/256bits,10ohm source and150fF per output. Original schematic device/signal/commonmode gates unchanged. Finite PDK contacts retained. Explicit wire_cref tied to testbench ground, not internal body. This loaded leaf test does not establish parent integration, full CDR, RF/substrate PEX, full PHY or mainchip timing.')
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['readback_controls']=readback_controls()
  pinpath=PIN;cp=json.loads(pinpath.read_text())
  previous,proof=reports.restore_report('cdr-active-levelshift-v51-composition',cp['run'],cp['summary_sha256'],cp['parts_sha256'],out/'composed',['levelshift18-wire.spice','composition.json'])
  assert previous==cp['report'] and previous['sources_unchanged'] and len(previous['controls'])==14
  assert previous['status']=='PASS_V51_LEAF18_ALL354_WIRE_ELEMENTS_AND14_COMPOSITION_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  SOURCE=out/'composed/levelshift18-wire.spice'
  contract=json.loads((out/'composed/composition.json').read_text());assert contract==previous['composition']
  assert contract['all_raw_wire_values_and_topology_preserved'] and contract['intrinsic_device_models_emitted_once']
  r.update(composition_source=proof,physical_layout_matches=True,topology_controls=controls(SOURCE.read_text(),contract))
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
  bound=bind(SOURCE.read_text(),contract,output)
  devices,mos,resistors=bound['devices'],bound['mos'],bound['resistors']
  nodes=bound['nodes']|{'avdd','ip','inn','op','on','iref'}
  nodes.discard('0')
  vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in mos]
  corner=args.case if args.case in pump.CORNERS else'nominal';c=pump.CORNERS[corner];scale=c['scale']
  bits=primitive.prbs(0x7f);models=lib/'models/models'
  osdi=[]
  for name in ('psp103.osdi','psp103_nqs.osdi'):
   matches=list(lib.rglob(name));assert len(matches)==1;osdi+=matches
  bias=0 if args.case=='bias_off'else.0005
  deck=['NSSOC actual native v51 extracted loaded leaf',
   f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',
   f'.lib "{models}/cornerMOSlv.lib" {c["mos"]}',f'.include "{SOURCE}"',f'.temp {c["temperature"]}',
   '.options reltol=1e-4 abstol=1e-12 klu',
   f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})',f'IREF avdd iref PWL(0 0 500p {bias:.12g})',
   'VIP ip0 0 '+parent.data(bits,1.48*scale,.03*scale),
   'VIN inn0 0 '+parent.data([1-b for b in bits],1.48*scale,.03*scale),
   'RIP ip0 ip 10','RIN inn0 inn 10',
   'XGAIN '+' '.join(bound['ports'])+' '+MODEL,
   'COP op 0 150f','CON on 0 150f','.control',
   f'pre_osdi {lib/"models/r3_cmc.osdi"}',*[f'pre_osdi {x}'for x in osdi],
   'set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
  for name in devices:
   q='q.'+name+'.qnpn13g2';deck += [f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END']
  deck += ['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}',
   'set filetype=binary','write wave.raw '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
  native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
  protected={str(f):sha(f)for f in [Path(__file__),SOURCE,METHOD,PIN,out/'composed/composition.json',ROOT/'scripts/cloud_cdr_sampler_parallel_drive.py',ROOT/'scripts/cloud_tx_stream.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
  r.update(devices=devices,mos_devices=mos,resistors=resistors,contacts=bound['contacts'],physical_contract=contract,vectors=vectors,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected,corner=corner)
  save()
  env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
  with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
  text=(native/'native.log').read_text();options,notes,_=backend_readback(text,'klu')
  r.update(returncode=proc.returncode,native_options=options,diagnostics=notes);save();assert proc.returncode==0 and not notes
  flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
  assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]
  assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
  r['native_flags_verified']=len(flags)
  r['full_native_wire_and_body_nodes_saved']=len(nodes)
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
  tail=sum(w['@n.'+name+'.nsg13_lv_nmos[ids]']for name in bound['tails'])
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
  r['status']=('PASS_NATIVE_EXTRACTED_LEVELSHIFT_FAULT_DETECTION_NOT_ACCEPTANCE'if fault else'PASS_NATIVE_EXTRACTED_LEVELSHIFT_LEAF_REQUIRES_PARENT_AND_FULL_CDR')if passed else'REJECTED_NATIVE_EXTRACTED_LEVELSHIFT_LEAF'
  assert passed,'Active level-shifter native component screen failed; preserve full evidence'
 except BaseException as error:
  if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
  r.update(error=repr(error),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
  save();print(r['status'],flush=True)
if __name__=='__main__':main()
