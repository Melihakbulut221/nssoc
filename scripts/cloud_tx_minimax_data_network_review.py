#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only data network diagnosis from immutable native wire model."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from review_tx_minimax_data_networks import inspect,controls
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-minimax-data-network-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        r['solver_controls']=controls()
        pin=json.loads((ROOT/'docs/evidence/tx-v5-minimax-wave-nominal-rejected-20261019.json').read_text())
        review_pin=json.loads((ROOT/'docs/evidence/tx-minimax-native-path-review-20261019.json').read_text())
        model_name='source/cloud-tx-v5-minimax-assembly/wire96/tree1674-wire01.spice'
        selected=['native/contract.json',model_name]
        prior,proof=reports.restore_report('tx-v5-minimax-wave-wire-nominal-none',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report'] and prior['source_unchanged'] and not prior['electrical_screen_passed']
        review=review_pin['report']
        assert review['original_gates_reproduced']and review['sources_unchanged']
        assert review['native_source']['summary_sha256']==pin['summary_sha256']
        assert review['original_signal_gate']==prior['review']['signals']
        assert review['original_interfaces']==prior['review']['interfaces']
        model=OUT/'source'/model_name
        assert sha(model)==prior['model_sha256']==review['native_clock_review']['model_sha256']
        contract=json.loads((OUT/'source/native/contract.json').read_text())
        assert contract['streams']==32 and len(contract['hbt'])==604 and len(contract['mos'])==512
        native=inspect(model,contract,review['physical_input_groups'])
        r.update(status='COMPLETE_NATIVE_TX_DATA_NETWORK_DIAGNOSIS_NOT_ACCEPTANCE',native=native,source=proof,
            original_signal_gate=review['original_signal_gate'],original_interfaces=review['original_interfaces'],
            original_gates_previously_reproduced=True,sources_unchanged=True,
            review_receipt_sha256=sha(ROOT/'docs/evidence/tx-minimax-native-path-review-20261019.json'))
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
