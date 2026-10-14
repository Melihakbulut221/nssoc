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


def test_hot_quarter_step_preserves_original_pvt_and_shared_table():
    from run_cloud_tx_operating_point import CONDITIONS as shared
    assert 'hot_low_quarter_step' not in shared
    assert mux4.CONDITIONS['hot_low_quarter_step'] == dict(shared['hot_low'], step_ps=.25)
    assert mux4.UI == 125e-12 and mux4.BITS == 256


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


def test_all_native_feeds_leave_no_ideal_reference_current_sources(tmp_path):
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
    deck,c=mux4.build(tmp_path,'hot_low_hbt_bcs',clock_bias='native_res',pre_bias='native_res',output_bias='native_res')
    assert not any(line.lower().startswith('i') for line in deck.splitlines())
    assert 'XFINALFEED finalfeed mr 0 nssoc_tx_final_bias_feed_v1' in deck
    assert 'XTXFEED txfeed tr 0 nssoc_tx_output_bias_feed_v1' in deck
    assert len(c['hbt'])==62 and len(c['mos'])==64
    assert {'i(vfinal_feed)','v(finalfeed)','i(vtx_feed)','v(txfeed)'} <= set(c['vectors'])
    assert c['bits']==mux4.sequence()


@pytest.mark.parametrize('streams',[4,8,16,32])
def test_complete_recursive_tree_selects_original_source_without_retiming(streams):
    plan=mux4.tree_plan(streams);bits=mux4.sequence()
    nodes={node['label']:node for node in plan['nodes']}
    clocks={clock['name']:points(mux4.pwl([int(i%2==0) for i in range(256)],0,.08,
            clock['period'],clock['origin'])) for clock in plan['clocks']}
    sources=[points(mux4.pwl(bits[bank::streams],.6,.6,streams*mux4.UI,
                mux4.START+(bank-plan['launch_offset'])*mux4.UI,invert=True)) for bank in range(streams)]
    for index,bit in enumerate(bits):
        for phase in (.3,.5,.7):
            t=mux4.START+(index+phase)*mux4.UI
            def choice(clock):
                p=clocks[clock]
                return 0 if np.interp(t,p[:,0],p[:,1])>0 else 1
            selected=('a','b')[choice('s')]
            visited=0
            while selected in nodes:
                node=nodes[selected];selected=node['inputs'][choice(node['clock'])];visited+=1
            assert selected==f'd{index%streams}' and visited==streams.bit_length()-2
            p=sources[index%streams]
            assert np.interp(t,p[:,0],p[:,1])==pytest.approx(1.2*(1-bit),abs=1e-12)
        # Leaf data is stable before the earliest selection on its actual path.
        selected_at=mux4.START+(index-(streams.bit_length()-2))*mux4.UI
        p=sources[index%streams]
        assert np.interp(selected_at,p[:,0],p[:,1])==pytest.approx(1.2*(1-bit),abs=1e-12)


@pytest.mark.parametrize('streams',[4,8,16,32])
def test_complete_tree_binds_every_device_and_limits_actual_clock_reference_fanout(tmp_path,streams):
    from collections import Counter
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
    deck,c=mux4.build(tmp_path,'nominal',clock_bias='native_res',pre_bias='native_res',output_bias='native_res',streams=streams)
    assert len(c['hbt'])==19*(streams-1)+4+(streams+1)//3
    assert len(c['mos'])==16*streams
    assert len(c['references'])==streams-2
    fanout=Counter(clock['reference'] for clock in c['tree_plan']['clocks'])
    assert sum(fanout.values())==streams-1 and max(fanout.values())<=3
    assert len(fanout)==len(c['clock_refs'])
    saves=[line.split()[1:] for line in deck.splitlines() if line.startswith('save ')]
    assert all(len(row)<=1000 for row in saves)
    assert [name for row in saves for name in row]==c['vectors']
    assert len(c['vectors'])+1<=10000
    assert not any(line.lower().startswith('i') for line in deck.splitlines())
    assert c['bits']==mux4.sequence() and len(set(c['vectors']))==len(c['vectors'])
    for reference in c['references']:
        assert f'i(vprebias_{reference})' in c['vectors']
    assert len([line for line in deck.splitlines() if line.startswith('xpre')])==streams-2


