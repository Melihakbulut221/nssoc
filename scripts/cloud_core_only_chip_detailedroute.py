#!/usr/bin/env python3
"""Detailed-route provisional integrated shell; preserve all native route evidence."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-detailedroute'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,final_core_route=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44288482143,'3504a9110b5b995fa8f8b7aa610a183f5f50f447');z,meta=archive(run,'core-only-chip-globalroute-native-44288482143');assert meta['id']==14419523617 and meta['digest']=='sha256:1a3c8a283db8bedda2c2d07eb6347e4a228dee1ff36f9ddff42e05687097290c'
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']and not source['audit']['unguided_multi_terminal_nets']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for n in ['chip-globalroute.odb','chip.guide','std.lib','io.lib','shell-cts.sdc']:(OUT/n).write_bytes(z.read(n))
        r['source_artifact']=meta;script=ROOT/'scripts/audit_core_only_chip_detailedroute.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-globalroute.odb',OUT/'chip.guide',OUT/'std.lib',OUT/'io.lib',OUT/'shell-cts.sdc']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def path(n):return '{'+str(OUT/n)+'}'
        tcl='set_thread_count 4\nread_liberty '+path('std.lib')+'\nread_liberty '+path('io.lib')+'\nread_db '+path('chip-globalroute.odb')+'\nread_sdc '+path('shell-cts.sdc')+'\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nread_guides '+path('chip.guide')+'\n'
        tcl+='detailed_route -output_drc '+path('route-drc.rpt')+' -output_maze '+path('maze.log')+' -output_guide_coverage '+path('guide-coverage.csv')+' -verbose 1\n'
        tcl+='set f [open '+path('native-drc-count.txt')+' w]\nputs $f [detailed_route_num_drvs]\nclose $f\n'
        tcl+='write_db '+path('chip-detailedroute.odb')+'\nwrite_def '+path('chip-detailedroute.def')+'\nwrite_verilog '+path('chip-detailedroute.v')+'\nputs NSSOC_CHIP_DETAILED_ROUTE_COMPLETE\n'
        (OUT/'route.tcl').write_text(tcl);r['status']='DETAILED_ROUTING';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'route.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_CHIP_DETAILED_ROUTE_COMPLETE'in(OUT/'native.log').read_text()
        r['native_drc_count']=int((OUT/'native-drc-count.txt').read_text());assert r['native_drc_count']>=0
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CHIP_DRT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'route-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items());r['sources_unchanged']=True
        r['status']='PROVISIONAL_CHIP_DETAILED_ROUTE_EXECUTED_REQUIRES_CONNECTIVITY_ANTENNA_RC_AND_SIGNOFF'
        assert r['native_drc_count']==0,'Native detailed-router DRC remains open'
        assert not r['audit']['unwired_guided_nets'],'Guided nets without native wire remain'
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
