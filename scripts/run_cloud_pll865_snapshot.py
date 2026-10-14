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




def full50_fifo_payload(stream, rows, width):
    """Hash complete binary rows and independently validate native FIFO trailer.

    Original capture engine records No.Points=0 and an ASCII point count after
    all binary rows. The trailer belongs to raw SHA, never payload SHA.
    """
    assert rows>1 and width>0
    remaining=rows*width*8;h=hashlib.sha256()
    while remaining:
        part=stream.read(min(1024**2,remaining));assert part,'Truncated FIFO row payload'
        h.update(part);remaining-=len(part)
    trailer=stream.read()
    assert trailer==str(rows).encode(), 'Missing/wrong/extra FIFO point-count trailer'
    return dict(payload_sha256=h.hexdigest(),trailer_ascii=trailer.decode(),payload_bytes=rows*width*8)


def full50_fifo_controls():
    payload=np.asarray([[0.,1.],[1.,2.],[2.,3.]],dtype='<f8').tobytes()
    good=payload+b'3'
    assert full50_fifo_payload(io.BytesIO(good),3,2)['payload_sha256']==digest(payload)
    bads=[payload,payload+b'2',payload+b'3x',payload[:-1]+b'3',good[:-9]]
    for bad in bads:
        try:full50_fifo_payload(io.BytesIO(bad),3,2)
        except AssertionError:continue
        raise AssertionError('Damaged native FIFO accepted')
    return dict(positive=1,rejected_missing_wrong_extra_trailer_or_truncated_payload=len(bads))



def full50_column_names(table, expected):
    """Preserve original source-vector order and exact native @device aliases."""
    assert len(table)==len(expected) and len(set(expected))==len(expected)
    assert all(len(row)==3 for row in table) and table[0]==['0','time','time']
    assert [row[0] for row in table]==list(map(str,range(len(table))))
    assert len({row[1] for row in table})==len(table)
    for row,name in zip(table,expected,strict=True):
        allowed={name}
        if name.startswith('@'):allowed|={'i('+name+')','v('+name+')'}
        assert row[1] in allowed,('Unexpected native vector alias/order',row,name)
    return list(expected)


def full50_alias_controls():
    table=[['0','time','time'],['1','v(up)','voltage'],['2','i(@n.m[ids])','current']]
    expected=['time','v(up)','@n.m[ids]']
    assert full50_column_names(table,expected)==expected
    faults=[table[:-1],[table[0],table[2],table[1]],
        [table[0],table[1],['2','i(@n.other[ids])','current']],
        [table[0],table[1],['2','v(up)','current']]]
    for bad in faults:
        try:full50_column_names(bad,expected)
        except AssertionError:continue
        raise AssertionError('Incorrect native vector binding accepted')
    return dict(positive=1,negative=len(faults))


def full50_probe_selection(names, parent, expected_pfd_mos=102):
    """Require actual PFD D/G/S coverage, not just extracted well-node names."""
    assert len(names)==len(set(names))
    devices=[]
    for line in parent.splitlines():
        words=line.lower().split()
        if words and words[0].startswith('x_xpfd_') and len(words)>5 and words[5] in ('sg13_hv_nmos','sg13_hv_pmos'):
            devices.append(dict(instance=words[0],model=words[5],terminals=dict(zip(('d','g','s'),words[1:4]))))
    assert len(devices)==expected_pfd_mos, ('Unexpected PFD MOS inventory',len(devices))
    required={'v(xloop.'+node+')' for d in devices for node in d['terminals'].values()}
    assert required<=set(names), ('Unrecorded PFD D/G/S probes',sorted(required-set(names)))
    chosen=[n for n in names if n in {'time','v(clkp)','v(clkn)','v(fb)','v(reference)','v(up)','v(down)','v(vctrl)','v(reset)'}
        or n.startswith(('v(xloop.xpfd.','v(xloop.xpump.','v(xloop.a_pfd','v(xloop.a_pump'))
        or n.startswith('@') and 'xpump' in n]
    assert {'time','v(fb)','v(reference)','v(up)','v(down)','v(vctrl)'}<=set(chosen)
    assert required<=set(chosen), 'PFD D/G/S probe omitted from analysis'
    return chosen,dict(pfd_mos_count=len(devices),required_terminal_vectors=sorted(required),
        every_pfd_drain_gate_source_recorded_and_analyzed=True,devices=devices)


def full50_probe_controls():
    parent='X_xpfd_xd0001 xpfd.t001_d xpfd.t001_g xpfd.t001_s xpfd.n_1 sg13_hv_nmos w=2u l=.45u'
    names=['time','v(fb)','v(reference)','v(up)','v(down)','v(vctrl)',
        'v(xloop.xpfd.n_1)','v(xloop.xpfd.t001_d)','v(xloop.xpfd.t001_g)','v(xloop.xpfd.t001_s)']
    selected,proof=full50_probe_selection(names,parent,1)
    assert selected==names and len(proof['required_terminal_vectors'])==3
    faults=[names[:-1],names[:-2]+[names[-1]],names+names[-1:]]
    for bad in faults:
        try:full50_probe_selection(bad,parent,1)
        except AssertionError:continue
        raise AssertionError('Missing/duplicate PFD terminal probe accepted')
    try:full50_probe_selection(names,parent,2)
    except AssertionError:pass
    else:raise AssertionError('Wrong PFD MOS inventory accepted')
    return dict(positive=1,negative=4)


def pfd_topology_map(parent, reference, ports=('ref','fb','reset','up','down','vdd','vss')):
    """Diagnostic MOS D/G/S graph correspondence; never modifies simulated RC.

    Collapse ONLY extracted PFD metal resistors for this naming map. Source/drain
    exchange is allowed, gate/model/W/L and every external port are anchored.
    Bodies, finite taps and RC electrical behavior are not LVS-proved by this map.
    """
    from collections import Counter, defaultdict
    from decimal import Decimal
    import re
    uf={}
    def root(n):
        uf.setdefault(n,n)
        while uf[n]!=n:
            uf[n]=uf[uf[n]];n=uf[n]
        return n
    def dim(value):
        m=re.fullmatch(r'([0-9.eE+-]+)([unp]?)',value)
        assert m, ('Unrecognized dimension',value)
        return str((Decimal(m[1])*{'':Decimal(1),'u':Decimal('1e-6'),'n':Decimal('1e-9'),'p':Decimal('1e-12')}[m[2]]).normalize())
    lines=[l.lower().split() for l in parent.splitlines()]
    wires=[w for w in lines if w and w[0].startswith('r_xpfd_')]
    assert len({w[0] for w in wires})==len(wires)
    for w in wires:
        assert len(w)==4 and Decimal(w[3])>0
        uf[root(w[2])]=root(w[1])
    native=[]
    for w in lines:
        if not (w and w[0].startswith('x_xpfd_') and len(w)>5 and w[5] in ('sg13_hv_nmos','sg13_hv_pmos')):continue
        params=dict(x.split('=',1) for x in w[6:])
        native.append(dict(path=w[0],model=w[5],params=params,nets=[root(n) for n in w[1:4]],raw_nets=w[1:4]))
    assert len(native)==len(reference) and len({d['path'] for d in native})==len(native)
    nports={root('a_pfd_'+p):p for p in ports};assert len(nports)==len(ports),'Shorted PFD ports'
    def graph(devs, anchored):
        bases={};neighbors=defaultdict(list)
        for n,p in anchored.items():bases[('n',n)]='PORT:'+p
        for dev in devs:
            dn=('d',dev['path']);assert dn not in bases
            bases[dn]='MOS:'+dev['model']+':'+dim(dev['params']['w'])+':'+dim(dev['params']['l'])
            for role,n in zip(('ds','g','ds'),dev['nets'][:3],strict=True):
                nn=('n',n);bases.setdefault(nn,'NET')
                neighbors[dn].append((role,nn));neighbors[nn].append((role,dn))
        return bases,neighbors
    graphs=[graph(reference,{p:p for p in ports}),graph(native,nports)]
    palette={k:i for i,k in enumerate(sorted({v for b,_ in graphs for v in b.values()}))}
    colors=[{n:palette[v] for n,v in b.items()} for b,_ in graphs]
    assert Counter(colors[0].values())==Counter(colors[1].values()),'MOS/port inventory differs'
    for iteration in range(sum(len(b) for b,_ in graphs)):
        signatures=[{n:(c[n],tuple(sorted((r,c[v]) for r,v in neighbors[n]))) for n in bases}
            for (bases,neighbors),c in zip(graphs,colors,strict=True)]
        palette={k:i for i,k in enumerate(sorted({v for sig in signatures for v in sig.values()}))}
        new=[{n:palette[v] for n,v in sig.items()} for sig in signatures]
        assert Counter(new[0].values())==Counter(new[1].values()),'PFD connectivity/gate/W/L mismatch'
        stable=len(set(new[0].values()))==len(set(colors[0].values()));colors=new
        if stable:break
    else:raise AssertionError('PFD graph refinement did not converge')
    netsets=[]
    for c in colors:
        groups=defaultdict(list)
        for (kind,n),color in c.items():
            if kind=='n':groups[color].append(n)
        netsets.append(groups)
    assert all(len(v)==1 for g in netsets for v in g.values()),'Ambiguous internal PFD net correspondence'
    mapped={v[0]:netsets[1][color][0] for color,v in netsets[0].items()}
    inverse={v:k for k,v in mapped.items()};assert len(inverse)==len(mapped)
    def key(dev,conv):
        d,g,s=(conv(n) for n in dev['nets'][:3])
        return dev['model'],dim(dev['params']['w']),dim(dev['params']['l']),g,tuple(sorted((d,s)))
    assert Counter(key(d,lambda n:n) for d in reference)==Counter(key(d,inverse.__getitem__) for d in native),'Complete MOS-edge check failed'
    mapping={}
    for logical,net in sorted(mapped.items()):
        points=[]
        for d in native:
            for role,n,raw in zip(('d','g','s'),d['nets'],d['raw_nets'],strict=True):
                if n==net:points.append(dict(device=d['path'],terminal=role,vector='v(xloop.'+raw+')'))
        mapping[logical]=dict(native_component=net,terminals=points)
    return dict(status='PASS_EXACT_MOS_DGS_TOPOLOGY_FOR_DIAGNOSTIC_NAMING_NOT_LVS',
        mos_count=len(native),metal_resistors=len(wires),refinement_rounds=iteration+1,nets=mapping,
        scope='Unique anchored net map and full MOS D/G/S/model/W/L multiset; DS exchange allowed. Bodies/taps/electrical RC not validated here. Original full RC circuit and waveform unchanged.')


def pfd_topology_controls():
    source=[dict(path='n',model='sg13_hv_nmos',params={'w':'2u','l':'.45u'},nets=['out','in','vss']),
        dict(path='p',model='sg13_hv_pmos',params={'w':'4u','l':'.45u'},nets=['out','in','vdd'])]
    text='\n'.join(['R_xpfd_1 n1 a_pfd_out 3','R_xpfd_2 n2 a_pfd_in 4',
        'X_xpfd_n a_pfd_vss n2 n1 body sg13_hv_nmos w=2u l=0.45u',
        'X_xpfd_p n1 n2 a_pfd_vdd well sg13_hv_pmos w=4u l=0.45u'])
    ports=('in','out','vdd','vss')
    good=pfd_topology_map(text,source,ports);assert good['mos_count']==2 and set(good['nets'])==set(ports)
    faults=[text.replace('n2 n1 body','n1 n1 body'),text.replace('w=4u','w=5u'),
        '\n'.join(text.splitlines()[:-1]),text.replace('n1 a_pfd_out','n1 a_pfd_in')]
    for bad in faults:
        try:pfd_topology_map(bad,source,ports)
        except AssertionError:continue
        raise AssertionError('Corrupt PFD graph accepted')
    return dict(positive_source_drain_exchange=1,rejected_gate_size_missing_device_short=len(faults))


def diagnose_pfd_topology():
    """Map completed native full50 terminal observations to original schematic."""
    import importlib.util
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted topology analysis only'
    out=ROOT/'cloud-pll-acquisition-review';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_PFD_TOPOLOGY_DIAGNOSIS',full_phy_accepted=False,acquisition_accepted=False,no_new_native=True)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        source=out/'full50.json'
        fetch(BASE+'cloud-results-38600813474-1-pll-acquisition-review/result.json',
            'fef204c48418fbf8242d9dbf739f9d06ce6cac1c2b38a6412c1ff55dc181f164',source)
        capture=json.loads(source.read_text())
        assert capture['status']=='COMPLETE_FULL50_PFD_PUMP_DIAGNOSIS_NOT_LOCK_ACCEPTANCE'
        assert capture['pfd_terminal_coverage']['every_pfd_drain_gate_source_recorded_and_analyzed']
        generator=ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py'
        spec=importlib.util.spec_from_file_location('pfd_original_source',generator)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        sources={name:(ROOT/'hw/soc/analog/pcie'/name).read_text() for name in module.SOURCES}
        reference=module.devices(sources);assert len(reference)==102
        parent='\n'.join(capture['parent_pfd_and_pump_statements'])
        proof=pfd_topology_map(parent,reference)
        assert proof['metal_resistors']==771 and proof['mos_count']==102
        observations={}
        for logical,net in proof['nets'].items():
            vectors=sorted({x['vector'] for x in net['terminals']})
            assert vectors,('Logical net lacks recorded terminal',logical)
            observations[logical]=[dict(start_s=i['start_s'],stop_s=i['stop_s'],
                terminals={v:i['signals'][v] for v in vectors}) for i in capture['intervals']]
        result.update(status='COMPLETE_SOURCE_MAPPED_PFD_STARTUP_DIAGNOSIS_NOT_LOCK_ACCEPTANCE',
            input=dict(run=38600813474,summary_sha256=sha(source),source_identity=capture['source_identity'],
                generator_sha256=sha(generator),schematic_sha256=module.SOURCES),
            mapping=proof,observations=observations,controls=pfd_topology_controls(),
            scope='Original full RC waveform only; topology names are exact102MOS D/G/S graph correspondence, not new body/tap LVS, qualified PEX or lock. Startup50ns cannot establish late1us causal closure.')
        save();print(result['status'],flush=True)
    except BaseException as error:
        result.update(status='FAILED_PFD_TOPOLOGY_DIAGNOSIS',error=repr(error));save();raise


