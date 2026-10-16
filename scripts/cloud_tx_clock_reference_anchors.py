#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore exact clock conductor graph and bind all physical terminal planes."""
import argparse,json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_tx_clock_reference_lef import TOP
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'l6p2':dict(summary='6cd0e1373c0cefaa2ca13dbfd81f258627212384b81d7c944c1a5886edcec964',parts='eff6d88b35e8eb300b8bb18cc7c097496912a6ea2afa2eb8ac47cbb7bba1bf69'),
 'l6p5':dict(summary='0053e77e0a5514901175a1cd2464038fc58b8bce0abd5ecc7204a74f27ab2997',parts='4d6a436f6cc754694ab4f4622906dad71ddc067639a44cf7697b3282244b08e5')}
SELECTED=('native01/wires.gds','native01/wires.l2n','native01/result.json','source/layout/'+TOP+'.gds','source/layout/result.json','source/check/lvs_flat/result.lvsdb')
SOURCES['l5p7']=dict(run=38961605786,head='9f940898df74a063c5f703acb67f6927182ab6c4',summary='fdec668ae9d829ef75f94d22fddf84dc2bf7a5d4a24bb1e9ac0531d9337dbbc0',parts='2b45dd68de63bc0f06f303501b8a02710889f418a36511d1020f2fb4b2c6143a')

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=sorted(SOURCES),required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';out=ROOT/('hw/soc/out/cloud-tx-clock-reference-anchors-'+args.variant);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,qualified_pex=False,wire_rc_extracted=False,serial_phy_complete=False)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        spec=SOURCES[args.variant];wire=out/'wire';prior,proof=reports.restore_report('tx-clock-reference-wires-'+args.variant,spec.get('run',38946981718),spec['summary'],spec['parts'],wire,SELECTED);r['source']=proof
        assert prior['status']=='PASS_ACTUAL_CLOCK6_WIRE_GRAPH_FIVE_COMPONENTS_NOT_TERMINAL_RC_OR_ELECTRICAL_ACCEPTANCE'and prior['source_unchanged']
        assert prior['source_head']==spec.get('head','66e9bf5fd12499c2b0e03a7a3854071e41dae4f5')and prior['variant']==args.variant
        pcell=out/'npn13G2_code.py'
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py','634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        r['execution']=execute([app,'python',ROOT/'scripts/tx_clock_reference_anchors_native.py',out],out,'anchors');save()
        assert r['execution']['returncode']==0,(out/'anchors.log').read_text()[-10000:]
        binding=json.loads((out/'anchors.json').read_text());assert binding['status']=='PASS_ALL16_CLOCK_TERMINALS_BOUND_WITH10_METAL6_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert len(binding['negative_controls'])==6 and all(x['rejected']for x in binding['negative_controls'])
        assert all(sha(Path(p))==v for p,v in binding['inputs'].items())
        assert all(sha(wire/p)==prior['outputs'][p]for p in SELECTED)
        r.update(status=binding['status'],binding=binding,source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
