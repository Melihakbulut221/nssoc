# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal circuit, lane identity, negative controls and native receipt guards."""
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import make_pcie_analog_bank as bank
import make_pcie_rx_cell_v2 as rx
import check_pcie_analog_bank as check


def tx_reference():
    text=(ROOT/'hw/soc/flow/make_pcie_tx_cell.py').read_text()
    # A small actual reference with literal original dimensions and square taps.
    return '\n'.join(['.subckt nssoc_tx_cml_layout '+' '.join(bank.CELL_PORTS['TX']),
      'QREF IREF IREF AVSS BULK npn13G2 Nx=1 we=0.07u le=0.9u m=1',
      'QTAIL TAIL IREF AVSS BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1',
      'QP OUTN INP TAIL BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1',
      'QN OUTP INN TAIL BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1',
      'RP AVDD OUTP BULK rsil w=10u l=70.215u m=1',
      'RN AVDD OUTN BULK rsil w=10u l=70.215u m=1',
      *[f'RTAP{i} SUB BULK ptap1 A=4p P=8u' for i in range(8)],'.ends nssoc_tx_cml_layout','']) if '70.215' in text else None


@pytest.fixture
def circuits():
    analog=(ROOT/'hw/soc/analog/pcie/rx_hbt_rsil_v2.spice').read_text()
    return tx_reference(),rx.physical_reference(analog)


def test_new_source_exact_and_v1_unchanged():
    actual=(ROOT/'hw/soc/analog/pcie/rx_hbt_rsil_v2.spice').read_text()
    assert rx.validate_circuit(actual)
    assert rx.CIRCUIT_SHA256=='d02827087e0cb43f447fc46fda05dbd23dcee13ad68755fd31ba738404332a4e'
    old=importlib.util.spec_from_file_location('old_rx',ROOT/'hw/soc/flow/make_pcie_rx_cell.py')
    module=importlib.util.module_from_spec(old);old.loader.exec_module(module)
    assert module.CIRCUIT_SHA256=='4450bac31930cca351a33dcb7b269ef732a342bcafef8d96610ee15340d51e5a'
    assert module.validate_circuit((ROOT/'hw/soc/analog/pcie/rx_hbt_rsil.spice').read_text())


@pytest.mark.parametrize('old,new',[('27.5u','28.5u'),('Nx=4','Nx=8'),('inp inn','inn inp'),('sw_et=1','sw_et=0'),('sub rsil','avss rsil')])
def test_rx_geometry_source_mutations_rejected(old,new):
    actual=(ROOT/'hw/soc/analog/pcie/rx_hbt_rsil_v2.spice').read_text()
    with pytest.raises(ValueError):rx.physical_reference(actual.replace(old,new,1))


def test_four_lane_reference_exact_ownership(circuits):
    text=bank.reference(*circuits);lines=text.splitlines()
    assert tuple(lines[2].split()[2:])==bank.PORTS
    assert len(bank.PORTS)==len(set(bank.PORTS))==47
    devices=[line.split() for line in lines if line.startswith(('Q','R'))]
    assert len(devices)==120
    assert sum(d[0].startswith('Q') for d in devices)==32
    assert sum('ptap1' in d for d in devices)==64
    assert len({d[0] for d in devices})==120
    for lane in range(4):
        for kind in ('TX','RX'):
            selected=[d for d in devices if d[0].startswith(('Q'+str(lane)+kind+'_','R'+str(lane)+kind+'_'))]
            assert len(selected)==(14 if kind=='TX' else 16)
            for d in selected:
                for term in d[1:5 if d[0][0]=='Q' else 3 if 'ptap1' in d else 4]:
                    assert term in ('AVDD','AVSS','SUB','BULK') or term.startswith(f'L{lane}_{kind}_')
    assert 'R0RX_RP AVDD L0_RX_OUTP BULK RSIL W=2U L=27.5U' in text
    assert 'R0TX_TAP0 SUB BULK ptap1 A=4p P=8u' in text


@pytest.mark.parametrize('part,old,new',[(0,'INP INN','INN INP'),(1,'RTAP0 SUB BULK ptap1 A=4p P=8u\n',''),(0,'RP AVDD','XP AVDD')])
def test_incomplete_or_wrong_contract_rejected(circuits,part,old,new):
    values=list(circuits);assert old in values[part];values[part]=values[part].replace(old,new,1)
    with pytest.raises(ValueError):bank.reference(*values)