def diagnose_full50():
    """Read original full-node PBUF10 wave, not the older reset865 circuit."""
    import gzip
    import shutil
    assert os.environ.get('GITHUB_ACTIONS')=='true', 'Hosted waveform analysis only'
    out=ROOT/'cloud-pll-acquisition-review';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_FULL50_INTERNAL_DIAGNOSIS',full_phy_accepted=False,
        acquisition_accepted=False,no_new_native=True,
        scope='Exact current PBUF10 parent865 full-node50ns startup diagnosis only. This cannot prove late1us lock or its failure cause; original rolling-frequency rejection remains.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        finite_files={FINITE_ROOT+n:pin for n,pin in {
            'result.json':(943771,'ffe86baa2ddfc6a0eb47214adb03360caaeb63e2da9aec199813f01d4b8ba855'),
            'bench.cir':(85790,'75a79f2248f9a941ff6a32bfab2d26cce8b23fa75379bb292f9952e1cf6acfd1'),
            'parent865.spice':(603656,RECORDS['native07/parent865.spice'][1]),
        }.items()}
        unpack(BASE+'cloud-migration-20261012-000/batch-000007.tar.gz',FINITE_SHA,669884,out/'finite',finite_files)
        finite=json.loads((out/'finite/result.json').read_text())
        assert finite['status']=='PASS_NATIVE_PARENT865_FINITE_POINT'
        fetch(BASE+'cloud-results-38589545075-1-pll-acquisition-review/result.json',
            '02d9495f9c3b5b4f3f0d113e777712dd9f20ef162ebcc5f04768946b07bc5b66',out/'one-us-diagnosis.json')
        diagnosis=json.loads((out/'one-us-diagnosis.json').read_text())
        parent=diagnosis['bound_source_netlists']['parent865'];bench=diagnosis['bound_source_netlists']['bench']
        assert digest(parent['text'].encode())==parent['sha256']==sha(out/'finite/parent865.spice')
        assert digest(bench['text'].encode())==bench['sha256']==RECORDS['native07/bench.cir'][1]
        old_body,old_control=(out/'finite/bench.cir').read_text().split('.control\n')
        new_body,new_control=bench['text'].split('.control\n')
        assert old_body.count('.tran 3.125e-13 5e-08 0 3.125e-13')==1
        assert old_body.replace('.tran 3.125e-13 5e-08 0 3.125e-13','.tran 3.125e-13 1e-06 0 3.125e-13')==new_body
        for prefix in ('alter ','pre_osdi '):
            assert [l for l in old_control.splitlines() if l.startswith(prefix)]==[l for l in new_control.splitlines() if l.startswith(prefix)]
        assert finite['zero_source_op'] and finite['clean_diagnostics']
        result['source_identity']=dict(parent_sha256=parent['sha256'],full50_bench_sha256=sha(out/'finite/bench.cir'),
            one_us_bench_sha256=bench['sha256'],circuit_body_identical_except_stop_time=True,
            native_off_flags_identical=True,osdi_loads_identical=True,
            original_late_acquisition_passed=diagnosis['selected_probe_acquisition_passed'])
        manifest_path=out/'full50.manifest.json'
        fetch(BASE+'cloud-migration-20261012-000/batch-000008.manifest.json',
            '2cd4453dd465ed3f8d69e363503e16e7d8cfbce4bfb51786b463e8ac5cb95d47',manifest_path)
        manifest=json.loads(manifest_path.read_text())
        assert manifest['encoding']=='concatenated-gzip-parts-single-file' and len(manifest['records'])==1
        record=manifest['records'][0]
        assert record['path']==FINITE_ROOT+'wave.raw.gz'
        assert record['sha256']==finite['outputs']['wave.raw.gz']['sha256']=='7eb021ef4143f8b9c7e706d212f8058512db654a9d86ac6d6ae38133f0f89a5e'
        packed=out/'wave.raw.gz';completed=[]
        with packed.open('xb') as dst:
            for part in manifest['parts']:
                path=out/'part.gz';fetch(part['url'],part['sha256'],path)
                assert path.stat().st_size==part['bytes']
                with gzip.open(path,'rb') as src:shutil.copyfileobj(src,dst,1024**2)
                path.unlink();completed.append(part['name'])
                result['verified_parts']=completed[:];save()
        assert packed.stat().st_size==record['bytes'] and sha(packed)==record['sha256']
        raw_path=out/'wave.raw'
        with gzip.open(packed,'rb') as src,raw_path.open('xb') as dst:shutil.copyfileobj(src,dst,1024**2)
        assert raw_path.stat().st_size==finite['raw_bytes'] and sha(raw_path)==finite['raw_sha256']
        with raw_path.open('rb') as src:
            header=b''
            while not header.endswith(b'Binary:\n'):
                line=src.readline();assert line and len(header)<1048576;header+=line
            offset=len(header)
            fifo=full50_fifo_payload(src,finite['rows'],len(finite['columns']))
            assert fifo['payload_sha256']==finite['payload_sha256']
        header=header.decode('ascii');assert 'Flags: real\n' in header
        fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in header.splitlines() if ':' in line}
        table=[line.split() for line in header.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
        assert table==finite['raw_table']
        names=full50_column_names(table,finite['columns'])
        rows,width=finite['rows'],len(names)
        assert int(fields['No. Variables'])==width and int(fields['No. Points'])==0
        assert offset+8*rows*width+len(str(rows))==finite['raw_bytes']
        values=np.memmap(raw_path,dtype='<f8',mode='r',offset=offset,shape=(rows,width))
        for first in range(0,rows,4096):assert np.isfinite(values[first:first+4096]).all()
        t=np.asarray(values[:,0]).copy();assert t[0]==0 and abs(t[-1]-50e-9)<1e-18
        assert np.all(np.diff(t)>0) and np.max(np.diff(t))<=3.125e-13*1.00001
        chosen,coverage=full50_probe_selection(names,parent['text'])
        result['pfd_terminal_coverage']=coverage
        data={n:np.asarray(values[:,names.index(n)]).copy() for n in chosen}
        feedback=rising(t,data['v(fb)'],1.25)
        intervals=[(0.,50e-9),*[(float(a),float(b)) for a,b in zip(feedback[:-1],feedback[1:])]]
        result['wave']=dict(raw_sha256=finite['raw_sha256'],payload_sha256=finite['payload_sha256'],rows=rows,columns=width,
            complete_header_payload_and_fifo_trailer_verified=True,header_declared_points=0,
            fifo_trailer=fifo,selected_columns=chosen)
        records=[]
        for start,stop in intervals:
            mask=(t>start)&(t<stop);at=np.r_[start,t[mask],stop];signals={}
            for n,v in data.items():
                if n=='time':continue
                y=np.r_[np.interp(start,t,v),v[mask],np.interp(stop,t,v)]
                stats=dict(minimum=float(y.min()),maximum=float(y.max()),time_mean=float(np.trapezoid(y,at)/(stop-start)))
                if n.startswith('v('):
                    edges=rising(at,y,1.25)
                    stats.update(rising_edges_at_1p25_v_s=edges.tolist(),
                        falling_edges_at_1p25_v_s=rising(at,-y,-1.25).tolist(),
                        above_1p25_v_time_fraction=float(np.trapezoid((y>=1.25).astype(float),at)/(stop-start)))
                signals[n]=stats
            records.append(dict(start_s=start,stop_s=stop,signals=signals))
        result.update(status='COMPLETE_FULL50_PFD_PUMP_DIAGNOSIS_NOT_LOCK_ACCEPTANCE',intervals=records,
            parent_pfd_and_pump_statements=[l for l in parent['text'].splitlines() if any(k in l.lower() for k in ['xpfd','xpump','a_pfd','a_pump'])],
            scope='Exact full-node50ns startup observation with every102PFD MOS drain/gate/source included. Voltage duty is not pump current. Actual recorded pump device currents are labeled by original vector names. No late1us internal capture, fitted phase, relaxed lock gate or causal closure.')
        save();del values;raw_path.unlink();packed.unlink()
        print(result['status'],flush=True)
    except BaseException as error:
        result.update(status='FAILED_FULL50_INTERNAL_DIAGNOSIS',error=repr(error));save();raise


def pfd_aoi_devices():
    """Use the same transistor list for native simulation and actual layout."""
    import importlib.util
    spec=importlib.util.spec_from_file_location('shared_pfd_geometry',ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.aoi_reset_devices()


def pfd_aoi_controls():
    import itertools
    def verify(rows):
        for up,down,reset in itertools.product((False,True),repeat=3):
            gates={'up':up,'down':down,'reset':reset};links={}
            for d in rows:
                a,g,b,_=d['nets'];on=gates[g] if d['model'].endswith('nmos') else not gates[g]
                if on:links.setdefault(a,set()).add(b);links.setdefault(b,set()).add(a)
            reached={'xloop.clearb'};todo=list(reached)
            while todo:
                for n in links.get(todo.pop(),()):
                    if n not in reached:reached.add(n);todo.append(n)
            assert ('vdd' in reached)==(not (reset or up and down))
            assert ('vss' in reached)==(reset or up and down)
        return True
    rows=pfd_aoi_devices();assert verify(rows)
    faults=[]
    for index in range(len(rows)):
        bad=json.loads(json.dumps(rows));old=bad[index]['nets'][1]
        bad[index]['nets'][1]={'up':'reset','down':'up','reset':'down'}[old];faults.append(bad)
    for bad in faults:
        try:verify(bad)
        except AssertionError:continue
        raise AssertionError('Wrong static AOI reset connection accepted')
    return dict(all_input_truth_states=8,rejected_wrong_gate_controls=len(faults),scope='Static rail connectivity only; dynamic reset recovery requires native transient')




def pfd_terminal_diagnosis(parent, names, values):
    """Quantify actual terminal stress; no device qualification limits inferred."""
    from collections import Counter
    from build_pcie_local_vco_hybrid_v6 import statements,number
    assert len(set(names))==len(names) and names[0]=='time'
    assert values.ndim==2 and values.shape[1]==len(names) and len(values)>1
    assert np.isfinite(values).all() and values[0,0]==0 and np.all(np.diff(values[:,0])>0)
    t=values[:,0];index={n:i for i,n in enumerate(names)}
    rows=[r for r in statements(parent) if r[0].lower().startswith('x_xpfd_')]
    assert len(rows)==235 and len({r[0].lower() for r in rows})==235
    census=Counter();mos=[];contacts=[];required=set()
    def vector(node):
        name='v(xloop.'+node.lower()+')';required.add(name)
        assert name in index,('Missing physical terminal probe',name)
        return values[:,index[name]]
    def extrema(y):
        low,high,absolute=int(np.argmin(y)),int(np.argmax(y)),int(np.argmax(abs(y)))
        return dict(minimum=float(y[low]),minimum_time_s=float(t[low]),
            maximum=float(y[high]),maximum_time_s=float(t[high]),
            maximum_abs=float(abs(y[absolute])),maximum_abs_time_s=float(t[absolute]))
    for r in rows:
        model_at=5 if len(r)>5 and r[5] in ('sg13_hv_nmos','sg13_hv_pmos') else 3
        model=r[model_at];assert model in ('sg13_hv_nmos','sg13_hv_pmos','ptap1','ntap1')
        census[model]+=1
        params={}
        for token in r[model_at+1:]:
            key,value=token.split('=');key=key.lower()
            assert key not in params;params[key]=number(value)
        nodes=r[1:model_at];vs=[vector(n) for n in nodes]
        if model_at==5:
            assert set(params)=={'l','w','as','ad','ps','pd','rfmode','ng','m'}
            assert params['l']>0 and params['w']>0 and params['m']==params['ng']==1
            d,g,s,b=vs
            mos.append(dict(instance=r[0],model=model,
                terminals=dict(zip(('D','G','S','B'),nodes,strict=True)),
                terminal_ranges_v={k:extrema(y) for k,y in zip(('D','G','S','B'),vs,strict=True)},
                differences_v={k:extrema(y) for k,y in [('Vgs',g-s),('Vgd',g-d),('Vds',d-s),('Vbs',b-s),('Vbd',b-d)]}))
        else:
            assert set(params)=={'r','w','l'} and params['r']>0 and params['w']>0 and params['l']>0
            drop=vs[0]-vs[1];resistance=float(params['r'])
            contacts.append(dict(instance=r[0],model=model,
                terminals=dict(zip(('TIE','WELL'),nodes,strict=True)),
                resistance_ohm=resistance,voltage_drop_v=extrema(drop),
                derived_resistive_current_a=extrema(drop/resistance),
                derived_resistive_power_w=extrema(drop*drop/resistance),
                native_current_probe=False))
    assert census==Counter(sg13_hv_nmos=47,sg13_hv_pmos=47,ptap1=94,ntap1=47)
    assert len(mos)==94 and len(contacts)==141
    top={key:sorted([dict(instance=r['instance'],model=r['model'],**r['differences_v'][key])
        for r in mos],key=lambda r:r['maximum_abs'],reverse=True)[:12] for key in ('Vgs','Vgd','Vds','Vbs','Vbd')}
    return dict(status='COMPLETE_235_DEVICE_TERMINAL_DIFFERENCES_NOT_ELECTRICAL_QUALIFICATION',
        devices=235,mos=94,contacts=141,census=dict(census),covered_terminal_voltage_vectors=sorted(required),
        samples=len(t),start_s=float(t[0]),end_s=float(t[-1]),mos_records=mos,contact_records=contacts,
        largest_mos_differences_v=top,
        largest_contact_drops_v=sorted(contacts,key=lambda r:r['voltage_drop_v']['maximum_abs'],reverse=True)[:12],
        contact_current_method='Voltage(TIE)-Voltage(WELL) divided by exact finite compact-model R; derived only, not a simulator current probe.',
        full_device_safety_accepted=False,qualified_pex=False,full_phy_accepted=False,
        scope='Complete actual235 PFD terminal voltage coverage and signed differentials. This is not full845-device safety, oxide/junction/current-density/temperature qualification, spatial substrate/RF extraction, PVT or PHY acceptance.')

def pfd_terminal_controls():
    """Reject lost physical terminals and malformed native device records."""
    names=['time','v(xloop.d)','v(xloop.g)','v(xloop.s)','v(xloop.b)']
    t=np.array([0.,1e-9,2e-9])
    v=np.column_stack([t,np.array([0.,.2,.4]),np.array([0.,.7,1.4]),np.zeros(3),np.array([0.,.1,.2])])
    lines=[]
    for i in range(94):
        model='sg13_hv_nmos' if i<47 else 'sg13_hv_pmos'
        lines.append(f'X_xpfd_d{i} d g s b {model} l=.45u w=4u as=1.36p ad=1.36p ps=8.68u pd=8.68u rfmode=0 ng=1 m=1')
    for i in range(141):
        lines.append(f'X_xpfd_t{i} d b '+('ptap1' if i<94 else 'ntap1')+' r=100 w=2u l=2u')
    parent='\n'.join(lines)
    good=pfd_terminal_diagnosis(parent,names,v)
    assert good['mos_records'][0]['differences_v']['Vgs']['maximum']==1.4
    assert abs(good['mos_records'][0]['differences_v']['Vgd']['maximum']-1.)<1e-15
    assert good['contact_records'][0]['derived_resistive_current_a']['maximum']==.002
    assert abs(good['contact_records'][0]['derived_resistive_power_w']['maximum']-.0004)<1e-18
    nonfinite=v.copy();nonfinite[1,2]=np.nan
    backwards=v.copy();backwards[2,0]=.5e-9
    cases=[
        ('missing_body_probe',parent,names[:-1],v[:,:-1]),
        ('duplicate_probe',parent,names[:-1]+[names[1]],v),
        ('missing_contact','\n'.join(lines[:-1]),names,v),
        ('duplicate_device_identity',parent.replace('X_xpfd_d1 ','X_xpfd_d0 '),names,v),
        ('invalid_model',parent.replace('sg13_hv_nmos','unknown_model',1),names,v),
        ('negative_contact_resistance',parent.replace('r=100','r=-100',1),names,v),
        ('duplicate_parameter',parent.replace('r=100','r=100 r=100',1),names,v),
        ('nonfinite_terminal',parent,names,nonfinite),
        ('backwards_time',parent,names,backwards)]
    failures=[]
    for label,source,columns,wave in cases:
        try:pfd_terminal_diagnosis(source,columns,wave)
        except (AssertionError,ValueError):failures.append(label)
        else:raise AssertionError('Accepted malformed physical-terminal evidence: '+label)
    return dict(positive=1,rejected=failures,qualified_pex=False)

def review_physical_pfd(profile='aoi4_rc'):
    """Read exact completed native capture, reconstruct source, quantify PFD stress."""
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted waveform analysis only'
    assert profile in ('aoi4_rc','aoi4_d2_rc')
    source_run=38616009542 if profile=='aoi4_d2_rc' else 38610259816
    source_head='e0bd3db29bd0bcc3b840da4e0334419bff5c128a' if profile=='aoi4_d2_rc' else '9e56ae047a0e36725bac42daa4868c092c2da261'
    out=ROOT/'cloud-pll-acquisition-review';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_PHYSICAL_PFD_NATIVE50_REVIEW',source_run=source_run,profile=profile,
        full_phy_accepted=False,acquisition_accepted=False,full_device_safety_accepted=False,
        no_new_native=True,controls=pfd_terminal_controls())
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
    save()
    try:
        run=api(f'actions/runs/{source_run}')
        assert run['status']=='completed' and run['conclusion']=='success','Await exact native capture; never restart it'
        assert run['head_sha']==source_head and run['run_attempt']==1
        release=api(f'releases/tags/cloud-results-{source_run}-1-pll-pfd-{profile}')
        stem=f'pll-snapshot-{profile}-{source_run}-1'
        def asset(name):
            matches=[r for r in release['assets'] if r['name']==name];assert len(matches)==1
            return matches[0]
        def get(a):
            data=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
            assert len(data)==a['size'] and a['digest']=='sha256:'+digest(data)
            return data
        sa,aa,ha=[asset(stem+suffix) for suffix in ('.json','.tar.gz','.tar.gz.sha256')]
        summary=get(sa);capture=json.loads(summary);checksum=get(ha).decode().split()
        assert checksum==[aa['digest'].removeprefix('sha256:'),stem+'.tar.gz']
        packed=out/'source.tar.gz';fetch(aa['browser_download_url'],checksum[0],packed)
        assert packed.stat().st_size==aa['size']
        result['source_assets']=dict(summary_id=sa['id'],summary_sha256=digest(summary),
            archive_id=aa['id'],archive_sha256=checksum[0],archive_bytes=aa['size']);save()
        with tarfile.open(packed) as tar:
            def member(name):
                matches=[m for m in tar.getmembers() if m.name=='cloud-pll-snapshot/'+name]
                assert len(matches)==1 and matches[0].isfile()
                return tar.extractfile(matches[0]).read()
            assert member('result.json')==summary
            assert capture['status']=='COMPLETE_PHYSICAL_PFD_NATIVE50_FIXTURE_SCREEN_NOT_LOCK_OR_PARENT_LAYOUT_ACCEPTANCE'
            assert capture['physical_pfd'] is True and capture['native_stop_s']==50e-9
            assert len(capture['inputs'])==35 and capture['native_off_flags']==102
            for item in capture['inputs'].values():
                data=member(item['hosted_path']);assert len(data)==item['bytes'] and digest(data)==item['sha256']
            parent=member('parent865.spice').decode();original=member('source/parent865.spice').decode()
            macro=member('pfd-physical-source/wire/pfd235-wire01.spice').decode()
            import importlib.util
            generator=ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py'
            spec=importlib.util.spec_from_file_location('physical_pfd_source_generator',generator)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            ref=module.profile_devices({n:(ROOT/'hw/soc/analog/pcie'/n).read_text() for n in module.SOURCES},profile.removesuffix('_rc'))
            expected,proof=pfd_physical_parent(original,macro,ref,profile)
            assert parent==expected and proof==capture['pfd_replacement']
            assert digest(parent.encode())==capture['parent_sha256']
            bench=member('source/bench.cir').decode()
            assert digest(bench.encode())==capture['source_deck_sha256']=='8d1ace49e8c2abe21be67433b1b5714f7a468790358e4ef33d4ef038b93944af'
            circuit=member('circuit.cir').decode()
            roots=set(re.findall(r'(/[^"\s]+/cloud-pll-snapshot)/models/models',circuit));assert len(roots)==1
            base=roots.pop();body,control=bench.split('.control\n');setup=control.split('\nop\n',1)[0]
            body=body.replace(MODEL_ROOT,base+'/models/models').replace('.tran 3.125e-13 1e-06 0 3.125e-13','.tran 3.125e-13 5e-08 0 3.125e-13')
            setup=setup.replace(OSDI_ROOT+'/r3_cmc.osdi',base+'/models/r3_cmc.osdi')
            for n in ('psp103.osdi','psp103_nqs.osdi'):setup=setup.replace(OSDI_ROOT+'/'+n,base+'/frontend/'+n)
            original_save=next(l for l in setup.splitlines() if l.startswith('save '))
            vectors=original_save[5:].split();assert len(vectors)==24
            vectors += [n for n in proof['physical_terminal_voltage_probes'] if n not in vectors]
            assert vectors==capture['vectors']
            setup=setup.replace(original_save,'save '+' '.join(vectors))
            assert circuit=='* '+body+'.control\n'+setup+'\n.endc\n.end\n'
            assert digest(circuit.encode())==capture['relocated_deck_sha256']
            assert member('spinit')==b'set num_threads=1\n'
            assert member('candidate.cir')==b'NSSOC source-bound PFD candidate50ns\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun candidate.raw\nquit\n.endc\n.end\n'
            runs=capture['native_runs'];assert len(runs)==1 and runs[0]['script']=='candidate.cir'
            assert runs[0]['returncode']==0 and not runs[0]['diagnostics']
            assert digest(member('candidate.cir.log'))==runs[0]['log_sha256']
            op=zero_source_operating_point(member('op.raw'),vectors)
            assert op==capture['zero_source_operating_point']
            raw=member('candidate.raw')
        packed.unlink()
        meta_capture=capture['captures']['candidate.raw']
        assert len(raw)==meta_capture['bytes'] and digest(raw)==meta_capture['sha256']
        names,values,meta=decode_prefix(raw)
        assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
        assert all(meta_capture[k]==v for k,v in meta.items())
        assert set(names)=={'time',*vectors} and len(names)==len(vectors)+1
        assert len(values)>150000 and abs(values[-1,0]-50e-9)<1e-15
        assert np.max(np.diff(values[:,0]))<=3.125e-13*1.00001
        diagnosis=pfd_terminal_diagnosis(parent,names,values)
        columns={n:values[:,i] for i,n in enumerate(names)};t=columns['time']
        clear=columns[proof['clearb_vector']];events={}
        for n in ('v(reference)','v(fb)'):
            edges=rising(t,columns[n],1.25)
            events[n]=[dict(time_s=float(e),clearb_v=float(np.interp(e,t,clear)),
                reset_asserted_at_1p25_v=bool(np.interp(e,t,clear)<1.25)) for e in edges if e>12e-9]
        assert events==capture['clock_events'],'Captured reset-mask summary disagrees with actual waveform'
        for n in vectors:
            assert float(columns[n].min())==capture['signals'][n]['minimum']
            assert float(columns[n].max())==capture['signals'][n]['maximum']
        result.update(status='COMPLETE_SOURCE_BOUND_PFD235_TERMINAL_REVIEW_NOT_SAFETY_OR_PHY_ACCEPTANCE',
            source_parent_sha256=digest(parent.encode()),source_macro_sha256=digest(macro.encode()),
            raw_sha256=digest(raw),capture=meta,diagnosis=diagnosis,
            source_clock_events=capture['clock_events'],source_signals=capture['signals'],
            source_fixture_scope=proof['scope'])
    except BaseException as error:
        result.update(status='FAILED_PHYSICAL_PFD_NATIVE50_REVIEW',error=repr(error));save();raise
    save();print(result['status'],flush=True)


def pfd_physical_parent(parent, macro, reference, profile='aoi4_rc'):
    """Flatten exact new physical PFD model into an unchanged parent test fixture."""
    from build_pcie_local_vco_hybrid_v6 import statements
    from collections import Counter
    assert digest(parent.encode())=='b7c2b8f7328c14ff15a5798c7aaec0629104ea7ec9252d2594d3dd9db168ff48'
    assert profile in ('aoi4_rc','aoi4_d2_rc')
    macro_hash,expected_r,expected_c={
        'aoi4_rc':('4231a31db0b6e39bad5ba4266159a56ed3e780d8508c6bcdbb9e74cb43203f38',716,1178),
        'aoi4_d2_rc':('a0ace2729326fd774bb40e8c60bcb7a817cada4036308a9b6bb0a4ebf347248c',715,1177)}[profile]
    assert digest(macro.encode())==macro_hash
    rows=statements(macro);ports=rows[0][2:]
    assert rows[0][:2]==['.subckt','nssoc_pfd235_wire_v1']
    assert ports==['sub','vdd','ref','vss','up','fb','down','reset','wire_cref']
    assert rows[-1]==['.ends','nssoc_pfd235_wire_v1']
    mapping={p:'a_pfd_'+p for p in ports if p!='wire_cref'};mapping['wire_cref']='wire_cref'
    def node(n):
        if n not in mapping:mapping[n]='xpfd.'+n.lower()
        return mapping[n]
    replacement=[];devices=[];count=Counter();ids=set()
    for w in rows[1:-1]:
        kind=w[0][0].lower();assert kind in 'xrc' and w[0].lower() not in ids;ids.add(w[0].lower())
        if kind=='x':
            model_at=5 if len(w)>5 and w[5] in ('sg13_hv_nmos','sg13_hv_pmos') else 3
            model=w[model_at];assert model in ('sg13_hv_nmos','sg13_hv_pmos','ntap1','ptap1')
            count[model]+=1
            assert all('=' in s for s in w[model_at+1:])
            translated=[kind.upper()+'_xpfd_'+w[0].lower(),*[node(n) for n in w[1:model_at]],*w[model_at:]]
            devices.append(dict(instance=translated[0],model=model,nodes=translated[1:model_at],source_row=w,translated_row=translated))
        else:
            assert len(w)==4;translated=[kind.upper()+'_xpfd_'+w[0].lower(),node(w[1]),node(w[2]),w[3]]
            count[kind]+=1
        replacement.append(' '.join(translated))
    assert count==Counter(sg13_hv_nmos=47,sg13_hv_pmos=47,ptap1=94,ntap1=47,r=expected_r,c=expected_c)
    assert len(mapping)==len(set(mapping.values())) and all(re.fullmatch(r'[a-zA-Z0-9_.]+',n) for n in mapping.values())
    inverse={v:k for k,v in mapping.items()}
    recovered=[]
    for original,translated in zip(rows[1:-1],replacement,strict=True):
        w=translated.split();n=5 if w[0].lower().startswith('x') and w[5] in ('sg13_hv_nmos','sg13_hv_pmos') else 3
        back=[w[0].split('_xpfd_',1)[1].upper(),*[inverse[v] for v in w[1:n]],*w[n:]]
        assert back[0]==original[0].upper() and back[1:]==original[1:],'Non-reversible native component translation'
        recovered.append(back)
    removed=Counter();kept=[]
    for line in parent.splitlines():
        words=line.lower().split()
        kind=next((k for k in 'xrc' if words and words[0].startswith(k+'_xpfd_')),None)
        if kind:removed[kind]+=1
        else:kept.append(line)
    assert removed==Counter(x=255,r=771,c=1256)
    assert not any('xpfd.' in l.lower() for l in kept)
    ends=[i for i,l in enumerate(kept) if l.lower().startswith('.ends')];assert len(ends)==1
    candidate='\n'.join(kept[:ends[0]]+replacement+kept[ends[0]:])+'\n'
    assert [l for l in candidate.splitlines() if not any(l.lower().startswith(k+'_xpfd_') for k in 'xrc')]==kept
    assert sum(l.lower().startswith('x') for l in candidate.splitlines())==845
    topology=pfd_topology_map(candidate,reference)
    assert topology['mos_count']==94 and topology['metal_resistors']==expected_r
    probes=sorted({'v(xloop.'+n.lower()+')' for d in devices for n in d['nodes']})
    clearpoints=topology['nets']['xloop.clearb']['terminals'];assert clearpoints
    clear=clearpoints[0]['vector'];assert clear in probes
    return candidate,dict(profile=profile,pfd_mos_count=94,total_native_instances=845,
        original_pfd_removed=dict(removed),native_census=dict(count),physical_pfd=True,pfd_wire_rc_present=True,
        original_parent_sha256=digest(parent.encode()),candidate_parent_sha256=digest(candidate.encode()),
        native_component_sha256=digest(macro.encode()),non_pfd_lines_sha256=digest(('\n'.join(kept)+'\n').encode()),
        reversible_terminal_and_parameter_translation=True,topology_naming=topology,
        physical_terminal_voltage_probes=probes,clearb_vector=clear,
        scope=f'Actual235device/{expected_r}R{expected_c}C standalone PFD candidate in frozen parent electrical fixture; all610other devices and non-PFD RC byte-identical. This does not recompose parent geometry or shared bulk substrate. Intrinsic body/tap models retained; distributed substrate/RF/parent physical integration and full safety/acquisition/PVT remain unqualified.')

def restore_pfd_physical_model(out, profile='aoi4_rc'):
    """Restore exact native RC composition and complete provenance from hosted review."""
    assert profile in ('aoi4_rc','aoi4_d2_rc')
    d2=profile=='aoi4_d2_rc'
    run=38615210714 if d2 else 38609444130
    archive_hash='1d3eb4cf985251b4c5eac6e451ce720b713c5758a6ed4edea28688907efeb86b' if d2 else '40f43ab7116303ab57a7431c7f2814045a4c1d35a42a1aedef2989626c9abedc'
    archive_bytes=6788161 if d2 else 6813196
    summary_hash='1df255b18e5fed6df0c3ad4470dcd0e6afd339727d9cfd2e0b4c0fbf6f23a82d' if d2 else '2f4bade844a8f5182f5cc1c4b5c75ce4c4ce753d6dbdc062c20da7548e875a82'
    macro_hash='a0ace2729326fd774bb40e8c60bcb7a817cada4036308a9b6bb0a4ebf347248c' if d2 else '4231a31db0b6e39bad5ba4266159a56ed3e780d8508c6bcdbb9e74cb43203f38'
    path=out/'pfd-physical-input.tar.gz'
    fetch(BASE+f'cloud-results-{run}-1-pll-pfd-layout/pfd94-layout-{run}-1.tar.gz',archive_hash,path)
    assert path.stat().st_size==archive_bytes
    prefix='hw/soc/out/cloud-pfd-layout/'
    names=['result.json','wire/pfd235-wire01.spice','wire/composition01.json',
        'wire/composition-controls01.json','wire/native-mutations01.json',
        'binding/devices01.json','layout/result.json']
    if d2:names.extend(['physical-source-result.json','wire/anchors01.json'])
    dest=out/'pfd-physical-source';dest.mkdir()
    with tarfile.open(path) as tar:
        for n in names:
            members=[m for m in tar.getmembers() if m.name==prefix+n]
            assert len(members)==1 and members[0].isfile()
            target=dest/n;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(tar.extractfile(members[0]).read())
    path.unlink()
    assert sha(dest/'result.json')==summary_hash
    result=json.loads((dest/'result.json').read_text())
    expected='PASS_PFD235_ACTUAL_DEVICE_WIRE_COMPOSITION_AND_FAULTS_REQUIRES_NATIVE_WAVEFORMS' if d2 else 'PASS_PFD235_SAVED_NATIVE_RC_AND_27_FAULTS_REQUIRES_NATIVE_WAVEFORMS'
    assert result['status']==expected
    assert len(result['raw_controls']['cases'])==13 and len(result['composition_controls']['actual_rejected_mutants'])==6
    composition=json.loads((dest/'wire/composition01.json').read_text())
    assert composition==result['composition'] and composition['devices']==235
    assert json.loads((dest/'wire/composition-controls01.json').read_text())==result['composition_controls']
    assert json.loads((dest/'wire/native-mutations01.json').read_text())==result['raw_controls']
    if d2:
        assert result['reset_profile']=='aoi4_d2'
        assert sha(dest/'physical-source-result.json')=='35841da91016821cb48937bc408bff5d70357b221da42b2ea36ef3cf2aa2ab20'
        physical=json.loads((dest/'physical-source-result.json').read_text())
        assert physical['status']=='PASS_PFD94_AOI4_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert json.loads((dest/'layout/result.json').read_text())==physical['layout']
        assert sha(dest/'binding/devices01.json')==composition['inputs']['/home/runner/work/nssoc/nssoc/'+prefix+'binding/devices01.json']
    else:
        for n in ('binding/devices01.json','layout/result.json'):
            key='/home/runner/work/nssoc/nssoc/'+prefix+n
            assert sha(dest/n)==result['protected_source_files'][key]
    macro=(dest/'wire/pfd235-wire01.spice').read_text()
    assert digest(macro.encode())==macro_hash
    return macro


def pfd_schematic_parent(parent, reference, profile):
    """Matched schematic-only PFD replacement; all other parent RC stays exact."""
    from decimal import Decimal
    assert profile in ('baseline_schematic','aoi4') and len(reference)==102
    unchanged=[d for d in reference if d['path'].startswith(('xloop.xup.','xloop.xdn.'))]
    assert len(unchanged)==88
    rows=reference if profile=='baseline_schematic' else unchanged+pfd_aoi_devices()
    assert len(rows)==(102 if profile=='baseline_schematic' else 94)
    aliases={p:'a_pfd_'+p for p in ('ref','fb','reset','up','down','vdd','vss','sub')}
    def node(n):
        if n in aliases:return aliases[n]
        assert n.startswith('xloop.')
        return 'pfd_candidate.'+n.removeprefix('xloop.')
    replacement=[]
    for i,d in enumerate(rows):
        assert d['model'] in ('sg13_hv_nmos','sg13_hv_pmos')
        w=d['params']['w'];l=d['params']['l'];assert w.endswith('u')
        microns=Decimal(w[:-1]);area=microns*Decimal('.34');perimeter=microns*2+Decimal('.68')
        replacement.append('X_pfd_candidate_'+str(i)+' '+' '.join(node(n) for n in d['nets'])+' '+d['model']+
            f' w={w} l={l} as={area}p ad={area}p ps={perimeter}u pd={perimeter}u rfmode=0 ng=1 m=1')
    removed={k:[] for k in ('x','r','c')};kept=[]
    for line in parent.splitlines():
        words=line.lower().split()
        kind=next((k for k in removed if words and words[0].startswith(k+'_xpfd_')),None)
        if kind:removed[kind].append(line)
        else:kept.append(line)
    assert {k:len(v) for k,v in removed.items()}=={'x':255,'r':771,'c':1256}
    assert not any('xpfd.' in l.lower() for l in kept), 'Unreplaced PFD internal reference'
    ends=[i for i,l in enumerate(kept) if l.lower().startswith('.ends')];assert len(ends)==1
    candidate='\n'.join(kept[:ends[0]]+replacement+kept[ends[0]:])+'\n'
    outside=[l for l in candidate.splitlines() if not l.startswith('X_pfd_candidate_')]
    assert outside==kept, 'Non-PFD circuit changed'
    total=sum(l.lower().startswith('x') for l in candidate.splitlines());assert total==610+len(rows)
    return candidate,dict(profile=profile,pfd_mos_count=len(rows),total_native_instances=total,
        original_pfd_removed={k:len(v) for k,v in removed.items()},
        original_parent_sha256=digest(parent.encode()),candidate_parent_sha256=digest(candidate.encode()),
        non_pfd_lines_sha256=digest(('\n'.join(kept)+'\n').encode()),
        original88_dff_devices_preserved=profile=='aoi4',candidate_device_source=rows,
        matched_baseline_required=True,physical_pfd=False,pfd_wire_rc_present=False,
        scope='Matched schematic PFD screening only. Original610other devices and all non-PFD RC/ports remain byte-identical. Original255device PFD with771R1256C replaced; local body contacts and extracted PFD RC absent in BOTH schematic profiles. No layout, safety, PEX or PHY acceptance.')


def zero_source_operating_point(raw, expected):
    """Strict one-row native operating-point reader; it has no time column."""
    end=raw.find(b'Binary:\n',0,1048576);assert end>=0
    end+=len(b'Binary:\n');header=raw[:end].decode('ascii')
    fields={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in header.splitlines() if ':' in l}
    assert fields['Flags']=='real' and fields['Plotname'].lower()=='operating point'
    table=[l.split() for l in header.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    assert int(fields['No. Points'])==1 and int(fields['No. Variables'])==len(expected)==len(table)
    assert [r[0] for r in table]==list(map(str,range(len(table))))
    names=[r[1] for r in table];assert len(set(names))==len(names) and set(names)==set(expected)
    assert all(r[2]=='voltage' for r in table) and len(raw)-end==8*len(names)
    values=np.frombuffer(raw[end:],dtype='<f8');assert np.isfinite(values).all()
    maximum=float(np.max(np.abs(values)));assert maximum<1e-9,'Nonzero startup operating point'
    return dict(maximum_abs_v=maximum,columns=names,sha256=digest(raw))


def pfd_op_controls():
    header=b'Title: OP control\nPlotname: Operating Point\nFlags: real\nNo. Variables: 2\nNo. Points: 1\nVariables:\n0 v(a) voltage\n1 v(b) voltage\nBinary:\n'
    raw=header+np.array([0.,0.],dtype='<f8').tobytes()
    assert zero_source_operating_point(raw,['v(a)','v(b)'])['maximum_abs_v']==0
    faults=[header+np.array([0.,.01],dtype='<f8').tobytes(),raw[:-1],raw+b'x',raw.replace(b'v(b)',b'v(c)'),raw.replace(b'No. Points: 1',b'No. Points: 2')]
    for bad in faults:
        try:zero_source_operating_point(bad,['v(a)','v(b)'])
        except AssertionError:continue
        raise AssertionError('Corrupt/nonzero operating point accepted')
    return dict(positive=1,negative=len(faults))


def run_pfd_candidate(executable,out,common,result,save,vectors):
    """Bounded native50ns candidate screen; no timing/lock acceptance inferred."""
    physical=result['pfd_replacement'].get('physical_pfd',False)
    text='NSSOC source-bound PFD candidate50ns\n'+common+'run candidate.raw\nquit\n.endc\n.end\n'
    (out/'candidate.cir').write_text(text)
    result.update(status='RUNNING_PHYSICAL_PFD_NATIVE50_SCREEN' if physical else 'RUNNING_SCHEMATIC_PFD_NATIVE50_SCREEN',native_budget_s=19000,
        native_stop_s=50e-9,comparison_stop_s=None,snapshot_stop_s=None,physical_pfd=physical)
    save();native_run(executable,out,'candidate.cir',time.monotonic()+19000,result,save)
    raw=(out/'candidate.raw').read_bytes();names,values,meta=decode_prefix(raw)
    assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
    assert set(names)=={'time',*vectors} and np.isfinite(values).all() and len(values)>150000
    t=values[:,0];assert t[0]==0 and abs(t[-1]-50e-9)<1e-15 and np.all(np.diff(t)>0)
    assert np.max(np.diff(t))<=3.125e-13*1.00001
    v={n:values[:,i] for i,n in enumerate(names)};stats={}
    for n,y in v.items():
        if n=='time':continue
        stats[n]=dict(minimum=float(y.min()),maximum=float(y.max()),
            rising_edges_at_1p25_v_s=rising(t,y,1.25).tolist(),falling_edges_at_1p25_v_s=rising(t,-y,-1.25).tolist())
    clear=v[result['pfd_replacement']['clearb_vector'] if physical else 'v(xloop.pfd_candidate.clearb)'];clock_events={}
    for n in ('v(reference)','v(fb)'):
        edge=rising(t,v[n],1.25);clock_events[n]=[dict(time_s=float(e),clearb_v=float(np.interp(e,t,clear)),
            reset_asserted_at_1p25_v=bool(np.interp(e,t,clear)<1.25)) for e in edge if e>12e-9]
    operating_point=zero_source_operating_point((out/'op.raw').read_bytes(),vectors)
    result.update(status='COMPLETE_PHYSICAL_PFD_NATIVE50_FIXTURE_SCREEN_NOT_LOCK_OR_PARENT_LAYOUT_ACCEPTANCE' if physical else 'COMPLETE_SCHEMATIC_PFD_NATIVE50_SCREEN_NOT_PHYSICAL_OR_LOCK_ACCEPTANCE',
        captures={'candidate.raw':dict(**meta,sha256=digest(raw),bytes=len(raw),start_s=float(t[0]),end_s=float(t[-1]))},
        zero_source_operating_point=operating_point,signals=stats,clock_events=clock_events,
        required_followup=(['Full-device electrical safety and original1us acquisition with actual PFD RC',
            'Recompose parent physical geometry and verify shared bulk/qualified substrate and RF extraction',
            'Independent PVT/timestep/CDR/jitter/full serialPHY and mainchip signoff'] if physical else ['Compare both matched baseline_schematic and aoi4 native results',
            'Generate actual PFD GDS/LEF, transistor LVS/DRC and exact new RC composition',
            'Repeat native full-device safety and original1us acquisition gates with physical candidate',
            'Independent PVT/timestep/CDR/jitter/full serialPHY and mainchip signoff']),
        acquisition_accepted=False,full_phy_accepted=False)
    save();print(result['status'],flush=True)


def recover_parent_methods(include_planes=False):
    """Recover source-bound PLL parent layout and latest native composition methods."""
    from concurrent.futures import ThreadPoolExecutor
    from verify_cloud_output_restore import pages,download
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted source recovery only'
    out=ROOT/'cloud-pll-acquisition-review';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_PLL_PARENT_METHOD_RECOVERY',full_phy_accepted=False,acquisition_accepted=False,no_new_native=True,
        scope='Source-only recovery of existing PLL parent physical composition and latest865/PBUF10 methods. Records actual archived geometry inventory; does not execute source or claim candidate parent integration.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    exact='hw/soc/out/pcie-pll753-parent-layout-20261010/'
    required={exact+'review12.py':'acce27a0b067c51bccec41d394f974744852212f408c693484bcf5e67c5b1115',
        exact+'inputs01.json':'bd31821d709d549f2d8ed25c08e9ed9e96d66f4a994bbb97aa20eac97a4d8a0e'}
    if include_planes:
        required={}
        result['scope']='Recover source-bound reset/release/rhi140/PBUF10 composition, wire-anchor metadata and original method sources. No execution or reference-plane acceptance.'
        result['include_reference_planes']=True
    try:
        releases=pages('repos/Melihakbulut221/nssoc/releases?per_page=100');assets=[]
        for release in releases:
            if release['tag_name'].startswith('cloud-migration-20261012-'):
                assets+=pages(f'repos/Melihakbulut221/nssoc/releases/{release["id"]}/assets?per_page=100')
        manifests=[a for a in assets if a['name'].startswith('batch-') and a['name'].endswith('.manifest.json')]
        assert manifests,'No migration manifests'
        def inspect(asset):
            path=out/(str(asset['id'])+'.manifest.json');h=download(asset,path)
            manifest=json.loads(path.read_text());path.unlink();selected=[];inventory=[]
            for record in manifest['records']:
                name=record['path'];parts=Path(name).parts
                if len(parts)<5 or parts[:3]!=('hw','soc','out'):continue
                family=parts[3]
                selected_family=(any(x in family for x in ('reset','release','rhi140','parent865','pbuf10')) if include_planes else (name.startswith(exact) or 'parent865' in family or 'pbuf10' in family))
                if not selected_family:continue
                leaf='/'.join(parts[4:])
                if name.endswith(('.gds','.lef','.spice','.cir','.py')) or leaf.endswith('result.json') or leaf=='inputs01.json':
                    inventory.append(dict(path=name,bytes=record['bytes'],sha256=record['sha256']))
                if '/' not in leaf and (leaf.endswith('.py') or leaf.startswith('inputs') and leaf.endswith('.json')):
                    selected.append(record)
                elif include_planes and record['bytes']<2*1024**2 and (leaf.endswith('/composition.json') or Path(leaf).name.startswith('anchors') and leaf.endswith('.json') or leaf.endswith('/result.json') and any(x in leaf for x in ('wire','model','layout','parent','binding'))):
                    selected.append(record)
                elif leaf.startswith('layout') and leaf.endswith('/result.json'):
                    selected.append(record)
            return dict(manifest_url=asset['browser_download_url'],manifest_sha256=h,encoding=manifest['encoding'],
                parts=manifest['parts'],selected=selected,physical_source_inventory=inventory) if selected or inventory else None
        with ThreadPoolExecutor(max_workers=8) as pool:matched=[x for x in pool.map(inspect,manifests) if x]
        result['searched_manifest_count']=len(manifests);result['matched_manifests']=matched;save()
        sources={}
        for bundle in matched:
            if not bundle['selected']:continue
            assert bundle['encoding']=='tar-gzip' and len(bundle['parts'])==1
            part=bundle['parts'][0];packed=out/'source.tar.gz';fetch(part['url'],part['sha256'],packed)
            assert packed.stat().st_size==part['bytes']
            with tarfile.open(packed) as tar:
                for record in bundle['selected']:
                    path=record['path'];assert path not in sources and record['bytes']<2*1024**2
                    members=[m for m in tar.getmembers() if m.name==path];assert len(members)==1
                    member=members[0];assert member.isfile() or member.islnk()
                    if member.islnk():
                        assert not member.linkname.startswith('/') and '..' not in Path(member.linkname).parts
                    content=tar.extractfile(member).read()
                    assert len(content)==record['bytes'] and digest(content)==record['sha256']
                    if path in required:assert digest(content)==required[path]
                    sources[path]=dict(bytes=len(content),sha256=digest(content),text=content.decode(),
                        manifest_url=bundle['manifest_url'],archive_url=part['url'],archive_sha256=part['sha256'])
            packed.unlink();result['recovered_sources']=sources;save()
        assert set(required)<=set(sources),('Required original methods missing',sorted(set(required)-set(sources)))
        if include_planes:
            assert any(p.endswith('/composition.json') for p in sources),'No original composition recovered'
            assert any('reset' in p or 'release' in p for p in sources),'No original release methods recovered'
        result.update(status='COMPLETE_SOURCE_BOUND_PLL_PARENT_AND_865_METHOD_RECOVERY',required_source_hashes_verified=required)
        save();print(result['status'],len(sources),flush=True)
    except BaseException as error:
        result.update(status='FAILED_PLL_PARENT_METHOD_RECOVERY',error=repr(error));save();raise



def recover_pfd_methods():
    """Recover archived original PFD extraction/binding sources on GitHub only."""
    from concurrent.futures import ThreadPoolExecutor
    from verify_cloud_output_restore import pages,download
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted source recovery only'
    out=ROOT/'cloud-pll-acquisition-review';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_PFD_METHOD_RECOVERY',full_phy_accepted=False,acquisition_accepted=False,no_new_native=True,
        scope='Source-only recovery of original PFD255 native terminal binding and wire extraction methods. Does not execute recovered code, change layout or qualify RC.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    prefixes=('hw/soc/out/pcie-pfd255-local-wire-20261009/','hw/soc/out/pcie-pfd255-local-binding-20261009/')
    required={prefixes[0]+'audit-rc01.py':'2d1b07a9960e3e246c7046887886bd899e7e3571a414f93d2ad39b88d1f851cb',
        prefixes[0]+'mutations02.py':'1f3e5604b48112e1e7848b3d634c5012377d3c8e85ffe0d43ac4c5f802379407',
        prefixes[0]+'check-compose01.py':'f8123bf05b35db89600a56ae010b29e388caf5d462efee2b88b367d5d3cc7bf4'}
    try:
        releases=pages('repos/Melihakbulut221/nssoc/releases?per_page=100');assets=[]
        for release in releases:
            if release['tag_name'].startswith('cloud-migration-20261012-'):
                assets+=pages(f'repos/Melihakbulut221/nssoc/releases/{release["id"]}/assets?per_page=100')
        manifests=[a for a in assets if a['name'].startswith('batch-') and a['name'].endswith('.manifest.json')]
        assert manifests,'No migration manifests'
        def inspect(asset):
            path=out/(str(asset['id'])+'.manifest.json');h=download(asset,path)
            manifest=json.loads(path.read_text());path.unlink();selected=[]
            for record in manifest['records']:
                for prefix in prefixes:
                    if record['path'].startswith(prefix):
                        leaf=record['path'].removeprefix(prefix)
                        if '/' not in leaf and (leaf.endswith('.py') or leaf in ('anchors01.json','devices01.json')):selected.append(record)
            return dict(manifest_url=asset['browser_download_url'],manifest_sha256=h,encoding=manifest['encoding'],parts=manifest['parts'],selected=selected) if selected else None
        with ThreadPoolExecutor(max_workers=8) as pool:matched=[x for x in pool.map(inspect,manifests) if x]
        result['searched_manifest_count']=len(manifests);result['matched_manifests']=matched;save()
        sources={}
        for bundle in matched:
            assert bundle['encoding']=='tar-gzip' and len(bundle['parts'])==1
            part=bundle['parts'][0];packed=out/'source.tar.gz';fetch(part['url'],part['sha256'],packed)
            assert packed.stat().st_size==part['bytes']
            with tarfile.open(packed) as tar:
                for record in bundle['selected']:
                    path=record['path'];assert path not in sources and record['bytes']<2*1024**2
                    members=[m for m in tar.getmembers() if m.name==path];assert len(members)==1
                    member=members[0];assert member.isfile() or member.islnk()
                    if member.islnk():
                        assert not member.linkname.startswith('/') and '..' not in Path(member.linkname).parts
                    content=tar.extractfile(member).read()
                    assert len(content)==record['bytes'] and digest(content)==record['sha256']
                    if path in required:assert digest(content)==required[path]
                    sources[path]=dict(bytes=len(content),sha256=digest(content),text=content.decode(),
                        manifest_url=bundle['manifest_url'],archive_url=part['url'],archive_sha256=part['sha256'])
            packed.unlink();result['recovered_sources']=sources;save()
        assert set(required)<=set(sources),('Required original methods missing',sorted(set(required)-set(sources)))
        result.update(status='COMPLETE_SOURCE_BOUND_PFD_BINDING_AND_WIRE_METHOD_RECOVERY',required_source_hashes_verified=required)
        save();print(result['status'],len(sources),flush=True)
    except BaseException as error:
        result.update(status='FAILED_PFD_METHOD_RECOVERY',error=repr(error));save();raise



def run_pfd_rc(reset_profile='aoi4'):
    """Bind actual235-device geometry and extract new wires on a hosted runner."""
    import shutil
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted extraction only'
    assert reset_profile in ('aoi4','aoi4_d2')
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD235_GEOMETRY_BOUND_RC',reset_profile=reset_profile,adopted=False,
        full_phy_accepted=False,qualified_pex=False,
        scope='Actual AOI94 candidate235-device binding, native terminal ownership, new distributed metal RC and raw corruption controls. No spatial substrate/RF qualification, waveform, acquisition, mainchip or PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,name):
        log=out/(name+'.log')
        with log.open('wb') as stream:code=subprocess.call([str(x) for x in cmd],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(name=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert code==0,(name,'failed')
    def restore(receipt,dest,label):
        packed=out/(label+'.tar.gz')
        fetch(receipt['url'],receipt['sha256'],packed)
        if 'bytes' in receipt:assert packed.stat().st_size==receipt['bytes']
        with tarfile.open(packed) as tar:tar.extractall(dest,filter='data')
        packed.unlink()
    def manifest(directory):
        m=json.loads((directory/'manifest.json').read_text())
        assert all(sha(directory/n)==v['sha256'] for n,v in m['files'].items())
        return m
    save()
    try:
        physical_receipt=dict(url=BASE+'cloud-results-38604234902-1-pll-pfd-layout/pfd94-layout-38604234902-1.tar.gz',
            sha256='869b6c076124a4773bf9a047309d49f41d0465db18456603d5c7e7e837d9b953',bytes=639953)
        if reset_profile=='aoi4_d2':
            physical_receipt=dict(url=BASE+'cloud-results-38614342619-1-pll-pfd-layout/pfd94-layout-38614342619-1.tar.gz',
                sha256='9e3de73d250ba223b093f44c55e91c1e7327f8487c8d185b96f2350104e45210',bytes=654630)
        restore(physical_receipt,ROOT,'physical-input')
        physical=json.loads((out/'result.json').read_text())
        assert physical['status']=='PASS_PFD94_AOI4_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        (out/'physical-source-result.json').write_text(json.dumps(physical,indent=2)+'\n')
        frozen={str(p):sha(p) for sub in ('layout','physical') for p in (out/sub).rglob('*') if p.is_file()}
        generated=json.loads((out/'layout/result.json').read_text())
        assert generated['reset_profile']==reset_profile and len(generated['core_devices'])==94
        expected_top='nssoc_pfd94_aoi4_d2_layout_v1' if reset_profile=='aoi4_d2' else 'nssoc_pfd94_aoi4_layout_v1'
        expected_gds='0451b81b8f73a8f1c4e2923e5f50d26cf3c09ad2c3a77ebd0f08acc864e1e08a' if reset_profile=='aoi4_d2' else '5eba584933e1308a1266e6bb94f8a4f3c54b545b03a7ee5010884875c16accf6'
        assert generated['top']==expected_top
        gds=out/'layout'/(expected_top+'.gds')
        assert sha(gds)==expected_gds
        assert all(sha(out/'layout'/n)==v for n,v in generated['outputs'].items())
        result['physical_source']=physical_receipt;save()
        layout_spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        restore(layout_spec['receipt'],ROOT,'pdk-input');pdk_manifest=manifest(ROOT)
        assert len(pdk_manifest['files'])==197
        electrical=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
        models=out/'model-inputs';models.mkdir()
        restore(electrical['receipt'],models,'models-input');model_manifest=manifest(models)
        shutil.copytree(models/'models',ROOT/'pdk/libs.tech/ngspice/models')
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
        rt=out/'magic-cloud';rt.mkdir();restore(runtime['receipt'],rt,'magic-input');rt_manifest=manifest(rt)
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        methods_path=out/'recovered-methods.json'
        fetch(BASE+'cloud-results-38606020769-1-pll-acquisition-review/result.json',
            '61c7bcbd29f8defec1a8565b0f0e1e110591474f9a5d42e5d077c33df543acf1',methods_path)
        assert methods_path.stat().st_size==640488
        recovered=json.loads(methods_path.read_text())['recovered_sources']
        originals=out/'frozen-methods';originals.mkdir()
        binding=out/'binding';binding.mkdir();wire=out/'wire';wire.mkdir()
        required={'export01.py','build_devices01.py','check_binding01.py','binding-controls01.py',
            'probe01.py','locate01.py','anchors01.py','run-rc01.py','audit-rc01.py',
            'mutations02.py','compose01.py','check-compose01.py'}
        seen=set();adaptations={}
        for path,item in recovered.items():
            name=Path(path).name
            if name not in required:continue
            assert name not in seen;seen.add(name)
            data=item['text'].encode();assert len(data)==item['bytes'] and digest(data)==item['sha256']
            (originals/name).write_bytes(data);source=data.decode();changes=[]
            def replace(before,after,required=False):
                nonlocal source
                count=source.count(before)
                if required:assert count>0,(name,before)
                if count:source=source.replace(before,after);changes.append(dict(before=before,after=after,count=count))
            for before,after in [
                ('hw/soc/out/pcie-pfd102-local-layout-20261009','hw/soc/out/cloud-pfd-layout'),
                ('hw/soc/out/pcie-pfd255-local-binding-20261009','hw/soc/out/cloud-pfd-layout/binding'),
                ('native-controls01/','physical/'),('layout01/','layout/'),
                ('nssoc_pfd102_layout_v1',expected_top),
                ("Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')","R/'pdk'"),
                ("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'magic-cloud/runtime/lib'"),
                ("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'magic-cloud/tech'"),
                ('7c461d7d5ec62c05ca9338a13de9a7442ffc0ad56e77080d2c5977875b52cca4',sha(gds)),
                ('NATIVE255','NATIVE235'),('Native255','Native235'),('native255','native235'),
                ('pfd255','pfd235'),('_255_','_235_'),
                ("'sg13_hv_nmos':51","'sg13_hv_nmos':47"),("'sg13_hv_pmos':51","'sg13_hv_pmos':47"),
                ("'ptap1':102","'ptap1':94"),("'ntap1':51","'ntap1':47"),
                ('"sg13_hv_nmos": 51','"sg13_hv_nmos": 47'),('"sg13_hv_pmos": 51','"sg13_hv_pmos": 47'),
                ('"ptap1": 102','"ptap1": 94'),('"ntap1": 51','"ntap1": 47'),
                ('sg13_hv_nmos=51','sg13_hv_nmos=47'),('sg13_hv_pmos=51','sg13_hv_pmos=47'),
                ('ptap1=102','ptap1=94'),('ntap1=51','ntap1=47'),
                ('"contacts": 153','"contacts": 141'),
                ('714','658'),('459','423'),('467','431'),
            ]:replace(before,after)
            for before,after in [('255','235'),('256','236'),('257','237')]:
                source,count=re.subn(r'\b'+before+r'\b',after,source)
                if count:changes.append(dict(before='integer'+before,after=after,count=count))
            if name=='audit-rc01.py':
                replace("B.parent/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'",
                    "Path.cwd()/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'",True)
                replace(" p=Path(p);a=", """ geometry=json.loads((B/'native01/result.json').read_text())
 require(geometry['status']=='PASS_GEOMETRIC_PFD_WIRE_COMPONENT_BINDING_NO_RC','Unverified physical conductor graph')
 for filename,record in geometry['inputs'].items():require(pin(filename)==record,'Physical conductor input changed')
 component_ids={r['component'] for r in geometry['wire_components']}
 component_count=len(component_ids)
 require(component_count==geometry['wire_component_count'] and component_count>8,'Actual conductor census changed')
 require(geometry['native_device_count']==235 and geometry['native_terminal_count']==658,'Native geometry device census')
 require(len(geometry['wire_components'])==len({r['native_cluster'] for r in geometry['wire_components']}),'Nonunique conductor ownership')
 p=Path(p);a=""",True)
                replace("['58']","[str(component_count+1)]",True)
                replace("['57']","[str(component_count)]",True)
                replace('set(range(1,58))','component_ids',True)
                replace('58**2','(component_count+1)**2',True)
                source,n=re.subn(r'\b57\b','component_count',source)
                assert n>0;changes.append(dict(before='integer57',after='actual geometry component_count',count=n))
            if name=='mutations02.py':
                # Select an actual two-anchor bridge. Removing it produces
                # two isolated real terminals, so the independent open gate
                # must reject without relying on edge-record comparison.
                replace('cases=[\n',"""resistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\\d+ \\S+ \\S+ \\S+',line)]
components={n:set(c) for c in nx.connected_components(graph) for n in c}
drop_index,drop_fields=next((i,f) for i,f in resistor_rows if len(components[f[1]])==2 and components[f[1]]<=set(anchor))
assert graph.number_of_edges(drop_fields[1],drop_fields[2])==1
dropped='\\n'.join(rows[:drop_index]+rows[drop_index+1:])+'\\n'
kept=m.rawparser.parse_spice(dropped);kg=nx.Graph();kg.add_nodes_from(anchor);kg.add_edges_from((x,y) for x,y,v in kept['resistors'])
assert len(kept['resistors'])==len(parsed['resistors'])-1
assert kg.degree(drop_fields[1])==kg.degree(drop_fields[2])==0
cases=[
""",True)
                replace("re.sub(r'^R\\d+ .*\\n','',text,count=1,flags=re.M)","dropped",True)
                replace("'RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',254","'RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',234",True)
            if name=='compose01.py':
                replace("and len(raw)==2029","and len(raw)==2+audit['actual_exported_resistors']+audit['actual_exported_capacitors']",True)
                replace("raw=core.statements(", "audit=json.loads((B/'audit.json').read_text());assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'\nraw=core.statements(",True)
                replace("SOURCE_ONLY_NATIVE235_WITH_771R_1256C","SOURCE_ONLY_NATIVE235_WITH_ACTUAL_DISTRIBUTED_RC",True)
                replace('wire_resistors=771,wire_capacitors=1256',
                    "wire_resistors=audit['actual_exported_resistors'],wire_capacitors=audit['actual_exported_capacitors']",True)
            if name=='check-compose01.py':
                replace('len(wires)==2027 and len(tokens)==2284',
                    'len(wires)==len(raw)-2 and len(tokens)==235+len(raw)',True)
                replace('Complete255 devices and771R1256C','Complete235 devices and every actual native wire record',True)
                replace('PASS_NATIVE235_AND_ALL2027_WIRE_RECORDS_WITH_EXPLICIT_REFERENCES',
                    'PASS_NATIVE235_AND_ALL_NATIVE_WIRE_RECORDS_WITH_EXPLICIT_REFERENCES',True)
                # Select actual device classes instead of inherited native IDs.
                replace("rows=core.statements(text)","""rows=core.statements(text)
mos_index=next(i for i,r in enumerate(rows) if len(r)>5 and r[5]=='sg13_hv_nmos' and r[4]!='sub')
tap_name=next(r[0] for r in rows if len(r)>3 and r[3]=='ptap1')
resistor_name=next(r[0] for r in rows if r[0].startswith('R'))""",True)
                replace("rs[2]","rs[mos_index]",True)
                replace("r[0]!='XD0103'","r[0]!=tap_name",True)
                replace("r[0]!='R0'","r[0]!=resistor_name",True)
            assert '/home/hasanmelih/' not in source and '/dev/shm/' not in source
            # Hosted syntax validation before executing any adapted method.
            ast.parse(source)
            target=(binding if 'local-binding' in path else wire)/name
            target.write_text(source);adaptations[name]=dict(original_sha256=item['sha256'],
                adapted_sha256=sha(target),changes=changes)
        assert seen==required
        result['method_adaptations']=adaptations
        result['sources']=dict(model_source=electrical['receipt'],runtime_source=runtime,
            pdk_source=layout_spec['receipt'],raw_parser=rawspec,recovered_source_sha256=sha(methods_path))
        save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==layout_spec['runtime_sha256']
        for mode,path in [('app',binding/'export01.py'),('python',binding/'build_devices01.py'),
                          ('python',binding/'binding-controls01.py'),('app',wire/'probe01.py'),
                          ('app',wire/'locate01.py'),('app',wire/'anchors01.py'),
                          ('python',wire/'run-rc01.py')]:
            run([app,'python',path] if mode=='app' else [sys.executable,path],path.stem)
        capture=json.loads((wire/'rc01/result.json').read_text());result['capture']=capture
        assert capture['returncode']==0 and capture['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        run([sys.executable,wire/'audit-rc01.py',wire/'rc01',wire/'anchors01.json',wire/'audit.json'],'raw-rc-audit')
        result['audit']=json.loads((wire/'audit.json').read_text());save()
        assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable,wire/'mutations02.py'],'raw-rc-controls')
        run([sys.executable,wire/'compose01.py'],'compose-native-devices-and-wires')
        run([sys.executable,wire/'check-compose01.py'],'composition-controls')
        for name,path in [('binding_controls',binding/'binding-controls01/result.json'),
                          ('raw_controls',wire/'native-mutations01.json'),
                          ('composition',wire/'composition01.json'),
                          ('composition_controls',wire/'composition-controls01.json')]:
            result[name]=json.loads(path.read_text())
        assert result['binding_controls']['status']=='PASS_NATIVE235_BINDING_AND_EIGHT_FAULTS'
        assert result['raw_controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(result['composition_controls']['actual_rejected_mutants'])==6
        assert result['composition']['wire_resistors']==result['audit']['actual_exported_resistors']
        assert result['composition']['wire_capacitors']==result['audit']['actual_exported_capacitors']
        assert all(sha(Path(n))==v for n,v in frozen.items())
        manifest(ROOT);manifest(models);manifest(rt)
        result['status']='PASS_PFD235_ACTUAL_DEVICE_WIRE_COMPOSITION_AND_FAULTS_REQUIRES_NATIVE_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAILED_PFD235_GEOMETRY_BOUND_RC',error=repr(error))
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-16000:] for p in out.glob('*.log') if p.is_file()}
        save();raise
    save();print(result['status'],flush=True)



def review_pfd_rc():
    """Review exact saved extraction; never rerun Magic or change raw results."""
    import shutil
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted extraction review only'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_SAVED_PFD235_RC_REVIEW',full_phy_accepted=False,
        qualified_pex=False,adopted=False,no_native_extraction_rerun=True,source_run=38608812756,
        scope='Exact saved actual235-device/716R1178C extraction, repaired actual bridge-open control and independent composition. No RF/substrate qualification, electrical acquisition or full PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,name):
        log=out/(name+'.log')
        with log.open('wb') as stream:code=subprocess.call([str(x) for x in cmd],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(name=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert code==0,(name,'failed')
    def restore(receipt,dest,label):
        packed=out/(label+'.tar.gz');fetch(receipt['url'],receipt['sha256'],packed)
        if 'bytes' in receipt:assert packed.stat().st_size==receipt['bytes']
        with tarfile.open(packed) as tar:tar.extractall(dest,filter='data')
        packed.unlink()
    def validate_inputs(record):
        for path,expected in record['inputs'].items():
            p=Path(path);assert p.is_relative_to(ROOT),('Outside exact restored workspace',path)
            assert sha(p)==(expected['sha256'] if isinstance(expected,dict) else expected),path
            if isinstance(expected,dict) and 'bytes' in expected:assert p.stat().st_size==expected['bytes']
    save()
    try:
        receipt=dict(url=BASE+'cloud-results-38608812756-1-pll-pfd-layout/pfd94-layout-38608812756-1.tar.gz',
            sha256='ddc9539a72d8b9f40f3c544c4e2ad09536c0440062944b28d582d4a17a578704',bytes=6604094)
        restore(receipt,ROOT,'saved-extraction')
        prior=json.loads((out/'result.json').read_text())
        assert prior['status']=='FAILED_PFD235_GEOMETRY_BOUND_RC' and prior['error']=="AssertionError(('raw-rc-controls', 'failed'))"
        (out/'saved-rc-source-result.json').write_text(json.dumps(prior,indent=2)+'\n')
        result['source_archive']=receipt;result['source_audit']=prior['audit']
        assert prior['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert prior['audit']['actual_exported_resistors']==716 and prior['audit']['actual_exported_capacitors']==1178
        save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        restore(spec['receipt'],ROOT,'pdk-input')
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==r['sha256'] for n,r in manifest['files'].items())
        models=out/'model-inputs';manifest=json.loads((models/'manifest.json').read_text())
        assert all(sha(models/n)==r['sha256'] for n,r in manifest['files'].items())
        shutil.copytree(models/'models',ROOT/'pdk/libs.tech/ngspice/models')
        rt=out/'magic-cloud';manifest=json.loads((rt/'manifest.json').read_text())
        assert all(sha(rt/n)==r['sha256'] for n,r in manifest['files'].items())
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        wire=out/'wire';binding=out/'binding'
        records=[binding/'devices01.json',binding/'binding01.json',binding/'binding-controls01/result.json',
            wire/'native01/result.json',wire/'device-locations01.json',wire/'anchors01.json',
            wire/'rc01/result.json',wire/'audit.json']
        for p in records:validate_inputs(json.loads(p.read_text()))
        for p in [wire/'rc01/result.json',wire/'native01/result.json']:
            r=json.loads(p.read_text())
            for name,expected in r['outputs'].items():
                q=p.parent/name;assert sha(q)==expected['sha256'] and q.stat().st_size==expected['bytes']
        binding_controls=json.loads((binding/'binding-controls01/result.json').read_text())
        assert binding_controls['status']=='PASS_NATIVE235_BINDING_AND_EIGHT_FAULTS' and len(binding_controls['faults'])==8
        protected={str(p):sha(p) for sub in ('layout','physical','binding','wire/native01','wire/rc01')
            for p in (out/sub).rglob('*') if p.is_file()}
        protected.update({str(p):sha(p) for p in [wire/'anchors01.json',wire/'device-locations01.json',wire/'audit-rc01.py']})
        original=(out/'frozen-methods/mutations02.py').read_text()
        assert digest(original.encode())=='1f3e5604b48112e1e7848b3d634c5012377d3c8e85ffe0d43ac4c5f802379407'
        selector="""resistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\\d+ \\S+ \\S+ \\S+',line)]
components={n:set(c) for c in nx.connected_components(graph) for n in c}
drop_index,drop_fields=next((i,f) for i,f in resistor_rows if len(components[f[1]])==2 and components[f[1]]<=set(anchor))
assert graph.number_of_edges(drop_fields[1],drop_fields[2])==1
dropped='\\n'.join(rows[:drop_index]+rows[drop_index+1:])+'\\n'
kept=m.rawparser.parse_spice(dropped);kg=nx.Graph();kg.add_nodes_from(anchor);kg.add_edges_from((x,y) for x,y,v in kept['resistors'])
assert len(kept['resistors'])==len(parsed['resistors'])-1
assert kg.degree(drop_fields[1])==kg.degree(drop_fields[2])==0
"""
        changes=[
            ('cases=[\n',selector+'cases=[\n'),
            ("re.sub(r'^R\\d+ .*\\n','',text,count=1,flags=re.M)",'dropped'),
            ("'RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',254","'RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',234")]
        revised=original
        for before,after in changes:
            assert revised.count(before)==1;revised=revised.replace(before,after)
        ast.parse(revised)
        old=wire/'mutations02.py';(wire/'mutations-source-failed.py').write_bytes(old.read_bytes());old.write_text(revised)
        result['control_adaptation']=dict(original_sha256=digest(original.encode()),
            revised_sha256=sha(old),changes=[dict(before=a,after=b) for a,b in changes],
            expected_open_rejection='Physical wire R graph open or incomplete',
            source_resistors_or_caps_changed=False)
        save()
        run([sys.executable,binding/'check_binding01.py','--devices',binding/'devices01.json',
            '--native',out/'physical/lvs/extracted.cir','--compact',binding/'pfd235-compact01.spice',
            '--technology',ROOT/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json',
            '--out',out/'binding-readback.json'],'exact-binding-readback')
        run([sys.executable,wire/'audit-rc01.py',wire/'rc01',wire/'anchors01.json',wire/'review-audit.json'],'exact-raw-readback')
        result['audit']=json.loads((wire/'review-audit.json').read_text());assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable,wire/'mutations02.py'],'corrected-raw-fault-controls')
        run([sys.executable,wire/'compose01.py'],'compose-native-devices-and-wires')
        run([sys.executable,wire/'check-compose01.py'],'composition-controls')
        result['binding_controls']=binding_controls
        for name,path in [('raw_controls',wire/'native-mutations01.json'),
                          ('composition',wire/'composition01.json'),
                          ('composition_controls',wire/'composition-controls01.json')]:
            result[name]=json.loads(path.read_text())
        assert result['raw_controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(result['raw_controls']['cases'])==13
        assert len(result['composition_controls']['actual_rejected_mutants'])==6
        assert result['composition']['wire_resistors']==716 and result['composition']['wire_capacitors']==1178
        assert all(sha(Path(n))==v for n,v in protected.items())
        result['protected_source_files']=protected
        result['status']='PASS_PFD235_SAVED_NATIVE_RC_AND_27_FAULTS_REQUIRES_NATIVE_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAILED_SAVED_PFD235_RC_REVIEW',error=repr(error))
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-16000:] for p in out.glob('*.log') if p.is_file()}
        save();raise
    save();print(result['status'],flush=True)


