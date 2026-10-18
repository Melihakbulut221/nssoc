#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reexecute the failed prepared-SoC checks with unchanged acceptance gates."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-ci-prepared-rtl-lint-20261018'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    suite=Path(os.environ['OSS_CAD_SUITE'])
    commands=[('lint-base',[sys.executable,'scripts/check_soc_lint.py','--profile','base','--output',str(OUT/'lint-base')]),('lint-full',[sys.executable,'scripts/check_soc_lint.py','--profile','full','--output',str(OUT/'lint-full')]),('async-pcie-ethernet',[sys.executable,'scripts/check_pcie_ethernet_soc.py','--out',str(OUT/'joint'),'--iverilog-dir',str(suite/'bin'),'--async-pcie'])]
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],commands=[],full_phy_accepted=False,physical_timing_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        for name,cmd in commands:
            log=OUT/(name+'.log')
            with log.open('w') as stream:code=subprocess.call(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            r['commands'].append(dict(name=name,argv=cmd,returncode=code,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()));save()
            if code:print(log.read_text(errors='replace')[-10000:],flush=True)
        assert all(x['returncode']==0 for x in r['commands'])
        for profile in ('base','full'):
            x=json.loads((OUT/('lint-'+profile)/'result.json').read_text())
            assert x['status']=='PASS_WITH_RECORDED_WARNINGS' and not any(x['delta'].values()) and x['sources_unchanged'] and not x['immutable_drift'] and not x['own_unaccepted']
        x=json.loads((OUT/'joint/result.json').read_text())
        assert x['status']=='PASS' and x['tests']==dict(passed=2,failed=0,skipped=0) and x['unchanged'] and x['runtime_unchanged'] and x['asynchronous_pcie']
        r['status']='PASS_BASE_FULL_LINT_AND_ACTUAL_ASYNC_PCIE_ETHERNET_RTL'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
