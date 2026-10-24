# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved native02 evidence readback; never rerun physical checks."""
from pathlib import Path
import collections,datetime,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent;D=B.parent;N=Path('/dev/shm/nssoc-div4-v7-checks-02');L=Path('/dev/shm/nssoc-div4-v7-layout-01');R=D.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def j(p):return json.loads(Path(p).read_text())
def stream_pin(f):
 h=hashlib.sha256();n=0
 while b:=f.read(1024**2):n+=len(b);h.update(b)
 return dict(bytes=n,sha256=h.hexdigest())
manifest=j(D/'native02-members.json');archive=D/'pcie-divider-v7-native-02-complete.tar.xz';assert pin(archive)==dict(bytes=554324,sha256='2b5d14e5d33d4a912f9d18118c96a52d053f1ccc2a9374dabeb4f3d8e6c9bd57')
with tarfile.open(archive,'r:xz') as t:
 assert len(t.getmembers())==len(manifest)==434 and set(t.getnames())==set(manifest)
 for m in t.getmembers():
  assert m.isfile() and m.size==manifest[m.name]['bytes']
  with t.extractfile(m) as f:assert stream_pin(f)==manifest[m.name]
record=j(N/'result.json');assert record['status']=='PASS_DIV4_V7_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY'
for name,digest in record['inputs'].items():assert pin(name)['sha256']==digest
for name,digest in record['outputs'].items():assert pin(N/name)['sha256']==digest
layout=j(L/'result.json')
for name,digest in layout['input_sha256'].items():assert pin(name)['sha256']==digest
for name,digest in layout['output_sha256'].items():assert pin(L/name)['sha256']==digest
launch=j(D/'launch-manifest02.json');assert {str(p.relative_to(L)):pin(p) for p in L.rglob('*') if p.is_file()}==launch['layout_files']
source=j(D/'native-schema-source-freeze01.json')
for n,v in source.items():assert pin(R/n)==v
peer=j(D/'native-schema-source-only-peer01-rx.json');assert peer['findings']==[] and peer['source_pins']==source
raw=j(B/'raw-database-read.json');assert len(raw['databases'])==16;database={x['name']:x for x in raw['databases']};outcomes=[]
positive=[];negative=[]
for step in record['steps']:
 name=step['name'];nd=N/name
 if name in ['drc','offgrid']:
  xml=ET.parse(nd/'drc.lyrdb').getroot();categories=xml.findall('.//category');items=xml.findall('./items/item');assert len(categories)==560
  counts=dict(collections.Counter(x.findtext('category') for x in items));assert len(items)==step['measurement']['markers'] and counts==step['measurement']['categories']
  assert 'KLayout DRC run for tables \'main\' completed' in (nd/'run.log').read_text()
  if name=='drc':assert not items;positive.append(name)
  else:assert len(items)==6 and counts['metal1_drw_Offgrid']==4;negative.append(name)
  outcomes.append(dict(name=name,categories=560,markers=len(items),marker_categories=counts));continue
 if 'audit' in step:
  d=database[name];assert pin(d['input']['path'])=={k:d['input'][k] for k in ['bytes','sha256']};assert len(d['pairs'])==1 and not d['extraction_diagnostics']
  pair=d['pairs'][0];assert pair['layout']=='nssoc_clock_div4_v7_layout' and pair['schematic']=='NSSOC_CLOCK_DIV4_V7_LAYOUT'
  audit=j(nd/'audit.json');assert audit==step['audit']
  for n,v in audit['inputs'].items():assert pin(n)==v
  assert audit['circuits'][0]['status']==pair['status'] and audit['circuits'][0]['layout_devices_recursive']==pair['layout_devices'] and audit['circuits'][0]['schematic_devices_recursive']==pair['schematic_devices']
  log=(nd/'deck.log').read_text();ports=re.search(r'^\.SUBCKT nssoc_clock_div4_v7_layout (.*)$',(nd/'extracted.cir').read_text(),re.M).group(1).split()
  assert 'strict port mode' in log and 'flag_missing_ports enabled' in log
  if name in ['lvs','lvs_flat']:
   assert pair['status']=='Match' and pair['layout_devices']==pair['schematic_devices']==74 and set(ports)==set(layout['ports']);assert 'INFO : Congratulations! Netlists match.' in log and "ERROR : Netlists don't match" not in log
   assert audit['reasons']==[];positive.append(name)
   lines=(nd/'extracted.cir').read_text().splitlines();rows=[]
   for line in lines:
    if line.startswith('+'):rows[-1]+=' '+line[1:]
    elif line and not line.startswith(('*','.')):rows.append(line)
   census=collections.Counter('hbt' if x.startswith('Q') else 'ptap' if ' ptap1 ' in x else 'resistor' if ' rppd ' in x else 'capacitor' if ' cap_cmim ' in x else 'UNKNOWN' for x in rows)
   assert census==dict(hbt=34,resistor=33,capacitor=6,ptap=1)
   assert sum('ptap1 A=72p P=144u' in x for x in rows)==1
  else:
   assert audit['status']=='FAIL' and "ERROR : Netlists don't match" in log and 'INFO : Congratulations! Netlists match.' not in log;negative.append(name)
   if name=='clock_open':assert pair['status']=='Match' and len(ports)==6 and set(ports)==set(layout['ports'])-{'CLKP'}
   else:assert pair['status']=='NoMatch'
   physical=nd/'wrong.gds';reference=nd/'wrong.cir'
   if physical.exists():assert pin(physical)!=pin(L/'nssoc_clock_div4_v7_layout.gds') and step['mutation_execution']['returncode']==0
   else:assert reference.exists() and pin(reference)!=pin(L/'schematic.cir')
  outcomes.append(dict(name=name,pair=pair,extracted_ports=ports,deck_verdict='MATCH' if name in ['lvs','lvs_flat'] else 'NO_MATCH',audit_reasons=audit['reasons']));continue
 log=(nd/'native.log').read_text();tcl=(nd/'inspect.tcl').read_text();assert tcl.count('findMTerm ')==7
 if name=='lef':
  assert step['execution']['returncode']==0 and 'PASS_NATIVE_ANALOG_BANK_LEF_ONLY' in log;positive.append(name)
 elif name=='lef_missing_pin':
  assert step['execution']['returncode']==1 and 'Analog terminal census changed' in log and 'PASS_NATIVE_ANALOG_BANK_LEF_ONLY' not in log;negative.append(name)
 elif name=='lef_blocked_pin':
  assert step['execution']['returncode']==1 and 'Divider pin obstruction overlap' in log and 'PASS_NATIVE_ANALOG_BANK_LEF_ONLY' not in log;negative.append(name)
 else:raise AssertionError(name)
 outcomes.append(dict(name=name,native_returncode=step['execution']['returncode'],native_seven_pin_tcl_checked=True))