@pytest.mark.parametrize('streams',[8,32])
def test_deep_leaf_fault_changes_only_actual_selector_bases_and_not_oracle(tmp_path,streams):
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
    before,b=mux4.build(tmp_path,'nominal',clock_bias='native_res',pre_bias='native_res',output_bias='native_res',streams=streams)
    after,a=mux4.build(tmp_path,'nominal',fault='swap_leaf_select',clock_bias='native_res',pre_bias='native_res',output_bias='native_res',streams=streams)
    assert a['bits']==b['bits']==mux4.sequence() and a['source_bits_sha256']==b['source_bits_sha256']
    assert a['tree_plan']==b['tree_plan'] and a['mos']==b['mos'] and a['vectors']==b['vectors']
    prefix='xprep'+str(streams//2)+'_'+str(streams//2-1)
    changed={n for n in a['hbt'] if a['hbt'][n]!=b['hbt'][n]}
    assert changed=={prefix+'.x'+side+'_'+str(i) for side in ('sa','sb') for i in (0,1)}
    for name in changed:
        previous=b['hbt'][name];actual=a['hbt'][name]
        assert {k:v for k,v in previous.items() if k!='terminals'}=={k:v for k,v in actual.items() if k!='terminals'}
        assert previous['terminals'][0]==actual['terminals'][0] and previous['terminals'][2:]==actual['terminals'][2:]
        assert previous['terminals'][1][:-1]==actual['terminals'][1][:-1]
        assert {previous['terminals'][1][-1],actual['terminals'][1][-1]}=={'p','n'}
    changes=[(x,y) for x,y in zip(before.splitlines(),after.splitlines(),strict=True) if x!=y]
    assert len(changes)==1 and changes[0][0].startswith(prefix+' ')


def test_final_margin_candidate_changes_only_two_actual_collector_widths():
    text=mux4.MARGIN_FINAL.read_text().replace('nssoc_tx_mux54_passive_drive_v5','nssoc_tx_mux54_passive_drive_v4')
    original=mux4.GUARDED_FINAL.read_text()
    changed=[(a,b) for a,b in zip(original.splitlines(),text.splitlines(),strict=True) if a!=b]
    assert len(changed)==2
    for before,after in changed:
        assert before.startswith(('XD0007 ','XD0008 '))
        assert before.replace('w=17.0u','w=18.0u')==after
    assert text.replace('w=18.0u','w=17.0u')==original


def test_reordered_physical_port_list_preserves_every_bound_device(tmp_path,monkeypatch):
    (tmp_path/'frontend').mkdir()
    original=mux4.PRE.read_text()
    (tmp_path/'mux54-compact01.spice').write_text(original)
    (tmp_path/'frontend/buf16.inc').write_text('''
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 X net1 VDD VDD sg13_lv_pmos
XP0 net1 A VDD VDD sg13_lv_pmos
.ends
''')
    _,before=mux4.build(tmp_path,'nominal',streams=8,clock_bias='native_res',pre_bias='native_res',output_bias='native_res')
    header=next(line for line in original.splitlines() if line.lower().startswith('.subckt '))
    fields=header.split();reordered=' '.join(fields[:2]+list(reversed(fields[2:]))+['wire_cref'])
    physical=tmp_path/'permuted.spice';physical.write_text(original.replace(header,reordered))
    monkeypatch.setattr(mux4,'PRE',physical)
    deck,after=mux4.build(tmp_path,'nominal',streams=8,clock_bias='native_res',pre_bias='native_res',output_bias='native_res')
    assert after['hbt']==before['hbt'] and after['mos']==before['mos']
    assert after['bits']==before['bits'] and after['tree_plan']==before['tree_plan']
    assert after['vectors']==before['vectors']
    # The actual source instance follows its declared ports, including explicit
    # wire-capacitance reference, instead of the old hand-written position list.
    instance=next(line.split() for line in deck.splitlines() if line.startswith('xprea '))
    assert instance[1]=='ra' and instance[-2]=='0'
    for node in after['tree_plan']['nodes']:
        assert 'v('+node['label']+'p)' in after['vectors']
        assert 'v('+node['label']+'n)' in after['vectors']
    physical.write_text(original.replace(header,reordered.replace(' wire_cref',' unexpected_pin')))
    with pytest.raises(AssertionError):
        mux4.build(tmp_path,'nominal',streams=8)


def test_physical_top_renaming_preserves_native_device_text_and_formal_order():
    text=mux4.MARGIN_FINAL.read_text()
    new=mux4.rename_physical_top(text,'nssoc_physical_final_v5')
    assert [line for line in text.splitlines() if line.startswith('X')]==[line for line in new.splitlines() if line.startswith('X')]
    old_header=next(line.split() for line in text.splitlines() if line.startswith('.subckt'))
    new_header=next(line.split() for line in new.splitlines() if line.startswith('.subckt'))
    assert old_header[2:]==new_header[2:]
    assert new_header[1]=='nssoc_physical_final_v5'
    ports=['n'+str(i) for i in range(len(old_header)-2)]
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        from pathlib import Path
        path=Path(directory)/'renamed.spice';path.write_text(new)
        _,before=mux4.bind_devices(mux4.MARGIN_FINAL,'xmux',ports,{'npn13g2'})
        _,after=mux4.bind_devices(path,'xmux',ports,{'npn13g2'})
        assert before==after and len(after)==19


@pytest.mark.parametrize('text',[
 '.subckt x a b\n.ends y\n',
 '.subckt x a b\n.ends x\n.subckt y a b\n.ends y\n',
 '.subckt x a b\nXX a b x\n.ends x\n',
])
def test_physical_top_rename_rejects_ambiguous_or_recursive_models(text):
    with pytest.raises(AssertionError):mux4.rename_physical_top(text,'unique_final')


def test_physical_final_profiles_use_distinct_receipt_files():
    assert mux4.physical_spec_path('power_trunks_vias').name=='pcie-cascade14-power-vias-composition-20261013.json'
    assert mux4.physical_spec_path('kelvin_dense_wide').name=='pcie-cascade14-kelvin-dense-wide-composition-20261013.json'
    assert mux4.physical_final_spec_path('power_trunks').name=='pcie-final-v5-composition-20261013.json'
    assert mux4.physical_final_spec_path('interleaved').name=='pcie-final-v5-interleaved-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_return').name=='pcie-final-v5-kelvin-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_short').name=='pcie-final-v5-kelvin-short-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_short_vias').name=='pcie-final-v5-kelvin-short-vias-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_dense').name=='pcie-final-v5-kelvin-dense-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_dense_wide').name=='pcie-final-v5-kelvin-dense-wide-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_signal_trunks').name=='pcie-final-v5-kelvin-signal-trunks-composition-20261013.json'
    assert mux4.physical_final_spec_path('kelvin_m3_10').name=='pcie-final-v5-kelvin-m3-10-composition-20261013.json'
    assert mux4.physical_final_spec_path('v8_kelvin_tail_paths').name=='pcie-final-v8-kelvin-tail-paths-composition-20261013.json'
    assert mux4.physical_final_circuit_profile('v8_kelvin_tail_paths')=='final_drive_v8'
    assert mux4.physical_final_spec_path('v8_kelvin_local_tail').name=='pcie-final-v8-kelvin-local-tail-composition-20261013.json'
    assert mux4.physical_final_circuit_profile('v8_kelvin_local_tail')=='final_drive_v8'
    assert mux4.physical_final_spec_path('v8_kelvin_local_return').name=='pcie-final-v8-kelvin-local-return-composition-20261013.json'
    assert mux4.physical_final_circuit_profile('v8_kelvin_local_return')=='final_drive_v8'
    with pytest.raises(AssertionError):mux4.physical_final_spec_path('unproven_geometry')


