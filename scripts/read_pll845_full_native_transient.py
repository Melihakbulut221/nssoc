#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded-memory validation of every terminal in the original full1us PLL capture."""
import hashlib,re
from pathlib import Path
import numpy as np
MARKER=b'Binary:\n'
MAX_HEADER=2*1024**2
CHUNK_ROWS=2048
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def header(path):
    with Path(path).open('rb')as f:
        data=f.read(MAX_HEADER)
    pos=data.find(MARKER);assert pos>=0,'Missing bounded native binary header'
    offset=pos+len(MARKER)
    h=data[:offset].decode('ascii')
    def field(key):
        found=[l.split(':',1)[1].strip()for l in h.splitlines()if l.startswith(key+':')]
        assert len(found)==1,('Missing/duplicate native field',key)
        return found[0]
    assert field('Flags')=='real'
    assert field('Plotname').lower()=='transient analysis'
    width=int(field('No. Variables'));rows=int(field('No. Points'))
    assert width>1 and rows>=0
    assert h.count('Variables:\n')==1
    table=[l.split()for l in h.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    assert len(table)==width and all(len(t)==3 for t in table)
    assert [t[0]for t in table]==list(map(str,range(width)))
    names=[t[1]for t in table]
    assert len(set(names))==width and table[0]==['0','time','time']
    assert all(t[2]=='voltage'and re.fullmatch(r'v\([^()\s]+\)',t[1])for t in table[1:])
    return names,dict(header_bytes=offset,declared_rows=rows,columns=width)
def read(path,vectors):
    """Validate all payload values in bounded chunks; retain read-only file-backed views."""
    path=Path(path);names,meta=header(path)
    assert len(vectors)==len(set(vectors))and set(names)=={'time',*vectors}
    assert len(names)==len(vectors)+1
    size=path.stat().st_size;payload=size-meta['header_bytes'];stride=8*len(names)
    assert payload>0 and payload%stride==0,'Truncated or extra native payload'
    rows=payload//stride
    assert rows==meta['declared_rows'],'Native header/payload point mismatch'
    values=np.memmap(path,dtype='<f8',mode='r',offset=meta['header_bytes'],shape=(rows,len(names)))
    last=None;max_step=0.
    for start in range(0,rows,CHUNK_ROWS):
        block=values[start:start+CHUNK_ROWS]
        assert np.isfinite(block).all(),'Nonfinite value in a native terminal'
        times=block[:,0]
        if last is not None:
            gap=float(times[0])-last
            assert gap>0,'Nonmonotonic native time across chunks'
            max_step=max(max_step,gap)
        dt=np.diff(times)
        assert np.all(dt>0),'Nonmonotonic native time'
        if len(dt):max_step=max(max_step,float(dt.max()))
        last=float(times[-1])
    meta.update(rows=rows,bytes=size,start_s=float(values[0,0]),end_s=float(values[-1,0]),
        native_max_step_s=max_step,every_native_column_finite=True,
        header_matches_observed=True,payload_has_only_complete_rows=True,
        raw_sha256=sha(path),validation_chunk_rows=CHUNK_ROWS,
        memory_mapped_readonly=True)
    return names,values,meta
def capture(path,vectors):
    assert len(vectors)==1694,'Full physical terminal coverage required'
    names,values,meta=read(path,vectors)
    assert meta['rows']>3000000,'Original full-duration capture incomplete'
    assert meta['start_s']==0 and abs(meta['end_s']-1e-6)<1e-15
    assert meta['native_max_step_s']<=3.125e-13*1.00001
    return names,values,meta
def controls():
    import tempfile
    vectors=[f'v(xloop.full_native_terminal_{i:04d}_physical_conductor)'for i in range(1694)]
    n=CHUNK_ROWS+5
    a=np.zeros((n,1695),dtype='<f8');a[:,0]=np.arange(n)*3.125e-13
    a[:,1:]=np.arange(1694)[None,:]*1e-6
    names=['time',*vectors]
    def make_header(names=names,rows=n):
        return ('Title: reader control only\nPlotname: Transient Analysis\nFlags: real\n'
           +f'No. Variables: {len(names)}\nNo. Points: {rows}\nVariables:\n'
           +''.join(f'\t{i}\t{x}\t'+('time'if i==0 else'voltage')+'\n'for i,x in enumerate(names))
           +'Binary:\n').encode()
    h=make_header();assert len(h)>65536
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'native.raw'
        def write(head=h,values=a,tail=b''):
            with p.open('wb')as f:f.write(head);f.write(values.tobytes());f.write(tail)
        write();_,v,m=read(p,vectors)
        assert m['rows']==n and m['columns']==1695 and np.array_equal(v,a)
        del v
        rejected=[]
        try:capture(p,vectors)
        except AssertionError:rejected.append('short_capture_not_full1us')
        else:raise AssertionError('Incomplete trajectory accepted')
        cases=[
            ('nan_last_unsummarized_terminal',CHUNK_ROWS,1694,float('nan')),
            ('inf_first_terminal',0,1,float('inf')),
            ('duplicate_time_chunk_boundary',CHUNK_ROWS,0,a[CHUNK_ROWS-1,0]),
            ('reversed_time_final',n-1,0,0.),
        ]
        for label,row,col,value in cases:
            b=a.copy();b[row,col]=value;write(values=b)
            try:read(p,vectors)
            except AssertionError:rejected.append(label)
            else:raise AssertionError('Accepted '+label)
        heads=[
            ('missing_terminal',make_header(names=['time',*vectors[:-1],'v(missing_identity)'])),
            ('duplicate_terminal',make_header(names=['time',vectors[1],*vectors[1:]])),
            ('wrong_points',make_header(rows=n+1)),
            ('wrong_plot',h.replace(b'Transient Analysis',b'Operating Point')),
            ('wrong_unit',h.replace(b'voltage',b'current',1)),
            ('duplicate_field',h.replace(b'Variables:\n',b'No. Points: 4\nVariables:\n')),
        ]
        for label,bad in heads:
            write(head=bad)
            try:read(p,vectors)
            except AssertionError:rejected.append(label)
            else:raise AssertionError('Accepted '+label)
        for label,tail,trunc in [('extra_payload',b'x',False),('truncated_payload',b'',True)]:
            write(tail=tail)
            if trunc:
                with p.open('r+b')as f:f.truncate(p.stat().st_size-1)
            try:read(p,vectors)
            except AssertionError:rejected.append(label)
            else:raise AssertionError('Accepted '+label)
    assert len(rejected)==13
    return dict(status='PASS_FULL_COLUMN_STREAMING_READER_CONTROLS_ONLY',
        controls=rejected,positive_columns=1695,positive_rows=n,header_bytes=len(h),
        native_simulation_or_lock_proven=False)
