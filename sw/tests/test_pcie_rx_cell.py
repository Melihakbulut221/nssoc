# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fixed RX circuit/physical-reference contract and actual fault binding guards."""
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
from make_pcie_rx_cell import CIRCUIT_SHA256, PORTS, physical_reference, validate_circuit
from check_pcie_rx_cell import fault_reference, lef_script, validate_lef_result

SOURCE = (ROOT/'hw/soc/analog/pcie/rx_hbt_rsil.spice').read_text()


def test_exact_analog_source_and_port_identity_are_retained():
    assert hashlib.sha256(SOURCE.encode()).hexdigest() == CIRCUIT_SHA256
    assert validate_circuit(SOURCE)[0].split()[2:] == [p.lower() for p in PORTS]
    result = physical_reference(SOURCE)
    rows = [line.split() for line in result.splitlines() if line.startswith(('Q','R'))]
    assert len(rows) == 16
    transistors = [r for r in rows if r[0].startswith('Q')]
    assert [r[6] for r in transistors] == ['NX=1','NX=4','NX=4','NX=4']
    assert all(r[-3:] == ['we=0.07u','le=0.9u','m=1'] for r in transistors)
    for source in validate_circuit(SOURCE)[1:-1]:
        original = source.upper().split()
        prefix = 'Q' if original[5] == 'NPN13G2' else 'R'
        derived = next(r for r in rows if r[0] == prefix+original[0][1:])
        assert derived[1:5] == ['BULK' if x == 'SUB' else x for x in original[1:5]]
        assert all(x in derived for x in original[5:] if x != 'SW_ET=1')
    taps = [r for r in rows if r[0].startswith('RTAP')]
    assert len(taps) == 8 and all(r[1:] == ['SUB','BULK','ptap1','A=4p','P=8u'] for r in taps)
    assert not any(r[0].startswith('V') for r in rows)
    assert not any({'AVSS','SUB'} <= set(r[1:3]) for r in rows)


@pytest.mark.parametrize(('old','new'),[
    ('Nx=4','Nx=3'),('w=10u','w=11u'),('l=41.785u','l=42u'),
    ('XP outn inp','XP outn inn'),('sub iref vcm','sub iref'),
    ('iref avss sub','iref avss avss'),('sw_et=1','sw_et=0'),
    ('XREF','*XREF'),('b=0','b=1'),('.ends nssoc_rx_hbt_rsil','')])
def test_changed_simulated_device_or_interface_fails_closed(old,new):
    assert old in SOURCE
    with pytest.raises(ValueError,match='analog source differs'):
        physical_reference(SOURCE.replace(old,new))


@pytest.mark.parametrize('fault',['termination_width','tail_nx','missing_tap','wrong_input','bulk_short'])
def test_each_negative_changes_exactly_bound_real_reference(fault):
    source = physical_reference(SOURCE)
    changed = fault_reference(source,fault)
    assert changed != source
    assert changed.splitlines()[2] == source.splitlines()[2]
    with pytest.raises(ValueError,match='absent or ambiguous'):
        fault_reference(source+source,fault)
    with pytest.raises(ValueError,match='absent or ambiguous'):
        fault_reference('',fault)


def test_unknown_fault_cannot_silently_turn_into_positive():
    with pytest.raises(ValueError,match='Unknown'):
        fault_reference(physical_reference(SOURCE),'ignored')


def test_tcl_path_metacharacters_rejected_before_native_launch():
    with pytest.raises(ValueError,match='Unsafe Tcl path'):
        lef_script(Path('/tmp/unsafe}path'),Path('/tmp/layout.lef'),{})


def test_real_missing_pin_diagnostic_is_required_not_any_tool_failure():
    validate_lef_result(1, 'Error: inspect.tcl, 6 RX terminal census changed\n', True)
    banner='PASS_RX_NATIVE_LEF_NINE_REAL_PORTS_SEVEN_OBSTRUCTED_LAYERS_NO_TIMING_ACCEPTANCE'
    validate_lef_result(0,banner+'\n',False)
    for code, text, negative in [(1,'segmentation fault',True), (0,'',True),
                                  (1,banner,True), (1,banner,False),
                                  (0,banner+'\nError: unexpected',False),
                                  (0,banner+'\n'+banner,False)]:
        with pytest.raises(ValueError):
            validate_lef_result(code,text,negative)
