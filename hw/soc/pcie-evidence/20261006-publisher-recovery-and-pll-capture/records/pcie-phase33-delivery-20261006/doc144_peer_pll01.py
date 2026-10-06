from pathlib import Path
import hashlib,json,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=R/'hw/soc/out/pcie-phase33-delivery-20261006';P=R/'hw/soc/out/publisher-reconciliation-20261006';C=R/'hw/soc/pcie-evidence/20261006-publisher-recovery-and-pll-capture';D=R/'docs/144-pcie-publication-recovery-and-incomplete-pll.md'
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_text())
def check(p,v):assert pin(p)=={k:v[k] for k in ('bytes','sha256')},str(p)
I=load(C/'delivery-inventory.json')
assert len(I['sources'])==2 and len(I['files'])==35 and len(I['archives'])==2 and len(I['public_assets'])==5
for p,v in I['sources'].items():check(p,v)
for p,v in I['files'].items():check(C/p,v);check(R/v['source'],v)
for p in I['sidecars']:assert (C/p).is_file()
control=load(P/'pcie-publisher-v4-native-controls-validation-20261006.json')
terminal=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01/terminal-members09.json'
maps=[control['members'],load(terminal)]
counts=[]
for a,records in zip(I['archives'],maps):
 check(a['path'],a)
 with tarfile.open(a['path'],'r|xz') as t:
  seen=set()
  for member in t:
   assert member.isfile() and member.name not in seen;seen.add(member.name)
   data=t.extractfile(member).read()
   if member.name=='members.json':assert json.loads(data)==records
   else:
    v=records[member.name];assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:v[k]for k in ('bytes','sha256')}
    check(v.get('original_path',v.get('original')),v)
  assert seen==set(records)|({'members.json'} if 'members.json' not in records and len(seen)>len(records) else set())
  assert len(seen)==a['members'];counts.append(len(seen))
assert counts==[312,2392] and sum(counts)==I['members']==2704
receipts=[load(P/n) for n in ('closed-captures-release01.json','recovered-part120-release01.json')]
assert all(r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'for r in receipts)
assets=sum((r['assets'] for r in receipts),[]);assert assets==I['public_assets']
for a in assets:
 assert a['authenticated_roundtrip'] is True and a['anonymous_roundtrip'] is True
 matches=[f for r in receipts for f in r['files'] if f['name']==a['name']];assert len(matches)==1
 check(matches[0]['path'],a)
assert assets[-1]['asset_id']==614632793 and assets[-1]['bytes']==13509560 and assets[-1]['sha256']=='1438044b6cbf5f301fec01c5e159c1ac651e3d30085d2666a702e065415b98e7'
diag=load(P/'diagnosis01.json')
for p,v in diag['input_pins'].items():check(p,v)
assert diag['upload_returncode']==-15 and diag['upload_deadline_seconds']==120 and round(diag['upload_elapsed_seconds'],3)==120.129
assert diag['complete_live_asset_count']==743 and diag['complete_live_pages']==8 and not diag['pagination_failure_observed'] and not diag['successful_upload_observed']
raw=Path('/dev/shm/nssoc-pll-acquisition-v4-max125-01')
result=load(raw/'result.json');execution=load(raw/'execution.json')
assert result['status']==I['original_PLL_result']=='ERROR_NATIVE_OR_STREAM_CAPTURE' and execution['returncode']==-15
preserved=load(P/'pcie-pll-max125-publication120-failure-validation-20261006.json')
assert preserved['last_actual_simulation_seconds']==383.288e-9 and preserved['original_public_completed_parts']==120
xml=ET.parse(P/'controls02.xml').getroot();cases=list(xml.iter('testcase'))
assert len(cases)==15 and not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped'))
assert '15 passed in 4.11s' in (P/'controls02.log').read_text() and 'All checks passed!' in (P/'ruff01.log').read_text()
peer=load(P/'source-saved-peer-pll01.json')
text=D.read_text()
for phrase in ['383.288 ns','2,704 members','2,392 members','13,509,560 bytes','614632793','743','eight-page','4.11 seconds','61 owned-child records','312 members','Partial raw data is not a','time zero','remain\nopen']:
 assert phrase in text,phrase
assert not I['full_phy_acceptance'] and not I['full_chip_final_timing_accepted'] and not I['production_acceptance']
out=dict(status='PASS_INDEPENDENT_DOC144_AND_FINITE_INVENTORY',document=dict(path=str(D),**pin(D)),inventory=dict(path=str(C/'delivery-inventory.json'),**pin(C/'delivery-inventory.json')),sources=2,compact_records=35,archives=counts,full_members_rehashed=2704,public_assets=5,actual_publisher_controls=15,upload_returncode=-15,upload_elapsed_s=diag['upload_elapsed_seconds'],last_native_ns=383.288,native_status=result['status'],findings=[],method=dict(path=__file__,**pin(__file__)),scope='Independent full document and source/compact/full-member bytes readback, saved actual XML/diagnostic/publication receipts. No controls/native/network rerun. Incomplete PLL and exact original failed receipts preserved; no numerical or physical closure.')
(B/'doc144-peer-pll01.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
