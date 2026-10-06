# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent stdlib readback of saved native boot, no producer/EDA imports."""
from pathlib import Path,PurePosixPath
import hashlib,itertools,json,re,stat,tarfile,zipfile
R=Path.cwd();B=Path(__file__).resolve().parent
START=R/'hw/soc/out/npu-init-delivery-20261006/cloud-recovery-startup01/result.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def bytepin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert pin(START)['sha256']=='be525d10014f55f055861eb7971a44cea8e86e7924644a110485e6861010aa7e'
startup=json.loads(START.read_text());api=json.loads((B/'run01.json').read_text());asset=json.loads((B/'artifact01.json').read_text());ready=json.loads((B/'readiness01.json').read_text())
assert api['id']==37403350883 and api['head_sha']=='c82d1280052c0da65281d87cda9af3b1c6177291' and api['run_attempt']==1 and api['status']=='completed' and api['conclusion']=='success'
assert asset['id']==11388653346 and asset['name']=='npu-init-eco-final-1' and asset['workflow_run']['id']==api['id'] and asset['workflow_run']['head_sha']==api['head_sha'] and not asset['expired']
assert pin(B/'final01.zip')==dict(bytes=15941823,sha256='329168d2296c77f92587f3d4baa6c5924eb9944300f1be6fb3529500ff6ef6cf')==dict(bytes=asset['size_in_bytes'],sha256=asset['digest'][7:])
qualification=R/'docs/evidence/alu-qualification-input-20261002.tar.xz'
assert pin(qualification)=={k:startup['qualification_inputs'][k]for k in ('bytes','sha256')}
with tarfile.open(qualification)as t:
 qual={m.name:t.extractfile(m).read()for m in t.getmembers()if m.isfile()}
