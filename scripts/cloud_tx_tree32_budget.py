#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native full32:1 emitter/current scaling study; not a physical PHY proof."""
import argparse,hashlib,json,os,re,resource,subprocess,time
from decimal import Decimal
from pathlib import Path
import run_cloud_tx_mux4 as tree
import cloud_tx_companion_replay as engines
from cloud_tx_driver_localpins_loaded import fixtures
from cloud_tx_stream import streaming_deck,pwl_voltage_sources
from run_cloud_tx_operating_point import sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/analog/pcie/tx_mux2_hbt_cascade_v4.spice'
SOURCE_SHA='c24851159489e6947989738bc6859e6731326b77ca9e17acaac9f6bd2d7b1495'
FINAL=ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v10.spice'
FINAL_SHA='56b50efbbc138e8af973c63809799574da4ffb9c79b9ff5b5732c44e7e234df8'
PROFILE='breakpoint_tight_trap'

def records(text):return [r.split()for r in text.splitlines()if r.strip()and not r.startswith('*')]

def resized(text,nx):
    assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA and nx in (1,2,3,4)
    rows=records(text);expected=[];changes=[];top='nssoc_tx_mux2_budget_nx'+str(nx)+'_v1'
    # Reduce native mirror/device area and raise all eight native resistor L/W
    # ratios by the inverse factor. This is a hypothesis, not an RC-preserving
    # equivalence: compact-model geometry/parasitics are simulated afresh.
    dimensions={1:{'XRP':('1','1.1'),'XRN':('1','1.1'),'XBA':('1','307.2'),'XBB':('1','307.2'),'XFPR':('1','31.6'),'XFNR':('1','31.6'),'XSP':('1','3.6'),'XSN':('1','3.6')},2:{'XRP':('2','1.1'),'XRN':('2','1.1'),'XBA':('1','153.6'),'XBB':('1','153.6'),'XFPR':('1','15.8'),'XFNR':('1','15.8'),'XSP':('1','1.8'),'XSN':('1','1.8')},3:{'XRP':('3','1.1'),'XRN':('3','1.1'),'XBA':('1','102.4'),'XBB':('1','102.4'),'XFPR':('1.5','15.8'),'XFNR':('1.5','15.8'),'XSP':('1.5','1.8'),'XSN':('1.5','1.8')},4:{'XRP':('4','1.1'),'XRN':('4','1.1'),'XBA':('1','76.8'),'XBB':('1','76.8'),'XFPR':('2','15.8'),'XFNR':('2','15.8'),'XSP':('2','1.8'),'XSN':('2','1.8')}}[nx]
    for old in rows:
        new=list(old)
        if old[0].lower()in ('.subckt','.ends'):new[1]=top
        elif 'npn13G2'in old:
            assert old[-1]==('Nx=1'if old[0]=='XREF'else'Nx=8')
            if old[0]!='XREF':new[-1]='Nx='+str(nx)
        elif 'rppd'in old:
            w,l=dimensions[old[0]];prior=dict(v.split('=',1)for v in old[5:]);assert prior.keys()=={'w','l','b','sw_et'}
            # Exact cross-products avoid rounding a recurring 8/3 ratio.
            assert Decimal(l)*Decimal(prior['w'][:-1])*nx==8*Decimal(w)*Decimal(prior['l'][:-1])
            new[5:]=['w='+w+'u','l='+l+'u','b=0','sw_et=1']
        else:raise AssertionError(old)
        if new!=old:changes.append(dict(before=old,after=new))
        expected.append(new)
    assert sum('npn13G2'in r for r in expected)==19 and sum('rppd'in r for r in expected)==8
    assert sum(int(r[-1].split('=')[1])for r in expected if 'npn13G2'in r)==1+18*nx
    result='* Native device/resistor scaling candidate; requires fresh layout and PVT.\n'+'\n'.join(' '.join(r)for r in expected)+'\n'
    def verify(candidate):assert records(candidate)==expected,'Undeclared topology or physical parameter change'
    verify(result);controls=[]
    for fault in ('reference_area','tail_area','load_geometry','data_terminal'):
        bad=[list(r)for r in expected]
        if fault=='reference_area':next(r for r in bad if r[0]=='XREF')[-1]='Nx=2'
        elif fault=='tail_area':next(r for r in bad if r[0]=='XT_0')[-1]='Nx=8'
        elif fault=='load_geometry':next(r for r in bad if r[0]=='XRP')[6]='l=999u'
        else:next(r for r in bad if r[0]=='XAP_0')[2]='wrong_data'
        try:verify('\n'.join(' '.join(r)for r in bad))
        except AssertionError:controls.append(fault)
        else:raise AssertionError('Sizing corruption escaped checker')
    return result,dict(nx=nx,emitters=1+18*nx,resistance_ratio=str(Decimal(8)/nx),changes=changes,actual_parameter_faults_rejected=controls,compact_parasitics_recomputed_by_native_model=True,physical_layout_matches=False)

