from pathlib import Path
import hashlib,json,ast
B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'source-freeze.json';assert pin(f)==dict(bytes=74564,sha256='2bde0358770527b6fa5bdf97c26c5b39bed58ab388aaa1110e6b63ccf5003552');j=json.loads(f.read_text());assert len(j['inputs'])==354
for p,v in j['inputs'].items():assert pin(p)==v,p
b=json.loads((B/'source-bridge.json').read_text())
for k in['before','after']:
 p=Path(b[k]['path']);assert pin(p)=={x:b[k][x]for x in['bytes','sha256']};assert ''.join(x[k]for x in b['opcodes'])==p.read_text()
a=Path(b['before']['path']).read_text();z=Path(b['after']['path']).read_text();assert a.replace('nssoc-div4-v7-layout-01','nssoc-div4-v7-power-v2-layout-01').replace('nssoc-div4-v7-binding-controls-01','nssoc-div4-v7-power-v2-binding-controls-01')==z
assert not(B/'result.json').exists()and not Path('/dev/shm/nssoc-div4-v7-power-v2-binding-controls-01').exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_BINDING_CONTROLS',freeze=pin(f),findings=[],inputs_rehashed=354,method=pin(__file__),full_byte_inverse_verified=True,review=['Read full 8608-byte harness: exact old controlled harness with only physical fixture G path including copied binder root literal and fresh owned scratch. No mutation or threshold change.','Positive actual copied-input run must reproduce complete production graph except provenance; four separately copied negatives each have exactly one declared JSON edit and require specific native traceback assertion, not any nonzero exit. Clock swap, physical resistor length, missing finite tap and MIM area each test a distinct binding predicate.','Frozen source and all positive geometry outputs verified before controls; binder itself inverse-byte checked with one fixture-root replacement. Production GDS and extraction outputs unchanged.','Same exact cloned checked owner functions,CPU10/2GiB/80MiB own cap24MiB reservation/1GiBentry512MiB continuous floor/no healthy elapsed watchdog; terminal resource and source checks retained. Every native child reaped before next.'],reviewed_or_native_methods_executed=False,scope='Source-only five copied-input validation controls. Not new physical extraction, electrical fault simulation or RC acceptance.')
p=B/'source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
