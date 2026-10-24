#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only phase55 child-load bench: fixed clocks, actual devices, no reset claim."""
import argparse,hashlib,json,math,re
from pathlib import Path
import numpy as np
import build_pcie_local_vco_hybrid_v6 as compact
MODEL_SHA='18c980350b1d3ea298e36462f3954155ac0022306645e42b38caacccbd8e08b6'
RC_RUN=40086006467
RC_SUMMARY='f93c6fcd7d454657ddca46986320d336cde713c6f7c7eb9389b16c9505a84b95'
RC_PARTS='e501214075a8d1e76a4d087eb2e6c4528386501731ba8e64019e20844b5b4198'
PORTS=['CLKP','CLKN','MP','MN','QP','QN','DIV_AVDD','AVSS','SUB','wire_cref']
UI=125e-12;START=2e-9;STOP=34e-9;STEP=.3125e-12
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def clock_points(cm,amplitude,invert=False):
    """The external test source is the original fixed 4GHz timing, not a PLL."""
    assert math.isfinite(cm)and math.isfinite(amplitude)and 0<cm-amplitude<cm+amplitude<=2.5
    def level(n):return cm+amplitude*((-1 if n%2 else 1)*(-1 if invert else 1))
    points=[(0.,0.),(1e-9,level(0))]
    for i in range(1,257):
        edge=START+i*UI
        if edge>=STOP:break
        points.extend(((edge,level(i-1)),(edge+10e-12,level(i))))
    points.append((STOP,points[-1][1]))
    assert all(b[0]>a[0]for a,b in zip(points,points[1:]))
    return points
def validate_boundary(boundary):
    # No amplitude/common-mode defaults. A controller must bind these exact
    # scalars to the completed, hash-verified observer before any native run.
    required={'source_run','summary_sha256','measurement_pair','saved_vectors',
              'common_mode_v','single_ended_amplitude_v','observed_window_s',
              'exact_observer_field_paths','frequency_hz','use'}
    assert set(boundary)==required
    assert boundary['source_run']==40084454916
    assert re.fullmatch('[0-9a-f]{64}',boundary['summary_sha256'])
    assert boundary['measurement_pair']=='div1_first_div2'
    assert boundary['saved_vectors']==['v(xloop.w_t398_c)','v(xloop.w_t389_c)']
    assert boundary['frequency_hz']==4e9
    assert boundary['use']=='isolated_fixed_frequency_test_not_PLL_replay'
    assert len(boundary['observed_window_s'])==2 and all(math.isfinite(x) for x in boundary['observed_window_s']) and boundary['observed_window_s'][1]>boundary['observed_window_s'][0]>=0
    assert set(boundary['exact_observer_field_paths'])=={'common_mode_v','single_ended_amplitude_v'}
    assert all(isinstance(v,str)and v for v in boundary['exact_observer_field_paths'].values())
    clock_points(boundary['common_mode_v'],boundary['single_ended_amplitude_v'])
def validate_paths(*paths):
    assert all(not any(c in str(p) for c in ('"','\n','\r','\x00')) for p in paths)
