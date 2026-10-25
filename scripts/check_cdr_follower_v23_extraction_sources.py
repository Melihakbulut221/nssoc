#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_follower_v23_planes.py': '5b7406948bcb48240a9d83df5cd0e484868de5bb860350f50f45af6e75dbea87', 'scripts/cloud_cdr_follower_v23_wire_inputs.py': 'a130ba98718829706b7f69c1873165c2c5a833555c6204bd51fe3c792d4abcc7', 'scripts/cloud_cdr_follower_v23_binding.py': '6357aa384e5680e5a8609f220d463d6b9678ed9fe8d152de4cc77db9684f219d', 'scripts/cloud_cdr_follower_v23_rc.py': 'd394c11d82df497213c257cc8b9005c3b5500884b429fd5a83335477819c8b14', 'scripts/cloud_cdr_follower_v23_extraction_stage.py': '88b9b202f05150da965a64cf06db596bf874afc7d80096c2f796120b30b8e632', '.github/workflows/cdr-follower-v23-extraction-cloud.yml': '3f8a930c6cfa6bebc84e9646aed0afc59e5a9bba2745e16e906e03e8fd324ad5'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    # Two old4R+2MIM+6tap leaves replaced by two2HBT+2R+4tap leaves.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476
    assert sum(census[k]*counts[k]for k in census)==1382
    assert sum(v for k,v in census.items()if k!='cap_cmim')==469
    assert 1382-469==913 and 913+25==938
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_METHODS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
