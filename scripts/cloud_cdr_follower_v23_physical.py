#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual candidate HBT retime followers and native physical checks; no electrical acceptance."""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=None

def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('follower',),required=True);args=p.parse_args()
    OUT=ROOT/('hw/soc/out/cloud-cdr-follower-v23-physical')
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    from check_cdr_follower_v23_sources import check
    check()
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',kind=args.kind,source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Two real Nx4 HBT emitter followers, two w4u/l4.5u rppd pull-downs and four finite substrate contacts. Seven external ports. Full560DRC, deep/flat8-deviceLVS, four reference faults and three physical geometry faults. Candidate requires full-parent integration, fresh RC and unchanged loaded waveform gates; not electrical or PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/cdr_retime_follower_v23.spice'
        assert sha(analog)=='82e880bbba3660af3064f6eda688d4ae78c7a110fda460f6f930beb695ff128d'
        receipt=ROOT/'docs/evidence/cdr-v22-native-latch-diagnosis-20261020.json'
        r['diagnosis_receipt_sha256']=sha(receipt)
        paths=[Path(__file__),receipt,analog,ROOT/'hw/soc/flow/make_pcie_cdr_retime_follower_v23.py',ROOT/'hw/soc/flow/check_pcie_cdr_retime_follower_v23.py']
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
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_cdr_retime_follower_v23.py','--pdk',ROOT/'pdk','--out',OUT/'layout','--kind',args.kind]),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retime_follower_v23.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app,'--kind',args.kind])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_NATIVE_PDK_CDR_FOLLOWER8_DRC_LVS_AND_SEVEN_FAULT_CONTROLS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        check()
        r.update(status='PASS_CDR_FOLLOWER_V23_LEAF_PHYSICAL_REQUIRES_PARENT_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
