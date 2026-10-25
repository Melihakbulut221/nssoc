#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for immutable replay derivation and observed-current ledgers."""
import ast,copy,hashlib,json,os,tempfile
from pathlib import Path
import numpy as np
import cloud_cdr_v58_current_ledger as c
import cdr_v58_current_ledger as r
import check_cdr_v58_saved_capture as frozen
ROOT=Path(__file__).resolve().parents[1]

def equal(a,b):assert a==b

def derive():
    m=c.methods();p=m['derivation']
    source=(ROOT/p['original_path']).read_text()
    assert hashlib.sha256(source.encode()).hexdigest()==p['original_sha256']
    for a,b in p['replacements']:
        assert source.count(a)==1,(a,source.count(a))
        source=source.replace(a,b,1)
    actual=(ROOT/p['candidate_path']).read_text()
    assert source==actual,'Unreported controller modification'
    back=actual
    for a,b in reversed(p['replacements']):
        assert back.count(b)==1
        back=back.replace(b,a,1)
    assert back==(ROOT/p['original_path']).read_text()
    aa={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(back).body if isinstance(n,ast.FunctionDef)}
    bb={n.name:ast.dump(n,include_attributes=False)for n in ast.parse((ROOT/p['original_path']).read_text()).body if isinstance(n,ast.FunctionDef)}
    assert aa==bb
    return dict(exact_controller_reversible_edits=len(p['replacements']),original_functions=len(aa))

def math_fixture(module,records,contract):
    # Four exact synthetic rows test report arithmetic, never qualify the DUT.
    t=r.START+np.array([0.,.1,.2,.3])*r.UI
    names={r.voltage(q['node'])for x in records.values()for q in x['terminals']}
    names.update(r.current(x)for x in records.values()if r.current(x))
    names.update(['v(cp)','v(cn)']);d={n:np.zeros(4)for n in names}
    h=records[59];rr=records[187]
    for k,v in [('C',[2.,4.,3.,1.]),('B',[1.,2.,4.,5.]),('E',[0.,3.,1.,0.])]:d[r.terminal(h,k)]=np.array(v)
    d[r.current(h)]=np.array([10.,20.,30.,40.])*1e-6
    d[r.terminal(rr,'rppd_1')]=np.array([1.,2.,3.,4.])
    d[r.terminal(rr,'rppd_2')]=np.zeros(4)
    point=module.device_point(t,d,1,h)
    assert point['row']==1 and point['time_s']==float(t[1])
    assert point['C_v']==4. and point['B_v']==2. and point['E_v']==3.
    assert point['VCE_v']==1. and point['VBE_v']==-1. and point['Ic_a']==float(d[r.current(h)][1])
    assert point['float64_le_hex'][r.current(h)]==np.asarray(d[r.current(h)][1],dtype='<f8').tobytes().hex()
    rp=module.device_point(t,d,1,rr)
    assert rp['terminal_voltage_difference_v']==2. and rp['current_a'] is None and rp['native_current_vector'] is None
    for p in contract['clock_tails']:
        for index,i in enumerate(p['cp']):
            d[r.current(records[i])]=np.array([1.+index,0.,0.,2.])*1e-6
            d[r.terminal(records[i],'B')]=np.array([1.,0.,0.,1.])
        for index,i in enumerate(p['cn']):
            d[r.current(records[i])]=np.array([0.,1.+index,1.+index,0.])*1e-6
            d[r.terminal(records[i],'B')]=np.array([0.,1.,1.,0.])
        for i in p['mos']:d[r.current(records[i])]=np.ones(4)*1e-6
    d['v(cp)']=np.array([1.,0.,0.,1.]);d['v(cn)']=np.array([0.,1.,1.,0.])
    ledger=module.steering(t,d,records,contract);assert len(ledger)==8
    for entry,plan in zip(ledger,contract['clock_tails'],strict=True):
        assert entry['native_topology']==plan
        assert entry['frame_rows']==[0,1,2,3]
        events=entry['all_current_difference_crossings']
        assert [(e['left_row'],e['right_row'],e['direction'])for e in events]==[(0,1,'falling'),(2,3,'rising')]
        assert len(entry['all4_actual_base_access_crossings'])==4
        for b in entry['all4_actual_base_access_crossings']:
            assert [(e['left_row'],e['right_row'])for e in b['events']]==[(0,1),(2,3)]
            assert len(b['current_event_relations'])==2
        first=entry['exact_native_row_frames'][0]
        assert first['row']==0 and first['cp_sum_Ic_a']==3e-6 and first['cn_sum_Ic_a']==0.
        assert first['MOS_sum_Ids_a']==4e-6 and len(first['devices'])==8
        assert entry['observed_Ic_minus_Ids_is_KCL_residual'] is False and entry['clock_acceptance'] is False
        assert first['observed_Ic_minus_Ids_a']==3e-6-4e-6
    return t,d

