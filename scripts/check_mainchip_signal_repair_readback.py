#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real readback boundaries and failure preservation. No CAD or prior archive."""
import copy,json,os,tempfile,types
from pathlib import Path
from unittest.mock import patch
import mainchip_signal_repair_readback as a
import cloud_mainchip_signal_repair_readback as d
import check_mainchip_repaired_postroute_bridge as prior
import check_mainchip_clock_marker_classification as marker_fixture
from cloud_chunked_results import pack
from check_mainchip_original_clock_restoration_driver import emit
OUT=a.c.ROOT/'cloud-mainchip-signal-repair-readback-controls'
def encoded(x):return (json.dumps(x,indent=2)+'\n').encode()
def fixture():
    files,r=prior.fixture()
    names=[f'ck{i:04}'for i in range(1691)]
    signals=['sig0','sig1','power']+[f's{i:06}'for i in range(143820-1691-3)]
    raw=b'VERSION 5.8 ;\nNETS 143820 ;\n'
    selected_set=set(names)
    raw+=b''.join(('- '+n+' + USE '+('CLOCK'if n in selected_set else'POWER'if n=='power'else'SIGNAL')+' ;\n').encode()for n in names+signals)
    raw+=b'END NETS\nEND DESIGN\n'
    files['work/expected-original-class.def']=raw
    files['work/ownership.json']=encoded(dict(selected=names,net_count=143820))
    tree,tr,measurement,_,_=marker_fixture.fixture()
    text=json.dumps(tree).replace('"ck0"','"ck0000"').replace('"ck1"','"ck0001"')
    marker=encoded(json.loads(text));tr=tr.replace(b'net:ck0',b'net:ck0000').replace(b'net:ck1',b'net:ck0001')
    measurement.update(all_categories_below_native_cap=True,zero_reported_DRT_markers=False,
        report_bytes=len(tr),report_sha256=a.c.digest(tr))
    measurement['serialized_markers']=a.drc.bind_serialized_markers(measurement,marker)
    files['work/initial-drc-markers.json']=marker
    files['work/initial-drc.rpt']=files['work/initial-drc-reread.rpt']=tr
    u=json.loads(files['work/unfix-audit-result.json']);u['expected_def_sha256']=a.c.digest(raw)
    files['work/unfix-audit-result.json']=encoded(u)
    final=json.loads(files['work/drc-audit-result.json']);final['final_DRT']=measurement
    final['next_stage']=a.repair.continuation_gate(final);files['work/drc-audit-result.json']=encoded(final)
    files['work/original-gate-before-repair/result.json']=files['work/original-gate-after-repair/result.json']
    phases=[]
    for label in a.PHASES:
        stdout=('synthetic exact stream '+label+'\n').encode();stderr=b''
        row=dict(label=label,returncode=0,supervision_failure=None,process_group_cleanup=dict(remaining_live=[]),
            stdout_bytes=len(stdout),stdout_sha256=a.c.digest(stdout),stderr_bytes=0,stderr_sha256=a.c.digest(stderr))
        if label=='drc-audit':row.update(supervision_failure='memory_sample_unavailable',memory_read_error="CounterError('Persistent unavailable live VmRSS')")
        else:phases.append(dict(row,requested_timeout_seconds=14400 if label=='one-signal-routing-attempt'else 1200))
        files['supervision/'+label+'.command.json']=encoded(row)
        files['supervision/'+label+'.stdout']=stdout;files['supervision/'+label+'.stderr']=stderr
    r.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR',phase_results=phases,native_result=None,
        error="memory_sample_unavailable: Persistent unavailable live VmRSS")
    r['outputs']={n:a.c.digest(b)for n,b in files.items()}
    return files,r,names
def changed(files,name,fn):
    x=json.loads(files[name]);fn(x);files[name]=encoded(x)
def write(root,files):
    for name,raw in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
def reject(name,fn):
    try:fn()
    except (AssertionError,KeyError,ValueError,FileNotFoundError):return name
    raise AssertionError('Accepted readback fault '+name)
