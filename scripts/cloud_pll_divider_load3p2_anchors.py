#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore exact clock conductor graph and bind all physical terminal planes."""
import argparse,json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_clock_div4_load3p2_v1_layout'
SELECTED=('native01/wires.gds','native01/wires.l2n','native01/result.json','source/layout/'+TOP+'.gds','source/layout/result.json','raw_flat/result.lvsdb')

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';out=ROOT/'hw/soc/out/cloud-pll-divider-load3p2-anchors';out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,wire_rc_extracted=False,serial_phy_complete=False)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        wire=out/'wire'
        prior,proof=reports.restore_report('pll-divider-load3p2-wires',38969703944,'bb0702e7a831120c10d991f9e9630ef8ca59e43320d0f3b07937e37ceadb7eda','ffcd115646a32b245464d488c02bd694bdbb564264560e7fd2471c4edbb3e586',wire,SELECTED);r['source']=proof
        assert prior['status']=='PASS_DIVIDER3P2_RAW91_LVS_FAULTS_AND_METAL_GRAPH_NOT_TERMINAL_RC_OR_ELECTRICAL_ACCEPTANCE'and prior['source_unchanged']
        assert prior['source_head']=='f00759f466f08ed4d55ad940fa8252506b480237'
        pcell=out/'npn13G2_code.py'
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py','634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        r['execution']=execute([app,'python',ROOT/'scripts/pll_divider_load3p2_anchors_native.py',out],out,'anchors');save()
        assert r['execution']['returncode']==0,(out/'anchors.log').read_text()[-10000:]
        binding=json.loads((out/'anchors.json').read_text());assert binding['status']=='PASS_ALL283_DIVIDER_TERMINALS_BOUND_WITH198_METAL85_BODY_AND_SEVEN_FAULTS_NOT_RC_ACCEPTANCE'
        assert len(binding['negative_controls'])==7 and all(x['rejected']for x in binding['negative_controls'])
        assert all(sha(Path(p))==v for p,v in binding['inputs'].items())
        assert all(sha(wire/p)==prior['outputs'][p]for p in SELECTED)
        r.update(status=binding['status'],binding=binding,source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
