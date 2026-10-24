#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full-driver native metal/via inventory, prerequisite to actual wire RC."""
import json,os,sys
from pathlib import Path
import cloud_tx_input_driver_wide as physical
from cloud_tx_driver_wide_lef import SOURCE
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-wide-wires'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,wire_rc_extracted=False,qualified_pex=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert all(v['expected_verdict_observed'] for v in prior['steps'].values() if 'expected_verdict_observed' in v)
        spec=json.loads((ROOT/'docs/evidence/tx-driver-wide-wire-method-20261016.json').read_text())
        method=ROOT/'scripts/tx_driver_wide_wire_native.py';assert sha(method)==spec['adapted_sha256']
        native=OUT/'probe.py';native.write_bytes(method.read_bytes());r['method']=spec
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        r['execution']=execute([app,'python',native],OUT,'native');save()
        if r['execution']['returncode']:
            print((OUT/'native.log').read_text(errors='replace')[-14000:]);raise RuntimeError('Full driver native wire binding failed')
        r['geometry']=json.loads((OUT/'native01/result.json').read_text())
        assert r['geometry']['status']=='PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC'
        assert r['geometry']['native_device_count']==100 and len(r['geometry']['native_ports'])==6
        assert all(sha(source/p)==v for p,v in prior['outputs'].items())
        r['status']=r['geometry']['status']
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
