#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace ideal driver/core joins with the actual whole8074 wire model."""
import copy,json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_p4_drive3_builder as tree
from cloud_tx_chunked_op import save_commands
from cloud_tx_stream import pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def adapt(deck,contract,model,composition,interfaces):
    original=deck;old=copy.deepcopy(contract);new=copy.deepcopy(contract)
    assert len(old['hbt'])==604 and len(old['mos'])==5376
    core_hbt={k:v for k,v in old['hbt'].items() if k.startswith('xtree.')}
    assert len(core_hbt)==589 and all(k.startswith('xad_') for k in old['mos'])
    rows=statements(model.read_text());formal=[v.lower() for v in rows[0][2:]]
    assert rows[0][0]=='.subckt' and rows[0][1]=='nssoc_tx_full32_raw8074_wire_v1'
    assert [v.lower() for v in composition['interface']]==formal and len(formal)==164
    assert composition['counts']['devices']==8074 and composition['counts']['R']==137221 and composition['counts']['C']==98241
    assert composition['no_ideal_driver_core_interconnect']
    assert interfaces['status']=='PASS_ACTUAL8074_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_REQUIRES_LOADED_WAVES'
    xtree=re.findall(r'(?mi)^xtree [^\n]+$',deck);assert len(xtree)==1
    oldrow=xtree[0].split();oldtop=oldrow[-1].lower()
    drivers=re.findall(r'(?mi)^xad_\S+ [^\n]+$',deck);assert len(drivers)==64
    driver_models={r.split()[-1].lower() for r in drivers};assert len(driver_models)==1
    includes=re.findall(r'(?mi)^\.include "([^"]+)"\s*$',deck)
    old_formal=None;removed_includes=[]
    for path in includes:
        s=Path(path).read_text()
        headers=[r for r in statements(s) if r[0].lower()=='.subckt']
        names={r[1].lower() for r in headers}
        if oldtop in names:
            assert old_formal is None
            old_formal=next([v.lower() for v in r[2:]] for r in headers if r[1].lower()==oldtop)
        if oldtop in names or names & driver_models:
            line='.include "'+path+'"';assert deck.count(line)==1
            deck=deck.replace(line,'* replaced by actual whole8074 physical model',1);removed_includes.append(path)
    assert old_formal is not None and len(removed_includes)==2
    public=dict(zip(old_formal,oldrow[1:-1],strict=True))
    data={f'd{i}{leg}' for i in range(32) for leg in 'pn'}
    assert data<=set(public)
    new_public={k:v for k,v in public.items() if k not in data}
    for d in data:
        line=next(r for r in drivers if r.split()[0].lower()=='xad_'+d).split()
        assert line[1:7]==[d+'0',d,'avdd','dvdd','0','0']
        new_public[d+'0']=d+'0'
    new_public['dvdd']='dvdd'
    assert set(new_public)==set(formal) and new_public['wire_cref']=='0'
    ports=[new_public[p] for p in formal]
    replacement='xtree '+' '.join(ports)+' '+rows[0][1]
    deck=deck.replace(xtree[0],replacement,1)
    for line in drivers:
        assert deck.count(line)==1;deck=deck.replace(line,'* driver included in actual whole8074 model',1)
    deck=deck.replace('.control\n','.include "'+str(model)+'"\n.control\n',1)
    top,hbts=tree.bind_devices(model,'xtree',ports,{'npn13g2'})
    _,mos=tree.bind_devices(model,'xtree',ports,{'sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos'})
    assert len(hbts)==589 and len(mos)==5376
    new['hbt']={k:v for k,v in old['hbt'].items() if not k.startswith('xtree.')}|hbts
    new['mos']=mos;new['interface_probes']=interfaces['modes']['wire']
    assert set(new['interface_probes'])==set(old['interface_probes'])
    def node(n):
        n=n.lower();return new_public.get(n,'xtree.'+n)
    all_nodes={node(t['node']) for r in composition['device_records'] for t in r['terminals']}
    all_nodes|={v for probes in new['interface_probes'].values() for v in probes}
    all_nodes.discard('0')
    vectors=[]
    for v in old['vectors']:
        if v.startswith('@q.xtree.'):continue
        if v.startswith('v('):
            n=v[2:-1]
            if n.startswith(('xtree.','xad_')) or n in data:continue
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
    def verify(candidate,c):
        lines=statements(candidate.split('.control\n')[0])
        assert [r for r in lines if r[0].lower()=='xtree']==[replacement.split()],'Whole-parent instance/port mapping changed'
        assert not any(r[0].lower().startswith('xad_') for r in lines),'Ideal-connected duplicate driver retained'
        assert c['hbt']==new['hbt'] and c['mos']==new['mos'],'Native terminal census/binding changed'
        assert c['interface_probes']==interfaces['modes']['wire'],'Wrong physical data planes'
        assert len(c['hbt'])==604 and len(c['mos'])==5376 and len(c['interface_probes'])==124
        required={'v('+n+')' for n in all_nodes}|{'@q.'+n+'.qnpn13g2[ic]' for n in new['hbt']}
        assert required<=set(c['vectors']),'Missing actual terminal/current observation'
    verify(deck,new);controls=[]
    for fault in ('wrong_whole_port','duplicate_driver','missing_hbt','missing_mos','wrong_data_plane','missing_terminal_probe','missing_hbt_current'):
        bad=deck;c=copy.deepcopy(new)
        if fault=='wrong_whole_port':
            rr=replacement.split();rr[1],rr[2]=rr[2],rr[1];assert rr!=replacement.split();bad=bad.replace(replacement,' '.join(rr),1)
        elif fault=='duplicate_driver':bad=bad.replace('.control\n',drivers[0]+'\n.control\n',1)
        elif fault=='missing_hbt':c['hbt'].pop(next(iter(hbts)))
        elif fault=='missing_mos':c['mos'].pop(next(iter(mos)))
        elif fault=='wrong_data_plane':c['interface_probes'][next(iter(c['interface_probes']))][0]='0'
        elif fault=='missing_terminal_probe':c['vectors'].remove('v('+next(iter(all_nodes))+')')
        else:c['vectors'].remove('@q.'+next(iter(hbts))+'.qnpn13g2[ic]')
        try:verify(bad,c)
        except AssertionError as e:controls.append(dict(name=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    return deck,new,dict(status='PREPARED_ACTUAL8074_NATIVE_WIRE_BENCH_REQUIRES_CHECKPOINTED_FULL_TRANSIENT',
       counts=composition['counts'],hbt_count=604,mos_count=5376,observed_whole_parent_terminal_nodes=len(all_nodes),
       controls=controls,original_stimuli_solver_and_timestep_unchanged=True,no_ideal_driver_core_interconnect=True,
       model_sha256=sha(model),full_serial_phy=False,mainchip_integrated=False,loaded_electrical_passed=False,
       remaining_ideal_boundaries='External clock modulation/clock macro interconnect, supply and output frontend boundaries; not complete PHY layout.')
def restore_and_adapt(out,deck,contract):
    assert os.environ.get('GITHUB_ACTIONS')=='true';out.mkdir(exist_ok=False);reports.OUT=out
    pin=json.loads((ROOT/'docs/evidence/tx-raw8074-interfaces-pass-20261021.json').read_text())
    assert pin['run']==39516735474 and pin['summary_sha256']=='a92c9e84d20f34d5c99a74b66750a6f5419f0427e22f98af068aa4f6489ca9df'
    selected=['interfaces.json','composed/raw8074-wire.spice','composed/composition.json']
    r,proof=reports.restore_report('tx-raw8074-interfaces',pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'source',selected)
    assert r==pin['report'] and r['sources_unchanged']
    assert len(r['controls'])==8 and len(r['actual_endpoint_faults'])==2
    model=out/'source/composed/raw8074-wire.spice'
    composition=json.loads((out/'source/composed/composition.json').read_text())
    interfaces=json.loads((out/'source/interfaces.json').read_text())
    candidate,new,binding=adapt(deck,contract,model,composition,interfaces)
    assert all(sha(out/'source'/p)==r['outputs'][p] for p in selected)
    binding['source']=proof
    (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    (out/'original-ideal-handoff.cir').write_text(deck)
    return candidate,new,binding
