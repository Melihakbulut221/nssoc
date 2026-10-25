#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted full immutable baseline restoration; no native import or model change."""
import ast, copy, hashlib, io, json, subprocess, tarfile, tempfile
from pathlib import Path, PurePosixPath
import cloud_chunked_results as chunks
import tx_phase_reset334_intrinsic_mim_source as source
ROOT=Path(__file__).resolve().parents[1]
REPO='Melihakbulut221/nssoc'
SOURCE=dict(run=40120130880,head='2e1f26e9c4fdf37d63433a0c859c2d305db3486b',
            group='tx-phase-reset244-physical',
            summary='5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913',
            parts='a6be15e92a1721ddd794ab75cce227e962f6ada294d5a54b0e58cc4778ec187b')
ROOT_NAME='cloud-tx-phase-reset244-physical'
STEM='tx-phase-reset244-physical-40120130880-1'
TAG='cloud-results-40120130880-1-tx-phase-reset244-physical'
BASELINE='docs/evidence/tx-phase-reset334-physical-full-result-20261024.json'
ASSETS={
 'summary':dict(id=672983363,name=STEM+'.summary.json',size=5644409,sha256=SOURCE['summary']),
 'parts':dict(id=672983475,name=STEM+'.parts.json',size=862,sha256=SOURCE['parts']),
 'archive':dict(id=672983547,name=STEM+'.tar.gz.part0000',size=3242850,
                sha256='839bba8877d625d7d66ef766cc3d17bd2885158f8a9b851d03ee12e88ae19b16')}
def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/'+path]))
def raw_asset(asset):
    b=subprocess.check_output(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
                               'repos/'+REPO+'/releases/assets/'+str(asset['id'])])
    assert len(b)==asset['size'] and digest(b)==asset['sha256']
    return b
def baseline():
    b=(ROOT/BASELINE).read_bytes();assert len(b)==ASSETS['summary']['size']and digest(b)==SOURCE['summary']
    prior=json.loads(b);validate(prior)
    return b,prior
def validate_release(release,ref):
    assert release['id']==422903518 and release['tag_name']==TAG
    assert release['target_commitish']==SOURCE['head'] and release['draft']is False
    assert ref['ref']=='refs/tags/'+TAG and ref['object']==dict(type='commit',sha=SOURCE['head'],url=ref['object']['url'])
    for expected in ASSETS.values():
        rows=[r for r in release['assets']if r['id']==expected['id']];assert len(rows)==1
        a=rows[0];assert a['name']==expected['name']and a['size']==expected['size']and a['state']=='uploaded'
        assert a['digest']=='sha256:'+expected['sha256']
def validate_manifest(manifest):
    a=ASSETS['archive']
    assert manifest['format']=='ordered-tar-gzip-parts-v1'
    assert manifest['stem']==STEM and manifest['source_directory']==ROOT_NAME
    assert manifest['bytes']==a['size']and manifest['sha256']==a['sha256']
    assert manifest['parts']==[dict(index=0,name=a['name'],bytes=a['size'],sha256=a['sha256'])]
def expected_files(prior):
    expected=dict(prior['outputs']);assert len(expected)==198 and 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];return expected

def audit_archive(path,expected,destination,root_name=ROOT_NAME):
    """Transport is authenticated before this function; stream every file, never select/skip."""
    assert not destination.exists();destination.mkdir(parents=True)
    seen=set();directories=set();inventory={}
    allowed_dirs={root_name}
    for name in expected:
        p=PurePosixPath(root_name)/name
        allowed_dirs.update(str(v)for v in p.parents if str(v)!='.')
    with tarfile.open(path,mode='r:gz')as archive:
        for member in archive:
            raw=member.name
            assert raw and '\\'not in raw and not raw.startswith('/')
            name=raw[:-1]if member.isdir()and raw.endswith('/')else raw
            p=PurePosixPath(name)
            assert str(p)==name and all(part not in ('','..','.')for part in p.parts)
            assert name not in seen;seen.add(name)
            assert p.parts[0]==root_name
            if member.isdir():
                assert name in allowed_dirs and member.size==0
                directories.add(name);continue
            assert member.isfile() and not member.issym()and not member.islnk()
            rel=str(p.relative_to(root_name));assert rel in expected
            target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();size=0;stream=archive.extractfile(member);assert stream is not None
            with target.open('xb')as output:
                while data:=stream.read(4*1024**2):h.update(data);size+=len(data);output.write(data)
            assert size==member.size and h.hexdigest()==expected[rel],('Baseline member digest',rel)
            inventory[rel]=dict(bytes=size,sha256=h.hexdigest())
    assert set(inventory)==set(expected)
    assert set(str(p.relative_to(destination))for p in destination.rglob('*')if p.is_file())==set(expected)
    return dict(files=inventory,all_files_streamed=True,directories=sorted(directories),
                unknown_duplicate_link_special_paths_rejected=True)
