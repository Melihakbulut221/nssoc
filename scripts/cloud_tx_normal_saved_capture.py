#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted read-only restore of one completed rejected TX capture, no engine."""
import argparse,base64,copy,hashlib,io,json,os,re,shutil,subprocess,tarfile,tempfile,traceback
from pathlib import Path,PurePosixPath
import tx_normal_saved_capture_diagnosis as observer
from cloud_verified_parts import JoinedParts,extract_verified,controls as selected_archive_controls
from cloud_chunked_results import verify_parts,pack,controls as parts_controls
import ensure_cloud_tested_source_release as release
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
GROUP='tx-normal-saved-capture-diagnosis'
OUT=ROOT/('cloud-'+GROUP)
METHOD=ROOT/'scripts/tx-normal-saved-capture-cloud-methods.json'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(path):
    return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def write(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    Path(path).write_bytes(raw)
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def methods():
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected_files'].items():assert sha(ROOT/p)==h,p
    assert not m['native_simulation_authorized']
    return m

def source_identity(run,info,ref,spec):
    assert run['id']==spec['run'] and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']==spec['conclusion']
    assert run['head_sha']==spec['source'] and run['head_branch']==spec['branch']
    assert run['path']==spec['workflow']
    return release.validate_release(info,ref,spec['tag'],spec['source'])

def precreated(group):
    tag,source=release.context(group,os.environ)
    return release.validate_release(api('releases/tags/'+tag),api('git/ref/tags/'+tag),tag,source)

def fetch_asset(row,target):
    assert not target.exists()
    with target.open('xb') as out:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
                        REPO+'releases/assets/'+str(row['id'])],stdout=out,check=True)
    assert target.stat().st_size==row['bytes'] and sha(target)==row['sha256']

def restore_parts(spec,manifest,folder):
    run=api('actions/runs/'+str(spec['run']))
    info=api('releases/tags/'+spec['tag']);ref=api('git/ref/tags/'+spec['tag'])
    identity=source_identity(run,info,ref,spec)
    assets={a['name']:a for a in info['assets']};assert len(assets)==len(info['assets'])
    folder.mkdir(exist_ok=False)
    for p in manifest['parts']:
        a=assets[p['name']]
        assert a['size']==p['bytes'] and a['digest']=='sha256:'+p['sha256']
        assert a['id']==spec['part_asset_ids'][p['index']]
        fetch_asset(dict(id=a['id'],bytes=p['bytes'],sha256=p['sha256']),folder/p['name'])
    return identity

def safe_relative(entry,prefix):
    raw=entry.name.rstrip('/') if entry.isdir() else entry.name
    p=PurePosixPath(raw)
    assert raw and '\\' not in raw and not p.is_absolute() and '..' not in p.parts
    assert p.as_posix()==raw and p.parts[0]==prefix
    assert entry.isdir() or entry.isfile(), 'Link/special archive entry refused'
    return '/'.join(p.parts[1:])

