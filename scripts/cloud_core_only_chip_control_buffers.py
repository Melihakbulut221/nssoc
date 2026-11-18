#!/usr/bin/env python3
"""Build and legalize a source-bound parent high-fanout ECO in cloud."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-control-buffers'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44296516767,'ed581f164b7337a907c6db87a3f9cfcabc515a9f');z,meta=archive(run,'core-only-chip-extracted-timing-native-44296516767')
        assert meta['id']==14422714653 and meta['digest']=='sha256:a0b94bf4cf885a862571975a130ab14ed8e7f8fe850830e2f3a2430db28d163e'
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for p in ['chip-detailedroute.odb','std.lib','io.lib','shell-cts.sdc']:(OUT/p).write_bytes(z.read(p))
        scripts=[ROOT/'scripts/buffer_core_only_chip_controls.py',ROOT/'scripts/audit_core_only_control_buffers.py'];protected={str(p):sha(p)for p in [Path(__file__),*scripts,OUT/'chip-detailedroute.odb',OUT/'std.lib',OUT/'io.lib',OUT/'shell-cts.sdc']};r.update(source_artifact=meta,protected_inputs=protected)
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT))
        with (OUT/'buffer.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(scripts[0])],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        def q(n):return '{'+str(OUT/n)+'}'
        tcl='read_db '+q('chip-buffered.odb')+'\ndetailed_placement\ncheck_placement -verbose\nwrite_db '+q('chip-buffered-placed.odb')+'\nwrite_def '+q('chip-buffered-placed.def')+'\nwrite_verilog '+q('chip-buffered-placed.v')+'\nputs NSSOC_BUFFER_LEGALIZATION_COMPLETE\n'
        (OUT/'legalize.tcl').write_text(tcl)
        with (OUT/'legalize.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'legalize.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_BUFFER_LEGALIZATION_COMPLETE'in(OUT/'legalize.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(scripts[1])],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'legalized-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items());r.update(status='CONTROL_BUFFER_ECO_LEGALIZED_REQUIRES_FRESH_ROUTING_EXTRACTION_AND_TIMING',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
