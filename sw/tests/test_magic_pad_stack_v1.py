# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native conductor receipt controls; actual GDS faults run in the public driver."""
import copy
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import check_magic_pad_stack_v1 as c  # noqa: E402
import patch_magic_pad_stack_v1 as p  # noqa: E402


def fixture():
    ports={};chains=[]
    for i in range(16):
        for kind,layer in [('PAD',134),('CORE',126)]:ports[f'{kind}{i:02d}']=dict(layer=layer,box=[0,0,1,1])
        chains.append(dict(index=i,orientation=i%8,route_layer=134 if i<8 else 126,ports=[f'PAD{i:02d}',f'CORE{i:02d}']))
    return dict(top='nssoc_pad_stack_fixture',ports=ports,chains=chains)


def raw(case='nominal'):
    r=fixture();lines=[f'port "{n}" {i} 0 0 1 1 m7' for i,n in enumerate(r['ports'])]
    for group in c.expected_partition(case):
        lines.append(f'node "{group[0]}" 0 0 0 0 m7')
        lines.extend(f'equiv "{group[0]}" "{n}"' for n in group[1:])
    return '\n'.join(lines)+'\n','NSSOC_PAD_STACK_COMPLETE\n',r


@pytest.mark.parametrize('case',['unfixed','nominal',*c.FAULTS])
def test_actual_control_partitions_are_distinct(case):
    result=c.assess(*raw(case))
    assert result['partition']==c.expected_partition(case)
    assert (result['partition']==c.expected_partition('nominal'))==(case=='nominal')


@pytest.mark.parametrize('before,after',[
    ('port "PAD00"','port "OTHER"'),('port "PAD00" 0 0 0 1 1 m7\n',''),
    ('node "CORE00" 0 0 0 0 m7','node "CORE00" 0 0 0 0 m7\nnode "CORE00" 0 0 0 0 m7'),
    ('equiv "CORE00" "PAD00"','equiv "CORE00"'),
    ('equiv "CORE00" "PAD00"',''),
])
def test_missing_or_corrupt_raw_terminal_receipt_rejects(before,after):
    ext,log,r=raw();assert before in ext
    with pytest.raises(ValueError):c.assess(ext.replace(before,after),log,r)


def test_native_equivalence_does_not_get_repaired_from_reference():
    ext,log,r=raw();ext=ext.replace('equiv "CORE00" "PAD00"','equiv "CORE01" "PAD00"')
    result=c.assess(ext,log,r)
    assert result['partition']!=c.expected_partition('nominal')


def test_unexpected_device_rejects():
    ext,log,r=raw()
    with pytest.raises(ValueError):c.assess(ext+'device resistor bogus\n',log,r)


@pytest.mark.parametrize('error',['','Error broken extraction','ERROR nativecrash','Unrecognized layer',
                                'Unknown command','No matching device','compatible substrate'])
def test_native_error_cannot_be_expected_physical_failure(error):
    ext,log,r=raw()
    with pytest.raises(ValueError):c.assess(ext,error+'\n'+log if error else '',r)


@pytest.mark.parametrize('field,value',[('index',9),('orientation',3),('route_layer',126),('ports',['PAD00','CORE01'])])
def test_no_relabelled_fixture_contract(field,value):
    r=copy.deepcopy(fixture());r['chains'][0][field]=value
    with pytest.raises(ValueError):c.validate_fixture(r)


def test_missing_chain_port_wrong_layer_rejects():
    for kind in ('chain','port','layer'):
        r=fixture()
        if kind=='chain':r['chains'].pop()
        elif kind=='port':r['ports'].pop('PAD00')
        else:r['ports']['PAD00']['layer']=126
        with pytest.raises(ValueError):c.validate_fixture(r)


def test_patcher_preserves_entire_technology_except_two_exact_plane_names():
    path=Path('/dev/shm/nssoc-magic-esd-tech-final/ihp-sg13g2.tech')
    if not path.exists():pytest.skip('Exact frozen technology not provisioned')
    source=path.read_bytes();after=p.patch(source)
    expected=source.replace(b'paint  m6      obsm5  m6',b'paint  m6      obsm6  m6').replace(
        b'paint  m7      obsm5  m7',b'paint  m7      obsm7  m7')
    assert after==expected and after!=source
    for data in (after,source+b'\n',source.replace(b'obsm5',b'obsm4',1)):
        with pytest.raises(ValueError):p.patch(data)


def test_any_unpinned_technology_rejected():
    with pytest.raises(ValueError):p.patch(b'wrong technology')


def test_no_virtual_node_join_command_or_body_edit():
    t=c.native_tcl(Path('/tmp/fixture.gds'),fixture(),Path('/tmp/out'))
    assert 'flatten pad_stack_flat' in t and 'extract all' in t
    assert 'connect' not in t and 'paint' not in t and 'global' not in t
    with pytest.raises(ValueError):c.native_tcl(Path('/tmp/{bad}'),fixture(),Path('/tmp/out'))
