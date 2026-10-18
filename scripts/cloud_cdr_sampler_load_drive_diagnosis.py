#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read original failed native startup logs, no new simulation or relaxed gate."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-sampler-load-drive-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    pin=json.loads((ROOT/'docs/evidence/cdr-sampler-load-drive-startup-rejection-20261018.json').read_text())
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,original_run=pin['run'],cases={})
    try:
        for case,p in pin['cases'].items():
            report=p['report'];wanted=[n for n in report['outputs']if n in ('native/native.log','native/bench.cir','native/op.dat')]
            assert 'native/native.log'in wanted and 'native/bench.cir'in wanted
            # Preserve and expose actual HBT wrapper/model parameter text too.
            wanted += [n for n in report['outputs']if n.startswith('models/') and 'npn13g2'in n.lower() and n.endswith(('.lib','.spice','.inc','.mod'))]
            destination=OUT/case
            old,proof=reports.restore_report('cdr-sampler-load-drive-'+case,pin['run'],p['summary_sha256'],p['parts_sha256'],destination,wanted)
            assert old==report
            log=(destination/'native/native.log').read_text()
            r['cases'][case]=dict(archive=proof,original_status=report['status'],diagnostics=report.get('diagnostics'),native_log=log,deck=(destination/'native/bench.cir').read_text(),op=(destination/'native/op.dat').read_text()if(destination/'native/op.dat').exists()else None,models={n:(destination/n).read_text()for n in wanted if n.startswith('models/')})
            print(case,log[-18000:],flush=True)
        r['status']='COMPLETE_ORIGINAL_NATIVE_STARTUP_LOG_REVIEW_FAILURE_REMAINS'
    except BaseException as error:r.update(status='FAIL_REVIEW',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
