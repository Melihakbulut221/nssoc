#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose all 64 actual raw100 input drivers with the full native32:1 tree."""
import copy,json,os,re
from pathlib import Path
import cloud_tx_input_driver_localpins as physical
import cloud_tx_p4_drive3_builder as tree
from cloud_tx_stream import pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def adapt(deck,contract,model):
    original=deck;contract=copy.deepcopy(contract);rows=statements(model.read_text())
    formal=rows[0][2:];top=rows[0][1]
    assert rows[0][0]=='.subckt' and formal in [physical.PORTS,physical.PORTS+['wire_cref']]
    mos=[r for r in rows[1:-1]if len(r)>5 and r[5]in ('sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos')]
    assert len(mos)==84 and sum(r[5]=='sg13_hv_nmos'for r in mos)==40
    assert len([r for r in rows[1:-1]if r[0].startswith('XD')])==100
    oldmos=contract['mos'];assert len(oldmos)==512
    newmos={};instances={}
    for bank in range(32):
        for suffix in ('p','n'):
            name=f'd{bank}{suffix}';instance='xad_'+name
            portmap=dict(zip(physical.PORTS,[name+'0',name,'avdd','dvdd','0','0'],strict=True));portmap['wire_cref']='0'
            ports=[portmap[p]for p in formal];replacement=instance+' '+' '.join(ports)+' '+top
            pattern=r'(?mi)^XAD_'+name+r' [^\n]+$';matches=re.findall(pattern,deck)
            assert len(matches)==1 and matches[0].split()[1:7]==[name+'0',name,'avdd','dvdd','0','0']
            deck=re.sub(pattern,lambda _:replacement,deck);instances[instance]=replacement.split()
            def node(n):return portmap.get(n,instance+'.'+n.lower())
            for r in mos:newmos[instance+'.'+r[0].lower()]=dict(model=r[5],terminals=[node(n)for n in r[1:5]])
    assert len(newmos)==5376
    oldvectors=contract['vectors'];vectors=[v for v in oldvectors if not v.startswith('v(xad_')]
    nodes=sorted({n for row in newmos.values()for n in row['terminals']} - {'0'})
    vectors=list(dict.fromkeys([*vectors,*['v('+n+')'for n in nodes]]))
    assert len(vectors)==len(set(vectors)) and len(vectors)<30000
    for prefix in ('wrdata op.dat ','wrdata wave.dat '):
        old=prefix+' '.join(oldvectors);assert deck.count(old)==1
        deck=deck.replace(old,prefix+' '.join(vectors))
    oldsave='\n'.join(tree.native_save_commands(oldvectors));assert deck.count(oldsave)==1
    deck=deck.replace(oldsave,'\n'.join(tree.native_save_commands(vectors)))
    oldinclude=f'.include "{tree.FRONT}"';assert deck.count(oldinclude)==1
    deck=deck.replace(oldinclude,f'.include "{model}"')
    assert pwl_voltage_sources(deck)==pwl_voltage_sources(original),'Source or timing changed'
    assert re.findall(r'(?m)^tran .+$',deck)==re.findall(r'(?m)^tran .+$',original)
    contract.update(mos=newmos,vectors=vectors)
    def verify(candidate,observed):
        actual={r[0].lower():r for r in statements(candidate.split('.control\n')[0])if r[0].lower().startswith('xad_')}
        assert actual==instances,'Actual driver instance or port order changed'
        required={'v('+n+')'for row in newmos.values()for n in row['terminals']if n!='0'}
        assert required<=set(observed),'Unobserved actual MOS terminal'
        assert len(actual)==64 and len(newmos)==5376
    verify(deck,vectors);controls=[]
    for fault in ('missing_driver','swapped_driver_ports','missing_terminal_probe'):
        bad=deck;observed=list(vectors);first=next(iter(instances.values()));line=' '.join(first)
        if fault=='missing_driver':bad=bad.replace(line,'* actual driver removed',1)
        elif fault=='swapped_driver_ports':
            altered=list(first);altered[1],altered[2]=altered[2],altered[1];bad=bad.replace(line,' '.join(altered),1)
        else:observed.remove(next(v for v in vectors if v.startswith('v(xad_')))
        try:verify(bad,observed)
        except AssertionError as error:controls.append(dict(fault=fault,rejected=True,error=str(error)))
        else:raise AssertionError('Adapter corruption escaped: '+fault)
    return deck,contract,dict(driver_instances=64,raw_devices=6400,raw_mos=5376,wire_cref_boundary='external ideal ground, separate from intrinsic substrate node',controls=controls)

def restore_and_adapt(out,inputs,deck,contract):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert contract['streams']==32 and len(contract['mos'])==512
    out.mkdir(exist_ok=False)
    spec=json.loads((ROOT/'docs/evidence/tx-driver-localpins-loaded-input-20261016.json').read_text())
    assert spec['source']['run']==38909917993 and spec['model_sha256']=='c624e9d1597ac8b68a2fb4772673ad0ffade0c35a21a027cbd449de1e2acf3d6'
    physical.OUT=out
    source,prior=physical.restore(spec['source'])
    assert prior['status']=='PASS_RAW100_AND_ALL260R295C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
    assert len(prior['controls'])==10 and all(v['rejected']for v in prior['controls'])
    model=source/'driver100-wire.spice';assert sha(model)==spec['model_sha256']
    base=source/'inputs/tx-driver-localpins-intrinsic/cloud-tx-driver-localpins-intrinsic'
    modelpins={}
    for name,folder in [('resistors_mod.lib',inputs/'models'),('sg13g2_moslv_mod.lib',inputs/'frontend/models'),('sg13g2_moshv_mod.lib',inputs/'frontend/models')]:
        assert sha(folder/name)==sha(base/'pdk/libs.tech/ngspice/models'/name)
        modelpins[name]=sha(folder/name)
    assert sha(tree.FRONT)==physical.DRIVER_SHA
    original=copy.deepcopy(contract)
    candidate,contract,binding=adapt(deck,contract,model)
    assert all(contract[k]==v for k,v in original.items()if k not in ('vectors','mos'))
    assert len(contract['hbt'])==604 and len(contract['mos'])==5376
    assert len([r for r in statements(model.read_text())if r[0].startswith('R')])==260
    assert len([r for r in statements(model.read_text())if r[0].startswith('C')])==295
    binding.update(source=spec['source'],model_sha256=sha(model),model_libraries=modelpins,
        source_composition_controls=prior['controls'],driver_models_are_unmodified=True,
        actual_driver_instances=64,actual_raw_devices=6400,actual_raw_mos=5376,
        metal_resistors_per_driver=260,metal_capacitors_per_driver=295,
        external_interconnect_scope='Driver/core boundary wires and chip supplies remain ideal. This is a loaded native macro simulation, not an assembled full-PHY layout.',
        full_phy_accepted=False,mainchip_integrated=False)
    (out/'original-schematic-drivers.cir').write_text(deck)
    (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    return candidate,contract,binding
