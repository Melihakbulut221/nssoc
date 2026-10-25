#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate existing current500 captures. Network/archive functions are cloud-only."""
import hashlib,json,os,re,subprocess,tarfile
from pathlib import Path,PurePosixPath
import numpy as np
import cloud_tx_stream as stream
import cloud_cdr_v59_loaded as original
import cdr_v58_saved_rows as rows
from cloud_verified_parts import JoinedParts
from cloud_chunked_results import verify_parts
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-headroom-readback-methods.json'
RUN=40219397958
HEAD='92a8253dd3410dd33bf34c1f7225991cf588d85d'
MODEL='current-mim-bundle/stage/composition/pd500-mim-wire.spice'
CONTRACT='current-mim-bundle/stage/composition/composition.json'
PLANES='current-mim-bundle/stage/precise/source/native-planes.json'
SELECT=('native/wave.raw','native/native.log','native/bench.cir','native/original-bench.cir','native/op.dat',MODEL,CONTRACT,PLANES,'native-controller-result.json')
API='repos/Melihakbulut221/nssoc/'
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def methods():
    m=json.loads((ROOT/METHOD).read_bytes())
    for p,h in m['protected'].items():
        path=ROOT/p;assert path.is_file()and not path.is_symlink()and sha(path)==h,p
    assert m['original_source']==HEAD and m['original_run']==RUN
    assert all(m[k]is False for k in ('simulation_authorized','extraction_authorized','geometry_authorized','electrical_acceptance'))
    return m
def reference(case,m):
    assert case in ('nominal_early','nominal_late')
    pin=m['cases'][case];prefix=pin['prefix']
    def read(suffix):
        p=prefix+suffix;assert sha(ROOT/p)==m['protected'][p];return json.loads((ROOT/p).read_bytes())
    outer,native,parts,receipt=map(read,('.summary.json','.native-result.json','.parts.json','.json'))
    validate_reports(case,pin,outer,native,parts,m['protected'][prefix+'.native-result.json'])
    return pin,outer,native,parts,receipt
def validate_reports(case,pin,outer,native,parts,native_sha):
    assert pin['case']==case and native['case']==outer['case']==case
    assert native['source_head']==outer['source_head']==HEAD
    assert outer['run_id']==RUN and outer['run_attempt']==1 and outer['preparation_only']is False
    assert outer['status']=='REJECTED_OR_FAILED_CURRENT_V59_LOADED_CASE'and outer['command']['returncode']==1
    assert native['status']=='REJECTED_WHOLE_MIM_PD500_LOADED'and native['returncode']==0
    assert native['error']=="AssertionError('Actual whole-wire retimed sampling, loaded phase/current or device gate failed')"
    assert not native['diagnostics']and native['native_flags_verified']==124 and native['zero_source_op_maximum']==0
    assert not native['actual_fault_detected']and not native['devices_passed']and not native['data_passed']and not native['vi']['passed']
    assert native['sources_unchanged']is True
    assert native['current_saved_input_integrity']==dict(files=5549,all_hashes_unchanged=True)
    for r in (outer,native):assert all(r[k]is False for k in ('accepted','cdr_accepted','full_phy_accepted','qualified_pex'))
    assert outer['outputs']['native-controller-result.json']==outer['native_controller_result_sha256']==native_sha
    assert {k:outer['outputs'][k]for k in native['outputs']}==native['outputs']
    assert len(native['outputs'])==5639 and len(outer['outputs'])==5641
    assert len(native['vectors'])==len(set(native['vectors']))==1151
    assert native['raw_capture']['raw_sha256']==native['outputs']['native/wave.raw']==pin['wave_sha256']
    assert native['raw_capture']['header_rows']==113475 and native['raw_capture']['columns']==1152
    assert native['source_bits']==original.primitive.prbs(0x7f)
    assert hashlib.sha256(bytes(native['source_bits'])).hexdigest()==native['source_bits_sha256']
    assert native['data_offset_s']==(-.15 if case=='nominal_early'else .15)*rows.UI
    assert parts==pin['parts']
    assert parts['source_directory']=='cloud-cdr-v59-loaded-'+case
    assert parts['stem']=='cdr-v59-loaded-'+case+'-'+str(RUN)+'-1'
    assert [p['index']for p in parts['parts']]==list(range(len(parts['parts'])))
    assert len({p['name']for p in parts['parts']})==len(parts['parts'])
    assert sum(p['bytes']for p in parts['parts'])==parts['bytes']
    assert parts['verification']['all_parts_and_combined_bytes_verified']is True
    return True
def identity(run,job,release,tag,pin):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['event']=='workflow_dispatch'and run['workflow_id']==396169705
    assert run['path']=='.github/workflows/cdr-v59-loaded-cloud.yml'
    assert job['id']==pin['job_id']and job['name']=='loaded ('+pin['case']+')'
    assert job['run_id']==RUN and job['run_attempt']==1 and job['head_sha']==HEAD
    assert job['status']=='completed'and job['conclusion']=='failure'
    assert release['id']==pin['release_id']and release['tag_name']==pin['tag']
    assert release['target_commitish']==HEAD and release['prerelease']is True and release['draft']is False
    assert tag['object']['type']=='commit'and tag['object']['sha']==HEAD
    return True
def asset_identity(actual,pin):
    assert {k:actual[k]for k in ('id','name','size','digest')}==pin
    assert actual['state']=='uploaded'and re.fullmatch(r'sha256:[0-9a-f]{64}',pin['digest'])
