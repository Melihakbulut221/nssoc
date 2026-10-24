# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit shared substrate and unchanged clocked bank geometry/terminal contracts."""
from pathlib import Path
import copy
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import make_pcie_padded_clocked_bank as make
import check_pcie_padded_clocked_bank as check
from test_pcie_clocked_bank_v4 import parents  # noqa:F401 -- immutable parent fixture
import make_pcie_clocked_bank_v4 as bank


@pytest.fixture
def reference(parents):  # noqa:F811
    text=bank.reference(parents)
    assert __import__('hashlib').sha256(text.encode()).hexdigest()==make.PARENTS['bank']['schematic']
    return make.reference(text)


def test_literal_bank_preserved_with_only_explicit_body_port_rename(parents,reference):  # noqa:F811
    expected=[line.split() for line in bank.reference(parents).splitlines() if line and line[0] in 'QRCM']
    actual=[line.split() for line in reference.splitlines() if line and line[0] in 'QRCM']
    assert actual==[['ESD_RETURN' if x=='BULK' else x for x in row] for row in expected]
    assert len(actual)==319 and len(make.PORTS)==56
    assert sum('ptap1' in row for row in actual)==108
    assert all(row[1:3]==['SUB','ESD_RETURN'] for row in actual if 'ptap1' in row)
    assert 'RVCO_NTAP AVDD2V3 VCO_NWELL ntap1' in reference
    assert set(make.PORTS)-set(bank.PORTS)=={'ESD_VDD','ESD_RETURN'}
    assert not any(line.startswith(('V','I','.connect')) for line in reference.splitlines())


def test_all_sixteen_pads_have_both_native_named_diode_types(reference):
    rows=[line.split() for line in reference.splitlines() if line.startswith('D')]
    assert len(rows)==32
    for net in make.SERIAL:
        these=[r for r in rows if r[2]==net]
        assert len(these)==2 and {r[4] for r in these}=={'diodevdd_2kv','diodevss_2kv'}
        assert all(r[1]=='ESD_VDD' and r[3]=='ESD_RETURN' and r[-1]=='m=1' for r in these)


@pytest.mark.parametrize('fault',check.REFERENCE_FAULTS)
def test_schematic_faults_bind_exactly_once(reference,fault):
    wrong=check.fault_reference(reference,fault);assert wrong!=reference
    for text in ('',reference+reference,wrong):
        with pytest.raises(ValueError):check.fault_reference(text,fault)


def native_rows():
    rows=[]
    def add(model,nets,**p):rows.append(dict(model=model,nets=nets,parameters=p))
    # Literal distribution after four separate four-way native parallel combinations.
    for nx,count in [(1,14),(2,41),(4,39),(8,12)]:
        for _ in range(count):add('npn13G2',{'C':'internal','B':'bias','E':'emitter','S':'ESD_RETURN'},we=.07,le=.9,Nx=nx,m=1)
    for clk in ('clock_a','clock_b'):
        add('npn13G2',{'C':'AVDD2V3','B':'bias_'+clk,'E':clk,'S':'ESD_RETURN'},we=.07,le=.9,Nx=4,m=4)
        add('npn13G2',{'C':clk,'B':'bias','E':'AVSS','S':'ESD_RETURN'},we=.07,le=.9,Nx=2,m=4)
    for model,count in [('rsil',24),('rppd',57)]:
        for _ in range(count):add(model,{model+'_sub':'ESD_RETURN'})
    for _ in range(6):add('cap_cmim',{})
    add('sg13_hv_pmos',{})
    add('ptap1',{'TIE':'SUB','WELL':'ESD_RETURN'},A=432,P=864)
    add('ntap1',{'TIE':'AVDD2V3','WELL':'well'},A=4,P=8)
    for net in make.SERIAL:
        for model in ('diodevdd_2kv','diodevss_2kv'):
            add(model,{'C':'ESD_RETURN' if model=='diodevdd_2kv' else 'ESD_VDD','B':'ESD_VDD' if model=='diodevdd_2kv' else 'ESD_RETURN','E':net},m=1)
    return rows


