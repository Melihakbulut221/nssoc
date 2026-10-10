# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fixed physical hierarchy, complete clock graph and strict native result guards."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_clocked_bank_v3 as make
import check_pcie_clocked_bank_v3 as check
import make_pcie_analog_bank_v2 as bank
import make_pcie_clock_vco as vco
import make_pcie_rx_cell_v2 as rx
import make_pcie_sampler_cell as sampler
from test_pcie_sampler_layout import tx_reference


@pytest.fixture
def parents():
    primitives = dict(TX=tx_reference(),
                      RX=rx.physical_reference((ROOT/'hw/soc/analog/pcie/rx_hbt_rsil_v2.spice').read_text()),
                      SAMPLER=sampler.physical_reference((ROOT/sampler.CIRCUIT).read_text()))
    return dict(BANK=bank.reference(primitives), VCO=vco.physical_reference((ROOT/vco.CIRCUIT).read_text()))


def test_clock_graph_connects_actual_follower_and_all_four_latches(parents):
    text=make.reference(parents)
    rows={f[0]:f for f in map(str.split,text.splitlines()) if f and f[0][0] in 'QRCM'}
    assert len(rows)==sum(make.COUNTS.values())==303
    assert len(make.PORTS)==len(set(make.PORTS))==54
    assert not any('CLK' in n or 'CLOCK' in n for n in make.PORTS)
    assert rows['QVCO_FP'][1:5]==['AVDD2V3','VCO_BO_P','CLOCKP','BULK']
    assert rows['QVCO_FN'][1:5]==['AVDD2V3','VCO_BO_N','CLOCKN','BULK']
    for lane in range(4):
        assert rows[f'QBANK_{lane}SAMPLER_M_CS'][2]=='CLOCKN'
        assert rows[f'QBANK_{lane}SAMPLER_M_CH'][2]=='CLOCKP'
        assert rows[f'QBANK_{lane}SAMPLER_S_CS'][2]=='CLOCKP'
        assert rows[f'QBANK_{lane}SAMPLER_S_CH'][2]=='CLOCKN'
        assert rows[f'RBANK_{lane}SAMPLER_IP'][1]==f'L{lane}_RX_OUTP'
        assert rows[f'RBANK_{lane}SAMPLER_IN'][1]==f'L{lane}_RX_OUTN'
    assert sum(f[0].startswith('Q') for f in rows.values())==110
    assert sum('ptap1' in f for f in rows.values())==104
    assert sum('ntap1' in f for f in rows.values())==1
    assert not any(f[0].startswith(('V','I')) for f in rows.values())


def test_three_rails_and_real_finite_substrate_well_contacts_stay_distinct(parents):
    text=make.reference(parents)
    assert 'MVCO_CTRL VCO_REF VCTRL AVDD2V3 VCO_NWELL sg13_hv_pmos' in text
    assert 'RVCO_NTAP AVDD2V3 VCO_NWELL ntap1 A=4p P=8u' in text
    assert 'RBANK_0RX_RP AVDD1V8 L0_RX_OUTP BULK' in text
    assert 'RBANK_0SAMPLER_M_RP AVDD2V5 L0_SAMPLER_MP BULK' in text
    assert 'RVCO_RP0 AVDD2V3 VCO_P0 BULK' in text
    for name in ('AVDD1V8','AVDD2V5','AVDD2V3'):
        assert make.use_direction(name)==('POWER','INOUT')
    assert make.use_direction('VCTRL')==('SIGNAL','INPUT')
    assert make.use_direction('SUB')==make.use_direction('AVSS')==('GROUND','INOUT')
    assert ' AVDD ' not in text and ' NWELL ' not in text


@pytest.mark.parametrize('kind',['BANK','VCO'])
def test_missing_device_or_changed_parent_ports_rejected(parents,kind):
    lines=parents[kind].splitlines()
    wrong=dict(parents);wrong[kind]='\n'.join(lines[:3]+lines[4:])+'\n'
    with pytest.raises(ValueError):
        make.reference(wrong)
    wrong=dict(parents);wrong[kind]=parents[kind].replace(' AVSS ',' EXTRA ',1)
    with pytest.raises(ValueError,match='port contract'):
        make.reference(wrong)


