# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real stream/files and exact inherited numerical bodies; no SPICE evidence."""
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import characterize_pcie_pll_acquisition_v5 as m
import durable_pcie_spool_v1 as local


def test_all_complete_body_bridges_inverse_and_private_globals():
    for name, source, original in [
        ('capture', m.capture_source, m.previous.capture_source),
        ('native_wait', m.native_wait_source, m.inherited_native_wait),
        ('run', m.run_source, m.previous.run_source),
        ('main', m.main_source, m.previous.main_source),
    ]:
        for before, after in reversed(m.BRIDGES[name]['exact_replacements']):
            assert source.count(after) == 1
            source = source.replace(after, before)
        assert source == original
        assert hashlib.sha256(source.encode()).hexdigest() == m.BRIDGES[name]['original_sha256']
    assert m.capture.__globals__ is m.namespace
    assert m.native_wait.__globals__ is m.namespace
    assert m._native_run.__globals__ is m.namespace
    assert m.previous.capture.__globals__ is not m.namespace
    assert 'OwnedPublisherV3(owner)' not in m.run_source
    assert 'life.PartQueue(' not in m.capture_source
    assert m.sha(local.__file__) == m.SPOOL_SHA


def test_exact_deck_and_all_physics_resource_aliases():
    for name in ['stream_deck', 'Meter', 'measurements', 'acquisition', 'startup_proof', 'prerequisites']:
        assert getattr(m, name) is getattr(m.previous, name)
    for name in ['native_limit', 'CAP', 'FLOOR', 'PART_BYTES', 'life', 'n']:
        assert m.namespace[name] is m.previous.namespace[name]
    fixture = ROOT / 'sw/tests/fixtures/pcie_pll_acquisition_v3/connected-loop-bench.cir'
    assert m.sha(fixture) == '6f31cfc4c419005b857608eb2d873d13b44c8e53e0328517cb9eefeb373b55c4'
    assert m.stream_deck(fixture.read_text(), m.TSTEP, m.STOP) == m.previous.stream_deck(fixture.read_text(), m.TSTEP, m.STOP)
    assert (m.TSTEP, m.TMAX, m.STOP) == (2.5e-12, 1.25e-12, 1e-6)
    assert m.previous.base.FREQUENCY_RELATIVE_LIMIT == 100e-6
    assert m.previous.base.PHASE_RANGE_LIMIT_S == 50e-12


class Irregular(io.BytesIO):
    def __init__(self, value, stride):
        super().__init__(value)
        self.stride, self.serial = stride, 0
    def read(self, count=-1):
        size = self.stride[self.serial % len(self.stride)]
        self.serial += 1
        return super().read(min(size, count) if count >= 0 else size)


def stream_fixture(monkeypatch):
    header = b'Title: test\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 2\nNo. Points: 0\nVariables:\n0 time time\n1 v(x) voltage\nBinary:\n'
    rows = [(i * 1.25e-12, (-1)**i * .125) for i in range(11)]
    payload = b''.join(struct.pack('<dd', *row) for row in rows)
    config = dict(extra_vectors=[], step_s=2.5e-12, max_step_s=1.25e-12,
                  stop_s=rows[-1][0], window_s=[0, rows[-1][0]])
    native = SimpleNamespace(vectors=lambda *a: ['v(x)'], common=m.n.common,
                             safety=lambda *a: dict(model_geometry_range_issues=[], all_device_bounds=[]))
    original_meter = m.Meter
    for ns in (m.namespace, m.previous.namespace):
        monkeypatch.setitem(ns, 'n', native)
        monkeypatch.setitem(ns, 'Meter', lambda cols, devices, cfg: original_meter(cols, devices, cfg, observations=['time', 'v(x)']))
        monkeypatch.setitem(ns, 'measurements', lambda data, cfg: {k: v.tolist() for k, v in data.items()})
    return header, payload, config


