from pathlib import Path
import json,hashlib,difflib
B=Path(__file__).resolve().parent;OLD=B.with_name('pcie-divider-v7-compact-v2-wire-v1-20261006');G=Path('/dev/shm/nssoc-div4-v8-cap-v1-layout-01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
ghash=pin(G/'nssoc_clock_div4_v8_cap_v1_layout.gds')['sha256'];names=['run_geometry','probe_native_cells','probe_device_locations','probe_wire_components','probe_terminal_anchors','prepare_anchors','bind_source_ids'];bridges=[]
for name in names:
 p=OLD/(name+'.py');q=B/p.name;old=p.read_text();s=old
 for a,b in [('nssoc-div4-v7-compact-v2-','nssoc-div4-v8-cap-v1-'),('nssoc_clock_div4_v7_compact_v2_layout','nssoc_clock_div4_v8_cap_v1_layout'),('db400e586cadbedbea9ec8aec5466c0eba4789e262c90ebd0d321a1c2cbcf579',ghash),('PASS_DIV4_V7_COMPACT_V2_STANDALONE','PASS_DIV4_V8_CAP_V1_STANDALONE'),('PASS_ACTUAL_COMPACT_INTRINSICS_POWER_AND_FOUR_GEOMETRY_CONTROLS','PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS'),('pcie-divider-v7-compact-v2-20261006/native-saved-peer-rx.json','pcie-divider-v8-cap-v1-20261006/native-saved-peer-rx.json'),('PASS_INDEPENDENT_SAVED_COMPACT_V2_NATIVE_RESULT','PASS_INDEPENDENT_SAVED_CAP24_V1_NATIVE_RESULT'),('DIVIDER_V7','DIVIDER_V8_CAP24')]:s=s.replace(a,b)
 assert not q.exists();q.write_text(s);a,b=old.splitlines(True),s.splitlines(True);ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()];bridges.append(dict(before=dict(path=str(p),**pin(p)),after=dict(path=str(q),**pin(q)),opcodes=ops))
(B/'native_unsimplified.lvs').write_bytes((OLD/'native_unsimplified.lvs').read_bytes());(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n');(B/'draft-only.json').write_text(json.dumps(dict(status='SOURCE_ONLY_FRESH_CAP24_WIRE_GEOMETRY_NOT_EXECUTED',GDS=pin(G/'nssoc_clock_div4_v8_cap_v1_layout.gds'),scope='Exact seven parent methods, freshCap24 roots/top/hash and independently saved nativepeer gate. All91/283/205/37/72 geometry/terminal/native cluster guards and7metals remain strict. Two actualMIM sizes changed20→24um; source identity binding reads newnative metadata andactual geometry. NoRC/loaded455run.'),indent=2)+'\n');print(ghash)