@pytest.mark.parametrize('version,geometry', [('v6','kelvin_dense_wide'),('v7','kelvin_dense_wide'),('v8','kelvin_dense_wide'),('v8','kelvin_low_critical'),('v8','kelvin_low_selects'),('v9','kelvin_low_critical'),('v10','kelvin_low_critical'),('v11','kelvin_low_ports_loads_shunts_series')])
@pytest.mark.parametrize('reported_profile', ['final_drive_v5', 'final_drive_v6', 'final_drive_v7', 'final_drive_v8', 'final_drive_v9', 'final_drive_v10', 'final_drive_v11'])
@pytest.mark.parametrize('reported_variant', ['critical_buses_kelvin_dense_wide', 'critical_buses_kelvin_low_critical', 'critical_buses_kelvin_low_selects', 'critical_buses_power_trunks_vias', 'critical_buses_kelvin_low_ports_loads_shunts_series'])
def test_physical_binding_rejects_a_validly_hashed_wrong_circuit_archive(tmp_path, monkeypatch, reported_profile, version, geometry, reported_variant):
    import hashlib
    import io
    import json
    import shutil
    import tarfile
    expected_variant = 'critical_buses_'+geometry
    profile = mux4.physical_final_circuit_profile(version+'_'+geometry)
    assert profile == 'final_drive_'+version
    assert mux4.physical_final_circuit_profile('kelvin_dense_wide') == 'final_drive_v5'
    date = '20261014' if version == 'v11' else '20261013'
    assert mux4.physical_final_spec_path(version+'_'+geometry).name == 'pcie-final-'+version+'-'+geometry.replace('_','-')+'-composition-'+date+'.json'
    with pytest.raises(AssertionError):
        mux4.physical_final_circuit_profile('unproven_geometry')
    model = (ROOT/f'hw/soc/analog/pcie/tx_mux54_passive_drive_{version}.spice').read_bytes()
    outputs = {'mux54-compact01.spice': hashlib.sha256(model).hexdigest()}
    report = json.dumps(dict(circuit_profile=reported_profile, outputs=outputs,
                             variant=reported_variant)).encode()
    archive = tmp_path/'source.tar.gz'
    with tarfile.open(archive, 'w:gz') as packed:
        for name, raw in [('result.json', report), ('mux54-compact01.spice', model)]:
            info = tarfile.TarInfo('cloud-tx-layout-composition/'+name)
            info.size = len(raw)
            packed.addfile(info, io.BytesIO(raw))
    spec = tmp_path/'receipt.json'
    spec.write_text(json.dumps(dict(
        status='PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT',
        receipt=dict(url='unused', sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), bytes=archive.stat().st_size),
        summary_sha256=hashlib.sha256(report).hexdigest(), outputs=outputs,
        variant=expected_variant)))
    monkeypatch.setattr(mux4, 'fetch', lambda url, digest, path: shutil.copyfile(archive, path))
    if reported_profile != profile or reported_variant != expected_variant:
        with pytest.raises(AssertionError):
            mux4.physical_macro(tmp_path, 'physical_compact', spec, profile, 'restored')
    else:
        bound = mux4.physical_macro(tmp_path, 'physical_compact', spec, profile, 'restored')
        assert bound.read_bytes() == model


