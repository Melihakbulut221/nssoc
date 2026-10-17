#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate fresh physical shunt-v4 CDR core; no reused-layout or full CDR claim."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from audit_tx_final_layout_source import audit
from cloud_corrpre_banked_postcts import sha
from cloud_corrpre_banked_handoff import api,wait_success
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-v4-core-layout'
CHANGES=[("circuit=ROOT/f'hw/soc/analog/pcie/tx_mux2_final_drive_{audit_profile}_layout_core.spice'", "circuit=ROOT/'hw/soc/analog/pcie/cdr_xor_shunt_v4_layout_core.spice'"), ("native=ROOT/f'hw/soc/analog/pcie/tx_mux54_passive_drive_{audit_profile}.spice'", "native=ROOT/'hw/soc/analog/pcie/cdr_xor_core_shunt_v4.spice'"), ('afca836aec7c57b13fb541afe7ba38b8d47f5cc27c65f0129842228b7f46ae6b', '8f42e4c8231700f26ac65bda195ebd500342467aa0ccc94fa0f7a9684f79e94f'), ('56b50efbbc138e8af973c63809799574da4ffb9c79b9ff5b5732c44e7e234df8', '47d444e7c6b28dc1d15960a534dced500604fee1c52d8d0ee4b38e55a14e55de'), ("top=f'nssoc_tx_mux2_final_drive_{audit_profile}_layout_v1'", "top='nssoc_cdr_xor_load_core_layout_v4'"), ("out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'", "out = ROOT / 'hw/soc/out/cloud-cdr-v4-core-layout'")]

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    base=ROOT/'scripts/run_cloud_tx_layout_repair.py'
    core=ROOT/'hw/soc/analog/pcie/cdr_xor_shunt_v4_layout_core.spice'
    native=ROOT/'hw/soc/analog/pcie/cdr_xor_core_shunt_v4.spice'
    assert sha(base)=='312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f'and sha(core)=='8f42e4c8231700f26ac65bda195ebd500342467aa0ccc94fa0f7a9684f79e94f'and sha(native)=='47d444e7c6b28dc1d15960a534dced500604fee1c52d8d0ee4b38e55a14e55de'
    protected={str(p):sha(p)for p in [Path(__file__),base,core,native,ROOT/'scripts/audit_tx_final_layout_source.py']}
    waiting={};wait_file=ROOT/'cloud-cdr-v4-source-wait.json'
    def save_wait():wait_file.write_text(json.dumps(waiting,indent=2)+'\n')
    run=wait_success(39046476349,'.github/workflows/cdr-xor-shunt-v4-cloud.yml',time.monotonic()+18000,waiting,save_wait)
    assert run['head_sha']=='770d1b4dfbdc65a7e7a78353c099d6ba8e9d8c40'and run['run_attempt']==1
    proofs=[]
    for case in ('nominal','hot_low','cold_high','swap_output'):
        group='cdr-xor-shunt-v4-'+case;stem=group+'-39046476349-1'
        release=api('releases/tags/cloud-results-39046476349-1-'+group)
        assets=[a for a in release['assets']if a['name']==stem+'.summary.json'];assert len(assets)==1
        asset=assets[0]
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(asset['id']),'-H','Accept: application/octet-stream'])
        digest=hashlib.sha256(raw).hexdigest()
        assert len(raw)==asset['size']
        if asset.get('digest'):assert asset['digest']=='sha256:'+digest
        report=json.loads(raw)
        assert report['source_head']==run['head_sha']and report['case']==case
        assert report['sources_unchanged']and report['devices_passed']and report['returncode']==0
        assert report['status']=='PASS_NATIVE_XOR_PRIMITIVE_ONLY_NOT_CDR_OR_LAYOUT'
        assert report['samples']==768 and report['native_flags_verified']==19 and not report['diagnostics']
        assert report['zero_source_op_maximum']<1e-9 and report['physical_device_count']==54
        assert len(report['device_checks'])==19
        assert all(v['minimum_active_vce_v']>=.4 and v['maximum_alltime_vce_v']<=1.6 and v['maximum_alltime_abs_ic_a']<.003*v['nx']for v in report['device_checks'].values())
        for suffix,d in [('hw/soc/analog/pcie/cdr_xor_core_shunt_v4.spice',sha(native)),
            ('hw/soc/analog/pcie/cdr_xor_hbt_shunt_v4.spice','670d7cf57a2e5bb986ba6347f4908a3b6e837303a6c94e9396fd3d5a64296ac7'),
            ('scripts/cloud_cdr_xor.py','3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe')]:
            assert [h for p,h in report['protected_inputs'].items()if p.endswith('/'+suffix)]==[d]
        if case=='swap_output':assert report['actual_output_swap_detected']and report['wrong_sign_samples']==768
        else:assert report['data_passed']and report['wrong_sign_samples']==report['below_100mv_samples']==0 and report['minimum_signed_margin_v']>=.1
        proofs.append(dict(case=case,asset=asset['id'],sha256=digest,report=report))
    assert {p['case']for p in proofs}=={'nominal','hot_low','cold_high','swap_output'}
    equivalence=audit(core.read_text(),native.read_text(),profile='v10')
    text=base.read_text()
    for old,new in CHANGES:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    assert hashlib.sha256(text.encode()).hexdigest()=='9d036ed7872f5651b37b2f6a775b55710241bb59d65299e76359d50e6fd3cfca'
    generated=ROOT/'scripts/_cloud_cdr_v4_core_layout_generated.py';assert not generated.exists();generated.write_text(text)
    command=[sys.executable,generated,'--variant','critical_buses_kelvin_low_ports_loads_shunts_series_left_outputs',
        '--circuit-profile','final_drive_v10','--boundary-pins','--boundary-policy','nearest_pair_tight']
    try:
        subprocess.run(list(map(str,command)),cwd=ROOT,check=True)
        result=json.loads((OUT/'result.json').read_text())
        assert result['status']=='PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
        assert result['physical']['status']=='PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
        assert result['generated_reference_equivalence']['native_sha256']==sha(native)
        assert result['generated_reference_equivalence']['core_sha256']==sha(core)
        assert all(sha(Path(p))==v for p,v in protected.items())
        result.update(status='PASS_CDR_SHUNT_V4_CORE_PHYSICAL_REQUIRES_XOR_PARENT_ROUTING_RC_AND_WAVES',sources_unchanged=True)
    except BaseException as error:
        OUT.mkdir(parents=True,exist_ok=True)
        result=json.loads((OUT/'result.json').read_text())if (OUT/'result.json').exists()else{}
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result.update(source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,cdr_accepted=False,
            xor_parent_routed=False,physical_core_only=True,native_source_proofs=proofs,
            generator_contract=equivalence,protected_inputs=protected,source_adaptations=CHANGES,
            source_generator_sha256='312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f',adapted_generator_sha256='9d036ed7872f5651b37b2f6a775b55710241bb59d65299e76359d50e6fd3cfca',
            scope='Fresh54device shunt-v4 mux core geometry, strict native560rule DRC/hierarchical-flat LVS and five actualfaults. Exact two1.8um collector loads, two8um output shunts and all27contacts. Separate12coreports: crossed XOR parent routes, freshRC/loaded waveform/realphase detector/fullCDR/mainchip are still required. v10 identifies inherited generator sizing policy only, not an unchanged v10 circuit.')
        (OUT/'adapted-controller.py').write_text(text)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