assert len(positive)==4 and len(negative)==17 and len(record['steps'])==21
lef=(L/'nssoc_clock_div4_v7_layout.lef').read_text()
for name,value in layout['ports'].items():
 p=re.search(r'  PIN '+name+r'\n(.*?)  END '+name,lef,re.S).group(1)
 direction='INPUT' if name in ['CLKP','CLKN'] else 'OUTPUT' if name in ['QP','QN'] else 'INOUT';use='POWER' if name=='DIV_AVDD' else 'GROUND' if name in ['AVSS','SUB'] else 'SIGNAL'
 assert 'DIRECTION '+direction+' ;' in p and 'USE '+use+' ;' in p
assert len(re.findall(r'^  PIN ',lef,re.M))==7
owners=[]
for path in N.rglob('*.owned.json'):
 owner=j(path);assert owner['status']=='HEALTHY' and owner['cleanup'] is None
 for entry in owner['processes']:assert entry['status']=='REAPED_NO_LIVE_MEMBERS' and entry['members_at_leader_exit']==[]
 owners.append(dict(path=str(path),**pin(path)))
read_owner=j(B/'saved-database-reader.owned.json');assert read_owner['cleanup'] is None and all(x['status']=='REAPED_NO_LIVE_MEMBERS' and not x['members_at_leader_exit'] for x in read_owner['processes'])
result=dict(status='PASS_INDEPENDENT_SAVED_DIVIDER_V7_NATIVE02_FINITE_PHYSICAL_REVIEW',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),archive=dict(path=str(archive),**pin(archive)),full_member_readback=434,native_inputs_rehashed=len(record['inputs']),native_outputs_rehashed=len(record['outputs']),immutable_generated_gds=pin(L/'nssoc_clock_div4_v7_layout.gds'),launch_layout_files_equal=True,source_pins=source,source_peer=pin(D/'native-schema-source-only-peer01-rx.json'),raw_database_read=pin(B/'raw-database-read.json'),raw_reader_execution=pin(B/'reader-execution.json'),positive_stages=positive,expected_negative_stages=negative,stage_details=outcomes,closed_native_owner_receipts=owners,scope='All21 saved standalone divider native stages checked with434 archive members and16 raw LVS databases independently read through KLayout API. Raw mainDRC560categories0markers, realoffgrid6markers, deep+flat74/74and7ports;8reference+6physicalfaults plusoffgrid and2LEFfaults rejected. Clockopen xref remainsMatch but actual CLKP port is missing and strictdeck rejects; this distinction is retained. Native01 parserfailure remains preserved separately. Read-only database reader invoked; generation/extraction/DRC/LVS/LEF and tests were not rerun.',manufacturing_approval=False,qualified_pex=False,extracted_division=False,clockbank_integration=False,phy_complete=False,physical_acceptance=False)
p=B/'review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
