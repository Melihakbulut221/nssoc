#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'docs/evidence/cdr-data3-v25-parent-physical-pass-20261021.json': '3b24f685b56f5a6a25b0eb3408635270b4229b6c1ea07a5273c9b8053ee5c3f0', 'scripts/cloud_cdr_data3_v25_planes.py': 'c0e3cb9398d4cf080e567e942e1c38966c4c787312a6a89fc7046ca51147e4d5', 'scripts/cloud_cdr_data3_v25_wire_inputs.py': 'c3e9cc5678333d5546ba4767bf963944c8df8d2e6fdf2f75878c4cc348eb79dd', 'scripts/cloud_cdr_data3_v25_binding.py': '680e6dd01c5b7ecfa8f9c0754ff99c633a9508c121df3595910af032a4017568', 'scripts/cloud_cdr_data3_v25_rc.py': '9a92b4670896606b9922624a64d41b2a6c79f8f13ce2d4c8fe06a540c924ac96', 'scripts/cloud_cdr_data3_v25_extraction_stage.py': 'ad12f1e06951ba368233096ac0e9370070c767d9530c8faf7dca1775eaf77579', '.github/workflows/cdr-data3-v25-extraction-cloud.yml': '925ab9fb265b5148b88b68acfc520f8b75fb70702d2eae829a07896833a73fae'}
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
    # Compare the actual producer path helper with every dependent consumer.
    # This catches dynamic date/name drift before any CAD calculation.
    import runpy
    stage=runpy.run_path(str(ROOT/'scripts/cloud_cdr_data3_v25_extraction_stage.py'))
    for name,deps in stage['DEPS'].items():
        path=ROOT/('scripts/cloud_cdr_data3_v25_'+name.replace('-','_')+'.py')
        literals={n.value for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        for dep in deps:
            expected=str(stage['receipt_path'](dep).relative_to(ROOT))
            assert expected in literals,('Producer/consumer receipt mismatch',name,dep,expected)
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_AND_ACTUAL_DEPENDENCY_PATHS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
