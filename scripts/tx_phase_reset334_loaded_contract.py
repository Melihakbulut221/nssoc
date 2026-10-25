#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only three real334-model fixture; no routed-parent or PHY acceptance."""
import copy,hashlib,json,math,re
from collections import Counter
from pathlib import Path
import numpy as np
import tx_phase_assert_offset_diagnostic as original
import tx_phase31_source_mapping as mapping
import tx_phase_reset334_loaded_binding as binding
from tx_phase55_loaded_contract import classify_device
from build_pcie_local_vco_hybrid_v6 import statements,number
SUMMARY_SHA='ea7ca38a1c9cecdf374f3ba6ecdeb520275d51186a71d72c226e6a7a5474ae6b'
SOURCE='76eb57e7fc57086f0ccb7c087196c22065d2a740'
RUN=40169988733
PAYLOAD_SHA={'p':'1f6149097822613f55ec71f177302b001659c60b58fd7a83fe9b3c30160a6adc',
             'n':'215e54dfb31f699d55421189432dc99c15707386f6729347dbd9793d65020ee0'}
FLAGS=dict(postlayout_electrical_accepted=False,real_selector_load_accepted=False,
  routed_three_cell_parent=False,reset_distribution_qualified=False,
  all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
def digest(data):
    return hashlib.sha256(data.encode()if isinstance(data,str)else data).hexdigest()
def qualified_inputs(summary_raw,payload_raw,models):
    assert digest(summary_raw)==SUMMARY_SHA and set(payload_raw)==set(models)=={'p','n'}
    summary=json.loads(summary_raw)
    assert summary['run_id']==RUN and summary['source_head']==SOURCE
    assert summary['status']=='PASS_TWO_PHYSICAL334_ROLE_BINDINGS_NOT_LOADED_ELECTRICAL_ACCEPTANCE'
    assert summary['validation_errors']==[] and summary['sources_unchanged'] and summary['actual_native_binding_executed']
    assert not summary['simulator_invoked'] and not summary['new_extraction_performed']
    payloads={}
    for sign in ('p','n'):
        raw=payload_raw[sign];assert digest(raw)==PAYLOAD_SHA[sign]==summary['variants'][sign]['binding_result_sha256']
        payload=json.loads(raw);assert payload['controls_passed']and len(payload['negative_controls'])==20
        positive=payload['positive']
        assert positive['preset']==sign and len(positive['compact_roles'])==244 and len(positive['hbt_roles'])==106
        assert positive['original_phase_oracle_unchanged']and positive['no_distributed_nodes_collapsed_or_aliased']
        assert positive['source_native_net_map']['SUB']!=positive['public_native_net_map']['SUB']
        assert positive['fixed_internal_probes']==summary['variants'][sign]['actual_internal_probe_pairs']
        assert digest(models[sign])==binding.MODELS[sign]==summary['variants'][sign]['model_sha256']
        payloads[sign]=positive
    return summary,payloads
def model_records(text,sign):
    assert digest(text)==binding.MODELS[sign]
    rows=statements(text);top='nssoc_tx_phase_reset334_'+sign+'_native_wire_v1'
    assert rows[0]==['.subckt',top,*binding.PORTS]and rows[-1]==['.ends',top]
    body=rows[1:-1];assert len({r[0].lower()for r in body})==len(body)
    devices=[r for r in body if r[0].startswith('XD')]
    wire=[r for r in body if r[0][0]in 'RC']
    assert len(devices)==334 and len(wire)==3892 and len(body)==4226
    kinds=[classify_device(r)for r in devices]
    assert Counter(kinds)==Counter(binding.CENSUS)
    assert Counter(r[0][0]for r in wire)==dict(R=1347,C=2545)
    assert all(len(r)==4 and r[1]!=r[2]and math.isfinite(number(r[3]))and number(r[3])>0 for r in wire)
    return top,list(zip(devices,kinds,strict=True)),wire
def configuration(sign):
    assert sign in ('p','n')
    _,cells,_=mapping.design(mapping.original())
    parent=next(c for c in cells if c['cell']==('phase_l1_k0'if sign=='p'else'phase_l2_k0'))
    assert parent['required_internal_preset']['MP']==int(sign=='p')
    byparent={c['parent_clock']:c for c in cells}
    m=byparent[parent['master_clock']];q=byparent[parent['slave_clock']]
    presets=lambda c:'p'if c['required_internal_preset']['MP']else'n'
    assert (presets(m),presets(q))==(('n','p')if sign=='p'else('p','n'))
    root=['clkp','clkn','mp','mn','qp','qn','armp','armn','avdd','0','0','0']
    mclock=[parent['master_positive_pin'].lower(),parent['master_negative_pin'].lower()]
    assert mclock==(['mp','mn']if sign=='p'else['mn','mp'])
    result=[
      dict(instance='xdut',variant=sign,physical_role=parent['cell'],actual_ports=root),
      dict(instance='xloadm',variant=presets(m),physical_role=m['cell'],
           actual_ports=[*mclock,'m_mp','m_mn','m_qp','m_qn','armp','armn','avdd','0','0','0']),
      dict(instance='xloadq',variant=presets(q),physical_role=q['cell'],
           actual_ports=['qp','qn','q_mp','q_mn','q_qp','q_qn','armp','armn','avdd','0','0','0'])]
    assert all(len(r['actual_ports'])==len(binding.PORTS)for r in result)
    return result
def changed_clock(events,key,invert=False):
    initial=int(events[0][key])^int(invert);old=initial;out=[]
    for row in events[1:]:
        value=int(row[key])^int(invert)
        if value!=old:out.append((row['t_s'],value));old=value
    assert all(b[0]>a[0]for a,b in zip(out,out[1:]))
    return initial,out
def child_oracle(sign,initial_clock,clock_events):
    """Prescribed parent events only. No native waveform or fitted delay is an input."""
    assert sign in ('p','n')and initial_clock in (0,1)
    assert all(type(t)is float and v in (0,1)for t,v in clock_events)
    assert all(b[0]>a[0]for a,b in zip(clock_events,clock_events[1:]))
    mp=int(sign=='p');qp=1;clk=initial_clock;armed=False;released=False;arm_start=None
    history=[dict(t_s=0.,MP=mp,QP=qp,release=0)];first=[]
    events=[(original.ARM_RELEASE,'arm',1),(original.RESET_ASSERT,'arm',0),(original.RESET_RELEASE,'arm',1)]
    events +=[(t,'clock',v)for t,v in clock_events]
    for t,kind,value in sorted(events):
        if kind=='arm':
            armed=bool(value)
            if armed:arm_start=t
            else:released=False;mp=int(sign=='p');qp=1
        else:
            old=clk;clk=value
            if armed and old==1 and clk==0 and not released:
                released=True;first.append(dict(arm_s=arm_start,fall_s=t))
            if released:
                if clk==0:mp=1-qp
                else:qp=mp
        history.append(dict(t_s=t,MP=mp,QP=qp,release=int(released)))
    assert len(first)==2
    return dict(events=history,first_falls=first,initial_master=int(sign=='p'),initial_slave=1,
      output_polarities_fixed=True,observed_phase_fit=False)
def oracles(sign,initial_high,config):
    assert config==configuration(sign)and type(initial_high)is bool
    parent=original.expected(sign,initial_high)
    mi,me=changed_clock(parent['events'],'MP',sign=='n')
    qi,qe=changed_clock(parent['events'],'QP')
    return {'xdut':parent,'xloadm':child_oracle(config[1]['variant'],mi,me),
            'xloadq':child_oracle(config[2]['variant'],qi,qe)}
def validate_paths(model_paths,model_directory,osdi):
    assert set(model_paths)=={'p','n'}and len({str(v)for v in model_paths.values()})==2
    for p in [*model_paths.values(),model_directory,osdi]:
        assert str(p)and not any(c in str(p)for c in ('"','\n','\r','\x00'))
    assert not any(c.isspace()for c in str(osdi))
def prepare(summary_raw,payload_raw,models,observer_raw,sign,initial_high,model_paths,model_directory,osdi):
    validate_paths(model_paths,model_directory,osdi)
    summary,proof=qualified_inputs(summary_raw,payload_raw,models)
    boundary=original.boundary(observer_raw)
    config=configuration(sign);predicted=oracles(sign,initial_high,config)
    parsed={p:model_records(models[p],p)for p in ('p','n')}
    hbt={};thermal=[];vectors=set();instances=[]
    for spec in config:
        name=spec['instance'];p=spec['variant'];top,devices,wires=parsed[p]
        portmap={k.lower():v for k,v in zip(binding.PORTS,spec['actual_ports'],strict=True)}
        def node(n):return portmap.get(n.lower(),name+'.'+n.lower())
        roles=proof[p]['hbt_roles'];byid={str(v['native_id']):v for v in roles.values()}
        assert len(byid)==106
        for row,kind in devices:
            count={'npn13G2':4,'rppd':3,'cap_cmim':2,'ptap1':2}[kind]
            nodes=[node(n)for n in row[1:count+1]]
            vectors.update('v('+n+')'for n in nodes if n!='0')
            if kind=='npn13G2':
                native_id=row[0][2:];role=byid[native_id]
                assert [role['terminals'][t]['model_node']for t in ('C','B','E','S')]==row[1:5]
                nx=float(role['parameters']['Nx']);assert nx in (1,2,4)
                target=name+'.'+row[0].lower();assert target not in hbt
                hbt[target]=dict(terminals=nodes,nx=int(nx),native_id=int(native_id),
                  source_instance=role['source_instance'],physical_preset=p,fixture_instance=name)
                vectors.add('@q.'+target+'.qnpn13g2[ic]')
            elif kind=='rppd':
                thermal.append(name+'.'+row[0].lower()+'.dt')
        for row in wires:vectors.update('v('+node(n)+')'for n in row[1:3]if node(n)!='0')
        vectors.update('v('+n+')'for n in spec['actual_ports']if n!='0')
        probe_pairs={k:[node(leg['model_node'])for leg in pair]for k,pair in proof[p]['fixed_internal_probes'].items()}
        vectors.update('v('+n+')'for pair in probe_pairs.values()for n in pair)
        instances.append(dict(**spec,top=top,model_sha256=binding.MODELS[p],
          body_node=node('BULK'),finite_body_contacts=90,probe_pairs=probe_pairs,
          oracle=predicted[name],binding_payload_sha256=PAYLOAD_SHA[p]))
    assert len(hbt)==318 and len(set(thermal))==len(thermal)==390
    assert len({r['body_node']for r in instances})==3 and all(r['body_node']!='0'for r in instances)
    vectors.update('v('+n+')'for n in thermal)
    vectors.update('i('+n+')'for n in ('vrail','vclkp','vclkn','varmp','varmn'))
    vectors=sorted(vectors);assert len(vectors)==len(set(vectors))
    lines=['NSSOC three physical334 models: real child load fixture, not routed parent or PLL acceptance',
      *[f'.lib "{Path(model_directory)/("corner"+kind+".lib")}" {corner}'for kind,corner in [('HBT','hbt_typ'),('RES','res_typ'),('CAP','cap_typ')]],
      *[f'.include "{model_paths[p]}"'for p in ('p','n')],'.temp 27',original.solver_options(original.PROFILE),
      'Vrail avdd 0 PWL(0 0 1n 2.5)']
    for name,arm,invert in [('clkp',False,False),('clkn',False,True),('armp',True,False),('armn',True,True)]:
        pts=original.source_points(boundary,initial_high,arm,invert)
        lines.append('V'+name+' '+name+' 0 PWL('+' '.join(f'{t:.16g} {v:.16g}'for t,v in pts)+')')
    lines +=[r['instance']+' '+' '.join(r['actual_ports'])+' '+r['top']for r in instances]
    lines +=[f'.tran {original.STEP:.16g} {original.STOP:.16g} 0 {original.STEP:.16g}',
      '.control',f'pre_osdi {osdi}','set filetype=binary','set numdgt=16','save '+' '.join(vectors),
      'op','write op.raw all','run wave.raw','echo NSSOC_SOLVER_OPTIONS_BEGIN','option',
      'echo NSSOC_NATIVE_MINBREAK $minbreak','echo NSSOC_SOLVER_OPTIONS_END','quit','.endc','.end']
    deck='\n'.join(lines)+'\n'
    assert sum(l.startswith('V')for l in lines)==5
    assert not any(l.startswith(('B','E','G','I','R','C'))for l in lines[1:])
    assert not re.search(r'(?im)^\s*(?:\.ic\b|\.nodeset\b|alter\b)|\buic\b',deck)
    contract=dict(schema='physical334-three-model-loaded-fixture-v1',variant=sign,initial_clock_high=initial_high,
      binding_run=RUN,binding_source=SOURCE,binding_summary_sha256=SUMMARY_SHA,
      instances=instances,hbt=hbt,thermal_nodes=thermal,vectors=vectors,boundary=boundary,
      device_count=1002,compact_original_devices=732,physical_contacts=270,native_wire_R=4041,native_wire_C=7635,
      actual_intrinsic_MIM=24,hbt_count=318,resistor_thermal_count=390,deck_sha256=digest(deck),
      timing=dict(UI_s=original.UI,START_s=original.START,STOP_s=original.STOP,maxstep_s=original.STEP,
        clock_ramp_s=original.RISE,arm_release_s=original.ARM_RELEASE,reset_assert_s=original.RESET_ASSERT,
        reset_release_s=original.RESET_RELEASE),
      limits=copy.deepcopy(original.LIMITS),solver_profile=original.PROFILE,
      external_boundaries={'rail':'2.5V original 1ns ramp','clock':'original nominal4GHz scalar fixture, not measured PLL replay',
        'ARM':'original common external fixture; physical driver/distribution unqualified',
        'AVSS_SUB_wire_cref':'All public external references tied to test ground; each actual finite internal BULK contact network retained',
        'intermacro':'testbench ideal nets only; no fabricated routing or parasitics asserted'},
      full_internal_model_nodes_saved=True,all318_HBT_safety_required=True,
      uniform_OFF_initialization_required_for_all318=True,zero_source_OP_required=True,
      initial_differential_phase_forced=False,observed_phase_fit=False,
      no_internal_ideal_sources=True,three_macro_internal_wire_RC_included=True,
      frequency_scope='Both preset variants stressed at original nominal4GHz; representative N topology is not a literal complete31 frequency tree.',
      **FLAGS)
    return deck,contract
def review(t,values,contract):
    assert contract['schema']=='physical334-three-model-loaded-fixture-v1'
    assert contract['limits']==original.LIMITS and contract['hbt_count']==318
    assert len(t)>100 and t[0]==0 and abs(t[-1]-original.STOP)<1e-18 and np.all(np.diff(t)>0)
    assert np.diff(t).max()<=original.STEP*1.00001
    assert set(values)==set(contract['vectors'])
    assert all(len(v)==len(t)and np.isfinite(v).all()for v in values.values())
    def v(n):return np.zeros_like(t)if n=='0'else values['v('+n+')']
    devices={}
    for name,row in contract['hbt'].items():
        c,b,e,s=[v(n)for n in row['terminals']]
        devices[name]=original.hbt_screen(t,c,b,e,values['@q.'+name+'.qnpn13g2[ic]'],row['nx'])
    assert len(devices)==318
    screens={}
    for spec in contract['instances']:
        name=spec['instance'];port=dict(zip(binding.PORTS,spec['actual_ports'],strict=True))
        p=spec['probe_pairs'];release=p['release']
        signals=dict(MP=v(port['MP'])-v(port['MN']),QP=v(port['QP'])-v(port['QN']),
          release=v(release[0])-v(release[1]),clock=v(port['CLKP'])-v(port['CLKN']))
        phase=original.signal_review(t,signals,dict(variant=spec['variant'],oracle=spec['oracle']))
        pairs={'fixture_input':[port['CLKP'],port['CLKN']],'master':[port['MP'],port['MN']],
          'slave':[port['QP'],port['QN']],**p}
        ranges={k:dict(minimum_v=float((v(a)-v(b)).min()),maximum_v=float((v(a)-v(b)).max()),
          minimum_common_mode_v=float(((v(a)+v(b))/2).min()),maximum_common_mode_v=float(((v(a)+v(b))/2).max()))
          for k,(a,b)in pairs.items()}
        screens[name]=dict(signals=phase,pair_ranges=ranges,physical_role=spec['physical_role'])
    assert set(screens)=={'xdut','xloadm','xloadq'}
    safe=all(d['passed']for d in devices.values());phase=all(s['signals']['diagnostic_signal_screen_passed']for s in screens.values())
    return dict(all318_HBT_safety_passed=safe,hbt_safety=devices,all_three_fixed_phase_screens_passed=phase,
      three_model_screens=screens,diagnostic_screen_passed=safe and phase,**FLAGS)
