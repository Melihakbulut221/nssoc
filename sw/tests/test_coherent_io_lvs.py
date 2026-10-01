# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Coherent-view, exact tap dialect and native failure contracts; no native work."""
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_coherent_io_lvs as runner  # noqa: E402
from test_extract_gds_hierarchy import cell, library, ref  # noqa: E402
from test_io_tap_topology_audit import CDL, LEF  # noqa: E402


def test_ap_tap_dialect_is_reversible_and_preserves_order_values_and_globals():
    raw = '.GLOBAL explicit\n.SUBCKT TAP first second\n  XR3 first second ptap1 A=141.253p P=47.54u\n.ENDS TAP\n'
    text, changes = runner.normalize_main_taps(raw)
    assert text == raw.replace('XR3', 'R3')
    assert changes == [dict(line=3, before='  XR3 first second ptap1 A=141.253p P=47.54u\n',
        after='  R3 first second ptap1 A=141.253p P=47.54u\n',
        reason='R-prefixed native CustomTap; same ordered nodes and explicit A/P')]
    selected, _, globals_ = runner.select_io_cdl(text, 'TAP')
    assert globals_ == ['explicit'] and '.GLOBAL sub!' not in selected
    assert 'R3 first second ptap1 A=141.253p P=47.54u' in selected
    absent = raw.replace('.GLOBAL explicit\n','')
    converted, _ = runner.normalize_main_taps(absent)
    assert runner.select_io_cdl(converted, 'TAP')[2] == []


@pytest.mark.parametrize('line', [
    'XR0 a b ptap1 A=1p P=2u m=2', 'XR0 a b ptap1 A=1p A=2p',
    'XR0 a b ptap1 P=2u A=1p', 'XR0 a b other A=1p P=2u',
    'XR0 a b ptap1 A=-1p P=2u', 'XR0 a b ptap1 A=1p P=0',
    'XR0 a b ptap1 A=nan P=2u', 'XR0 a b c ptap1 A=1p P=2u',
    'XR0 a b / ptap1 A=1p P=2u', 'XR0 a b ptap1 A=1p Perim=2u',
    'XR0 a b ptap1 A=1p P=2u\r\n',
])
def test_tap_adapter_rejects_ambiguous_or_unreviewed_dialects(line):
    with pytest.raises(ValueError):
        runner.normalize_main_taps(line)


def fixture_views(tmp_path, monkeypatch, fault=None):
    text = CDL.replace('.ends', 'XR0 anode sub! ptap1 A=141.253p P=47.54u\n.ends', 1)
    if fault == 'guard':
        text = text.replace('XI1 iovss vss iovdd', 'XI1 iovss vss iovss')
    content = {'gds':library(cell('sg13g2_DCNDiode'),cell('sg13g2_DCPDiode'),
        cell(runner.TOP,ref('sg13g2_DCNDiode')+ref('sg13g2_DCPDiode'))),
        'cdl':text.encode(), 'lef':LEF.encode()}
    monkeypatch.setattr(runner, 'GDS_PREFIX_BYTES', len(content['gds']))
    monkeypatch.setattr(runner, 'GDS_ZERO_PADDING_BYTES', 12)
    content['gds'] += bytes(12)
    pins = {}
    for kind, raw in content.items():
        path = tmp_path/('source.'+kind)
        path.write_bytes(raw)
        identity = runner.topology.file_identity(path)
        pins[kind] = (len(raw), identity['git_blob_sha1'])
    monkeypatch.setattr(runner, 'VIEWS', pins)
    def open_url(url, timeout):
        assert runner.COMMIT in url and timeout == 60
        kind = url.rsplit('.',1)[1]
        data = content[kind]
        if fault == 'mixed-gds' and kind == 'gds':
            data = data.replace(b'sg13g2_DCNDiode', b'sg13g2_DCPDiode')
        if fault == 'oversized' and kind == 'gds':
            data += b'bad'
        return io.BytesIO(data)
    monkeypatch.setattr(runner.urllib.request, 'urlopen', open_url)
    return content