@pytest.mark.parametrize('version,changed_count,expected_nx', [('v6',16,{1:1,4:16,8:2}),('v7',12,{1:1,4:12,8:6}),('v8',16,{1:1,4:12,6:4,8:2}),('v9',16,{1:1,2:12,6:4,8:2}),('v10',16,{1:1,3:12,6:4,8:2}),('v11',4,{1:1,6:4,8:14})])
def test_final_override_keeps_original_oracle_and_accounts_for_actual_emitter_count(tmp_path,version,changed_count,expected_nx):
    from collections import Counter
    (tmp_path/'frontend').mkdir()
    (tmp_path/'frontend/buf16.inc').write_text("""
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 net1 A VDD VDD sg13_lv_pmos
XP0 X net1 VDD VDD sg13_lv_pmos
.ends
""")
    args = dict(clock_bias='native_res', pre_bias='native_res', output_bias='native_res', final_drive='double_taps_margin')
    before, old = mux4.build(tmp_path, 'nominal', **args)
    final = ROOT/f'hw/soc/analog/pcie/tx_mux54_passive_drive_{version}.spice'
    after, new = mux4.build(tmp_path, 'nominal', final_override=final, **args)
    for key in ('bits','source_bits_sha256','tree_plan','mos','clock_refs','rails'):
        assert new[key] == old[key]
    changed = {name for name in new['hbt'] if new['hbt'][name] != old['hbt'][name]}
    assert len(changed) == changed_count and all(name.startswith('xmux.') for name in changed)
    for name in changed:
        assert old['hbt'][name]['nx'] == 8
        expected = 6 if version in ('v8','v9','v10','v11') and new['hbt'][name]['terminals'][1] in ('sp','sn') else {'v9':2,'v10':3,'v11':8}.get(version,4)
        assert new['hbt'][name]['nx'] == expected
        assert {k:v for k,v in old['hbt'][name].items() if k != 'nx'} == {k:v for k,v in new['hbt'][name].items() if k != 'nx'}
    assert Counter(row['nx'] for name,row in new['hbt'].items() if name.startswith('xmux.')) == expected_nx
    assert [l for l in before.splitlines() if l.startswith('V')] == [l for l in after.splitlines() if l.startswith('V')]


