#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Locate saved native instruction pointers without restoring or executing OpenROAD."""
import argparse,copy,hashlib,json,os,re,struct,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-saved-ip'
METHOD='scripts/mainchip-saved-ip-methods.json'
RUN=40120760532
HEAD='84b513cb437b68af0f4cb22bc4707db1a35958cf'
SUMMARY='1e21e2c65b9264727bd6abd502da805023b53c1e3a0d943aba8743c072ebc0c2'
PARTS='1cd467372d2b8629169f2d77290164a611a844ebfc61e5fc486aa68b1a8c36d1'
CRIU='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
ELF='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
GROUP='mainchip-route12-observed'
IMAGE='sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8'
ELF_PATH='/nix/store/qqz49dx8dpx4q9i5wriif091n7iaa0ld-openroad-2026-02-17/bin/.openroad-wrapped'
FLAGS=dict(native_process_restored=False,native_process_started=False,route_progress_proven=False,
 routing_complete=False,normal_continuation_accepted=False,final_timing_complete=False,full_phy_accepted=False)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def uint(v):
 assert type(v)is int and 0<=v<2**64
 return v
def locate(core,mm,files):
 assert core['mtype']in(1,'X86_64')
 regs=core['thread_info']['gpregs'];ip=uint(regs['ip'])
 uint(regs['sp']);uint(regs['bp'])
 vmas=mm['vmas'];assert vmas
 ordered=sorted(vmas,key=lambda v:uint(v['start']))
 for i,v in enumerate(ordered):
  assert uint(v['start'])<uint(v['end'])
  uint(v['pgoff']);uint(v['shmid']);uint(v['prot'])
  if i:assert ordered[i-1]['end']<=v['start']
 hits=[v for v in ordered if v['start']<=ip<v['end']]
 assert len(hits)==1
 v=hits[0];assert v['prot']&4,'Instruction is not in an executable VMA'
 matches=[f for f in files if f['id']==v['shmid']and f.get('type')in(1,'REG')]
 assert len(matches)==1
 f=matches[0];assert f['reg']['id']==f['id']
 name=f['reg']['name'];p=Path(name)
 assert p.is_absolute()and '..'not in p.parts and str(p)==name and name.startswith('/nix/store/')
 offset=uint(ip-v['start']+v['pgoff'])
 return dict(registers=regs,vma=v,file=f,file_offset=offset,path=name,
  interpretation='One saved instruction location only; not a sampled profile, stack trace, progress or root-cause proof.')
def elf_address(path,offset):
 uint(offset)
 with Path(path).open('rb')as f:
  h=f.read(64);assert len(h)==64 and h[:7]==b'\x7fELF\x02\x01\x01'
  vals=struct.unpack('<16sHHIQQQIHHHHHH',h)
  _,kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,*_=vals
  assert kind in(2,3)and machine==62 and version==1 and ehsize==64 and phsize==56 and 0<phnum<1024
  f.seek(0,2);length=f.tell();assert phoff+phnum*phsize<=length
  rows=[]
  for i in range(phnum):
   f.seek(phoff+i*phsize);p=struct.unpack('<IIQQQQQQ',f.read(phsize))
   typ,flags,off,va,pa,fs,ms,align=p
   if typ==1 and flags&1 and off<=offset<off+fs:
    assert off+fs<=length and fs<=ms
    rows.append(dict(elf_type=kind,machine=machine,program_header_index=i,file_offset=offset,
     segment_file_offset=off,segment_virtual_address=va,elf_virtual_address=uint(va+offset-off)))
  assert len(rows)==1,'Instruction file offset does not map to exactly one executable PT_LOAD'
  return rows[0]
