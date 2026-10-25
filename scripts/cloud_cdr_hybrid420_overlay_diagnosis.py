#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact failed native markers in cloud; no replacement geometry or verdict."""
import hashlib,json,os,xml.etree.ElementTree as ET
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-cdr-hybrid420-overlay-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    pin=json.loads((ROOT/'docs/evidence/cdr-hybrid420-parent-overlay-rejection-20261018.json').read_text())
    old,proof=reports.restore_report('cdr-retimed-hybrid-v2-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',['physical/drc/drc.lyrdb','layout/result.json'])
    assert old==pin['report']and old['physical']['steps']['drc']['measurement']['markers']==4
    p=OUT/'source/physical/drc/drc.lyrdb';assert sha(p)==old['physical']['steps']['drc']['measurement']['report_sha256']
    tree=ET.parse(p);items=[ET.tostring(x,encoding='unicode')for x in tree.findall('.//items/item')];assert len(items)==4
    layout=json.loads((OUT/'source/layout/result.json').read_text());assert layout==old['layout']
    result=dict(status='COMPLETE_EXACT_FAILED_MARKER_READBACK_NOT_PHYSICAL_ACCEPTANCE',source_head=os.environ['GITHUB_SHA'],source=proof,accepted=False,full_phy_accepted=False,markers=items,measurement=old['physical']['steps']['drc']['measurement'],placements=layout['placements'],supply_overlay=layout['supply_overlay'])
    result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()};(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],markers=items)))
if __name__=='__main__':main()
