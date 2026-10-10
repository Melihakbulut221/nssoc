from pathlib import Path
import json,hashlib,datetime
R=Path.cwd();B=Path(__file__).resolve().parent
old=B/'source-freeze03.json';f=json.loads(old.read_text())
def pin(p):
 p=Path(p)
 with p.open('rb') as stream:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
assert '43/44 tests collected (1 deselected)' in (B/'collection04.log').read_text()
f['product_sources']={n:pin(R/n) for n in f['product_sources']}
for n,v in f['sources'].items():
 p=R/n
 if str(p.relative_to(R)) in f['product_sources'] if p.is_relative_to(R) else False:continue
 assert pin(p)==v,n
f['sources']={n:pin(R/n) for n in f['sources']}
extras=[old,B/'source-only-peer-rx03.json',B/'reset-repair-source-supplement04.json',B/'prepare_reset_repair04.py',B/'collection04.log',Path(__file__),B/'unknown-reset-saved-peer-rx01.json']
for name in ('failed-controls01','burst-diagnostic01','burst-baseline-diagnostic02','component-diagnostic01'):
 extras.extend(p for p in (B/name).rglob('*') if p.is_file())
extras.extend(B/n for n in ('diagnose_burst01.py','diagnose_burst_baseline02.py','diagnose_component01.py','seal_failed_controls01.py','seal-failed-controls01.log','status01.json','owner01.json','controls01.log','controls01.xml'))
D=B/'source-snapshot04';D.mkdir()
for n in f['product_sources']:
 p=R/n;q=D/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());extras.append(q)
f['sources'].update({str(p):pin(p) for p in extras})
f.update(status='FROZEN_V25_DIRECT_RESET_ASYNC_REPAIR_REQUIRES_PEER',utc=datetime.datetime.now(datetime.UTC).isoformat(),functional_predicates=43,parent_freeze=pin(old),scope='Explicit asynchronous nontrue reset hold for registered command fields/valid/apply/cache. Known-state original profile and restricted +1 relation unchanged. Full43 functional predicates must run; original40PASS2FAIL retained. Ring16/MAX18 is explicit stress override, not automatic minimum sizing. No full legacy unknown-state equivalence or physical adoption.')
(B/'source-freeze04.json').write_text(json.dumps(f,indent=2)+'\n')
print(dict(freeze=pin(B/'source-freeze04.json'),inputs=len(f['sources'])))
