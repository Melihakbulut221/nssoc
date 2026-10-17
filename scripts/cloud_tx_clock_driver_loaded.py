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
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-clock-driver-loaded'
import compare_cloud_routed_endpoints as reports
from cloud_tx_driver_localpins_loaded import adapt,fixtures
from cloud_tx_driver_stage_repair import clock_candidate,CLOCK,CLOCK_SHA
from cloud_tx_driver_stage_repair_loaded import COMMON_METHOD_PINS
SOURCES={'l2p4-series-l6p2':dict(run=38946552766,group='tx-driver-pullup-compose-l2p4-series-l6p2',summary='1985f6e30bb729e6f02b706d5805d15b4436dd86ca508282e06a94397ede2a26',parts='85020905f7a7f7af79ed27659c151e5f5a637204afe57efbc27b510805aebbc3',model='6e77bfdac07cd973a37b7aca558c0c4aeea64ba76b3d5cb2486562df80ebaa3b')}
CLOCK_SOURCE=dict(run=38950944472,group='tx-clock-reference-compose-l6p2',summary='f5065cc41f2ae8da2ff4c144a2a2c1c601691536303ebfdfe88220d08eef10ef',parts='4a95f28c27da6d91ffb32b17b9ed314d032fc244de19ece6d98fbf6a15b9cc42',model='2188c3c4c7c723f314dc6c0b8a967fdcd927ecb71a66cbbf0ebe391365ffb116')
from cloud_tx_clock_loaded_adapter import adapt_clock
PROFILE='breakpoint_tight_trap'
def restore(spec):
    stem=spec['group']+'-'+str(spec['run'])+'-1'
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-1-'+spec['group']+'/'+stem+'.summary.json'
    fetch(url,spec['summary'],OUT/'composition-summary.json');frozen=json.loads((OUT/'composition-summary.json').read_text())
    source=OUT/'source';prior,proof=reports.restore_report(spec['group'],spec['run'],spec['summary'],spec['parts'],source,tuple(frozen['outputs']))
    assert prior==frozen and prior['source_unchanged']
    return source,prior,proof

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);args=parser.parse_args()
    OUT=ROOT/('hw/soc/out/cloud-tx-clock-driver-loaded-'+args.variant);SOURCE=SOURCES[args.variant];reports.OUT=OUT
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode='wire',variant=args.variant,source=SOURCE,serial_phy_complete=False,qualified_timing=False,mainchip_integrated=False,qualified_pex=False,component_screen_passed=False,
        clock_physical_model_used=True,matched_driver_physical_model_used=True,full_combined_physical_acceptance=False,
        scope='Eight actual raw100/260R295C drivers, actual162-device routed core, and actual native6/13R28C clock reference with finite body contacts. Full34ns/256bits/672MOS/62HBT/original phases, gates and zeroOP unchanged. External clock modulation, supplies, driver-core-clock connections and TX/bias elements not all physically integrated. No PVT/32:1/four-lane/fullPHY/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save();run=OUT/'native';run.mkdir()
    try:
        assert all(sha(ROOT/path)==digest for path,digest in COMMON_METHOD_PINS.items()),'Shared loaded-tree method drift'
        assert sha(CLOCK)==CLOCK_SHA
        source,prior,proof=restore(SOURCE);result['restore']=proof
        assert prior['variant']==args.variant
        assert prior['status']=='PASS_RAW100_AND_ALL260R295C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(prior['controls'])==10
        base=source/'inputs'/('tx-driver-pullup-intrinsic-'+args.variant)
        model=source/'driver100-wire.spice'
        assert sha(model)==SOURCE['model']==prior['model_sha256']
        result['original_driver_model_sha256']=sha(model)
        clockroot=OUT/'clock-source';selected=('clock6-wire.spice','inputs/tx-clock-reference-intrinsic-l6p2/pdk/libs.tech/ngspice/models/sg13g2_hbt_mod.lib','inputs/tx-clock-reference-intrinsic-l6p2/pdk/libs.tech/ngspice/models/resistors_mod.lib')
        cp,proof=reports.restore_report(CLOCK_SOURCE['group'],CLOCK_SOURCE['run'],CLOCK_SOURCE['summary'],CLOCK_SOURCE['parts'],clockroot,selected)
        assert cp['source_head']=='9dc1ef7c9d974c9840fd2f35b3c933953883cb5b'and cp['source_unchanged']and cp['variant']=='l6p2'
        assert cp['status']=='PASS_RAW6_AND_ALL13R28C_EXACT_CLOCK_COMPOSITION_WITH11_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(cp['controls'])==11 and all(c['rejected']for c in cp['controls'])
        clockmodel=clockroot/'clock6-wire.spice';assert sha(clockmodel)==CLOCK_SOURCE['model']==cp['model_sha256'];result['clock_restore']=proof

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
        for name in ['resistors_mod.lib','sg13g2_hbt_mod.lib']:
            assert sha(inputs/'models'/name)==sha(clockroot/'inputs/tx-clock-reference-intrinsic-l6p2/pdk/libs.tech/ngspice/models'/name),('Physical clock compact model changed',name)
        result['model_libraries']=modelpins;tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
        assert sha(tree.FRONT)==physical.DRIVER_SHA
        core,probes,scope=tree.assembled_tree_core(inputs,'wire','compact_return_strap');result['downstream_physical_core']=scope
        original,contract=tree.build(inputs,'nominal',clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=4,clock_reference='stiff65',assembled_core=core,interface_probes=probes,solver_profile=PROFILE)
        deck,contract,binding=adapt(original,contract,model);result['binding']=binding
        deck,contract,clockbinding=adapt_clock(deck,contract,clockmodel);result['clock_binding']=clockbinding
        result['clock_model_sha256']=sha(clockmodel)
        assert len(contract['hbt'])==62 and len(contract['mos'])==672
        (run/'original-schematic-driver-bench.cir').write_text(original)
        (run/'bench.cir').write_text(streaming_deck(deck,contract));(run/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        (run/'spinit').write_text('set num_threads=1\n')
        protected=[clockmodel,ROOT/'scripts/cloud_tx_clock_loaded_adapter.py',CLOCK,tree.CLOCK_REFERENCES['stiff65'],tree.CLOCK_FEEDS['stiff65'],*[ROOT/p for p in COMMON_METHOD_PINS],model,core,paths['patched'],run/'bench.cir',run/'contract.json',run/'spinit',tree.FRONT,tree.TX,
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
        assert all(sha(source/path)==digest for path,digest in prior['outputs'].items())
        assert all(sha(clockroot/p)==cp['outputs'][p]for p in selected)
        result['source_unchanged']=True
        result['status']='COMPLETE_ACTUAL_CLOCK_AND_DRIVER_FRESH_RC_LOADED_TREE_STUDY_NOT_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','mode','component_screen_passed','elapsed_s')}),flush=True)
if __name__=='__main__':main()
