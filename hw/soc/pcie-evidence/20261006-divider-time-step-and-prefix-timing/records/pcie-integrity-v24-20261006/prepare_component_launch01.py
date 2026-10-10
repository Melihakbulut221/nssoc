# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare a source-pinned standalone proof campaign; no compiler execution."""
from pathlib import Path
import json,hashlib,difflib,ast
B=Path(__file__).resolve().parent;R=B.parents[3];O=B.with_name('pcie-integrity-v23-20261006')
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
sources=[B/'architecture-contract01.json',B/'prefix_candidate01.vh',B/'test_matrix_relation01.py',R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v',R/'sw/tests/test_pcie_gen3_integrity_v3_crc.py',R/'scripts/generate_pcie_crc_candidates_v3.py',R/'scripts/characterize_pcie_clock_trim_stream_v2.py']
rt=json.loads((O.with_name('pcie-integrity-v18-20261005')/'max4118-01/runtime-targets-observed01.json').read_text())
sources += [Path(p) for p in rt['files']]
for p,h in rt['files'].items():assert pin(p)==h
f={'status':'FROZEN_STANDALONE_V24_MATRIX_COMPONENT_NOT_PRODUCT','sources':{str(p):pin(p) for p in sources},'native_mapping_started':False,'HDL_controls_started':False,'selected_controls':5,'scope':'One exhaustive actual four-state matrix alphabet positive and four actual miswired candidate fragments, unchanged frozen V23 helpers. No product integration or public-port acceptance.'}
freeze=B/'component-source-freeze01.json';assert not freeze.exists();freeze.write_text(json.dumps(f,indent=2)+'\n')
old=(O/'launch_controls_targeted03.py').read_text();s=old
s=s.replace('V23','V24').replace('v23','v24')
s=s.replace('source-freeze03.json','component-source-freeze01.json').replace('81b39160001de5717fa414371ec18b62772e367e7625e7aaab3af3b0f3af0540',pin(freeze)['sha256'])
s=s.replace('source-only-peer-vco03.json','component-source-peer-vco01.json').replace('PASS_SOURCE_ONLY_V24_ADJACENT_HEADER_RELATION','PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS')
a="assert j['freeze']==pin(freeze) and j['targeted_helper']==pin(B/'targeted_controls03.py') and j['saved_positive_reader']==pin(B/'read_targeted_positive02.py')"
s=s.replace(a,"assert j['freeze']==pin(freeze) and j['launcher']==pin(Path(__file__))")
s=s.replace('nssoc-integrity-v24-public-controls03','nssoc-integrity-v24-matrix-controls01')
start=s.index('command=');end=s.index('\nowner=',start)
s=s[:start]+"command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(B/'test_matrix_relation01.py'),'--basetemp='+str(D),'--junitxml='+str(B/'component-controls01.xml')]"+s[end:]
for a,b in [('controls-status03.json','component-status01.json'),('controls-owner03.json','component-owner01.json'),('controls03.log','component-controls01.log')]:s=s.replace(a,b)
s=s.replace('Separate V24 adjacent accepted header relation fromV22; same latency, allpublic cyclemiter and predecessor ownership; original4ns and2GiB fixed. Full functional controls plus independentpeer mustpass before any native mapping. ExistingPLL untouched.','Standalone V24 finite matrix relation and four actual mutants only; product RTL remains V23. No native mapping or public-cycle acceptance from this component proof. Existing PLL untouched.')
launcher=B/'launch_component01.py';assert not launcher.exists();launcher.write_text(s)
old2=(O/'detach_controls_targeted03.py').read_text();t=old2.replace('V23','V24').replace('v23','v24')
t=t.replace('launch_controls_targeted03.py','launch_component01.py').replace("{'bytes': 3754, 'sha256': 'c9ddafac32fdfcf1a51688e5288a95c7bc0ed99945114461f9a4bf9f2ac8c3fa'}",repr(pin(launcher)))
t=t.replace('source-freeze03.json','component-source-freeze01.json').replace("{'bytes': 2179, 'sha256': '81b39160001de5717fa414371ec18b62772e367e7625e7aaab3af3b0f3af0540'}",repr(pin(freeze)))
t=t.replace('source-only-peer-vco03.json','component-source-peer-vco01.json').replace('PASS_SOURCE_ONLY_V24_ADJACENT_HEADER_RELATION','PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS')
t=t.replace('nssoc-integrity-v24-public-controls03','nssoc-integrity-v24-matrix-controls01').replace('controls-status03.json','component-status01.json').replace('controls-detached-once03.json','component-detached-once01.json').replace('controls-launch03.log','component-launch01.log').replace('controls-detached-receipt03.json','component-detached-receipt01.json')
t=t.replace("assert not Path('/dev/shm", "assert j['launcher']==pin(B/'launch_component01.py') and j['detacher']==pin(Path(__file__))\nassert not Path('/dev/shm")
detach=B/'detach_component01.py';assert not detach.exists();detach.write_text(t)
for p in [launcher,detach,B/'test_matrix_relation01.py']:ast.parse(p.read_text())
r={'freeze':pin(freeze),'launcher':pin(launcher),'detacher':pin(detach),'ancestor_launcher':pin(O/'launch_controls_targeted03.py'),'ancestor_detacher':pin(O/'detach_controls_targeted03.py'),'whole_launcher_diff':''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),'whole_detacher_diff':''.join(difflib.unified_diff(old2.splitlines(True),t.splitlines(True))),'native_or_controls_launched':False}
(B/'component-launch-bridge01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if not k.startswith('whole')}))
