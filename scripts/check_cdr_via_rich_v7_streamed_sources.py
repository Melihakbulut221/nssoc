#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_via_rich_v7_loaded_sources import check as prior
    prior()
    d=json.loads((ROOT/'scripts/cdr-via-rich-v7-streamed-source-delta.json').read_text())
    for p,h in d['unchanged_dependencies'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for f in d['files']:
        raw=(ROOT/f['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['baseline_sha256'];s=raw.decode()
        for e in f['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/f['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==f['candidate_sha256']
    tp=json.loads((ROOT/'docs/evidence/cdr-via-rich-stream-transport-pass-20261019.json').read_text())
    proof=tp['report'];assert proof['status']=='PASS_FULL_CDR_MODEL_ALL_VECTOR_3NS_STREAM_TRANSPORT_REQUIRES_FULL_LOADED_SCREEN'and proof['sources_unchanged']
    assert proof['save_command_repair']['helper_sha256']==d['unchanged_dependencies']['scripts/run_cloud_tx_mux4.py']
    assert proof['stream_capture']['columns']==1108 and proof['transport_comparison']['vectors']==1107 and len(proof['transport_controls'])==2
    failed=json.loads((ROOT/'docs/evidence/cdr-via-rich-v7-loaded-memory-rejection-20261018.json').read_text())
    composition=json.loads((ROOT/'docs/evidence/cdr-via-rich-v7-mim-composition-pass-20261018.json').read_text())
    assert proof['failed_source']['summary_sha256']==failed['summary_sha256']
    assert failed['report']['composition_source']['summary_sha256']==composition['summary_sha256']
    print('PASS_EXACT_LOSSLESS_SAVE_AND_STREAM_ADAPTATION_ORIGINAL_FULL_WAVE_GATES_RETAINED')
if __name__=='__main__':check()
