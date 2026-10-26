#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Saved-result readback of the exact failed repair; no native process or waiver."""
import json,shutil
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as repair
import mainchip_original_clock_drc as drc
import mainchip_clock_marker_classification as classification
from mainchip_clock_marker_capture import audit_extract,canonical_member
RUN=40344497930
SOURCE='2a81095f744193451800ef178c9a7ae7314dd2dc'
GROUP='mainchip-fixed-clock-signal-repair'
RELEASE=424387428
PREFIX='docs/evidence/mainchip-fixed-clock-signal-repair-via-corrected-native-terminal-20261026'
SUMMARY='74c86b9b1526342aff7da67d1e009ad6050f66e64f6459d355d5f522fa437f09'
PARTS='00f403be73b0624fb99d13ae4d278c4734fbb55533a068d07ca9655d05c1b186'
ARCHIVE='2acb6d217a19a10acbf0af4b5858bbef865c2e9b299b6ad9720f2e88c1357f96'
PHASES=('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version','prepare',
 'load-exact-saved-guides','guide-audit','one-signal-routing-attempt','route-audit',
 'paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit')
SELECTED=('work/prepare-result.json','work/guide-audit-result.json','work/route-audit-result.json',
 'work/unfix-audit-result.json','work/drc-audit-result.json','work/ownership.json',
 'work/original-gate-before-repair/result.json','work/original-gate-after-repair/result.json',
 'work/original-gate-after-final-drc/result.json','work/initial-drc-markers.json',
 'work/initial-drc.rpt','work/initial-drc-reread.rpt','work/expected-original-class.def',
 *[f'supervision/{p}.{suffix}'for p in PHASES for suffix in ('command.json','stdout','stderr')])
ASSETS={678934198:(GROUP+'-'+str(RUN)+'-1.summary.json',61963,SUMMARY),
 678934314:(GROUP+'-'+str(RUN)+'-1.parts.json',892,PARTS),
 678934435:(GROUP+'-'+str(RUN)+'-1.tar.gz.part0000',670979402,ARCHIVE)}
def value(raw):return classification.json_read(raw)
def live_envelope(run,jobs,release,tag):
    assert (run['id'],run['run_attempt'],run['head_sha'])==(RUN,1,SOURCE)
    assert run['head_branch']=='codex/mainchip-fixed-clock-signal-repair'
    assert run['path']=='.github/workflows/mainchip-fixed-clock-signal-repair-cloud.yml'
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='failure'
    assert len(jobs['jobs'])==2
    assert {j['id']:(j['name'],j['status'],j['conclusion'])for j in jobs['jobs']}=={
        121647707160:('controls','completed','success'),121648067587:('native','completed','failure')}
    import ensure_cloud_tested_source_release as guard
    name=f'cloud-results-{RUN}-1-{GROUP}'
    guard.validate_release(release,tag,name,SOURCE)
    assert release['id']==RELEASE and len(release['assets'])==len(ASSETS)
    assert len({a['id']for a in release['assets']})==len(ASSETS)
    for a in release['assets']:
        name,size,digest=ASSETS[a['id']]
        assert (a['name'],a['size'],a['digest'])==(name,size,'sha256:'+digest)
    return dict(run=RUN,attempt=1,source_head=SOURCE,release=RELEASE,
        original_conclusion='failure',resource_guard_failure_preserved=True)
def expected_report(raw):
    assert len(raw)==61963 and c.digest(raw)==SUMMARY
    r=value(raw)
    assert (r['run_id'],r['run_attempt'],r['source_head'])==(RUN,1,SOURCE)
    assert r['status']=='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR'and r['native_routing_started']is True
    assert all(r[k]is False for k in ('accepted','automatic_retry','final_timing_complete','full_phy_accepted'))
    assert r['prior_DRT_markers']==762
    assert [p['label']for p in r['phase_results']]==list(PHASES[:-1])
    for p in r['phase_results']:
        assert p['returncode']==0 and p['supervision_failure']is None
        assert p['process_group_cleanup']['remaining_live']==[]
        assert p['requested_timeout_seconds']==(14400 if p['label']=='one-signal-routing-attempt'else 1200)
    assert 'memory_sample_unavailable'in r['error']and 'Persistent unavailable live VmRSS'in r['error']
    assert len(r['outputs'])==93 and 'result.json'not in r['outputs']
    assert set(SELECTED)<=set(r['outputs'])
    for name,digest in r['outputs'].items():
        canonical_member(name)
        assert type(digest)is str and len(digest)==64 and all(x in '0123456789abcdef'for x in digest)
    return r
def manifest(raw):
    assert len(raw)==892 and c.digest(raw)==PARTS
    m=value(raw);stem=f'{GROUP}-{RUN}-1'
    assert m['format']=='ordered-tar-gzip-parts-v1'and m['stem']==stem
    assert m['source_directory']=='cloud-mainchip-fixed-clock-signal-repair'
    assert m['bytes']==670979402 and m['sha256']==ARCHIVE
    assert m['parts']==[dict(index=0,name=stem+'.tar.gz.part0000',bytes=670979402,sha256=ARCHIVE)]
    return m
