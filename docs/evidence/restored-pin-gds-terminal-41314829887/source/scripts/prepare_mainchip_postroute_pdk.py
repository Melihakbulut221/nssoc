#!/usr/bin/env python3
"""Restore the exact original LibreLane PDK, and export tool-owned input files.
Hosted-only. Native routing, extraction and STA are never started here.
"""
import hashlib,json,os,shutil,sys,tarfile,tempfile,urllib.request
from pathlib import Path
import ciel
import librelane
import zstandard as zstd
from ciel.source import StaticWebDataSource
from librelane.common import get_pdk_hash
ROOT=Path(__file__).resolve().parents[1]
REV='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
ARCHIVES={
 'common.tar.zst':(384869154,'ed6b5583b8607a6c3f03011bc8fc1735a3e35e1191bee335bcff6f5a5340ffd1'),
 'sg13g2_io.tar.zst':(12837819,'0abc1a6c269f064a9fb31252f751f04a2e63098523b96d0659c05c5296262db6'),
 'sg13g2_pr.tar.zst':(175934,'95c328dd7486cccab4d48fdc5370f628dccd461a9fe266739523a629a5544f1a'),
 'sg13g2_sram.tar.zst':(2418451,'185f266584d85a316dcc518af46a04f20f46a47deda040946d43cbce81dac6af'),
 'sg13g2_stdcell.tar.zst':(6262256,'c3dec00ae2cc4a894c5d2478c9e049e38ae0bc1635a55a7d5e0993b1c73879ab')}
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    config_path=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
    cfg=json.loads(config_path.read_text())
    assert get_pdk_hash('ihp-sg13g2')==REV
    home=ciel.get_ciel_home(str(ROOT/'hw/soc/tools/ciel-corrpre'))
    # Exact API, default libraries and static source used by the original 3.0.5 CLI.
    version=ciel.fetch(home,'ihp-sg13g2',REV,
        data_source=StaticWebDataSource('https://fossi-foundation.github.io/ciel-releases'),
        include_libraries=['default','sg13g2_stdcell'])
    version_dir=Path(version.get_dir(home))
    assert version_dir==Path(cfg['PDK_ROOT'])
    records={};archives={}
    # Ciel's version identifier alone is insufficient: compare each installed
    # member against the independently SHA256-pinned upstream release archives.
    with tempfile.TemporaryDirectory(prefix='exact-pdk-',dir=out)as td:
        for name,(size,digest)in ARCHIVES.items():
            path=Path(td)/name
            url='https://github.com/fossi-foundation/ciel-releases/releases/download/ihp-sg13g2-'+REV+'/'+name
            with urllib.request.urlopen(url,timeout=120)as src,path.open('xb')as dst:
                shutil.copyfileobj(src,dst)
            assert path.stat().st_size==size and sha(path)==digest,(name,'upstream archive identity')
            members=0
            with zstd.open(path,'rb')as stream,tarfile.open(fileobj=stream,mode='r:')as tf:
                for member in tf:
                    if member.isdir():continue
                    rel=Path(member.name)
                    assert not rel.is_absolute()and '..'not in rel.parts
                    assert rel.parts[0]=='ihp-sg13g2'
                    target=version_dir/rel
                    assert target.is_file(),('Missing original Ciel member',str(rel))
                    src=tf.extractfile(member);assert src is not None
                    digest_state=hashlib.sha256();member_bytes=0
                    while chunk:=src.read(1024**2):digest_state.update(chunk);member_bytes+=len(chunk)
                    expected=digest_state.hexdigest()
                    assert sha(target)==expected and target.stat().st_size==member_bytes,(name,str(rel),'installed member mismatch')
                    key=str(target.relative_to(ROOT))
                    record=dict(sha256=expected,bytes=target.stat().st_size,archive=name)
                    if key in records:assert records[key]['sha256']==expected
                    records[key]=record;members+=1
            archives[name]=dict(bytes=size,sha256=digest,verified_members=members)
            path.unlink()
    tool_paths=set()
    def visit(v):
        if isinstance(v,dict):
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
        elif isinstance(v,str)and v.startswith('/nix/store/'):tool_paths.add(v)
    visit(cfg)
    tools={}
    for value in sorted(tool_paths):
        p=Path(value)
        # At present the full resolved config has exactly the runtime base SDC.
        assert p==Path(librelane.__file__).parent/'scripts/base.sdc',('Unexpected tool input',value)
        assert p.is_file()
        dst=out/'tool-files'/p.relative_to('/')
        dst.parent.mkdir(parents=True);shutil.copyfile(p,dst)
        assert sha(dst)==sha(p)
        tools[value]=dict(exported=str(dst.relative_to(out)),sha256=sha(p),bytes=p.stat().st_size)
    assert len(tools)==1
    report=dict(status='PASS_PINNED_ORIGINAL_PDK_ARCHIVES_AND_TOOL_INPUTS_ONLY',
        pdk_revision=REV,pdk_root=str(version_dir),config_sha256=sha(config_path),
        archives=archives,installed_files=records,tool_files=tools,
        native_routing_started=False,final_timing_complete=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(records),flush=True)
if __name__=='__main__':main()