def test_cascade16_changes_only_two_native_output_pulldowns():
    def devices(version):
        text=(ROOT/f'hw/soc/analog/pcie/tx_mux2_hbt_cascade_{version}.spice').read_text()
        return {line.split()[0]:line.split()[1:] for line in text.splitlines() if line.startswith('X')}
    old, new=devices('v2'), devices('v3')
    assert len(old)==len(new)==27 and set(old)==set(new)
    assert {name for name in old if old[name]!=new[name]}=={'XFPR','XFNR'}
    for name in old:
        expected=[('l=16.0u' if value=='l=14.0u' else value) for value in old[name]]
        assert new[name]==expected


@pytest.mark.parametrize('reported_profile', ['cascade14','cascade16','cascade158'])
@pytest.mark.parametrize('requested,expected_profile,version,variant', [
    ('cascade16_kelvin_dense_wide','cascade16','v3','critical_buses_kelvin_dense_wide'),
    ('cascade158_kelvin_supply_direct','cascade158','v4','critical_buses_kelvin_supply_direct'),
])
def test_new_prestage_rejects_validly_hashed_old_circuit(tmp_path, monkeypatch, reported_profile,
                                                       requested, expected_profile, version, variant):
    import hashlib
    import io
    import json
    import shutil
    import tarfile
    assert mux4.physical_spec_path(requested).name=='pcie-'+requested.replace('_','-')+'-composition-20261013.json'
    assert mux4.physical_prestage_circuit_profile(requested)==expected_profile
    assert mux4.physical_prestage_circuit_profile('kelvin_dense_wide')=='cascade14'
    with pytest.raises(AssertionError):
        mux4.physical_prestage_circuit_profile('unproven_prestage')
    model=(ROOT/f'hw/soc/analog/pcie/tx_mux2_hbt_cascade_{version}.spice').read_bytes()
    outputs={'mux54-compact01.spice':hashlib.sha256(model).hexdigest()}
    report=json.dumps(dict(circuit_profile=reported_profile,outputs=outputs,
                           variant=variant)).encode()
    archive=tmp_path/'source.tar.gz'
    with tarfile.open(archive,'w:gz') as packed:
        for name,raw in [('result.json',report),('mux54-compact01.spice',model)]:
            info=tarfile.TarInfo('cloud-tx-layout-composition/'+name)
            info.size=len(raw);packed.addfile(info,io.BytesIO(raw))
    spec=tmp_path/'receipt.json'
    spec.write_text(json.dumps(dict(
        status='PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT',
        receipt=dict(url='unused',sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size),
        summary_sha256=hashlib.sha256(report).hexdigest(),outputs=outputs,
        variant=variant)))
    def selected_spec(profile):
        assert profile==requested
        return spec
    monkeypatch.setattr(mux4,'physical_spec_path',selected_spec)
    monkeypatch.setattr(mux4,'fetch',lambda url,digest,path:shutil.copyfile(archive,path))
    if reported_profile!=expected_profile:
        with pytest.raises(AssertionError):
            mux4.physical_prestage(tmp_path,'physical_compact',requested)
    else:
        bound=mux4.physical_prestage(tmp_path,'physical_compact',requested)
        assert bound.read_bytes()==model


def test_offset_reference_changes_only_native_resistor_and_preserves_clock_oracle(tmp_path):
    def devices(path):
        return {f[0]:f for line in path.read_text().splitlines()
                if (f:=line.lower().split()) and f[0].startswith('x')}
    old=devices(mux4.CLOCK_REFERENCES['baseline'])
    new=devices(mux4.CLOCK_REFERENCES['offset75'])
    assert old.keys()==new.keys()=={'xref','xoffset'}
    assert old['xref']==new['xref']
    assert old['xoffset']==['l=6.5u' if f=='l=7.5u' else f for f in new['xoffset']]
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
    args=dict(clock_bias='native_res',pre_bias='native_res',output_bias='native_res')
    before,b=mux4.build(tmp_path,'hot_low',**args)
    after,a=mux4.build(tmp_path,'hot_low',clock_reference='offset75',**args)
    for key in ('hbt','mos','bits','tree_plan','condition','rails','vectors','source_bits_sha256'):
        assert a[key]==b[key]
    assert a['clock_reference_sha256'] != b['clock_reference_sha256']
    assert 'XCLKBIAS clkbias 0 0 nssoc_tx_clock_common_bias_v2' in after
    assert 'ICLKBIAS' not in after
    for key in ('sap','san','sbp','sbn','sp','sn'):
        stimulus=lambda text:text.split('V'+key+' ')[1].split('R'+key+' ')[0]
        assert stimulus(before)==stimulus(after)
    with pytest.raises(AssertionError):
        mux4.build(tmp_path,'hot_low',clock_reference='offset75',clock_bias='ideal')
    with pytest.raises(AssertionError):
        mux4.build(tmp_path,'hot_low',clock_reference='unknown',**args)

