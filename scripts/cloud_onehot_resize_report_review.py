#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read saved route reports after an antenna count consistency rejection."""
import json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-resize-report-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-resize-route-report-rejection-20261019.json').read_text())
        selected=[n for n in pin['report']['outputs']if n.startswith('run/')and (n.endswith('state_out.json')or n.endswith('antenna.rpt')or n.endswith('native-spef-integrity.json')or n.endswith('native-sta-script-proof.json')or n.endswith('ws.max.rpt')or n.endswith('ws.min.rpt')or n.endswith('sta.log')or n.endswith('unpropagated.rpt'))]
        assert len(selected)>=20
        source=OUT/'source'
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert prior==pin['report']and prior['returncode']==0 and prior['error']=='AssertionError()'
        r['source']=proof
        antenna=json.loads((source/'run/3-openroad-checkantennas/state_out.json').read_text())
        text=(source/'run/3-openroad-checkantennas/reports/antenna.rpt').read_text()
        nets=re.findall(r'(?m)^\s*Net:\s*(\S+)',text)
        r['antenna']=dict(original_report_text=text,original_report_sha256=sha(source/'run/3-openroad-checkantennas/reports/antenna.rpt'),net_heading_count=len(nets),unique_net_heading_count=len(set(nets)),net_headings=nets,metrics={k:v for k,v in antenna['metrics'].items()if 'antenna'in k},original_count_assertion_holds=len(nets)==antenna['metrics']['route__antenna_violation__count'])
        physical=json.loads((source/'run/4-odb-reportdisconnectedpins/state_out.json').read_text())
        r['physical_metrics']={k:v for k,v in physical['metrics'].items()if any(x in k for x in ['route__drc','disconnected','antenna'])}
        r['spef_integrity']=json.loads((source/'run/5-nssoc-onehotroutercx/native-spef-integrity.json').read_text())
        sta=source/'run/6-nssoc-onehotroutedsta'
        r['sta_script_proof']=json.loads((sta/'native-sta-script-proof.json').read_text())
        state=json.loads((sta/'state_out.json').read_text());r['corners']={}
        for corner in ['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']:
            folder=sta/corner
            r['corners'][corner]=dict(metrics={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)},unpropagated_text=(folder/'unpropagated.rpt').read_text(),original_clock_propagation_marker='NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in(folder/'sta.log').read_text(),worst_setup_text=(folder/'ws.max.rpt').read_text(),worst_hold_text=(folder/'ws.min.rpt').read_text())
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)
        r.update(status='COMPLETE_SAVED_NATIVE_ROUTE_REPORT_DIAGNOSIS_NOT_SIGNOFF',sources_unchanged=True,scope='Read-only native evidence. Original antenna consistency rejection retained. No routing restart, corrected counts, relaxed gates or timing acceptance.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
