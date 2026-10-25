#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted complete-record CDC proof. No LTSSM, lane mapping or physical CDC claim."""
import argparse, ast, base64, hashlib, importlib, json, math, os, re, signal, sys, threading, traceback
import xml.etree.ElementTree as ET
from pathlib import Path
import check_pcie_gen12_record_cdc_source as source

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source'
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-record-cdc'
PUBLICATION=ROOT/'hw/soc/out/cloud-pcie-gen12-record-cdc-publication'
GROUP='pcie-gen12-record-cdc'
METHOD=ROOT/'scripts/pcie-gen12-record-cdc-cloud-methods.json'
BENCH=ROOT/'hw/soc/tb/cocotb'
MAKEFILE=BENCH/'Makefile.gen12_record_cdc'
HARNESS=BENCH/'pcie_gen12_record_cdc_harness.py'
DIRECT='soc_pcie_gen12_record_cdc_v1'
COMPOSED='soc_pcie_gen12_recovered_records_v1'
DEPTHS=(4,8,32)
VERILATOR_REF='51cdf52d0f3a3e59b51fd87762646a851e9f4aff'
TESTS=source.TESTS
RTL_NAMES=(
 'soc_pcie_gen12_record_cdc_v1.v','soc_pcie_gen12_recovered_records_v1.v',
 'soc_pcie_gen3_block_cdc_v1.v','soc_pcie_gen12_training_records.v',
 'soc_pcie_gen12_raw32_rx.v','soc_pcie_gen12_raw32_align.v',
 'soc_pcie_gen12_tx_raw32.v','soc_pcie_gen12_8b10b_decode.v',
 'soc_pcie_gen12_8b10b_encode.v','vendor/benz_8b10b_decode.v','vendor/benz_8b10b_encode.v')
PACKAGE_FILES={
 'cocotb/regression.py':'5d91583fcb4e315e322cf2bc0500db8697af9bbc5abe030a77f646d543e8918f',
 'cocotb/_xunit_reporter.py':'e0796ac5af22e789a2d63ae367e2e022ebef37beaf3271e20c9fc440ac42e088',
 'cocotb_tools/makefiles/simulators/Makefile.icarus':'466d4be796b12abbd4d3de05a536fddafaaad84cf7426e9d114600efb000ea64',
 'cocotb_tools/makefiles/simulators/Makefile.verilator':'f6ce137b65d7064282b714ec40b1439886680d86de4e6a15bbc986248818a6eb'}
SCOPE=dict(TS_accepted=False,LTSSM_implemented=False,x4_lane_mapping=False,
           automatic_clock_loss_detection=False,physical_CDC_qualified=False,full_PHY_accepted=False)
SUP=None
RESULT=None
ENV=None

def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_info(path):
    b=Path(path).read_bytes()
    return dict(bytes=len(b),sha256=sha(b))
