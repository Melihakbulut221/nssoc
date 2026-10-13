# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check source ordering, launch contract and whole-stage device accounting."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('mux4',ROOT/'scripts/run_cloud_tx_mux4.py')
mux4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mux4)


def test_independent_hbt_resistor_corners_do_not_change_circuit_or_shared_studies():
    from run_cloud_tx_operating_point import CONDITIONS as shared
    assert 'hbt_bcs_res_wcs' not in shared
    assert mux4.CONDITIONS['hbt_bcs_res_wcs'] == {'hbt':'hbt_bcs','resistor':'res_wcs'}
    assert mux4.CONDITIONS['hbt_wcs_res_bcs'] == {'hbt':'hbt_wcs','resistor':'res_bcs'}
    for base, field, value in [('hot_low','resistor','res_bcs'), ('hot_low','hbt','hbt_bcs'),
                               ('cold_high','resistor','res_wcs'), ('cold_high','hbt','hbt_wcs')]:
        actual=mux4.CONDITIONS[base+'_'+value]
        assert actual==dict(shared[base],**{field:value})
        assert not any(key in actual for key in ('pre_bias','final_drive','prestage','phase'))


def points(text):
    return np.asarray([tuple(map(float,line.lstrip('+ ').split()))
                       for line in text[4:-1].splitlines() if line.strip()])


def test_four_physical_source_streams_preserve_original_bit_order_and_phase():
    bits=mux4.sequence()
    streams=[]
    for bank in range(4):
        p=points(mux4.pwl(bits[bank::4],.6,.6,4*mux4.UI,
                         mux4.START+(bank-3)*mux4.UI,invert=True))
        assert p[0].tolist()==[0,0] and p[1,0]==1e-9 and p[-1,0]==mux4.STOP
        assert np.all(np.diff(p[:,0])>0)
        streams.append(p)
    for index,bit in enumerate(bits):
        stream=streams[index%4]
        for phase in (.3,.5,.7):
            sample=mux4.START+(index+phase)*mux4.UI
            value=np.interp(sample,stream[:,0],stream[:,1])
            # Gate polarity is inverted by the physical HV common-source stage.
            assert value==pytest.approx(1.2*(1-bit),abs=1e-12)
        # A selected source is already stable before its prestage selection.
        selection=mux4.START+(index-1)*mux4.UI
        assert np.interp(selection,stream[:,0],stream[:,1])==pytest.approx(1.2*(1-bit),abs=1e-12)


def test_explicit_preclocks_select_the_original_bank_at_all_output_samples():
    selectors={}
    for name,origin,period in [('a',mux4.START-mux4.UI,2*mux4.UI),
                               ('b',mux4.START,2*mux4.UI),('final',mux4.START,mux4.UI)]:
        selectors[name]=points(mux4.pwl([int(i%2==0) for i in range(256)],1.23,.08,period,origin))
    for index in range(256):
        for phase in (.3,.5,.7):
            sample=mux4.START+(index+phase)*mux4.UI
            def choice(name):
                p=selectors[name]
                return np.interp(sample,p[:,0],p[:,1])>1.23
            bank=(0 if choice('a') else 2) if choice('final') else (1 if choice('b') else 3)
            assert bank==index%4


def test_all_native_pre_stage_devices_and_reference_are_bound():
    ports='d0p d0n d2p d2n sap san ap an avdd 0 0 ra'.split()
    name,devices=mux4.bind_devices(mux4.PRE,'xprea',ports,{'npn13g2'})
    assert len(devices)==19
    assert devices['xprea.xref']['terminals']==['ra','ra','0','0']
    assert devices['xprea.xsa_0']['terminals'][1]=='sap'
    assert devices['xprea.xap_0']['terminals'][1]=='d0p'
    assert all(row['nx'] in (1,8) for row in devices.values())
    assert all(n.startswith('xprea.') for n in devices)