def methods():
 m=json.loads((ROOT/METHOD).read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 return m
def controls():
 import tempfile
 core=dict(mtype='X86_64',thread_info=dict(gpregs=dict(ip=0x501010,sp=0x90000,bp=0x90080)))
 mm=dict(vmas=[dict(start=0x501000,end=0x502000,pgoff=0x1000,shmid=7,prot=5)])
 files=[dict(id=7,type='REG',reg=dict(id=7,name='/nix/store/test/bin/native'))]
 p=locate(core,mm,files);assert p['file_offset']==0x1010
 rejected=[]
 faults=[('outside',lambda c,m,f:c['thread_info']['gpregs'].update(ip=0x503000)),
 ('end-exclusive',lambda c,m,f:c['thread_info']['gpregs'].update(ip=0x502000)),
 ('negative-ip',lambda c,m,f:c['thread_info']['gpregs'].update(ip=-1)),
 ('missing-sp',lambda c,m,f:c['thread_info']['gpregs'].pop('sp')),
 ('nonexec',lambda c,m,f:m['vmas'][0].update(prot=3)),
 ('overlap',lambda c,m,f:m['vmas'].append(copy.deepcopy(m['vmas'][0]))),
 ('missing-file',lambda c,m,f:f.clear()),
 ('duplicate-file',lambda c,m,f:f.append(copy.deepcopy(f[0]))),
 ('wrong-reg-id',lambda c,m,f:f[0]['reg'].update(id=8)),
 ('unsafe-file',lambda c,m,f:f[0]['reg'].update(name='/nix/store/../other')),
 ('negative-offset',lambda c,m,f:m['vmas'][0].update(pgoff=-1)),
 ('overflow-offset',lambda c,m,f:m['vmas'][0].update(pgoff=2**64-1)),
 ('wrong-arch',lambda c,m,f:c.update(mtype='ARM'))]
 for label,edit in faults:
  c,m,f=copy.deepcopy((core,mm,files));edit(c,m,f)
  try:locate(c,m,f)
  except(AssertionError,KeyError):rejected.append(label)
  else:raise AssertionError('Accepted '+label)
 # Independent ELF fixture with nonzero file offset and unequal VMA/ELF base.
 with tempfile.TemporaryDirectory()as td:
  path=Path(td)/'fixture.elf'
  hdr=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+bytes(9),3,62,1,0,64,0,0,64,56,1,0,0,0)
  ph=struct.pack('<IIQQQQQQ',1,5,0x1000,0x401000,0,64,64,4096)
  original=hdr+ph+bytes(0x1000-len(hdr)-len(ph))+bytes(range(64));path.write_bytes(original)
  assert elf_address(path,p['file_offset'])['elf_virtual_address']==0x401010
  for label,b,off in [('elf-magic',b'BAD!'+original[4:],0x1010),('elf-truncated',original[:-32],0x1010),
   ('elf-nonexec',hdr+struct.pack('<IIQQQQQQ',1,4,0x1000,0x401000,0,64,64,4096)+original[120:],0x1010),
   ('elf-outside',original,0x1040),('elf-negative',original,-1)]:
   path.write_bytes(b)
   try:elf_address(path,off)
   except(AssertionError,struct.error):rejected.append(label)
   else:raise AssertionError('Accepted '+label)
 assert len(rejected)==18
 return dict(status='PASS_SYNTHETIC_SAVED_IP_MAPPING_CONTROLS',faults=rejected,positive_file_offset=0x1010,
  positive_elf_virtual_address=0x401010,**FLAGS)
