# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Negative native receipt/source controls; actual geometry controls run separately."""
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import check_magic_esd_v1 as c  # noqa: E402
import patch_magic_esd_v1 as p  # noqa: E402


def fixture():
    ports = {'SUB':[dict(layer=8,box=[0,0,1,1]) for _ in range(32)]}
    devices,spice,ext = [],[],['scale 1000 1 0.5']
    for i in range(32):
        model = 'diodevdd_2kv' if i < 16 else 'diodevss_2kv'
        for name in (f'PAD{i:02d}',f'VDD{i:02d}'):
            ports[name] = [dict(layer=10,box=[0,0,1,1])]
        devices.append(dict(index=i,model=model,orientation=i % 8,terminals=[f'VDD{i:02d}',f'PAD{i:02d}','SUB']))
        spice.append(f'X{i} VDD{i:02d} PAD{i:02d} SUB {model} ea=35.0028p ep=58.08u')
        ext.append(f'device subckt {model} 0 0 1 1 "SUB" "VDD{i:02d}" 0 0 "PAD{i:02d}" 0 1400112,11616')
    r = dict(top='nssoc_esd_fixture',ports=ports,devices=devices)
    return ('.subckt esd_flat '+' '.join(ports)+'\n'+'\n'.join(spice)+'\n.ends\n',
            '\n'.join(ext)+'\n','exttospice finished.\nNSSOC_ESD_NATIVE_COMPLETE\n',r)


def test_positive_does_not_claim_bank_or_stress():
    r = c.assess(*fixture())
    assert r['count'] == 32 and r['ports'] == 65
    assert not r['full_bank_qualified'] and not r['qualified_pex'] and not r['esd_stress_qualified']
    assert r['raw_geometry_annotations_are_not_compact_model_parameters']


@pytest.mark.parametrize('before,after',[
    ('X0 VDD00 PAD00 SUB','X0 PAD00 VDD00 SUB'),
    ('X0 VDD00 PAD00 SUB','X0 VDD00 PAD01 SUB'),
    ('X0 VDD00 PAD00 SUB','X0 VDD00 PAD00 VDD00'),
    ('X0 VDD00 PAD00 SUB','X0 OTHER PAD00 SUB'),
    ('X0 VDD00 PAD00 SUB','X1 VDD00 PAD00 SUB'),
    ('SUB diodevdd_2kv','SUB diodevss_2kv'),
    ('SUB diodevdd_2kv','SUB diodevdd_4kv'),
    ('ea=35.0028p','ea=35.1p'),('ep=58.08u','ep=58.1u'),
    ('ea=35.0028p ep=58.08u','ea=35.0028p ea=58.08u'),
    ('ea=35.0028p ep=58.08u','ea=35.0028p ep=58.08u m=1'),
    ('.subckt esd_flat SUB','.subckt esd_flat'),
    ('.subckt esd_flat SUB','.subckt esd_flat EXTRA SUB'),
    ('.ends','Rbad SUB VDD00 0\n.ends'),('.ends','.ends altered'),
])
def test_spice_mutations_reject(before,after):
    s,e,log,r = fixture(); assert before in s
    with pytest.raises(ValueError):
        c.assess(s.replace(before,after,1),e,log,r)


@pytest.mark.parametrize('fault',['missing','duplicate','wrong_model','wrong_base','wrong_emitter',
                                 'wrong_substrate','wrong_area','wrong_perimeter','bad_grid','extra'])
def test_raw_native_bridge_rejects(fault):
    s,e,log,r = fixture(); lines = e.splitlines()
    if fault == 'missing': lines.pop(1)
    elif fault == 'duplicate': lines.append(lines[1])
    elif fault == 'wrong_model': lines[1] = lines[1].replace('diodevdd_2kv','diodevss_2kv')
    elif fault == 'wrong_base': lines[1] = lines[1].replace('"VDD00"','"VDD01"')
    elif fault == 'wrong_emitter': lines[1] = lines[1].replace('"PAD00"','"PAD01"')
    elif fault == 'wrong_substrate': lines[1] = lines[1].replace('"SUB"','"VDD00"')
    elif fault == 'wrong_area': lines[1] = lines[1].replace('1400112','1400113')
    elif fault == 'wrong_perimeter': lines[1] = lines[1].replace('11616','11617')
    elif fault == 'bad_grid': lines[0] = 'scale 1000 1 1'
    else: lines[1] += ' extra'
    with pytest.raises(ValueError): c.assess(s,'\n'.join(lines),log,r)


