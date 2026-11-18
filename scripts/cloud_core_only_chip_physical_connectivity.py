#!/usr/bin/env python3
"""Read-only physical geometry audit of the exact routed candidate."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,api,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-physical-connectivity'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_gds_lvs=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=api('actions/runs/44289826075');assert run['head_sha']=='723fe02e71279036fabb7a5d7204d309351f4e19'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
        z,meta=archive(run,'core-only-chip-detailedroute-native-44289826075');assert meta['id']==14420727343 and meta['digest']=='sha256:10a4fc032d2da17bf3dc2e59418905b3e9c38bd8f30e7c0e2e88163aeb3a2920'
        source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['source_head']==run['head_sha']and source['native_drc_count']==0
        assert source['error']=="AssertionError('Guided nets without native wire remain')"
        assert source['audit']['placements_connections_pin_shapes_and_power_geometry_unchanged']and len(source['audit']['unwired_guided_nets'])==76
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        assert z.read('route-drc.rpt')==b''
        (OUT/'chip-detailedroute.odb').write_bytes(z.read('chip-detailedroute.odb'));r['source_artifact']=meta;r['native_drc_count']=0;r['original_unwired_guided_nets']=source['audit']['unwired_guided_nets']
        script=ROOT/'scripts/audit_native_signal_geometry.py';protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'chip-detailedroute.odb']};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(OUT),NSSOC_PHYSICAL_ROUTE_ODB=str(OUT/'chip-detailedroute.odb')),stdout=log,stderr=subprocess.STDOUT,check=True)
        a=json.loads((OUT/'physical-route-audit.json').read_text());r['audit']=a
        assert not a['signal_nets_with_disconnected_geometry']and not a['terminals_without_geometry']and a['inter_net_contact_pairs']==0
        assert sorted(x['net']for x in a['unwired_multi_terminal_nets'])==sorted(r['original_unwired_guided_nets'])
        assert all(x['components']==1 and x['terminals']==2 for x in a['unwired_multi_terminal_nets'])
        assert all(sha(p)==h for p,h in protected.items());r.update(status='ROUTED_SIGNAL_GEOMETRY_CONNECTED_WITH_COINCIDENT_PAD_TERMINALS_REQUIRES_FULL_GDS_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
