#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce measured native XOR collector/supply access resistance in real geometry."""
import json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-xor-collector-access'
TOP='nssoc_cdr_pd484_localbus_v12'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        closed_loop=False,qualified_pex=False,main_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        path_receipts=[]
        for case in ('nominal_early','nominal_late'):
            geometry_pin=json.loads((ROOT/('docs/evidence/cdr-xor-headroom-paths-'+case+'-20261019.json')).read_text())
            diagnosis=geometry_pin['report']
            assert geometry_pin['run']==39311024780
            assert diagnosis['status']=='COMPLETE_ORIGINAL_XOR_SUPPLY_LOAD_TERMINAL_OBSERVATIONS_NOT_ACCEPTANCE'
            assert diagnosis['source_unchanged']and diagnosis['all116original_hbt_checks_reproduced']
            for tag in ('x','y'):
                network=diagnosis['xor_networks'][tag]
                assert len(network['devices'])==59 and len(network['pullups'])==2
                drops=[t['drop_from_public_supply_v']['at_worst_vce']for v in network['pullups'].values()for t in v['terminals']if 'drop_from_public_supply_v'in t]
                assert len(drops)==2 and max(drops)>.27
                assert network['original_failed_check']['minimum_active_vce_v']<.4
            path_receipts.append(dict(run=geometry_pin['run'],case=case,summary_sha256=geometry_pin['summary_sha256']))
        r['measured_xor_paths']=path_receipts
        pin=json.loads((ROOT/'docs/evidence/cdr-source-access-v14-physical-pass-20261019.json').read_text())
        names=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds','layout/'+TOP+'.lef']
        leaves=[n for n in pin['report']['outputs'] if n=='children.json' or n.startswith('inputs/')]
        assert 'children.json' in leaves and len([n for n in leaves if n.endswith('.gds')])==8
        names+=leaves
        original,proof=reports.restore_report('cdr-sampler-source-access',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'baseline',names)
        assert original==pin['report']and original['sources_unchanged']
        assert original['status']=='PASS_PD484_NATIVE_SOURCE_MIDPOINT_ACCESS_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
        assert original['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        r['physical_source']=proof
        for n in leaves:
            source=OUT/'baseline'/n;dest=OUT/n
            assert sha(source)==original['outputs'][n]
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        r['retained_child_sources']={n:sha(OUT/n)for n in leaves}
        capture_pin=json.loads((ROOT/'docs/evidence/cdr-source-access-v14-mim-parent-capture-pass-20261019.json').read_text())
        selected=['wire/anchors08.json','source/wire/device-locations01.json','source/wire/native05/wires.l2n']
        capture,cp=reports.restore_report('cdr-source-access-v14-mim-parent-rc',capture_pin['run'],capture_pin['summary_sha256'],capture_pin['parts_sha256'],OUT/'capture',selected)
        assert capture==capture_pin['report']and capture['sources_unchanged']
        assert diagnosis['capture_source']['summary_sha256']==capture_pin['summary_sha256']
        assert capture['outputs']['source/parent/layout/'+TOP+'.gds']==sha(OUT/'baseline/layout'/(TOP+'.gds'))
        r['native_geometry_source']=cp
        methods=[Path(__file__),ROOT/'scripts/generate_cdr_xor_collector_access.py',
            ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py',
            ROOT/'scripts/cdr_retimed_localbus_v12_parent_plan.py',
            ROOT/'docs/evidence/cdr-xor-headroom-paths-nominal_early-20261019.json',ROOT/'docs/evidence/cdr-xor-headroom-paths-nominal_late-20261019.json']
        protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names],*[OUT/'capture'/n for n in selected]]}
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(Path(n))==v for n,v in protected.items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);save()
        for name,command in [
            ('generation',[app,'python',ROOT/'scripts/generate_cdr_xor_collector_access.py','--out',OUT]),
            ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
            with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            r[name+'_returncode']=code
            if (OUT/'geometry-proof.json').is_file():r['geometry']=json.loads((OUT/'geometry-proof.json').read_text())
            save()
            if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
            assert code==0,('Native source-access stage failed',name,code)
        geometry=r['geometry']
        assert geometry['original_devices']==484 and geometry['route_accesses']==36 and geometry['native_via_stacks']==576
        assert geometry['xor_count']==2 and geometry['bus_count']==6 and geometry['via_group_count']==108
        assert all(geometry[k]for k in ('original_geometry_retained','all_layers_exact','serialized_gds_checked','reference_and_lef_byte_identical'))
        assert len(geometry['rejected'])==3
        r['physical']=json.loads((OUT/'physical/result.json').read_text())
        assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        assert all(sha(Path(n))==v for n,v in protected.items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(OUT/n)==v for n,v in r['retained_child_sources'].items())
        r.update(status='PASS_PD484_NATIVE_XOR_COLLECTOR_ACCESS_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
            sources_unchanged=True,protected_inputs=protected,
            scope='Widen36actual collector/pullup access routes and6local buses in two original XORs with576native single-cut stacks across108existing access groups. Retain all original484devices,source-contact additions,geometry,ports and reference. Original native560DRC/deep+flatLVS/fault gates remain. Fresh RC and all original loaded data/phase/device checks required; no recovered clock or fullPHY acceptance.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name in ('layout','physical'):
            p=OUT/name/'result.json'
            if p.is_file():r[name]=json.loads(p.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
