#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted native865 snapshot portability experiment, not PLL lock acceptance."""
import argparse
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

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    controls=self_test()
    if args.self_test: print(json.dumps(controls));return
    assert os.environ.get('GITHUB_ACTIONS')=='true', 'Hosted execution only'
    out=ROOT/'cloud-pll-snapshot';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING_NATIVE865_SNAPSHOT_PORTABILITY',controls=controls,
        full_phy_accepted=False,acquisition_accepted=False,snapshot_validated=False,
        reference='https://ngspice.sourceforge.io/docs/ngspice-manual.pdf',
        scope='Actual865-device circuit and full extracted metal RC, exact historical 1us deck stopped at25/50ns. Original model/runtime bytes, startup sources, .3125ps step and tolerances retained. Compares continuous vs same-process resumed vs fresh-process restored waveforms. Only bounded restart-method evidence, not1us lock, all-device safety, PVT, CDR, full serialPHY, or chip acceptance.')
    def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
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
        result.update(status='FAILED_NATIVE865_SNAPSHOT_NOT_ACQUISITION',error=repr(error))
        save();raise

if __name__=='__main__':
    main()
