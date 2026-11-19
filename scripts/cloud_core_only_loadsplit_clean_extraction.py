#!/usr/bin/env python3
"""Fresh nominal RC of the 21-buffer route; physical and provenance gates fail closed."""
import os,json,subprocess
from pathlib import Path
import cloud_core_only_regression_antenna_extraction as previous
from cloud_core_only_postgrt import put,sha
from rebind_loadsplit_antenna_inventory import rebind_inventory,verify_moved_export
flow=previous.flow
OUT=flow.ROOT/'hw/soc/out/core-only-loadsplit-clean-extraction'
RUN=44562378599
HEAD='d800be2ea61e39adef89e58c075591d77f71773e'
ODB_HASH='12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458'

def restore_candidate():
    z,r,m=previous.verified(RUN,HEAD,'core-only-loadsplit-neighbor-route-'+str(RUN),14549769828,'f11b5b5f3affd565311424f68028f32613ecc68c35d313bf6f914e5b3d1a3f39')
    assert len(r['outputs'])==47
    assert r['status']=='LOAD_SPLIT_NEIGHBOR_ROUTE_GEOMETRY_AND_ANTENNA_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF'
    ident,preserve,g=previous.identity(r,106693,103080)
    assert ident['nets']==103117
    assert all(v['passed'] for v in g['native_decoder_qualification'].values()) and all(g['synthetic_controls'].values())
    assert g['actual_route_removal_control']['removed_route_shapes']>0 and g['actual_route_removal_control']['detected_components']>1
    for k in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins','flow__errors__count']:assert r['metrics'][k]==0
    assert r['routed_odb_sha256']==ODB_HASH and r['output_odb']=='restored-status.odb'
    assert r['outputs']['candidate-partially-routed.odb']=='3c55f2e88aff518b5483e10760b2d75042856d2b77616526bc731cb2083fd7c3'
    assert r['fixed_route_preparation']['fixed_nets']==102964 and r['fixed_route_preparation']['all_records_verified']
    for key,expected in [('fixed-type-admission','FIXED'),('restored-type-admission','ROUTED')]:
        t=r[key];assert t['checked_nets']==102964 and t['expected_encoded_type']==expected and not t['wrong_types'] and t['source_unchanged']
        assert t['controls']['metadata_only_fix_rejected'] and t['controls']['encoded_fixed_accepted']
    assert r['restored-type-admission']['source_sha256']==ODB_HASH
    report,artifacts,initial=previous.restore_candidate()
    assert report['fresh_view_binding']['odb_sha256']=='bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc'
    assert len(report['cumulative_antenna_inventory'])==1410
    bz,b,bm=previous.verified(44555127293,'bb26e933787c729110c6fa16167bfa44a393e2dc','core-only-loadsplit-prep-44555127293',14544652590,'2d0eebbd815fa2411933ddddadc8c5a8eeeed8c15793d7424f6ea74be5d65daf')
    assert b['status']=='TWENTY_ONE_LOAD_SPLIT_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
    assert b['source_admission']['odb_sha256']==report['fresh_view_binding']['odb_sha256']
    assert b['outputs']['candidate-partially-routed.odb']==r['outputs']['candidate-partially-routed.odb']
    assert r['source_artifact']['id']==bm['id'] and r['source_artifact']['digest']==bm['digest']
    bi=b['audit'];assert bi==r['source_audit'] and bi['instances']==106693 and bi['new_buffers']==21 and bi['moved_diode_count']==44
    for k in ['all_original_geometry_preserved','original_functional_connections_recovered_after_identity_buffer_collapse','wrong_connection_control_rejected','power_geometry_ports_preserved','diode_connections_recovered_after_buffer_collapse']:assert bi[k]
    bp=b['power_contact'];assert bp['checked_power_terminals']==42 and not bp['failures'] and bp['sources_unchanged']
    assert all(bp['synthetic_controls'].values()) and bp['native_rail_removal_control']['loss_of_contact_detected']
    pr=b['preserved_routes'];assert pr['unchanged_def_net_records']==103086 and pr['checked_clock_nets']==2113 and pr['clock_routes_preserved'] and pr['ndr_assignments_preserved']
    moved_audit=json.loads(bz.read('diode-reconnection-audit.json'));assert moved_audit==r['source_diode_reconnection']
    cumulative,moved=rebind_inventory(report['cumulative_antenna_inventory'],moved_audit)
    assert len(cumulative)==1410 and len(moved)==44
    report['cumulative_antenna_inventory']=cumulative
    odb=OUT/'loadsplit-route.odb';put(odb,z.read('restored-status.odb'),ODB_HASH)
    state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdchash=sha(sdc)
    assert sdchash=='f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1'
    export=OUT/'routed-export.tcl'
    export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_LOADSPLIT_EXPORT_COMPLETE\n')
    with (OUT/'routed-export.log').open('w') as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
    assert 'NSSOC_LOADSPLIT_EXPORT_COMPLETE' in (OUT/'routed-export.log').read_text()
    netlist=(OUT/'routed.v').read_text();check=flow.check_added_antennas(netlist,cumulative)
    assert check['new_diodes_exported']==1410 and not check['missing_diodes'] and not check['duplicate_diodes'] and not check['signal_connection_mismatches']
    moved_check=verify_moved_export(netlist,moved)
    assert sha(sdc)==sdchash and sha(odb)==ODB_HASH
    state.update(odb=str(odb),nl=str(OUT/'routed.v'),metrics={});state['def']=str(OUT/'routed.def')
    for key in ['spef','sdf','lib','pnl']:
        if key in state:state[key]=None
    initial.write_text(json.dumps(state,indent=2)+'\n')
    report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdchash,export_script_sha256=sha(export))
    report['antenna_netlist_export']=check
    evidence=dict(run=RUN,head=HEAD,artifact=m,metrics=r['metrics'],identity=ident,preservation=preserve,geometry=g,buffer_artifact=bm,buffer_audit=bi,buffer_power=bp,diode_moves=moved_audit,moved_diode_export=moved_check,wrapper_sha256=sha(__file__),rebind_helper_sha256=sha(Path(__file__).with_name('rebind_loadsplit_antenna_inventory.py')),production_admissible=False)
    (OUT/'loadsplit-route-source.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (OUT/'source-antenna.rpt').write_bytes(z.read('antenna.rpt'))
    artifacts.extend([bm,m])
    return report,artifacts,initial

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    previous.OUT=OUT;previous.previous.OUT=OUT;previous.previous.clean.OUT=OUT;flow.OUT=OUT
    flow.EXPECTED_INSTANCES=106693
    flow.restore_route=restore_candidate;flow.RUN=RUN;flow.HEAD=HEAD
    flow.main()
