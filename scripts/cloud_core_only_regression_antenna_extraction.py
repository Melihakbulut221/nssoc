#!/usr/bin/env python3
"""Fresh nominal RC for the six-buffer candidate; requires pinned clean-route evidence."""
import os,json,hashlib,subprocess,re
from pathlib import Path
import cloud_core_only_load_resize_antenna_extraction as previous
from cloud_core_only_postgrt import api,archive,put,sha
from rebind_regression_antenna_inventory import rebind_inventory,verify_moved_export
flow=previous.flow
OUT=flow.ROOT/'hw/soc/out/core-only-regression-antenna-extraction'
RUN=44545302944
HEAD='99aea3abd3ac6622674556f6854995436d9c1d6b'

def verified(rid,head,name,aid,digest,conclusion='success'):
    rr=api('actions/runs/'+str(rid))
    assert rr['head_sha']==head and rr['run_attempt']==1 and rr['status']=='completed' and rr['conclusion']==conclusion
    z,m=archive(rr,name)
    assert m['id']==aid and m['digest']=='sha256:'+digest
    r=json.loads(z.read('result.json'))
    assert r['source_head']==head and r['accepted'] is False
    assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
    for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    if conclusion=='success':assert r['sources_unchanged']
    return z,r,m

def identity(r,count,preserved):
    i=r['detailed_identity'];assert i['instances']==count and i['sources_unchanged']
    for k in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert i[k]
    p=r['detailed_preservation'];assert p['checked_unchanged_nets']==preserved and p['checked_clock_nets']==2113
    assert not p['changed_unselected_nets'] and not p['changed_clock_nets']
    g=r['visible_geometry'];assert g['source_unchanged'] and g['actual_route_removal_control']
    assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry'] and g['inter_net_contact_pairs']==0
    assert g['source_odb_sha256']==r['routed_odb_sha256']
    return i,p,g

