#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Generate the real3p2 collector-load candidate; old RC hypotheses cannot accept it.
import json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-pll-divider-load3p2v2-physical';out.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,electrically_validated=False,serial_phy_complete=False,mainchip_integrated=False,scope='Corrected actual div4 first-toggle loads L2.8 W8 and tail11.5 with four second-toggle collector loads L3.2 W8. Same candidate will be needed twice in PLL. Native DRC/deep+flat LVS/LEF and all original fault controls plus wrong-load control. No extractedRC/acquisition/device-safety acceptance.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());pack=out/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],pack);assert pack.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(pack)as t:t.extractall(ROOT,filter='data')
        pack.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef';tech.parent.mkdir(parents=True,exist_ok=True)
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef','e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',tech)
        r['additional_tech_lef']=dict(pdk_commit='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c',sha256=sha(tech),bytes=tech.stat().st_size)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        checker=ROOT/'hw/soc/flow/check_pcie_clock_div4_load3p2_v2.py'
        sources=[checker,ROOT/'hw/soc/flow/make_pcie_clock_div4_load3p2_v2.py',Path(__file__)]
        r['inputs']={str(p):sha(p)for p in sources};save()
        with (out/'physical.log').open('w')as log:
            rc=subprocess.call([sys.executable,str(checker),'--generate','--pdk',str(ROOT/'pdk'),'--layout',str(out/'layout'),'--out',str(out/'check')],stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=rc
        for label in ['layout','check']:
            p=out/label/'result.json'
            if p.exists():r[label]=json.loads(p.read_text())
        save();assert rc==0,'Native physical validation failed; preserve full logs'
        assert r['check']['status']=='PASS_DIV4_LOAD3P2_V2_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY'
        assert all(sha(Path(p))==h for p,h in r['inputs'].items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r['status']='PASS_DIVIDER_LOAD3P2V2_PARENT_FIRST_LOADS_RESTORED_NATIVE_PHYSICAL_SCREEN_REQUIRES_FRESH_RC_AND_ACQUISITION'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
