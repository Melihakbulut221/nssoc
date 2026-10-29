#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only actual handoff packing/restoration controls; no real native payload."""
from contextlib import ExitStack,contextmanager
import copy
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from unittest.mock import patch
import mainchip_built_engine_route_tail_contract as c
import mainchip_built_engine_route_tail_handoff as h
import cloud_mainchip_two_signal_repair as original
from mainchip_witness_engine_build import fingerprint


def refused(fn,reason):
    try:fn()
    except (ValueError,AssertionError,RuntimeError,KeyError,OSError) as exc:
        assert reason in str(exc),(reason,repr(exc))
        return dict(type=type(exc).__name__,error=str(exc))
    raise AssertionError('Expected actual handoff refusal: '+reason)


def packed(files):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tar:
        for name,raw in sorted(files.items()):
            info=tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
    return stream.getvalue()


@contextmanager
def fixture(mode='off'):
    with tempfile.TemporaryDirectory() as d:
        directory=Path(d);root=directory/'checkout';root.mkdir();work=directory/'route';work.mkdir()
        out=work/'out';out.mkdir()
        m=dict(protected={'scripts/synthetic-only.txt':c.digest(b'synthetic source')})
        source=root/'scripts/synthetic-only.txt';source.parent.mkdir();source.write_bytes(b'synthetic source')
        c.atomic_record(root/c.METHOD,m)
        for p in [*m['protected'],c.METHOD]:
            target=work/'tail-source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/p,target)
        members={'source/synthetic.txt':b'frozen old source','engine/openroad':b'synthetic-not-ELF',
            'input.odb':b'synthetic-not-ODB','runtime-dependencies.json':b'{}',
            'routing-inputs/clock/selected/synthetic.txt':b'clock',
            'routing-inputs/global/synthetic.txt':b'global',
            'input-transport/selected/synthetic.txt':b'old input',
            'out/work/fixed.odb':b'synthetic fixed','out/work/repair.tcl':b'synthetic route Tcl'}
        for i in range(746-len(members)):members['source/fixture-%04d.txt'%i]=str(i).encode()
        for p,raw in members.items():
            path=work/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        roots=['source','engine/openroad','input.odb','runtime-dependencies.json','routing-inputs/clock/selected',
            'routing-inputs/global','input-transport/selected','out/work']
        inv=dict(roots=roots,files={p:fingerprint(work/p) for p in members})
        assert len(inv['files'])==746
        c.atomic_record(work/'frozen-manifest.json',inv)
        engine=fingerprint(work/'engine/openroad');input_record=fingerprint(work/'input.odb')
        request=dict(source='a'*40,mode=mode,stage='route',run_id=123,engine=engine)
        c.atomic_record(work/'request.json',request)
        route_raw=b'NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\nNSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\n'
        (out/'supervision').mkdir();(out/'supervision/one-two-signal-routing-attempt.stdout').write_bytes(route_raw)
        command=dict(label=c.PHASES[0],argv=c.command(c.PHASES[0]),returncode=0,
            requested_timeout_seconds=14400,supervision_failure=None,memory_read_error=None,
            process_group_cleanup=dict(remaining_live=[]),maximum_group_rss_kib=c.LIMITS['max_group_rss_kib'],
            minimum_available_kib=c.LIMITS['min_available_kib'],stdout_sha256=c.digest(route_raw),stdout_bytes=len(route_raw))
        for p in ('routed-fixed.odb','routed-fixed.def','fixed-routing.drc'):(out/'work'/p).write_bytes(('synthetic '+p).encode())
        route_outputs={p:fingerprint(out/'work'/p) for p in ('routed-fixed.odb','routed-fixed.def','fixed-routing.drc')}
        route_witness={}
        if mode=='on':
            (out/'witness').mkdir()
            for p in ('imported.jsonl','before_dr.jsonl','after_dr.jsonl','after_writer.jsonl'):
                (out/'witness'/p).write_bytes(('synthetic witness '+p).encode());route_witness[p]=fingerprint(out/'witness'/p)
        case=dict(source=request['source'],mode=mode,stage='route',run_id=123,
            status='PASS_ROUTE_ONLY_AWAITING_ORIGINAL_AUDITS',complete_route=True,engine=engine,
            prefix_source=c.PREFIX_SOURCE,prefix_run=c.PREFIX_RUN,terminal_errors=[],physical_acceptance=False,
            timing_accepted=False,full_phy_accepted=False,commands=[command],
            route_log=original.qualified.s.route_log(route_raw),route_outputs=route_outputs,route_witness=route_witness)
        host=dict(source=request['source'],mode=mode,stage='route',status='PASS_OWNED_ROUTE_STAGE_DIAGNOSTIC',
            physical_acceptance=False,terminal_errors=[],container_terminal=dict(State=dict(Running=False,OOMKilled=False,ExitCode=0,Error='')))
        inner=dict(stage='route',status='PASS_BUILT_ELF_ACTUAL_ROUTE_STAGE',terminal_errors=[],
            commands=[dict(label=x,returncode=0,timed_out=False) for x in ('version','ldd','tcl-smoke','route-stage')])
        for name,row in (('host-result',host),('inner-result',inner),('case-result',case)):c.atomic_record(out/(name+'.json'),row)
        shutil.copyfile(root/c.METHOD,out/'method.json')
        ctx=dict(source=request['source'],mode=mode,stage='audit',token='123-1')
        env=dict(GITHUB_RUN_ID='123')
        with ExitStack() as stack:
            stack.enter_context(patch.object(c,'ENGINE',engine));stack.enter_context(patch.object(c,'INPUT',input_record))
            stack.enter_context(patch.object(c,'method',return_value=m));stack.enter_context(patch.object(c.previous,'method',return_value={}))
            stack.enter_context(patch.object(c,'prefix_contract',return_value=inv))
            stack.enter_context(patch.object(h.shutil,'disk_usage',return_value=type('Disk',(),{'free':64*1024**3})()))
            yield dict(directory=directory,work=work,out=out,root=root,ctx=ctx,env=env,original=inv,
                request=request,case=case,host=host,inner=inner)


