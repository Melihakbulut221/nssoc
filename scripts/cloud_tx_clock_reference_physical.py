#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Build and physically check the actual native TX clock reference in cloud."""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=['l6p5','l6p2'],required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('hw/soc/out/cloud-tx-clock-reference-'+args.variant);out.mkdir(parents=True,exist_ok=False)
    record=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,accepted=False,qualified_pex=False,electrically_validated=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    try:
        # Recover the exact native launch failure in the cloud, without downloading
        # result archives to the user's machine or changing the physical source.
        import compare_cloud_routed_endpoints as reports
        reports.OUT=out
        failed,proof=reports.restore_report('tx-clock-reference-l6p2',38941349787,
            '3c710802b068b4595cbdd4d07a80c56cbd979eccdb765c8362d8f52e9a622052',
            'd97e5576b5e14caf235700740b08c1b282d7c85d4739a94c3f97be8fd4c30936',
            out/'failed-launch',('check/drc/run.log',))
        assert failed['status']=='FAIL_OR_ERROR'
        assert failed['physical_checks']['steps']['drc']['execution']['returncode']==127
        record['failed_launch_recovery']=proof
        record['failed_native_launch_log']=(out/'failed-launch/check/drc/run.log').read_text()
        print('PRESERVED ORIGINAL NATIVE LAUNCH FAILURE:',record['failed_native_launch_log'],flush=True)
        save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=out/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];record['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        generator=ROOT/'hw/soc/flow/make_pcie_tx_clock_reference_v1.py'
        checker=ROOT/'hw/soc/flow/check_pcie_tx_clock_reference_v1.py'
        sources=[generator,checker,Path(__file__),ROOT/'hw/soc/analog/pcie/tx_clock_common_bias_v3.spice',ROOT/'hw/soc/analog/pcie/tx_clock_bias_feed_v2.spice']
        record['inputs']={str(p):sha(p)for p in sources}
        record['generation']=execute([app,'python',generator,'--pdk',ROOT/'pdk','--out',out/'layout','--variant',args.variant],out,'generate');save()
        assert record['generation']['returncode']==0,(out/'generate.log').read_text()[-8000:]
        record['geometry']=json.loads((out/'layout/result.json').read_text());save()
        record['verification']=execute([sys.executable,checker,'--layout',out/'layout','--out',out/'check','--app',app],out,'verify')
        if (out/'check/result.json').exists():record['physical_checks']=json.loads((out/'check/result.json').read_text())
        save();assert record['verification']['returncode']==0,(out/'verify.log').read_text()[-8000:]
        assert record['physical_checks']['status']=='PASS_NATIVE_CLOCK_REFERENCE6_DRC_LVS_AND_SIX_FAULTS_NOT_ELECTRICAL_ACCEPTANCE'
        assert all(sha(Path(p))==v for p,v in record['inputs'].items())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        record.update(status='PASS_NATIVE_CLOCK_REFERENCE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:record.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        record['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
