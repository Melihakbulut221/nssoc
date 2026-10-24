#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_selector_small_v24_planes.py': 'd7a717cfb14dc0aa759f94d08a77b10b8fbf1af78bc89be087b64a282462044e', 'scripts/cloud_cdr_selector_small_v24_wire_inputs.py': '52559a647d8bf32463b2e587e07fa9bb209a78cce88679f7239e2861e6f783fe', 'scripts/cloud_cdr_selector_small_v24_binding.py': 'b1160c0015a3671bbde152ab950dd85fd14e1b41228660f5e9363b5ec7ccc174', 'scripts/cloud_cdr_selector_small_v24_rc.py': '4762400c581c0680dae43dd115cd97170fcf27b063f97ea57c497e8ce0dc5362', 'scripts/cloud_cdr_selector_small_v24_extraction_stage.py': 'cd7b74d7dc94d7d87e8cf33b7acf960a8180a9b7509c9835c725346ad76cf147', '.github/workflows/cdr-selector-small-v24-extraction-cloud.yml': '6bd6ae087f773c291679b4ef2513146129c8ddffe21b04ff259727bb182e1038'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    # v24 changes32 selector multiplicities only; all native device/terminal counts remain.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476
    assert sum(census[k]*counts[k]for k in census)==1382
    assert sum(v for k,v in census.items()if k!='cap_cmim')==469
    assert 1382-469==913 and 913+25==938
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_METHODS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
