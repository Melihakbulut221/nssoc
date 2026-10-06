# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;E=B.parent/'pcie-vco-v6-divider-tail115-v1-eighthstep-20261006';S=B.parent/'pcie-tail115-streaming-replay-v1-20261006'
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def bridge(parent,child):
 a=parent.read_text();z=child.read_text();v=dict(parent=dict(path=str(parent),**pin(parent)),child=dict(path=str(child),**pin(child)),full_diff=''.join(difflib.unified_diff(a.splitlines(True),z.splitlines(True))),opcodes=[dict(tag=t,a0=i,a1=j,b0=k,b1=l,old=a[i:j],new=z[k:l])for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]);(B/(child.name+'.source-bridge.json')).write_text(json.dumps(v,indent=2)+'\n')
s=(E/'characterize_eighthstep01.py').read_text().replace('512 * 1024 * 1024','1024 * 1024 * 1024').replace('6.25e-13','3.125e-13').replace('eighthstep','sixteenthstep').replace('Own512MiB','Own1024MiB')
assert s!=(E/'characterize_eighthstep01.py').read_text();p=B/'characterize_sixteenthstep01.py';p.write_text(s);bridge(E/'characterize_eighthstep01.py',p)
s=(E/'launch_probe01.py').read_text().replace('eighthstep','sixteenthstep').replace('EIGHTHSTEP','SIXTEENTHSTEP');p=B/'launch_probe01.py';p.write_text(s);bridge(E/p.name,p)
s=(E/'seal_probe01.py').read_text().replace('eighthstep','sixteenthstep').replace('6.25e-13','3.125e-13')
s=s.replace("import characterize_sixteenthstep01 as candidate","sys.path.insert(0,str(R/'hw/soc/out/pcie-tail115-streaming-replay-v1-20261006'))\nfrom raw_table01 import open_table\nimport characterize_sixteenthstep01 as candidate")
s=s.replace("assert len(r['devices'])==455","assert len(r['devices'])==455\nassert r['config']['step_s']==3.125e-13 and r['config']['stop_s']==34e-9 and r['config']['window_s']==[4e-9,34e-9]")
a=s.index("with gzip.open(P/'wave.raw.gz'");z=s.index("assert all(np.isfinite",a)
read="with gzip.open(P/'wave.raw.gz','rb') as stream:\n    header,meta=m.life.tiny.parse_header(stream,m.n.vectors(r['devices'],r['config']['extra_vectors']))\nwith open_table(P/'wave.raw.gz',rows=r['rows'],columns=m.stream.previous.data_names(meta['columns']),compressed_pin=r['outputs']['wave.raw.gz'],raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],raw_bytes=r['raw_bytes'],scratch_directory=B,scratch_limit=1024**3) as table:\n    assert table['header']==header\n    data=dict(zip(table['columns'],table['matrix'].T))\n"
s=s[:a]+read+s[z:];a=s.index('assert all(np.isfinite');z=s.index("review={'status'",a);block=s[a:z].replace("34e-9,3.125e-13)","34e-9,r['config']['step_s'])")
s=s[:a]+''.join('    '+line if line.strip()else line for line in block.splitlines(True))+"    del data,values\n"+s[z:]
p=B/'seal_probe01.py';p.write_text(s);bridge(E/p.name,p)
s=(E/'compare_saved_steps01.py').read_text()
s=s.replace('import numpy as np','import numpy as np\nimport sys\nsys.path.insert(0,str(Path.cwd()/\'hw/soc/out/pcie-tail115-streaming-replay-v1-20261006\'))\nfrom raw_table01 import open_table')
s=s.replace("NEW=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-eighthstep-06-01')","EIGHTH=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-eighthstep-06-01')\nNEW=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01')")
s=s.replace("results=[]\n", "assert pin(EIGHTH/'result.json')==dict(bytes=426392,sha256='03977b90f4877791934cf74b13274b3476f41ae790307f3c3005481ab6d709ff')\nresults=[]\n",1)
s=s.replace("(QUARTER,1.25e-12),(NEW,6.25e-13)","(QUARTER,1.25e-12),(EIGHTH,6.25e-13),(NEW,3.125e-13)")
a=s.index(' raw=gzip.decompress');z=s.index(' full_ce=crossings',a)
read=" names=r['columns'];assert len(names)==957 and len(set(names))==957\n with open_table(root/'wave.raw.gz',rows=r['rows'],columns=names,compressed_pin=r['outputs']['wave.raw.gz'],raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],raw_bytes=r['raw_bytes'],scratch_directory=B,scratch_limit=1024**3)as table:\n  a=table['matrix'];d=dict(zip(names,a.T));t=d['time'];assert np.all(np.diff(t)>0)and t[-1]==34e-9\n"
s=s[:a]+read+s[z:];a=s.index(' full_ce=crossings');z=s.index(' del raw,payload,a,d',a);block=s[a:z];s=s[:a]+''.join(' '+line if line.strip()else line for line in block.splitlines(True))+"  del a,d,t\n"+s[z+len(' del raw,payload,a,d\n'):]
needle='# This is numerical evidence, not an alternative pass predicate.'
s=s.replace(needle,"for path,value in json.loads((B/'source-freeze01.json').read_text())['pins'].items():assert pin(path)==value\nfor entry in results:\n for path,value in entry['source_inputs'].items():assert pin(path)==value\n"+needle)
p=B/'compare_saved_steps01.py';p.write_text(s);bridge(E/p.name,p)
s=(E/'verify_derivative01.py').read_text().replace("'pcie-vco-v6-divider-tail115-v1-quarterstep-20261006'","'pcie-vco-v6-divider-tail115-v1-eighthstep-20261006'").replace('characterize_eighthstep01 as new','characterize_sixteenthstep01 as new').replace('characterize_quarterstep01 as old','characterize_eighthstep01 as old').replace("B/'characterize_eighthstep01.py'","B/'characterize_sixteenthstep01.py'").replace('step_s=6.25e-13','step_s=3.125e-13').replace(".tran 6.25e-13 3.4e-08 0 6.25e-13",".tran 3.125e-13 3.4e-08 0 3.125e-13").replace(".tran 1.25e-12 3.4e-08 0 1.25e-12",".tran 6.25e-13 3.4e-08 0 6.25e-13")
s=s.replace("new.OWN_LIMIT==512*1024**2 and old._scope['OWN_LIMIT']==256*1024**2","new.OWN_LIMIT==1024*1024**2 and old._scope['OWN_LIMIT']==512*1024**2").replace('Own512MiB','Own1024MiB').replace('Own256MiB','Own512MiB').replace('400','800').replace('511','1023').replace('PASS_EIGHTHSTEP_','PASS_SIXTEENTHSTEP_').replace('1.25ps→0.625ps','0.625ps→0.3125ps').replace('bounded512MiB','bounded1024MiB')
p=B/'verify_derivative01.py';p.write_text(s);bridge(E/p.name,p)
for name in ['convergence_policy01.py','test_numerical_policy01.py']:
 p=B/name;p.write_bytes((E/name).read_bytes());bridge(E/name,p)
p=json.loads((E/'numerical-policy01.json').read_text());p.update(reference_step_s=6.25e-13,candidate_step_s=3.125e-13,reference_native_result=pin(Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-eighthstep-06-01/result.json')))
(B/'numerical-policy01.json').write_text(json.dumps(p,indent=2)+'\n');bridge(E/'numerical-policy01.json',B/'numerical-policy01.json')
print('prepared new sources; no native')