def test_prepare_uses_one_commit_and_preserves_byte_subset_and_reference(tmp_path, monkeypatch):
    content = fixture_views(tmp_path, monkeypatch)
    out = tmp_path/'out';out.mkdir()
    record = runner.prepare(out)
    assert record['commit'] == runner.COMMIT
    assert record['explicit_globals'] == [] and record['globals_inferred'] is False
    assert record['ordered_pin_contract']['old_actual_indices_for_new_order'] == [2,3,0,1]
    assert record['ordered_pin_contract']['old_callers_changed'] is False
    assert record['subset']['geometry_records_modified'] is False
    assert record['tap_parameters_changed'] is False
    assert (out/'inputs/sg13g2_io.cdl').read_bytes() == content['cdl']
    assert (out/'inputs/sg13g2_io.gds').read_bytes() == content['gds']
    assert (out/'inputs/subset/subset.gds').read_bytes() == content['gds'][:-12]
    assert (out/'inputs/unpadded-source.gds').read_bytes() == content['gds'][:-12]
    assert record['padding_transport_adapter']['padding']['bytes'] == 12
    assert record['padding_transport_adapter']['original_retained'] is True
    assert 'R0 anode sub! ptap1 A=141.253p P=47.54u' in (out/'inputs/schematic.cir').read_text()


def test_model_less_unrelated_tap_is_not_invented_or_selected():
    good = CDL.replace('.ends', 'XR0 anode sub! ptap1 A=141.253p P=47.54u\n.ends', 1)
    unrelated = '.SUBCKT unrelated a b\nXR0 a b A=19.141p P=17.5u\n.ENDS\n'
    selected_raw, adapted, changes, cells, globals_ = runner.vss_reference(good+unrelated)
    assert len(cells) == 3 and len(changes) == 1 and globals_ == []
    assert 'unrelated' not in selected_raw and '19.141p' not in adapted
    # The same incomplete primitive inside the selected closure is fatal.
    with pytest.raises(ValueError):
        runner.vss_reference(good.replace('ptap1 A=141.253p', 'A=141.253p'))
    with pytest.raises(ValueError):
        runner.vss_reference(good.replace('XI1 iovss vss iovdd / sg13g2_DCNDiode',
            'XI1 iovss vss iovdd / unknown_child'))


@pytest.mark.parametrize('fault',['mixed-gds','oversized','guard'])
def test_prepare_rejects_mixed_bytes_or_old_wrong_guard(tmp_path, monkeypatch, fault):
    fixture_views(tmp_path, monkeypatch, fault)
    out = tmp_path/'out';out.mkdir()
    with pytest.raises(ValueError):
        runner.prepare(out)
    assert not (out/'inputs/preparation.json').exists()


def test_download_never_overwrites_an_existing_input(tmp_path):
    dest = tmp_path/'view.gds';dest.write_bytes(b'original')
    with pytest.raises(FileExistsError):
        runner.download_view('gds',dest)
    assert dest.read_bytes() == b'original'


@pytest.mark.parametrize('fault', ['nonzero-tail','wrong-length','wrong-endlib','source-mutation','occupied-output'])
def test_padding_transport_rejects_nonpadding_corruption_and_preserves_original(tmp_path,monkeypatch,fault):
    content=fixture_views(tmp_path,monkeypatch)
    source=tmp_path/'padded.gds';source.write_bytes(content['gds'])
    output=tmp_path/'prefix.gds'
    if fault=='nonzero-tail': source.write_bytes(content['gds'][:-1]+b'X')
    if fault=='wrong-length': source.write_bytes(content['gds']+b'\0')
    if fault=='wrong-endlib':
        raw=bytearray(content['gds']);raw[runner.GDS_PREFIX_BYTES-2]=5;source.write_bytes(raw)
    # Pin malformed fixtures deliberately so ENDLIB/tail rules, not just the
    # upstream hash check, must reject them.
    identity=runner.topology.file_identity(source)
    runner.VIEWS['gds']=(identity['bytes'],identity['git_blob_sha1'])
    before=source.read_bytes()
    if fault=='occupied-output': output.write_bytes(b'existing')
    if fault=='source-mutation':
        verify=runner.topology.verify_view
        def changed(*args):
            result=verify(*args)
            data=bytearray(source.read_bytes());data[10]^=1;source.write_bytes(data)
            return result
        monkeypatch.setattr(runner.topology,'verify_view',changed)
    with pytest.raises((ValueError,FileExistsError)):
        runner.unpad_coherent_gds(source,output)
    if fault=='occupied-output': assert output.read_bytes()==b'existing'
    else: assert not output.exists()
    if fault!='source-mutation': assert source.read_bytes()==before


