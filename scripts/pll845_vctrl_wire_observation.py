#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe actual modeled metal currents; never infer MOS current from duty."""
import copy, hashlib, io, json, os, re, subprocess, tarfile
from pathlib import Path
import numpy as np

REPO = 'Melihakbulut221/nssoc'
ASSETS = {
    'model': (658048609, '154e2f2f8a49c98459f3f34f61e3b1552eef6370c5c6dfc1b13fe116782330bd'),
    'reader': (667303791, '334bc671b5e57d34c76f790555fe88b8c623a9307aa94d20261ebfe1a5ae8af6'),
}
MODEL_SHA = '27c0642acb26d35c901cf61198127b8d0f2621259ac8504780fbfac577244c8b'
RAW_SHA = '4646ad014fb3cf44b06adf6b9ec7b29a9ed50011ea7214f4223d1c9acff314d1'
EXPECTED = {('XD0187','D'), ('XD0376','D'), ('XD0567','rppd_2'),
            ('XD0568','rppd_1'), ('XD0574','mim_top'),
            *{(d,'G') for d in ('XD0320','XD0333','XD0334','XD0335')}}

def digest(b): return hashlib.sha256(b).hexdigest()

def members(which):
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    aid, expected = ASSETS[which]
    b = subprocess.check_output(['gh','api',f'repos/{REPO}/releases/assets/{aid}',
                                 '-H','Accept: application/octet-stream'])
    assert digest(b) == expected, ('Immutable archive mismatch', which)
    with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as archive:
        wanted = ['pll845-mim-wire.spice'] if which == 'model' else [
            'prepared/composition/composition.json', 'prepared/terminal-instrumentation.json',
            'header/native-header.txt', 'original-reader-result.json']
        result = {}
        for suffix in wanted:
            matches = [m for m in archive.getmembers() if m.name.endswith('/'+suffix)]
            assert len(matches) == 1 and matches[0].isfile(), suffix
            result[suffix] = archive.extractfile(matches[0]).read()
    return result

def plan(model, comp, instrumentation, names):
    assert digest(model.encode()) == MODEL_SHA, 'Changed actual wire model'
    assert len(comp['device_records']) == 845
    assert comp['counts'] == dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
    assert len(names) == 5106 and len(set(names)) == 5106
    rows = [line.split() for line in model.splitlines() if line and not line.startswith('*')]
    resistors = [r for r in rows if r[0].startswith('R')]
    caps = [r for r in rows if r[0].startswith('C')]
    assert len(resistors) == 3381 and len(caps) == 5105
    assert all(len(r)==4 and np.isfinite(float(r[3])) and float(r[3])>0 for r in resistors+caps)
    cards={r[0]:r for r in rows if r[0].startswith('XD')}
    assert len(cards)==845
    for d in comp['device_records']:
        prefix=[d['instance'],*[t['node'] for t in d['terminals']],d['model']]
        assert cards[d['instance']][:len(prefix)]==prefix, ('Model terminal binding',d['instance'])
        assert set(cards[d['instance']][len(prefix):])=={k+'='+v for k,v in d['parameters'].items()}, ('Model parameter binding',d['instance'])
    terminals = []
    for d in comp['device_records']:
        for terminal in d['terminals']:
            if terminal['native_cluster'] == 480:
                terminals.append(dict(instance=d['instance'], terminal=terminal['terminal'],
                                      node=terminal['node'], model=d['model']))
    assert {(t['instance'],t['terminal']) for t in terminals} == EXPECTED
    assert len(terminals) == len({t['node'] for t in terminals}) == 9
    nodes = {'vctrl'}
    while True:
        grown = nodes | {n for r in resistors if nodes.intersection(r[1:3]) for n in r[1:3]}
        if grown == nodes: break
        nodes = grown
    assert all(t['node'] in nodes for t in terminals)
    actual = {(d['instance'],t['terminal']) for d in comp['device_records']
              for t in d['terminals'] if t['node'] in nodes}
    assert actual == EXPECTED, ('Other native terminals on modeled control network', actual)
    interface = set(comp['interface'])
    assert nodes & interface == {'vctrl'}, 'Unexpected driven/public control network pin'
    selected_r = [r for r in resistors if r[1] in nodes or r[2] in nodes]
    assert all(r[1] in nodes and r[2] in nodes for r in selected_r)
    selected_c = [r for r in caps if r[1] in nodes or r[2] in nodes]
    assert all((r[1] in nodes and r[2]=='wire_cref') or
               (r[2] in nodes and r[1]=='wire_cref') for r in selected_c)
    external = instrumentation['external_mapping']
    assert external['vctrl'] == 'vctrl' and external['wire_cref']=='wire_cref'
    def vector(n):
        return 'v('+external[n].lower()+')' if n in external else 'v(xloop.'+n.lower()+')'
    vector_map = {n:vector(n) for n in sorted(nodes | {'wire_cref'})}
    assert set(vector_map.values()) <= set(names), 'Missing actual wire-node voltage column'
    leaves = {t['node'] for t in terminals}
    for terminal in terminals:
        node = terminal['node']
        rr = [r for r in selected_r if node in r[1:3]]
        assert rr and all(not ({r[1],r[2]}-{node}) & leaves for r in rr)
        terminal['outgoing_resistors'] = [
            dict(name=r[0], positive=node, negative=r[2] if r[1]==node else r[1],
                 ohms=float(r[3]), original_record=' '.join(r)) for r in rr]
        terminal['local_shunt_caps'] = [r for r in selected_c if node in r[1:3]]
    for dev, expected_r in [('XD0187','R3379'),('XD0376','R3380')]:
        rr=next(t for t in terminals if t['instance']==dev)['outgoing_resistors']
        assert len(rr)==1 and rr[0]['name']==expected_r and rr[0]['ohms']==53.7174
    interior = nodes-leaves
    return dict(model_sha256=MODEL_SHA, raw_sha256=RAW_SHA, native_cluster=480,
                terminals=terminals, modeled_network_nodes=sorted(nodes),
                vector_map=vector_map, interior_nodes=sorted(interior),
                interior_caps=[r for r in selected_c if (set(r[1:3]) & interior)],
                modeled_resistors=selected_r, modeled_caps=selected_c,
                current_sign='Positive from native-device metal terminal into interior VCTRL wire network.',
                scope='Actual modeled wire-branch current only. Local terminal shunt capacitance is outside the cut. No MOS channel-current or qualified physical PEX claim.')

