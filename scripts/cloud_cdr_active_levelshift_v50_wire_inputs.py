#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind exact v50 native metal/via geometry to all intrinsic device terminals."""
import hashlib,json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-active-levelshift-v50-wire-inputs'
TOP='nssoc_cdr_active_levelshift_layout_v50'
def check():
    m=json.loads((ROOT/'scripts/cdr-active-levelshift-v50-wire-method.json').read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    check()
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,wire_rc_extracted=False,
           full_phy_accepted=False,closed_loop=False,main_chip_integrated=False,
           scope='Exact v50 leaf18native devices,50intrinsic terminals,32metal/18body references and8ports. Geometric conductor graph and native terminal ownership only. No substrate spreading,RF/coupling qualification or full parent acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,label):
        log=OUT/(label+'.log')
        with log.open('w')as f:code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-18000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-active-levelshift-v50-physical-pass-20261024.json').read_text())
        prior,proof=reports.restore_report('cdr-active-levelshift-v50-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',list(pin['outputs']))
        assert prior==pin['report'] and prior['sources_unchanged']
        assert prior['status']=='PASS_CDR_ACTIVE_LEVELSHIFT_V50_LEAF_PHYSICAL_REQUIRES_PARENT_RC_AND_LOADED_WAVES'
        assert prior['layout']['outputs'][TOP+'.gds']=='63fa4e9da52b2890f97e1d7e63857a2e437d7a0d0f5966920dcd21f8b2752913'
        steps=prior['physical']['steps']
        assert steps['drc']['measurement']['markers']==0 and steps['drc']['measurement']['category_count']==560
        for name in ('lvs','lvs_flat'):
            a=steps[name]['audit']
            assert a['status']=='PASS within comparison scope' and not a['extraction_diagnostics']
            assert a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==18
        assert len(steps)==12 and all(s['status']=='REJECTED_EXPECTED_FAULT'for n,s in steps.items()if n not in ('drc','lvs','lvs_flat'))
        r['physical_source']=proof;save()
        methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
        wire=OUT/'wire';wire.mkdir();adaptations={}
        for name in ('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            original=methods[name]['text'];assert hashlib.sha256(original.encode()).hexdigest()==methods[name]['sha256']
            text=original;changes=[]
            def replace(a,b,count=1):
                nonlocal text
                assert text.count(a)==count,(name,a,text.count(a))
                text=text.replace(a,b);changes.append(dict(before=a,after=b,count=count))
            if name!='dedup01.py':
                for old,new in [("/'layout91/","/'parent/layout/"),("/'physical92/lvs/","/'parent/physical/lvs_flat/")]:
                    count=text.count(old);assert count>=1
                    replace(old,new,count)
                replace('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP)
                replace('g.top_cell()',"g.cell("+repr(TOP)+")",2 if name=='locate01.py'else 1)
            if name in ('locate01.py','anchors01.py'):
                replace("('sg13_hv_nmos','B')","('sg13_lv_nmos','B'),('sg13_hv_nmos','B')")
            if name=='probe01.py':
                replace('c.pin_count()==12','c.pin_count()==8')
                replace('dict(npn13G2=19,rppd=8,ptap1=27)','dict(npn13G2=2,sg13_lv_nmos=3,rppd=4,ptap1=9)')
            elif name=='locate01.py':
                replace("models=dict(npn13G2='npn13G2',rppd='rppd',ptap1='ptap1')","models=dict(npn13G2='npn13G2',rppd='rppd',ptap1='ptap1',nmos='sg13_lv_nmos')")
                replace('len(physical)==54','len(physical)==18')
                replace('len(used)==54','len(used)==18')
                replace('PASS_ALL_54_DEVICES','PASS_ALL_18_DEVICES')
            elif name=='anchors01.py':
                replace("elif cls.name in ('sg13_hv_nmos','sg13_hv_pmos'):","elif cls.name in ('sg13_lv_nmos','sg13_hv_nmos','sg13_hv_pmos'):")
                # Original native anchor method already uses the actual TopMetal2 public pins.
                replace('len(rows)==154 and len(anchors)==112','len(rows)==50 and len(anchors)==40')
                replace('PASS_154_NATIVE_TERMINALS_WITH_100_METAL_AND_54_BODY_REFERENCES','PASS_50_NATIVE_TERMINALS_WITH_32_METAL_AND_18_BODY_REFERENCES')
                replace('public_ports=12','public_ports=8')
            else:replace('len(anchors)>12','len(anchors)>8')
            (wire/name).write_text(text)
            adaptations[name]=dict(original_sha256=methods[name]['sha256'],adapted_sha256=sha(wire/name),changes=changes)
        r['method_adaptations']=adaptations;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        for name in adaptations:run([app,'python',wire/name],name)
        r['geometry']=json.loads((wire/'native05/result.json').read_text())
        r['devices']=json.loads((wire/'device-locations01.json').read_text())
        r['anchors']=json.loads((wire/'anchors08.json').read_text());save()
        assert r['geometry']['native_device_count']==18 and r['geometry']['native_terminal_count']==50
        assert r['geometry']['no_wire_geometry_change'] and r['geometry']['no_component_union_by_native_label']
        assert r['devices']['model_census']==dict(npn13G2=2,sg13_lv_nmos=3,rppd=4,ptap1=9)
        assert r['anchors']['logical_anchor_count']==40 and r['anchors']['public_ports']==8
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=32,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=18)
        assert all(sha(OUT/'parent'/n)==v for n,v in prior['outputs'].items())
        assert all(sha(wire/n)==v['adapted_sha256']for n,v in adaptations.items())
        check()
        r.update(status='PASS_V50_NATIVE_LEAF_METAL_GRAPH_AND_ALL50_TERMINAL_ANCHORS_REQUIRES_FRESH_RC',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