def run():
 from pycriu import images
 import compare_cloud_routed_endpoints as reports
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 m=methods();assert m['readback_authorized']is True
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],**FLAGS)
 owned=None
 try:
  source=api('actions/runs/'+str(RUN))
  assert source['head_sha']==HEAD and source['run_attempt']==1 and source['status']=='completed'and source['conclusion']=='success'
  assert source['path']=='.github/workflows/mainchip-observed-diagnostic-cloud.yml'
  release=api('releases/422907570')
  assert release['tag_name']=='cloud-results-40120760532-1-'+GROUP
  assert api('git/ref/tags/'+release['tag_name'])['object']['sha']==HEAD
  criu_root=Path(os.environ['NSSOC_CRIU_SOURCE'])
  assert subprocess.check_output(['git','-C',str(criu_root),'rev-parse','HEAD'],text=True).strip()==CRIU
  result['criu_source_commit']=CRIU
  selected=['inner-controller-result.json','current-inputs-before.json','current-inputs-after.json']
  # Explicit published paths; never substitute the original rejected capsule.
  published=json.loads((ROOT/'docs/evidence/mainchip-observed-native-result-20261024.json').read_text())
  assert sha(ROOT/'docs/evidence/mainchip-observed-native-result-20261024.json')==SUMMARY
  image_names=['core-1.img','core-7.img','core-8.img','core-9.img','mm-1.img','files.img','pstree.img']
  for name in image_names:
   matches=[p for p in published['outputs']if p.startswith('checkpoints/')and p.endswith('/'+name)]
   assert len(matches)==1,(name,matches)
   assert published['outputs'][matches[0]]==published['new_saved_process_images'][name]
   selected.append(matches[0])
  saved,proof=reports.restore_report(GROUP,RUN,SUMMARY,PARTS,OUT/'saved',selected)
  assert saved==published
  assert saved['status']=='PASS_IDENTITY_BOUND_PROCESS_DIAGNOSIS_NOT_ROUTING_OR_CONTINUATION'
  assert saved['expected_rejection']['original_no_log_progress_rejection_reproduced']
  assert not saved['routing_complete']and not saved['continuation_accepted']
  inner=json.loads((OUT/'saved/inner-controller-result.json').read_text())
  assert inner['status']=='FAIL_OR_ERROR'and inner['native_process_saved']and inner['native_log']['single_entrypoint']
  assert inner['checkpointed_elf_sha256']==ELF and inner['image_id']==IMAGE
  assert inner['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
  assert inner['retained_timing_contract']['derating_percent']==5
  result['saved_capsule']=proof;result['original_failure_retained']=True
  decoded={}
  for name in image_names:
   rel=next(p for p in selected if p.endswith('/'+name));path=OUT/'saved'/rel
   with path.open('rb')as stream:obj=images.load(stream,pretty=False)
   assert isinstance(obj['entries'],list)and obj['entries']
   decoded[name]=obj
   write(OUT/(name+'.json'),obj)
  cores={int(n.split('-')[1].split('.')[0]):d for n,d in decoded.items()if n.startswith('core-')}
  pstree=decoded['pstree.img']['entries'];assert len(pstree)==1 and pstree[0]['pid']==1
  assert set(pstree[0]['threads'])==set(cores)=={1,7,8,9}
  assert len(decoded['mm-1.img']['entries'])==1
  mm=decoded['mm-1.img']['entries'][0];fs=decoded['files.img']['entries']
  result['threads']={}
  for tid,core in sorted(cores.items()):
   assert len(core['entries'])==1
   result['threads'][str(tid)]=locate(core['entries'][0],mm,fs)
  portable=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())
  runtime,rproof=reports.restore_report(portable['group'],portable['run'],portable['summary_sha256'],portable['parts_sha256'],OUT/'runtime',['native-image.tar','runtime-inventory.json'])
  assert runtime==portable['report']and runtime['sources_unchanged']and runtime['image_id']==IMAGE
  result['runtime_source']=rproof
  def command(argv):
   p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
   assert p.returncode==0,(argv,p.returncode,p.stderr[-3000:].decode(errors='replace'))
   return p.stdout
  result['docker_load']=command(['docker','load','-i',str(OUT/'runtime/native-image.tar')]).decode()
  info=json.loads(command(['docker','image','inspect',IMAGE]));assert len(info)==1 and info[0]['Id']==IMAGE
  # docker create does not execute its entrypoint. Never docker start/run/restore.
  owned=command(['docker','create','--network','none','--entrypoint','/bin/true',IMAGE]).decode().strip()
  assert re.fullmatch('[a-f0-9]{64}',owned)
  info=json.loads(command(['docker','inspect',owned]))[0];assert info['State']['Status']=='created'and not info['State']['Running']
  paths=sorted({ELF_PATH,*[r['path']for r in result['threads'].values()]});native=OUT/'native-files';native.mkdir()
  copied={}
  for index,name in enumerate(paths):
   path=native/str(index);command(['docker','cp',owned+':'+name,str(path)])
   assert path.is_file()and not path.is_symlink()
   copied[name]=dict(path=path,sha256=sha(path),bytes=path.stat().st_size)
  assert copied[ELF_PATH]['sha256']==ELF
  result['native_file_inventory']={k:{a:b for a,b in v.items()if a!='path'}for k,v in copied.items()}
  for tid,row in result['threads'].items():
   native_path=copied[row['path']]['path']
   mapping=elf_address(native_path,row['file_offset']);address=mapping['elf_virtual_address']
   row['elf_mapping']=mapping;row['elf_sha256']=copied[row['path']]['sha256']
   row['addr2line']=command(['addr2line','-f','-C','-e',str(native_path),hex(address)]).decode()
   asm=command(['objdump','-d','-C','--start-address='+hex(max(0,address-128)),'--stop-address='+hex(address+128),str(native_path)])
   (OUT/('thread-'+tid+'-disassembly.txt')).write_bytes(asm)
   row['disassembly_sha256']=hashlib.sha256(asm).hexdigest()
  assert json.loads(command(['docker','inspect',owned]))[0]['State']['Status']=='created'
  methods();result['status']='PASS_AUTHENTICATED_SAVED_INSTRUCTION_LOCATIONS_NOT_ROUTE_OR_CAUSAL_PROOF'
 except BaseException as error:
  result.update(status='FAIL_SAVED_IP_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  if owned:subprocess.run(['docker','rm',owned],check=False)
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.glob('*')if p.is_file()and p.name!='result.json'}
  write(OUT/'result.json',result)
  print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--controls',action='store_true');args=a.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 methods()
 if args.controls:print(json.dumps(controls(),indent=2))
 else:run()
