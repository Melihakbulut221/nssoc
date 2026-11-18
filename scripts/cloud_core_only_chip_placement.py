#!/usr/bin/env python3
"""Cloud-only legal shell placement; provisional core, no timing acceptance."""
import hashlib,json,os,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-placement'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,final_core_route=False,timing_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44275589227,'9d29ca02d34ff6261a7dffec384442ec77cf163b')
        z,meta=archive(run,'core-only-chip-assembly-native-44275589227')
        assert meta['id']==14414790892 and meta['digest']=='sha256:f4b055d167c1cab6b18733a0b86b3d5d5edd49d987b2819b92148f8325633178'
        source=json.loads(z.read('result.json'))
        assert source['source_head']==run['head_sha'] and source['sources_unchanged'] and source['native_result']['odb_readback_equal']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        (OUT/'chip-initial.odb').write_bytes(z.read('chip-initial.odb'))
        r['source_artifact']=meta
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        audit=ROOT/'scripts/audit_core_only_chip_placement.py'
        protected={str(p):sha(p)for p in [Path(__file__),audit,OUT/'chip-initial.odb']};r['protected_inputs']=protected
        tcl=OUT/'place.tcl'
        tcl.write_text('read_db {'+str(OUT/'chip-initial.odb')+'}\n'+
          'initialize_floorplan -die_area {0 0 4000 3200} -core_area {200 200 3800 3000} -site CoreSite\n'+
          'cut_rows -halo_width_x 20 -halo_width_y 20\n'+
          'global_placement -disable_timing_driven -disable_routability_driven -density 0.3\n'+
          'detailed_placement\ncheck_placement -verbose -report_file_name {'+str(OUT/'placement-check.json')+'}\n'+
          'write_db {'+str(OUT/'chip-placed.odb')+'}\nwrite_def {'+str(OUT/'chip-placed.def')+'}\nputs NSSOC_LEGAL_PLACEMENT_COMPLETE\n')
        r['status']='PLACING';save()
        with (OUT/'placement.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_LEGAL_PLACEMENT_COMPLETE' in (OUT/'placement.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=dict(os.environ,NSSOC_PLACEMENT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'audit.json').read_text())
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PROVISIONAL_SHELL_LEGAL_PLACEMENT_VERIFIED_REQUIRES_CTS_POWER_ROUTING_AND_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
