# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure pinned-source, native-capture and failure gates; never invokes KLayout."""
import ast
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_io_tap_mask_probe as probe  # noqa: E402


def fake_deck(tmp_path):
    base=tmp_path/probe.BASE
    (base/'rule_decks').mkdir(parents=True)
    for name in (*probe.ORDER,'custom_classes'):
        (base/'rule_decks'/f'{name}.lvs').write_text('# independent fixture\n')
    entry=''.join('  # %include rule_decks/'+name+'.lvs\n' for name in (*probe.ORDER,'devices_connections'))
    (base/'sg13g2.lvs').write_text(entry)
    return entry


def test_exact_derivation_order_and_controls_before_real_input(tmp_path):
    entry=fake_deck(tmp_path)
    assert probe.derivation_order(entry)==list(probe.ORDER)
    text=probe.program(tmp_path)
    assert text.index('rectangle control') < text.index("source($input, 'sg13g2_IOPadVss')")
    assert text.index('File.write($controls') < text.index("source($input, 'sg13g2_IOPadVss')")
    assert text.index("raise 'bridged Q-hole control'") < text.index("source($input, 'sg13g2_IOPadVss')")
    assert text.index("raise 'deep transformed export control'") < text.index("source($input, 'sg13g2_IOPadVss')")
    paths=[str((tmp_path/probe.BASE/'rule_decks'/f'{name}.lvs').resolve()) for name in probe.ORDER]
    assert [text.index('# %include '+path+'\n') for path in paths]==sorted(text.index('# %include '+path+'\n') for path in paths)
    for forbidden in ('extract_devices(', 'compare(', 'connect_implicit(', 'connect_global(', 'schematic(', 'cheat('):
        assert forbidden not in text
    assert 'layer.data.each_merged' in text
    assert 'layer.merge' not in text  # Only flatten/merge a separate Region copy.


@pytest.mark.parametrize('fault',['swap','missing','extra'])
def test_derivation_order_changes_fail_closed(tmp_path,fault):
    entry=fake_deck(tmp_path)
    if fault=='swap':
        entry=entry.replace('mos_derivations.lvs','TMP.lvs',1).replace('bjt_derivations.lvs','mos_derivations.lvs',1).replace('TMP.lvs','bjt_derivations.lvs',1)
    elif fault=='missing':
        entry=entry.replace('  # %include rule_decks/cap_derivations.lvs\n','')
    else:
        entry=entry.replace('  # %include rule_decks/tap_derivations.lvs\n','  # %include rule_decks/unknown.lvs\n  # %include rule_decks/tap_derivations.lvs\n')
    with pytest.raises(ValueError):
        probe.derivation_order(entry)


def archive_fixture(tmp_path,monkeypatch,files=None):
    files=files or [('comparison/small.bin',b'unchanged'),('comparison/second.bin',b'data')]
    archive=tmp_path/'tiny.zip'
    with zipfile.ZipFile(archive,'w') as target:
        for name,data in files:
            target.writestr(name,data)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(probe,'ASSET',dict(name='tiny.zip',bytes=archive.stat().st_size,sha256=digest))
    monkeypatch.setattr(probe,'ARCHIVE_MEMBERS',len(files))
    monkeypatch.setattr(probe,'ARCHIVE_EXPANDED',sum(len(data) for _,data in files))
    monkeypatch.setattr(probe,'SELECTED',{'comparison/small.bin':('small.bin',hashlib.sha256(b'unchanged').hexdigest())})
    return archive


def test_whole_zip_and_selected_pin_verified_without_network_or_history(tmp_path,monkeypatch):
    archive=archive_fixture(tmp_path,monkeypatch)
    inventory=probe.unpack(archive,tmp_path/'inputs')
    assert set(inventory)=={'comparison/small.bin','comparison/second.bin'}
    assert (tmp_path/'inputs/small.bin').read_bytes()==b'unchanged'
    assert list((tmp_path/'inputs').iterdir())==[tmp_path/'inputs/small.bin']


@pytest.mark.parametrize('fault',['whole-sha','selected-sha','missing','traversal','duplicate','count','expanded'])
def test_archive_mutation_fails_before_writing_input(tmp_path,monkeypatch,fault):
    files=None
    if fault=='missing':files=[('missing',b'data')]
    if fault=='traversal':files=[('../escape',b'data')]
    if fault=='duplicate':files=[('comparison/small.bin',b'unchanged')]*2
    archive=archive_fixture(tmp_path,monkeypatch,files)
    if fault=='whole-sha':monkeypatch.setitem(probe.ASSET,'sha256','0'*64)
    if fault=='selected-sha':monkeypatch.setattr(probe,'SELECTED',{'comparison/small.bin':('small.bin','0'*64)})
    if fault=='count':monkeypatch.setattr(probe,'ARCHIVE_MEMBERS',3)
    if fault=='expanded':monkeypatch.setattr(probe,'ARCHIVE_EXPANDED',1)
    with pytest.raises(ValueError):probe.unpack(archive,tmp_path/'inputs')
    assert not (tmp_path/'inputs').exists()
    assert not (tmp_path/'escape').exists()


