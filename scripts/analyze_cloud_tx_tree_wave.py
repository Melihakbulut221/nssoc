#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound stage-delay and MOS-overshoot diagnosis of complete native waves.

Read-only engineering diagnosis. Never shifts the source-bit oracle, changes
acceptance limits, executes archived code or claims PHY acceptance.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
REPO='Melihakbulut221/nssoc'
TAG='cloud-migration-20261012-000'
UI,START,STOP=125e-12,2e-9,34e-9
CASES={
    'hot_fixed': ('pcie-mux4-divider-damping-20261013.json','hot_low_direct',
                  'tx-mux4-divider14-hot_low-direct-38328968244-1.tar.gz'),
    'hot_native': ('pcie-mux4-native-clock-bias-20261013.json','hot_low',
                  'tx-mux4-native-bias-hot_low-direct-38329329431-1.tar.gz'),
    'cold_native': ('pcie-mux4-native-clock-bias-20261013.json','cold_high',
                   'tx-mux4-native-bias-cold_high-direct-38329329431-1.tar.gz'),
    'nominal_native': ('pcie-mux4-native-clock-bias-20261013.json','nominal',
                      'tx-mux4-native-bias-nominal-direct-38329329431-1.tar.gz'),
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def crossings(t,y,level,begin,end):
    """All rising crossings in the closed window; ambiguous events stay visible."""
    t,y=np.asarray(t),np.asarray(y)
    assert t.ndim==y.ndim==1 and t.shape==y.shape and len(t)>1
    assert np.isfinite(t).all() and np.isfinite(y).all() and np.all(np.diff(t)>0)
    assert t[0]<=begin<end<=t[-1]
    a,b=np.searchsorted(t,[begin,end])
    a=max(0,a-1);b=min(len(t)-1,b)
    candidates=np.flatnonzero((y[a:b]<level)&(y[a+1:b+1]>=level))+a
    result=[]
    for i in candidates:
        at=t[i]+(t[i+1]-t[i])*(level-y[i])/(y[i+1]-y[i])
        if begin<=at<=end:
            result.append(float(at))
    return result


def transition_table(t,clock,mux,output,bits):
    events=[]
    assert len(bits)==256 and set(bits)=={0,1}
    for index in range(1,len(bits)):
        if bits[index]==bits[index-1]:
            continue
        edge=START+index*UI
        begin,end=edge-.1*UI,min(STOP,edge+.9*UI)
        sign=2*bits[index]-1
        csign=1 if index%2==0 else -1
        c=crossings(t,clock*csign,0,begin,end)
        m=crossings(t,mux*sign,0,begin,end)
        o=crossings(t,output*sign,0,begin,end)
        threshold=crossings(t,output*sign,.1,begin,end)
        row=dict(index=index,bit=bits[index],clock_zero_ps=[(v-edge)*1e12 for v in c],
                 mux_zero_ps=[(v-edge)*1e12 for v in m],output_zero_ps=[(v-edge)*1e12 for v in o],
                 output_100mv_ps=[(v-edge)*1e12 for v in threshold],
                 at_original_03ui_v=float(np.interp(edge+.3*UI,t,output)*sign))
        row['unambiguous']=all(len(v)==1 for v in (c,m,o,threshold))
        if row['unambiguous']:
            row.update(clock_to_mux_zero_ps=(m[0]-c[0])*1e12,
                       mux_to_tx_zero_ps=(o[0]-m[0])*1e12,
                       source_to_output_100mv_ps=(threshold[0]-edge)*1e12)
        events.append(row)
    assert events
    stats={}
    for metric in ('clock_to_mux_zero_ps','mux_to_tx_zero_ps','source_to_output_100mv_ps'):
        vals=[r[metric] for r in events if r['unambiguous']]
        stats[metric]=dict(count=len(vals),minimum=min(vals) if vals else None,
            median=float(np.median(vals)) if vals else None,maximum=max(vals) if vals else None)
    return dict(events=events,summary=stats,ambiguous_events=sum(not r['unambiguous'] for r in events),
                original_03ui_below_100mv=sum(r['at_original_03ui_v']<.1 for r in events),
                note='All changing original bits; complete crossing lists retained. Stage delays use only events with exactly one crossing at every node. No fitted delay or acceptance change.')


def api(path):
    return json.loads(subprocess.check_output(['gh','api',path],text=True))


def analyze(label,work):
    evidence,key,asset_name=CASES[label]
    record=json.loads((ROOT/'docs/evidence'/evidence).read_text())['cases'][key]
    release=api(f'repos/{REPO}/releases/tags/{TAG}')
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',
        f'repos/{REPO}/releases/{release["id"]}/assets?per_page=100'],text=True))
    asset=next(a for page in pages for a in page if a['name']==asset_name)
    packed=work/'source.tar.gz'
    subprocess.run(['curl','--fail','--location','--retry','4','--silent','--show-error',
                    asset['browser_download_url'],'-o',str(packed)],check=True)
    assert packed.stat().st_size==asset['size'] and asset['digest']=='sha256:'+sha(packed)
    wanted={'cloud-tx-mux4/result.json':'result.json',
            'cloud-tx-mux4/native/contract.json':'contract.json',
            'cloud-tx-mux4/native/wave.dat.gz':'wave.dat.gz'}
    found=set()
    with tarfile.open(packed,'r|gz') as archive:
        for member in archive:
            if member.name in wanted:
                assert member.isfile() and member.size<2*1024**3 and member.name not in found
                with archive.extractfile(member) as src,(work/wanted[member.name]).open('xb') as dst:
                    import shutil
                    shutil.copyfileobj(src,dst)
                found.add(member.name)
    assert found==set(wanted)
    packed.unlink()
    report=json.loads((work/'result.json').read_text());contract=json.loads((work/'contract.json').read_text())
    assert sha(work/'result.json')==record['summary_sha256']
    for name in ('contract.json','wave.dat.gz'):
        assert sha(work/name)==report['outputs']['native/'+name]
    assert report['raw_wave']==record['raw_wave']
    assert hashlib.sha256(bytes(contract['bits'])).hexdigest()==record['signals']['source_bits_sha256']
    raw_hash=hashlib.sha256();size=0
    with gzip.open(work/'wave.dat.gz','rb') as src:
        while block:=src.read(1024**2):
            raw_hash.update(block);size+=len(block)
    assert size==record['raw_wave']['bytes'] and raw_hash.hexdigest()==record['raw_wave']['sha256']
    nodes={'sp','sn','mp','mn','op','on','avdd','dvdd','tvdd'}
    if contract.get('clock_bias')=='native_vbe':nodes.add('clkbias')
    for name in record['failed_mos']:
        nodes.update(contract['mos'][name]['terminals'])
    for name in record['failed_hbts']:
        nodes.update(contract['hbt'][name]['terminals'])
    nodes.discard('0')
    names=['time']+['v('+n+')' for n in sorted(nodes)]
    with gzip.open(work/'wave.dat.gz','rt') as src:
        header=src.readline().split()
        assert header==['time',*contract['vectors']]
        data=np.loadtxt(src,usecols=[header.index(n) for n in names])
    assert data.ndim==2 and data.shape[1]==len(names) and np.isfinite(data).all()
    values=dict(zip(names,data.T,strict=True));t=values['time']
    assert t[0]==0 and abs(t[-1]-STOP)<1e-18 and np.all(np.diff(t)>0)
    zeros=np.zeros_like(t)
    def v(n):return zeros if n=='0' else values['v('+n+')']
    stages=transition_table(t,v('sp')-v('sn'),v('mp')-v('mn'),v('op')-v('on'),contract['bits'])
    peaks={}
    for name,prior in record['failed_mos'].items():
        terminals=contract['mos'][name]['terminals'];d,g,s,b=[v(n) for n in terminals]
        case={}
        for metric,series in [('vds',d-s),('vgs',g-s),('vgd',g-d)]:
            index=int(np.argmax(abs(series)))
            assert abs(abs(float(series[index]))-prior['peaks'][metric])<1e-9
            offsets=np.asarray([-20,-10,-5,-2,0,2,5,10,20])*1e-12
            observations=np.clip(t[index]+offsets,t[0],t[-1])
            case[metric]=dict(peak_abs_v=float(abs(series[index])),time_s=float(t[index]),
                signed_peak_v=float(series[index]),terminals=terminals,
                trace=[dict(time_s=float(at),volts=[float(np.interp(at,t,v(n))) for n in terminals]) for at in observations])
        peaks[name]=case
    hbt={}
    active=np.flatnonzero(t>=START)
    for name,prior in record['failed_hbts'].items():
        terminals=contract['hbt'][name]['terminals'];c,b,e,sub=[v(n) for n in terminals]
        index=active[int(np.argmin((c-e)[active]))]
        assert abs(float(c[index]-e[index])-prior['min_post_vce_v'])<1e-9
        hbt[name]=dict(min_vce_v=float(c[index]-e[index]),time_s=float(t[index]),
                       terminals=terminals,volts=[float(v(n)[index]) for n in terminals])
    return dict(status='COMPLETE_SOURCE_BOUND_WAVE_DIAGNOSIS_NOT_ACCEPTANCE',case=label,
        archive_url=asset['browser_download_url'],archive_sha256=asset['digest'].removeprefix('sha256:'),
        original_summary_sha256=record['summary_sha256'],raw_wave=record['raw_wave'],
        transitions=stages,mos_peak_events=peaks,hbt_minimum_events=hbt)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',choices=tuple(CASES),required=True)
    args=parser.parse_args();out=Path('cloud-tx-tree-wave-diagnosis');out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',case=args.case)
    try:
        with tempfile.TemporaryDirectory() as temp:
            result=analyze(args.case,Path(temp))
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result.get('transitions',{}).get('summary',result)),flush=True)


if __name__=='__main__':main()