def test_exact_native_flags_do_not_add_virtual_joins_or_parameter_exemptions(tmp_path):
    deep = runner.command(Path('deck'),tmp_path,tmp_path/'case','deep')
    flat = runner.command(Path('deck'),tmp_path,tmp_path/'case','flat')
    assert [(a,b) for a,b in zip(deep,flat,strict=True) if a!=b] == [('run_mode=deep','run_mode=flat')]
    values = dict(word.split('=',1) for word in deep[7::2])
    assert values['topcell'] == runner.TOP
    assert values['disable_tap_extraction'] == values['ignore_top_ports_mismatch'] == 'false'
    assert set(values) == {'input','schematic','topcell','report','log','target_netlist','run_mode','thr','disable_tap_extraction','ignore_top_ports_mismatch'}
    with pytest.raises(ValueError):
        runner.command(Path('deck'),tmp_path,tmp_path,'waived')


def make_audit(tmp_path, passed):
    case=tmp_path/'case';case.mkdir()
    for name in ('lvs.lvsdb.gz','extracted.cir'):
        (case/name).write_bytes(b'synthetic small audit contract, not native evidence')
    log='INFO : Congratulations! Netlists match.' if passed else "ERROR : Netlists don't match"
    (case/'deck.log').write_text(log)
    rows=[dict(layout=runner.TOP,schematic=runner.TOP,status='Match' if passed else 'NoMatch',
        layout_devices_recursive=3,schematic_devices_recursive=3)]
    audit=runner.native.assess(rows,runner.TOP,log)
    audit['inputs']={str(case/name):dict(bytes=(case/name).stat().st_size,sha256=runner.native.sha(case/name)) for name in ('lvs.lvsdb.gz','deck.log')}
    (case/'audit.json').write_text(json.dumps(audit))
    return case,audit


@pytest.mark.parametrize('passed',[True,False])
def test_native_exit_zero_does_not_turn_mismatch_into_pass(tmp_path,passed):
    case,audit=make_audit(tmp_path,passed)
    assert runner.strict_verdict(case,{'returncode':0},{'returncode':0 if passed else 1}) == audit


@pytest.mark.parametrize('fault',['native-abort','wrong-top','changed-report','skipped-circuit','missing-report','warning'])
def test_incomplete_or_forged_native_audit_is_rejected(tmp_path,fault):
    case,audit=make_audit(tmp_path,True)
    execution={'returncode':0}
    if fault=='native-abort': execution['returncode']=-6
    if fault=='wrong-top': audit['top']='OTHER'
    if fault=='changed-report': (case/'lvs.lvsdb.gz').write_bytes(b'changed')
    if fault=='skipped-circuit': audit['circuits'][0]['status']='Skipped'
    if fault=='missing-report': (case/'extracted.cir').unlink()
    if fault=='warning': audit['extraction_diagnostics']=[dict(severity='Warning',category='must-connect')]
    (case/'audit.json').write_text(json.dumps(audit))
    with pytest.raises(ValueError):
        runner.strict_verdict(case,execution,{'returncode':0})


def test_low_resources_prevent_download_or_native_launch(tmp_path,monkeypatch):
    monkeypatch.setattr(runner.native,'OUTPUT_ROOT',tmp_path)
    def no_resources(): raise ValueError('5 GiB unavailable')
    monkeypatch.setattr(runner.native,'require_resources',no_resources)
    monkeypatch.setattr(runner,'prepare',lambda *_:pytest.fail('download must not occur'))
    monkeypatch.setattr(runner.native,'execute',lambda *_:pytest.fail('native must not occur'))
    with pytest.raises(ValueError,match='5 GiB'):
        runner.run(tmp_path/'out',tmp_path/'controls.json')
    assert json.loads((tmp_path/'out/result.json').read_text())['cell_lvs_accepted'] is False


def test_workflow_only_bootstraps_its_own_source_and_preserves_failures():
    import yaml
    row=yaml.safe_load((ROOT/'.github/workflows/coherent-io-lvs.yml').read_text())
    triggers = row.get('on',row.get(True))
    assert set(triggers) == {'workflow_dispatch','push'}
    assert triggers['push']['paths'] == ['.github/workflows/coherent-io-lvs.yml']
    assert row['concurrency']['cancel-in-progress'] is False
    job=row['jobs']['vss-coherent-main']
    assert job['runs-on']=='ubuntu-22.04'
    assert job['steps'][-1]['if']=='always()'
    assert 'run_coherent_io_lvs.py' in '\n'.join(s.get('run','') for s in job['steps'])
