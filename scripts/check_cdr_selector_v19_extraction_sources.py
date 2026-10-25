#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind new physical selector source; retain original complete native extraction checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_bands_v18_extraction_sources import check as original
    original()
    delta=json.loads((ROOT/'scripts/cdr-selector-v19-extraction-source-delta.json').read_text())
    for d in delta['files']:
        text=(ROOT/d['baseline_path']).read_text()
        assert hashlib.sha256(text.encode()).hexdigest()==d['baseline_sha256']
        cursor=0;parts=[]
        for e in d['changes']:
            assert cursor<=e['start']<=e['end']<=len(text)
            parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
        parts.append(text[cursor:]);raw=(ROOT/d['candidate_path']).read_bytes()
        assert raw==''.join(parts).encode()and hashlib.sha256(raw).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-selector-v19-physical-pass-20261020.json').read_text())
    assert pin['run']==39394475994 and pin['source_head']=='5fabcec3577e00bafb6c7190f3a9c842cb18e074'
    assert pin['summary_sha256']=='8bd5a68094ea63cfab23f5e09b31e3ebeb1f8798f981458666507cad1d1b4361'and pin['parts_sha256']=='64cf69007de7189943fea190d65943908cc79655be954294ee320427abc6ac60'
    assert pin['report']['outputs']['layout/nssoc_cdr_pd484_localbus_v12.gds']=='247fd159b5a245c9dd8df13082cab62d4f185ea39102a62b9c4491ce230d999b'
    print('PASS_EXACT_V19_PHYSICAL_PARENT_AND_UNCHANGED_NATIVE_EXTRACTION_GATES')
if __name__=='__main__':check()
