#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'docs/evidence/cdr-data3-v25-parent-physical-pass-20261021.json': '3b24f685b56f5a6a25b0eb3408635270b4229b6c1ea07a5273c9b8053ee5c3f0', 'scripts/cloud_cdr_data3_v25_planes.py': 'c0e3cb9398d4cf080e567e942e1c38966c4c787312a6a89fc7046ca51147e4d5', 'scripts/cloud_cdr_data3_v25_wire_inputs.py': 'c3e9cc5678333d5546ba4767bf963944c8df8d2e6fdf2f75878c4cc348eb79dd', 'scripts/cloud_cdr_data3_v25_binding.py': '680e6dd01c5b7ecfa8f9c0754ff99c633a9508c121df3595910af032a4017568', 'scripts/cloud_cdr_data3_v25_rc.py': '9a92b4670896606b9922624a64d41b2a6c79f8f13ce2d4c8fe06a540c924ac96', 'scripts/cloud_cdr_data3_v25_extraction_stage.py': '18cbde8b28db313aca72928d11c7878df919c5f8abc06b291210f69f570ad25e', '.github/workflows/cdr-data3-v25-extraction-cloud.yml': '0efe44dcaa54ee4c65befb9f2f96f6130668bb7cde4843f19e012ed6c55b382d'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    # v25 changes32 data/hold multiplicities only; all native device/terminal counts remain.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476
    assert sum(census[k]*counts[k]for k in census)==1382
    assert sum(v for k,v in census.items()if k!='cap_cmim')==469
    assert 1382-469==913 and 913+25==938
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_METHODS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
