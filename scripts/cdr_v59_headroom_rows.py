#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same native row headroom budgets; observational evidence, never a circuit verdict."""
import hashlib,json
from pathlib import Path
import numpy as np
import cdr_v58_saved_rows as rows
TARGETS=(61,62,115,116)
BRANCHES=(
 dict(name='D_cn',cn=[61,62],cp=[64,65],upper=[54,56],mos=[3,4,5,6],bleed=179,bias='ird'),
 dict(name='C_cn',cn=[115,116],cp=[118,119],upper=[106,108],mos=[32,33,34,35],bleed=217,bias='irc'))
def name(i):return 'xpd.xd'+str(i).zfill(4)
def terminals(record):return {t['terminal']:t for t in record['terminals']}
def vector(bound,i,terminal):
    dev=next(d for group in bound['groups'].values()for d in group.values()if d['native_id']==i)
    order={'npn13g2':['C','B','E','S'],'sg13_lv_nmos':['D','G','S','B'],'rppd':['rppd_1','rppd_2','rppd_sub']}
    kind=next(k for k,g in bound['groups'].items()if name(i)in g)
    n=dev['nodes'][order[kind].index(terminal)]
    assert n!='0','Selected physical terminal unexpectedly aliases ideal ground'
    return 'v('+n+')'
def current_vector(record):
    if record['model']=='npn13g2':return '@q.'+name(record['native_id'])+'.qnpn13g2[ic]'
    if record['model']=='sg13_lv_nmos':return '@n.'+name(record['native_id'])+'.nsg13_lv_nmos[ids]'
    return None
def topology(contract,bound):
    records={d['native_id']:d for d in contract['device_records']}
    assert len(records)==len(contract['device_records'])==500
    for i,r in records.items():
        b=bound['groups'][r['model']][name(i)]
        assert b['native_id']==i and b['parameters']==r['parameters']
        expected=[bound['interface'].get(t['node'],'xpd.'+t['node'].lower())for t in r['terminals']]
        assert b['nodes']==expected
    def key(i,p):return tuple(terminals(records[i])[p][k]for k in ('native_cluster','native_net'))
    branches=[];selected=set()
    for spec in BRANCHES:
        b=dict(spec);a=spec['cn'][0];collector=key(a,'C');tail=key(a,'E')
        for i in spec['cn']:
            assert records[i]['model']=='npn13g2'and records[i]['parameters']['nx']=='2'
            assert key(i,'B')[1]=='cn'and key(i,'C')==collector and key(i,'E')==tail
        for i in spec['cp']:
            assert records[i]['model']=='npn13g2'and records[i]['parameters']['nx']=='2'
            assert key(i,'B')[1]=='cp'and key(i,'E')==tail
        for i in spec['upper']:
            assert records[i]['model']=='npn13g2'and records[i]['parameters']['nx']=='4'
            assert key(i,'E')==collector
        assert sorted(i for i,r in records.items()if r['model']=='npn13g2'and key(i,'E')==collector)==spec['upper']
        assert sorted(i for i,r in records.items()if r['model']=='sg13_lv_nmos'and key(i,'D')==tail)==spec['mos']
        for i in spec['mos']:
            assert records[i]['parameters']['w']=='36u'and records[i]['parameters']['l']=='0.3u'
            assert key(i,'G')[1]==spec['bias']and key(i,'S')[1]=='avss'
        r=records[spec['bleed']]
        assert r['model']=='rppd'and r['parameters']==dict(w='1u',l='38.4u',ps='0u',b='0',m='1',sw_et='1')
        assert key(spec['bleed'],'rppd_1')==collector and key(spec['bleed'],'rppd_2')[1]=='avss'
        # Include every directly incident physical terminal at upper C/B, collector,
        # tail and bias nets; never substitute one logical-net alias for accesses.
        nets={collector,tail,*[key(i,p)for i in spec['upper']for p in ('C','B')],
              *[key(i,'G')for i in spec['mos']]}
        neighbors=sorted(i for i,r in records.items()if any((t['native_cluster'],t['native_net'])in nets for t in r['terminals'])and r['model']in ('npn13g2','sg13_lv_nmos','rppd'))
        b.update(collector=collector,tail=tail,incident_ids=neighbors)
        selected.update(neighbors+spec['cp']+spec['cn']);branches.append(b)
    assert {i for b in branches for i in b['cn']}==set(TARGETS)
    return records,branches,sorted(selected)
