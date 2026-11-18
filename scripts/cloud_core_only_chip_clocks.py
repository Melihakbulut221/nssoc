#!/usr/bin/env python3
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-clocks'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        sources=[]
        for rid,head,name,aid,digest,folder,entry,target in [
          (44280535239,'d7494b71ca03709edd3c4a99589c843170bcc0cf','core-only-chip-placement-native-',14415469830,'77c6f9d188a013dd4b30560971bbf8b5f7c3599652238e2dc2ac20378b32da32','','chip-placed.odb','chip-placed.odb'),
          (44268658068,'8e3e1d4192178ebce2eb83ec4a7430a0bb80bac5','core-only-shell-map-',14410678768,'8bda874049c1183108258285d4b3dbd8782c6df175d3c5faa2875691058a0d15','core-only-shell-map/','nssoc_chip.mapped.json','shell.json')]:
            run=completed(rid,head);z,meta=archive(run,name+str(rid));assert meta['id']==aid and meta['digest']=='sha256:'+digest
            source=json.loads(z.read(folder+'result.json'));assert source['source_head']==head and source['sources_unchanged']
            for p,h in source['outputs'].items():assert hashlib.sha256(z.read(folder+p)).hexdigest()==h
            (OUT/target).write_bytes(z.read(folder+entry));sources.append(meta)
        script=ROOT/'scripts/audit_core_only_chip_clocks.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-placed.odb',OUT/'shell.json']};r['protected_inputs']=protected;r['source_artifacts']=sources
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_CLOCK_AUDIT_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'clock-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items());r.update(status=r['audit']['status'],sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