@pytest.mark.parametrize('field,value',[('index',2),('model','diodevss_2kv'),('orientation',7),
                                      ('terminals',['VDD00','PAD00','other'])])
def test_source_labels_cannot_override_native_contract(field,value):
    s,e,log,r = fixture(); r = copy.deepcopy(r); r['devices'][0][field] = value
    with pytest.raises(ValueError): c.assess(s,e,log,r)


@pytest.mark.parametrize('extra',['Error bad terminal','ERROR failure','Unrecognized layer',
                                'Device esdnpn does not have a compatible substrate node!',
                                'Grid scaling is finer','No matching device','Unknown command'])
def test_execution_failure_is_not_geometry_negative(extra):
    with pytest.raises(ValueError): c.completed(fixture()[2]+extra)


def test_incomplete_native_receipts_reject():
    for log in ('','NSSOC_ESD_NATIVE_COMPLETE\n',fixture()[2]*2):
        with pytest.raises(ValueError): c.completed(log)


def operator_fixture():
    mag = '''magic
tech ihp-sg13g2
<< esd_interact_yes >>
rect 0 0 1000 1000
rect 2000 0 3000 1000
rect 6000 400 6400 1000
rect 6000 0 7000 400
<< esd_interact_no >>
rect 4000 0 5000 1000
<< end >>
'''
    return mag,dict(interacting=[[0,0,10,10],[20,0,30,10],[60,0,70,4],[60,4,64,10]],
                    noninteracting=[[40,0,50,10]])


def test_operator_compares_entire_connected_region_without_tile_order_dependency():
    mag,r = operator_fixture()
    assert c.operator_assess(mag,r)['status'].startswith('PASS')
    split = mag.replace('rect 0 0 1000 1000','rect 0 0 500 1000\nrect 500 0 1000 1000')
    assert c.operator_assess(split,r)['status'].startswith('PASS')


@pytest.mark.parametrize('before,after',[
    ('rect 6000 400 6400 1000\n',''),('rect 0 0 1000 1000','rect 0 0 1001 1000'),
    ('rect 2000 0 3000 1000\n',''),('<< esd_interact_no >>','<< esd_interact_yes >>'),
    ('tech ihp-sg13g2','tech ihp-sg13g2\nmagscale 1 2'),
])
def test_operator_incomplete_or_fitted_regions_reject(before,after):
    mag,r = operator_fixture()
    with pytest.raises(ValueError): c.operator_assess(mag.replace(before,after),r)


@pytest.mark.parametrize('name',list(p.PINS))
def test_exact_preimage_required(name):
    with pytest.raises(ValueError): p.patch(name,b'altered input')


@pytest.mark.parametrize('name',list(p.PINS))
def test_private_patches_remain_exact_additive_delta(name):
    source = (Path('/dev/shm/nssoc-finite-tap-v1-build-final/source/cif')/name if name.endswith('.c')
              else Path('/dev/shm/nssoc-finite-tap-tech-final')/name)
    if not source.exists(): pytest.skip('Exact private native parent not provisioned')
    original = source.read_bytes(); result = p.patch(name,original)
    assert result != original
    with pytest.raises(ValueError): p.patch(name,result)


@pytest.mark.parametrize('name',['make_magic_esd_fixture_v1.py','audit_magic_esd_geometry_v1.py'])
def test_import_does_not_launch_native_or_create_geometry(name):
    spec = importlib.util.spec_from_file_location('esd_method',ROOT/'scripts'/name)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert callable(m.main)