def names_for(records,selected,bound):
    names={'v(avdd)','v(cn)','v(cp)','v(irc)','v(ird)'}
    for i in selected:
        kind=records[i]['model'];dev=bound['groups'][kind][name(i)]
        names.update('v('+n+')'for n in dev['nodes']if n!='0')
        cur=current_vector(records[i])
        if cur:names.add(cur)
    return sorted(names)
def current_sum(d,records,ids):
    assert ids and len(ids)==len(set(ids))
    vv=[current_vector(records[i])for i in ids]
    assert None not in vv and len(vv)==len(set(vv))
    return sum((d[v]for v in vv),np.zeros_like(d[vv[0]]))
def intervals(t,signal,start,limit):
    assert t.shape==signal.shape and np.isfinite(signal).all()
    ids=np.flatnonzero((t>=start)&(signal<limit));out=[]
    if not len(ids):return out
    for run in np.split(ids,np.flatnonzero(np.diff(ids)!=1)+1):
        a,z=int(run[0]),int(run[-1]);worst=int(run[np.argmin(signal[run])])
        before=a-1 if a>0 else None;after=z+1 if z+1<len(t)else None
        out.append(dict(first=a,last=z,worst=worst,native_rows=len(run),
            before=before,after=after,first_s=float(t[a]),last_s=float(t[z]),
            observed_span_s=float(t[z]-t[a]),minimum_v=float(signal[worst]),
            boundary_times_interpolated=False))
    assert sum(x['native_rows']for x in out)==len(ids)
    return out
def budget(c,b,e,uc,ue,dd):
    vals=(c,b,e,uc,ue,dd);assert all(np.isfinite(x)for x in vals)
    result=dict(VCE_v=c-e,VBE_v=b-e,VCB_v=c-b,
        supply_to_upper_C_v=dd-uc,upper_VCE_v=uc-ue,
        upper_E_to_target_C_access_v=ue-c,target_E_above_ideal_ground_v=e)
    reconstruction=dd-result['supply_to_upper_C_v']-result['upper_VCE_v']-result['upper_E_to_target_C_access_v']-e
    # Numerical arithmetic identity only, never an electrical tolerance waiver.
    assert np.isclose(reconstruction,c-e,rtol=0,atol=32*np.finfo(float).eps*max(1.,*map(abs,vals)))
    result['reconstruction_v']=reconstruction
    result['required_VCE_recovery_to_original_0p4_v']=max(0.,.4-(c-e))
    return result
def frame(t,d,row,records,branches,selected,bound):
    p=rows.point(t,d,row,names_for(records,selected,bound));budgets=[]
    for b in branches:
        currents={label:sum(float(d[current_vector(records[i])][row])for i in b[key])for label,key in [('cn_Ic_a','cn'),('cp_Ic_a','cp'),('upper_Ic_a','upper'),('tail_Ids_a','mos')]}
        for i in b['cn']:
            C,B,E=(float(d[vector(bound,i,k)][row])for k in ('C','B','E'))
            for upper in b['upper']:
                UC,UE=(float(d[vector(bound,upper,k)][row])for k in ('C','E'))
                item=budget(C,B,E,UC,UE,float(d['v(avdd)'][row]))
                item.update(target=i,upper=upper,branch=b['name'],currents=currents,
                    target_Ic_a=float(d[current_vector(records[i])][row]),
                    base_to_parent_cn_v=B-float(d['v(cn)'][row]),
                    tail_drain_to_target_E_v={str(m):float(d[vector(bound,m,'D')][row])-E for m in b['mos']},
                    bleed_terminal_voltage_v=float(d[vector(bound,b['bleed'],'rppd_1')][row]-d[vector(bound,b['bleed'],'rppd_2')][row]),
                    bleed_current_a=None,complete_KCL=False)
                budgets.append(item)
    p['headroom_paths']=budgets
    return p
