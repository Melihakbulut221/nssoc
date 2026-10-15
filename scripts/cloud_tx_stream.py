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


def main():
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
