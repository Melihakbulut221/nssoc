#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind all38 actual TX output14 terminals to distinct native physical references."""
import json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-anchors'
TOP='nssoc_tx_cml_layout'
SELECTED=('native01/wires.gds','native01/wires.l2n','native01/result.json','source/layout/'+TOP+'.gds','source/layout/result.json','source/layout/schematic.cir','source/check/lvs_flat/result.lvsdb','source/check/lvs_flat/audit.json','source/check/lvs/result.lvsdb')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,wire_rc_extracted=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output14-wires-pass-20261021.json').read_text())
        assert pin['run']==39565287494 and pin['summary_sha256']=='098702e940393922124420146bc54cf0a19d022856c986deed83562a2bae608c'
        prior,proof=reports.restore_report('tx-output14-wires',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'wire',SELECTED)
        assert prior==pin['report']and prior['sources_unchanged']
        assert prior['status']=='PASS_ACTUAL_TX_OUTPUT14_WIRE_GRAPH_NINE_COMPONENTS_REQUIRES_TERMINAL_PLANES_RC_AND_PARENT_ROUTE'
        r['source']=proof
        m=json.loads((ROOT/'scripts/tx-output14-anchors-source-delta.json').read_text())
        baseline=ROOT/m['baseline'];candidate=ROOT/m['candidate']
        assert sha(baseline)==m['baseline_sha256']and sha(candidate)==m['candidate_sha256']
        text=baseline.read_text();pieces=[];cursor=0
        for e in m['changes']:
            assert cursor<=e['start']<=e['end']<=len(text)
            pieces.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
        pieces.append(text[cursor:]);assert candidate.read_text()==''.join(pieces)
        pcell=OUT/'npn13G2_code.py'
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py','634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        r['execution']=execute([app,'python',candidate,OUT],OUT,'anchors');save()
        assert r['execution']['returncode']==0,(OUT/'anchors.log').read_text()[-12000:]
        binding=json.loads((OUT/'anchors.json').read_text());r['binding']=binding;save()
        assert binding['status']=='PASS_ALL38_TX_OUTPUT_TERMINALS_BOUND_WITH24_METAL14_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert binding['counts']==dict(devices=14,terminals=38,metal_terminals=24,body_terminals=14,public_ports=8,unique_reference_planes=32,wire_components=9)
        assert len(binding['negative_controls'])==6 and all(x['rejected']for x in binding['negative_controls'])
        assert all(sha(Path(p))==v for p,v in binding['inputs'].items())
        assert all(sha(OUT/'wire'/p)==prior['outputs'][p]for p in SELECTED)
        assert sha(baseline)==m['baseline_sha256']and sha(candidate)==m['candidate_sha256']
        r.update(status=binding['status'],sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