def diagnostic(t,d,report,contract):
    records,branches,selected=topology(contract,report['binding'])
    names=names_for(records,selected,report['binding'])
    assert set(names)<=set(report['vectors'])
    rows.validate_rows(t,{n:d[n]for n in names},names)
    assert t[0]==0 and abs(t[-1]-rows.STOP)<1e-18
    assert float(np.diff(t).max())<=rows.STEP*1.00001
    active=np.flatnonzero(t>=rows.START);assert len(active)
    chosen=set();targets={}
    for i in TARGETS:
        vc=d[vector(report['binding'],i,'C')];ve=d[vector(report['binding'],i,'E')];vce=vc-ve
        worst=int(active[np.argmin(vce[active])])
        assert float(vce[worst])==report['device_checks'][name(i)]['minimum_active_vce_v']
        spans=intervals(t,vce,rows.START,.4);assert spans and vce[worst]<.4
        rr={worst}
        for q in spans:rr.update(x for x in (q['first'],q['last'],q['worst'],q['before'],q['after'])if x is not None)
        for x in list(rr):chosen.update(range(max(0,x-1),min(len(t),x+2)))
        targets[str(i)]=dict(worst_native_row=worst,minimum_VCE_v=float(vce[worst]),
            failing_native_rows=sum(q['native_rows']for q in spans),all_violation_intervals=spans,
            minimum_frame=frame(t,d,worst,records,branches,selected,report['binding']))
    parent=rows.crossings(t,d['v(cp)']-d['v(cn)'],rows.START,rows.STOP)
    events=[]
    for b in branches:
        cn=current_sum(d,records,b['cn']);cp=current_sum(d,records,b['cp'])
        bases=[dict(cp_id=p,cn_id=n,events=rows.crossings(t,d[vector(report['binding'],p,'B')]-d[vector(report['binding'],n,'B')],rows.START,rows.STOP))for p in b['cp']for n in b['cn']]
        current_events=rows.crossings(t,cp-cn,rows.START,rows.STOP)
        for event in [*parent,*current_events,*[e for pair in bases for e in pair['events']]]:
            chosen.update((event['left_row'],event['right_row']))
        events.append(dict(branch=b['name'],all_current_crossings=current_events,all_four_local_base_pairs=bases))
    return dict(status='SAME_NATIVE_ROWS_HEADROOM_OBSERVATIONS_ONLY',
        targets=targets,topology=branches,selected_native_ids=selected,selected_vectors=names,
        selected_records=[records[i]for i in selected],frame_rows=sorted(chosen),
        parent_clock_events=parent,branch_events=events,
        original_electrical_rejection_preserved=True,new_simulation=False,
        accepted=False,cdr_accepted=False,qualified_pex=False,full_phy_accepted=False,
        interpolation=False,phase_fitting=False,causality_proven=False,
        unsaved=['HBT Ib/Ie','intrinsic rppd current','unsaved internal wire voltages','complete dynamic KCL'])
def write_frames(path,t,d,diagnosis,report,contract):
    records,branches,selected=topology(contract,report['binding'])
    assert diagnosis['selected_native_ids']==selected
    count=0
    with Path(path).open('xb')as out:
        for row in diagnosis['frame_rows']:
            out.write((json.dumps(frame(t,d,row,records,branches,selected,report['binding']),sort_keys=True,allow_nan=False)+'\n').encode());count+=1
    with Path(path).open('rb')as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(rows=count,bytes=Path(path).stat().st_size,sha256=digest,format='complete separate JSONL; not embedded in compact result')
