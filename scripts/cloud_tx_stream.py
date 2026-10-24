#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Lossless native serializer capture transport; no observation reduction."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def streaming_deck(deck, contract):
    body,control=deck.split('.control\n')
    rows=control.splitlines()
    trans=[r for r in rows if r.startswith('tran ')]
    assert len(trans)==1 and '.tran ' not in body
    output='wrdata wave.dat '+' '.join(contract['vectors'])
    assert rows.count(output)==1
    assert rows.count('op')==1
    assert rows.count('wrdata op.dat '+' '.join(contract['vectors']))==1
    assert rows[-3:]==['quit','.endc','.end']
    index=rows.index(trans[0])
    assert rows[index+1]==output
    rows[index:index+2]=['set filetype=binary','run wave.raw']
    # Preserve every device/model/source/solver/save/alter statement. Move the
    # identical analysis parameters into the netlist for run's rawfile path.
    return body+'.'+trans[0]+'\n.control\n'+'\n'.join(rows)+'\n'


def read_streamed_wave(path,vectors,stop,step):
    """Strict full regular-file raw reader with bounded memory mapping."""
    path=Path(path);assert vectors and len(vectors)==len(set(vectors))
    with path.open('rb') as stream:
        parts=[]
        while True:
            row=stream.readline(1048576)
            assert row and row.endswith(b'\n'),'Incomplete native header'
            parts.append(row)
            assert sum(map(len,parts))<=1048576,'Unbounded native header'
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(parts).decode('ascii')
    def field(key):
        matches=[line.split(':',1)[1].strip() for line in header.splitlines() if line.startswith(key+':')]
        assert len(matches)==1,('Missing/duplicate raw field',key)
        return matches[0]
    assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
    width=int(field('No. Variables'));count=int(field('No. Points'))
    assert width==len(vectors)+1 and count>1
    assert header.count('Variables:\n')==1
    table=[row.split() for row in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and all(len(row)==3 for row in table)
    assert [r[0] for r in table]==list(map(str,range(width)))
    assert table[0]==['0','time','time']
    aliases={'time':'time'}
    for name in vectors:
        for native in ([name,'i('+name+')'] if name.startswith('@') else [name]):
            assert native not in aliases or aliases[native]==name
            aliases[native]=name
    names=[]
    for _,native,kind in table:
        assert native in aliases,('Unexpected native vector',native)
        logical=aliases[native]
        expected='time' if logical=='time' else 'voltage' if logical.startswith('v(') else 'current'
        assert kind==expected,(native,kind,expected)
        names.append(logical)
    assert len(set(names))==width and set(names)=={'time',*vectors}
    assert path.stat().st_size-offset==count*width*8,'Truncated/extra raw payload or incorrect header row count'
    matrix=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    for first in range(0,count,1024):
        assert np.isfinite(matrix[first:first+1024]).all(),'Nonfinite native sample'
    t=matrix[:,0]
    assert t[0]==0 and abs(t[-1]-stop)<1e-18
    delta=np.diff(t)
    assert np.all(delta>0) and np.max(delta)<=step*1.00001
    values={n:matrix[:,i] for i,n in enumerate(names) if i}
    return t,values,dict(header_rows=count,columns=width,header_bytes=offset,
        raw_bytes=path.stat().st_size,raw_sha256=digest(path),
        start_s=float(t[0]),end_s=float(t[-1]),max_step_s=float(delta.max()),
        logical_vector_order=names,complete_unmodified_rows=True,
        method='Memory-mapped full binary raw; every original vector retained; no interpolation/decimation')


def compare_complete(legacy, time, values, vectors):
    assert legacy.shape==(len(time),len(vectors)+1),'Transport row/column mismatch'
    assert np.isfinite(legacy).all()
    columns={'time':time,**values}
    assert set(columns)=={'time',*vectors}
    worst={}
    for index,name in enumerate(['time',*vectors]):
        a=legacy[:,index];b=columns[name]
        # Original wrdata uses numdgt16; these are decimal transport bounds,
        # not physical device, signal-margin, acquisition or timing criteria.
        atol=1e-21 if name=='time' else 2e-14
        bound=atol+2e-14*np.abs(a)
        delta=np.abs(a-b)
        assert np.all(delta<=bound),('Native transport changed samples',name,float(delta.max()))
        worst[name]=float(delta.max())
    return dict(status='PASS_ALL_NATIVE_SAMPLES_UNSHIFTED_STREAM_TRANSPORT',
        rows=len(time),vectors=len(vectors),maximum_absolute_differences=worst,
        decimal_rtol=2e-14,time_atol_s=1e-21,signal_atol=2e-14,
        interpolation=False,fitted_phase=False,omitted_vectors=False)



def pwl_voltage_sources(deck):
    """Keep every original PWL source byte-for-byte for a labelled linear reduction."""
    body=deck.split('.control\n')[0]
    statements=[]
    for line in body.splitlines(keepends=True):
        if line.startswith('+'):
            assert statements
            statements[-1]+=line
        else:
            statements.append(line)
    sources=[s for s in statements if s[:1].lower()=='v' and 'pwl(' in s.lower()]
    assert sources and len({s.split()[0].lower() for s in sources})==len(sources)
    return sources


def failed_capture_tail(path, expected_hash):
    """Inspect rejected raw data only; never relax the complete-capture reader."""
    import math
    path=Path(path)
    assert digest(path)==expected_hash, 'Changed failed native capture'
    with path.open('rb') as stream:
        rows=[]
        while True:
            row=stream.readline(1048576)
            assert row and row.endswith(b'\n')
            rows.append(row)
            assert sum(map(len,rows))<=1048576
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(rows).decode('ascii')
    def field(key):
        values=[line.split(':',1)[1].strip()for line in header.splitlines()if line.startswith(key+':')]
        assert len(values)==1
        return values[0]
    assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
    count=int(field('No. Points'));width=int(field('No. Variables'))
    assert count>1 and width>1 and path.stat().st_size-offset==count*width*8
    table=[row.split()for row in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and [r[0]for r in table]==list(map(str,range(width)))
    assert table[0]==['0','time','time']
    matrix=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    for first in range(0,count,1024):assert np.isfinite(matrix[first:first+1024]).all()
    t=matrix[:,0];delta=np.diff(t)
    result=dict(status='DIAGNOSTIC_OF_REJECTED_CAPTURE_ONLY',accepted=False,sha256=expected_hash,
        rows=count,columns=width,start_s=float(t[0]),end_s=float(t[-1]),
        nonincreasing_time_steps=int(np.sum(delta<=0)),min_delta_s=float(delta.min()),max_delta_s=float(delta.max()),
        nonincreasing_events=[dict(index=int(i),previous_time_s=float(t[i]),next_time_s=float(t[i+1]),delta_s=float(delta[i]))for i in np.flatnonzero(delta<=0)[:32]],
        tail=[dict(time_s=float(t[i]),time_hex=float(t[i]).hex(),ulp_s=math.ulp(float(t[i])),
                   delta_s=float(t[i]-t[i-1])if i else None)for i in range(max(0,count-32),count)],
        last_values={name:float(matrix[-1,i])for i,(_,name,_)in enumerate(table)})
    del matrix,t,delta
    return result


def diagnose_failed_breakpoints():
    import re, math, tarfile, shutil
    from run_cloud_tx_operating_point import fetch
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    root=Path(__file__).resolve().parents[1]
    out=root/'cloud-tx-breakpoint-diagnosis';out.mkdir(exist_ok=False)
    spec=json.loads((root/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    selected=spec['placement_variants']['compact_edge_supply']['failed_numerical_captures']
    runtime=json.loads((root/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())['native_runtime']
    assert digest(os.environ['CLOUD_NGSPICE'])==runtime['executable_sha256']
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=selected['run'],
        accepted=False,serial_phy_complete=False,native_runtime=runtime,cases=[],
        scope='Source-bound rejected-wave tail and exact-PWL linear RC reduction only; no original physical circuit or acceptance gate changed.')
    try:
        for record in selected['cases']:
            if record['mode']!='compact':continue
            case=out/record['condition'];case.mkdir();packed=case/'source.tar.gz'
            fetch(record['url'],record['sha256'],packed)
            assert packed.stat().st_size==record['bytes']
            hashes={};summary=None;seen=set()
            with tarfile.open(packed,'r|gz')as archive:
                for item in archive:
                    assert item.name not in seen;seen.add(item.name)
                    if not item.isfile():continue
                    if item.name=='cloud-tx-mux4/result.json':
                        raw=archive.extractfile(item).read()
                        assert hashlib.sha256(raw).hexdigest()==record['summary_sha256']
                        summary=json.loads(raw);(case/'original-summary.json').write_bytes(raw)
                    elif item.name.startswith('cloud-tx-mux4/native/'):
                        relative=item.name[len('cloud-tx-mux4/'):]
                        raw=archive.extractfile(item)
                        if relative in ('native/wave.raw','native/bench.cir','native/contract.json','native/run.log'):
                            dest=case/Path(relative).name
                            with dest.open('wb')as stream:shutil.copyfileobj(raw,stream)
                            hashes[relative]=digest(dest)
                        else:hashes[relative]=hashlib.file_digest(raw,'sha256').hexdigest()
            assert summary is not None and summary['status']=='FAIL_OR_ERROR' and not summary['accepted']
            assert hashes==summary['outputs']==record['native_outputs']
            assert summary['condition']==record['condition'] and summary['assembled_core_scope']['mode']=='compact'
            contract=json.loads((case/'contract.json').read_text());original=(case/'bench.cir').read_text()
            tail=failed_capture_tail(case/'wave.raw',hashes['native/wave.raw'])
            stop=34e-9;assert tail['end_s']<stop
            failure=[line for line in summary['diagnostics']if 'Timestep too small' in line]
            assert len(failure)==1
            failed_at=float(re.search(r'time = ([^,]+)',failure[0])[1])
            sources=pwl_voltage_sources(original)
            knots=[]
            units={'n':1e-9,'p':1e-12,'u':1e-6}
            def time_value(text):
                return float(text[:-1])*units[text[-1].lower()]if text[-1].lower()in units else float(text)
            for source in sources:
                pairs=re.search(r'(?is)pwl\((.*)\)',source)[1].replace('\n+',' ').split()
                assert len(pairs)%2==0
                times=[time_value(pairs[i])for i in range(0,len(pairs),2)]
                assert all(y>x for x,y in zip(times,times[1:]))
                nearby=sorted(times,key=lambda t:abs(t-failed_at))[:3]
                knots.append(dict(source=source.split()[0],sha256=hashlib.sha256(source.encode()).hexdigest(),
                    nearest=[dict(time_s=t,time_hex=t.hex(),delta_to_failure_s=t-failed_at,ulp_s=math.ulp(t))for t in nearby]))
            row=dict(condition=record['condition'],original_summary_sha256=record['summary_sha256'],
                archive_sha256=record['sha256'],all_native_outputs_verified=hashes,original_diagnostics=summary['diagnostics'],
                failed_capture=tail,pwl_sources=knots,linear_reduction=None)
            result['cases'].append(row)
            # Remove the already verified large raw/archive. They remain in the pinned permanent release.
            (case/'wave.raw').unlink();packed.unlink()
            positive={s.split()[1]for s in sources};negative={s.split()[2]for s in sources}-{'0'}
            assert not positive&negative, 'Unexpected source dependency in diagnostic reduction'
            options=[line for line in original.splitlines()if line.startswith('.options ')];trans=[line for line in original.splitlines()if line.startswith('.tran ')]
            assert len(options)==len(trans)==1
            vectors=[];parts=['NSSOC DIAGNOSTIC ONLY: original PWL sources with linear RC loads\n',*sources]
            for i,node in enumerate(sorted(negative)):parts.append(f'VREF{i} {node} 0 0\n')
            for i,node in enumerate(sorted(positive)):
                parts.append(f'RDIAG{i} {node} diag{i} 1000\nCDIAG{i} diag{i} 0 1f\n')
                vectors.extend([f'v({node})',f'v(diag{i})'])
            parts.extend([options[0]+'\n',trans[0]+'\n.control\nsave '+' '.join(vectors)+'\nset filetype=binary\nrun wave.raw\nquit\n.endc\n.end\n'])
            deck=''.join(parts);assert pwl_voltage_sources(deck)==sources
            row['linear_reductions']={}
            for variant,minbreak in [('original',None),('minbreak_1as',1e-18)]:
                linear=case/variant;linear.mkdir()
                trial_deck=deck if minbreak is None else deck.replace(options[0],options[0]+' minbreak=1e-18')
                assert pwl_voltage_sources(trial_deck)==sources
                (linear/'bench.cir').write_text(trial_deck);(linear/'spinit').write_text('* Explicit empty init\n')
                env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME','LD_PRELOAD')}
                env.update(SPICE_SCRIPTS=str(linear),OMP_NUM_THREADS='1')
                with (linear/'run.log').open('w')as log:
                    code=subprocess.call([os.environ['CLOUD_NGSPICE'],'-n','-b','bench.cir'],cwd=linear,env=env,stdout=log,stderr=subprocess.STDOUT)
                log=(linear/'run.log').read_text(errors='replace')
                lr=dict(returncode=code,bench_sha256=digest(linear/'bench.cir'),same_original_pwl_sources=True,
                    same_original_tran=True,original_options=options[0],minbreak_override_s=minbreak,original_source_count=len(sources),
                    physical_circuit_preserved=False,accepted=False,diagnostics=[s for s in log.splitlines()if any(k in s.lower()for k in ('error','warning','too small','singular'))])
                if (linear/'wave.raw').exists():
                    lr['raw_diagnosis']=failed_capture_tail(linear/'wave.raw',digest(linear/'wave.raw'))
                    lr['reached_original_stop']=abs(lr['raw_diagnosis']['end_s']-stop)<1e-18
                    if lr['reached_original_stop']:
                        try:
                            t,values,proof=read_streamed_wave(linear/'wave.raw',vectors,stop,contract['condition']['step_ps']*1e-12)
                            lr['complete_linear_transport']=proof;del t,values
                        except AssertionError as error:
                            lr['strict_complete_transport_rejected']=repr(error)
                    (linear/'wave.raw').unlink()
                row['linear_reductions'][variant]=lr
        assert len(result['cases'])==2
        result['status']='COMPLETE_FAILED_CAPTURE_DIAGNOSIS_NOT_PHYSICAL_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):digest(p)for p in out.rglob('*')if p.is_file()and p.name not in ('wave.raw','source.tar.gz')}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ('status','source_head','accepted')}),flush=True)

def main():
    if sys.argv[1:]==['--diagnose-failed-breakpoints']:
        diagnose_failed_breakpoints();return
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_args',nargs=argparse.REMAINDER)
    args=parser.parse_args().native_args
    if args[:1]==['--']:args=args[1:]
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert '--stream-raw' not in args
    assert args[args.index('--streams')+1]=='4','Small same-circuit transport control before full32'
    root=Path(__file__).resolve().parents[1]
    out=root/'cloud-tx-mux4';baseline=root/'cloud-tx-stream-baseline'
    assert not out.exists() and not baseline.exists()
    command=[sys.executable,str(root/'scripts/run_cloud_tx_mux4.py'),*args]
    subprocess.run(command,check=True)
    out.rename(baseline)
    try:
        subprocess.run([*command,'--stream-raw'],check=True)
        native=out/'native'
        first=json.loads((baseline/'result.json').read_text())
        second=json.loads((out/'result.json').read_text())
        assert first['returncode']==second['returncode']==0
        assert not first['diagnostics'] and not second['diagnostics']
        contract=json.loads((native/'contract.json').read_text())
        assert (native/'contract.json').read_bytes()==(baseline/'native/contract.json').read_bytes()
        assert (native/'bench.cir').read_text()==streaming_deck((baseline/'native/bench.cir').read_text(),contract)
        assert set(first['inputs'])==set(second['inputs'])
        bench=str(native/'bench.cir')
        assert all(first['inputs'][p]==second['inputs'][p] for p in first['inputs'] if p!=bench)
        with gzip.open(baseline/'native/wave.dat.gz','rt') as stream:
            assert stream.readline().split()==['time',*contract['vectors']]
            legacy=np.loadtxt(stream)
        from run_cloud_tx_mux4 import STOP
        t,v,raw=read_streamed_wave(native/'wave.raw',contract['vectors'],STOP,contract['condition']['step_ps']*1e-12)
        proof=compare_complete(legacy,t,v,contract['vectors'])
        proof.update(raw=raw,legacy_result_sha256=digest(baseline/'result.json'),
            original_stream_result_sha256=digest(out/'result.json'),
            legacy_raw_sha256=first['raw_wave']['sha256'],
            physical_gate_decisions_identical=first['review']['all_engineering_gates_passed']==second['review']['all_engineering_gates_passed'],
            scope='Exact same4:1 native circuit all-sample transport control. Not full32/PVT/PHY acceptance.')
        assert proof['physical_gate_decisions_identical']
        (native/'capture-result.json').write_bytes((out/'result.json').read_bytes())
        (out/'stream-transport-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        second['stream_transport_control']={k:v for k,v in proof.items() if k!='maximum_absolute_differences'}
        (out/'result.json').write_text(json.dumps(second,indent=2)+'\n')
        print(proof['status'],flush=True)
    finally:
        if out.exists():baseline.rename(out/'legacy-transport-control')
        else:baseline.rename(out)


if __name__=='__main__':
    main()
