#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,json
from pathlib import Path
from cloud_pll_rhi120_c8_sparse_resume import source_contract
root=Path(__file__).resolve().parents[1]
manifest,methods=source_contract(root)
for p in manifest['current_files']:
    if p.endswith('.py'):ast.parse((root/p).read_text(),filename=p)
print(json.dumps(dict(status='PASS_EXACT_RHI120_SPARSE_SOURCE_DELTA_NOT_NATIVE_RESUME',methods=methods)))
