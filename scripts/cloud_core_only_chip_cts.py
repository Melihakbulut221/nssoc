#!/usr/bin/env python3
"""Experimental shell CTS with native libraries, never full-chip timing acceptance."""
import base64,os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-cts'
REV='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,core_timing_model_available=False,extracted_timing=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44282199219,'faacea2a5b0220cd9593fc80e626ce2cbd5b5bed');z,meta=archive(run,'core-only-chip-clocks-native-44282199219')
        assert meta['id']==14416528949 and meta['digest']=='sha256:3c26d000b834d717231d3bddd642e018ff1b2dd46bb0c84deb7a82e8c049ebdd'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged'] and source['source_head']==run['head_sha']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for name in ['chip-placed.odb','shell.json','clock-audit.json']:(OUT/name).write_bytes(z.read(name))
        r['source_artifact']=meta
        for name,path,digest in [
          ('std.lib','sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib','968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'),
          ('io.lib','sg13g2_io/lib/sg13g2_io_typ_1p2V_3p3V_25C.lib','e9af7d440c807799de55d16a126467e27d3235e7f53a928e014cdabee98369c9')]:
            row=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/libs.ref/'+path+'?ref='+REV]))
            if row.get('encoding')!='base64':row=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/git/blobs/'+row['sha']]))
            data=base64.b64decode(row['content']);assert hashlib.sha256(data).hexdigest()==digest;(OUT/name).write_bytes(data)
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');script=ROOT/'scripts/audit_core_only_chip_cts.py'
        protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-placed.odb',OUT/'shell.json',OUT/'clock-audit.json',OUT/'std.lib',OUT/'io.lib']};r['protected_inputs']=protected
        def path(name):return '{'+str(OUT/name)+'}'
        tcl='read_liberty '+path('std.lib')+'\nread_liberty '+path('io.lib')+'\nread_db '+path('chip-placed.odb')+'\n'
        tcl+='create_clock -name shell_main -period 20 [get_pins {u_pad_clk_i/p2c}]\ncreate_clock -name shell_test -period 20 [get_pins {u_pad_test_clk/p2c}]\n'
        tcl+='set_timing_derate -early 0.95\nset_timing_derate -late 1.05\nset_wire_rc -signal -layer Metal3\nset_wire_rc -clock -layer Metal4\n'
        tcl+='clock_tree_synthesis -clk_nets {n_1486 n_1484} -root_buf sg13g2_buf_8 -buf_list {sg13g2_buf_2 sg13g2_buf_4 sg13g2_buf_8 sg13g2_buf_16} -sink_clustering_enable -sink_clustering_size 8 -obstruction_aware -dont_use_dummy_load\n'
        tcl+='add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power\nadd_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground\nglobal_connect\n'
        tcl+='detailed_placement\ncheck_placement -verbose\nreport_cts\nwrite_db '+path('chip-cts.odb')+'\nwrite_def '+path('chip-cts.def')+'\nwrite_verilog '+path('chip-cts.v')+'\nwrite_sdc '+path('shell-cts.sdc')+'\nputs NSSOC_SHELL_CTS_COMPLETE\n'
        (OUT/'cts.tcl').write_text(tcl);r['status']='EXPERIMENTAL_CTS';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'cts.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_SHELL_CTS_COMPLETE' in (OUT/'native.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CTS_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'cts-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items())
        r.update(status='EXPERIMENTAL_SHELL_CTS_CONNECTED_REQUIRES_CORE_MODEL_ROUTING_AND_TIMING',sources_unchanged=True,scope='Typical native models and LEF wire RC estimate; internal clock roots both20ns; no I/O delay or final core clock capacitance/insertion delay model. No CTS signoff, CDC/MTBF, extracted skew, power routing or production acceptance.')
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
