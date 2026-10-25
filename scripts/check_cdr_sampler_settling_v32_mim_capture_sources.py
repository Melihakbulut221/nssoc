#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the actual v32 parent and unchanged native MIM capture equations/gates."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_sampler_settling_v32_extraction_sources import check as original_extraction
 original_extraction()
 pins=json.loads((ROOT/'scripts/cdr-sampler-settling-v32-mim-capture-pins.json').read_text())
 for name,digest in pins.items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
  if name.endswith('.py'):ast.parse(raw,filename=name)
 for suffix in ('mim_parent_rc','mim_capture_stage'):
  old=(ROOT/('scripts/cloud_cdr_input_loading_v28_'+suffix+'.py')).read_text()
  expected=old.replace('cdr-input-loading-v28','cdr-sampler-settling-v32').replace('cdr_input_loading_v28','cdr_sampler_settling_v32').replace('20261021','20261022')
  assert (ROOT/('scripts/cloud_cdr_sampler_settling_v32_'+suffix+'.py')).read_text()==expected,'Native MIM capture changed beyond provenance namespace'
 spec=json.loads((ROOT/'docs/evidence/cdr-sampler-settling-v32-mim-capture-input-20261022.json').read_text())
 assert spec==dict(run=39740697762,source_head='2247a00db1e2e5111556e280837983b3c9c3afa4',
  workflow_path='.github/workflows/cdr-sampler-settling-v32-extraction-cloud.yml',
  stages=['planes','wire-inputs','binding','rc'],
  parent_summary_sha256='946587a69d7843b31025493531a10f1bfad2454029fe91df703cb0967ea71ae1')
 print('PASS_FROZEN_V32_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
