#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""All eight raw100 input drivers loaded by the actual routed162-device tree.

Paired driver intrinsic/wire cases retain the same routed downstream tree,
original source bits and full34ns gates. Not x4/PLL/CDR/mainchip acceptance.
"""
import argparse,copy,json,os,re,resource,subprocess,tarfile,time
from pathlib import Path
import cloud_tx_input_driver as physical
import cloud_tx_companion_replay as engines
import run_cloud_tx_mux4 as tree
from cloud_tx_stream import streaming_deck,pwl_voltage_sources
from build_pcie_local_vco_hybrid_v6 import statements
from run_cloud_tx_operating_point import fetch,sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-loaded'
SOURCE=dict(run=38876864912,group='tx-driver-compose',root='cloud-tx-driver-compose',bytes=8351085,sha='e963365560c3096f2127c9a8052dfe8c182f6fb96aae200de3c46cf5e1764afc',summary='088b313a9cdf0d1803842b3ae0eefda12af07d75c36cd4c7bd79b126d2b71cf7')
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

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('intrinsic','wire'),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode=args.mode,source=SOURCE,serial_phy_complete=False,qualified_timing=False,mainchip_integrated=False,qualified_pex=False,component_screen_passed=False,
        scope='Eight actual100-device drivers with raw junctions/finite contacts, loaded by the actual162-device routed four-input tree. Driver wire case includes each251R294C. Full34ns256-bit8GT/s oracle unchanged. Tree-to-driver external connections, clocks and supplies remain ideal; no32:1/x4/CDR/PLL/ESD/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save();run=OUT/'native';run.mkdir()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_RAW100_AND_ALL251R294C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(prior['controls'])==10
        base=source/'inputs/tx-driver-intrinsic/cloud-tx-driver-intrinsic'
        model=source/'driver100-wire.spice'if args.mode=='wire'else base/'driver100.spice'
        assert sha(model)==('e0219a2c161fdf5b522be533010432a3f7fd472112ae4cfbb6ee82490702c408'if args.mode=='wire'else'f0a4f8dae1fa2e7ae7894c6325d21ea35c9aadf8253f7bc4b90313113fdd2ca5')
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
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','mode','component_screen_passed','elapsed_s')}),flush=True)
if __name__=='__main__':main()
