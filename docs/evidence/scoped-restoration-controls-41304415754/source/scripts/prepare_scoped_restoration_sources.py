"""Materialize and authenticate original source only; no native archive acquisition."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'original'
BASE='7a0776718ec37a106b7dfde0cbd477c6a2a5522f'
MANIFEST='scripts/mainchip-bounded-route-host-pins.json'
def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ORIGINAL,text=True).strip()==BASE
    m=json.loads((ORIGINAL/MANIFEST).read_bytes())
    paths=set(m['files'])|{MANIFEST}
    assert len(m['files'])==2361
    for n in paths:assert not n.startswith('/')and '..'not in n.split('/')
    patterns=['/'+re.sub(r'([*?\[\]\\])',r'\\\1',n)for n in sorted(paths)]
    subprocess.run(['git','sparse-checkout','set','--no-cone','--stdin'],cwd=ORIGINAL,
        input='\n'.join(patterns)+'\n',text=True,check=True)
    sys.path.insert(0,str(ORIGINAL/'scripts'))
    import cloud_mainchip_bounded_route_stage as frozen
    assert frozen.source_gate()==m
    out=ROOT/'scoped-restoration-controls';out.mkdir(exist_ok=True)
    raw=(ORIGINAL/MANIFEST).read_bytes()
    (out/'original-source-qualification.json').write_text(json.dumps(dict(source=BASE,
        files=len(m['files']),manifest=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
        all_original_sources_exact=True,native_acquisition=False,native_executed=False),indent=2)+'\n')
if __name__=='__main__':main()