def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w')as f:
        f.write(json.dumps(data,indent=2,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def supervisor():
    global SUP
    if SUP is None:
        old=list(sys.path);sys.path.insert(0,str(ARCHIVE/'scripts'))
        try:SUP=importlib.import_module('cloud_pcie_gen12_training_records_telemetry')
        finally:sys.path[:]=old
        assert Path(SUP.__file__).resolve()==ARCHIVE/'scripts/cloud_pcie_gen12_training_records_telemetry.py'
        from pcie_live_memory_sampler import install
        install(SUP)
    return SUP

def pins():
    s=supervisor();s.host()
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha((ROOT/p).read_bytes())==h,p
    old=s.pins()
    assert len(old['protected'])==52
    checked=source.check()
    assert checked['mutation_definitions']==18 and sum(map(len,checked['tests'].values()))==11
    assert m['source_only_reviewed_basis']=='50708f2c75c4c44246a7226cb4b9cb86dd2f10af'
    assert m['supervisor_reuse']['source_sha256']=='e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b'
    assert m['supervisor_reuse']['minimum_available_kib']==2*1024*1024
    assert m['supervisor_reuse']['maximum_group_rss_kib']==10*1024*1024
    assert m['supervisor_reuse']['phase_seconds']==1200
    assert m['positive_named_executions']==66 and m['mapped_named_executions']==33
    assert m['compiling_behavioral_mutations']==18
    return m

def authorization(m,execute=False):
    assert type(m['native_execution_authorized'])is bool
    if m['native_execution_authorized']:
        assert m['review_status']=='REVIEWED_FOR_ONE_HOSTED_PROOF'
        record=m['native_review_receipt']
        path=ROOT/record['path'];raw=path.read_bytes()
        assert sha(raw)==record['sha256']
        review=json.loads(raw)
        assert review['status']=='CLEARED_FOR_ONE_HOSTED_PROOF'
        assert review['protected_sources']==m['protected']
        assert re.fullmatch('[0-9a-f]{40}',review['reviewed_source'])
    else:
        assert m['review_status']=='SOURCE_ONLY_REVIEW_PENDING'
        assert m['native_review_receipt']is None
    if execute:assert m['native_execution_authorized'],'Native proof not authorized'

def progress(phase,**data):
    global RESULT
    if RESULT is not None:
        RESULT['phase']=phase;RESULT.update(data);save(OUT/'result.json',RESULT)
    supervisor().event('cdc_phase',phase=phase,**data)

def command(args,label,passed=True,seconds=1200,cwd=None,tool_env=False):
    assert 0<seconds<=1200
    if tool_env:
        assert ENV is not None
        args=['env','-u','COCOTB_TESTCASE','-u','MODULE','-u','TESTCASE',
              *[k+'='+v for k,v in ENV.items()],*map(str,args)]
    return supervisor().supervised(list(map(str,args)),label,passed,seconds=seconds,cwd=cwd or ROOT)

def mutation_list():
    return json.loads((ROOT/'scripts/pcie-gen12-record-cdc-mutations.json').read_text())['mutations']

# Every allowed site is a real assertion in the byte-pinned public-port oracle.
# Unknown-value conversions and simulator/setup errors cannot satisfy this table.
FIELD=('field or order mismatch',)
MESSAGES={
 **{n:FIELD for n in ('drop_data','drop_K','drop_code_error','drop_disparity','drop_comma','swap_code_disparity')},
 'ignore_ready':('held complete record changed',),
 'hide_loss':('bounded public-port scenario timeout',),
 'ignore_write_reset':('output escaped epoch barrier',),
 'ignore_read_reset':('output escaped epoch barrier',),
 'duplicate_source':('fabricated write acceptance','accepted outside source epoch'),
 'unmask_stale_fields':('output escaped epoch barrier',),
 'hide_polarity_loss':('bounded public-port scenario timeout',),
 'hide_external_loss':('bounded public-port scenario timeout',),
 'bypass_arming':('field or order mismatch','accepted record before oracle completed it'),
 'wrong_collector_pop':('field or order mismatch','fabricated/duplicate/unaccepted record',
                        'accepted record before oracle completed it'),
 'collector_reset_POR_only':('field or order mismatch','accepted record before oracle completed it',
                             'fabricated/duplicate/unaccepted record'),
 'ignore_polarity':('field or order mismatch','accepted record before oracle completed it',
                    'bounded public-port scenario timeout')}
EXPRESSIONS={
 'ignore_write_reset':("not self.value('rv') and not self.value('wa')","self.output() == (0,) * 5"),
 'ignore_read_reset':("not self.value('rv') and not self.value('wa')","self.output() == (0,) * 5"),
 'bypass_arming':('link.reads - before == 2',),
 'collector_reset_POR_only':('link.reads - before == 5',),
 'ignore_polarity':('link.reads - before == 3',)}
def assertion_site(node,name):
    if isinstance(node,ast.Assert):
        message=node.msg.value if isinstance(node.msg,ast.Constant)and isinstance(node.msg.value,str)else None
        expression=ast.unparse(node.test)
        expression_match=expression in EXPRESSIONS.get(name,())
        if name in ('ignore_write_reset','ignore_read_reset'):
            # Only the already-declared reset predicates use structural equality.
            # Formatting-only parentheses must not change an exact AST predicate.
            expression_match=any(
                ast.dump(node.test,include_attributes=False)==
                ast.dump(ast.parse(allowed,mode='eval').body,include_attributes=False)
                for allowed in EXPRESSIONS[name])
        if message in MESSAGES[name]or expression_match:
            return {'message':message,'expression':expression}
    elif isinstance(node,ast.Raise)and node.cause is None:
        call=node.exc
        # The existing bounded public-port wait uses this explicit literal raise.
        # No dynamic message, arbitrary exception, alias, chained cause or re-raise.
        if (isinstance(call,ast.Call)and isinstance(call.func,ast.Name)and
            call.func.id=='AssertionError'and len(call.args)==1 and not call.keywords and
            isinstance(call.args[0],ast.Constant)and
            call.args[0].value=='bounded public-port scenario timeout'and
            call.args[0].value in MESSAGES[name]):
            return {'message':call.args[0].value,'expression':ast.unparse(node),
                    'kind':'explicit_literal_AssertionError_raise'}
    return None

def assertion_sites(mutation):
    top=Path(mutation['path']).stem
    sites={}
    for path in (HARNESS,BENCH/('test_'+top+'.py')):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            site=assertion_site(node,mutation['name'])
            if site is not None:sites[(str(path.resolve()),node.lineno)]=site
    assert sites,mutation['name']
    return sites

def xml_review(raw,top,returncode,*,mutation=None,log=''):
    assert len(raw)<=2*1024*1024,'oversized XML'
    assert b'<!DOCTYPE'not in raw and b'<!ENTITY'not in raw
    tree=ET.fromstring(raw)
    assert tree.tag in ('testsuite','testsuites')
    cases=list(tree.iter('testcase'))
    assert len(cases)==len(TESTS[top]),'incomplete or extra named tests'
    names=[c.attrib.get('name')for c in cases]
    assert len(set(names))==len(names)and set(names)==set(TESTS[top]),'wrong/duplicate test names'
    assert not list(tree.iter('error')),'XML test error is not behavioral detection'
    result=[]
    for c in cases:
        name=c.attrib['name'];module='test_'+top
        assert c.attrib.get('classname')==module,'wrong module'
        assert Path(c.attrib['file']).resolve()==BENCH/(module+'.py'),'wrong test source'
        assert math.isfinite(float(c.attrib['sim_time_ns']))and float(c.attrib['sim_time_ns'])>=0
        failures=c.findall('failure');skips=c.findall('skipped')
        assert all(x.tag in ('failure','skipped')for x in c),'unknown testcase child'
        if mutation is not None and name!=mutation['test']:
            # Cocotb2.0.1 writes explicitly filtered tests as skipped XML entries.
            assert len(skips)==1 and not failures and float(c.attrib['sim_time_ns'])==0,'unexpected unselected test execution'
            result.append(dict(test=name,disposition='FILTERED_NOT_EXECUTED'));continue
        assert not skips,'required test skipped'
        assert float(c.attrib['sim_time_ns'])>0,'no actual simulation'
        if mutation is None:
            assert returncode==0 and not failures,'positive test failed'
            result.append(dict(test=name,disposition='PASS'));continue
        assert returncode!=0 and len(failures)==1,'mutant survived or malformed failure'
        failure=failures[0]
        assert failure.attrib.get('error_type')=='AssertionError','setup/simulator/unknown failure'
        frames=re.findall(r'File "([^"]+)", line ([0-9]+), in [^\n]+',log)
        assert frames,'missing actual assertion traceback'
        origin=(str(Path(frames[-1][0]).resolve()),int(frames[-1][1]))
        sites=assertion_sites(mutation)
        assert origin in sites,'unqualified failure site'
        site=sites[origin]
        if site['message'] is not None:
            assert site['message'] in failure.attrib.get('error_msg',''),'wrong assertion message'
        result.append(dict(test=name,disposition='DETECTED_ASSERTION',error_type='AssertionError',
                           error_msg=failure.attrib.get('error_msg',''),origin=list(origin),assertion=site))
    assert sum(x['disposition']=='DETECTED_ASSERTION'for x in result)==int(mutation is not None)
    return result

def compile_admission(returncode,binary):
    assert returncode==0,'compile/setup failure is not behavioral detection'
    assert Path(binary).is_file()and Path(binary).stat().st_size>0,'missing compiled image'

def vendor_admission(raw,record):
    assert len(raw)==record['bytes']and sha(raw)==record['sha256'],'vendor bytes'
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['git_blob_sha']
    assert raw.count(b'module axis_async_fifo')==1

def source_paths(vendor,mutation=None):
    paths=[ROOT/'hw/soc/rtl/pcie'/n for n in RTL_NAMES]+[vendor]
    assert len(paths)==len(set(paths))
    assert sum('module axis_async_fifo' in p.read_text()for p in paths)==1
    if mutation:
        src=ROOT/mutation['path'];text=src.read_text()
        assert text.count(mutation['before'])==1 and mutation['before']!=mutation['after']
        altered=text.replace(mutation['before'],mutation['after'])
        assert altered!=text and altered.count(mutation['after'])==1
        target=OUT/'mutations'/mutation['name']/src.name
        target.parent.mkdir(parents=True,exist_ok=False);target.write_text(altered)
        paths=[target if p==src else p for p in paths]
    for p in paths:assert re.fullmatch(r'[A-Za-z0-9_./-]+',str(p))
    return paths

def bootstrap(m,scratch):
    global ENV
    progress('bounded_tool_setup')
    command(['sudo','apt-get','update'],'apt-update',seconds=600)
    command(['sudo','apt-get','install','-y','iverilog','yosys','build-essential','autoconf',
             'flex','bison','libfl-dev','zlib1g-dev','help2man','python3-venv'],'apt-install',seconds=1200)
    venv=scratch/'venv'
    command(['python3','-m','venv',venv],'venv-create',seconds=120)
    command([venv/'bin/python','-m','pip','install','--require-hashes','--only-binary=:all:',
             '-r',ROOT/'scripts/pcie-gen12-record-cdc-requirements.txt'],'cocotb-wheel',seconds=300)
    build=scratch/'verilator';build.mkdir()
    command(['git','init',build],'verilator-init',seconds=60)
    command(['git','-C',build,'fetch','--depth=1','https://github.com/verilator/verilator.git',VERILATOR_REF],
            'verilator-source',seconds=300)
    command(['git','-C',build,'checkout','--detach','FETCH_HEAD'],'verilator-checkout',seconds=60)
    actual=command(['git','-C',build,'rev-parse','HEAD'],'verilator-head',seconds=60).stdout.strip()
    assert actual==VERILATOR_REF
    assert not command(['git','-C',build,'status','--porcelain'],'verilator-clean',seconds=60).stdout.strip()
    command(['autoconf'],'verilator-autoconf',cwd=build,seconds=120)
    prefix=scratch/'tools'
    command([build/'configure','--prefix='+str(prefix)],'verilator-configure',cwd=build,seconds=180)
    command(['make','-j2'],'verilator-build',cwd=build)
    command(['make','install'],'verilator-install',cwd=build,seconds=300)
    ENV={'PATH':str(venv/'bin')+':'+str(prefix/'bin')+':'+os.environ['PATH'],
         'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1',
         'COCOTB_REWRITE_ASSERTION_FILES':'','COCOTB_ANSI_OUTPUT':'0','COCOTB_RANDOM_SEED':'20261025',
         'COCOTB_LOG_LEVEL':'INFO','COCOTB_REDUCED_LOG_FMT':'1',
         'COCOTB_HDL_TIMEUNIT':'1ns','COCOTB_HDL_TIMEPRECISION':'1ps','MAKEFLAGS':''}
    checks='import sys,sysconfig,importlib.metadata,json;from pathlib import Path;import hashlib;'+ \
           'assert sys.version_info[:2]==(3,12);assert importlib.metadata.version("cocotb")=="2.0.1";'+ \
           'assert importlib.metadata.version("find_libpython")=="0.4.0";'+ \
           'p=Path(sysconfig.get_paths()["purelib"]);expect='+repr(PACKAGE_FILES)+';'+ \
           'actual={k:hashlib.sha256((p/k).read_bytes()).hexdigest()for k in expect};assert actual==expect;print(json.dumps(actual))'
    package=command([venv/'bin/python','-c',checks],'installed-package-identities',seconds=60,tool_env=True)
    versions={}
    for tool,args in (('iverilog',['iverilog','-V']),('verilator',['verilator','--version']),('yosys',['yosys','-V'])):
        r=command(args,'version-'+tool,seconds=60,tool_env=True)
        versions[tool]={'stdout':r.stdout,'stderr':r.stderr}
    assert 'Verilator 5.040' in versions['verilator']['stdout']
    vendor=m['vendor'];endpoint='repos/alexforencich/verilog-ethernet/git/blobs/'+vendor['git_blob_sha']
    r=command(['gh','api',endpoint],'vendor-source-json',seconds=120)
    metadata=json.loads(r.stdout);assert metadata['sha']==vendor['git_blob_sha']and metadata['encoding']=='base64'
    raw=base64.b64decode(metadata['content'],validate=False);vendor_admission(raw,vendor)
    path=OUT/'vendor'/'axis_async_fifo.v';path.parent.mkdir();path.write_bytes(raw)
    save(OUT/'toolchain.json',dict(verilator_source=actual,versions=versions,packages=json.loads(package.stdout),
                                  vendor={**vendor,**file_info(path)}))
    return path

def make_args(top,depth,sim,paths,build,xml,mutation=None,mapped=False):
    args=['make','-f',str(MAKEFILE),'SIM='+sim,'TOPLEVEL='+top,'DEPTH='+str(depth),
          'SIM_BUILD='+str(build),'COCOTB_RESULTS_FILE='+str(xml),'WAVES=0',
          'VERILOG_SOURCES='+' '.join(map(str,paths)),'BUILD_ARGS=-j2',
          'COCOTB_TEST_FILTER='+('^test_'+top+r'\.'+mutation['test']+'$'if mutation else '')]
    if mapped:
        assert sim=='icarus'
        # Mapped top has fixed elaborated depth, no remaining parameter override.
        # Retain the pinned Icarus recipe's generated timescale command file.
        args+=['COMPILE_ARGS=-f '+str(build/'cmds.f')]
    return args

def simulate(top,depth,sim,paths,label,mutation=None,mapped=False):
    run=OUT/'simulations'/label;run.mkdir(parents=True,exist_ok=False)
    build=run/'build';xml=run/'results.xml'
    args=make_args(top,depth,sim,paths,build,xml,mutation,mapped)
    binary=build/('sim.vvp'if sim=='icarus'else'Vtop')
    progress('compile_'+label)
    c=command(args+[str(binary)],label+'-compile',False,tool_env=True)
    compile_admission(c.returncode,binary)
    compiled=file_info(binary)
    progress('simulate_'+label)
    r=command(args+[str(xml)],label+'-simulate',False,tool_env=True)
    assert xml.is_file(),'simulation produced no XML'
    rows=xml_review(xml.read_bytes(),top,r.returncode,mutation=mutation,log=r.stdout+'\n'+r.stderr)
    result=dict(label=label,top=top,depth=depth,simulator=sim,mapped=mapped,
                compile_returncode=c.returncode,compiled_image=compiled,run_returncode=r.returncode,
                xml=file_info(xml),tests=rows,mutation=None if mutation is None else mutation['name'])
    save(run/'review.json',result)
    return result

def synthesize(top,depth,paths):
    target=OUT/'mapped'/('%s-d%d'%(top,depth));target.mkdir(parents=True,exist_ok=False)
    netlist=target/'mapped.v';netjson=target/'mapped.json'
    param='DEPTH'if top==DIRECT else'FIFO_DEPTH'
    script='read_verilog -sv -noautowire '+' '.join(map(str,paths))+'; '+ \
           'chparam -set '+param+' '+str(depth)+' '+top+'; hierarchy -check -top '+top+'; '+ \
           'synth -top '+top+' -flatten -noshare; check -assert; '+ \
           'write_json '+str(netjson)+'; write_verilog -noattr '+str(netlist)
    (target/'synthesis.ys').write_text(script+'\n')
    label='synthesis-'+top+'-d'+str(depth);progress(label)
    r=command(['yosys','-p',script],label)
    actual=json.loads(netjson.read_text());assert set(actual['modules'])=={top}
    module=actual['modules'][top]
    assert not module.get('memories')and not module.get('attributes',{}).get('blackbox')
    assert all(c['type'].startswith('$_')for c in module['cells'].values()),'unmapped/blackbox cell'
    assert netlist.stat().st_size>0
    result=dict(top=top,depth=depth,returncode=r.returncode,full_synth_and_check=True,
                optional_share_disabled=True,json=file_info(netjson),verilog=file_info(netlist),
                cells=len(module['cells']))
    save(target/'review.json',result)
    return netlist,result

def native():
    global RESULT
    m=pins();authorization(m,execute=True)
    s=supervisor();OUT.mkdir(parents=True,exist_ok=False)
    s.TRACE=OUT/'supervision';s.TRACE.mkdir()
    scratch=Path(os.environ['RUNNER_TEMP'])/('record-cdc-'+os.environ['GITHUB_RUN_ID'])
    scratch.mkdir(exist_ok=False)
    RESULT=dict(status='RUNNING',run=os.environ['GITHUB_RUN_ID'],attempt=os.environ['GITHUB_RUN_ATTEMPT'],
                source=os.environ['GITHUB_SHA'],source_pins=m,scope=SCOPE,engineering_accepted=False,
                rtl=[],mapped=[],synthesis=[],mutations=[])
    old={sig:signal.signal(sig,s.interrupted)for sig in (signal.SIGTERM,signal.SIGINT)}
    thread=threading.Thread(target=s.heartbeat,daemon=True);thread.start()
    try:
        progress('admission')
        assert os.environ['GITHUB_RUN_ATTEMPT']=='1','No implicit retry of this proof'
        command([sys.executable,ROOT/'scripts/wait_cloud_tested_source_release.py','--group',GROUP],
                'exact-source-release-preflight',seconds=360)
        progress('exact_source_prerelease_verified_before_bootstrap')
        vendor=bootstrap(m,scratch);paths=source_paths(vendor)
        for sim in ('icarus','verilator'):
            for depth in DEPTHS:
                for top in TESTS:
                    row=simulate(top,depth,sim,paths,'%s-%s-d%d'%(sim,top,depth))
                    RESULT['rtl'].append(row);progress('rtl_case_complete')
        assert sum(len(x['tests'])for x in RESULT['rtl'])==66
        for depth in DEPTHS:
            for top in TESTS:
                netlist,syn=synthesize(top,depth,paths);RESULT['synthesis'].append(syn)
                row=simulate(top,depth,'icarus',[netlist],'mapped-%s-d%d'%(top,depth),mapped=True)
                RESULT['mapped'].append(row);progress('mapped_case_complete')
        assert len(RESULT['synthesis'])==6 and sum(len(x['tests'])for x in RESULT['mapped'])==33
        for mutation in mutation_list():
            top=Path(mutation['path']).stem
            # The same top/depth/test has already passed on both exact RTL engines.
            assert all(any(x['top']==top and x['depth']==4 and x['simulator']==sim and
                       any(t['test']==mutation['test']and t['disposition']=='PASS'for t in x['tests'])
                       for x in RESULT['rtl'])for sim in ('icarus','verilator'))
            row=simulate(top,4,'icarus',source_paths(vendor,mutation),'mutant-'+mutation['name'],mutation)
            RESULT['mutations'].append(row);progress('mutation_complete')
        assert len(RESULT['mutations'])==18
        pins()
        RESULT.update(status='PASS_RECORD_CDC_66_RTL_33_MAPPED_18_COMPILED_FAULTS',
                      engineering_accepted=True)
    except BaseException as error:
        RESULT.update(status='FAIL_OR_INTERRUPTED',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        cleanup=s.stop_process(s.ACTIVE);s.STOP.set();thread.join(timeout=2)
        for sig,fn in old.items():signal.signal(sig,fn)
        RESULT['last_cleanup']=cleanup
        try:pins();RESULT['terminal_source_pins_unchanged']=True
        except BaseException as error:
            RESULT.update(status='FAIL_OR_INTERRUPTED',engineering_accepted=False,source_recheck_error=repr(error))
        save(OUT/'result.json',RESULT)
        s.event('cdc_terminal',status=RESULT['status'],engineering_accepted=RESULT['engineering_accepted'])
        assert RESULT.get('terminal_source_pins_unchanged')is True,'terminal source identity failed'

def log_result(controls=False):
    path=OUT/('controls.json'if controls else'result.json')
    if not path.exists():
        print('CDC_RESULT_ABSENT '+path.name,flush=True);return
    raw=path.read_bytes();assert len(raw)<=2*1024*1024
    encoded=base64.b64encode(raw).decode();chunks=[encoded[i:i+4096]for i in range(0,len(encoded),4096)]
    print('CDC_RESULT '+json.dumps(dict(name=path.name,bytes=len(raw),sha256=sha(raw),chunks=len(chunks))),flush=True)
    for i,chunk in enumerate(chunks):print('CDC_RESULT_CHUNK '+path.name+' '+str(i)+' '+chunk,flush=True)

def publish():
    """Publish stable completed/failed evidence; never create or move a release."""
    m=pins();s=supervisor()
    OUT.mkdir(parents=True,exist_ok=True)
    PUBLICATION.mkdir(parents=True,exist_ok=False)
    # Packing/upload supervision must not change the directory being archived.
    s.TRACE=PUBLICATION/'supervision';s.TRACE.mkdir()
    if not (OUT/'result.json').exists():
        save(OUT/'result.json',dict(status='FAIL_MISSING_NATIVE_RESULT',run=os.environ['GITHUB_RUN_ID'],
          attempt=os.environ['GITHUB_RUN_ATTEMPT'],source=os.environ['GITHUB_SHA'],
          engineering_accepted=False,scope=SCOPE,source_pins=m))
    command([sys.executable,ROOT/'scripts/wait_cloud_tested_source_release.py','--group',GROUP],
            'publication-exact-source-prerelease',seconds=360)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    summary=PUBLICATION/(stem+'.summary.json')
    summary.write_bytes((OUT/'result.json').read_bytes())
    command([sys.executable,ROOT/'scripts/cloud_chunked_results.py','--directory',OUT,'--stem',stem],
            'pack-complete-evidence',cwd=PUBLICATION)
    parts=PUBLICATION/(stem+'.parts.json');manifest=json.loads(parts.read_text())
    paths=[summary,parts,*[PUBLICATION/x['name']for x in manifest['parts']]]
    # Reuse the pinned publisher's retries/no-overwrite/digest verification, but
    # replace only its release lookup with the existing strict read-only validator.
    # This prevents its legacy create fallback from targeting another branch.
    program=r"""
import json,os,sys
sys.path.insert(0,sys.argv[1])
import ensure_cloud_tested_source_release as guard
import migrate_outputs_to_cloud as migration
import publish_cloud_results as publisher
group=sys.argv[2]
expected,source=guard.context(group,os.environ)
def readonly_release(tag):
    assert tag==expected
    info=guard.api('releases/tags/'+tag)
    guard.validate_release(info,guard.api('git/ref/tags/'+tag),tag,source)
    return info
migration.release=readonly_release
result=publisher.publish_results(group,sys.argv[3:])
assert result['tag']==expected
readonly_release(expected)
print(json.dumps(result,sort_keys=True),flush=True)
"""
    r=command([sys.executable,'-c',program,ROOT/'scripts',GROUP,*paths],'publish-verified-assets')
    proof=json.loads(r.stdout);assert len(proof['assets'])==len(paths)
    save(PUBLICATION/'publication.json',dict(status='PUBLISHED_EXACT_SOURCE_COMPLETE_EVIDENCE',
         summary=file_info(summary),parts=file_info(parts),publication=proof,
         original_engineering_status=json.loads(summary.read_text())['status'],
         publication_does_not_change_acceptance=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--native',action='store_true');modes.add_argument('--publish',action='store_true')
    modes.add_argument('--log-result',action='store_true');modes.add_argument('--log-controls',action='store_true')
    args=parser.parse_args()
    if args.log_result or args.log_controls:log_result(args.log_controls)
    elif args.publish:publish()
    else:native()
