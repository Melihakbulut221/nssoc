#!/usr/bin/env python3
"""Global-route actual shell plus power-connected provisional core and pads."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-globalroute'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,final_core_route=False,detailed_route=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        sources=[]
        for rid,head,prefix,aid,digest,names in [
          (44287583796,'fe75725b7b6b6336b644b03a6e9752bb5d943ffa','core-only-pdn-bridge-native-',14419453462,'05965467d9472143166b0f9b68898e7f28070a15eccb6b7cba4a609d5cd179c2',['chip-pdn.odb']),
          (44283129318,'8526e0b702f7d0ede3d272700272122125d535fb','core-only-chip-cts-native-',14418726039,'18d07bd2c3e6cceabb308361cadac9e20665ddce448d7af9e0a1f41aa3506621',['std.lib','io.lib','shell-cts.sdc'])]:
            run=completed(rid,head);z,meta=archive(run,prefix+str(rid));assert meta['id']==aid and meta['digest']=='sha256:'+digest
            source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['source_head']==head
            for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
            if rid==44287583796:
                assert source['short_audit']['contact_pairs']==0 and source['bridge_audit']['bridge_count']==172
                assert all(c['returncode']==0 and c['completed']for c in source['connectivity_checks'].values())
            for n in names:(OUT/n).write_bytes(z.read(n))
            sources.append(meta)
        r['source_artifacts']=sources;script=ROOT/'scripts/audit_core_only_chip_globalroute.py'
        protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-pdn.odb',OUT/'std.lib',OUT/'io.lib',OUT/'shell-cts.sdc']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def path(n):return '{'+str(OUT/n)+'}'
        tcl='read_liberty '+path('std.lib')+'\nread_liberty '+path('io.lib')+'\nread_db '+path('chip-pdn.odb')+'\nread_sdc '+path('shell-cts.sdc')+'\n'
        tcl+='make_tracks\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.3\n'
        tcl+='global_route -guide_file '+path('chip.guide')+' -congestion_report_file '+path('congestion.rpt')+' -congestion_iterations 50 -verbose\n'
        tcl+='write_db '+path('chip-globalroute.odb')+'\nwrite_def '+path('chip-globalroute.def')+'\nputs NSSOC_SHELL_GLOBAL_ROUTE_COMPLETE\n'
        (OUT/'route.tcl').write_text(tcl);r['status']='GLOBAL_ROUTING';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'route.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_SHELL_GLOBAL_ROUTE_COMPLETE'in(OUT/'native.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CHIP_ROUTE_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'route-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PROVISIONAL_CHIP_GLOBAL_GUIDES_GENERATED_REQUIRES_COVERAGE_DETAILED_ROUTE_AND_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
