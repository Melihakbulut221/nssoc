#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inspect the immutable interrupted 865-device PLL prefix, never accept lock."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'hw/soc/out/pcie-pbuf10-acquisition-20261012/'
BASE = 'https://github.com/Melihakbulut221/nssoc/releases/download/'
RECORDS = {
    'native07/wave.raw': (149771119, '7c1f37bd9e29e794f2a33c67fe5efaa3f0c021bc907484d1d7efa60521d25ba8'),
    'native07/result.json': (51922, '757dff0cd5bfaac9eac3f62a138e6538255098513c88ee33a77bba0845d4bc4f'),
    'native07/owned-processes.json': (1044, '9b3be045bad01f6c1fcf92a7382373d0b702237464739d52281bb5dc90ba2d6f'),
    'native07/run.log': (1973718, '4054c46355a18e55001d01751398082319eef537367f3437a64acefce93653a2'),
    'native07/bench.cir': (20469, '8d1ace49e8c2abe21be67433b1b5714f7a468790358e4ef33d4ef038b93944af'),
    'native07/parent865.spice': (603656, 'b7c2b8f7328c14ff15a5798c7aaec0629104ea7ec9252d2594d3dd9db168ff48'),
    'gate01.json': (1772, 'f1c202dfc05e9210f7fb53f017cf3bf68d9f8ca63bb902a93f28bbab1b8ac861'),
}
def digest(data):
    return hashlib.sha256(data).hexdigest()

def decode_prefix(raw, *, interrupted_diagnostic=False):
    end = raw.find(b'Binary:\n', 0, 1048576)
    assert end >= 0, 'Missing bounded native binary header'
    end += len(b'Binary:\n')
    header = raw[:end].decode('ascii')
    assert 'Flags: real\n' in header
    field = lambda key: next(l.split(':', 1)[1].strip() for l in header.splitlines() if l.startswith(key+':'))
    table = [l.split() for l in header.split('Variables:\n', 1)[1].split('Binary:\n', 1)[0].splitlines()]
    width = int(field('No. Variables'))
    declared = int(field('No. Points'))
    assert width > 0 and len(table) == width
    assert [r[0] for r in table] == list(map(str, range(width)))
    names = [r[1] for r in table]
    assert len(set(names)) == width and names[0] == 'time'
    payload = memoryview(raw)[end:]
    trailing = len(payload) % (8*width)
    assert not trailing or interrupted_diagnostic, 'Incomplete trailing native row'
    # A cancellation can interrupt a binary row. Never pad or synthesize it.
    # Opt-in applies only to diagnosis; the strict default still rejects it.
    complete = payload[:-trailing] if trailing else payload
    excluded = payload[-trailing:] if trailing else memoryview(b'')
    values = np.frombuffer(complete, dtype='<f8').reshape(-1, width)
    assert len(values) > 1 and np.isfinite(values).all()
    assert np.all(np.diff(values[:, 0]) > 0), 'Nonmonotonic native time'
    return names, values, dict(header_points=declared, observed_rows=len(values),
        width=width, header_bytes=end, payload_sha256=digest(payload),
        header_matches_observed=declared == len(values),
        payload_has_only_complete_rows=not trailing,
        excluded_trailing_bytes=trailing, excluded_trailing_sha256=digest(excluded),
        complete_rows_sha256=digest(complete),
        interrupted_diagnostic=interrupted_diagnostic)

def rising(time, signal, threshold):
    indices = np.flatnonzero((signal[:-1] < threshold) & (signal[1:] >= threshold))
    return time[indices]+(threshold-signal[indices])/(signal[indices+1]-signal[indices])*(time[indices+1]-time[indices])

def self_test():
    header = b'Title: prefix control\nFlags: real\nNo. Variables: 2\nNo. Points: 0\nVariables:\n0 time time\n1 v(fb) voltage\nBinary:\n'
    values = np.array([[0., 0.], [1e-9, 2.5], [2e-9, 0.]])
    raw = header+values.astype('<f8').tobytes()
    names, data, meta = decode_prefix(raw)
    assert names == ['time', 'v(fb)'] and meta['observed_rows'] == 3
    assert not meta['header_matches_observed']
    assert np.allclose(rising(data[:,0],data[:,1],1.25),[.5e-9],rtol=0,atol=1e-20)
    bad_values = values.copy(); bad_values[1,1] = np.nan
    bad_time = values.copy(); bad_time[2,0] = bad_time[1,0]
    cases = [raw[:-1], raw+b'x', header+bad_values.astype('<f8').tobytes(),
             header+bad_time.astype('<f8').tobytes(), raw.replace(b'1 v(fb)', b'0 v(fb)', 1)]
    for bad in cases:
        try:
            decode_prefix(bad)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('Corruption control was not rejected')
    # Explicit partial diagnosis must retain exactly two complete rows and
    # report all 15 bytes of the third; it cannot silently round up a sample.
    _, partial, meta = decode_prefix(raw[:-1], interrupted_diagnostic=True)
    assert np.array_equal(partial, values[:2])
    assert meta['excluded_trailing_bytes'] == 15
    assert meta['excluded_trailing_sha256'] == digest(raw[-16:-1])
    assert not meta['payload_has_only_complete_rows']
    assert meta['observed_rows'] == 2
    return dict(valid_interrupted_header_preserved=True,
        negative_controls_rejected=len(cases), explicit_partial_diagnosis_control=True)

