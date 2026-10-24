#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the actual v30 parent and unchanged native MIM capture equations/gates."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_input_impedance_v30_extraction_sources import check as original_extraction
 original_extraction()
 pins=json.loads((ROOT/'scripts/cdr-input-impedance-v30-mim-capture-pins.json').read_text())
 for name,digest in pins.items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
  if name.endswith('.py'):ast.parse(raw,filename=name)
 for suffix in ('mim_parent_rc','mim_capture_stage'):
  old=(ROOT/('scripts/cloud_cdr_input_loading_v28_'+suffix+'.py')).read_text()
  expected=old.replace('cdr-input-loading-v28','cdr-input-impedance-v30').replace('cdr_input_loading_v28','cdr_input_impedance_v30').replace('20261021','20261022')
  assert (ROOT/('scripts/cloud_cdr_input_impedance_v30_'+suffix+'.py')).read_text()==expected,'Native MIM capture changed beyond provenance namespace'
 spec=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-mim-capture-input-20261022.json').read_text())
 assert spec==dict(run=39707446970,source_head='97c114638871b59de1cb6f0192391436ce9f5b01',
  workflow_path='.github/workflows/cdr-input-impedance-v30-extraction-cloud.yml',
  stages=['planes','wire-inputs','binding','rc'],
  parent_summary_sha256='c73830e98e87cbee1d1287c658dd29504e6a04275067b90bea7bd6dfbb4e9ae6')
 print('PASS_FROZEN_V30_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
