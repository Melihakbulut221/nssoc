#!/usr/bin/env python3
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,api,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-pdn-shorts'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=api('actions/runs/44285682859');assert run['head_sha']=='0155ccf26dd83c73b4a5d0306e0d247fd6e1a279'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
        z,meta=archive(run,'core-only-chip-pdn-native-44285682859');assert meta['id']==14417519581 and meta['digest']=='sha256:4c8d5f1dd0de7bace219023fa7229611db30247f0fdcfab559ff06003cef2fab'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged'] and source['source_head']==run['head_sha'] and source['status']=='FAIL_OR_INCOMPLETE'
        assert source['audit']['top_pin_shapes_unchanged']and source['audit']['readback_equal']
        assert {k:v['returncode']for k,v in source['connectivity_checks'].items()}=={'VDD':1,'VSS':1,'IOVDD':0,'IOVSS':0}
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        (OUT/'chip-pdn.odb').write_bytes(z.read('chip-pdn.odb'));r['source_artifact']=meta;r['source_connectivity_accepted']=False
        script=ROOT/'scripts/audit_core_only_pdn_shorts.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-pdn.odb']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PDN_SHORT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'short-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items());r.update(status=r['audit']['status'],sources_unchanged=True)
        assert r['audit']['contact_pairs']==0,'Native power-metal contacts found; see bound diagnostic'
    except BaseException as error:r.update(error=repr(error));r['status']='FAIL_OR_INCOMPLETE'if 'audit'not in r else r['audit']['status'];raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
