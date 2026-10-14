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
    text='NSSOC matched schematic PFD candidate50ns\n'+common+'run candidate.raw\nquit\n.endc\n.end\n'
    (out/'candidate.cir').write_text(text)
    result.update(status='RUNNING_SCHEMATIC_PFD_NATIVE50_SCREEN',native_budget_s=19000,
        native_stop_s=50e-9,comparison_stop_s=None,snapshot_stop_s=None,physical_pfd=False)
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
    clear=v['v(xloop.pfd_candidate.clearb)'];clock_events={}
    for n in ('v(reference)','v(fb)'):
        edge=rising(t,v[n],1.25);clock_events[n]=[dict(time_s=float(e),clearb_v=float(np.interp(e,t,clear)),
            reset_asserted_at_1p25_v=bool(np.interp(e,t,clear)<1.25)) for e in edge if e>12e-9]
    operating_point=zero_source_operating_point((out/'op.raw').read_bytes(),vectors)
    result.update(status='COMPLETE_SCHEMATIC_PFD_NATIVE50_SCREEN_NOT_PHYSICAL_OR_LOCK_ACCEPTANCE',
        captures={'candidate.raw':dict(**meta,sha256=digest(raw),bytes=len(raw),start_s=float(t[0]),end_s=float(t[-1]))},
        zero_source_operating_point=operating_point,signals=stats,clock_events=clock_events,
        required_followup=['Compare both matched baseline_schematic and aoi4 native results',
            'Generate actual PFD GDS/LEF, transistor LVS/DRC and exact new RC composition',
            'Repeat native full-device safety and original1us acquisition gates with physical candidate',
            'Independent PVT/timestep/CDR/jitter/full serialPHY and mainchip signoff'],
        acquisition_accepted=False,full_phy_accepted=False)
    save();print(result['status'],flush=True)


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



def run_pfd_rc():
    """Bind actual235-device geometry and extract new wires on a hosted runner."""
    import shutil
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted extraction only'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD235_GEOMETRY_BOUND_RC',adopted=False,
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
        restore(physical_receipt,ROOT,'physical-input')
        physical=json.loads((out/'result.json').read_text())
        assert physical['status']=='PASS_PFD94_AOI4_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        (out/'physical-source-result.json').write_text(json.dumps(physical,indent=2)+'\n')
        frozen={str(p):sha(p) for sub in ('layout','physical') for p in (out/sub).rglob('*') if p.is_file()}
        generated=json.loads((out/'layout/result.json').read_text())
        assert generated['reset_profile']=='aoi4' and len(generated['core_devices'])==94
        gds=out/'layout/nssoc_pfd94_aoi4_layout_v1.gds'
        assert sha(gds)=='5eba584933e1308a1266e6bb94f8a4f3c54b545b03a7ee5010884875c16accf6'
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
                ('nssoc_pfd102_layout_v1','nssoc_pfd94_aoi4_layout_v1'),
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


