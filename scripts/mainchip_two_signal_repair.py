#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact failed-input and two-signal-only boundary. Native execution is separate."""
import json
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as old
import mainchip_two_signal_geometry as geometry
ROOT=c.ROOT
METHOD=ROOT/'scripts/mainchip-two-signal-repair-methods.json'
INPUT='work/drc-observed.odb'
INPUT_SHA='444f75328e4065ae1fd1fdf1b872980931fcbae8ec8a62182a833e48230bf9b1'
INPUT_BYTES=213740873
DEF_SHA='50637ee844f1166c6e2faf7dd6d6e365147096ac974fa878b6a00aeb0448be4a'
READBACK='docs/evidence/mainchip-signal-repair-saved-readback-native-terminal-20261026.diagnostics/full-saved-report.json'
READBACK_SHA='ec42c65f24662cfbe928f147f9ae7b5040767d9ca4ea4fb8bf370ed122f4b1a4'
MARKER_SHA='7cd9e8de6c42fdd7da36ffac188298100fe207099c3db8687184feee47284934'
TR_SHA='47391c36cc33bc08cdf11552d52da427de1e1c287ca99527aa7074d5d68a3d26'
TARGETS=geometry.TARGETS

def methods():
    m=json.loads(c.regular(METHOD).read_bytes())
    for path,h in m['protected'].items():assert c.file_sha(ROOT/path)==h,('source',path)
    assert m['input']==dict(run=40344497930,source='2a81095f744193451800ef178c9a7ae7314dd2dc',
        member=INPUT,sha256=INPUT_SHA,bytes=INPUT_BYTES,admitted_as='failed-input-for-new-repair-only')
    assert m['targets']==list(TARGETS)
    assert m['limits']==dict(phase_seconds=1200,routing_seconds=14400,threads=2,
        max_group_rss_kib=10485760,min_available_kib=2097152)
    for key in ('simulation_authorized','rc_sta_execution_authorized','timing_accepted','full_phy_accepted'):
        assert m[key]is False
    return m

def readback():
    raw=c.regular(ROOT/READBACK).read_bytes();assert c.digest(raw)==READBACK_SHA
    r=json.loads(raw)
    assert r['original_run']==40344497930 and r['original_source']=='2a81095f744193451800ef178c9a7ae7314dd2dc'
    assert r['original_run_conclusion']=='failure'and r['original_resource_guard_failure_preserved']is True
    assert r['remaining_marker_count']==3 and r['selected_clock_fixed_count']==1691
    assert r['classification']['exclusive_group_counts']=={'clock-signal':3}
    assert r['postroute_bridge_eligible']is False and r['accepted']is False
    f=r['saved_final_native_audit']
    assert f['original1691_clock_gate_passed']is True and f['native_invariants_passed']is True
    assert f['final_DRT']['marker_count']==3
    assert f['final_DRT']['report_sha256']==TR_SHA
    return r

def source_input(path,report,proof):
    assert report['source_head']=='2a81095f744193451800ef178c9a7ae7314dd2dc'
    assert report['status']=='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR'
    assert report['outputs'][INPUT]==INPUT_SHA and c.file_sha(path)==INPUT_SHA
    assert c.regular(path).stat().st_size==INPUT_BYTES
    inv=proof['inventory']
    assert len(inv['all_original_files'])==94
    assert inv['complete_original_inventory_verified_before_analysis']is True
    assert proof['envelope']['original_conclusion']=='failure'
    assert proof['envelope']['resource_guard_failure_preserved']is True
    r=readback()
    gate=r['saved_original_clock_gates']['after-final-drc']
    assert INPUT_SHA in gate['source_hashes'].values()
    assert gate['clock_or_fixed_nets']==1691 and gate['all_source_clock_and_fixed_records_preserved']is True
    return dict(member=INPUT,sha256=INPUT_SHA,bytes=INPUT_BYTES,
        original_failure_preserved=True,prior_markers=3,admitted_as='failed-input-for-new-repair-only')

def ownership(raw,names,snapshot):
    assert c.digest(raw)==DEF_SHA
    p=c.parse_def(raw)
    assert len(p['records'])==143820
    assert names==sorted(set(names))and len(names)==1691
    assert c.digest(c.canonical(names))==old.SELECTED_SHA
    assert set(snapshot['identity'])==set(snapshot['encoded'])==set(p['records'])
    for name in TARGETS:
        assert name not in names
        assert snapshot['identity'][name]['sigtype']=='SIGNAL'
        e=snapshot['encoded'][name]
        assert e['wire_present']and e['metadata']=='ROUTED'and e['paths']and set(e['paths'])=={'ROUTED'}
        old.wire_head(p['records'][name])
    frozen=sorted(set(p['records'])-set(TARGETS))
    fixed,classes=c.fixed_overlay(raw,frozen)
    c.validate_encoded({k:snapshot['encoded'][k]for k in frozen},classes)
    assert all(kind in (None,'ROUTED','FIXED')for kind in classes.values()),'Unsupported protected original class'
    return dict(selected=names,mutable=list(TARGETS),frozen=frozen,net_count=143820),fixed,classes

