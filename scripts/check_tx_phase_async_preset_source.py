#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source topology/census controls only; zero physical or electrical qualification."""
import copy,hashlib,itertools,json
from collections import Counter
from pathlib import Path
import build_tx_phase_async_preset_source as builder
import tx_phase31_source_mapping as phase31
ROOT=Path(__file__).resolve().parents[1]
N=builder.NAMES
PRIMITIVES={'npn13G2':4,'rppd':3,'cap_cmim':2}
def card_map(definition):
    rows=definition['cards'];result={r[0]:r for r in rows}
    assert len(result)==len(rows)and len({r[0].lower()for r in rows})==len(rows),'Duplicate source instance'
    return result
def validate(text):
    d=builder.definitions(text);assert set(d)==set(N.values())and len(d)==9
    for definition in d.values():
        assert len({p.lower()for p in definition['ports']})==len(definition['ports'])
        card_map(definition)
    latch,tail,front=builder.reference();old={r[0]:r for r in tail['cards']}
    seed=d[N['seed']];assert seed['ports']==['p','n','avdd','avss','sub']
    assert seed['cards']==builder.seed_cards(),'Unqualified seed design geometry or ownership changed'
    signs={}
    for sign in ('p','n'):
        cell=d[N['sel'+sign]];a=card_map(cell)
        assert cell['ports']=='dp dn runp runn outp outn avdd avss sub'.split()
        assert set(a)=={'XBIAS','XREF','XAP','XAN','XBP','XBN','XSA','XSB','XT','XRP','XRN','XBA','XBB','XSEED'}
        for name in ('XBIAS','XREF'):assert a[name]==old[name]
        for name,nodes,nx in [('XAP','outn dp ea',2),('XAN','outp dn ea',2),
          ('XSA','ea runp tail',4),('XSB','eb runn tail',4),('XT','tail ref avss',4)]:
            assert a[name]==[name,*nodes.split(),'sub','npn13G2','Nx='+str(nx)]
        for name,nodes in [('XBP','outn'),('XBN','outp')]:
            assert a[name][1]==nodes and a[name][3:]==['eb','sub','npn13G2','Nx=2']
        pair=(a['XBP'][2],a['XBN'][2])
        assert pair in (('seedp','seedn'),('seedn','seedp'))
        signs[sign]=int(pair==('seedp','seedn'))
        assert signs[sign]==int(sign=='p')
        for name,nodes,w,l in [('XRP','avdd outp','8u','2.12u'),('XRN','avdd outn','8u','2.12u'),
          ('XBA','ea avss','1u','38.4u'),('XBB','eb avss','1u','38.4u')]:
            assert a[name]==[name,*nodes.split(),'sub','rppd','w='+w,'l='+l,'b=0','sw_et=1']
        assert a['XSEED']==['XSEED','seedp','seedn','avdd','avss','sub',N['seed']]
    for sign in ('p','n'):
        cell=d[N['latch'+sign]];a=card_map(cell)
        assert cell['ports']=='dp dn qp qn cp cn runp runn avdd avss sub ref'.split()
        assert set(a)=={r[0]for r in latch['cards']}|{'XDATA','XHOLD'}
        for r in latch['cards']:
            expected=list(r)
            if r[0]in ('XDP','XDN','XLP','XLN'):expected[2]={'XDP':'data_p','XDN':'data_n','XLP':'hold_p','XLN':'hold_n'}[r[0]]
            assert a[r[0]]==expected,'Original latch stack/device changed outside four selected bases'
        assert a['XDATA']==['XDATA','dp','dn','runp','runn','data_p','data_n','avdd','avss','sub',N['sel'+sign]]
        assert a['XHOLD']==['XHOLD','qp','qn','runp','runn','hold_p','hold_n','avdd','avss','sub',N['sel'+sign]]
    remap={'clkp':'ip','clkn':'in','ckp':'cp','ckn':'cn'}
    assert d[N['level']]['ports']=='ip in cp cn avdd avss sub'.split()
    assert d[N['level']]['cards']==[[remap.get(t,t)for t in r]for r in front['cards']if r[0]!='XSECOND']
    release=d[N['release']];a=card_map(release)
    assert release['ports']=='clkp clkn armp armn releasep releasen avdd avss sub'.split()
    assert set(a)=={'XARM','XBIAS','XREF','XSEED','XM','XS'}
    for name in ('XBIAS','XREF'):assert a[name]==old[name]
    assert a['XARM']==['XARM','armp','armn','armcp','armcn','avdd','avss','sub',N['level']]
    assert a['XSEED']==['XSEED','capturep','capturen','avdd','avss','sub',N['seed']]
    assert a['XM']==['XM','capturep','capturen','amp','amn','clkp','clkn','armcp','armcn','avdd','avss','sub','ref',N['latchn']]
    assert a['XS']==['XS','amp','amn','releasep','releasen','clkn','clkp','armcp','armcn','avdd','avss','sub','ref',N['latchn']]
    for sign in ('p','n'):
        parent=d[N['parent'+sign]];a=card_map(parent)
        assert parent['ports']=='CLKP CLKN MP MN QP QN ARM_P ARM_N DIV_AVDD AVSS SUB'.split()
        assert set(a)=={'XCLK','XRELEASE','XRUN','XBIAS','XREF','XM','XS','XSEEDP','XSEEDN'}
        assert a['XCLK']==['XCLK','CLKP','CLKN','ckp','ckn','DIV_AVDD','AVSS','SUB',N['level']]
        assert a['XRELEASE']==['XRELEASE','ckp','ckn','ARM_P','ARM_N','releasedp','releasedn','DIV_AVDD','AVSS','SUB',N['release']]
        assert a['XRUN']==['XRUN','releasedp','releasedn','runp','runn','DIV_AVDD','AVSS','SUB',N['level']]
        assert a['XM']==['XM','QN','QP','MP','MN','ckn','ckp','runp','runn','DIV_AVDD','AVSS','SUB','ref',N['latch'+sign]]
        assert a['XS']==['XS','MP','MN','QP','QN','ckp','ckn','runp','runn','DIV_AVDD','AVSS','SUB','ref',N['latchp']]
        supply={'avdd':'DIV_AVDD','avss':'AVSS','sub':'SUB','mp':'MP','mn':'MN'}
        for name in ('XBIAS','XREF','XSEEDP','XSEEDN'):assert a[name]==[supply.get(t,t)for t in old[name]]
    def flatten(name,actual,path='',stack=()):
        assert name not in stack and len(actual)==len(d[name]['ports'])
        mapping={p.lower():n for p,n in zip(d[name]['ports'],actual,strict=True)}
        def node(t):return mapping.get(t.lower(),path+t.lower())
        result=[]
        for row in d[name]['cards']:
            primitives=[(model,n)for model,n in PRIMITIVES.items()if len(row)>n+1 and row[n+1]==model]
            if primitives:
                assert len(primitives)==1;model,n=primitives[0]
                parameters=row[n+2:];keys=[p.split('=',1)[0]for p in parameters]
                assert len(keys)==len(set(keys))and all('='in p for p in parameters)
                expected={'npn13G2':{'Nx'},'rppd':{'w','l','b','sw_et'},'cap_cmim':{'w','l'}}
                assert set(keys)==expected[model]
                result.append(dict(instance=path+row[0],model=model,nodes=[node(t)for t in row[1:n+1]],parameters=parameters))
            else:
                child=row[-1];assert child in d
                result.extend(flatten(child,[node(t)for t in row[1:-1]],path+row[0]+'.',(*stack,name)))
        return result
    census={}
    for sign in ('p','n'):
        top=N['parent'+sign];flat=flatten(top,d[top]['ports'],top+'.')
        counts=Counter(x['model']for x in flat)
        assert counts==dict(npn13G2=106,rppd=127,cap_cmim=8),counts
        assert len(flat)==241 and len({x['instance'].lower()for x in flat})==241
        assert sum(len(x['nodes'])for x in flat)==821
        nx=Counter(int(x['parameters'][0].split('=')[1])for x in flat if x['model']=='npn13G2')
        assert nx=={1:13,2:54,4:39},nx
        census[sign]=dict(compact_primitives=dict(counts),compact_terminals=821,hbt_Nx_inventory=dict(nx),
          physical_body_contacts_not_yet_extracted=True)
    # Pure truth relations, conditional on actual cells preserving their
    # differential signs and real safety/load margins. Not analog simulation.
    truth_cases=0
    for sign in ('p','n'):
        preset=signs[sign]
        for cp,data,q in itertools.product((0,1),repeat=3):
            selected_data=selected_hold=preset
            output=selected_data if cp else selected_hold
            assert output==preset
            normal=data if cp else q
            assert normal in (0,1);truth_cases+=1
    # Both arm phases: asynchronous negative preset and first-fall capture.
    release_cases=[]
    for initial_clock in (0,1):
        m=q=0
        if initial_clock:m=1
        values=[1-initial_clock,initial_clock,1-initial_clock,initial_clock]
        first_fall=next(i for i,v in enumerate(values)if v==0)
        history=[]
        for i,clk in enumerate(values):
            if clk:m=1
            else:q=m
            history.append(q);assert q==int(i>=first_fall)
        # The physical topology's asynchronous negative selector is required
        # to restore BOTH internal signs if global ARM is removed.
        m=q=signs['n'];assert m==q==0
        release_cases.append(dict(initial_clock=initial_clock,release_history=history,first_fall_index=first_fall))
    ns=phase31.original();plan,cells,clocks=phase31.design(ns)
    assignments=[]
    for cell in cells:
        sign='p'if cell['required_internal_preset']['MP']else'n'
        assert signs[sign]==cell['required_internal_preset']['MP']and cell['required_internal_preset']['QP']==1
        assignments.append(dict(cell=cell['cell'],candidate_model=N['parent'+sign],
          master_positive_pin=cell['master_positive_pin'],master_negative_pin=cell['master_negative_pin'],
          physical_implementation_accepted=False))
    assert Counter(x['candidate_model']for x in assignments)=={N['parentp']:4,N['parentn']:11}
    return dict(census=census,original_core_stack_preserved=True,actual_selectors_on_data_and_hold=True,
      real_qualified_source_level_network_preserved=True,independent_preset_truth_cases=truth_cases,
      first_fall_release_source_truth=release_cases,all15_source_variant_assignments=assignments,
      proof_assumptions=['Healthy loaded differential seed polarity','Healthy loaded selector/level/latch sign transfer','Finite preset/removal timing still requires native proof'],
      source_topology_only=True,actual_native_DRCLVS=False,actual_native_RC=False,actual_native_electrical=False,
      deterministic_reset_qualified=False,PLL_connected=False,full_PHY_accepted=False)
