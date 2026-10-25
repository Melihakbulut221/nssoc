#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate one complete saved archive, stream every member, select diagnostic text only."""
import hashlib,json,os,shutil,tarfile
from pathlib import Path,PurePosixPath
import mainchip_original_clock_restoration as c
from cloud_chunked_results import verify_parts
from cloud_verified_parts import JoinedParts
RUN=40223193329
SOURCE='7ad3ba10842df1fcf3646e7196812f4f58d149dd'
GROUP='mainchip-original-clock-restoration'
SUMMARY='b7fe3efe42036da94095606d51d3deaa8d5604b260c72cad477074c1b539fd15'
PARTS='f9b03951c9aa025a14512ee1155005a4e212c54500e5ade780cc87724b585011'
ARCHIVE='34d157ee08bcbe1735b06c194ee0cde6b250004eec5fcaeec5fb92907e90f371'
PREFIX='docs/evidence/mainchip-original-clock-marker-native-complete-nonzero-DRT-20261025'
SELECTED=('work/initial-drc-markers.json','work/initial-drc.rpt','work/audit-restored-result.json',
          'work/audit-fixed-result.json','work/audit-unfixed-result.json','work/drc-audit-result.json','work/restored.def')
ASSETS={675864543:(GROUP+'-'+str(RUN)+'-1.summary.json',42196,SUMMARY),
        675864582:(GROUP+'-'+str(RUN)+'-1.parts.json',895,PARTS),
        675864653:(GROUP+'-'+str(RUN)+'-1.tar.gz.part0000',828126547,ARCHIVE)}

def live_envelope(run,jobs,release,tag):
    assert run['id']==RUN and run['run_attempt']==1 and run['head_sha']==SOURCE
    assert run['head_branch']=='codex/mainchip-original-clock-restoration'
    assert run['path']=='.github/workflows/mainchip-original-clock-restoration-cloud.yml'
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='success'
    assert {j['id']:(j['name'],j['conclusion'],j['status'])for j in jobs['jobs']}=={
        121259008912:('controls','success','completed'),121259115060:('native','success','completed')}
    assert len(jobs['jobs'])==2
    import ensure_cloud_tested_source_release as g
    name='cloud-results-'+str(RUN)+'-1-'+GROUP
    g.validate_release(release,tag,name,SOURCE)
    assert release['id']==423594261
    assets=release['assets'];assert len(assets)==len(ASSETS)
    assert len({a['id']for a in assets})==len(assets)
    for a in assets:
        assert a['id']in ASSETS
        n,size,h=ASSETS[a['id']]
        assert a['name']==n and a['size']==size and a['digest']=='sha256:'+h
    return dict(run=RUN,source=SOURCE,attempt=1,release=423594261,terminal_success=True)

def expected_report(raw):
    assert len(raw)==42196 and c.digest(raw)==SUMMARY
    r=json.loads(raw)
    assert r['source_head']==SOURCE and r['run_id']==RUN and r['run_attempt']==1
    assert r['status']=='COMPLETE_CLOCK_RESTORATION_INITIAL_DRT_AND_FIXED_ROUNDTRIP_NOT_SIGNOFF'
    for k in ('accepted','zero_DRT_markers','full_phy_accepted','final_timing_complete','native_routing_started'):assert r[k]is False
    for k in ('actual218_clock_records_restored','original1691_clock_gate_passed','full_FIXED_roundtrip_verified','original_inputs_unchanged'):assert r[k]is True
    m=r['initial_DRT']['measurement']
    assert m['marker_count']==762 and m['all_categories_below_native_cap']is True
    assert m['serialized_markers']['bytes']==959864 and m['serialized_markers']['sha256']==r['outputs'][SELECTED[0]]
    assert m['report_bytes']==121010 and m['report_sha256']==r['outputs'][SELECTED[1]]
    assert len(r['phase_results'])==14
    for p in r['phase_results']:
        assert p['returncode']==0 and p['supervision_failure']is None and not p['process_group_cleanup']['remaining_live']
    return r

def canonical_member(name,directory=False):
    assert type(name)is str and name and '\\'not in name and '\0'not in name
    if directory:name=name.rstrip('/')
    p=PurePosixPath(name)
    assert p.parts and not p.is_absolute()and p.as_posix()==name and all(v not in ('.','..','')for v in p.parts)
    return p

