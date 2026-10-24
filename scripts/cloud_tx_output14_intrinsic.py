#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export and validate actual output14 intrinsic devices with eight finite contacts."""
import json,os,re,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
from cloud_tx_driver_localpins_intrinsic import PDK
from run_cloud_tx_layout_repair import sha,fetch
import tx_output14_intrinsic_model as model
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-intrinsic'
TOP='nssoc_tx_output14_intrinsic_v1'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],wire_parasitics_included=False,simulator_checked=False,qualified_pex=False,qualified_substrate=False,full_phy_accepted=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output14-physical-pass-20261021.json').read_text())
        assert pin['run']==39564026768 and pin['summary_sha256']=='8f434b1368bcf613ca2f32c4eeebc528d3e131a243299bf6df09f609c293f9fa'
        source=OUT/'source';selected=('layout/nssoc_tx_cml_layout.gds','layout/result.json','check/lvs/result.lvsdb','check/lvs_flat/result.lvsdb')
        prior,proof=reports.restore_report('tx-output14-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert prior==pin['report']and prior['sources_unchanged'];r['physical_source']=proof
        assert prior['status']=='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE'
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        scripts=[Path(__file__),ROOT/'scripts/tx_output14_intrinsic_model.py',ROOT/'scripts/export_tx_output14_native.py',ROOT/'scripts/build_pcie_local_vco_hybrid_v6.py',ROOT/'scripts/cloud_tx_driver_localpins_intrinsic.py']
        r['protected_sources']={str(p):sha(p)for p in scripts}
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        r['native_export']=execute([app,'python',ROOT/'scripts/export_tx_output14_native.py',source,OUT/'native.json'],OUT,'export');save()
        assert r['native_export']['returncode']==0,(OUT/'export.log').read_text()[-12000:]
        native=json.loads((OUT/'native.json').read_text())
        assert native['gds_sha256']==pin['gds_sha256']
        r['native_topology']=model.validate_native(native);r['native_controls']=model.native_controls(native);save()
        rows=native['modes']['lvs_flat']['devices'];models=OUT/'pdk'
        pins={p:h for p,h in compact.MODEL_PINS.items()if p.endswith(('resistors_mod.lib','sg13g2_hbt_mod.lib','sg13g2_tech.json','utility_functions.py'))}
        for path,digest in pins.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        hbt=(models/'libs.tech/ngspice/models/sg13g2_hbt_mod.lib').read_text(encoding='latin-1')
        res=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text()
        assert len(re.findall(r'^\.subckt\s+npn13G2\s+c\s+b\s+e\s+bn\s*$',hbt,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+rsil\s+1\s+2\s+bn\s*$',res,re.M|re.I))==1
        tap=re.search(r'^\.subckt\s+ptap1\s+1\s+2\s*\n(.*?)^\.ends\s+ptap1',res,re.M|re.S|re.I);assert tap
        assert [line.strip()for line in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',tap[1],re.M)]==['R1 1 2 R=R']
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        text,bindings=model.build(rows,tech,TOP);path=OUT/'output14.spice';path.write_text(text)
        r.update(positive=model.verify(path.read_text(),rows,tech,TOP),bindings=bindings,controls=model.controls(text,rows,tech,TOP,OUT))
        assert len(r['controls'])==8 and all(x['rejected']for x in r['controls'])
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)and all(sha(models/p)==h for p,h in pins.items())
        assert all(sha(Path(p))==h for p,h in r['protected_sources'].items())
        r.update(status='PASS_NATIVE_TX_OUTPUT14_INTRINSIC_EIGHT_FINITE_CONTACTS_AND16_CONTROLS_REQUIRES_RC_COMPOSITION',model_sha256=sha(path),models=dict(commit=PDK,hashes=pins),gds_sha256=native['gds_sha256'],native_database_sha256=native['modes']['lvs_flat']['database_sha256'],sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
