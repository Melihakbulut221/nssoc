#!/usr/bin/env python3
"""Three genuine library corners, nominal SPEF, provisional shell timing only."""
import os,json,hashlib,subprocess,urllib.request,re,math,sys
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,api,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-buffered-timing'
ROUTE_RUN=44299714366
ROUTE_HEAD='4e5f4aac78beb0e08282f62af347080b13ae5f7f'
# Admission pinned after independent native/summary/output/source verification.
ROUTE_ARTIFACT_ID=14425388007
ROUTE_ARTIFACT_SHA='c05a6ef1e93f269db0fb0f04aa9758e0f674c3bf9712f2774aecf9ab3f280d5d'
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
MODELS={
 'slow': [('sg13g2_stdcell','sg13g2_stdcell_slow_1p08V_125C.lib','ed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d'),('sg13g2_io','sg13g2_io_slow_1p08V_3p0V_125C.lib','a23776c264fc0d177b4a5612eb3e1595c0eddc98d5b28b5ef7925e40b743b6ae')],
 'fast': [('sg13g2_stdcell','sg13g2_stdcell_fast_1p32V_m40C.lib','547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e'),('sg13g2_io','sg13g2_io_fast_1p32V_3p6V_m40C.lib','0dbc28e762ac820f9db193a2736f408cf1cbf521547fef850083a585c70f212f')]}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,qualified_rc_minmax=False,full_chip_timing=False,core_model_present=False,external_io_constraints_qualified=False,cdc_constraints_qualified=False,corners={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        assert ROUTE_ARTIFACT_ID and ROUTE_ARTIFACT_SHA,'Route artifact must be independently verified and pinned before dispatch'
        run=completed(ROUTE_RUN,ROUTE_HEAD);z,meta=archive(run,'core-only-chip-buffered-route-native-'+str(ROUTE_RUN))
        assert meta['id']==ROUTE_ARTIFACT_ID and meta['digest']=='sha256:'+ROUTE_ARTIFACT_SHA
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']and source['native_drc_count']==0
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        a=source['geometry_audit'];assert not a['signal_nets_with_disconnected_geometry']and not a['terminals_without_geometry']and a['inter_net_contact_pairs']==0
        assert source['identity_audit']['placements_masters_connections_pins_and_power_geometry_unchanged']
        assert source['route_selection']['all_omitted_have_identical_pin_shapes']and len(source['route_selection']['selected_nets'])==1794
        for p in ['chip-detailedroute.odb','std.lib','io.lib','shell-cts.sdc']:(OUT/p).write_bytes(z.read(p))
        assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
        r['route_artifact']=meta
        url=f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/ihp-sg13g2/libs.tech/librelane/IHP_rcx_patterns.rules'
        with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()=='ffda02d57a6ecb39b02268be9511d89ef072911f17bd2dcd095f3f3cbeb5a905'
        rule=OUT/'IHP_rcx_patterns.rules';rule.write_bytes(data)
        auditor=ROOT/'hw/soc/flow/audit_estimated_spef.py';coverage=ROOT/'scripts/audit_core_only_chip_spef_coverage.py'
        stage_protected={str(p):sha(p)for p in [Path(__file__),OUT/'chip-detailedroute.odb',rule,auditor,coverage]}
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def q(p):return '{'+str(p)+'}'
        extraction=OUT/'extract.tcl'
        extraction.write_text('set_thread_count 4\nread_db '+q(OUT/'chip-detailedroute.odb')+'\ndefine_process_corner -ext_model_index 0 nominal\nextract_parasitics -ext_model_file '+q(rule)+' -lef_res\nwrite_spef '+q(OUT/'chip-shell.nom.spef')+'\nputs NSSOC_FRESH_BUFFERED_RCX_COMPLETE\n')
        stage_protected[str(extraction)]=sha(extraction);r['status']='FRESH_BUFFERED_EXTRACTION';save()
        with (OUT/'extraction.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(extraction)],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_FRESH_BUFFERED_RCX_COMPLETE'in(OUT/'extraction.log').read_text()
        sys.path.insert(0,str(auditor.parent));from audit_estimated_spef import audit
        check=audit(OUT/'chip-shell.nom.spef',allow_coupling=True);r['spef_integrity']=check
        (OUT/'spef-integrity.json').write_text(json.dumps(check,indent=2)+'\n');assert check['status'].startswith('PASS')
        with (OUT/'coverage.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(coverage)],env=dict(os.environ,NSSOC_SPEF_COVERAGE_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        ca=json.loads((OUT/'coverage.json').read_text());assert ca['parsed_nets']==ca['expected_wired_multiterminal_nets']==1794
        assert not any(ca[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
        assert ca['unwired_multiterminal_nets']==sorted(x['net']for x in source['route_selection']['coincident_pad_nets'])
        r['coverage']=ca
        assert all(sha(p)==h for p,h in stage_protected.items())
        libs={'typ':[OUT/'std.lib',OUT/'io.lib']};r['library_sources']={}
        for corner,models in MODELS.items():
            libs[corner]=[]
            for library,name,digest in models:
                url=f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/ihp-sg13g2/libs.ref/{library}/lib/{name}'
                with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
                assert hashlib.sha256(data).hexdigest()==digest
                path=OUT/name;path.write_bytes(data);libs[corner].append(path);r['library_sources'][name]=dict(url=url,sha256=digest)
        protected={str(p):sha(p)for p in [Path(__file__),OUT/'chip-detailedroute.odb',OUT/'chip-shell.nom.spef',OUT/'shell-cts.sdc',*[p for pair in libs.values()for p in pair]]};protected.update(stage_protected);r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def q(p):return '{'+str(p)+'}'
        for corner in ['slow','typ','fast']:
            folder=OUT/corner;folder.mkdir()
            tcl='set_thread_count 1\n'+''.join('read_liberty '+q(p)+'\n'for p in libs[corner])
            tcl+='read_db '+q(OUT/'chip-detailedroute.odb')+'\nread_sdc '+q(OUT/'shell-cts.sdc')+'\nread_spef '+q(OUT/'chip-shell.nom.spef')+'\n'
            tcl+='if {[llength [all_clocks]] != 2} {error "Unexpected shell clocks"}\nforeach name {shell_main shell_test} {set c [get_clocks $name]; if {[llength $c]!=1 || abs([get_property $c period]-20)>1e-9 || ![get_property $c is_propagated]} {error "Shell clock constraint changed"}}\n'
            tcl+='puts NSSOC_ACTUAL_SPEF_LOADED_PROPAGATED_SHELL_CLOCKS\nreport_parasitic_annotation -report_unannotated\ncheck_setup -verbose\nreport_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\n'
            for delay in ['max','min']:
                tcl+='report_checks -path_delay '+delay+' -group_path_count 100 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 9 > '+q(folder/(delay+'-paths.rpt'))+'\n'
            tcl+='report_check_types -max_delay -min_delay -max_slew -max_capacitance -max_fanout -violators -digits 9 > '+q(folder/'violations.rpt')+'\nputs NSSOC_PARENT_EXTRACTED_STA_COMPLETE\n'
            script=folder/'timing.tcl';script.write_text(tcl);protected[str(script)]=sha(script);r['status']='ANALYZING_'+corner;save()
            with (folder/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
            log=(folder/'native.log').read_text();assert 'NSSOC_PARENT_EXTRACTED_STA_COMPLETE'in log and 'NSSOC_ACTUAL_SPEF_LOADED_PROPAGATED_SHELL_CLOCKS'in log
            metrics={}
            for delay in ['max','min']:
                matches=re.findall(r'(?m)^worst slack '+delay+r' ([+-]?[0-9]+(?:\.[0-9]+)?)\s*$',log);assert len(matches)==1,(corner,delay)
                metrics[delay+'_worst_slack_ns']=float(matches[0]);assert math.isfinite(metrics[delay+'_worst_slack_ns'])
                assert 'Startpoint:'in(folder/(delay+'-paths.rpt')).read_text(),'No real paths reported'
            r['corners'][corner]=dict(metrics=metrics,log_sha256=sha(folder/'native.log'),nominal_rc_only=True,provisional_internal_clocks=True)
        assert all(sha(p)==h for p,h in protected.items());r.update(status='BUFFERED_PARENT_FRESH_RCX_COVERAGE_AND_THREE_CORNER_TIMING_COMPLETE_NOT_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
