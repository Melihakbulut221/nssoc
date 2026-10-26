#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact routing-only acceptance boundary. No native execution or archive access."""
import json,re
from pathlib import Path
import mainchip_original_clock_restoration as c
ROOT=c.ROOT
METHOD=ROOT/'scripts/mainchip-fixed-clock-signal-repair-methods.json'
SELECTED_SHA='3cefc8413f74daf211af146b0b352eb6907ee8d6b7ea611e4d4a299819f02e91'
RESTORED_SHA='2d75a1e620c74cbe24a762683db17b1708aaac003a0b3e4b54099c769748c7da'
FIXED_SHA='8ed9d4a37eee2c2c73aa9b09becee0940fed71257c1186dd6a1919464a58fb28'
RESTORED_DEF='55fbc30c508b42a27301054206a8820b020bbbb3a525beeef0aed73692870ece'
FIXED_DEF='cb418272215f738a169f6a7ed5971503fa021fa09e96a090ed624a95217b5888'
GLOBAL_PROOF='docs/evidence/mainchip-route12-global-pass-20261023.json'
GLOBAL_PROOF_SHA='b1f5ba79b842b4a4dc2667b6a5eea58e75df897376f373cec20ab6d0390b2729'
GLOBAL_PREFIX='run/1-nssoc-repairfreshglobal/'
GLOBAL_INPUTS={
 GLOBAL_PREFIX+'fresh_fanout_native.tcl':'dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e',
 GLOBAL_PREFIX+'fresh-fanout.guide':'54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde',
 GLOBAL_PREFIX+'_env.tcl':'255d39b6b296466fae51428718fd9fdd5019594fdf6d1c2cbdd116ac52e8c8f0',
 GLOBAL_PREFIX+'config.json':'c6dfea371e243881a4ae20499da8726980c83224ea31e1b4e5fe7bb44cbccaaa',
 'trial-config.json':'b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f'}
CLOCK_INPUTS={
 'work/restored.odb':RESTORED_SHA,'work/fixed.odb':FIXED_SHA,
 'source/geometry/routed/work/before-guide-read.odb':c.DONOR_SHA,
 'work/restored.def':RESTORED_DEF,'work/fixed.def':FIXED_DEF,
 'work/audit-restored-result.json':'9d3af1345ac677e1dfeceaaaad3d192cf382ef506b0f28716595d3aaf67a548f',
 'work/audit-fixed-result.json':'0845a1e7b58e4c160e5a0b5070fd25dd8defbf6cdff18c0f62ce325b7529b679',
 'work/audit-unfixed-result.json':'3df0778e224fc3b27d0f3165d618ac8e1d8b329e7a0121ddc02b44d9a35c5dd5'}
SETTINGS={'DESIGN_NAME':'soc_top','DRT_THREADS':'2','DRT_OPT_ITERS':'64',
 'DRT_SAVE_SNAPSHOTS':'0','DRT_SAVE_DRC_REPORT_ITERS':'5'}
LAYERS='set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2'
SETUP='set_thread_count $::env(DRT_THREADS)\n\nset drc_report_iter_step_arg ""\nif { $::env(DRT_SAVE_SNAPSHOTS) } {\n    set_debug_level DRT snapshot 1\n    set drc_report_iter_step_arg "-drc_report_iter_step 1"\n    detailed_route_debug -snapshot_dir "$::env(STEP_DIR)"\n}\nif { [info exists ::env(DRT_SAVE_DRC_REPORT_ITERS)] } {\n    set drc_report_iter_step_arg "-drc_report_iter_step $::env(DRT_SAVE_DRC_REPORT_ITERS)"\n}\n\n'
ARGUMENTS='set drt_args [list]\nlappend drt_args -droute_end_iter $::env(DRT_OPT_ITERS)\nlappend drt_args -or_seed 42\nlappend drt_args -verbose 1\nlappend drt_args {*}$drc_report_iter_step_arg\n'

CLASSIFICATION='docs/evidence/mainchip-clock-marker-classification-readback-pass-20261025.summary.json'
CLASSIFICATION_SHA='11c46c28fdcab265b8d3c934e212e8d42a859f6c56ccd966e55d70417cf1ca95'

