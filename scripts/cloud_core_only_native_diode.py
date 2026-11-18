#!/usr/bin/env python3
"""Native diode-only reproducer; no product changes or model parameter edits."""
import os,json,subprocess,hashlib,tarfile,io,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/core-only-native-diode'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 report=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,product_circuit=False,osdi_loaded=False,status='PREPARING',cases={})
 try:
  raw=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream','repos/Melihakbulut221/nssoc/releases/assets/635228650'])
  assert hashlib.sha256(raw).hexdigest()=='43134a616eb4c742709a08d63f8277e2bd0536bfa89f690e170c0ac5859464bf'
  with tarfile.open(fileobj=io.BytesIO(raw))as archive:
   manifest=json.load(archive.extractfile('manifest.json'))
   model=archive.extractfile('models/diodes.lib').read()
  assert hashlib.sha256(model).hexdigest()==manifest['files']['models/diodes.lib']['sha256']
  models=OUT/'diodes.lib';models.write_bytes(model)
  init=OUT/'startup';init.mkdir();(init/'spinit').write_text('set num_threads=1\noption klu\n')
  env=dict(os.environ,SPICE_SCRIPTS=str(init));ng=Path(os.environ['CLOUD_NGSPICE'])
  report['runtime_version']=subprocess.check_output([str(ng),'--version'],env=env,text=True);assert 'ngspice-47'in report['runtime_version']
  protected={str(p):sha(p)for p in [Path(__file__),ng,models,init/'spinit']};report['protected_inputs']=protected
  parts={'antenna':'Xdio 0 gate dantenna l=0.64u w=0.48u','area':'D1 0 gate darea area=0.3072','perimeter':'D2 0 gate dperim area=2.24','corner':'D3 0 gate dcorner area=4'}
  for part,device in parts.items():
   for mode in ['release','reverse','zero']:
    name=part+'-'+mode;folder=OUT/name;folder.mkdir();row={};report['cases'][name]=row
    try:
     drive='PWL(0 3 20n 3 20.12n 0 50n 0)'if mode=='release'else('3'if mode=='reverse'else'0')
     instance={'antenna':'d.xdio.d1','area':'d1','perimeter':'d2','corner':'d3'}[part]
     fields=['vd','id','gd','cd','charge','capcur'];vectors=' '.join('@'+instance+'['+field+']'for field in fields)
     row['wave_columns']=['time','gate_voltage','drive_current']+fields
     deck=['* unchanged native diode model, no transistors or OSDI','.temp 125','.options method=gear maxord=2 itl4=100','.include "'+str(models)+'"','Vdrive gate 0 '+drive,device,'.control','set wr_singlescale','set wr_vecnames','set numdgt=15','save v(gate) i(vdrive) '+vectors,'option method=gear maxord=2 itl4=100','tran 1p 50n 0 1p','echo NSSOC_DIODE_SOLVER_READBACK','option','wrdata wave.dat v(gate) i(vdrive) '+vectors,'echo NSSOC_DIODE_CAPTURE_END','quit','.endc','.end']
     p=folder/'bench.cir';p.write_text('\n'.join(deck)+'\n');protected[str(p)]=sha(p)
     with (folder/'native.log').open('w')as log:result=subprocess.run([str(ng),'-n','-b',str(p)],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
     log=(folder/'native.log').read_text();tail=log.split('NSSOC_DIODE_SOLVER_READBACK')[-1]
     row['returncode']=result.returncode
     row['diagnostics']=[l for l in log.splitlines()if re.search(r'(?i)warning|error|singular|timestep too small|convergence|failed',l)and l.strip()!='Truncation error correction, charge based, is selected:']
     row['solver_readback']=bool(re.search(r'Matrix solver:\s*KLU\b',tail)and 'Using KLU as Direct Linear Solver'in log and 'Integration Method = GEAR'in tail and 'MaxOrder = 2'in tail and 'itl4 (transient iterations) = 100'in tail)
     assert row['solver_readback']and result.returncode==0 and 'NSSOC_DIODE_CAPTURE_END'in log
     a=np.loadtxt(folder/'wave.dat',skiprows=1);assert a.ndim==2 and a.shape[1]==9 and np.isfinite(a).all()
     row['last_sample_before_validation']={k:float(v)for k,v in zip(row['wave_columns'],a[-1])}
     assert not row['diagnostics'],row['diagnostics']
     dt=np.diff(a[:,0]);assert np.all(dt>0)and a[-1,0]>=49.99e-9 and np.max(dt)<=1.001e-12+1e-18
     row.update(status='CAPTURE_COMPLETE',rows=len(a),last_time_s=float(a[-1,0]),maximum_step_s=float(np.max(dt)),final_drive_current_a=float(a[-1,2]))
    except Exception as error:row.update(status='FAIL_OR_INCOMPLETE',error=repr(error))
  assert all(sha(p)==h for p,h in protected.items());report['sources_unchanged']=True
  failures={n:r.get('error')for n,r in report['cases'].items()if r['status']!='CAPTURE_COMPLETE'}
  assert len(report['cases'])==12 and not failures,failures
  report['status']='NATIVE_DIODE_CAPTURES_COMPLETE_NOT_PRODUCT_SIGNOFF'
 except BaseException as error:report.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
 finally:
  report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