def test_full_tree_capture_also_saves_rails_connected_only_through_resistors(tmp_path):
    # Native rail avdd feeds resistors, so enumerating transistor pins alone
    # misses it. tvdd is similarly absent from the TX HBT terminal set.
    inputs=tmp_path
    (inputs/'frontend').mkdir()
    (inputs/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (inputs/'frontend/buf16.inc').write_text('''
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos w=4.44u l=130n
XN0 X net1 VSS VSS sg13_lv_nmos w=11.84u l=130n
XP1 X net1 VDD VDD sg13_lv_pmos w=17.92u l=130n
XP0 net1 A VDD VDD sg13_lv_pmos w=6.72u l=130n
.ends
''')
    deck,contract=mux4.build(inputs,'nominal')
    assert len(contract['hbt'])==61 and len(contract['mos'])==64
    assert set(contract['rails'])=={'avdd','tvdd','dvdd'}
    for name in contract['rails']:
        vector='v('+name+')'
        assert vector in contract['vectors']
        for prefix in ('save ', 'wrdata op.dat ', 'wrdata wave.dat '):
            row=next(line for line in deck.splitlines() if line.startswith(prefix))
            assert vector in row.split()


def test_damped_frontend_binds_actual_buffer_gate_after_native_resistor(tmp_path,monkeypatch):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text('''
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 X net1 VDD VDD sg13_lv_pmos
XP0 net1 A VDD VDD sg13_lv_pmos
.ends
''')
    monkeypatch.setattr(mux4,'FRONT',ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v6.inc')
    deck,c=mux4.build(tmp_path,'cold_high')
    assert c['mos']['xad_d0p.xbuf.xn1']['terminals'][1]=='xad_d0p.gate'
    assert 'v(xad_d0p.gate)' in c['vectors'] and 'v(d0p0)' in c['vectors']
    assert len(c['hbt'])==61 and len(c['mos'])==64
    assert 'XGATE din gate sub rppd w=2u l=4.5u' in mux4.FRONT.read_text()


def test_native_bias_is_loaded_by_all_three_actual_clock_pairs(tmp_path):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text('''
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 X net1 VDD VDD sg13_lv_pmos
XP0 net1 A VDD VDD sg13_lv_pmos
.ends
''')
    deck,c=mux4.build(tmp_path,'cold_high',clock_bias='native_vbe')
    assert len(c['hbt'])==62 and len(c['mos'])==64
    assert c['hbt']['xclkbias.xref']['terminals']==['clkbias','clkbias','xclkbias.er','0']
    assert 'v(clkbias)' in c['vectors'] and 'v(xclkbias.er)' in c['vectors']
    for name in ('sap','san','sbp','sbn','sp','sn'):
        assert f'V{name} {name}0 clkbias PWL(' in deck
        assert f'R{name} {name}0 {name} 25' in deck
    assert 'ICLKBIAS avdd clkbias PWL(0 0 1n .00065)' in deck


def test_faster_final_stage_preserves_every_hbt_and_changes_real_passives_only():
    original=ROOT/'hw/soc/analog/pcie/tx_mux2_hbt_passive_fast_v1.spice'
    actual=mux4.FAST_FINAL
    old=original.read_text().splitlines();new=actual.read_text().splitlines()
    assert [s for s in old if ' npn13G2 ' in s]==[s for s in new if ' npn13G2 ' in s]
    old_r=[s.split() for s in old if ' rppd ' in s];new_r=[s.split() for s in new if ' rppd ' in s]
    assert len(old_r)==len(new_r)==8
    for before,after in zip(old_r,new_r,strict=True):
        assert [x for x in before if not x.startswith('w=')]==[x for x in after if not x.startswith('w=')]
        width=lambda row:float(next(x[2:-1] for x in row if x.startswith('w=')))
        assert width(after)==2*width(before)
    assert 'w=2u l=12u' in (ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc').read_text()


def test_tapped_drive_preserves_exact_native_substrate_network_and_all_other_fields():
    import hashlib
    import re
    text=mux4.TAPPED_FINAL.read_text()
    assert len([line for line in text.splitlines() if ' ptap1 ' in line])==27
    assert len([line for line in text.splitlines() if ' npn13g2 ' in line])==19
    rows=[]
    for line in text.splitlines(keepends=True):
        if ' rppd ' in line:
            line=re.sub(r'\bw=([0-9.]+)u',lambda m:'w='+format(float(m.group(1))/2,'.1f')+'u',line,count=1)
        rows.append(line.replace('nssoc_tx_mux54_passive_drive_v3','nssoc_tx_mux54_compact_v1'))
    # Reverse only the eight intended resistor-width changes and subckt rename.
    assert hashlib.sha256(''.join(rows).encode()).hexdigest()=='bc22f8c7fefdf56187fcecd5fe056d4333c8b25f31934867dd6f5ee908950b09'


def test_headroom_repair_changes_only_two_collector_resistor_widths():
    text=mux4.GUARDED_FINAL.read_text().replace('nssoc_tx_mux54_passive_drive_v4','nssoc_tx_mux54_passive_drive_v3')
    rows=[]
    for line in text.splitlines(keepends=True):
        if line.startswith(('XD0007 ','XD0008 ')):
            assert 'w=17.0u' in line
            line=line.replace('w=17.0u','w=16.0u')
        rows.append(line)
    assert ''.join(rows)==mux4.TAPPED_FINAL.read_text()
    assert mux4.PRE_BIASES=={'baseline':.0005,'plus10':.00055,'plus20':.0006}


def test_native_prestage_bias_replaces_current_sources_and_measures_loaded_feeds(tmp_path):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text('''
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 X net1 VDD VDD sg13_lv_pmos
XP0 net1 A VDD VDD sg13_lv_pmos
.ends
''')
    deck,c=mux4.build(tmp_path,'hot_low',clock_bias='native_vbe',final_drive='double_taps_guard',pre_bias='native_res')
    assert len(c['hbt'])==62 and len(c['mos'])==64
    assert not any(line.startswith(('Ira ','Irb ')) for line in deck.splitlines())
    for reference in ('ra','rb'):
        assert f'Vprebias_{reference} avdd prefeed_{reference} 0' in deck
        assert f'XPREBIAS_{reference} prefeed_{reference} {reference} 0 nssoc_tx_pre_bias_res_v1' in deck
        assert f'i(vprebias_{reference})' in c['vectors']
        assert f'v(prefeed_{reference})' in c['vectors']
    assert 'Imr avdd mr PWL(0 0 1n 0.001)' in deck
    assert 'rppd w=2u l=22u' in mux4.PRE_FEED.read_text()


def test_native_clock_feed_removes_ideal_bias_without_changing_clock_phase(tmp_path):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text("""
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 X net1 VDD VDD sg13_lv_pmos
XP0 net1 A VDD VDD sg13_lv_pmos
.ends
""")
    before,b=mux4.build(tmp_path,'hbt_typ_res_wcs',clock_bias='native_vbe',pre_bias='native_res')
    after,a=mux4.build(tmp_path,'hbt_typ_res_wcs',clock_bias='native_res',pre_bias='native_res')
    assert 'ICLKBIAS' in before and 'ICLKBIAS' not in after
    assert 'Vclkbias_feed avdd clkfeed 0' in after
    assert 'XCLKFEED clkfeed clkbias 0 nssoc_tx_clock_bias_feed_v1' in after
    assert a['hbt']==b['hbt'] and a['mos']==b['mos'] and a['bits']==b['bits']
    assert {'i(vclkbias_feed)','v(clkfeed)'} <= set(a['vectors'])
    for key in ('sap','san','sbp','sbn','sp','sn'):
        stimulus=lambda text:text.split('V'+key+' ')[1].split('R'+key+' ')[0]
        assert stimulus(before)==stimulus(after)