@pytest.mark.parametrize('fault',check.REFERENCE_FAULTS)
def test_literal_reference_faults_bind_once_and_reject_missing_or_ambiguous(parents,fault):
    text=make.reference(parents);changed=check.fault_reference(text,fault)
    assert changed!=text and changed.splitlines()[2]==text.splitlines()[2]
    for bad in ('',text+text,changed):
        with pytest.raises(ValueError):
            check.fault_reference(bad,fault)


def positive():
    return dict(name='lvs',audit_execution={'returncode':0},audit={'status':'PASS within comparison scope',
                'circuit_status_counts':{'Match':1},'circuits':[{'layout_devices_recursive':200,'schematic_devices_recursive':200}]})


def test_native_success_requires_complete_200_devices_and_all54_exact_ports():
    header='.subckt '+make.TOP+' '+' '.join(make.PORTS)
    step=positive();check.validate_lvs(step,header,True)
    for path,value in [(('audit_execution','returncode'),1),(('audit','status'),'FAIL'),
                       (('audit','circuits'),[]),(('audit','circuits'),[{'layout_devices_recursive':199,'schematic_devices_recursive':200}])]:
        changed=copy.deepcopy(step);obj=changed
        for key in path[:-1]:
            obj=obj[key]
        obj[path[-1]]=value
        with pytest.raises(ValueError):
            check.validate_lvs(changed,header,True)
    for changed in (header.replace(' VCTRL',''),header.replace(' VCTRL',' EXTRA'),header.replace(' AVDD2V3',' AVDD2V5')):
        with pytest.raises(ValueError):
            check.validate_lvs(step,changed,True)


def test_real_internal_clock_open_must_produce_native_nomatch_not_runtime_error():
    step=dict(name='clock_open',audit_execution={'returncode':1},audit={'status':'FAIL','circuit_status_counts':{'NoMatch':1}})
    check.validate_lvs(step,'',False)
    step['audit']['circuit_status_counts']={}
    with pytest.raises(ValueError):
        check.validate_lvs(step,'',False)
    step['audit_execution']['returncode']=2
    with pytest.raises(ValueError):
        check.validate_lvs(step,'',False)


def test_control_open_requires_the_specific_missing_boundary_port():
    step=dict(name='vctrl_open',audit_execution={'returncode':1},audit={'status':'FAIL'})
    header='.subckt '+make.TOP+' '+' '.join(p for p in make.PORTS if p!='VCTRL')
    check.validate_lvs(step,header,False)
    with pytest.raises(ValueError):
        check.validate_lvs(step,header+' VCTRL',False)


def generated():
    return dict(ports={n:dict(rect_um=[100+20*i,0,104+20*i,4]) for i,n in enumerate(make.SUPPLIES)},
                clock_connections=[dict(sink='L2_SAMPLER_CLKP',branch=dict(rect_um=[30,1805,101,1807]))],
                routes=[dict(net=n,layer='TopMetal2',rect_um=[x-2,500,x+2,2800]) for n,x in (('CLOCKP',30),('CLOCKN',50))])


@pytest.mark.parametrize('fault',(*check.PHYSICAL_FAULTS,'offgrid'))
def test_actual_conductor_mutation_targets_complete_branch_or_rails(fault):
    data=generated();data['ports']['VCTRL']=dict(rect_um=[0,2815,2,2817])
    code=check.mutation_source(Path('/native.gds'),Path('/wrong.gds'),data,fault)
    compile(code,'physical_control','exec')
    if fault=='clock_open':
        assert 'DBox(70,1804.0,74,1808.0)' in code and 'region-=' in code
    elif fault=='vctrl_open':
        assert 'DBox(3,2814.0,4,2818.0)' in code
    elif fault=='offgrid':
        assert 'l.layer(8,0)' in code
    else:
        assert 'l.layer(134,0)' in code


def test_clock_fault_cannot_silently_mutate_unbound_branch():
    data=generated();data['clock_connections']=[]
    with pytest.raises(ValueError,match='branch missing'):
        check.mutation_source(Path('i'),Path('o'),data,'clock_open')
    data=generated();data['routes'].pop()
    with pytest.raises(ValueError,match='trunks missing'):
        check.mutation_source(Path('i'),Path('o'),data,'clock_short')
