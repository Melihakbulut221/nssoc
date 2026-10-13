# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject real connectivity, body-contact and device mutations before layout."""
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('adapter',ROOT/'scripts/audit_tx_final_layout_source.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CORE=(ROOT/'hw/soc/analog/pcie/tx_mux2_final_drive_v5_layout_core.spice').read_text()
NATIVE=(ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v5.spice').read_text()


def test_native_54_including_separate_body_contacts():
    result=m.audit(CORE,NATIVE)
    assert result['substrate_contacts']==27 and result['body_port_separate']


@pytest.mark.parametrize('side,before,after',[
 ('core','w=18u','w=17u'),
 ('core','qn ap ea','qn an ea'),
 ('core','XAP_0 qn ap ea sub npn13G2 Nx=8\n',''),
 ('core','iref avss sub npn13G2','iref sub sub npn13G2'),
 ('core','Nx=8','Nx=7'),
 ('core','l=38.4u','l=38.405u'),
 ('native','XD0010 sub n_1 ptap1 r=81.66666666666666666666666668 w=2u l=2u\n',''),
 ('native','sub n_1 ptap1','sub sub ptap1'),
 ('native','n_1 npn13g2','sub npn13g2'),
 ('native','we=0.07u','we=0.08u'),
 ('native','sw_et=1','sw_et=0'),
 ('native','r=81.66666666666666666666666668','r=80'),
 ('native',' w=2u l=2u',' w=3u l=2u'),
 ('native','ps=0.0u','ps=1u'),
 ('native','m=1','m=2'),
 ('native',' sub ap an bp bn',' avss ap an bp bn'),
])
def test_native_faults_rejected(side,before,after):
    core,native=CORE,NATIVE
    assert before in (core if side=='core' else native)
    if side=='core':core=core.replace(before,after,1)
    else:native=native.replace(before,after,1)
    with pytest.raises(AssertionError):m.audit(core,native)


def test_generated_reference_and_missing_contact_control():
    rows=['.subckt native '+' '.join(sorted(m.PORTS))]
    for i,(model,nodes,params) in enumerate(m.parse(CORE)):
        nodes[-1]='BULK'
        rows.append('X%d '%i+' '.join(nodes)+' '+model+' '+' '.join(k+'='+v for k,v in params.items()))
    taps=[f'RPTAP{i} sub BULK ptap1 A=4p P=8u' for i in range(27)]
    generated='\n'.join(rows+taps+['.ends native'])
    assert m.audit(CORE,NATIVE,generated)['generated_sha256']
    with pytest.raises(AssertionError):m.audit(CORE,NATIVE,generated.replace(taps[0]+'\n',''))
    with pytest.raises(AssertionError):m.audit(CORE,NATIVE,generated.replace('A=4p','A=6p',1))


CORE6=(ROOT/'hw/soc/analog/pcie/tx_mux2_final_drive_v6_layout_core.spice').read_text()
NATIVE6=(ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v6.spice').read_text()


def test_v6_switching_size_is_explicit_and_old_profile_stays_strict():
    assert m.audit(CORE6,NATIVE6,profile='v6')['profile']=='v6'
    with pytest.raises(AssertionError):m.audit(CORE6,NATIVE6)
    with pytest.raises(AssertionError):m.audit(CORE,NATIVE,profile='v6')
    # Even equivalent changes on both sides cannot silently change the v6 size contract.
    with pytest.raises(AssertionError):
        m.audit(CORE6.replace('Nx=4','Nx=8'),NATIVE6.replace('nx=4','nx=8'),profile='v6')
    with pytest.raises(AssertionError):
        m.audit(CORE6.replace('Nx=8','Nx=4'),NATIVE6.replace('nx=8','nx=4'),profile='v6')


def test_v6_generated_reference_preserves_all_27_body_contacts():
    rows=['.subckt native '+' '.join(sorted(m.PORTS))]
    for i,(model,nodes,params) in enumerate(m.parse(CORE6)):
        nodes[-1]='BULK'
        rows.append('X%d '%i+' '.join(nodes)+' '+model+' '+' '.join(k+'='+v for k,v in params.items()))
    taps=[f'RPTAP{i} sub BULK ptap1 A=4p P=8u' for i in range(27)]
    generated='\n'.join(rows+taps+['.ends native'])
    assert m.audit(CORE6,NATIVE6,generated,profile='v6')['generated_sha256']
    with pytest.raises(AssertionError):m.audit(CORE6,NATIVE6,generated.replace(taps[0]+'\n',''),profile='v6')
    with pytest.raises(AssertionError):m.audit(CORE6,NATIVE6,generated.replace('nx=4','nx=8',1),profile='v6')


CORE7=(ROOT/'hw/soc/analog/pcie/tx_mux2_final_drive_v7_layout_core.spice').read_text()
NATIVE7=(ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v7.spice').read_text()


def test_v7_resizes_only_four_selectors_and_preserves_strict_profiles():
    assert m.audit(CORE7,NATIVE7,profile='v7')['profile']=='v7'
    old,new=m.parse(CORE6),m.parse(CORE7)
    changes=[(a,b) for a,b in zip(old,new,strict=True) if a!=b]
    assert len(changes)==4
    for a,b in changes:
        assert a[:2]==b[:2] and a[0]=='npn13g2' and a[1][1] in ('sp','sn')
        assert a[2]['nx']=='4' and b[2]['nx']=='8'
        assert {k:v for k,v in a[2].items() if k!='nx'}=={k:v for k,v in b[2].items() if k!='nx'}
    for core,native,profile in [(CORE6,NATIVE6,'v7'),(CORE7,NATIVE7,'v6'),(CORE,NATIVE,'v7')]:
        with pytest.raises(AssertionError):m.audit(core,native,profile=profile)
    # Consistent mutations on both source representations must still fail.
    with pytest.raises(AssertionError):
        m.audit(CORE7.replace('Nx=4','Nx=8'),NATIVE7.replace('nx=4','nx=8'),profile='v7')
    with pytest.raises(AssertionError):
        m.audit(CORE7.replace('Nx=8','Nx=4'),NATIVE7.replace('nx=8','nx=4'),profile='v7')


def test_v7_generated_reference_keeps_all_native_body_contacts():
    rows=['.subckt native '+' '.join(sorted(m.PORTS))]
    for i,(model,nodes,params) in enumerate(m.parse(CORE7)):
        nodes[-1]='BULK'
        rows.append('X%d '%i+' '.join(nodes)+' '+model+' '+' '.join(k+'='+v for k,v in params.items()))
    taps=[f'RPTAP{i} sub BULK ptap1 A=4p P=8u' for i in range(27)]
    generated='\n'.join(rows+taps+['.ends native'])
    assert m.audit(CORE7,NATIVE7,generated,profile='v7')['generated_sha256']
    with pytest.raises(AssertionError):m.audit(CORE7,NATIVE7,generated.replace(taps[0]+'\n',''),profile='v7')