def api(path):return json.loads(subprocess.check_output(['gh','api',API+path,'--allow-escape-sequences']))
def cloud_guard(m):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    assert m['readback_authorized']is True
def download(pin,target,m):
    cloud_guard(m);asset_identity(api('releases/assets/'+str(pin['id'])),pin)
    with Path(target).open('xb')as f:
        p=subprocess.run(['gh','api',API+'releases/assets/'+str(pin['id']),'-H','Accept: application/octet-stream','--allow-escape-sequences'],stdout=f)
    assert p.returncode==0 and Path(target).stat().st_size==pin['size']and sha(target)==pin['digest'][7:]
def relative(name,prefix):
    assert isinstance(name,str)and name and chr(92)not in name and '\x00'not in name and ':'not in name
    p=PurePosixPath(name)
    assert str(p)==name and not p.is_absolute()and '..'not in p.parts and p.parts[0]==prefix
    return str(p.relative_to(prefix))
def extract(manifest,parts_dir,dest,outer,summary_hash):
    assert not dest.exists();dest.mkdir()
    archive=verify_parts(manifest,parts_dir)
    expected={**outer['outputs'],'result.json':summary_hash}
    wanted=set(SELECT)|{'result.json'}
    assert wanted<=set(expected)
    seen=set();files=set();proof={}
    with JoinedParts([parts_dir/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as tar:
            for item in tar:
                p=relative(item.name,manifest['source_directory'])
                assert item.name not in seen and(item.isfile()or item.isdir())
                seen.add(item.name)
                if item.isdir():continue
                assert p in expected and p not in files;files.add(p)
                target=None
                if p in wanted:
                    target=dest/p;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();size=0
                handle=target.open('xb')if target else None
                try:
                    with tar.extractfile(item)as f:
                        while b:=f.read(4*1024**2):
                            size+=len(b);h.update(b)
                            if handle:handle.write(b)
                finally:
                    if handle:handle.close()
                assert size==item.size and h.hexdigest()==expected[p],p
                if target:proof[p]=dict(bytes=size,sha256=h.hexdigest())
    assert files==set(expected)and set(proof)==wanted
    return dict(archive=archive,all_member_hashes_verified=len(files),selected=proof)
def restore(case,out,m):
    cloud_guard(m);pin,outer,native,manifest,receipt=reference(case,m)
    identity(api('actions/runs/'+str(RUN)),api('actions/jobs/'+str(pin['job_id'])),
        api('releases/'+str(pin['release_id'])),api('git/ref/tags/'+pin['tag']),pin)
    out.mkdir(exist_ok=False);parts_dir=out/'transport';parts_dir.mkdir()
    for label,suffix in [('summary','.summary.json'),('native','.native-result.json'),('manifest','.parts.json')]:
        p=parts_dir/(label+'.json');download(pin['assets'][label],p,m)
        assert p.read_bytes()==(ROOT/(pin['prefix']+suffix)).read_bytes()
    for p in manifest['parts']:download(pin['assets'][p['name']],parts_dir/p['name'],m)
    saved=out/'saved'
    proof=extract(manifest,parts_dir,saved,outer,m['protected'][pin['prefix']+'.summary.json'])
    assert (saved/'native-controller-result.json').read_bytes()==(ROOT/(pin['prefix']+'.native-result.json')).read_bytes()
    assert (saved/'result.json').read_bytes()==(ROOT/(pin['prefix']+'.summary.json')).read_bytes()
    return saved,native,proof
def validate_native(saved,report):
    contract=json.loads((saved/CONTRACT).read_bytes());planes=json.loads((saved/PLANES).read_bytes())
    bound=original.bind_native((saved/MODEL).read_text(),contract,planes)
    assert bound==report['binding']and bound['groups']['npn13g2']==report['devices']
    assert bound['groups']['sg13_lv_nmos']==report['mos_devices']and bound['groups']['cap_cmim']==report['native_caps']
    nodes={n for g in bound['groups'].values()for dev in g.values()for n in dev['nodes']}|set(bound['ports'])|set(bound['aliases'].values());nodes.discard('0')
    vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in report['devices']]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in report['mos_devices']]
    assert vectors==report['vectors']
    deck=(saved/'native/original-bench.cir').read_text()
    assert (saved/'native/bench.cir').read_text()==stream.streaming_deck(deck,dict(vectors=vectors))
    for net,point in bound['sampler_points'].items():assert deck.count(f'C_{net} {point} 0 150f\n')==1
    for n in ('xp','xn','yp','yn'):assert deck.count(f'C_{n} {n} 0 50f\n')==1
    log=(saved/'native/native.log').read_text()
    opts,notes,_=original.backend_readback(log,'klu')
    assert opts==report['native_options']and notes==report['diagnostics']==[]
    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
    assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in report['devices']]
    assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
    op=np.loadtxt(saved/'native/op.dat',skiprows=1)
    assert op.size==1152 and np.isfinite(op).all()and float(abs(op).max())==report['zero_source_op_maximum']==0
    t,d,capture=stream.read_streamed_wave(saved/'native/wave.raw',vectors,rows.STOP,rows.STEP)
    assert capture==report['raw_capture']
    frozen=(ROOT/'scripts/cloud_cdr500_v58_loaded.py').read_text()
    block=''.join(frozen.splitlines(keepends=True)[274:333])
    assert block in (ROOT/'scripts/cloud_cdr_v59_loaded.py').read_text()
    reproduced=rows.replay(frozen,t,d,capture,report)
    return t,d,contract,reproduced