def transport(f):
    out=f['out'];files={p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()}
    outputs=dict(source=f['ctx']['source'],mode=f['ctx']['mode'],stage='route',
        files={p:dict(bytes=len(raw),sha256=c.digest(raw)) for p,raw in files.items()},physical_acceptance=False)
    files['outputs.json']=(json.dumps(outputs,sort_keys=True,indent=2)+'\n').encode()
    outer=packed(files);part='route-tail-evidence.tar.gz.part000'
    parts=dict(archive=dict(bytes=len(outer),sha256=c.digest(outer)),
        parts=[dict(name=part,bytes=len(outer),sha256=c.digest(outer))])
    payloads={name:files[name] for name in ('host-result.json','inner-result.json','case-result.json','outputs.json',
        'method.json','route-handoff.json','route-handoff-inventory.json')}
    payloads['parts.json']=(json.dumps(parts)+'\n').encode();payloads[part]=outer
    tag='cloud-results-123-1-'+c.group(f['ctx']['mode'],'route')
    release=dict(id=12,tag_name=tag,target_commitish=f['ctx']['source'],draft=False,prerelease=True,
        assets=[dict(id=100+i,name=name,size=len(raw),digest='sha256:'+c.digest(raw),browser_download_url='https://fixture.invalid/'+name)
            for i,(name,raw) in enumerate(payloads.items())])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=f['ctx']['source']))
    run=dict(id=123,head_sha=f['ctx']['source'],run_attempt=1,status='in_progress')
    jobs=dict(jobs=[dict(id=44,name='route-only ('+f['ctx']['mode']+')',status='completed',conclusion='success')])
    def read(endpoint):
        if endpoint=='actions/runs/123':return copy.deepcopy(run)
        if endpoint=='actions/runs/123/jobs?per_page=100':return copy.deepcopy(jobs)
        if endpoint=='releases/tags/'+tag:return copy.deepcopy(release)
        if endpoint=='git/ref/tags/'+tag:return copy.deepcopy(ref)
        raise AssertionError('unexpected fixture endpoint '+endpoint)
    def fetch(url,expected,path):
        raw=payloads[url.rsplit('/',1)[1]]
        # Simulate the qualified transport digest contract without bypassing the actual extractor.
        assert c.digest(raw)==expected,'fixture transport digest'
        Path(path).write_bytes(raw)
    return dict(read=read,fetch=fetch,payloads=payloads,release=release,ref=ref,run=run,jobs=jobs)


