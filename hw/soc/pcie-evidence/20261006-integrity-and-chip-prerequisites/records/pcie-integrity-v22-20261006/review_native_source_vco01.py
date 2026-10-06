from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent
R=B.parents[3]
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
p=B/'continuation-policy01.json';policy=json.loads(p.read_text())
for name,v in policy['method_pins'].items():assert pin(name)==v
for name,v in policy['source_pins'].items():assert pin(R/name)==v
bridges=json.loads((B/'native-source-bridges01.json').read_text())
for row in bridges:
 assert pin(row['parent'])==row['parent_pin'] and pin(row['path'])==row['pin']
 before=Path(row['parent']).read_text();after=before;states=[]
 for step in row['replacements']:
  assert after.count(step['before'])==step['count'];states.append(after);after=after.replace(step['before'],step['after'])
 assert after==Path(row['path']).read_text()
 for step,prior in reversed(list(zip(row['replacements'],states))):
  chunks=prior.split(step['before']);assert step['after'].join(chunks)==after;after=step['before'].join(chunks)
 assert after==before
for name in ['run_balanced_map.py','balanced_import.py','balanced_preplacement.py']:
 s=(B/name).read_text();assert 'killpg(' in s and 'process_identity' not in s
r=dict(status='SOURCE_ONLY_V22_NATIVE_LIFECYCLE_FINDINGS',policy=pin(p),detacher=pin(B/'detach_native01.py'),full_byte_bridges=len(bridges),method_pins_rehashed=len(policy['method_pins']),source_pins_rehashed=len(policy['source_pins']),findings=[dict(id='TERMINAL_RESOURCE_FLOOR',files=['run_balanced_map.py','balanced_import.py','balanced_preplacement.py'],detail='Each launcher checks free shared scratch only while child.poll() is None. A short child can cross the floor and exit between polls, then be accepted without a terminal resource check.'),dict(id='REAPED_GROUP_SIGNAL',files=['run_balanced_map.py','balanced_import.py','balanced_preplacement.py'],detail='Exception handlers call killpg(pid) without checking the child is still live and has the exact captured birth/group identity. An exception after poll/wait reaps the child can signal an unowned or recycled process group. Capture identity with launch signals blocked and check live birth/group before cleanup.')],functional_review='All eight complete bridges reconstructed both ways; exact V22 composite 38/35/3 gate and 17-case/8 cache-witness gate. Actual corrected V21 descriptor Q/D boundary, complete pin graph proof, fixed 4ns three-corner constraints and all timing reductions preserved. No product acceptance relaxation.',scope='Source-only review; no reviewed producer, map, STA, controls or native execution.',method=pin(__file__))
out=B/'native-source-only-peer01-findings-vco.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
