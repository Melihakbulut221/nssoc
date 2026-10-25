#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace the actual reference and feed instances with the matching extracted macro."""
import copy,re
import run_cloud_tx_mux4 as tree
from build_pcie_local_vco_hybrid_v6 import statements
from cloud_tx_stream import pwl_voltage_sources

def adapt_clock(deck,contract,model):
    original=deck;before=copy.deepcopy(contract);contract=copy.deepcopy(contract)
    rows=statements(model.read_text());assert rows[0][0]=='.subckt'and rows[0][2:]==['avdd','cm','avss','sub','wire_cref']
    assert sum(r[0].startswith('XD')for r in rows)==6 and sum(r[0].startswith('R')for r in rows)==13 and sum(r[0].startswith('C')for r in rows)==28
    assert contract['streams']==4 and len(contract['clock_refs'])==1
    ref=contract['clock_refs'][0];assert ref==dict(node='clkbias',feed='clkfeed',probe='vclkbias_feed')
    oldnames=[n for n in contract['hbt']if n.startswith('xclkbias.')];assert len(oldnames)==1
    oldname=oldnames[0];assert contract['hbt'][oldname]['nx']==1
    top,found=tree.bind_devices(model,'xclkphys',['clkfeed','clkbias','0','0','0'],{'npn13g2'})
    assert len(found)==1;newname=next(iter(found));assert found[newname]['nx']==1
    replacement='XCLKPHYS clkfeed clkbias 0 0 0 '+top
    bias=re.findall(r'(?m)^XCLKBIAS [^\n]+$',deck);feed=re.findall(r'(?m)^XCLKFEED [^\n]+$',deck)
    assert len(bias)==len(feed)==1 and bias[0].split()[1:4]==['clkbias','0','0']and feed[0].split()[1:4]==['clkfeed','clkbias','0']
    deck=deck.replace(bias[0],replacement).replace(feed[0],'* Reference feed is inside the actual extracted clock macro.')
    for path in [tree.CLOCK_REFERENCES['stiff65'],tree.CLOCK_FEEDS['stiff65']]:
        line=f'.include "{path}"';assert deck.count(line)==1;deck=deck.replace(line,'* Original schematic clock include replaced by physical macro.')
    deck=deck.replace('.control\n',f'.include "{model}"\n.control\n',1)
    oldvectors=contract['vectors'];removed=[v for v in oldvectors if v.startswith('v(xclkbias.')or v=='@q.'+oldname+'.qnpn13g2[ic]']
    vectors=[v for v in oldvectors if v not in removed]
    required={'v('+n+')'for r in found.values()for n in r['terminals']if n!='0'}|{'@q.'+newname+'.qnpn13g2[ic]'}
    vectors=list(dict.fromkeys([*vectors,*sorted(required)]));assert len(vectors)<10000 and len(vectors)==len(set(vectors))
    for prefix in ['wrdata op.dat ','wrdata wave.dat ']:
        old=prefix+' '.join(oldvectors);assert deck.count(old)==1;deck=deck.replace(old,prefix+' '.join(vectors))
    old='\n'.join(tree.native_save_commands(oldvectors));assert deck.count(old)==1
    deck=deck.replace(old,'\n'.join(tree.native_save_commands(vectors)))
    # The native OFF readback controls must track the physical HBT's actual hierarchy.
    olddevice='q.'+oldname+'.qnpn13g2';newdevice='q.'+newname+'.qnpn13g2'
    assert deck.count(olddevice)==3;deck=deck.replace(olddevice,newdevice)
    contract['hbt']={newname if n==oldname else n:found[newname]if n==oldname else r for n,r in contract['hbt'].items()}
    contract['vectors']=vectors
    assert len(contract['hbt'])==62 and len(contract['mos'])==672
    assert {n:r for n,r in contract['hbt'].items()if n!=newname}=={n:r for n,r in before['hbt'].items()if n!=oldname}
    assert all(contract[k]==v for k,v in before.items()if k not in ['hbt','vectors'])
    assert pwl_voltage_sources(deck)==pwl_voltage_sources(original),'Source bits, supply ramp or modulation changed'
    assert re.findall(r'(?m)^tran .+$',deck)==re.findall(r'(?m)^tran .+$',original),'Capture or timestep changed'
    assert 'Vclkbias_feed avdd clkfeed 0'in deck
    def verify(candidate,observed):
        actual=[r for r in statements(candidate.split('.control\n')[0])if r[0].lower().startswith(('xclkphys','xclkbias','xclkfeed'))]
        assert actual==[replacement.split()],'Actual physical clock instance or ports changed'
        assert required<=set(observed),'Physical clock HBT terminal/current is unobserved'
        assert candidate.count(f'.include "{model}"')==1,'Physical clock model include changed'
        assert all(f'.include "{p}"'not in candidate for p in [tree.CLOCK_REFERENCES['stiff65'],tree.CLOCK_FEEDS['stiff65']]),'Schematic clock model restored'
    verify(deck,vectors);controls=[]
    for fault in ['missing_clock','swapped_clock_ports','missing_hbt_probe','duplicate_schematic_feed']:
        bad=deck;observed=list(vectors)
        if fault=='missing_clock':bad=bad.replace(replacement,'* clock removed')
        elif fault=='swapped_clock_ports':
            parts=replacement.split();parts[1],parts[2]=parts[2],parts[1];bad=bad.replace(replacement,' '.join(parts))
        elif fault=='missing_hbt_probe':observed.remove(next(v for v in sorted(required)if v.startswith('v(xclkphys.')))
        else:bad=bad.replace(replacement,replacement+'\n'+feed[0])
        try:verify(bad,observed)
        except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted physical clock adapter corruption '+fault)
    return deck,contract,dict(clock_instances=1,native_devices=6,wire_resistors=13,wire_capacitors=28,finite_contacts=3,new_hbt=found,removed_schematic_hbt=oldname,added_required_probes=sorted(required),removed_obsolete_probes=removed,controls=controls,external_clock_modulation_unchanged=True,external_supply_ground_and_wire_cref_ideal=True,intermacro_connections_ideal=True)
