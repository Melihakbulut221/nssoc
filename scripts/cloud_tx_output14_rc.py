#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh TX output14 wire RC and independent native/export conservation audit."""
import json,os,shutil,subprocess,sys
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-rc'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,full_phy_accepted=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(name,args=()):
        log=OUT/(name+'.log')
        with log.open('x')as stream:code=subprocess.call([sys.executable,OUT/name,*map(str,args)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(script=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(name,code)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output14-anchors-pass-20261021.json').read_text())
        assert pin['run']==39566626613 and pin['summary_sha256']=='e61055da451ac0866f0fab48754fe8469c6c2f951e0c9502004aa55eb88ff71c'
        source=OUT/'source';prior,proof=reports.restore_report('tx-output14-anchors',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,tuple(pin['outputs']))
        assert prior==pin['report']and prior['sources_unchanged'];r['physical_source']=proof
        assert prior['status']=='PASS_ALL38_TX_OUTPUT_TERMINALS_BOUND_WITH24_METAL14_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert prior['binding']['counts']==dict(devices=14,terminals=38,metal_terminals=24,body_terminals=14,public_ports=8,unique_reference_planes=32,wire_components=9)
        assert len(prior['binding']['negative_controls'])==6 and all(x['rejected']for x in prior['binding']['negative_controls'])
        shutil.copytree(source/'wire/native01',OUT/'native01')
        anchors=json.loads((source/'anchors.json').read_text());original=json.loads((source/'anchors.json').read_text())
        old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-output14-anchors'
        paths={}
        for name,digest in anchors['inputs'].items():
            if name.startswith(old+'/'):p=source/name[len(old)+1:]
            else:
                prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
            assert sha(p)==digest;paths[str(p)]=digest
        anchors['inputs']=paths
        anchors['dispositions']=dict(Counter(x['disposition']for x in anchors['rows']))
        assert anchors['dispositions']==dict(ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R=24,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=14)
        assert anchors['rows']==original['rows']and anchors['anchors']==original['anchors']
        (OUT/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
        rt=OUT/'magic-cloud';rt.mkdir()
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        magic=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in magic['files'].items());r['runtime']=runtime
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        methods=json.loads((ROOT/'scripts/tx-output14-rc-methods.json').read_text())
        for name,spec in methods.items():
            baseline=ROOT/spec['baseline_path'];candidate=ROOT/spec['path']
            assert sha(baseline)==spec['baseline_sha256']and sha(candidate)==spec['adapted_sha256']
            text=baseline.read_text()
            for e in spec['edits']:
                assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
            assert candidate.read_text()==text
            shutil.copyfile(candidate,OUT/name)
        r['method_adaptations']=methods;save()
        run('run-rc01.py');r['native']=json.loads((OUT/'rc01/result.json').read_text());save()
        assert r['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and r['native']['returncode']==0
        run('audit-rc02.py',[OUT/'rc01',OUT/'anchors03.json',OUT/'audit.json']);r['audit']=json.loads((OUT/'audit.json').read_text());save()
        assert r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',r['audit'].get('error')
        run('mutations01.py');r['controls']=json.loads((OUT/'native-mutations01.json').read_text());save()
        assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(r['controls']['cases'])==13
        assert all(sha(source/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in magic['files'].items())and sha(raw)==rawspec['sha256']
        r.update(status='PASS_FRESH_TX_OUTPUT14_WIRE_RC_AND13_RAW_CONTROLS_REQUIRES_COMPOSITION_AND_PARENT_ROUTE',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