def inputs():
    a=members('model'); b=members('reader')
    model=a['pll845-mim-wire.spice'].decode()
    comp=json.loads(b['prepared/composition/composition.json'])
    inst=json.loads(b['prepared/terminal-instrumentation.json'])
    header=b['header/native-header.txt'].decode()
    table=re.findall(r'(?m)^\s*(\d+)\s+(\S+)\s+(time|voltage|current)\s*$',header)
    assert [int(r[0]) for r in table]==list(range(5106)), 'Exact native header census'
    names=[r[1] for r in table]
    old=json.loads(b['original-reader-result.json'])
    assert old['status']=='REJECTED_ORIGINAL_FULL845_ACQUISITION_GATES'
    assert old['full_capture'] and old['capture']['raw_sha256']==RAW_SHA
    return model,comp,inst,names,old

def binding_controls(model,comp,inst,names):
    result=plan(model,comp,inst,names); rejected=[]
    cases=[]
    bad=copy.deepcopy(comp);next(d for d in bad['device_records'] if d['instance']=='XD0187')['terminals'][0]['native_cluster']=481
    cases.append(('wrong_native_owner',model,bad,inst,names))
    bad=copy.deepcopy(comp);next(d for d in bad['device_records'] if d['instance']=='XD0187')['terminals'][0]['node']='absent'
    cases.append(('missing_terminal_node',model,bad,inst,names))
    cases.append(('missing_raw_node',model,comp,inst,[n if n!='v(xloop.w_t187_d)' else 'absent' for n in names]))
    cases.append(('duplicate_column',model,comp,inst,names[:-1]+[names[0]]))
    cases.append(('changed_actual_resistance',model.replace('53.7174','53.7175',1),comp,inst,names))
    bad=copy.deepcopy(inst);bad['external_mapping']['vctrl']='wrong'
    cases.append(('changed_public_mapping',model,comp,bad,names))
    for label,m,c,i,n in cases:
        try:plan(m,c,i,n)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Fault accepted: '+label)
    return result,dict(rejected=rejected,actual_model_and_header_bound=True)

def integrate(t,y):
    assert t.ndim==y.ndim==1 and len(t)==len(y)>1
    assert np.isfinite(t).all() and np.isfinite(y).all() and np.all(np.diff(t)>0)
    return float(np.sum((y[1:]+y[:-1])*.5*np.diff(t),dtype=np.float64))

