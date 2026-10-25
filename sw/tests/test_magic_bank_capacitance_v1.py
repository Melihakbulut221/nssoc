# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import check_magic_bank_capacitance_v1 as m


def example():
    ports = ['AVSS', 'ESD_RETURN'] + [f'P{i}' for i in range(54)]
    names = ports + [f'I{i}' for i in range(154)]
    ext = ['scale 1000 1 0.5', 'style ngspice()', 'tech ihp-sg13g2',
           'substrate ESD_RETURN 0 0 0 0 m7']
    for i, name in enumerate(names):
        if name in ports:
            ext.append(f'port {name} {i+1} 0 0 1 1 m7')
        if name != 'ESD_RETURN':
            ext.append(f'node {name} 0 10 0 0 m7')
    ext.append('cap AVSS P0 2.5')
    spice = ['.subckt native ' + ' '.join(ports)]
    for model, count in m.MODELS.items():
        for i in range(count):
            spice.append(f'X{model}_{i} P0 AVSS ESD_RETURN {model} w=1 l=1')
    for i, name in enumerate(names):
        if name != 'ESD_RETURN':
            spice.append(f'C{i} {name} ESD_RETURN 1e-17')
    spice += ['Cmut AVSS P0 2.5e-18', '.ends native']
    return '\n'.join(ext)+'\n', '\n'.join(spice)+'\n'


def test_full_c_matrix_and_named_substrate_accounted():
    result = m.audit(*example())
    assert result['matrix_entries_compared'] == 210**2
    assert len(result['source_edges_af']) == 210
    assert sum(result['device_models'].values()) == 351
    assert not result['qualified_pex'] and not result['unreduced_resistance_qualified']


def test_native_floating_annotation_preserved_not_waived():
    ext, spice = example()
    result = m.audit(ext, spice.replace('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN 1e-17 $ **FLOATING'))
    assert result['native_floating_capacitor_annotations'] == ['C0']


@pytest.mark.parametrize('old,new', [
    ('C0 AVSS ESD_RETURN 1e-17', ''),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN 2e-17'),
    ('Cmut AVSS P0 2.5e-18', ''),
    ('Cmut AVSS P0 2.5e-18', 'Cmut AVSS P1 2.5e-18'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS AVSS 1e-17'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 UNKNOWN ESD_RETURN 1e-17'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN -1e-17'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN nan'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN inf'),
    ('C0 AVSS ESD_RETURN 1e-17', 'C0 AVSS ESD_RETURN 1e-17 $ ignored'),
    ('Cmut AVSS P0 2.5e-18', 'Cmut AVSS P0 2.5e-18\nC0 AVSS ESD_RETURN 1e-17'),
    ('Xrsil_0 P0 AVSS ESD_RETURN rsil w=1 l=1', ''),
    ('Xrsil_0 P0 AVSS ESD_RETURN rsil w=1 l=1', 'Xrsil_0 P0 AVSS ESD_RETURN other w=1 l=1'),
    ('Xrsil_0 P0 AVSS ESD_RETURN rsil w=1 l=1', 'Xrsil_0 UNKNOWN AVSS ESD_RETURN rsil w=1 l=1'),
    ('.ends native', '.ends different'),
    ('C0 AVSS ESD_RETURN 1e-17', 'Rstray AVSS ESD_RETURN 1'),
])
def test_export_fault_rejected(old, new):
    ext, spice = example()
    assert old in spice
    with pytest.raises(ValueError):
        m.audit(ext, spice.replace(old, new))


@pytest.mark.parametrize('old,new', [
    ('scale 1000 1 0.5', 'scale 1000 2 0.5'),
    ('substrate ESD_RETURN', 'substrate AVSS'),
    ('style ngspice()', 'style other'),
    ('tech ihp-sg13g2', 'tech other'),
    ('node P0 0 10', 'node P0 0 -10'),
    ('node P0 0 10', 'node P0 0 nan'),
    ('cap AVSS P0 2.5', 'cap AVSS P0 2.5\nnode P0 0 10 0 0 m7'),
    ('cap AVSS P0 2.5', 'cap AVSS P0 2.5\nunknown bogus'),
    ('port P0 3', 'port P0 1'),
    ('cap AVSS P0 2.5', 'cap AVSS P0 2.5\nequiv AVSS P0'),
])
def test_source_fault_rejected(old, new):
    ext, spice = example()
    assert old in ext
    with pytest.raises(ValueError):
        m.audit(ext.replace(old, new), spice)
