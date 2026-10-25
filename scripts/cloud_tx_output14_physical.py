#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rebuild actual TX output14 with unsimplified native LVS before parent integration."""
import json,os,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-physical'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,parent_tree_integrated=False,mainchip_integrated=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-lane-boundaries-pass-20261021.json').read_text())
        assert pin['run']==39555328447 and pin['summary_sha256']=='bc99a8d71e863e81b8f367c599e449d1a17143bb82a720c9a4e60c4d27b2f8e4'
        prior,proof=reports.restore_report('tx-lane-boundaries',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'boundaries',['clock-boundaries.json'])
        assert prior==pin['report']and prior['sources_unchanged']
        r['actual_parent_boundary_source']=proof
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        generator=ROOT/'hw/soc/flow/make_pcie_tx_cell.py'
        checker=ROOT/'hw/soc/flow/check_pcie_tx_output14.py'
        circuit=ROOT/'hw/soc/analog/pcie/tx_cml_rsil.spice'
        assert sha(generator)=='78bf226b2d81f821501e5661876068dd60725c005734d770be87fbd857c9be2c'
        assert sha(circuit)=='eec3e2491d7711deaa022343828d2fe8821228ac5b82f4c2f5b1299115017af9'
        legacy=json.loads((ROOT/'docs/evidence/pcie-tx-cell-20260926.json').read_text())
        assert legacy['final']['input_sha256']['hw/soc/flow/make_pcie_tx_cell.py']==sha(generator)
        r['same_legacy_generator']=True
        sources=[generator,checker,Path(__file__),circuit,ROOT/'scripts/audit_tx_output14_binding.py']
        r['inputs']={str(p):sha(p)for p in sources};save()
        r['generation']=execute([app,'python',generator,'--pdk',ROOT/'pdk','--out',OUT/'layout'],OUT,'generate');save()
        assert r['generation']['returncode']==0,(OUT/'generate.log').read_text()[-8000:]
        r['geometry']=json.loads((OUT/'layout/result.json').read_text())
        from audit_tx_output14_binding import check
        r['actual_output_binding']=check(circuit.read_text(),(OUT/'layout/schematic.cir').read_text(),json.loads((OUT/'boundaries/clock-boundaries.json').read_text()));save()
        r['verification']=execute([sys.executable,checker,'--layout',OUT/'layout','--out',OUT/'check','--app',app],OUT,'verify')
        if (OUT/'check/result.json').exists():r['physical_checks']=json.loads((OUT/'check/result.json').read_text())
        save();assert r['verification']['returncode']==0,(OUT/'verify.log').read_text()[-12000:]
        assert r['physical_checks']['status']=='PASS_NATIVE_TX_OUTPUT14_DRC_LVS_AND_SIX_FAULTS_NOT_ELECTRICAL_ACCEPTANCE'
        assert all(sha(Path(p))==v for p,v in r['inputs'].items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r.update(status='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
