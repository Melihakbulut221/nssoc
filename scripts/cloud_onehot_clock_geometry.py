#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read original and candidate clock geometry and exported nominal RC in cloud."""
import json,os,shutil,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from bootstrap_flow import verify
from route_cloud_newer_postcts import sha
from inspect_onehot_clock_spef import parse,review,controls
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-geometry'
ODB='run/2-openroad-detailedrouting/soc_top.odb'
SPEF='run/5-nssoc-onehotroutercx/nom/soc_top.nom.spef'
PINS={
 'before':dict(group='onehot-critical-data-route',run=39293720171,
  summary='206246763d36b45f2d6ab03ec9b4a022531dd3233db4a1530af32c51b8bdbfea',
  parts='47093e5e6e4dbf9df7809a75a803b69552a3784af6ecb68fb54ef4c408cacff2',
  odb_sha256='782c6fb2990e35dd422f817eaab7a5aa7a98bab35b8da1ee2c15dcc2f8bc3d90'),
 'after':dict(group='onehot-coverage-data-route',run=39331918238,
  summary='6f3041930535ac4aba84e79cd5cc20b17b341cd7d02d13760d10d85f6bf11498',
  parts='8c13d94a7e70f1470145103d3e1047372ba3fc9da89fa21324f4a21252019a80',
  odb_sha256='dcc0170a01f70c131b99fba6484df16d3ca4e042c2ef17f4dfe0fa30e8aaea26')}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,
       scope='Read-only paired native routed clock geometry and nominal exported SPEF, not qualified PEX or repair.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['identifier_controls']=controls()
        sources={};protected={}
        for tag,pin in PINS.items():
            source,proof=reports.restore_report(pin['group'],pin['run'],pin['summary'],pin['parts'],OUT/tag,[ODB,SPEF])
            assert source['sources_unchanged']and source['detailed_route_complete']and source['returncode']==0
            assert source['native_routing_drc_errors']==0 and source['critical_disconnected_pins']==0
            assert sha(OUT/tag/ODB)==pin['odb_sha256']==source['routed_odb_sha256']
            assert sha(OUT/tag/SPEF)==source['outputs'][SPEF]
            sources[tag]=dict(**pin,spef_sha256=sha(OUT/tag/SPEF),restore_proof=proof)
            for name in (ODB,SPEF):protected[str(OUT/tag/name)]=sha(OUT/tag/name)
        (OUT/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        exe=shutil.which('openroad');assert exe
        helper=ROOT/'scripts/inspect_onehot_clock_geometry.py'
        for p in (Path(__file__),helper,ROOT/'scripts/inspect_onehot_clock_spef.py',OUT/'sources.json'):protected[str(p)]=sha(p)
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        with(OUT/'native-clock-geometry.log').open('w')as f:
            code=subprocess.call([exe,'-exit','-python',str(helper)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        if code:print((OUT/'native-clock-geometry.log').read_text()[-10000:],flush=True)
        assert code==0
        geometry=json.loads((OUT/'native-geometry.json').read_text())
        r.update(native_openroad_sha256=sha(Path(exe)),sources=sources,geometry=geometry,rc={});save()
        for tag in PINS:
            nets=geometry['sources'][tag]['nets'];wanted=[n['net']for n in nets]
            actual=parse(OUT/tag/SPEF,wanted)
            r['rc'][tag]={n['net']:review(actual[n['net']],n)for n in nets};save()
        comparison=[]
        for name,a in r['rc']['before'].items():
            b=r['rc']['after'][name]
            assert set(a['lowest_series_resistance_path_ohm'])<=set(b['lowest_series_resistance_path_ohm'])
            comparison.append(dict(net=name,driver=a['driver'],wire_cap_pf_before=a['declared_wire_cap_pf'],
               wire_cap_pf_after=b['declared_wire_cap_pf'],
               original_sink_series_r=[dict(sink=k,before_ohm=v,after_ohm=b['lowest_series_resistance_path_ohm'][k])
                 for k,v in a['lowest_series_resistance_path_ohm'].items()]))
        assert all(sha(Path(p))==v for p,v in protected.items())
        r.update(status='PASS_NATIVE_PAIRED_CLOCK_GEOMETRY_AND_NOMINAL_RC_NOT_REPAIR',comparison=comparison,sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
