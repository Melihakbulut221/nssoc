# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal VCO native geometry, electrical polarity and strict result guards."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_clock_vco_v3 as make
import check_pcie_clock_vco_v3 as check

SOURCE = (ROOT / make.CIRCUIT).read_text()


def test_stronger_circuit_geometry_and_native_body_contacts():
    rows=make.devices(SOURCE)
    assert len(rows)==len({r['name'] for r in rows})==46
    assert sorted(r['nx'] for r in rows if r['kind']=='hbt')==[1]*2+[2]*17+[4]*11
    mos=[r for r in rows if r['kind']=='pmos']
    assert mos==[dict(kind='pmos',name='CTRL',nets=['REF','VCTRL','AVDD','AVDD'],width_um=32,length_um=.45,ng=1)]
    caps=[r for r in rows if r['kind']=='capacitor']
    assert len(caps)==6
    assert sorted((r['width_um'],r['length_um']) for r in caps)==[(12,12)]*5+[(12.2,12)]
    assert next(r for r in caps if r['name']=='CP0')['nets']==['P0','AVSS']
    resistors=[r for r in rows if r['kind']=='resistor']
    assert sorted((r['width_um'],r['length_um']) for r in resistors)==[(2,7.4)]+[(8,4.0)]*2+[(8,4.4)]*6
    reference=make.physical_reference(SOURCE)
    assert 'MCTRL REF VCTRL AVDD NWELL sg13_hv_pmos w=32u l=0.45u ng=1 m=1' in reference
    assert 'RNTAP AVDD NWELL ntap1 A=4p P=8u' in reference
    assert reference.count('SUB BULK ptap1 A=4p P=8u')==12
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


def extracted_document():
    result=[]
    for line in make.physical_reference(SOURCE).splitlines():
        if any(line.startswith("Q"+name+" ") for side in ("P", "N") for prefix in ("F", "FT") for index in range(1,4) for name in [prefix+side+"D"+str(index)]):
            continue
        if line.startswith("RTAP"):
            if not line.startswith("RTAP0 "):
                continue
            line=line.replace("A=4p P=8u", "A=48p P=96u")
        if line.split(" ")[0] in ("QFP", "QFN", "QFTP", "QFTN"):
            line=line.replace("m=1", "m=4")
        result.append(line.replace("we=0.07u le=0.9u", "we=70n le=900n"))
    return "\n".join(result)


def test_strict_six_ports_and_complete_devices_required():
    header=extracted_document()
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
    data['origin_translation_um']=[3,7]
    data['routes']=[dict(device='FPD2',net='AVDD',actual_pin_um='(1520,20;1528,20.3)',escape_lane_um=1511,escape_y_um=20.2)]
    code=check.mutation_source(Path('/input.gds'),Path('/wrong.gds'),data,fault)
    compile(code,'physical_fault','exec')
    assert ('l.layer(30,0)' if fault=='follower_open' else 'l.layer(67,0)') in code
    if fault=='clock_short':
        assert '1398.5' in code and '1399.5' in code
    elif fault=='control_open':
        assert 'region-=' in code and 'DBox(3,' in code
    elif fault=='power_short':
        assert 'DBox(0.5,' in code
    else:
        assert 'region-=' in code and '1520.4' in code and '26.9' in code


def test_external_voltage_control_and_output_port_types():
    assert make.use_direction('VCTRL')==('SIGNAL','INPUT')
    assert make.use_direction('CLKP')==make.use_direction('CLKN')==('SIGNAL','OUTPUT')
    assert make.use_direction('AVDD')==('POWER','INOUT')
    assert make.use_direction('SUB')==make.use_direction('AVSS')==('GROUND','INOUT')


@pytest.mark.parametrize('old,new', [('Nx=4 we=70n le=900n m=4','Nx=4 we=70n le=900n m=3'),
    ('QFP AVDD BO_P CLKP','QFP AVDD BO_P CLKN'), ('Nx=2 we=70n le=900n m=4','Nx=4 we=70n le=900n m=4'),
    ('A=48p P=96u','A=32p P=64u'), ('RNTAP AVDD NWELL','RNTAP AVDD AVDD'), ('we=70n','we=71n')])
def test_combined_native_records_preserve_thirty_separate_hbt_equivalents(old,new):
    native=extracted_document()
    check.validate_expanded_devices(native)
    assert old in native
    with pytest.raises(ValueError):
        check.validate_expanded_devices(native.replace(old,new,1))


def test_all_eight_native_follower_sink_branches_per_polarity_are_literal():
    d={row['name']:row for row in make.devices(SOURCE)}
    for side,clock,bias in [('P','CLKP','BO_P'),('N','CLKN','BO_N')]:
        for suffix in ('','D1','D2','D3'):
            assert d['F'+side+suffix]['nets']==['AVDD',bias,clock,'SUB']
            assert d['F'+side+suffix]['nx']==4
            assert d['FT'+side+suffix]['nets']==[clock,'BREF','AVSS','SUB']
            assert d['FT'+side+suffix]['nx']==2


def test_native_lef_guard_checks_pin_and_obstruction_overlap():
    g={'bbox_um':[0,0,1880,277.03], 'ports':{name:dict(rect_um=[0,i*10,2,i*10+2]) for i,name in enumerate(make.PORTS)}}
    code=check.lef_script(Path('/pdk'),Path('/view.lef'),g)
    assert 'VCO pin obstruction overlap' in code
    assert 'foreach ob [$master getObstructions]' in code
    assert '[$pb xMin] < [$ob xMax]' in code and '[$pb yMin] < [$ob yMax]' in code