def compose_pfd_actual_parent():
    """Compose only source-bound actual845 geometry and separately prove its intrinsic graph."""
    import copy
    import importlib.util
    import networkx as nx
    from collections import Counter
    from build_pcie_local_vco_hybrid_v6 import statements, number
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_ACTUAL845_PARENT_COMPOSITION',source_run=38627542372,
        qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False,
        parent_electrical_accepted=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def require(ok,why):
        if not ok:raise ValueError(why)
    save()
    try:
        packed=out/'parent-rc-source.tar.gz'
        fetch(BASE+'cloud-results-38627542372-1-pll-pfd-layout/pfd94-layout-38627542372-1.tar.gz',
            'bd8cea7f0532921ee4566d6b8b8e7dc4ebe2b132b62e3ea088b8a68d9839ff09',packed)
        require(packed.stat().st_size==10655669,'Parent RC capsule size')
        prefix='hw/soc/out/cloud-pfd-layout/'
        with tarfile.open(packed) as tar:
            names=set()
            for entry in tar.getmembers():
                if not entry.isfile():continue
                require(entry.name.startswith(prefix),'Unexpected archive root')
                rel=entry.name[len(prefix):]
                require(not Path(rel).is_absolute() and '..' not in Path(rel).parts and rel not in names,'Unsafe/duplicate archive path')
                names.add(rel)
                if rel=='result.json':rel='parent-rc-source-result.json'
                target=out/rel;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(tar.extractfile(entry).read())
        packed.unlink()
        require(sha(out/'parent-rc-source-result.json')=='908ab5606c70576588cc74fb376cc9daa67b34bf4dd0ea10ca9c2cc519fbb0dc','Parent RC summary hash')
        source=json.loads((out/'parent-rc-source-result.json').read_text())
        require(source['status']=='PASS_ACTUAL845_PARENT_WIRE_RC_AND_EIGHT_FAULTS_NOT_COMPOSITION_OR_ELECTRICAL_ACCEPTANCE','Parent RC acceptance')
        require(len(source['controls']['negative_controls'])==8,'Missing native RC corruption controls')
        for key in ['native_export_r_edge_value_multiset_exact','geometry_conductor_ownership_exact','every_native_point_ground_capacitance_preserved','every_native_mutual_attachment_and_value_preserved']:
            require(source['audit'][key],key)
        for name,item in source['native']['outputs'].items():
            require(sha(out/'parent-rc'/name)==item['sha256'],'Changed parent raw source '+name)
        binding=json.loads((out/'parent-wires/result.json').read_text())
        require(binding['counts']==dict(components=25,anchors=83,child_macro_pins=66,parent_pins=17),'Parent anchor census')
        for path,h in binding['inputs'].items():require(sha(Path(path))==h,'Changed geometry binding '+path)
        planes=binding['reference_plane_proof']
        require(len(set(planes['unchanged_original_parent_anchors']))==82 and planes['changed_anchor']=='A_pfd_reset','Original planes')
        require(len(planes['release_child_model_matches'])==5,'Release planes')
        result['reference_plane_proof']=planes
        selected={PREFIX+'native07/parent865.spice':RECORDS['native07/parent865.spice']}
        unpack(BASE+'cloud-migration-20261012-000/batch-000002.tar.gz',SOURCE_SHA,141989022,out/'original-parent',selected)
        original=(out/'original-parent/parent865.spice').read_text()
        require(digest(original.encode())=='b7c2b8f7328c14ff15a5798c7aaec0629104ea7ec9252d2594d3dd9db168ff48','Original865 source')
        canonical_path='hw/soc/out/pcie-feedback-pbuf10-20261012/model29/parent865.spice'
        unpack(BASE+'cloud-migration-20261012-000/batch-000001.tar.gz',
            '213a563da91f2b31ba6998a5d14dbfd25972255d7941e566d8f33f7be3b500e1',263318296,out/'canonical-parent',
            {canonical_path:(604976,'802c93c1a4ebf492133a2873f04c3f3e898323166d630328bb3864a18bfbe31a')})
        canonical=(out/'canonical-parent/parent865.spice').read_text()
        canonical_rows=statements(canonical);original_rows=statements(original)
        require(canonical_rows[0]==original_rows[0] and canonical_rows[-1]==original_rows[-1],'Native fixture changes public interface')
        def flat_records(rows):
            records={}
            for w in rows[1:-1]:
                require(w[0][0].lower() in 'xrc' and w[0].lower() not in records,'Unexpected canonical row')
                records[w[0].lower()]=w
            return records
        a=flat_records(canonical_rows);z=flat_records(original_rows)
        require(set(a)==set(z) and len(a)==865+8783,'Native fixture changes original record IDs')
        aliases={};inverse_aliases={}
        for key,w in a.items():
            other=z[key]
            at=next(i for i,v in enumerate(w)if '='in v)-1 if w[0][0].lower()=='x' else 3
            require(len(w)==len(other) and w[at:]==other[at:],'Native fixture changes component parameters '+key)
            for old,new in zip(w[1:at],other[1:at],strict=True):
                require(aliases.setdefault(old,new)==new,'Inconsistent native node rename '+old)
                require(inverse_aliases.setdefault(new,old)==old,'Non-bijective native node rename '+new)
        require(all(aliases.get(p,p)==p for p in canonical_rows[0][2:]),'Changed native public port name')
        require(all(aliases.get('a_pfd_'+p,'a_pfd_'+p)=='a_pfd_'+p for p in ('sub','vdd','ref','vss','up','fb','down','reset')),'Unexpected PFD native alias')
        require(aliases.get('a_count_vss','a_count_vss')=='a_count_vss','Changed common bulk reference name')
        result['original_native_alias_proof']=dict(canonical_sha256=digest(canonical.encode()),
            original_native_sha256=digest(original.encode()),exact_component_records=len(a),
            all_models_parameters_wire_values_and_attachments_preserved=True,bijective=True,
            changed_names={k:v for k,v in aliases.items()if k!=v})
        save()
        macro=restore_pfd_physical_model(out,'aoi4_d2_rc')
        generator=ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py'
        spec=importlib.util.spec_from_file_location('actual_parent_pfd_generator',generator)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        reference=module.profile_devices({n:(ROOT/'hw/soc/analog/pcie'/n).read_text() for n in module.SOURCES},'aoi4_d2')
        fixture,fixture_proof=pfd_physical_parent(original,macro,reference,'aoi4_d2_rc')
        result['standalone_translation']=fixture_proof
        # Compare the actual standalone RC probe coordinates to the parent pin
        # locations. Equality of logical names alone cannot establish a plane.
        child=json.loads((out/'pfd-physical-source/wire/anchors01.json').read_text())
        result['pfd_anchor_source_keys']=list(child)
        require(sha(out/'pfd-physical-source/wire/anchors01.json')=='74e52f3fe2345d7de9c1b9f74867e09c9ff5357bc1daefad6271ec43514224ef','PFD wire anchor source')
        # The standalone native anchors carry their actual export labels. All
        # eight physical macro pins must exist exactly once and coincide.
        child_anchors=child['anchors']
        pfd_planes=[]
        for parent in binding['anchors']:
            if not parent['label'].startswith('A_pfd_'):continue
            port=parent['label'][6:]
            matches=[a for a in child_anchors if a['label'].lower()=='p_'+port.lower()]
            require(len(matches)==1,'PFD child port plane '+port)
            anchor=matches[0]
            require(parent['point_dbu']==[anchor['point_dbu'][0]+200000,anchor['point_dbu'][1]+100000],'PFD physical reference point '+port)
            require(parent['metal']==anchor['metal'],'PFD reference metal '+port)
            pfd_planes.append(dict(port=port,parent=parent['point_dbu'],child=anchor['point_dbu'],metal=parent['metal']))
        require(len(pfd_planes)==8,'PFD8 reference planes')
        result['pfd_reference_planes']=pfd_planes;save()
        # Derive the single intrinsic common bulk from all native NMOS bodies
        # and ptap WELL terminals; never alias a measured metal RC node.
        rows=statements(macro);bulk=set()
        for w in rows[1:-1]:
            if w[0].lower().startswith('x') and len(w)>5 and w[5]=='sg13_hv_nmos':bulk.add(w[4])
            elif w[0].lower().startswith('x') and len(w)>3 and w[3]=='ptap1':bulk.add(w[2])
        require(len(bulk)==1,'PFD common intrinsic bulk census')
        bulk=bulk.pop()
        require(bulk not in rows[0][2:],'Bulk must be separate intrinsic reference')
        require(all(bulk not in w[1:3] for w in rows[1:-1] if w[0][0].lower() in 'rc'),'Do not collapse substrate into measured metal')
        old_bulk='xpfd.'+bulk.lower();new_bulk='a_count_vss'
        bound=[];body_changes=[]
        for line in fixture.splitlines():
            w=line.split()
            if w and w[0].lower().startswith('x_xpfd_'):
                positions=[i for i,n in enumerate(w) if n==old_bulk]
                for i in positions:
                    require((len(w)>5 and w[5]=='sg13_hv_nmos' and i==4) or (w[3]=='ptap1' and i==2),'Unexpected bulk endpoint')
                    w[i]=new_bulk
                if positions:body_changes.append(dict(instance=w[0],positions=positions))
                line=' '.join(w)
            bound.append(line)
        require(len(body_changes)==141,'Expected47 NMOS plus94 ptap bulk endpoints')
        require(not any(old_bulk in line.split() for line in bound),'Private PFD bulk left behind')
        kept=[];removed_parent=Counter()
        for line in bound:
            w=line.lower().split()
            if w and any(w[0].startswith(k+'_xparent_') for k in 'rc'):
                removed_parent[w[0][0]]+=1
            else:kept.append(line)
        require(all(removed_parent[k]>0 for k in 'rc'),'Original parent wire records missing')
        require(not any(re.search(r'\bxparent\.',line.lower())for line in kept),'Old internal parent wires left behind')
        def rename(n):
            canonical='wire_cref' if n.lower()=='sub' else n[2:].lower() if n.startswith('P_') else n.lower()
            return aliases.get(canonical,canonical)
        added=[];counts=Counter()
        for w in statements((out/'parent-rc/wires.spice').read_text()):
            if w[0][0].upper() in 'RC' and not w[0].startswith('.'):
                require(len(w)==4,'Unexpected native RC syntax')
                kind=w[0][0].upper();counts[kind]+=1
                added.append(' '.join([kind+'_xparent_'+w[0].lower(),rename(w[1]),rename(w[2]),w[3]]))
            else:require(w[0].lower() in ('.subckt','.ends'),'Unknown native RC directive')
        require(counts==Counter(R=98,C=242),'Fresh parent wire census')
        stop=[i for i,l in enumerate(kept)if l.lower().startswith('.ends')]
        require(len(stop)==1,'Flat composed parent scope')
        candidate='\n'.join(kept[:stop[0]]+added+kept[stop[0]:])+'\n'
        candidate=candidate.replace('nssoc_parent865_wire_v1','nssoc_parent845_wire_v1')
        physical=json.loads((out/'integrated/result.json').read_text())
        require(sha(out/'integrated/schematic.cir')=='6de9c745fa2911ce732d1f772b28ac8147b476690d97152266c3554bd02d800d','Actual845 physical reference')
        reference_text=(out/'integrated/schematic.cir').read_text()
        # Strict hierarchy reader with model arities. Unknown directives, extra
        # instance parameters and repeated names are errors, not ignored rows.
        model_arity={'npn13g2':4,'sg13_hv_nmos':4,'sg13_hv_pmos':4,'sg13_lv_nmos':4,'sg13_lv_pmos':4,
            'rppd':3,'rhigh':3,'cap_cmim':2,'ntap1':2,'ptap1':2}
        def parse(text,top):
            definitions={};active=None
            for raw in statements(text):
                w=[v.lower()for v in raw];op=w[0]
                if op=='.subckt':
                    require(active is None and w[1] not in definitions,'Duplicate/nested subckt')
                    require(len(w[2:])==len(set(w[2:])),'Duplicate formal pin')
                    active=w[1];definitions[active]=(w[2:],[]);continue
                if op=='.ends':
                    require(active is not None and (len(w)==1 or w[1]==active),'Mismatched ends')
                    active=None;continue
                require(active is not None and op[0] in 'xmrcq','Unknown reference statement '+str(w))
                definitions[active][1].append(w)
            require(active is None and top in definitions,'Unclosed/missing top')
            devices=[];wires=[]
            def expand(name,path,actual,stack):
                require(name not in stack,'Recursive hierarchy')
                formal,items=definitions[name];require(len(formal)==len(actual),'Instance arity '+name)
                mapping=dict(zip(formal,actual))
                node=lambda n:mapping[n]if n in mapping else path+'.'+n if path else n
                seen=set()
                for w in items:
                    require(w[0] not in seen,'Duplicate instance '+path+'.'+w[0]);seen.add(w[0])
                    instance=path+'.'+w[0] if path else w[0]
                    if w[0][0] in 'rc' and len(w)==4 and '='not in w[3]:
                        # Primitive numerical R/C records are measured wire
                        # components; modeled intrinsic R/C are kept devices.
                        try:value=number(w[3])
                        except (ValueError,ArithmeticError):value=None
                        if value is not None:
                            require(value>0,'Nonpositive measured RC')
                            wires.append(dict(path=instance,kind=w[0][0],nets=[node(n)for n in w[1:3]],value=w[3]));continue
                    at=next((i for i,v in enumerate(w)if '='in v),len(w))-1
                    require(at>=2,'Missing model')
                    model=w[at];nets=[node(n)for n in w[1:at]]
                    params={}
                    for p in w[at+1:]:
                        require(p.count('=')==1,'Malformed parameter')
                        k,v=p.split('=');require(k not in params,'Duplicate parameter');number(v);params[k]=v
                    if model in definitions:
                        require(not params,'Unexpected hierarchical override')
                        expand(model,instance,nets,stack+[name])
                    else:
                        require(model in model_arity and len(nets)==model_arity[model],'Unknown model/arity '+str(w))
                        devices.append(dict(path=instance,model=model,nets=nets,params=params))
            public=definitions[top][0];expand(top,'',public,[])
            require(len({d['path']for d in devices})==len(devices),'Duplicate expanded devices')
            require(len({w['path']for w in wires})==len(wires),'Duplicate expanded wire IDs')
            return public,devices,wires
        public,actual,wires=parse(candidate,'nssoc_parent845_wire_v1')
        reference_ports,expected,no_wires=parse(reference_text,physical['top'])
        result['parse_counts']=dict(actual=len(actual),expected=len(expected),wires=len(wires),reference_wires=len(no_wires),
            actual_models=dict(Counter(d['model']for d in actual)),reference_models=dict(Counter(d['model']for d in expected)))
        save()
        require(len(actual)==len(expected)==845 and not no_wires,'845 intrinsic device census')
        require(set(public)==set(reference_ports)|{'wire_cref'} and len(reference_ports)==17,'17 physical public ports and separate wire C reference')
        # Token-level component preservation is independent of the collapsed
        # graph check. No R/C removal, rescaling or changed point attachment can
        # pass simply because the intrinsic topology is unchanged.
        expected_rows=statements(candidate)
        def preserved(text):
            require(statements(text)==expected_rows,'Changed component, wire value or point attachment')
        source_kept=[l for l in original.splitlines() if l and not l.startswith('*') and not l.lower().startswith(('.subckt','.ends')) and not any(l.lower().startswith(k+'_'+group+'_')for k in 'xrc'for group in ('xpfd','xparent'))]
        actual_kept=[l for l in candidate.splitlines() if l and not l.startswith('*') and not l.lower().startswith(('.subckt','.ends')) and not any(l.lower().startswith(k+'_'+group+'_')for k in 'xrc'for group in ('xpfd','xparent'))]
        require(actual_kept==source_kept,'Changed other macro line')
        require(sum(l.lower().startswith('x')for l in source_kept)==610,'610 unchanged intrinsic devices')
        def geometry(d):
            p=d['params'];model=d['model']
            if model in ('ptap1','ntap1'):
                a=number(p['a'])if 'a'in p else number(p['w'])*number(p['l'])
                perimeter=number(p['p'])if 'p'in p else 2*(number(p['w'])+number(p['l']))
                return (('a',str(a.normalize())),('p',str(perimeter.normalize())))
            keys=['nx','we','le']if model=='npn13g2'else['w','l']
            return tuple((k,str(number(p[k]).normalize()))for k in keys)
        def collapsed(devices,wire_rows):
            graph=nx.Graph()
            for w in wire_rows:
                if w['kind']=='r':
                    require(number(w['value'])>0,'Invalid wire R');graph.add_edge(*w['nets'])
            rename={}
            for component in nx.connected_components(graph):
                fixed=component&set(reference_ports)
                require(len(fixed)<=1,'Shorted public ports '+str(fixed))
                target=next(iter(fixed))if fixed else min(component)
                rename.update({n:target for n in component})
            rows=copy.deepcopy(devices)
            for d in rows:d['nets']=[rename.get(n,n)for n in d['nets']]
            return rows
        def graph(rows):
            g=nx.Graph()
            for d in rows:
                dn='d:'+d['path'];g.add_node(dn,label=('device',d['model'],geometry(d)))
                for i,n in enumerate(d['nets']):
                    role='ds'if d['model'].startswith('sg13_') and i in (0,2)else 'ends'if d['model'] in ('rppd','rhigh') and i in (0,1)else i
                    tn=dn+':'+str(i);nn='n:'+n
                    g.add_node(tn,label=('terminal',role));g.add_node(nn,label=('net',n if n in reference_ports else 'internal'))
                    g.add_edge(dn,tn);g.add_edge(tn,nn)
            return g
        want=graph(expected)
        def check_graph(devices,wire_rows):
            require(Counter((d['model'],geometry(d))for d in devices)==Counter((d['model'],geometry(d))for d in expected),'Intrinsic geometry census differs')
            graphs=[want,graph(collapsed(devices,wire_rows))]
            require(len(graphs[0])==len(graphs[1]),'Intrinsic graph node count differs')
            pool={};colors=[]
            for g in graphs:
                c={}
                for n in g:
                    key=g.nodes[n]['label'];pool.setdefault(key,len(pool));c[n]=pool[key]
                colors.append(c)
            prior=0
            for i in range(64):
                new=[];pool={}
                for g,c in zip(graphs,colors):
                    nc={}
                    for n in g:
                        key=(c[n],tuple(sorted(c[v]for v in g[n])));pool.setdefault(key,len(pool));nc[n]=pool[key]
                    new.append(nc)
                require(Counter(new[0].values())==Counter(new[1].values()),'Intrinsic connectivity color mismatch round '+str(i))
                colors=new
                if len(pool)==prior:break
                prior=len(pool)
            for g,c in zip(graphs,colors):nx.set_node_attributes(g,c,'refined')
            mapping=nx.vf2pp_isomorphism(*graphs,node_label='refined')
            require(mapping is not None and set(mapping)==set(graphs[0]) and set(mapping.values())==set(graphs[1]),'No exact intrinsic graph bijection')
            require(all(graphs[0].nodes[a]['label']==graphs[1].nodes[b]['label']for a,b in mapping.items()),'Bijection changes labels')
            require(len(graphs[0].edges)==len(graphs[1].edges) and all(graphs[1].has_edge(mapping[a],mapping[b])for a,b in graphs[0].edges),'Bijection changes edges')
            return mapping
        net=out/'parent845.spice';net.write_text(candidate)
        result['candidate_sha256']=sha(net);result['bulk_binding']=dict(from_node=old_bulk,to_node=new_bulk,terminals=body_changes,
            scope='Common intrinsic bulk ideal reference consistent with native parent schematic; no distributed substrate/well or RF qualification')
        result['component_preservation']=dict(unchanged_devices=610,unchanged_lines=len(source_kept),
            unchanged_lines_sha256=digest(('\n'.join(source_kept)+'\n').encode()),
            old_parent_wire_records=dict(removed_parent),new_parent_wire_records=dict(counts),
            new_pfd_r=715,new_pfd_c=1177,body_binding_does_not_change_wire_records=True)
        save()
        actual_collapsed=collapsed(actual,wires)
        def net_records(rows):
            nets={}
            for d in rows:
                for i,n in enumerate(d['nets']):
                    role='ds'if d['model'].startswith('sg13_') and i in (0,2)else 'ends'if d['model'] in ('rppd','rhigh') and i in (0,1)else i
                    nets.setdefault(n,[]).append(dict(device=d['path'],model=d['model'],geometry=geometry(d),role=role,terminal=i))
            records=[]
            for n,terminals in nets.items():
                signature=json.dumps(sorted([json.dumps([t['model'],t['geometry'],t['role']])for t in terminals]))
                records.append(dict(net=n,terminals=terminals,signature=signature))
            return records
        expected_nets=net_records(expected);actual_nets=net_records(actual_collapsed)
        matched=Counter(r['signature']for r in expected_nets)&Counter(r['signature']for r in actual_nets)
        def unmatched(records):
            remaining=matched.copy();different=[]
            for r in records:
                if remaining[r['signature']]:remaining[r['signature']]-=1
                else:different.append(r)
            return different
        result['graph_diagnostic']=dict(expected_net_count=len(expected_nets),actual_net_count=len(actual_nets),
            expected_graph_nodes=len(graph(expected)),actual_graph_nodes=len(graph(actual_collapsed)),
            matched_net_signatures=sum(matched.values()),
            unmatched_expected=unmatched(expected_nets),unmatched_actual=unmatched(actual_nets))
        diagnostic=out/'graph-diagnostic.json'
        diagnostic.write_text(json.dumps(dict(expected=expected,actual_collapsed=actual_collapsed,wires=wires),indent=2)+'\n')
        result['graph_diagnostic_sha256']=sha(diagnostic);save()
        mapping=check_graph(actual,wires)
        result['exact_graph']=dict(nodes=len(mapping),devices=845,public_ports=17,mapping=mapping);save()
        graph_faults=[]
        for name in ('missing_device','wrong_pfd_width','wrong_hbt_nx','private_pfd_bulk','clock_polarity','reset_bypass'):
            ds=copy.deepcopy(actual);ws=copy.deepcopy(wires)
            if name=='missing_device':ds.pop()
            elif name=='wrong_pfd_width':next(d for d in ds if 'xpfd_' in d['path'] and d['model']=='sg13_hv_nmos')['params']['w']='123u'
            elif name=='wrong_hbt_nx':next(d for d in ds if d['model']=='npn13g2')['params']['nx']='123'
            elif name=='private_pfd_bulk':
                for d in ds:
                    if 'xpfd_'in d['path'] and d['model']=='sg13_hv_nmos':d['nets'][3]='private_bulk_fault'
                    elif 'xpfd_'in d['path'] and d['model']=='ptap1':d['nets'][1]='private_bulk_fault'
            elif name=='clock_polarity':
                for d in ds:d['nets']=[{'a_pfd_ref':'a_pfd_fb','a_pfd_fb':'a_pfd_ref'}.get(n,n)for n in d['nets']]
                for w in ws:
                    if 'xpfd_'in w['path']:w['nets']=[{'a_pfd_ref':'a_pfd_fb','a_pfd_fb':'a_pfd_ref'}.get(n,n)for n in w['nets']]
            else:ws.append(dict(path='r_fault',kind='r',nets=['a_count_reset_b','clearb'],value='1e-6'))
            try:check_graph(ds,ws)
            except ValueError as error:graph_faults.append(dict(name=name,rejection=str(error)))
            else:raise ValueError('Graph accepted fault '+name)
        wire_faults=[]
        for name in ('missing_parent_R','changed_parent_R','changed_parent_C','moved_parent_C','changed_child_R','changed_child_C','changed_kept_geometry'):
            lines=candidate.splitlines()
            if name=='changed_kept_geometry':
                index=next(i for i,l in enumerate(lines)if l.lower().startswith('x') and not l.lower().startswith('x_xpfd_'))
                lines[index]+=' m=2'
            else:
                kind='r'if name.endswith('_R')else'c'
                group='xparent'if 'parent'in name else 'xpfd'
                index=next(i for i,l in enumerate(lines)if l.lower().startswith(kind+'_'+group+'_'))
                if name.startswith('missing'):lines.pop(index)
                else:
                    w=lines[index].split()
                    if name.startswith('moved'):w[1]='wrong_point_fault'
                    else:w[3]='12345'
                    lines[index]=' '.join(w)
            try:preserved('\n'.join(lines)+'\n')
            except ValueError as error:wire_faults.append(dict(name=name,rejection=str(error)))
            else:raise ValueError('Composition accepted fault '+name)
        require(sha(net)==result['candidate_sha256'],'Positive model changed during faults')
        result.update(status='PASS_ACTUAL845_PARENT_COMPONENTS_REFERENCE_PLANES_AND_EXACT_INTRINSIC_GRAPH_NOT_ELECTRICAL_ACCEPTANCE',
            graph_faults=graph_faults,component_faults=wire_faults,counts=dict(devices=845,wires=len(wires)),
            scope='Actual new parent geometry/source and fresh98R242C plus new235-device715R1177C PFD; all610 other devices and remaining macro RC preserved. Exact intrinsic graph checks physical reference with17 fixed pins and all model geometry/body/contact terminals. Raw C/R preservation separately proven. Common substrate is idealized; no qualified distributed substrate/RF, transient/acquisition/PVT, fullPHY or mainchip timing acceptance.')
    except BaseException as error:
        result.update(status='FAILED_ACTUAL845_PARENT_COMPOSITION',error=repr(error));save();raise
    save();print(result['status'],flush=True)


