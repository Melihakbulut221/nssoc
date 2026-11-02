#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source, complete-case dispatch and XML refusal controls; no RTL execution."""
import copy,json,xml.etree.ElementTree as ET
from pathlib import Path
import check_pcie_guarded_root as target
def reject(call,label):
    try:call()
    except (AssertionError,KeyError,ValueError,TypeError,ET.ParseError):return label
    raise AssertionError('Accepted invalid control: '+label)
def main():
    m=target.pins();raw={p:(target.ROOT/p).read_bytes()for p in m['protected']};rejected=[]
    for p in raw:
        bad=dict(raw);bad[p]+=b'\n'
        rejected.append(reject(lambda:target.check_manifest(m,bad),'source:'+p))
    bad=dict(raw);bad.pop(next(iter(bad)))
    rejected.append(reject(lambda:target.check_manifest(m,bad),'missing-source'))
    bad=dict(raw,extra=b'x')
    rejected.append(reject(lambda:target.check_manifest(m,bad),'extra-source'))
    changed=copy.deepcopy(m);changed['scope']['full_phy_accepted']=True
    rejected.append(reject(lambda:target.check_manifest(changed,raw),'claimed-PHY'))
    changed=copy.deepcopy(m);changed['legacy_manifests']['scripts/pcie-training-epoch-ingress-methods.json']['admitted_root_deltas']={}
    rejected.append(reject(lambda:target.check_manifest(changed,raw),'removed-nettype-delta-proof'))
    assert len(target.cases('shared'))==5 and len(target.cases('epoch'))==6
    for suite in ('shared','epoch'):
        assert sum(len(target.TESTS[module])for depth,top,module in target.cases(suite))==target.EXPECTED[suite]
    positive=[]
    for module,names in target.TESTS.items():
        root=ET.Element('testsuites');suite=ET.SubElement(root,'testsuite')
        for name in names:ET.SubElement(suite,'testcase',name=name,classname=module,file=str(target.BENCH/(module+'.py')),sim_time_ns='200')
        data=ET.tostring(root);assert len(target.review(data,module,0))==len(names);positive.append(module)
        for kind in ('missing','duplicate','skip','error','zero-time','nonfinite-time','wrong-module','wrong-file','wrong-test','failure'):
            bad=copy.deepcopy(root);parent=bad.find('testsuite');case=parent[0]
            if kind=='missing':parent.remove(case)
            elif kind=='duplicate':parent.append(copy.deepcopy(case))
            elif kind=='skip':ET.SubElement(case,'skipped')
            elif kind=='error':ET.SubElement(case,'error')
            elif kind=='zero-time':case.set('sim_time_ns','0')
            elif kind=='nonfinite-time':case.set('sim_time_ns','nan')
            elif kind=='wrong-module':case.set('classname','wrong')
            elif kind=='wrong-file':case.set('file','wrong.py')
            elif kind=='wrong-test':case.set('name','invented')
            elif kind=='failure':ET.SubElement(case,'failure')
            rejected.append(reject(lambda:target.review(ET.tostring(bad),module,0),module+':'+kind))
        rejected.append(reject(lambda:target.review(data,module,1),module+':nonzero-exit'))
        rejected.append(reject(lambda:target.review(b'<!DOCTYPE x>'+data,module,0),module+':doctype'))
    target.pins()
    out=target.ROOT/'hw/soc/out/guarded-root-controls';out.mkdir(parents=True)
    target.shared.save(out/'result.json',dict(status='PASS_ROOT_GUARDED_PCIE_SOURCE_CONTROLS',
      reviewed_modules=positive,refusals=rejected,expected_shared_tests=25,expected_epoch_tests=30,
      actual_RTL_executed=False,scope=target.SCOPE))
    print('PASS root guarded PCIe source binding, complete case matrix and',len(rejected),'refusals')
if __name__=='__main__':main()
