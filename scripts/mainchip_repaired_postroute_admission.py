#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled proposal: admit only the exact completed original-class signal repair."""
import hashlib,json,os,shutil
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as repair
import mainchip_original_clock_drc as drc
from mainchip_clock_marker_capture import audit_extract,canonical_member
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/mainchip-repaired-postroute-bridge-methods.json'
SPEC=dict(run=40344497930,attempt=1,source_head='2a81095f744193451800ef178c9a7ae7314dd2dc',
    group='mainchip-fixed-clock-signal-repair',release=424387428,
    branch='codex/mainchip-fixed-clock-signal-repair',
    workflow='.github/workflows/mainchip-fixed-clock-signal-repair-cloud.yml',
    jobs={'controls':121647707160,'native':121648067587})
INPUT_PACKAGE=dict(run=39635867954,attempt=1,group='mainchip-postroute-inputs',
    source_head='d37ef5a4358933a7b9b106ef7f9c6724a4e71f3b',
    controller_sha256='b4ea0290387bd9891559c146b88aab274da60f180cad4b356bd53b986398382a',
    summary_sha256='069978a77028b77bc5a59534a241bb97b4d5ef3a13c3b72621133a64eb0cfd73',
    parts_sha256='256db094424d4c4f35afac9592a0339a241a615c9de6c4a636650e2ba215c716')
APP='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
PHASES=('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',
    'prepare','load-exact-saved-guides','guide-audit','one-signal-routing-attempt',
    'route-audit','paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit')
CANDIDATE='work/repaired.odb'
SELECTED=(CANDIDATE,'work/prepare-result.json','work/guide-audit-result.json',
    'work/route-audit-result.json','work/unfix-audit-result.json','work/drc-audit-result.json',
    'work/expected-original-class.def','work/repaired-audit.def','work/drc-before.def',
    'work/drc-after.def','work/measured-audit.def','work/initial-drc-markers.json',
    'work/initial-drc.rpt','work/initial-drc-reread.rpt',
    'work/original-gate-after-repair/result.json','work/original-gate-after-final-drc/result.json',
    'source-admission.json',*[f'supervision/{p}.command.json'for p in PHASES])
SOURCE_FILES={
    'scripts/cloud_mainchip_fixed_clock_signal_repair.py':'85e6f7799965f3f702ef1c37b4296ebd63bf910ea70c19ea4f4162fa9e35df98',
    'scripts/mainchip_fixed_clock_signal_repair_native.py':'a33fc4659e0da96325ebc8a5cc33dbc7afe5e350be0f9bd643848c0ab56ff386',
    'scripts/mainchip_fixed_clock_signal_repair.py':'fefe067abf459cd9827dcd89113eec3a63b948bf7a46146fdfe1f902e69f7c2d',
    'scripts/publish_mainchip_saved_postroute.py':'7f7b4d76261f7fe97a6ed779c32a2cf8c568766e74f5efd6e6139e308fa6b277'}
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
    assert m['repair_source']==SPEC and m['input_package']==INPUT_PACKAGE
    for name,h in m['protected'].items():assert c.file_sha(ROOT/name)==h,('Changed source',name)
    for name in ('native_routing_authorized','simulation_authorized','timing_accepted','full_phy_accepted','qualified_pex'):
        assert m[name]is False
    return m
def require_terminal_binding(m):
    pin=m['terminal_binding']
    assert type(pin)is dict,'Actual terminal repair proof is not yet bound'
    assert set(pin)=={'summary','parts','archive','assets','file_count','total_unpacked_bytes','candidate_sha256'}
    for key in ('summary','parts','archive'):
        row=pin[key];assert set(row)=={'bytes','sha256'}
        assert type(row['bytes'])is int and row['bytes']>0;hash_string(row['sha256'])
    assert pin['summary']['bytes']<=32*1024**2 and pin['parts']['bytes']<=32*1024**2
    assert type(pin['file_count'])is int and pin['file_count']>len(SELECTED)
    assert type(pin['total_unpacked_bytes'])is int and 0<pin['total_unpacked_bytes']<=12*1024**3
    hash_string(pin['candidate_sha256'])
    assert type(pin['assets'])is list and len(pin['assets'])>=3
    assert len({a['name']for a in pin['assets']})==len(pin['assets'])
    assert len({a['id']for a in pin['assets']})==len(pin['assets'])
    for a in pin['assets']:
        assert set(a)=={'id','name','bytes','sha256'}
        assert type(a['id'])is int and a['id']>0 and type(a['bytes'])is int and a['bytes']>0
        assert canonical_member(a['name']).parts==(a['name'],);hash_string(a['sha256'])
    return pin
