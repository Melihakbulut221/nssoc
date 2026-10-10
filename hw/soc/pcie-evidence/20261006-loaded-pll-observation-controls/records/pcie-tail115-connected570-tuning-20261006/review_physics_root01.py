"""Independent source/configuration/measurement audit; no570 native execution."""
from pathlib import Path
import ast,collections,hashlib,json,os,resource,sys
R=Path.cwd();B=Path(__file__).resolve().parent;S=B.parent/'pcie-tail115-connected570-source-20261006'
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def exact(p,w):assert pin(p)=={k:w[k]for k in ('bytes','sha256')},str(p)
def body(s,n):return ast.get_source_segment(s,next(x for x in ast.parse(s).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))and x.name==n))+'\n'
f=read(B/'source-freeze01.json');assert len(f['pins'])==1670 and f['actual_cases']==40
for name,w in f['pins'].items():exact(name,w)
for name,w in f['products'].items():exact(B/name,w)
exact(S/'source-freeze01.json',f['source570_freeze']);exact(S/'source-contract-peer-root01.json',f['source570_peer']);assert not read(S/'source-contract-peer-root01.json')['findings']
exact(B/'driver-source-bridge01.json',f['full_driver_bridge']);bridge=read(B/'driver-source-bridge01.json');exact(bridge['parent'],bridge['parent_pin']);exact(B/'characterize_clamped570_01.py',bridge['output'])
old=Path(bridge['parent']).read_text();new=(B/'characterize_clamped570_01.py').read_text()
for row in bridge['functions']:assert row['before']==body(old,row['name']) and row['after']==body(new,row['name'])
assert body(old,'run_native')==body(new,'run_native')
expected=body(old,'Meter').replace('Frozen424 device screens','Frozen539 non-contact device screens').replace('== 455','== 570').replace('        super().push(block)','        require(self.count + len(block) <= MAX_ROWS, "Bounded120000 native rows including adaptive extras")\n        super().push(block)')
assert body(new,'Meter')==expected
assert body(new,'deck')==body(old,'deck').replace('Actual455-device VCOv6 and divider wire RC loaded /80 prototype','Clamped570 full-device PFD-idle tuning diagnostic; not a connected-loop run')
# Explicit producer module is safe to import: main is guarded; config only reads.
sys.path.insert(0,str(B));import characterize_clamped570_01 as m
composition=read(S/'composition01.json')['variants']['negative'];recipes=read(B/'recipes01.json');assert [r['vctrl']for r in recipes]==[.5,.6,.7]
expanded=composition['devices'];assert len(expanded)==570 and len({r['path']for r in expanded})==570
assert sum(len(r['nets'])for r in expanded)==2097
censuses=[];decks=[]
for recipe in recipes:
 value=recipe['vctrl'];c,rows,texts=m.config(value)
 assert rows==expanded==recipe['devices'] and c==recipe['config'] and texts==recipe['physical_texts']
 assert c['roots']==[composition['root']] and c['step_s']==3.125e-13 and c['stop_s']==34e-9 and c['window_s']==[4e-9,34e-9]
 assert not c['polarity_selected'] and not c['connected_loop_acceptance']
 fixture=list(composition['fixture']);idx=fixture.index('VRESET reset 0 PWL(0 0 500p 2.5 8n 2.5 8.1n 0)');fixture[idx]='VRESET reset 0 PWL(0 0 500p 2.5)';fixture.append(f'VCTRL vctrl 0 PWL(0 0 500p {value:.1f})');assert c['fixture']==fixture
 vectors=m.n.vectors(rows,c['extra_vectors']);assert len(vectors)==len(set(vectors))==1133 and set(vectors)==set(composition['observation_vectors'])|{'i(vctrl)'} and vectors==recipe['observations']
 deck=m.deck(c,rows,texts);assert deck==recipe['deck'];assert deck.count('alter @q.')==64 and deck.count('show q.')==64 and '.temp 27' in deck
 assert '.tran 3.125e-13 3.4e-08 0 3.125e-13' in deck
 assert deck.count('VCTRL vctrl 0 PWL(')==1 and 'run stream.fifo' in deck
 assert ' uic' not in deck.lower() and '\n.ic ' not in deck.lower()
 decks.append(deck.replace(f'500p {value:.1f})','500p CLAMP)'))
 censuses.append(dict(value=value,devices=len(rows),terminals=sum(len(r['nets'])for r in rows),saved_vectors=len(vectors),models=dict(collections.Counter(r['model']for r in rows)),deck_sha256=hashlib.sha256(deck.encode()).hexdigest()))
assert decks[0]==decks[1]==decks[2]
# Actual finite controls: raw N16 division reductions plus clearly synthetic570 fixtures.
ctrl=f['actual_controls']['finite'];exact(ctrl['path'],ctrl['pin']);j=read(ctrl['path']);assert j['cases']==len(j['outcomes'])==11 and all(x['passed']for x in j['outcomes']) and not j['native_or_solver_executed'];assert j['source']==pin(B/'characterize_clamped570_01.py')
positive=j['outcomes'][0];assert len(positive['checks'])==13 and all(positive['checks'].values())
safe=next(x for x in j['outcomes']if x['case']=='all570_safety_rules_on_four_static_saved_operating_rows');assert len(safe['bounds'])==570 and all(x['passed']for x in safe['bounds'])
assert {x['path']for x in safe['bounds']}=={r['path']for r in expanded}
assert {'reject_pfd_up_idle','reject_pfd_down_idle','reject_external_reset_asserted','reject_actual_clamp_level','actual_added_pfd_device_terminal_overvoltage','retained_finite_contact_voltage_rejection','finite_capture_nonfinite','finite_capture_row_budget'}<={x['case']for x in j['outcomes']}
for row in j['outcomes']:
 for key in ['fixture','captured']:
  if key in row:assert row[key]['bytes']>0 and len(row[key]['sha256'])==64
assert not m.NATIVE_ROOT.exists()
result=dict(status='PASS_SOURCE_ONLY_CLAMPED570_PHYSICS_DECK_AND_MEASUREMENT',freeze=pin(B/'source-freeze01.json'),findings=[],method=pin(__file__),complete_pin_count=1670,recipes=censuses,full_inherited_bodies=4,unchanged_native_owner=True,unchanged_device_safety_except_census_and_rowcap=True,original_division_predicates=13,added_idle_clamp_predicates=4,finite_control_cases=11,limits='Source and saved finite controls only. Existing source570 peer binds physical455 plus115 exactPFD/pump/filter. Ideal VCTRL/PFDheldreset is explicit tuning fixture, cannot demonstrate closedloop acquisition/polarity/pump reachability. Contact voltage <=3.3V is only voltage screen, inferred currents unqualified. Each native point pending;455adjacentstep not transferred to570.',resource_peer_pending=True,native_started=False)
p=B/'physics-source-peer-root01.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],peer=pin(p),pins=1670)))
