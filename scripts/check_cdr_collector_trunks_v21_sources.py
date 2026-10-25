#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze native gates and the exact collector-routing candidate."""
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/check_cdr_data_v20_parent_sources.py'),run_name='__main__')
m=json.loads((root/'scripts/cdr-collector-trunks-v21-source-pins.json').read_text())
for path,digest in m['protected'].items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
assert m['baseline_run']==39420628714 and m['passive_measurement_run']==39432130535
print('PASS_FROZEN_V20_NATIVE_GATES_AND_EXPLICIT_FOUR_COLLECTOR_TRUNK_ROUTING_CANDIDATE')
