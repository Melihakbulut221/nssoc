#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve completed native boot evidence without rerunning simulation."""
import hashlib,io,json,os,subprocess,zipfile
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=Path('cloud-corrpre-boot-evidence');root.mkdir(exist_ok=False)
repo='repos/Melihakbulut221/nssoc'
run=json.loads(subprocess.check_output(['gh','api',repo+'/actions/runs/38970744432']))
assert run['head_sha']=='11d16ac647a2754a1e5488e5cd415f0207ccb2ec'and run['status']=='completed'and run['conclusion']=='success'
raw=subprocess.check_output(['gh','api',repo+'/actions/artifacts/12079369570/zip'])
digest=hashlib.sha256(raw).hexdigest();assert digest=='b95c4b0a3b3f1725a9cbf8ff77569f7accc6dbff23cf1d1e71f88d39f97bc2cf'
(root/'original-corrpre-native-boot-full.zip').write_bytes(raw)
z=zipfile.ZipFile(io.BytesIO(raw));assert len(z.namelist())==42
files={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest())for n in z.namelist()}
configuration=json.loads(z.read('core-configuration.json'));assert configuration['RF_CORRPRE']==1 and configuration['RF_SYNPRE']==0 and configuration['interface_profile']=='full'
gates=json.loads(z.read('gates/result.json'));assert gates['passed']and gates['sources_unchanged']and gates['native_cell_gate']['passed']
assert len(gates['runs'])==1 and gates['runs'][0]['returncode']==0 and gates['runs'][0]['pass_banner']
log=z.read('gates/run-0.log').decode();assert 'LOGICROM_GL PASS checks=28'in log
assert 'checks=28 fails=00000000 code=00000000 magic=600dc0de'in log
scrub=json.loads(z.read('scrub-native/result.json'));assert scrub['status']=='PASS'and scrub['sources_unchanged']
assert scrub['commands'][-1]['returncode']==1 and scrub['commands'][2]['returncode']==0
result=dict(status='PRESERVED_COMPLETED_NATIVE_CORRPRE_BOOT_AND_SCRUB_CONTROLS_NOT_TIMING_OR_PHYSICAL_ADOPTION',source_head=os.environ['GITHUB_SHA'],source_run=38970744432,source_head_original=run['head_sha'],source_artifact=12079369570,original_zip_sha256=digest,original_zip_bytes=len(raw),configuration=configuration,gate_result=gates,scrub_result=scrub,native_log_banner=[s for s in log.splitlines()if s.startswith('LOGICROM_GL')],files=files,accepted=False,new_simulation=False,final_timing_complete=False,scope='Original unmodified42-file artifact preserved permanently in Releases. Native mapped full-interface functional boot28checks; noSDF, qualified physical timing, arbitrary faults or PHY acceptance. CORRPRE remains experimental and not adopted in routed mainchip.')
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
