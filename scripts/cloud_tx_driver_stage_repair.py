#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound next headroom/drive hypotheses; no physical adoption."""
import hashlib,json,os
from pathlib import Path
from build_pcie_local_vco_hybrid_v6 import statements
from run_cloud_tx_layout_repair import sha
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-stage-repair-controls'
DRIVER_SHA='8eec4846d8cef0e3367c07f8e1a0f3413f4a628684bbb1a283c6f6883b95ad79'
CLOCK_SHA='da579518bd5140afc4e68545020524c3877a0119e2786c04833bc2e3e26ff199'
CLOCK=ROOT/'hw/soc/analog/pcie/tx_clock_common_bias_v3.spice'

def source_driver(text,intrinsic,composition):
    assert hashlib.sha256(text.encode()).hexdigest()==DRIVER_SHA,'Wrong physical pullup parent'
    rows=statements(text);byname={r[0]:r for r in rows[1:-1]}
    assert len(byname)==len(rows)-2==655
    assert sum(r[0].startswith('XD')for r in rows[1:-1])==100
    assert sum(r[0].startswith('R')for r in rows[1:-1])==260 and sum(r[0].startswith('C')for r in rows[1:-1])==295
    bound=[r for r in intrinsic['bindings']if r['instance']=='XD86'];assert len(bound)==1
    binding=bound[0];assert binding['model']=='rppd' and binding['nodes']==['sink','dout','BULK']
    assert binding['compact_parameters']==dict(w='2.0u',l='6.92u',ps='0.0u',b='0',m='1',sw_et='1')
    linked=[r for r in composition['bindings']if r['instance']=='XD86'];assert len(linked)==1
    assert [b['terminal']for b in linked[0]['bindings']]==binding['named_terminal_order']
    nodes=[b['node']for b in linked[0]['bindings']]
    assert byname['XD86']==['XD86',*nodes,'rppd',*[k+'='+v for k,v in binding['compact_parameters'].items()]]
    return rows

def series_candidate(original,intrinsic,composition):
    rows=source_driver(original,intrinsic,composition)
    expected=[list(r)for r in rows]
    row=next(r for r in expected if r[0]=='XD86');assert row.count('l=6.92u')==1;row[row.index('l=6.92u')]='l=6.2u'
    def verify(candidate):assert statements(candidate)==expected,'Undeclared device, wire or model boundary change'
    lines=original.splitlines();index=next(i for i,l in enumerate(lines)if l.startswith('XD86 '));lines[index]=' '.join(row)
    candidate='\n'.join(lines)+'\n';verify(candidate)
    controls=[]
    for fault in ['gate_damping_changed','wire_resistance_changed']:
        bad=[list(r)for r in expected]
        if fault=='gate_damping_changed':
            r=next(r for r in bad if r[0]=='XD85');length=next(i for i,s in enumerate(r)if s.startswith('l='));r[length]='l=6u'
        else:next(r for r in bad if r[0].startswith('R'))[3]='123456'
        badtext='\n'.join(' '.join(r)for r in bad)+'\n'
        try:verify(badtext)
        except AssertionError as e:controls.append(dict(fault=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    return candidate,dict(instance='XD86',logical_nodes=['sink','dout','BULK'],width_um=2,original_length_um=6.92,candidate_length_um=6.2,
        original_sha256=DRIVER_SHA,candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),controls=controls,old_interconnect_frozen=True,physically_realized=False)

def clock_candidate(original):
    assert hashlib.sha256(original.encode()).hexdigest()==CLOCK_SHA,'Clock reference source drift'
    before='XOFFSET er avss sub rppd w=4u l=6.5u b=0 sw_et=1';after=before.replace('l=6.5u','l=6.2u')
    assert original.splitlines().count(before)==1
    candidate=original.replace(before,after);expected=statements(candidate)
    assert candidate.replace(after,before)==original
    def verify(text):assert statements(text)==expected,'Undeclared clock reference change'
    verify(candidate);controls=[]
    for fault,bad in [('clock_HBT_changed',candidate.replace('Nx=1','Nx=2')),('offset_missing',candidate.replace(after+'\n',''))]:
        assert bad!=candidate
        try:verify(bad)
        except AssertionError as e:controls.append(dict(fault=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    return candidate,dict(instance='XOFFSET',width_um=4,original_length_um=6.5,candidate_length_um=6.2,original_sha256=CLOCK_SHA,candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),controls=controls,
        current_source_added=False,clock_phase_or_amplitude_changed=False,physically_realized=False)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir();reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,simulator_checked=False,physical_change=False,serial_phy_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        source=OUT/'source';base='inputs/tx-driver-pullup-intrinsic-l2p4/result.json'
        prior,proof=reports.restore_report('tx-driver-pullup-compose-l2p4',38935779019,
            'cf6515591ce239ff9a482d88fb01088173a0204803c62d344da724e00cf52ffd',
            '7acd44238caaf6314ca7df89fccb4bfe780b67858b0b334b8c59d4a8a049ef79',source,('driver100-wire.spice',base))
        assert prior['source_unchanged'] and prior['variant']=='l2p4' and len(prior['controls'])==10
        original=(source/'driver100-wire.spice').read_text();intrinsic=json.loads((source/base).read_text())
        assert intrinsic['variant']=='l2p4' and len(intrinsic['controls'])==8
        candidate,result['series']=series_candidate(original,intrinsic,prior);(OUT/'series-candidate.spice').write_text(candidate)
        candidate,result['clock']=clock_candidate(CLOCK.read_text());(OUT/'clock-candidate.spice').write_text(candidate)
        assert all(sha(source/p)==v['sha256']for p,v in proof['restore']['selected_files'].items()) and sha(CLOCK)==CLOCK_SHA
        result.update(status='PASS_SOURCE_BOUND_STAGE_REPAIR_AND_FOUR_UNDECLARED_CHANGE_CONTROLS_NOT_ELECTRICAL_ACCEPTANCE',source=proof,source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
