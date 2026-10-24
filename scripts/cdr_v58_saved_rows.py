#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact saved native rows and bounded edge brackets; never electrical acceptance."""
import copy,hashlib,json,math
from pathlib import Path
import numpy as np

BLOCK_SHA='7a9787a019bf460d31d40e23f94e76f51c9540cb0aafef465a1b82e8767ace64'
UI=125e-12
START=2e-9
STOP=START+258*UI
STEP=.3125e-12

def digest_bytes(b):return hashlib.sha256(b).hexdigest()

def measurement_source(source):
    assert digest_bytes(source.encode())=='12fffebb23c7478d0994c00bc0e6fc53e4842b09bfca496db59316c923e86ab2'
    block=''.join(source.splitlines(keepends=True)[274:333])
    assert len(block.encode())==6722 and digest_bytes(block.encode())==BLOCK_SHA
    # Original statements byte-exact; only a function wrapper and return added.
    wrapper='def replay(t,d,capture,bound,bits,offset,constant,devices,mos,caps):\n        r={}\n'+block+'        return r\n'
    return wrapper

def replay(source,t,d,capture,report):
    env=dict(np=np,UI=UI,START=START,STOP=STOP,STEP=STEP)
    exec(compile(measurement_source(source),'<immutable-CDR-measurements>','exec'),env)
    r=env['replay'](t,d,capture,report['binding'],report['source_bits'],report['data_offset_s'],False,report['devices'],report['mos_devices'],report['native_caps'])
    compare_reproduction(r,report)
    assert not r['devices_passed'] and not r['data_passed'] and not r['vi']['passed']
    return r

def compare_reproduction(reproduced,report):
    assert reproduced and set(reproduced)<=set(report)
    for key,value in reproduced.items():assert value==report[key],('Original measurement mismatch',key)

def topology(contract,planes,bound,requirements):
    devices={d['native_id']:d for d in contract['device_records']}
    assert len(devices)==500
    logical={}
    for p in planes['anchors']:
        pair=(p['native_cluster'],p['native_name'])
        assert logical.setdefault(p['logical_net'],pair)==pair
    assert logical['cp'][0]==27 and logical['cn'][0]==26
    failed=requirements['exact_failed_device_records']
    assert len(failed)==8 and len({d['native_id'] for d in failed})==8
    for expected in failed:
        actual=devices[expected['native_id']]
        assert actual['instance']==expected['instance'] and actual['model']==expected['model']
        assert actual['parameters']==expected['parameters']
        for a,e in zip(actual['terminals'],expected['terminals'],strict=True):
            assert all(a[k]==e[k] for k in ('terminal','node','anchor','native_cluster','native_net'))
    pairs=requirements['clock_mapping_requirement']['parallel_pairs']
    assert len(pairs)==16
    seen=set();clock={}
    for p in pairs:
        assert p['clock'] in ('cp','cn') and p['base_native_cluster']==logical[p['clock']][0]
        assert len(p['native_ids'])==2
        for ident,vector in zip(p['native_ids'],p['vectors'],strict=True):
            assert ident not in seen;seen.add(ident);d=devices[ident]
            assert d['model']=='npn13g2' and d['parameters']==dict(nx='2',we='0.070u',le='0.900u')
            terms={t['terminal']:t for t in d['terminals']}
            assert list(terms)==['C','B','E','S']
            for term,key in [('C','collector_native_cluster'),('B','base_native_cluster'),('E','emitter_native_cluster')]:
                assert terms[term]['native_cluster']==p[key]
                assert vector[term]=='v(xpd.'+terms[term]['node'].lower()+')'
            assert vector['native_id']==ident and vector['Ic']=='@q.xpd.'+d['instance'].lower()+'.qnpn13g2[ic]'
            name='xpd.'+d['instance'].lower()
            assert bound['groups']['npn13g2'][name]['native_id']==ident
            clock[ident]=dict(sampler=p['sampler'],clock=p['clock'],nodes=terms,vectors=vector,nx=2)
        receivers=sorted(d['native_id'] for d in devices.values() if d['model']=='npn13g2' and any(t['terminal']=='E' and t['native_cluster']==p['collector_native_cluster'] for t in d['terminals']))
        assert receivers==p['collector_drives_HBT_emitter_ids']
    assert seen==set(sum(requirements['clock_mapping_requirement']['physical_ids'].values(),[]))
    assert not seen.intersection(d['native_id'] for d in failed)
    return clock

