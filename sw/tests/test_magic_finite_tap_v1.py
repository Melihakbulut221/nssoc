# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed native finite-tap contract controls; no simulator reimplementation."""
import copy
from decimal import Decimal
import importlib.util
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import check_magic_finite_tap_v1 as c  # noqa: E402
import patch_magic_finite_tap_v1 as p  # noqa: E402


def fixture(grid='.005'):
    ports, devices, spice, ext = {}, [], [], ['scale 1000 1 '+str(Decimal(grid)*100)]
    for i in range(132):
        model = 'ptap1' if i < 108 else 'ntap1'
        n = i if i < 108 else i-108
        w, length = [(.78,.78),(2.,2.),(2.,3.)][n//8 % 3]
        if 24 <= i < 108:
            w = length = 2.
        tie, body = f'T{i:03d}', 'sub' if i < 108 else f'W{i:03d}'
        ports[tie] = dict(layer=8, box=[0,0,w,length])
        if i >= 108:
            ports[body] = dict(layer=31, box=[0,0,w,length])
        resistance = 980/(w*length+2*(w+length))
        devices.append(dict(tie=tie,body='BULK' if i < 108 else body,model=model,
                            w_um=w,l_um=length,orientation=n % 8,resistance_ohm=resistance))
        raw_r=format(resistance,'.6g')
        exported=format(struct.unpack('f',struct.pack('f',float(raw_r)))[0],'.5f')
        spice.append(f'X{i} {tie} {body} {model} w={w}u l={length}u r={exported}')
        ext.append(f'device csubckt {model} 0 0 1 1 r={raw_r} '
                   f'w={Decimal(str(w))/Decimal(grid)} l={Decimal(str(length))/Decimal(grid)} '
                   f'"None" "{tie}" 0 0 "{body}" 0 0')
    record=dict(top='nssoc_finite_taps',ports=ports,devices=devices)
    return ('.subckt finite_taps_flat '+' '.join(ports)+'\n'+'\n'.join(spice)+'\n.ends\n',
            '\n'.join(ext)+'\n','NSSOC_FINITE_TAP_NATIVE_COMPLETE\n',record)


@pytest.mark.parametrize('grid',['.005','.01'])
def test_two_native_grid_contracts(grid):
    row=c.assess(*fixture(grid))
    assert row['ptap_count']==108 and row['ntap_count']==24 and row['port_count']==156
    assert row['qualified_pex'] is False and row['full_bank_qualified'] is False


@pytest.mark.parametrize('fault', ['extra_element','omit','duplicate','short','wrong_body','wrong_well',
                                 'wrong_model','wrong_r','wrong_w','duplicate_param','extra_param',
                                 'missing_port','extra_port','bad_end'])
def test_native_export_faults_reject(fault):
    s,e,log,r=fixture()
    changes={
        'extra_element':('.ends','Rbad sub 0 0\n.ends'),
        'omit':('X0 T000 sub ptap1 w=0.78u l=0.78u r=262.84698\n',''),
        'duplicate':('X1 T001','X0 T001'),
        'short':('X0 T000 sub','X0 T000 T000'),
        'wrong_body':('X0 T000 sub','X0 T000 other'),
        'wrong_well':('X108 T108 W108','X108 T108 W109'),
        'wrong_model':('X0 T000 sub ptap1','X0 T000 sub ntap1'),
        'wrong_r':('r=262.84698','r=30'),
        'wrong_w':('w=0.78u','w=0.80u'),
        'duplicate_param':('w=0.78u l=0.78u','w=0.78u w=0.78u'),
        'extra_param':('w=0.78u l=0.78u','w=0.78u l=0.78u m=1'),
        'missing_port':('flat T000 T001','flat T001'),
        'extra_port':('flat T000','flat EXTRA T000'),
        'bad_end':('.ends','.ends altered'),
    }
    before,after=changes[fault]; assert before in s
    with pytest.raises(ValueError):c.assess(s.replace(before,after,1),e,log,r)


@pytest.mark.parametrize('fault', ['missing','duplicate','wrong_model','wrong_body','wrong_r',
                                 'wrong_w','wrong_grid','malformed','extra_param'])
def test_raw_ext_bridge_faults_reject(fault):
    s,e,log,r=fixture()
    lines=e.splitlines()
    if fault=='missing':lines.pop(1)
    elif fault=='duplicate':lines.append(lines[1])
    elif fault=='wrong_model':lines[1]=lines[1].replace('ptap1','ntap1')
    elif fault=='wrong_body':lines[1]=lines[1].replace('"sub"','"other"')
    elif fault=='wrong_r':lines[1]=lines[1].replace('r=262.847','r=30')
    elif fault=='wrong_w':lines[1]=lines[1].replace('w=156','w=157')
    elif fault=='wrong_grid':lines[0]='scale 1000 1 1'
    elif fault=='malformed':lines[1]+=' extra'
    else:lines[1]=lines[1].replace('r=262.847','r=262.847 x=1')
    with pytest.raises(ValueError):c.assess(s,'\n'.join(lines),log,r)


@pytest.mark.parametrize('warning', ['','ERROR: extractor crash','Error bad terminal',
                                  'NSSOC devresist grid coefficient overflow',
                                  'NSSOC terminal component geometry/connectivity failure',
                                  'Grid scaling is finer than limit set by the process!',
                                  'Unable to open file','Unknown command'])
def test_no_native_failure_as_negative(warning):
    log=warning+'\nNSSOC_FINITE_TAP_NATIVE_COMPLETE\n' if warning else ''
    with pytest.raises(ValueError):c.completed_native(log)


@pytest.mark.parametrize('field,value', [('tie','T001'),('body','T000'),('model','ntap1'),
                                      ('w_um',2),('l_um',2),('orientation',7),('resistance_ohm',30)])
def test_source_catalog_cannot_be_relabelled(field,value):
    s,e,log,r=fixture();r=copy.deepcopy(r);r['devices'][0][field]=value
    with pytest.raises(ValueError):c.assess(s,e,log,r)


def test_empty_or_duplicate_catalog_rejected():
    r=fixture()[3]
    for rows in ([],r['devices']+[r['devices'][0]],r['devices'][1:]):
        altered=copy.deepcopy(r);altered['devices']=rows
        with pytest.raises(ValueError):c.validate_fixture(altered)


def test_native_grid_uses_empty_database_before_import():
    t=c.native_tcl(Path('/tmp/fixture.gds'),fixture()[3],Path('/tmp/out'),2)
    assert t.index('scalegrid 2 1') < t.index('gds read')
    assert 'ext2spice global off' in t
    with pytest.raises(ValueError):c.native_tcl(Path('/tmp/fixture.gds'),fixture()[3],Path('/tmp/out'),4)
    with pytest.raises(ValueError):c.native_tcl(Path('/tmp/{unsafe}'),fixture()[3],Path('/tmp/out'))


@pytest.mark.parametrize('name',list(p.PINS))
def test_patcher_rejects_any_unpinned_preimage(name):
    with pytest.raises(ValueError):p.patch(name,b'wrong source')


@pytest.mark.parametrize('name',list(p.PINS))
def test_exact_native_patches_reversible(name):
    base=Path('/dev/shm/nssoc-hbt-nx-v3-build-final/source/extract')
    path=base/name if name.endswith('.c') else Path('/dev/shm/nssoc-hbt-nx-v3-native-final/tech')/name
    if not path.exists():pytest.skip('Exact native private build not provisioned')
    data=path.read_bytes();changed=p.patch(name,data)
    assert changed!=data
    with pytest.raises(ValueError):p.patch(name,changed)
    with pytest.raises(ValueError):p.patch(name,data+b'\n')


def test_pcell_module_import_has_no_native_execution():
    spec=importlib.util.spec_from_file_location('tap_fixture',ROOT/'scripts/make_magic_finite_tap_fixture_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert callable(module.main)
