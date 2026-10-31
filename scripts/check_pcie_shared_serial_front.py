#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted shared raw32 record front integration; no physical or LTSSM acceptance."""
import argparse,ast,hashlib,json,math,os,re,subprocess,sys,tempfile,traceback,urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/'hw/soc/tb/cocotb'
MAKEFILE=BENCH/'Makefile.pcie_shared_serial_front'
METHOD=ROOT/'scripts/pcie-shared-serial-front-methods.json'
RTL=ROOT/'hw/soc/rtl/pcie'
FRONT='soc_pcie_gen3_recovered_front_x4_v1'
MITER='pcie_shared_front_events_compare'
BASELINE='b70200e8415e8403e9e6f63e299828fd45f0e56b'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
TESTS={"test_pcie_shared_serial_front":["raw_bits_all_offsets_complete_fields","independent_lane_stalls_preserve_every_record","loss_overflow_realign_and_reset_exclude_old_records","independent_startup_and_common_clock_status_ownership"],"test_pcie_shared_serial_front_composition":["stopped_lane_keeps_normal_all_lane_barrier","early_arm_faults_both_compositions_and_reset_recovers"],"test_soc_pcie_gen3_recovered_events_v2":["crc_bad_nullified_ack_nak_fc_and_owner_wrap","complete_dllp_density_exceeds_every_owner_buffer","independent_tlp_and_event_backpressure","all_32_raw_phases_preserve_owners_and_events","eieos_drains_all_owned_outputs","normal_end_keeps_held_events_during_later_lane_fault","normal_end_waits_for_events_after_body_drains","finite_owner_exhaustion_aborts_without_stale_events","bad_token_aborts_owned_epoch","missing_eds_aborts_owned_epoch","explicit_abort_suppresses_held_event_before_edge_and_reset_recovers"]}
MUTATIONS=[
 dict(name='lost-realign',old='.wr_realign_i(realign)',new=".wr_realign_i(1'b0)"),
 dict(name='truncated-194-bit-record',old='.wr_block_i(block_data)',new=".wr_block_i({64'b0,block_data[129:0]})")]
