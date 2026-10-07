import sys,pathlib,subprocess,json,signal,hashlib,ast
B=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(B));import characterize_pump13_02 as m
out=B/'file-limit-control';out.mkdir();native=out/'bounded.bin'
command=[sys.executable,'-c',"import os,errno;f=open('bounded.bin','wb',buffering=0)\ntry:\n f.write(b'x'*(9*1024**2))\n f.write(b'x')\nexcept OSError as e:\n assert e.errno==errno.EFBIG\n assert os.stat('bounded.bin').st_size==8*1024**2\n print('EXPECTED_EFBIG_AT_8MIB',flush=True)\nelse:raise AssertionError('No native file cap')"]
with m.life.ProcessOwner(out/'owner.json') as owner:
 with (out/'log.txt').open('w') as log:
  child=owner.launch('native',command,cwd=out,stdout=log,stderr=subprocess.STDOUT,preexec_fn=m.native_limit)
  while child.poll() is None:owner.check();owner.cancelled.wait(.05)
  code=owner.complete(child);owner.check()
owner.check();assert code==0;assert native.stat().st_size==8*1024**2
assert 'EXPECTED_EFBIG_AT_8MIB' in (out/'log.txt').read_text()
old=pathlib.Path('hw/soc/out/pcie-tail115-pump13-characterization-20261006/characterize_pump13_01.py');delta=json.loads((B/'resource-change.json').read_text());a=old.read_text();b=(B/'characterize_pump13_02.py').read_text()
assert hashlib.sha256(a.encode()).hexdigest()==delta['previous_source_sha256']
assert a.count(delta['replacement_before'])==1 and a.replace(delta['replacement_before'],delta['replacement_after'])==b
for case in m.CASES:
 c,rows,texts=m.config(case);total=sum(len(v.encode()) for v in texts.values())+len(m.deck(c,rows,texts).encode())+len('set num_threads=1\n');assert total<2*1024**2
r=dict(status='PASS_ACTUAL_NATIVE_FILE_CAP_AND_EXACT_SINGLE_CHANGE',bytes_at_limit=native.stat().st_size,returncode=code,resource_bound=delta,source_change_only_native_limit=True,graph_unchanged=True,reviewer='root',external_independent_review=False)
(B/'file-limit-control.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
