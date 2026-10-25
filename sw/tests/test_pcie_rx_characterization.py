# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail closed on missing RX evidence, native stress and untested coverage."""
import itertools
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import characterize_pcie_rx as rx  # noqa: E402
import review_pcie_rx as review  # noqa: E402


def test_exact_native_topology_and_independent_bulk():
    lines=[line for line in rx.NETLIST.read_text().splitlines() if line and not line.startswith('*')]
    assert lines[0].split()==['.subckt','nssoc_rx_hbt_rsil','inp','inn','outp','outn','avdd','avss','sub','iref','vcm']
    assert lines[-1]=='.ends nssoc_rx_hbt_rsil'
    assert len(lines)==10 and all(line.startswith('X')for line in lines[1:-1])
    assert [line.split()for line in lines[1:5]]==[
        ['XREF','iref','iref','avss','sub','npn13G2','Nx=1'],
        ['XTAIL','tail','iref','avss','sub','npn13G2','Nx=4'],
        ['XP','outn','inp','tail','sub','npn13G2','Nx=4'],
        ['XN','outp','inn','tail','sub','npn13G2','Nx=4']]
    assert {tuple(line.split()[1:4])for line in lines[5:9]}=={
        ('inp','vcm','sub'),('inn','vcm','sub'),('avdd','outp','sub'),('avdd','outn','sub')}
    assert all('b=0 sw_et=1'in line for line in lines[5:9])
    assert sum('w=10u l=70.215u'in line for line in lines)==2
    assert sum('w=2u l=41.785u'in line for line in lines)==2


def test_matrix_crosses_native_process_resistor_temperature_supply_without_waivers():
    cases=rx.cases();assert len(cases)==96 and len({c['name']for c in cases})==96
    matrix=[c for c in cases if c['name'].startswith('hbt_')]
    assert {(c['hbt'],c['resistor'],c['temp'],c['supply'])for c in matrix}==set(itertools.product(
        ('hbt_typ','hbt_bcs','hbt_wcs'),('res_typ','res_bcs','res_wcs'),(-40,27,125),(1.71,1.8,1.89)))
    assert all(c['fault']is None and c['vcm']==1.36 and c['reference_a']==.0005 for c in matrix)
    assert {c['fault']for c in cases if c['fault']}=={
        'no_bias','swapped','overload','tiny_input','low_common_mode','clipped_overbias'}
    assert len(rx.cases(True))==16
    assert next(c for c in cases if c['name']=='half_timestep')['step_s']==.5e-12
    assert rx.LIMITS['min_margin_v']==.1 and rx.LIMITS['min_vce_v']==.4 and rx.LIMITS['max_vce_v']==1.6


def test_deck_has_real_loading_and_explicit_external_bias(tmp_path):
    case=rx.cases(True)[0];text,bits=rx.deck(case,tmp_path,tmp_path/'native.osdi')
    assert len(bits)==254 and bits[:127]==bits[127:]
    assert 'RSP sp ip 50\nRSN sn inn 50'in text
    assert 'VCM cm 0 1.36'in text and 'IREF avdd ref 0.0005'in text
    assert 'XRX ip inn op on avdd 0 0 ref cm nssoc_rx_hbt_rsil'in text
    assert '.lib 'in text and 'pre_osdi 'in text and '1e-12'in text
    # Physical netlist is independent of the 50-ohm Thevenin bench sources.
    assert all(not line.startswith(('B','E','F','G','H'))for line in rx.NETLIST.read_text().splitlines())
    ac,_=rx.deck(case,tmp_path,tmp_path/'native.osdi',ac=True)
    assert 'VP sp 0 DC 1.36 AC .5'in ac and 'VN sn 0 DC 1.36 AC .5 180'in ac
    assert 'let zd=(v(ip)-v(inn))/((i(vn)-i(vp))/2)'in ac
    assert 'PWL('not in ac and 'ac dec 40 1Meg 20Gig'in ac


def test_negative_decks_change_actual_circuit_or_stimulus_not_verdict_only(tmp_path):
    cases={c['name']:c for c in rx.cases(True)}
    assert 'IREF avdd ref 0'in rx.deck(cases['no_bias'],tmp_path,tmp_path/'r.osdi')[0]
    assert 'XRX ip inn on op'in rx.deck(cases['swapped_output'],tmp_path,tmp_path/'r.osdi')[0]
    assert 'CP op 0 1e-10'in rx.deck(cases['overload'],tmp_path,tmp_path/'r.osdi')[0]
    assert 'VCM cm 0 1.1'in rx.deck(cases['low_common_mode'],tmp_path,tmp_path/'r.osdi')[0]
    assert 'IREF avdd ref 0.003'in rx.deck(cases['clipped_overbias'],tmp_path,tmp_path/'r.osdi')[0]
    pts=re.findall(r'\+ ([0-9.e+-]+) ([0-9.e+-]+)',rx.stimulus([1,0],cases['tiny_input']))
    assert max(float(v)for _,v in pts)-min(float(v)for _,v in pts)==pytest.approx(.01)