def test_native_named_terminal_census_and_joint_strict_lvs_scope():
    rows=native_rows();r=check.validate_device_rows(rows)
    assert r['expanded_hbt_instances']==122 and len(r['named_esd_connections'])==32
    step=dict(name='lvs',audit_execution={'returncode':0},audit={'status':'PASS within comparison scope','circuits':[{'layout_devices_recursive':232,'schematic_devices_recursive':232}]})
    check.validate_lvs(step,'.subckt '+make.TOP+' '+' '.join(make.PORTS),True)
    step['audit']['status']='FAIL'
    with pytest.raises(ValueError):check.validate_lvs(step,'',True)


@pytest.mark.parametrize('model,key,value',[
    ('npn13G2','S','AVSS'),('rsil','rsil_sub','AVSS'),('rppd','rppd_sub','SUB'),
    ('ptap1','WELL','SUB'),('ntap1','WELL','AVDD2V3'),
    ('diodevdd_2kv','C','AVSS'),('diodevss_2kv','B','SUB'),
    ('diodevdd_2kv','B','AVDD1V8'),('diodevss_2kv','C','AVDD2V5'),
    ('diodevdd_2kv','E','L2_RX_INP')])
def test_real_body_rail_and_serial_mappings_fail_closed(model,key,value):
    rows=native_rows();r=next(r for r in rows if r['model']==model);r['nets'][key]=value
    with pytest.raises(ValueError):check.validate_device_rows(rows)


@pytest.mark.parametrize('model,key,value',[('ptap1','A',428),('ptap1','P',856),('npn13G2','Nx',3),('npn13G2','we',.071),('diodevdd_2kv','m',2)])
def test_geometry_and_multiplicity_changes_rejected(model,key,value):
    rows=native_rows();r=next(r for r in rows if r['model']==model);r['parameters'][key]=value
    with pytest.raises(ValueError):check.validate_device_rows(rows)


def test_missing_duplicate_native_device_rejected():
    rows=native_rows()
    for wrong in (rows[1:],rows+[copy.deepcopy(rows[0])]):
        with pytest.raises(ValueError):check.validate_device_rows(wrong)


def generated():
    return dict(serial_connections=[dict(net=n,bridge=dict(rect_um=[80+4*i,270+8*i,500+4*i,272+8*i])) for i,n in enumerate(make.SERIAL)],
                ports={n:dict(layer='TopMetal2',rect_um=[1500+20*i,3436,1504+20*i,3440]) for i,n in enumerate(make.PORTS)},
                vias=[dict(net='ESD_RETURN',bottom='Metal5',top='TopMetal2',center_um=[2890,220])])


@pytest.mark.parametrize('fault',check.PHYSICAL_FAULTS)
def test_actual_conductor_faults_bind_exact_branches_and_cloned_native_vias(fault):
    d=generated();text=check.mutation_source(Path('/input.gds'),Path('/output.gds'),d,fault);compile(text,'mutate','exec')
    if fault.startswith('open_'):
        assert 'region-=' in text and 'l.layer(126,0)' in text
        d['serial_connections']=[]
    else:
        assert 'native.dtrans' in text and 'l.layer(67,0)' in text
        d['vias']=[]
    with pytest.raises(ValueError):check.mutation_source(Path('/i'),Path('/o'),d,fault)


def test_all_branches_and_separate_explicit_returns_are_exposed():
    assert {f[5:] for f in check.PHYSICAL_FAULTS if f.startswith('open_')}==set(make.SERIAL)
    assert make.use_direction('ESD_RETURN')==('GROUND','INOUT')
    assert make.use_direction('ESD_VDD')==('POWER','INOUT')
    d=generated();d['bbox_um']=[0,0,make.WIDTH,make.HEIGHT]
    text=check.lef_script(Path('/pdk'),Path('/view.lef'),d)
    assert '!= 56' in text and 'pin obstruction overlap' in text
