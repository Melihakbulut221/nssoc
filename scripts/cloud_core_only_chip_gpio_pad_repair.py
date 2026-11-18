#!/usr/bin/env python3
"""Candidate-only pad wire repair using explicit LEF placement estimates."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-gpio-pad-repair'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,estimated_candidate_only=True,extracted_timing_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44306169864,'7a105c9f7c8b30b3ad8fffba375d48ffaa801928');z,meta=archive(run,'core-only-chip-pad-repaired-timing-native-44306169864');assert meta['id']==14427703059 and meta['digest']=='sha256:1da59177617373371b6650b0c5c0565cc72d4465c641cbe660ae88caaab44321'
        summary,sm=archive(run,'core-only-chip-pad-repaired-timing-summary-44306169864')
        assert sm['id']==14429105410 and sm['digest']=='sha256:a0b3089db04eaebf25c709d5331c4fb44aa448bd6820063e66241ed6a099b5d9'
        assert z.read('result.json')==summary.read('result.json')
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']and source['coverage']['parsed_nets']==1939
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for p,h in source['protected_inputs'].items():
            prefix='/home/runner/work/nssoc/nssoc/'
            assert p.startswith(prefix)
            relative=p[len(prefix):]
            if not relative.startswith('hw/soc/out/'):assert sha(ROOT/relative)==h,relative
        for p in ['chip-detailedroute.odb','std.lib','io.lib','shell-cts.sdc','sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib']:(OUT/p).write_bytes(z.read(p))
        (OUT/'slow-violations.rpt').write_bytes(z.read('slow/violations.rpt'))
        scripts=[ROOT/'scripts/prepare_core_only_gpio_pad_repair.py',ROOT/'scripts/audit_core_only_pad_repair.py',ROOT/'scripts/buffer_core_only_chip_controls.py'];protected={str(p):sha(p)for p in [Path(__file__),*scripts,*[p for p in OUT.iterdir()if p.is_file()]]};r.update(source_artifact=meta,protected_inputs=protected)
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');env=dict(os.environ,NSSOC_PAD_REPAIR_OUT=str(OUT),NSSOC_CONTROL_BUFFER_OUT=str(OUT))
        with (OUT/'prepare.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(scripts[0])],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        r['selection']=json.loads((OUT/'repair-selection.json').read_text())
        def q(n):return '{'+str(OUT/n)+'}'
        tcl='set_thread_count 4\nread_liberty '+q('sg13g2_stdcell_slow_1p08V_125C.lib')+'\nread_liberty '+q('sg13g2_io_slow_1p08V_3p0V_125C.lib')+'\nread_db '+q('repair-input.odb')+'\nread_sdc '+q('shell-cts.sdc')+'\n'
        tcl+='set_wire_rc -signal -layer Metal3\nset_wire_rc -clock -layer Metal4\nestimate_parasitics -placement\nrepair_design -max_wire_length 500 -slew_margin 10 -cap_margin 10 -verbose\n'
        tcl+='add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power\nadd_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground\nglobal_connect\ndetailed_placement\ncheck_placement -verbose\n'
        tcl+='write_db '+q('repair-placed.odb')+'\nwrite_verilog '+q('repair-placed.v')+'\nputs NSSOC_PAD_REPAIR_CANDIDATE_COMPLETE\n'
        (OUT/'repair.tcl').write_text(tcl);r['status']='ESTIMATED_PLACEMENT_REPAIR';save()
        with (OUT/'repair.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'repair.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_PAD_REPAIR_CANDIDATE_COMPLETE'in(OUT/'repair.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(scripts[1])],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'repair-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items());r.update(status='PAD_BUFFER_CANDIDATE_LEGALIZED_AND_CONNECTIVITY_VERIFIED_REQUIRES_FRESH_PHYSICAL_AND_TIMING',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