def fetch(url, expected, destination):
    subprocess.run(['curl','--fail','--location','--retry','4',url,'-o',str(destination)],check=True)
    data = destination.read_bytes()
    assert digest(data) == expected
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    controls = self_test()
    if args.self_test:
        print(json.dumps(controls)); return
    out = ROOT/'cloud-pll-prefix'
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING_ARCHIVED_PREFIX_DIAGNOSIS', full_phy_accepted=False,
                  acquisition_accepted=False, controls=controls)
    def save():
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    packed = ROOT/'pll-prefix-input.tar.gz'
    try:
        sources = [dict(asset_id=634832275,bytes=141989022,
            sha256='6021e860444f74adae386a07f85254169bb6e75ab03fd981dff8cc52c098f6ce',
            url=BASE+'cloud-migration-20261012-000/batch-000002.tar.gz',
            members=[n for n in RECORDS if n != 'native07/wave.raw']),
            dict(asset_id=634833900,bytes=121865817,
            sha256='867100a4e8844477ae6003fa84bb7c10801099afb335b8dd3d1b56a6a99450fb',
            url=BASE+'cloud-migration-20261012-000/batch-000003.tar.gz',
            members=['native07/wave.raw'])]
        selected = {}
        for source in sources:
            archive = fetch(source['url'],source['sha256'],packed)
            assert len(archive) == source['bytes']
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
                for name in source['members']:
                    size,sha = RECORDS[name]
                    matches = [m for m in tar.getmembers() if m.name == PREFIX+name]
                    assert len(matches) == 1, 'Missing or duplicate exact archived member'
                    member = matches[0]
                    assert member.isfile() and member.size == size
                    data = tar.extractfile(member).read()
                    assert len(data) == size and digest(data) == sha
                    assert name not in selected
                    selected[name] = data
            packed.unlink()
        assert set(selected) == set(RECORDS)
        gate=json.loads(selected['gate01.json'])
        assert all(gate[k] for k in ('functional_passed','independent_electrical_passed','native_safety_passed','dispatched'))
        native=json.loads(selected['native07/result.json'])
        owner=json.loads(selected['native07/owned-processes.json'])
        assert native['status']=='FAILED_ONE_US_SELECTED_PROBE_DIAGNOSTIC'
        assert owner['status']=='CANCELLED' and owner['reason']=='Parent received SIGTERM'
        assert owner['processes'][0]['returncode']==-15
        bench=selected['native07/bench.cir'].decode()
        assert '.tran 3.125e-13 1e-06 0 3.125e-13' in bench
        assert '.options reltol=1e-4 abstol=1e-12 klu' in bench
        names,values,capture=decode_prefix(selected['native07/wave.raw'], interrupted_diagnostic=True)
        assert len(names)==25 and 100000 < len(values) < 4000000
        saved=next(l[5:].split() for l in bench.splitlines() if l.startswith('save '))
        assert set(names)=={'time',*saved}
        t=values[:,0]
        assert t[0]==0 and 200e-9 < t[-1] < 1e-6
        v={name:values[:,i] for i,name in enumerate(names)}
        edges={name:rising(t,signal,threshold) for name,signal,threshold in [
            ('vco',v['v(clkp)']-v['v(clkn)'],0.),
            ('feedback',v['v(fb)'],1.25),('reference',v['v(reference)'],1.25)]}
        windows=[]
        for start,end in [(25,50),(50,100),(100,150),(150,200),(200,230)]:
            a,z=start*1e-9,end*1e-9
            if t[-1] < z: continue
            mask=(t>=a)&(t<=z)
            stats={}
            for name,edge in edges.items():
                e=edge[(edge>=a)&(edge<=z)]; periods=np.diff(e)
                stats[name]=dict(rising_edges=len(e),frequency_from_median_period_hz=float(1/np.median(periods)) if len(periods) else None,
                    min_period_s=float(periods.min()) if len(periods) else None,max_period_s=float(periods.max()) if len(periods) else None)
            rails={name:dict(minimum=float(v[name][mask].min()),mean=float(v[name][mask].mean()),maximum=float(v[name][mask].max()))
                   for name in ['v(vctrl)','v(up)','v(down)','v(fb)','v(reference)']}
            windows.append(dict(start_ns=start,end_ns=end,edges=stats,node_ranges=rails))
        result.update(status='COMPLETE_INTERRUPTED_PREFIX_DIAGNOSIS_NOT_ACQUISITION',
            sources=sources,records={n:dict(bytes=s,sha256=h) for n,(s,h) in RECORDS.items()},
            native_status=native['status'],cancellation=owner,capture=capture,
            captured_start_s=float(t[0]),captured_end_s=float(t[-1]),required_stop_s=1e-6,
            missing_required_windows_ns=[[800,900],[900,1000]],windows=windows,
            scope='Exact historical865 native prefix only. Original bytes and cancellation retained; no simulation rerun, no phase fit, no changed electrical thresholds. Incomplete trailing row is excluded with exact byte count/hash, never padded; strict complete-capture decoding remains fail-closed. Fixed short windows diagnose direction of frequency/control-voltage evolution. They cannot substitute the missing final800-1000ns acquisition windows, full-device1us safety, timestep/PVT, PLL/CDR or fullPHY acceptance.')
        save()
        print(result['status'])
        print(json.dumps(windows,indent=2))
    except BaseException as error:
        result.update(status='FAILED_PREFIX_READBACK_NOT_PHY',error=repr(error));save();raise
    finally:
        if packed.exists(): packed.unlink()

if __name__=='__main__':
    main()
