# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One source-gated2ps command/OP control, never a570 tuning point."""
from pathlib import Path
import copy,gzip,hashlib,io,json,os,re,resource,shutil,subprocess,sys
B=Path(__file__).resolve().parent;R=Path.cwd();T=B.parent/'pcie-tail115-connected570-tuning-20261006';sys.path.insert(0,str(T));sys.path.insert(0,str(B))
import characterize_clamped570_02 as m
import save_batches03 as batch
N=B/'native-control01';FLOOR=512*1024**2;CAP=128*1024**2

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def guard():
 assert shutil.disk_usage('/dev/shm').free>=FLOOR,'Shared512MiBfloor'
 assert shutil.disk_usage(B).free>=1024**3,'SSD1GiBfloor'
 assert sum(p.stat().st_size for p in N.rglob('*')if p.is_file())<=CAP,'Control128MiBcap'
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,)*2);os.sched_setaffinity(0,{10})
def main():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));assert os.sched_getaffinity(0)=={10}
 freeze=B/'source-freeze01.json';f=json.loads(freeze.read_text());peer=json.loads((B/'source-only-peer-root01.json').read_text())
 assert peer['status']=='PASS_SOURCE_ONLY_570_BATCHED_SAVE_NATIVE_CONTROLS'and peer['freeze']==pin(freeze)and peer['findings']==[]
 for p,v in f['pins'].items():assert pin(p)==v,p
 assert not N.exists();assert shutil.disk_usage('/dev/shm').free>=1024**3 and shutil.disk_usage(B).free>=1024**3+CAP
 N.mkdir();cases=[];config,rows,texts=m.config(.5);expected=m.n.vectors(rows,config['extra_vectors']);assert len(rows)==570 and len(expected)==1133
 old=m.deck(config,rows,texts);new=batch.replace_save(old,expected)
 assert new.replace('\n'.join(batch.commands(expected))+'\n','save '+' '.join(expected)+'\n')==old
 # Only this command/format control uses2ps, with unchanged output/maxstep.
 tiny=copy.deepcopy(config);tiny['stop_s']=2e-12
 deck=batch.replace_save(m.deck(tiny,rows,texts),expected).replace('run stream.fifo','run\nwrite tiny.raw all')
 assert deck.count('run\nwrite tiny.raw all')==1 and '.tran 3.125e-13 2e-12 0 3.125e-13' in deck
 for name,text in texts.items():(N/name).write_text(text)
 (N/'spinit').write_text('set num_threads=1\n');(N/'bench.cir').write_text(deck)
 inputs={str(p):pin(p)for p in N.iterdir()};inputs.update(f['pins']);record=dict(status='RUNNING_BOUNDED_570_SAVE_BATCH_COMMAND_CONTROL',inputs=inputs,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),full34ns_tuning_executed=False)
 m.n.common.atomic(N/'result.json',record)
 try:
  env={k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(N),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',RAYON_NUM_THREADS='1')
  with m.life.ProcessOwner(N/'owner.json')as owner:
   with(N/'run.log').open('x')as log:
    child=owner.launch('native',[str(m.n.NG),'-n','-b','bench.cir'],cwd=N,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
    while child.poll()is None:owner.check();guard();owner.cancelled.wait(.05)
    assert owner.complete(child)==0;owner.check();guard()
  owner.check();guard()
  assert all(pin(p)==v for p,v in inputs.items())
  log=(N/'run.log').read_text();assert 'too many args'not in log.lower()
  startup=m.stream.previous.startup_proof(N,dict(devices=rows,config=config));assert startup['zero_source_op']and len(startup['native_off_flags'])==64
  with(N/'tiny.raw').open('rb')as src:header,meta=m.life.tiny.parse_header(src,expected)
  assert meta['declared_points']>0 and len(meta['columns'])==1134 and len(header)<65536
  data=m.n.read_raw(N/'tiny.raw',expected,True);assert len(data)==1134 and len(data['time'])==meta['declared_points'] and data['time'][0]==0 and abs(data['time'][-1]-2e-12)<1e-24
  cases.append(dict(case='actual570_OP_and2ps_samebinary_batched_save',passed=True,commands=len(batch.commands(expected)),arguments=[len(s.split())-1 for s in batch.commands(expected)],vectors=1133,raw_columns=1134,rows=len(data['time']),header_bytes=len(header),actual_raw_order=meta['columns'],startup=startup))
  for mode in ('missing','duplicate','reordered'):
   words=list(expected)
   if mode=='missing':words.pop()
   elif mode=='duplicate':words[-1]=words[0]
   else:words[0],words[1]=words[1],words[0]
   lines=['save '+' '.join(words[i:i+128])for i in range(0,len(words),128)]
   try:batch.verify(lines,expected)
   except AssertionError as e:assert 'Exact ordered observation' in str(e)
   else:raise AssertionError(mode+' command corruption accepted')
   (N/('bad-command-'+mode+'.txt')).write_text('\n'.join(lines)+'\n');cases.append(dict(case='reject_actual_command_'+mode,passed=True))
  hlines=header.decode().splitlines(True);start=hlines.index('Variables:\n')+1
  for mode in ('missing','duplicate','reordered'):
   lines=list(hlines)
   if mode=='missing':del lines[start+1]
   elif mode=='duplicate':
    token=lines[start+1].split()[1];fields=lines[start+2].split();fields[1]=token;lines[start+2]='\t'.join(fields)+'\n'
   else:lines[start+1],lines[start+2]=lines[start+2],lines[start+1]
   raw=''.join(lines).encode();(N/('bad-header-'+mode+'.bin')).write_bytes(raw)
   try:m.life.tiny.parse_header(io.BytesIO(raw),expected)
   except ValueError as e:diagnostic=str(e)
   else:raise AssertionError(mode+' native header corruption accepted')
   cases.append(dict(case='reject_actual_native_header_'+mode,passed=True,diagnostic=diagnostic))
  failed=T/'native02/v050-01';prior=json.loads((failed/'capture-failure.json').read_text());prefix=gzip.decompress((failed/'wave.raw.gz').read_bytes())
  assert 'save: too many args.'in(failed/'run.log').read_text()and b'No. Variables: 2679\n'in prefix and hashlib.sha256(prefix).hexdigest()==prior['received_raw_sha256']
  assert len(prefix)==65596 and (failed/'bench.cir').read_text()==old
  oldresult=json.loads((failed/'result.json').read_text());assert oldresult['inputs'][str(m.n.NG)]==pin(m.n.NG)
  cases.append(dict(case='original_actual1133_single_command_negative_preserved_not_rerun',passed=True,original_header_pin=pin(failed/'wave.raw.gz'),native_failure=pin(failed/'result.json'),diagnostic='save: too many args.'))
  record.update(status='PASS_BOUNDED_NATIVE570_SAVE_BATCH_COMMAND_AND_OBSERVATION_CONTROLS',cases=len(cases),outcomes=cases,observations=meta['columns'],full34ns_tuning_executed=False,physics_acceptance=False)
 except BaseException as e:record.update(status='FAILED_BOUNDED_NATIVE_SAVE_CONTROL_RETAINED',error=repr(e));raise
 finally:
  record['outputs']={str(p.relative_to(N)):pin(p)for p in N.rglob('*')if p.is_file()and p.name!='result.json'};m.n.common.atomic(N/'result.json',record)
 guard();print(json.dumps(dict(status=record['status'],cases=record.get('cases'),result=pin(N/'result.json'))))
if __name__=='__main__':main()
