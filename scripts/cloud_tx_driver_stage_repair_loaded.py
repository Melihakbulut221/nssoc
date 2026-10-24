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
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-pullup-loaded'
import compare_cloud_routed_endpoints as reports
from cloud_tx_driver_localpins_loaded import adapt,fixtures
from cloud_tx_driver_stage_repair import series_candidate,clock_candidate,CLOCK,CLOCK_SHA
COMMON_METHOD_PINS={'scripts/run_cloud_tx_mux4.py': '0aa343689a7524e1577861c134bf93004bc56b1e7f9cdb1fd6e270037d2216c6', 'scripts/cloud_tx_driver_localpins_loaded.py': 'db95b5b84bf8b2c9551da680efb878ed82712030cb45299361461dce4b6f24d9', 'scripts/cloud_tx_stream.py': '2894eede2e5e087c23cadee9cec9dbdca359315a786cec0cabfe7f8da37449cb', 'hw/soc/analog/pcie/tx_clock_bias_feed_v2.spice': '650579e07ec3c52c9ae1f429c3c9c56bec5b8761eae953bac33d08e0dbc4b8cc'}
SOURCES={
 'l2p7':dict(run=38935779019,group='tx-driver-pullup-compose-l2p7',summary='6011d01f3a47b3fb23698d3ddcd4f59e3e23739aa700cbcf0167675117378934',parts='df3bd23312c9670e3d1840f7b685a6000afed133a2c57c8d50188d37c6b5d9ca',model='1c880df545c06617347d3bca4bce3144034cb083e11e154eb198c160a5e36963'),
 'l2p4':dict(run=38935779019,group='tx-driver-pullup-compose-l2p4',summary='cf6515591ce239ff9a482d88fb01088173a0204803c62d344da724e00cf52ffd',parts='7acd44238caaf6314ca7df89fccb4bfe780b67858b0b334b8c59d4a8a049ef79',model='8eec4846d8cef0e3367c07f8e1a0f3413f4a628684bbb1a283c6f6883b95ad79'),
}
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
    parser=argparse.ArgumentParser();parser.add_argument('--repair',choices=['series','clock','combined'],required=True);parser.add_argument('--parent-summary-sha',required=True);args=parser.parse_args();args.variant='l2p4'
    OUT=ROOT/('hw/soc/out/cloud-tx-stage-repair-loaded-'+args.repair);SOURCE=SOURCES[args.variant];reports.OUT=OUT
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode='wire',variant=args.variant,repair=args.repair,source=SOURCE,serial_phy_complete=False,qualified_timing=False,mainchip_integrated=False,qualified_pex=False,component_screen_passed=False,
        scope='Eight actual100-device drivers with raw junctions/finite contacts, loaded by the actual162-device routed four-input tree. Driver wire case includes each260R295C. Full34ns256-bit8GT/s oracle unchanged. Tree-to-driver external connections, clocks and supplies remain ideal; no32:1/x4/CDR/PLL/ESD/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save();run=OUT/'native';run.mkdir()
    try:
        assert all(sha(ROOT/path)==digest for path,digest in COMMON_METHOD_PINS.items()),'Shared native method or clock feed drift'
        assert re.fullmatch(r'[0-9a-f]{64}',args.parent_summary_sha)
        parent_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38936139904-1-tx-driver-pullup-loaded-l2p4/tx-driver-pullup-loaded-l2p4-38936139904-1.summary.json'
        fetch(parent_url,args.parent_summary_sha,OUT/'measured-parent.json');parent=json.loads((OUT/'measured-parent.json').read_text())
        assert parent['status']=='COMPLETE_ACTUAL_PULLUP_DRIVER_FRESH_RC_LOADED_TREE_STUDY_NOT_PHY_ACCEPTANCE'
        assert parent['source_head']=='9e6679b30a0f31556d0ea32097cefd1c480dc47e' and parent['source_unchanged'] and parent['variant']=='l2p4'
        assert parent['original_driver_model_sha256']==SOURCE['model'] and parent['returncode']==0 and not parent['diagnostics']
        assert parent['review']['zero_source_op'] and parent['review']['coverage_s']==[0.0,3.4e-8]
        assert len(parent['review']['hbt_devices'])==62 and len(parent['review']['mos_devices'])==672
        assert not parent['component_screen_passed'],'Baseline already passed; reconsider need for this repair'
        result['measured_parent']=dict(run=38936139904,summary_sha256=args.parent_summary_sha,component_screen_passed=parent['component_screen_passed'])
        source,prior,proof=restore(SOURCE);result['restore']=proof
        assert prior['variant']==args.variant
        assert prior['status']=='PASS_RAW100_AND_ALL260R295C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(prior['controls'])==10
        base=source/'inputs'/('tx-driver-pullup-intrinsic-'+args.variant)
        model=source/'driver100-wire.spice'
        assert sha(model)==SOURCE['model']==prior['model_sha256']
        result['original_driver_model_sha256']=sha(model)
        result['stage_repair']={}
        if args.repair in ('series','combined'):
            candidate,change=series_candidate(model.read_text(),json.loads((base/'result.json').read_text()),prior)
            model=OUT/'series-candidate.spice';model.write_text(candidate);result['stage_repair']['series']=change
        if args.repair in ('clock','combined'):
            candidate,change=clock_candidate(CLOCK.read_text());clock=OUT/'clock-candidate.spice';clock.write_text(candidate)
            tree.CLOCK_REFERENCES=dict(tree.CLOCK_REFERENCES);tree.CLOCK_REFERENCES['stiff65']=clock;result['stage_repair']['clock']=change
        assert sha(CLOCK)==CLOCK_SHA
        result['effective_driver_model_sha256']=sha(model)
        result['scope']='Source-bound series6.92to6.2um and/or native clock offset6.5to6.2um sensitivity from actual physical l2p4 driver. Old wires frozen only for changed driver geometry; changed clock reference has no physical realization. Same full34ns/256bits/672MOS/62HBT/source phases and limits. No fitted clock source, accepted layout, PVT or fullPHY claim.'
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
        protected=[model,core,CLOCK,tree.CLOCK_REFERENCES['stiff65'],tree.CLOCK_FEEDS['stiff65'],*[ROOT/p for p in COMMON_METHOD_PINS],paths['patched'],run/'bench.cir',run/'contract.json',run/'spinit',tree.FRONT,tree.TX,
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
        result['source_unchanged']=True
        result['diagnostic_screen_passed']=result['component_screen_passed'];result['component_screen_passed']=False
        result['status']='COMPLETE_SOURCE_BOUND_STAGE_REPAIR_SENSITIVITY_NOT_PHYSICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','mode','component_screen_passed','elapsed_s')}),flush=True)
if __name__=='__main__':main()
