#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud qualification of exact reader integration; no native activation."""
import json,os
from pathlib import Path
import cloud_pll845_allcolumn_disk as adapter
import cloud_pll845_allcolumn_acquisition as controller
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll845-reader-migration'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir()
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_performed=False,full_phy_accepted=False,full_capture_accepted=False,storage_capacity_fixed=False)
 try:
  m,current=adapter.source_contract(ROOT)
  assert controller.method_hashes()==current
  r['method_controls']=adapter.controls()
  contract=adapter.load_contract(ROOT)
  assert adapter.load_contract(ROOT,contract['required_vectors'])==contract
  try:adapter.load_contract(ROOT,contract['required_vectors'][:-1])
  except AssertionError:r['missing_prepared_vector_rejected']=True
  else:raise AssertionError('Missing prepared vector accepted')
  r['original_controller_controls']=controller.controls()
  r['status']='PASS_EXACT_PLL_READER_ONLY_CONTROLLER_MIGRATION_ORIGINAL_NATIVE_AND_ACQUISITION_METHODS_RETAINED_NO_RESUME'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