def context():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    assert json_value(os.environ['NSSOC_INPUT_PACKAGE'])==INPUT_PACKAGE,'Different postroute input package'
    assert json_value(os.environ['NSSOC_COMPLETED_DRT'])==SPEC,'Different repaired-route descriptor'
def live_envelope(run,jobs,release,tag,pin):
    assert type(run['id'])is int and type(run['run_attempt'])is int
    assert (run['id'],run['run_attempt'],run['head_sha'])==(SPEC['run'],1,SPEC['source_head'])
    assert run['head_branch']==SPEC['branch']and run['path']==SPEC['workflow']
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='success'
    assert len(jobs['jobs'])==2
    assert {j['name']:(j['id'],j['status'],j['conclusion'])for j in jobs['jobs']}=={
        k:(v,'completed','success')for k,v in SPEC['jobs'].items()}
    import ensure_cloud_tested_source_release as guard
    name=f"cloud-results-{SPEC['run']}-1-{SPEC['group']}"
    guard.validate_release(release,tag,name,SPEC['source_head'])
    assert release['id']==SPEC['release']
    actual=[dict(id=a['id'],name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:'))
        for a in release['assets']if a['digest'].startswith('sha256:')]
    assert sorted(actual,key=lambda a:a['id'])==sorted(pin['assets'],key=lambda a:a['id'])
    assert len(actual)==len(release['assets'])
    return dict(run=SPEC['run'],attempt=1,source_head=SPEC['source_head'],release=SPEC['release'],terminal_success=True)
def summary(raw,pin):
    assert len(raw)==pin['summary']['bytes']and digest(raw)==pin['summary']['sha256']
    r=json_value(raw)
    assert type(r['run_id'])is int and type(r['run_attempt'])is int
    assert (r['run_id'],r['run_attempt'],r['source_head'])==(SPEC['run'],1,SPEC['source_head'])
    assert r['status']=='COMPLETE_BOUNDED_SIGNAL_REPAIR_NOT_RC_STA_OR_PHY_ACCEPTANCE'
    for k in ('accepted','final_timing_complete','full_phy_accepted','automatic_retry'):assert r[k]is False
    assert r['original_inputs_unchanged']is True and r['native_routing_started']is True
    assert r['runtime_appimage_sha256']==APP
    phases=r['phase_results'];assert [p['label']for p in phases]==list(PHASES)
    for p in phases:
        assert type(p['returncode'])is int and p['returncode']==0 and p['supervision_failure']is None
        assert p['process_group_cleanup']['remaining_live']==[]
        assert p['requested_timeout_seconds']==(14400 if p['label']=='one-signal-routing-attempt'else 1200)
    outputs=r['outputs'];assert type(outputs)is dict and 'result.json'not in outputs
    for name,h in outputs.items():canonical_member(name);hash_string(h)
    assert set(SELECTED)<=set(outputs)and outputs[CANDIDATE]==pin['candidate_sha256']
    assert len(outputs)+1==pin['file_count']
    eligible=repair.continuation_gate(r['native_result'])
    assert eligible==r['next_stage']==r['native_result']['next_stage']
    assert eligible['eligible_for_separately_reviewed_RC_STA']is True and eligible['DRT_markers']==0,'Nonzero final original-class DRC'
    assert r['native_result']['status']=='COMPLETE_SIGNAL_REPAIR_AND_ORIGINAL_CLASS_DRC_NOT_TIMING_OR_PHY_ACCEPTANCE'
    return r
def manifest(raw,pin):
    assert len(raw)==pin['parts']['bytes']and digest(raw)==pin['parts']['sha256']
    m=json_value(raw);stem=f"{SPEC['group']}-{SPEC['run']}-1"
    assert m['stem']==stem and m['source_directory']=='cloud-mainchip-fixed-clock-signal-repair'
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
    final=value('work/drc-audit-result.json');assert final==r['native_result']
    prior=value('work/unfix-audit-result.json')
    assert prior['status']=='PASS_ORIGINAL_CLASS_SIGNAL_REPAIR_REQUIRES_COMPLETE_DRC'
    assert prior['candidate_sha256']==pin['candidate_sha256']==expected[CANDIDATE]
    assert prior['original1691_clock_gate_passed']is True and prior['native_invariants_passed']is True
    assert prior['routing_delta']==final['routing_delta']
    via=prior['via_proof']
    assert via['definitions_present_and_identical_in_both_databases']is True and via['newly_generated_via_definitions_not_admitted']is True
    geometry=prior['native_geometry'];hash_string(geometry['sha256'])
    assert geometry['counts']['net']==143820 and geometry['counts']['instance']==153130
    for name in ('work/expected-original-class.def','work/repaired-audit.def','work/drc-before.def',
                 'work/drc-after.def','work/measured-audit.def'):
        assert expected[name]==prior['expected_def_sha256']
    for obj,name in ((prior,'work/original-gate-after-repair/result.json'),
                     (final,'work/original-gate-after-final-drc/result.json')):
        gate=value(name)
        assert obj['original_gate']==dict(result=gate,sha256=expected[name])
        assert gate['clock_or_fixed_nets']==1691 and gate['all_source_clock_and_fixed_records_preserved']is True
    measurement=final['final_DRT']
    marker=raw('work/initial-drc-markers.json')
    assert drc.bind_serialized_markers(measurement,marker)==measurement['serialized_markers']
    report=raw('work/initial-drc.rpt')
    assert report==raw('work/initial-drc-reread.rpt')==b''
    assert measurement['report_bytes']==0 and measurement['report_sha256']==digest(report)
    prep=value('work/prepare-result.json')
    assert prep['status']=='PREPARED_FIXED_CLOCK_SIGNAL_REPAIR'and prep['selected']==1691
    assert prep['timing_contract']==dict(clock_periods_ns=[20,4,8,8],derating_percent=5,new_RC_STA_required=True,accepted=False)
    guide=value('work/guide-audit-result.json')
    assert guide['status']=='PASS_EXACT_GUIDE_LOAD_BEFORE_ROUTING'
    g=guide['guide_proof'];assert type(g['guides'])is int and type(g['in_range_guides'])is int
    assert g['guides']>=g['in_range_guides']>0;hash_string(g['sha256'])
    assert guide['guide_loaded_odb_sha256']==expected['work/guide-loaded.odb']
    route=value('work/route-audit-result.json')
    assert route['status']=='PASS_SIGNAL_ONLY_DELTA_WITH_CLOCKS_ENCODED_FIXED'and route['native_invariants_passed']is True
    assert route['routing_delta']==prior['routing_delta']
    assert route['via_proof']['definitions_present_and_identical_in_both_databases']is True
    assert route['via_proof']['newly_generated_via_definitions_not_admitted']is True
    source=value('source-admission.json');assert source==r['source_admission']
    assert source['complete_clock_archive_verified']is True
    assert source['clock_inputs']==repair.CLOCK_INPUTS and source['global_inputs']==repair.GLOBAL_INPUTS
    for phase in r['phase_results']:
        record=value('supervision/'+phase['label']+'.command.json')
        projected=dict(phase);projected.pop('requested_timeout_seconds')
        assert record==projected,'Command summary differs from archived owned-process evidence'
    return dict(candidate_sha256=pin['candidate_sha256'],original1691_clock_gate_passed=True,
        final_original_class_DRT_markers=0,complete_original_inventory_verified=True,
        reported_count_kind='Final original-class read-only DRT census; not routing-iteration history',
        final_DRT=dict(sha256=measurement['report_sha256'],bytes=0,final_native_count=0,
            zero_count_and_empty_report_consistent=True,serialized_markers=measurement['serialized_markers']),
        input_package=INPUT_PACKAGE,resized_netlist_sha256='3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd',
        historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True,
        timing_accepted=False,qualified_pex=False,full_phy_accepted=False)
def consume(root,out):
    context();m=methods()
    assert m['cloud_restore_authorized']is True and m['native_execution_authorized']is True
    assert m['rc_sta_execution_authorized']is True
    pin=require_terminal_binding(m)
    assert root.resolve()==ROOT.resolve()
    assert out==ROOT/'cloud-mainchip-route12-postroute/geometry'
    assert out.is_dir()and all(not p.is_symlink()for p in (out,*out.parents))
    import ensure_cloud_tested_source_release as guard
    from cloud_mainchip_postroute_review import source_hash
    from route_cloud_newer_postcts import fetch
    name=f"cloud-results-{SPEC['run']}-1-{SPEC['group']}"
    envelope=live_envelope(guard.api('actions/runs/'+str(SPEC['run'])),
        guard.api('actions/runs/'+str(SPEC['run'])+'/jobs?per_page=100'),
        guard.api('releases/'+str(SPEC['release'])),guard.api('git/ref/tags/'+name),pin)
    for path,h in SOURCE_FILES.items():assert source_hash(path,SPEC['source_head'])==h==c.file_sha(ROOT/path)
    transport=out/'repaired-input';assert not transport.exists();transport.mkdir()
    required=pin['archive']['bytes']+pin['total_unpacked_bytes']+4*1024**3
    assert shutil.disk_usage(transport).free>=required,'Insufficient complete-archive restoration headroom'
    stem=f"{SPEC['group']}-{SPEC['run']}-1"
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
