"""Additive freeze after completed stdout: preserve freeze01 and all six products."""
from pathlib import Path
import hashlib,json,difflib
B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
old=B/'source-freeze01.json';f=json.loads(old.read_text());bad=[]
for p,expected in f['inputs'].items():
 if pin(p)!=expected:bad.append(p)
assert bad==[str(B/'freeze01.log')],bad
assert f['inputs'][bad[0]]==dict(bytes=0,sha256=hashlib.sha256(b'').hexdigest())
assert pin(bad[0])==dict(bytes=100,sha256='f1fbbdd8bdb35bc7055fc5d279a7c33c647f21a0994690c533824356d303bb6b')
f['inputs'][bad[0]]=pin(bad[0])
f['inputs'].update({str(p):pin(p) for p in [old,B/'source-peer-findings01-rx.json',B/'prepare_launch02.py',Path(__file__)]})
a=(B/'prepare_launch01.py').read_text();b=(B/'prepare_launch02.py').read_text()
assert b==a.replace("fpath=B/'source-freeze01.json'","fpath=B/'source-freeze02.json'").replace("assert peer['source_pins']==f['product_sources']","assert peer['freeze']==pin(fpath)\nassert peer['source_pins']==f['product_sources']")
bridge=B/'source-supplement02.json';bridge.write_text(json.dumps(dict(status='PRESERVE_ORIGINAL_FREEZE_AND_COMPLETE_STDOUT_PIN',old=pin(old),only_changed_prior_pin=dict(path=bad[0],before=dict(bytes=0,sha256=hashlib.sha256(b'').hexdigest()),after=pin(bad[0])),preparer_before=dict(path=str(B/'prepare_launch01.py'),**pin(B/'prepare_launch01.py')),preparer_after=dict(path=str(B/'prepare_launch02.py'),**pin(B/'prepare_launch02.py')),complete_diff=''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True)))),indent=2)+'\n')
f['inputs'][str(bridge)]=pin(bridge)
f['freeze_correction']='Only completed freeze01.log replaces its accidentally captured empty open stdout pin. Original freeze01 retained; six products and launch01 byte-identical. Preparer02 binds this new freeze and peer explicitly. This freezer stdout must be outside B.'
f['inputs']=={p:pin(p) for p in f['inputs']}
assert f['product_sources']=={p:pin(p) for p in f['product_sources']}
q=B/'source-freeze02.json';assert not q.exists();q.write_text(json.dumps(f,indent=2)+'\n');print(len(f['inputs']),pin(q))