def restore(transport):
    import ensure_cloud_tested_source_release as guard
    from route_cloud_newer_postcts import fetch
    name=f'cloud-results-{RUN}-1-{GROUP}'
    envelope=live_envelope(guard.api('actions/runs/'+str(RUN)),
        guard.api('actions/runs/'+str(RUN)+'/jobs?per_page=100'),
        guard.api('releases/'+str(RELEASE)),guard.api('git/ref/tags/'+name))
    assert not transport.exists();transport.mkdir()
    assert shutil.disk_usage(transport).free>=8*1024**3
    stem=f'{GROUP}-{RUN}-1';url='https://github.com/Melihakbulut221/nssoc/releases/download/'+name+'/'
    for suffix,digest in (('.summary.json',SUMMARY),('.parts.json',PARTS)):
        fetch(url+stem+suffix,digest,transport/('input'+suffix))
        assert (transport/('input'+suffix)).read_bytes()==c.regular(c.ROOT/(PREFIX+suffix)).read_bytes()
    r=expected_report(c.regular(transport/'input.summary.json').read_bytes())
    m=manifest(c.regular(transport/'input.parts.json').read_bytes())
    for p in m['parts']:fetch(url+p['name'],p['sha256'],transport/p['name'])
    expected=dict(r['outputs'],**{'result.json':SUMMARY})
    proof=audit_extract(m,transport,transport/'selected',expected,SELECTED)
    assert len(proof['all_original_files'])==94 and proof['complete_original_inventory_verified_before_analysis']is True
    return r,dict(envelope=envelope,inventory=proof,summary_sha256=SUMMARY,parts_sha256=PARTS)
def inspect_saved(root,r):
    def raw(name):
        data=c.regular(root/name).read_bytes()
        assert c.digest(data)==r['outputs'][name],('Changed selected saved bytes',name)
        return data
    def read(name):return value(raw(name))
    for name in SELECTED:raw(name)
    commands={}
    for index,label in enumerate(PHASES):
        row=read('supervision/'+label+'.command.json')
        assert row['label']==label and row['process_group_cleanup']['remaining_live']==[]
        for stream in ('stdout','stderr'):
            data=raw('supervision/'+label+'.'+stream)
            assert (len(data),c.digest(data))==(row[stream+'_bytes'],row[stream+'_sha256'])
        if index<len(PHASES)-1:
            original=dict(r['phase_results'][index]);original.pop('requested_timeout_seconds')
            assert row==original
        else:
            assert row['returncode']==0 and row['supervision_failure']=='memory_sample_unavailable'
            assert 'Persistent unavailable live VmRSS'in row['memory_read_error']
        commands[label]=row
    final=read('work/drc-audit-result.json')
    assert final['status']=='COMPLETE_SIGNAL_REPAIR_AND_ORIGINAL_CLASS_DRC_NOT_TIMING_OR_PHY_ACCEPTANCE'
    assert final['original1691_clock_gate_passed']is True and final['native_invariants_passed']is True
    prior=read('work/unfix-audit-result.json')
    assert prior['status']=='PASS_ORIGINAL_CLASS_SIGNAL_REPAIR_REQUIRES_COMPLETE_DRC'
    assert prior['candidate_sha256']==r['outputs']['work/repaired.odb']
    assert prior['expected_def_sha256']==r['outputs']['work/expected-original-class.def']
    assert prior['routing_delta']==final['routing_delta']
    assert prior['original1691_clock_gate_passed']is True and prior['native_invariants_passed']is True
    gates={}
    for label,obj in (('after-repair',prior),('after-final-drc',final)):
        name='work/original-gate-'+label+'/result.json';gate=read(name)
        assert obj['original_gate']==dict(result=gate,sha256=r['outputs'][name])
        assert gate['clock_or_fixed_nets']==1691 and gate['all_source_clock_and_fixed_records_preserved']is True
        gates[label]=gate
    owners=read('work/ownership.json');names=owners['selected']
    assert names==sorted(set(names))and len(names)==1691 and owners['net_count']==143820
    assert c.digest(c.canonical(names))==repair.SELECTED_SHA
    net_inventory=classification.net_inventory(raw('work/expected-original-class.def'),names)
    assert len(net_inventory)==143820
    measurement=final['final_DRT'];marker=raw('work/initial-drc-markers.json')
    assert drc.bind_serialized_markers(measurement,marker)==measurement['serialized_markers']
    report=raw('work/initial-drc.rpt')
    assert report==raw('work/initial-drc-reread.rpt')
    assert (len(report),c.digest(report))==(measurement['report_bytes'],measurement['report_sha256'])
    classified=classification.analyze(marker,report,measurement,net_inventory,names)
    reported_gate=repair.continuation_gate(final)
    assert reported_gate==final['next_stage']
    return dict(status='COMPLETE_FAILED_RUN_SAVED_REPORT_READBACK_NOT_ACCEPTANCE',
        original_run=RUN,original_source=SOURCE,original_run_conclusion='failure',
        original_resource_guard_failure_preserved=True,
        original_resource_guard_failure=commands['drc-audit'],
        saved_final_native_audit=final,saved_original_clock_gates=gates,
        saved_unfix_audit=prior,complete_original_command_records=commands,
        saved_native_reported_next_stage=reported_gate,
        postroute_bridge_eligible=False,reroute_authorized=False,
        classification=classified,selected_clock_fixed_count=1691,
        original_marker_count=762,remaining_marker_count=classified['marker_count'],
        accepted=False,final_timing_complete=False,full_phy_accepted=False,
        interpretation='Complete saved physical reports are evidence from a failed supervised run, not a waiver of its resource failure.')
