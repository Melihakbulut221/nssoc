#!/usr/bin/env python3
"""Admit a narrowly expanded route set using an authenticated rejected artifact."""
import json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,ROOT

def verify_rejection(out):
    run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44573258297']))
    assert run['head_sha']=='26b92963b1fa7080ae6baa6c5a5570ea288b3713' and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']=='failure'
    z,m=archive(run,'core-only-signal-fanout-route-44573258297')
    assert m['id']==14574906878 and m['digest']=='sha256:49146cfdc855dcecc16424a8875ff02ba59fe5874e58a990f450e8cc5e0074f1'
    r=json.loads(z.read('result.json'))
    assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
    assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
    for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    assert len(r['outputs'])==45
    assert r['routed_odb_sha256']=='aa14215aceb062d14e6a39eb576e369a37ff31f7157762caaea47e78f7f603e7'
    evidence=json.loads((ROOT/'docs/evidence/core-only-signal-fanout-route-rejection-20261120.json').read_text())
    assert r['outputs']==evidence['verified_outputs']
    g=json.loads(z.read('geometry/physical-route-audit.json'))
    assert g['source_odb_sha256']==r['routed_odb_sha256']and g['source_unchanged']
    counts={p['layer']+':'+':'.join(p['nets']):p['contacts']for p in evidence['contact_pairs']}
    assert len(counts)==158 and sum(counts.values())==680
    assert g['inter_net_contact_pairs']==680 and g['contact_counts']==counts
    assert not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']
    assert all(v['passed']for v in g['native_decoder_qualification'].values())and all(g['synthetic_controls'].values())
    assert g['actual_route_removal_control']['detected_components']>1
    assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==13 and r['metrics']['antenna__violating__pins']==17
    ident=r['detailed_identity'];assert ident['instances']==107106 and ident['nets']==103530 and ident['sources_unchanged']
    for k in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[k]
    p=r['detailed_preservation'];assert p['checked_unchanged_nets']==102910 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets']and not p['changed_clock_nets']
    (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
    (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
    return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=45,contact_counts=counts,antenna_nets=13,antenna_pins=17,production_admissible=False)
