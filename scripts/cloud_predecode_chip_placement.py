#!/usr/bin/env python3
"""Implement exact new predecode mapped chip as a non-adopted physical candidate.
Functional boot is independently running; this is not a boot-qualified handoff.
"""
import hashlib,json,os,subprocess,time
from pathlib import Path
from prepare_pcie_mainchip_pnr import prepare
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-predecode-chip-placement'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,functional_boot_accepted=False,full_phy_accepted=False,final_timing_complete=False,qualified_pex=False,scope='Exact new predecode physical candidate only. Boot43620739672 remains separate and pending; no old boot proof reused. Placement and CTS only, no routed timing, serial PHY or production acceptance.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  report=json.loads((ROOT/'out/source-binding.json').read_text())
  assert report['source_run']==43618915765 and report['source_head']=='b900da8cc1d57b8b2ce80416b6742c36239afd63' and report['authenticated_files']==60
  assert report['netlist_sha256']=='4b17ff9e9dac2452c60fc3a1e1860e775cdce2015589bb020b7530ab83314997' and report['accepted'] is False
  boot=ROOT/'hw/soc/out/corrpre-pcie-mbist-native-boot'
  assert sha(boot/'synthesis/soc_top.netlist.v')==report['netlist_sha256']
  assert sha(boot/'synthesis/soc_top.mapped.json')=='532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a'
  prepared=OUT/'prepared';r['preparation']=prepare(boot/'synthesis/soc_top.mapped.json',boot/'synthesis/soc_top.netlist.v',prepared)
  config=json.loads((prepared/'config.json').read_text())
  assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
  assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
  assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
  assert len(r['preparation']['macros'])==20
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');flow=ROOT/'hw/soc/pnr/pcie_interface_flow.py'
  command=[str(app),'python',str(flow),'--flow','PacketInterfaces','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--from','Yosys.JsonHeader','--to','OpenROAD.CTS','--with-initial-state',str(prepared/'state.json')]
  for step in ['Yosys.Synthesis','Checker.YosysUnmappedCells','Checker.YosysSynthChecks','Checker.NetlistAssignStatements']:command+=['--skip',step]
  command.append(str(prepared/'config.json'))
  protected={str(p):sha(p)for p in [Path(__file__),flow,ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'scripts/prepare_pcie_mainchip_pnr.py',ROOT/'scripts/pcie_soc_constraints.py',ROOT/'scripts/pcie_apb_cdc_constraints.py',prepared/'config.json',prepared/'physical.sdc',prepared/'state.json',boot/'synthesis/soc_top.netlist.v',boot/'synthesis/soc_top.mapped.json']}
  r.update(status='RUNNING_NATIVE_PLACEMENT_CTS',source_binding=report,command=command,protected_inputs=protected,app_sha256=sha(app));save();start=time.monotonic()
  (OUT/'run').mkdir(exist_ok=False)
  with (OUT/'run.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
  if code:print((OUT/'run.log').read_text(errors='replace')[-18000:],flush=True)
  assert code==0,'Native stage failed; evidence retained'
  assert all(sha(p)==h for p,h in protected.items()),'Protected source changed'
  states=list((OUT/'run').glob('*-openroad-cts/state_out.json'));assert len(states)==1,states
  state=json.loads(states[0].read_text());assert state.get('odb')and Path(state['odb']).is_file()
  r.update(status='COMPLETE_PREDECODE_CANDIDATE_CTS_REQUIRES_BOOT_ROUTING_AND_ALL_SIGNOFF_GATES',cts_state=str(states[0].relative_to(OUT)),cts_odb_sha256=sha(state['odb']),metrics=state.get('metrics',{}),sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
