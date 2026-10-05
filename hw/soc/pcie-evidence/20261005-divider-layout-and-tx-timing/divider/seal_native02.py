# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve a complete native physical prototype suite, without timing acceptance."""
from pathlib import Path
import hashlib,json,tarfile,sys,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'hw/soc/flow'));import check_pcie_clock_div4_v7_v2 as c
ns=c.lifecycle()
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
manifest=json.loads((B/'launch-manifest02.json').read_text());identity=json.loads((B/'identity-checkpoint02.json').read_text())['identity']
live=ns['process_identity'](identity['pid']);assert live is None or live['state']=='Z' or live['start_ticks']!=identity['start_ticks']
checks=Path(manifest['checks']);layout=Path(manifest['layout']);result=json.loads((checks/'result.json').read_text())
assert result['status']=='PASS_DIV4_V7_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY'
expected=['drc','offgrid','lvs','lvs_flat',*c.REFERENCE_FAULTS,*c.PHYSICAL_FAULTS,'lef','lef_missing_pin','lef_blocked_pin']
assert [s['name'] for s in result['steps']]==expected and len(expected)==21
assert result['outputs']=={str(p.relative_to(checks)):pin(p)['sha256'] for p in sorted(checks.rglob('*')) if p.is_file() and p!=checks/'result.json'}
assert not ET.parse(checks/'drc/drc.lyrdb').getroot().findall('./items/item')
assert ET.parse(checks/'offgrid/drc.lyrdb').getroot().findall('./items/item')
assert manifest['layout_files']=={str(p.relative_to(layout)):pin(p) for p in layout.rglob('*') if p.is_file()}
for name in ('lvs','lvs_flat'):
 a=json.loads((checks/name/'audit.json').read_text());assert a['status']=='PASS within comparison scope';assert len(a['circuits'])==1 and a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==74
for fault in [*c.REFERENCE_FAULTS,*c.PHYSICAL_FAULTS]:
 a=json.loads((checks/fault/'audit.json').read_text());assert a['status']=='FAIL'
files={}
for label,root in [('layout',layout),('checks',checks)]:
 for p in sorted(root.rglob('*')):
  if p.is_file():files['native/'+label+'/'+str(p.relative_to(root))]=p
  if p.name.endswith('.owned.json'):
   for e in json.loads(p.read_text())['processes']:
    assert not any(x['state']!='Z' for x in ns['group_members'](e['process_group']))
excluded={}
for name,expected_pin in manifest['inputs'].items():
 p=Path(name);assert pin(p)==expected_pin
 if p.stat().st_size>2*1024**2:excluded[name]=expected_pin;continue
 rel='project/'+str(p.relative_to(R)) if p.is_relative_to(R) else 'external/'+str(p).lstrip('/')
 files[rel]=p
for name in ('launch-manifest02.json','identity-checkpoint02.json','launch-dispatch02.json','native02.log','source-only-peer01-circuit-and-findings.json','source_peer_circuit01.py','source-peer-boundary-findings01.json','source-controls01.log','source-controls02.log','source-controls03.log','source-controls04.log','source-only-peer03-rx.json','native-schema-source-only-peer01-rx.json','native-schema-controls01.log','native01-preservation.json','native01-members.json','native01-validation.json','release-native01.json','seal_native02.py'):
 files['review/'+name]=B/name
summary=dict(status='ACTUAL_STANDALONE_DIVIDER_V7_21_NATIVE_STEPS_COMPLETE',primitive_counts=json.loads((layout/'result.json').read_text())['primitive_counts'],ports=list(c.PORTS),native_steps=[dict(name=s['name'],status=s['status']) for s in result['steps']],main_DRC_violations=0,deep_flat_LVS_devices=74,positive_checks=4,actual_negative_checks=17,excluded_large_runtime_binaries_still_pinned=excluded,first_parser_failure_preserved=True,layout_sha256=pin(layout/(c.TOP+'.gds'))['sha256'],qualified_rc=False,extracted_division=False,PHY_or_manufacturing_acceptance=False)
(B/'native02-summary.json').write_text(json.dumps(summary,indent=2)+'\n');files['review/native02-summary.json']=B/'native02-summary.json'
members={n:pin(p) for n,p in files.items()};cap=B/'pcie-divider-v7-native-02-complete.tar.xz';assert not cap.exists()
with tarfile.open(cap,'w:xz',preset=1) as arc:
 for n,p in files.items():arc.add(p,arcname=n,recursive=False)
seen={}
with tarfile.open(cap,'r|xz') as arc:
 for item in arc:
  assert item.isfile() and item.name not in seen;seen[item.name]=dict(bytes=item.size,sha256=hashlib.file_digest(arc.extractfile(item),'sha256').hexdigest())
assert seen==members and all(pin(p)==members[n] for n,p in files.items())
(B/'native02-members.json').write_text(json.dumps(members,indent=2)+'\n')
receipt=dict(status='SEALED_NATIVE_DIVIDER_PHYSICAL_PROTOTYPE_ALL_MEMBERS_VERIFIED',archive=dict(path=str(cap),**pin(cap)),members=len(members),physical_acceptance=False,qualified_rc=False,extracted_division=False)
(B/'native02-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