def restore_candidate():
    # Values are supplied only after independent inspection of the completed run.
    aid=int(os.environ['NSSOC_REGRESSION_ROUTE_ARTIFACT_ID'])
    digest=os.environ['NSSOC_REGRESSION_ROUTE_ARTIFACT_SHA256']
    odbhash=os.environ['NSSOC_REGRESSION_ROUTE_ODB_SHA256']
    assert re.fullmatch('[0-9a-f]{64}',digest) and re.fullmatch('[0-9a-f]{64}',odbhash)
    z,r,m=verified(RUN,HEAD,'core-only-regression-antenna-route-'+str(RUN),aid,digest)
    assert r['status']=='REGRESSION_ANTENNA_ROUTE_GEOMETRY_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF'
    ident,preserve,g=identity(r,106672,103093)
    for k in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert r['metrics'][k]==0
    assert r['routed_odb_sha256']==odbhash and r['output_odb']=='restored-status.odb'
    counts=[]
    for key,expected in [('fixed-type-admission','FIXED'),('restored-type-admission','ROUTED')]:
        t=r[key];assert t['checked_nets']==102977 and t['expected_encoded_type']==expected and not t['wrong_types'] and t['source_unchanged']
        assert t['controls']['metadata_only_fix_rejected'] and t['controls']['encoded_fixed_accepted'];counts.append(t['checked_nets'])
    assert counts[0]==counts[1]==r['fixed_route_preparation']['fixed_nets'] and r['fixed_route_preparation']['all_records_verified']
    report,artifacts,initial=previous.restore_candidate()
    assert report['fresh_view_binding']['odb_sha256']=='171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb'
    assert len(report['cumulative_antenna_inventory'])==1408
    bz,b,bm=verified(44532861957,'481824f68e5ada49d73c47c15b93aa2f77b48615','core-only-regression-load-isolation-prep-44532861957',14533803559,'19ba066d94d191b0ae85c306da9a3cce7f1a76cc692c0741e9c5757de37b40f4')
    assert b['status']=='SIX_REGRESSION_LOAD_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
    assert b['source_admission']['odb_sha256']==report['fresh_view_binding']['odb_sha256']
    assert b['outputs']['candidate-partially-routed.odb']=='941525579d58b9da088a84b47f3bf4ed35ce33e6b24bc9ee6c6aabeca91d9b2e'
    bi=b['audit'];assert bi['instances']==106670 and bi['new_buffers']==6 and bi['moved_diode_count']==10
    for k in ['all_original_geometry_preserved','original_functional_connections_recovered_after_identity_buffer_collapse','wrong_connection_control_rejected','power_geometry_ports_preserved','diode_connections_recovered_after_buffer_collapse']:assert bi[k]
    bp=b['power_contact'];assert bp['checked_power_terminals']==12 and not bp['failures'] and bp['sources_unchanged']
    assert all(bp['synthetic_controls'].values()) and bp['native_rail_removal_control']['loss_of_contact_detected']
    moved_audit=json.loads(bz.read('diode-reconnection-audit.json'))
    cumulative,moved=rebind_inventory(report['cumulative_antenna_inventory'],moved_audit)
    nz,n,nm=verified(44538905014,'07d0ef3dd129d244b41d4cde36aeff19b9c919ff','core-only-regression-load-neighbor-route-44538905014',14539530451,'24af52387042dd16ef340e6df0c1bbca15d1710e87ee7ff65a60fec4b2eddaca','failure')
    identity(n,106670,103080)
    assert n['source_artifact']['id']==bm['id'] and n['source_artifact']['digest']==bm['digest']
    assert n['source_audit']==bi and n['source_diode_reconnection']==moved_audit
    assert n['metrics']['route__drc_errors']==0 and n['metrics']['antenna__violating__nets']==1 and n['metrics']['antenna__violating__pins']==1
    assert n['routed_odb_sha256']=='7f0a7df920df5716d0f31ca93b6f141c0d1909a403f6ded16c38cf5eb93c8764'
    az,a,am=verified(44543564994,'d72f86c0b21a4fa58e8ba0c78ea909bccd49b732','core-only-regression-antenna-prep-44543564994',14539671194,'0f19828dcb524691653a206c474ec42b9ef54294c0a18f969dac7f15f76955d1')
    assert a['outputs']['source.odb']==n['routed_odb_sha256']
    assert a['candidate_odb_sha256']==a['outputs']['diodes-inserted.odb']=='942ddc27bced208cc806144b74ac4bc90a084bf25cc2c47366c29c4004b087e6'
    ai=a['insertion_audit'];assert ai==r['source_audit'] and ai['original_instances']==106670 and ai['new_diodes']==2 and ai['total_instances']==106672
    assert r['source_artifact']['id']==am['id'] and r['source_artifact']['digest']==am['digest']
    for k in ['original_geometry_status_and_connections_preserved','power_geometry_ports_and_die_preserved','all_new_terminals_connected','sources_unchanged']:assert ai[k]
    assert set(ai['new_cells'])=={'ANTENNA_2577','ANTENNA_2578'}
    for cell in ai['new_cells'].values():assert cell['master']=='sg13g2_antennanp' and cell['signal_terms']==[dict(pin='A',type='SIGNAL',net='nssoc_regiso_0_net')]
    ap=a['added_power_contact'];assert ap==r['added_power_contact'] and ap['checked_power_terminals']==4 and not ap['failures'] and ap['sources_unchanged']
    assert all(ap['synthetic_controls'].values()) and ap['native_rail_removal_control']['loss_of_contact_detected']
    assert not set(cumulative)&set(ai['new_cells']);cumulative.update(ai['new_cells']);assert len(cumulative)==1410
    report['cumulative_antenna_inventory']=cumulative
    report['added_diode_power_contact'].update(checked_terminals=2820,regression_repair_terminals=4,regression_repair_artifact=am)
    odb=OUT/'regression-route.odb';put(odb,z.read('restored-status.odb'),odbhash)
    state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdchash=sha(sdc)
    assert sdchash=='f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1'
    export=OUT/'routed-export.tcl'
    export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_REGRESSION_EXPORT_COMPLETE\n')
    with (OUT/'routed-export.log').open('w') as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
    assert 'NSSOC_REGRESSION_EXPORT_COMPLETE' in (OUT/'routed-export.log').read_text()
    netlist=(OUT/'routed.v').read_text();check=flow.check_added_antennas(netlist,cumulative)
    assert check['new_diodes_exported']==1410 and not check['missing_diodes'] and not check['duplicate_diodes'] and not check['signal_connection_mismatches']
    moved_check=verify_moved_export(netlist,moved)
    assert sha(sdc)==sdchash
    state.update(odb=str(odb),nl=str(OUT/'routed.v'),metrics={});state['def']=str(OUT/'routed.def')
    for key in ['spef','sdf','lib','pnl']:
        if key in state:state[key]=None
    initial.write_text(json.dumps(state,indent=2)+'\n')
    report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdchash,export_script_sha256=sha(export))
    report['antenna_netlist_export']=check
    evidence=dict(run=RUN,head=HEAD,artifact=m,metrics=r['metrics'],identity=ident,preservation=preserve,geometry=g,buffer_artifact=bm,buffer_audit=bi,buffer_power=bp,diode_moves=moved_audit,moved_diode_export=moved_check,diode_artifact=am,diode_power=ap,wrapper_sha256=sha(__file__),rebind_helper_sha256=sha(Path(__file__).with_name('rebind_regression_antenna_inventory.py')),production_admissible=False)
    (OUT/'regression-route-source.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (OUT/'source-antenna.rpt').write_bytes(z.read('antenna.rpt'))
    artifacts.extend([bm,nm,am,m])
    return report,artifacts,initial

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    previous.OUT=OUT;previous.clean.OUT=OUT;flow.OUT=OUT
    flow.EXPECTED_INSTANCES=106672
    flow.restore_route=restore_candidate;flow.RUN=RUN;flow.HEAD=HEAD
    flow.main()