@pytest.fixture
def wave(tmp_path,monkeypatch):
    monkeypatch.setattr(rx,'BITS',20);monkeypatch.setattr(rx,'STOP',4.5e-9)
    bits=[i%2 for i in range(20)];case=rx.cases(True)[0];rows=[]
    for j in range(4501):
        t=j*1e-12;bit=bits[max(0,min(19,int((t-rx.START)/rx.UI)))];sign=1 if bit else-1
        values=[1.36+.04*sign,1.36-.04*sign,1.5+.2*sign,1.5-.2*sign,.55,.85,
                -.0025,-.000001,-.0008*sign,.0008*sign,.002,.001,.001,.0005,.5,.5,.01,.01]
        rows.append([t,*values])
    p=tmp_path/'wave.dat';p.write_text(' '.join(['time',*rx.VECTORS])+'\n'+
        '\n'.join(' '.join(map(str,row))for row in rows)+'\n')
    return p,case,bits


def test_actual_measurement_numbers(wave):
    result=rx.measure(*wave)
    assert result['screen_pass'] and result['sign_errors']==0 and result['samples']==12
    assert result['min_signed_margin_v']==pytest.approx(.4)
    assert result['minimum_loaded_input_differential_v']==pytest.approx(.08)
    assert result['analog_supply_power_w']==pytest.approx(.0045)
    assert result['common_mode_supply_power_w']==pytest.approx(.00000136)
    assert result['max_native_resistor_temperature_rise_k']==.5
    assert result['min_vce_v']==.55 and result['max_vce_v']==pytest.approx(1.15)


@pytest.mark.parametrize('fault',['truncated','nan','wrong_header','extra_column','time_gap','duplicate_time'])
def test_corrupt_native_waveform_is_rejected(wave,fault):
    p,case,bits=wave;lines=p.read_text().splitlines()
    if fault=='truncated':lines.pop()
    elif fault=='nan':lines[100]=lines[100].replace('1.4','nan')
    elif fault=='wrong_header':lines[0]=lines[0].replace('v(op)','v(other)')
    elif fault=='extra_column':lines[100]+=' 0'
    elif fault=='time_gap':lines.pop(100)
    else:lines[100]=lines[99]
    p.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError):rx.measure(p,case,bits)


@pytest.mark.parametrize('fault,check',[
    ('reverse','margin'),('zero_signal','margin'),('low_tail','vce_headroom'),
    ('high_vce','vce_maximum'),('low_current','active_tail_current'),
    ('overcurrent','current_density'),('input_overrail','input_within_rails')])
def test_faulty_transistor_response_cannot_pass(wave,fault,check):
    p,case,bits=wave;lines=p.read_text().splitlines();header=lines[0].split()
    for i in range(1,len(lines)):
        row=lines[i].split()
        if fault=='reverse':row[3],row[4]=row[4],row[3]
        elif fault=='zero_signal':row[3]=row[4]='1.5'
        elif fault=='low_tail':row[5]='.2'
        elif fault=='high_vce':row[3]='2.3'
        elif fault=='low_current':row[header.index('@q.xrx.xtail.qnpn13g2[ic]')]='.0001'
        elif fault=='overcurrent':row[header.index('@q.xrx.xp.qnpn13g2[ic]')]='.02'
        else:row[1]='2.0'
        lines[i]=' '.join(row)
    p.write_text('\n'.join(lines)+'\n');got=rx.measure(p,case,bits)
    assert not got['checks'][check] and not got['screen_pass']


def test_ac_impedance_and_gain_and_missing_frequency_detection(tmp_path):
    p=tmp_path/'ac.dat';header='frequency zd_r zd_i gd_r gd_i\n'
    values=['1000000 99 -.1 5 -.1','1000000000 98 -1 4.8 -1','4000000000 97 -2 4 -2',
            '8000000000 93 -4 2 -3','20000000000 85 -8 1 -4']
    p.write_text(header+'\n'.join(values)+'\n');m=rx.measure_ac(p)
    assert m['low_frequency_impedance_ohm']['real']==99 and m['at_4GHz']['gd_r']==4
    p.write_text(header+'\n'.join(values[:-1])+'\n')
    with pytest.raises(ValueError):rx.measure_ac(p)


