#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact selected-text diagnosis of the completed, unsuccessful two-net repair."""
import json,shutil
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as repair
import mainchip_original_clock_drc as drc
import mainchip_clock_marker_classification as classification
import mainchip_two_signal_repair as source
from mainchip_clock_marker_capture import audit_extract,canonical_member
RUN=40572767703
SOURCE='3ee00226fe604d6c019c383e773dc23b5892afc9'
GROUP='mainchip-two-signal-repair'
RELEASE=425914881
PREFIX='docs/evidence/mainchip-two-signal-typed-special-native-terminal-20261027'
SUMMARY='85e4594592bd1cb54041824eb5125c3b9204aec9064eb439449ab4b8a223f0a7'
PARTS='52fbcef18cb058497850b38a7e3887ff25e3ab85c5f1767d0242648e9604d558'
ARCHIVE='10eeca6214afc595be11ec8b9c0ae4e0c76dd2925baf571af54245e24aee404a'
FINAL_ODB='13eda10135ad036c7e2e6b9ba0559210c8bee8008ad42e9da81c53301837342a'
PHASES=('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version','ownership',
 'prepare-fixed','paired-all-nontarget-fixed-import','fixed-audit','one-two-signal-routing-attempt',
 'route-audit','paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit')
GATES=('before-two-net-repair','after-two-net-repair','after-final-two-net-drc')
SELECTED=(
 *['work/'+p for p in ('ownership-result.json','ownership.json','owners.json','original-classes.json',
 'prepare-fixed-result.json','fixed-audit-result.json','router-census-observed.json','router-census-report.json',
 'route-audit-result.json','unfix-audit-result.json','drc-audit-result.json',
 'repair.tcl','fixed.tcl','unfix.tcl','final-drc.tcl','source-markers.json','source-markers.rpt',
 'initial-drc-markers.json','initial-drc.rpt','initial-drc-reread.rpt','expected-original-class.def',
 'fixed-routing.drc','fixed-routing.drc-5.rpt','fixed-routing.drc-10.rpt','fixed-routing.drc-15.rpt','fixed-routing.drc-20.rpt')],
 *['work/original-gate-'+g+'/result.json'for g in GATES],
 *[f'supervision/{p}.{suffix}'for p in PHASES for suffix in ('command.json','stdout','stderr')],
 'supervision/events.jsonl','supervision/latest.json')
ASSETS={682825447:(GROUP+'-'+str(RUN)+'-1.summary.json',659276,SUMMARY),
 682825546:(GROUP+'-'+str(RUN)+'-1.parts.json',868,PARTS),
 682825666:(GROUP+'-'+str(RUN)+'-1.tar.gz.part0000',767365866,ARCHIVE)}
MAX_SELECTED=1024**3
MAX_JSON=256*1024**2
def value(raw):return classification.json_read(raw)
def live_envelope(run,jobs,release,tag):
    assert (run['id'],run['run_attempt'],run['head_sha'])==(RUN,1,SOURCE)
    assert run['head_branch']=='codex/mainchip-fixed-clock-signal-repair'
    assert run['path']=='.github/workflows/mainchip-two-signal-repair-cloud.yml'
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='success'
    assert jobs['total_count']==len(jobs['jobs'])==2
    assert {j['id']:(j['name'],j['status'],j['conclusion'])for j in jobs['jobs']}=={
      122431088644:('controls','completed','success'),122432552864:('native','completed','success')}
    assert all(j['run_id']==RUN and j['head_sha']==SOURCE for j in jobs['jobs'])
    import ensure_cloud_tested_source_release as guard
    guard.validate_release(release,tag,f'cloud-results-{RUN}-1-{GROUP}',SOURCE)
    assert release['id']==RELEASE and len(release['assets'])==len(ASSETS)
    assert len({a['id']for a in release['assets']})==len(ASSETS)
    for a in release['assets']:
        name,size,digest=ASSETS[a['id']]
        assert (a['name'],a['size'],a['digest'])==(name,size,'sha256:'+digest)
    return dict(run=RUN,attempt=1,source_head=SOURCE,release=RELEASE,
      execution_conclusion='success',repair_succeeded=False,original_guard_failure_preserved=True)