def restore(out):
    b,prior=baseline();run=api('actions/runs/'+str(SOURCE['run']));job=api('actions/jobs/120949804811')
    validate_run(run,job)
    release=api('releases/422903518');ref=api('git/ref/tags/'+TAG);validate_release(release,ref)
    assert raw_asset(ASSETS['summary'])==b
    manifest_bytes=raw_asset(ASSETS['parts']);manifest=json.loads(manifest_bytes);validate_manifest(manifest)
    transport=out/'baseline-transport';transport.mkdir();part=transport/ASSETS['archive']['name']
    with part.open('xb')as output:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
                        'repos/'+REPO+'/releases/assets/672983547'],stdout=output,check=True)
    assert part.stat().st_size==ASSETS['archive']['size']and sha(part)==ASSETS['archive']['sha256']
    proof=chunks.verify_parts(manifest,transport)
    destination=out/'baseline';audit=audit_archive(part,expected_files(prior),destination)
    assert (destination/'result.json').read_bytes()==b
    for pol in ('p','n'):
        assert json.loads((destination/pol/'layout/result.json').read_text())==prior['variants'][pol]['generation']
    return dict(source=SOURCE,release_id=release['id'],tag=TAG,manifest=manifest,transport=proof,
                directory=str(destination),inventory=audit,all199_files_authenticated=True,
                baseline_geometry_unchanged=True)

def unchanged(proof):
    root=Path(proof['directory'])
    expected=proof['inventory']['files']
    actual={str(p.relative_to(root)):p for p in root.rglob('*')if p.is_file()}
    assert set(actual)==set(expected)
    for name,p in actual.items():assert p.stat().st_size==expected[name]['bytes']and sha(p)==expected[name]['sha256']
    return True

def archive_controls():
    """Each malformed TAR has a fresh correct transport digest before structural audit."""
    rejected=[];positive=None
    payload={'result.json':b'{"original":"preserved"}\n','p/layout/a.gds':b'opaque baseline GDS'}
    expected={p:digest(b)for p,b in payload.items()}
    def build(path,mode):
        rows=[(ROOT_NAME+'/'+n,b,tarfile.REGTYPE)for n,b in payload.items()]
        if mode=='missing':rows.pop()
        elif mode=='unknown':rows.append((ROOT_NAME+'/unknown',b'x',tarfile.REGTYPE))
        elif mode=='duplicate':rows.append(rows[0])
        elif mode=='wrong_root':rows[0]=(rows[0][0].replace(ROOT_NAME,'wrong',1),rows[0][1],tarfile.REGTYPE)
        elif mode=='traversal':rows[0]=(ROOT_NAME+'/../outside',rows[0][1],tarfile.REGTYPE)
        elif mode=='absolute':rows[0]=('/'+rows[0][0],rows[0][1],tarfile.REGTYPE)
        elif mode=='backslash':rows[0]=(ROOT_NAME+'/a\\b',rows[0][1],tarfile.REGTYPE)
        elif mode=='dot_component':rows[0]=(ROOT_NAME+'/./result.json',rows[0][1],tarfile.REGTYPE)
        elif mode=='digest':rows[0]=(rows[0][0],rows[0][1]+b'changed',tarfile.REGTYPE)
        elif mode in ('symlink','hardlink','fifo'):
            rows[0]=(rows[0][0],b'',{'symlink':tarfile.SYMTYPE,'hardlink':tarfile.LNKTYPE,'fifo':tarfile.FIFOTYPE}[mode])
        elif mode=='unknown_directory':rows.append((ROOT_NAME+'/unexpected',b'',tarfile.DIRTYPE))
        with tarfile.open(path,'w:gz')as archive:
            for name,b,kind in rows:
                item=tarfile.TarInfo(name);item.type=kind;item.size=len(b)
                if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):item.linkname='/outside'
                archive.addfile(item,io.BytesIO(b)if kind==tarfile.REGTYPE else None)
    with tempfile.TemporaryDirectory()as tmp:
        base=Path(tmp)
        modes=('positive','missing','unknown','duplicate','wrong_root','traversal','absolute','backslash',
               'dot_component','digest','symlink','hardlink','fifo','unknown_directory')
        for i,mode in enumerate(modes):
            part=base/('fixture'+str(i)+'.tar.gz.part0000');build(part,mode)
            m=dict(format='ordered-tar-gzip-parts-v1',stem='fixture'+str(i),bytes=part.stat().st_size,
                   sha256=sha(part),parts=[dict(index=0,name=part.name,bytes=part.stat().st_size,sha256=sha(part))])
            transport=chunks.verify_parts(m,base);assert transport['all_parts_and_combined_bytes_verified']
            try:proof=audit_archive(part,expected,base/('out'+str(i)))
            except (AssertionError,KeyError,ValueError,tarfile.TarError):
                assert mode!='positive';rejected.append(mode)
            else:
                assert mode=='positive';positive=proof
    assert len(rejected)==13 and positive['all_files_streamed']
    return dict(positive=positive,rejected=rejected,valid_transport_before_each_archive_fault=True,
                inherited_parts_controls=chunks.controls())

