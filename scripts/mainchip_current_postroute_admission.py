#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled successor: bind an actual successful compatible repair, never a prospective run."""
import hashlib,json,os,shutil
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as repair
import mainchip_original_clock_drc as drc
from mainchip_clock_marker_capture import audit_extract,canonical_member
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/mainchip-current-postroute-methods.json'
REPAIR_SCHEMA='two-signal-original-class-v1'
SOURCE_DIRECTORY='cloud-mainchip-two-signal-repair'
PRODUCER_PATHS=('scripts/cloud_mainchip_two_signal_repair.py',
    'scripts/mainchip_two_signal_repair.py','scripts/mainchip_two_signal_repair_native.py')
ALWAYS_FALSE=('native_routing_authorized','simulation_authorized','timing_accepted',
    'full_phy_accepted','qualified_pex','qualified_RC_minmax','automatic_retry')
EXECUTION_FLAGS=('cloud_restore_authorized','native_execution_authorized','rc_sta_execution_authorized')
INPUT_PACKAGE=dict(run=39635867954,attempt=1,group='mainchip-postroute-inputs',
    source_head='d37ef5a4358933a7b9b106ef7f9c6724a4e71f3b',
    controller_sha256='b4ea0290387bd9891559c146b88aab274da60f180cad4b356bd53b986398382a',
    summary_sha256='069978a77028b77bc5a59534a241bb97b4d5ef3a13c3b72621133a64eb0cfd73',
    parts_sha256='256db094424d4c4f35afac9592a0339a241a615c9de6c4a636650e2ba215c716')
APP='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
PHASES=('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',
    'ownership','prepare-fixed','paired-all-nontarget-fixed-import','fixed-audit',
    'one-two-signal-routing-attempt','route-audit','paired-original-class-return',
    'unfix-audit','full-original-class-read-only-DRT','drc-audit')
CANDIDATE='work/drc-observed.odb'
BASELINE_SHA='2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a'
NETLIST_SHA='3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd'
SELECTED=(CANDIDATE,'work/repaired.odb','work/prepare-fixed-result.json',
    'work/fixed-audit-result.json','work/route-audit-result.json','work/unfix-audit-result.json',
    'work/drc-audit-result.json','work/expected-original-class.def','work/repaired-audit.def',
    'work/drc-before.def','work/drc-after.def','work/measured-audit.def',
    'work/initial-drc-markers.json','work/initial-drc.rpt','work/initial-drc-reread.rpt',
    'work/original-gate-after-two-net-repair/result.json',
    'work/original-gate-after-final-two-net-drc/result.json',
    *[f'supervision/{p}.command.json'for p in PHASES],
    *[f'supervision/{p}.{stream}'for p in PHASES for stream in ('stdout','stderr')])
def digest(raw):return hashlib.sha256(raw).hexdigest()
def json_value(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:
            assert k not in result,'Duplicate JSON key'
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique)
def hash_string(h):
    assert type(h)is str and len(h)==64 and all(x in '0123456789abcdef'for x in h)
    return h
def methods():
    m=json_value(c.regular(METHOD).read_bytes())
    assert m['schema']=='mainchip-current-postroute-disabled-v1'
    assert m['input_package']==INPUT_PACKAGE and m['repair_schema']==REPAIR_SCHEMA
    assert m['original_numerical_sha256']=='c6335c535959286b7f77c3aaf6a5ab631640557c8453079a80dd97c97f58701f'
    assert m['clock_periods_ns']==[20,4,8,8]and m['derating_percent']==5
    for name,h in m['protected'].items():assert c.file_sha(ROOT/name)==h,('Changed source',name)
    validate_authorizations(m)
    return m

def validate_authorizations(m):
    for name in ALWAYS_FALSE:assert m[name]is False,('Forbidden authority',name)
    for name in (*EXECUTION_FLAGS,'source_controls_authorized'):
        assert type(m[name])is bool,('Authorization must be bool',name)
    assert len({m[name]for name in EXECUTION_FLAGS})==1,'Split native authorization'
    ready=m['readiness']
    assert set(ready)=={'admission_reviewed','worker_reviewed','outer_reviewed','import_closure_reviewed',
        'inactive_template_reviewed','actual_source_controls_passed','actual_success_bound'}
    assert all(type(v)is bool for v in ready.values()),'Readiness must be bool'
    if m['native_execution_authorized']:
        assert m['source_controls_authorized']is True,'Native execution requires source controls'
        assert all(ready.values()),'Postroute source readiness incomplete'
        require_terminal_binding(m)
    return m