def pins():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted verification only'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    assert os.environ.get('GITHUB_REF')=='refs/heads/codex/pcie-shared-serial-front-v1'
    assert re.fullmatch('[0-9a-f]{40}',os.environ['GITHUB_SHA'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==os.environ['GITHUB_SHA']
    m=json.loads(METHOD.read_bytes())
    assert m['schema']=='pcie-shared-serial-front-v1' and m['base']==BASELINE
    assert all(v is False for v in m['physical_and_protocol_acceptance'].values())
    for p,h in m['protected'].items():assert sha((ROOT/p).read_bytes())==h,'Source pin: '+p
    for module,names in TESTS.items():
        tree=ast.parse((BENCH/(module+'.py')).read_text())
        actual=[n.name for n in tree.body if isinstance(n,ast.AsyncFunctionDef)and any(
          isinstance(d,ast.Call)and isinstance(d.func,ast.Attribute)and isinstance(d.func.value,ast.Name)
          and d.func.value.id=='cocotb'and d.func.attr=='test'for d in n.decorator_list)]
        assert actual==names,'Named tests changed: '+module
    d=m['derivation'];old=(RTL/'soc_pcie_gen3_recovered_x4_v4.v').read_text()
    segment=d['front_baseline_segment'];assert old.count(segment)==1
    expected=old.replace('soc_pcie_gen3_recovered_x4_v4','soc_pcie_gen3_recovered_x4_v5').replace(segment,d['v5_replacement'])
    assert (RTL/'soc_pcie_gen3_recovered_x4_v5.v').read_text()==expected,'v5 semantic derivation changed'
    front=segment
    for a,b in d['front_body_substitutions']:front=front.replace(a,b)
    assert (RTL/(FRONT+'.v')).read_text().count(front)==1,'Shared aligner/CDC body changed'
    for source,target,a,b in [
      ('soc_pcie_gen3_recovered_owned_rx_v1','soc_pcie_gen3_recovered_owned_rx_v2','soc_pcie_gen3_recovered_x4_v4','soc_pcie_gen3_recovered_x4_v5'),
      ('soc_pcie_gen3_recovered_events_v2','soc_pcie_gen3_recovered_events_v3','soc_pcie_gen3_recovered_owned_rx_v1','soc_pcie_gen3_recovered_owned_rx_v2')]:
        assert (RTL/(target+'.v')).read_text()==(RTL/(source+'.v')).read_text().replace(source,target).replace(a,b)
    assert (RTL/(FRONT+'.v')).read_text().count('soc_pcie_gen3_lane_align_v3 aligner')==1
    assert (RTL/(FRONT+'.v')).read_text().count('soc_pcie_gen3_block_cdc_v1 #')==1
    for p in m['protected']:
        if p.endswith('.py'):ast.parse((ROOT/p).read_text(),filename=p)
    return m

def save(path,value):
    path=Path(path);raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    assert len(raw)<=8*1024**2
    tmp=path.with_name(path.name+'.writing');tmp.write_bytes(raw);tmp.replace(path)

def source_controls():
    m=pins()
    return dict(status='PASS_SHARED_FRONT_SOURCE_CONTROLS',source=os.environ['GITHUB_SHA'],
      protected=len(m['protected']),normal_consumer_derivation_verified=True,
      owned_events_composition_verified=True,original_oracles_byte_frozen=True,
      named_tests=TESTS,physical_and_protocol_acceptance=m['physical_and_protocol_acceptance'])

def vendor_admission(raw,record):
    assert len(raw)==record['bytes']and sha(raw)==record['sha256'],'Vendor bytes'
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['git_blob_sha']
    assert raw.count(b'module axis_async_fifo')==1

def execute(args,directory,label,env,seconds=900):
    assert type(seconds)is int and 1<=seconds<=900
    directory.mkdir(parents=True,exist_ok=True)
    out=directory/(label+'.stdout');err=directory/(label+'.stderr')
    command=['timeout','--signal=TERM','--kill-after=10s',str(seconds)+'s',*map(str,args)]
    with out.open('xb')as stdout,err.open('xb')as stderr:
        completed=subprocess.run(command,cwd=BENCH,env=env,stdout=stdout,stderr=stderr,check=False)
    if completed.returncode:
        print('ACTUAL_FAILED_COMMAND '+label,flush=True)
        print(out.read_text(errors='replace'),flush=True)
        print(err.read_text(errors='replace'),flush=True)
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


def runtime(out,simulators):
    assert sys.version_info[:2]==(3,12),'Use qualified Python3.12'
    venv=Path(tempfile.mkdtemp(prefix='shared-front-runtime-',dir=os.environ['RUNNER_TEMP']))/'venv'
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
      COCOTB_REWRITE_ASSERTION_FILES='',COCOTB_ANSI_OUTPUT='0',COCOTB_RANDOM_SEED='20261031',
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



def paths(vendor,front_only=False):
    names=[FRONT+'.v','soc_pcie_gen3_lane_align_v3.v','soc_pcie_gen3_block_cdc_v1.v']
    if not front_only:names+=['soc_pcie_gen3_recovered_x4_v4.v','soc_pcie_gen3_recovered_x4_v5.v',
      'soc_pcie_gen3_recovered_owned_rx_v1.v','soc_pcie_gen3_recovered_owned_rx_v2.v',
      'soc_pcie_gen3_recovered_events_v2.v','soc_pcie_gen3_recovered_events_v3.v',
      'soc_pcie_gen3_framer_rx_owned_v3.v','soc_pcie_gen3_dllp_consumer_v6.v',
      'soc_pcie_gen3_sds_deskew_v2.v','soc_pcie_gen3_record_descrambler_v1.v']
    result=[RTL/n for n in names]+[vendor]
    if not front_only:result+=[ROOT/'hw/soc/tb/pcie_shared_front_events_compare.v']
    assert len(set(result))==len(result)
    assert sum('module axis_async_fifo' in p.read_text()for p in result)==1
    return result

def xml_review(raw,module,returncode,mutation=None,log=''):
    assert len(raw)<=2*1024**2 and b'<!DOCTYPE'not in raw and b'<!ENTITY'not in raw
    tree=ET.fromstring(raw);assert tree.tag in ('testsuites','testsuite')
    cases=list(tree.iter('testcase'));names=[c.attrib['name']for c in cases]
    assert len(names)==len(set(names))and set(names)==set(TESTS[module]),'Incomplete named test matrix'
    assert not list(tree.iter('error')),'XML setup error is not behavioral detection'
    result=[]
    for c in cases:
        name=c.attrib['name']
        assert c.attrib['classname']==module and Path(c.attrib['file']).resolve()==BENCH/(module+'.py')
        time=float(c.attrib['sim_time_ns']);assert math.isfinite(time)and time>=0
        failures=c.findall('failure');skips=c.findall('skipped')
        assert all(x.tag in ('failure','skipped')for x in c)
        if mutation and name!=TESTS[module][0]:
            assert len(skips)==1 and not failures and time==0
            result.append(dict(test=name,disposition='FILTERED_NOT_EXECUTED'));continue
        assert not skips and time>0,'Skipped or unexecuted required test'
        if mutation:
            assert returncode!=0 and len(failures)==1
            f=failures[0];assert f.attrib.get('error_type')=='AssertionError'
            assert 'Complete front record mismatch' in f.attrib.get('error_msg',''),'Nonsemantic mutation failure'
            frames=re.findall(r'File "([^"]+)", line ([0-9]+), in [^\n]+',log)
            assert frames and Path(frames[-1][0]).resolve()==BENCH/(module+'.py')
            line=(BENCH/(module+'.py')).read_text().splitlines()[int(frames[-1][1])-1]
            assert 'assert item==expected' in line,'Wrong mutation assertion origin'
            result.append(dict(test=name,disposition='DETECTED_ASSERTION',error=f.attrib,origin=frames[-1]))
        else:
            assert returncode==0 and not failures,'Actual positive RTL failed'
            result.append(dict(test=name,disposition='PASS',sim_time_ns=time))
    return result

def matrix():
    return [(sim,depth,FRONT,'test_pcie_shared_serial_front',None)
      for sim in ('icarus','verilator')for depth in (4,8,32)]+[
      (sim,32,MITER,module,None)for sim in ('icarus','verilator')
      for module in ('test_soc_pcie_gen3_recovered_events_v2','test_pcie_shared_serial_front_composition')]+[
      ('icarus',4,FRONT,'test_pcie_shared_serial_front',m)for m in MUTATIONS]

def hierarchy(out,env,vendor):
    proof=[]
    for top in ('soc_pcie_gen3_recovered_x4_v5','soc_pcie_gen3_recovered_events_v3'):
        directory=out/'hierarchy'/top;directory.mkdir(parents=True)
        js=directory/'hierarchy.json'
        sources=[p for p in paths(vendor)if p.name!='pcie_shared_front_events_compare.v']
        script='read_verilog -sv '+' '.join(map(str,sources))+'; hierarchy -check -top '+top+'; proc; check -assert; write_json '+str(js)
        row=execute(['yosys','-Q','-p',script],directory,'yosys',env)
        assert row['returncode']==0 and js.is_file(),'Actual production hierarchy failed'
        modules=json.loads(js.read_text())['modules'];counts={}
        def walk(name):
            module=modules[name];kind=module.get('attributes',{}).get('hdlname',name).split()[0]
            counts[kind]=counts.get(kind,0)+1
            for cell in module['cells'].values():
                if cell['type']in modules:walk(cell['type'])
        walk(top)
        for kind,n in [(FRONT,1),('soc_pcie_gen3_lane_align_v3',4),('soc_pcie_gen3_block_cdc_v1',4),('axis_async_fifo',4)]:
            assert counts.get(kind)==n,('Duplicate/missing production front',top,kind,counts)
        proof.append(dict(top=top,status='PASS',counts=counts,command=row,sha256=sha(js.read_bytes())))
    return proof

def run(out):
    m=pins();out=Path(out).resolve();assert out.is_relative_to(ROOT/'hw/soc/out')
    out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',run=os.environ['GITHUB_RUN_ID'],attempt=os.environ['GITHUB_RUN_ATTEMPT'],
      source=os.environ['GITHUB_SHA'],method_sha256=sha(METHOD.read_bytes()),simulations=[],hierarchy=[],
      physical_and_protocol_acceptance=m['physical_and_protocol_acceptance'],errors=[])
    primary=None
    try:
        save(out/'result.json',result)
        env,result['toolchain']=runtime(out,('icarus','verilator'))
        vendor=fetch_vendor(out,m['vendor'])
        result['hierarchy']=hierarchy(out,env,vendor);save(out/'result.json',result)
        for sim,depth,top,module,mutation in matrix():
            label=sim+'-'+module+'-d'+str(depth)+(('-'+mutation['name'])if mutation else '')
            case=out/'simulations'/label;case.mkdir(parents=True)
            source_paths=paths(vendor,top==FRONT)
            if mutation:
                original=source_paths[0].read_text();assert original.count(mutation['old'])==1
                changed=case/(FRONT+'.v');changed.write_text(original.replace(mutation['old'],mutation['new']))
                source_paths[0]=changed
            build=case/'build';xml=case/'results.xml'
            args=['make','-f',str(MAKEFILE),'SIM='+sim,'TOPLEVEL='+top,'DEPTH='+str(depth),
              'COCOTB_TEST_MODULES='+module,'SIM_BUILD='+str(build),'COCOTB_RESULTS_FILE='+str(xml),
              'VERILOG_SOURCES='+' '.join(map(str,source_paths)),'BUILD_ARGS=-j2','WAVES=0',
              'COCOTB_TEST_FILTER='+('^'+module+r'\.'+TESTS[module][0]+'$'if mutation else '')]
            binary=build/('sim.vvp'if sim=='icarus'else'Vtop')
            row=dict(label=label,simulator=sim,depth=depth,top=top,module=module,mutation=mutation,status='COMPILING')
            result['simulations'].append(row);save(out/'result.json',result)
            print('SHARED_FRONT_CASE '+label,flush=True)
            row['compile']=execute(args+[str(binary)],case,'compile',env)
            assert row['compile']['returncode']==0 and binary.is_file()and binary.stat().st_size>0,'Compile/setup failure'
            row['compiled_image']=dict(bytes=binary.stat().st_size,sha256=sha(binary.read_bytes()))
            row['status']='SIMULATING';save(out/'result.json',result)
            row['simulation']=execute(args+[str(xml)],case,'simulation',env)
            assert xml.is_file(),'Simulation produced no XML'
            log=Path(row['simulation']['stdout']['path']).read_text()+Path(row['simulation']['stderr']['path']).read_text()
            row['tests']=xml_review(xml.read_bytes(),module,row['simulation']['returncode'],mutation,log)
            row.update(status='PASS'if mutation is None else'DETECTED_ASSERTION',xml_sha256=sha(xml.read_bytes()))
            save(out/'result.json',result)
        assert len(result['simulations'])==12
        assert sum(t['disposition']=='PASS'for r in result['simulations']for t in r['tests'])==50
        assert sum(t['disposition']=='DETECTED_ASSERTION'for r in result['simulations']for t in r['tests'])==2
        result['status']='PASS_SHARED_FRONT_50_RTL_2_MUTATIONS_2_HIERARCHIES'
    except BaseException as error:
        primary=error;result.update(status='FAIL_SHARED_FRONT_RTL',error=repr(error),traceback=traceback.format_exc())
    finally:
        try:pins();result['terminal_source_pins_unchanged']=True
        except BaseException as error:
            result['errors'].append(dict(phase='terminal-pins',error=repr(error)));result['status']='FAIL_SHARED_FRONT_RTL'
            if primary is None:primary=error
        result['outputs']=inventory(out);save(out/'result.json',result)
    if primary is not None:raise primary
    return result

def publish(out,destination):
    import cloud_chunked_results
    import ensure_cloud_tested_source_release as release
    pins();out=Path(out).resolve();destination=Path(destination).resolve()
    assert out.is_relative_to(ROOT/'hw/soc/out')and out.exists()
    assert not destination.is_relative_to(out)
    destination.mkdir(parents=True,exist_ok=False)
    tag,source=release.context('pcie-shared-serial-front-v1',os.environ)
    info=release.api('releases/tags/'+tag)
    proof=release.validate_release(info,release.api('git/ref/tags/'+tag),tag,source)
    assert proof['existing_assets']==[],'Never overwrite or retry a partial publication'
    stem='pcie-shared-serial-front-v1'
    manifest=cloud_chunked_results.pack(out,stem,destination)
    direct=destination/'result.json';direct.write_bytes((out/'result.json').read_bytes())
    uploads=[destination/r['name']for r in manifest['parts']]+[destination/(stem+'.parts.json'),direct]
    for path in uploads:
        subprocess.run(['gh','release','upload',tag,str(path),'-R',release.REPO],check=True)
    terminal=release.api('releases/tags/'+tag)
    assert {a['name']for a in terminal['assets']}=={p.name for p in uploads}
    for a in terminal['assets']:
        p=destination/a['name'];assert a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p.read_bytes())
    receipt=dict(status='COMPLETE_UNFILTERED_OUTPUTS_PUBLISHED',release_id=info['id'],tag=tag,source=source,
      assets=terminal['assets'],all_outputs_preserved=True,assets_overwritten=False,
      physical_and_protocol_acceptance=json.loads(METHOD.read_bytes())['physical_and_protocol_acceptance'])
    save(destination/'publication-receipt.json',receipt)
    subprocess.run(['gh','release','upload',tag,str(destination/'publication-receipt.json'),'-R',release.REPO],check=True)
    print(json.dumps(receipt,indent=2))

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--source-controls',action='store_true');g.add_argument('--out');g.add_argument('--publish')
    p.add_argument('--destination');a=p.parse_args()
    if a.source_controls:print(json.dumps(source_controls(),indent=2))
    elif a.publish:publish(a.publish,a.destination)
    else:run(a.out)
if __name__=='__main__':main()