# Byte-exact copied validators from the qualified physical/MIM admission controller.
def validate_run(run,job):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['path']=='.github/workflows/tx-phase-reset244-physical-cloud.yml'and run['head_branch']=='codex/tx-clock-phase-parent'
    assert run['status']=='completed'and run['conclusion']=='success'
    assert job['id']==120949804811 and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['head']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'

def validate(prior):
    assert prior['source_head']==SOURCE['head']and prior['sources_unchanged']and prior['validation_errors']==[]
    assert prior['status']=='PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET'
    assert set(prior['variants'])=={'p','n'}and len(prior['outputs'])==198
    for pol,v in prior['variants'].items():
        assert v['status']=='PASS_FRESH334_DRC_DEEP_FLAT_LVS9_FAULTS_AND1010_NATIVE_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_RESET'and v['sources_unchanged']
        assert v['generation']['preset_polarity']==pol
        assert v['generation']['output_sha256'][source.top(pol)+'.gds']==source.GDS[pol]
        assert prior['outputs'][pol+'/layout/'+source.top(pol)+'.gds']==source.GDS[pol]
        assert v['generation']['primitive_counts']==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
        d=v['steps']['drc']['measurement'];assert d['status']=='PASS'and d['markers']==0 and d['category_count']==560
        for mode in ('deep_lvs','flat_lvs'):
            d=v['steps'][mode];a=d['audit']
            assert d['expected_verdict_observed']and d['ports']['passed']and d['ports']['actual_count']==d['ports']['expected_count']==11
            assert a['status']=='PASS within comparison scope'and not a['reasons']and not a['extraction_diagnostics']
            assert a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==334
        faults={k:v for k,v in v['steps'].items()if k not in ('drc','deep_lvs','flat_lvs')}
        assert len(faults)==9 and all(x['expected_verdict_observed']and not x['positive']for x in faults.values())
        w=v['wires'];g=w['graph'];a=w['anchors']
        assert w['sources_unchanged']and w['physical_GDS_sha256']==source.GDS[pol]
        assert g['native_device_count']==334 and g['native_terminal_count']==1010
        assert g['native_electrical_net_count']==120 and g['wire_component_count']==119
        assert g['no_wire_geometry_change']and g['no_component_union_by_native_label']
        assert a['counts']==dict(devices=334,terminals=1010,metal_terminals=684,body_terminals=326,public_ports=11,unique_reference_planes=695,wire_components=119)
        assert len(a['negative_controls'])==7 and all(x['rejected']for x in a['negative_controls'])
        assert v['generation']['exactly243_other_compact_devices_unchanged']
        assert v['generation']['sole_device_dimension_delta']==dict(name='PHASE__XRUN__XAND_SKEW',old_L_um=32,new_L_um=20,W_um=1)
    assert all(prior[k]is False for k in ('qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'))
