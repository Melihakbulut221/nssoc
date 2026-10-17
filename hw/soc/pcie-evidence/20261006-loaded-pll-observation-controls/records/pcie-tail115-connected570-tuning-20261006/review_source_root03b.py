"""Independent whole-body delta and actual tiny-native readback for full retry03."""
from pathlib import Path
import ast,hashlib,json,sys
T=Path(__file__).resolve().parent;C=T.parent/'pcie-tail115-connected570-save-batches-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
f=read(T/'source-freeze03.json');assert len(f['pins'])==1822
for p,w in f['pins'].items():assert pin(p)==w,p
old=read(T/'source-freeze02.json')
for p,w in old['pins'].items():assert f['pins'][p]==w and pin(p)==w,p
p2=read(T/'source-only-peer-root02.json');pc=read(C/'source-only-peer-root01.json');assert not p2['findings'] and not pc['findings']
oldtext=(T/'characterize_clamped570_02.py').read_text();newtext=(T/'characterize_clamped570_03.py').read_text()
inv=newtext.replace("NATIVE_ROOT=B/'native03'","NATIVE_ROOT=B/'native02'").replace("SAVE_SOURCE=B.parent/'pcie-tail115-connected570-save-batches-20261006'\nsys.path.insert(0,str(SAVE_SOURCE))\nimport save_batches03 as batch\n",'').replace('*batch.commands(n.vectors(rows, c["extra_vectors"]))','"save " + " ".join(n.vectors(rows, c["extra_vectors"]))')
assert inv==oldtext
b=read(T/'batch-source-supplement03.json');assert b['before']==oldtext and b['after']==newtext
oldtree=ast.parse(oldtext);newtree=ast.parse(newtext)
for name in b['unchanged_functions']:
 a=next(x for x in oldtree.body if getattr(x,'name',None)==name);z=next(x for x in newtree.body if getattr(x,'name',None)==name);assert ast.dump(a)==ast.dump(z)
assert len(b['unchanged_functions'])==10
launch2=(T/'launch_three02.py').read_text();launch3=(T/'launch_three03.py').read_text()
inverse=launch3
for before,after in [('characterize_clamped570_03','characterize_clamped570_02'),('source-freeze03.json','source-freeze02.json'),('source-only-peer-root03.json','source-only-peer-root02.json'),('campaign03.json','campaign02.json'),('launch-once03.json','launch-once02.json'),('controller03.log','controller02.log'),('detached-launch03.json','detached-launch02.json')]:inverse=inverse.replace(before,after)
assert inverse==launch2
sys.path.insert(0,str(T));sys.path.insert(0,str(C));import characterize_clamped570_02 as m2;import characterize_clamped570_03 as m3;import save_batches03 as batch
for v in m3.POINTS:
 a,ar,at=m2.config(v);z,zr,zt=m3.config(v);z['sources']=[s.replace('characterize_clamped570_03.py','characterize_clamped570_02.py')for s in z['sources']]
 assert a==z and ar==zr and at==zt
 assert len(zr)==570 and len(m3.n.vectors(zr,z['extra_vectors']))==1133
 assert batch.replace_save(m2.deck(a,ar,at),m2.n.vectors(ar,a['extra_vectors']))==m3.deck(z,zr,zt)
 assert a['step_s']==3.125e-13 and a['stop_s']==34e-9 and a['window_s']==[4e-9,34e-9]
N=C/'native-control01';result=read(N/'result.json');assert result['status']=='PASS_BOUNDED_NATIVE570_SAVE_BATCH_COMMAND_AND_OBSERVATION_CONTROLS' and result['cases']==8
assert result['physics_acceptance'] is False and not result['full34ns_tuning_executed']
for p,w in result['inputs'].items():assert pin(p)==w,p
for p,w in result['outputs'].items():assert pin(N/p)==w,p
assert all(x['passed']for x in result['outcomes'])
c,rows,texts=m3.config(.5);expected=m3.n.vectors(rows,c['extra_vectors']);raw=m3.n.read_raw(N/'tiny.raw',expected,True)
assert len(raw)==1134 and len(raw['time'])==19 and abs(raw['time'][-1]-2e-12)<1e-24
with(N/'tiny.raw').open('rb')as stream:header,meta=m3.life.tiny.parse_header(stream,expected)
assert len(header)==60234 and meta['columns']==result['observations']
startup=m3.stream.previous.startup_proof(N,dict(devices=rows,config=c));assert startup['zero_source_op'] and len(startup['native_off_flags'])==64
log=(N/'run.log').read_text();assert 'too many args'not in log.lower()
owner=read(N/'owner.json');assert owner['status']=='HEALTHY' and len(owner['processes'])==1 and all(r['status']=='REAPED_NO_LIVE_MEMBERS' and r['returncode']==0 for r in owner['processes'])
for row in owner['processes']:
 i=row['identity'];p=Path(f'/proc/{i["pid"]}/stat');assert not p.exists() or p.read_text().rsplit(')',1)[1].split()[19]!=str(i['start_ticks'])
assert f['inherited_actual_cases']==41 and f['new_actual_cases']==8 and f['total_reused_and_new_actual_cases']==49
for row in f['actual_controls'].values():assert pin(row['path'])==row['pin'] and read(row['path'])['status']==row['status']
assert not m3.NATIVE_ROOT.exists()
out=dict(status='PASS_SOURCE_ONLY_CLAMPED570_THREE_POINT_DIAGNOSTICS',freeze=pin(T/'source-freeze03.json'),findings=[],method=pin(__file__),prior_peer=pin(T/'source-only-peer-root02.json'),batch_control_source_peer=pin(C/'source-only-peer-root01.json'),bounded_native_control=pin(N/'result.json'),pins=1822,old_pins_unchanged=1736,complete_driver_inverse=True,unchanged_functions=10,launcher_complete_version_inverse=True,actual_prior_controls=41,new_control_checks=8,independent_native_readback=dict(devices=570,HBT_OFF=64,vectors=1133,columns=1134,rows=19,header_bytes=60234,stop_s=2e-12),full_retry_stop_s=34e-9,points=[.5,.6,.7],physics_unchanged=True,thresholds_unchanged=True,reviewer_correction='First review used overbroad03to02 filename inverse affecting unchanged03d numeric formatting, and assumed top-levelowner terminal schema; corrected exactseven filename replacements and per-childreaped status. Original review/log retained; no product change.',scope='Exact sequential fresh native03 diagnostics only. Complete bounded samebinary2ps saved raw/OP/control review passed; not tuning-range/loop/PHY acceptance.',physical_acceptance=False)
(T/'source-only-peer-root03.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