def validate_rows(t,d,names):
    assert len(t)>1 and list(d)==names and len(names)==len(set(names))
    assert np.isfinite(t).all() and np.all(np.diff(t)>0)
    for name in names:assert d[name].shape==t.shape and np.isfinite(d[name]).all()

def point(t,d,row,names):
    assert isinstance(row,int) and 0<=row<len(t)
    return dict(row=row,time_s=float(t[row]),time_hex=float(t[row]).hex(),
                values={n:float(d[n][row]) for n in names},
                float64_le_hex={n:np.asarray(d[n][row],dtype='<f8').tobytes().hex() for n in names})

def bracket(t,d,x,names):
    assert math.isfinite(x) and t[0]<=x<=t[-1]
    hi=int(np.searchsorted(t,x))
    if hi<len(t) and t[hi]==x:
        return dict(requested_s=x,exact_native=True,rows=[point(t,d,hi,names)],interpolation=False)
    assert 0<hi<len(t) and t[hi-1]<x<t[hi]
    return dict(requested_s=x,exact_native=False,rows=[point(t,d,hi-1,names),point(t,d,hi,names)],
                interval_s=[float(t[hi-1]),float(t[hi])],interpolation=False,
                ambiguity='Requested time lies between two native rows; neither is relabelled as an exact sample.')

def crossings(t,signal,lo,hi,threshold=0.):
    assert signal.shape==t.shape and np.isfinite(signal).all() and math.isfinite(threshold) and lo<=hi
    # Strict sign transitions with an exact-zero plateau represented as one bracket.
    # No event filtering, hysteresis, fitted clock or inferred edge from device labels.
    x=signal-threshold;nonzero=np.flatnonzero(x!=0);events=[]
    for a,b in zip(nonzero[:-1],nonzero[1:],strict=True):
        if np.signbit(x[a])==np.signbit(x[b]):continue
        if t[b]<lo or t[a]>hi:continue
        assert a<b
        events.append(dict(left_row=int(a),right_row=int(b),left_s=float(t[a]),right_s=float(t[b]),
            left_value=float(signal[a]),right_value=float(signal[b]),threshold=threshold,
            direction='rising' if x[b]>x[a] else 'falling',
            linear_estimate_s=float(t[a]+(threshold-signal[a])*(t[b]-t[a])/(signal[b]-signal[a])),
            zero_plateau_rows=int(b-a-1),ordering_qualified=False))
    return events

def relation(a,b):
    if a['right_s']<b['left_s']:return 'a_definitely_before_b'
    if b['right_s']<a['left_s']:return 'b_definitely_before_a'
    return 'overlapping_native_brackets_order_ambiguous'

def hbt_point(t,d,row,name,dev):
    voltages=['v('+n+')' for n in dev['nodes'] if n!='0']
    current='@q.'+name+'.qnpn13g2[ic]'
    p=point(t,d,row,[*voltages,current])
    values=[0. if n=='0' else float(d['v('+n+')'][row]) for n in dev['nodes']]
    c,b,e,s=values
    p.update(C_v=c,B_v=b,E_v=e,S_v=s,VCE_v=c-e,VBE_v=b-e,
             Ic_a=float(d[current][row]),Ic_per_emitter_a=float(d[current][row])/dev['nx'],nx=dev['nx'])
    return p

def selected_names(report,clock):
    all_names=set(report['vectors']);names=set()
    for ident in [59,60,71,72,87,88,111,112,*clock]:
        dev=report['devices']['xpd.xd'+str(ident).zfill(4)]
        names.update('v('+n+')' for n in dev['nodes'] if n!='0')
        names.add('@q.xpd.xd'+str(ident).zfill(4)+'.qnpn13g2[ic]')
    names.update(['v(cp)','v(cn)','v(dp)','v(dn)','v(xp)','v(xn)','v(yp)','v(yn)','v(vip)','v(vin)'])
    names.update('v('+n+')' for n in report['binding']['aliases'].values())
    assert names<=all_names
    return sorted(names)

