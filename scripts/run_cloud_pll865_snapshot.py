#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted exact native865 capture and snapshot experiment; no implicit PLL acceptance."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tarfile
import time

import numpy as np
from read_cloud_pll_acquisition_prefix import decode_prefix, digest, rising, RECORDS, PREFIX, BASE
from run_cloud_tx_operating_point import fetch, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = '6021e860444f74adae386a07f85254169bb6e75ab03fd981dff8cc52c098f6ce'
FINITE_SHA = 'e59ca7de8b8f79a200b226fc7f817bc6eee415ebc563cb811ad5c0be1ae832c6'
MODEL_ROOT = '/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/ngspice/models'
OSDI_ROOT = '/dev/shm/nssoc-clock-vco-full-20261004'
FINITE_ROOT = 'hw/soc/out/pcie-pbuf10-native865-20261012/native01/closed-01/'
# Declared before any native result. Method validation only, never PHY margins.
MAX_NODE_ERROR_V = .001
MAX_EDGE_ERROR_S = 1e-12

def compare(reference, candidate):
    rn, rv = reference
    cn, cv = candidate
    assert rn == cn and len(rn) >= 4
    assert all(np.isfinite(v).all() and np.all(np.diff(v[:,0])>0) for v in (rv,cv))
    assert rv[0,0] <= 25.001e-9 and cv[0,0] <= 25.001e-9
    assert all(50e-9 <= v[-1,0] <= 50.001e-9 for v in (rv,cv))
    start=max(25.001e-9,rv[0,0],cv[0,0])
    end=min(50e-9,rv[-1,0],cv[-1,0])
    mask=(rv[:,0]>=start)&(rv[:,0]<=end)
    assert mask.sum()>1000 and end-start > 24.99e-9
    times=rv[mask,0]
    errors={name:float(np.max(abs(rv[mask,i]-np.interp(times,cv[:,0],cv[:,i]))))
            for i,name in enumerate(rn) if i}
    edge_errors={}
    for name,p,n,threshold in [('vco','v(clkp)','v(clkn)',0.),
                                ('feedback','v(fb)',None,1.25),
                                ('reference','v(reference)',None,1.25)]:
        def crossings(v):
            signal=v[:,rn.index(p)]-(v[:,rn.index(n)] if n else 0)
            e=rising(v[:,0],signal,threshold)
            return e[(e>26e-9)&(e<49e-9)]
        a,b=crossings(rv),crossings(cv)
        assert len(a)==len(b) and len(a)>0, 'Native edge-count mismatch'
        edge_errors[name]=dict(count=len(a),max_absolute_edge_error_s=float(abs(a-b).max()))
    passed=all(e<=MAX_NODE_ERROR_V for e in errors.values()) and all(
        v['max_absolute_edge_error_s']<=MAX_EDGE_ERROR_S for v in edge_errors.values())
    return dict(passed=passed,comparison_start_s=start,comparison_end_s=end,
                reference_samples=int(mask.sum()),node_max_absolute_error_v=errors,
                edge_errors=edge_errors,voltage_limit_v=MAX_NODE_ERROR_V,
                edge_limit_s=MAX_EDGE_ERROR_S,phase_shift_fitted=False)

def self_test():
    t=np.linspace(0,50e-9,10001)
    signal=np.sin(2*np.pi*t/125e-12)
    a=np.column_stack([t,signal,-signal,1.25+np.sin(2*np.pi*t/10e-9),
                       1.25+np.sin(2*np.pi*t/10e-9)])
    names=['time','v(clkp)','v(clkn)','v(fb)','v(reference)']
    assert compare((names,a),(names,a))['passed']
    voltage=a.copy();voltage[:,1]+=.01
    shifted=a.copy();shifted[:,1]=np.sin(2*np.pi*(t+20e-12)/125e-12)
    bads=[(names,voltage),(names,shifted),(names,a[:8000]),
          (names[:-1],a[:,:-1])]
    for bad in bads:
        try:
            accepted=compare((names,a),bad)['passed']
        except (AssertionError,ValueError):
            accepted=False
        assert not accepted, 'Mismatch was not rejected'
    return dict(identical_waveform_passed=True,rejected_controls=len(bads))

