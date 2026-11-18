#!/usr/bin/env python3
"""Three genuine library corners, nominal SPEF, provisional shell timing only."""
import os,json,hashlib,subprocess,urllib.request,re,math
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,api,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-extracted-timing'
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
MODELS={
 'slow': [('sg13g2_stdcell','sg13g2_stdcell_slow_1p08V_125C.lib','ed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d'),('sg13g2_io','sg13g2_io_slow_1p08V_3p0V_125C.lib','a23776c264fc0d177b4a5612eb3e1595c0eddc98d5b28b5ef7925e40b743b6ae')],
 'fast': [('sg13g2_stdcell','sg13g2_stdcell_fast_1p32V_m40C.lib','547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e'),('sg13g2_io','sg13g2_io_fast_1p32V_3p6V_m40C.lib','0dbc28e762ac820f9db193a2736f408cf1cbf521547fef850083a585c70f212f')]}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,qualified_rc_minmax=False,full_chip_timing=False,core_model_present=False,external_io_constraints_qualified=False,cdc_constraints_qualified=False,corners={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44295912370,'32defeaac27ef9bb4abb7ad04d612a9b18a11f18');z,meta=archive(run,'core-only-chip-spef-coverage-native-44295912370')
        assert meta['id']==14423477347 and meta['digest']=='sha256:1c96b8296ca6afc02a7f5611b94a925b42097d7e0e77fedac69f6c42b922a793'
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        a=source['audit'];assert a==json.loads(z.read('coverage.json'))and a['parsed_nets']==a['expected_wired_multiterminal_nets']==1615
        assert not any(a[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
        for p in ['chip-detailedroute.odb','chip-shell.nom.spef']:(OUT/p).write_bytes(z.read(p))
        r['coverage_artifact']=meta
        route=api('actions/runs/44289826075');assert route['head_sha']=='723fe02e71279036fabb7a5d7204d309351f4e19'and route['status']=='completed'and route['conclusion']=='failure'
        rz,rm=archive(route,'core-only-chip-detailedroute-native-44289826075');assert rm['id']==14420727343 and rm['digest']=='sha256:10a4fc032d2da17bf3dc2e59418905b3e9c38bd8f30e7c0e2e88163aeb3a2920'
        rr=json.loads(rz.read('result.json'));assert rr['error']=="AssertionError('Guided nets without native wire remain')"and rr['sources_unchanged']
        for p,h in rr['outputs'].items():assert hashlib.sha256(rz.read(p)).hexdigest()==h
        assert rr['outputs']['chip-detailedroute.odb']==sha(OUT/'chip-detailedroute.odb')
        for p in ['std.lib','io.lib','shell-cts.sdc']:(OUT/p).write_bytes(rz.read(p))
        assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
        libs={'typ':[OUT/'std.lib',OUT/'io.lib']};r['library_sources']={}
        for corner,models in MODELS.items():
            libs[corner]=[]
            for library,name,digest in models:
                url=f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/ihp-sg13g2/libs.ref/{library}/lib/{name}'
                with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
                assert hashlib.sha256(data).hexdigest()==digest
                path=OUT/name;path.write_bytes(data);libs[corner].append(path);r['library_sources'][name]=dict(url=url,sha256=digest)
        protected={str(p):sha(p)for p in [Path(__file__),OUT/'chip-detailedroute.odb',OUT/'chip-shell.nom.spef',OUT/'shell-cts.sdc',*[p for pair in libs.values()for p in pair]]};r['protected_inputs']=protected
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
        assert all(sha(p)==h for p,h in protected.items());r.update(status='THREE_LIBRARY_CORNER_PARENT_SPEF_DIAGNOSTIC_COMPLETE_NOT_FULL_CHIP_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
