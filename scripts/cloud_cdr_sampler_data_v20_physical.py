#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact sampler layout with unsimplified54device native deep/flat LVS."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-data-v20-physical'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Only eight data/hold HBTs change Nx8 to Nx4. All46 other native drawings and parameters retained, including Nx4 selectors, original bias and tail geometry. Fresh54-device layout and original560DRC/deep-flatLVS/LEF with an added wrong-data-Nx fault. Requires fresh whole-parent RC and original full loaded electrical gates; no electrical acceptance from this layout.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/rx_sampler_data_drive_v20.spice'
        assert sha(analog)=='b8f060f20cf9834535b11fb03742b306041e163e37a6c6cff5158dfadd97dcc2'
        assert sha(ROOT/'hw/soc/flow/make_pcie_sampler_data_v20.py')=='eb34ea13ff057c2609fe7cf6c8458a98845738952ec10d31d67dd4b53c36c779'
        paths=[Path(__file__),analog,*[ROOT/p for p in ('hw/soc/flow/make_pcie_sampler_compact_v1.py','hw/soc/flow/make_pcie_sampler_data_v20.py','hw/soc/flow/check_pcie_sampler_compact_v1.py','hw/soc/flow/check_pcie_sampler_data_v20.py','scripts/check_cdr_sampler_data_v20_sources.py','scripts/cdr-sampler-data-v20-source-delta.json','hw/soc/flow/check_pcie_sampler_left_v1.py','scripts/check_cdr_sampler_data_v20_geometry.py')]]
        subprocess.run([sys.executable,ROOT/'scripts/check_cdr_sampler_data_v20_sources.py'],check=True)
        protected={str(p):sha(p) for p in paths};r['protected_inputs']=protected
        reports.OUT=OUT
        electrical_pin=json.loads((ROOT/'docs/evidence/cdr-sampler-parallel-drive-native-pass-20261018.json').read_text())
        assert electrical_pin['run']==39125857951 and electrical_pin['source_head']=='3c5d2dcde9235c499ed0238e057fd2c3e6cb9605'
        r['baseline_native_electrical_screens']={}
        for case,bound in electrical_pin['cases'].items():
            report,receipt=reports.restore_report('cdr-sampler-parallel-drive-'+case,electrical_pin['run'],bound['summary_sha256'],bound['parts_sha256'],OUT/('electrical-'+case),['native/bench.cir','native/native.log','native/op.dat'])
            assert report==bound['report']and report['source_head']==electrical_pin['source_head']
            assert report['status']=='PASS_NATIVE_PARALLEL_DRIVE_STRESS_NOT_CDR_OR_PHYSICAL_ACCEPTANCE'
            assert report['sources_unchanged']and report['devices_passed']and not report['diagnostics']and report['samples']==768
            assert report['protected_inputs'][str(ROOT/'hw/soc/analog/pcie/rx_sampler_parallel_drive_v8.spice')]==sha(ROOT/'hw/soc/analog/pcie/rx_sampler_parallel_drive_v8.spice')
            assert len(report['devices'])==16 and len(report['mos_devices'])==9 and len(report['resistors'])==12
            assert report['parallel_tail_topology']['total_width_per_stage_um']==144
            assert report['data_passed']if case in ('nominal','hot_low','cold_high')else report['actual_fault_detected']
            r['baseline_native_electrical_screens'][case]=receipt
        assert set(r['baseline_native_electrical_screens'])=={'nominal','hot_low','cold_high','swap_output','clock_stopped'}
        save()
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
        baseline_pin=json.loads((ROOT/'docs/evidence/cdr-sampler-selector-v19-physical-pass-20261020.json').read_text())
        assert baseline_pin['run']==39391984326 and baseline_pin['source_head']=='2ffc2ae6dc2f9f1cf1fa9d4b6a57b3717760ac2f'
        assert baseline_pin['group']=='cdr-sampler-selector-v19-physical'
        assert baseline_pin['summary_sha256']=='aeb0b6a953f21c68caa1cf46503a60d9ac4e0583305a9d021bff6df765c750a3'
        baseline_report,baseline_restore=reports.restore_report(baseline_pin['group'],baseline_pin['run'],baseline_pin['summary_sha256'],baseline_pin['parts_sha256'],OUT/'baseline',['layout/result.json','layout/schematic.cir','layout/nssoc_rx_sampler_selector_layout_v19.gds'])
        assert baseline_report['source_head']==baseline_pin['source_head']and baseline_report['status']==baseline_pin['status']and baseline_report['sources_unchanged']
        r['baseline_physical_source']=baseline_restore;save()
        for name,command in [
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_sampler_data_v20.py','--pdk',ROOT/'pdk','--out',OUT/'layout']),
          ('primitive_identity',[app,'python',ROOT/'scripts/check_cdr_sampler_data_v20_geometry.py','--baseline',OUT/'baseline/layout','--candidate',OUT/'layout','--output',OUT/'primitive-identity.json']),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_sampler_data_v20.py','--layout',OUT/'layout','--pdk',ROOT/'pdk','--out',OUT/'physical','--app',app])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_DATA4_SELECTOR4_SAMPLER54_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_EIGHTEEN_FAULTS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='PASS_DATA4_SELECTOR4_SAMPLER54_PHYSICAL_REQUIRES_FRESH_PARENT_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
