#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent native GDS/LEF validation of the source-bound clock macro."""
import argparse,json,os,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_clock_reference_layout_v1'
SOURCES={
'l6p2':dict(summary='3f10b07ee87e5045269232ae178a5594e0c74f81874e8f06177958b9b44ca6b3',parts='1183c86c58129ebb4d83f9f11f5e97d900aa294da461ebc85e92cdbafcacf789',gds='ee1cef81afe91c1afc2257198d090ec375fbe9c6cdf1c74011e7f2e5ac8146a0'),
'l6p5':dict(summary='6a94d45b0fe1a2d7949adcc4bb98dc0b0120652c1a7ab71efe7c93d85350b9ff',parts='df5b6494767da107340dfc03b0d54edc48805e76ed8c768f9fdc7f83e8e9bf5c',gds='bab73526a1ee84c84ee392e249b4d97ac267098de97f54938f8c0c20a4cb51a5')}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('hw/soc/out/cloud-tx-clock-reference-lef-'+args.variant);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,source_run=38941785196,accepted=False,qualified_pex=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        spec=SOURCES[args.variant];source=out/'source'
        prior,proof=reports.restore_report('tx-clock-reference-'+args.variant,38941785196,spec['summary'],spec['parts'],source,
            ('layout/result.json','layout/'+TOP+'.gds','layout/'+TOP+'.lef','layout/schematic.cir'))
        assert prior['source_head']=='4a6550887640d452523888967c76eb709ef60277' and prior['variant']==args.variant
        assert prior['status']=='PASS_NATIVE_CLOCK_REFERENCE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE' and prior['source_unchanged']
        checks=prior['physical_checks']['steps'];assert set(checks)=={'drc','lvs','lvs_flat','wrong_finger_count','wrong_offset_length','missing_hbt','q_open','rail_short','offgrid'}
        assert all(v['status']==('PASS' if k in ('drc','lvs','lvs_flat')else 'REJECTED_EXPECTED_FAULT')for k,v in checks.items())
        assert sha(source/'layout'/ (TOP+'.gds'))==spec['gds'];result['source']=proof
        fixture=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=out/'fixture.tar.gz'
        fetch(fixture['receipt']['url'],fixture['receipt']['sha256'],packed);assert packed.stat().st_size==fixture['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'
        assert not tech.exists(),'Fixture unexpectedly supplies a technology LEF; reconcile provenance first'
        tech.parent.mkdir(parents=True,exist_ok=True)
        tech_url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'
        fetch(tech_url,'e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',tech)
        assert tech.stat().st_size==28396
        result['technology_lef']=dict(url=tech_url,bytes=28396,sha256=sha(tech),upstream_git_blob='0b3558d0277a80e6ca91bd8fd6b82e610f416aa9')
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==fixture['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        from check_pcie_tx_clock_reference_lef import run
        native=out/'inspect-gds.py'
        native.write_text(r"""import pya,json,sys
from pathlib import Path
source=Path(sys.argv[1]);target=Path(sys.argv[2]);topname='nssoc_tx_clock_reference_layout_v1'
L=pya.Layout();L.read(str(source/(topname+'.gds')));top=L.cell(topname)
assert top is not None and L.dbu==0.001
assert str(top.bbox())=='(0,0;126000,89630)'
expected={'avdd':(0,64430,2000,65630),'avss':(0,70430,2000,71630),'cm':(0,76430,2000,77630),'sub':(0,88430,2000,89630)}
labels={}
for s in top.each_shape(L.layer(67,25)):
    assert s.is_text()
    t=s.text;assert t.string not in labels
    labels[t.string]=(t.trans.disp.x,t.trans.disp.y)
assert set(labels)==set(expected)
boxes=[]
for s in top.each_shape(L.layer(67,2)):
    assert s.is_box();b=s.box;boxes.append((b.left,b.bottom,b.right,b.top))
assert sorted(boxes)==sorted(expected.values())
metal=pya.Region(top.begin_shapes_rec(L.layer(67,0))).merged()
for name,coords in expected.items():
    b=pya.Box(*coords);x,y=labels[name]
    assert b.left<=x<=b.right and b.bottom<=y<=b.top
    assert (pya.Region(b)-metal).is_empty()
record=dict(status='PASS_NATIVE_GDS_FOUR_PORTS_OUTLINE_AND_PIN_CONDUCTOR_COVERAGE',dbu=L.dbu,outline_dbu=str(top.bbox()),ports_dbu=expected,labels_dbu=labels)
target.write_text(json.dumps(record,indent=2)+'\n')
print(record['status'])
""")
        compile(native.read_text(),str(native),'exec')
        result['gds_execution']=execute([app,'python',native,source/'layout',out/'gds.json'],out,'gds')
        assert result['gds_execution']['returncode']==0,(out/'gds.log').read_text()
        result['gds_audit']=json.loads((out/'gds.json').read_text());save()
        run(source/'layout',out/'lef',ROOT/'pdk',app)
        result['lef_audit']=json.loads((out/'lef/result.json').read_text());assert result['lef_audit']['status']=='PASS_NATIVE_CLOCK_LEF_FOUR_PINS_AND_THREE_FAULTS'
        assert all(sha(source/p)==v['sha256']for p,v in proof['restore']['selected_files'].items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        result.update(status='PASS_NATIVE_CLOCK_GDS_LEF_AND_THREE_LEF_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        if (out/'lef/result.json').exists():result['lef_audit']=json.loads((out/'lef/result.json').read_text())
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