def audit_extract(manifest,parts,destination,expected,selected):
    proof=verify_parts(manifest,parts)
    prefix=manifest['source_directory'];assert canonical_member(prefix).parts==(prefix,)
    assert set(selected)<=set(expected)and expected
    for name,h in expected.items():
        canonical_member(name)
        assert type(h)is str and len(h)==64 and all(ch in '0123456789abcdef'for ch in h)
    assert not destination.exists()and not destination.is_symlink()
    destination.mkdir(parents=True);seen=set();found={};total=0
    directories={PurePosixPath(prefix)}
    for name in expected:
        directories.update((PurePosixPath(prefix)/name).parents)
    directories.discard(PurePosixPath('.'))
    with JoinedParts([parts/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as archive:
            for e in archive:
                assert e.isdir()or e.isfile(),'Nonregular archive member'
                path=canonical_member(e.name,e.isdir())
                assert path.parts[0]==prefix and str(path)not in seen,'Wrong root or duplicate member'
                seen.add(str(path))
                if e.isdir():
                    assert path in directories,'Unrecorded archive directory'
                    continue
                name=path.relative_to(prefix).as_posix()
                assert name in expected,'Unrecorded archive file'
                assert 0<=e.size<=4*1024**3
                total+=e.size;assert total<=12*1024**3,'Unexpected full inventory size'
                target=destination/name if name in selected else None
                if target:target.parent.mkdir(parents=True,exist_ok=True)
                output=target.open('xb')if target else None
                digest=hashlib.sha256();size=0
                try:
                    with archive.extractfile(e)as stream:
                        while data:=stream.read(4*1024**2):
                            digest.update(data);size+=len(data)
                            if output:output.write(data)
                finally:
                    if output:output.close()
                assert size==e.size and digest.hexdigest()==expected[name],('Changed original archive file',name)
                found[name]=dict(bytes=size,sha256=digest.hexdigest())
    assert set(found)==set(expected),'Missing original archive file'
    return dict(archive=proof,all_original_files=found,total_unpacked_bytes=total,
        complete_original_inventory_verified_before_analysis=True,selected_files={n:found[n]for n in selected})

def restore(transport):
    import ensure_cloud_tested_source_release as g
    from route_cloud_newer_postcts import fetch
    name='cloud-results-'+str(RUN)+'-1-'+GROUP
    envelope=live_envelope(g.api('actions/runs/'+str(RUN)),
        g.api('actions/runs/'+str(RUN)+'/jobs?per_page=100'),
        g.api('releases/423594261'),g.api('git/ref/tags/'+name))
    assert not transport.exists();transport.mkdir()
    assert shutil.disk_usage(transport).free>=4*1024**3,'Insufficient readback storage'
    stem=GROUP+'-'+str(RUN)+'-1'
    base='https://github.com/Melihakbulut221/nssoc/releases/download/'+name+'/'
    fetch(base+stem+'.summary.json',SUMMARY,transport/'summary.json')
    fetch(base+stem+'.parts.json',PARTS,transport/'parts.json')
    raw=c.regular(transport/'summary.json').read_bytes();r=expected_report(raw)
    assert raw==c.regular(c.ROOT/(PREFIX+'.summary.json')).read_bytes()
    part_raw=c.regular(transport/'parts.json').read_bytes()
    assert part_raw==c.regular(c.ROOT/(PREFIX+'.parts.json')).read_bytes()
    manifest=json.loads(part_raw)
    assert manifest['source_directory']=='cloud-mainchip-original-clock-restoration'
    assert manifest['stem']==stem and manifest['bytes']==828126547 and manifest['sha256']==ARCHIVE
    assert len(manifest['parts'])==1
    p=manifest['parts'][0]
    assert p['name']==stem+'.tar.gz.part0000'and p['index']==0 and p['bytes']==828126547 and p['sha256']==ARCHIVE
    fetch(base+p['name'],p['sha256'],transport/p['name'])
    expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SUMMARY
    proof=audit_extract(manifest,transport,transport/'selected',expected,SELECTED)
    return r,dict(envelope=envelope,inventory=proof,summary_sha256=SUMMARY,parts_sha256=PARTS)
