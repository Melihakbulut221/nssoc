#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""All eight raw100 input drivers loaded by the actual routed162-device tree.

Paired driver intrinsic/wire cases retain the same routed downstream tree,
original source bits and full34ns gates. Not x4/PLL/CDR/mainchip acceptance.
"""
import argparse,copy,json,os,re,resource,subprocess,tarfile,time
from decimal import Decimal
from pathlib import Path
import cloud_tx_input_driver_localpins as physical
import cloud_tx_companion_replay as engines
import run_cloud_tx_mux4 as tree
from cloud_tx_stream import streaming_deck,pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements,number
from run_cloud_tx_operating_point import fetch,sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-localpins-loaded'
SOURCE={'run': 38909917993, 'group': 'tx-driver-localpins-compose', 'root': 'cloud-tx-driver-localpins-compose', 'bytes': 8396068, 'sha': '94875bf3eefe06ee39ba3ce115867fe2c5df2017e5cfaf15da2a49441ca82259', 'summary': 'ed35b35933e6514ad4e4b1a694513f04f4783b68147005d2852019929cc55209'}
PROFILE='breakpoint_tight_trap'

def fixtures(dest):
    dest.mkdir()
    for name,spec,folder in [('native','pcie-tx-cloud-input-20261013.json',dest),('frontend','pcie-cmos-data-driver-input-20261013.json',dest/'frontend')]:
        pin=json.loads((ROOT/'docs/evidence'/spec).read_text())['receipt'];packed=dest/(name+'.tar.gz')
        fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
        with tarfile.open(packed)as archive:archive.extractall(folder,filter='data')
        packed.unlink();manifest=json.loads((folder/'manifest.json').read_text())
        assert all(sha(folder/p)==v['sha256']for p,v in manifest['files'].items())

def adapt(deck,contract,model):
    original=deck;contract=copy.deepcopy(contract);rows=statements(model.read_text())
    formal=rows[0][2:];top=rows[0][1]
    assert rows[0][0]=='.subckt' and formal in [physical.PORTS,physical.PORTS+['wire_cref']]
    mos=[r for r in rows[1:-1]if len(r)>5 and r[5]in ('sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos')]
    assert len(mos)==84 and sum(r[5]=='sg13_hv_nmos'for r in mos)==40
    assert len([r for r in rows[1:-1]if r[0].startswith('XD')])==100
    oldmos=contract['mos'];assert len(oldmos)==64
    newmos={};instances={}
    for bank in range(4):
        for suffix in ('p','n'):
            name=f'd{bank}{suffix}';instance='xad_'+name
            portmap=dict(zip(physical.PORTS,[name+'0',name,'avdd','dvdd','0','0'],strict=True));portmap['wire_cref']='0'
            ports=[portmap[p]for p in formal];replacement=instance+' '+' '.join(ports)+' '+top
            pattern=r'(?mi)^XAD_'+name+r' [^\n]+$';matches=re.findall(pattern,deck)
            assert len(matches)==1 and matches[0].split()[1:7]==[name+'0',name,'avdd','dvdd','0','0']
            deck=re.sub(pattern,lambda _:replacement,deck);instances[instance]=replacement.split()
            def node(n):return portmap.get(n,instance+'.'+n.lower())
            for r in mos:newmos[instance+'.'+r[0].lower()]=dict(model=r[5],terminals=[node(n)for n in r[1:5]])
    assert len(newmos)==672
    oldvectors=contract['vectors'];vectors=[v for v in oldvectors if not v.startswith('v(xad_')]
    nodes=sorted({n for row in newmos.values()for n in row['terminals']} - {'0'})
    vectors=list(dict.fromkeys([*vectors,*['v('+n+')'for n in nodes]]))
    assert len(vectors)==len(set(vectors)) and len(vectors)<10000
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
        assert len(actual)==8 and len(newmos)==672
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
    return deck,contract,dict(driver_instances=8,raw_devices=800,raw_mos=672,wire_cref_boundary='external ideal ground, separate from intrinsic substrate node',controls=controls)

def diagnostic_wires(original,mode):
    assert mode in ('wire_half_r','wire_half_c')
    before=statements(original)
    assert len([r for r in before if r[0].startswith('R')])==260
    assert len([r for r in before if r[0].startswith('C')])==295
    prefix='R'if mode=='wire_half_r'else'C'
    rows=[];changed=[]
    for row in before:
        if row[0].startswith(prefix):
            assert len(row)==4 and number(row[3])>0
            replacement=[*row[:3],str(number(row[3])*Decimal('.5'))]
            changed.append(dict(original=row,replacement=replacement));rows.append(replacement)
        else:rows.append(row)
    assert len(changed)==(260 if prefix=='R'else 295)
    assert len(rows)==len(before)
    def verify(candidate):
        assert len(candidate)==len(before)
        for original,row in zip(before,candidate,strict=True):
            if original[0].startswith(prefix):
                assert row[:3]==original[:3]and len(row)==4 and number(row[3])==number(original[3])*Decimal('.5')
            else:assert row==original,'Intrinsic device, finite contact, other wire element or port changed'
        assert len([r for r in candidate if r[0].startswith('XD')])==100
    verify(rows)
    bad=[list(r)for r in rows];victim=next(i for i,r in enumerate(bad)if r[0].startswith('XD'));bad[victim][1]='diagnostic_fault'
    try:verify(bad)
    except AssertionError as error:assert 'Intrinsic device'in str(error)
    else:raise AssertionError('Intrinsic terminal corruption escaped sensitivity audit')
    return '* DIAGNOSTIC ONLY: nonphysical half-wire sensitivity; never acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n',dict(mode=mode,changed=changed,scale='0.5',wire_nodes_or_intrinsic_devices_changed=False,physically_realized=False,intrinsic_terminal_fault='REJECTED')

def diagnostic_pullup(original, mode, intrinsic, composition):
    """Change one source-bound resistor geometry parameter, not wire RC or test limits."""
    lengths = {'pullup_l2p7': '2.7u', 'pullup_l2p4': '2.4u'}
    assert mode in lengths
    before = statements(original)
    assert sum(row[0].startswith('R') for row in before) == 260
    assert sum(row[0].startswith('C') for row in before) == 295
    assert sum(row[0].startswith('XD') for row in before) == 100
    native = [row for row in intrinsic['bindings'] if row['instance'] == 'XD87']
    assert len(native) == 1
    native = native[0]
    assert native['model'] == 'rppd' and native['nodes'] == ['avdd', 'dout', 'BULK']
    assert native['native_parameters'] == {'w': 4.0, 'l': 3.08, 'ps': 0.0, 'b': 0.0, 'm': 1.0}
    wired = [row for row in composition['bindings'] if row['instance'] == 'XD87']
    assert len(wired) == 1 and wired[0]['native_id'] == 87
    nodes = {row['terminal']: row['node'] for row in wired[0]['bindings']}
    index = next(i for i, row in enumerate(before) if row[0] == 'XD87')
    old = before[index]
    assert old[1:4] == [nodes[n] for n in native['named_terminal_order']]
    assert old[4] == 'rppd'
    params = dict(word.split('=', 1) for word in old[5:])
    assert len(params) == len(old[5:]) and set(params) == set(native['compact_parameters'])
    assert all(number(params[k]) == number(v) for k,v in native['compact_parameters'].items())
    rows = [list(row) for row in before]
    position = next(i for i, word in enumerate(old) if word.startswith('l='))
    rows[index][position] = 'l=' + lengths[mode]
    def verify(candidate):
        assert len(candidate) == len(before)
        for i, (a, b) in enumerate(zip(before, candidate, strict=True)):
            expected = list(a)
            if i == index:
                expected[position] = 'l=' + lengths[mode]
            assert b == expected, 'Undeclared device, terminal or wire change'
    verify(rows)
    controls = []
    for fault in ('gate_damping_changed', 'pullup_terminal_changed'):
        bad = [list(row) for row in rows]
        if fault == 'gate_damping_changed':
            gate = next(i for i,row in enumerate(bad) if row[0] == 'XD85')
            length = next(i for i,word in enumerate(bad[gate]) if word.startswith('l='))
            bad[gate][length] = 'l=6u'
        else:
            bad[index][1] = 'corrupted_pullup_terminal'
        try:
            verify(bad)
        except AssertionError as error:
            assert 'Undeclared' in str(error)
            controls.append(dict(fault=fault, rejected=True))
        else:
            raise AssertionError('Pullup sensitivity corruption escaped')
    return '* SCHEMATIC SENSITIVITY ONLY: new pullup length with frozen old wires.\n' + '\n'.join(' '.join(row) for row in rows) + '\n', dict(
        mode=mode, instance='XD87', native_id=87, original_length='3.08u',
        candidate_length=lengths[mode], original_row=old, candidate_row=rows[index],
        native_logical_nodes=native['nodes'], controls=controls,
        all260_wire_resistors_and295_capacitors_unchanged=True,
        gate_damping_and_all_other99_devices_unchanged=True,
        physically_realized=False, fresh_geometry_and_extraction_required=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('intrinsic','wire','wire_half_r','wire_half_c','pullup_l2p7','pullup_l2p4'),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode=args.mode,source=SOURCE,serial_phy_complete=False,qualified_timing=False,mainchip_integrated=False,qualified_pex=False,component_screen_passed=False,
        scope='Eight actual100-device drivers with raw junctions/finite contacts, loaded by the actual162-device routed four-input tree. Driver wire case includes each260R295C. Full34ns256-bit8GT/s oracle unchanged. Tree-to-driver external connections, clocks and supplies remain ideal; no32:1/x4/CDR/PLL/ESD/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save();run=OUT/'native';run.mkdir()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_RAW100_AND_ALL260R295C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(prior['controls'])==10
        base=source/'inputs/tx-driver-localpins-intrinsic/cloud-tx-driver-localpins-intrinsic'
        model=source/'driver100-wire.spice'if args.mode!='intrinsic'else base/'driver100.spice'
        assert sha(model)==('c624e9d1597ac8b68a2fb4772673ad0ffade0c35a21a027cbd449de1e2acf3d6'if args.mode!='intrinsic'else'f0a4f8dae1fa2e7ae7894c6325d21ea35c9aadf8253f7bc4b90313113fdd2ca5')
        result['original_driver_model_sha256']=sha(model)
        pullup=args.mode in ('pullup_l2p7','pullup_l2p4')
        diagnostic=pullup or args.mode in ('wire_half_r','wire_half_c')
        if diagnostic:
            url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38910247036-1-tx-driver-localpins-loaded-wire/tx-driver-localpins-loaded-wire-38910247036-1.summary.json'
            fetch(url,'0ba488d996b9cd251bf9ec457a22cb78fbe425aa4927f3af6e15c85ee9f0a5f8',OUT/'measured-parent.json')
            measured=json.loads((OUT/'measured-parent.json').read_text())
            assert measured['status']=='COMPLETE_RAW_DRIVER_LOADED_PHYSICAL_TREE_STUDY_NOT_PHY_ACCEPTANCE'and not measured['component_screen_passed']
            assert measured['original_driver_model_sha256']==sha(model)and measured['mode']=='wire'
            result['measured_parent']=dict(run=38910247036,summary_sha256='0ba488d996b9cd251bf9ec457a22cb78fbe425aa4927f3af6e15c85ee9f0a5f8',component_screen_passed=False)
            if pullup:
                text,change=diagnostic_pullup(model.read_text(),args.mode,json.loads((base/'result.json').read_text()),prior)
                result['pullup_sensitivity']=change
                result['scope']='Source-bound pullup resistor XD87 length3.08um to2.7um or2.4um, width4um retained. All260R295C wire elements, gate damping and99other intrinsic devices, full34ns/256bits/originalphases/672MOS/62HBT and limits unchanged. Frozen old wires do not match the proposed new resistor geometry. This schematic sensitivity can guide a fresh physical candidate but never supplies layout, PVT, qualifiedPEX or fullPHY acceptance.'
            else:
                text,change=diagnostic_wires(model.read_text(),args.mode)
                result['wire_sensitivity']=change
                result['scope']='Artificial wire sensitivity on the unchanged failed raw-driver/routed-tree study. Only all295wireC or all260wireR scaled0.5; every intrinsic device, finite contact, source bit, clock, load, probe and gate unchanged. Neither variant is a realizable physical model or an acceptance candidate.'
            model=OUT/'diagnostic-driver.spice';model.write_text(text)
        engines.OUT=OUT;paths,provenance=engines.restore_engines();result['runtime_provenance']=provenance
        assert sha(paths['patched'])=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        inputs=OUT/'fixtures';fixtures(inputs)
        # Reject accidental model-library drift between electrical fixtures and
        # the source-bound raw-device conversion, including the finite taps.
        modelpins={}
        for name,folder in [('resistors_mod.lib',inputs/'models'),('sg13g2_moslv_mod.lib',inputs/'frontend/models'),('sg13g2_moshv_mod.lib',inputs/'frontend/models')]:
            target=folder/name;reference=base/'pdk/libs.tech/ngspice/models'/name
            assert sha(target)==sha(reference),('Electrical model library changed',name)
            modelpins[name]=sha(target)
        result['model_libraries']=modelpins;tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
        assert sha(tree.FRONT)==physical.DRIVER_SHA
        core,probes,scope=tree.assembled_tree_core(inputs,'wire','compact_return_strap');result['downstream_physical_core']=scope
        original,contract=tree.build(inputs,'nominal',clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=4,clock_reference='stiff65',assembled_core=core,interface_probes=probes,solver_profile=PROFILE)
        deck,contract,binding=adapt(original,contract,model);result['binding']=binding
        assert len(contract['hbt'])==62 and len(contract['mos'])==672
        (run/'original-schematic-driver-bench.cir').write_text(original)
        (run/'bench.cir').write_text(streaming_deck(deck,contract));(run/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (run/'spinit').write_text('set num_threads=1\n')
        protected=[model,core,paths['patched'],run/'bench.cir',run/'contract.json',run/'spinit',tree.FRONT,tree.TX,
                   *inputs.rglob('*.lib'),*inputs.rglob('*.inc'),*inputs.rglob('*.osdi')]
        result['protected_inputs']={str(p):sha(p)for p in protected};save()
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(run),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        start=time.monotonic()
        with (run/'run.log').open('w')as log:code=subprocess.call([str(paths['patched']),'-n','-b','bench.cir'],cwd=run,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
        text=(run/'run.log').read_text(errors='replace');result.update(returncode=code,elapsed_s=time.monotonic()-start)
        assert code==0,'Simulator process failed'
        result['solver_options']=tree.verify_solver_options(text,PROFILE);result['diagnostics']=tree.native_diagnostics(text,PROFILE)
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [x[0]for x in flags]==['q.'+n+'.qnpn13g2'for n in contract['hbt']]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
        result['review']=tree.review(run,contract)
        assert len(result['review']['mos_devices'])==672 and len(result['review']['hbt_devices'])==62
        assert all(sha(p)==s for p,s in result['protected_inputs'].items())
        result['component_screen_passed']=result['review']['all_engineering_gates_passed']and not result['diagnostics']
        result['status']='COMPLETE_RAW_DRIVER_LOADED_PHYSICAL_TREE_STUDY_NOT_PHY_ACCEPTANCE'
        if diagnostic:
            result['diagnostic_screen_passed']=result['component_screen_passed'];result['component_screen_passed']=False
            result['status']='COMPLETE_PULLUP_DEVICE_SENSITIVITY_NOT_PHYSICAL_ACCEPTANCE' if pullup else 'COMPLETE_ARTIFICIAL_DRIVER_WIRE_SENSITIVITY_NOT_PHYSICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','mode','component_screen_passed','elapsed_s')}),flush=True)
if __name__=='__main__':main()
