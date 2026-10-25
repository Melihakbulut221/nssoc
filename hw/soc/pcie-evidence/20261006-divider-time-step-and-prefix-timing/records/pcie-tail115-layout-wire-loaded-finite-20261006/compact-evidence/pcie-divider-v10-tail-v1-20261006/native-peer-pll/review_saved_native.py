# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved Tail115V1 evidence readback; never rerun physical checks."""
from pathlib import Path
import collections,datetime,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
from decimal import Decimal
B=Path(__file__).resolve().parent;D=B.parent;N=Path('/dev/shm/nssoc-div4-v10-tail-v1-checks-01');L=Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01');R=D.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def j(p):return json.loads(Path(p).read_text())
def stream_pin(f):
 h=hashlib.sha256();n=0
 while b:=f.read(1024**2):n+=len(b);h.update(b)
 return dict(bytes=n,sha256=h.hexdigest())
backup=j(D/'native-archive01.json');manifest=backup['members'];archive=Path(backup['archive']['path']);assert pin(archive)=={k:backup['archive'][k]for k in ['bytes','sha256']}
with tarfile.open(archive,'r:xz') as t:
 assert len(t.getmembers())==len(manifest)==340 and set(t.getnames())==set(manifest)
 for m in t.getmembers():
  assert m.isfile() and m.size==manifest[m.name]['bytes']
  with t.extractfile(m) as f:assert stream_pin(f)=={k:manifest[m.name][k]for k in ['bytes','sha256']}
ready=j(D/'native-finite-review-ready01.json');assert len(ready['closed_native_files'])==195
for name,value in ready['closed_native_files'].items():assert pin(name)==value
record=j(N/'result.json');assert record['status']=='PASS_DIV4_V10_TAIL_V1_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY'
for name,digest in record['inputs'].items():assert pin(name)['sha256']==digest
for name,digest in record['outputs'].items():assert pin(N/name)['sha256']==digest
layout=j(L/'result.json')
for name,digest in layout['input_sha256'].items():assert pin(name)['sha256']==digest
for name,digest in layout['output_sha256'].items():assert pin(L/name)['sha256']==digest
launch=j(D/'launch-manifest01.json');assert {str(p.relative_to(L)):pin(p) for p in L.rglob('*') if p.is_file()}=={str(Path(p).relative_to(L)):v for p,v in ready['closed_native_files'].items() if Path(p).is_relative_to(L)}
freeze=j(D/'source-freeze02.json');source=freeze['product_sources']
assert pin(D/'source-freeze02.json')==ready['source_freeze']
oldfreeze=j(D/'source-freeze01.json')
assert oldfreeze['product_sources']==source
assert [n for n,v in oldfreeze['inputs'].items()if freeze['inputs'].get(n)!=v]==[str(D/'freeze01.log')]
for n,v in freeze['inputs'].items():assert pin(n)==v
for n,v in source.items():assert pin(n)==v
peer=j(D/'source-only-peer01-rx.json');assert peer['findings']==[] and peer['source_pins']==source
assert peer['freeze']==pin(D/'source-freeze02.json')
assert pin(D/'source-peer-findings01-rx.json')==peer['retained_freeze_finding']
assert pin(D/'source-supplement02.json')==peer['freeze_correction']
geometry=j(N/'power-geometry.json');assert geometry['status']=='PASS_ACTUAL_TAIL115_ONE_RPPD_DELTA_BIAS8_CAP24_AND_TEN_GEOMETRY_CONTROLS'
for name,value in geometry['inputs'].items():assert pin(name)==value
assert geometry['physical_primitives']==91 and geometry['native_instances']==725 and geometry['native_vias']==634
assert geometry['power_arrays']==47 and geometry['power_straps']==8 and geometry['local_buses']==47
assert len(geometry['controls'])==10 and all(x['status']=='EXPECTED_REJECTION' for x in geometry['controls'])
assert [x['fault'] for x in geometry['controls']]==['remove_actual_hbt','remove_hbt_metal1','remove_power_via4','remove_power_straps','remove_actual_changed_mim_plate','restore_undersized_actual_mim','remove_actual_changed_resistor_body','restore_shorter_actual_pulldown','remove_actual_reference_resistor_body','restore_old_reference_length']
assert geometry['retained_layout_owners'] and not geometry['full_route_identity_claim'] and not geometry['qualified_pex']
assert geometry['changed_reference_length_um']=={'DIV__XSECOND__XBIAS':[12.7,11.5]} and geometry['unchanged_intrinsics']==90
assert geometry['retained_bias8_pulldown_names']==['DIV__XDN','DIV__XDP']
for name,length in [('DIV__XSECOND__XBIAS',11.5),('DIV__XFIRST__XCORE__XBIAS',12.7)]:
 row=next(x for x in layout['instances']if x['name']==name)
 assert row['kind']=='resistor'and row['width_um']==1 and row['length_um']==length
