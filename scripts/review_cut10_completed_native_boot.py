# SPDX-License-Identifier: Apache-2.0
"""Re-evaluate preserved completed cut10 native boot; do not rerun simulation."""
import hashlib,json,pathlib,sys,zipfile,re
sys.path.insert(0,'hw/soc/flow')
from sim_logic_boot_gl import boot_checks,validate_mbist_profile,validate_pcie_profile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r=dict(status='FAIL',full_chip_acceptance=False,manufacturing_approval=False,source_run=43475775445,source_commit='ba32f20d93f3256c9cab5bbea2211ff057b1723a',scope='Re-evaluation of the preserved zero-delay native Icarus gate-level CPU/Ethernet firmware boot with PCIe held link-down. No PCIe traffic, MBIST execution, SDF, analog PHY or fault coverage.')
try:
 raw=pathlib.Path('native.zip').read_bytes();sha=hashlib.sha256(raw).hexdigest()
 assert sha=='60a63237c80f62200b6ff960cb9d0320e6ca896c94a48ff10bf6c20d6a36acc7'
 z=zipfile.ZipFile('native.zip');hashes={}
 def read(suffix):
  names=[n for n in z.namelist() if ('/'+n).endswith('/'+suffix)];assert len(names)==1,(suffix,names)
  data=z.read(names[0]);hashes[suffix]=hashlib.sha256(data).hexdigest();return data
 inputs=json.loads(read('gates/inputs.json'));old=json.loads(read('gates/result.json'))
 log=read('gates/run-0.log').decode();config=json.loads(read('core-configuration.json'))
 net=read('synthesis/soc_top.netlist.v')
 matched=[v for k,v in inputs['sources'].items() if k.endswith('/synthesis/soc_top.netlist.v')];assert len(matched)==1
 assert hashlib.sha256(net).hexdigest()==matched[0]['sha256']
 assert inputs['pcie']['profile']=='packet-async' and inputs['mbist']['profile']=='off'
 assert '-DNSSOC_GL_MBIST' not in inputs['compile_command']
 assert inputs['simulator']=='iverilog' and old['sources_unchanged'] is True
 assert old['compile']['returncode']==0 and old['native_cell_gate']['passed'] is True
 assert len(old['runs'])==len(inputs['run_commands'])==1
 pcie=validate_pcie_profile(net.decode(),'packet-async');mbist=validate_mbist_profile(net.decode(),'off')
 corrected=boot_checks(log,old['runs'][0]['returncode'],'packet-async','off')
 assert corrected['passed'] and corrected['mbist_boot_passed'] is None and corrected['mbist_boot_status']=='not_requested'
 assert corrected['pcie_idle_boot_status']=='passed'
 r.update(status='PASS_SCOPED_NATIVE_PCIE_IDLE_BOOT',archive_sha256=sha,member_hashes=hashes,corrected_checks=corrected,original_checks=old['runs'][0],original_report_mbist_claim_invalid=True,configuration=config,pcie=pcie,mbist=mbist,compile=old['compile'],simulator=inputs['simulator'],version=inputs['version'],cycle_bound=inputs['cycle_bound'],run_timeout_s=inputs['run_timeout_s'],banners=[line for line in log.splitlines() if line.startswith(('LOGICROM_GL PASS','PCIE_IDLE_BOOT PASS','MBIST_BOOT PASS'))],netlist_sha256=hashlib.sha256(net).hexdigest())
except Exception as e:r.update(error=type(e).__name__+': '+str(e))
(out/'native-boot-corrected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['status']=='PASS_SCOPED_NATIVE_PCIE_IDLE_BOOT' else 1)
