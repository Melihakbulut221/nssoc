#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Checkpoint actual detailed-route work and continue it on another cloud VM.

The original global ODB/guides and native DRT arguments are immutable inputs.
DRT completion is not antenna/RC/STA/signoff acceptance.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from cloud_mainchip_process_checkpoint import TUNABLES,CRIU_COMMIT
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'cloud-mainchip-repair-deep-drt-runtime'
REPO='repos/Melihakbulut221/nssoc/'
PREFIX='source/run/1-openroad-detailedrouting/'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def digest(b):return hashlib.sha256(b).hexdigest()
LEGACY_CONTROLLER_SHA256='13060f197d5e9f75368e9db1e104d7f30381e3ca4bfa4f9d10e7c4438a625fc5'
GLOBAL_INPUTS=dict(global_candidate_instance_count=153130,
 global_odb_sha256='6bf5a055467ffea2e4fb0059ffcac4293d939171b0e17af6e224aee13b41c00c',
 global_guides_sha256='4b22365ef87d0c5880fe2e27732e6be19644f24cbcc2d309862a841b80721efb',
 candidate_netlist_sha256='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030',
 source_sdc_sha256='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597')
def validate_saved_source(spec,run,report,summary_sha,parts_sha,compatible):
    assert set(spec)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256'}
    assert type(spec['run'])is int and spec['run']>0 and spec['attempt']==1
    assert spec['group']=='mainchip-repair-deep-drt-cross'
    assert re.fullmatch('[a-f0-9]{40}',spec['source_head'])
    for k in ('controller_sha256','summary_sha256','parts_sha256'):
        assert re.fullmatch('[a-f0-9]{64}',spec[k])
    assert summary_sha==spec['summary_sha256'] and parts_sha==spec['parts_sha256']
    assert run['id']==spec['run'] and run['run_attempt']==1
    assert run['head_sha']==spec['source_head'] and run['head_branch']=='codex/complete-open-work'
    assert run['path']in('.github/workflows/mainchip-repair-deep-drt-cloud.yml','.github/workflows/mainchip-repair-deep-drt-continuation-cloud.yml')
    assert run['status']=='completed' and run['conclusion']=='success'
    assert all(report[k]==v for k,v in GLOBAL_INPUTS.items()),'Saved process belongs to a different candidate'
    assert report['source_head']==spec['source_head'] and report['run_id']==spec['run'] and report['stage']=='cross'
    assert report['sources_unchanged'] and report['native_process_saved'] and not report['route_complete']
    assert report['status']=='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF'
    assert report['active_drt_cross_runner_progress_proven'] and report['restored_native_process']
    assert report['controller_sha256']==spec['controller_sha256'] and spec['controller_sha256']in compatible
    assert report['checkpointed_elf_sha256']=='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
    assert report['checkpoint_images'] and report['native_log']['single_entrypoint']
    c=report['continuation']
    assert {k:c[k]for k in ('run','attempt','group','source_head','controller_sha256')}=={k:spec[k]for k in ('run','attempt','group','source_head','controller_sha256')}
    assert c['native_process_saved'] and c['next_phase']=='continue_same_native_process'
