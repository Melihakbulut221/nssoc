# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent bounded archive/hash/XML audit; never execute simulation."""
import ast,gzip,hashlib,io,json,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd(); O=Path(__file__).resolve().parent

def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}

def bp(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def j(p):return json.loads(Path(p).read_text())

def archive(p,expected):
 seen={};texts={};total=0
 with tarfile.open(p,'r|xz') as t:
  for m in t:
   assert m.isfile() and m.name not in seen and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts,m.name
   f=t.extractfile(m);h=hashlib.sha256();n=0;keep=m.size<=2*1024**2 and not m.name.endswith('.vvp');chunks=[]
   while b:=f.read(1024*1024):
    h.update(b);n+=len(b)
    if keep:chunks.append(b)
   seen[m.name]={'bytes':n,'sha256':h.hexdigest()};assert n==m.size
   if keep:texts[m.name]=b''.join(chunks);total+=n
 assert seen==expected,{'missing':list(set(expected)-set(seen)),'extra':list(set(seen)-set(expected))}
 return seen,texts,total

def publication(p,archive_path):
 d=j(p);assert d['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';a=next(a for a in d['assets'] if a['name']==archive_path.name)
 assert a['authenticated_roundtrip'] is True and a['anonymous_roundtrip'] is True
 assert pin(archive_path)=={k:a[k] for k in ('bytes','sha256')}
 return a

B=R/'hw/soc/out/pcie-strict-pcs-20261005';V=B/'root-delivery/validation.json';P=B/'root-delivery/package.json';v=j(V);p=j(P);a=Path(p['archive'])
assert pin(V)==p['validation'];assert pin(a)==p['archive_pin'];pub=publication(B/'root-delivery/release.json',a)
expected={**v['members'],'validation.json':pin(V)};members,texts,kept=archive(a,expected);assert len(members)==p['members']==818
freeze=j(B/'source-freeze.json');assert len(freeze)==10 and freeze==v['sources']
for name,h in freeze.items():assert pin(R/name)==h==members['sources/'+name]
assert j(R/'hw/soc/out/pcie-sds-deskew-20261005/native-v3/source-freeze.json')['sources']['hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v2.v']==freeze['hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v2.v']
base=(R/'hw/soc/rtl/pcie/soc_pcie_gen3_sds_deskew_v2.v').read_text();tree=ast.parse((R/'sw/tests/test_pcie_gen3_sds_deskew_v2.py').read_text())
def literal(name):return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name))
cases=literal('CASES');mutants=literal('MUTANTS');leaf=[]
for row in v['leaf']['audits']:
 name='native/'+row['path'].removeprefix('/dev/shm/');assert members[name]==row['pin'];c=json.loads(texts[name]);d=str(Path(name).parent);log=texts[d+'/run.log'].decode();assert c['returncode']==row['returncode']
 if 'nssoc-strict-sds-deskew-v2-final01/' not in name:continue
 if row['mutant']:
  key,=row['mutant'];old,new,case,diagnostic=mutants[key];assert base.count(old)==1
  assert texts[d+'/mutant.v'].decode()==base.replace(old,new)
  assert c['case']==case and c['returncode']==1 and diagnostic in log
 else:assert c['case'] in cases and c['returncode']==0 and 'PASS ' in log
 leaf.append({'case':c['case'],'mutant':row['mutant'],'native_returncode':c['returncode']})
