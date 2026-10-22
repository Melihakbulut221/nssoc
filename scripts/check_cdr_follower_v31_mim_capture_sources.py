#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the actual v31 parent and unchanged native MIM capture equations/gates."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_follower_v31_extraction_sources import check as original_extraction
 original_extraction()
 pins=json.loads((ROOT/'scripts/cdr-follower-v31-mim-capture-pins.json').read_text())
 for name,digest in pins.items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
  if name.endswith('.py'):ast.parse(raw,filename=name)
 for suffix in ('mim_parent_rc','mim_capture_stage'):
  old=(ROOT/('scripts/cloud_cdr_input_loading_v28_'+suffix+'.py')).read_text()
  expected=old.replace('cdr-input-loading-v28','cdr-follower-v31').replace('cdr_input_loading_v28','cdr_follower_v31').replace('20261021','20261022')
  assert (ROOT/('scripts/cloud_cdr_follower_v31_'+suffix+'.py')).read_text()==expected,'Native MIM capture changed beyond provenance namespace'
 spec=json.loads((ROOT/'docs/evidence/cdr-follower-v31-mim-capture-input-20261022.json').read_text())
 assert spec==dict(run=39720055542,source_head='462b8a4ac896fc26626787c7c0010e3595a6dae3',
  workflow_path='.github/workflows/cdr-follower-v31-extraction-cloud.yml',
  stages=['planes','wire-inputs','binding','rc'],
  parent_summary_sha256='e197afa755eda54ab91f8153ab786eb0b2e5f559f73a7871c7ee7f099aa2545f')
 print('PASS_FROZEN_V31_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
