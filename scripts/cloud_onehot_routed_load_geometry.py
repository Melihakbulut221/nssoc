#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Locate long high-load native data connections before choosing a repair."""
import json,os,shutil,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from select_onehot_routed_loads import select,controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-routed-load-geometry'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-logic-resize-route-result-20261019.json').read_text())
        assert pin['run']==39202263552 and pin['source_head']=='84063da15c34482d07f05b7efae85a27d95ab52c'
        odbrel='run/2-openroad-detailedrouting/soc_top.odb'
        names=[odbrel]+[v['directory']+'/max.rpt'for v in pin['report']['measurements'].values()]
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert prior==pin['report']and prior['sources_unchanged']and prior['returncode']==0
        r['source']=proof;r['source_metrics']=prior['measurements'];r['selector_controls']=controls()
        targets={};counts={}
        for corner,metrics in prior['measurements'].items():
            rel=metrics['directory']+'/max.rpt'
            found=select((OUT/'source'/rel).read_text());assert found
            counts[corner]=dict(eligible=len(found),selected=min(32,len(found)),report_sha256=sha(OUT/'source'/rel))
            for row in found[:32]:
                key=row['instance']+'/'+row['pin']
                entry=targets.setdefault(key,{**row,'observations':[]})
                assert all(entry[k]==row[k]for k in ('instance','pin','master','reported_fanout'))
                entry['observations'] += [dict(corner=corner,**v)for v in row['observations']]
        selection=dict(targets=list(targets.values()),per_corner=counts,scope='Union of top32 measured weak data drivers per corner using unchanged source selector: negative setup paths, cap>=0.1pF, stage delay>=1ns. Diagnostic sample, not full violation census.')
        (OUT/'targets.json').write_text(json.dumps(selection,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        helper=ROOT/'scripts/inspect_onehot_routed_load_geometry.py'
        protected={str(p):sha(p)for p in [Path(__file__),helper,Path(__import__('select_onehot_routed_loads').__file__),app,OUT/'targets.json',*[OUT/'source'/n for n in names]]}
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        openroad=shutil.which('openroad');assert openroad
        with(OUT/'geometry.log').open('w')as log:
            code=subprocess.call([openroad,'-exit','-python',str(helper)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=code
        if code:print((OUT/'geometry.log').read_text()[-10000:],flush=True)
        assert code==0
        geometry=json.loads((OUT/'geometry.json').read_text())
        assert geometry['sources_unchanged']and geometry['selected_net_count']==len(targets)
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='COMPLETE_READ_ONLY_ROUTED_LOAD_GEOMETRY_NOT_REPAIR',selection=selection,geometry=geometry,protected_inputs=protected,sources_unchanged=True)
        # Exact source ODB remains in its immutable upstream release; avoid another
        # large duplicate in the diagnostic publication after byte checks pass.
        (OUT/'source'/odbrel).unlink()
        r['source_odb_retained_in_pinned_upstream_release']=True
    except BaseException as e:r.update(status='FAIL_NATIVE_GEOMETRY_DIAGNOSIS',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
