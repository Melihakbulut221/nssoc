# SPDX-License-Identifier: Apache-2.0
"""Identical short startup throughput only; no acquisition or device approval."""
import hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
from pll_c5r3k_bench import read_raw
from pll_c5r3k_temperature_screen import validate_temperature
out=pathlib.Path('performance');out.mkdir(exist_ok=True)
r={'status':'INCOMPLETE','acquisition_accepted':False,'device_safety_accepted':False,'production_accepted':False,'stop_s':5e-8,'maxstep_s':3.125e-13,'temperature_c':int(sys.argv[1]),'threads':int(sys.argv[2]),'scope':'Runtime experiment only. Shortened 50 ns startup cannot prove 1 us acquisition. Full original gates and duration remain required.'}
try:
 assert r['temperature_c'] in [-40,125] and r['threads'] in [1,2,4]
 env=dict(os.environ,SPICE_SCRIPTS=str(pathlib.Path('case').resolve()),OMP_NUM_THREADS=str(r['threads']))
 started=time.monotonic()
 with open('case/ngspice.log','wb') as f:
  try:rc=subprocess.run([str(pathlib.Path('engine').resolve()),'-n','-b','probe.cir'],cwd='case',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600).returncode
  except subprocess.TimeoutExpired:rc=124
 r.update(returncode=rc,elapsed_s=time.monotonic()-started)
 assert rc==0,'simulator did not complete'
 r['temperature_readback']=validate_temperature(pathlib.Path('case/ngspice.log').read_text(errors='replace'),r['temperature_c'])
 data,names=read_raw(pathlib.Path('case/probe.raw'));t=np.asarray(data[:,0]);assert np.isfinite(t).all() and len(t)>1 and np.all(np.diff(t)>0)
 assert abs(float(t[-1])-5e-8)<=3.125e-13,'incomplete interval'
 r.update(status='COMPLETE_THROUGHPUT_SAMPLE_ONLY',points=len(t),end_s=float(t[-1]),seconds_per_simulated_ns=r['elapsed_s']/(float(t[-1])*1e9),source_hashes={})
 for p in ['case/probe-circuit.cir','case/parent865.spice','case/spinit','engine','case/probe.raw']:
  with open(p,'rb') as f:r['source_hashes'][p]=hashlib.file_digest(f,'sha256').hexdigest()
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'throughput.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status']=='COMPLETE_THROUGHPUT_SAMPLE_ONLY' else 1)
