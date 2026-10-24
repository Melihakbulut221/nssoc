#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source/reader controls only. Synthetic waves below are never DUT evidence."""
import copy,json,struct,tempfile
from pathlib import Path
import numpy as np
import tx_phase_async_preset_diagnostic as b
import cloud_tx_phase_async_preset_intrinsic as native
from cloud_tx_stream import read_streamed_wave
def fails(f):
    try:f()
    except (AssertionError,ValueError,KeyError):return True
    return False
def synthetic(t,contract):
    # Observer fixture: finite10ps transition after each PREDECLARED source event.
    events=contract['oracle']['events'];out={}
    for k in ('MP','QP','release'):
        pts=[(0.,.2*(2*events[0][k]-1))]
        prev=events[0][k]
        for e in events[1:]:
            if e[k]!=prev:
                pts.extend(((e['t_s'],.2*(2*prev-1)),(e['t_s']+b.RISE,.2*(2*e[k]-1))));prev=e[k]
        pts.append((b.STOP,pts[-1][1]))
        out[k]=np.interp(t,[x[0]for x in pts],[x[1]for x in pts])
    out['clock']=np.ones_like(t)
    return out
def raw_fixture(path,vectors,values,plot='Transient Analysis'):
    table=[('time','time')]+[(n,'voltage'if n.startswith('v(')else'current')for n in vectors]
    head='Title: analytic transport control\nPlotname: '+plot+'\nFlags: real\nNo. Variables: '+str(len(table))+'\nNo. Points: '+str(len(values))+'\nVariables:\n'
    head+=''.join(f'\t{i}\t{n}\t{k}\n'for i,(n,k)in enumerate(table))+'Binary:\n'
    path.write_bytes(head.encode()+np.asarray(values,dtype='<f8').tobytes())