@pytest.mark.parametrize('stride', [(65536,), (1, 3, 7, 17, 31), (79, 2, 13)])
def test_actual_irregular_raw_capture_same_reducer_and_all_bytes(tmp_path, monkeypatch, stride):
    header, payload, config = stream_fixture(monkeypatch)
    raw = header + payload + b'11'
    def synthetic_old_transport(path, receipt):
        # Explicit unit-only transport substitute; no real/public acceptance.
        receipt.write_text('{}')
        return dict(name=path.name, **local.pin(path), authenticated_roundtrip=True, anonymous_roundtrip=True)
    old = m.previous.capture(Irregular(raw, stride), tmp_path / 'old', {'devices': []}, config,
                             'local-parser-fixture', synthetic_old_transport, rows_per_part=3)
    spool = local.Spool(tmp_path / 'ssd', 'local-parser-fixture',
                        limits=local.Limits(reserve=4096, payload=1024**2, floor=4096, parts=16))
    new = m.capture(Irregular(raw, stride), tmp_path / 'new', {'devices': []}, config,
                    spool.prefix, spool, rows_per_part=3)
    for name in ['safety', 'time_grid', 'measurement', 'rows', 'values', 'raw_sha256',
                 'payload_sha256', 'canonical_payload_sha256', 'canonical_order', 'columns', 'raw_table']:
        assert old[name] == new[name]
    assert new['status'] == 'PASS_LOCAL_COMPLETE_CAPTURE' and not new['public_verified']
    assert new['raw_sha256'] == hashlib.sha256(raw).hexdigest()
    ledger = local.inspect_spool(spool.root, raw=True)['ledger']
    assert [row['rows'] for row in ledger['parts']] == [3, 3, 3, 2]
    recovered = b''.join(local.check_row(spool.root, ledger, row, i, row['first_row'], raw=True)
                         for i, row in enumerate(ledger['parts']))
    assert (spool.root / 'header.bin').read_bytes() + recovered + (spool.root / 'trailer.bin').read_bytes() == raw


@pytest.mark.parametrize('fault', ['trailer', 'partial_frame', 'nonfinite', 'grid'])
def test_actual_invalid_raw_fails_and_retains_tails(tmp_path, monkeypatch, fault):
    header, payload, config = stream_fixture(monkeypatch)
    if fault == 'trailer':
        raw = header + payload + b'12'
    elif fault == 'partial_frame':
        raw = header + payload[:-3]
    elif fault == 'nonfinite':
        altered = np.frombuffer(payload, '<f8').copy(); altered[5] = float('nan')
        raw = header + altered.tobytes() + b'11'
    else:
        altered = np.frombuffer(payload, '<f8').copy(); altered[2] = 2.5e-12
        raw = header + altered.tobytes() + b'11'
    spool = local.Spool(tmp_path / 'ssd', 'local-parser-fixture',
                        limits=local.Limits(reserve=4096, payload=1024**2, floor=4096, parts=16))
    out = tmp_path / 'capture'
    with pytest.raises(ValueError):
        m.capture(Irregular(raw, (11, 3, 79)), out, {'devices': []}, config,
                  spool.prefix, spool, rows_per_part=3)
    failure = json.loads((out / 'failure.json').read_text())
    assert failure['status'] == 'ERROR_CAPTURE'
    assert (out / 'unparsed-tail.bin').is_file() and (out / 'unpublished-tail.bin').is_file()
    assert local.inspect_spool(spool.root)['ledger']['status'] == 'CAPTURING_LOCAL'
    assert (spool.root / 'reservation.bin').exists()


@pytest.mark.parametrize('status,code', [('PASS_NATIVE_LOCAL_STREAM_FINITE_SCREEN', 0),
                                      ('FAIL_NATIVE_LOCAL_STREAM_FINITE_SCREEN', 1),
                                      ('PASS_NATIVE_STREAM_FINITE_SCREEN', 1)])
def test_cli_never_calls_local_capture_public(tmp_path, monkeypatch, status, code):
    seen = []
    monkeypatch.setitem(m.namespace, 'runtime', SimpleNamespace(check_runtime=lambda *a: None))
    monkeypatch.setitem(m.namespace, 'run', lambda *a, **k: (seen.append((a, k)) or {'status': status}))
    monkeypatch.setattr(sys, 'argv', ['local', '--out', str(tmp_path / 'ram'), '--spool', str(tmp_path / 'ssd'),
                                    '--prefix', 'fixture', '--step-ps', '2.5', '--reference', 'ref', '--reference-sha', 'r',
                                    '--prerequisites', 'prereq', '--prerequisites-sha', 'p'])
    assert m.main() == code
    assert seen[0][0][2:4] == (m.TSTEP, m.STOP) and seen[0][1] == {'spool_root': tmp_path / 'ssd'}