def unpack(url, expected, size, destination, selected=None):
    packed=destination.parent/(destination.name+'.tar.gz')
    fetch(url,expected,packed)
    assert packed.stat().st_size==size
    destination.mkdir()
    with tarfile.open(packed) as tar:
        if selected is None:
            tar.extractall(destination,filter='data')
        else:
            for path,(count,h) in selected.items():
                matches=[m for m in tar.getmembers() if m.name==path]
                assert len(matches)==1 and matches[0].isfile()
                data=tar.extractfile(matches[0]).read()
                assert len(data)==count and digest(data)==h
                (destination/Path(path).name).write_bytes(data)
    packed.unlink()

def native_run(executable, directory, script, deadline, result, save):
    log=directory/(script+'.log')
    started=time.monotonic()
    with log.open('wb') as stream:
        proc=subprocess.Popen([str(executable),'-n','-b',script],cwd=directory,
            stdout=stream,stderr=subprocess.STDOUT,
            env={**os.environ,'SPICE_SCRIPTS':str(directory),'OMP_NUM_THREADS':'1'})
        result['active_native']=dict(script=script,pid=proc.pid,started_epoch=time.time())
        save()
        while True:
            try:
                code=proc.wait(timeout=30)
                break
            except subprocess.TimeoutExpired:
                elapsed=time.monotonic()-started
                print(json.dumps(dict(native=script,elapsed_s=elapsed,log_bytes=log.stat().st_size)),flush=True)
                if time.monotonic()>deadline:
                    proc.terminate()
                    try: proc.wait(timeout=30)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
                    raise TimeoutError('Hosted safety deadline before runner hard limit; no native result accepted')
    record=dict(script=script,returncode=code,elapsed_s=time.monotonic()-started,
        log_sha256=sha(log),peak_children_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    result.setdefault('native_runs',[]).append(record)
    result.pop('active_native',None);save()
    text=log.read_text(errors='replace')
    errors=[l for l in text.splitlines() if re.search(
        r'(^Error:|fatal|timestep too small|singular matrix|not implemented|ignored|unable to read|different version|vector .*not found)',l,re.I)]
    record['diagnostics']=errors
    assert code==0 and not errors, 'Native execution or snapshot diagnostic failure'
    return text


ACQUISITION_REVIEW_SHA = '168a1563ed1847e752c67e3058b823200bfe2b3f4e2b345046a0ed13318530db'
ACQUISITION_RUN = 38507479646
ACQUISITION_SOURCE = '444e78eb4ad91b996cbcdf80d8189b2abbb62cb2'


def acquisition_analyzer():
    """Reuse only the three frozen pure edge/window functions, not old539 I/O."""
    path = ROOT/'scripts/review_pcie_pll_acquisition_v1.py'
    assert sha(path) == ACQUISITION_REVIEW_SHA, 'Frozen original acceptance criteria'
    tree = ast.parse(path.read_text())
    wanted = {'independent_edges', 'monotone_ordinals', 'independent_analysis'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert len(nodes) == len(wanted)
    def require(condition, message):
        if not condition:
            raise AssertionError(message)
    namespace = {'np': np, 'require': require}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['independent_analysis']


def acquisition_controls():
    analyze = acquisition_analyzer()
    t = np.linspace(0, 1e-6, 100001)
    ref = 1.25 + np.sin(2*np.pi*(t-2e-9)/10e-9)
    good = {'time': t, 'v(reference)': ref, 'v(fb)': ref.copy(),
            'v(vctrl)': np.ones_like(t)}
    assert analyze(good)['passed']
    altered = {}
    altered['frequency'] = {**good, 'v(fb)': 1.25 + np.sin(2*np.pi*(t-2e-9)*101e6)}
    delay = np.clip((t-800e-9)/100e-9, 0, 1)*200e-12
    altered['phase_drift'] = {**good, 'v(fb)': 1.25 + np.sin(2*np.pi*(t-delay-2e-9)/10e-9)}
    missing = ref.copy(); missing[(t>840e-9)&(t<849e-9)] = .25
    altered['missing_edge'] = {**good, 'v(fb)': missing}
    altered['control_voltage'] = {**good, 'v(vctrl)': np.full_like(t, 1.6)}
    verdicts = {name: analyze(data) for name, data in altered.items()}
    assert all(not x['passed'] for x in verdicts.values())
    assert any(not w['checks']['frequency_100ppm'] for w in verdicts['frequency']['rolling_windows'])
    assert any(not w['checks']['phase_range_50ps'] for w in verdicts['phase_drift']['rolling_windows'])
    assert not verdicts['missing_edge']['final_two_windows_no_slip']
    assert not verdicts['control_voltage']['rolling_windows'][-1]['checks']['control_development_window']
    for broken in [{k:v[:-1] for k,v in good.items()}, {k:v.copy() for k,v in good.items()}]:
        if len(broken['time']) == len(t): broken['v(fb)'][50] = np.nan
        try: analyze(broken)
        except AssertionError: continue
        raise AssertionError('Incomplete/nonfinite acquisition accepted')
    return dict(original_gate_source_sha256=ACQUISITION_REVIEW_SHA,
                identical_locked_control=True, physical_faults_rejected=list(altered),
                incomplete_and_nonfinite_rejected=True)


def acquisition_cycle_diagnosis(data, independent):
    """Descriptive cycle records only. Never changes the frozen acceptance gate."""
    names=('time','v(clkp)','v(clkn)','v(vctrl)','v(up)','v(down)')
    assert all(n in data for n in names)
    t=data['time']; assert len(t)>2 and np.all(np.diff(t)>0)
    assert all(len(data[n])==len(t) and np.all(np.isfinite(data[n])) for n in names)
    edges=np.asarray(independent['feedback_edges_s'])
    assert len(edges)>2 and np.all(np.diff(edges)>0)
    assert t[0]<=edges[0] and edges[-1]<=t[-1]
    differential=data['v(clkp)']-data['v(clkn)']
    crossings=np.flatnonzero((differential[:-1]<=0)&(differential[1:]>0))
    clock_edges=t[crossings]-differential[crossings]*(t[crossings+1]-t[crossings])/(differential[crossings+1]-differential[crossings])
    rows=[]
    for ordinal,(start,end) in enumerate(zip(edges[:-1],edges[1:])):
        lo,hi=np.searchsorted(t,[start,end]); grid=np.concatenate(([start],t[lo:hi],[end]))
        row=dict(feedback_edge_ordinal=ordinal,interval_s=[float(start),float(end)],
                 feedback_period_s=float(end-start),
                 differential_clock_rising_edges=int(np.count_nonzero((clock_edges>=start)&(clock_edges<end))))
        for name in ('v(vctrl)','v(up)','v(down)'):
            trace=np.interp(grid,t,data[name]); mean=float(np.trapezoid(trace,grid)/(end-start))
            row[name]=dict(minimum_v=float(trace.min()),maximum_v=float(trace.max()),mean_v=mean,
                start_v=float(trace[0]),end_v=float(trace[-1]))
            if name!='v(vctrl)':
                row[name]['duty_above_1p25v']=float(np.trapezoid((trace>1.25).astype(float),grid)/(end-start))
        rows.append(row)
    return dict(cycles=rows,threshold_v=1.25,threshold_scope='Descriptive UP/DOWN logic duty only, not charge-pump current.',
        scope='Exact original feedback-edge intervals, unfitted and unshifted. Clock zero-crossing counts, VCTRL ripple and UP/DOWN voltage integrals. No synthetic compensation, target fitting or acceptance decision.')


def acquisition_cycle_controls():
    t=np.linspace(0,40e-9,401); ramp=1+t*1e6
    good={'time':t,'v(vctrl)':ramp,'v(up)':np.full_like(t,2.5),'v(down)':np.zeros_like(t),
          'v(clkp)':np.sin(2*np.pi*t*1e9),'v(clkn)':-np.sin(2*np.pi*t*1e9)}
    edges={'feedback_edges_s':[10e-9,20e-9,30e-9]}
    rows=acquisition_cycle_diagnosis(good,edges)['cycles'];assert len(rows)==2
    assert all(abs(r['feedback_period_s']-10e-9)<1e-20 for r in rows)
    assert abs(rows[0]['v(vctrl)']['mean_v']-1.015)<1e-12
    assert all(r['v(up)']['duty_above_1p25v']==1 and r['v(down)']['duty_above_1p25v']==0 for r in rows)
    bad={k:v.copy() for k,v in good.items()};bad['v(up)'][100]=np.nan
    for vectors,edge_record in [(bad,edges),(good,{'feedback_edges_s':[20e-9,10e-9,30e-9]})]:
        try: acquisition_cycle_diagnosis(vectors,edge_record)
        except AssertionError: continue
        raise AssertionError('Invalid descriptive cycle input accepted')
    return dict(ramp_mean_and_constant_pulse_controls=True,nonfinite_and_reversed_edges_rejected=True)


def review_completed_acquisition(diagnose=False):
    """Hosted lossless review of one exact completed run; launches no simulator."""
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    controls = acquisition_controls()
    if diagnose: controls['cycle_diagnosis']=acquisition_cycle_controls()
    out = ROOT/'cloud-pll-acquisition-review'; out.mkdir(exist_ok=False)
    result = dict(status='RUNNING_EXACT_NATIVE865_ACQUISITION_REVIEW',
                  source_run=ACQUISITION_RUN, controls=controls,
                  full_phy_accepted=False, full_device_safety_accepted=False,
                  acquisition_accepted=False, no_new_native=True)
    def save(): (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api',
            'repos/Melihakbulut221/nssoc/'+path]))
    save()
    try:
        run = api(f'actions/runs/{ACQUISITION_RUN}')
        assert run['status']=='completed' and run['conclusion']=='success', 'Await original native completion; never restart'
        assert run['head_sha']==ACQUISITION_SOURCE and run['run_attempt']==1
        release = api(f'releases/tags/cloud-results-{ACQUISITION_RUN}-1-pll-snapshot')
        stem = f'pll-snapshot-{ACQUISITION_RUN}-1'
        def asset(name):
            matches = [a for a in release['assets'] if a['name']==name]
            assert len(matches)==1
            return matches[0]
        summary_asset, archive_asset, hash_asset = [asset(stem+suffix) for suffix in ['.json','.tar.gz','.tar.gz.sha256']]
        def bytes_of(a):
            raw = subprocess.check_output(['gh','api',f"repos/Melihakbulut221/nssoc/releases/assets/{a['id']}",'-H','Accept: application/octet-stream'])
            assert len(raw)==a['size']
            return raw
        summary = bytes_of(summary_asset); record=json.loads(summary)
        words=bytes_of(hash_asset).decode().split()
        assert len(words)==2 and words[1]==stem+'.tar.gz' and re.fullmatch('[0-9a-f]{64}',words[0])
        packed=out/'original.tar.gz';fetch(archive_asset['browser_download_url'],words[0],packed)
        assert packed.stat().st_size==archive_asset['size']
        result['source_assets'] = dict(summary_id=summary_asset['id'],summary_sha256=digest(summary),
            archive_id=archive_asset['id'],archive_sha256=words[0],archive_bytes=archive_asset['size'])
        with tarfile.open(packed) as tar:
            def member(name):
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                matches=[m for m in tar.getmembers() if m.name=='cloud-pll-snapshot/'+name]
                assert len(matches)==1 and matches[0].isfile(), 'Unique regular capture member'
                return tar.extractfile(matches[0]).read()
            assert member('result.json')==summary, 'Published and archived result identity'
            assert record['status']=='COMPLETE_ONE_US_NATIVE865_SELECTED_PROBES_REQUIRES_LOCK_AND_SAFETY_REVIEW'
            assert record['mode']=='fresh_time_zero_acquisition_capture'
            assert len(record['inputs'])==35 and record['native_stop_s']==1e-6
            assert record['comparison_stop_s'] is None and record['snapshot_stop_s'] is None
            for item in record['inputs'].values():
                data=member(item['hosted_path'])
                assert len(data)==item['bytes'] and digest(data)==item['sha256']
            bench=member('source/bench.cir'); parent=member('parent865.spice')
            assert digest(bench)==RECORDS['native07/bench.cir'][1]==record['source_deck_sha256']
            assert digest(parent)==RECORDS['native07/parent865.spice'][1]==record['parent_sha256']
            circuit=member('circuit.cir').decode()
            roots=set(re.findall(r'(/[^"\s]+/cloud-pll-snapshot)/models/models',circuit))
            assert len(roots)==1
            base=roots.pop()
            body,control=bench.decode().split('.control\n');setup=control.split('\nop\n',1)[0]
            expected_body=body.replace(MODEL_ROOT,base+'/models/models')
            expected_setup=setup.replace(OSDI_ROOT+'/r3_cmc.osdi',base+'/models/r3_cmc.osdi')
            for name in ['psp103.osdi','psp103_nqs.osdi']:
                expected_setup=expected_setup.replace(OSDI_ROOT+'/'+name,base+'/frontend/'+name)
            assert circuit=='* '+expected_body+'.control\n'+expected_setup+'\n.endc\n.end\n'
            assert digest(circuit.encode())==record['relocated_deck_sha256']
            assert member('spinit')==b'set num_threads=1\n'
            assert member('acquisition.cir')==b'NSSOC native865 original1us continuous capture\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun acquisition.raw\nquit\n.endc\n.end\n'
            runs=record['native_runs']; assert len(runs)==1 and runs[0]['script']=='acquisition.cir'
            assert runs[0]['returncode']==0 and not runs[0]['diagnostics']
            assert digest(member('acquisition.cir.log'))==runs[0]['log_sha256']
            raw=member('acquisition.raw')
        capture=record['captures']['acquisition.raw']
        assert len(raw)==capture['bytes'] and digest(raw)==capture['sha256']
        names,values,meta=decode_prefix(raw)
        assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
        assert all(capture[k]==v for k,v in meta.items())
        assert set(names)=={'time',*record['vectors']} and len(names)==25 and len(values)>3000000
        assert np.max(np.diff(values[:,0]))<=3.125e-13*1.00001
        data={name:values[:,i] for i,name in enumerate(names)}
        independent=acquisition_analyzer()(data)
        result.update(status='COMPLETE_ORIGINAL_ACQUISITION_SCREEN_NOT_PHY_ACCEPTANCE',
            selected_probe_acquisition_passed=independent['passed'], independent=independent,
            capture=meta,raw_sha256=digest(raw),phase_shift_fitted=False,
            scope='Exact original865 selected24probes/full1us. Original100ppm/50ps/no-slip/VCTRL and final800-900ns/900-1000ns gates. No full-device1us safety, timestep/PVT/CDR/jitter or PHY acceptance.')
        if diagnose:
            result['cycle_diagnosis']=acquisition_cycle_diagnosis(data,independent)
            result['bound_source_netlists']=dict(bench=dict(sha256=digest(bench),text=bench.decode()),
                parent865=dict(sha256=digest(parent),text=parent.decode()))
        save();packed.unlink(); print(result['status'],flush=True)
    except BaseException as error:
        result.update(status='FAILED_EXACT_NATIVE865_ACQUISITION_REVIEW',error=repr(error));save();raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--review-acquisition',action='store_true')
    parser.add_argument('--diagnose-acquisition',action='store_true')
    parser.add_argument('--acquisition',action='store_true',help='Fresh uninterrupted original1us selected-probe capture; never restore a snapshot')
    args=parser.parse_args()
    if args.review_acquisition or args.diagnose_acquisition:
        assert not args.acquisition and not args.self_test
        review_completed_acquisition(diagnose=args.diagnose_acquisition);return
    controls=self_test()
    controls['acquisition_review']=acquisition_controls()
    controls['cycle_diagnosis']=acquisition_cycle_controls()
    if args.self_test: print(json.dumps(controls));return
    assert os.environ.get('GITHUB_ACTIONS')=='true', 'Hosted execution only'
    out=ROOT/'cloud-pll-snapshot';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_NATIVE865_SNAPSHOT_PORTABILITY',controls=controls,
        full_phy_accepted=False,acquisition_accepted=False,snapshot_validated=False,
        reference='https://ngspice.sourceforge.io/docs/ngspice-manual.pdf',
        scope='Actual865-device circuit and full extracted metal RC, exact historical 1us deck stopped at25/50ns. Original model/runtime bytes, startup sources, .3125ps step and tolerances retained. Compares continuous vs same-process resumed vs fresh-process restored waveforms. Only bounded restart-method evidence, not1us lock, all-device safety, PVT, CDR, full serialPHY, or chip acceptance.')
    def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.acquisition:
        result.update(status='RUNNING_ONE_US_NATIVE865_SELECTED_PROBE_CAPTURE',
            mode='fresh_time_zero_acquisition_capture',
            scope='Original865 circuit and full extracted metal RC with exact32models/3OSDIs, startup, .3125ps step, KLU and tolerances. Fresh uninterrupted1us selected24probes only. Complete capture is NOT acquisition/phase/slip, full-device safety, PVT, CDR, jitter or PHY acceptance; those reviews remain required. No cross-process snapshot is used.')
    save()
    try:
        selected={PREFIX+n:RECORDS[n] for n in ['native07/bench.cir','native07/parent865.spice','gate01.json']}
        unpack(BASE+'cloud-migration-20261012-000/batch-000002.tar.gz',
               SOURCE_SHA,141989022,out/'source',selected)
        gate=json.loads((out/'source/gate01.json').read_text())
        assert all(gate[k] for k in ('functional_passed','independent_electrical_passed','native_safety_passed','dispatched'))
        unpack(BASE+'cloud-migration-20261012-000/batch-000007.tar.gz',
               FINITE_SHA,669884,out/'finite',{FINITE_ROOT+'result.json':
                (943771,'ffe86baa2ddfc6a0eb47214adb03360caaeb63e2da9aec199813f01d4b8ba855')})
        finite=json.loads((out/'finite/result.json').read_text())
        assert finite['status']=='PASS_NATIVE_PARENT865_FINITE_POINT'
        assert finite['zero_source_op'] and finite['clean_diagnostics']
        specs=[json.loads((ROOT/'docs/evidence'/name).read_text()) for name in
               ['pcie-tx-cloud-input-20261013.json','pcie-cmos-data-driver-input-20261013.json']]
        for name,spec in zip(['models','frontend'],specs):
            r=spec['receipt'];dest=out/name
            unpack(r['url'],r['sha256'],r['bytes'],dest)
            m=json.loads((dest/'manifest.json').read_text())
            assert all((dest/n).stat().st_size==v['bytes'] and sha(dest/n)==v['sha256']
                       for n,v in m['files'].items())
        checked={}
        for old,v in finite['inputs'].items():
            path=Path(old)
            if old.startswith(MODEL_ROOT+'/'):
                new=out/'models/models'/path.name
            elif old.startswith(OSDI_ROOT+'/'):
                new=out/('models' if path.name=='r3_cmc.osdi' else 'frontend')/path.name
            else: continue
            assert new.stat().st_size==v['bytes'] and sha(new)==v['sha256']
            checked[old]=dict(hosted_path=str(new.relative_to(out)),**v)
        assert len(checked)==35, 'Require all32 original model files and3 OSDIs'
        executable=Path(os.environ['CLOUD_NGSPICE'])
        assert sha(executable)==specs[0]['native_runtime']['executable_sha256']
        bench=(out/'source/bench.cir').read_text()
        assert bench.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
        assert '.options reltol=1e-4 abstol=1e-12 klu' in bench
        body,control=bench.split('.control\n')
        setup=control.split('\nop\n',1)[0]
        assert '\nop\n' in control and setup.count('save ')==1
        vectors=next(l[5:].split() for l in setup.splitlines() if l.startswith('save '))
        assert len(vectors)==24 and len(set(vectors))==24
        alters=[l for l in setup.splitlines() if l.startswith('alter ')]
        assert alters and all(l.endswith('[off] = 1') for l in alters)
        relocated=body.replace(MODEL_ROOT,str(out/'models/models'))
        assert body.count(MODEL_ROOT)==5
        setup=setup.replace(OSDI_ROOT+'/r3_cmc.osdi',str(out/'models/r3_cmc.osdi'))
        for n in ['psp103.osdi','psp103_nqs.osdi']:
            setup=setup.replace(OSDI_ROOT+'/'+n,str(out/'frontend'/n))
        assert '/home/hasanmelih/' not in relocated+setup and '/dev/shm/' not in relocated+setup
        (out/'parent865.spice').write_bytes((out/'source/parent865.spice').read_bytes())
        # The reusable deck is also included: its original title must be a comment.
        (out/'circuit.cir').write_text('* '+relocated+'.control\n'+setup+'\n.endc\n.end\n')
        (out/'spinit').write_text('set num_threads=1\n')
        common='.include "circuit.cir"\n.control\nop\nwrite op.raw all\n'
        continuous='NSSOC native865 continuous50ns reference\n'+common+'stop when time > 50n\nrun\nwrite continuous.raw all\nquit\n.endc\n.end\n'
        split='NSSOC native865 same-process snapshot control\n'+common+'stop when time > 25n\nrun\nwrite prefix.raw all\nsnsave checkpoint.snap\ndelete all\nstop when time > 50n\nresume\nwrite same-process.raw all\nquit\n.endc\n.end\n'
        restored='NSSOC script fresh-process native865 restart\n.control\nsnload circuit.cir checkpoint.snap\nstop when time > 50n\nresume\nwrite restored.raw all\nquit\n.endc\n.end\n'
        for n,s in [('continuous.cir',continuous),('split.cir',split),('restore.script',restored)]:
            (out/n).write_text(s)
        result.update(inputs=checked,executable_sha256=sha(executable),
            source_deck_sha256=sha(out/'source/bench.cir'),relocated_deck_sha256=sha(out/'circuit.cir'),
            parent_sha256=sha(out/'parent865.spice'),native_off_flags=len(alters),vectors=vectors,
            native_stop_s=1e-6,comparison_stop_s=50e-9,snapshot_stop_s=25e-9)
        save()
        if args.acquisition:
            # Native run's rawfile records output during execution; retain it even
            # if the runner deadline interrupts a row. Never pad or accept it.
            text='NSSOC native865 original1us continuous capture\n'+common+'run acquisition.raw\nquit\n.endc\n.end\n'
            assert 'stop when' not in text and 'snload' not in text and 'resume' not in text
            (out/'acquisition.cir').write_text(text)
            result.update(native_budget_s=20800,required_capture_stop_s=1e-6,
                runtime_basis=dict(run=38503868241,continuous50ns_s=994.3820633739999,
                    linear1us_estimate_s=19887.64126748,estimate_is_not_a_guarantee=True),
                comparison_stop_s=None,snapshot_stop_s=None)
            save()
            native_run(executable,out,'acquisition.cir',time.monotonic()+20800,result,save)
            raw=(out/'acquisition.raw').read_bytes()
            names,values,meta=decode_prefix(raw)
            assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
            assert set(names)=={'time',*vectors} and len(values)>3000000
            t=values[:,0]
            assert t[0]==0 and 1e-6-1e-15 <= t[-1] <= 1e-6+1e-15
            assert np.max(np.diff(t)) <= 3.125e-13*1.00001
            result['captures']={'acquisition.raw':dict(**meta,sha256=digest(raw),bytes=len(raw),
                start_s=float(t[0]),end_s=float(t[-1]))}
            v={name:values[:,i] for i,name in enumerate(names)}
            edges={name:rising(t,signal,threshold) for name,signal,threshold in [
                ('vco',v['v(clkp)']-v['v(clkn)'],0.),
                ('feedback',v['v(fb)'],1.25),('reference',v['v(reference)'],1.25)]}
            windows=[]
            for start,end in [(0,50),(50,100),(100,200),(200,400),(400,600),(600,800),(800,900),(900,1000)]:
                a,z=start*1e-9,end*1e-9;mask=(t>=a)&(t<=z)
                stats={}
                for name,edge in edges.items():
                    e=edge[(edge>=a)&(edge<=z)];periods=np.diff(e)
                    stats[name]=dict(rising_edges=len(e),
                        frequency_from_median_period_hz=float(1/np.median(periods)) if len(periods) else None,
                        min_period_s=float(periods.min()) if len(periods) else None,
                        max_period_s=float(periods.max()) if len(periods) else None)
                windows.append(dict(start_ns=start,end_ns=end,edges=stats,
                    node_ranges={name:dict(minimum=float(v[name][mask].min()),maximum=float(v[name][mask].max()))
                        for name in ['v(vctrl)','v(up)','v(down)','v(fb)','v(reference)']}))
            result.update(status='COMPLETE_ONE_US_NATIVE865_SELECTED_PROBES_REQUIRES_LOCK_AND_SAFETY_REVIEW',
                windows=windows,phase_shift_fitted=False,
                required_followup=['fixed original acquisition phase/frequency/slip review',
                    'all-device1us native safety','timestep and independent PVT','PLL/CDR serialPHY integration'])
            save();print(result['status'],flush=True);return
        deadline=time.monotonic()+19000
        captures={}
        for script,name in [('continuous.cir','continuous.raw'),('split.cir','same-process.raw'),
                            ('restore.script','restored.raw')]:
            native_run(executable,out,script,deadline,result,save)
            raw=(out/name).read_bytes()
            names,values,meta=decode_prefix(raw)
            assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
            assert set(names)=={'time',*vectors}
            captures[name]=(names,values)
            result.setdefault('captures',{})[name]=dict(**meta,sha256=digest(raw),bytes=len(raw),
                start_s=float(values[0,0]),end_s=float(values[-1,0]))
            if script=='split.cir':
                assert (out/'checkpoint.snap').stat().st_size>1000
                result['snapshot']=dict(bytes=(out/'checkpoint.snap').stat().st_size,sha256=sha(out/'checkpoint.snap'))
            save()
        result['continuous_vs_same_process']=compare(captures['continuous.raw'],captures['same-process.raw'])
        result['same_process_vs_restored']=compare(captures['same-process.raw'],captures['restored.raw'])
        result['continuous_vs_restored']=compare(captures['continuous.raw'],captures['restored.raw'])
        passed=all(result[n]['passed'] for n in ['continuous_vs_same_process','same_process_vs_restored','continuous_vs_restored'])
        result.update(snapshot_validated=passed,status='PASS_BOUNDED_NATIVE865_RESTART_NOT_ACQUISITION' if passed else 'FAIL_NATIVE865_RESTART_MISMATCH')
        save()
        assert passed, 'Snapshot transport is not equivalent under fixed diagnostic bounds'
    except BaseException as error:
        result.update(status='FAILED_ONE_US_NATIVE865_SELECTED_PROBE_CAPTURE' if args.acquisition else 'FAILED_NATIVE865_SNAPSHOT_NOT_ACQUISITION',error=repr(error))
        save();raise

if __name__=='__main__':
    main()