def audit_complete(manifest,parts,destination,expected,selected):
    """Hash every original file, retain only exact analysis members; no extractall."""
    proof=verify_parts(manifest,parts)
    prefix=manifest['source_directory'];assert PurePosixPath(prefix).name==prefix
    assert set(selected)<=set(expected) and not destination.exists()
    destination.mkdir(parents=True);seen=set();found={};directories=[]
    with JoinedParts([parts/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as archive:
            for member in archive:
                name=safe_relative(member,prefix)
                assert name not in seen, 'Duplicate archive path';seen.add(name)
                if member.isdir():directories.append(name);continue
                assert name in expected,('Unrecorded original file',name)
                total=0;h=hashlib.sha256();out=None
                if name in selected:
                    path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);out=path.open('xb')
                try:
                    with archive.extractfile(member)as src:
                        while b:=src.read(4*1024**2):
                            h.update(b);total+=len(b)
                            if out is not None:out.write(b)
                finally:
                    if out is not None:out.close()
                assert total==member.size and h.hexdigest()==expected[name],('Changed original file',name)
                found[name]=dict(bytes=total,sha256=h.hexdigest(),retained=name in selected)
    assert set(found)==set(expected),'Missing original files'
    return dict(archive=proof,all_original_files=found,directories=directories,
                complete_inventory_and_bytes_verified=True,native_image_executed=False)

def validate_contract(contract,bench,model,qualified):
    frozen=observer.frozen_functions(json.loads((ROOT/observer.METHOD).read_bytes())['protected_files'])
    assert contract['fault']=='none' and contract['streams']==32
    assert contract['bits']==frozen['sequence']() and len(contract['bits'])==256
    assert contract['source_bits_sha256']==hashlib.sha256(bytes(contract['bits'])).hexdigest()
    assert contract['condition']['step_ps']==.5 and contract['solver_profile']=='breakpoint_tight_trap'
    plan=frozen['tree_plan'](32)
    assert contract['tree_plan']['nodes']==plan['nodes'] and len(contract['tree_plan']['clocks'])==31
    for c,w in zip(contract['tree_plan']['clocks'],plan['clocks'],strict=True):
        assert {k:c[k]for k in ('name','origin','period')}==w
    assert len(contract['vectors'])==len(set(contract['vectors']))==14181
    assert len(contract['hbt'])==604 and len(contract['mos'])==5376
    assert observer.canonical(qualified)==observer.canonical(json.loads((ROOT/observer.ROLES).read_bytes()))
    roles=observer.catalog(contract,qualified)
    head=[r.lower().split()for r in model.splitlines()if r.lower().startswith('.subckt ')]
    assert len(head)==1 and len(set(head[0][2:]))==len(head[0][2:])
    cards=[r.lower().split()for r in bench.splitlines()if r.lower().startswith('xtree ')]
    assert len(cards)==1 and cards[0][-1]==head[0][1]
    mapping=dict(zip(head[0][2:],cards[0][1:-1],strict=True))
    def node(n):return mapping.get(n,'xtree.'+n)
    devices={};physical=[]
    for line in model.splitlines():
        r=line.lower().split()
        if not r or not re.fullmatch(r'xd[0-9]+',r[0]):continue
        physical.append(r[0])
        if len(r)>5 and (r[5]=='npn13g2' or r[5].startswith('sg13_') and ('nmos' in r[5] or 'pmos' in r[5])):
            q=dict(model=r[5],terminals=[node(n)for n in r[1:5]])
            if r[5]=='npn13g2':q['nx']=int(next(z.split('=')[1]for z in r[6:]if z.startswith('nx=')))
            devices['xtree.'+r[0]]=q
    assert len(physical)==len(set(physical))==8088
    expected={n:r for n,r in {**contract['hbt'],**contract['mos']}.items()if n.startswith('xtree.')}
    assert devices==expected and len(devices)==593+5376
    for n,r in contract['hbt'].items():
        assert r['model']=='npn13g2' and 1<=r['nx']<=10 and len(r['terminals'])==4
        assert '@q.'+n+'.qnpn13g2[ic]'in contract['vectors']
        assert all(v=='0' or 'v('+v+')'in contract['vectors']for v in r['terminals'])
    mapping=contract['interface_probes']
    assert len(mapping)==124 and all(len(v)==3 for v in mapping.values())
    assert len({n for v in mapping.values()for n in v})==372
    assert all('v('+n+')'in contract['vectors']for v in mapping.values()for n in v)
    return dict(actual_core_devices=8088,actual_core_hbts=593,actual_core_mos=5376,
        canonical_tree_hbts=len(roles),source_bits_unchanged=True,all_actual_terminal_and_Nx_projections_equal=True,
        original_clock_origins_and_half_periods_unchanged=True)

def actual_controls(contract,bench,model,qualified):
    positive=validate_contract(contract,bench,model,qualified);bad=[]
    def reject(label,change):
        c,b,m,q=copy.deepcopy((contract,bench,model,qualified));c,b,m,q=change(c,b,m,q)
        try:validate_contract(c,b,m,q)
        except(AssertionError,KeyError,ValueError,StopIteration):bad.append(label)
        else:raise AssertionError('Accepted actual input corruption '+label)
    def edit(fn):
        def change(c,b,m,q):fn(c);return c,b,m,q
        return change
    trials=[('source_bit',lambda c:c['bits'].__setitem__(0,1-c['bits'][0])),
      ('source_bit_hash',lambda c:c.__setitem__('source_bits_sha256','0'*64)),
      ('case',lambda c:c.__setitem__('fault','swap_leaf_select')),
      ('step',lambda c:c['condition'].__setitem__('step_ps',1.)),
      ('solver',lambda c:c.__setitem__('solver_profile','default')),
      ('clock_phase',lambda c:c['tree_plan']['clocks'][0].__setitem__('origin',c['tree_plan']['clocks'][0]['origin']+1e-12)),
      ('clock_period',lambda c:c['tree_plan']['clocks'][0].__setitem__('period',c['tree_plan']['clocks'][0]['period']*2)),
      ('selector_nx',lambda c:c['hbt']['xtree.xd5676'].__setitem__('nx',5)),
      ('selector_collector',lambda c:c['hbt']['xtree.xd5676']['terminals'].__setitem__(0,c['hbt']['xtree.xd5676']['terminals'][1])),
      ('selector_emitter',lambda c:c['hbt']['xtree.xd5676']['terminals'].__setitem__(2,'0')),
      ('selector_substrate',lambda c:c['hbt']['xtree.xd5676']['terminals'].__setitem__(3,'0')),
      ('missing_hbt',lambda c:c['hbt'].pop('xtree.xd5676')),
      ('missing_mos',lambda c:c['mos'].pop(next(iter(c['mos'])))),
      ('duplicate_vector',lambda c:c['vectors'].__setitem__(-1,c['vectors'][0])),
      ('missing_parallel_base',lambda c:next(iter(c['interface_probes'].values())).pop()),
      ('wrong_tree_selection',lambda c:c['tree_plan']['nodes'][0]['inputs'].reverse())]
    for name,fn in trials:reject(name,edit(fn))
    def role(c,b,m,q):q['binding']['all589_actual_devices'][0]['devices'][0]['role']='wrong';return c,b,m,q
    reject('changed_native_role',role)
    reject('missing_physical_model',lambda c,b,m,q:(c,b,'',q))
    reject('wrong_top_instance',lambda c,b,m,q:(c,b.replace('\nxtree ','\nwrongtree '),m,q))
    assert len(bad)==19
    return dict(positive=positive,rejected=bad,full_waveform_review_repeated=False)

def source_controls():
    m=methods();from check_tx_normal_saved_capture_diagnosis import main as math_controls
    math=math_controls();assert len(math['negative_controls'])==20
    parts=parts_controls();selected=selected_archive_controls();publication=release.controls()
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);d=root/'fixture';d.mkdir();(d/'a').write_bytes(b'actual\\x1b opaque bytes');(d/'b').write_bytes(b'keep inventory')
        manifest=pack(d,'fixture',root,32);expected={n:sha(d/n)for n in ('a','b')}
        positive=audit_complete(manifest,root,root/'good',expected,{'a'})
        assert (root/'good/a').read_bytes()==(d/'a').read_bytes() and not(root/'good/b').exists()
        bad=[]
        def reject(name,fn):
            try:fn()
            except(AssertionError,KeyError,FileNotFoundError):bad.append(name)
            else:raise AssertionError('Accepted transport fault '+name)
        reject('missing_inventory',lambda:audit_complete(manifest,root,root/'bad1',dict(expected,c='0'*64),{'a'}))
        reject('extra_inventory',lambda:audit_complete(manifest,root,root/'bad2',{'a':expected['a']},{'a'}))
        reject('changed_unselected_bytes',lambda:audit_complete(manifest,root,root/'bad3',dict(expected,b='0'*64),{'a'}))
        reject('unknown_selection',lambda:audit_complete(manifest,root,root/'bad4',expected,{'c'}))
        for name,path,kind in [('traversal','fixture/../x',tarfile.REGTYPE),('absolute','/fixture/x',tarfile.REGTYPE),
            ('backslash','fixture/\\x',tarfile.REGTYPE),('wrong_root','other/x',tarfile.REGTYPE),
            ('symlink','fixture/x',tarfile.SYMTYPE),('hardlink','fixture/x',tarfile.LNKTYPE),
            ('noncanonical','fixture//x',tarfile.REGTYPE)]:
            entry=tarfile.TarInfo(path);entry.type=kind
            reject(name,lambda entry=entry:safe_relative(entry,'fixture'))
        assert len(bad)==11
    return dict(status='PASS_SOURCE_MATH_AND_TRANSPORT_CONTROLS_ONLY',math=math,parts=parts,
        selected_archive=selected,strict_archive_faults=bad,publication=publication,
        readback_authorized=m['readback_authorized'],native_simulation=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true');a=p.parse_args()
    assert a.controls != a.readback and os.environ.get('GITHUB_ACTIONS')=='true'
    m=methods()
    if a.controls:print(json.dumps(source_controls(),indent=2));return
    assert m['readback_authorized'] is True
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        accepted=False,original_electrical_accepted=False,new_simulation=False,native_process_resumed=False,
        full_phy_accepted=False,mainchip_integrated=False,thermal_state_available=False)
    def save():write(OUT/'result.json',result)
    save();work=Path(os.environ['RUNNER_TEMP'])/'tx-normal-authenticated-capture'
    try:
        result['publication_preflight']=precreated(GROUP);save()
        assert shutil.disk_usage(work.parent).free >= 24*1024**3,'Need24GiB for exact existing capture restore'
        work.mkdir(exist_ok=False)
        source=json.loads((ROOT/observer.RESULT).read_bytes());parts=json.loads((ROOT/m['native_parts_path']).read_bytes())
        original_source=api('contents/scripts/cloud_tx_output8088_branchtailfeed_native.py?ref='+m['native_source']['source'])
        if not original_source.get('content'):original_source=api('git/blobs/'+original_source['sha'])
        assert hashlib.sha256(base64.b64decode(original_source['content'])).hexdigest()==source['controller_sha256']
        result['native_source_identity']=restore_parts(m['native_source'],parts,work/'native-parts');save()
        expected=dict(source['outputs']);expected['result.json']=m['source_summary_sha256']
        selected={'work/'+n for n in ('wave.raw','bench.cir','contract.json','native.log','op.dat')}
        result['native_archive']=audit_complete(parts,work/'native-parts',work/'native',expected,selected);save()
        prep=json.loads((ROOT/m['prepared_summary_path']).read_bytes());pp=json.loads((ROOT/m['prepared_parts_path']).read_bytes())
        assert prep['outputs']['whole8088/source/composed/output8088-wire.spice']==m['model_sha256']
        assert source['preparation_source']['summary_sha256']==m['prepared_summary_sha256']
        result['prepared_source_identity']=restore_parts(m['prepared_source'],pp,work/'prep-parts');save()
        chosen={n:prep['outputs'][n]for n in ('whole8088/source/composed/output8088-wire.spice','whole8088/source/composed/composition.json')}
        result['prepared_model_restore']=extract_verified(pp,work/'prep-parts',work/'model',chosen);save()
        model=(work/'model/whole8088/source/composed/output8088-wire.spice').read_text()
        case=work/'native/work';contract=json.loads((case/'contract.json').read_bytes());bench=(case/'bench.cir').read_text()
        qualified=json.loads((ROOT/observer.ROLES).read_bytes())
        result['actual_input_controls']=actual_controls(contract,bench,model,qualified);save()
        method=json.loads((ROOT/observer.METHOD).read_bytes())
        assert method['readback_authorized'] is True,'Core and wrapper require separate explicit reviewed authorization'
        diagnosis=observer.observe_restored(case,method)
        proof=write(OUT/'complete-native-row-diagnosis.json',diagnosis)
        compact=dict(status=diagnosis['status'],full_witness=proof,
            original_failed_samples=len(diagnosis['failed_sample_events']),failed_hbt_count=len(diagnosis['failed_hbt_same_row_witnesses']),
            native_frame_count=len(diagnosis['frames']),unclassified_output_roles=diagnosis['unmapped_full_output_devices'],
            original_rejection_reproduced=diagnosis['original_rejection_reproduced'],
            worst_device='xtree.xd5676',worst_device_extrema=diagnosis['failed_hbt_same_row_witnesses']['xtree.xd5676']['extrema'],
            thermal_state_available=False,causal_conclusion=False)
        write(OUT/'diagnostic-index.json',compact)
        result.update(status='PASS_SAVED_CAPTURE_DIAGNOSIS_ORIGINAL_TX_REJECTION_REMAINS',diagnostic_index=compact,
                      full_original_review_replays=1,source_capture_sha256=m['raw_sha256'])
    except BaseException as error:
        result.update(status='FAIL_SAVED_CAPTURE_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        save()
        raw=(OUT/'result.json').read_bytes();assert len(raw)<2*1024**2
        print('RESULT_SHA256',hashlib.sha256(raw).hexdigest());print('RESULT_BYTES',len(raw))
        data=base64.b64encode(raw).decode();chunks=[data[i:i+4096]for i in range(0,len(data),4096)]
        for i,c in enumerate(chunks):print(f'RESULT_BASE64 {i}/{len(chunks)} {c}')
if __name__=='__main__':main()