@pytest.mark.parametrize('terminal_floor_fault', [False, True])
def test_actual_owned_native_fifo_and_terminal_guard(tmp_path, monkeypatch, terminal_floor_fault):
    header, payload, config = stream_fixture(monkeypatch)
    raw = header + payload + b'11'
    fake = tmp_path / 'fixture-native'
    fake.write_text('#!' + sys.executable + '\nfrom pathlib import Path\n'
                    'with Path("stream.fifo").open("wb") as f:\n'
                    ' f.write(bytes.fromhex(' + repr(raw.hex()) + ')); f.flush()\n')
    fake.chmod(0o755)
    m.namespace['n'].NG = fake
    out = tmp_path / 'native'; out.mkdir()
    spool = local.Spool(tmp_path / 'ssd', 'actual-owned-fifo-fixture',
                        limits=local.Limits(reserve=4096, payload=1024**2, floor=4096, parts=16))
    monkeypatch.setattr(m, '_active_spool', spool)
    original_guard = m.guard
    def guard(folder):
        result = original_guard(folder)
        if terminal_floor_fault and (folder / 'execution.json').exists():
            raise ValueError('Actual terminal guard injected after wait')
        return result
    monkeypatch.setitem(m.namespace, 'guard', guard)
    def run():
        return m.native_wait(out, lambda stream, owner: m.capture(stream, out / 'capture',
                             {'devices': []}, config, spool.prefix, spool, rows_per_part=3))
    if terminal_floor_fault:
        with pytest.raises(ValueError, match='terminal guard'):
            run()
    else:
        result = run()
        assert result['raw_sha256'] == hashlib.sha256(raw).hexdigest()
    ownership = json.loads((out / 'owned-processes.json').read_text())
    assert len(ownership['processes']) == 1
    for process in ownership['processes']:
        assert not any(x['state'] != 'Z' for x in m.previous.life.group_members(process['process_group']))
    assert json.loads((out / 'execution.json').read_text())['returncode'] == 0
    assert local.inspect_spool(spool.root, raw=True)['rows'] == 11


def test_actual_native_sigterm_reaps_writer_and_preserves_partial_payload(tmp_path):
    script = tmp_path / 'outer.py'
    script.write_text('''import sys,json,struct
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,SCRIPTS)
import characterize_pcie_pll_acquisition_v5 as m
import durable_pcie_spool_v1 as local
B=Path(BASE);out=B/'native';out.mkdir()
spool=local.Spool(B/'ssd','actual-cancel-fixture',limits=local.Limits(reserve=4096,payload=1024**2,floor=4096,parts=16))
m._active_spool=spool
header=b'Title: test\\nPlotname: Transient Analysis\\nFlags: real\\nNo. Variables: 2\\nNo. Points: 0\\nVariables:\\n0 time time\\n1 v(x) voltage\\nBinary:\\n'
body=b''.join(struct.pack('<dd',i*1.25e-12,.5)for i in range(3))
fake=B/'fixture-native'
fake.write_text('#!'+sys.executable+'\\nimport time\\nfrom pathlib import Path\\nf=Path("stream.fifo").open("wb")\\nf.write(bytes.fromhex('+repr((header+body).hex())+'));f.flush()\\nPath("wrote-native-bytes").write_text("3")\\ntime.sleep(60)\\n')
fake.chmod(0o755)
n=SimpleNamespace(NG=fake,vectors=lambda*a:['v(x)'],common=m.n.common,safety=lambda*a:dict(model_geometry_range_issues=[],all_device_bounds=[]))
original=m.Meter
for ns in (m.namespace,m.previous.namespace):
 ns['n']=n;ns['Meter']=lambda cols,devices,cfg:original(cols,devices,cfg,observations=['time','v(x)'])
 ns['measurements']=lambda data,cfg:{k:v.tolist()for k,v in data.items()}
config=dict(extra_vectors=[],step_s=2.5e-12,max_step_s=1.25e-12,stop_s=10e-12,window_s=[0,10e-12])
try:
 m.native_wait(out,lambda stream,owner:m.capture(stream,out/'capture',{'devices':[]},config,spool.prefix,spool,rows_per_part=9))
except BaseException as error:
 result=dict(status='ERROR_NATIVE_OR_STREAM_CAPTURE',error=repr(error))
 (out/'result.json').write_text(json.dumps(result))
 spool.terminal(result,native_root=out)
 raise
finally:spool.close()
'''.replace('SCRIPTS', repr(str(ROOT / 'scripts'))).replace('BASE', repr(str(tmp_path))))
    logfile = tmp_path / 'outer.log'
    with logfile.open('wb') as log:
        outer = subprocess.Popen([sys.executable, str(script)], stdout=log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        deadline = time.monotonic() + 8
        while not (tmp_path / 'native/wrote-native-bytes').exists():
            if outer.poll() is not None:
                pytest.fail(logfile.read_text())
            if time.monotonic() > deadline:
                outer.kill(); outer.wait(); pytest.fail('Native fixture startup boundary absent')
            time.sleep(.01)
        outer.send_signal(signal.SIGTERM)
        assert outer.wait(timeout=8) != 0
    ownership = json.loads((tmp_path / 'native/owned-processes.json').read_text())
    for process in ownership['processes']:
        assert not any(x['state'] != 'Z' for x in m.previous.life.group_members(process['process_group']))
    terminal = json.loads((tmp_path / 'ssd/native-terminal.json').read_text())
    assert terminal['result']['status'] == 'ERROR_NATIVE_OR_STREAM_CAPTURE'
    tail = tmp_path / 'ssd/native-terminal-capture/capture/unpublished-tail.bin'
    assert tail.read_bytes() == b''.join(struct.pack('<dd', i * 1.25e-12, .5) for i in range(3))
    assert not (tmp_path / 'ssd/reservation.bin').exists()