def extract_pfd_parent_rc():
    """Extract and audit fresh real845-parent wires, never reuse the old parent RC."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_ACTUAL_D2_PARENT_NATIVE_RC',source_run=38626309896,qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,name):
        log=out/(name+'.log')
        with log.open('wb') as stream:code=subprocess.call([str(x)for x in cmd],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(name=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(name,'failed')
    save()
    try:
        packed=out/'wire-source.tar.gz'
        fetch(BASE+'cloud-results-38626309896-1-pll-pfd-layout/pfd94-layout-38626309896-1.tar.gz',
            '8ffebb42b9a959ed9c6c18ed9813873c4e92a4c3c2080945e366e677680e1e2a',packed)
        assert packed.stat().st_size==4612750
        prefix='hw/soc/out/cloud-pfd-layout/'
        with tarfile.open(packed) as tar:
            for m in tar.getmembers():
                if not m.isfile():continue
                assert m.name.startswith(prefix)
                rel=m.name[len(prefix):];assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
                if rel=='result.json':rel='wire-source-result.json'
                p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
        packed.unlink()
        assert sha(out/'wire-source-result.json')=='608b16457b8d9500d13a7b60011aa018af1c25369093b10bb50f057679b5684d'
        source=json.loads((out/'wire-source-result.json').read_text())
        assert source['status']=='PASS_ACTUAL_D2_PARENT_WIRE_BINDING_AND_FAULTS_NOT_RC'
        binding=json.loads((out/'parent-wires/result.json').read_text())
        assert binding==source['wire_binding']
        planes=binding['reference_plane_proof']
        assert len(set(planes['unchanged_original_parent_anchors']))==82
        assert planes['changed_anchor']=='A_pfd_reset'
        assert {r['port'] for r in planes['release_child_model_matches']}=={'CLK','RESET_B','RELEASE_B','VDD','VSS'}
        assert all(r['parent_point_dbu']==[r['child_point_dbu'][0]+2580000,r['child_point_dbu'][1]+1500000] for r in planes['release_child_model_matches'])
        result['reference_plane_proof']=planes
        assert binding['counts']==dict(components=25,anchors=83,child_macro_pins=66,parent_pins=17)
        assert all(sha(Path(p))==h for p,h in binding['inputs'].items())
        assert all(sha(out/'parent-wires'/p)==h for p,h in binding['outputs'].items())
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
        rt=out/'magic-cloud';rt.mkdir();packed=out/'magic-runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
        assert packed.stat().st_size==runtime['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(rt,filter='data')
        packed.unlink();manifest=json.loads((rt/'manifest.json').read_text())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
        raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        methods=out/'recovered-parent-methods.json'
        fetch(BASE+'cloud-results-38612960848-1-pll-acquisition-review/result.json',
            'a7b9bdce63bd51971e7295f571f557cbf5b1ae40df80b8529b3ad8c6ee0c1e49',methods)
        assert methods.stat().st_size==1464733
        rows=json.loads(methods.read_text())['recovered_sources'];frozen=out/'frozen-parent-methods';frozen.mkdir()
        prefix='hw/soc/out/pcie-pll753-parent-layout-20261010/'
        pins={'run-parent-rc25.py':'f0d72913bd4cbdda4dea037fe0410fa7de28cf47cf095fac0d1dd68a2e9a054b',
            'audit-parent-rc26.py':'b95945a63367c80f27522cff4c2e2fc90426e92a1540cc6f6380f538c6c10cae'}
        result['method_adaptations']={}
        for name,h in pins.items():
            item=rows[prefix+name];data=item['text'].encode()
            assert digest(data)==h==item['sha256'] and len(data)==item['bytes']
            (frozen/name).write_bytes(data);s=data.decode();changes=[]
            def replace(a,b):
                nonlocal s
                count=s.count(a);assert count>0,(name,a)
                s=s.replace(a,b);changes.append(dict(before=a,after=b,count=count))
            replace('parent-wires24/','parent-wires/')
            if name=='run-parent-rc25.py':
                replace("B/'parent-rc25'","B/'parent-rc'")
                replace("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B/'magic-cloud/runtime/lib'")
                replace("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B/'magic-cloud/tech'")
                target=out/'run-parent-rc.py'
            else:
                replace("def audit(p,anchors):", """def audit(p,anchors):
 frozen=json.loads((B/'parent-wires/result.json').read_text())
 require(frozen['status']=='PASS_ACTUAL845_PARENT_WIRE_GEOMETRY_AND_NATIVE_NET_BINDING_WITH_FAULTS','Unverified parent conductor geometry')
 n_components=frozen['counts']['components'];anchor_count=frozen['counts']['anchors']
 component_ids={r['component'] for r in frozen['wire_components']}
 require(len(component_ids)==n_components==25 and anchor_count==83,'Actual parent component or anchor census differs')""")
                for a,b in [
                    ("==['25']","==[str(n_components+1)]"),("==['24']","==[str(n_components)]"),
                    ("set(range(1,25))","component_ids"),("==78","==anchor_count"),("==24","==n_components"),
                    ("public_ports=17","public_ports=frozen['counts']['parent_pins']"),
                    ("physical_wire_components=24","physical_wire_components=n_components"),
                    ("geometry_probes=78","geometry_probes=anchor_count"),
                    ("logical_metal_references=78","logical_metal_references=anchor_count"),
                    ("connected_wire_components=24","connected_wire_components=n_components"),
                    ("collapsed_matrix_entries=25**2","collapsed_matrix_entries=(n_components+1)**2")]:replace(a,b)
                target=out/'audit-parent-rc.py'
            target.write_text(s);result['method_adaptations'][name]=dict(original_sha256=h,adapted_sha256=sha(target),edits=changes)
        result['runtime']=runtime;save()
        run([sys.executable,out/'run-parent-rc.py'],'native-parent-rc')
        result['native']=json.loads((out/'parent-rc/result.json').read_text())
        assert result['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT' and result['native']['returncode']==0
        save()
        run([sys.executable,out/'audit-parent-rc.py',out/'parent-rc',out/'parent-wires/result.json',out/'parent-rc-audit.json'],'audit-parent-rc')
        result['audit']=json.loads((out/'parent-rc-audit.json').read_text());save()
        assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',result['audit']
        controls=out/'parent-rc-faults.py';controls.write_text("from pathlib import Path\nimport json,shutil,hashlib,importlib.util\nO=Path(__file__).resolve().parent;A=O/'parent-rc';source=O/'audit-parent-rc.py'\nsp=importlib.util.spec_from_file_location('parent_rc_audit',source);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)\nanchors=json.loads((O/'parent-wires/result.json').read_text())\nsha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\nprotected={str(p):sha(p)for p in A.iterdir()if p.is_file()}\npositive=m.audit(A,anchors);assert positive['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'\nfaults=[];base=O/'parent-rc-faults';base.mkdir()\nfor name in ['drop_R','change_R','drop_C','change_C','move_C_reference','change_native_R','change_native_point_C','wrong_anchor']:\n D=base/name;shutil.copytree(A,D);mutated_anchors=json.loads(json.dumps(anchors))\n path=D/('parent_wires.res.ext'if name.startswith('change_native')else'wires.spice')\n lines=path.read_text().splitlines()\n if name=='wrong_anchor':mutated_anchors['anchors'][0]['point_dbu'][0]+=5\n elif name.startswith('change_native'):\n  kind='resist'if name=='change_native_R'else'rnode'\n  i=next(i for i,l in enumerate(lines)if l.startswith(kind+' '))\n  row=lines[i].split();j=3\n  row[j]=str(float(row[j])+1);lines[i]=' '.join(row);path.write_text('\\n'.join(lines)+'\\n')\n else:\n  kind='R'if name.endswith('_R')else'C'\n  i=next(i for i,l in enumerate(lines)if l and l[0].upper()==kind and not l.startswith('*'))\n  if name.startswith('drop'):lines.pop(i)\n  else:\n   row=lines[i].split()\n   if name=='move_C_reference':row[2]='UNBOUND_CAP_REFERENCE'\n   else:row[3]='9.999'\n   lines[i]=' '.join(row)\n  path.write_text('\\n'.join(lines)+'\\n')\n try:\n  result=m.audit(D,mutated_anchors)\n  assert result['status']!='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY','Accepted physical raw corruption '+name\n  rejection=result['status']\n except ValueError as error:rejection=str(error)\n faults.append(dict(name=name,rejection=rejection))\nassert len(faults)==8\nassert all(sha(Path(p))==h for p,h in protected.items())\nresult=dict(status='PASS_PARENT_RC_EIGHT_ACTUAL_CORRUPTION_CONTROLS',positive=positive,negative_controls=faults,unchanged_positive_inputs=protected,qualified_pex=False)\n(O/'parent-rc-controls.json').write_text(json.dumps(result,indent=2)+'\\n')\nprint(result['status'])\n")
        run([sys.executable,controls],'parent-rc-faults')
        result['controls']=json.loads((out/'parent-rc-controls.json').read_text())
        assert result['controls']['status']=='PASS_PARENT_RC_EIGHT_ACTUAL_CORRUPTION_CONTROLS'
        assert all(sha(Path(p))==h for p,h in binding['inputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        result['status']='PASS_ACTUAL845_PARENT_WIRE_RC_AND_EIGHT_FAULTS_NOT_COMPOSITION_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAILED_D2_PARENT_NATIVE_RC',error=repr(error))
        for key,path in [('native','parent-rc/result.json'),('audit','parent-rc-audit.json'),('controls','parent-rc-controls.json')]:
            if (out/path).exists():result[key]=json.loads((out/path).read_text())
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-14000:]for p in out.glob('*.log')}
        save();raise
    save();print(result['status'],flush=True)


def export_pfd_parent_wires():
    """Export only real parent interconnect and bind every polygon/anchor to native LVS."""
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_D2_PARENT_WIRE_BINDING',source_run=38622111375,qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        packed=out/'source.tar.gz'
        fetch(BASE+'cloud-results-38622111375-1-pll-pfd-layout/pfd94-layout-38622111375-1.tar.gz',
            '7456fa988f5fd399a03e23d570ad3a11ade32f4ec7a101a7200aab382d9345fb',packed)
        assert packed.stat().st_size==2426976
        prefix='hw/soc/out/cloud-pfd-layout/'
        with tarfile.open(packed) as tar:
            for m in tar.getmembers():
                if not m.isfile():continue
                assert m.name.startswith(prefix)
                rel=m.name[len(prefix):];assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
                if rel=='result.json':rel='physical-source-result.json'
                p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
        packed.unlink()
        assert sha(out/'physical-source-result.json')=='aabb9a94912402ca8ed27443fe8b380989d7724dd44d1e106140ab7e59e05f8b'
        source=json.loads((out/'physical-source-result.json').read_text())
        assert source['status']=='PASS_ACTUAL_D2_PARENT_GEOMETRY_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert all(sha(out/'integrated'/n)==h for n,h in source['integrated']['outputs'].items())
        protected={str(p):sha(p)for folder in (out/'integrated',out/'parent-physical')for p in folder.rglob('*')if p.is_file()}
        recovered_path=out/'recovered-reference-planes.json'
        fetch(BASE+'cloud-results-38624930704-1-pll-acquisition-review/result.json',
            'e3482fbcaccf9315236b5b47451e1bb0488ca054dc5e3f9299795f03f8ff227e',recovered_path)
        assert recovered_path.stat().st_size==23052321
        recovery=json.loads(recovered_path.read_text())
        assert recovery['status']=='FAILED_PLL_PARENT_METHOD_RECOVERY' and recovery['error']=="AssertionError('No original composition recovered')"
        # The final optional composition inventory assertion failed. Each of
        # these recovered source records already passed its archived SHA binding.
        wanted={
            'hw/soc/out/pcie-reset865-parent-20261011/parent-wires05/result.json':('original-parent-anchors.json','5b126d7155fd56110f0ed4444c50f0a999ce0f68c20b2e7993afa180769c39b1',34280),
            'hw/soc/out/pcie-reset865-composition-20261011/release01/anchors08.json':('release-model-anchors.json','0aaa81bacda8b3a843f469d34a585bf1741bf26e78170e7457fe760a266052e4',652030)}
        for path,(name,h,size) in wanted.items():
            row=recovery['recovered_sources'][path];data=row['text'].encode()
            assert digest(data)==h==row['sha256'] and len(data)==size==row['bytes']
            (out/name).write_bytes(data)
        result['original_reference_plane_sources']={path:dict(sha256=h,bytes=size)for path,(_,h,size) in wanted.items()}
        native=out/'export-parent-wires.py';native.write_text("from pathlib import Path\nfrom collections import defaultdict\nimport pya,json,hashlib,copy\nO=Path(__file__).resolve().parent;A=O/'integrated';D=O/'parent-physical';W=O/'parent-wires';W.mkdir()\nr=json.loads((A/'result.json').read_text());audit=json.loads((D/'lvs_flat/audit.json').read_text())\nTOP=r['top'];assert audit['status']=='PASS within comparison scope' and audit['circuits'][0]['layout_devices_recursive']==845\nsha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()\nold_planes=json.loads((O/'original-parent-anchors.json').read_text())\nrelease_planes=json.loads((O/'release-model-anchors.json').read_text())\nassert old_planes['status']=='PASS_PARENT_ONLY_WIRE_GEOMETRY_AND_NATIVE_NET_BINDING'\nold_by_label={x['label']:x for x in old_planes['anchors']};assert len(old_by_label)==83\nDB=D/'lvs_flat/result.lvsdb';native=pya.LayoutVsSchematic();native.read(str(DB))\nmetals=[8,10,30,50,67,126,134];vias=[19,29,49,66,125,133]\ndef inspect(gds,meta,write=False):\n L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert T is not None\n macro_tops={x['top']for x in meta['instances']};regions={};mapping={}\n wire=pya.Layout();wire.dbu=L.dbu;wt=wire.create_cell('parent_wires')\n for m in metals+vias:\n  li=L.layer(m,0);reg=pya.Region(T.shapes(li))\n  for inst in T.each_inst():\n   if inst.cell.name not in macro_tops:reg+=pya.Region(inst.cell.begin_shapes_rec(li)).transformed(inst.trans)\n  reg=reg.merged();regions[m]=reg;wt.shapes(wire.layer(m,0)).insert(reg)\n  if m in metals and not reg.is_empty():\n   # Compare against the positive full-parent conductor; negative open case\n   # may remove only a parent wire and must then fail connected-net binding.\n   if write:\n    full=pya.Region(T.begin_shapes_rec(li)).merged()\n    candidates=[j for j in native.layer_indexes()if(native.layer_by_index(j)^full).is_empty()]\n   else:candidates=[positive_mapping[m]]\n   assert len(candidates)==1,(m,candidates)\n   mapping[m]=candidates[0]\n   assert(reg-native.layer_by_index(mapping[m])).is_empty()\n e=pya.LayoutToNetlist('PARENT',L.dbu)\n for m,reg in regions.items():\n  if not reg.is_empty():e.register(reg,'gds_'+str(m));e.connect(reg)\n for a,v,b in zip(metals,vias,metals[1:]):\n  if not regions[v].is_empty():e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])\n e.extract_netlist();anchors=[];groups=defaultdict(list)\n def add(label,m,x,y,net,detail):\n  point=pya.Point(round(x/L.dbu),round(y/L.dbu))\n  en=e.probe_net(e.layer_by_name('gds_'+str(m)),point);nn=native.probe_net(native.layer_by_index(mapping[m]),point)\n  assert en is not None and nn is not None,('Anchor unbound',label)\n  row=dict(label=label,metal=m,point_dbu=[point.x,point.y],wire_component=en.cluster_id,native_cluster=nn.cluster_id,logical_net=net,detail=detail)\n  anchors.append(row);groups[en.cluster_id].append(row)\n for macro in meta['instances']:\n  for pin,v in macro['ports'].items():\n   a,b,c,d=v['box_um'];x=(a+c)/2;y=(b+d)/2\n   if macro['name']=='count' and v['layer']==8:x=a+.15\n   if macro['name']!='pfd':\n    previous=old_by_label['A_'+macro['name']+'_'+pin]\n    assert previous['metal']==v['layer'] and previous['logical_net']==v['net']\n    x,y=[z*L.dbu for z in previous['point_dbu']]\n    assert a<=x<=c and b<=y<=d,'Original child reference plane no longer inside macro pin'\n    assert e.probe_net(e.layer_by_name('gds_'+str(v['layer'])),pya.Point(*previous['point_dbu'])) is not None,'Original child reference plane no longer on parent metal'\n   x=round(x/.005)*.005;y=round(y/.005)*.005\n   preferred=pya.Point(round(x/L.dbu),round(y/L.dbu));chosen=preferred\n   plane=e.layer_by_name('gds_'+str(v['layer']))\n   if e.probe_net(plane,chosen) is None:\n    pinbox=pya.Box(*[round(z/L.dbu)for z in v['box_um']])\n    overlap=(regions[v['layer']]&pya.Region(pinbox)).merged()\n    assert not overlap.is_empty(),('No parent wire touches macro pin',macro['name'],pin)\n    candidates=[]\n    for poly in overlap.each():\n     box=poly.bbox();xs=[(box.left+box.right)//2,box.left+5,box.right-5]\n     ys=[(box.bottom+box.top)//2,box.bottom+5,box.top-5]\n     for px in xs:\n      for py in ys:\n       pt=pya.Point(round(px/5)*5,round(py/5)*5)\n       if poly.inside(pt) and e.probe_net(plane,pt) is not None:candidates.append(pt)\n    assert candidates,('No native-grid wire point inside macro pin',macro['name'],pin)\n    chosen=min(candidates,key=lambda q:((q.x-preferred.x)**2+(q.y-preferred.y)**2,q.x,q.y))\n   add('A_'+macro['name']+'_'+pin,v['layer'],chosen.x*L.dbu,chosen.y*L.dbu,v['net'],\n       dict(macro=macro['name'],pin=pin,declared_pin_box_um=v['box_um'],\n            preferred_point_dbu=[preferred.x,preferred.y],\n            original_child_plane_preserved=macro['name']!='pfd',\n            reference_plane_rebinding_required=chosen!=preferred or(macro['name']=='count'and v['layer']==8),\n            parent_wire_intersection_selected=chosen!=preferred))\n for pin,v in meta['ports'].items():\n  a,b,c,d=v['rect_um'];add('P_'+pin,v['layer'],(a+c)/2,(b+d)/2,pin,dict(parent_port=pin))\n assert len({x['label']for x in anchors})==len(anchors)\n native_nets=list(e.netlist().top_circuit().each_net())\n assert set(groups)=={n.cluster_id for n in native_nets},'Unanchored physical wire component'\n expected={v['net']for m in meta['instances']for v in m['ports'].values()}|set(meta['ports'])\n assert len(groups)==len(expected),'Physical open or short changes component census'\n summary=[]\n for cluster,rows in groups.items():\n  names={x['logical_net']for x in rows};nativeids={x['native_cluster']for x in rows}\n  assert len(names)==len(nativeids)==1,'Mixed logical or native nets in wire component'\n  q=rows[0];ref=native.probe_net(native.layer_by_index(mapping[q['metal']]),pya.Point(*q['point_dbu']))\n  en=next(n for n in native_nets if n.cluster_id==cluster)\n  for m in mapping:\n   assert(e.shapes_of_net(en,regions[m],True)-native.shapes_of_net(ref,native.layer_by_index(mapping[m]),True)).is_empty(),'Wire polygon belongs to another native net'\n  summary.append(dict(component=cluster,logical_net=next(iter(names)),native_cluster=next(iter(nativeids)),anchors=[x['label']for x in rows]))\n assert len({x['native_cluster']for x in summary})==len(groups)\n assert {x['logical_net']for x in summary}==expected\n if write:wire.write(str(W/'wires.gds'));e.write(str(W/'wires.l2n'))\n return anchors,summary,mapping\nanchors,summary,positive_mapping=inspect(A/(TOP+'.gds'),r,True)\nunchanged=[a['label']for a in anchors if a['point_dbu']==old_by_label[a['label']]['point_dbu'] and a['metal']==old_by_label[a['label']]['metal']]\nassert len(unchanged)==82 and set(old_by_label)-set(unchanged)=={'A_pfd_reset'}\nrelease=next(m for m in r['instances']if m['name']=='release')\norigin=[round(v*1000)for v in release['position_um']];release_matches=[]\nfor port in release['ports']:\n child=next(a for a in release_planes['anchors']if a['label']=='P_'+port)\n parent=next(a for a in anchors if a['label']=='A_release_'+port)\n assert [x-y for x,y in zip(parent['point_dbu'],origin)]==child['point_dbu'] and parent['metal']==child['metal']\n release_matches.append(dict(port=port,parent_point_dbu=parent['point_dbu'],child_point_dbu=child['point_dbu']))\nfaults=[]\nfor name in ['reset_bridge_open','wrong_reset_logical_net']:\n meta=copy.deepcopy(r);gds=A/(TOP+'.gds')\n if name=='reset_bridge_open':gds=A/'reset-open.gds'\n else:next(x for x in meta['instances']if x['name']=='pfd')['ports']['reset']['net']='ref'\n try:inspect(gds,meta)\n except AssertionError as error:faults.append(dict(name=name,rejection=str(error)))\n else:raise AssertionError('Accepted actual parent wire fault '+name)\nresult=dict(status='PASS_ACTUAL845_PARENT_WIRE_GEOMETRY_AND_NATIVE_NET_BINDING_WITH_FAULTS',\n anchors=anchors,wire_components=summary,counts=dict(components=len(summary),anchors=len(anchors),child_macro_pins=sum(len(x['ports'])for x in r['instances']),parent_pins=len(r['ports'])),\n reference_plane_proof=dict(unchanged_original_parent_anchors=unchanged,release_child_model_matches=release_matches,changed_anchor='A_pfd_reset'),\n negative_controls=faults,inputs={str(p):sha(p)for p in [Path(__file__),O/'original-parent-anchors.json',O/'release-model-anchors.json',A/(TOP+'.gds'),A/'reset-open.gds',DB,A/'result.json',D/'lvs_flat/audit.json']},\n outputs={p.name:sha(p)for p in W.iterdir()},qualified_pex=False,composition_ready=False,\n scope='Only actual updated parent metal/vias, excluding all ten macro contents; every polygon and every macro/public anchor bound to accepted845-device native nets. Includes real moved-reset bridge. Native Magic RC and independent raw audit still required; intrinsic substrate remains a separate idealized model boundary until qualified.')\n(W/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print(result['status'],result['counts'])\n")
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        log=out/'export-parent-wires.log'
        with log.open('wb') as stream:
            code=subprocess.call([str(app),'python',str(native)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result['execution']=dict(returncode=code,script_sha256=sha(native),log_sha256=sha(log))
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,'Native parent wire binding failed'
        assert all(sha(Path(p))==h for p,h in protected.items())
        result['wire_binding']=json.loads((out/'parent-wires/result.json').read_text())
        result['status']='PASS_ACTUAL_D2_PARENT_WIRE_BINDING_AND_FAULTS_NOT_RC'
    except BaseException as error:
        result.update(status='FAILED_D2_PARENT_WIRE_BINDING',error=repr(error))
        if (out/'export-parent-wires.log').exists():result['diagnostic_log']=(out/'export-parent-wires.log').read_text(errors='replace')[-14000:]
        save();raise
    save();print(result['status'],flush=True)


def review_saved_pfd_parent():
    """Recheck exact saved native parent with the hierarchical port reader fixed."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_SAVED_D2_PARENT_PHYSICAL_REVIEW',source_run=38621210521,
        new_geometry_generated=False,qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        packed=out/'source.tar.gz'
        fetch(BASE+'cloud-results-38621210521-1-pll-pfd-layout/pfd94-layout-38621210521-1.tar.gz',
            '6ceb0027c22cb56116f7ac1f7ab53e85b94fcfcf37de346dd28e1eb381fc141a',packed)
        assert packed.stat().st_size==1663987
        prefix='hw/soc/out/cloud-pfd-layout/'
        with tarfile.open(packed) as tar:
            for m in tar.getmembers():
                if not m.isfile():continue
                assert m.name.startswith(prefix)
                rel=m.name[len(prefix):];assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
                if rel=='result.json':rel='original-result.json'
                elif rel.startswith('parent-physical/'):rel=rel.replace('parent-physical/','parent-physical-original/',1)
                p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
        packed.unlink()
        assert sha(out/'original-result.json')=='36211fa13eaedc0fa1b6f662d9d7ff5e52403c371f297aa7192b6ab1b70a2d6f'
        original=json.loads((out/'original-result.json').read_text())
        assert original['status']=='FAILED_D2_PARENT_INTEGRATION'
        old=original['physical']['steps']
        assert old['lvs']['error']=="ValueError('Extracted top differs')"
        assert old['lvs']['audit']['status']=='PASS within comparison scope'
        assert old['lvs_flat']['status']=='PASS'
        assert old['reset_open']['status']==old['wrong_width']['status']=='REJECTED_EXPECTED_FAULT'
        for n,h in original['integrated']['outputs'].items():assert sha(out/'integrated'/n)==h
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=out/'pdk.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert len(manifest['files'])==197 and all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        checker=out/'check-parent-fixed.py';checker.write_text("from pathlib import Path\nimport os,json,sys\nR=Path.cwd();O=Path(__file__).resolve().parent;A=O/'integrated';D=O/'parent-physical';D.mkdir()\nsys.path.insert(0,str(R/'hw/soc/flow'))\nfrom check_ihp_drc import digest,record_result\nfrom check_pcie_rx_cell import execute\nfrom prepare_ihp_drc import validate_lock,verify\nfrom check_pcie_analog_bank import extracted_ports\ndef parent_extracted_ports(text,top):\n lines=[]\n for line in text.splitlines():\n  if line.startswith('+'):\n   if not lines:raise ValueError('Orphan SPICE continuation')\n   lines[-1]+=' '+line[1:].strip()\n  elif line.strip() and not line.startswith('*'):lines.append(line.strip())\n headers=[line.split()for line in lines if line.lower().startswith('.subckt ')]\n names=[h[1]for h in headers]\n if len(names)!=len(set(n.casefold()for n in names)):raise ValueError('Duplicate subcircuit header')\n selected=[h for h in headers if h[1]==top]\n if len(selected)!=1:raise ValueError('Extracted parent top missing or ambiguous')\n ports=selected[0][2:]\n if len(ports)!=len(set(ports)):raise ValueError('Duplicate extracted parent port')\n return set(ports)\ndef parser_controls():\n assert parent_extracted_ports('.subckt child c d\\n.ends child\\n.subckt parent a\\n+ b\\n.ends parent\\n','parent')=={'a','b'}\n for bad in ['.subckt child a b\\n.ends child\\n','.subckt parent a b\\n.subckt parent a b\\n','.subckt parent a a\\n','+ a\\n.subckt parent a b\\n']:\n  try:parent_extracted_ports(bad,'parent')\n  except ValueError:pass\n  else:raise AssertionError('Malformed hierarchical port input accepted')\n return dict(hierarchical_positive=1,negative_controls=4)\nr=json.loads((A/'result.json').read_text());TOP=r['top'];app=Path(os.environ['CLOUD_APPIMAGE'])\nassert digest(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'\npins={Path(p):h for p,h in r['inputs'].items()}\npins.update({A/n:h for n,h in r['outputs'].items()})\npins.update({p:digest(p)for p in [app,Path(__file__),A/'result.json',R/'hw/soc/flow/audit_klayout_lvs.py']})\nfor typ in ['drc','lvs']:\n p=R/f'hw/soc/pnr/ihp-{typ}.lock.json';lock=json.loads(p.read_text());validate_lock(lock)\n assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6';pins[p]=digest(p)\n for row in lock['files']:\n  p=R/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);pins[p]=row['sha256']\nassert all(digest(p)==h for p,h in pins.items())\nresult=dict(status='RUNNING_D2_PARENT_NATIVE_CHECKS',inputs={str(p):h for p,h in pins.items()},steps={},port_parser_controls=parser_controls(),expected_native_devices=845,full_phy_accepted=False,main_chip_integrated=False,qualified_pex=False)\ndef save():(D/'result.json').write_text(json.dumps(result,indent=2)+'\\n')\nsave()\nfor name in ['drc','lvs','lvs_flat','reset_open','wrong_width']:\n q=D/name;q.mkdir();step=result['steps'][name]={}\n try:\n  if name=='drc' and (O/'parent-physical-original/result.json').exists():\n   prior=json.loads((O/'parent-physical-original/result.json').read_text())\n   drc=prior['steps']['drc']\n   assert drc['status']=='PASS' and drc['measurement']['status']=='PASS' and drc['measurement']['category_count']==560\n   # Exact source geometry is pinned by the original checker, not the current file name.\n   oldgds=next(h for p,h in prior['inputs'].items()if p.endswith('/integrated/'+TOP+'.gds'))\n   assert digest(A/(TOP+'.gds'))==oldgds\n   result['steps'][name]=dict(drc,reused_source_run=38621210521,geometry_byte_identical=True)\n   save();print(name,'PASS_SAVED_IDENTICAL_GEOMETRY',flush=True);continue\n  gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/('reset-open-flat.gds' if name=='reset_open' else 'flat.gds')\n  ref=A/('wrong-width.cir' if name=='wrong_width' else 'schematic.cir')\n  typ='drc' if name=='drc' else 'lvs'\n  entry=R/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc' if typ=='drc' else 'lvs/sg13g2.lvs')\n  opts=[f'input={gds}',f'topcell={TOP}',f'log={q/\"deck.log\"}','run_mode='+('deep' if name in ('drc','lvs') else 'flat')]\n  opts+=([f'report={q/\"drc.lyrdb\"}','threads=2','no_recommended=False','precheck_drc=False']if typ=='drc'else[f'schematic={ref}',f'report={q/\"result.lvsdb\"}',f'target_netlist={q/\"extracted.cir\"}','thr=2','no_simplify=true','top_lvl_pins=true'])\n  cmd=[app,'klayout','-b','-zz','-r',entry]\n  for x in opts:cmd+=['-rd',x]\n  step['execution']=execute(cmd,q,'run');save()\n  assert step['execution']['returncode']==0,'Native deck execution failed'\n  if name=='drc':\n   step['measurement']=record_result(q,TOP,0,pins)\n   assert step['measurement']['category_count']==560\n   assert step['measurement']['status']=='PASS','Actual parent DRC violation'\n  else:\n   step['audit_execution']=execute([app,'python',R/'hw/soc/flow/audit_klayout_lvs.py',q/'result.lvsdb','--top',TOP,'--deck-log',q/'deck.log','--output',q/'audit.json'],q,'audit')\n   audit=json.loads((q/'audit.json').read_text());step['audit']=audit\n   if name in ('lvs','lvs_flat'):\n    assert step['audit_execution']['returncode']==0 and audit['status']=='PASS within comparison scope'\n    assert not audit['extraction_diagnostics'] and set(audit['circuit_status_counts'])=={'Match'}\n    roots=[x for x in audit['circuits']if x['layout']==TOP];assert len(roots)==1\n    assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==845\n    assert parent_extracted_ports((q/'extracted.cir').read_text(),TOP)==set(r['ports'])\n   else:\n    assert step['audit_execution']['returncode']==1 and audit['status']=='FAIL'\n    assert 'Deck explicitly reported a mismatch' in audit['reasons']\n  step['status']='PASS' if name in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT'\n except BaseException as error:step.update(status='FAILED',error=repr(error))\n save();print(name,step['status'],flush=True)\nassert all(digest(p)==h for p,h in pins.items())\npassed=all(x['status'] in ('PASS','REJECTED_EXPECTED_FAULT') for x in result['steps'].values())\nresult['status']='PASS_NATIVE_D2_PARENT_DRC_HIER_FLAT_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_NATIVE_D2_PARENT_CHECKS'\nsave();print(result['status']);assert passed\n")
        log=out/'check-parent-fixed.log'
        with log.open('wb') as stream:
            code=subprocess.call([sys.executable,str(checker)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result['execution']=dict(returncode=code,log_sha256=sha(log),checker_sha256=sha(checker))
        if (out/'parent-physical/result.json').exists():result['physical']=json.loads((out/'parent-physical/result.json').read_text())
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0 and result['physical']['status']=='PASS_NATIVE_D2_PARENT_DRC_HIER_FLAT_LVS_AND_FAULTS_NOT_RC'
        assert all(sha(out/'integrated'/n)==h for n,h in original['integrated']['outputs'].items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        result['integrated']=original['integrated']
        result['status']='PASS_ACTUAL_D2_PARENT_GEOMETRY_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAILED_SAVED_D2_PARENT_PHYSICAL_REVIEW',error=repr(error));save();raise
    save();print(result['status'],flush=True)


def integrate_pfd_parent():
    """Replace only the PFD in the real PLL GDS and run strict parent native gates."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted parent integration only'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_D2_PARENT_INTEGRATION',full_phy_accepted=False,main_chip_integrated=False,qualified_pex=False,
        scope='Actual parent GDS PFD replacement and moved reset reconnection; native DRC/hierarchical and flat LVS, actual open/width faults. Fresh parent RC and electrical qualification remain required.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,name):
        log=out/(name+'.log')
        with log.open('wb') as stream:code=subprocess.call([str(x)for x in cmd],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(name=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(name,'failed')
    save()
    try:
        packed=out/'parent-interface.tar.gz'
        fetch(BASE+'cloud-results-38619621840-1-pll-pfd-layout/pfd94-layout-38619621840-1.tar.gz',
            'a84187f9fb911e8dc181d1ea38af394db0df5ec898ed4570e8fd6aa3203d82fc',packed)
        assert packed.stat().st_size==255244
        prefix='hw/soc/out/cloud-pfd-layout/'
        selected=['parent/result.json','parent/schematic.cir','parent/nssoc_pll865_rhi140_pbuf10_development_v1.gds',
            'layout/result.json','layout/schematic.cir','layout/nssoc_pfd94_aoi4_d2_layout_v1.gds','layout/nssoc_pfd94_aoi4_d2_layout_v1.lef']
        with tarfile.open(packed) as tar:
            for name in selected+['result.json']:
                items=[m for m in tar.getmembers()if m.name==prefix+name];assert len(items)==1 and items[0].isfile()
                raw=tar.extractfile(items[0]).read()
                p=out/('interface-source.json' if name=='result.json' else name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        packed.unlink()
        assert sha(out/'interface-source.json')=='ee6fa848a5a5b34e150b300f7865b43c5d39846c72873d6b1909688222c1071b'
        prior=json.loads((out/'interface-source.json').read_text())
        assert prior['status']=='PASS_NATIVE_D2_PARENT_INTERFACE_INVENTORY_NOT_INTEGRATION'
        for p,h in prior['parent_interface_sources'].items():
            relative=p.split('/hw/soc/out/cloud-pfd-layout/',1)[1]
            if relative in selected:assert sha(out/relative)==h
        result['source_interface_run']=38619621840
        result['source_inputs']={n:sha(out/n)for n in selected};save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=out/'pdk.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert len(manifest['files'])==197 and all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        builder=out/'build-parent.py';builder.write_text("from pathlib import Path\nimport pya,json,hashlib,re,copy\nO=Path(__file__).resolve().parent;P=O/'parent';C=O/'layout';A=O/'integrated';A.mkdir()\nsha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()\nold=json.loads((P/'result.json').read_text());new=json.loads((C/'result.json').read_text())\noldtop='nssoc_pll865_rhi140_pbuf10_development_v1';TOP='nssoc_pll845_rhi140_pbuf10_pfd94d2_development_v1'\noldpfd='nssoc_pfd102_layout_v1';newpfd='nssoc_pfd94_aoi4_d2_layout_v1'\nassert old['top']==oldtop and new['top']==newpfd and new['reset_profile']=='aoi4_d2'\nL=pya.Layout();L.read(str(P/(oldtop+'.gds')));T=L.cell(oldtop)\nG=pya.Layout();G.read(str(C/(newpfd+'.gds')));N=G.cell(newpfd);assert L.dbu==G.dbu==.001\ndef shapes(layout,c):return sorted((str(layout.get_info(i)),str(s)) for i in layout.layer_indices() for s in c.each_shape(i))\ndef instances(c):return sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())\noriginal={c.name:(shapes(L,c),instances(c))for c in L.each_cell()}\nii=[i for i in T.each_inst()if i.cell.name==oldpfd];assert len(ii)==1;I=ii[0]\nassert str(I.dcplx_trans)=='r0 *1 200,100'\nmeta=next(x for x in old['instances'] if x['name']=='pfd');assert meta['top']==oldpfd\ndef coords(s):return list(map(float,re.findall(r'-?\\d+(?:\\.\\d+)?',s)))\nchanged=[]\nfor pin,bounds in new['ports'].items():\n a=meta['ports'][pin]['box_um'];b=coords(bounds)\n b=[v+(200 if i%2==0 else 100)for i,v in enumerate(b)]\n if any(abs(x-y)>1e-7 for x,y in zip(a,b,strict=True)):changed.append(pin)\nassert changed==['reset'] and coords(new['ports']['reset'])==[0,1183.23,2,1184.43]\nfor c in G.each_cell():\n if c.name!=newpfd:c.name='pfd94d2_'+c.name\nassert all(L.cell(c.name)is None for c in G.each_cell())\nG.write(str(A/'unique-child.gds'));L.read(str(A/'unique-child.gds'));N=L.cell(newpfd)\nfor name,(ss,ins)in original.items():\n assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ins,name\nfor li in G.layer_indices():\n j=L.layer(G.get_info(li))\n assert(pya.Region(G.cell(newpfd).begin_shapes_rec(li))^pya.Region(N.begin_shapes_rec(j))).is_empty()\nI.cell_index=N.cell_index()\nassert str(I.dbbox())=='(200,100;854,1340.03)'\nT.name=TOP\n# The seven other ports remain at their existing parent endpoints. Join the\n# moved reset pin to its original parent stub by one real Metal5 conductor.\nbridge=pya.Box(200700,1283530,201300,1440930)\nopt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index())\nL.write(str(A/'reset-open.gds'),opt)\nT.shapes(L.layer(67,0)).insert(bridge)\nexpected=original[oldtop][0]+[('67/0',str(next(s for s in T.each_shape(L.layer(67,0))if s.is_box() and s.box==bridge)))]\nassert shapes(L,T)==sorted(expected)\nassert instances(T)==sorted((newpfd if row[0]==oldpfd else row[0],*row[1:])for row in original[oldtop][1])\nfor name,(ss,ins)in original.items():\n if name!=oldtop:assert shapes(L,L.cell(name))==ss and instances(L.cell(name))==ins,name\ns=(P/'schematic.cir').read_text();pattern=r'(?ms)^\\.subckt '+re.escape(oldpfd)+r' .*?^\\.ends '+re.escape(oldpfd)+r'\\s*$'\nmatch=re.search(pattern,s);assert match and len(re.findall(pattern,s))==1\nreference=(C/'schematic.cir').read_text().strip()\nline=next(l for l in reference.splitlines()if l.lower().startswith('.subckt '))\noldline=match.group(0).splitlines()[0];oldports=oldline.split()[2:]\nassert oldports[-1]=='BULK' and line.split()[2:]==oldports[:-1]\nreference=reference.replace(line,line+' BULK',1)\n# Expose the existing intrinsic substrate node to the parent's existing BULK\n# terminal. No new electrical short is invented; native hierarchy/flat LVS\n# must prove the actual shared silicon substrate topology.\ns=s[:match.start()]+reference+'\\n'+s[match.end():]\ns=s.replace(oldpfd,newpfd).replace(oldtop,TOP)\nassert 'Xpfd fb ref reset up down div_avdd avss sub avss '+newpfd in s\n(A/'schematic.cir').write_text(s)\nwrong=reference.replace('MD1 xloop.xup.db vdd vss BULK sg13_hv_nmos w=4u l=0.45u','MD1 xloop.xup.db vdd vss BULK sg13_hv_nmos w=5u l=0.45u',1)\nassert wrong!=reference\n(A/'wrong-width.cir').write_text(s.replace(reference,wrong,1))\nL.write(str(A/(TOP+'.gds')),opt)\nmeta['top']=newpfd;meta['bbox_um']=str(I.dbbox());meta['ports']['reset']['box_um']=[200,1283.23,202,1284.43]\nold.update(top=TOP,status='GENERATED_D2_PARENT_REQUIRES_NATIVE_DRC_LVS',parent_drc_pass=False,parent_lvs_pass=False,closed_loop_accepted=False,qualified_pex=False,serial_phy_complete=False,main_chip_integrated=False)\nold['routes'].append(dict(layer=67,rect_um=[200.7,1283.53,201.3,1440.93],net='reset',purpose='D2 moved reset to preserved original stub'))\nold['integration_proof']=dict(only_changed_macro='pfd',other_cell_shapes_and_instances_unchanged=True,parent_own_shapes_only_added_reset_bridge=True,seven_ports_unchanged=True,pfd_intrinsic_bulk_reference_exposed=True,native_bulk_connectivity_proven=False,expected_native_devices=845)\nold['inputs']={str(p):sha(p)for p in [Path(__file__),P/'result.json',P/(oldtop+'.gds'),P/'schematic.cir',C/'result.json',C/(newpfd+'.gds'),C/'schematic.cir']}\n# Flat LVS view removes only macro metal interface text, preserving every\n# physical polygon and all primitive device-recognition labels.\ndef physical(layout,t,li):\n reg=pya.Region();it=t.begin_shapes_rec(li)\n while not it.at_end():\n  z=it.shape()\n  if z.is_box()or z.is_polygon()or z.is_path():reg.insert(z.polygon.transformed(it.trans()))\n  else:assert z.is_text()\n  it.next()\n return reg.merged()\nfor source,target in [(TOP+'.gds','flat.gds'),('reset-open.gds','reset-open-flat.gds')]:\n F=pya.Layout();F.read(str(A/source));U=F.cell(TOP)\n before={str(F.get_info(li)):physical(F,U,li)for li in F.layer_indices()}\n direct=sorted(z.text.string for li in F.layer_indices()for z in U.each_shape(li)if z.is_text())\n assert direct==sorted(old['ports'])\n allowed={x['top']:set(x['ports'])for x in old['instances']};removed=[]\n for name,ports in allowed.items():\n  cell=F.cell(name);assert cell is not None,name\n  for li in F.layer_indices():\n   info=F.get_info(li)\n   if info.datatype!=25 or info.layer not in [8,10,30,50,67,126,134]:continue\n   for z in list(cell.each_shape(li)):\n    if z.is_text()and z.text.string in ports:removed.append((name,z.text.string));z.delete()\n assert len(removed)==sum(len(p)for p in allowed.values())\n for li in F.layer_indices():assert(before[str(F.get_info(li))]^physical(F,U,li)).is_empty()\n assert sorted(z.text.string for li in F.layer_indices()for z in U.each_shape(li)if z.is_text())==direct\n so=pya.SaveLayoutOptions();so.select_cell(U.cell_index());F.write(str(A/target),so)\nold['outputs']={p.name:sha(p)for p in A.iterdir()if p.is_file()}\n(A/'result.json').write_text(json.dumps(old,indent=2)+'\\n')\nprint(old['status'])\n")
        checker=out/'check-parent.py';checker.write_text("from pathlib import Path\nimport os,json,sys\nR=Path.cwd();O=Path(__file__).resolve().parent;A=O/'integrated';D=O/'parent-physical';D.mkdir()\nsys.path.insert(0,str(R/'hw/soc/flow'))\nfrom check_ihp_drc import digest,record_result\nfrom check_pcie_rx_cell import execute\nfrom prepare_ihp_drc import validate_lock,verify\nfrom check_pcie_analog_bank import extracted_ports\ndef parent_extracted_ports(text,top):\n lines=[]\n for line in text.splitlines():\n  if line.startswith('+'):\n   if not lines:raise ValueError('Orphan SPICE continuation')\n   lines[-1]+=' '+line[1:].strip()\n  elif line.strip() and not line.startswith('*'):lines.append(line.strip())\n headers=[line.split()for line in lines if line.lower().startswith('.subckt ')]\n names=[h[1]for h in headers]\n if len(names)!=len(set(n.casefold()for n in names)):raise ValueError('Duplicate subcircuit header')\n selected=[h for h in headers if h[1]==top]\n if len(selected)!=1:raise ValueError('Extracted parent top missing or ambiguous')\n ports=selected[0][2:]\n if len(ports)!=len(set(ports)):raise ValueError('Duplicate extracted parent port')\n return set(ports)\ndef parser_controls():\n assert parent_extracted_ports('.subckt child c d\\n.ends child\\n.subckt parent a\\n+ b\\n.ends parent\\n','parent')=={'a','b'}\n for bad in ['.subckt child a b\\n.ends child\\n','.subckt parent a b\\n.subckt parent a b\\n','.subckt parent a a\\n','+ a\\n.subckt parent a b\\n']:\n  try:parent_extracted_ports(bad,'parent')\n  except ValueError:pass\n  else:raise AssertionError('Malformed hierarchical port input accepted')\n return dict(hierarchical_positive=1,negative_controls=4)\nr=json.loads((A/'result.json').read_text());TOP=r['top'];app=Path(os.environ['CLOUD_APPIMAGE'])\nassert digest(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'\npins={Path(p):h for p,h in r['inputs'].items()}\npins.update({A/n:h for n,h in r['outputs'].items()})\npins.update({p:digest(p)for p in [app,Path(__file__),A/'result.json',R/'hw/soc/flow/audit_klayout_lvs.py']})\nfor typ in ['drc','lvs']:\n p=R/f'hw/soc/pnr/ihp-{typ}.lock.json';lock=json.loads(p.read_text());validate_lock(lock)\n assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6';pins[p]=digest(p)\n for row in lock['files']:\n  p=R/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);pins[p]=row['sha256']\nassert all(digest(p)==h for p,h in pins.items())\nresult=dict(status='RUNNING_D2_PARENT_NATIVE_CHECKS',inputs={str(p):h for p,h in pins.items()},steps={},port_parser_controls=parser_controls(),expected_native_devices=845,full_phy_accepted=False,main_chip_integrated=False,qualified_pex=False)\ndef save():(D/'result.json').write_text(json.dumps(result,indent=2)+'\\n')\nsave()\nfor name in ['drc','lvs','lvs_flat','reset_open','wrong_width']:\n q=D/name;q.mkdir();step=result['steps'][name]={}\n try:\n  if name=='drc' and (O/'parent-physical-original/result.json').exists():\n   prior=json.loads((O/'parent-physical-original/result.json').read_text())\n   drc=prior['steps']['drc']\n   assert drc['status']=='PASS' and drc['measurement']['status']=='PASS' and drc['measurement']['category_count']==560\n   # Exact source geometry is pinned by the original checker, not the current file name.\n   oldgds=next(h for p,h in prior['inputs'].items()if p.endswith('/integrated/'+TOP+'.gds'))\n   assert digest(A/(TOP+'.gds'))==oldgds\n   result['steps'][name]=dict(drc,reused_source_run=38621210521,geometry_byte_identical=True)\n   save();print(name,'PASS_SAVED_IDENTICAL_GEOMETRY',flush=True);continue\n  gds=A/(TOP+'.gds') if name in ('drc','lvs') else A/('reset-open-flat.gds' if name=='reset_open' else 'flat.gds')\n  ref=A/('wrong-width.cir' if name=='wrong_width' else 'schematic.cir')\n  typ='drc' if name=='drc' else 'lvs'\n  entry=R/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc' if typ=='drc' else 'lvs/sg13g2.lvs')\n  opts=[f'input={gds}',f'topcell={TOP}',f'log={q/\"deck.log\"}','run_mode='+('deep' if name in ('drc','lvs') else 'flat')]\n  opts+=([f'report={q/\"drc.lyrdb\"}','threads=2','no_recommended=False','precheck_drc=False']if typ=='drc'else[f'schematic={ref}',f'report={q/\"result.lvsdb\"}',f'target_netlist={q/\"extracted.cir\"}','thr=2','no_simplify=true','top_lvl_pins=true'])\n  cmd=[app,'klayout','-b','-zz','-r',entry]\n  for x in opts:cmd+=['-rd',x]\n  step['execution']=execute(cmd,q,'run');save()\n  assert step['execution']['returncode']==0,'Native deck execution failed'\n  if name=='drc':\n   step['measurement']=record_result(q,TOP,0,pins)\n   assert step['measurement']['category_count']==560\n   assert step['measurement']['status']=='PASS','Actual parent DRC violation'\n  else:\n   step['audit_execution']=execute([app,'python',R/'hw/soc/flow/audit_klayout_lvs.py',q/'result.lvsdb','--top',TOP,'--deck-log',q/'deck.log','--output',q/'audit.json'],q,'audit')\n   audit=json.loads((q/'audit.json').read_text());step['audit']=audit\n   if name in ('lvs','lvs_flat'):\n    assert step['audit_execution']['returncode']==0 and audit['status']=='PASS within comparison scope'\n    assert not audit['extraction_diagnostics'] and set(audit['circuit_status_counts'])=={'Match'}\n    roots=[x for x in audit['circuits']if x['layout']==TOP];assert len(roots)==1\n    assert roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==845\n    assert parent_extracted_ports((q/'extracted.cir').read_text(),TOP)==set(r['ports'])\n   else:\n    assert step['audit_execution']['returncode']==1 and audit['status']=='FAIL'\n    assert 'Deck explicitly reported a mismatch' in audit['reasons']\n  step['status']='PASS' if name in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT'\n except BaseException as error:step.update(status='FAILED',error=repr(error))\n save();print(name,step['status'],flush=True)\nassert all(digest(p)==h for p,h in pins.items())\npassed=all(x['status'] in ('PASS','REJECTED_EXPECTED_FAULT') for x in result['steps'].values())\nresult['status']='PASS_NATIVE_D2_PARENT_DRC_HIER_FLAT_LVS_AND_FAULTS_NOT_RC' if passed else 'FAILED_NATIVE_D2_PARENT_CHECKS'\nsave();print(result['status']);assert passed\n")
        result['source_bindings']=dict(builder_sha256=sha(builder),checker_sha256=sha(checker),pdk_archive=spec['receipt'],runtime_sha256=sha(app));save()
        run([app,'python',builder],'build-parent')
        result['integrated']=json.loads((out/'integrated/result.json').read_text());save()
        run([sys.executable,checker],'check-parent')
        result['physical']=json.loads((out/'parent-physical/result.json').read_text())
        assert result['physical']['status']=='PASS_NATIVE_D2_PARENT_DRC_HIER_FLAT_LVS_AND_FAULTS_NOT_RC'
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(out/n)==h for n,h in result['source_inputs'].items())
        result['status']='PASS_ACTUAL_D2_PARENT_GEOMETRY_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAILED_D2_PARENT_INTEGRATION',error=repr(error))
        for key,path in [('integrated','integrated/result.json'),('physical','parent-physical/result.json')]:
            if (out/path).exists():result[key]=json.loads((out/path).read_text())
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-14000:]for p in out.glob('*.log')}
        save();raise
    save();print(result['status'],flush=True)


def inspect_pfd_parent_interface():
    """Recover the exact real PLL parent and inspect replacement geometry natively."""
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted parent geometry only'
    run_pfd_lef('aoi4_d2')
    out=ROOT/'hw/soc/out/cloud-pfd-layout'
    result=json.loads((out/'result.json').read_text())
    result['status']='RUNNING_D2_PARENT_GEOMETRY_INTERFACE'
    result['scope']='Read-only exact parent23 and D2 native GDS comparison. No parent geometry replacement, electrical acceptance, shared-bulk binding or PHY closure.'
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        parent=out/'parent';parent.mkdir()
        packed=out/'parent-source.tar.gz'
        fetch(BASE+'cloud-migration-20261012-000/batch-000001.tar.gz',
            '213a563da91f2b31ba6998a5d14dbfd25972255d7941e566d8f33f7be3b500e1',packed)
        assert packed.stat().st_size==263318296
        wanted={
            'nssoc_pll865_rhi140_pbuf10_development_v1.gds':(805654,'de4c0ee0a24da966de32e2d10bc75818b5c51c18f34713f5b033418b42460be3'),
            'result.json':(115421,'7ef831a3e059e94d95ea8e28da4d621de720591b5df30fef6f542fcad70a2697'),
            'schematic.cir':(46553,'3def78b53af0d639fc10f6cc356f4a7c48f8cd20a524237356821aa5fbf5b86f')}
        with tarfile.open(packed) as tar:
            for name,(size,h) in wanted.items():
                target='hw/soc/out/pcie-feedback-pbuf10-20261012/parent23/'+name
                items=[m for m in tar.getmembers() if m.name==target]
                assert len(items)==1 and items[0].isfile()
                raw=tar.extractfile(items[0]).read();assert len(raw)==size and digest(raw)==h
                (parent/name).write_bytes(raw)
        packed.unlink()
        protected={str(p):sha(p) for folder in (parent,out/'layout') for p in folder.iterdir() if p.is_file()}
        native=out/'inspect-parent.py'
        native.write_text("""from pathlib import Path
import pya,json,re
O=Path(__file__).resolve().parent
P=O/'parent';C=O/'layout'
meta=json.loads((P/'result.json').read_text());candidate=json.loads((C/'result.json').read_text())
L=pya.Layout();L.read(str(P/'nssoc_pll865_rhi140_pbuf10_development_v1.gds'))
T=L.cell('nssoc_pll865_rhi140_pbuf10_development_v1');assert T is not None
G=pya.Layout();G.read(str(C/'nssoc_pfd94_aoi4_d2_layout_v1.gds'))
N=G.cell('nssoc_pfd94_aoi4_d2_layout_v1');assert N is not None
assert str(N.dbbox())==candidate['bbox_um'] and G.dbu==L.dbu
pfd=[i for i in T.each_inst() if 'pfd' in i.cell.name.lower()];assert len(pfd)==1
I=pfd[0]
def labels(layout,cell):
 return [dict(layer=str(layout.get_info(li)),text=s.text.string,position=str(s.text.trans))
  for li in layout.layer_indices() for s in cell.each_shape(li) if s.is_text()]
reference=(P/'schematic.cir').read_text()
instance_lines=[l for l in reference.splitlines() if l.lower().startswith('x') and I.cell.name in l.split()]
assert len(instance_lines)==1
subckts=[l for l in reference.splitlines() if l.lower().startswith('.subckt '+I.cell.name.lower()+' ')]
assert len(subckts)==1
port_order=subckts[0].split()[2:];nodes=instance_lines[0].split()[1:-1]
assert len(nodes)==len(port_order)
report=dict(status='PASS_NATIVE_D2_PARENT_INTERFACE_INVENTORY_NOT_INTEGRATION',parent_top=T.name,
 parent_bbox_um=str(T.dbbox()),parent_metadata=meta,old_pfd_top=I.cell.name,
 old_pfd_local_bbox_um=str(I.cell.dbbox()),old_pfd_placed_bbox_um=str(I.dbbox()),
 transform=str(I.dcplx_trans),candidate_bbox_um=str(N.dbbox()),
 candidate_at_original_transform_bbox_um=str(I.dcplx_trans*N.dbbox()),
 same_local_bbox=I.cell.dbbox()==N.dbbox(),old_pfd_direct_labels=labels(L,I.cell),
 candidate_direct_labels=labels(G,N),candidate_ports=candidate['ports'],
 original_reference_pin_order=port_order,original_parent_node_by_pin=dict(zip(port_order,nodes)),
 original_reference_instance=instance_lines[0],
 other_parent_instances=[dict(cell=i.cell.name,transform=str(i.dcplx_trans),bbox_um=str(i.dbbox())) for i in T.each_inst() if i.cell.name!=I.cell.name],
 unchanged_inputs=True,geometry_replaced=False,shared_bulk_bound=False,qualified_pex=False,mainchip_integrated=False)
(O/'parent-interface.json').write_text(json.dumps(report,indent=2)+'\\n')
print(report['status'])
""")
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        log=out/'parent-interface.log'
        with log.open('wb') as stream:
            code=subprocess.call([str(app),'python',str(native)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result['parent_interface_execution']=dict(returncode=code,log_sha256=sha(log),script_sha256=sha(native))
        if code:print(log.read_text(errors='replace')[-10000:],flush=True)
        assert code==0,'Native parent geometry inspection failed'
        assert all(sha(Path(p))==h for p,h in protected.items())
        result['parent_interface']=json.loads((out/'parent-interface.json').read_text())
        result['parent_interface_sources']=protected
        result['status']='PASS_NATIVE_D2_PARENT_INTERFACE_INVENTORY_NOT_INTEGRATION'
    except BaseException as error:
        result.update(status='FAILED_D2_PARENT_INTERFACE_INVENTORY',error=repr(error));save();raise
    save();print(result['status'],flush=True)


def run_pfd_lef(reset_profile='aoi4'):
    """Read exact accepted-development GDS companion LEF without rerunning DRC."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted physical-interface verification only'
    assert reset_profile in ('aoi4','aoi4_d2')
    drive2=reset_profile=='aoi4_d2'
    source_run=38614342619 if drive2 else 38604234902
    archive_sha='9e3de73d250ba223b093f44c55e91c1e7327f8487c8d185b96f2350104e45210' if drive2 else '869b6c076124a4773bf9a047309d49f41d0465db18456603d5c7e7e837d9b953'
    archive_bytes=654630 if drive2 else 639953
    top='nssoc_pfd94_'+reset_profile+'_layout_v1'
    gds_sha='0451b81b8f73a8f1c4e2923e5f50d26cf3c09ad2c3a77ebd0f08acc864e1e08a' if drive2 else '5eba584933e1308a1266e6bb94f8a4f3c54b545b03a7ee5010884875c16accf6'
    lef_sha='6a94d26e4a0803f80d661b116d5df91a76b1887ee763375664f28961d5a9d89e' if drive2 else '00e00d8794e9aa98c162c804f41cd23aec1986031d1136219a799675ea5d7bea'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD94_NATIVE_LEF',reset_profile=reset_profile,adopted=False,full_phy_accepted=False,
        scope=f'Exact DRC/LVS-checked candidate{source_run} LEF. Native OpenROAD pin/outline/obstruction readback and actual missing/obstructed-pin controls. Not RC, electrical, mainchip or PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        archive=out/'physical.tar.gz'
        fetch(BASE+f'cloud-results-{source_run}-1-pll-pfd-layout/pfd94-layout-{source_run}-1.tar.gz',archive_sha,archive)
        assert archive.stat().st_size==archive_bytes
        layout=out/'layout';layout.mkdir()
        names=['result.json','schematic.cir',top+'.gds',top+'.lef']
        with tarfile.open(archive) as tar:
            for name in names:
                matches=[m for m in tar.getmembers() if m.name=='hw/soc/out/cloud-pfd-layout/layout/'+name]
                assert len(matches)==1 and matches[0].isfile()
                (layout/name).write_bytes(tar.extractfile(matches[0]).read())
        archive.unlink();generated=json.loads((layout/'result.json').read_text())
        assert generated['reset_profile']==reset_profile and generated['top']==top and len(generated['core_devices'])==94
        assert sha(layout/(top+'.gds'))==gds_sha
        assert sha(layout/(top+'.lef'))==lef_sha
        assert all(sha(layout/n)==h for n,h in generated['outputs'].items())
        tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef';tech.parent.mkdir(parents=True,exist_ok=True)
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef',
            'e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',tech)
        assert tech.stat().st_size==28396
        app=Path(os.environ['CLOUD_APPIMAGE']);checker=ROOT/'hw/soc/flow/check_pcie_pfd102_lef.py'
        result['source_bindings']=dict(physical_run=source_run,physical_archive_sha256=archive_sha,
            geometry_sha256=sha(layout/(top+'.gds')),lef_sha256=sha(layout/(top+'.lef')),technology_sha256=sha(tech),checker_sha256=sha(checker))
        save()
        log=out/'lef.log'
        with log.open('wb') as stream:
            code=subprocess.call([sys.executable,str(checker),'--layout',str(layout),'--out',str(out/'lef'),
                '--pdk',str(ROOT/'pdk'),'--app',str(app)],stdout=stream,stderr=subprocess.STDOUT)
        if code:print(log.read_text(errors='replace')[-10000:],flush=True)
        assert code==0,'Native PFD LEF verification failed'
        result['lef']=json.loads((out/'lef/result.json').read_text())
        assert result['lef']['status']=='PASS_NATIVE_LEF_AND_TWO_PHYSICAL_FAULTS'
        result['status']='PASS_NATIVE_PFD94_LEF_AND_TWO_PHYSICAL_FAULTS_NOT_MAINCHIP_INTEGRATION'
    except BaseException as error:
        result.update(status='FAILED_NATIVE_PFD94_LEF',error=repr(error))
        if (out/'lef/result.json').exists():result['lef']=json.loads((out/'lef/result.json').read_text())
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-10000:] for p in out.rglob('*.log') if p.is_file()}
        save();raise
    save();print(result['status'],flush=True)