def numeric_controls():
    t=np.array([0.,.1,.35,.7,1.],dtype='<f8')
    current=2*t+3
    assert integrate(t,current)==4.
    assert integrate(t,-current)==-4.
    rejected=[]
    for name,ts,ys in [('nonfinite',t,np.array([0.,1.,np.nan,2.,3.])),
                       ('nonmonotonic',t[::-1],current),('missing',t,current[:-1])]:
        try:integrate(ts,ys)
        except AssertionError:rejected.append(name)
        else:raise AssertionError(name)
    return dict(irregular_grid_linear_integral=True,sign_control=True,rejected=rejected)

def observe(names,values,binding,out,progress):
    assert values.shape==(3201410,5106) and values.dtype==np.dtype('<f8')
    wanted=list(dict.fromkeys(['time','v(vctrl)','v(up)','v(down)','v(reference)','v(fb)',
                              *binding['vector_map'].values()]))
    assert set(wanted)<=set(names)
    indices=[names.index(n) for n in wanted]
    selected=np.empty((len(values),len(wanted)),dtype='<f8')
    h=hashlib.sha256()
    for start in range(0,len(values),4096):
        stop=min(start+4096,len(values))
        block=np.take(values[start:stop],indices,axis=1)
        assert np.isfinite(block).all()
        selected[start:stop]=block
        assert np.array_equal(selected[start:stop].view('<u8'),block.view('<u8'))
        h.update(block.tobytes())
        if start%(4096*64)==0:progress('COPY_NATIVE_VCTRL_WIRE_COLUMNS',rows_done=stop,rows_total=len(values))
    np.save(out/'original-vctrl-columns.npy',selected,allow_pickle=False)
    (out/'original-vctrl-column-names.json').write_text(json.dumps(wanted,indent=2)+'\n')
    data={n:selected[:,i] for i,n in enumerate(wanted)}
    t=data['time'];assert t[0]==0 and abs(t[-1]-1e-6)<1e-15 and np.all(np.diff(t)>0)
    volt={n:data[v] for n,v in binding['vector_map'].items()}
    currents={}
    for terminal in binding['terminals']:
        label=terminal['instance']+'.'+terminal['terminal']
        currents[label]=sum((volt[r['positive']]-volt[r['negative']])/r['ohms']
                            for r in terminal['outgoing_resistors'])
    total=sum(currents.values())
    charge=np.zeros(len(t),dtype='<f8')
    for r in binding['interior_caps']:
        node=r[1] if r[1]!='wire_cref' else r[2]
        charge+=float(r[3])*(volt[node]-volt['wire_cref'])
    windows=[]
    for start,stop in [(0.,1e-6)]+[(i*1e-7,(i+1)*1e-7) for i in range(10)]:
        lo=int(np.searchsorted(t,start,side='left'));hi=int(np.searchsorted(t,stop,side='right'))
        tw=t[lo:hi];assert len(tw)>1
        interval=float(tw[-1]-tw[0])
        branch={}
        for label,cur in currents.items():
            y=cur[lo:hi];q=integrate(tw,y)
            branch[label]=dict(minimum_a=float(y.min()),maximum_a=float(y.max()),
                               charge_c=q,time_mean_a=q/interval)
        qin=integrate(tw,total[lo:hi]);dq=float(charge[hi-1]-charge[lo])
        # A coarsened quadrature is an error indicator, not a replacement capture or certified error bound.
        index=np.unique(np.r_[np.arange(lo,hi,2),hi-1])
        coarse=integrate(t[index],total[index])
        windows.append(dict(requested_start_s=start,requested_end_s=stop,
                            first_native_s=float(tw[0]),last_native_s=float(tw[-1]),native_rows=len(tw),
                            branch=branch,net_wire_charge_c=qin,interior_cap_delta_charge_c=dq,
                            wire_kcl_quadrature_residual_c=qin-dq,
                            coarsened_quadrature_difference_c=coarse-qin))
    report=dict(status='COMPLETE_ORIGINAL_SAMPLE_MODELED_WIRE_CURRENT_OBSERVATION_NOT_PLL_ACCEPTANCE',
                raw_sha256=RAW_SHA,rows=len(t),original_columns=len(names),selected_columns=wanted,
                selected_row_major_sha256=h.hexdigest(),exact_original_sample_bits=True,
                native_samples_removed=0,interpolated_samples=0,windows=windows,
                acquisition_accepted=False,full_phy_accepted=False,qualified_pex=False,
                current_scope=binding['scope'],
                integration_scope='Trapezoidal quadrature over original adaptive samples only. Window endpoints are actual included samples; no boundary interpolation. KCL residual and coarse quadrature difference reported, not converted to a reliability or acquisition pass.')
    (out/'wire-current-observation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
