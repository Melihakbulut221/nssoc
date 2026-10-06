# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Three finite clamped570 diagnostics; no polarity/acquisition acceptance."""
import argparse, concurrent.futures, copy, gzip, hashlib, importlib.util, json
import os, resource, shutil, stat, subprocess, sys, time, types, zlib
from pathlib import Path
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent
S=R/'hw/soc/out/pcie-tail115-connected570-source-20261006'
P16=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006'
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(P16))
import characterize_sixteenthstep01 as previous
core=previous.core;n=previous.n;stream=previous.stream;require=previous.require;life=previous.life
HYBRID=previous.HYBRID;PINS=previous.PINS;SOURCE=S/'loop-negative01.spice'
NATIVE_ROOT=B/'native01'
POINT_LIMIT=1280*1024**2;AGGREGATE_LIMIT=4*1024**3
FLOOR=512*1024**2;SSD_FLOOR=1024**3;RECEIPT_RESERVE=2*1024**2
MAX_ROWS=120000;HEADER_CAP=4*1024**2;FAILED_TAIL_RESERVE=1024**2
POINTS=(0.5,0.6,0.7)
OBS=[x.replace('v(xchain.','v(xloop.xchain.') for x in previous.OBS]
OBS+=['v(vctrl)','i(vctrl)','v(up)','v(down)','v(reset)','v(reference)']
assert len(OBS)==len(set(OBS))

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def config(vctrl=0.6,fault=''):
 require(vctrl in POINTS and fault=='','Only three named nominal tuning diagnostics')
 freeze=json.loads((S/'source-freeze01.json').read_text())
 require(pin(S/'source-freeze01.json')==dict(bytes=35763,sha256='961db3c0f582da14ddfa73cd3da648e3ab10b3424e362a7df9dda55c765f400a'),'Frozen570 source contract')
 for path,value in freeze['inputs'].items():require(pin(path)==value,'570 source input drift '+path)
 peer=json.loads((S/'source-contract-peer-root01.json').read_text())
 require(peer['status']=='PASS_SOURCE_ONLY_570_COMPOSITION_AND_TUNING_CONTRACT'and peer['findings']==[]and peer['freeze']==pin(S/'source-freeze01.json'),'570 independent source gate')
 composition=json.loads((S/'composition01.json').read_text());variant=composition['variants']['negative']
 rows=copy.deepcopy(variant['devices']);texts={p.name:p.read_text()for p in sorted((S/'includes01').glob('*.spice'))}
 texts[SOURCE.name]=SOURCE.read_text()
 fixture=list(variant['fixture'])
 old='VRESET reset 0 PWL(0 0 500p 2.5 8n 2.5 8.1n 0)'
 require(fixture.count(old)==1,'Exact original PFD reset fixture')
 fixture[fixture.index(old)]='VRESET reset 0 PWL(0 0 500p 2.5)'
 fixture.append(f'VCTRL vctrl 0 PWL(0 0 500p {vctrl:.1f})')
 c=dict(case='clamped570_pfd_idle_tuning_only',sources=[str(S/'source-freeze01.json'),str(S/'source-contract-peer-root01.json'),str(S/'composition01.json'),str(S/'tuning-contract01.json'),str(SOURCE),str(Path(__file__)),*[str(S/'includes01'/name)for name in texts if name!=SOURCE.name]],roots=[variant['root']],fixture=fixture,step_s=3.125e-13,stop_s=34e-9,window_s=[4e-9,34e-9],minimum_states=8,vctrl=vctrl,fault='',polarity_selected=False,connected_loop_acceptance=False,maximum_rows=MAX_ROWS)
 extras=[f'i({line.split()[0].lower()})'for line in fixture if line.startswith('V')]
 native_nodes={f'v({node})'for r in rows for node in r['nets']if node!='0'}
 for vector in OBS[1:]:
  if vector not in native_nodes and vector not in extras:extras.append(vector)
 c['extra_vectors']=extras
 require(len(rows)==570 and sum(x['model']=='npn13g2'for x in rows)==64,'Complete570/64HBT census')
 require(sum(x['model']in('ptap1','ntap1')for x in rows)==31,'Complete31 contacts')
 expected=set(variant['observation_vectors'])|{'i(vctrl)'}
 actual=n.vectors(rows,extras)
 require(set(actual)==expected and len(actual)==1133,'Every source-census observation plus actual clamp current')
 return c,rows,texts

