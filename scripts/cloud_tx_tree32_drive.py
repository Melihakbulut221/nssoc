#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native lower-output-impedance full32 candidate, never old-layout acceptance."""
import argparse,hashlib,importlib.util,json,os,sys
from fractions import Fraction
from pathlib import Path
import cloud_tx_tree32_budget as original
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='52999bc99256be7e2c414324a097d869e9bce81bdd2762720e522de79d4230f4'
EDITS=[{'before': 'budget_high3_trim', 'after': 'budget_drive_v1', 'count': 5}, {'before': 'cloud-tx-tree32-budget-', 'after': 'cloud-tx-tree32-drive-', 'count': 1}, {'before': 'low_output_resistor_l_um=30.,high_output_resistor_l_um=15.4', 'after': 'low_output_resistor_l_um=12.77,high_output_resistor_l_um=6.55', 'count': 1}]
ADAPTED_SHA='19e9d9f3c644a8e97938d5a9a548f8c296fe41f37cc1a730f9bcefd5f9d41227'

def candidate(text,nx):
    before,prior=original.trim_dividers(text,nx)
    rows=original.records(before);expected=[list(x)for x in rows]
    assert nx in (1,3)
    dims={'XSP':('4','3.6'),'XSN':('4','3.6'),'XFPR':('1','12.77'),'XFNR':('1','12.77')}if nx==1 else{'XSP':('6','1.8'),'XSN':('6','1.8'),'XFPR':('1.5','6.55'),'XFNR':('1.5','6.55')}
    changes=[]
    for row in expected:
        if row[0]not in dims:continue
        assert row[4]=='rppd'and row[7:]==['b=0','sw_et=1']
        w,l=dims[row[0]];old=list(row);row[5:7]=['w='+w+'u','l='+l+'u'];changes.append(dict(before=old,after=list(row)))
    assert len(changes)==4
    assert [x for x in rows if 'npn13G2'in x]==[x for x in expected if 'npn13G2'in x]
    assert [x for x in rows if x[0]not in dims]==[x for x in expected if x[0]not in dims]
    def verify(text):assert original.records(text)==expected,'Unspecified native device, topology or geometry change'
    candidate='* Lower-output-impedance candidate; new native PVT/layout/RC required.\n'+'\n'.join(' '.join(x)for x in expected)+'\n'
    verify(candidate);faults=[]
    for label in ('unmodified_series','wrong_shunt','hbt_area','data_terminal'):
        bad=[list(x)for x in expected]
        if label=='unmodified_series':next(x for x in bad if x[0]=='XSP')[5]=next(x for x in rows if x[0]=='XSP')[5]
        elif label=='wrong_shunt':next(x for x in bad if x[0]=='XFPR')[6]='l=999u'
        elif label=='hbt_area':next(x for x in bad if x[0]=='XAP_0')[-1]='Nx=99'
        else:next(x for x in bad if x[0]=='XAP_0')[2]='wrong_data'
        try:verify('\n'.join(' '.join(x)for x in bad))
        except AssertionError:faults.append(label)
        else:raise AssertionError('Actual candidate corruption accepted')
    def ratio(table,name):
        row=next(x for x in table if x[0]==name)
        return Fraction(row[6][2:-1])/Fraction(row[5][2:-1])
    assert ratio(expected,'XSP')/ratio(rows,'XSP')==Fraction(1,4)
    # First-order constant-current collector/load-divider equation only.
    rc,rs,rf=(ratio(rows,name)for name in ('XRP','XSP','XFPR'))
    ideal_alpha=(rc+rs/4)/(rc+rs);assert ideal_alpha==Fraction(20,47)
    actual_alpha=ratio(expected,'XFPR')/rf
    assert abs(actual_alpha/ideal_alpha-1)<Fraction(1,1000)
    return candidate,dict(parent_trim=prior,changes=changes,series_L_over_W_ratio='1/4',first_order_shunt_ratio='20/47',actual_shunt_ratio=str(actual_alpha),geometry_rounding_relative_error=float(actual_alpha/ideal_alpha-1),rejected_controls=faults,hbt_sizes_and_connections_unchanged=True,original_primitive_source_sha256=original.SOURCE_SHA,candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),physical_layout_matches=False,scope='First-order divider matching is a design hypothesis, not DC/PVT equivalence. Native compact parasitics and self-heating are recomputed; original physical RC cannot be reused.')

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert hashlib.sha256((ROOT/'scripts/cloud_tx_tree32_budget.py').read_bytes()).hexdigest()==BASE_SHA
    result={}
    for nx in (1,3):
        source,_=original.resized(original.SOURCE.read_text(),nx);text,proof=candidate(source,nx)
        assert len(proof['rejected_controls'])==4
        assert sum('npn13G2'in x for x in original.records(text))==19
        assert sum('rppd'in x for x in original.records(text))==8
        result[nx]=proof
    assert 28*19+2*55+77==719
    print(json.dumps(result,indent=2),flush=True)
    return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if sys.argv[1:]==['--controls']:controls();return
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=['budget_drive_v1'],required=True);p.add_argument('--fault',choices=['none','swap_leaf_select'],required=True);p.add_argument('--condition',choices=['nominal','hot_low','cold_high'],required=True);args=p.parse_args()
    proofs=controls();base=ROOT/'scripts/cloud_tx_tree32_budget.py';text=base.read_text()
    for edit in EDITS:
        assert text.count(edit['before'])==edit['count'];text=text.replace(edit['before'],edit['after'])
    assert hashlib.sha256(text.encode()).hexdigest()==ADAPTED_SHA
    generated=ROOT/'scripts/_cloud_tx_tree32_drive_native.py';assert not generated.exists();generated.write_text(text)
    spec=importlib.util.spec_from_file_location('tree32_drive_native',generated);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.trim_dividers=candidate
    out=ROOT/('cloud-tx-tree32-drive-budget_drive_v1-'+args.fault+(''if args.condition=='nominal'else'-'+args.condition))
    script_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:module.main()
    finally:
        out.mkdir(exist_ok=True);path=out/'result.json';r=json.loads(path.read_text())if path.exists()else dict(status='FAIL_BEFORE_NATIVE_REPORT')
        r.update(candidate='budget_drive_v1',original_controller_sha256=BASE_SHA,adapted_controller_sha256=ADAPTED_SHA,controller_adaptations=EDITS,output_impedance_candidate_proofs=proofs,accepted=False,physical_layout_matches=False,full_serial_phy_complete=False,scope='Full32 native schematic candidate: original604HBT/512MOS,719treeemitters, fixed clock and sourcebits, all34ns/256bit/threephase and device gates preserved. Lower native output resistors only; no reused physical RC, no loaded-wire, layout or PHY acceptance.')
        assert hashlib.sha256(base.read_bytes()).hexdigest()==BASE_SHA and hashlib.sha256(generated.read_bytes()).hexdigest()==ADAPTED_SHA
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==script_sha
        r['candidate_controller_sha256']=script_sha
        path.write_text(json.dumps(r,indent=2)+'\n')
    if args.fault=='none':assert r.get('schematic_screen_passed')is True,'Native candidate failed original engineering gates'
    else:assert r.get('actual_leaf_fault_rejected_by_original_bits')is True
if __name__=='__main__':main()
