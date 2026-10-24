#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh actual8074-device driver/core native wire RC and independent raw graph audit."""
import json,os,shutil,subprocess,sys
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-raw64-native-rc'
SOURCE={'run': 39471428433, 'source_head': '59a8c969bb35502f81496fb0163b6022fb00f101', 'summary_sha256': '6fb4b9d01b5581557a1ee986324e29ff31b199bb19f905bbd9084d2fbd65bed9', 'parts_sha256': 'c2cfac566bfb7398ee989491c11b28f1adb3d25fa1313b436de77ae228ba89bd'}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False,full_parent_composed=False,electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,args=()):
        log=OUT/(name+'.log')
        with log.open('w')as stream:code=subprocess.call([sys.executable,OUT/name,*map(str,args)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(script=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:])
        assert code==0,(name,code)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-raw64-native-anchors-pass-20261020.json').read_text())
        assert all(pin[k]==v for k,v in SOURCE.items())
        reports.OUT=OUT;source=OUT/'source'
        prior,proof=reports.restore_report('tx-raw64-native-anchors',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,list(pin['outputs']))
        assert prior['source_head']==pin['source_head']and prior['sources_unchanged']and prior['outputs']==pin['outputs']
        assert prior['status']=='PASS_ALL28582_FULL_PARENT_TERMINALS_WITH20508_METAL8074_BODY_AND_FOUR_FAULTS_NOT_RC_ACCEPTANCE'
        assert prior['binding']['counts']==dict(devices=8074,terminals=28582,metal_terminals=20508,body_terminals=8074,public_ports=163,unique_reference_planes=13344,wire_components=698)
        assert len(prior['binding']['negative_controls'])==4 and all(r['rejected']for r in prior['binding']['negative_controls'])
        result['anchor_source']=proof
        shutil.copytree(source/'source/native01',OUT/'native01')
        anchors=json.loads((source/'anchors.json').read_text());original=json.loads((source/'anchors.json').read_text())
        old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-raw64-native-anchors'
        paths={}
        for name,digest in anchors['inputs'].items():
            if name.startswith(old+'/'):p=source/name[len(old)+1:]
            else:
                prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
            assert sha(p)==digest;paths[str(p)]=digest
        anchors['inputs']=paths
        anchors['dispositions']=dict(Counter(r['disposition']for r in anchors['rows']))
        assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R=20508,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=8074)
        assert anchors['rows']==original['rows'] and anchors['anchors']==original['anchors']
        (OUT/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        magic=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in magic['files'].items());result['runtime']=runtime
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser'];raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        manifest=json.loads((ROOT/'scripts/tx-raw64-rc-methods.json').read_text())
        for name,spec in manifest.items():
            p=ROOT/spec['path'];assert sha(p)==spec['adapted_sha256'];shutil.copyfile(p,OUT/name)
        result['method_adaptations']=manifest;save()
        run('run-rc01.py');result['native']=json.loads((OUT/'rc01/result.json').read_text());save()
        assert result['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT' and result['native']['returncode']==0
        run('audit-rc02.py',[OUT/'rc01',OUT/'anchors03.json',OUT/'audit.json']);result['audit']=json.loads((OUT/'audit.json').read_text());save()
        assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',result['audit'].get('error')
        run('mutations01.py');result['controls']=json.loads((OUT/'native-mutations01.json').read_text());save()
        assert result['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS' and len(result['controls']['cases'])==13
        assert all(sha(source/n)==v for n,v in prior['outputs'].items()) and all(sha(rt/n)==v['sha256']for n,v in magic['files'].items()) and sha(raw)==rawspec['sha256']
        result['status']='PASS_FRESH_RAW64_CORE8074_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
