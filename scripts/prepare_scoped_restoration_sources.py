"""Materialize and authenticate original source only; no native archive acquisition."""
import hashlib,json,os,re,subprocess,sys
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
    import prepare_mainchip_targeted_counterpart_inputs as derived
    cfg=json.loads((ORIGINAL/derived.M).read_bytes())
    generated={cfg['materialized_directory']+'/'+n for n in cfg['inputs']}
    assert generated=={'targeted-routing-inputs/'+n for n in ('counterparts.json','insertion_plan.json','summary.json')}
    missing={n for n in m['files']if not (ORIGINAL/n).is_file()}
    assert missing==generated,('only documented derived inputs may be absent',sorted(missing))
    for n,digest in m['files'].items():
        if n in generated:continue
        path=ORIGINAL/n
        assert path.is_file()and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,n
    for n,pin in cfg['source_files'].items():
        raw=(ORIGINAL/n).read_bytes()
        assert len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],n
    release=derived.api('releases/430116200')
    assert release['id']==430116200 and release['tag_name']=='cloud-results-41230348060-1-mainchip-stale-wire-terminal-readback'
    assert release['target_commitish']=='a472ca9f5955d28d8767b8f51aa34ba553b9b699'and release['draft']is False
    ref=derived.api('git/ref/tags/'+release['tag_name'])
    assert ref['object']['type']=='commit'and ref['object']['sha']==release['target_commitish']
    asset=next(a for a in release['assets']if a['id']==696171435)
    pin=cfg['inputs']['insertion_plan.json']
    assert asset['name']==pin['asset_name']and asset['size']==pin['bytes']and asset['digest']=='sha256:'+pin['sha256']
    dest=ORIGINAL/cfg['materialized_directory'];dest.mkdir(exist_ok=False)
    for n,pin in cfg['inputs'].items():
        assert '/'not in n and chr(92)not in n and n.endswith('.json')
        raw=derived.remote(pin)
        assert len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],n
        assert m['files'][cfg['materialized_directory']+'/'+n]==pin['sha256']
        json.loads(raw);(dest/n).write_bytes(raw)
    assert frozen.source_gate()==m
    out=ROOT/'scoped-restoration-controls';out.mkdir(exist_ok=True)
    raw=(ORIGINAL/MANIFEST).read_bytes()
    (out/'original-source-qualification.json').write_text(json.dumps(dict(source=BASE,
        files=len(m['files']),manifest=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
        all_original_sources_exact=True,derived_inputs=cfg['inputs'],
        derived_release=release['id'],original_source=BASE,adapter_source=os.environ['GITHUB_SHA'],
        native_acquisition=False,native_executed=False),indent=2)+'\n')
if __name__=='__main__':main()
