#!/usr/bin/env python3
"""Read-only coverage audit of authenticated nominal shell extraction."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-spef-coverage'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44295338338,'94bc6b6dec9615e25d39883916454d2dd4b40f7c');z,meta=archive(run,'core-only-chip-extraction-native-44295338338')
        assert meta['id']==14422128950 and meta['digest']=='sha256:3e115d0de651a784965fe8d8e0899ec1752a07f2096de6d22a4c9efea2c2c226'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['source_head']==run['head_sha']and source['spef_integrity']['inconsistent_nets']==0
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        for p in ['chip-detailedroute.odb','chip-shell.nom.spef']:(OUT/p).write_bytes(z.read(p))
        script=ROOT/'scripts/audit_core_only_chip_spef_coverage.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-detailedroute.odb',OUT/'chip-shell.nom.spef']};r.update(source_artifact=meta,protected_inputs=protected)
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_SPEF_COVERAGE_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
        r['audit']=json.loads((OUT/'coverage.json').read_text());assert all(sha(p)==h for p,h in protected.items())
        expected=sorted(x['net']for x in source['visible_geometry_audit']['unwired_multi_terminal_nets'])
        assert r['audit']['unwired_multiterminal_nets']==expected
        r.update(status='PARENT_SPEF_INVENTORY_AND_RESISTANCE_GRAPH_VERIFIED_REQUIRES_TIMING_AND_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
