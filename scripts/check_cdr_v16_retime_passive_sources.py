#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_streamed_sources import check as source
    source()
    for p,h in json.loads((ROOT/'scripts/cdr-v16-retime-passive-source-pins.json').read_text())['files'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    print('PASS_CDR_V16_RETIME_NATIVE_GRAPH_AND_UNCHANGED_PASSIVE_SOLVER_SOURCES')
if __name__=='__main__':check()