def capture(mode='deep'):
    names=['D$ptap1'+('$'+str(i) if i else '') for i in range(4 if mode=='deep' else 3)]
    templates=''.join(f' D({name} ptap1\n  T(TIE\n   R(l159 (0 0) (1000 1000))\n  )\n )\n' for name in names)
    def device(name,index):
        return f'  D({index} {name}\n   Y(1000 2000)\n   E(A 1)\n   E(P 4)\n  )\n'
    if mode=='flat':
        circuits=' X('+probe.TOP+'\n'+''.join(device(name,i) for i,name in enumerate(names))+' )\n'
    else:
        circuits=' X(sg13g2_DCPDiode\n'+device(names[2],3)+' )\n'
        circuits+=' X(sg13g2_DCNDiode\n'+device(names[3],3)+' )\n'
        circuits+=' X('+probe.TOP+'\n'+device(names[0],1)+device(names[1],2)
        circuits+='  X(1 sg13g2_DCNDiode O(90) Y(12000 7000)\n  )\n'
        circuits+='  X(2 sg13g2_DCPDiode O(90) Y(12000 66000)\n  )\n )\n'
    return '#%lvsdb-klayout\nJ(\n U(0.001)\n'+templates+circuits+')\nH(\n)\n'


@pytest.mark.parametrize('mode',['deep','flat'])
def test_capture_reader_uses_device_then_parent_transform(tmp_path,mode):
    path=tmp_path/'report.gz';path.write_bytes(gzip.compress(capture(mode).encode()))
    rows=probe.captured_geometry(path,mode)
    assert len(rows)==(4 if mode=='deep' else 3)
    if mode=='deep':
        child=next(r for r in rows if r['cell']=='sg13g2_DCPDiode')
        assert child['cell_transform']==[90,12000,66000]
        assert child['points_dbu']==[[10000,67000],[10000,68000],[9000,68000],[9000,67000]]
    else:
        assert rows[0]['points_dbu']==[[1000,2000],[2000,2000],[2000,3000],[1000,3000]]


@pytest.mark.parametrize('fault',['dbu','missing-shape','unknown-transform','missing-child'])
def test_capture_reader_rejects_outside_format(tmp_path,fault):
    text=capture()
    if fault=='dbu':text=text.replace('U(0.001)','U(0.002)')
    elif fault=='missing-shape':text=text.replace('R(l159 (0 0) (1000 1000))','Z(l159 (0 0) (1000 1000))',1)
    elif fault=='unknown-transform':text=text.replace('O(90)','O(45)',1)
    else:text=text.replace('X(2 sg13g2_DCPDiode','X(2 unknown',1)
    path=tmp_path/'report.gz';path.write_bytes(gzip.compress(text.encode()))
    with pytest.raises((ValueError,KeyError)):probe.captured_geometry(path,'deep')


@pytest.mark.parametrize('fault',['status','case','dbu','bridge','deep'])
def test_control_receipts_fail_closed(tmp_path,fault):
    row=dict(status='PASS_NATIVE_MASK_CONTROLS',cases=['rectangle','hole','overlap','xor','bridged_q_hole','transformed_deep_export'],dbu_um=0.001)
    if fault=='status':row['status']='PARTIAL'
    if fault=='case':row['cases'].pop()
    if fault=='dbu':row['dbu_um']=0.002
    if fault=='bridge':row['cases'].remove('bridged_q_hole')
    if fault=='deep':row['cases'].remove('transformed_deep_export')
    path=tmp_path/'controls.json';path.write_text(json.dumps(row))
    with pytest.raises(ValueError):probe.check_controls(path)


def test_runner_control_process_is_a_real_failure_gate_before_archive(monkeypatch,tmp_path):
    monkeypatch.setattr(probe.native,'OUTPUT_ROOT',tmp_path)
    monkeypatch.setattr(probe.native,'verify_runtime',lambda *args:None)
    monkeypatch.setattr(probe.native,'verify_deck',lambda:('unused',{}))
    monkeypatch.setattr(probe.native,'execute',lambda *args:dict(returncode=1))
    monkeypatch.setattr(probe,'fetch',lambda *args:pytest.fail('download must not occur after failed controls'))
    with pytest.raises(ValueError,match='Native geometry controls failed'):
        probe.run(tmp_path/'out')
    receipt=json.loads((tmp_path/'out/result.json').read_text())
    assert receipt['status']=='FAILED_DIAGNOSTIC'
    assert receipt['cell_lvs_accepted'] is False
    assert not (tmp_path/'out/inputs').exists()


def test_workflow_has_narrow_native_trigger_and_no_publish_or_full_lvs():
    text=(ROOT/'.github/workflows/io-tap-mask-probe.yml').read_text()
    assert 'workflow_dispatch:' in text and '  push:' in text
    assert text.count('      - .github/workflows/') == 1
    assert '      - .github/workflows/io-tap-mask-probe.yml' in text
    assert 'contents: read' in text and 'contents: write' not in text
    assert 'if: always()' in text
    assert 'run_io_tap_mask_probe.py' in text and 'run_coherent_io_lvs.py' not in text
    # The helper imports native bindings only after an explicit main action.
    helper=ast.parse((ROOT/'hw/soc/flow/io_tap_mask_probe.py').read_text())
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and 'klayout' in ast.unparse(n) for n in helper.body)
    assert "output/'archive'" in inspect.getsource(probe.run)
