#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh actual8088-device driver/core native wire RC and independent raw graph audit."""
import json,os,shutil,subprocess,sys
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-native-rc'
SOURCE={'run': 39898478620, 'source_head': '15ec1dc3c3dd7d3a392c28719e015e9f5ceb2399', 'summary_sha256': '350eabcb2b1014a6fad1c76512800b51392906d4c2a859697562f58cf829ce0b', 'parts_sha256': 'de9fbc36e471eaddedc55bf98f1541df60dd902d823de9c65b0c7b43c4d58987'}
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
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-native-anchors-pass-20261023.json').read_text())
        assert all(pin[k]==v for k,v in SOURCE.items())
        reports.OUT=OUT;source=OUT/'source'
        prior,proof=reports.restore_report('tx-output8088-power128return64-native-anchors',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,list(pin['outputs']))
        assert prior['source_head']==pin['source_head']and prior['sources_unchanged']and prior['outputs']==pin['outputs']
        assert prior['status']=='PASS_ALL28620_FULL_PARENT_TERMINALS_WITH20532_METAL8088_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert prior['binding']['counts']==dict(devices=8088,terminals=28620,metal_terminals=20532,body_terminals=8088,public_ports=165,unique_reference_planes=13370,wire_components=703)
        assert len(prior['binding']['negative_controls'])==6 and all(r['rejected']for r in prior['binding']['negative_controls'])
        result['anchor_source']=proof
        shutil.copytree(source/'source/native01',OUT/'native01')
        anchors=json.loads((source/'anchors.json').read_text());original=json.loads((source/'anchors.json').read_text())
        old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-output8088-power128return64-native-anchors'
        paths={}
        for name,digest in anchors['inputs'].items():
            if name.startswith(old+'/'):p=source/name[len(old)+1:]
            else:
                prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
            assert sha(p)==digest;paths[str(p)]=digest
        anchors['inputs']=paths
        anchors['dispositions']=dict(Counter(r['disposition']for r in anchors['rows']))
        assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R=20532,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=8088)
        assert anchors['rows']==original['rows'] and anchors['anchors']==original['anchors']
        (OUT/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        magic=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in magic['files'].items());result['runtime']=runtime

        qualified,qproof=reports.restore_report('tx-raw64-totalcap-precision',39486998309,
            'bdcbddedf70af7e4bc9a1d6b3ec4ac334a619e2fe208244b83a6e8b74cc09a38',
            '3b0dc36952ae38ac4ce1c1ea8e27cac8e4917ca7543a81a916a207b49adaa9e2',
            OUT/'producer',['precise-source/magic/tclmagic.so'])
        assert qualified['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        for key in ('sources_unchanged','baseline_reproduced_original_rc_and_failure','no_rc_records_changed','no_geometry_technology_or_threshold_change','both_native_input_orders_verified'):assert qualified[key]
        assert len(qualified['controls']['cases'])==len(qualified['historical_controls']['cases'])==13
        assert qualified['source_changes']['changed_only']=='resis/resis.h'
        lib=OUT/'producer/precise-source/magic/tclmagic.so'
        precise='1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c'
        assert sha(lib)==qualified['rebuilt_runtimes']['precise']['sha256']==precise
        dependencies=subprocess.run(['ldd',str(lib)],capture_output=True,text=True)
        (OUT/'producer-ldd.log').write_text(dependencies.stdout+dependencies.stderr)
        assert dependencies.returncode==0 and 'not found'not in dependencies.stdout+dependencies.stderr
        target=rt/'runtime/lib/magic/tcl/tclmagic.so'
        assert sha(target)=='e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e'
        shutil.copyfile(lib,target);assert sha(target)==precise
        result['qualified_double_total_producer']=dict(source=qproof,sha256=precise,all_other_runtime_files_unchanged=True)

        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser'];raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        manifest=json.loads((ROOT/'scripts/tx-output8088-power128return64-rc-methods.json').read_text())
        for name,spec in manifest.items():
            p=ROOT/spec['path'];assert sha(p)==spec['adapted_sha256']
            baseline=ROOT/spec['baseline_path'];assert sha(baseline)==spec['baseline_sha256']
            text=baseline.read_text()
            for e in spec['edits']:
                assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
            assert text==p.read_text()
            shutil.copyfile(p,OUT/name)
        result['method_adaptations']=manifest;save()
        run('run-rc01.py');result['native']=json.loads((OUT/'rc01/result.json').read_text());save()
        assert result['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT' and result['native']['returncode']==0
        run('audit-rc02.py',[OUT/'rc01',OUT/'anchors03.json',OUT/'audit.json']);result['audit']=json.loads((OUT/'audit.json').read_text());save()
        assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',result['audit'].get('error')
        run('mutations01.py');result['controls']=json.loads((OUT/'native-mutations01.json').read_text());save()
        assert result['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS' and len(result['controls']['cases'])==13
        assert all(sha(source/n)==v for n,v in prior['outputs'].items()) and all(sha(rt/n)==(precise if n=='runtime/lib/magic/tcl/tclmagic.so'else v['sha256'])for n,v in magic['files'].items()) and sha(raw)==rawspec['sha256'] and sha(lib)==precise
        result['sources_unchanged']=True
        result['status']='PASS_FRESH_TX_OUTPUT8088_POWER128RETURN64_PRECISE_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