def regular_bytes(directory):
 """Bounded conservative sample; only the exact owned FIFO may be nonregular."""
 used=0
 with os.scandir(directory)as entries:
  for entry in entries:
   metadata=entry.stat(follow_symlinks=False)
   if stat.S_ISDIR(metadata.st_mode):used+=regular_bytes(entry.path)
   elif stat.S_ISFIFO(metadata.st_mode):
    require(Path(entry.path).name=='stream.fifo'and Path(entry.path).parent.parent==NATIVE_ROOT,'Only exact direct-point stream FIFO')
   else:
    require(stat.S_ISREG(metadata.st_mode),'No linked or special native evidence')
    used+=metadata.st_size
 return used

def sampled_bytes(directory):
 directory=Path(directory)
 if not directory.exists():
  require(not directory.is_symlink(),'No dangling native evidence symlink')
  return 0
 require(not directory.is_symlink(),'No native evidence root symlink')
 for attempt in range(4):
  try:return regular_bytes(directory)
  except FileNotFoundError:
   if attempt==3:raise
 raise AssertionError('unreachable')

def guard(folder,pending=0,*,terminal_tail=False):
 folder=Path(folder)
 require(folder.parent==NATIVE_ROOT and not folder.is_symlink(),'Declared fresh SSD point root')
 require(B.stat().st_dev!=Path('/dev/shm').stat().st_dev,'SSD native storage')
 free=shutil.disk_usage('/dev/shm').free;ssd_free=shutil.disk_usage(B).free
 reserve=RECEIPT_RESERVE if not terminal_tail else RECEIPT_RESERVE-FAILED_TAIL_RESERVE
 if terminal_tail:
  # This branch is only reached after an exception and always re-raises it.
  # Close already-received bytes from the reserved space even if the trigger
  # was a shared/SSD floor violation. It cannot make a failed point pass.
  require(0<=pending<=FAILED_TAIL_RESERVE,'Reserved failed-tail bytes only')
  require(ssd_free>=pending+reserve,'Failed-tail physical space and receipt reserve')
 else:
  require(free>=FLOOR,'Shared512MiB reserve')
  require(ssd_free>=SSD_FLOOR+pending+reserve,'SSD1GiB continuous and terminal reserve')
 point=sampled_bytes(folder);total=sampled_bytes(NATIVE_ROOT)
 require(point+pending+reserve<=POINT_LIMIT,'Point1280MiB byte cap and final receipts')
 require(total+pending+reserve<=AGGREGATE_LIMIT,'Aggregate4GiB byte cap including failures')
 return free,total

def measurement(data,c):
 observed={key.replace('v(xloop.xchain.','v(xchain.'):value for key,value in data.items()}
 result=previous.core.old.measure_chain(observed,c)
 require(len(result['checks'])==13,'Original thirteen division predicates')
 result['vctrl_external_v']=c['vctrl'];result['connected_pll']=False
 t=data['time'];mask=(t>=c['window_s'][0])&(t<=c['window_s'][1]);require(mask.any(),'Settled570 tuning samples')
 tuning=dict(pfd_up_idle=bool(np.max(abs(data['v(up)'][mask]))<=0.25),pfd_down_idle=bool(np.max(abs(data['v(down)'][mask]))<=0.25),external_reset_asserted=bool(np.min(data['v(reset)'][mask])>=2.25),actual_clamp_level=bool(np.max(abs(data['v(vctrl)'][mask]-c['vctrl']))<=1e-9))
 result['tuning_checks']=tuning;result['division_passed']=result['passed'];result['passed']=result['passed']and all(tuning.values())
 result['polarity_selected']=False;result['quasistatic_pump_reachability_measured']=False
 result['clamp_current_sign']='Positive i(VCTRL) is current sunk by external ideal clamp; sign control is required before combining with separate pump force measurements.'
 result['windows']=[]
 for start,end in [(4e-9,14e-9),(14e-9,24e-9),(24e-9,34e-9)]:
  item=dict(interval_s=[start,end],clamp_charge_c=float(n.common.integrate(t,data['i(vctrl)'],start,end)),vctrl_min_v=float(data['v(vctrl)'][(t>=start)&(t<=end)].min()),vctrl_max_v=float(data['v(vctrl)'][(t>=start)&(t<=end)].max()))
  item['clamp_mean_a']=item['clamp_charge_c']/(end-start)
  for label,signal,threshold in [('vco',data['v(clkp)']-data['v(clkn)'],0),('cml',data['v(qp)']-data['v(qn)'],0),('feedback',data['v(fb)'],0.6)]:
   edges=[x for x in n.common.crossings(t,signal,threshold)if start<=x<end]
   item[label]=dict(edges_s=edges,frequency_hz=None if len(edges)<2 else float(1/np.mean(np.diff(edges))))
  result['windows'].append(item)
 return result
