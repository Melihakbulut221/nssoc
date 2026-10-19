#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Summarize the already measured native clock report, entirely in cloud."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-minimax-clock-summary'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-minimax-native-path-review-20261019.json').read_text())
        names=['native-clock-terminals.json']
        prior,proof=reports.restore_report('tx-v5-minimax-path-review',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert prior==pin['report']and prior['sources_unchanged']and prior['original_gates_reproduced']
        path=OUT/'source/native-clock-terminals.json'
        assert sha(path)==prior['outputs'][names[0]]==prior['native_clock_review']['report_sha256']
        clock=json.loads(path.read_text())
        assert clock['status']=='COMPLETE_ACTUAL31_CLOCKS_124_NATIVE_SELECTOR_BASES_READ_ONLY'
        assert clock['model_sha256']==prior['native_clock_review']['model_sha256']
        rows=[]
        for item in clock['clocks']:
            intervals=[];missing_native=missing_public=0;counts=[]
            for pair in item['terminal_pairs']:
                for edges in pair['event_brackets']:
                    intervals += [e['delay_interval_ps']for e in edges['matched']]
                    missing_native += len(edges['unmatched_native']);missing_public += edges['unmatched_public']
                    counts.append(dict(polarity=edges['polarity'],public=edges['public_edges'],native=edges['native_edges'],matched=len(edges['matched'])))
            assert intervals
            lo=min(x[0]for x in intervals);hi=max(x[1]for x in intervals)
            low_cm=min(p['native_commonmode_range_v'][0]for p in item['terminal_pairs'])
            high_cm=max(p['native_commonmode_range_v'][1]for p in item['terminal_pairs'])
            rows.append(dict(clock=item['clock'],delay_envelope_ps=[lo,hi],
                unmatched_native_edges=missing_native,unmatched_public_edges=missing_public,
                edge_counts=counts,commonmode_envelope_v=[low_cm,high_cm],
                native_differential_envelopes_v=[p['native_diff_range_v']for p in item['terminal_pairs']],
                wire_components=item['wire_components']))
        assert len(rows)==31
        assert sha(path)==prior['outputs'][names[0]]
        r.update(status='COMPLETE_NATIVE31_CLOCK_DELAY_AND_WIRE_LOADING_SUMMARY_NOT_ACCEPTANCE',
            source=proof,original_gates_reproduced=True,sources_unchanged=True,
            clocks=rows,raw_clock_report=clock,
            meaning='Envelope includes every paired native edge bracket; nearest same-polarity association is diagnostic, not acceptance or proof of causal delay. Missing edges remain explicit. Wire C excludes intrinsic/RF/body models.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