def expected_report(raw):
    assert len(raw)==659276 and c.digest(raw)==SUMMARY
    r=value(raw)
    assert (r['run_id'],r['run_attempt'],r['source_head'])==(RUN,1,SOURCE)
    assert r['status']=='COMPLETE_CONDITIONAL_TWO_SIGNAL_ATTEMPT_NOT_RC_STA_OR_PHY_ACCEPTANCE'
    assert r['native_routing_started']is True and r['original_inputs_unchanged']is True
    assert r['original_run']==40344497930 and r['original_run_conclusion']=='failure'
    assert r['original_guard_failure_preserved']is True and r['prior_DRT_markers']==3
    assert all(r[k]is False for k in ('accepted','automatic_retry','final_timing_complete','full_phy_accepted'))
    assert r['only_allowed_signals']==list(source.TARGETS)
    assert [p['label']for p in r['phase_results']]==list(PHASES)
    for p in r['phase_results']:
        assert p['returncode']==0 and p['supervision_failure']is None
        assert p['process_group_cleanup']['remaining_live']==[]
        assert p['requested_timeout_seconds']==(14400 if p['label']=='one-two-signal-routing-attempt'else 1200)
    assert r['terminal_checks']==[dict(label=k,status='PASS')for k in (
      'owned-process-cleanup','heartbeat-stop','restore-signal-2','restore-signal-15','final-source-integrity')]
    assert r['native_result']['routing_delta']['changed_signal_names']==[]
    assert r['native_result']['routing_delta']['changed_signal_count']==0
    assert r['native_result']['final_DRT']['marker_count']==3
    assert r['next_stage']['eligible_for_separately_reviewed_RC_STA']is False
    assert len(r['outputs'])==155 and 'result.json'not in r['outputs']
    assert r['outputs']['work/drc-observed.odb']==FINAL_ODB
    assert set(SELECTED)<=set(r['outputs']) and len(SELECTED)==len(set(SELECTED))
    for name,digest in r['outputs'].items():
        canonical_member(name)
        assert type(digest)is str and len(digest)==64 and all(x in '0123456789abcdef'for x in digest)
    return r
def manifest(raw):
    assert len(raw)==868 and c.digest(raw)==PARTS
    m=value(raw);stem=f'{GROUP}-{RUN}-1'
    assert m['format']=='ordered-tar-gzip-parts-v1'and m['stem']==stem
    assert m['source_directory']=='cloud-mainchip-two-signal-repair'
    assert m['bytes']==767365866 and m['sha256']==ARCHIVE
    assert m['parts']==[dict(index=0,name=stem+'.tar.gz.part0000',bytes=767365866,sha256=ARCHIVE)]
    assert m['verification']==dict(parts=1,bytes=767365866,sha256=ARCHIVE,all_parts_and_combined_bytes_verified=True)
    return m
def restore(transport):
    import ensure_cloud_tested_source_release as guard
    from route_cloud_newer_postcts import fetch
    name=f'cloud-results-{RUN}-1-{GROUP}'
    envelope=live_envelope(guard.api('actions/runs/'+str(RUN)),
      guard.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100'),
      guard.api('releases/'+str(RELEASE)),guard.api('git/ref/tags/'+name))
    assert not transport.exists();transport.mkdir()
    # Frozen extractor streams all members: <=12GiB uncompressed, <=4GiB each.
    # With <1GiB compressed input, 16GiB free also covers a refused large selection.
    assert shutil.disk_usage(transport).free>=16*1024**3
    stem=f'{GROUP}-{RUN}-1';url='https://github.com/Melihakbulut221/nssoc/releases/download/'+name+'/'
    for suffix,digest in (('.summary.json',SUMMARY),('.parts.json',PARTS)):
        fetch(url+stem+suffix,digest,transport/('input'+suffix))
        assert (transport/('input'+suffix)).read_bytes()==c.regular(c.ROOT/(PREFIX+suffix)).read_bytes()
    r=expected_report(c.regular(transport/'input.summary.json').read_bytes())
    m=manifest(c.regular(transport/'input.parts.json').read_bytes())
    for p in m['parts']:fetch(url+p['name'],p['sha256'],transport/p['name'])
    expected=dict(r['outputs'],**{'result.json':SUMMARY})
    proof=audit_extract(m,transport,transport/'selected',expected,SELECTED)
    assert len(proof['all_original_files'])==156 and proof['complete_original_inventory_verified_before_analysis']is True
    assert sum(x['bytes']for x in proof['selected_files'].values())<=MAX_SELECTED
    for name,info in proof['selected_files'].items():
        if name.endswith('.json'):assert info['bytes']<=MAX_JSON
    return r,dict(envelope=envelope,inventory=proof,summary_sha256=SUMMARY,parts_sha256=PARTS,
      all156_members_authenticated=True,selected_text_only=True,no_ODB_selected=True)
