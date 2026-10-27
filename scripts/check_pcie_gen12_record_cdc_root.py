#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Focused hosted root regression for the unchanged qualified Gen12 CDC package."""
import argparse,base64,hashlib,importlib.metadata,json,math,os,re,subprocess,sys,traceback
import urllib.request,tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import check_pcie_gen12_record_cdc_source as source

ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/'hw/soc/tb/cocotb'
MAKEFILE=BENCH/'Makefile.gen12_record_cdc'
METHOD=ROOT/'scripts/pcie-gen12-record-cdc-root-integration-methods.json'
TESTS=source.TESTS
RTL_NAMES=('soc_pcie_gen12_record_cdc_v1.v','soc_pcie_gen12_recovered_records_v1.v',
 'soc_pcie_gen3_block_cdc_v1.v','soc_pcie_gen12_training_records.v',
 'soc_pcie_gen12_raw32_rx.v','soc_pcie_gen12_raw32_align.v','soc_pcie_gen12_tx_raw32.v',
 'soc_pcie_gen12_8b10b_decode.v','soc_pcie_gen12_8b10b_encode.v',
 'vendor/benz_8b10b_decode.v','vendor/benz_8b10b_encode.v')
sha=source.sha

def pins():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted verification only'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc','Wrong repository'
    m=json.loads(METHOD.read_bytes())
    assert m['schema']=='root-gen12-record-cdc-functional-regression-v1'
    assert all(v is False for v in m['scope'].values())
    for p,h in m['protected'].items():
        assert sha((ROOT/p).read_bytes())==h,'Integration source pin: '+p
    original=source.check()
    assert original['protected_count']==27
    return m,original

def binding(module):
    pins()
    assert module in {'test_'+top for top in TESTS},'Unknown CDC test module'
    return True

def save(path,value):
    path=Path(path);raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    assert len(raw)<=4*1024**2,'Oversized result'
    tmp=path.with_name(path.name+'.writing')
    with tmp.open('wb')as f:f.write(raw)
    tmp.replace(path)

# Four functions below are copied byte-exact from qualified d246ded3 controller.
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

def source_paths(vendor):
    paths=[ROOT/'hw/soc/rtl/pcie'/n for n in RTL_NAMES]+[vendor]
    assert len(paths)==len(set(paths))==12
    assert sum('module axis_async_fifo' in p.read_text()for p in paths)==1
    for p in paths:assert re.fullmatch(r'[A-Za-z0-9_./-]+',str(p))
    return paths

def execute(args,directory,label,env,seconds=900):
    assert type(seconds)is int and 1<=seconds<=900
    directory.mkdir(parents=True,exist_ok=True)
    out=directory/(label+'.stdout');err=directory/(label+'.stderr')
    command=['timeout','--signal=TERM','--kill-after=10s',str(seconds)+'s',*map(str,args)]
    with out.open('xb')as stdout,err.open('xb')as stderr:
        completed=subprocess.run(command,cwd=BENCH,env=env,stdout=stdout,stderr=stderr,check=False)
    return dict(command=command,returncode=completed.returncode,
      stdout=dict(path=str(out),bytes=out.stat().st_size,sha256=sha(out.read_bytes())),
      stderr=dict(path=str(err),bytes=err.stat().st_size,sha256=sha(err.read_bytes())))

def fetch_vendor(out,record):
    url='https://raw.githubusercontent.com/alexforencich/verilog-ethernet/'+record['source_ref']+'/'+record['path']
    assert record['source_ref']=='12744433de03b28ba4b0081ad3f49b150327b8fc'
    assert record['path']=='lib/axis/rtl/axis_async_fifo.v'
    with urllib.request.urlopen(url,timeout=60)as response:raw=response.read(record['bytes']+1)
    vendor_admission(raw,record)
    path=out/'vendor/axis_async_fifo.v';path.parent.mkdir()
    path.write_bytes(raw)
    return path

def matrix(simulators,depths):
    assert simulators in [('icarus',),('icarus','verilator')],'Unreviewed simulators'
    assert depths==(4,8,32),'All three qualified depths are required'
    return [(sim,depth,top)for sim in simulators for depth in depths for top in TESTS]

def runtime(out,simulators):
    assert sys.version_info[:2]==(3,12),'Use qualified Python3.12'
    venv=Path(tempfile.mkdtemp(prefix='gen12-root-runtime-',dir=os.environ['RUNNER_TEMP']))/'venv'
    setup=dict(os.environ)
    created=execute([sys.executable,'-m','venv',venv],out/'toolchain','venv',setup,120)
    assert created['returncode']==0,'Runtime venv creation failed'
    installed=execute([venv/'bin/python','-m','pip','install','--require-hashes','--only-binary=:all:',
      '-r',ROOT/'scripts/pcie-gen12-record-cdc-requirements.txt'],out/'toolchain','packages',setup,300)
    assert installed['returncode']==0,'Pinned runtime installation failed'
    verify='import sys,importlib.metadata;assert sys.version_info[:2]==(3,12);assert importlib.metadata.version("cocotb")=="2.0.1";assert importlib.metadata.version("find_libpython")=="0.4.0"'
    verified=execute([venv/'bin/python','-c',verify],out/'toolchain','package-identities',setup,60)
    assert verified['returncode']==0,'Installed runtime identities differ'
    env=dict(os.environ,PATH=str(venv/'bin')+':'+os.environ['PATH'],
      PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',
      COCOTB_REWRITE_ASSERTION_FILES='',COCOTB_ANSI_OUTPUT='0',COCOTB_RANDOM_SEED='20261025',
      COCOTB_LOG_LEVEL='INFO',COCOTB_REDUCED_LOG_FMT='1',COCOTB_HDL_TIMEUNIT='1ns',
      COCOTB_HDL_TIMEPRECISION='1ps',MAKEFLAGS='')
    versions={}
    for sim in simulators:
        command=['iverilog','-V']if sim=='icarus'else['verilator','--version']
        row=execute(command,out/'toolchain','version-'+sim,env,60)
        assert row['returncode']==0,'Tool version command failed'
        if sim=='verilator':
            assert 'Verilator 5.040' in Path(row['stdout']['path']).read_text(),'Use qualified Verilator5.040'
        versions[sim]=row
    return env,dict(python=sys.version,cocotb='2.0.1',find_libpython='0.4.0',versions=versions,
      setup=[created,installed,verified],requirements_sha256=sha((ROOT/'scripts/pcie-gen12-record-cdc-requirements.txt').read_bytes()))

