#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read the immutable failed hybrid native LVS evidence on a hosted runner."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-hybrid-lvs-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        wanted=('physical/lvs/extracted.cir','layout/schematic.cir','physical/lvs/deck.log','physical/lvs/result.lvsdb','physical/lvs/audit.json')
        prior,proof=reports.restore_report('cdr-sampler-hybrid-physical',39105690621,'f63e4c585aac47d158729a0d538b561def1197e099d00d9aaf186b1091256121','0e50c50ded8cc5b5af22905f5bcef5d33b92d22772acadd96353e842bd29dab4',OUT/'source',wanted)
        assert prior['source_head']=='4bcb050c4d13a9f20eb3d8b87269f5faae7166f2' and prior['status']=='FAIL_OR_ERROR'
        assert prior['physical']['steps'][0]['measurement']['markers']==0
        assert prior['physical']['steps'][-1]['audit']['status']=='FAIL'
        result['source']=proof;result['texts']={n:(OUT/'source'/n).read_text()for n in wanted}
        result['status']='COMPLETE_NATIVE_LVS_EVIDENCE_READING_NOT_REPAIR'
        print(json.dumps(result['texts'],indent=2),flush=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
