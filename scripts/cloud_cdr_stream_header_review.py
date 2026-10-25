#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import json,os
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_tx_stream as stream
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-cdr-stream-header-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-via-rich-stream-width-rejection-20261019.json').read_text());selected=['legacy/wave.dat','streamed/wave.raw','legacy/native.log','streamed/native.log','legacy/bench.cir','streamed/bench.cir']
        old,proof=reports.restore_report('cdr-via-rich-stream-control',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected);assert old==pin['report'];r['source']=proof
        for mode in ('legacy','streamed'):assert old['captures'][mode]['returncode']==0 and not old['captures'][mode]['diagnostics']
        vectors=json.loads((ROOT/'docs/evidence/cdr-via-rich-v7-loaded-memory-rejection-20261018.json').read_text())['report']['vectors'];assert len(vectors)==1107
        path=OUT/'source/streamed/wave.raw'
        with path.open('rb')as f:
            lines=[]
            while True:
                row=f.readline(1048576);assert row and row.endswith(b'\n');lines.append(row);assert sum(map(len,lines))<=1048576
                if row==b'Binary:\n':break
            offset=f.tell()
        header=b''.join(lines).decode('ascii');r['raw_header']=header
        def field(k):
            xs=[x.split(':',1)[1].strip()for x in header.splitlines()if x.startswith(k+':')];assert len(xs)==1;return xs[0]
        assert field('Flags')=='real'and field('Plotname')=='Transient Analysis'
        width,count=int(field('No. Variables')),int(field('No. Points'));assert count>1 and width>1
        table=[x.split()for x in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()];assert len(table)==width and all(len(x)==3 for x in table)
        assert table[0]==['0','time','time']and [x[0]for x in table]==list(map(str,range(width)))and len({x[1]for x in table})==width
        assert path.stat().st_size-offset==count*width*8
        aliases={}
        for n in vectors:
            for a in ([n,'i('+n+')']if n.startswith('@')else[n]):assert a not in aliases or aliases[a]==n;aliases[a]=n
        missing=set(vectors);found={};extra=[]
        for i,n,kind in table[1:]:
            if n in aliases:
                logical=aliases[n];assert logical not in found;found[logical]=int(i);missing.discard(logical)
            else:extra.append(dict(index=int(i),name=n,kind=kind))
        r['header_analysis']=dict(rows=count,columns=width,expected_columns=1108,missing=sorted(missing),extra=extra,matched=len(found),raw_bytes=path.stat().st_size)
        data=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
        for start in range(0,count,1024):assert np.isfinite(data[start:start+1024]).all()
        t=data[:,0];dt=np.diff(t);assert t[0]==0 and abs(t[-1]-3e-9)<1e-18 and np.all(dt>0)and dt.max()<=.3125e-12*1.00001
        if not missing:
            baseline=np.loadtxt(OUT/'source/legacy/wave.dat',skiprows=1)
            r['requested_all_sample_comparison']=stream.compare_complete(baseline,t,{n:data[:,i]for n,i in found.items()},vectors)
        assert all(sha(OUT/'source'/n)==old['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_RAW_HEADER_REVIEW_ORIGINAL_TRANSPORT_GATE_NOT_OVERRIDDEN'
    except BaseException as e:r.update(status='FAIL_RAW_HEADER_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
