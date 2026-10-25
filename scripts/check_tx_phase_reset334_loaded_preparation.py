#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preparation/source controls only; generated decks are never simulated here."""
import copy,json
from pathlib import Path
import numpy as np
import tx_phase_reset334_loaded_contract as bench
import tx_phase_assert_offset_diagnostic as original
def reject(label,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError):return label
    raise AssertionError('Accepted '+label)
def controls():
    # Hand-specified first-fall times come from the immutable125ps input schedule.
    # These test the hierarchy-event adapter, not an analog waveform.
    expected={
      ('p',True):[2.125e-9,2.125e-9,2.25e-9],
      ('p',False):[2.25e-9,2.25e-9,2.375e-9],
      ('n',True):[2.125e-9,2.375e-9,2.25e-9],
      ('n',False):[2.25e-9,2.5e-9,2.375e-9]}
    positive=[]
    for (sign,high),times in expected.items():
        config=bench.configuration(sign);oracles=bench.oracles(sign,high,config)
        assert oracles['xdut']==original.expected(sign,high)
        actual=[oracles[c['instance']]['first_falls'][0]['fall_s']for c in config]
        assert all(abs(a-b)<1e-23 for a,b in zip(actual,times,strict=True))
        assert config[1]['actual_ports'][:2]==(['mp','mn']if sign=='p'else['mn','mp'])
        assert config[2]['actual_ports'][:2]==['qp','qn']
        assert [c['variant']for c in config]==(['p','n','p']if sign=='p'else['n','p','n'])
        for c in config:
            o=oracles[c['instance']];assert len(o['first_falls'])==2
            assert [r['arm_s']for r in o['first_falls']]==[original.ARM_RELEASE,original.RESET_RELEASE]
            assert o['initial_master']==int(c['variant']=='p')and o['initial_slave']==1
            assert not o['observed_phase_fit']
        positive.append(dict(sign=sign,initial_high=high,first_fall_s=actual))
    faults=[]
    config=bench.configuration('n')
    for label,edit in [
        ('wrong-master-leg',lambda c:c[1]['actual_ports'].__setitem__(0,'mp')),
        ('wrong-child-preset',lambda c:c[1].update(variant='n')),
        ('wrong-slave-parent',lambda c:c[2]['actual_ports'].__setitem__(0,'mp')),
        ('missing-real-child',lambda c:c.pop()),
        ('ideal-clock-for-child',lambda c:c[1]['actual_ports'].__setitem__(0,'ideal_child_clock')),
        ('short-internal-body-to-public-ground',lambda c:c[0].update(body_node='0'))]:
        changed=copy.deepcopy(config);edit(changed)
        faults.append(reject(label,lambda:bench.oracles('n',True,changed)))
    faults.append(reject('invalid-root-preset',lambda:bench.configuration('x')))
    faults.append(reject('nonboolean-clock-phase',lambda:bench.oracles('n',1,config)))
    faults.append(reject('duplicate-clock-event',lambda:bench.child_oracle('p',1,[(2.1e-9,0),(2.1e-9,1)])))
    for label,path in [('newline-osdi','/tmp/a\nb'),('space-osdi','/tmp/a b'),('quote-model','/tmp/a"b')]:
        models={'p':'/tmp/p.spice','n':'/tmp/n.spice'};osdi='/tmp/rppd.osdi'
        if label=='quote-model':models['p']=path
        else:osdi=path
        faults.append(reject(label,lambda:bench.validate_paths(models,'/tmp/models',osdi)))
    for count in (1,1000,1001,9999):
        vectors=['v(fixture_'+str(i)+')'for i in range(count)]
        commands=bench.native_save_commands(vectors)
        assert [v for line in commands for v in line.split()[1:]]==vectors
        assert all(line.startswith('save ')and len(line.split())-1<=1000 for line in commands)
        assert len(commands)==(1 if count<=1000 else (count+127)//128)
    faults.append(reject('empty-native-save',lambda:bench.native_save_commands([])))
    faults.append(reject('duplicate-native-save',lambda:bench.native_save_commands(['v(a)','v(a)'])))
    faults.append(reject('over-limit-native-save',lambda:bench.native_save_commands(['v(a'+str(i)+')'for i in range(10000)])))
    assert len(faults)==15
    return dict(status='PASS_SOURCE_ONLY_THREE_MODEL_FIXED_EVENT_CONTROLS',positive_cases=positive,
      rejected=faults,native_simulator_executed=False,actual_model_preparation_executed=False,**bench.FLAGS)
def positive_prepare(summary_raw,payload_raw,models,observer_raw,source_text,model_paths,model_directory,osdi,out):
    source=controls();out=Path(out);out.mkdir(exist_ok=False)
    cases={}
    for sign in ('p','n'):
        for high in (True,False):
            label=sign+'-initial-'+('high'if high else'low')
            deck,c=bench.prepare(summary_raw,payload_raw,models,observer_raw,sign,high,model_paths,model_directory,osdi)
            old_deck,old=original.prepare(source_text,c['boundary'],sign,high,'/fixture/original244.spice',model_directory,osdi)
            assert [l for l in deck.splitlines()if l.startswith('V')]==[l for l in old_deck.splitlines()if l.startswith('V')]
            assert c['instances'][0]['oracle']==old['oracle']
            assert c['timing']==old['timing']and c['limits']==old['limits']
            assert c['device_count']==1002 and c['hbt_count']==318 and c['physical_contacts']==270
            assert c['native_wire_R']==4041 and c['native_wire_C']==7635 and c['actual_intrinsic_MIM']==24
            assert len(c['hbt'])==318 and len(c['thermal_nodes'])==390
            commands=[l for l in deck.splitlines()if l.startswith('save ')]
            assert [v for line in commands for v in line.split()[1:]]==c['vectors']
            assert all(len(line.split())-1<=1000 for line in commands)
            assert c['uniform_OFF_initialization_required_for_all318']and c['zero_source_OP_required']
            assert c['full_internal_model_nodes_saved']and c['all318_HBT_safety_required']
            assert len({r['body_node']for r in c['instances']})==3
            assert sum(l.startswith(('xdut ','xloadm ','xloadq '))for l in deck.splitlines())==3
            assert not any(c[k]for k in bench.FLAGS)
            case=out/label;case.mkdir()
            (case/'bench.cir').write_text(deck);(case/'contract.json').write_text(json.dumps(c,indent=2,allow_nan=False)+'\n')
            cases[label]=dict(deck_sha256=bench.digest(deck),contract_sha256=bench.digest((case/'contract.json').read_bytes()),
              vectors=len(c['vectors']),hbt_devices=len(c['hbt']),thermal_nodes=len(c['thermal_nodes']),
              all_original_external_source_cards_identical=True,original_parent_oracle_identical=True,
              three_predetermined_child_roles=[r['physical_role']for r in c['instances']])
    kwargs=dict(summary_raw=summary_raw,payload_raw=payload_raw,models=models,observer_raw=observer_raw,
      sign='p',initial_high=True,model_paths=model_paths,model_directory=model_directory,osdi=osdi)
    faults=[]
    for label,edit in [
      ('changed-binding-summary',lambda d:d.update(summary_raw=d['summary_raw']+b'\n')),
      ('changed-P-binding',lambda d:d['payload_raw'].update(p=d['payload_raw']['p']+b'\n')),
      ('changed-N-binding',lambda d:d['payload_raw'].update(n=d['payload_raw']['n']+b'\n')),
      ('changed-P-model',lambda d:d['models'].update(p=d['models']['p']+'\n')),
      ('changed-N-model',lambda d:d['models'].update(n=d['models']['n']+'\n')),
      ('changed-PLL-scalar-receipt',lambda d:d.update(observer_raw=d['observer_raw']+b'\n')),
      ('missing-second-model',lambda d:d['models'].pop('n')),
      ('aliased-model-paths',lambda d:d['model_paths'].update(n=d['model_paths']['p']))]:
        changed=copy.deepcopy(kwargs);edit(changed)
        faults.append(reject(label,lambda:bench.prepare(**changed)))
    assert len(cases)==4 and len(faults)==8
    return dict(status='PASS_FOUR_EXACT_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE',
      source_controls=source,cases=cases,actual_input_faults=faults,actual_model_preparation_executed=True,
      simulator_executed=False,**bench.FLAGS)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
