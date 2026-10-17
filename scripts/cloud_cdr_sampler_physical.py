#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact sampler layout with unsimplified35device native deep/flat LVS."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-physical'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Frozen native sampler v2 with15HBT,12rppd and8separate substrate contacts. Previous physical LVS simplified eight parallel taps toone:28compared devices. This fresh run disables simplification, requires35devices and bothdeep/flat comparisons. Original560ruleDRC,10faultcontrols andnativeLEF remain. No RC/fullCDR/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/rx_sampler_hbt_v2.spice'
        assert sha(analog)=='2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f'
        assert sha(ROOT/'hw/soc/flow/make_pcie_sampler_cell.py')=='9d6689ba659eb99f878e8bfd0696e8e758f31c00313edcacaef502bef8c113d1'
        paths=[Path(__file__),ROOT/'hw/soc/flow/check_pcie_sampler_cell.py',analog,ROOT/'hw/soc/flow/make_pcie_sampler_cell.py',ROOT/'hw/soc/flow/check_pcie_sampler_unsimplified.py']
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
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_sampler_cell.py','--pdk',ROOT/'pdk','--out',OUT/'layout']),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_sampler_unsimplified.py','--layout',OUT/'layout','--pdk',ROOT/'pdk','--out',OUT/'physical','--app',app])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_SAMPLER35_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_TEN_FAULTS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='PASS_CDR_SAMPLER35_PHYSICAL_NOT_PARENT_RC_OR_CLOSED_LOOP',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
