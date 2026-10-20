#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native cloud-only28-route capacitance candidate with unmodified physical gates."""
import json,os,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-fast-wire20-physical'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        log=OUT/(label+'.log')
        with log.open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-12000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        from check_tx_fast_wire20_sources import check
        check()
        pin=json.loads((ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json').read_text())
        selected=[n for n in pin['outputs']if n.startswith('layout/')]+['verify-tree32.py']
        prior,proof=reports.restore_report('tx-v5-timing-priority-assembly',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['status']=='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert prior['physical']['steps']['drc']['measurement']['markers']==0
        r['physical_source']=proof
        # Restore exact pinned PDK/native flow inputs as in the accepted baseline.
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime-source.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        run([app,'python',ROOT/'scripts/generate_tx_fast_wire20.py',OUT],'native-geometry')
        r['geometry_delta']=json.loads((OUT/'geometry-delta.json').read_text())
        r['layout']=json.loads((OUT/'layout/result.json').read_text());save()
        verification=OUT/'source/verify-tree32.py'
        assert sha(verification)==pin['outputs']['verify-tree32.py']
        run([sys.executable,verification,'--layout',OUT/'layout','--out',OUT/'physical','--app',app],'original-native-physical-gates')
        r['physical']=json.loads((OUT/'physical/result.json').read_text())
        assert r['physical']['status']=='PASS_NATIVE_PDK_TX_TREE1674_DRC_LVS_AND_FAULT_CONTROLS'
        assert r['physical']['steps']['drc']['measurement']['category_count']==560
        assert r['physical']['steps']['drc']['measurement']['markers']==0
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        check();r['sources_unchanged']=True
        r['status']='PASS_TX28_FAST_DATA_WIRE20_NATIVE_PHYSICAL_REQUIRES_FRESH_RC_AND_LOADED_GATES'
    except BaseException as e:
        r.update(status='FAIL_OR_ERROR',error=repr(e))
        if (OUT/'physical/result.json').exists():r['physical']=json.loads((OUT/'physical/result.json').read_text())
        raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
