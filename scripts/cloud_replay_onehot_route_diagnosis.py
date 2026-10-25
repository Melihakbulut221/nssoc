#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inspect immutable timed-out DRT logs and saved-state inventory on hosted runner."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-replay-onehot-route-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        prior,proof=reports.restore_report('replay-onehot-detailed-route',39084569446,'4e123d6850814b2550feff017694fccc50bb003ba52d60b2e1e7af74965d8851','4e14a30146624ff06e2101eeaf87694b9429070af22562f1854a6fef85272f25',OUT/'source',['native.log', 'initial-state.json', 'trial-config.json', 'run/flow.log', 'run/resolved.json', 'run/error.log', 'run/warning.log', 'run/1-openroad-detailedrouting/openroad-detailedrouting.log', 'run/1-openroad-detailedrouting/clean_orphan_guides_drt.tcl', 'run/1-openroad-detailedrouting/state_in.json', 'run/1-openroad-detailedrouting/COMMANDS', 'run/1-openroad-detailedrouting/_env.tcl', 'run/1-openroad-detailedrouting/high-fanout.rpt', 'run/1-openroad-detailedrouting/propagated_native.tcl', 'run/1-openroad-detailedrouting/config.json', 'run/1-openroad-detailedrouting/drt-run-0/soc_top.drc-5.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-15.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-5.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-20.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-10.rpt', 'run/1-openroad-detailedrouting/drt-run-2/soc_top.drc-5.rpt'])
        assert prior['source_head']=='92c6161af3fbb040ce6433ccae32ee614e6db1ab'and prior['status']=='INTERRUPTED_NATIVE_STAGE_RETAINED_NOT_ACCEPTED'
        r['source']=proof;r['source_outputs']=prior['outputs'];r['texts']={n:(OUT/'source'/n).read_text(errors='replace')for n in ['native.log', 'initial-state.json', 'trial-config.json', 'run/flow.log', 'run/resolved.json', 'run/error.log', 'run/warning.log', 'run/1-openroad-detailedrouting/openroad-detailedrouting.log', 'run/1-openroad-detailedrouting/clean_orphan_guides_drt.tcl', 'run/1-openroad-detailedrouting/state_in.json', 'run/1-openroad-detailedrouting/COMMANDS', 'run/1-openroad-detailedrouting/_env.tcl', 'run/1-openroad-detailedrouting/high-fanout.rpt', 'run/1-openroad-detailedrouting/propagated_native.tcl', 'run/1-openroad-detailedrouting/config.json', 'run/1-openroad-detailedrouting/drt-run-0/soc_top.drc-5.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-15.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-5.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-20.rpt', 'run/1-openroad-detailedrouting/drt-run-1/soc_top.drc-10.rpt', 'run/1-openroad-detailedrouting/drt-run-2/soc_top.drc-5.rpt']}
        r['status']='COMPLETE_INTERRUPTED_NATIVE_ROUTE_DIAGNOSIS_NOT_ROUTING_ACCEPTANCE'
        for n,t in r['texts'].items():
            if n.endswith('.log'):print(n,t[-18000:],flush=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