def classification_fields(r):
    assert (r['run_id'],r['run_attempt'],r['source_head'])==(40227070148,1,'e42177896ed7c5ca706c48c2b0bf3a19f2a51308')
    assert r['status']=='COMPLETE_SAVED_MARKER_CLASSIFICATION_NOT_ROUTE_ACCEPTANCE'
    x=r['classification']
    assert x['marker_count']==762 and x['exclusive_group_counts']=={'clock-signal':762}
    assert x['selected_clock_fixed_count']==1691 and x['selected_names_sha256']==SELECTED_SHA
    assert x['net_inventory_count']==143820 and x['known_clock_clock_marker_ordinals']==[]and x['unresolved_marker_ordinals']==[]
    assert x['exact_complete_JSON_TR_reconstruction']is True and x['routing_feasibility_proven']is False
    assert x['marker_json_sha256']=='9ac2e9865ce6f0efe37a729b3a1855e65b53efdd2821657271e50851d4090f7b'
    assert x['TR_sha256']=='dd7eef05f595947260df575ec9cb7ef474d880442c28c4d1a5bb5f6577f5500a'
    return x

def classification_admission():
    raw=c.regular(ROOT/CLASSIFICATION).read_bytes()
    assert c.digest(raw)==CLASSIFICATION_SHA
    return classification_fields(json.loads(raw))

def methods():
    m=json.loads(c.regular(METHOD).read_bytes())
    for path,h in m['protected'].items():assert c.file_sha(ROOT/path)==h,('source',path)
    for key in ('rc_sta_execution_authorized','simulation_authorized','timing_accepted','full_phy_accepted'):
        assert m[key]is False
    assert m['limits']==dict(phase_seconds=1200,threads=2,max_group_rss_kib=10485760,min_available_kib=2097152)
    return m

def skeleton(parsed):
    chunks=[];cursor=0
    for a,b in parsed['spans'].values():chunks.append(parsed['raw'][cursor:a]);cursor=b
    chunks.append(parsed['raw'][cursor:])
    return b''.join(chunks)

def wire_head(record):
    hits=list(c.ROUTE.finditer(record))
    assert len(hits)==1 and hits[0].group(2)==b'ROUTED','Only an existing ROUTED signal clause can change'
    start=hits[0].start()
    assert len(re.findall(rb'(?m)^[ \t]*\+ [A-Z]+',record[start:]))==1,'Trailing nonwire clause not admitted'
    return record[:start]

def ownership(raw,names,identity,encoded):
    p=c.parse_def(raw)
    assert set(identity)==set(encoded)==set(p['records'])
    selected=set(names);assert selected<=set(p['records'])
    mutable=[]
    for name,record in p['records'].items():
        row=identity[name];e=encoded[name]
        assert row['name']==name
        if name not in selected and row['sigtype']=='SIGNAL'and e['wire_present']:
            assert e['metadata']=='ROUTED'and e['paths']and set(e['paths'])=={'ROUTED'}
            wire_head(record);mutable.append(name)
    assert mutable,'No admitted routed signal nets'
    return dict(selected=sorted(selected),mutable=sorted(mutable),net_count=len(p['records']))

def routing_delta(before,after,owners):
    a,b=c.parse_def(before),c.parse_def(after)
    assert list(a['records'])==list(b['records']),'NETS census/order changed'
    assert skeleton(a)==skeleton(b),'Non-NETS or inter-record bytes changed'
    mutable=set(owners['mutable']);selected=set(owners['selected'])
    assert not mutable&selected and mutable|selected<=set(a['records'])
    changed=[]
    for name,record in a['records'].items():
        got=b['records'][name]
        if name in mutable:
            assert wire_head(record)==wire_head(got),('Signal identity/attribute prefix changed',name)
            assert c.prefix(record)==c.prefix(got),('Signal connection prefix changed',name)
            if record!=got:changed.append(name)
        else:assert record==got,('Protected non-SIGNAL/selected/unwired record changed',name)
    return dict(changed_signal_count=len(changed),changed_signal_names=changed,
        changed_signal_names_sha256=c.digest(c.canonical(changed)),other_records_byte_exact=True,
        non_NETS_bytes_exact=True,accepted=False)