with zipfile.ZipFile(B/'final01.zip')as z:
 names=z.namelist();assert len(names)==len(set(names));files=[i for i in z.infolist()if not i.is_dir()]
 assert sum(i.file_size for i in files)<2*1024**3
 for i in z.infolist():
  p=PurePosixPath(i.filename);assert not p.is_absolute()and '..'not in p.parts and '\\'not in i.filename and not stat.S_ISLNK(i.external_attr>>16)
 row=json.loads(z.read('result.json'));assert z.read('result.json')==(B/'result.json').read_bytes()
 assert set(row['outputs'])|{'result.json'}=={i.filename for i in files}
 members={}
 for i in files:
  with z.open(i)as f:p=dict(bytes=i.file_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
  if i.filename!='result.json':assert p==row['outputs'][i.filename],i.filename
  members[i.filename]=p
 for k in startup.keys()-{'status','scope','outputs'}:assert row[k]==startup[k],k
 for k,v in startup['outputs'].items():assert row['outputs'][k]==v,k
 assert row['status']=='PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY'
 assert row['github_source_commit']==api['head_sha'] and row['memory']=='vendor' and row['variant']=='candidate' and row['cycle_bound']==3000000
 for k in ('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted'):assert row[k]is False
 assert row['compile']['returncode']==row['boot_execution']['returncode']==0 and row['boot_execution']['command']==row['boot_command']
 assert row['outputs']['compiled/factored.vvp']==row['compiled_simulation'] and row['outputs']['compiled/original.vvp']==row['original_compiled_simulation']
 old=row['original_sources'];new=row['sources'];removed=set(old)-set(new);added=set(new)-set(old)
 assert len(removed)==len(added)==1
 assert next(iter(removed))==row['eco']['original_netlist_path'] and next(iter(added)).endswith('/eco/soc_top.netlist.v')
 assert all(old[k]==new[k]for k in old.keys()&new.keys())
 cmd=list(row['original_compile']['command']);cmd[cmd.index(next(iter(removed)))]=next(iter(added));cmd[cmd.index(row['original_compiled_simulation_path'])]=row['compiled_simulation_path'];assert cmd==row['compile']['command']
 actual_sources={}
 for path,expected in row['sources'].items():
  if '/inputs/'in path:
   n=path.split('/inputs/',1)[1];actual=bytepin(qual[n])
  else:
   n=path.split('/npu-init-eco/',1)[1];actual=members[n]
  assert actual==expected,path;actual_sources[path]=dict(member=n,**actual)
 assert members['eco/soc_top.netlist.v']==row['eco']['candidate']==ready['mapped_bridge']['factored_vendor_netlist']
 mapping=json.loads((R/'hw/soc/out/npu-eco-mapping-20261006/source-freeze01.json').read_text())
 original=Path(mapping['netlists']['candidate']).read_text();factored=z.read('eco/soc_top.netlist.v').decode()
 assert bytepin(original.encode())==row['eco']['original'] and original.count(row['eco']['original_gate'])==original.count(row['eco']['retained_predecessor'])==1
 assert original.replace(row['eco']['original_gate'],row['eco']['replacement'])==factored
 methods={}
 for n,v in row['methods'].items():
  assert members['methods/'+n]==v,n;methods[n]=v
 raw=z.read('boot.log');assert raw==(B/'boot.log').read_bytes();log=raw.decode()
 assert re.findall(r'(?m)^QUALIFICATION_MBIST PASS cycles=(\d+)$',log)==['983043']
 assert re.findall(r'(?m)^LOGICROM_GL PASS checks=(\d+)$',log)==['28']
 terminal=re.findall(r'(?m)^LOGICROM_GL cycles=(\d+) checks=(\d+) fails=(\w+) code=(\w+) magic=(\w+) watchdog=(\d+)/(\d+)/(\d+) flash_violations=(\d+) uart_pass=(\d+) framing=(\d+)$',log)
 assert terminal==[('1596123','28','00000000','00000000','600dc0de','1','0','0','0','1','0')]
 assert not re.search(r'(?im)(?:\bFATAL:|\bERROR:|Assertion failed|%Fatal|%Error)',log)
 # Progress prefixes bind actual continuously growing boot output, not only banners.
 progress=[]
 for n in sorted(k for k in members if k.startswith('progress/')):
  p=json.loads(z.read(n));prefix=raw[:p['log_prefix']['bytes']];assert bytepin(prefix)==p['log_prefix'] and p['raw_marker']in prefix.decode() and p['compiled_simulation']==row['compiled_simulation'];progress.append(p['cycle'])
 assert progress==list(range(10000,1590001,10000))
 # Independently recompute primitive four-state truth tables from raw outputs.
 def inv(a):return '1'if a=='0'else '0'if a=='1'else 'x'
 def land(*a):return '0'if '0'in a else '1'if all(x=='1'for x in a)else 'x'
 def lor(*a):return '1'if '1'in a else '0'if all(x=='0'for x in a)else 'x'
 def mux(s,a,b):return a if s=='0'else b if s=='1'else a if a==b else 'x'
 controls={}
 for variant in ('factored','miswired_mux'):
  text=z.read('native-controls/'+variant+'/run.log').decode();cases=re.findall(r'(?m)^CASE (\d+) inputs=([01xz]{4}) original=([01xz]) candidate=([01xz])$',text)
  assert len(cases)==256 and [int(x[0])for x in cases]==list(range(256))
  assert [x[1]for x in cases]==[''.join(v)for v in itertools.product('01xz',repeat=4)]
  mismatches=[];defined=0
  for idx,bits,g,h in cases:
   a,b,c,d=bits;expected_g=inv(land(lor(a,b),inv(land(a,c,d))));expected_h=mux(a,inv(b),land(c,d)if variant=='factored'else inv(b))
   assert(g,h)==(expected_g,expected_h),(variant,idx,g,h,expected_g,expected_h)
   if g in '01':defined+=1
   if set(bits)<={'0','1'}and g!=h:mismatches.append(int(idx))
  assert defined==78 and mismatches==([]if variant=='factored'else[64,65,68,85])
  assert cases[133]==('133','x011','x','1')
  controls[variant]=dict(vectors=len(cases),binary_mismatch_cases=mismatches,original_defined_vectors=defined,reconvergence_case=cases[133])
 bench=z.read('tb_qualification_boot.v').decode()
 # Actual critical termination and MBIST gates; no SRAM/ROM preload primitive.
 uncommented=re.sub(r'//[^\n]*|/\*.*?\*/','',bench,flags=re.S)
 assert not re.search(r'\bforce\b|\$readmem',uncommented)
 for term in ["ram_word(`CHECKS_ADDR)!==32'd28",'ram_word(`FAILS_ADDR)!==0','wdog_stage1!=1','u_flash0.violations!=0','saw_double_fault',"dut.eth_mbist_done_o !== 2'b11","dut.mbist_busy_o !== 1'b0"]:assert term in bench,term
 assert 'NATIVE_CELL_GATE PASS'in z.read('native-cell-gate/run-0.log').decode()
 assert row['native_cell_gate']['passed'] and row['native_cell_gate']['library_sha256']==row['eco']['native_controls']['model_sha256']==bytepin(qual['models/sg13g2_stdcell.v'])['sha256']
 assert ready['status']=='READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY' and ready['strict_boot']['archive']==pin(B/'final01.zip') and ready['strict_boot']['api_run']==pin(B/'run01.json') and ready['strict_boot']['api_artifact']==pin(B/'artifact01.json')
 receipt=dict(status='PASS_INDEPENDENT_SAVED_STRICT_NPU_ECO_BOOT_AND_MBIST',findings=[],archive=pin(B/'final01.zip'),api_run=pin(B/'run01.json'),api_artifact=pin(B/'artifact01.json'),result=pin(B/'result.json'),raw_boot_log=pin(B/'boot.log'),readiness=pin(B/'readiness01.json'),startup=pin(START),qualification_archive=pin(qualification),method=pin(__file__),full_readback=dict(file_members=len(members),uncompressed_bytes=sum(p['bytes']for p in members.values()),members=members),source_model_firmware_inputs=actual_sources,method_pins=methods,unchanged_startup_fields=True,exact_two_compile_argument_changes=True,full_netlist_single_gate_inverse=True,boot_observations=dict(completed_cycles=1596123,firmware_checks=28,fail_mask=0,exit_code=0,exit_magic='600dc0de',watchdog=[1,0,0],flash_violations=0,uart_pass=True,uart_framing_errors=0,system_and_ethernet_MBIST_cycle=983043,progress_prefixes_verified=len(progress)),independent_native_truth_recount=controls,native_or_test_rerun=False,scope='Exact saved four-state Icarus/native IHP/vendor SRAM-model boot plus public firmware/MBIST checks. API digest, every archive byte, unchanged startup/model/firmware/compiled inputs and raw critical qualification gates independently re-established. Not SDF/transistor SRAM proof, physical timing, final SoC/PHY or manufacturing acceptance; source-pinned reviewed physical experiment only.')
 p=B/'saved-boot-peer-pll01.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],pin(p),'members',len(members),'cycles',1596123)
