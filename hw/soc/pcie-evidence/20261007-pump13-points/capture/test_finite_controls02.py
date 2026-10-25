# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual finite-byte controls over declared synthetic13 fixtures; no solver."""
from pathlib import Path
import copy,gzip,hashlib,io,json,os,resource,sys
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_pump13_02 as m
D=B/'finite-controls02'

def main():
 assert not D.exists();D.mkdir();outcomes=[];recipes={}
 def ok(label,**kw):outcomes.append(dict(case=label,passed=True,**kw))
 for case in m.CASES:
  c,rows,texts=m.config(case);deck=m.deck(c,rows,texts);saved=[l for l in deck.splitlines()if l.startswith('save ')]
  assert len(saved)==1 and saved[0].split()[1:]==m.n.vectors(rows,c['extra_vectors']) and len(saved[0].split())==28
  assert len(rows)==13 and sum(len(r['nets'])for r in rows)==47 and len(m.OBS)==28
  assert 'alter @q.' not in deck and '.tran 3.125e-13 3.4e-08 0 3.125e-13' in deck
  recipes[case]=dict(config=c,devices=rows,text_pins={k:dict(bytes=len(v.encode()),sha256=hashlib.sha256(v.encode()).hexdigest())for k,v in texts.items()},deck=deck)
  t=np.array([0,4e-9,14e-9,24e-9,34e-9]);data={name:np.zeros(len(t)) for name in m.OBS};data['time']=t
  for name,value in [('v(up)',c['command_levels'][0]),('v(down)',c['command_levels'][1]),('v(vctrl)',c['vctrl']),('v(avdd)',2.3),('v(dvdd)',2.5)]:data[name][:]=value
  for name in ['i(vdd)','i(vddiv)','i(vup)','i(vdown)','i(vctrl)']:data[name][:]=2e-6
  result=m.measurement(data,c);assert result['passed'] and not result['loaded_force_computed']
  assert all(abs(w['currents']['i(vctrl)']['mean_a']-2e-6)<1e-18 for w in result['windows'])
  ok('recipe_and_synthetic_measurement_'+case,model_count=13,terminals=47,vectors=27,checks=result['checks'])
 c,rows,texts=m.config('v060-idle')
 t=np.array([0,4e-9,14e-9,24e-9,34e-9]);data={name:np.zeros(len(t))for name in m.OBS};data['time']=t
 for name,value in [('v(vctrl)',.6),('v(avdd)',2.3),('v(dvdd)',2.5)]:data[name][:]=value
 for vector in ['v(up)','v(down)','v(vctrl)','v(avdd)','v(dvdd)']:
  bad=copy.deepcopy(data);bad[vector]+=1e-6;r=m.measurement(bad,c)
  assert not r['passed'] and not r['checks'][vector];ok('reject_wrong_boundary_'+vector)
 columns=['time']+m.n.vectors(rows,c['extra_vectors']);names=m.stream.previous.data_names(columns)
 short=copy.deepcopy(c);short.update(stop_s=3*c['step_s'],window_s=[0,3*c['step_s']])
 a=np.zeros((4,len(columns)));a[:,0]=np.arange(4)*c['step_s']
 for name,value in [('v(avdd)',2.3),('v(dvdd)',2.5),('v(vctrl)',.6)]:a[:,names.index(name)]=value
 meter=m.Meter(columns,rows,short);meter.push(a);safe,_,_=meter.finish();assert safe['passed'] and len(safe['all_device_bounds'])==13
 ok('all13_inherited_safety_on_synthetic_four_static_rows',bounds=safe['all_device_bounds'],not_operating_point=True)
 for label,changed,array in [('terminal_overvoltage',rows,a.copy()),('drain_overcurrent',rows,a.copy()),('model_geometry',copy.deepcopy(rows),a.copy())]:
  row=next(r for r in changed if r['model']=='sg13_hv_nmos')
  if label=='terminal_overvoltage':array[:,names.index('v('+row['nets'][0]+')')]=3.301
  elif label=='drain_overcurrent':
   key='i(@n.'+row['path']+'.nsg13_hv_nmos[ids])';array[:,names.index(key)]=.01*float(row['params']['w'][:-1])
  else:row['params']['w']='0.000001u'
  meter=m.Meter(columns,changed,short);meter.push(array);s,_,_=meter.finish();assert not s['passed'];ok('reject_'+label)
 def raw(array,trailer=b'4'):
  h=f'Title: Explicit synthetic13 finite control\nDate: fixed\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: {len(columns)}\nNo. Points: 0\nVariables:\n'
  for i,name in enumerate(names):h+=f'{i}\t{name}\t'+('time'if i==0 else'current'if name.startswith('i(')else'voltage')+'\n'
  return h.encode()+b'Binary:\n'+array.astype('<f8').tobytes()+trailer
 root=m.NATIVE_ROOT;callback=m.measurement;m.NATIVE_ROOT=D/'native';m.NATIVE_ROOT.mkdir()
 m.measurement=lambda data,c:dict(passed=False,synthetic_four_row_transport_only=True)
 try:
  for label,array,limit,diagnostic in [('positive',a,m.MAX_ROWS,None),('nonfinite',a.copy(),m.MAX_ROWS,'All native observations finite'),('row_budget',a,3,'Bounded120000 native rows including adaptive extras')]:
   if label=='nonfinite':array[2,1]=np.nan
   folder=m.NATIVE_ROOT/label;folder.mkdir();body=raw(array);fixture=D/(label+'.raw');fixture.write_bytes(body)
   old=m.MAX_ROWS;m.MAX_ROWS=limit
   try:
    try:r=m.capture(io.BytesIO(body),folder,rows,short)
    except BaseException as e:
     assert diagnostic and diagnostic in str(e),(label,repr(e));failure=json.loads((folder/'capture-failure.json').read_text())
     assert failure['received_raw_bytes']==len(body) and failure['received_raw_sha256']==hashlib.sha256(body).hexdigest()
    else:assert diagnostic is None and r['safety']['passed'] and r['rows']==4
   finally:m.MAX_ROWS=old
   assert gzip.decompress((folder/'wave.raw.gz').read_bytes())==body
   ok('finite_capture_'+label,fixture=m.pin(fixture),captured=m.pin(folder/'wave.raw.gz'),expected_diagnostic=diagnostic)
 finally:m.NATIVE_ROOT=root;m.measurement=callback
 (B/'recipes01.json').write_text(json.dumps(recipes,indent=2)+'\n')
 result=dict(status='PASS_SYNTHETIC13_RECIPE_MEASUREMENT_SAFETY_AND_FINITE_CAPTURE_CONTROLS',cases=len(outcomes),outcomes=outcomes,
             method=m.pin(__file__),producer=m.pin(m.__file__),recipes=m.pin(B/'recipes01.json'),native_or_solver_executed=False,
             scope='Synthetic declared level/current and four-row safety/transport fixtures; actual reviewed formula/parser/gzip code executes. No circuit OP, physical current, sign-control, pump-force or loaded570 result.')
 (D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(outcomes))))

if __name__=='__main__':main()
