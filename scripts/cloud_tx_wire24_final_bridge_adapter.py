#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Load the actual native2/3R8C bridge on final sp/sn; preserve the original bench."""
import copy,json,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_fast_wire24_builder as tree
from cloud_tx_stream import pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements,number
from run_cloud_tx_layout_repair import sha
SPEC=dict(run=39375939797,head='37467b505865a6ab2e109bfd294125c92f979d2f',
 summary='1006797a382ec2cf682e10a3d75b2906f3262f655a781915f9d521e7e2b520f7',
 parts='00700140bd18698b88e9a0ce91c5e64a5b21083015d3c2753adde4356c6ea41e',
 model='ad89ed29fe7507aad77844e2bdc4eec1e1aef224403ac34a3f321df5a53e61ff')
TOP='nssoc_tx_final_clock_bridge_native2_wire_v1'
def restore_and_adapt(out,inputs,deck,contract):
    reports.OUT=out;source=out/'final-bridge-source'
    selected=('bridge2-wire.spice','inputs/tx-final-clock-bridge-native/pdk/libs.tech/ngspice/models/resistors_mod.lib')
    prior,proof=reports.restore_report('tx-final-clock-bridge-compose',SPEC['run'],SPEC['summary'],SPEC['parts'],source,selected)
    assert prior['source_head']==SPEC['head'] and prior['source_unchanged']
    assert prior['status']=='PASS_RAW2_AND_ALL3R8C_EXACT_BRIDGE_COMPOSITION_WITH12_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
    assert prior['positive']==dict(devices=2,wire_resistors=3,wire_capacitors=8,terminals=5,wire_components=3,body_nodes=1,ports=['sp','sn','sub','wire_cref'])
    assert len(prior['controls'])==12 and all(c['rejected']for c in prior['controls'])
    model=source/'bridge2-wire.spice';assert sha(model)==SPEC['model']==prior['model_sha256']
    assert sha(inputs/'models/resistors_mod.lib')==sha(source/selected[1])
    deck,contract,binding=adapt(deck,contract,model)
    binding.update(source=proof,source_head=SPEC['head'])
    assert all(sha(source/p)==prior['outputs'][p]for p in selected)
    return deck,contract,binding,source

def adapt(deck,contract,model):
    assert sha(model)==SPEC['model']
    original=deck;before=copy.deepcopy(contract);contract=copy.deepcopy(contract)
    assert len(contract['hbt'])==604 and len(contract['mos'])==512 and contract['streams']==32
    rows=statements(model.read_text())
    assert rows[0]==['.subckt',TOP,'sp','sn','sub','wire_cref'] and rows[-1]==['.ends',TOP]
    assert sum(r[0].startswith('XD')for r in rows)==2
    assert sum(r[0].startswith('R')for r in rows)==3 and sum(r[0].startswith('C')for r in rows)==8
    assert deck.count('.control\n')==1
    for name in ('sp','sn'):
        assert deck.count('R'+name+' '+name+'0 '+name+' 25')==1
        assert deck.count('V'+name+' '+name+'0 clkbias PWL')==1
    instance='XFINALBRIDGE sp sn 0 0 '+TOP
    payload=f'.include "{model}"\n'+instance+'\n'
    assert 'XFINALBRIDGE'not in deck
    deck=deck.replace('.control\n',payload+'.control\n')
    # Preserve public source nodes and every internal bridge node in native output.
    nodes=set()
    for row in rows[1:-1]:
        width=3 if 'rppd'in row else 2
        nodes.update(row[1:1+width])
    assert nodes=={'sp','sn','sub','wire_cref','BULK','w00000','w00001','w00002'}
    required={'v('+('sp' if n=='sp'else'sn'if n=='sn'else'xfinalbridge.'+n.lower())+')'
              for n in nodes if n not in ('sub','wire_cref')}
    assert len(required)==6
    oldvectors=contract['vectors'];vectors=list(dict.fromkeys([*oldvectors,*sorted(required)]))
    assert len(vectors)<10000
    for prefix in ['wrdata op.dat ','wrdata wave.dat ']:
        old=prefix+' '.join(oldvectors);assert deck.count(old)==1
        deck=deck.replace(old,prefix+' '.join(vectors))
    oldsave='\n'.join(tree.native_save_commands(oldvectors))
    newsave='\n'.join(tree.native_save_commands(vectors))
    assert deck.count(oldsave)==1;deck=deck.replace(oldsave,newsave)
    contract['vectors']=vectors
    assert all(contract[k]==v for k,v in before.items()if k!='vectors')
    def verify(candidate,observed):
        assert candidate.count(payload)==1,'Bridge instance/include absent or duplicated'
        assert required<=set(observed),'Bridge terminal voltage omitted'
        recovered=candidate.replace(payload,'',1)
        for prefix in ['wrdata op.dat ','wrdata wave.dat ']:
            new=prefix+' '.join(vectors);assert recovered.count(new)==1,'Native output vector list changed'
            recovered=recovered.replace(new,prefix+' '.join(oldvectors))
        assert recovered.count(newsave)==1,'Native save vector list changed'
        recovered=recovered.replace(newsave,oldsave)
        assert recovered==original,'Original clock source, source resistance, circuit or analysis changed'
        assert pwl_voltage_sources(candidate)==pwl_voltage_sources(original)
        assert re.findall(r'(?m)^tran .+$',candidate)==re.findall(r'(?m)^tran .+$',original)
    verify(deck,vectors);controls=[]
    for fault in ['missing_bridge','wrong_port','duplicate_bridge','bypass_source_R','changed_clock_reference','missing_probe']:
        bad=deck;observed=list(vectors)
        if fault=='missing_bridge':bad=bad.replace(instance,'* missing bridge')
        elif fault=='wrong_port':bad=bad.replace(instance,instance.replace(' sp sn ',' sp sp '))
        elif fault=='duplicate_bridge':bad=bad.replace(instance,instance+'\n'+instance)
        elif fault=='bypass_source_R':bad=bad.replace('Rsp sp0 sp 25','Rsp sp0 sp 0')
        elif fault=='changed_clock_reference':bad=bad.replace('Vsp sp0 clkbias PWL','Vsp sp0 0 PWL')
        else:observed.remove('v(xfinalbridge.bulk)')
        assert bad!=deck or observed!=vectors
        try:verify(bad,observed)
        except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted bridge loaded bench corruption '+fault)
    return deck,contract,dict(model_sha256=sha(model),instance=instance,native_devices=2,
        wire_resistors=3,wire_capacitors=8,finite_contacts=1,added_required_probes=sorted(required),
        controls=controls,original_bench_exact_after_removing_only_bridge_and_added_probes=True,
        external_clock_modulation_unchanged=True,original_25ohm_sources_unchanged=True,
        external_substrate_and_wire_cref_ideal=True,intermacro_connections_ideal=True,
        qualified_substrate=False,qualified_pex=False,mainchip_integrated=False,full_phy_accepted=False)
