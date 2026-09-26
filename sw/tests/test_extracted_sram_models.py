# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed parser and explicit junction semantics; PDK waves are separate."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
import share_extracted_sram_models as adapter


@pytest.fixture
def convert(monkeypatch):
    # Synthetic wrapper/model fixture only. Actual pinned PDK DC/transient
    # equivalence is recorded independently by the physical campaign.
    wrapper = ''.join(
        f'.subckt sg13_lv_{kind} d g s b\n'
        f'+ w=0.35u l={length} ng=1 m=1 mm_ok=1 as=0 ad=0 pd=0 ps=0 trise=0 '
        'z1=0.34e-6 z2=0.38e-6 wmin=0.15e-6 rfmode=0 pre_layout=1\n'
        for kind, length in [('nmos', '0.34u'), ('pmos', '0.28u')]
    )
    parameters = ''.join(
        f'.model sg13g2_lv_{kind}_psp psp103\n+ test={{w+l+ng+pre_layout}}\n'
        for kind in ['nmos', 'pmos']
    )
    monkeypatch.setattr(adapter, 'WRAPPER_SHA256', hashlib.sha256(wrapper.encode()).hexdigest())

    def run(text, mode=0):
        return adapter.specialize_extracted(text, parameters, wrapper, pre_layout=mode)
    return run


MOS = 'X0 drain gate source body sg13_lv_nmos w=.2u l=.13u as=38f ad=.102p ps=.58u pd=.925u'


def test_actual_units_junctions_nodes_and_passives_are_preserved(convert):
    passive = 'R1 drain d2 125.4\nC1 d2 body 38f'
    circuit, models, mapping = convert(MOS + '\n' + passive)
    fields = circuit.splitlines()[0].split()
    assert fields[:5] == ['N0', 'drain', 'gate', 'source', 'body']
    values = {k: float(v) for k, v in (x.split('=') for x in fields[6:])}
    assert values['as'] == pytest.approx(38e-15)
    assert values['ad'] == pytest.approx(.102e-12)
    assert values['ps'] == pytest.approx(.58e-6)
    assert values['pd'] == pytest.approx(.925e-6)
    assert passive in circuit
    assert mapping['profiles'][0]['wrapper_fallback'] is False
    assert 'pre_layout' not in models
    assert mapping['qualified_pex'] is False


def test_zero_as_triggers_all_four_wrapper_defaults(convert):
    _, _, mapping = convert(MOS.replace('as=38f', 'as=0'))
    row = mapping['profiles'][0]
    assert row['wrapper_fallback'] is True
    assert row['effective_junction'] == pytest.approx(
        {'as': .2e-6 * .34e-6, 'ad': .2e-6 * .34e-6,
         'ps': 1.08e-6, 'pd': 1.08e-6})
    assert row['input']['ad'] == pytest.approx(.102e-12)


def test_layout_choice_binds_original_expressions(convert):
    a, ma, _ = convert(MOS, 0)
    b, mb, _ = convert(MOS, 1)
    assert a != b and ma != mb
    assert '_layout0' in a and '_layout1' in b


@pytest.mark.parametrize('text', [
    MOS.replace('as=38f', 'ad=38f'), MOS.replace('w=.2u', 'w=nan'),
    MOS.replace('w=.2u', 'w=.1u'), MOS.replace('pd=.925u', 'pd=-1u'),
    MOS + ' ng=2', MOS + '\n' + MOS, MOS.replace('X0', 'M0'),
    MOS + '\nC1 a b {parameter}', '+ orphan', 'R1 a b 1',
])
def test_unsupported_or_incomplete_input_rejected(convert, text):
    with pytest.raises(ValueError):
        convert(text)


@pytest.mark.parametrize('mode', [None, True, 2, -1, '0'])
def test_layout_choice_must_be_explicit_integer(convert, mode):
    with pytest.raises(ValueError):
        convert(MOS, mode)


def test_changed_wrapper_rejected():
    with pytest.raises(ValueError, match='Unverified wrapper'):
        adapter.specialize_extracted(MOS, '', 'changed', pre_layout=0)
