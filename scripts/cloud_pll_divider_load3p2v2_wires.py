#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Actual divider3p2 unsimplified native devices and metal/via graph, before RC.
import json,os,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-divider-load3p2v2-wires'
TOP='nssoc_clock_div4_load3p2_v2_layout'
GDS_SHA='265d5245f5b406aa20c20647afbe9d87ad9e8f1493cfe3cae3fed9d64885a71b'
METHOD_SHA='171fba4772907101b840342696477c377e4f249dd915a9761a2f6f1b9b479225'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,wire_rc_extracted=False,qualified_pex=False,full_phy_complete=False,scope='Hash-bound actual3p2 divider. Native no-simplify/uncombined deep+flat LVS preserves all91 physical primitives and283 terminals. Raw reference faults and geometry-owned metal/via graph required. No electrical, acquisition or qualifiedPEX acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        source=OUT/'source';selected=('layout/'+TOP+'.gds','layout/result.json','layout/schematic.cir')
        prior,proof=reports.restore_report('pll-divider-load3p2v2-physical',38975762261,'f20bddda06c6d1765645de357ed50710127cc2af4bda3a796516bf31eb25124d','0566cf48bfdb598c0392a1598a6b07e21df7e1519911f53335422e14e97d0011',source,selected)
        assert prior['status']=='PASS_DIVIDER_LOAD3P2V2_PARENT_FIRST_LOADS_RESTORED_NATIVE_PHYSICAL_SCREEN_REQUIRES_FRESH_RC_AND_ACQUISITION'
        assert prior['source_head']=='9aa04e1f255aef3ccacf49b917f929761f4087ff'
        gds=source/'layout'/(TOP+'.gds');assert sha(gds)==GDS_SHA;r['source']=proof
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());pack=OUT/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],pack)
        with tarfile.open(pack)as t:t.extractall(ROOT,filter='data')
        pack.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256'];r['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        from check_pcie_clock_div4_load3p2_v2 import physical_reference,fault_reference
        from prepare_ihp_drc import validate_lock,verify
        assert (source/'layout/schematic.cir').read_text()==physical_reference(ROOT)
        lock=json.loads((ROOT/'hw/soc/pnr/ihp-lvs.lock.json').read_text());validate_lock(lock)
        assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
        for row in lock['files']:verify((ROOT/'hw/soc/tools/ihp-lvs-5e6d592'/row['path']).read_bytes(),row)
        entry=ROOT/'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs'
        for name,mode,fault in [('raw_deep','deep',None),('raw_flat','flat',None),('wrong_load','flat','collector_load_reverted'),('wrong_first_load','flat','first_stage_parent_load_reverted'),('missing_tap','flat','missing_tap'),('wrong_nx','flat','limiter_nx')]:
            d=OUT/name;d.mkdir();reference=source/'layout/schematic.cir'
            if fault:
                text=fault_reference(reference.read_text(),fault);reference=d/'wrong.cir';reference.write_text(text)
            opts=['input='+str(gds),'topcell='+TOP,'log='+str(d/'deck.log'),'run_mode='+mode,'schematic='+str(reference),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),'thr=2','no_simplify=true','top_lvl_pins=true','combine_devices=false']
            cmd=[app,'klayout','-b','-zz','-r',entry]
            for option in opts:cmd+=['-rd',option]
            step=dict(name=name,mode=mode,combine_devices=False,no_simplify=True);r.setdefault('steps',[]).append(step)
            step['execution']=execute(cmd,d,'run');save();assert step['execution']['returncode']==0
            step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',TOP,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
            audit=json.loads((d/'audit.json').read_text());step['audit']=audit;save()
            if fault:assert step['audit_execution']['returncode']==1 and audit['status']=='FAIL'and audit['circuit_status_counts'].get('NoMatch',0)>0
            else:
                assert step['audit_execution']['returncode']==0 and audit['status']=='PASS within comparison scope'
                assert len(audit['circuits'])==1 and audit['circuits'][0]['layout_devices_recursive']==91 and audit['circuits'][0]['schematic_devices_recursive']==91
        method=ROOT/'scripts/tx_driver_localpins_wire_native.py';assert sha(method)==METHOD_SHA;original=method.read_text();adapted=original
        edits=[
          ('nssoc_tx_input_driver_v7_physical_localpins_v1',TOP),
          ("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B/'source'"),
          ("P/'base/layout.gds'","P/'layout/"+TOP+".gds'"),
          ("P/'check-raw_flat_lvs/","B/'raw_flat/"),
          ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',GDS_SHA),
          ('c.pin_count()==6','c.pin_count()==7'),
          ('dict(sg13_hv_nmos=40,sg13_lv_nmos=22,sg13_lv_pmos=22,ptap1=10,ntap1=2,rppd=4)','dict(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)'),
          ("'full_driver_wires'","'divider_load3p2_wires'"),
          ("'DRIVERWIRES'","'DIVIDERWIRES'"),
          ('PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC','PASS_DIVIDER3P2_METAL_VIA_GRAPH_BOUND_TO_ALL91_NATIVE_DEVICES_NO_RC')]
        for a,b in edits:
            assert adapted.count(a)==(2 if a=="P/'check-raw_flat_lvs/"else 1),(a,adapted.count(a));adapted=adapted.replace(a,b)
        back=adapted
        for a,b in reversed(edits):back=back.replace(b,a)
        assert back==original
        native=OUT/'probe.py';native.write_text(adapted);r['graph_method']=dict(original_sha256=METHOD_SHA,adapted_sha256=sha(native),exact_edits=edits,geometry_algorithm_unchanged=True)
        r['graph_execution']=execute([app,'python',native],OUT,'graph');save();assert r['graph_execution']['returncode']==0
        graph=json.loads((OUT/'native01/result.json').read_text())
        assert graph['native_device_count']==91 and graph['native_terminal_count']==283
        assert set(graph['native_ports'])=={'CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB'}
        assert graph['no_wire_geometry_change']and graph['no_component_union_by_native_label']
        assert all(sha(source/p)==prior['outputs'][p]for p in selected)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r.update(graph=graph,source_unchanged=True,status='PASS_DIVIDER3P2V2_RAW91_LVS_FOUR_FAULTS_AND_METAL_GRAPH_NOT_TERMINAL_RC_OR_ELECTRICAL_ACCEPTANCE')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