assert sorted(r['case'] for r in leaf if not r['mutant'])==sorted(cases)
assert sorted(r['mutant'][0] for r in leaf if r['mutant'])==sorted(mutants)
packet=[]
for row in v['packet']['audits']:
 name='native/'+row['path'].removeprefix('/dev/shm/');assert members[name]==row['pin'];r=json.loads(texts[name]);d=str(Path(name).parent)
 counts=[0,0,0]
 for case in ET.fromstring(texts[d+'/results.xml']).iter('testcase'):
  if case.find('skipped') is not None:counts[2]+=1
  elif case.find('failure') is not None or case.find('error') is not None:counts[1]+=1
  else:counts[0]+=1
 assert counts==row['counts'],(name,counts,row['counts'])
 assert r['status']==row['status'] and r['exact_test']==row['exact_test']
 for output,h in r['outputs'].items():assert members[d+'/'+output]==h
 for original,h in r['inputs'].items():assert h in members.values(),(original,h)
 for path,h in r['runtime'].items():assert pin(path)==h
 packet.append({'result':name,'status':r['status'],'kind':row['kind'],'mutant':row['mutant'],'exact_test':r['exact_test'],'counts':counts})
final=[r for r in packet if '/nssoc-recovered-packet-rx-v1-controls03/' in r['result'] or '/nssoc-recovered-packet-rx-v1-controls04/' in r['result']]
assert len({r['mutant'][0] for r in final if r['mutant']})==8
assert any(r['counts']==[15,0,0] and not r['mutant'] for r in final)
assert any(r['kind']=='mutant_survived_initial_reset_oracle' for r in packet)
strict={'archive':pin(a),'publication':pub,'validation':pin(V),'members_rehashed':len(members),'current_sources_rehashed':10,'leaf_final':leaf,'packet_saved_XML_recounts':packet,'retained_text_bytes':kept,'scope':'Independent local full archive member hashes,current source pins,all saved packet XML/output/input/runtime closures and final29leaf result/mutant bytes. No fixture regeneration, HDL execution or protocol/formal/timing proof. Historical runtime pins are rechecked only where emitted by original top producer; direct leaf runtime inventory is not retroactively invented.'}
# Own separately mapped campaign: second complete archive pass and full gz payload replay.
B=R/'hw/soc/out/pcie-sds-deskew-20261005/native-v3';V=B/'validation.json';v=j(V);a=Path(v['archive']['path']);pub=publication(B/'publication.json',a);assert pin(a)=={k:v['archive'][k] for k in ('bytes','sha256')}
m,t,kept=archive(a,v['members']);r=json.loads(t['native/result.json']);assert r['status']=='PASS_NATIVE_GEN3_STRICT_SDS_COHORT_DESKEW'
assert len(r['cases'])==29 and len(r['maps'])==11 and len(r['closed_vvp_preservation'])==29
replayed=[]
for row in r['closed_vvp_preservation']:
 name='native/'+str(Path(row['compressed_path']).relative_to('/dev/shm/nssoc-sds-deskew-native-v3-01'));assert m[name]==row['compressed']
 with gzip.GzipFile(fileobj=io.BytesIO(t[name])) as f:
  h=hashlib.sha256();n=0
  while b:=f.read(1024*1024):h.update(b);n+=len(b)
 q={'bytes':n,'sha256':h.hexdigest()};assert q==row['raw']==row['full_decompressed_readback'];replayed.append({'member':name,**q})
for name,h in r['source_pins'].items():assert pin(name)==h
for name,h in r['runtime'].items():assert pin(name)==h
native={'archive':pin(a),'publication':pub,'validation':pin(V),'members_rehashed':len(m),'compiled_payload_replays':replayed,'retained_text_bytes':kept,'scope':'Additive author-owned archive and29 full gzip payload audit; not an independent new native execution.'}
result={'status':'PASS_BOUNDED_LOCAL_STRICT_PCS_AND_NATIVE_ARCHIVE_AUDIT','strict_root_independent':strict,'strict_native_author_additive':native,'review_method':pin(Path(__file__)),'limitations':['No new network download: exact local capsules match immutable public dual-roundtrip receipt digests.','No simulator, solver, PDK timing or analog process launched.','Incomplete/full-PCS/LTSSM/physicalCDC/main-chip acceptance remains open.']}
(O/'archive-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(pin(O/'archive-audit.json'));print('strict818 native465,29gzip payloads,packetXML',len(packet))
