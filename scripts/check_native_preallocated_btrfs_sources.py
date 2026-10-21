#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    import runpy
    runpy.run_path(str(ROOT/'scripts/check_native_btrfs_sources.py'),run_name='__main__')
    m=json.loads((ROOT/'scripts/native-preallocated-btrfs-source-delta.json').read_text())
    for p,h in {**m['current_files'],**m['unchanged_files']}.items():
        data=(ROOT/p).read_bytes();assert hashlib.sha256(data).hexdigest()==h,p
        if p.endswith('.py'):ast.parse(data,filename=p)
    d=m['controller'];raw=(ROOT/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for e in d['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    assert text==(ROOT/d['candidate_path']).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==d['candidate_sha256']
    from cloud_pll845_preallocated_storage import controls
    result=controls();assert len(result['rejected'])==4
    assert result['independent_inside_and_outside_reserves']
    print('PASS_PRE_DOWNLOAD_STORAGE_DELTA_ORIGINAL_NATIVE_GATES_AND_INDEPENDENT_CAPACITY_CONTROLS')
if __name__=='__main__':check()
