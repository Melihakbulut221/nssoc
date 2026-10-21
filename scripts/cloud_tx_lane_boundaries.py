#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory actual saved TX lane boundaries before physical parent integration."""
import hashlib,json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from build_pcie_local_vco_hybrid_v6 import statements,number
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-lane-boundaries'
PREPARED=Path('/home/runner/work/nssoc/nssoc/cloud-tx-raw8074-prepared-wire-nominal-none')
def definitions(text):
    result={};active=None
    for row in statements(text):
        key=row[0].lower()
        if key=='.subckt':
            assert active is None
            name=row[1].lower();assert name not in result
            formal=[]
            for token in row[2:]:
                if token.lower()=='params:'or '='in token:break
                formal.append(token.lower())
            result[name]=dict(formal=formal,header=row,body=[])
            active=name
        elif key=='.ends':
            assert active is not None
            active=None
        elif active is not None:result[active]['body'].append(row)
    assert active is None
    return result
def analyze(deck,contract,models):
    lines=deck.splitlines()
    assert lines[0]=='NSSOC native full 32:1 tree, unchanged source-bit oracle'
    rows=statements('\n'.join(lines[1:]).split('.control\n',1)[0])
    top={r[0].lower():r for r in rows if not r[0].startswith('.')}
    assert len(top)==len([r for r in rows if not r[0].startswith('.')]),'Duplicate top-level primitive'
    assert len(contract['hbt'])==604 and len(contract['mos'])==5376
    assert len(contract['clock_refs'])==11 and len(contract['tree_plan']['clocks'])==31
    core=top['xtree'];assert core[-1].lower()=='nssoc_tx_full32_raw8074_wire_v1'
    formal=models[core[-1].lower()]['formal'];assert len(formal)==164
    ports=dict(zip(formal,[x.lower()for x in core[1:-1]],strict=True))
    hbts=contract['hbt']
    core_hbts={k:v for k,v in hbts.items()if k.startswith('xtree.')}
    clock_hbts={k:v for k,v in hbts.items()if k.startswith('xclkphys')}
    output_hbts={k:v for k,v in hbts.items()if k.startswith('xtx.')}
    assert len(core_hbts)==589 and len(clock_hbts)==11 and len(output_hbts)==4
    assert set(hbts)==set(core_hbts)|set(clock_hbts)|set(output_hbts)
    groups=[];handoffs=[];clock_sources=set();clock_resistors=set()
    for index,ref in enumerate(contract['clock_refs']):
        suffix=''if index==0 else'_g'+str(index)
        inst='xclkphys'+suffix;row=top[inst]
        variant='l5p7'if index in (0,2,3,4)else'l6p25'
        expected='nssoc_clock_reference_'+variant+'_native6_wire_v1'
        assert row[-1].lower()==expected
        assert [x.lower()for x in row[1:-1]]==[ref['feed'],ref['node'],'0','0','0']
        assert models[expected]['formal']==['avdd','cm','avss','sub','wire_cref']
        members=contract['tree_plan']['clocks'][index*3:(index+1)*3]
        assert 1<=len(members)<=3
        groups.append(dict(index=index,instance=inst,variant=variant,reference_node=ref['node'],
            supply_feed=ref['feed'],clock_names=[c['name']for c in members],
            placed_with_core=False,reference_to_modulator_is_ideal=True))
        for clock in members:
            assert clock['reference']==ref['node']
            for leg in 'pn':
                key=clock['name']+leg;v=top['v'+key];r=top['r'+key]
                assert [n.lower()for n in v[1:3]]==[key+'0',ref['node']]
                assert v[3].upper().startswith('PWL')
                assert [n.lower()for n in r[1:3]]==[key+'0',key]and len(r)==4 and number(r[3])==25
                assert ports[key]==key,'Nominal core clock endpoint changed'
                clock_sources.add(v[0].lower());clock_resistors.add(r[0].lower())
                handoffs.append(dict(clock=clock['name'],leg=leg,group=index,
                    reference_node=ref['node'],reference_instance=inst,
                    ideal_modulator=v[0],modulator_endpoints=v[1:3],
                    modulation_card_sha256=hashlib.sha256(' '.join(v).encode()).hexdigest(),
                    schematic_series_resistor=r,core_formal=key,core_actual=ports[key],
                    period_s=clock['period'],origin_s=clock['origin'],
                    modulation_implemented_in_hardware=False,series_resistor_placed_and_extracted=False,
                    intermacro_route_placed_and_extracted=False))
    assert len(handoffs)==len(clock_sources)==len(clock_resistors)==62
    instances=[]
    for label,row in top.items():
        if not label.startswith('x'):continue
        model=row[-1].lower();assert model in models,('Unresolved active top-level model',label,model)
        desc=models[model];actual=[x.lower()for x in row[1:-1]]
        assert len(actual)==len(desc['formal']),(label,actual,desc['formal'])
        role='actual8074_physical_parent'if label=='xtree'else'individual_clock_leaf_not_parent_integrated'if label.startswith('xclkphys')else'schematic_external_instance_requires_layout_binding'
        body=[]if label=='xtree'else desc['body']
        instances.append(dict(instance=label,model=model,role=role,ports=dict(zip(desc['formal'],actual,strict=True)),
            header=desc['header'],external_body_cards=body,
            outside_current_physical_parent=label!='xtree'))
    assert next(i for i in instances if i['instance']=='xtx')['ports']==dict(inp='mp',inn='mn',outp='op',outn='on',avdd='tvdd',avss='0',sub='0',iref='tr')
    other_primitives=[]
    for label,row in top.items():
        if label.startswith('x')or label in clock_sources or label in clock_resistors:continue
        if label in ('rload','cop','con'):role='declared_external_output_test_load'
        elif label in ('vavdd','vtvdd','vdvdd'):role='declared_supply_stimulus_requires_physical_power_network'
        elif re.fullmatch(r'vd\d+[pn]',label):role='declared_digital_input_stimulus_requires_mainchip_driver_connection'
        elif label.startswith('v')and len(row)==4 and number(row[3])==0:role='zero_voltage_current_probe_requires_finite_physical_route'
        else:role='unclassified_external_primitive_requires_explicit_resolution'
        other_primitives.append(dict(name=row[0],endpoints=row[1:3],role=role,
            card=(row if len(row)<20 else row[:3]+['<full stimulus retained in immutable deck>']),
            card_sha256=hashlib.sha256(' '.join(row).encode()).hexdigest()))
    assert not any(x['role'].startswith('unclassified') for x in other_primitives),'Unresolved actual top-level primitive'
    return dict(title=lines[0],clock_groups=groups,clock_handoffs=handoffs,top_instances=instances,
        other_top_primitives=other_primitives,external_output_hbts=output_hbts,
        hbt_ownership=dict(core=589,clock_leaves=11,output_stage=4,total=604),
        scope='Actual nominal saved8074 bench boundaries. The11clock6 leaves,62ideal differential modulation sources,62schematic25ohm legs and schematic output/bias instances are NOT a physically assembled lane. Supply/data stimuli and external output loads remain separately classified; do not treat testbench sources as fabricated circuitry.',
        physical_handoffs_complete=False,full_serial_phy=False,mainchip_integrated=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-raw8074-preparation-pass-20261021.json').read_text())['cases']['none']
        assert pin['run']==39518358552 and pin['summary_sha256']=='3479396a12e86147e40b4da481e6c11101950e5c88ea16e2d0618bce68625496'
        selected=[n for n in pin['outputs']if n in ('native/bench.cir','native/contract.json')or n.endswith(('/clock6-wire.spice','/raw8074-wire.spice'))]
        assert len(selected)==5
        selected+=sorted(n for n in pin['outputs'] if n.startswith('fixtures/') and n.endswith(('.inc','.spice','.lib')))
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior['source_unchanged']and prior['status']=='READY_ACTUAL8074_PHYSICAL_WIRE_DECK_NOT_SIMULATED'
        assert prior['core_counts']==dict(devices=8074,R=137221,C=98241)
        assert prior['model_sha256']=='4b249f619ab6c4d192714f25c7d2c1a72b21491d788edc42aa2adc53ef261969'
        deck=(OUT/'source/native/bench.cir').read_text()
        contract=json.loads((OUT/'source/native/contract.json').read_text())
        assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
        models={};includes=[]
        for raw in re.findall(r'(?mi)^\.include "([^"]+)"\s*$',deck.split('.control\n',1)[0]):
            source=Path(raw)
            assert source.is_absolute()and'..'not in source.parts
            if source.is_relative_to(PREPARED):
                relative=str(source.relative_to(PREPARED));assert relative in selected,('Active include missing from restored source set',relative)
                path=OUT/'source'/relative;expected=prior['outputs'][relative]
            else:
                assert source.is_relative_to(ROOT)
                path=source;expected=prior['protected_inputs'][raw]
            assert sha(path)==expected
            text=path.read_text();defs=definitions(text)
            assert not set(defs)&set(models),'Duplicate active subcircuit definition'
            models.update(defs);includes.append(dict(original_path=raw,sha256=expected,subcircuits=list(defs)))
        result=analyze(deck,contract,models)
        faults=[]
        first=result['clock_handoffs'][0];clockrow=first['schematic_series_resistor'];original=' '.join(clockrow)
        assert original in deck
        variants={
            'unexpected_behavioral_source':deck.replace('.control\n','BUNBOUND extra 0 V=1\n.control\n',1),
            'missing_clock_resistor':deck.replace(original,'* missing physical handoff candidate',1),
            'wrong_clock_endpoint':deck.replace(original,' '.join([clockrow[0],clockrow[1],first['reference_node'],clockrow[3]]),1),
            'wrong_clock_reference':deck.replace(first['modulator_endpoints'][0]+' '+first['reference_node']+' PWL',first['modulator_endpoints'][0]+' avdd PWL',1),
            'wrong_native_clock_variant':deck.replace('XCLKPHYS clkfeed clkbias 0 0 0 nssoc_clock_reference_l5p7_native6_wire_v1','XCLKPHYS clkfeed clkbias 0 0 0 nssoc_clock_reference_l6p25_native6_wire_v1',1)}
        for name,mutant in variants.items():
            assert mutant!=deck,name
            try:analyze(mutant,contract,models)
            except (AssertionError,KeyError):faults.append(dict(name=name,rejected=True))
            else:raise AssertionError('Invalid actual clock handoff accepted: '+name)
        assert len(faults)==5
        (OUT/'clock-boundaries.json').write_text(json.dumps(result,indent=2)+'\n')
        r.update(source=proof,includes=includes,inventory=result,controls=faults,
            actual_deck_sha256=sha(OUT/'source/native/bench.cir'),actual_contract_sha256=sha(OUT/'source/native/contract.json'))
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True
        r['status']='INVENTORIED_ACTUAL_TX_CLOCK_MODULATION_BIAS_OUTPUT_BOUNDARIES_NOT_PHYSICAL_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:r.get(k)for k in ('status','error','full_phy_accepted')}))
if __name__=='__main__':main()
