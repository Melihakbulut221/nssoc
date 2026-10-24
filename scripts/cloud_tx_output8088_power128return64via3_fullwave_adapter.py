#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace the8074 core and separate output with the actual8088 wire parent."""
import copy,json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_p4_drive3_builder as tree
from cloud_tx_chunked_op import save_commands
from cloud_tx_stream import pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_output8088_wire_v1'
def adapt(deck,contract,model,composition,interfaces):
    original=deck;old=copy.deepcopy(contract);new=copy.deepcopy(contract)
    assert len(old['hbt'])==604 and len(old['mos'])==5376
    assert sum(k.startswith('xtree.') for k in old['hbt'])==589
    assert sum(k.startswith('xtx.') for k in old['hbt'])==4
    assert all(k.startswith('xtree.') for k in old['mos'])
    rows=statements(model.read_text());formal=[v.lower() for v in rows[0][2:]]
    assert rows[0][:2]==['.subckt',TOP] and len(formal)==166
    assert [v.lower() for v in composition['interface']]==formal
    assert composition['counts']==dict(devices=8088,R=140222,C=99906,external_ports=166,physical_ports=165,metal_reference_planes=13370,body_nets=65,conductors=703,terminals=28620)
    assert composition['no_ideal_driver_core_interconnect'] and composition['every_terminal_reference_plane_preserved']
    assert interfaces['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
    assert set(interfaces['output_ports'])=={'op','on','tvdd','tr'}
    assert all(v['node']==k and v['reference_label']=='P_'+k for k,v in interfaces['output_ports'].items())
    xtree=re.findall(r'(?mi)^xtree [^\n]+$',deck);xtx=re.findall(r'(?mi)^xtx [^\n]+$',deck)
    assert len(xtree)==len(xtx)==1
    oldrow=xtree[0].split();oldtop=oldrow[-1].lower();txrow=xtx[0].split()
    assert txrow==['xtx','mp','mn','op','on','tvdd','0','0','tr','nssoc_tx_cml_rsil']
    includes=re.findall(r'(?mi)^\.include "([^"]+)"\s*$',deck)
    old_formal=None;removed=[]
    for path in includes:
        headers=[r for r in statements(Path(path).read_text()) if r[0].lower()=='.subckt']
        names={r[1].lower() for r in headers}
        if oldtop in names:
            assert old_formal is None
            old_formal=next([v.lower() for v in r[2:]] for r in headers if r[1].lower()==oldtop)
        if oldtop in names or txrow[-1] in names:
            line='.include "'+path+'"';assert deck.count(line)==1
            deck=deck.replace(line,'* replaced by actual8088 physical parent',1);removed.append(path)
    assert oldtop=='nssoc_tx_full32_raw8074_wire_v1' and old_formal is not None and len(removed)==2
    public=dict(zip(old_formal,oldrow[1:-1],strict=True))
    assert len(public)==164 and public['mp']=='mp' and public['mn']=='mn'
    assert public['avss']==public['sub']==public['wire_cref']=='0'
    new_public={k:v for k,v in public.items() if k not in ('mp','mn')}
    new_public.update(zip(('op','on','tvdd','tr'),(txrow[i] for i in (3,4,5,8)),strict=True))
    assert set(new_public)==set(formal)
    ports=[new_public[p] for p in formal]
    replacement='xtree '+' '.join(ports)+' '+TOP
    deck=deck.replace(xtree[0],replacement,1).replace(xtx[0],'* output14 is inside the actual8088 physical parent',1)
    deck=deck.replace('.control\n','.include "'+str(model)+'"\n.control\n',1)
    _,hbts=tree.bind_devices(model,'xtree',ports,{'npn13g2'})
    _,mos=tree.bind_devices(model,'xtree',ports,{'sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos'})
    assert len(hbts)==593 and len(mos)==5376
    external={k:v for k,v in old['hbt'].items() if not k.startswith(('xtree.','xtx.'))}
    assert len(external)==11
    new['hbt']=external|hbts;new['mos']=mos
    new['interface_probes']=copy.deepcopy(interfaces['modes']['wire'])
    assert set(new['interface_probes'])==set(old['interface_probes'])
    def node(n):
        n=n.lower();return new_public.get(n,'xtree.'+n)
    all_nodes={node(t['node']) for d in composition['device_records'] for t in d['terminals']}
    all_nodes|={v for probes in new['interface_probes'].values() for v in probes}
    all_nodes.discard('0')
    vectors=[]
    for v in old['vectors']:
        if v.startswith(('@q.xtree.','@q.xtx.')):continue
        if v.startswith('v('):
            n=v[2:-1]
            if n.startswith(('xtree.','xtx.')) or n in ('mp','mn'):continue
        vectors.append(v)
    vectors=list(dict.fromkeys([*vectors,*['v('+n+')' for n in sorted(all_nodes)],*['@q.'+n+'.qnpn13g2[ic]' for n in hbts]]))
    assert len(vectors)==len(set(vectors))<30000
    for prefix in ('wrdata op.dat ','wrdata wave.dat '):
        line=prefix+' '.join(old['vectors']);assert deck.count(line)==1
        deck=deck.replace(line,prefix+' '.join(vectors),1)
    oldsave='\n'.join(save_commands(old['vectors']));assert deck.count(oldsave)==1
    deck=deck.replace(oldsave,'\n'.join(save_commands(vectors)),1)
    def flags(names):
        result=[]
        for name in names:
            device='q.'+name+'.qnpn13g2'
            result += [f'alter @{device}[off] = 1','echo NSSOC_NATIVE_FLAG_BEGIN '+device,'show '+device+' : off','echo NSSOC_NATIVE_FLAG_END']
        return '\n'.join(result)
    oldflags=flags(old['hbt']);assert deck.count(oldflags)==1
    deck=deck.replace(oldflags,flags(new['hbt']),1);new['vectors']=vectors
    assert pwl_voltage_sources(deck)==pwl_voltage_sources(original),'Original source waveforms changed'
    assert re.findall(r'(?m)^tran .+$',deck)==re.findall(r'(?m)^tran .+$',original)
    assert re.findall(r'(?m)^\.options .+$',deck)==re.findall(r'(?m)^\.options .+$',original)
    assert all(new[k]==old[k] for k in old if k not in ('hbt','mos','interface_probes','vectors'))
    # Every other element/load/source card is unchanged. This includes all
    # external bias feeds, clock macros and original output loads.
    def external_cards(text):
        return [r for r in statements(text.split('.control\n')[0])
                if r[0][0] not in ('.','*') and r[0].lower() not in ('xtree','xtx')]
    assert external_cards(deck)==external_cards(original)
    def verify(candidate,c):
        lines=statements(candidate.split('.control\n')[0])
        assert [r for r in lines if r[0].lower()=='xtree']==[replacement.split()],'Actual8088 instance/port mapping changed'
        assert not any(r[0].lower()=='xtx' for r in lines),'Duplicate schematic output retained'
        assert external_cards(candidate)==external_cards(original),'External loads or sources changed'
        assert c['hbt']==new['hbt'] and c['mos']==new['mos'],'Native terminal census/binding changed'
        assert c['interface_probes']==interfaces['modes']['wire'],'Wrong actual input reference planes'
        assert len(c['hbt'])==604 and len(c['mos'])==5376 and len(c['interface_probes'])==124
        required={'v('+n+')' for n in all_nodes}|{'@q.'+n+'.qnpn13g2[ic]' for n in new['hbt']}
        assert required<=set(c['vectors']),'Missing actual terminal/current observation'
        assert not any('xtx.' in v or v in ('v(mp)','v(mn)') for v in c['vectors']),'Stale schematic output observation'
        assert '\n'.join(save_commands(c['vectors'])) in candidate,'Native saves do not match all observations'
    verify(deck,new);controls=[]
    for fault in ('swapped_output_polarity','swapped_output_supply_bias','duplicate_output','missing_hbt','missing_mos','wrong_data_plane','missing_terminal_probe','missing_hbt_current','stale_output_probe','changed_external_load'):
        bad=deck;c=copy.deepcopy(new)
        if fault in ('swapped_output_polarity','swapped_output_supply_bias'):
            a,b=('op','on') if fault=='swapped_output_polarity' else ('tvdd','tr')
            rr=replacement.split();i,j=formal.index(a)+1,formal.index(b)+1
            rr[i],rr[j]=rr[j],rr[i];assert rr!=replacement.split();bad=bad.replace(replacement,' '.join(rr),1)
        elif fault=='duplicate_output':bad=bad.replace('.control\n',xtx[0]+'\n.control\n',1)
        elif fault=='missing_hbt':c['hbt'].pop(next(iter(hbts)))
        elif fault=='missing_mos':c['mos'].pop(next(iter(mos)))
        elif fault=='wrong_data_plane':c['interface_probes'][next(iter(c['interface_probes']))][0]='0'
        elif fault=='missing_terminal_probe':c['vectors'].remove('v('+sorted(all_nodes)[0]+')')
        elif fault=='missing_hbt_current':c['vectors'].remove('@q.'+next(iter(hbts))+'.qnpn13g2[ic]')
        elif fault=='stale_output_probe':c['vectors'].append('v(mp)')
        else:bad=bad.replace('.control\n','Rinjected op on 1\n.control\n',1)
        try:verify(bad,c)
        except AssertionError as e:controls.append(dict(name=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    return deck,new,dict(status='PREPARED_ACTUAL8088_POWER128RETURN64VIA3_NATIVE_WIRE_BENCH_REQUIRES_CHECKPOINTED_FULL_TRANSIENT',
        counts=composition['counts'],hbt_count=604,mos_count=5376,physical_parent_hbts=593,external_clock_hbts=11,
        observed_whole_parent_terminal_nodes=len(all_nodes),controls=controls,
        original_stimuli_solver_timestep_external_loads_and_gates_unchanged=True,
        separate_schematic_output_removed=True,no_ideal_driver_core_or_output_interconnect=True,
        model_sha256=sha(model),full_serial_phy=False,mainchip_integrated=False,loaded_electrical_passed=False,
        remaining_boundaries='External clock modulation/intermacro clock wiring, supply/bias feeds, substrate/device-access/RF PEX and mainchip integration remain open.')
def restore_and_adapt(out,deck,contract):
    assert os.environ.get('GITHUB_ACTIONS')=='true';out.mkdir(exist_ok=False);previous=reports.OUT;reports.OUT=out
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64via3-interfaces-pass-20261023.json').read_text())
        assert pin['run']==40003582105 and pin['summary_sha256']=='48aa3b39422955f78d94749252eb8a545153979141d1bb7cd7f9f207c6e3949b'
        selected=['interfaces.json','composed/output8088-wire.spice','composed/composition.json']
        r,proof=reports.restore_report('tx-output8088-power128return64via3-interfaces',pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'source',selected)
        assert r==pin['report'] and r['sources_unchanged']
        assert len(r['controls'])==8 and len(r['actual_endpoint_faults'])==2 and len(r['output_port_controls'])==2
        assert all(sha(out/'source'/p)==r['outputs'][p] for p in selected)
        model=out/'source/composed/output8088-wire.spice'
        composition=json.loads((out/'source/composed/composition.json').read_text())
        interfaces=json.loads((out/'source/interfaces.json').read_text())
        candidate,new,binding=adapt(deck,contract,model,composition,interfaces);binding['source']=proof
        (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
        (out/'original8074-plus-schematic-output.cir').write_text(deck)
        return candidate,new,binding
    finally:reports.OUT=previous
