#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh actual full-driver native wire RC and independent raw graph audit."""
import argparse,json,os,shutil,subprocess,sys
import compare_cloud_routed_endpoints as reports
from collections import Counter
from pathlib import Path
import cloud_tx_input_driver_localpins as physical
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-localpins-rc'
SOURCES={
 'l2p4-series-l6p2':dict(run=38945153543,summary='599c4e9260ff04ba4f608d32dc5184d0143b4cf9009bceb6f193bef0adf06d2d',parts='c4618adff94af1b4e075b3f0851fe744a2c69b33a3405ea71149a7cd79d8d397'),
 'l2p7':dict(summary='ea9041bfe2dc5b75341d978c6b7135e7fce7550f49ec749aee9842cb15f54404',parts='9ff1da22c2a9f4806af2d67003f268f83f05c5f2c2ebd6dcc5d15e5431613435'),
 'l2p4':dict(summary='52e20fdc7fc3f473d9662598043159675aa96e11d6b2586008bdbdcd58c05ae7',parts='6a0e203d7a1f3c918bea39a1108f66a72a467be7e6c718157593f1e705a478ab'),
}
def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);args=parser.parse_args()
    OUT=ROOT/('hw/soc/out/cloud-tx-driver-pullup-rc-'+args.variant)
    SOURCE=dict(run=38934298533,group='tx-driver-pullup-wires-'+args.variant)|SOURCES[args.variant]
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False,full_driver_composed=False,electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,args=()):
        log=OUT/(name+'.log')
        with log.open('w')as stream:code=subprocess.call([sys.executable,OUT/name,*map(str,args)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(script=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:])
        assert code==0,(name,code)
    save()
    try:
        reports.OUT=OUT;source=OUT/'source'
        stem=SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']+'/'+stem+'.summary.json'
        fetch(url,SOURCE['summary'],OUT/'wire-summary.json');frozen=json.loads((OUT/'wire-summary.json').read_text())
        prior,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],source,tuple(frozen['outputs']))
        assert prior==frozen and prior['variant']==args.variant and prior['source_unchanged']
        result['variant']=args.variant;result['restore']=proof
        assert prior['status']=='PASS_ACTUAL_PULLUP_WIRE_GRAPH_AND372_TERMINAL_ANCHORS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert prior['binding']['counts']==dict(devices=100,terminals=372,metal_terminals=272,body_terminals=100,public_ports=6,unique_reference_planes=164,wire_components=10)
        assert len(prior['binding']['negative_controls'])==4 and all(r['rejected']for r in prior['binding']['negative_controls'])
        wire=source/'native01';shutil.copytree(wire,OUT/'native01')
        anchors=json.loads((source/'anchors.json').read_text());original=json.loads((source/'anchors.json').read_text())
        old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-driver-pullup-wires-'+args.variant
        paths={}
        for name,digest in anchors['inputs'].items():
            if name.startswith(old+'/'):p=source/name[len(old)+1:]
            else:
                prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
            assert sha(p)==digest;paths[str(p)]=digest
        anchors['inputs']=paths
        anchors['dispositions']=dict(Counter(r['disposition']for r in anchors['rows']))
        assert anchors['dispositions']==dict(ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R=272,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=100)
        assert anchors['rows']==original['rows'] and anchors['anchors']==original['anchors']
        (OUT/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        magic=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in magic['files'].items());result['runtime']=runtime
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser'];raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        manifest=json.loads((ROOT/'docs/evidence/tx-driver-rc-methods-20261016.json').read_text())
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
        result['status']='PASS_FRESH_ACTUAL_PULLUP_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