def require_terminal_binding(m):
    pin=m['terminal_binding']
    assert type(pin)is dict,'Actual successful terminal repair is not bound'
    assert set(pin)=={'source','summary','parts','archive','assets','file_count',
        'total_unpacked_bytes','candidate_sha256','source_admission_sha256'}
    source=pin['source']
    assert set(source)=={'run','attempt','source_head','group','release','branch','workflow','jobs'}
    assert type(source['run'])is int and source['run']>0 and type(source['attempt'])is int and source['attempt']==1
    assert type(source['release'])is int and source['release']>0
    assert type(source['source_head'])is str and len(source['source_head'])==40
    assert all(v in '0123456789abcdef'for v in source['source_head'])
    assert source['group']=='mainchip-two-signal-repair'
    assert source['branch']=='codex/mainchip-fixed-clock-signal-repair'
    assert source['workflow']=='.github/workflows/mainchip-two-signal-repair-cloud.yml'
    assert set(source['jobs'])=={'controls','native'}
    assert all(type(v)is int and v>0 for v in source['jobs'].values())
    assert len(set(source['jobs'].values()))==2
    approved=m['approved_producer']
    assert type(approved)is dict and set(approved)=={'source_head','files','review'}
    assert approved['source_head']==source['source_head']
    assert set(PRODUCER_PATHS)<=set(approved['files'])
    for path,h in approved['files'].items():canonical_member(path);hash_string(h)
    review=approved['review']
    assert set(review)=={'path','sha256'}and review['path'].startswith('docs/evidence/')
    canonical_member(review['path']);hash_string(review['sha256'])
    assert m['protected'][review['path']]==review['sha256'],'Producer review must be protected'
    for key in ('summary','parts','archive'):
        row=pin[key];assert set(row)=={'bytes','sha256'}
        assert type(row['bytes'])is int and row['bytes']>0;hash_string(row['sha256'])
    assert pin['summary']['bytes']<=32*1024**2 and pin['parts']['bytes']<=32*1024**2
    assert type(pin['file_count'])is int and pin['file_count']>len(SELECTED)
    assert type(pin['total_unpacked_bytes'])is int and 0<pin['total_unpacked_bytes']<=12*1024**3
    hash_string(pin['candidate_sha256']);hash_string(pin['source_admission_sha256'])
    assert type(pin['assets'])is list and len(pin['assets'])>=3
    assert len({a['name']for a in pin['assets']})==len(pin['assets'])
    assert len({a['id']for a in pin['assets']})==len(pin['assets'])
    for a in pin['assets']:
        assert set(a)=={'id','name','bytes','sha256'}
        assert type(a['id'])is int and a['id']>0 and type(a['bytes'])is int and a['bytes']>0
        assert canonical_member(a['name']).parts==(a['name'],);hash_string(a['sha256'])
    return pin

def context(pin):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert json_value(os.environ['NSSOC_INPUT_PACKAGE'])==INPUT_PACKAGE,'Different postroute input package'
    assert json_value(os.environ['NSSOC_COMPLETED_DRT'])==pin['source'],'Different repaired-route descriptor'

