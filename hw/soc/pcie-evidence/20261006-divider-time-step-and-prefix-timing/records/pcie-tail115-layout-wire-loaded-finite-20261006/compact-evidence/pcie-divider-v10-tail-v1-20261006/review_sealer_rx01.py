"""Independent whole-source sealer inverse; does not execute preservation."""
import json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p);return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
r=json.loads((B/'sealer-source-bridge01.json').read_text())
for k in ('before','after'):assert pin(r[k]['path'])=={n:r[k][n] for n in ('bytes','sha256')}
old=Path(r['before']['path']).read_text();new=Path(r['after']['path']).read_text();expected=old
for a,b in r['substitutions']:
 assert a in expected;expected=expected.replace(a,b)
assert expected==new
inverse=new
for a,b in reversed(r['substitutions']):inverse=inverse.replace(b,a)
assert inverse==old
result={'status':'PASS_SOURCE_ONLY_DIVIDER_V10_CLOSED_NATIVE_SEALER','findings':[],'method':pin(Path(__file__)),'source':pin(B/'preserve_native01.py'),'bridge':pin(B/'sealer-source-bridge01.json'),'parent':r['before'],'scope':'Whole3399-byte source read and exact six substitutions forward/inverse checked. Only paths/status/freeze02 and saved parent layout changed. Terminal21 predicate status, closed owner groups, full frozen input readback, original source rehash, unique regular archive members and full streamed archive readback retained. Source/history entries are selected by explicit suffix policy; original method attempts remain local where not selected. Stdout must be outside B and caller must wait for native owner closure. No sealer, native producer, DRC/LVS or controls executed.'}
p=B/'sealer-source-only-peer-rx01.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(pin(p))
