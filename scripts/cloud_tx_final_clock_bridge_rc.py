#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh actual bridge wire RC and complete raw-export audits; not qualified PEX."""
import json,os,shutil,subprocess,sys
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-final-clock-bridge-rc'
SOURCE=dict(run=39375124889,head='ee9de646c851b200964cb6944864302f02b1b93d',
 group='tx-final-clock-bridge-planes',
 summary='27b07b3d80a74e155bfa4c0d5a46f3f812f90910ea81ff25d56c8af5a9a1de2b',
 parts='2bd4399d39617b4e68d6067bd39ec3ffcdd5491507de982a701c0e451aaf6123')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,
                accepted=False,qualified_pex=False,qualified_substrate=False,qualified_timing=False,
                serial_phy_complete=False,mainchip_integrated=False,full_clock_composed=False,electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,args=()):
        log=OUT/(name+'.log')
        with log.open('w')as stream:
            code=subprocess.call([sys.executable,OUT/name,*map(str,args)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(script=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:])
        assert code==0,(name,code)
    save()
    try:
        pins=json.loads((ROOT/'scripts/tx-final-clock-bridge-rc-sources.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in pins.items()),'Protected extraction source changed'
        manifest=json.loads((ROOT/'scripts/tx-final-clock-bridge-rc-methods.json').read_text())
        for m in manifest:
            assert sha(ROOT/m['baseline'])==m['baseline_sha256']
            adapted=(ROOT/m['baseline']).read_text()
            for old,new in m['edits']:
                assert adapted.count(old)==m['occurrences'][old];adapted=adapted.replace(old,new)
            assert adapted==(ROOT/m['path']).read_text() and sha(ROOT/m['path'])==m['sha256']
        stem=SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
        base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']+'/'
        fetch(base+stem+'.summary.json',SOURCE['summary'],OUT/'wire-summary.json')
        frozen=json.loads((OUT/'wire-summary.json').read_text())
        source=OUT/'source'
        prior,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],source,tuple(frozen['outputs']))
        assert prior==frozen and prior['source_head']==SOURCE['head'] and prior['source_unchanged']
        assert prior['status']=='PASS_NATIVE_BRIDGE2_WIRE_GRAPH_ALL5_TERMINAL_PLANES_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert prior['binding']['counts']==dict(devices=2,terminals=5,metal_terminals=3,body_terminals=2,public_ports=3,unique_reference_planes=6,wire_components=3)
        assert len(prior['binding']['negative_controls'])==6 and all(c['rejected'] for c in prior['binding']['negative_controls'])
        result['restore']=proof;shutil.copytree(source/'native01',OUT/'native01')
        anchors=json.loads((source/'anchors.json').read_text());original=json.loads((source/'anchors.json').read_text())
        old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-final-clock-bridge-planes';paths={}
        for name,digest in anchors['inputs'].items():
            if name.startswith(old+'/'):p=source/name[len(old)+1:]
            else:
                prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
            assert sha(p)==digest;paths[str(p)]=digest
        anchors['inputs']=paths;anchors['dispositions']=dict(Counter(r['disposition'] for r in anchors['rows']))
        assert anchors['dispositions']==dict(ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R=3,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=2)
        assert anchors['rows']==original['rows'] and anchors['anchors']==original['anchors']
        (OUT/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
        rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        magic=json.loads((rt/'manifest.json').read_text())
        assert all(sha(rt/n)==v['sha256'] for n,v in magic['files'].items());result['runtime']=runtime
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        for name,path in [('run-rc01.py','scripts/tx_final_clock_bridge_run_rc01.py'),
                          ('audit-rc02.py','scripts/tx_final_clock_bridge_audit_rc02.py'),
                          ('mutations01.py','scripts/tx_final_clock_bridge_rc_mutations.py')]:
            shutil.copyfile(ROOT/path,OUT/name)
        result['method_adaptations']=manifest;save()
        run('run-rc01.py');result['native']=json.loads((OUT/'rc01/result.json').read_text());save()
        assert result['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT' and result['native']['returncode']==0
        run('audit-rc02.py',[OUT/'rc01',OUT/'anchors03.json',OUT/'audit.json'])
        result['audit']=json.loads((OUT/'audit.json').read_text());save()
        assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',result['audit'].get('error')
        run('mutations01.py');result['controls']=json.loads((OUT/'native-mutations01.json').read_text());save()
        assert result['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_SAVED_RAW_CORRUPTION_CONTROLS' and len(result['controls']['cases'])==13
        assert all(sha(source/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256'] for n,v in magic['files'].items()) and sha(raw)==rawspec['sha256']
        assert all(sha(ROOT/p)==h for p,h in pins.items())
        result.update(status='PASS_FRESH_ACTUAL_BRIDGE_WIRE_RC_AND13_SAVED_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
