#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure separate static-reader capacity; never restore or modify a native solver."""
import hashlib,json,os,shutil
from pathlib import Path
import cloud_pll_storage_headroom as inventory
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-reader-host-capacity'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert not (ROOT/'hw').exists()and not (ROOT/'docs').exists(),'This static-reader capacity probe requires scripts-only checkout'
 pins=json.loads((ROOT/'scripts/pll845-sparse-reader-pins.json').read_text())
 # This checkout deliberately has only source scripts, not CAD or raw assets.
 for p,h in pins.items():assert sha(ROOT/p)==h
 inventory.OUT=ROOT/'cloud-static-reader-headroom';inventory.main()
 observed=json.loads((inventory.OUT/'result.json').read_text())
 assert observed['protected_executables_unchanged']and not observed['native_activation']
 OUT.mkdir(exist_ok=False)
 free=shutil.disk_usage(ROOT).free
 guard=4*1024**3
 # This is a static reader-only reserve; all native/checkpoint reserves stay
 # unchanged in the preserved native controller and are reported separately.
 maximum=(max(0,free-guard-reader_header_allowance())//(5106*8))
 r=dict(status='MEASURED_SEPARATE_STATIC_READER_CAPACITY_NOT_NATIVE_OR_FULL_CAPTURE_PROOF',
  source_head=os.environ['GITHUB_SHA'],free_bytes=free,static_reader_minimum_free_bytes=guard,
  native_reserves_unchanged=observed['original_reserves_retained'],
  maximum_raw_bytes_with_static_reserve=max(0,free-guard),header_allowance_bytes=reader_header_allowance(),
  maximum5106_column_rows_with_static_reserve=maximum,
  original_full_duration_minimum_rows=3200001,
  fits_minimum_only=maximum>3200000,
  exact_completed_raw_size_must_be_checked_before_download=True,
  simultaneous_native_solver_allowed=False,full_capture_accepted=False,full_phy_accepted=False,
  live_native_process_changed=False,source_inventory_sha256=sha(inventory.OUT/'result.json'),
  source_inventory=observed)
 (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items()if not isinstance(v,dict)}))
def reader_header_allowance():return 2*1024**2
if __name__=='__main__':main()