def prepare(model_text,rc_summary_text,boundary,model_path,model_directory,r3_osdi):
    validate_boundary(boundary)
    assert digest(rc_summary_text)==RC_SUMMARY
    rc_summary=json.loads(rc_summary_text)
    assert digest(model_text)==MODEL_SHA
    assert rc_summary['status']=='PASS_NATIVE55_FOUR_MIM_TWO_PRECISE_ORDERS_22_CONTROLS_EACH_AND19_COMPOSITION_CONTROLS_REQUIRES_LOADED_PHASE'
    assert rc_summary['both_native_orders_verified']and rc_summary['native_rc_and_device_records_equal_in_both_orders']and rc_summary['sources_unchanged']
    c=rc_summary['composition'];assert c['model_sha256']==MODEL_SHA and len(c['controls'])==19 and all(x['rejected']for x in c['controls'])
    assert c['positive']==dict(devices=55,wire_resistors=238,wire_capacitors=410,terminals=168,wire_components=24,body_nodes=1,ports=PORTS)
    rows=compact.statements(model_text);assert rows[0][0].lower()=='.subckt'and rows[0][2:]==PORTS and rows[-1][0].lower()=='.ends'and rows[-1][1]==rows[0][1]
    top=rows[0][1];devices=[r for r in rows[1:-1]if r[0].startswith('XD')]
    assert len(devices)==55 and sum('cap_cmim'in r for r in devices)==4
    hbts=[r for r in devices if r[5]=='npn13G2'];assert len(hbts)==19
    # Every output pair sees one complete real downstream divider, not an
    # ideal capacitor, a guessed input impedance or a terminal short.
    instances=[
      ('xdut',['clkp','clkn','mp','mn','qp','qn','avdd','0','0','0']),
      ('xloadm',['mp','mn','m_mp','m_mn','m_qp','m_qn','avdd','0','0','0']),
      ('xloadq',['qp','qn','q_mp','q_mn','q_qp','q_qn','avdd','0','0','0'])]
    bindings={};vectors=set()
    for instance,actual in instances:
        ports={p.lower():n.lower()for p,n in zip(PORTS,actual,strict=True)}
        def node(n):return ports.get(n.lower(),instance+'.'+n.lower())
        for row in hbts:
            name=instance+'.'+row[0].lower()
            record=dict(terminals=[node(n)for n in row[1:5]],nx=int(next(p.split('=')[1]for p in row[6:]if p.startswith('Nx='))))
            assert record['nx']in (1,2,4);bindings[name]=record
            vectors.update('v('+n+')'for n in record['terminals']if n!='0')
            vectors.add('@q.'+name+'.qnpn13g2[ic]')
        vectors.update('v('+n+')'for n in actual if n!='0')
    assert len(bindings)==57
    vectors=sorted(vectors)
    libraries=Path(model_directory)
    lines=['NSSOC phase55 actual child-load diagnostic; no deterministic startup or full PHY acceptance',
      *[f'.lib "{libraries / ("corner"+kind+".lib")}" {corner}'for kind,corner in [('HBT','hbt_typ'),('RES','res_typ'),('CAP','cap_typ')]],
      f'.include "{model_path}"','.temp 27',
      '.options method=trap maxord=2 reltol=1e-6 abstol=1e-13 vntol=1e-8 trtol=1 itl4=100 minbreak=1e-18',
      'Vrail avdd 0 PWL(0 0 1n 2.5)']
    for name,invert in [('clkp',False),('clkn',True)]:
        points=clock_points(boundary['common_mode_v'],boundary['single_ended_amplitude_v'],invert)
        lines.append('V'+name+' '+name+' 0 PWL('+' '.join(f'{t:.16g} {v:.16g}'for t,v in points)+')')
    lines.extend(name+' '+' '.join(nodes)+' '+top for name,nodes in instances)
    lines.extend(['.control',f'pre_osdi "{r3_osdi}"','set filetype=binary','set numdgt=16','save '+' '.join(vectors),
      'op','write op.raw all',f'tran {STEP:.16g} {STOP:.16g} 0 {STEP:.16g}','write wave.raw all','quit','.endc','.end'])
    deck='\n'.join(lines)+'\n'
    assert not re.search(r'(?im)^\s*(?:\.ic\b|\.nodeset\b|alter\b)|\buic\b',deck)
    assert sum(line.startswith('V')for line in lines)==3
    assert not any(line.startswith(('B','E','G','I','R','C'))for line in lines[1:])
    validate_paths(model_path,model_directory,r3_osdi)
    contract=dict(schema='phase55-real-child-load-v1',model_sha256=MODEL_SHA,rc_run=RC_RUN,rc_summary_sha256=RC_SUMMARY,
      rc_parts_sha256=RC_PARTS,boundary=boundary,instances=instances,hbt=bindings,vectors=vectors,
      device_count=165,native_wire_R=714,native_wire_C=1230,actual_intrinsic_MIM=12,
      fixed_timing=dict(start_s=START,stop_s=STOP,max_step_s=STEP,input_frequency_hz=4e9,expected_output_frequency_hz=2e9,adjacent_phase_s=UI),
      fixed_phase_map={'MP':'sa','QP':'sb'},expected_origin_s={'MP':START-UI,'QP':START},
      phase_origin_fitted=False,initial_state_forced=False,internal_ideal_clock_sources=0,reset_implemented=False,
      exact_observer_scalar_binding_verified=False,physical_intermacro_routing=False,selector_level_driver_included=False,
      full_selector_load_included=False,clock_tree_31_implemented=False,pll_connected=False,full_phy_accepted=False,
      deck_sha256=digest(deck),scope='Source-ready isolated three-macro child-load diagnostic. All165 devices and each internal wire are real qualified models. Intermacro nets and external test supply/clock remain test boundaries. Actual selector-level buffers, reset/sync and parent routing are absent. Observer scalar provenance must be independently validated before native dispatch.')
    return deck,contract
def crossings(t,d):
    ix=np.flatnonzero((d[:-1]<=0)&(d[1:]>0));return t[ix]+(t[ix+1]-t[ix])*(-d[ix])/(d[ix+1]-d[ix])
