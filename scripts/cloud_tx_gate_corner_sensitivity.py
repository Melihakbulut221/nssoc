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
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-gate-corner-sensitivity'
import compare_cloud_routed_endpoints as reports
from cloud_tx_driver_localpins_loaded import adapt,fixtures
from cloud_tx_driver_stage_repair import clock_candidate,CLOCK,CLOCK_SHA
from cloud_tx_driver_stage_repair_loaded import COMMON_METHOD_PINS
SOURCES={'l2p4-series-l6p2':dict(run=38946552766,group='tx-driver-pullup-compose-l2p4-series-l6p2',summary='1985f6e30bb729e6f02b706d5805d15b4436dd86ca508282e06a94397ede2a26',parts='85020905f7a7f7af79ed27659c151e5f5a637204afe57efbc27b510805aebbc3',model='6e77bfdac07cd973a37b7aca558c0c4aeea64ba76b3d5cb2486562df80ebaa3b')}
CLOCK_SOURCE=dict(run=38963145890,group='tx-clock-reference-compose-l5p7',summary='f32864cece544bfd022ae74c5d2584838d028bce703d07e09008af5b4ce4c2ca',parts='519527defca6bf1fbfb40caa08b1afd8725c38eebc7270ffa09a3a2db1816586',model='1f4eb38c991e326a7803536376d5249634e333772bc4ca49f5a7b277fed7c91f')
from cloud_tx_clock_loaded_adapter import adapt_clock
PROFILE='breakpoint_tight_trap'
def restore(spec):
    stem=spec['group']+'-'+str(spec['run'])+'-1'
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-1-'+spec['group']+'/'+stem+'.summary.json'
    fetch(url,spec['summary'],OUT/'composition-summary.json');frozen=json.loads((OUT/'composition-summary.json').read_text())
    source=OUT/'source';prior,proof=reports.restore_report(spec['group'],spec['run'],spec['summary'],spec['parts'],source,tuple(frozen['outputs']))
    assert prior==frozen and prior['source_unchanged']
    return source,prior,proof



def gate_candidate(original,intrinsic,composition,length):
    import hashlib
    assert length in ('6','9')
    assert hashlib.sha256(original.encode()).hexdigest()==SOURCES['l2p4-series-l6p2']['model']
    rows=statements(original)
    assert sum(r[0].startswith('XD')for r in rows)==100
    assert sum(r[0].startswith('R')for r in rows)==260 and sum(r[0].startswith('C')for r in rows)==295
    matches=[b for b in intrinsic['bindings']if b['instance']=='XD85'];assert len(matches)==1
    bound=matches[0]
    assert bound['model']=='rppd' and bound['nodes']==['din','gate','BULK']
    assert bound['compact_parameters']==dict(w='2.0u',l='12.0u',ps='0.0u',b='0',m='1',sw_et='1')
    matches=[b for b in composition['bindings']if b['instance']=='XD85'];assert len(matches)==1
    linked=matches[0];assert linked['native_id']==85
    assert [b['terminal']for b in linked['bindings']]==bound['named_terminal_order']
    expected=[list(r)for r in rows];index=next(i for i,r in enumerate(expected)if r[0]=='XD85');old=rows[index]
    assert old==['XD85',*[b['node']for b in linked['bindings']],'rppd',*[k+'='+v for k,v in bound['compact_parameters'].items()]]
    at=old.index('l=12.0u');expected[index][at]='l='+length+'u'
    lines=original.splitlines();line=next(i for i,l in enumerate(lines)if l.startswith('XD85 '));lines[line]=' '.join(expected[index])
    changed='\n'.join(lines)+'\n'
    def verify(text):assert statements(text)==expected,'Undeclared device, wire, boundary or terminal change'
    verify(changed);faults=[]
    for name in ('wrong_gate_terminal','wrong_length','changed_wire','changed_MOS'):
        bad=[list(r)for r in expected]
        if name=='wrong_gate_terminal':bad[index][1]='unbound_gate_terminal'
        elif name=='wrong_length':bad[index][at]='l=12.0u'
        elif name=='changed_wire':next(r for r in bad if r[0].startswith('R'))[3]='123456'
        else:next(r for r in bad if r[0].startswith('XD')and any(v.startswith('sg13_')for v in r))[1]='wrong_mos_terminal'
        try:verify('\n'.join(' '.join(r)for r in bad)+'\n')
        except AssertionError as error:faults.append(dict(fault=name,rejected=True,reason=str(error)))
        else:raise AssertionError('Gate sensitivity corruption accepted')
    return changed,dict(instance='XD85',original=old,candidate=expected[index],controls=faults,
        original_model_sha256=hashlib.sha256(original.encode()).hexdigest(),candidate_model_sha256=hashlib.sha256(changed.encode()).hexdigest(),
        physically_realized=False,old_wire_rc_retained=True,all_other99devices_and555wires_unchanged=True,
        scope='Explicit resistor geometry hypothesis; new GDS/LVS/extraction and full-corner simulation required before physical adoption.')