@pytest.mark.parametrize('message', [
    'The temperature limiting function received NaN.',
    'Warning: singular matrix: check internal node',
    'Note: Starting dynamic gmin stepping\nNote: Dynamic gmin stepping completed',
    'OSDI(debug): WARNING: Irb current density is greater than specified by jmax',
    'OSDI(debug): WARNING: V(i1,c) voltage is greater than specified by vmax'])
def test_recovery_and_finite_samples_cannot_hide_numerical_failure(message):
    result = review.diagnostics(message+'\nInitial Transient Solution\nNo. of Data Rows : 34520\nngspice-42 done\n')
    assert not result['numerical_clean'] and result['lines']
    assert review.diagnostics('No. of Data Rows : 34520\nngspice-42 done')['numerical_clean']


def test_ac_review_requires_complete_original_bias_and_process_pairs():
    rows = [dict(case=dict(rx.cases()[0], hbt=h, resistor=r, temp=27, supply=1.8),
                 execution={'returncode': 0}) for h, r in itertools.product(
                     ('hbt_typ', 'hbt_bcs', 'hbt_wcs'), ('res_typ', 'res_bcs', 'res_wcs'))]
    result = dict(quick=False, ac_cases=rows)
    review.ac_contract(result)
    with pytest.raises(ValueError, match='coverage'):
        review.ac_contract(dict(result, ac_cases=rows[:-1]))
    with pytest.raises(ValueError, match='coverage'):
        review.ac_contract(dict(result, ac_cases=[rows[0], *rows[0:8]]))
    rows[0]['case']['vcm'] = 1.2
    with pytest.raises(ValueError, match='bias'):
        review.ac_contract(result)


def test_compressed_native_bytes_and_symlinks_are_not_trusted(tmp_path):
    import gzip
    import hashlib
    content = b'time voltage\n0 1\n1e-12 2\n'
    archive = tmp_path/'wave.gz'; archive.write_bytes(gzip.compress(content))
    target = tmp_path/'wave.dat'
    digest = hashlib.sha256(content).hexdigest()
    review.unpack_wave(archive, target, digest)
    assert target.read_bytes() == content
    with pytest.raises(ValueError, match='pin'):
        review.unpack_wave(archive, tmp_path/'wrong.dat', '0'*64)
    link = tmp_path/'link'; link.symlink_to(target)
    with pytest.raises(ValueError, match='pin'):
        review.verify(link, digest)
    with pytest.raises(ValueError, match='pin'):
        review.verify(target, '0'*64)


def test_timestep_review_recomputes_measurements_instead_of_trusting_pass():
    rows = [dict(case={'name': name}, measurement={'min_signed_margin_v': margin,
             'analog_supply_power_w': power}) for name, margin, power in (
                 ('hbt_typ_res_typ_27_1.8', .2, .004), ('half_timestep', .20002, .004001))]
    result = review.sensitivity(rows)
    assert result['screen_pass'] and result['margin_difference_v'] == pytest.approx(.00002)
    rows[1]['measurement']['min_signed_margin_v'] = .202
    assert not review.sensitivity(rows)['screen_pass']


def test_partial_capsule_requires_exact_named_subset_and_never_substitutes_missing_wave(tmp_path):
    import lzma
    folder = tmp_path/'case'; folder.mkdir()
    original = {}
    for name in ('bench.cir', 'run.log', 'rx_hbt_rsil.spice'):
        path = folder/name; path.write_text(name); original[name] = rx.tx.sha(path)
    original['wave.dat.gz'] = 'a'*64
    entry = dict(case={'name': 'hbt_typ_res_typ_27_1.8'}, output_sha256=original)
    with pytest.raises(ValueError, match='inventory'):
        review.transient_files(folder, entry, True)
    wave = folder/'wave.dat.xz'; wave.write_bytes(lzma.compress(b'raw original wave'))
    assert review.transient_files(folder, entry, True) == wave
    with pytest.raises(ValueError, match='inventory'):
        review.transient_files(folder, entry, False)
    entry['case']['name'] = 'another_case'
    with pytest.raises(ValueError, match='inventory'):
        review.transient_files(folder, entry, True)
    wave.unlink()
    assert review.transient_files(folder, entry, True) is None
    (folder/'run.log').write_text('altered warning')
    with pytest.raises(ValueError, match='pin'):
        review.transient_files(folder, entry, True)