assert geometry['retained_cap24_mim_names']==['DIV__XCN','DIV__XCP']
for name in ['DIV__XDN','DIV__XDP']:
 row=next(x for x in layout['instances']if x['name']==name)
 assert row['kind']=='resistor'and row['width_um']==1 and row['length_um']==8
for name in ['DIV__XCN','DIV__XCP']:
 row=next(x for x in layout['instances']if x['name']==name)
 assert row['kind']=='capacitor'and row['width_um']==24 and row['length_um']==24
raw=j(B/'raw-database-read.json');assert len(raw['databases'])==16;database={x['name']:x for x in raw['databases']};outcomes=[]
positive=[];negative=[]
for step in record['steps']:
 name=step['name'];nd=N/name
 if name in ['drc','offgrid']:
  xml=ET.parse(nd/'drc.lyrdb').getroot();categories=xml.findall('./categories//category');items=xml.findall('./items/item');assert len(categories)==560
  counts=dict(collections.Counter(x.findtext('category') for x in items));assert len(items)==step['measurement']['markers'] and counts==step['measurement']['categories']
  assert 'KLayout DRC run for tables \'main\' completed' in (nd/'run.log').read_text()
  if name=='drc':assert not items;positive.append(name)
  else:assert len(items)==6 and counts['metal1_drw_Offgrid']==4;negative.append(name)
  outcomes.append(dict(name=name,categories=560,markers=len(items),marker_categories=counts));continue
 if 'audit' in step:
  d=database[name];assert pin(d['input']['path'])=={k:d['input'][k] for k in ['bytes','sha256']};assert len(d['pairs'])==1 and not d['extraction_diagnostics']
  pair=d['pairs'][0];assert pair['layout']=='nssoc_clock_div4_v10_tail_v1_layout' and pair['schematic']=='NSSOC_CLOCK_DIV4_V10_TAIL_V1_LAYOUT'
  audit=j(nd/'audit.json');assert audit==step['audit']
  for n,v in audit['inputs'].items():assert pin(n)==v
  assert audit['circuits'][0]['status']==pair['status'] and audit['circuits'][0]['layout_devices_recursive']==pair['layout_devices'] and audit['circuits'][0]['schematic_devices_recursive']==pair['schematic_devices']
  log=(nd/'deck.log').read_text();ports=re.search(r'^\.SUBCKT nssoc_clock_div4_v10_tail_v1_layout (.*)$',(nd/'extracted.cir').read_text(),re.M).group(1).split()
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
   # Independently compare every native parameter census to actual generation.
   for model,kind,count,index in [('rppd','resistor',33,4),('cap_cmim','capacitor',6,3)]:
    selected=[line.split() for line in rows if ' '+model+' ' in line];assert len(selected)==count
    measured=[]
    for fields in selected:
     parts=fields[index+1:];params=dict(v.split('=')for v in parts);assert len(parts)==len(params) and params['m']=='1'
     if model=='rppd':assert set(params)=={'w','l','ps','b','m'} and params['ps']=='0u' and params['b']=='0'
     else:assert set(params)=={'w','l','A','P','m'}
     assert all(re.fullmatch(r'[0-9]+(?:\.[0-9]+)?u',params[k]) for k in ['w','l'])
     w,length=Decimal(params['w'][:-1]),Decimal(params['l'][:-1]);assert w>0 and length>0;measured.append((w,length))
     if model=='cap_cmim':assert params['A'].endswith('p')and params['P'].endswith('u')and Decimal(params['A'][:-1])==w*length and Decimal(params['P'][:-1])==2*(w+length)
    expected=[(Decimal(str(q['width_um'])),Decimal(str(q['length_um'])))for q in layout['instances']if q['kind']==kind]
    assert collections.Counter(measured)==collections.Counter(expected)
    if model=='cap_cmim':assert measured.count((Decimal(24),Decimal(24)))==2
   selected=[line.split()for line in rows if line.startswith('Q')];nx=[]
   for fields in selected:
    assert len(fields)==10 and fields[5]=='npn13G2';parts=fields[6:];params=dict(v.split('=')for v in parts)
    assert len(params)==len(parts)==4 and params['we']=='70n'and params['le']=='900n'and params['m']=='1';nx.append(int(params['Nx']))
   assert collections.Counter(nx)==collections.Counter(q['nx']for q in layout['instances']if q['kind']=='hbt')
  else:
   assert audit['status']=='FAIL' and "ERROR : Netlists don't match" in log and 'INFO : Congratulations! Netlists match.' not in log;negative.append(name)
   if name=='clock_open':assert pair['status']=='Match' and len(ports)==6 and set(ports)==set(layout['ports'])-{'CLKP'}
   else:assert pair['status']=='NoMatch'
   physical=nd/'wrong.gds';reference=nd/'wrong.cir'
   if physical.exists():assert pin(physical)!=pin(L/'nssoc_clock_div4_v10_tail_v1_layout.gds') and step['mutation_execution']['returncode']==0
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
lef=(L/'nssoc_clock_div4_v10_tail_v1_layout.lef').read_text()
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
result=dict(reviewer='PLL independent saved-byte reviewer',status='PASS_INDEPENDENT_SAVED_TAIL115_V1_NATIVE_RESULT',findings=[],checks=pin(N/'result.json'),geometry=pin(N/'power-geometry.json'),GDS=pin(L/'nssoc_clock_div4_v10_tail_v1_layout.gds'),ready=pin(D/'native-finite-review-ready01.json'),utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),archive=dict(path=str(archive),**pin(archive)),full_member_readback=340,native_inputs_rehashed=len(record['inputs']),native_outputs_rehashed=len(record['outputs']),immutable_generated_gds=pin(L/'nssoc_clock_div4_v10_tail_v1_layout.gds'),launch_layout_files_equal=True,source_pins=source,source_peer=pin(D/'source-only-peer01-rx.json'),raw_database_read=pin(B/'raw-database-read.json'),raw_reader_execution=pin(B/'reader-execution.json'),positive_stages=positive,expected_negative_stages=negative,stage_details=outcomes,closed_native_owner_receipts=owners,scope='All21 saved standalone Tail115V1 divider native stages checked with340 archive members and195 closed raw files and16 raw LVS databases independently read through KLayout API. Raw mainDRC560categories0markers, realoffgrid6markers, deep+flat74/74and7ports;8reference+6physicalfaults plusoffgrid and2LEFfaults rejected. Clockopen xref remainsMatch but actual CLKP port is missing and strictdeck rejects; this distinction is retained. All source-test failures and additive metadata correction remain preserved. Hash-bound actualGDS audit verifies one SECOND reference rppd L12.7to11.5um delta with FIRST L12.7, both pull-down L8 and both24um MIMs retained and90unchanged intrinsic geometries at725declared placements,634nativevias,47powerarrays,8powerstraps,47localbuses and10actualgeometryfaults. Independent positive netlist census additionally checks every passive W/L, MIM area/perimeter, HBT Nx/geometry and finite body contacts. Route identity is explicitly not claimed after changed placement. Read-only database reader invoked; generation/extraction/DRC/LVS/LEF and tests were not rerun.',manufacturing_approval=False,qualified_pex=False,extracted_division=False,clockbank_integration=False,phy_complete=False,physical_acceptance=False)
p=D/'native-saved-peer-rx.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
