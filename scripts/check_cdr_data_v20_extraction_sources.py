#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind new physical data/hold source; retain original complete native extraction checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_v19_extraction_sources import check as original
    original()
    delta=json.loads((ROOT/'scripts/cdr-data-v20-extraction-source-delta.json').read_text())
    for d in delta['files']:
        text=(ROOT/d['baseline_path']).read_text()
        assert hashlib.sha256(text.encode()).hexdigest()==d['baseline_sha256']
        cursor=0;parts=[]
        for e in d['changes']:
            assert cursor<=e['start']<=e['end']<=len(text)
            parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
        parts.append(text[cursor:]);raw=(ROOT/d['candidate_path']).read_bytes()
        assert raw==''.join(parts).encode()and hashlib.sha256(raw).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-data-v20-parent-physical-pass-20261020.json').read_text())
    assert pin['run']==39420628714 and pin['source_head']=='87b35ff5bc80630cb4ad4614bd644ed37d5e77e8'
    assert pin['summary_sha256']=='e00f439f650c884950ccc232bca90a26958cce39e93606316834a991e945e463'and pin['parts_sha256']=='7bf653c3d1a370acb7c34704423e60277261e29c68919579976ff37518d1cd78'
    assert pin['report']['outputs']['layout/nssoc_cdr_pd484_localbus_v12.gds']=='56733ea37cc7dc7fc6e8b2180d122511cfddd4a3bc9e1917a8f280f0d7604636'
    print('PASS_EXACT_V20_PHYSICAL_PARENT_AND_UNCHANGED_NATIVE_EXTRACTION_GATES')
if __name__=='__main__':check()