@pytest.mark.parametrize('condition', ['nominal', 'hot_low', 'cold_high'])
def test_stiff_reference_keeps_fixed_native_pair_and_original_clock_oracle(tmp_path, condition):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text("""
.subckt sg13g2_buf_16 X A VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 net1 A VDD VDD sg13_lv_pmos
XP0 X net1 VDD VDD sg13_lv_pmos
.ends
""")
    args=dict(clock_bias='native_res', pre_bias='native_res', output_bias='native_res')
    before,b=mux4.build(tmp_path,condition,clock_reference='offset75',**args)
    after,a=mux4.build(tmp_path,condition,clock_reference='stiff65',**args)
    for key in ('hbt','mos','bits','tree_plan','condition','rails','vectors','source_bits_sha256'):
        assert a[key]==b[key]
    assert a['clock_reference_sha256']!=b['clock_reference_sha256']
    assert a['clock_feed_sha256']!=b['clock_feed_sha256']
    assert a['clock_feed_sha256']==mux4.sha(mux4.CLOCK_FEEDS['stiff65'])
    assert 'XCLKBIAS clkbias 0 0 nssoc_tx_clock_common_bias_v3' in after
    assert 'XCLKFEED clkfeed clkbias 0 nssoc_tx_clock_bias_feed_v2' in after
    assert 'nssoc_tx_clock_bias_feed_v1' not in after
    assert not any(line.lower().startswith('i') for line in after.splitlines())
    # Every stimulus, source resistor and all data-path instances remain exact.
    def invariant_lines(deck):
        return [line for line in deck.splitlines()
                if not line.startswith(('.include ', 'XCLKBIAS', 'XCLKFEED'))]
    assert invariant_lines(before)==invariant_lines(after)
    offset=mux4.CLOCK_REFERENCES['stiff65'].read_text()
    feed=mux4.CLOCK_FEEDS['stiff65'].read_text()
    assert 'XREF cm cm er sub npn13G2 Nx=1' in offset
    assert 'XOFFSET er avss sub rppd w=4u l=6.5u b=0 sw_et=1' in offset
    assert 'XFEED avdd cm sub rppd w=4u l=14.5u b=0 sw_et=1' in feed
    with pytest.raises(AssertionError):
        mux4.build(tmp_path,condition,clock_reference='stiff65',clock_bias='ideal')


@pytest.mark.parametrize('count',[1,999,1000,1001,4096,9999])
def test_native_save_batches_preserve_every_observation_and_writer_limit(count):
    vectors=[f'v(n{i})' for i in range(count)]
    commands=mux4.native_save_commands(vectors)
    assert [name for command in commands for name in command.split()[1:]]==vectors
    assert all(command.startswith('save ') and len(command.split())-1<=1000 for command in commands)
    if count<=1000:
        assert commands==['save '+' '.join(vectors)]
    else:
        assert max(len(command.split())-1 for command in commands)<=128


@pytest.mark.parametrize('vectors',[[],['v(a)','v(a)'],[f'v(n{i})' for i in range(10000)]])
def test_native_capture_rejects_empty_duplicate_or_unwritable_census(vectors):
    with pytest.raises(AssertionError):
        mux4.native_save_commands(vectors)