def run_pfd_layout(reset_profile='aoi4'):
    """Hosted actual PFD geometry, strict native DRC/LVS and physical faults."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted physical work only'
    assert reset_profile in ('aoi4','aoi4_d2')
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD94_AOI4_PHYSICAL',reset_profile=reset_profile,adopted=False,full_phy_accepted=False,
        scope='Actual94MOS plus94substrate/47well contacts. Requires560nativeDRC categories, strict flat/hierarchical235device LVS and five physical/reference fault controls. No new RC/electrical/PHY/chip acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,name):
        log=out/(name+'.log')
        with log.open('wb') as stream:code=subprocess.call([str(x) for x in cmd],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(name=name,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(name,'failed')
    save()
    try:
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=out/'pdk.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert len(manifest['files'])==197 and all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        generator=ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py'
        checker=ROOT/'hw/soc/flow/check_pcie_pfd102_v1.py'
        result['source_bindings']=dict(pdk_archive=spec['receipt'],native_runtime_sha256=sha(app),generator_sha256=sha(generator),checker_sha256=sha(checker))
        save()
        run([app,'python',generator,'--pdk',ROOT/'pdk','--out',out/'layout','--reset-profile',reset_profile],'generate')
        generated=json.loads((out/'layout/result.json').read_text())
        assert generated['reset_profile']==reset_profile and len(generated['core_devices'])==94
        if reset_profile=='aoi4_d2':
            result['sizing_scope']='88DFF MOS widths doubled; original AOI reset6MOS unchanged. New physical candidate requires its own RC and native timing, no reuse of original waveform qualification.'
        result['layout']=generated;save()
        run([sys.executable,checker,'--layout',out/'layout','--out',out/'physical','--app',app],'physical')
        physical=json.loads((out/'physical/result.json').read_text())
        assert physical['status']=='PASS_NATIVE_PFD94_AOI4_DRC_LVS_AND_FAULT_CONTROLS'
        result['physical']={k:v for k,v in physical.items() if k!='inputs'}
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        result['status']='PASS_PFD94_AOI4_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAILED_PFD94_AOI4_PHYSICAL',error=repr(error))
        if (out/'physical/result.json').exists():result['physical']=json.loads((out/'physical/result.json').read_text())
        result['diagnostic_logs']={str(p.relative_to(out)):p.read_text(errors='replace')[-14000:] for p in out.rglob('*.log') if p.is_file()}
        save();raise
    save();print(result['status'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--pfd-layout',action='store_true')
    parser.add_argument('--pfd-layout-drive2',action='store_true')
    parser.add_argument('--pfd-lef',action='store_true')
    parser.add_argument('--pfd-lef-drive2',action='store_true')
    parser.add_argument('--inspect-pfd-parent',action='store_true')
    parser.add_argument('--integrate-pfd-parent',action='store_true')
    parser.add_argument('--review-pfd-parent',action='store_true')
    parser.add_argument('--export-pfd-parent-wires',action='store_true')
    parser.add_argument('--extract-pfd-parent-rc',action='store_true')
    parser.add_argument('--compose-pfd-parent',action='store_true')
    parser.add_argument('--pfd-rc',action='store_true')
    parser.add_argument('--pfd-rc-drive2',action='store_true')
    parser.add_argument('--pfd-rc-review',action='store_true')
    parser.add_argument('--review-physical-pfd',action='store_true')
    parser.add_argument('--review-physical-pfd-drive2',action='store_true')
    parser.add_argument('--recover-parent-methods',action='store_true')
    parser.add_argument('--recover-parent-planes',action='store_true')
    parser.add_argument('--recover-pfd-methods',action='store_true')
    parser.add_argument('--pfd-candidate',choices=('baseline_schematic','aoi4','aoi4_rc','aoi4_d2_rc'))
    parser.add_argument('--review-acquisition',action='store_true')
    parser.add_argument('--diagnose-acquisition',action='store_true')
    parser.add_argument('--diagnose-full50',action='store_true')
    parser.add_argument('--diagnose-pfd-topology',action='store_true')
    parser.add_argument('--acquisition',action='store_true',help='Fresh uninterrupted original1us selected-probe capture; never restore a snapshot')
    args=parser.parse_args()
    if args.pfd_rc_drive2:
        assert not any([args.pfd_layout_drive2,args.recover_parent_methods,args.review_physical_pfd,args.pfd_rc_review,args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        run_pfd_rc('aoi4_d2');return
    if args.pfd_layout_drive2:
        assert not any([args.recover_parent_methods,args.review_physical_pfd,args.pfd_rc_review,args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        run_pfd_layout('aoi4_d2');return
    if args.recover_parent_planes:
        assert not any([args.recover_parent_methods,args.pfd_candidate,args.self_test,args.acquisition])
        recover_parent_methods(True);return
    if args.recover_parent_methods:
        assert not any([args.review_physical_pfd,args.pfd_rc_review,args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        recover_parent_methods();return
    if args.review_physical_pfd_drive2:
        assert not any([args.review_physical_pfd,args.pfd_candidate,args.self_test,args.acquisition])
        review_physical_pfd('aoi4_d2_rc');return
    if args.review_physical_pfd:
        assert not any([args.pfd_rc_review,args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        review_physical_pfd();return
    if args.pfd_rc_review:
        assert not any([args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        review_pfd_rc();return
    if args.pfd_rc:
        assert not any([args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        run_pfd_rc();return
    if args.recover_pfd_methods:
        assert not (args.pfd_layout or args.pfd_lef or args.pfd_candidate or args.self_test or args.acquisition or args.diagnose_full50 or args.diagnose_pfd_topology or args.review_acquisition or args.diagnose_acquisition)
        recover_pfd_methods();return
    if args.compose_pfd_parent:
        assert not any([args.extract_pfd_parent_rc,args.export_pfd_parent_wires,args.pfd_candidate,args.self_test,args.acquisition])
        compose_pfd_actual_parent();return
    if args.extract_pfd_parent_rc:
        assert not any([args.export_pfd_parent_wires,args.pfd_candidate,args.self_test,args.acquisition])
        extract_pfd_parent_rc();return
    if args.export_pfd_parent_wires:
        assert not any([args.review_pfd_parent,args.pfd_candidate,args.self_test,args.acquisition])
        export_pfd_parent_wires();return
    if args.review_pfd_parent:
        assert not any([args.integrate_pfd_parent,args.pfd_candidate,args.self_test,args.acquisition])
        review_saved_pfd_parent();return
    if args.integrate_pfd_parent:
        assert not any([args.inspect_pfd_parent,args.pfd_candidate,args.self_test,args.acquisition])
        integrate_pfd_parent();return
    if args.inspect_pfd_parent:
        assert not any([args.pfd_lef_drive2,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition])
        inspect_pfd_parent_interface();return
    if args.pfd_lef_drive2:
        assert not (args.pfd_lef or args.pfd_layout or args.pfd_candidate or args.self_test or args.acquisition)
        run_pfd_lef('aoi4_d2');return
    if args.pfd_lef:
        assert not (args.pfd_layout or args.pfd_candidate or args.self_test or args.acquisition or args.diagnose_full50 or args.diagnose_pfd_topology or args.review_acquisition or args.diagnose_acquisition)
        run_pfd_lef();return
    if args.pfd_layout:
        assert not (args.pfd_candidate or args.self_test or args.acquisition or args.diagnose_full50 or args.diagnose_pfd_topology or args.review_acquisition or args.diagnose_acquisition)
        run_pfd_layout();return
    if args.diagnose_pfd_topology:
        assert not (args.acquisition or args.self_test or args.review_acquisition or args.diagnose_acquisition or args.diagnose_full50)
        diagnose_pfd_topology();return
    if args.diagnose_full50:
        assert not (args.acquisition or args.self_test or args.review_acquisition or args.diagnose_acquisition)
        diagnose_full50();return
    if args.review_acquisition or args.diagnose_acquisition:
        assert not args.acquisition and not args.self_test
        review_completed_acquisition(diagnose=args.diagnose_acquisition);return
    controls=self_test()
    controls['acquisition_review']=acquisition_controls()
    controls['cycle_diagnosis']=acquisition_cycle_controls()
    controls['full50_fifo']=full50_fifo_controls()
    controls['full50_alias']=full50_alias_controls()
    controls['full50_probe_coverage']=full50_probe_controls()
    controls['pfd_topology']=pfd_topology_controls()
    controls['pfd_aoi_truth']=pfd_aoi_controls()
    controls['pfd_operating_point']=pfd_op_controls()
    controls['pfd_physical_terminals']=pfd_terminal_controls()
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
        if args.pfd_candidate:
            import importlib.util
            assert not args.acquisition
            generator=ROOT/'hw/soc/flow/make_pcie_pfd102_local_v2.py'
            spec=importlib.util.spec_from_file_location('original_pfd_generator',generator)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            reference=module.devices({n:(ROOT/'hw/soc/analog/pcie'/n).read_text() for n in module.SOURCES})
            if args.pfd_candidate in ('aoi4_rc','aoi4_d2_rc'):
                profile='aoi4_d2' if args.pfd_candidate=='aoi4_d2_rc' else 'aoi4'
                reference=module.profile_devices({n:(ROOT/'hw/soc/analog/pcie'/n).read_text() for n in module.SOURCES},profile)
                macro=restore_pfd_physical_model(out,args.pfd_candidate)
                parent,proof=pfd_physical_parent((out/'source/parent865.spice').read_text(),macro,reference,args.pfd_candidate)
            else:
                parent,proof=pfd_schematic_parent((out/'source/parent865.spice').read_text(),reference,args.pfd_candidate)
            (out/'parent865.spice').write_text(parent);result['pfd_replacement']=proof
            result['scope']=proof['scope'];result['controls']['pfd_aoi_truth']=pfd_aoi_controls()
            relocated=relocated.replace('.tran 3.125e-13 1e-06 0 3.125e-13','.tran 3.125e-13 5e-08 0 3.125e-13')
            extra=['v(xloop.pfd_candidate.'+n+')' for n in ['clearb','xup.mq','xup.mqb','xup.clkb','xup.qb','xdn.mq','xdn.mqb','xdn.clkb','xdn.qb']]
            if args.pfd_candidate in ('aoi4_rc','aoi4_d2_rc'):extra=proof['physical_terminal_voltage_probes']
            extra=[n for n in extra if n not in vectors]
            old_save='save '+' '.join(vectors);assert setup.count(old_save)==1
            vectors+=extra;assert len(vectors)==len(set(vectors));setup=setup.replace(old_save,'save '+' '.join(vectors))
        else:
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
        if args.pfd_candidate:
            run_pfd_candidate(executable,out,common,result,save,vectors);return
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
        result.update(status='FAILED_PHYSICAL_PFD_NATIVE50_SCREEN' if args.pfd_candidate in ('aoi4_rc','aoi4_d2_rc') else 'FAILED_SCHEMATIC_PFD_NATIVE50_SCREEN' if args.pfd_candidate else 'FAILED_ONE_US_NATIVE865_SELECTED_PROBE_CAPTURE' if args.acquisition else 'FAILED_NATIVE865_SNAPSHOT_NOT_ACQUISITION',error=repr(error))
        save();raise

if __name__=='__main__':
    main()
