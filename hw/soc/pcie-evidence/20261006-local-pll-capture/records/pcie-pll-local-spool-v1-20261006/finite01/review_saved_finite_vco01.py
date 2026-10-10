# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-only streaming archive/control census. No producer import."""
import ast,collections,hashlib,json,os,resource,tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();D=Path(__file__).resolve().parent;B=D.parent
A=D/'pcie-pll-local-spool-v1-controls-and-launch-20261006.tar.xz';M=D/'members.json';V=D/'pcie-pll-local-spool-v1-controls-and-launch-validation-20261006.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def bits(e):return {k:e[k]for k in ['bytes','sha256']}
v=json.loads(V.read_text());m=json.loads(M.read_text());f=json.loads((B/'source-freeze02.json').read_text())
assert pin(A)==bits(v['archive'])and pin(M)==bits(v['members'])
assert pin(B/'source-freeze02.json')==v['source_freeze']
assert v['status']=='PASS_FULL_MEMBER_LOCAL_PLL_SPOOL_FINITE_CAPTURE'and not v['findings']
assert all(v[k]is False for k in ['native_completion','numerical_convergence','physical_acceptance'])
expected=dict(m['files']);expected['members.json']=dict(path=str(M),**pin(M));seen={};saved={};large=[]
with tarfile.open(A,'r|xz')as archive:
 for item in archive:
  assert item.isfile()and item.name in expected and item.name not in seen,item.name
  entry=expected[item.name];assert item.size==entry['bytes']
  h=hashlib.sha256();total=0;allzero=True;parts=[];small=item.size<2*1024**2
  with archive.extractfile(item)as stream:
   while chunk:=stream.read(1024**2):
    h.update(chunk);total+=len(chunk)
    if item.size>100*1024**2:allzero=allzero and chunk.count(0)==len(chunk)
    if small:parts.append(chunk)
  observed=dict(bytes=total,sha256=h.hexdigest());assert observed==bits(entry),item.name;seen[item.name]=observed
  if small:saved[item.name]=b''.join(parts)
  if item.size>100*1024**2:large.append(dict(name=item.name,bytes=item.size,all_zero=allzero))
assert set(seen)==set(expected)and len(seen)==3967
assert sum(e['bytes']for e in m['files'].values())==v['logical_data_bytes']==3132649663
assert len(large)==6 and all(e['all_zero']for e in large)
assert saved['members.json']==M.read_bytes()
for e in m['files'].values():
 p=Path(e['path'])
 assert all(not p.is_relative_to(x)for x in m['excluded_active_roots'])
 assert str(p)not in m['excluded_active_paths']
 assert pin(p)==bits(e),str(p)
for p,e in m['external_runtime_pins'].items():assert pin(p)==e
frozen=f['sources']+list(f['dependencies'].values())+f['evidence']+f['actual_fixture_files']
manifest_paths={e['path']:bits(e)for e in m['files'].values()}|m['external_runtime_pins']
for e in frozen:assert manifest_paths[e['path']]==bits(e)and pin(e['path'])==bits(e)
assert len(f['actual_fixture_files'])==3804 and len(f['sources'])==6
for p,e in v['source_allowlist'].items():assert pin(R/p)==e
campaigns=[];historical=[]
def parse_xml(path):
 path=Path(path);key=next(k for k,e in m['files'].items()if e['path']==str(path));raw=saved[key];assert raw==path.read_bytes();return list(ET.fromstring(raw).iter('testcase'))
for c in f['controls']:
 cases=parse_xml(c['xml']['path']);failed=[x for x in cases if any(y.tag in('failure','error')for y in x)];skipped=[x for x in cases if any(y.tag=='skipped'for y in x)]
 row=dict(name=c['name'],cases=len(cases),passed=len(cases)-len(failed)-len(skipped),failed=len(failed),skipped=len(skipped));assert all(row[k]==c[k]for k in ['cases','passed','failed']);campaigns.append(row)
 historical +=[dict(campaign=c['name'],name=x.attrib['name'],message='\n'.join(y.attrib.get('message','')for y in x if y.tag in('failure','error')))for x in failed]
assert campaigns==v['campaigns']and len(campaigns)==12
assert sum(x['cases']for x in campaigns)==303 and sum(x['failed']for x in campaigns)==2
current={}
for x in parse_xml(B/'complete-controls03.xml'):
 if x.attrib['classname']!='sw.tests.test_pcie_pll_local_capture_v1':current[(x.attrib['classname'],x.attrib['name'])]=x
for x in parse_xml(B/'bridge-controls05.xml'):
 key=x.attrib['classname'],x.attrib['name'];assert key not in current;current[key]=x
assert len(current)==69 and all(not list(x)for x in current.values())
counts=collections.Counter(k[0]for k in current)
assert counts=={'sw.tests.test_pcie_durable_spool_v1':30,'sw.tests.test_pcie_local_spool_publisher_v1':21,'sw.tests.test_pcie_pll_local_capture_v1':18}
for module in counts:
 p=R/(module.replace('.','/')+'.py');functions={n.name for n in ast.walk(ast.parse(p.read_text()))if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 assert all(name.split('[',1)[0]in functions for cls,name in current if cls==module)
p=B/'source-saved-peer-root02.json';peer=json.loads(p.read_text());assert pin(p)==v['aggregate_peer']and peer['freeze']==v['source_freeze']and peer['findings']==[]and peer['distinct_current_predicates']==69
p=B/'launch01/source-peer-vco01.json';support=json.loads(p.read_text());assert pin(p)==v['support_peer']and support['policy']==pin(B/'launch01/policy.json')and support['findings']==[]
assert len(v['source_allowlist'])==6
out=dict(status='PASS_INDEPENDENT_SAVED_LOCAL_PLL_SPOOL_CONTROLS_AND_LAUNCH',archive=pin(A),validation=pin(V),members=pin(M),findings=[],method=pin(__file__),readback_members=len(seen),data_members=len(m['files']),logical_data_bytes=v['logical_data_bytes'],sparse_zero_fixtures=large,source_files=6,frozen_fixture_files=3804,all_frozen_source_dependency_evidence_fixture_pins=len(frozen),campaigns=campaigns,total_executions=303,total_historical_failures=2,historical_failures=historical,current_predicates=69,current_counts=dict(counts),current_actual_xml_predicates=[dict(module=c,name=n)for c,n in sorted(current)],aggregate_peer=pin(B/'source-saved-peer-root02.json'),support_peer=pin(B/'launch01/source-peer-vco01.json'),scope='Independent stdlib streaming readback of every closed member and original file; six sparse fixtures fully hashed without allocation. Twelve actual XML campaigns and current69 source-corresponding predicates recounted; historical failures retained. Existing independent source/launch peers rebound. Active PLL/spool/publication excluded and not read. No producer import, tests, native or network rerun. Native completion, numerical convergence and physical acceptance remain false.',native_completion=False,numerical_convergence=False,physical_acceptance=False)
(D/'saved-finite-peer-vco01.json').write_text(json.dumps(out,indent=2)+'\n');print(pin(D/'saved-finite-peer-vco01.json'))
