#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume only missing LEF checks from immutable successful native pump proofs."""
import json,os,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-filter-lef'
TECH_SHA='e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6'
def restore_technology():
    tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'
    tech.parent.mkdir(parents=True,exist_ok=True)
    fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef',TECH_SHA,tech)
    assert tech.stat().st_size==28396
    return tech

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],physical_source_run=38848309907,size_um=9,accepted=False,parent_integrated=False,qualified_pex=False,serial_phy_complete=False,
        scope='Restore exact published9um pump GDS/LEF and successful native DRC/deep+flat LVS/fault evidence. Execute only previously missing native LEF positive/missing-pin/blocked-pin checks. No repeated electrical capture or parent/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38848309907-1-pll-filter-layout-9/'
        stem='pll-filter-layout-9-38848309907-1'
        summary_sha='ae90bac4182e79be42f41aedea9605ade46d2f80b5a127c7f38f7b25534ba0ad'
        parts_sha='f52d7d03da41475095a6067b958c99d629a959da9829e58e6915148d297e525b'
        archive_sha='2a8e067beb6b2598a3eab4bc88d79acf0b5a5e8cb4a2f26a214a36c0629297cf'
        fetch(base+stem+'.summary.json',summary_sha,OUT/'source-summary.json')
        fetch(base+stem+'.parts.json',parts_sha,OUT/'source-parts.json')
        prior=json.loads((OUT/'source-summary.json').read_text());manifest=json.loads((OUT/'source-parts.json').read_text())
        assert prior['source_head']=='8380558b46bbc150b7d3e459e8f47be2fd260313' and prior['size_um']==9
        assert prior['status']=='FAIL_OR_ERROR' and prior['error'].startswith('FileNotFoundError(')
        assert prior['physical']['status']=='PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS'
        assert {k:v['status'] for k,v in prior['physical']['steps'].items()}=={k:('PASS' if k in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT') for k in ('drc','lvs','lvs_flat','wrong_width','missing_well','vctrl_open','rail_short','offgrid')}
        expected=dict(index=0,name=stem+'.tar.gz.part0000',bytes=248708,sha256=archive_sha)
        assert manifest['format']=='ordered-tar-gzip-parts-v1' and manifest['parts']==[expected]
        assert manifest['bytes']==248708 and manifest['sha256']==archive_sha
        packed=OUT/'source.tar.gz';fetch(base+expected['name'],archive_sha,packed);assert packed.stat().st_size==248708
        dest=OUT/'restored';dest.mkdir()
        with tarfile.open(packed) as tar:
            members=tar.getmembers();assert len(members)==len({m.name for m in members})
            for m in members:
                p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='cloud-pll-filter-layout'
                assert m.isfile() or m.isdir()
            tar.extractall(dest,filter='data')
        packed.unlink();source=dest/'cloud-pll-filter-layout'
        assert sha(source/'result.json')==summary_sha
        assert all(sha(source/n)==v for n,v in prior['outputs'].items())
        assert all(sha(source/'layout'/n)==v for n,v in prior['layout']['outputs'].items())
        r['source_evidence']=dict(summary_sha256=summary_sha,parts_sha256=parts_sha,archive_sha256=archive_sha,layout_outputs=prior['layout']['outputs'],physical_status=prior['physical']['status']);save()
        tech=restore_technology();r['technology_sha256']=sha(tech);save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256'];r['runtime_sha256']=sha(app)
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        import check_pcie_pump_filter13_lef as checker
        checker.TOP='nssoc_pump_filter13_rhi140_c9_v1'
        checker.run(source/'layout',OUT/'lef',ROOT/'pdk',app)
        r['lef']=json.loads((OUT/'lef/result.json').read_text());assert r['lef']['status']=='PASS_NATIVE_LEF_AND_TWO_PHYSICAL_FAULTS'
        assert all(sha(source/n)==v for n,v in prior['outputs'].items()) and sha(tech)==TECH_SHA
        r['status']='PASS_RESTORED_PUMP_LEF_WITH_PRIOR_DRC_LVS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        if (OUT/'lef/result.json').exists():r['lef']=json.loads((OUT/'lef/result.json').read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