@pytest.mark.parametrize('streams',[4,32])
@pytest.mark.parametrize('mode',['output_feedback','output_feedback_tc'])
def test_output_feedback_is_loaded_by_actual_stage_outputs(tmp_path,streams,mode):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'mux54-compact01.spice').write_text(mux4.PRE.read_text())
    (tmp_path/'frontend/buf16.inc').write_text("""
.subckt sg13g2_buf_16 A X VDD VSS
XN1 net1 A VSS VSS sg13_lv_nmos
XN0 X net1 VSS VSS sg13_lv_nmos
XP1 net1 A VDD VDD sg13_lv_pmos
XP0 X net1 VDD VDD sg13_lv_pmos
.ends
""")
    args=dict(streams=streams,clock_bias='native_res',output_bias='native_res')
    subckt='nssoc_tx_pre_bias_feedback_tc_v1' if mode=='output_feedback_tc' else 'nssoc_tx_pre_bias_feedback_v1'
    before,old=mux4.build(tmp_path,'cold_high_res_wcs',pre_bias='native_res',**args)
    after,new=mux4.build(tmp_path,'cold_high_res_wcs',pre_bias=mode,**args)
    for key in ('hbt','mos','bits','source_bits_sha256','tree_plan','rails','clock_refs','condition','vectors'):
        assert new[key]==old[key]
    assert not any(l.lower().startswith('i') for l in after.splitlines())
    assert after.count(subckt)==streams-2
    for node in new['tree_plan']['nodes']:
        ref,label=node['reference'],node['label']
        assert f'XPREBIAS_{ref} {label}p {label}n prefeed_{ref} 0 {subckt}' in after
        assert f'Vprebias_{ref} prefeed_{ref} {ref} 0' in after
        assert f'Vprebias_{ref} avdd' not in after
    broken,c=mux4.build(tmp_path,'cold_high_res_wcs',pre_bias=mode,fault='disable_pre_b_bias',**args)
    assert 'XPREBIAS_rb ' not in broken and c['bits']==new['bits']
    assert broken.count(subckt)==streams-3
    for key in ('sap','san','sbp','sbn','sp','sn'):
        stimulus=lambda deck:deck.split('V'+key+' ')[1].split('R'+key+' ')[0]
        assert stimulus(before)==stimulus(after)


def test_physical_final_receipts_supply_required_native_runtime_metadata():
    import ast
    import json
    # Read the actual supported profiles rather than duplicating a second list.
    tree = ast.parse((ROOT/'scripts/run_cloud_tx_mux4.py').read_text())
    choices = next(keyword.value for call in ast.walk(tree)
                   if isinstance(call, ast.Call) and call.args
                   and isinstance(call.args[0], ast.Constant)
                   and call.args[0].value == '--physical-final-profile'
                   for keyword in call.keywords if keyword.arg == 'choices')
    for profile in ast.literal_eval(choices):
        spec = json.loads(mux4.physical_final_spec_path(profile).read_text())
        assert spec['status'] == 'PASS_SOURCE_BOUND_NATIVE_DEVICE_WIRE_COMPOSITION_REQUIRES_TRANSIENT'
        assert spec['counts']['devices'] == 54
        assert all(isinstance(spec['counts'][key], int) and spec['counts'][key] > 0 for key in ('R', 'C'))
        assert all(len(spec['outputs'][name]) == 64 for name in ('mux54-wire01.spice','mux54-compact01.spice'))


@pytest.mark.parametrize('nx',[4,5,6,8])
def test_v11_data_area_binds_current_density_to_changed_emitters(tmp_path,nx):
    names=[f'XD{i:04d}' for i in (*range(41,47),*range(49,55))]
    text='.subckt v11 c b e s\n'+''.join(f'{name} c b e s npn13G2 Nx=8\n' for name in names)
    text+='XD0047 c b e s npn13G2 Nx=8\nXD0001 c b e s npn13G2 Nx=6\nR1 c b 2.5\nC1 b e 2f\n.ends\n'
    changed,receipt=mux4.diagnostic_v11_data_area(text,nx)
    p=tmp_path/'changed.spice';p.write_text(changed)
    _,devices=mux4.bind_devices(p,'xmux',['c','b','e','s'],{'npn13g2'})
    assert all(devices['xmux.'+n.lower()]['nx']==nx for n in names)
    assert devices['xmux.xd0047']['nx']==8 and devices['xmux.xd0001']['nx']==6
    assert changed.split('XD0047')[1]==text.split('XD0047')[1]
    assert not receipt['physical_accepted'] and receipt['device_geometry_matches_layout']==(nx==8)
    assert (changed==text)==(nx==8)
    for broken in (text.replace('XD0041','XD9999'),text.replace('Nx=8','Nx=7',1),
                   text.replace('.ends','XD0041 c b e s npn13G2 Nx=8\n.ends'),
                   text.replace('XD0041 c b e s npn13G2','XD0041 c b e s other')):
        with pytest.raises(AssertionError):mux4.diagnostic_v11_data_area(broken,nx)