def main():
    methods=json.loads((ROOT/'scripts/tx-phase-async-preset-source-methods.json').read_text())
    for p,h in methods['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    text=(ROOT/builder.OUTPUT).read_text();assert text==builder.build()
    positive=validate(text);rejected=[]
    mutations=[
      ('hold_selector_bypassed','XLP qn hold_p he','XLP qn qp he'),
      ('data_selector_bypassed','XDP qn data_p se','XDP qn dp se'),
      ('regenerative_polarity_reversed','XHOLD qp qn runp runn','XHOLD qn qp runp runn'),
      ('added_original_tail_stack','XT te ref avss sub','XT te ref extra sub'),
      ('seed_symmetric','XLP p avss sub rppd w=4u l=40u','XLP p avss sub rppd w=4u l=20u'),
      ('selector_preset_reversed','XBP outn seedp eb','XBP outn seedn eb'),
      ('release_positive_edge','XM capturep capturen amp amn clkp clkn','XM capturep capturen amp amn clkn clkp'),
      ('release_slave_not_preset_negative','XS amp amn releasep releasen clkn clkp armcp armcn avdd avss sub ref '+N['latchn'],
        'XS amp amn releasep releasen clkn clkp armcp armcn avdd avss sub ref '+N['latchp']),
      ('run_bypasses_release','XRUN releasedp releasedn runp runn','XRUN ARM_P ARM_N runp runn'),
      ('master_preset_variant_changed','XM QN QP MP MN ckn ckp runp runn DIV_AVDD AVSS SUB ref '+N['latchp'],
        'XM QN QP MP MN ckn ckp runp runn DIV_AVDD AVSS SUB ref '+N['latchn']),
      ('slave_feedback_short','XS MP MN QP QN ckp ckn','XS MP MP QP QN ckp ckn'),
      ('wrong_original_seed','XSEEDP MP AVSS cap_cmim w=2.2u','XSEEDP MP AVSS cap_cmim w=2u'),
      ('level_public_polarity_swap',N['level']+' ip in cp cn',N['level']+' in ip cp cn'),
      ('ideal_internal_drive','XREF ref ref avss sub npn13G2 Nx=1','VREF ref avss 0.8')]
    for name,old,new in mutations:
        assert old in text
        try:validate(text.replace(old,new,1))
        except (AssertionError,KeyError,ValueError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    print(json.dumps(dict(status='PASS_SOURCE_ONLY_REAL_DEVICE_ASYNC_PRESET_FIRST_FALL_CONNECTIONS_AND_CONTROLS',
      source_sha256=hashlib.sha256(text.encode()).hexdigest(),positive=positive,negative_controls=rejected,
      reset_or_release_hardware_qualified=False,physical_parent_routed=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
