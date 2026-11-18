#!/usr/bin/env python3
"""Native provisional chip PDN generation with strict terminal connectivity checks."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-pdn'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,production_qualified=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44283129318,'8526e0b702f7d0ede3d272700272122125d535fb');z,meta=archive(run,'core-only-chip-cts-native-44283129318')
        assert meta['id']==14418726039 and meta['digest']=='sha256:18d07bd2c3e6cceabb308361cadac9e20665ddce448d7af9e0a1f41aa3506621'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged'] and source['source_head']==run['head_sha']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for name in ['chip-cts.odb','std.lib','io.lib']:(OUT/name).write_bytes(z.read(name))
        r['source_artifact']=meta;script=ROOT/'scripts/audit_core_only_chip_pdn.py'
        protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-cts.odb',OUT/'std.lib',OUT/'io.lib']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def path(n):return '{'+str(OUT/n)+'}'
        tcl='read_liberty '+path('std.lib')+'\nread_liberty '+path('io.lib')+'\nread_db '+path('chip-cts.odb')+'\n'
        tcl+='set_voltage_domain -name CORE -power VDD -ground VSS\n'
        tcl+='define_pdn_grid -name shell -voltage_domains CORE\n'
        tcl+='add_pdn_ring -grid shell -layers {TopMetal1 TopMetal2} -widths 5 -spacings 3 -core_offsets 5 -connect_to_pads -connect_to_pad_layers {Metal3 Metal4 TopMetal1} -add_connect\n'
        tcl+='add_pdn_stripe -grid shell -layer Metal1 -width 0.44 -followpins\n'
        tcl+='add_pdn_stripe -grid shell -layer Metal4 -width 1.2 -pitch 50 -offset 10\n'
        tcl+='add_pdn_stripe -grid shell -layer Metal5 -width 2 -pitch 75.6 -offset 10\n'
        tcl+='add_pdn_stripe -grid shell -layer TopMetal1 -width 2.2 -pitch 75.6 -offset 10 -extend_to_core_ring\n'
        tcl+='add_pdn_stripe -grid shell -layer TopMetal2 -width 2.2 -pitch 75.6 -offset 10 -extend_to_core_ring\n'
        for layers in ['Metal1 Metal4','Metal4 Metal5','Metal5 TopMetal1','TopMetal1 TopMetal2']:tcl+='add_pdn_connect -grid shell -layers {'+layers+'}\n'
        tcl+='define_pdn_grid -name core_macro -macro -instances u_core -voltage_domains CORE -grid_over_pg_pins\nadd_pdn_connect -grid core_macro -layers {TopMetal1 TopMetal2}\n'
        tcl+='pdngen -dont_add_pins -failed_via_report '+path('failed-vias.rpt')+'\nwrite_db '+path('chip-pdn.odb')+'\nwrite_def '+path('chip-pdn.def')+'\nputs NSSOC_PDN_GEOMETRY_GENERATED\n'
        (OUT/'pdn.tcl').write_text(tcl);r['status']='GENERATING';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'pdn.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_PDN_GEOMETRY_GENERATED' in (OUT/'native.log').read_text()
        with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PDN_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'pdn-audit.json').read_text());checks={}
        # Run each rail independently and retain every failure without skipping terminals.
        for net in ['VDD','VSS','IOVDD','IOVSS']:
            check=OUT/(net+'.tcl');check.write_text('read_db '+path('chip-pdn.odb')+'\ncheck_power_grid -net '+net+' -error_file '+path(net+'-errors.rpt')+'\nputs NSSOC_GRID_CHECK_COMPLETE\n')
            with (OUT/(net+'.log')).open('w')as log:p=subprocess.run([str(app),'openroad','-exit',str(check)],stdout=log,stderr=subprocess.STDOUT)
            checks[net]=dict(returncode=p.returncode,completed='NSSOC_GRID_CHECK_COMPLETE' in (OUT/(net+'.log')).read_text())
        r['connectivity_checks']=checks;assert all(sha(p)==h for p,h in protected.items());r['sources_unchanged']=True
        assert all(x['returncode']==0 and x['completed']for x in checks.values()),checks
        r.update(status='PROVISIONAL_PDN_NATIVE_CONNECTIVITY_CHECKED_REQUIRES_SHORT_DRC_IR_EM_AND_FINAL_CORE')
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
