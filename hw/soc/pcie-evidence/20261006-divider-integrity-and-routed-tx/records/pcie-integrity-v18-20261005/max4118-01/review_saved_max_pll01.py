# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent completed MAX4118 archive/XML/native-byte recount; no HDL run."""
from pathlib import Path
import json,hashlib,tarfile,xml.etree.ElementTree as ET,re,datetime
B=Path(__file__).resolve().parent;C=B/'recovery02';R=B.parents[4]
W=Path('/dev/shm/nssoc-integrity-v18-max4118-01');L=Path('/dev/shm/nssoc-integrity-v18-max4118-lifecycle01')
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def load(p):return json.loads(Path(p).read_text())
def counts(cases):return {'passed':sum(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in cases),'failed':sum(any(c.find(t) is not None for t in ['failure','error']) for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases)}
archive=B/'pcie-integrity-v18-max4118-complete-20261005.tar.xz';validation=B/'pcie-integrity-v18-max4118-validation-20261005.json';package=B/'pcie-integrity-v18-max4118-package-20261005.json'
assert pin(archive)=={'bytes':4551672,'sha256':'7b87849f550da76c1a3983f5b88077bdef58d81463f297dd768ea6de549fce80'}
v=load(validation);p=load(package);assert pin(archive)==p['archive'] and pin(validation)==p['validation'];assert v['member_count']==len(p['members'])==127
readbacks={};small={};actual_paths=0
with tarfile.open(archive,'r:xz') as t:
 assert len(t.getmembers())==127 and {x.name for x in t}==set(p['members'])
 for m in t:
  assert m.isfile() and not m.issym() and not m.islnk()
  with t.extractfile(m) as f:h={'bytes':m.size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
  assert h==p['members'][m.name];readbacks[m.name]=h
  if m.name in ['member-pins.json','review.json']:small[m.name]=json.load(t.extractfile(m));continue
  prefix,rel=m.name.split('/',1);base={'functional':W,'lifecycle-controls':L,'method':B,'recovery':C,'source':R}[prefix]
  assert pin(base/rel)==h,(m.name,str(base/rel));actual_paths+=1
assert small['member-pins.json']=={k:h for k,h in p['members'].items() if k!='member-pins.json'}
assert all(v[k]==val for k,val in small['review.json'].items())
s=load(C/'status.json');assert s['status']=='COMPLETE_TWO_PROFILES_XML_VERIFIED_REQUIRES_RECOVERY_AWARE_SEAL';assert not s['current_external'] and not s['current_owned'] and not s['stop_reason']
assert s['old_controller_abruptly_lost'] and not s['original_parent_wait_status_recoverable']
assert v['controller_status']==pin(C/'status.json') and v['method']==pin(C/'seal.py')
policy=load(B/'policy.json');rp=load(C/'policy.json');assert s['policy']==v['recovery_policy']==pin(C/'policy.json')
for q in [policy,rp]:
 for path,h in q['pins'].items():assert pin(path)==h,path
runtime=load(B/'runtime-targets-observed01.json')
for path,h in runtime['files'].items():assert pin(path)==h
closed=[]
for ident in rp['adopted_births']+rp['lost_controllers']+[s['controller'],s['miter_identity']]:
 q=Path('/proc')/str(ident['pid'])/'stat'
 if q.exists():
  a=q.read_text().rsplit(') ',1)[1].split();assert a[19]!=str(ident['start_ticks']) or a[0]=='Z'
 closed.append(ident)
owner=load(C/'owner.json');assert owner['status']=='HEALTHY' and not owner['reason'] and len(owner['processes'])==1
owned=owner['processes'][0];assert owned['returncode']==0 and owned['status']=='REAPED_NO_LIVE_MEMBERS' and not owned['members_at_leader_exit']
rows=[]
for stage in s['stages']:
 name=stage['name'];hpath=Path(stage['helper_result']['path']);h=load(hpath)
 assert stage['helper_result']=={'path':str(hpath),**pin(hpath)}
 assert h['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX' and h['mode']=='rtl'
 assert h['max_encoded_bytes']==4118 and h['minimum_packet_ring_dwords']==2048 and h['address_space_limit_bytes']==2*1024**3
 assert h['exact_test_selection'] is None and h['expected_tests']==13
 for path,hsh in {**h['inputs'],**h['runtime']}.items():assert pin(path)==hsh,path
 for rel,hsh in h['outputs'].items():assert pin(hpath.parent/rel)==hsh
 cases=list(ET.parse(hpath.parent/'results.xml').iter('testcase'));assert len(cases)==len({c.attrib['name'] for c in cases})==13
 names=[c.attrib['name'] for c in cases];assert counts(cases)==h['tests']==stage['actual_cocotb_counts']=={'passed':13,'failed':0,'skipped':0}
 assert names==stage['actual_cocotb_names'];assert all(float(c.attrib['sim_time_ns'])>0 and float(c.attrib['time'])>0 for c in cases)
 py=B/(name+'-pytest.xml');pcs=list(ET.parse(py).iter('testcase'));assert len(pcs)==1 and counts(pcs)=={'passed':1,'failed':0,'skipped':0} and '4118' in pcs[0].attrib['name']
 assert stage['pytest_xml']=={'path':str(py),**pin(py)}
 command=h['commands'];assert len(command)==1 and command[0]['returncode']==0 and 'PCIE_WIDE_MAX_BYTES=4118' in command[0]['argv'] and 'PCIE_NATIVE=0' in command[0]['argv']
 assert command[0]['log_pin']==pin(hpath.parent/'simulation.log')
 log=(hpath.parent/'simulation.log').read_text();assert 'TESTS=13 PASS=13 FAIL=0 SKIP=0' in log
 binary=hpath.parent/'sim/sim.vvp';raw=binary.read_text();params={}
 for param,value in [('MAX_ENCODED_BYTES',4118),('RING_DWORDS',2048)]:
  matches=re.findall(r'\.param/l "'+param+r'"[^\n]*\+C4<([01]+)>',raw);assert len(matches)==(2 if name=='direct' else 5) and all(int(x,2)==value for x in matches);params[param]={'instances':len(matches),'value':value}
 if name=='direct':assert stage['returncode'] is None and stage['returncode_provenance']=='unavailable_non_child_orphan'
 else:
  assert stage['returncode']==0 and stage['returncode_provenance']=='waited_owned_child'
  scope=load(hpath.parent/'miter-scope.json');assert scope['status']=='PASS_THIRTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES' and scope['maximum']==4118 and len(scope['outputs'])==17
  for path,hsh in scope['source_pins'].items():assert pin(R/path)==hsh
  wrapper=hpath.parent.parent/'miter-rtl/soc_pcie_gen3_continuous_rx_integrity_v18.v';txt=wrapper.read_text()
  for filename in ['soc_pcie_gen3_continuous_rx_integrity_v11.v','soc_pcie_gen3_framer_rx_integrity_v11.v','soc_pcie_gen3_ingress.v']:assert (R/'hw/soc/rtl/pcie'/filename).read_text() in txt
  for diagnostic in ['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','PCIE_COMMITTED_SLOT_VERDICT_MISMATCH','PCIE_INGRESS_CONTROL_MISMATCH','PCIE_PREDECODE_COMPANION_MISMATCH']:assert diagnostic in txt and diagnostic in raw
  gate='{'+','.join(scope['outputs'])+'}';gold='{'+','.join('gold_'+x for x in scope['outputs'])+'}';assert gate+' !== '+gold in txt
 rows.append({'name':name,'helper':pin(hpath),'cocotb_xml':pin(hpath.parent/'results.xml'),'pytest_xml':pin(py),'counts':counts(cases),'case_names':names,'simulated_ns':sum(float(c.attrib['sim_time_ns']) for c in cases),'compiled_vvp':pin(binary),'actual_compiled_parameters':params,'returncode':stage['returncode'],'returncode_provenance':stage['returncode_provenance']})
preservation=load(C/'preservation-status.json');assert preservation['status']=='COMPLETE_PUBLIC_CAPTURE_FINITE_DELIVERY_REVIEW_REQUIRED' and not preservation['stop_reason']
assert [(x['name'],x['returncode']) for x in preservation['stages']]==[('seal',0),('publish',0)]
assert preservation['release']==pin(B/'release.json');release=load(B/'release.json');assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(release['assets'])==3
for a in release['assets']:
 assert a['authenticated_roundtrip'] and a['anonymous_roundtrip'] and {k:a[k] for k in ['bytes','sha256']}==pin(B/a['name'])
files=[archive,validation,package,B/'release.json',B/'policy.json',B/'runtime-targets-observed01.json',C/'status.json',C/'policy.json',C/'owner.json',C/'preservation-status.json',Path(__file__)]
r={'status':'PASS_INDEPENDENT_SAVED_V18_MAX4118_DIRECT_AND_MITER','utc':datetime.datetime.now(datetime.UTC).isoformat(),'findings':[],'inputs':{str(x):pin(x) for x in files},'archive_members_checked':127,'all_nonembedded_original_files_rehashed':actual_paths,'complete_member_pins':readbacks,'rows':rows,'all_runtime_and_original_recovery_pins_rehashed':True,'closed_births':closed,'public_assets':release['assets'],'direct_parent_wait_code_unavailable_not_fabricated':True,'miter_actual_owned_wait_exit0':True,'source_method':'Independent stdlib full archive hashes, original source/output/runtime pins, actual raw pytest/cocotb XML and compiledVVP parameter readback, complete public output compare and stored-owner witnesses. No producer imports, no simulation/test/native reruns.','scope':'Actual V18 RTL MAX4118/ring2048 direct scalar oracle and V11/V18 cycle miter each13cases pass. Does not validate mappedMAX4118 timing, laterV19..V24 MAX4118, full formal/PHY/chip integration or manufacturing.'}
out=B/'saved-native-peer-pll01.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(out))
