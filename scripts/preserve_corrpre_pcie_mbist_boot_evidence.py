#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve completed native boot evidence without rerunning simulation."""
import hashlib,io,json,os,re,subprocess,zipfile
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=Path('cloud-corrpre-pcie-mbist-boot-evidence');root.mkdir(exist_ok=False)
repo='repos/Melihakbulut221/nssoc'
run=json.loads(subprocess.check_output(['gh','api',repo+'/actions/runs/38994926932']))
assert run['head_sha']=='471a966524f68c18b9801488bfc512bee2dc2de0'and run['status']=='completed'and run['conclusion']=='success'
raw=subprocess.check_output(['gh','api',repo+'/actions/artifacts/12090748551/zip'])
digest=hashlib.sha256(raw).hexdigest();assert digest=='0fcb32e81d63669f7df2833b83f4cb371bd9972a251bb0e15e77121b5e710d92'
(root/'original-corrpre-pcie-mbist-native-boot-full.zip').write_bytes(raw)
z=zipfile.ZipFile(io.BytesIO(raw));assert len(z.namelist())==43 and len(set(z.namelist()))==43
files={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest())for n in z.namelist()}
configuration=json.loads(z.read('core-configuration.json'));assert configuration['RF_CORRPRE']==1 and configuration['RF_SYNPRE']==0 and configuration['interface_profile']=='full'
gates=json.loads(z.read('gates/result.json'));assert gates['passed']and gates['sources_unchanged']and gates['native_cell_gate']['passed']
assert len(gates['runs'])==1 and gates['runs'][0]['returncode']==0 and gates['runs'][0]['pass_banner']
log=z.read('gates/run-0.log').decode();assert 'LOGICROM_GL PASS checks=28'in log
assert 'checks=28 fails=00000000 code=00000000 magic=600dc0de'in log
assert configuration['SOC_PCIE_PROFILE']=='packet-async'and not configuration['pcie_traffic_tested']
assert gates['runs'][0]['pcie_idle_boot_passed']
samples=re.findall(r'(?m)^PCIE_IDLE_BOOT PASS samples=([1-9][0-9]*)$',log);assert len(samples)==1
assert configuration['SOC_SRAM_MBIST']==configuration['SOC_ETH_MBIST']==1
assert gates['runs'][0]['mbist_boot_passed']
mbist=re.findall(r'(?m)^MBIST_BOOT PASS busy_cycles=([1-9][0-9]*) done_cycle=([1-9][0-9]*) eth_done=3$',log)
assert len(mbist)==1 and int(mbist[0][1])>int(mbist[0][0])
assert re.search(r'(?im)(?:FATAL:|ERROR:|%Fatal|%Error)',log) is None
inputs=json.loads(z.read('gates/inputs.json'))
netlist_sources=[v for k,v in inputs['sources'].items()if k.endswith('/synthesis/soc_top.netlist.v')]
assert len(netlist_sources)==1 and netlist_sources[0]['sha256']==files['synthesis/soc_top.netlist.v']['sha256']
scrub=json.loads(z.read('scrub-native/result.json'));assert scrub['status']=='PASS'and scrub['sources_unchanged']
assert scrub['commands'][-1]['returncode']==1 and scrub['commands'][2]['returncode']==0
result=dict(status='PRESERVED_COMPLETED_NATIVE_CORRPRE_PCIE_SYSTEM_ETHERNET_MBIST_BOOT_NOT_TIMING_OR_PHYSICAL_ADOPTION',source_head=os.environ['GITHUB_SHA'],source_run=38994926932,source_head_original=run['head_sha'],source_artifact=12090748551,original_zip_sha256=digest,original_zip_bytes=len(raw),configuration=configuration,gate_result=gates,scrub_result=scrub,native_log_banner=[s for s in log.splitlines()if s.startswith(('LOGICROM_GL','PCIE_IDLE_BOOT','MBIST_BOOT'))],files=files,accepted=False,new_simulation=False,final_timing_complete=False,scope='Original unmodified43-file artifact preserved permanently in Releases. Native mapped full-interface CORRPRE/SYNPRE0 packet-async boot28checks and independent PCIe idle samples; actual system and both Ethernet MBIST busy/done handover observed. Exact native netlist hash agrees with simulation input record. No packet traffic, noSDF, qualified physical timing, arbitrary faults or PHY acceptance. CORRPRE remains experimental and not adopted in routed mainchip.')
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
