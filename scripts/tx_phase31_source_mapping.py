#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact source-level31 clock ownership/startup requirements. No hardware simulation."""
import ast,copy,hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORACLE='scripts/run_cloud_tx_mux4.py'
ORACLE_SHA='bb7f5c5ef736dd54c5ed560424d97d248894f4aa6fa6119f1e95c5f5c3df4b52'
def original():
    source=(ROOT/ORACLE).read_text()
    assert hashlib.sha256(source.encode()).hexdigest()==ORACLE_SHA
    tree=ast.parse(source)
    constants=next(n for n in tree.body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Tuple)and
      [x.id for x in n.targets[0].elts]==['UI','START','BITS'])
    ui,start,bits=ast.literal_eval(constants.value)
    assert (ui,start,bits)==(125e-12,2e-9,256)
    namespace=dict(UI=ui,START=start,BITS=bits,STOP=start+ui*bits)
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ('tree_plan','pwl')]
    assert len(funcs)==2
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'<unchanged source oracle>','exec'),namespace)
    return namespace
def oracle_events(ns,clock):
    # Preserve the original transition-start order, not an invented ideal
    # acceptance waveform. Electrical zero-crossing/propagation remains unproved.
    text=ns['pwl']([int(i%2==0)for i in range(ns['BITS'])],1.23,.08,clock['period'],clock['origin'])
    values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',text)))
    points=list(zip(values[::2],values[1::2],strict=True));events=[]
    for (ta,va),(tb,vb)in zip(points,points[1:]):
        if ta>=1e-9 and va!=vb:
            assert abs((tb-ta)-10e-12)<1e-20
            tick=round(ta/ns['UI']);assert abs(ta-tick*ns['UI'])<1e-20
            events.append([tick,int(vb>1.23)])
    assert events and events[0][1]==0
    return dict(initial=1,events=events)
def design(ns):
    plan=ns['tree_plan'](32)
    index={(n['stride'],n['offset']):n['clock']for n in plan['nodes']}
    index[(1,0)]='s';clocks={c['name']:c for c in plan['clocks']}
    assert len(index)==len(clocks)==31
    cells=[]
    for H in (1,2,4,8):
        level=H.bit_length()
        for k in range(H):
            parent=index[H,k]
            master_offset=(k+1-H)%(2*H)
            swapped=k<H-1
            outputs=dict(master=index[2*H,master_offset],slave=index[2*H,k+1])
            record=dict(cell=f'phase_l{level}_k{k}',level=level,parent_clock=parent,
              parent_halfperiod_ui=H,parent_offset=k,
              master_clock=outputs['master'],master_offset=master_offset,master_pair_swapped=swapped,
              master_positive_pin='MN'if swapped else'MP',master_negative_pin='MP'if swapped else'MN',
              slave_clock=outputs['slave'],slave_offset=k+1,slave_positive_pin='QP',slave_negative_pin='QN',
              required_internal_preset=dict(MP=int(not swapped),MN=int(swapped),QP=1,QN=0),
              release_event='first_actual_parent_falling_edge_after_global_arm',
              independent_master_slave_preset_required=swapped,
              physical_reset_or_release_implemented=False)
            cells.append(record)
    assert len(cells)==15 and sum(c['master_pair_swapped']for c in cells)==11
    outputs=[c[x]for c in cells for x in ('master_clock','slave_clock')]
    assert len(set(outputs))==30 and set(outputs)==set(clocks)-{'s'}
    return plan,cells,clocks
