"""Independent saved-byte/source review; no DUT or producer imports/execution."""
from pathlib import Path
import ast, hashlib, json, re, tarfile, xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def patch(old,diff):
 lines=old.splitlines(True);d=diff.splitlines(True);out=[];at=0;i=2
 while i<len(d):
  m=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',d[i]);assert m
  start=int(m[1])-1;assert start>=at;out+=lines[at:start];at=start;i+=1
  while i<len(d) and not d[i].startswith('@@ '):
   tag,body=d[i][0],d[i][1:];assert tag in ' +-'
   if tag in ' -':assert lines[at]==body;at+=1
   if tag in ' +':out.append(body)
   i+=1
 out+=lines[at:];return ''.join(out)
f=read(B/'source-freeze03.json');old=read(B/'source-freeze02.json');c=read(B/'diagnostic-correction03.json')
assert len(f['sources'])==193 and len(f['product_sources'])==10
for p,h in f['sources'].items():assert pin(R/p)==h,p
for p,h in f['product_sources'].items():assert pin(R/p)==h,p
changed=[p for p in old['sources'] if f['sources'][p]!=old['sources'][p]]
assert len(changed)==1 and changed[0].endswith('/sw/tests/test_pcie_gen3_integrity_v24_miter.py'),changed
assert f['selected_tools']==old['selected_tools'] and f['profile']==old['profile']
for p,h in old['product_sources'].items():
 snapshot=Path(c['source_snapshot'])/(Path(p).relative_to(R) if Path(p).is_absolute() else Path(p))
 assert pin(snapshot)==h
 assert p in f['product_sources']
for b in c['whole_bridges']:
 for key in ('parent','candidate'):assert pin(b[key]['path'])=={k:b[key][k] for k in ('bytes','sha256')}
 assert patch(Path(b['parent']['path']).read_text(),b['whole_diff'])==Path(b['candidate']['path']).read_text()
assert len(c['whole_bridges'])==3
m=c['whole_bridges'][0];a=Path(m['parent']['path']).read_text();z=Path(m['candidate']['path']).read_text()
addition='''    ) or (
        # This named mutation now first trips the independent consumed-mode
        # observer. Accept only its precise native fatal, never any error.
        fault == "header_carried_always_bad"
        and result.returncode != 0
        and re.search(
            r"FATAL: [^\\n]+:\\d+: V24_CONTEXT_CONSUMED_MODE word=1\\n"
            r"\\s+Time: \\d+  Scope: soc_pcie_gen3_continuous_rx_integrity_v24\\n",
            log,
        ) is not None
'''
assert z.count(addition)==1 and z.replace(addition,'')==a
# The original assertion is the first OR branch; new branch permits this fault only.
fn=next(n for n in ast.parse(z).body if isinstance(n,ast.FunctionDef) and n.name=='test_actual_miter_fault_is_observed')
expr=next(n.test for n in ast.walk(fn) if isinstance(n,ast.Assert) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.op,ast.Or))
assert len(expr.values)==2 and isinstance(expr.values[1].op,ast.And)
regex=next(n.args[0].value for n in ast.walk(expr.values[1]) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='search')
v=read(B/'controls01-final-validation.json');assert pin(c['history_validation']['path'])=={k:c['history_validation'][k]for k in ('bytes','sha256')}
assert v['pytest']['passed']==41 and v['pytest']['failed']==1
assert pin(v['archive']['path'])=={k:v['archive'][k]for k in ('bytes','sha256')}
manifest=read(B/'controls01-final-members.json');assert pin(B/'controls01-final-members.json')==v['member_manifest'];assert len(manifest)==418
saved={};count=0
with tarfile.open(v['archive']['path'],'r:xz') as tf:
 for member in tf:
  assert member.isfile()
  raw=tf.extractfile(member).read();h=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  if member.name=='members.json':assert raw==(B/'controls01-final-members.json').read_bytes()
  else:assert member.name in manifest and h=={k:manifest[member.name][k]for k in h}
  if h in [v['xml'],v['failure']['log'],v['failure']['result']]:saved[h['sha256']]=raw
  count+=1
assert count==419
cases=list(ET.fromstring(saved[v['xml']['sha256']]).iter('testcase'));fail=[x for x in cases if x.find('failure')is not None or x.find('error')is not None]
assert len(cases)==42 and len(fail)==1 and fail[0].get('name')==v['failure']['test']
log=saved[v['failure']['log']['sha256']].decode();result=json.loads(saved[v['failure']['result']['sha256']]);assert re.search(regex,log)
assert 'Time: 50000  Scope: soc_pcie_gen3_continuous_rx_integrity_v24' in log
for bad in [log.replace('word=1','word=2'),log.replace('Scope: soc_pcie_gen3_continuous_rx_integrity_v24','Scope: wrong'),log.replace('FATAL:','ERROR:')]:assert not re.search(regex,bad)
# Compare unchanged runtime guard function ASTs, in addition to complete source bridge reads.
for name in ('launch_controls','detach_controls'):
 aa=ast.parse((B/(name+'02.py')).read_text());bb=ast.parse((B/(name+'03.py')).read_text())
 for n in aa.body:
  if isinstance(n,ast.FunctionDef) and n.name!='save':
   nn=next(x for x in bb.body if isinstance(x,ast.FunctionDef)and x.name==n.name);assert ast.dump(n,include_attributes=False)==ast.dump(nn,include_attributes=False)
assert not (B/'status03.json').exists() and not Path('/dev/shm/nssoc-integrity-v24-diagnostic-controls03').exists()
out=dict(status='PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION',freeze=pin(B/'source-freeze03.json'),launcher=pin(B/'launch_controls03.py'),detacher=pin(B/'detach_controls03.py'),findings=[],reviewer='vco_loaded_feedback',method=pin(__file__),reviewer_attempts=['attempt01 corrected relative product snapshot path handling','attempt02 corrected418 payloads plus1 embedded manifest census; all419 archive members independently checked'],previous_peer=pin(B/'source-only-peer-vco02.json'),diagnostic_bridge=pin(B/'diagnostic-correction03.json'),history_validation=pin(B/'controls01-final-validation.json'),archive=v['archive'],full_members_rehashed=count,source_count=len(f['sources']),source_pins=f['product_sources'],checks=['All193 current pins and ten previous product snapshots rehashed. Only host miter diagnostic predicate changed; RTL, test stimuli, observers and nine other products remain identical.','All three whole forward source bridges independently reconstructed. Host change independently removed to recover complete prior file; new OR branch retains nonzero native result and is restricted to header_carried_always_bad plus exact consumed-mode word1 fatal/time/scope format.','All419 historical archive members rehashed; independently parsed actual42-case XML as41PASS/1FAIL. Saved mutated native fatal is word1 at50ns in the actual continuous wrapper. Historical host FAIL remains retained; regex independently rejects wrong word, wrong scope and nonfatal ERROR.','Full launcher/detacher read; only targeted two tests, pins and fresh03 paths/classification change. Same CPU6/2GiB,1GiB entry528MiB continuous/terminal floor, source/runtime gates, post-complete/post-context cancellation checks, sanitized detached launch and no healthy timeout.','No reviewed producer, HDL, tests or native mapping executed. Actual two targeted predicates and independent merged control acceptance remain required.'])
(B/'source-only-peer-vco03.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'receipt':pin(B/'source-only-peer-vco03.json'),'status':out['status']}))