@pytest.mark.parametrize('lane,kind',[(4,'TX'),(-1,'RX'),(0,'PHY')])
def test_unknown_lane_rejected(lane,kind):
    with pytest.raises(ValueError):bank.mapped_net(lane,kind,'INP')


@pytest.mark.parametrize('kind,fault',[('bank','wrong_load'),('bank','wrong_lane'),('bank','missing_tap'),('rx-v2','wrong_load'),('rx-v2','wrong_input'),('rx-v2','missing_tap')])
def test_comparison_fault_binds_once(circuits,kind,fault):
    text=bank.reference(*circuits) if kind=='bank' else circuits[1]
    changed=check.fault_reference(text,kind,fault);assert changed!=text
    with pytest.raises(ValueError):check.fault_reference(changed,kind,fault)
    with pytest.raises(ValueError):check.fault_reference(text+text,kind,fault)


def test_unknown_fault_rejected(circuits):
    with pytest.raises(ValueError):check.fault_reference(circuits[1],'rx-v2','waive')
    with pytest.raises(ValueError):check.mutation_source(Path('a'),Path('b'),'top','waive',{})


def test_physical_open_bound_to_lane2_real_route():
    generated={'routes':[dict(lane=2,kind='RX',terminal='INP',source_m5_rect_um=[30,40,32,42])]}
    code=check.mutation_source(Path('/a.gds'),Path('/b.gds'),bank.TOP,'physical_open',generated)
    compile(code,'mutation','exec')
    assert 'len(matches)!=1' in code and '31.0' in code and '41.0' in code
    assert 'l.layer(125,0)' in code and 'matches[0].delete()' in code
    with pytest.raises(StopIteration):check.mutation_source(Path('a'),Path('b'),bank.TOP,'physical_open',{'routes':[]})


def test_native_lef_positive_and_exact_negative():
    check.validate_lef(0,'PASS_NATIVE_ANALOG_BANK_LEF_ONLY\n',False)
    check.validate_lef(1,'Error: inspect.tcl, 8 Analog terminal census changed\n',True)
    for code,text in [(1,'segfault'),(0,'Error: inspect.tcl, 8 Analog terminal census changed'),(1,'PASS_NATIVE_ANALOG_BANK_LEF_ONLY\nError: inspect.tcl, 8 Analog terminal census changed')]:
        with pytest.raises(ValueError):check.validate_lef(code,text,True)
    for text in ['','PASS_NATIVE_ANALOG_BANK_LEF_ONLY\n'*2,'PASS_NATIVE_ANALOG_BANK_LEF_ONLY\n[ERROR unknown]']:
        with pytest.raises(ValueError):check.validate_lef(0,text,False)


def test_tcl_path_rejected():
    for text in ('x{y','x}y','x\ny','x\ry'):
        with pytest.raises(ValueError):check.quote(text)


def test_exact_port_open_receipt_and_mutation_guards():
    import copy
    step={'status':'FAIL','audit_execution':{'returncode':1},'audit':{
      'circuit_status_counts':{'Match':1},'extraction_diagnostics':[],
      'reasons':['Missing explicit successful deck verdict','Deck explicitly reported a mismatch'],
      'circuits':[{'layout_devices_recursive':57,'schematic_devices_recursive':57}]}}
    header='.subckt '+bank.TOP+' '+' '.join(p for p in bank.PORTS if p!='L2_RX_INP')+'\n.ends '+bank.TOP
    check.validate_open_rejection(step,header,bank.PORTS)
    for path,value in [(('status',),'PASS'),(('audit_execution','returncode'),0),
                       (('audit','circuit_status_counts'),{'NoMatch':1}),
                       (('audit','extraction_diagnostics'),['error']),
                       (('audit','reasons'),['Deck explicitly reported a mismatch'])]:
        wrong=copy.deepcopy(step);target=wrong
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        with pytest.raises(ValueError):check.validate_open_rejection(wrong,header,bank.PORTS)
    for bad in [header.replace('L0_RX_VCM','L2_RX_INP'),header.replace('L0_RX_VCM',''),header.replace('L0_RX_VCM','L0_RX_VCM L2_RX_INP')]:
        with pytest.raises(ValueError):check.validate_open_rejection(step,bad,bank.PORTS)
    for bad in ['+ orphan', '.subckt t A A', '.subckt t A\n.subckt other A']:
        with pytest.raises(ValueError):check.extracted_ports(bad,'t')
