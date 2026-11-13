# SPDX-License-Identifier: Apache-2.0
"""Paired full-PLL short-startup solver experiment; never acquisition approval."""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys
import numpy as np
from pll_c5r3k_bench import read_raw
P=pathlib.Path
out=P('solver-performance');out.mkdir();r={'status':'INCOMPLETE','temperature_c':int(sys.argv[1]),'acquisition_accepted':False,'production_accepted':False,'scope':'Paired 50 ns startup; no relaxation of full 1 us acquisition gates','cases':{}}
try:
 original=(P('case')/'probe.cir').read_text()
 assert not re.search(r'(?im)^\s*(?:\.option\w*|set)\b[^\n]*\bklu\b',original+'\n'+(P('case')/'probe-circuit.cir').read_text()),'Unexpected preexisting KLU setting'
 for solver in ['default','klu']:
  if solver=='klu':
   shutil.copytree('case-default','case',ignore=shutil.ignore_patterns('*.raw','ngspice.log'))
   (P('case')/'probe.cir').write_text(original.replace('\n.include ', '\n.option klu\n.include ',1))
  p=subprocess.run([sys.executable,'scripts/measure_pll_thread_throughput.py',sys.argv[1],'4'],check=False)
  result=json.loads(P('performance/throughput.json').read_text());r['cases'][solver]=result
  log=P('case/ngspice.log').read_text(errors='replace')
  expected='Using KLU as Direct Linear Solver' if solver=='klu' else 'Using SPARSE 1.3 as Direct Linear Solver'
  assert expected in log,'Requested solver not confirmed in runtime log'
  assert p.returncode==0 and result['status']=='COMPLETE_THROUGHPUT_SAMPLE_ONLY','Incomplete startup'
  P('case').rename('case-'+solver);shutil.rmtree('performance')
 for p in ['probe-circuit.cir','parent865.spice','spinit']:
  assert (P('case-default')/p).read_bytes()==(P('case-klu')/p).read_bytes(),'Circuit or initialization changed'
 a,an=read_raw(P('case-default/probe.raw'));b,bn=read_raw(P('case-klu/probe.raw'));assert an==bn
 ta=np.asarray(a[:,0]);tb=np.asarray(b[:,0]);assert ta[0]>=tb[0] and ta[-1]<=tb[-1]
 diffs=[]
 for i in range(1,len(an)):
  av=np.asarray(a[:,i]);bv=np.asarray(b[:,i]);assert np.isfinite(av).all() and np.isfinite(bv).all()
  delta=av-np.interp(ta,tb,bv);scale=max(float(np.max(np.abs(av))),float(np.max(np.abs(bv))),1e-30)
  diffs.append({'signal':an[i],'max_abs_difference':float(np.max(np.abs(delta))),'max_abs_relative_to_peak':float(np.max(np.abs(delta)))/scale})
 r.update(status='PAIRED_STARTUP_DIAGNOSTIC_COMPLETE',signal_count=len(diffs),worst_peak_normalized_differences=sorted(diffs,key=lambda x:x['max_abs_relative_to_peak'],reverse=True)[:30],speedup_default_over_klu=r['cases']['default']['elapsed_s']/r['cases']['klu']['elapsed_s'],numerical_equivalence_accepted=False)
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status']=='PAIRED_STARTUP_DIAGNOSTIC_COMPLETE' else 1)