def simulate(root,cells,mutation=None):
    # Abstract latch truth/event model only. Holding independent internal values
    # is a REQUIRED physical function, not an available reset or forced SPICE IC.
    waves={'s':copy.deepcopy(root)}
    for cell0 in cells:
        cell=copy.deepcopy(cell0);selected=cell['cell']=='phase_l2_k0'
        if selected and mutation=='wrong_master_polarity':cell['master_pair_swapped']=False
        if selected and mutation=='wrong_master_preset':cell['required_internal_preset']['MP']=1
        if selected and mutation=='wrong_slave_preset':cell['required_internal_preset']['QP']=0
        m=cell['required_internal_preset']['MP'];q=cell['required_internal_preset']['QP']
        released=selected and mutation=='release_before_first_fall'
        if released:q=m # Slave is transparent while the initial parent clock is high.
        master=dict(initial=m^int(cell['master_pair_swapped']),events=[])
        slave=dict(initial=q,events=[])
        previous_m=master['initial'];previous_q=q;falls=0
        parent=waves[cell['parent_clock']]
        assert parent['initial']==1
        for tick,value in parent['events']:
            if value==0:
                falls+=1
                needed=2 if selected and mutation=='skip_first_fall'else 1
                if falls>=needed and not(selected and mutation=='never_release'):released=True
                if released:m=1-q
            elif released:q=m
            ym=m^int(cell['master_pair_swapped'])
            if ym!=previous_m:master['events'].append([tick,ym]);previous_m=ym
            if q!=previous_q:slave['events'].append([tick,q]);previous_q=q
        if selected and mutation=='swap_output_ownership':master,slave=slave,master
        waves[cell['master_clock']]=master;waves[cell['slave_clock']]=slave
    return waves
def verify(waves,reference,ns):
    assert set(waves)==set(reference)
    # Entire transition list AND every original 256-UI center are checked.
    for name,wave in waves.items():
        assert wave==reference[name],name
        for i in range(ns['BITS']):
            tick=ns['START']/ns['UI']+i+.5
            def at(w):
                value=w['initial']
                for t,v in w['events']:
                    if t>tick:break
                    value=v
                return value
            assert at(wave)==at(reference[name])
def main():
    methods=json.loads((ROOT/'scripts/tx-phase31-source-methods.json').read_text())
    for path,digest in methods['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    tail=(ROOT/'hw/soc/analog/pcie/clock_div4_hbt_v10.spice').read_text().splitlines()
    assert 'XM qn qp mp mn clkn clkp avdd avss sub ref nssoc_cml_latch'in tail
    assert 'XS mp mn qp qn clkp clkn avdd avss sub ref nssoc_cml_latch'in tail
    ns=original();plan,cells,clocks=design(ns)
    reference={name:oracle_events(ns,c)for name,c in clocks.items()}
    waves=simulate(reference['s'],cells);verify(waves,reference,ns)
    rejected=[]
    for fault in ('wrong_master_polarity','wrong_master_preset','wrong_slave_preset',
                  'release_before_first_fall','skip_first_fall','never_release','swap_output_ownership'):
        try:verify(simulate(reference['s'],cells,fault),reference,ns)
        except AssertionError:rejected.append(fault)
        else:raise AssertionError('Accepted '+fault)
    result=dict(status='PASS_ANALYTIC_SOURCE31_PHASE_OWNERSHIP_AND_RESET_REQUIREMENTS_NOT_HARDWARE',
      source_oracle=dict(path=ORACLE,sha256=ORACLE_SHA,tree_and_pwl_functions_unchanged=True),
      timing=dict(UI_s=ns['UI'],START_s=ns['START'],STOP_s=ns['STOP'],BITS=ns['BITS']),
      physical_divider_instances_required=15,clock_pairs=31,master_pairs_swapped=11,master_pairs_direct=4,
      frequency_inventory={str(k):v for k,v in Counter(round(1/(2*c['period']))for c in clocks.values()).items()},
      cells=cells,exact_all31_original_transition_lists_match=True,
      original_sample_centers_compared=31*256,negative_controls=rejected,
      proof_scope='Zero-delay abstract latch event ownership under explicitly required independent presets and first-fall release. Not device simulation, measured phase, jitter, reset implementation or a routed parent.',
      physical_reset_primitive_available=False,physical_release_sequencer_available=False,
      asynchronous_reset_release_timing_qualified=False,analogue_load_or_common_mode_qualified=False,
      physical_selector_buffer_included=False,physical_parent_routing=False,PLL_connected=False,full_PHY_accepted=False)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