def cache(path,t,d,names):
    validate_rows(t,{n:d[n] for n in names},names)
    h=hashlib.sha256()
    with path.open('xb') as out:
        for first in range(0,len(t),1024):
            a=np.column_stack([t[first:first+1024],*[d[n][first:first+1024] for n in names]]).astype('<f8',copy=False)
            raw=a.tobytes(order='C');out.write(raw);h.update(raw)
    expected=dict(rows=len(t),columns=['time',*names],bytes=len(t)*(1+len(names))*8,sha256=h.hexdigest(),dtype='<f8',all_native_rows_retained=True)
    verify_cache(path,t,d,expected)
    return expected

def verify_cache(path,t,d,meta):
    assert meta['columns'][0]=='time' and len(meta['columns'])==len(set(meta['columns']))
    names=meta['columns'][1:];assert set(names)<=set(d)
    assert meta['rows']==len(t) and meta['bytes']==path.stat().st_size==len(t)*len(meta['columns'])*8
    with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==meta['sha256']
    mm=np.memmap(path,mode='r',dtype='<f8',shape=(len(t),len(meta['columns'])))
    for first in range(0,len(t),1024):
        actual=mm[first:first+1024]
        expected=np.column_stack([t[first:first+1024],*[d[n][first:first+1024] for n in names]]).astype('<f8',copy=False)
        assert actual.tobytes()==expected.tobytes(),'Selected cache changed native float64 bits'
    del mm