def trim_dividers(text,nx):
    assert nx in (1,3)
    original,_=resized(SOURCE.read_text(),nx)
    assert text==original,'Unbound original sizing source'
    before=records(text);expected=[list(r)for r in before]
    old,new=('31.6','30') if nx==1 else ('15.8','15.4')
    changed=[]
    for row in expected:
        if row[0] not in ('XFPR','XFNR'):continue
        assert row[6]=='l='+old+'u' and row[5]==('w=1u' if nx==1 else 'w=1.5u')
        row[6]='l='+new+'u';changed.append(row[0])
    assert changed==['XFPR','XFNR']
    def verify(candidate):
        assert records(candidate)==expected,'Undeclared divider or topology change'
    candidate='* Fixed common-mode/headroom trim; requires native corners and fresh physical proof.\n'+'\n'.join(' '.join(r)for r in expected)+'\n'
    verify(candidate);faults=[]
    for label in ('untrimmed','wrong_width','tail_area','data_terminal'):
        bad=[list(r)for r in expected]
        if label=='untrimmed':bad=before
        elif label=='wrong_width':next(r for r in bad if r[0]=='XFPR')[5]='w=7u'
        elif label=='tail_area':next(r for r in bad if r[0]=='XT_0')[-1]='Nx=99'
        else:next(r for r in bad if r[0]=='XAP_0')[2]='wrong_data'
        try:verify('\n'.join(' '.join(r)for r in bad))
        except AssertionError:faults.append(label)
        else:raise AssertionError('Actual trim corruption accepted')
    return candidate,dict(source_sha256=hashlib.sha256(text.encode()).hexdigest(),candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),changed_instances=changed,old_l_um=old,new_l_um=new,widths_and_other_records_unchanged=True,rejected_controls=faults,physical_layout_matches=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=('baseline','budget','budget_high8','budget_high2','budget_high3','budget_high3_trim','budget_all1'),required=True);p.add_argument('--fault',choices=('none','swap_leaf_select'),default='none');p.add_argument('--condition',choices=('nominal','hot_low','cold_high'),default='nominal');args=p.parse_args()
    assert args.variant!='baseline'or args.fault=='none'
    assert args.condition=='nominal'or(args.variant in ('budget_high3','budget_high3_trim')and args.fault=='none')
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-tx-tree32-budget-'+args.variant+'-'+args.fault+(''if args.condition=='nominal'else'-'+args.condition));out.mkdir(exist_ok=False);native=out/'native';native.mkdir()
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,fault=args.fault,condition=args.condition,condition_parameters=tree.CONDITIONS[args.condition],accepted=False,full_serial_phy_complete=False,physical_layout_matches=False,schematic_screen_passed=False,scope='New actual full32-input/five-level transistor schematic at250Mb/s per input and8Gb/s output. 30pre+1final, native resistor bias, external differential clock modulation, schematic CMOS drivers and ideal intermacro connections. Every604HBT/512MOS terminal/current captured and original34ns/256bits/three phases/device limits retained. Original4427-emitter physical tree remains rejected. New candidate needs fresh cells/GDS/LVS/DRC/PEX, actual raw100 frontends/physical clock, all corners, RX/PLL/CDR, four lanes and mainchip before acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        assert sha(SOURCE)==SOURCE_SHA and sha(FINAL)==FINAL_SHA
        inputs=out/'fixtures';fixtures(inputs);engines.OUT=out;paths,provenance=engines.restore_engines();result['runtime_provenance']=provenance
        assert sha(paths['patched'])=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        low,prooflow=resized(SOURCE.read_text(),1)
        high_nx={'budget_high2':2,'budget_high3':3,'budget_high3_trim':3,'budget_all1':1}.get(args.variant,4)
        high,proofhigh=resized(SOURCE.read_text(),high_nx)
        # The measured Nx4 candidate failed 32 HBT VCE checks in a/b.
        # Keep those two fast stages at the original, hash-bound Nx8 topology;
        # retain Nx1 in all 28 lower-rate stages. No limits or stimuli change.
        if args.variant=='budget_high8':
            high=SOURCE.read_text()
            proofhigh=dict(nx=8,emitters=145,resistance_ratio='1',changes=[],
                           source_sha256=SOURCE_SHA,unchanged_original_cell=True,
                           compact_parasitics_recomputed_by_native_model=True,
                           physical_layout_matches=False)
        clock_key='stiff65'
        if args.variant=='budget_high3_trim':
            low,prooflow['divider_trim']=trim_dividers(low,1)
            high,proofhigh['divider_trim']=trim_dividers(high,3)
            clock_key='stiff625'
            clock_path=ROOT/'hw/soc/analog/pcie/tx_clock_common_bias_trim625_v1.spice'
            assert sha(clock_path)=='597ecb6d90aed4f6fe0ed0f425a5925cd836969cbd9502a9ebffa54ef90719ca'
            tree.CLOCK_REFERENCES[clock_key]=clock_path
            tree.CLOCK_FEEDS[clock_key]=tree.CLOCK_FEEDS['stiff65']
            result['fixed_headroom_candidate']=dict(low_output_resistor_l_um=30.,high_output_resistor_l_um=15.4,clock_offset_l_um=6.25,clock_source_sha256=sha(clock_path),per_corner_retuning=False,new_layout_or_rc_accepted=False)
        lowpath=out/'pre-nx1.spice';lowpath.write_text(low)
        highpath=out/('pre-nx'+str(proofhigh['nx'])+'.spice');highpath.write_text(high)
        result['sizing']={'low':prooflow,'high':proofhigh}
        tree.PRE=SOURCE if args.variant=='baseline'else lowpath
        tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
        deck,contract=tree.build(inputs,args.condition,fault=args.fault,clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=32,final_override=FINAL,clock_reference=clock_key,solver_profile=PROFILE)
        stimuli=pwl_voltage_sources(deck);original_vectors=list(contract['vectors'])
        assert len(contract['tree_plan']['nodes'])==30 and contract['streams']==32 and len(contract['hbt'])==604 and len(contract['mos'])==512
        if args.variant not in ('baseline','budget_all1'):
            selected=[n for n in contract['tree_plan']['nodes']if n['stride']==2];assert {n['label']for n in selected}=={'a','b'}
            for n in selected:
                instance='xpre'+n['label'];lines=re.findall(r'(?m)^'+instance+r' [^\n]+$',deck);assert len(lines)==1
                row=lines[0].split();top,found=tree.bind_devices(highpath,instance,row[1:-1],{'npn13g2'})
                assert len(found)==19 and set(found)<set(contract['hbt'])
                assert all(found[k]['terminals']==contract['hbt'][k]['terminals']for k in found)
                contract['hbt'].update(found);deck=deck.replace(lines[0],' '.join([*row[:-1],top]),1)
            old=f'.include "{lowpath}"';assert deck.count(old)==1;deck=deck.replace(old,old+f'\n.include "{highpath}"',1)
        assert pwl_voltage_sources(deck)==stimuli and contract['vectors']==original_vectors
        assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
        assert tree.UI==125e-12 and tree.START==2e-9 and tree.BITS==256 and abs(tree.STOP-34e-9)<1e-22
        stages={}
        for n in contract['tree_plan']['nodes']:
            rows={k:v for k,v in contract['hbt'].items()if k.startswith('xpre'+n['label']+'.')};assert len(rows)==19
            expected=8 if args.variant=='baseline'else proofhigh['nx'] if n['stride']==2 else 1
            assert sorted(r['nx']for r in rows.values())==[1]+[expected]*18
            stages[n['label']]=dict(stride=n['stride'],emitters=sum(r['nx']for r in rows.values()))
        final=[v for k,v in contract['hbt'].items()if k.startswith('xmux.')];assert len(final)==19 and sum(r['nx']for r in final)==77
        tree_emitters=sum(r['emitters']for r in stages.values())+77;assert tree_emitters=={'baseline':4427,'budget':755,'budget_high8':899,'budget_high2':683,'budget_high3':719,'budget_high3_trim':719,'budget_all1':647}[args.variant]
        result['budget']=dict(stages=stages,tree_emitters=tree_emitters,four_lane_tree_only=4*tree_emitters,explicit_lane_hbt_emitters=sum(r['nx']for r in contract['hbt'].values()),remaining_chip_blocks_included=False,whole_chip_emitter_budget_passed=False)
        (native/'bench.cir').write_text(streaming_deck(deck,contract));(native/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected=[Path(__file__),SOURCE,FINAL,lowpath,highpath,tree.FRONT,tree.TX,tree.PRE_FEED,tree.OUTPUT_FEEDS,tree.CLOCK_REFERENCES[clock_key],tree.CLOCK_FEEDS[clock_key],ROOT/'scripts/run_cloud_tx_mux4.py',ROOT/'scripts/cloud_tx_stream.py',ROOT/'scripts/cloud_tx_data_driver.py',paths['patched'],*[p for p in inputs.rglob('*')if p.is_file()],native/'bench.cir',native/'contract.json',native/'spinit']
        result['protected_inputs']={str(q):sha(q)for q in protected};save()
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        start=time.monotonic()
        with (native/'run.log').open('w')as log:code=subprocess.call([str(paths['patched']),'-n','-b','bench.cir'],cwd=native,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
        text=(native/'run.log').read_text(errors='replace');result.update(returncode=code,elapsed_s=time.monotonic()-start)
        assert code==0,'Native simulation failed'
        result['solver_options']=tree.verify_solver_options(text,PROFILE);result['diagnostics']=tree.native_diagnostics(text,PROFILE)
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in contract['hbt']]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
        result['native_off_flags_count']=len(flags);result['review']=tree.review(native,contract)
        assert set(result['review']['interfaces'])=={'cmos','final','level_4','level_8','level_16'}
        assert all(sha(Path(q))==h for q,h in result['protected_inputs'].items());result['source_unchanged']=True
        result['schematic_screen_passed']=args.fault=='none'and result['review']['all_engineering_gates_passed']and not result['diagnostics']
        if args.fault!='none':
            result['actual_leaf_fault_rejected_by_original_bits']=not result['review']['signals']['passed'];assert result['actual_leaf_fault_rejected_by_original_bits'],'Actual deepest selector fault escaped original bit oracle'
        result['status']='COMPLETE_NATIVE_TREE32_EMITTER_STUDY_NOT_PHYSICAL_ACCEPTANCE'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()and q!=out/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','variant','fault','schematic_screen_passed')}),flush=True)
if __name__=='__main__':main()
