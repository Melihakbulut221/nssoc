#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact sampler layout with unsimplified54device native deep/flat LVS."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-via-rich-physical'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,closed_loop=False,qualified_pex=False,
           main_chip_integrated=False,
           scope='Parallel via arrays at local access and strap junctions;32um load-resistor Metal3 escapes widened to2um. All native primitive drawings/positions, devices and original physical gates unchanged. New16HBT9LVNMOS12rppd17taps, original560DRC/deep-flat54deviceLVS/LEF gates, MOS dimension/connectivity faults plus missing split devices; fourteen actual negative controls. Fresh parent RC and original loaded gates required; no electrical or full PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        analog=ROOT/'hw/soc/analog/pcie/rx_sampler_parallel_drive_v8.spice'
        assert sha(analog)=='876bd1d55af65726ebfcb979d56036b83faccc691e3427f0fb09333d8100acc3'
        assert sha(ROOT/'hw/soc/flow/make_pcie_sampler_via_rich_v11.py')=='7a48825ee5b3c83856d86437fc536c892973d2a6fda7cf19ee1a70572dc3cd7a'
        paths=[Path(__file__),analog,*[ROOT/p for p in ('hw/soc/flow/make_pcie_sampler_compact_v1.py','hw/soc/flow/make_pcie_sampler_via_rich_v11.py','hw/soc/flow/check_pcie_sampler_compact_v1.py','hw/soc/flow/check_pcie_sampler_via_rich_v11.py','scripts/check_cdr_sampler_via_rich_sources.py','scripts/cdr-sampler-via-rich-source-delta.json','hw/soc/flow/check_pcie_sampler_left_v1.py','scripts/check_cdr_sampler_via_rich_geometry.py')]]
        subprocess.run([sys.executable,ROOT/'scripts/check_cdr_sampler_via_rich_sources.py'],check=True)
        protected={str(p):sha(p) for p in paths};r['protected_inputs']=protected
        reports.OUT=OUT
        electrical_pin=json.loads((ROOT/'docs/evidence/cdr-sampler-parallel-drive-native-pass-20261018.json').read_text())
        assert electrical_pin['run']==39125857951 and electrical_pin['source_head']=='3c5d2dcde9235c499ed0238e057fd2c3e6cb9605'
        r['native_electrical_screens']={}
        for case,bound in electrical_pin['cases'].items():
            report,receipt=reports.restore_report('cdr-sampler-parallel-drive-'+case,electrical_pin['run'],bound['summary_sha256'],bound['parts_sha256'],OUT/('electrical-'+case),['native/bench.cir','native/native.log','native/op.dat'])
            assert report==bound['report']and report['source_head']==electrical_pin['source_head']
            assert report['status']=='PASS_NATIVE_PARALLEL_DRIVE_STRESS_NOT_CDR_OR_PHYSICAL_ACCEPTANCE'
            assert report['sources_unchanged']and report['devices_passed']and not report['diagnostics']and report['samples']==768
            assert report['protected_inputs'][str(analog)]==sha(analog)
            assert len(report['devices'])==16 and len(report['mos_devices'])==9 and len(report['resistors'])==12
            assert report['parallel_tail_topology']['total_width_per_stage_um']==144
            assert report['data_passed']if case in ('nominal','hot_low','cold_high')else report['actual_fault_detected']
            r['native_electrical_screens'][case]=receipt
        assert set(r['native_electrical_screens'])=={'nominal','hot_low','cold_high','swap_output','clock_stopped'}
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
        baseline_pin=json.loads((ROOT/'docs/evidence/cdr-sampler-strapped-physical-pass-20261018.json').read_text())
        baseline_report,baseline_restore=reports.restore_report('cdr-sampler-strapped-physical',baseline_pin['run'],baseline_pin['summary_sha256'],baseline_pin['parts_sha256'],OUT/'baseline',['layout/result.json','layout/schematic.cir','layout/nssoc_rx_sampler_strapped_layout_v10.gds'])
        assert baseline_report==baseline_pin['report']and baseline_report['sources_unchanged']
        r['baseline_physical_source']=baseline_restore;save()
        for name,command in [
          ('generation',[app,'python',ROOT/'hw/soc/flow/make_pcie_sampler_via_rich_v11.py','--pdk',ROOT/'pdk','--out',OUT/'layout']),
          ('primitive_identity',[app,'python',ROOT/'scripts/check_cdr_sampler_via_rich_geometry.py','--baseline',OUT/'baseline/layout','--candidate',OUT/'layout','--output',OUT/'primitive-identity.json']),
          ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_sampler_via_rich_v11.py','--layout',OUT/'layout','--pdk',ROOT/'pdk','--out',OUT/'physical','--app',app])]:
            with (OUT/(name+'.log')).open('w')as log:
                code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code;save()
            if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
            assert code==0,name+' failed; retain actual geometry and reports'
        physical=json.loads((OUT/'physical/result.json').read_text())
        assert physical['status']=='PASS_PARALLEL_SAMPLER54_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_FOURTEEN_FAULTS'
        assert all(sha(Path(p))==h for p,h in protected.items())
        r.update(status='PASS_PARALLEL_SAMPLER54_PHYSICAL_REQUIRES_FRESH_PARENT_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.exists():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