def change_record(t,name,mutate):
    row=c.decode(t['payloads'][name]);mutate(row)
    raw=(json.dumps(row,sort_keys=True)+'\n').encode();t['payloads'][name]=raw
    a=next(a for a in t['release']['assets'] if a['name']==name)
    a.update(size=len(raw),digest='sha256:'+c.digest(raw))


def controls():
    positives=[];negatives=[];terminals=[]
    for mode in ('off','on'):
        with fixture(mode) as f:
            proof=h.freeze(f['work'],f['out'],f['root']);t=transport(f)
            work=f['directory']/'audit';work.mkdir();out=work/'out';out.mkdir()
            lineage=h.restore(work,out,f['root'],f['ctx'],f['env'],t['read'],t['fetch'])
            inv=c.decode((f['out']/'route-handoff-inventory.json').read_bytes())
            assert lineage['authenticated_complete_route'] and lineage['complete_extracted_handoff_retained']
            assert c.frozen_unchanged(work/'route-restored',inv)['files']==len(inv['files'])
            assert c.frozen_unchanged(work,f['original'])['files']==746
            projection=h.route_projection(inv['files'])
            assert c.frozen_unchanged(work,dict(files=projection))['files']==len(projection)
            assert (work/'route-restored/out/host-result.json').read_bytes()==(f['out']/'host-result.json').read_bytes()
            assert not (out/'host-result.json').exists() and (out/'route-host-result.json').exists()
            assert sorted(p.name for p in (out/'witness').iterdir())==sorted(f['case']['route_witness']) if mode=='on' else not (out/'witness').exists()
            positives.append(dict(mode=mode,frozen_files=746,handoff_files=proof['files'],canonical_files=len(projection),complete_evidence_retained=True))
    modes=('failed_job','wrong_source','annotated_tag','wrong_method','case_incomplete','original_map',
        'part_hash','missing_outer_member','changed_nested_member','missing_nested_member','destination_collision','witness_join')
    for mode in modes:
        with fixture('on' if mode=='witness_join' else 'off') as f:
            h.freeze(f['work'],f['out'],f['root']);t=transport(f)
            work=f['directory']/'audit';work.mkdir();out=work/'out';out.mkdir()
            if mode=='failed_job':t['jobs']['jobs'][0]['conclusion']='failure';reason='complete route job required'
            elif mode=='wrong_source':t['run']['head_sha']='b'*40;reason='same workflow route run'
            elif mode=='annotated_tag':t['ref']['object']['type']='tag';reason=''
            elif mode=='wrong_method':change_record(t,'method.json',lambda r:r.update(unapproved=True));reason='route/audit exact method'
            elif mode=='case_incomplete':change_record(t,'case-result.json',lambda r:r.update(complete_route=False));reason='route body completion'
            elif mode=='original_map':f['original']['files']['input.odb']['sha256']='f'*64;reason='route changed original frozen input'
            elif mode=='part_hash':change_record(t,'parts.json',lambda r:r['parts'][0].update(sha256='f'*64));reason='route part asset join'
            elif mode=='destination_collision':(work/'input.odb').write_bytes(b'collision');reason='audit projection collision'
            elif mode=='witness_join':change_record(t,'case-result.json',lambda r:r['route_witness'].pop('imported.jsonl'));reason='route witness census'
            else:
                # Corrupt actual archive member bytes. Rebind the outer transport only, retaining independent nested/input maps.
                if mode=='missing_outer_member':
                    files={p.relative_to(f['out']).as_posix():p.read_bytes() for p in f['out'].rglob('*') if p.is_file()}
                    files['outputs.json']=t['payloads']['outputs.json'];files.pop('method.json');outer=packed(files);reason='missing archive member'
                else:
                    restored={}
                    with tarfile.open(fileobj=io.BytesIO((f['out']/'route-handoff.tar.gz').read_bytes()),mode='r:gz') as tar:
                        for member in tar:restored[member.name]=tar.extractfile(member).read()
                    if mode=='changed_nested_member':restored['input.odb']=b'bad-native-byte';reason='archive member identity/size'
                    else:restored.pop('input.odb');reason='missing archive member'
                    nested=packed(restored);(f['out']/'route-handoff.tar.gz').write_bytes(nested)
                    proof=c.decode((f['out']/'route-handoff.json').read_bytes());proof['archive']=fingerprint(f['out']/'route-handoff.tar.gz')
                    c.atomic_record(f['out']/'route-handoff.json',proof);t=transport(f);outer=t['payloads']['route-tail-evidence.tar.gz.part000']
                part='route-tail-evidence.tar.gz.part000';t['payloads'][part]=outer
                asset=next(a for a in t['release']['assets'] if a['name']==part);asset.update(size=len(outer),digest='sha256:'+c.digest(outer))
                def rebound(r):
                    r['archive']=dict(bytes=len(outer),sha256=c.digest(outer));r['parts']=[dict(name=part,bytes=len(outer),sha256=c.digest(outer))]
                change_record(t,'parts.json',rebound)
            error=refused(lambda:h.restore(work,out,f['root'],f['ctx'],f['env'],t['read'],t['fetch']),reason)
            assert not (work/'route-lineage.json').exists()
            negatives.append(dict(case=mode,result=error))
    for mode in ('frozen_input','route_failed','proof_replace','tar_add'):
        with fixture() as f:
            sentinel=OSError('actual handoff terminal '+mode);original_replace=os.replace;original_add=tarfile.TarFile.add
            def replace(a,b):
                if Path(b).name=='route-handoff.json':raise sentinel
                return original_replace(a,b)
            count=[]
            def add(tar,name,*a,**kw):
                count.append(str(name))
                if len(count)==2:raise sentinel
                return original_add(tar,name,*a,**kw)
            if mode=='frozen_input':(f['work']/'input.odb').write_bytes(b'changed frozen');reason='frozen input changed'
            elif mode=='route_failed':
                bad=copy.deepcopy(f['host']);bad['status']='FAIL';c.atomic_record(f['out']/'host-result.json',bad);reason='route host completion'
            with ExitStack() as stack:
                if mode=='proof_replace':stack.enter_context(patch.object(os,'replace',side_effect=replace))
                if mode=='tar_add':stack.enter_context(patch.object(tarfile.TarFile,'add',add))
                if mode in ('frozen_input','route_failed'):
                    error=refused(lambda:h.freeze(f['work'],f['out'],f['root']),reason)
                else:
                    try:h.freeze(f['work'],f['out'],f['root'])
                    except OSError as exc:assert exc is sentinel;error=dict(same_exception=True)
                    else:raise AssertionError('handoff failure swallowed')
            assert not (f['out']/'route-handoff.json').exists()
            if mode in ('proof_replace','tar_add'):
                assert (f['out']/'route-handoff-inventory.json').is_file() and (f['out']/'route-handoff.tar.gz').is_file()
            if mode=='proof_replace':assert list(f['out'].glob('route-handoff.json.*.tmp'))
            terminals.append(dict(case=mode,result=error,partial_evidence_preserved=True))
    assert len(positives)==2 and len(negatives)==12 and len(terminals)==4
    return dict(positive=positives,refusals=negatives,terminal=terminals,
        actual_freeze_restore_executed=True,synthetic_payloads_only=True,native_engine_executed=False)
