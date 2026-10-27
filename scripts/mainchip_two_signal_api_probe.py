#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate disabled read-only identity probe contract; never authorizes repair."""
import json
import mainchip_original_clock_restoration as c
import mainchip_two_signal_repair as original
ROOT=c.ROOT
METHOD=ROOT/'scripts/mainchip-two-signal-api-probe-methods.json'
LABELS=('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version','api-identity-census')

def methods():
    m=json.loads(c.regular(METHOD).read_bytes())
    assert m['purpose']=='READ_ONLY_API_AND_IDENTITY_DIAGNOSTIC_NOT_REPAIR'
    for p,h in m['protected'].items():assert c.file_sha(ROOT/p)==h,('source',p)
    assert m['input']==dict(member=original.INPUT,sha256=original.INPUT_SHA,bytes=original.INPUT_BYTES,
        original_run=40344497930,original_failure_preserved=True)
    for key in ('source_controls_authorized','cloud_restore_authorized','native_execution_authorized','native_api_probe_authorized'):
        assert type(m[key])is bool
    assert m['cloud_restore_authorized']==m['native_execution_authorized']==m['native_api_probe_authorized']
    if m['native_api_probe_authorized']:
        assert m['source_controls_authorized']is True and m['source_unit_complete']is True
    for key in ('native_routing_authorized','geometry_mutation_authorized','simulation_authorized',
                'rc_sta_execution_authorized','timing_accepted','full_phy_accepted'):
        assert m[key]is False
    assert m['limits']==dict(phase_seconds=1200,max_group_rss_kib=10485760,min_available_kib=2097152,
        output_limit_per_stream_bytes=16777216)
    return m

def command_seconds(label):
    assert type(label)is str and label in LABELS,('Unknown API probe command label',label)
    return 1200

def validate_report(report):
    assert report['status']=='COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_OWNERSHIP_QUALIFICATION'
    assert report['all_net_count']==143820 and report['all_instance_count']==153130
    assert report['complete_census_counts']['net']==143820 and report['complete_census_counts']['instance']==153130
    assert report['complete_raw_opcode_data_pairs']>0 and report['raw_operand_native_lookups']['layers']
    assert set(report['raw_operand_native_lookups'])=={'layers','rules','vias'}
    assert report['every_block_terminal_reconciled_with_connected_net_census']is True
    assert report['every_raw_terminal_lookup_reconciled_with_both_censuses']is True
    assert type(report['raw_terminal_named_joins'])is list
    assert len(report['raw_terminal_named_joins'])==report['unique_raw_terminal_OID_joins']
    assert all(type(r['raw_OID'])is int and r['raw_OID']>0 and r['kind']in ('iterm','bterm')
        and type(r['owner'])is str and r['owner'] for r in report['raw_terminal_named_joins'])
    assert report['input']==dict(member=original.INPUT,sha256=original.INPUT_SHA,bytes=original.INPUT_BYTES)
    assert report['terminal_checks']==[dict(label=label,status='PASS')for label in
        ('destroy-read-only-database','unchanged-source-file')]
    assert report['original_getId_failure_preserved']is True
    for key in ('layer_numbers_or_routing_levels_used_as_OIDs','table_OIDs_invented',
                'source_geometry_mutated','native_routing_started','ownership_eligible','accepted','full_phy_accepted'):
        assert report[key]is False
    return dict(api_diagnostic_complete=True,repair_eligible=False,ownership_qualified=False,
        original_failures_preserved=True,requires_separate_source_proposal_and_controls=True)