def source_controls():
    import copy
    # Structural fixtures only, not a simulated or actual router progress claim.
    h='1'*64
    s=dict(run=17,attempt=1,group='mainchip-repair-deep-drt-cross',source_head='a'*40,controller_sha256=h,summary_sha256='2'*64,parts_sha256='3'*64)
    run=dict(id=17,run_attempt=1,head_sha='a'*40,head_branch='codex/complete-open-work',path='.github/workflows/mainchip-repair-deep-drt-cloud.yml',status='completed',conclusion='success')
    r=dict(source_head='a'*40,run_id=17,stage='cross',sources_unchanged=True,native_process_saved=True,route_complete=False,
        status='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF',
        active_drt_cross_runner_progress_proven=True,restored_native_process=True,controller_sha256=h,
        checkpointed_elf_sha256='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b',
        checkpoint_images={'pages-1.img':'4'*64},native_log={'single_entrypoint':True},
        continuation={k:s[k]for k in ('run','attempt','group','source_head','controller_sha256')}|dict(native_process_saved=True,next_phase='continue_same_native_process'))
    r.update(GLOBAL_INPUTS)
    validate_saved_source(s,run,r,'2'*64,'3'*64,{h})
    faults=[]
    cases=[('live_source','run','status','in_progress'),('failed_source','run','conclusion','failure'),
        ('wrong_run','run','id',18),('wrong_head','run','head_sha','b'*40),
        ('unknown_controller','report','controller_sha256','5'*64),
        ('no_process','report','native_process_saved',False),('route_already_done','report','route_complete',True),
        ('no_progress','report','active_drt_cross_runner_progress_proven',False),
        ('wrong_binary','report','checkpointed_elf_sha256','6'*64),
        ('empty_process_images','report','checkpoint_images',{}),
        ('changed_summary','spec','summary_sha256','7'*64),('changed_parts','spec','parts_sha256','8'*64),
        ('cold_initial_capsule','spec','group','mainchip-repair-deep-drt-initial'),
        ('unknown_source_workflow','run','path','.github/workflows/unrelated.yml')]
    cases += [('changed-'+k,'report',k,0 if isinstance(v,int)else'0'*64)for k,v in GLOBAL_INPUTS.items()]
    for label,which,key,value in cases:
        ss,rr,pp=copy.deepcopy((s,run,r));{'spec':ss,'run':rr,'report':pp}[which][key]=value
        try:validate_saved_source(ss,rr,pp,'2'*64,'3'*64,{h})
        except (AssertionError,KeyError):faults.append(dict(name=label,rejected=True))
        else:raise AssertionError('Accepted malformed source: '+label)
    try:validate_saved_source(s,run,r,'2'*64,'3'*64,{'9'*64})
    except AssertionError:faults.append(dict(name='incompatible_controller_version',rejected=True))
    else:raise AssertionError('Accepted incompatible controller')
    assert len(faults)==20
    return dict(scope='Synthetic descriptor/receipt validation only; actual CRIU progress must be proven separately',faults=faults)
def initial_receipt():
    spec=json.loads(os.environ['NSSOC_DRT_SOURCE'])
    assert type(spec['run'])is int and spec['run']!=int(os.environ['GITHUB_RUN_ID'])
    run=api('actions/runs/'+str(spec['run']))
    assert run['status']=='completed' and run['conclusion']=='success','Never replay a live or rejected source'
    group=spec['group'];assert group=='mainchip-repair-deep-drt-cross' and spec['attempt']==1
    rel=api('releases/tags/cloud-results-'+str(spec['run'])+'-1-'+group);got={}
    for suffix in ('.summary.json','.parts.json'):
        found=[a for a in rel['assets']if a['name'].endswith(suffix)];assert len(found)==1
        a=found[0];raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
        assert len(raw)==a['size']and a['digest']=='sha256:'+digest(raw);got[suffix]=(a,raw)
    a,raw=got['.summary.json'];b,parts=got['.parts.json'];r=json.loads(raw)
    compatible={LEGACY_CONTROLLER_SHA256,sha(Path(__file__))}
    validate_saved_source(spec,run,r,digest(raw),digest(parts),compatible)
    return dict(run=spec['run'],group=group,summary_sha256=digest(raw),parts_sha256=digest(parts),report=r,descriptor=spec)
def log_proof(raw,boots,prefix=None):
    assert boots==b'native-entrypoint\n','Cold restart or missing entrypoint'
    text=raw.decode(errors='strict')
    assert text.count('NSSOC_SAVED_GLOBAL_DRT_BEGIN')==1,'Missing or repeated detailed-router initialization'
    assert re.search(r'Start \d+(?:st|nd|rd|th) optimization iteration',text),'No native DRT optimization state observed'
    if prefix is not None:assert raw.startswith(prefix),'Frozen native log prefix changed'
    return dict(bytes=len(raw),sha256=digest(raw),single_entrypoint=True,
        optimization_iterations=re.findall(r'Start (\d+)(?:st|nd|rd|th) optimization iteration',text),
        progress=[dict(percent=int(a),violations=int(b))for a,b in re.findall(r'Completing\s+(\d+)% with\s+(\d+) violations',text)],
        completed_violation_counts=list(map(int,re.findall(r'\[INFO DRT-0199\]\s+Number of violations = (\d+)',text))))
