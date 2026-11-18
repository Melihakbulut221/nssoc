#!/usr/bin/env python3
"""Pinned schematic pad turn-off current diagnostic; no timing-model waiver."""
import os,json,subprocess,hashlib,tarfile,io,base64,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CLAMP=os.environ['NSSOC_PAD_CLAMP_OHMS'];assert CLAMP in ['0','1','10']
ITL4=os.environ['NSSOC_PAD_ITL4'];assert ITL4 in ['100','1000']
STEP=os.environ.get('NSSOC_PAD_STEP_PS','5');assert STEP in ['5','2.5','1']
REDUCTION=os.environ['NSSOC_PAD_REDUCTION'];assert REDUCTION in ['n_clamp','n_forward','n_reverse']
OUT=ROOT/('hw/soc/out/core-only-pad-nmos-'+REDUCTION+'-'+CLAMP+'ohm-itl4-'+ITL4+'-step-'+STEP+'ps')
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def asset(aid,digest):
 b=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid)])
 assert hashlib.sha256(b).hexdigest()==digest
 return tarfile.open(fileobj=io.BytesIO(b))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(reduction=REDUCTION,modified_diagnostic_circuit=True,full_pad_equivalent=False,clamp_series_ohms=int(CLAMP),source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,transistor_schematic_only=True,parasitic_extraction_qualified=False,liberty_modified=False,cases={})
 try:
  inp=OUT/'inputs';inp.mkdir()
  with asset(635228650,'43134a616eb4c742709a08d63f8277e2bd0536bfa89f690e170c0ac5859464bf')as t:
   t.extractall(inp,filter='data')
  manifest=json.loads((inp/'manifest.json').read_text())
  assert all(sha(inp/p)==v['sha256']for p,v in manifest['files'].items())
  with asset(634990104,'276fbd8b9128750b2f524ec7b0f9e43a45652af62e477a6d618a74ab804a91bf')as t:
   (inp/'r3_cmc.osdi').write_bytes(t.extractfile('r3_cmc.osdi').read())
  assert sha(inp/'r3_cmc.osdi')=='9b41facf3c49d2266e542406547ed00677304f09c1dd281f3bf90414ee053828'
  path='ihp-sg13g2/libs.ref/sg13g2_io/spice/sg13g2_io.spi'
  obj=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/contents/'+path+'?ref='+PDK]))
  (inp/'sg13g2_io.spi').write_bytes(base64.b64decode(obj['content']))
  assert sha(inp/'sg13g2_io.spi')=='c2cfa122268050f770e91eeb0c70682775f9610cf4d5b066805b2d57c5980ce2'
  ng=Path(os.environ['CLOUD_NGSPICE'])
  init=inp/'startup';init.mkdir();(init/'spinit').write_text('set num_threads=1'+chr(10)+'option klu'+chr(10))
  native_env=dict(os.environ,SPICE_SCRIPTS=str(init))
  r['solver_configuration']=dict(matrix_solver='KLU',method='gear',maxord=2,max_step_ps=float(STEP),transient_iteration_limit=int(ITL4),initial_conditions='native DC operating point',forced_initial_conditions=False,tolerances_relaxed=False)
  r['runtime_version']=subprocess.check_output([str(ng),'--version'],text=True,env=native_env)
  assert 'ngspice-47'in r['runtime_version']
  protected={str(p):sha(p)for p in [Path(__file__),ng,*[p for p in inp.rglob('*')if p.is_file()]]}
  r['protected_inputs']=protected
  for bit in [0,1]:
   for mode in ['turnoff','enabled','disabled']:
    name=str(bit)+'-'+mode;folder=OUT/name
    try:
     folder.mkdir()
     enable='PWL(0 1.08 20n 1.08 20.12n 0 50n 0)'if mode=='turnoff'else('1.08'if mode=='enabled'else'0')
     diagnostic=['.subckt diagnostic_pad vss vdd iovss iovdd p2c c2p c2p_en pad']
     if REDUCTION=='n_clamp':
      diagnostic+=['Xnclamp iovss iovdd pad ngate sg13g2_Clamp_N2N2D']
     elif REDUCTION=='n_forward':
      diagnostic+=['Xn pad ngate iovss iovss sg13_hv_nmos l=0.6um w=4.4um']
     else:
      diagnostic+=['Xn iovss ngate pad iovss sg13_hv_nmos l=0.6um w=4.4um']
     if True:
      active_n=3 if bit==0 else 0;active_p=3 if bit==0 else 0
      def gate_source(active,off):
       if mode=='turnoff':return 'PWL(0 '+str(active)+' 20n '+str(active)+' 20.12n '+str(off)+' 50n '+str(off)+')'
       return str(active if mode=='enabled'else off)
      diagnostic+=['Vngate ngate iovss '+gate_source(active_n,0),'Vpgate pgate iovss '+gate_source(active_p,3)]
     diagnostic+=['.ends diagnostic_pad']
     deck=['* native 4mA bidirectional pad, slow supplies and slow MOS, clamp at half IO rail',
       '.global sub!', 'Vsub sub! 0 0','.temp 125','.options method=gear maxord=2 itl4='+ITL4,
       '.lib "'+str(inp/'models/cornerMOSlv.lib')+'" mos_ss',
       '.lib "'+str(inp/'models/cornerMOShv.lib')+'" mos_ss',
       '.lib "'+str(inp/'models/cornerRES.lib')+'" res_wcs',
       '.lib "'+str(inp/'models/cornerDIO.lib')+'" dio_ss',
       '.include "'+str(inp/'sg13g2_io.spi')+'"',
       'Vcore vdd 0 1.08','Vio iovdd 0 3.0','Vdata data 0 '+str(bit*1.08),
       'Ven en 0 '+enable,*(['Vhold pad 0 1.5']if CLAMP=='0'else['Vhold held 0 1.5','Rfixture pad held '+CLAMP]),
       *diagnostic,'Xdut 0 vdd 0 iovdd p2c data en pad diagnostic_pad',
       '.control']
     deck+=['pre_osdi '+str(inp/p)for p in ['psp103.osdi','psp103_nqs.osdi','r3_cmc.osdi']]
     deck+=['set wr_singlescale','set wr_vecnames','save v(en) i(vhold) v(xdut.ngate) v(xdut.pgate) v(pad)',
       'option method=gear maxord=2 itl4='+ITL4,'option','tran '+STEP+'p 50n 0 '+STEP+'p','echo NSSOC_POST_TRAN_SOLVER_READBACK','option','wrdata wave.dat v(en) i(vhold) v(xdut.ngate) v(xdut.pgate) v(pad)',
       'echo NSSOC_PAD_CURRENT_CAPTURE_COMPLETE','quit','.endc','.end']
     p=folder/'bench.cir';p.write_text('\n'.join(deck)+'\n');protected[str(p)]=sha(p)
     with (folder/'native.log').open('w')as log:proc=subprocess.run([str(ng),'-n','-b',str(p)],cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=native_env)
     log=(folder/'native.log').read_text();row=dict(returncode=proc.returncode,diagnostics=[l for l in log.splitlines()if re.search(r'(?i)warning|error|singular|timestep too small|convergence|failed',l) and l.strip()!='Truncation error correction, charge based, is selected:'])
     r['cases'][name]=row
     solver_log=log.split('NSSOC_POST_TRAN_SOLVER_READBACK')[-1]
     row['gear2_native_readback']=bool(re.search(r'(?i)Integration Method = GEAR',solver_log)and re.search(r'MaxOrder = 2',solver_log))
     assert row['gear2_native_readback'],'Native post-transient Gear2 readback missing'
     row['iteration_limit_native_readback']=bool(re.search(r'itl4 \(transient iterations\) = '+ITL4+r'\b',solver_log))
     assert row['iteration_limit_native_readback'],'Native iteration limit readback missing'
     row['klu_native_readback']=bool(re.search(r'Matrix solver:\s*KLU\b',solver_log)and re.search(r'Using KLU.*Direct Linear Solver',log))
     assert row['klu_native_readback'],'Native KLU solver readback missing'
     assert proc.returncode==0 and 'NSSOC_PAD_CURRENT_CAPTURE_COMPLETE'in log
     assert not row['diagnostics'],row['diagnostics']
     a=np.loadtxt(folder/'wave.dat',skiprows=1);assert a.ndim==2 and a.shape[1]==6 and np.isfinite(a).all()
     t=a[:,0];assert np.all(np.diff(t)>0)and t[-1]>=49.99e-9
     row['maximum_observed_step_s']=float(np.max(np.diff(t)))
     assert row['maximum_observed_step_s']<=float(STEP)*1e-12*1.001+1e-18,'Capture exceeds requested maximum step'
     pre=(t>=10e-9)&(t<=19e-9);post=(t>=40e-9)&(t<=49e-9)
     assert pre.sum()>20 and post.sum()>20
     current=a[:,2];row['maximum_pad_deviation_from_clamp_v']=float(np.max(np.abs(a[:,5]-1.5)));row.update(rows=len(a),pre_current_a=float(np.median(current[pre])),post_current_a=float(np.median(current[post])),post_abs_max_a=float(np.max(np.abs(current[post]))))
     if mode!='disabled'and bit==0:assert abs(row['pre_current_a'])>1e-6,'No active pad drive'
     if mode=='turnoff'and bit==0:
      cutoff=.01*abs(row['pre_current_a']);indices=np.where((t>=20.06e-9)&(np.abs(current)<cutoff))[0]
      row['first_below_one_percent_after_enable_midpoint_s']=None if not len(indices)else float(t[indices[0]]-20.06e-9)
    except Exception as error:
     row=r['cases'].setdefault(name,{})
     row.update(status='FAIL_OR_INCOMPLETE',error=repr(error))
    else:
     row['status']='CAPTURE_COMPLETE'
  assert all(sha(p)==h for p,h in protected.items())
  r['sources_unchanged']=True
  failures={name:row.get('error','missing case')for name,row in r['cases'].items()if row.get('status')!='CAPTURE_COMPLETE'}
  assert len(r['cases'])==6 and not failures,failures
  r.update(status='REDUCED_DIAGNOSTIC_CAPTURES_COMPLETE_NOT_FULL_PAD_ACCEPTANCE',sources_unchanged=True)
 except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
