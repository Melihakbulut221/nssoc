#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual native DRC marker geometry from the rejected54device sampler."""
import collections,json,os,re,xml.etree.ElementTree as ET
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-parallel-drc-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-parallel-first-drc-rejection-20261018.json').read_text())
        paths=('layout/result.json','layout/schematic.cir','physical/drc/drc.lyrdb','physical/drc/deck.log','physical/drc/run.log')
        report,proof=reports.restore_report('cdr-sampler-parallel-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',paths)
        assert report==pin['report'] and report['source_head']==pin['source_head']
        measured=report['physical']['steps'][0]['measurement'];assert measured['status']=='FAIL'and measured['markers']==193 and measured['category_count']==560
        geometry=json.loads((OUT/'source/layout/result.json').read_text());path=OUT/'source/physical/drc/drc.lyrdb'
        assert sha(path)==measured['report_sha256']
        tree=ET.parse(path);items=[]
        for item in tree.getroot().findall('./items/item'):
            items.append(dict(category=item.findtext('category'),cell=item.findtext('cell'),multiplicity=item.findtext('multiplicity'),values=[v.text for v in item.findall('./values/value')]))
        counts=dict(collections.Counter(x['category']for x in items))
        result.update(original_source=proof,original_measurement=measured,marker_count=len(items),marker_categories=counts,markers=items,original_geometry=geometry,native_reference=(OUT/'source/layout/schematic.cir').read_text(),raw_native_report=path.read_text())
        assert len(items)==193 and counts==measured['categories'],(len(items),counts,measured['categories'])
        assert geometry['primitive_counts']==dict(hbt=16,nmos=9,rppd=12,physical_tap=17)
        result['status']='COMPLETE_ORIGINAL193_DRC_MARKERS_REPRODUCED_NOT_ACCEPTANCE'
        print(json.dumps(dict(categories=counts,cells=sorted({i['cell']for i in items}),examples={cat:[i for i in items if i['category']==cat][:3]for cat in counts}),indent=2),flush=True)
    except BaseException as error:result.update(status='FAIL_REVIEW',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
