#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all eleven full32 clock references to their actual six-device RC macro."""
import copy,re
import cloud_tx_v5_return64_builder as tree
from build_pcie_local_vco_hybrid_v6 import statements
from cloud_tx_stream import pwl_voltage_sources
from run_cloud_tx_layout_repair import sha

MODEL_SHA='c2f8e8dc96806c020fdef24547419c425dfc93b915c2c35437a9ae03860fe06a'

FIRST_MODEL_SHA="1f4eb38c991e326a7803536376d5249634e333772bc4ca49f5a7b277fed7c91f"

def adapt_clock32(deck,contract,model,first_group_model=None):
    assert sha(model)==MODEL_SHA
    original=deck;before=copy.deepcopy(contract);contract=copy.deepcopy(contract)
    if first_group_model is not None:
        assert sha(first_group_model)==FIRST_MODEL_SHA
        first_rows=statements(first_group_model.read_text())
        assert first_rows[0]==['.subckt','nssoc_clock_reference_l5p7_native6_wire_v1','avdd','cm','avss','sub','wire_cref']
        assert sum(r[0].startswith('XD')for r in first_rows)==6
        assert sum(r[0].startswith('R')for r in first_rows)==13
        assert sum(r[0].startswith('C')for r in first_rows)==28
        assert [c['name']for c in contract['tree_plan']['clocks'][:3]]==['sa','sb','s']
        for clock in ('sa','sb','s'):
            for suffix in ('p','n'):
                assert re.search(r'(?m)^V'+clock+suffix+r' '+clock+suffix+r'0 clkbias PWL',deck)

    assert contract['streams']==32 and contract['clock_reference']=='stiff625'
    assert contract['clock_reference_sha256']=='597ecb6d90aed4f6fe0ed0f425a5925cd836969cbd9502a9ebffa54ef90719ca'
    assert contract['clock_feed_sha256']=='650579e07ec3c52c9ae1f429c3c9c56bec5b8761eae953bac33d08e0dbc4b8cc'
    assert len(contract['hbt'])==604 and len(contract['mos'])==512 and len(contract['clock_refs'])==11
    rows=statements(model.read_text());assert rows[0]==['.subckt','nssoc_clock_reference_l6p25_native6_wire_v1','avdd','cm','avss','sub','wire_cref']
    assert sum(r[0].startswith('XD')for r in rows)==6 and sum(r[0].startswith('R')for r in rows)==13 and sum(r[0].startswith('C')for r in rows)==28
    replacements=[];oldfeeds=[];rename={};newhbt={};required=set()
    for index,ref in enumerate(contract['clock_refs']):
        suffix=''if index==0 else '_g'+str(index)
        assert ref==dict(node='clkbias'+suffix,feed='clkfeed'+suffix,probe='vclkbias_feed'+suffix)
        oldnames=[n for n in contract['hbt']if n.startswith('xclkbias'+suffix+'.')];assert len(oldnames)==1
        old=oldnames[0];assert contract['hbt'][old]['nx']==1
        selected_model=first_group_model if index==0 and first_group_model is not None else model
        top,found=tree.bind_devices(selected_model,'xclkphys'+suffix,[ref['feed'],ref['node'],'0','0','0'],{'npn13g2'})
        assert len(found)==1;new=next(iter(found));assert found[new]['nx']==1
        rename[old]=new;newhbt.update(found)
        replacement='XCLKPHYS'+suffix+' '+ref['feed']+' '+ref['node']+' 0 0 0 '+top
        bias=re.findall(r'(?m)^XCLKBIAS'+re.escape(suffix)+r' [^\n]+$',deck)
        feed=re.findall(r'(?m)^XCLKFEED'+re.escape(suffix)+r' [^\n]+$',deck)
        assert len(bias)==len(feed)==1
        assert bias[0].split()[1:4]==[ref['node'],'0','0'] and feed[0].split()[1:4]==[ref['feed'],ref['node'],'0']
        deck=deck.replace(bias[0],replacement).replace(feed[0],'* Physical clock macro contains reference and feed '+str(index))
        replacements.append(replacement.split());oldfeeds.append(feed[0])
        required|={'v('+n+')'for r in found.values()for n in r['terminals']if n!='0'}|{'@q.'+new+'.qnpn13g2[ic]'}
        assert 'Vclkbias_feed'+suffix+' avdd '+ref['feed']+' 0'in deck
    assert len(rename)==len(newhbt)==11
    includes=[tree.CLOCK_REFERENCES['stiff625'],tree.CLOCK_FEEDS['stiff625']]
    for path in includes:
        line=f'.include "{path}"';assert deck.count(line)==1
        deck=deck.replace(line,'* Schematic clock include replaced by physical macro.')
    physical_models=[model]+([]if first_group_model is None else[first_group_model])
    deck=deck.replace('.control\n',''.join(f'.include "{p}"\n'for p in physical_models)+'.control\n',1)
    oldvectors=contract['vectors']
    removed={v for v in oldvectors if v.startswith('v(xclkbias')or v in {'@q.'+n+'.qnpn13g2[ic]'for n in rename}}
    vectors=list(dict.fromkeys([*[v for v in oldvectors if v not in removed],*sorted(required)]))
    assert len(vectors)<10000 and len(vectors)==len(set(vectors))
    for prefix in ['wrdata op.dat ','wrdata wave.dat ']:
        old=prefix+' '.join(oldvectors);assert deck.count(old)==1;deck=deck.replace(old,prefix+' '.join(vectors))
    old='\n'.join(tree.native_save_commands(oldvectors));assert deck.count(old)==1
    deck=deck.replace(old,'\n'.join(tree.native_save_commands(vectors)))
    for old,new in rename.items():
        device='q.'+old+'.qnpn13g2';assert deck.count(device)==3
        deck=deck.replace(device,'q.'+new+'.qnpn13g2')
    contract['hbt']={rename[n]if n in rename else n:newhbt[rename[n]]if n in rename else r for n,r in contract['hbt'].items()}
    contract['vectors']=vectors
    assert len(contract['hbt'])==604 and len(contract['mos'])==512
    assert {n:r for n,r in contract['hbt'].items()if n not in newhbt}=={n:r for n,r in before['hbt'].items()if n not in rename}
    assert all(contract[k]==v for k,v in before.items()if k not in ('hbt','vectors'))
    assert pwl_voltage_sources(deck)==pwl_voltage_sources(original)
    assert re.findall(r'(?m)^tran .+$',deck)==re.findall(r'(?m)^tran .+$',original)
    def verify(candidate,observed):
        actual=[r for r in statements(candidate.split('.control\n')[0])if r[0].lower().startswith(('xclkphys','xclkbias','xclkfeed'))]
        assert actual==replacements,'Physical clock instances or ports changed'
        assert required<=set(observed),'Physical HBT terminal/current omitted'
        assert all(candidate.count(f'.include "{p}"')==1 for p in physical_models)
        assert all(f'.include "{p}"'not in candidate for p in includes)
    verify(deck,vectors);controls=[]
    # Corrupt every group's actual instance, not only a representative clock.
    for index,replacement in enumerate(replacements):
        line=' '.join(replacement)
        for fault in ('missing_clock','swapped_ports','missing_hbt_probe','duplicate_feed'):
            bad=deck;observed=list(vectors)
            if fault=='missing_clock':bad=bad.replace(line,'* Removed actual clock')
            elif fault=='swapped_ports':
                words=list(replacement);words[1],words[2]=words[2],words[1];bad=bad.replace(line,' '.join(words))
            elif fault=='missing_hbt_probe':
                prefix='v('+replacement[0].lower()+'.'
                observed.remove(next(v for v in sorted(required)if v.startswith(prefix)))
            else:bad=bad.replace(line,line+'\n'+oldfeeds[index])
            try:verify(bad,observed)
            except AssertionError as error:controls.append(dict(group=index,fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual clock binding corruption')
    assert len(controls)==44 and all(c['rejected']for c in controls)
    return deck,contract,dict(clock_instances=11,native_devices=66,wire_resistors=143,wire_capacitors=308,finite_contacts=33,controls=controls,
        first_group_model_sha256=sha(first_group_model)if first_group_model is not None else None,
        clock_variants=['l5p7'if first_group_model is not None else'l6p25']+['l6p25']*10,
        model_sha256=sha(model),new_hbt=newhbt,removed_schematic_hbt=list(rename),added_required_probes=sorted(required),removed_obsolete_probes=sorted(removed),
        external_clock_modulation_unchanged=True,external_supply_ground_and_wire_cref_ideal=True,intermacro_connections_ideal=True,
        qualified_substrate=False,qualified_pex=False,mainchip_integrated=False,full_phy_accepted=False)