def phase_fixture(module,records,contract):
    # Independent fixed-grid construction exercises native bracket choice and extrema.
    t=r.START+np.arange(1033)*(.25*r.UI)
    names={r.voltage(q['node'])for x in records.values()for q in x['terminals']}
    names.update(r.current(x)for x in records.values()if r.current(x))
    d={n:np.zeros(len(t))for n in names}
    report=dict(source_bits=[i%2 for i in range(256)],data_offset_s=-.15*r.UI,
                device_checks={},binding=dict(aliases={}))
    for ident in r.FAILED:
        x=records[ident];vc=np.ones(len(t));vb=np.ones(len(t))*.6;ve=np.ones(len(t))*.2
        ic=np.ones(len(t))*4e-6;vc[6]=2.;vb[7]=3.;ic[8]=8e-6
        for term,data in [('C',vc),('B',vb),('E',ve)]:d[r.terminal(x,term)]=data
        d[r.current(x)]=ic
        report['device_checks'][r.name(x)]=dict(maximum_alltime_abs_vce_v=2.-.2,
            maximum_alltime_abs_vbe_v=3.-.2,maximum_alltime_abs_ic_per_emitter_a=8e-6/4.,
            minimum_active_vce_v=1.-.2)
    for tag in 'abcd':
        p,n='fixture_'+tag+'p','fixture_'+tag+'n'
        report['binding']['aliases'].update({'xpd.'+tag+'qp':p,'xpd.'+tag+'qn':n})
        d['v('+p+')']=np.zeros(len(t));d['v('+n+')']=np.zeros(len(t))
        # Bit 11: C expects bit10=0, A/B/D expect bit11=1.
        row=45 if tag=='b'else 47
        d['v('+p+')'][row]=1. if tag=='c'else -1.
    reasons,extrema,phase,drops=module.target_rows(t,d,report,records,contract)
    for ident in r.FAILED:
        assert extrema[str(ident)]==dict(max_abs_vce=6,max_abs_vbe=7,max_abs_ic_per_emitter=8,min_active_vce=0)
    for tag in 'abcd':
        row=45 if tag=='b'else 47
        assert phase[tag]['row']==row and phase[tag]['bit_index']==11
        assert phase[tag]['signed_margin_v']==-1.
        assert [p['row']for p in phase[tag]['bracket']['rows']]==[row,row+1]
        assert row in reasons and row+1 in reasons
    assert len(drops)==12
    for x in drops:
        assert x['current_not_inferred']and x['same_logical_net']
        assert x['voltage_difference_v']==float(d[x['from_vector']][x['row']]-d[x['to_vector']][x['row']])
    return report

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    inherited=frozen.controls();assert len(inherited['rejected'])==58
    derivation=derive();faults=[]
    from ensure_cloud_tested_source_release import controls as publication_controls
    publication=publication_controls();assert len(publication['rejected'])==17
    def reject(label,fn):
        try:fn()
        except (AssertionError,ValueError,TypeError,KeyError,IndexError):faults.append(label)
        else:raise AssertionError('Accepted ledger corruption '+label)
    actual=json.loads((ROOT/'docs/evidence/cdr500-v58-mim-precision-pass-20261024.json').read_text())['report']['composition']['contract']
    planes=json.loads((ROOT/'docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json').read_text())['report']['native_planes']
    req=json.loads((ROOT/c.REQ).read_text());pin=req['failed_cases'][0]
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'summary.json';c.asset(pin['summary'],path)
        report=json.loads(path.read_text());c.summary(report,pin)
    contract=r.contract();bound=report['binding'];records=r.validate_contract(contract,actual,bound)
    clock=r.topology(actual,planes,bound,req);names=r.selected_names(report,clock)
    assert set(names)<=set(report['vectors']) and len(names)==len(set(names))
    assert len(clock)==32 and len(records)==126
    mutations=[
      ('schema',lambda x:x.update(schema='other')),
      ('run',lambda x:x.update(original_run=1)),
      ('head',lambda x:x.update(original_head='0'*40)),
      ('case-scope',lambda x:x['original_capture_cases'].reverse()),
      ('record-missing',lambda x:x['native_device_records'].pop()),
      ('record-duplicate',lambda x:x['native_device_records'].__setitem__(1,x['native_device_records'][0])),
      ('census',lambda x:x['model_census'].__setitem__('npn13g2',71)),
      ('native-parameter',lambda x:x['native_device_records'][0]['parameters'].__setitem__('w','1u')),
      ('terminal-cluster',lambda x:x['native_device_records'][0]['terminals'][0].__setitem__('native_cluster',1)),
      ('follower-id',lambda x:x['gain_paths'][3].__setitem__('follower',122)),
      ('gain-label',lambda x:x['gain_paths'][0].__setitem__('sampler','A')),
      ('load-id',lambda x:x['gain_paths'][0].__setitem__('input_load',188)),
      ('hold-bleeder',lambda x:x['hold_paths'][0].__setitem__('bleed',210)),
      ('hold-label',lambda x:x['hold_paths'][0].__setitem__('sampler','D')),
      ('clock-polarity',lambda x:x['clock_tails'][0].__setitem__('cp',x['clock_tails'][0]['cn'])),
      ('clock-duplicate',lambda x:x['clock_tails'][0]['cp'].__setitem__(1,x['clock_tails'][0]['cp'][0])),
      ('tail-mos',lambda x:x['clock_tails'][0]['mos'].__setitem__(0,7)),
      ('current-inference',lambda x:x['observed_currents'].__setitem__('rppd','L/W')),
      ('vbe-inference',lambda x:x['scope'].__setitem__('derive_current_from_VBE',True)),
      ('complete-kcl',lambda x:x['scope'].__setitem__('complete_KCL_accepted',True)),
      ('missing-wire',lambda x:x['original_wire_observability'].__setitem__('missing_count',0)),
      ('wire-census',lambda x:x['original_wire_observability']['counts'].__setitem__('R',1)),
      ('fixed-ui',lambda x:x['limits'].__setitem__('original_bits',255)),
      ('unsaved-current',lambda x:x['unavailable'].remove('HBT Ie')),
      ('physical-digest',lambda x:x['binding_sources']['physical'].__setitem__('sha256','0'*64)),
    ]
    for label,mutate in mutations:
        bad=copy.deepcopy(contract);mutate(bad)
        reject(label,lambda bad=bad:r.validate_contract(bad,actual,bound))
    for mode in ('nodes','parameters','native_id'):
        bad=copy.deepcopy(bound);v=bad['groups']['npn13g2']['xpd.xd0059']
        if mode=='nodes':v['nodes'][0],v['nodes'][1]=v['nodes'][1],v['nodes'][0]
        elif mode=='parameters':v['parameters']['nx']='2'
        else:v['native_id']=60
        reject('bound-'+mode,lambda bad=bad:r.validate_contract(contract,actual,bad))
    t,d=math_fixture(r,records,contract)
    phase_fixture(r,records,contract)
    for label,ids in [('sum-duplicate',[61,61]),('sum-unsaved-rppd',[187]),('sum-empty',[])]:
        reject(label,lambda ids=ids:r.current_sum(d,records,ids))
    missing=copy.deepcopy(d);del missing[r.current(records[61])]
    reject('missing-saved-current',lambda:r.current_sum(missing,records,[61,62]))
    # Compile real reporting corruptions, then require the independent fixture to reject.
    source=(ROOT/'scripts/cdr_v58_current_ledger.py').read_text()
    mutants=[
      ('shift-current-row','Ic_a=float(d[cc][row])','Ic_a=float(d[cc][(row+1)%len(t)])'),
      ("independent-voltage-extrema","c,b,e=[float(d[terminal(record,k)][row])for k in ('C','B','E')]","c,b,e=[float(d[terminal(record,k)].max())for k in ('C','B','E')]"),
      ('divide-current-sum','return sum((d[v]for v in vectors),np.zeros_like(d[vectors[0]]))','return sum((d[v]for v in vectors),np.zeros_like(d[vectors[0]]))/len(vectors)'),
      ('invert-steering','difference=cp-cn','difference=cn-cp'),
      ('drop-current-event','events=old.crossings(t,difference,START,STOP)','events=old.crossings(t,difference,START,STOP)[:-1]'),
      ('invent-rppd-current','current_a=None,','current_a=(v1-v2)/1000.,'),
      ('false-kcl','observed_Ic_minus_Ids_is_KCL_residual=False','observed_Ic_minus_Ids_is_KCL_residual=True'),
      ('omit-base-access','for inn in p[\'cn\']:',"for inn in p['cn'][:1]:"),
    ]
    import types
    for label,before,after in mutants:
        assert source.count(before)==1,(label,source.count(before))
        env={'__file__':str(ROOT/'scripts/cdr_v58_current_ledger.py'),'__name__':'ledger_mutant'}
        exec(compile(source.replace(before,after,1),'<ledger-corruption-'+label+'>','exec'),env)
        reject(label,lambda env=env:math_fixture(types.SimpleNamespace(**env),records,contract))
    phase_mutants=[
      ('shift-phase',"when=edge+.3*UI","when=edge+.6*UI"),
      ('change-C-bit',"c=bits[:-1]","c=bits[1:]"),
      ('change-B-clock',"(0 if tag=='b'else .5)","(.5 if tag=='b'else .5)"),
      ('truncate-bit-scope',"enumerate(expected[tag],1)","enumerate(expected[tag][:-1],1)"),
    ]
    for label,before,after in phase_mutants:
        assert source.count(before)==1,(label,source.count(before))
        env={'__file__':str(ROOT/'scripts/cdr_v58_current_ledger.py'),'__name__':'ledger_phase_mutant'}
        exec(compile(source.replace(before,after,1),'<ledger-corruption-'+label+'>','exec'),env)
        reject(label,lambda env=env:phase_fixture(types.SimpleNamespace(**env),records,contract))
    assert len(faults)==len(set(faults))==44,len(faults)
    return dict(status='PASS_CURRENT_LEDGER_58_INHERITED_AND44_NEW_CONTROLS_ONLY',
        inherited=inherited,rejected=faults,derivation=derivation,publication=publication,
        actual_native_device_records=126,actual_clock_devices=32,selected_columns=1+len(names),
        synthetic_current_math_only=True,full_native_capture_read=False,new_simulation=False,
        original_electrical_rejections_preserved=True,cdr_accepted=False,full_phy_accepted=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
