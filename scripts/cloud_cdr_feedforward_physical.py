#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact CDR feed-forward passive geometry and native physical checks, no PHY acceptance."""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=None

def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('retime','data','select'),required=True);args=p.parse_args()
    OUT=ROOT/('hw/soc/out/cloud-cdr-feedforward-'+args.kind+'-physical')
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',kind=args.kind,source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Exact retimed PD feed-forward differential networks: four native rppd, two native MIM and six separate contacts per leaf. All dimensions and connections derive from fixed native PD/V-I source. Three leaf types cover five real parent instances. Native560rule DRC/deep-flat12device LVS and five actual/reference faults. Full parent/RC/closed-loop remain open.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/cdr_retimed_pd_vi_v1.spice'
        assert sha(analog)=='5d2f451b0c5d428e7e96bb1b06929e7960a384777ac6b4e6a197c8334b5fcf41'
        receipt=ROOT/'docs/evidence/cdr-pd-vi-native-pass-20261017.json'
        assert sha(receipt)=='ade1d9c2802af05e1eb792339415eb67a4da6adb771358c244065277d14999b7'
        native=json.loads(receipt.read_text())
        assert native['run']==39061446683 and native['status']=='PASS_13_NATIVE_PD_VI_CASES_NOT_CLOSED_LOOP_OR_PHYSICAL_ACCEPTANCE'
        assert len(native['cases'])==13
        assert all(c['report']['source_head']=='d6e1fea0fa7cea93ecb0278a60f94a88ef8be78f' and c['report']['status']=='PASS_NATIVE_PD_VI_SCREEN_NOT_CLOSED_LOOP_OR_PHYSICAL_ACCEPTANCE' for c in native['cases'])
        r['native_source_receipt_sha256']=sha(receipt)
        paths=[Path(__file__),receipt,analog,ROOT/'hw/soc/flow/make_pcie_cdr_feedforward_v1.py',ROOT/'hw/soc/flow/check_pcie_cdr_feedforward_v1.py']
        protected={str(p):sha(p) for p in paths};r['protected_inputs']=protected
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);save()
        for name,command in [
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_cdr_feedforward_v1.py','--pdk',ROOT/'pdk','--out',OUT/'layout','--kind',args.kind]),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_feedforward_v1.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app,'--kind',args.kind])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_NATIVE_PDK_CDR_FEEDFORWARD12_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='PASS_CDR_FEEDFORWARD_LEAF_PHYSICAL_NOT_PARENT_RC_OR_CLOSED_LOOP',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