def inventory(out):
    return {str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
      for p in sorted(out.rglob('*'))if p.is_file()and p.name not in ('result.json','result.json.writing')}

def run(out,simulators,depths):
    m,original=pins();cases=matrix(simulators,depths)
    out=Path(out).resolve()
    assert out.is_relative_to(ROOT/'hw/soc/out'),'Output must remain in the root evidence tree'
    out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',run=os.environ.get('GITHUB_RUN_ID'),source=os.environ.get('GITHUB_SHA'),
      original_source_controls=original,method_sha256=sha(METHOD.read_bytes()),scope=m['scope'],simulations=[],expected_invocations=len(cases),
      expected_tests=11*len(simulators)*len(depths),source_pins=m['protected'],errors=[])
    primary=None
    try:
        save(out/'result.json',result)
        env,result['toolchain']=runtime(out,simulators)
        vendor=fetch_vendor(out,m['vendor']);paths=source_paths(vendor)
        result['vendor']=dict(path=str(vendor),bytes=vendor.stat().st_size,sha256=sha(vendor.read_bytes()))
        for sim,depth,top in cases:
            label=sim+'-'+top+'-d'+str(depth);case=out/'simulations'/label
            case.mkdir(parents=True,exist_ok=False)
            build=case/'build';xml=case/'results.xml'
            args=make_args(top,depth,sim,paths,build,xml)
            binary=build/('sim.vvp'if sim=='icarus'else'Vtop')
            print('GEN12_ROOT_CASE '+label,flush=True)
            row=dict(label=label,simulator=sim,depth=depth,top=top,status='COMPILING')
            result['simulations'].append(row);save(out/'result.json',result)
            row['compile']=execute(args+[str(binary)],case,'compile',env)
            compile_admission(row['compile']['returncode'],binary)
            row.update(status='SIMULATING',compiled_image=dict(bytes=binary.stat().st_size,sha256=sha(binary.read_bytes())))
            save(out/'result.json',result)
            row['simulation']=execute(args+[str(xml)],case,'simulation',env)
            assert xml.is_file(),'Simulation produced no XML'
            raw=xml.read_bytes();row['tests']=xml_review(raw,top,row['simulation']['returncode'])
            row.update(status='PASS',xml=dict(bytes=len(raw),sha256=sha(raw),path=str(xml)))
            save(out/'result.json',result)
        assert len(result['simulations'])==result['expected_invocations']
        assert sum(len(r['tests'])for r in result['simulations'])==result['expected_tests']
        result['status']='PASS_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL'
    except BaseException as error:
        primary=error;result.update(status='FAIL_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL',error=repr(error),traceback=traceback.format_exc())
    finally:
        try:pins();result['terminal_source_pins_unchanged']=True
        except BaseException as error:
            result['errors'].append(dict(phase='terminal-source-pins',error=repr(error)))
            result['status']='FAIL_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL'
            if primary is None:primary=error
        try:result['outputs']=inventory(out)
        except BaseException as error:
            result['errors'].append(dict(phase='terminal-inventory',error=repr(error)))
            result['status']='FAIL_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL'
            if primary is None:primary=error
        save(out/'result.json',result)
    if primary is not None:raise primary
    return result

def counts(path):
    result=json.loads(Path(path).read_bytes())
    assert result['status']=='PASS_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL'
    assert result['terminal_source_pins_unchanged']is True and result['errors']==[]
    rows=result['simulations']
    assert len(rows)==result['expected_invocations']and len({r['label']for r in rows})==len(rows)
    simulators=tuple(dict.fromkeys(r['simulator']for r in rows))
    assert [(r['simulator'],r['depth'],r['top'])for r in rows]==matrix(simulators,(4,8,32)),'Result matrix changed'
    assert all(r['status']=='PASS'and r['compile']['returncode']==r['simulation']['returncode']==0 for r in rows)
    assert all([t['test']for t in r['tests']]==TESTS[r['top']]or
      (len(r['tests'])==len(TESTS[r['top']])and{t['test']for t in r['tests']}==set(TESTS[r['top']]))for r in rows)
    assert all(t['disposition']=='PASS'for r in rows for t in r['tests'])
    n=sum(len(r['tests'])for r in rows);assert n==result['expected_tests']
    return n,0,0

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--out');g.add_argument('--counts');g.add_argument('--bind-module')
    p.add_argument('--simulators',nargs='+',default=['icarus']);p.add_argument('--depths',nargs='+',type=int,default=[4,8,32])
    a=p.parse_args()
    if a.counts:print(*counts(a.counts));return
    if a.bind_module:binding(a.bind_module);return
    run(a.out,tuple(a.simulators),tuple(a.depths))

if __name__=='__main__':main()