def phase_diagnostics(t,mp,mn,qp,qn):
    assert len(t)==len(mp)==len(mn)==len(qp)==len(qn)and np.isfinite(np.column_stack([t,mp,mn,qp,qn])).all()and np.all(np.diff(t)>0)
    samples=START+(np.arange(256)+.5)*UI
    assert t[0]<=samples[0]and t[-1]>=samples[-1]
    result={}
    for label,p,n,origin in [('MP',mp,mn,START-UI),('QP',qp,qn,START)]:
        diff=p-n;values=np.interp(samples,t,diff)
        expected=np.where((np.floor((samples-origin)/(2*UI)).astype(int)%2)==0,1.,-1.)
        margin=values*expected;edges=crossings(t,diff);selected=edges[(edges>=START)&(edges<STOP)]
        result[label]=dict(fixed_origin_s=origin,samples=256,wrong_sign_samples=int(np.count_nonzero(margin<=0)),
          minimum_signed_margin_v=float(margin.min()),rising_edges_s=selected.tolist(),
          output_frequency_hz=float((len(selected)-1)/(selected[-1]-selected[0]))if len(selected)>1 else None,
          common_mode_range_v=[float(((p+n)/2).min()),float(((p+n)/2).max())])
    m=crossings(t,mp-mn);q=crossings(t,qp-qn);relative=[]
    for x in m[(m>=START)&(m<STOP-4*UI)]:
        y=q[q>x]
        if len(y):relative.append(float(y[0]-x))
    result.update(master_to_next_same_polarity_slave_rising_s=relative,ideal_same_polarity_spacing_s=UI,
      fixed_absolute_phase_signs_match=all(result[k]['wrong_sign_samples']==0 for k in ('MP','QP')),
      adaptive_phase_or_polarity_fit=False,deterministic_startup_qualified=False,phase_jitter_or_selector_timing_qualified=False)
    return result
def review_samples(t,values,contract):
    t=np.asarray(t)
    assert t.ndim==1 and len(t)>100 and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)
    assert np.diff(t).max()<=STEP*1.00001
    assert set(values)==set(contract['vectors'])and all(len(v)==len(t)and np.isfinite(v).all()for v in values.values())
    def v(name):return np.zeros_like(t)if name=='0'else values['v('+name+')']
    active=t>=START;devices={}
    for name,device in contract['hbt'].items():
        c,b,e,s=[v(n)for n in device['terminals']];ic=values['@q.'+name+'.qnpn13g2[ic]']/device['nx']
        ce=c-e;be=b-e
        r=dict(min_post_vce_v=float(ce[active].min()),max_whole_abs_vce_v=float(abs(ce).max()),max_whole_abs_vbe_v=float(abs(be).max()),max_whole_abs_ic_per_emitter_a=float(abs(ic).max()))
        r['passed']=r['min_post_vce_v']>=.4 and r['max_whole_abs_vce_v']<=1.6 and r['max_whole_abs_vbe_v']<=1 and r['max_whole_abs_ic_per_emitter_a']<=.003
        devices[name]=r
    assert len(devices)==57
    phases=phase_diagnostics(t,v('mp'),v('mn'),v('qp'),v('qn'))
    return dict(all57_actual_hbt_safety_passed=all(x['passed']for x in devices.values()),devices=devices,phase_diagnostics=phases,
      deterministic_startup_qualified=False,electrical_tree_accepted=False,full_phy_accepted=False)
def controls():
    # Analytic waveforms test the observer only; they are not DUT evidence.
    t=np.arange(0,STOP+STEP/2,STEP);cm=1.
    def wave(origin):return np.where(np.floor((t-origin)/(2*UI)+1e-7).astype(int)%2==0,.1,-.1)
    m=wave(START-UI);q=wave(START)
    good=phase_diagnostics(t,cm+m,cm-m,cm+q,cm-q);assert good['fixed_absolute_phase_signs_match']
    rejected=[]
    for name,mm,qq in [('master_polarity',-m,q),('slave_polarity',m,-q),('master_slave_swap',q,m),('same_phase',m,m),('lost_master_clock',np.full_like(m,.1),q)]:
        result=phase_diagnostics(t,cm+mm,cm-mm,cm+qq,cm-qq)
        assert not result['fixed_absolute_phase_signs_match'],name;rejected.append(name)
    for points in (clock_points(2.,.1),clock_points(2.,.1,True)):
        assert len(points)>2 and points[0]==(0.,0.)and points[-1][0]==STOP
    return dict(analytic_observer_only=True,positive_fixed_map=True,negative_controls=rejected,native_evidence=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args();assert a.controls
    print(json.dumps(controls(),indent=2))