def log_controls(raw,boots):
    out=[]
    for name,changed,b,prefix in [
        ('cold_restart',raw,boots+boots,None),
        ('removed_initialization',raw.replace(b'NSSOC_SAVED_GLOBAL_DRT_BEGIN',b'FAULT'),boots,None),
        ('duplicate_initialization',raw+b'NSSOC_SAVED_GLOBAL_DRT_BEGIN\n',boots,None),
        ('changed_checkpoint_prefix',b'FAULT'+raw[5:],boots,raw[:100])]:
        assert changed!=raw or b!=boots
        try:log_proof(changed,b,prefix)
        except (AssertionError,UnicodeError,ValueError):out.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    return out
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('initial','cross'),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    assert args.stage=='cross','Continuation controller cannot start a fresh native route'
    from check_mainchip_repair_deep_drt_continuation_sources import check
    check();source_controls()
    out=ROOT/('cloud-mainchip-repair-deep-drt-'+args.stage);out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out
    case=BASE/'work';case.mkdir()
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],stage=args.stage,route_complete=False,final_timing_complete=False,full_phy_accepted=False,
        scope='Actual saved-global mainchip detailed routing, original native DRT parameters. Antenna repair, disconnected pins, fixed-clock/topology checks, RC and original20/4/8/8ns three-corner STA remain mandatory after routing. No old interrupted optimization state is reused.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label,command,required=True,timeout=900):
        p=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        (out/(label+'.log')).write_text(p.stdout+p.stderr)
        r.setdefault('commands',[]).append(dict(label=label,returncode=p.returncode,log_sha256=sha(out/(label+'.log'))));save()
        if required and p.returncode:
            print((p.stdout+p.stderr)[-16000:],flush=True);raise RuntimeError(label+' failed')
        return p
    def state(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]['State']
    owned=[];save()
    try:
        methods=json.loads((ROOT/'scripts/mainchip-repair-deep-drt-methods.json').read_text())
        assert all(sha(ROOT/n)==h for n,h in methods.items())
        portable=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())
        checkpoint=json.loads((ROOT/'docs/evidence/mainchip-cross-runner-native-checkpoint-pass-20261021.json').read_text())
        assert checkpoint['report']['status']=='PASS_ACTUAL_OPENROAD_LOADED_DB_PROCESS_ACROSS_DISTINCT_RUNNERS_REQUIRES_ACTIVE_DRT_PROOF'
        assert checkpoint['report']['boot_id']!=checkpoint['report']['previous_boot_id']
        assert checkpoint['report']['runtime_source']['summary_sha256']==portable['summary_sha256']
        names=['native-image.tar','runtime-inventory.json']
        runtime,proof=reports.restore_report(portable['group'],portable['run'],portable['summary_sha256'],portable['parts_sha256'],BASE/'input',names)
        assert runtime==portable['report']and runtime['sources_unchanged'];r['runtime_source']=proof;r['image_id']=runtime['image_id']
        r['loaded_process_portability_source']={k:checkpoint[k]for k in ('run','summary_sha256','parts_sha256')}
        inventory=json.loads((BASE/'input/runtime-inventory.json').read_text())
        assert inventory['actual_elf_sha256']==runtime['actual_elf']['actual_elf_sha256']
        r['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip();r['job']=os.environ['GITHUB_JOB'];r['run_id']=int(os.environ['GITHUB_RUN_ID'])
        run('kernel',['uname','-a']);run('cpu',['lscpu','--json']);run('criu-check',['sudo','criu','check','--all'],False)
        build=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text())
        assert build['source_commit']==CRIU_COMMIT and sha(Path('/usr/sbin/criu'))==build['binary_sha256'];r['criu_build']=build
        assert not run('empty-containers',['docker','ps','-aq']).stdout.strip()
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        run('load-exact-image',['docker','load','-i',str(BASE/'input/native-image.tar')])
        info=json.loads(run('exact-image',['docker','image','inspect',r['image_id']]).stdout)[0];assert info['Id']==r['image_id']
        native_env=[]
        for key,value in sorted(inventory['environment'].items()):native_env+=['-e',key+'='+value]
        gp=json.loads((ROOT/'docs/evidence/mainchip-repair-deep-global-pass-20261021.json').read_text())
        glive=api('actions/runs/'+str(gp['run']))
        assert glive['status']=='completed'and glive['conclusion']=='success'and glive['run_attempt']==1
        assert glive['head_sha']==gp['source_head']and glive['path']=='.github/workflows/mainchip-repair-deep-global-cloud.yml'
        global_names=['trial-config.json','candidate-state.json','geometry/result.json','fixed-clock.json',
            *[gp['report']['step_path']+'/'+n for n in ('fresh-fanout-global.odb','fresh_fanout_native.tcl','fresh-fanout.guide','_env.tcl','config.json')]]
        global_report,global_proof=reports.restore_report(gp['group'],gp['run'],gp['summary_sha256'],gp['parts_sha256'],BASE/'global',global_names)
        assert global_report==gp['report']and global_report['sources_unchanged']
        assert global_report['status']=='PASS_NATIVE_FRESH_GLOBAL_REQUIRES_RESUMABLE_DETAIL_ROUTE_AND_FRESH_RC_STA'
        assert global_report['native_global_complete']and not global_report['detailed_route_complete']
        assert global_report['candidate_instance_count']==153130 and global_report['geometry']['instance_count']==153130
        assert global_report['geometry']['sram_instances']==20 and len(global_report['geometry']['rejected'])==2
        assert global_report['fixed_clock']['original_physical_route_preserved']
        assert global_report['candidate_netlist_sha256']=='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
        assert global_report['source_sdc_sha256']=='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
        assert global_report['original_clock_periods_ns']==[20,4,8,8]and global_report['derating_percent']==5
        source=BASE/'global'/global_report['step_path']
        assert sha(source/'fresh-fanout-global.odb')==global_report['global_odb_sha256']
        assert sha(source/'fresh-fanout.guide')==global_report['global_guides_sha256']
        assert sha(source/'fresh_fanout_native.tcl')=='dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e'
        assert json.loads((BASE/'global/geometry/result.json').read_text())==global_report['geometry']
        assert json.loads((BASE/'global/fixed-clock.json').read_text())==global_report['fixed_clock']
        r.update(global_source=global_proof,global_candidate_instance_count=153130,
            global_odb_sha256=global_report['global_odb_sha256'],global_guides_sha256=global_report['global_guides_sha256'],
            candidate_netlist_sha256=global_report['candidate_netlist_sha256'],source_sdc_sha256=global_report['source_sdc_sha256'])
        save()
        # Ask the actual pinned Tcl runtime to interpret the original generated
        # environment, rather than approximate Tcl quoting with a Python parser.
        inspect=case/'inspect-environment.tcl'
        inspect.write_text('source {'+str(source/'_env.tcl')+'}\nforeach key {DESIGN_NAME DRT_THREADS DRT_OPT_ITERS DRT_SAVE_SNAPSHOTS DRT_SAVE_DRC_REPORT_ITERS DRT_ANTENNA_REPAIR_ITERS DIODE_CELL} {\nif {[info exists ::env($key)]} {puts "NSSOC_SETTING $key=$::env($key)"} else {puts "NSSOC_SETTING $key=__UNSET__"}\n}\nexit\n')
        cmd=['docker','run','--rm','--network','none','--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly',
            '-e','GLIBC_TUNABLES='+TUNABLES,*native_env,'--entrypoint',inventory['actual_elf'],r['image_id'],'-exit','-no_init',str(inspect)]
        observed=run('original-native-environment',cmd).stdout
        settings=dict(re.findall(r'^NSSOC_SETTING (\w+)=(.*)$',observed,re.M))
        assert set(settings)=={'DESIGN_NAME','DRT_THREADS','DRT_OPT_ITERS','DRT_SAVE_SNAPSHOTS','DRT_SAVE_DRC_REPORT_ITERS','DRT_ANTENNA_REPAIR_ITERS','DIODE_CELL'}
        threads=int(settings['DRT_THREADS']);iterations=int(settings['DRT_OPT_ITERS']);assert threads>=1 and 1<=iterations<=64
        r['original_native_settings']=settings;save()
        original_cfg=json.loads((source/'config.json').read_text())
        # Librelane's per-step config intentionally omits STA-only options.
        # Bind those guards to the exact full flow config, never a default.
        # This repaired candidate carries the same original full flow contract.
        # Restore it from its own passed global run, without replaying old routing.
        (BASE/'flow-config').mkdir()
        shutil.copyfile(BASE/'global/trial-config.json',BASE/'flow-config/trial-config.json')
        full=global_report;full_proof=global_proof
        assert sha(BASE/'flow-config/trial-config.json')==full['outputs']['trial-config.json']=='b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f'
        flow_cfg=json.loads((BASE/'flow-config/trial-config.json').read_text())
        for key in ('CLOCK_PORT','CLOCK_PERIOD','TIME_DERATING_CONSTRAINT'):
            assert original_cfg[key]==flow_cfg[key],('Step and original full-flow config differ',key)
        r['full_flow_config_source']=full_proof

        assert int(original_cfg['DRT_OPT_ITERS'])==iterations
        assert original_cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert float(original_cfg['CLOCK_PERIOD'])==20 and float(original_cfg['TIME_DERATING_CONSTRAINT'])==5
        assert flow_cfg['SETUP_VIOLATION_CORNERS']==flow_cfg['HOLD_VIOLATION_CORNERS']==['*']
        r['retained_timing_contract']=dict(clock_periods_ns=[20,4,8,8],derating_percent=5,
            new_native_sta_run_required=True,step_configuration_sha256=sha(source/'config.json'),full_flow_configuration_sha256=sha(BASE/'flow-config/trial-config.json'))
        assert re.fullmatch(r'[A-Za-z0-9_]+',settings['DESIGN_NAME'])
        cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=threads
        r['cpuset']=','.join(map(str,cpus[:threads]));r['original_native_settings']=settings
        original=(source/'fresh_fanout_native.tcl').read_text()
        setup=original[original.index('set_thread_count $::env(DRT_THREADS)'):original.index('# The input has only stale data wires removed.')]
        a=original.index('set drt_args [list]');b=original.index('drt_run $i {*}$drt_args',a);arguments=original[a:b]
        assert arguments.count('-or_seed 42')==1 and '-droute_end_iter $::env(DRT_OPT_ITERS)'in arguments
        layers='set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2'
        assert original.count(layers)==1
        header="""set case $::env(NSSOC_DRT_CASE)
if {[file exists [file join $case boots.log]]} {error "Cold restart detected"}
set boot [open [file join $case boots.log] w]
puts $boot native-entrypoint
close $boot
source $::env(NSSOC_DRT_ORIGINAL_ENV)
set ::env(STEP_DIR) $case
read_db $::env(NSSOC_DRT_ODB)
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 153130} {error "Saved global instance census changed"}
set fixed [$block findNet clknet_3_5_0_pcie_clk_i]
if {$fixed eq "NULL" || [$fixed getWireType] ne "FIXED"} {error "Original fixed clock metadata missing"}
set fixed_wire [$fixed getWire]
if {$fixed_wire eq "NULL"} {error "Original encoded clock wire missing"}
write_db [file join $case before-guide-read.odb]
read_guides $::env(NSSOC_DRT_GUIDE)
if {[$fixed getWire] ne $fixed_wire || [$fixed getWireType] ne "FIXED"} {error "Guide loading changed fixed clock wire"}
"""
        tail="""puts NSSOC_SAVED_GLOBAL_DRT_BEGIN
detailed_route {*}$drt_args -output_drc [file join $case detailed-route.drc]
write_db [file join $case detailed-route.odb]
set done [open [file join $case drt-done] w]
puts $done "Native DRT returned; postroute physical and STA gates remain required"
close $done
exit
"""
        generated=header+layers+'\n'+setup+'\n'+arguments+'\n'+tail
        tcl=case/'route.tcl';tcl.write_text(generated)
        r['route_script']=dict(sha256=sha(tcl),original_sha256=sha(source/'fresh_fanout_native.tcl'),
            exact_native_drt_setup=setup,exact_native_drt_arguments=arguments,layers=layers,
            already_executed_global_route_replaced_by_hash_pinned_saved_global=True,
            sta_before_global_route_provenance_only_no_new_timing_acceptance=True)
        r['controller_sha256']=sha(Path(__file__))
        expected=global_report['global_odb_sha256']
        assert sha(source/'fresh-fanout-global.odb')==expected;save()
        def command(name,create=False):
            env=['-e','GLIBC_TUNABLES='+TUNABLES,'-e','NSSOC_DRT_CASE='+str(case),'-e','NSSOC_DRT_ODB='+str(source/'fresh-fanout-global.odb'),
                 '-e','NSSOC_DRT_GUIDE='+str(source/'fresh-fanout.guide'),'-e','NSSOC_DRT_ORIGINAL_ENV='+str(source/'_env.tcl'),*native_env]
            return ['docker','create'if create else'run',*([]if create else['-d']),'--name',name,'--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',r['cpuset'],
                '--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly','--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),*env,
                '--entrypoint','/bin/sh',r['image_id'],'-c','exec "$1" -exit -no_init "$2" > "$3" 2>&1','nssoc',inventory['actual_elf'],str(tcl),str(case/'native.log')]
        name='nssoc-active-drt-'+args.stage;owned.append(name);prefix=None
        if args.stage=='initial':
            run('start-actual-drt',command(name))
            deadline=time.monotonic()+2400
            while True:
                st=state(name);raw=(case/'native.log').read_bytes()if(case/'native.log').exists()else b''
                if not st['Running']:
                    print(raw.decode(errors='replace')[-20000:],flush=True)
                    raise RuntimeError('Actual DRT exited before active optimization checkpoint')
                if re.search(rb'Start \d+(?:st|nd|rd|th) optimization iteration',raw):break
                assert time.monotonic()<deadline,'No actual DRT optimization state before bounded preparation deadline'
                time.sleep(10)
            r['native_active_optimization_seen']=True;save()
            budget=300
        else:
            pin=initial_receipt()
            old_names=[n for n in pin['report']['outputs']if n.startswith(('work/','checkpoints/'))]
            assert old_names
            old,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'initial',old_names)
            assert old==pin['report']and old['sources_unchanged']and old['controller_sha256']in{LEGACY_CONTROLLER_SHA256,r['controller_sha256']}
            assert old['boot_id']!=r['boot_id']and old['run_id']!=r['run_id']
            assert old['image_id']==r['image_id']and old['cpuset']==r['cpuset']
            assert old['route_script']==r['route_script']and old['original_native_settings']==settings
            assert old['criu_build']['source_commit']==build['source_commit']
            for p in (out/'initial/work').rglob('*'):
                dest=case/p.relative_to(out/'initial/work')
                if p.is_dir():dest.mkdir(parents=True,exist_ok=True)
                elif p.is_file():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
                else:raise AssertionError('Unexpected saved work file type')
            prefix=(case/'native.log').read_bytes()
            assert digest(prefix)==old['native_log']['sha256']and sha(tcl)==r['route_script']['sha256']
            log_proof(prefix,(case/'boots.log').read_bytes())
            images=out/'initial/checkpoints/state'
            assert {str(p.relative_to(images)):sha(p)for p in images.rglob('*')if p.is_file()}==old['checkpoint_images']
            ident=run('create-restored',command(name,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)
            docker_root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
            target=docker_root/'containers'/ident/'checkpoints/state'
            run('checkpoint-parent',['sudo','mkdir','-p',str(target.parent)]);run('checkpoint-copy',['sudo','cp','-a',str(images),str(target)])
            compare="import pathlib,hashlib,sys;scan=lambda d:{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in d.rglob('*')if p.is_file()};assert scan(pathlib.Path(sys.argv[1]))==scan(pathlib.Path(sys.argv[2]))"
            run('checkpoint-copy-proof',['sudo','python3','-c',compare,str(images),str(target)])
            resumed=run('restore-active-drt',['docker','start','--checkpoint','state',name],False)
            if resumed.returncode:
                run('restore-diagnostic',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+ident+'/work/restore.log'],False)
                raise RuntimeError('Active DRT process restore failed')
            assert state(name)['Running'],'Restored native process is not live'
            assert all(sha(out/'initial'/n)==old['outputs'][n]for n in old_names)
            r['initial_source']=proof;r['previous_boot_id']=old['boot_id'];r['restored_native_process']=True
            r['continuation_source_descriptor']=pin['descriptor']
            r['restored_work_prefixes_verified']={n:old['outputs'][n]for n in old_names if n.startswith('work/')}
            # The prior images remain immutable in their original release. The
            # default eager CRIU restore has finished; do not accumulate a second
            # on-disk copy of every prior multi-GB process image in every segment.
            run('remove-consumed-default-checkpoint',['sudo','rm','-rf',str(target)])
            shutil.rmtree(out/'initial/checkpoints');shutil.rmtree(out/'initial/work')
            r['consumed_downloads_removed_after_verified_restore']=True;save()
            budget=int(os.environ.get('NSSOC_DRT_SECONDS','3600'))
            assert 600<=budget<=7200
        start=time.monotonic()
        while time.monotonic()-start<budget and state(name)['Running']:
            if shutil.disk_usage(case).free<=14*1024**3:
                r['early_checkpoint_reason']='Reserve native process dump/publication space';save();break
            time.sleep(15)
        st=state(name);r['segment_elapsed_s']=time.monotonic()-start
        if st['Running']:
            actual=run('actual-native-executable',['sudo','sha256sum','/proc/'+str(st['Pid'])+'/exe']).stdout.split()[0]
            assert actual==inventory['actual_elf_sha256'];r['checkpointed_elf_sha256']=actual
            images=out/'checkpoints';images.mkdir()
            run('checkpoint-active-drt',['docker','checkpoint','create','--checkpoint-dir',str(images),name,'state'],timeout=900)
            assert not state(name)['Running']
            run('readable-process-images',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(images)])
            r['checkpoint_images']={str(p.relative_to(images/'state')):sha(p)for p in(images/'state').rglob('*')if p.is_file()}
            assert r['checkpoint_images'];r['native_process_saved']=True
        else:
            assert st['ExitCode']==0 and(case/'drt-done').is_file()and(case/'detailed-route.odb').is_file()
            r['route_complete']=True;r['routed_odb_sha256']=sha(case/'detailed-route.odb')
        raw=(case/'native.log').read_bytes();r['native_log']=log_proof(raw,(case/'boots.log').read_bytes(),prefix)
        assert sha(case/'before-guide-read.odb')==expected,'Original global DB changed before guide loading'
        r['controls']=log_controls(raw,(case/'boots.log').read_bytes())
        if args.stage=='cross':
            assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'
            appended=raw[len(prefix):].decode()
            assert re.search(r'Completing\s+\d+%|Start \d+(?:st|nd|rd|th) optimization iteration|Number of violations',appended),'No native optimization progress witness after restore'
            r['active_drt_cross_runner_progress_proven']=True
        shutil.copytree(case,out/'work')
        assert all(sha(BASE/'input'/n)==runtime['outputs'][n]for n in names)
        if args.stage=='cross':assert r['consumed_downloads_removed_after_verified_restore'] and r['restored_work_prefixes_verified']
        assert sha(BASE/'flow-config/trial-config.json')==full['outputs']['trial-config.json']
        assert all(sha(BASE/'global'/n)==global_report['outputs'][n]for n in global_names)
        assert all(sha(ROOT/n)==h for n,h in methods.items())
        assert sha(Path(__file__))==r['controller_sha256']and sha(tcl)==r['route_script']['sha256'];r['sources_unchanged']=True
        r['status']=('COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES'if r['route_complete']else
            'SAVED_ACTUAL_ACTIVE_DRT_PROCESS_REQUIRES_CROSS_RUNNER_CONTINUATION'if args.stage=='initial'else
            'SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF')
        r['continuation']=dict(run=int(os.environ['GITHUB_RUN_ID']),attempt=1,group='mainchip-repair-deep-drt-'+args.stage,
            source_head=os.environ['GITHUB_SHA'],controller_sha256=r['controller_sha256'],native_process_saved=r.get('native_process_saved',False),
            next_phase='postroute_validation'if r['route_complete']else'continue_same_native_process')
        r['next_action']='Continue the exact saved process, never cold-start or replay the completed prefix. On native completion run original fixed-clock/topology/antenna/disconnect/RC/STA gates before acceptance.'
    except BaseException as error:
        import traceback
        r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc())
        if(case/'native.log').exists():print((case/'native.log').read_text(errors='replace')[-16000:],flush=True)
        raise
    finally:
        # Only owned containers are removed; a valid checkpoint remains in out.
        for name in owned:run('cleanup-'+name,['docker','rm','-f',name],False)
        if case.exists()and not(out/'work').exists():shutil.copytree(case,out/'work')
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        save()
if __name__=='__main__':main()
