#!/usr/bin/env python3
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-pdn-bridge'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44286574706,'22c7d954d5acd546e0618d7a6f4bbb5d7a795731');z,meta=archive(run,'core-only-chip-pdn-shorts-native-44286574706');assert meta['id']==14420205462 and meta['digest']=='sha256:6f8a01a1c1279103d58422f53bc0098f416856c6c58363ef9d47516a77d84e47'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['source_head']==run['head_sha']and source['audit']['contact_pairs']==0
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for name,target in [('chip-pdn.odb','source-pdn.odb'),('metal-shapes.json.gz','source-metal-shapes.json.gz')]:(OUT/target).write_bytes(z.read(name))
        r['source_artifact']=meta;r['input_core_connectivity_accepted']=False
        builder=ROOT/'scripts/bridge_core_only_pdn_native.py';audit=ROOT/'scripts/audit_core_only_pdn_shorts.py';protected={str(p):sha(p)for p in [Path(__file__),builder,audit,OUT/'source-pdn.odb',OUT/'source-metal-shapes.json.gz']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'build.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(builder)],env=dict(os.environ,NSSOC_BRIDGE_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['bridge_audit']=json.loads((OUT/'bridge-audit.json').read_text())
        with (OUT/'short.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=dict(os.environ,NSSOC_PDN_SHORT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['short_audit']=json.loads((OUT/'short-audit.json').read_text());checks={}
        for net in ['VDD','VSS','IOVDD','IOVSS']:
            t=OUT/(net+'.tcl');t.write_text('read_db {'+str(OUT/'chip-pdn.odb')+'}\ncheck_power_grid -net '+net+' -error_file {'+str(OUT/(net+'-errors.rpt'))+'}\nputs NSSOC_GRID_CHECK_COMPLETE\n')
            with (OUT/(net+'.log')).open('w')as log:p=subprocess.run([str(app),'openroad','-exit',str(t)],stdout=log,stderr=subprocess.STDOUT)
            checks[net]=dict(returncode=p.returncode,completed='NSSOC_GRID_CHECK_COMPLETE'in(OUT/(net+'.log')).read_text())
        r['connectivity_checks']=checks;assert all(sha(p)==h for p,h in protected.items());r['sources_unchanged']=True
        assert r['short_audit']['contact_pairs']==0
        assert all(c['returncode']==0 and c['completed']for c in checks.values()),checks
        r['status']='PROVISIONAL_CORE_POWER_BRIDGES_CONNECTED_REQUIRES_FULL_GDS_DRC_IR_EM_AND_FINAL_CORE'
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
