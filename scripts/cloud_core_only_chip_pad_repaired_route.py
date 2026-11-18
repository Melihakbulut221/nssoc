#!/usr/bin/env python3
"""Fresh global+detailed routing and geometry checks for the buffer ECO."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-pad-repaired-route'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,extracted_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        admission=json.loads((ROOT/'docs/evidence/core-only-pad-repair-admission.json').read_text())
        assert admission['verified'] and admission['artifact_id'] and admission['artifact_sha256'],'Pad repair must be independently admitted before dispatch'
        run=completed(admission['run'],admission['head'])
        z,meta=archive(run,'core-only-chip-pad-repair-native-'+str(admission['run']))
        assert meta['id']==admission['artifact_id'] and meta['digest']=='sha256:'+admission['artifact_sha256']
        summary,smeta=archive(run,'core-only-chip-pad-repair-summary-'+str(admission['run']))
        assert smeta['id']==admission['summary_id'] and smeta['digest']=='sha256:'+admission['summary_sha256']
        assert z.read('result.json')==summary.read('result.json')
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']
        assert source['status']=='PAD_BUFFER_CANDIDATE_LEGALIZED_AND_CONNECTIVITY_VERIFIED_REQUIRES_FRESH_PHYSICAL_AND_TIMING'
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        a=source['audit'];assert all(a[k]for k in ['original_instances_pins_and_power_geometry_unchanged','original_connectivity_classes_preserved','only_selected_pad_nets_modified','actual_buffer_sources_verified','stale_routes_removed'])
        assert a['new_buffers']==admission['new_buffers'] and a['new_buffers']>0
        expected_nets=1794+a['new_buffers']
        for p in ['std.lib','io.lib','shell-cts.sdc','repair-audit.json','repair-selection.json']:(OUT/p).write_bytes(z.read(p))
        # Byte-identical alias for the previously qualified route identity checker.
        (OUT/'chip-buffered-placed.odb').write_bytes(z.read('chip-pad-repair-unrouted.odb'))
        assert sha(OUT/'chip-buffered-placed.odb')==source['outputs']['chip-pad-repair-unrouted.odb']
        r['pad_repair_admission']=admission;r['expected_routed_nets']=expected_nets
        r['source_artifact']=meta
        selector=ROOT/'scripts/select_core_only_pad_repaired_route_nets.py'
        scripts=[ROOT/'scripts/audit_core_only_buffered_route.py',ROOT/'scripts/audit_native_signal_geometry.py',ROOT/'scripts/buffer_core_only_chip_controls.py']
        protected={str(p):sha(p)for p in [Path(__file__),ROOT/'docs/evidence/core-only-pad-repair-admission.json',selector,*scripts,OUT/'chip-buffered-placed.odb',OUT/'std.lib',OUT/'io.lib',OUT/'shell-cts.sdc']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'selection.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(selector)],env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_EXPECTED_PAD_ROUTE_NETS=str(expected_nets)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['route_selection']=json.loads((OUT/'route-selection.json').read_text());assert len(r['route_selection']['selected_nets'])==expected_nets
        def q(n):return '{'+str(OUT/n)+'}'
        tcl='set_thread_count 4\nread_liberty '+q('std.lib')+'\nread_liberty '+q('io.lib')+'\nread_db '+q('chip-route-input.odb')+'\nread_sdc '+q('shell-cts.sdc')+'\n'
        tcl+='foreach name {VDD VSS IOVDD IOVSS} {set net [[ord::get_db_block] findNet $name]; if {$net=="NULL"} {error "Missing supply"}; $net setSpecial; check_power_grid -net $name; puts "NSSOC_POWER_CONNECTED_$name"}\n'
        tcl+='set_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.3\n'
        tcl+='source '+q('route-selection.tcl')+'\n'
        tcl+='global_route -guide_file '+q('chip.guide')+' -congestion_report_file '+q('congestion.rpt')+' -congestion_iterations 300 -verbose\n'
        tcl+='write_db '+q('chip-globalroute.odb')+'\nread_guides '+q('chip.guide')+'\n'
        tcl+='detailed_route -output_drc '+q('route-drc.rpt')+' -output_maze '+q('maze.log')+' -output_guide_coverage '+q('guide-coverage.csv')+' -verbose 1\n'
        tcl+='set f [open '+q('native-drc-count.txt')+' w]\nputs $f [detailed_route_num_drvs]\nclose $f\nwrite_db '+q('chip-detailedroute.odb')+'\nwrite_def '+q('chip-detailedroute.def')+'\nwrite_verilog '+q('chip-detailedroute.v')+'\nputs NSSOC_BUFFERED_DETAILED_ROUTE_COMPLETE\n'
        script=OUT/'route.tcl';script.write_text(tcl);protected[str(script)]=sha(script);r['status']='ROUTING_BUFFERED_CANDIDATE';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
        log=(OUT/'native.log').read_text();assert 'NSSOC_BUFFERED_DETAILED_ROUTE_COMPLETE'in log
        assert all('NSSOC_POWER_CONNECTED_'+n in log for n in ['VDD','VSS','IOVDD','IOVSS'])
        r['native_drc_count']=int((OUT/'native-drc-count.txt').read_text());assert r['native_drc_count']==0 and (OUT/'route-drc.rpt').read_text().strip()==''
        env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_PHYSICAL_ROUTE_OUT=str(OUT),NSSOC_PHYSICAL_ROUTE_ODB=str(OUT/'chip-detailedroute.odb'))
        for script,name in [(scripts[0],'identity'),(scripts[1],'physical')]:
            with (OUT/(name+'.log')).open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        r['identity_audit']=json.loads((OUT/'route-identity.json').read_text());r['geometry_audit']=json.loads((OUT/'physical-route-audit.json').read_text())
        a=r['geometry_audit'];assert not a['signal_nets_with_disconnected_geometry']and not a['terminals_without_geometry']and a['inter_net_contact_pairs']==0
        assert sorted(x['net']for x in a['unwired_multi_terminal_nets'])==r['identity_audit']['unwired']and len(a['unwired_multi_terminal_nets'])==76
        assert all(x['components']==1 and x['terminals']==2 for x in a['unwired_multi_terminal_nets'])
        assert all(sha(p)==h for p,h in protected.items());r.update(status='BUFFERED_PARENT_ROUTED_AND_VISIBLE_GEOMETRY_VERIFIED_REQUIRES_EXTRACTED_TIMING_AND_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