def inspect_saved(root,r):
    def raw(name):
        p=c.regular(root/name)
        if name.endswith('.json'):assert p.stat().st_size<=MAX_JSON
        data=p.read_bytes()
        assert c.digest(data)==r['outputs'][name],('Changed selected saved bytes',name)
        return data
    def read(name):return value(raw(name))
    assert sum(c.regular(root/name).stat().st_size for name in SELECTED)<=MAX_SELECTED
    for name in SELECTED:raw(name)
    commands={}
    for index,label in enumerate(PHASES):
        row=read('supervision/'+label+'.command.json')
        assert row['label']==label and row['process_group_cleanup']['remaining_live']==[]
        for stream in ('stdout','stderr'):
            data=raw('supervision/'+label+'.'+stream)
            assert (len(data),c.digest(data))==(row[stream+'_bytes'],row[stream+'_sha256'])
        original=dict(r['phase_results'][index]);original.pop('requested_timeout_seconds')
        assert row==original and row['returncode']==0 and row['supervision_failure']is None
        commands[label]=row
    final=read('work/drc-audit-result.json')
    assert final==r['native_result']
    assert final['status']=='COMPLETE_TWO_SIGNAL_ATTEMPT_ORIGINAL_CLASS_DRC_NOT_ACCEPTANCE'
    assert final['original1691_clock_gate_passed']is True and final['native_invariants_passed']is True
    prior=read('work/unfix-audit-result.json')
    assert prior['status']=='PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC'
    assert prior['candidate_sha256']==r['outputs']['work/repaired.odb']
    assert prior['expected_def_sha256']==r['outputs']['work/expected-original-class.def']
    assert prior['routing_delta']==final['routing_delta']
    assert prior['original1691_clock_gate_passed']is True and prior['native_invariants_passed']is True
    assert final['routing_delta']['changed_signal_count']==0 and final['routing_delta']['changed_signal_names']==[]
    gates={g:read('work/original-gate-'+g+'/result.json')for g in GATES}
    for g,gate in gates.items():
        assert gate['clock_or_fixed_nets']==1691 and gate['all_source_clock_and_fixed_records_preserved']is True
    for label,obj in ((GATES[1],prior),(GATES[2],final)):
        name='work/original-gate-'+label+'/result.json'
        assert obj['original_gate']==dict(result=gates[label],sha256=r['outputs'][name])
    ownership=read('work/ownership.json');assert ownership==r['ownership']
    ownership_phase=read('work/ownership-result.json')
    assert ownership_phase['native_ownership']==ownership
    assert ownership_phase['original_gate']==dict(result=gates[GATES[0]],sha256=r['outputs']['work/original-gate-'+GATES[0]+'/result.json'])
    owners=read('work/owners.json');names=owners['selected']
    assert names==sorted(set(names))and len(names)==1691 and owners['net_count']==143820
    assert c.digest(c.canonical(names))==repair.SELECTED_SHA
    assert owners['mutable']==list(source.TARGETS) and len(set(owners['frozen']))==143818
    net_inventory=classification.net_inventory(raw('work/expected-original-class.def'),names)
    assert len(net_inventory)==143820 and set(net_inventory)==set(owners['frozen'])|set(source.TARGETS)
    measurement=final['final_DRT'];marker=raw('work/initial-drc-markers.json')
    assert drc.bind_serialized_markers(measurement,marker)==measurement['serialized_markers']
    report=raw('work/initial-drc.rpt')
    assert report==raw('work/initial-drc-reread.rpt')==raw('work/source-markers.rpt')
    assert marker==raw('work/source-markers.json')
    assert (len(report),c.digest(report))==(measurement['report_bytes'],measurement['report_sha256'])
    classified=classification.analyze(marker,report,measurement,net_inventory,names)
    assert classified['marker_count']==3 and final['next_stage']==r['next_stage']==source.require_complete(final)
    assert final['next_stage']['eligible_for_separately_reviewed_RC_STA']is False
    observed=read('work/router-census-observed.json');census=read('work/router-census-report.json')
    assert observed['status']=='COMPLETE_ROUTER_CENSUS_GATE_NOT_ROUTING_ACCEPTANCE'
    assert observed['enumeration_complete']is True and observed['enumerated_count']==143820
    assert observed['duplicate_names']==[] and observed['current_net']is None and observed['accepted']is False
    assert observed['source_odb_sha256']==r['outputs']['work/fixed.odb']
    rederived=source.router_census_observation(observed['rows'],owners)
    assert all(census[k]==v for k,v in rederived.items())
    assert census['refusals']==census['native_observation_refusals']==[]
    assert census['observation_status']==observed['status']and census['enumeration_complete']is True
    assert census['enumerated_count']==143820 and census['current_net']is None
    assert set(observed['special_observations'])==set(census['special_names'])
    fixed=read('work/fixed-audit-result.json')
    assert fixed['status']=='PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT'
    expected_census=source.router_census(observed['rows'],owners)
    expected_census['saved_census']={n:r['outputs']['work/'+n]for n in ('router-census-observed.json','router-census-report.json')}
    assert fixed['router_census']==expected_census
    assert fixed['repair_tcl_sha256']==r['outputs']['work/repair.tcl']
    assert fixed['fixed_odb_sha256']==r['outputs']['work/fixed.odb']
    route=read('work/route-audit-result.json')
    assert route['status']=='PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED'and route['native_invariants_passed']is True
    assert route['routing_delta']['changed_signal_names']==[] and route['routing_delta']['changed_signal_count']==0
    classes=read('work/original-classes.json')
    assert set(classes)==set(owners['frozen'])and all(v in (None,'ROUTED','FIXED')for v in classes.values())
    options=raw('work/repair.tcl').decode('utf-8')
    router_log=raw('supervision/one-two-signal-routing-attempt.stdout').decode('utf-8')
    assert len(router_log.encode())==r['route_log']['bytes']and c.digest(router_log.encode())==r['route_log']['sha256']
    # Lines are indexed verbatim for review, not interpreted as a replacement for full DRC.
    indexed=[dict(line=i,text=line)for i,line in enumerate(router_log.splitlines(),1)
      if any(token in line.lower()for token in ('drc','violation','guide','route','net','fixed','warn','error'))]
    return dict(status='COMPLETE_CURRENT_TWO_SIGNAL_TEXT_DIAGNOSIS_NOT_REPAIR_ACCEPTANCE',
      original_run=RUN,source=SOURCE,execution_conclusion='success',repair_succeeded=False,
      original_guard_failure_preserved=True,reroute_authorized=False,postroute_bridge_eligible=False,
      accepted=False,full_phy_accepted=False,final_timing_complete=False,
      selected_clock_fixed_count=1691,remaining_marker_count=3,
      changed_signal_count=0,changed_signal_names=[],classification=classified,
      saved_final_native_audit=final,saved_unfix_audit=prior,saved_route_audit=route,
      saved_original_clock_gates=gates,complete_original_command_records=commands,
      router_census=census,exact_target_rows={n:observed['rows'][n]for n in source.TARGETS},
      exact_special_rows={n:observed['rows'][n]for n in census['special_names']},
      special_observation_file_sha256=r['outputs']['work/router-census-observed.json'],
      saved_fixed_audit=fixed,original_classes_sha256=r['outputs']['work/original-classes.json'],
      repair_Tcl_exact=options,router_log_index=indexed,
      full_router_stdout_sha256=r['outputs']['supervision/one-two-signal-routing-attempt.stdout'],
      fixed_overlay_report_empty=len(raw('work/fixed-routing.drc'))==0,
      original_class_markers_unchanged=True,
      root_cause_established=False,
      interpretation='The saved attempt completed and changed zero signal records. Three original-class shorts remain; routing-overlay output is not final DRC acceptance.')
