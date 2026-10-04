# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal VCO native geometry, electrical polarity and strict result guards."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_clock_vco as make
import check_pcie_clock_vco as check

SOURCE = (ROOT / make.CIRCUIT).read_text()


def test_original_circuit_geometry_and_native_body_contacts():
    rows=make.devices(SOURCE)
    assert len(rows)==len({r['name'] for r in rows})==34
    assert sorted(r['nx'] for r in rows if r['kind']=='hbt')==[1]*4+[2]*9+[4]*5
    mos=[r for r in rows if r['kind']=='pmos']
    assert mos==[dict(kind='pmos',name='CTRL',nets=['REF','VCTRL','AVDD','AVDD'],width_um=32,length_um=.45,ng=1)]
    caps=[r for r in rows if r['kind']=='capacitor']
    assert len(caps)==6
    assert sorted((r['width_um'],r['length_um']) for r in caps)==[(12,12)]*5+[(12.2,12)]
    assert next(r for r in caps if r['name']=='CP0')['nets']==['P0','AVSS']
    resistors=[r for r in rows if r['kind']=='resistor']
    assert sorted((r['width_um'],r['length_um']) for r in resistors)==[(2,7.4)]+[(8,4.4)]*8
    reference=make.physical_reference(SOURCE)
    assert 'MCTRL REF VCTRL AVDD NWELL sg13_hv_pmos w=32u l=0.45u ng=1 m=1' in reference
    assert 'RNTAP AVDD NWELL ntap1 A=4p P=8u' in reference
    assert reference.count('SUB BULK ptap1 A=4p P=8u')==8
    assert not any(line.startswith(('V','I','.ic','.IC')) for line in reference.splitlines())
    assert tuple(reference.splitlines()[2].split()[2:])==make.PORTS


def test_ring_and_follower_literal_connections():
    d={r['name']:r for r in make.devices(SOURCE)}
    for stage,previous in ((0,2),(1,0),(2,1)):
        assert d[f'P{stage}']['nets']==[f'P{stage}',f'P{previous}',f'T{stage}','SUB']
        assert d[f'N{stage}']['nets']==[f'N{stage}',f'N{previous}',f'T{stage}','SUB']
    assert d['FP']['nets']==['AVDD','BO_P','CLKP','SUB']
    assert d['FN']['nets']==['AVDD','BO_N','CLKN','SUB']


@pytest.mark.parametrize('old,new',[('32u','31u'),('12.2u','12u'),('Nx=4','Nx=3'),('sw_et=1','sw_et=0'),
                                    ('p1 p0','p1 n0'),('ref vctrl avdd avdd','ref vctrl avdd sub'),('b=0','b=1')])
def test_actual_circuit_drift_rejected(old,new):
    assert old in SOURCE
    with pytest.raises(ValueError,match='frozen source'):
        make.devices(SOURCE.replace(old,new,1))


@pytest.mark.parametrize('fault',check.REFERENCE_FAULTS)
def test_exact_device_negative_is_bound_once(fault):
    text=make.physical_reference(SOURCE)
    wrong=check.fault_reference(text,fault)
    assert wrong!=text and wrong.splitlines()[2]==text.splitlines()[2]
    for invalid in ('',text+text,wrong):
        with pytest.raises(ValueError):
            check.fault_reference(invalid,fault)


def positive():
    return dict(name='lvs',audit_execution={'returncode':0},audit={'status':'PASS within comparison scope',
                'circuit_status_counts':{'Match':1},'circuits':[{'layout_devices_recursive':36,'schematic_devices_recursive':36}]})


def test_strict_six_ports_and_complete_devices_required():
    header='.subckt '+make.TOP+' '+' '.join(make.PORTS)
    step=positive();check.validate_lvs(step,header,True)
    for path,value in [(('audit_execution','returncode'),1),(('audit','status'),'FAIL'),
                       (('audit','circuits'),[]),(('audit','circuits'),[{'layout_devices_recursive':35,'schematic_devices_recursive':36}])]:
        wrong=copy.deepcopy(step);target=wrong
        for key in path[:-1]:
            target=target[key]
        target[path[-1]]=value
        with pytest.raises(ValueError):
            check.validate_lvs(wrong,header,True)
    for wrong in (header.replace(' VCTRL',''),header.replace(' VCTRL',' UNUSED'),header.replace(' VCTRL',' CLKP')):
        with pytest.raises(ValueError):
            check.validate_lvs(step,wrong,True)


def test_control_open_is_exact_missing_boundary_port_not_native_error():
    header='.subckt '+make.TOP+' '+' '.join(n for n in make.PORTS if n!='VCTRL')
    step=dict(name='control_open',audit_execution={'returncode':1},audit={'status':'FAIL'})
    check.validate_lvs(step,header,False)
    with pytest.raises(ValueError):
        check.validate_lvs(step,header+' VCTRL',False)
    step['audit_execution']['returncode']=2
    with pytest.raises(ValueError):
        check.validate_lvs(step,header,False)


@pytest.mark.parametrize('fault',check.PHYSICAL_FAULTS)
def test_real_physical_mutation_targets_control_output_and_rails(fault):
    data={'bbox_um':[0,0,1400,260],'ports':{name:dict(rect_um=[0,90+10*i,2,92+10*i]) for i,name in enumerate(make.PORTS)}}
    for name in ('CLKP','CLKN'):
        data['ports'][name]['rect_um'][0]=1398
        data['ports'][name]['rect_um'][2]=1400
    code=check.mutation_source(Path('/input.gds'),Path('/wrong.gds'),data,fault)
    compile(code,'physical_fault','exec')
    assert 'l.layer(67,0)' in code
    if fault=='clock_short':
        assert '1398.5' in code and '1399.5' in code
    elif fault=='control_open':
        assert 'region-=' in code and 'DBox(3,' in code
    else:
        assert 'DBox(0.5,' in code


def test_external_voltage_control_and_output_port_types():
    assert make.use_direction('VCTRL')==('SIGNAL','INPUT')
    assert make.use_direction('CLKP')==make.use_direction('CLKN')==('SIGNAL','OUTPUT')
    assert make.use_direction('AVDD')==('POWER','INOUT')
    assert make.use_direction('SUB')==make.use_direction('AVSS')==('GROUND','INOUT')