def diagnose(t,d,report,clock,requirements):
    failed={}
    active=np.flatnonzero(t>=START)
    for ident in [59,60,71,72,87,88,111,112]:
        name='xpd.xd'+str(ident).zfill(4);dev=report['devices'][name]
        assert dev['nx']==4
        vc,vb,ve=[d['v('+n+')'] for n in dev['nodes'][:3]]
        current=d['@q.'+name+'.qnpn13g2[ic]']
        rows=dict(max_abs_vce=int(np.argmax(abs(vc-ve))),max_abs_vbe=int(np.argmax(abs(vb-ve))),
                  max_abs_ic_per_emitter=int(np.argmax(abs(current))),min_active_vce=int(active[np.argmin((vc-ve)[active])]))
        observed={k:hbt_point(t,d,i,name,dev) for k,i in rows.items()}
        old=report['device_checks'][name]
        assert abs(observed['max_abs_vce']['VCE_v'])==old['maximum_alltime_abs_vce_v']
        assert abs(observed['max_abs_vbe']['VBE_v'])==old['maximum_alltime_abs_vbe_v']
        assert abs(observed['max_abs_ic_per_emitter']['Ic_per_emitter_a'])==old['maximum_alltime_abs_ic_per_emitter_a']
        assert observed['min_active_vce']['VCE_v']==old['minimum_active_vce_v']
        failed[str(ident)]=dict(role=requirements['failed_roles'][str(ident)],same_row_extrema=observed)
    parent=crossings(t,d['v(cp)']-d['v(cn)'],START,STOP)
    pairs=[]
    for p in requirements['clock_mapping_requirement']['parallel_pairs']:
        records=[]
        for ident in p['native_ids']:
            name='xpd.xd'+str(ident).zfill(4);dev=report['devices'][name]
            vv=clock[ident]['vectors'];b=d[vv['B']];other='v(cn)' if p['clock']=='cp' else 'v(cp)'
            local=crossings(t,b-d[other],START,STOP)
            records.append(dict(id=ident,clock=p['clock'],
                terminal_base_vs_opposite_parent_clock=local,
                caveat='Base-versus-opposite-parent comparison is not an ideal local differential pair; each distinct native base remains separately recorded.',
                parent_edges=[dict(parent_edge=e,bracket_rows=[hbt_point(t,d,e['left_row'],name,dev),hbt_point(t,d,e['right_row'],name,dev)]) for e in parent]))
        pairs.append(dict(native_topology=p,devices=records))
    # Native differential base crossings for each physical shared-tail complementary
    # branch: all Cartesian accesses retained (parallel bases are distributed nodes).
    branches=[]
    grouping={}
    for p in requirements['clock_mapping_requirement']['parallel_pairs']:
        grouping.setdefault((p['sampler'],p['emitter_native_cluster']),[]).append(p)
    for (sampler,tail),ps in grouping.items():
        assert len(ps)==2 and {p['clock'] for p in ps}=={'cp','cn'}
        cp=next(p for p in ps if p['clock']=='cp');cn=next(p for p in ps if p['clock']=='cn')
        for ip in cp['native_ids']:
            for inn in cn['native_ids']:
                bp=clock[ip]['vectors']['B'];bn=clock[inn]['vectors']['B']
                ev=crossings(t,d[bp]-d[bn],START,STOP)
                cpv=clock[ip]['vectors']['C'];cnv=clock[inn]['vectors']['C']
                output_events=crossings(t,d[cpv]-d[cnv],START,STOP)
                for item in [*ev,*output_events]:
                    item['same_native_row_devices']=[
                        dict(cp=hbt_point(t,d,index,'xpd.xd'+str(ip).zfill(4),report['devices']['xpd.xd'+str(ip).zfill(4)]),
                             cn=hbt_point(t,d,index,'xpd.xd'+str(inn).zfill(4),report['devices']['xpd.xd'+str(inn).zfill(4)]))
                        for index in (item['left_row'],item['right_row'])]
                branches.append(dict(sampler=sampler,tail_cluster=tail,cp_id=ip,cn_id=inn,
                    actual_base_vectors=[bp,bn],events=ev,actual_collector_vectors=[cpv,cnv],collector_events=output_events,
                    collector_to_base_relations=[dict(collector_index=i,base_indices=[j for j,x in enumerate(ev) if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI],
                        relations=[relation(x,e) for x in ev if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI]) for i,e in enumerate(output_events)],
                    parent_relations=[dict(parent_index=i,local_indices=[j for j,x in enumerate(ev) if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI],
                        relations=[relation(e,x) for x in ev if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI]) for i,e in enumerate(parent)]))
    settling={}
    bits=report['source_bits'];offset=report['data_offset_s']
    expected=dict(a=bits[1:],b=bits[1:] if offset<0 else bits[:-1],c=bits[:-1],d=bits[1:] if offset<0 else bits[:-1])
    for tag in 'abcd':
        vp='v('+report['binding']['aliases']['xpd.'+tag+'qp']+')';vn='v('+report['binding']['aliases']['xpd.'+tag+'qn']+')'
        diff=d[vp]-d[vn];rows=[]
        for i,bit in enumerate(expected[tag],1):
            edge=START+(i+(0 if tag=='b' else .5))*UI
            sign=2*bit-1;ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[diff[ids]*sign<.1]
            delay=0. if not len(bad) else float(t[bad[-1]]-edge+STEP)
            assert delay==report['sampler_checks'][tag]['clock_to_valid_by_bit_s'][i-1]
            rows.append(dict(bit_index=i,expected_bit=bit,ideal_source_edge_s=edge,
                fixed_points=[dict(phase_ui=phase,bracket=bracket(t,d,edge+phase*UI,[vp,vn,'v(cp)','v(cn)'])) for phase in (-.05,0,.3,.6,.9)],
                native_100mV_crossings=crossings(t,diff*sign,edge,edge+.95*UI,.1),
                last_bad_native_row=None if not len(bad) else point(t,d,int(bad[-1]),[vp,vn,'v(cp)','v(cn)']),
                original_clock_to_valid_s=delay))
        settling[tag]=rows
    return dict(status='DIAGNOSTIC_ONLY_ORIGINAL_ELECTRICAL_REJECTION_REPRODUCED',
        same_row_failed_devices=failed,parent_clock_native_crossing_brackets=parent,
        actual_parallel_clock_pairs=pairs,actual_shared_tail_base_differences=branches,sampler_settling=settling,
        interpolation_used_for_new_diagnostic=False,event_filtering=False,phase_fitting=False,
        original_measurement_interpolation_preserved=True,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