def lifecycle_controls():
    import threading
    import ensure_cloud_tested_source_release as guard
    positives=[]
    for mode in ('complete_failed_native_report','supervision_refusal','truncated_command','source_integrity_failure'):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);out=root/'out';transport=root/'transport'
            after=[False];error=RuntimeError('EXACT_READBACK_SUPERVISION_REFUSAL')
            def method():
                if mode=='source_integrity_failure'and after[0]:raise AssertionError('EXACT_READBACK_SOURCE_CHANGE')
                return dict(cloud_readback_authorized=True,protected={d.runtime.SAMPLER:'f'*64})
            def supervised(argv,label,**kw):
                assert argv[-1]=='--worker'and label==d.LABEL and kw==dict(seconds=1200,cwd=d.ROOT)
                (out/'saved').mkdir();(out/'saved/retained.json').write_bytes(b'{"retained":true}')
                stdout=b'complete readback stream';stderr=b''
                row=dict(label=label,returncode=0,supervision_failure=None,
                    process_group_cleanup=dict(remaining_live=[]),stdout_bytes=len(stdout),
                    stdout_sha256=a.c.digest(stdout),stderr_bytes=0,stderr_sha256=a.c.digest(stderr))
                trace=out/'supervision'
                for suffix,raw in [('stdout',stdout),('stderr',stderr),('command.json',encoded(row))]:
                    (trace/(label+'.'+suffix)).write_bytes(raw)
                d.save(out/'classification-index.json',dict(marker_count=11,resource_guard_failure_preserved=True))
                d.save(out/'source-admission.json',dict(fixture=True))
                if mode=='truncated_command':(trace/(label+'.command.json')).write_bytes(b'{"label":')
                after[0]=True
                if mode in ('supervision_refusal','truncated_command'):raise error
            sup=types.SimpleNamespace(ACTIVE=None,STOP=threading.Event(),TRACE=out/'supervision',
                interrupted=lambda *x:None,heartbeat=lambda:None,stop_process=lambda p:dict(remaining_live=[]),
                supervised=supervised)
            with patch.object(d,'OUT',out),patch.object(d,'TRANSPORT',transport),patch.object(d,'methods',method),\
                 patch.object(d.runtime,'supervisor',return_value=sup),patch.object(d.shutil,'disk_usage',return_value=types.SimpleNamespace(free=16*1024**3)),\
                 patch.object(guard,'context',return_value=('tag','a'*40)),patch.object(guard,'api',return_value={}),patch.object(guard,'validate_release',return_value={}):
                try:d.run()
                except RuntimeError as got:
                    assert mode in ('supervision_refusal','truncated_command')and got is error
                except AssertionError:
                    assert mode=='source_integrity_failure'
                else:assert mode=='complete_failed_native_report'
                result=json.loads((out/'result.json').read_bytes())
                assert result['resource_guard_failure_preserved']is True and result['postroute_bridge_eligible']is False
                assert result['outputs']['saved/retained.json']==a.c.file_sha(out/'saved/retained.json')
                if mode=='complete_failed_native_report':
                    assert result['status']=='COMPLETE_SAVED_SIGNAL_REPAIR_REPORTS_ORIGINAL_FAILURE_RETAINED'
                else:assert result['status']=='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR_READBACK'
                if mode=='truncated_command':
                    assert result['terminal_command_parse_error']and 'terminal_command_record'not in result
                    assert result['terminal_command_raw']['sha256']==a.c.file_sha(out/'supervision'/(d.LABEL+'.command.json'))
                if mode=='source_integrity_failure':assert 'EXACT_READBACK_SOURCE_CHANGE'in result['source_integrity_error']
                positives.append(mode)
    return dict(actual_outer_run_finally=positives,archive_or_native_access=False)
def publication_controls():
    import publish_mainchip_saved_postroute as publisher
    import mainchip_saved_postroute_publisher_base as transport
    positive=[];original=publisher.GROUP
    for mode in ('complete','direct_failure'):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);out=root/'out';out.mkdir();pub=root/('publication-'+d.GROUP);calls=[]
            (out/'full-saved-report.json').write_bytes(b'{"original_run_conclusion":"failure"}')
            failure=ValueError('EXACT_DIRECT_UPLOAD_REFUSAL')
            def packed(actual,destination):
                calls.append(('pack',publisher.GROUP,actual,destination))
                assert actual==out;destination.mkdir()
                d.save(out/'result.json',dict(source_head='a'*40,status='FAIL_ORIGINAL',
                    outputs={'full-saved-report.json':a.c.file_sha(out/'full-saved-report.json')}))
                return dict(packed=True)
            def upload(group,paths):
                calls.append(('direct',group,[p.name for p in paths]))
                assert group==d.GROUP and len(paths)==1
                assert paths[0].read_bytes()==(out/'full-saved-report.json').read_bytes()
                if mode=='direct_failure':raise failure
                return dict(uploaded=True)
            with patch.object(d,'ROOT',root),patch.object(d,'OUT',out),patch.object(d,'methods',return_value={}),\
                 patch.object(d.shutil,'disk_usage',return_value=types.SimpleNamespace(free=16*1024**3)),\
                 patch.object(publisher,'publish_evidence',packed),patch.object(transport,'publish_files',upload),\
                 patch.dict(os.environ,{'GITHUB_RUN_ID':'17','GITHUB_RUN_ATTEMPT':'1'}):
                try:result=d.publish()
                except ValueError as got:assert mode=='direct_failure'and got is failure
                else:assert mode=='complete'and result['original_failure_preserved']is True
            assert publisher.GROUP==original and [r[0]for r in calls]==['pack','direct']
            assert calls[0][1]==d.GROUP and (out/'result.json').is_file()
            positive.append(mode)
    return dict(actual_publisher_binding_and_direct_file_program=positive,
        actual_transport_mocked=True,qualified_transport_separately_exercised=True)

