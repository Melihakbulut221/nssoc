#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted runtime-provenance/retention fixtures; no native archive acquisition."""
import copy,json,signal,tarfile,time,types
from pathlib import Path
import cdr_via2_m3_loaded_runtime as r
import check_cdr_via2_m3_loaded_producer as fixtures
q=r.q;a=r.a

def reject(fn,label,records):
    try:fn()
    except (ValueError,RuntimeError,AssertionError,KeyError,TypeError,OSError,TimeoutError,tarfile.TarError)as error:records.append(dict(name=label,error=type(error).__name__));return error
    raise AssertionError('expected refusal '+label)

def controls(root,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);positive=[];refusals=[]
    c,d=r.records(root);expected,selected=r.archive_contract(c,d)
    assert len(expected)==120 and len(selected)==40
    actual=r.validate_live(c,d,d['pump-run.json'],d['pump-jobs.json'],d['pump-release.json'],d['pump-tag-ref.json'])
    assert actual['conclusion']=='failure'and actual['historical_failed_measurement_preserved']is True
    positive.append('actual_historical_failure_and120_member_40_selected_contract')
    for group,key,value in [('pump-run.json','conclusion','success'),('pump-run.json','head_sha','0'*40),('pump-run.json','run_attempt',2),('pump-release.json','target_commitish','main'),('pump-release.json','id',1),('pump-release.json','assets',[])]:
        mutated=copy.deepcopy(d);mutated[group][key]=value
        reject(lambda:r.validate_live(c,d,mutated['pump-run.json'],mutated['pump-jobs.json'],mutated['pump-release.json'],mutated['pump-tag-ref.json']),'live_'+group+'_'+key,refusals)
    values={name:('SYNTHETIC ONLY '+name+'\n').encode()for name in expected if name!='result.json'}
    model_names=[n for n in values if n.startswith('source/model-sources/')]
    models={n[len('source/model-sources/'):]:q.fingerprint(values[n])['sha256']for n in model_names}
    assert len(models)==37
    values['source-pin.json']=q.encode(dict(scope='SYNTHETIC_SOURCE_FIXTURE',preparation=dict(model_sources=models)))
    synthetic=copy.deepcopy(d);synthetic['pump-summary.json']['outputs']={n:q.fingerprint(v)['sha256']for n,v in values.items()}
    values['result.json']=q.encode(synthetic['pump-summary.json'])
    fake=copy.deepcopy(c);fake['producer']['engine_sha256']=q.fingerprint(values['source/runtime/patched-ngspice'])['sha256']
    for name,pin in fake['records'].items():
        if name.endswith('/pump-summary.json'):pin.update(q.fingerprint(values['result.json']))
    ex,sel=r.archive_contract(fake,synthetic)
    archive=out/'synthetic.tar.gz';fixtures.fixture_archive(archive,values,fake['producer']['archive_root'])
    restored=out/'restored';full=q.select_archive(archive,ex,sel,fake['producer']['archive_root'],restored)
    paths=r.verify_restored(fake,synthetic,restored,full)
    assert set(paths)=={'lib','engine','source_pin','models_summary'}
    assert sum(path.is_file()for path in Path(paths['lib']).rglob('*'))==37
    positive.append('real_archive_reader_full120_select40_and_complete37_model_join')
    for key,value in [('every_member_authenticated',False),('full_member_count',119),('full_members',{}),('selected',{})]:
        bad=copy.deepcopy(full);bad[key]=value
        reject(lambda:r.verify_restored(fake,synthetic,restored,bad),'proof_'+key,refusals)
    member=next(iter(sel));path=restored/member;raw=path.read_bytes()
    path.write_bytes(raw+b'x');reject(lambda:r.verify_restored(fake,synthetic,restored,full),'changed_selected',refusals);path.write_bytes(raw)
    path.unlink();reject(lambda:r.verify_restored(fake,synthetic,restored,full),'missing_selected',refusals);path.write_bytes(raw)
    path.unlink();path.symlink_to(out/'unowned');reject(lambda:r.verify_restored(fake,synthetic,restored,full),'linked_selected',refusals);path.unlink();path.write_bytes(raw)
    extra=restored/'extra';extra.write_text('synthetic');reject(lambda:r.verify_restored(fake,synthetic,restored,full),'extra_selected',refusals);extra.unlink()
    before=(signal.getsignal(signal.SIGALRM),signal.getitimer(signal.ITIMER_REAL))
    def cpu_timeout():
        with a.phase_budget(.05):
            while True:pass
    reject(cpu_timeout,'actual_cpu_phase_timeout',refusals)
    assert signal.getsignal(signal.SIGALRM)==before[0]and signal.getitimer(signal.ITIMER_REAL)==before[1]
    positive.append('real_cpu_watchdog_restores_prior_signal_timer')
    with a.phase_budget(2)as budget:
        assert 0<budget.timeout(30)<=2
        reject(lambda:a.phase_budget(.1).__enter__(),'nested_phase_timer_refused',refusals)
    positive.append('remaining_deadline_caps_every_io_timeout')
    def fixture_acquire(name,download):
        owned=out/name;owned.mkdir()
        fake_a=types.SimpleNamespace(source_guard=lambda *args,**kw:None,native_preflight=lambda *args,**kw:None,api=lambda endpoint,budget:({'run':d['pump-run.json'],'jobs':d['pump-jobs.json'],'release':d['pump-release.json'],'ref':d['pump-tag-ref.json']}['jobs'if'/jobs?'in endpoint else'release'if endpoint.startswith('releases/')else'ref'if endpoint.startswith('git/')else'run']),download=download)
        clone=types.FunctionType(r.acquire.__code__,dict(r.acquire.__globals__,a=fake_a),r.acquire.__name__,r.acquire.__defaults__)
        error=reject(lambda:clone(root,owned,dict(explicitly_synthetic=True),{}, {},a.Deadline(2)),name,refusals)
        result=q.decode((owned/'runtime'/'result.json').read_bytes())
        assert result['status']=='FAIL_OR_ERROR'and result['error']==repr(error)
        retained=Path(result['retained_failed_acquisition']['path'])
        assert retained.is_relative_to(owned)and retained.is_dir()
        assert list(retained.iterdir())
        return error,result,retained
    def partial_download(pin,path,budget):
        path.write_bytes(b'PARTIAL SYNTHETIC ARCHIVE');raise OSError('SYNTHETIC_DOWNLOAD_FAILURE')
    error,record,retained=fixture_acquire('partial-download-retained',partial_download)
    assert 'SYNTHETIC_DOWNLOAD_FAILURE'in str(error);positive.append('failed_download_bytes_retained_in_cloud_owned_output')
    def malformed_archive(pin,path,budget):
        path.write_bytes(b'NOT A GZIP ARCHIVE')
    fixture_acquire('malformed-archive-retained',malformed_archive)
    positive.append('failed_archive_validation_bytes_retained')
    result=dict(schema='cdr-via2-m3-loaded-runtime-controls-v1',positive=len(positive),refusals=len(refusals),positive_cases=positive,refusal_cases=refusals,scope='ACTUAL_DERIVED_METADATA_PLUS_SYNTHETIC_ARCHIVES_NO_NATIVE_ACQUISITION',native_payload_acquired=False,loaded_simulation_executed=False)
    r.write(out/'result.json',result);return result

if __name__=='__main__':raise SystemExit('Hosted source-control integration only')