def live_envelope(run,jobs,release,tag,pin):
    assert type(run['id'])is int and type(run['run_attempt'])is int
    assert (run['id'],run['run_attempt'],run['head_sha'])==(pin['source']['run'],1,pin['source']['source_head'])
    assert run['head_branch']==pin['source']['branch']and run['path']==pin['source']['workflow']
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='success'
    assert len(jobs['jobs'])==2
    assert {j['name']:(j['id'],j['status'],j['conclusion'])for j in jobs['jobs']}=={
        k:(v,'completed','success')for k,v in pin['source']['jobs'].items()}
    import ensure_cloud_tested_source_release as guard
    name=f"cloud-results-{pin['source']['run']}-1-{pin['source']['group']}"
    guard.validate_release(release,tag,name,pin['source']['source_head'])
    assert release['id']==pin['source']['release']
    actual=[dict(id=a['id'],name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:'))
        for a in release['assets']if a['digest'].startswith('sha256:')]
    assert sorted(actual,key=lambda a:a['id'])==sorted(pin['assets'],key=lambda a:a['id'])
    assert len(actual)==len(release['assets'])
    return dict(run=pin['source']['run'],attempt=1,source_head=pin['source']['source_head'],release=pin['source']['release'],terminal_success=True)
def summary(raw,pin):
    assert len(raw)==pin['summary']['bytes']and digest(raw)==pin['summary']['sha256']
    r=json_value(raw);source=pin['source']
    assert type(r['run_id'])is int and type(r['run_attempt'])is int
    assert (r['run_id'],r['run_attempt'],r['source_head'])==(source['run'],1,source['source_head'])
    assert r['status']=='COMPLETE_CONDITIONAL_TWO_SIGNAL_ATTEMPT_NOT_RC_STA_OR_PHY_ACCEPTANCE','Repair did not complete successfully'
    for k in ('accepted','final_timing_complete','full_phy_accepted','automatic_retry'):assert r[k]is False
    assert r['original_inputs_unchanged']is True and r['native_routing_started']is True
    assert r['original_guard_failure_preserved']is True and r['original_run_conclusion']=='failure'
    assert r['runtime_appimage_sha256']==APP
    assert r['only_allowed_signals']==['net36993','net459']
    phases=r['phase_results'];assert [p['label']for p in phases]==list(PHASES)
    for p in phases:
        assert type(p['returncode'])is int and p['returncode']==0 and p['supervision_failure']is None
        assert p['process_group_cleanup']['remaining_live']==[]
        assert p['requested_timeout_seconds']==(14400 if p['label']=='one-two-signal-routing-attempt'else 1200)
    terminal=r['terminal_checks']
    assert [x['label']for x in terminal]==['owned-process-cleanup','heartbeat-stop',
        'restore-signal-2','restore-signal-15','final-source-integrity']
    assert all(x==dict(label=x['label'],status='PASS')for x in terminal),'Repair terminal checks failed'
    outputs=r['outputs'];assert type(outputs)is dict and 'result.json'not in outputs
    for name,h in outputs.items():canonical_member(name);hash_string(h)
    assert set(SELECTED)<=set(outputs)and outputs[CANDIDATE]==pin['candidate_sha256']
    assert len(outputs)+1==pin['file_count']
    eligible=repair.continuation_gate(r['native_result'])
    assert eligible==r['next_stage']==r['native_result']['next_stage']
    assert eligible['eligible_for_separately_reviewed_RC_STA']is True and eligible['DRT_markers']==0,'Nonzero final original-class DRC'
    assert r['native_result']['status']=='COMPLETE_TWO_SIGNAL_ATTEMPT_ORIGINAL_CLASS_DRC_NOT_ACCEPTANCE'
    canonical=(json.dumps(r['source_admission'],sort_keys=True,separators=(',',':'))+'\n').encode()
    assert digest(canonical)==pin['source_admission_sha256'],'Different complete source admission'
    return r

def manifest(raw,pin):
    assert len(raw)==pin['parts']['bytes']and digest(raw)==pin['parts']['sha256']
    m=json_value(raw);stem=f"{pin['source']['group']}-{pin['source']['run']}-1"
    assert m['stem']==stem and m['source_directory']==SOURCE_DIRECTORY
    assert m['format']=='ordered-tar-gzip-parts-v1'
    assert m['bytes']==pin['archive']['bytes']and m['sha256']==pin['archive']['sha256']
    assert m['parts']and [p['index']for p in m['parts']]==list(range(len(m['parts'])))
    named={a['name']:a for a in pin['assets']}
    assert set(named)=={stem+'.summary.json',stem+'.parts.json',*[p['name']for p in m['parts']]}
    for suffix,key in (('.summary.json','summary'),('.parts.json','parts')):
        a=named[stem+suffix];assert {k:a[k]for k in ('bytes','sha256')}==pin[key]
    for i,p in enumerate(m['parts']):
        assert type(p['index'])is int and type(p['bytes'])is int and p['bytes']>0;hash_string(p['sha256'])
        assert p['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        a=named[p['name']];assert p['bytes']==a['bytes']and p['sha256']==a['sha256']
    assert sum(p['bytes']for p in m['parts'])==m['bytes']
    return m
def restored(r,root,inventory,pin):
    expected=dict(r['outputs'],**{'result.json':pin['summary']['sha256']})
    assert inventory['complete_original_inventory_verified_before_analysis']is True
    all_files=inventory['all_original_files']
    assert set(all_files)==set(expected)and len(all_files)==pin['file_count']
    assert all(all_files[n]['sha256']==h for n,h in expected.items())
    assert inventory['total_unpacked_bytes']==sum(v['bytes']for v in all_files.values())==pin['total_unpacked_bytes']
    def raw(name):
        p=c.regular(root/name)
        assert c.file_sha(p)==expected[name]and p.stat().st_size==all_files[name]['bytes'],('Restored file changed',name)
        return p.read_bytes()
    for name in SELECTED:
        p=c.regular(root/name)
        assert c.file_sha(p)==expected[name]and p.stat().st_size==all_files[name]['bytes'],('Restored file changed',name)
    assert inventory['selected_files']=={n:all_files[n]for n in SELECTED}
    def value(name):return json_value(raw(name))
    prepare=value('work/prepare-fixed-result.json')
    assert prepare['status']=='PREPARED_ALL_NONTARGET_FIXED_ENCODING'
    assert prepare['mutable']==['net36993','net459']
    assert (prepare['protected_wired'],prepare['protected_unwired'])==(143704,114)
    fixed=value('work/fixed-audit-result.json')
    assert fixed['status']=='PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT'
    assert fixed['fixed_odb_sha256']==expected['work/fixed.odb']
    assert fixed['repair_tcl_sha256']==expected['work/repair.tcl']
    assert fixed['guide_proof']==dict(guides=1173427,in_range_guides=770474,
        sha256='b51c6617d53747bdf53b64860f71a28e81885c8cf932b9cb38cd7fcbbebc7780',
        source='Exact saved global guide loaded and observed through dbGuide before routing')
    assert fixed['timing_contract']==dict(accepted=False,clock_periods_ns=[20,4,8,8],
        derating_percent=5,new_RC_STA_required=True)
    census=fixed['router_census']
    assert census['class_counts']==dict(ordinary_fixed=143704,ordinary_unwired=112,special=2,target=2)
    assert census['all_other_wired_paths_encoded_FIXED']is True and census['no_unguided_fallback_admitted']is True
    assert census['two_routed_nonfixed_guided_names']==['net36993','net459']
    assert census['actual_special_nonparticipants']==['VGND','VPWR']
    assert len(census['unwired_nonparticipants'])==len(set(census['unwired_nonparticipants']))==112
    hash_string(census['observed_rows_sha256'])
    assert set(census['saved_census'])=={'router-census-observed.json','router-census-report.json'}
    for name,h in census['saved_census'].items():assert h==expected['work/'+name]
    for report in (prepare,fixed):
        assert report['original_run_failure_preserved']is True
        for key in ('accepted','timing_accepted','full_phy_accepted'):assert report[key]is False
    final=value('work/drc-audit-result.json');assert final==r['native_result']
    prior=value('work/unfix-audit-result.json')
    assert prior['status']=='PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC'
    assert prior['candidate_sha256']==expected['work/repaired.odb']
    assert prior['original1691_clock_gate_passed']is True and prior['native_invariants_passed']is True
    delta=prior['routing_delta'];assert delta==final['routing_delta']
    assert delta['only_two_signals_permitted']==['net36993','net459']
    assert delta['other_records_byte_exact']is True and delta['non_NETS_bytes_exact']is True
    assert delta['changed_signal_names']==sorted(set(delta['changed_signal_names']))
    assert set(delta['changed_signal_names'])<=set(('net36993','net459'))
    assert type(delta['changed_signal_count'])is int and delta['changed_signal_count']==len(delta['changed_signal_names'])
    assert delta['accepted']is False
    via=prior['via_proof']
    assert via['definitions_present_and_identical_in_both_databases']is True and via['newly_generated_via_definitions_not_admitted']is True
    geometry=prior['native_geometry'];hash_string(geometry['sha256'])
    assert geometry['counts']['net']==143820 and geometry['counts']['instance']==153130
    for name in ('work/expected-original-class.def','work/repaired-audit.def','work/drc-before.def',
                 'work/drc-after.def','work/measured-audit.def'):
        assert expected[name]==prior['expected_def_sha256']
    for obj,name,candidate in (
        (prior,'work/original-gate-after-two-net-repair/result.json','work/repaired.odb'),
        (final,'work/original-gate-after-final-two-net-drc/result.json',CANDIDATE)):
        gate=value(name)
        assert obj['original_gate']==dict(result=gate,sha256=expected[name])
        assert gate['status']=='PASS_ALL_SOURCE_CLOCK_AND_FIXED_NET_DEF_RECORDS_AND_ATTACHED_GEOMETRY_EXACT'
        assert gate['clock_or_fixed_nets']==1691 and gate['all_source_clock_and_fixed_records_preserved']is True
        assert gate['source_hashes'][str(ROOT/SOURCE_DIRECTORY/candidate)]==expected[candidate]
        assert set(gate['source_hashes'].values())=={BASELINE_SHA,expected[candidate]}
        assert len(gate['source_hashes'])==2 and gate['accepted']is False
    measurement=final['final_DRT']
    marker=raw('work/initial-drc-markers.json')
    assert drc.bind_serialized_markers(measurement,marker)==measurement['serialized_markers']
    report=raw('work/initial-drc.rpt')
    assert report==raw('work/initial-drc-reread.rpt')==b''
    assert measurement['marker_count']==0 and measurement['zero_reported_DRT_markers']is True
    assert measurement['all_categories_below_native_cap']is True and measurement['full_signoff_DRC']is False
    assert measurement['report_bytes']==0 and measurement['report_sha256']==digest(report)
    route=value('work/route-audit-result.json')
    assert route['status']=='PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED'
    assert route['native_invariants_passed']is True and route['routing_delta']==delta
    assert route['via_proof']==via
    for phase in r['phase_results']:
        record=value('supervision/'+phase['label']+'.command.json')
        projected=dict(phase);projected.pop('requested_timeout_seconds')
        assert record==projected,'Command summary differs from archived owned-process evidence'
        for stream in ('stdout','stderr'):
            name='supervision/'+phase['label']+'.'+stream
            assert record[stream+'_sha256']==expected[name]and record[stream+'_bytes']==all_files[name]['bytes']
    return dict(candidate_sha256=pin['candidate_sha256'],original1691_clock_gate_passed=True,
        final_original_class_DRT_markers=0,complete_original_inventory_verified=True,
        reported_count_kind='Final original-class read-only DRT census; not routing-iteration history',
        final_DRT=dict(sha256=measurement['report_sha256'],bytes=0,final_native_count=0,
            zero_count_and_empty_report_consistent=True,serialized_markers=measurement['serialized_markers']),
        input_package=INPUT_PACKAGE,resized_netlist_sha256=NETLIST_SHA,
        historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True,
        original_failed_input_preserved=True,timing_accepted=False,qualified_pex=False,full_phy_accepted=False)

def consume(root,out):
    m=methods()
    assert m['cloud_restore_authorized']is True and m['native_execution_authorized']is True
    assert m['rc_sta_execution_authorized']is True
    pin=require_terminal_binding(m);context(pin)
    assert root.resolve()==ROOT.resolve()
    assert out==ROOT/'cloud-mainchip-route12-postroute/geometry'
    assert out.is_dir()and all(not p.is_symlink()for p in (out,*out.parents))
    import ensure_cloud_tested_source_release as guard
    from cloud_mainchip_postroute_review import source_hash
    from route_cloud_newer_postcts import fetch
    name=f"cloud-results-{pin['source']['run']}-1-{pin['source']['group']}"
    envelope=live_envelope(guard.api('actions/runs/'+str(pin['source']['run'])),
        guard.api('actions/runs/'+str(pin['source']['run'])+'/jobs?per_page=100'),
        guard.api('releases/'+str(pin['source']['release'])),guard.api('git/ref/tags/'+name),pin)
    for path,h in m['approved_producer']['files'].items():
        assert source_hash(path,pin['source']['source_head'])==h,('Changed producer source',path)
    transport=out/'repaired-input';assert not transport.exists();transport.mkdir()
    required=pin['archive']['bytes']+pin['total_unpacked_bytes']+4*1024**3
    assert shutil.disk_usage(transport).free>=required,'Insufficient complete-archive restoration headroom'
    stem=f"{pin['source']['group']}-{pin['source']['run']}-1"
    base='https://github.com/Melihakbulut221/nssoc/releases/download/'+name+'/'
    for suffix,key in (('.summary.json','summary'),('.parts.json','parts')):
        fetch(base+stem+suffix,pin[key]['sha256'],transport/key)
    raw=c.regular(transport/'summary').read_bytes();r=summary(raw,pin)
    parts=manifest(c.regular(transport/'parts').read_bytes(),pin)
    for p in parts['parts']:fetch(base+p['name'],p['sha256'],transport/p['name'])
    expected=dict(r['outputs'],**{'result.json':pin['summary']['sha256']})
    inventory=audit_extract(parts,transport,transport/'selected',expected,SELECTED)
    proof=restored(r,transport/'selected',inventory,pin)
    destination=out/'routed/work/detailed-route.odb'
    assert not (out/'routed').exists();destination.parent.mkdir(parents=True)
    shutil.copyfile(transport/'selected'/CANDIDATE,destination)
    assert c.file_sha(destination)==pin['candidate_sha256']
    proof.update(envelope=envelope,summary_sha256=pin['summary']['sha256'],parts_sha256=pin['parts']['sha256'],
        complete_archive=inventory,compatibility_mapping=dict(original_member=CANDIDATE,
            compatibility_member='routed/work/detailed-route.odb',sha256=pin['candidate_sha256'],
            same_bytes=True,no_historical_log_or_CRIU_provenance_fabricated=True))
    return destination,proof
