#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact sampler layout with unsimplified38device native deep/flat LVS."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-hybrid-physical'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Actual left-edge sampler output pins with physical M7 signal shunts. New12HBT3LVNMOS12rppd11taps, original560DRC/deep-flat38deviceLVS/LEF gates, MOS dimension/connectivity faults; twelve actual negative controls. Fresh parent RC and original loaded gates required; no electrical or full PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/rx_sampler_hybrid_tail_v1.spice'
        assert sha(analog)=='dcf0b8ee36f2b4ed181c64a80ae4998f47376043204d9e15a42b0d5b05d20ae5'
        assert sha(ROOT/'hw/soc/flow/make_pcie_sampler_hybrid_tail_v1.py')=='dacc174b0adc1d90f691b20e5d37c0e0d4dd5a723e5aac6e6c9619d138a5071d'
        paths=[Path(__file__),analog,*[ROOT/p for p in ('hw/soc/flow/make_pcie_sampler_compact_v1.py','hw/soc/flow/make_pcie_sampler_hybrid_tail_v1.py','hw/soc/flow/check_pcie_sampler_compact_v1.py','hw/soc/flow/check_pcie_sampler_hybrid_tail_v1.py','scripts/check_cdr_sampler_hybrid_physical_sources.py','scripts/cdr-sampler-hybrid-physical-delta.json','hw/soc/flow/check_pcie_sampler_left_v1.py')]]
        subprocess.run([sys.executable,ROOT/'scripts/check_cdr_sampler_hybrid_physical_sources.py'],check=True)
        protected={str(p):sha(p) for p in paths};r['protected_inputs']=protected
        reports.OUT=OUT
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);save()
        tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'
        tech.parent.mkdir(parents=True,exist_ok=True)
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef','e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',tech)
        assert tech.stat().st_size==28396
        protected[str(tech)]=sha(tech)
        r['technology_lef_source']=dict(pdk_commit='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c',url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef',sha256=sha(tech),bytes=tech.stat().st_size)
        save()
        for name,command in [
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_sampler_hybrid_tail_v1.py','--pdk',ROOT/'pdk','--out',OUT/'layout']),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_sampler_hybrid_tail_v1.py','--layout',OUT/'layout','--pdk',ROOT/'pdk','--out',OUT/'physical','--app',app])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_HYBRID_SAMPLER38_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_TWELVE_FAULTS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='PASS_HYBRID_SAMPLER38_PHYSICAL_REQUIRES_FRESH_PARENT_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