def require_actionable(result):
    assert result['read_only']is True
    assert result['source_net_count']==3 and result['all_net_count']==143820 and result['instance_count']==153130
    assert set(result['full_source_material'])=={geometry.CLOCK,*TARGETS}
    assert result['markers']==geometry.marker_boxes(result['dbu_per_micron'])
    repeated=geometry.ownership_decision(result['markers'],result['records'])
    for key in ('witnesses','blockers','eligible_for_one_two_net_attempt'):
        assert repeated[key]==result[key],('Ownership decision changed',key)
    assert result['eligible_for_one_two_net_attempt']is True,'Native pin/obstruction/unknown conflict forbids routing'
    assert {w['marker']for w in result['witnesses']}=={0,1,2}
    assert all(w['target_movable']and not w['clock_movement_permitted']for w in result['witnesses'])
    return True

def router_census_observation(rows,owners):
    """Classify every observed row without accepting it or discarding refusals."""
    classes={key:[]for key in ('target','ordinary_fixed','ordinary_unwired','special')}
    refusals=[]
    def refuse(name,reason):refusals.append(dict(name=name,reason=reason))
    expected=set(owners['frozen'])|set(TARGETS)
    if len(rows)!=143820 or set(rows)!=expected:
        refuse(None,'complete_net_membership')
    for name,row in rows.items():
        if set(row)!={'wire_present','metadata','paths','guides','terminals','special','sigtype'}:
            refuse(name,'row_schema');continue
        if (type(row['wire_present'])is not bool or type(row['special'])is not bool
            or type(row['guides'])is not int or row['guides']<0
            or type(row['terminals'])is not int or row['terminals']<0
            or type(row['metadata'])is not str or not row['metadata']
            or type(row['sigtype'])is not str or not row['sigtype']
            or type(row['paths'])is not list or any(type(p)is not str for p in row['paths'])):
            refuse(name,'row_types');continue
        if name in TARGETS:
            classes['target'].append(name)
            if not (row['wire_present']and row['metadata']=='ROUTED'and row['paths']
                and set(row['paths'])=={'ROUTED'}and row['guides']>0
                and not row['special']and row['sigtype']=='SIGNAL'):
                refuse(name,'target_must_be_ordinary_routed_guided_signal')
            continue
        # Actual dbNet.isSpecial alone selects the pinned DRT addSNet population.
        # It does not imply empty stored guides or absent special-wire geometry.
        if row['special']:
            classes['special'].append(name)
            if row['wire_present']:
                if not (row['metadata']=='FIXED'and row['paths']and set(row['paths'])=={'FIXED'}):
                    refuse(name,'special_ordinary_wire_must_remain_FIXED')
            elif row['paths']!=[]:
                refuse(name,'special_absent_wire_has_paths')
            continue
        if row['sigtype']in ('POWER','GROUND'):
            refuse(name,'ordinary_supply_is_DRT_305_not_a_skip')
        if row['wire_present']:
            classes['ordinary_fixed'].append(name)
            if not (row['metadata']=='FIXED'and row['paths']and set(row['paths'])=={'FIXED'}):
                refuse(name,'ordinary_nontarget_wire_must_be_FIXED')
        else:
            classes['ordinary_unwired'].append(name)
            # This conservative original ordinary-net refusal is unchanged.
            if not (row['paths']==[]and row['guides']==0 and row['terminals']<=1):
                refuse(name,'ordinary_unwired_must_be_unguided_singleton')
    if sorted(classes['target'])!=sorted(TARGETS):
        refuse(None,'exact_two_targets_required')
    return dict(status='OBSERVED_ROUTER_CENSUS_NOT_ACCEPTANCE',accepted=False,
        net_count=len(rows),expected_net_count=143820,
        missing_names=sorted(expected-set(rows)),extra_names=sorted(set(rows)-expected),
        class_counts={k:len(v)for k,v in classes.items()},
        special_names=sorted(classes['special']),ordinary_unwired_names=sorted(classes['ordinary_unwired']),
        target_names=sorted(classes['target']),refusals=refusals,
        refusal_count=len(refusals),rows_sha256=c.digest(c.canonical(rows)),
        refusals_sha256=c.digest(c.canonical(refusals)),
        ordinary_unwired_rule='paths=[] and guides=0 and terminals<=1',
        special_basis='Actual dbNet.isSpecial; pinned dcf36133 Parser.addNet addSNet versus addNet')

def router_census(rows,owners):
    """Only the two targets may route; typed special material remains protected."""
    report=router_census_observation(rows,owners)
    assert not report['refusals'],('Router census refused',report['refusals'][0],
        report['refusal_count'],report['refusals_sha256'])
    return dict(two_routed_nonfixed_guided_names=report['target_names'],
        unwired_nonparticipants=report['ordinary_unwired_names'],
        actual_special_nonparticipants=report['special_names'],
        class_counts=report['class_counts'],observed_rows_sha256=report['rows_sha256'],
        all_other_wired_paths_encoded_FIXED=True,no_unguided_fallback_admitted=True)

def restore_expectation(raw,classes):
    assert set(classes).isdisjoint(TARGETS)
    return c.restore_classes(raw,classes)

def routing_delta(before,after,owners):
    assert owners['mutable']==list(TARGETS)
    result=old.routing_delta(before,after,owners)
    assert set(result['changed_signal_names'])<=set(TARGETS)
    result['only_two_signals_permitted']=list(TARGETS)
    return result

def require_complete(result):
    assert result['original1691_clock_gate_passed']is True and result['native_invariants_passed']is True
    assert set(result['routing_delta']['changed_signal_names'])<=set(TARGETS)
    return old.continuation_gate(result)
