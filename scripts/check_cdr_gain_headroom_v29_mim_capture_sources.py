#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the actual v29 parent and unchanged native MIM capture equations/gates."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_gain_headroom_v29_extraction_sources import check as original_extraction
 original_extraction()
 pins=json.loads((ROOT/'scripts/cdr-gain-headroom-v29-mim-capture-pins.json').read_text())
 for name,digest in pins.items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
  if name.endswith('.py'):ast.parse(raw,filename=name)
 for suffix in ('mim_parent_rc','mim_capture_stage'):
  old=(ROOT/('scripts/cloud_cdr_input_loading_v28_'+suffix+'.py')).read_text()
  expected=old.replace('cdr-input-loading-v28','cdr-gain-headroom-v29').replace('cdr_input_loading_v28','cdr_gain_headroom_v29').replace('20261021','20261022')
  assert (ROOT/('scripts/cloud_cdr_gain_headroom_v29_'+suffix+'.py')).read_text()==expected,'Native MIM capture changed beyond provenance namespace'
 spec=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-mim-capture-input-20261022.json').read_text())
 assert spec==dict(run=39693048851,source_head='db62ee1056042d7531d068c09a62359afe8cdcde',
  workflow_path='.github/workflows/cdr-gain-headroom-v29-extraction-cloud.yml',
  stages=['planes','wire-inputs','binding','rc'],
  parent_summary_sha256='5e7ab07191831d3f378a7719d355cacc591f76553d5302ce10b53cad21788b6f')
 print('PASS_FROZEN_V29_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