def corner_contract(deck,contract,nominal,base,name):
    c=dict(base['condition']);c.update(tree.CONDITIONS[name]);assert contract['condition']==c
    assert all(contract[k]==v for k,v in base.items()if k not in ('condition','rails'))
    expect={'avdd':2.5*c['supply_scale'],'tvdd':1.8*c['supply_scale'],'dvdd':1.2*c['core_scale']}
    assert contract['rails']==expect
    def fixed(text,corner):
        sources=pwl_voltage_sources(text)
        for src in sources:text=text.replace(src,'* checked-source '+src.split()[0]+'\n')
        assert text.count('.temp '+str(corner['temperature_c'])+'\n')==1
        text=text.replace('.temp '+str(corner['temperature_c'])+'\n','.temp CHECKED\n')
        for kind,key in [('HBT','hbt'),('RES','resistor'),('MOSlv','lv_corner'),('MOShv','hv_corner')]:
            pattern=r'(?m)^(\.lib "[^\n"]*/corner'+kind+r'\.lib") '+re.escape(corner[key])+r'$'
            text,count=re.subn(pattern,r'\1 CHECKED',text);assert count==1,'Missing actual model corner '+kind
        return text,{v.split()[0].lower():v for v in sources}
    actual,sources=fixed(deck,c);reference,old=fixed(nominal,base['condition'])
    assert actual==reference,'Changed topology, probes, solver, source identity or capture'
    assert sources.keys()==old.keys()
    checked=[]
    for key,src in sources.items():
        def points(v):
            pre,body=v.split('PWL(',1);assert body.rstrip().endswith(')')
            values=body.rstrip()[:-1].replace('+',' ').split();assert len(values)%2==0
            return pre.split(),[number(v)for v in values]
        pre,a=points(src);oldpre,b=points(old[key]);assert pre==oldpre and len(a)==len(b)
        scale=c['core_scale']if re.fullmatch(r'vd[0-3][pn]',key)or key=='vdvdd'else c['supply_scale']if key in ('vavdd','vtvdd')else 1.
        factor=Decimal(str(scale))
        assert a[::2]==b[::2],'Source-bit or clock edge time changed'
        assert all(abs(x-y*factor)<Decimal('1e-13')for x,y in zip(a[1::2],b[1::2])),'Source amplitude is not declared corner scale'
        checked.append(dict(source=key,scale=scale,points=len(a)//2))
    assert len(checked)==17
    return dict(condition=c,rails=expect,all_source_edges_unchanged=True,sources=checked,
                source_bits_sha256=contract['source_bits_sha256'],original_capture_solver_topology_probes_unchanged=True,
                nominal_wire_rc_retained=True,complete_pvt_qualified=False)

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);parser.add_argument('--condition',choices=('hot_low','cold_high'),required=True);parser.add_argument('--gate-length',choices=('6','9'),required=True);args=parser.parse_args()
    OUT=ROOT/('hw/soc/out/cloud-tx-gate-corner-sensitivity-'+args.variant+'-'+args.condition+'-g'+args.gate_length+'u');SOURCE=SOURCES[args.variant];reports.OUT=OUT
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode='wire',variant=args.variant,condition_name=args.condition,source=SOURCE,full_pvt_qualified=False,wire_rc_corner='nominal_geometry',serial_phy_complete=False,qualified_timing=False,mainchip_integrated=False,qualified_pex=False,component_screen_passed=False,
        clock_variant='l5p7',clock_candidate_matches_geometry=True,clock_wire_rc_is_fresh_candidate_extraction=True,clock_physical_model_used=True,matched_driver_physical_model_used=False,driver_candidate_matches_geometry=False,physically_realized=False,gate_length_um=args.gate_length,full_combined_physical_acceptance=False,
        scope='SCHEMATIC SENSITIVITY: only native XD85 gate damping length12um to6um or9um in each raw100 driver; old260R295C wires retained and do not match new geometry. Actual162-device routed core and physical5p7clock unchanged. Full34ns/256bits/672MOS/62HBT/original phases, gates and zeroOP unchanged. External clock modulation, supplies, driver-core-clock connections and TX/bias elements not all physically integrated. Two transistor/temperature/supply corners with nominal geometry wire RC; no correlated RC-corner, complete PVT/32:1/four-lane/fullPHY/mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save();run=OUT/'native';run.mkdir()
    try:
        nominal_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38963616666-1-tx-clock-candidate-loaded-l2p4-series-l6p2/tx-clock-candidate-loaded-l2p4-series-l6p2-38963616666-1.summary.json'
        fetch(nominal_url,'ef5a73beacc646110a46b83f1cb8dee1427b73fcdf14deb69bce8329d9e7de41',OUT/'nominal-source.json')
        nominal_source=json.loads((OUT/'nominal-source.json').read_text())
        assert nominal_source['component_screen_passed'] and nominal_source['source_unchanged']
        assert nominal_source['clock_model_sha256']==CLOCK_SOURCE['model'] and nominal_source['original_driver_model_sha256']==SOURCE['model']
        result['nominal_source']=dict(run=38963616666,summary_sha256=sha(OUT/'nominal-source.json'))
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
        candidate,change=gate_candidate(model.read_text(),json.loads((base/'result.json').read_text()),prior,args.gate_length)
        model=OUT/'diagnostic-gate-driver.spice';model.write_text(candidate)
        result['gate_sensitivity']=change;result['candidate_driver_model_sha256']=sha(model)
        clockroot=OUT/'clock-source';selected=('clock6-wire.spice','inputs/tx-clock-reference-intrinsic-l5p7/pdk/libs.tech/ngspice/models/sg13g2_hbt_mod.lib','inputs/tx-clock-reference-intrinsic-l5p7/pdk/libs.tech/ngspice/models/resistors_mod.lib')
        cp,proof=reports.restore_report(CLOCK_SOURCE['group'],CLOCK_SOURCE['run'],CLOCK_SOURCE['summary'],CLOCK_SOURCE['parts'],clockroot,selected)
        assert cp['source_head']=='d8af62ad843f89363b59367374df3833a268175c'and cp['source_unchanged']and cp['variant']=='l5p7'
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
            assert sha(inputs/'models'/name)==sha(clockroot/'inputs/tx-clock-reference-intrinsic-l5p7/pdk/libs.tech/ngspice/models'/name),('Physical clock compact model changed',name)
        result['model_libraries']=modelpins;tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
        assert sha(tree.FRONT)==physical.DRIVER_SHA
        core,probes,scope=tree.assembled_tree_core(inputs,'wire','compact_return_strap');result['downstream_physical_core']=scope
        original,contract=tree.build(inputs,args.condition,clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=4,clock_reference='stiff65',assembled_core=core,interface_probes=probes,solver_profile=PROFILE)
        nominal,nominal_contract=tree.build(inputs,'nominal',clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=4,clock_reference='stiff65',assembled_core=core,interface_probes=probes,solver_profile=PROFILE)
        result['corner_contract']=corner_contract(original,contract,nominal,nominal_contract,args.condition)
        faults=[]
        mutations=[('nominal_temperature',original.replace('.temp '+str(contract['condition']['temperature_c']),'.temp 27',1)),
                   ('nominal_hbt',original.replace(' '+contract['condition']['hbt']+'\n',' hbt_typ\n',1)),
                   ('shortened_capture',re.sub(r'(?m)^(tran \S+) \S+',r'\1 1e-8',original,count=1)),
                   ('removed_input',original.replace('Vd0p d0p0 0 ','Vmissing d0p0 0 ',1))]
        for name,bad in mutations:
            assert bad!=original
            try:corner_contract(bad,contract,nominal,nominal_contract,args.condition)
            except AssertionError as error:faults.append(dict(fault=name,rejected=True,reason=str(error)))
            else:raise AssertionError('Corner contract mutation accepted '+name)
        result['corner_faults']=faults
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
        result['status']='COMPLETE_FROZEN_WIRE_GATE_LENGTH_SENSITIVITY_NOT_LAYOUT_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','mode','component_screen_passed','elapsed_s')}),flush=True)
if __name__=='__main__':main()
