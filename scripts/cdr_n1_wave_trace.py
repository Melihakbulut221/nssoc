# SPDX-License-Identifier: Apache-2.0
"""Derived per-bit trace of the preserved N1 actual650 loaded waveform.

Reads the complete native raw file of run 41733225660 inside the hosted job,
checks every header and payload invariant, and samples every saved vector at
16 phases per unit interval. No simulation is run and no gate is changed;
this is a diagnosis input, never an electrical acceptance.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12;PHASES=16
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb')as f:
        for b in iter(lambda:f.read(1<<22),b''):h.update(b)
    return h.hexdigest()
def read_raw(path):
    with open(path,'rb')as stream:
        parts=[]
        while True:
            row=stream.readline(1<<20);assert row.endswith(b'\n'),'incomplete header'
            parts.append(row);assert sum(map(len,parts))<=1<<20,'unbounded header'
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(parts).decode('ascii')
    field=lambda k:[l.split(':',1)[1].strip()for l in header.splitlines()if l.startswith(k+':')]
    assert field('Flags')==['real']and field('Plotname')==['Transient Analysis']
    width=int(field('No. Variables')[0]);count=int(field('No. Points')[0])
    table=[r.split()for r in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and table[0][1]=='time'
    assert Path(path).stat().st_size-offset==count*width*8,'payload size'
    m=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    return m,[r[1]for r in table],dict(points=count,columns=width,header_bytes=offset)
def main(raw,out):
    m,names,info=read_raw(raw);t=np.asarray(m[:,0])
    assert t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)
    grid=(START+np.arange(258)[:,None]*UI+np.arange(PHASES)[None,:]*UI/PHASES).ravel()
    samples=np.empty((len(names)-1,len(grid)),dtype=np.float32)
    for i in range(1,len(names)):
        column=np.asarray(m[:,i]);assert np.isfinite(column).all(),names[i]
        samples[i-1]=np.interp(grid,t,column)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/'n1-bit-phase-samples.npz',samples=samples,names=np.array(names[1:]),grid=grid)
    info.update(raw_bytes=Path(raw).stat().st_size,raw_sha256=sha(raw),phases_per_ui=PHASES,bits=258,
        start_s=START,ui_s=UI,derived_only=True,electrical_acceptance=False,
        source_run=41733225660,source_artifact=13283214752)
    (out/'n1-wave-trace.json').write_text(json.dumps(info,indent=2,sort_keys=True)+'\n')
    print(json.dumps(info,sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