def main():
    assert native.os.environ.get('GITHUB_ACTIONS')=='true','Cloud source controls only'
    pins=native.source_pins();raw,bound=native.observer()
    text=(b.ROOT/b.builder.OUTPUT).read_text()
    cases={};prepared=[]
    t=np.arange(0,b.STOP+.5e-12,1e-12)
    for sign in ('p','n'):
        for high in (True,False):
            deck,c=b.prepare(text,bound,sign,high,'candidate.spice','/fixture-models','/fixture-models/r3_cmc.osdi')
            assert c['primitive_census']==dict(npn13G2=106,rppd=127,cap_cmim=8)and len(c['hbt'])==106
            assert len(c['vectors'])==len(set(c['vectors']))
            all_terminals={'v('+n+')'for h in c['hbt'].values()for n in h['terminals']if n!='0'}
            all_currents={'@q.'+n+'.qnpn13g2[ic]'for n in c['hbt']}
            assert all_terminals|all_currents<=set(c['vectors'])
            assert c['deck_sha256']==b.digest(deck)
            observed=synthetic(t,c);measured=b.signal_review(t,observed,c)
            assert measured['diagnostic_signal_screen_passed'],measured
            name=sign+'-'+str(high)
            cases[name]=dict(prepared=True,deck_sha256=c['deck_sha256'],all106_HBT_probed=True,vector_count=len(c['vectors']),synthetic_observer_positive=True)
            prepared.append((deck,c,observed))
    deck,c,good=prepared[0]
    # Reproduce the established 31-map's root positive first window exactly,
    # before our deliberate asynchronous reset interrupts the normal stream.
    ns=b.mapping.original();plan,cells,clocks=b.mapping.design(ns)
    ref={n:b.mapping.oracle_events(ns,clocks[n])for n in ('sa','sb')}
    samples=b.START+(np.arange(80)+.5)*b.UI
    for k,n in [('MP','sa'),('QP','sb')]:
        exp=b.at_events(samples,c['oracle']['events'],k)
        for time,value in zip(samples,exp,strict=True):
            state=ref[n]['initial']
            for tick,v in ref[n]['events']:
                if tick*b.UI>time:break
                state=v
            assert state==value
    rejected=[]
    altered={}
    altered['master_polarity']={**good,'MP':-good['MP']}
    altered['slave_polarity']={**good,'QP':-good['QP']}
    altered['release_never']={**good,'release':np.full_like(t,-.2)}
    altered['release_early']={**good,'release':np.interp(t+70e-12,t,good['release'])}
    altered['release_after_center']={**good,'release':np.interp(t-80e-12,t,good['release'])}
    altered['missing_reset']={**good,'release':np.where(t>b.RESET_ASSERT,.2,good['release'])}
    altered['master_not_reset']={**good,'MP':np.where((t>b.RESET_ASSERT+b.UI)&(t<b.RESET_RELEASE),-.2,good['MP'])}
    altered['slave_not_reset']={**good,'QP':np.where((t>b.RESET_ASSERT+b.UI)&(t<b.RESET_RELEASE),-.2,good['QP'])}
    altered['insufficient_margin']={k:v*.1 for k,v in good.items()}
    altered['swapped_master_slave']={**good,'MP':good['QP'],'QP':good['MP']}
    for name,v in altered.items():
        assert not b.signal_review(t,v,c)['diagnostic_signal_screen_passed'],name;rejected.append(name)
    # Original safety numbers, with each distinct failure deliberately exercised.
    tt=np.array([0.,b.START,b.STOP]);zero=np.zeros(3);cv=np.ones(3);bv=np.full(3,.75);ic=np.full(3,.001)
    assert b.hbt_screen(tt,cv,bv,zero,ic,1)['passed']
    for name,col,base,cur in [
      ('low_headroom',np.full(3,.39),bv,ic),('maximum_VCE',np.full(3,1.61),bv,ic),
      ('maximum_VBE',cv,np.full(3,1.01),ic),('current_density',cv,bv,np.full(3,.00301))]:
        assert not b.hbt_screen(tt,col,base,zero,cur,1)['passed'];rejected.append(name)
    # Exact observer binding rejects changed real metadata, not only fake scalars.
    d=json.loads(raw);d['stage_statistics']['div1_first_div2']['common_mode']['median']=2.
    assert fails(lambda:b.boundary(json.dumps(d).encode()));rejected.append('changed_observer')
    for name,p in [('newline','bad\nname'),('CR','bad\rname'),('quote','bad"name'),('NUL','bad\x00name')]:
        assert fails(lambda:b.prepare(text,bound,'p',True,p,'/models','/r3'));rejected.append('path_'+name)
    assert fails(lambda:b.inventory(text.replace('Nx=4','Nx=8',1),'p'));rejected.append('changed_device')
    # Actual binary reader is exercised in the cloud on tiny complete records.
    raw_controls=[]
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'wave.raw';vectors=['v(a)','@q.x.qnpn13g2[ic]'];s=b.STEP
        rows=np.array([[0.,0.,0.],[s,1.,.001],[2*s,-1.,-.001]])
        raw_fixture(p,vectors,rows)
        rt,rv,rr=read_streamed_wave(p,vectors,2*s,s);assert rr['complete_unmodified_rows']
        base=p.read_bytes()
        for name,mut in [('truncated',base[:-1]),('extra_byte',base+b'x'),('wrong_vector',base.replace(b'v(a)',b'v(b)')),
          ('wrong_count',base.replace(b'No. Points: 3',b'No. Points: 4'))]:
            p.write_bytes(mut);assert fails(lambda:read_streamed_wave(p,vectors,2*s,s));raw_controls.append(name)
        for name,v in [('nonfinite',np.array([[0.,0.,0.],[s,np.nan,.001],[2*s,0.,0.]])),
          ('nonmonotone',np.array([[0.,0.,0.],[s,0.,0.],[s,0.,0.]])),
          ('gap',np.array([[0.,0.,0.],[.5*s,0.,0.],[2*s,0.,0.]]))]:
            raw_fixture(p,vectors,v);assert fails(lambda:read_streamed_wave(p,vectors,2*s,s));raw_controls.append(name)
    assert native.source_pins()==pins
    print(json.dumps(dict(status='PASS_INTRINSIC241_SOURCE_PREPARATION_AND_OBSERVER_CONTROLS_NO_NATIVE_SIMULATION',
      source=b.SOURCE_SHA,boundary=bound,positive_cases=cases,original_first80_root_phase_centers_match=True,
      all106_actual_HBT_terminal_and_current_binding=True,negative_controls=rejected,full_raw_reader_controls=raw_controls,
      DUT_waveforms_executed=False,deterministic_reset_qualified=False,physical_accepted=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