def controls():
    assert d.methods()['source_controls_authorized']is True
    positives=[];refusals=[]
    receipt=a.value(a.c.regular(a.c.ROOT/(a.PREFIX+'.json')).read_bytes())
    args=[receipt[k]for k in ('run','jobs','release','tag_ref')]
    args[1]={'jobs':args[1]}
    assert a.live_envelope(*args)['original_conclusion']=='failure'
    report=a.expected_report(a.c.regular(a.c.ROOT/(a.PREFIX+'.summary.json')).read_bytes())
    assert a.manifest(a.c.regular(a.c.ROOT/(a.PREFIX+'.parts.json')).read_bytes())['sha256']==a.ARCHIVE
    positives.append('actual_pinned_failed_run_envelope_summary_parts')
    for label,fn in [
      ('source',lambda v:v[0].update(head_sha='0'*40)),('attempt',lambda v:v[0].update(run_attempt=2)),
      ('not_terminal',lambda v:v[0].update(status='in_progress')),('success_relabel',lambda v:v[0].update(conclusion='success')),
      ('wrong_native_job',lambda v:v[1]['jobs'][1].update(id=1)),
      ('native_success_relabel',lambda v:v[1]['jobs'][1].update(conclusion='success')),
      ('wrong_release',lambda v:v[2].update(id=1)),('asset_digest',lambda v:v[2]['assets'][0].update(digest='sha256:'+'0'*64)),
      ('annotated_tag',lambda v:v[3]['object'].update(type='tag'))]:
        values=copy.deepcopy(args);fn(values)
        refusals.append(reject(label,lambda values=values:a.live_envelope(*values)))
    files,r,names=fixture();selector=a.c.digest(a.c.canonical(names))
    with tempfile.TemporaryDirectory()as tmp,patch.object(a.repair,'SELECTED_SHA',selector):
        root=Path(tmp);write(root,files)
        observed=a.inspect_saved(root,r)
        assert observed['remaining_marker_count']==11 and observed['selected_clock_fixed_count']==1691
        assert observed['postroute_bridge_eligible']is False and observed['original_resource_guard_failure_preserved']is True
        assert observed['classification']['exact_complete_JSON_TR_reconstruction']is True
        assert observed['saved_native_reported_next_stage']['eligible_for_separately_reviewed_RC_STA']is False
        positives.append('actual_full_saved_boundary_complete_143820_net_DEF_and_failed_guard')
    def body_case(name,fn):
        local=copy.deepcopy(files);changed(local,name,fn)
        rr=copy.deepcopy(r);rr['outputs']={n:a.c.digest(b)for n,b in local.items()}
        with tempfile.TemporaryDirectory()as tmp,patch.object(a.repair,'SELECTED_SHA',selector):
            root=Path(tmp);write(root,local);a.inspect_saved(root,rr)
    for label,name,fn in [
      ('native_final_status','work/drc-audit-result.json',lambda x:x.update(status='RUNNING')),
      ('final_clock_gate','work/drc-audit-result.json',lambda x:x.update(original1691_clock_gate_passed=False)),
      ('final_native_invariant','work/drc-audit-result.json',lambda x:x.update(native_invariants_passed=False)),
      ('unfix_status','work/unfix-audit-result.json',lambda x:x.update(status='RUNNING')),
      ('candidate_hash','work/unfix-audit-result.json',lambda x:x.update(candidate_sha256='0'*64)),
      ('DEF_hash','work/unfix-audit-result.json',lambda x:x.update(expected_def_sha256='0'*64)),
      ('gate_count','work/original-gate-after-repair/result.json',lambda x:x.update(clock_or_fixed_nets=1690)),
      ('final_gate_false','work/original-gate-after-final-drc/result.json',lambda x:x.update(all_source_clock_and_fixed_records_preserved=False)),
      ('selector_duplicate','work/ownership.json',lambda x:x['selected'].__setitem__(1,x['selected'][0])),
      ('net_census','work/ownership.json',lambda x:x.update(net_count=143819)),
      ('guard_waiver','supervision/drc-audit.command.json',lambda x:x.update(supervision_failure=None)),
      ('child_nonzero','supervision/drc-audit.command.json',lambda x:x.update(returncode=1)),
      ('live_orphan','supervision/drc-audit.command.json',lambda x:x['process_group_cleanup'].update(remaining_live=[7])),
      ('stream_hash','supervision/drc-audit.command.json',lambda x:x.update(stdout_sha256='0'*64)),
      ('earlier_command_differs','supervision/prepare.command.json',lambda x:x.update(returncode=1)),
      ('marker_count','work/drc-audit-result.json',lambda x:x['final_DRT'].update(marker_count=10)),
      ('marker_cap','work/drc-audit-result.json',lambda x:x['final_DRT']['categories'][1].update(maximum_markers=11)),
      ('marker_source','work/initial-drc-markers.json',lambda x:x[a.drc.CATEGORY].update(source='wrong')),
      ('next_stage_relabel','work/drc-audit-result.json',lambda x:x['next_stage'].update(eligible_for_separately_reviewed_RC_STA=True))]:
        refusals.append(reject(label,lambda name=name,fn=fn:body_case(name,fn)))
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)/'evidence';root.mkdir()
        small={'result.json':b'{}','selected.txt':b'exact selected','unselected.txt':b'full unseen member'}
        write(root,small);transport=Path(tmp)/'parts';transport.mkdir();manifest=pack(root,'fixture',transport,127)
        proof=a.audit_extract(manifest,transport,Path(tmp)/'selected',{n:a.c.digest(b)for n,b in small.items()},['selected.txt'])
        assert len(proof['all_original_files'])==3 and not(Path(tmp)/'selected/unselected.txt').exists()
        positives.append('real_complete_pack_selected_only_readback')
        expected={n:a.c.digest(b)for n,b in small.items()};expected['unselected.txt']='0'*64
        refusals.append(reject('unselected_member_hash',lambda:a.audit_extract(manifest,transport,Path(tmp)/'bad',expected,['selected.txt'])))
    # Direct file assembly executes against real files, including zero-length TR semantics.
    with tempfile.TemporaryDirectory()as tmp,patch.object(d,'OUT',Path(tmp)/'saved'):
        d.OUT.mkdir();output=Path(tmp)/'published';output.mkdir()
        for name in d.DIRECT:
            p=d.OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b''if name.endswith('.rpt')else b'{"exact":true}')
        summary={'outputs':{n:a.c.file_sha(d.OUT/n)for n in d.DIRECT}}
        paths=d.direct_files(output,summary,'fixture')
        assert len(paths)==len(d.DIRECT)-2 and len({p.name for p in paths})==len(paths)
        positives.append('actual_direct_JSON_files_empty_TR_explicitly_not_zero_claim')
        bad=copy.deepcopy(summary);bad['outputs'][d.DIRECT[0]]='0'*64
        refusals.append(reject('direct_digest',lambda:d.direct_files(output,bad,'bad')))
        bad=copy.deepcopy(summary);bad['outputs'].pop(d.DIRECT[0])
        refusals.append(reject('unrecorded_direct',lambda:d.direct_files(output,bad,'bad2')))
    import check_mainchip_saved_postroute_publication as pubcheck
    import publish_mainchip_saved_postroute as publisher
    import wait_cloud_tested_source_release as waiter
    with patch.object(publisher,'GROUP',d.GROUP):publication=pubcheck.controls()
    wait=waiter.controls()
    assert len(publication['positives'])==3 and len(publication['rejected'])==13
    assert len(wait['positive_cases'])==3 and len(wait['rejected'])==4
    assert len(positives)==4 and len(refusals)==31 and len(set(refusals))==31
    return dict(status='PASS_FAILED_SIGNAL_REPAIR_READBACK_SOURCE_CONTROLS',positives=positives,refusals=refusals,
        publication=publication,wait=wait,lifecycle=lifecycle_controls(),direct_publication=publication_controls(),fixture_ODB_not_used=True,synthetic_saved_reports=True,
        native_or_prior_archive_accessed=False,original_failed_run_not_accepted=True)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);r=dict(status='RUNNING_SOURCE_CONTROLS',source_head=os.environ['GITHUB_SHA'])
    try:r.update(controls())
    except BaseException as e:r.update(status='FAIL_SOURCE_CONTROLS',error=repr(e));raise
    finally:
        path=OUT/'boundary-controls.json';d.save(path,r)
if __name__=='__main__':main()
