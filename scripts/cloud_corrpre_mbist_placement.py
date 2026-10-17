#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Implement the exact MBIST/PCIe boot-proven CORRPRE netlist through CTS."""
import argparse,hashlib,json,os,subprocess,time,zipfile
from pathlib import Path
from prepare_pcie_mainchip_pnr import prepare
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-corrpre-mbist-placement'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-spec',type=Path);args=parser.parse_args()
 spec=json.loads(args.source_spec.read_text())if args.source_spec else dict(run=38994926932,head='471a966524f68c18b9801488bfc512bee2dc2de0',artifact=12090748551,zip_sha256='0fcb32e81d63669f7df2833b83f4cb371bd9972a251bb0e15e77121b5e710d92')
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,qualified_pex=False,scope='CORRPRE/PCIe/20SRAM MBIST candidate from exact boot-proven netlist. This native stage ends at CTS; routing, all-corner extracted setup/hold and physical signoff remain required.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  source=ROOT/'cloud-corrpre-pcie-mbist-boot-evidence';report=json.loads((source/'result.json').read_text())
  assert report['status']=='PRESERVED_COMPLETED_NATIVE_CORRPRE_PCIE_SYSTEM_ETHERNET_MBIST_BOOT_NOT_TIMING_OR_PHYSICAL_ADOPTION'
  assert report['source_run']==spec['run'] and report['source_head_original']==spec['head'] and report['source_artifact']==spec['artifact'] and report['gate_result']['passed']
  if args.source_spec:assert report['source_spec']==spec and spec['bank_proof_and_protocol_verified'] is True
  archive=source/'original-corrpre-pcie-mbist-native-boot-full.zip'
  assert sha(archive)==report['original_zip_sha256']==spec['zip_sha256']
  boot=OUT/'boot';boot.mkdir()
  with zipfile.ZipFile(archive)as z:
   assert set(z.namelist())==set(report['files'])
   for n,meta in report['files'].items():
    p=Path(n);assert not p.is_absolute()and '..'not in p.parts
    data=z.read(n);assert hashlib.sha256(data).hexdigest()==meta['sha256']and len(data)==meta['bytes']
    target=boot/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  c=report['configuration'];assert c['RF_CORRPRE']==1 and c['RF_SYNPRE']==0 and c['SOC_SRAM_MBIST']==c['SOC_ETH_MBIST']==1 and c['CORE_REQ_REG']==c['CORE_WB_STAGE']==0
  assert c['SOC_PCIE_PROFILE']=='packet-async'and c['interface_profile']=='full'
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
  r.update(status='RUNNING_NATIVE_PLACEMENT_CTS',boot_source=report,command=command,protected_inputs=protected,app_sha256=sha(app));save();start=time.monotonic()
  (OUT/'run').mkdir(exist_ok=False)
  with (OUT/'run.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
  if code:print((OUT/'run.log').read_text(errors='replace')[-18000:],flush=True)
  assert code==0,'Native stage failed; evidence retained'
  assert all(sha(p)==h for p,h in protected.items()),'Protected source changed'
  states=list((OUT/'run').glob('*-openroad-cts/state_out.json'));assert len(states)==1,states
  state=json.loads(states[0].read_text());assert state.get('odb')and Path(state['odb']).is_file()
  r.update(status='COMPLETE_NATIVE_CORRPRE_MBIST_CTS_REQUIRES_ROUTING_AND_ALL_SIGNOFF_GATES',cts_state=str(states[0].relative_to(OUT)),cts_odb_sha256=sha(state['odb']),metrics=state.get('metrics',{}),sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