def native_invariants(before,after,owners):
    assert before['geometry']==after['geometry'],'Native connections/placement/pins/metadata changed'
    assert set(before['identity'])==set(after['identity'])
    assert before['identity']==after['identity'],'Native net terminal identity changed'
    for name,e in before['encoded'].items():
        got=after['encoded'][name]
        if name in owners['mutable']:
            assert got['wire_present']and got['metadata']=='ROUTED'and got['paths']and set(got['paths'])=={'ROUTED'}
        else:assert got==e,('Protected encoded route changed',name)
    return True

def exact_setup(original):
    assert c.digest(original)==GLOBAL_INPUTS[GLOBAL_PREFIX+'fresh_fanout_native.tcl']
    text=original.decode()
    a=text.index('set_thread_count $::env(DRT_THREADS)')
    b=text.index('# The input has only stale data wires removed.',a)
    x=text.index('set drt_args [list]');y=text.index('drt_run $i {*}$drt_args',x)
    assert text[a:b]==SETUP and text[x:y]==ARGUMENTS and text.count(LAYERS)==1
    return SETUP,ARGUMENTS

def timing_contract(step,full):
    assert step['CLOCK_PORT']==full['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
    assert float(step['CLOCK_PERIOD'])==float(full['CLOCK_PERIOD'])==20
    assert float(step['TIME_DERATING_CONSTRAINT'])==float(full['TIME_DERATING_CONSTRAINT'])==5
    assert full['SETUP_VIOLATION_CORNERS']==full['HOLD_VIOLATION_CORNERS']==['*']
    assert int(step['DRT_OPT_ITERS'])==64
    return dict(clock_periods_ns=[20,4,8,8],derating_percent=5,new_RC_STA_required=True,accepted=False)

def route_tcl(source,environment,out,original,quote):
    setup,arguments=exact_setup(original)
    guards=''.join('if {![info exists ::env('+k+')] || $::env('+k+') ne "'+v+'"} {error "Original setting '+k+' differs"}\n'for k,v in SETTINGS.items())
    return ('source '+quote(environment)+'\n'+guards+'set ::env(STEP_DIR) '+quote(out)+'\n'+
        'read_db '+quote(source)+'\n'+LAYERS+'\n'+setup+'\n'+arguments+'\n'+
        'puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\n'+
        'detailed_route {*}$drt_args -output_drc '+quote(out/'fixed-routing.drc')+'\n'+
        'write_def '+quote(out/'routed-fixed.def')+'\nwrite_db '+quote(out/'routed-fixed.odb')+'\n'+
        'puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\nexit\n')

def route_log(raw):
    text=raw.decode('utf-8','strict')
    assert text.count('NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN')==1
    assert text.count('NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED')==1
    assert text.index('NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN')<text.index('NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED')
    # initGuide may fall back to GR only with no valid guides; native guide proof precedes launch.
    return dict(bytes=len(raw),sha256=c.digest(raw),single_returned_attempt=True,
                router_report_is_not_final_original_class_DRC=True)

def continuation_gate(result):
    assert result['original1691_clock_gate_passed']is True
    assert result['routing_delta']['other_records_byte_exact']is True
    assert result['routing_delta']['non_NETS_bytes_exact']is True
    assert result['native_invariants_passed']is True
    m=result['final_DRT']
    assert type(m['marker_count'])is int and m['marker_count']>=0
    assert m['all_categories_below_native_cap']is True
    assert m['serialized_markers']['complete_native_category_census_equal']is True
    assert m['serialized_markers']['marker_count']==m['marker_count']
    assert m['zero_reported_DRT_markers']is (m['marker_count']==0)
    return dict(eligible_for_separately_reviewed_RC_STA=m['marker_count']==0,
        DRT_markers=m['marker_count'],timing_accepted=False,full_phy_accepted=False)
