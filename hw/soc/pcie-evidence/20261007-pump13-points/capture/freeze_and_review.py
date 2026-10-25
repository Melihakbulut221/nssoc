from pathlib import Path
import json,sys,hashlib,ast
R=Path.cwd();B=Path(__file__).resolve().parent;sys.path.insert(0,str(B));import characterize_pump13_02 as m
pin=m.pin
controls={}
for folder in ['finite-controls02','storage-controls01','contract-controls02','startup-controls01']:
 p=B/folder/'result.json';d=json.loads(p.read_text());assert d['status'].startswith('PASS_');controls[folder]=dict(result=pin(p),cases=d.get('cases',len(d.get('outcomes',[]))))
assert sum(x['cases']for x in controls.values())==71
cap=json.loads((B/'file-limit-control.json').read_text());assert cap['status']=='PASS_ACTUAL_NATIVE_FILE_CAP_AND_EXACT_SINGLE_CHANGE'
assert cap['resource_bound']['worst_case_sum_bytes']<m.POINT_LIMIT
paths=set(B.glob('*.py'))|set(B.glob('*.json'))
for folder in controls:paths.update(x for x in (B/folder).rglob('*') if x.is_file())
paths.update([m.n.NG,*m.n.OSDI,*m.n.MODELS.glob('*.lib'),Path(sys.executable).resolve()])
for case in m.CASES:
 c,rows,texts=m.config(case);assert len(rows)==13 and len(m.OBS)==28;paths.update(map(Path,c['sources']))
for mod in list(sys.modules.values()):
 f=getattr(mod,'__file__',None)
 if f and Path(f).resolve().is_relative_to(R) and '/tools/' not in str(Path(f)) :paths.add(Path(f).resolve())
for x in [m.S/'source-freeze02.json',m.S/'composition01.json',m.S/'force-contract02.json',m.S/'architecture-source-peer-root01.json']:paths.add(x)
pins={str(p.resolve()):pin(p)for p in sorted(paths)}
freeze=dict(status='FROZEN_PUMP13_FILE_CAP_REPAIR',pins=pins,controls=controls,actual_file_cap_control=pin(B/'file-limit-control.json'),physical_changes=False,physical_acceptance=False)
p=B/'source-freeze01.json';assert not p.exists();p.write_text(json.dumps(freeze,indent=2)+'\n')
review=dict(status='PASS_SOURCE_ONLY_PUMP13_EXECUTABLE_AND_CONTROLS',freeze=pin(p),findings=[],reviewer='root',external_independent_review=False,scope='Root review of inherited driver and exact one resource-limit replacement; 71 finite/storage/arithmetic/startup controls plus actual8MiB child. No physical outcome, matched570 boundary or loop claim.',checked_pins=len(pins),passed_controls=72)
(B/'source-only-peer-root01.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review))
