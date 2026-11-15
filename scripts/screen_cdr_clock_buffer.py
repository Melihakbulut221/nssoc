# SPDX-License-Identifier: Apache-2.0
"""Native transistor feasibility only. Ideal sizing R/C, no physical PHY claim."""
import os,json,hashlib,subprocess,traceback,re
from pathlib import Path
import numpy as np
import cdr_mos650_gate_ac as runtime
import cdr_mos650_full650_loaded as frozen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'clock-buffer-screen';NATIVE=OUT/'native';DERIVED=OUT/'derived'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,data):(DERIVED/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REF']=='refs/heads/codex/cdr-cascode-clock-buffer-screen'
 assert os.environ['GITHUB_SHA']==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 assert sha(ROOT/'scripts/cdr_mos650_gate_ac.py')=='9d0fa16f38d785aef6278a68dcddc32d25bdc0a0c8b9740a519f62959cef8ca0'
 assert sha(ROOT/'scripts/cdr_mos650_full650_loaded.py')=='7f590eeab9c510b4739d56a80c6a214e13698d2e0eb41da182ef3ecb3b87de5c'
 assert sha(ROOT/'scripts/cdr-mos650-gate-ac-inputs.json')=='e4bde43353f157ad91ec572cdb0d11d4c58e14b67f7830c39d4beafd3ca4ddfa'
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 runtime.OUT=OUT;runtime.NATIVE=NATIVE;runtime.DERIVED=DERIVED
 cfg=runtime.read(ROOT/runtime.CFG);models=runtime.acquire_models(cfg['runtime'])
 engine=NATIVE/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
 assert (models/'models/models/cornerHBT.lib').is_file(),'Authenticated HBT library missing before native execution'
 circuit=ROOT/'scripts/cdr_cascode_clock_buffer_candidate.inc'
 specs={'xip':('ep','inp','tail',12),'xin':('en','inn','tail',12),'xcp':('cp','cas','ep',12),'xcn':('cn','cas','en',12),'xfp':('avdd','cn','outp',12),'xfn':('avdd','cp','outn',12),'xref':('bias','bias','0',1),'xtail':('tail','bias','0',12),'xtp':('outp','bias','0',16),'xtn':('outn','bias','0',16)}
 lines=[l for l in circuit.read_text().splitlines()if l and not l.startswith('*')]
 assert len(lines)==17 and sum(l.lower().startswith('x')for l in lines)==10
 for name,(c,b,e,nx)in specs.items():
  assert f'{name} {c} {b} {e} 0 npn13g2 nx={nx}' in [l.lower()for l in lines]
 protected={str(p):sha(p)for p in [Path(__file__),circuit,engine,Path(runtime.__file__),Path(frozen.__file__),*[p for p in models.rglob('*')if p.is_file()]]}
 results=[]
 for buffered in [False,True]:
  for load_ff in [100,250,500]:
   tag=('buffer'if buffered else'direct')+'-'+str(load_ff)+'ff';folder=NATIVE/tag;folder.mkdir()
   sourcep='inp'if buffered else'outp';sourcen='inn'if buffered else'outn'
   nodes=sorted({'cp0','cn0','avdd','outp','outn'}|({n for x in specs.values()for n in x[:3]}-{'0'}if buffered else set()))
   vectors=['v('+n+')'for n in nodes]+(['@q.'+n+'.qnpn13g2[ic]'for n in specs]if buffered else[])
   deck=['Native cascode clock buffer feasibility - not physical signoff',f'.lib "{models}/models/models/cornerHBT.lib" hbt_typ','.temp 27','.options reltol=1e-4 abstol=1e-12 sparse','VDD avdd 0 PWL(0 0 500p 2.5)', 'VCP cp0 0 '+frozen.clock(1.,True,False),'VCN cn0 0 '+frozen.clock(1.,False,False),f'RCP cp0 {sourcep} 10',f'RCN cn0 {sourcen} 10',f'CLP outp 0 {load_ff}f',f'CLN outn 0 {load_ff}f']
   if buffered:deck += [f'.include "{circuit}"']
   deck += [f'.tran {frozen.STEP:.14g} {frozen.STOP:.14g} 0 {frozen.STEP:.14g}', '.control','set num_threads=1','set filetype=binary','save '+' '.join(vectors)]
   if buffered:
    for n in specs:deck += [f'alter @q.{n}.qnpn13g2[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN q.{n}.qnpn13g2',f'show q.{n}.qnpn13g2 : off','echo NSSOC_NATIVE_FLAG_END']
   deck += ['op','run wave.raw','echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
   (folder/'bench.cir').write_text('\n'.join(deck)+'\n');(folder/'spinit').write_text('set num_threads=1\n')
   runtime.execute([engine,'-n','-b','bench.cir'],tag,seconds=1800,cwd=folder)
   log=(NATIVE/(tag+'.stdout')).read_text()+'\n'+(NATIVE/(tag+'.stderr')).read_text()
   options,notes,_=frozen.backend_readback(log,'sparse');assert not notes,notes
   if buffered:
    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
    assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in specs] and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',v)==['1']for _,v in flags)
   t,v,raw=frozen.read_streamed_wave(folder/'wave.raw',vectors,frozen.STOP,frozen.STEP)
   def voltage(n):return np.zeros(len(t))if n=='0'else v['v('+n+')']
   active=t>=frozen.START;delta=voltage('outp')-voltage('outn');cm=(voltage('outp')+voltage('outn'))/2
   tracking={};delays=[];missing=0;multiple=0
   for phase_ps in [10,20,37.5]:
    signed=[]
    for i in range(1,256):
     for edge,sign in [(frozen.START+(i+.5)*frozen.UI,1),(frozen.START+(i+1)*frozen.UI,-1)]:
      signed.append(float(np.interp(edge+phase_ps*1e-12,t,delta))*sign)
    tracking[str(phase_ps)]=dict(samples=len(signed),minimum_signed_v=min(signed),wrong_sign=sum(x<=0 for x in signed),below100mv=sum(x<.1 for x in signed))
   for i in range(1,256):
    for edge,sign in [(frozen.START+(i+.5)*frozen.UI,1),(frozen.START+(i+1)*frozen.UI,-1)]:
     ids=np.flatnonzero((t[:-1]>=edge)&(t[1:]<=edge+frozen.UI/2)&(delta[:-1]*sign<=0)&(delta[1:]*sign>0))
     if len(ids)!=1:missing+=len(ids)==0;multiple+=len(ids)>1;continue
     k=int(ids[0]);cross=t[k]-delta[k]*(t[k+1]-t[k])/(delta[k+1]-delta[k]);delays.append(float(cross-edge))
   devices={}
   if buffered:
    for name,(c,b,e,nx)in specs.items():
     vce=voltage(c)-voltage(e);vbe=voltage(b)-voltage(e);ic=v['@q.'+name+'.qnpn13g2[ic]']
     devices[name]=dict(minimum_active_vce_v=float(vce[active].min()),maximum_abs_vce_v=float(abs(vce).max()),maximum_abs_vbe_v=float(abs(vbe).max()),maximum_model_ic_per_emitter_a=float(abs(ic).max()/nx))
   demand={n:float(np.max(abs((voltage(src)-voltage(pin))/10)))for n,src,pin in [('p','cp0',sourcep),('n','cn0',sourcen)]}
   result=dict(case=tag,buffered=buffered,load_ff=load_ff,raw=raw,tracking=tracking,source_peak_current_a=demand,clock_crossing=dict(expected=510,observed=len(delays),missing=missing,multiple=multiple,minimum_s=min(delays)if delays else None,maximum_s=max(delays)if delays else None),commonmode_active_v=[float(cm[active].min()),float(cm[active].max())],devices=devices,options=options,accepted=False,scope='Standalone topology screen with native HBTs, ideal sizing resistors and lumped capacitors. Not actual650 load, native rppd, PEX, PVT, device-current SOA certification or PHY acceptance.')
   save(tag+'.json',result);results.append(result);print('MEASURED_CLOCK_BUFFER_CASE',tag,tracking['37.5'],flush=True)
 assert all(sha(p)==h for p,h in protected.items())
 save('result.json',dict(status='SIX_NATIVE_TOPOLOGY_SCREENS_COMPLETE_NOT_PHY_ACCEPTANCE',source_head=os.environ['GITHUB_SHA'],cases=[x['case']for x in results],protected_inputs=protected,accepted=False,physical_implementation=False,full_phy_accepted=False,scope='Follow-up requires realistic rppd/bias/contact geometry and complete unchanged actual650 loaded test; passing standalone traces cannot qualify integration.'))
try:main()
except BaseException:
 DERIVED.mkdir(parents=True,exist_ok=True);save('failure.json',dict(traceback=traceback.format_exc(),accepted=False));raise