def run_pfd_lef():
    """Read exact accepted-development GDS companion LEF without rerunning DRC."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted physical-interface verification only'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD94_NATIVE_LEF',adopted=False,full_phy_accepted=False,
        scope='Exact DRC/LVS-checked candidate38604234902 LEF. Native OpenROAD pin/outline/obstruction readback and actual missing/obstructed-pin controls. Not RC, electrical, mainchip or PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        archive=out/'physical.tar.gz'
        fetch(BASE+'cloud-results-38604234902-1-pll-pfd-layout/pfd94-layout-38604234902-1.tar.gz',
            '869b6c076124a4773bf9a047309d49f41d0465db18456603d5c7e7e837d9b953',archive)
        assert archive.stat().st_size==639953
        layout=out/'layout';layout.mkdir()
        names=['result.json','schematic.cir','nssoc_pfd94_aoi4_layout_v1.gds','nssoc_pfd94_aoi4_layout_v1.lef']
        with tarfile.open(archive) as tar:
            for name in names:
                matches=[m for m in tar.getmembers() if m.name=='hw/soc/out/cloud-pfd-layout/layout/'+name]
                assert len(matches)==1 and matches[0].isfile()
                (layout/name).write_bytes(tar.extractfile(matches[0]).read())
        archive.unlink();generated=json.loads((layout/'result.json').read_text())
        assert generated['reset_profile']=='aoi4' and len(generated['core_devices'])==94
        assert sha(layout/'nssoc_pfd94_aoi4_layout_v1.gds')=='5eba584933e1308a1266e6bb94f8a4f3c54b545b03a7ee5010884875c16accf6'
        assert sha(layout/'nssoc_pfd94_aoi4_layout_v1.lef')=='00e00d8794e9aa98c162c804f41cd23aec1986031d1136219a799675ea5d7bea'
        assert all(sha(layout/n)==h for n,h in generated['outputs'].items())
        tech=ROOT/'pdk/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef';tech.parent.mkdir(parents=True,exist_ok=True)
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef',
            'e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',tech)
        assert tech.stat().st_size==28396
        app=Path(os.environ['CLOUD_APPIMAGE']);checker=ROOT/'hw/soc/flow/check_pcie_pfd102_lef.py'
        result['source_bindings']=dict(physical_run=38604234902,physical_archive_sha256='869b6c076124a4773bf9a047309d49f41d0465db18456603d5c7e7e837d9b953',
            geometry_sha256=sha(layout/'nssoc_pfd94_aoi4_layout_v1.gds'),lef_sha256=sha(layout/'nssoc_pfd94_aoi4_layout_v1.lef'),technology_sha256=sha(tech),checker_sha256=sha(checker))
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


def run_pfd_layout():
    """Hosted actual PFD geometry, strict native DRC/LVS and physical faults."""
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted physical work only'
    out=ROOT/'hw/soc/out/cloud-pfd-layout';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_PFD94_AOI4_PHYSICAL',adopted=False,full_phy_accepted=False,
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
        run([app,'python',generator,'--pdk',ROOT/'pdk','--out',out/'layout','--reset-profile','aoi4'],'generate')
        generated=json.loads((out/'layout/result.json').read_text())
        assert generated['reset_profile']=='aoi4' and len(generated['core_devices'])==94
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
    parser.add_argument('--pfd-lef',action='store_true')
    parser.add_argument('--pfd-rc',action='store_true')
    parser.add_argument('--pfd-rc-review',action='store_true')
    parser.add_argument('--recover-pfd-methods',action='store_true')
    parser.add_argument('--pfd-candidate',choices=('baseline_schematic','aoi4'))
    parser.add_argument('--review-acquisition',action='store_true')
    parser.add_argument('--diagnose-acquisition',action='store_true')
    parser.add_argument('--diagnose-full50',action='store_true')
    parser.add_argument('--diagnose-pfd-topology',action='store_true')
    parser.add_argument('--acquisition',action='store_true',help='Fresh uninterrupted original1us selected-probe capture; never restore a snapshot')
    args=parser.parse_args()
    if args.pfd_rc_review:
        assert not any([args.pfd_rc,args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        review_pfd_rc();return
    if args.pfd_rc:
        assert not any([args.pfd_layout,args.pfd_lef,args.pfd_candidate,args.self_test,args.acquisition,args.diagnose_full50,args.diagnose_pfd_topology,args.review_acquisition,args.diagnose_acquisition,args.recover_pfd_methods])
        run_pfd_rc();return
    if args.recover_pfd_methods:
        assert not (args.pfd_layout or args.pfd_lef or args.pfd_candidate or args.self_test or args.acquisition or args.diagnose_full50 or args.diagnose_pfd_topology or args.review_acquisition or args.diagnose_acquisition)
        recover_pfd_methods();return
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
            parent,proof=pfd_schematic_parent((out/'source/parent865.spice').read_text(),reference,args.pfd_candidate)
            (out/'parent865.spice').write_text(parent);result['pfd_replacement']=proof
            result['scope']=proof['scope'];result['controls']['pfd_aoi_truth']=pfd_aoi_controls()
            relocated=relocated.replace('.tran 3.125e-13 1e-06 0 3.125e-13','.tran 3.125e-13 5e-08 0 3.125e-13')
            extra=['v(xloop.pfd_candidate.'+n+')' for n in ['clearb','xup.mq','xup.mqb','xup.clkb','xup.qb','xdn.mq','xdn.mqb','xdn.clkb','xdn.qb']]
            old_save='save '+' '.join(vectors);assert setup.count(old_save)==1
            vectors+=extra;setup=setup.replace(old_save,'save '+' '.join(vectors))
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
        result.update(status='FAILED_SCHEMATIC_PFD_NATIVE50_SCREEN' if args.pfd_candidate else 'FAILED_ONE_US_NATIVE865_SELECTED_PROBE_CAPTURE' if args.acquisition else 'FAILED_NATIVE865_SNAPSHOT_NOT_ACQUISITION',error=repr(error))
        save();raise

if __name__=='__main__':
    main()
