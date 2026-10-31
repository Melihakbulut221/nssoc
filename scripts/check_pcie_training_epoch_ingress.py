#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted candidate command/typed-ingress checks. No PHY, timing or signoff claim."""
import argparse,ast,hashlib,json,math,os,re,subprocess,sys,traceback
import xml.etree.ElementTree as ET
from pathlib import Path
import check_pcie_shared_serial_front as shared
ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/'hw/soc/tb/cocotb';RTL=ROOT/'hw/soc/rtl/pcie'
METHOD=ROOT/'scripts/pcie-training-epoch-ingress-methods.json'
BRANCH='codex/pcie-training-epoch-ingress-v1'
GROUP='pcie-training-epoch-ingress-v1'
REVIEWED_CORE_SOURCE='2a69d010371aff75fb8be204c92ef4c1d384d48e'
REVIEWED_CORE_PINS={"hw/soc/rtl/pcie/soc_pcie_training_epoch_control_v1.v":"cefc0002abae89ad0cafaae0bc6b78df02ddc4f702340b96b6465b0232747143","hw/soc/rtl/pcie/soc_pcie_training_ingress_x4_v1.v":"92d9cf982699c334aacf612f258fad32e43efa9e728589643479d16326872474","hw/soc/tb/cocotb/test_pcie_training_epoch_control.py":"42771e1e62452a33108d975422a52797f5dd4f5a9e9c1a80e62dcfa3cf96220f","hw/soc/tb/cocotb/test_pcie_training_ingress.py":"6b3ed9aa218f43dcc7e1314a9e1e0c3b5eeb7f67bea71a381c1ac38d821c3048"}
BASE='1d9847cfd8c159a3faef5dd50cc05cdf364cdfc8'
CONTROL='soc_pcie_training_epoch_control_v1'
INGRESS='soc_pcie_training_ingress_x4_v1'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
TESTS={
 'test_pcie_training_epoch_control':['held_payload_and_four_phase_ack_barrier',
  'modulo_wrap_stopped_clock_reset_and_fresh_ack','pma_wrong_epoch_encoding_and_lost_ack_are_not_success',
  'common_pause_abort_startup_and_illegal_encoding','stopped_lane_after_high_ack_cannot_abandon_low_phase','abort_on_completion_edge_suppresses_success_witness'],
 'test_pcie_training_ingress':['actual_gen12_full_records_all_offsets_polarities_and_errors',
  'actual_gen3_all_offsets_opaque_os_and_194_bit_metadata',
  'independent_ready_and_cross_encoding_epoch_flush_wrap',
  'asymmetric_reset_stopped_lane_overflow_and_no_stale_ack']}
def context(env,head):
    assert env.get('GITHUB_ACTIONS')=='true','Hosted only'
    assert env.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc','Repository'
    assert env.get('GITHUB_REF')=='refs/heads/'+BRANCH,'Actual branch'
    assert re.fullmatch('[0-9a-f]{40}',env.get('GITHUB_SHA','')),'Source format'
    assert env['GITHUB_SHA']==head,'Actual checked-out source'
    assert env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','Manual only'
    return head

def validate_manifest(m,raw):
    assert m['schema']=='pcie-training-epoch-ingress-v1'and m['base']==BASE
    assert m['branch']==BRANCH
    assert m['native_authorized']is True,'Native activation manifest'
    assert m['native_review']['core_source']==REVIEWED_CORE_SOURCE
    assert m['native_review']['dispatch_requires_exact_source']is True
    assert {p:m['protected'][p]for p in REVIEWED_CORE_PINS}==REVIEWED_CORE_PINS,'Reviewed RTL/oracle changed'
    expected_acceptance={'complete_semantic_training_owner','mainchip_serial_integration','full_gen3_x4_phy',
      'analog_cdr_pll_pma','physical_cdc','layout_drc_lvs','final_setup_hold','production_signoff'}
    assert set(m['physical_and_protocol_acceptance'])==expected_acceptance,'Acceptance schema'
    assert all(v is False for v in m['physical_and_protocol_acceptance'].values())
    assert set(raw)==set(m['protected']),'Exact protected source set'
    for p,h in m['protected'].items():
        assert type(raw[p])is bytes and sha(raw[p])==h,'Source bytes: '+p
    return m

def pins():
    context(os.environ,subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    m=json.loads(METHOD.read_bytes())
    validate_manifest(m,{p:(ROOT/p).read_bytes()for p in m['protected']})
    for module,names in TESTS.items():
        tree=ast.parse((BENCH/(module+'.py')).read_text())
        actual=[n.name for n in tree.body if isinstance(n,ast.AsyncFunctionDef)and any(
          isinstance(d,ast.Call)and isinstance(d.func,ast.Attribute)and isinstance(d.func.value,ast.Name)
          and d.func.value.id=='cocotb'and d.func.attr=='test'for d in n.decorator_list)]
        assert actual==names,'Required named oracle changed'
    for p in m['protected']:
        if p.endswith('.py'):ast.parse((ROOT/p).read_text(),filename=p)
    for mutation in m['mutations']:
        assert (RTL/mutation['file']).read_text().count(mutation['old'])==1,'Mutation anchor'
        assert mutation['assertion']in(BENCH/(mutation['module']+'.py')).read_text()
    # There is one frozen Gen3 front; no new decoder, aligner or FIFO inside ingress.
    ingress=(RTL/(INGRESS+'.v')).read_text()
    assert ingress.count('soc_pcie_gen3_recovered_front_x4_v1 #')==1
    assert ingress.count('soc_pcie_gen12_recovered_records_v1 #')==1
    assert all(x not in ingress for x in ('axis_async_fifo #','soc_pcie_gen3_lane_align_v3 '))
    assert 'fronts_ready=&common_running_o;'in ingress
    assert m['source_origins']['shared_front_ref']=='64d31863ad2f5cd59483251dbe1dad8e7069c44e'
    return m

def authorize_native(m,env=None,head=None):
    # Explicit manual exact-source dispatch only. Unit controls use isolated
    # dictionary arguments; neither real environment nor real Git refs are changed.
    env=os.environ if env is None else env
    if head is None:head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    context(env,head)
    assert m['native_authorized']is True
    assert m['native_review']['core_source']==REVIEWED_CORE_SOURCE
    assert {p:m['protected'][p]for p in REVIEWED_CORE_PINS}==REVIEWED_CORE_PINS
    assert env.get('GITHUB_JOB')=='epoch-rtl','Dedicated native job only'
    assert env.get('NSSOC_EPOCH_NATIVE')=='rtl','Explicit native mode required'
    assert env.get('NSSOC_EPOCH_APPROVED_SOURCE')==head,'Exact dispatch source approval required'
    return dict(source=head,reviewed_core_source=REVIEWED_CORE_SOURCE,native_job_authorized=True,
      physical_acceptance=False)

def reservation(m):
    import ensure_cloud_tested_source_release as release
    authorize_native(m)
    tag,source=release.context(GROUP,os.environ)
    return empty_reservation(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,source)

def empty_reservation(info,ref,tag,source):
    import ensure_cloud_tested_source_release as release
    proof=release.validate_release(info,ref,tag,source)
    assert proof['existing_assets']==[],'Native execution requires a separate empty exact-source release'
    return proof

def xml_review(raw,module,returncode,mutation=None,log=''):
    assert type(raw)is bytes and len(raw)<=2*1024**2 and b'<!DOCTYPE'not in raw and b'<!ENTITY'not in raw
    tree=ET.fromstring(raw);assert tree.tag in ('testsuites','testsuite')
    cases=list(tree.iter('testcase'));names=[c.attrib['name']for c in cases]
    assert len(names)==len(set(names))and set(names)==set(TESTS[module]),'Incomplete required named tests'
    assert not list(tree.iter('error')),'Setup errors do not qualify'
    result=[]
    for c in cases:
        name=c.attrib['name'];time=float(c.attrib['sim_time_ns'])
        assert math.isfinite(time)and time>=0
        assert c.attrib['classname']==module and Path(c.attrib['file']).resolve()==BENCH/(module+'.py')
        failures=c.findall('failure');skips=c.findall('skipped')
        assert all(x.tag in ('failure','skipped')for x in c)
        if mutation and name!=mutation['test']:
            assert len(skips)==1 and not failures and time==0
            result.append(dict(test=name,disposition='FILTERED_NOT_EXECUTED'));continue
        assert not skips and time>0,'Required test skipped'
        if mutation:
            assert returncode!=0 and len(failures)==1
            f=failures[0];assert f.attrib.get('error_type')=='AssertionError'
            assert mutation['assertion']in f.attrib.get('error_msg',''),'Wrong behavioral assertion'
            assert mutation['assertion']in log
            frames=re.findall(r'File "([^"]+)", line ([0-9]+), in [^\n]+',log)
            assert frames and Path(frames[-1][0]).resolve()==BENCH/(module+'.py'),'Wrong assertion file'
            origin=(BENCH/(module+'.py')).read_text().splitlines()[int(frames[-1][1])-1]
            assert mutation['assertion']in origin and 'assert 'in origin,'Wrong behavioral assertion origin'
            result.append(dict(test=name,disposition='DETECTED_ASSERTION',error=f.attrib,sim_time_ns=time,origin=frames[-1]))
        else:
            assert returncode==0 and not failures,'Actual RTL test failed'
            result.append(dict(test=name,disposition='PASS',sim_time_ns=time))
    return result

def paths(vendor):
    names=[CONTROL+'.v',INGRESS+'.v','soc_pcie_gen12_recovered_records_v1.v',
      'soc_pcie_gen12_record_cdc_v1.v','soc_pcie_gen12_training_records.v','soc_pcie_gen12_raw32_rx.v',
      'soc_pcie_gen12_raw32_align.v','soc_pcie_gen12_tx_raw32.v',
      'soc_pcie_gen12_8b10b_encode.v','soc_pcie_gen12_8b10b_decode.v',
      'vendor/benz_8b10b_encode.v','vendor/benz_8b10b_decode.v']
    result=[RTL/n for n in names]+shared.paths(vendor)
    assert len(set(result))==len(result)
    return result

def hierarchy(out,env,vendor):
    proofs=shared.hierarchy(out,env,vendor)
    for ew in (2,16):
        d=out/'hierarchy'/('ingress-e'+str(ew));d.mkdir(parents=True)
        js=d/'hierarchy.json';sources=[p for p in paths(vendor)if p.name!='pcie_shared_front_events_compare.v']
        script='read_verilog -sv '+' '.join(map(str,sources))+'; chparam -set EPOCH_W '+str(ew)+' '+INGRESS+'; hierarchy -check -top '+INGRESS+'; proc; check -assert; write_json '+str(js)
        row=shared.execute(['yosys','-Q','-p',script],d,'yosys',env)
        assert row['returncode']==0 and js.is_file(),'Actual ingress hierarchy failed'
        modules=json.loads(js.read_text())['modules'];counts={}
        allowed={n for p in sources for n in re.findall(r'^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)',p.read_text(),re.M)}
        def walk(name):
            module=modules[name];kind=module.get('attributes',{}).get('hdlname',name).split()[0].lstrip(chr(92))
            assert kind in allowed,('Unknown native module',kind)
            counts[kind]=counts.get(kind,0)+1
            for cell in module['cells'].values():
                if cell['type']in modules:walk(cell['type'])
        walk(INGRESS)
        for kind,n in [(CONTROL,1),('soc_pcie_gen3_recovered_front_x4_v1',1),
          ('soc_pcie_gen3_lane_align_v3',4),('soc_pcie_gen12_recovered_records_v1',4),
          ('soc_pcie_gen12_training_records',4),('soc_pcie_gen12_record_cdc_v1',4),
          ('soc_pcie_gen3_block_cdc_v1',8),('axis_async_fifo',8)]:
            assert counts.get(kind)==n,('Actual physical instance census',kind,counts)
        controllers=[module for module in modules.values()
          if module.get('attributes',{}).get('hdlname','').split()
          and module['attributes']['hdlname'].split()[0].lstrip(chr(92))==CONTROL]
        assert len(controllers)==1,'One actual mailbox controller required'
        cm=controllers[0];nets=cm['netnames'];cells=cm['cells']
        sync={n:v for n,v in nets.items()if str(v.get('attributes',{}).get('ASYNC_REG','')).upper()=='TRUE'}
        expected={'ack_meta_q':4,'ack_sync_q':4}
        expected.update({'mailboxes['+str(k)+'].request_sync_q':2 for k in range(4)})
        assert {n:len(v['bits'])for n,v in sync.items()}==expected,'Synchronizer attributes or widths changed'
        sync_proof={}
        for name,width in expected.items():
            bits=sync[name]['bits'];assert len(set(bits))==width
            owners=[(n,c)for n,c in cells.items()if c['type']=='$adff'and c['connections']['Q']==bits]
            assert len(owners)==1,'Synchronizer register must have one actual async-reset flop bundle'
            cell_name,cell=owners[0]
            assert cell['connections']['ARST']==nets['por_ni']['bits']
            assert int(cell['parameters']['ARST_POLARITY'],2)==0
            assert int(cell['parameters']['ARST_VALUE'],2)==0
            if name.startswith('mailboxes['):
                lane=int(name.split('[')[1].split(']')[0])
                assert cell['connections']['CLK']==[nets['recovered_clk_i']['bits'][lane]]
                assert cell['connections']['D']==nets['request_q']['bits']+[bits[0]]
            else:
                assert cell['connections']['CLK']==nets['common_clk_i']['bits']
                expected_d='ack_local'if name=='ack_meta_q'else'ack_meta_q'
                assert cell['connections']['D']==nets[expected_d]['bits']
            sync_proof[name]=dict(bits=bits,cell=cell_name,connections=cell['connections'],parameters=cell['parameters'])
        proofs.append(dict(top=INGRESS,epoch_width=ew,status='PASS',counts=counts,
          synchronizer_registers=sync_proof,bundled_data_physical_constraints_qualified=False,
          command=row,sha256=sha(js.read_bytes())))
    return proofs

def run(out):
    m=pins();authorize_native(m);reserved=reservation(m)
    out=Path(out).resolve();assert out.is_relative_to(ROOT/'hw/soc/out')
    out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
      attempt=os.environ['GITHUB_RUN_ATTEMPT'],method_sha256=sha(METHOD.read_bytes()),
      reservation=reserved,simulations=[],hierarchy=[],physical_and_protocol_acceptance=m['physical_and_protocol_acceptance'])
    error=None
    try:
        env,result['toolchain']=shared.runtime(out,('icarus','verilator'))
        vendor=shared.fetch_vendor(out,m['vendor'])
        result['hierarchy']=hierarchy(out,env,vendor)
        own=[(sim,depth,CONTROL if module.endswith('control')else INGRESS,module,None)
          for sim in ('icarus','verilator')for depth in (4,8,32)for module in TESTS]
        old=[(sim,depth,top,module,None)for sim,depth,top,module,mut in shared.matrix()if mut is None]
        mutations=[('icarus',4,CONTROL if mu['module'].endswith('control')else INGRESS,mu['module'],mu)for mu in m['mutations']]
        for sim,depth,top,module,mutation in own+old+mutations:
            label=sim+'-'+module+'-d'+str(depth)+(('-'+mutation['name'])if mutation else '')
            case=out/'simulations'/label;case.mkdir(parents=True)
            source_paths=paths(vendor)if module in TESTS else shared.paths(vendor,top==shared.FRONT)
            if mutation:
                original=RTL/mutation['file'];s=original.read_text()
                assert s.count(mutation['old'])==1
                changed=case/original.name;changed.write_text(s.replace(mutation['old'],mutation['new']))
                source_paths=[changed if p==original else p for p in source_paths]
            build=case/'build';xml=case/'results.xml'
            is_own=module in TESTS
            makefile=BENCH/('Makefile.pcie_training_epoch_ingress'if is_own else'Makefile.pcie_shared_serial_front')
            current_env=dict(env,EPOCH_WIDTH='2')
            args=['make','-f',str(makefile),'SIM='+sim,'TOPLEVEL='+top,'DEPTH='+str(depth),
              'COCOTB_TEST_MODULES='+module,'SIM_BUILD='+str(build),'COCOTB_RESULTS_FILE='+str(xml),
              'VERILOG_SOURCES='+' '.join(map(str,source_paths)),'BUILD_ARGS=-j2','WAVES=0',
              'COCOTB_TEST_FILTER='+('^'+module+r'\.'+mutation['test']+'$'if mutation else '')]
            if is_own:args+=['EPOCH_W=2']
            binary=build/('sim.vvp'if sim=='icarus'else'Vtop')
            row=dict(label=label,simulator=sim,depth=depth,top=top,module=module,mutation=mutation,status='COMPILING')
            result['simulations'].append(row);shared.save(out/'result.json',result)
            print('EPOCH_INGRESS_CASE '+label,flush=True)
            row['compile']=shared.execute(args+[str(binary)],case,'compile',current_env)
            assert row['compile']['returncode']==0 and binary.is_file()and binary.stat().st_size>0,'Compile/setup failure'
            row['compiled_image']=dict(bytes=binary.stat().st_size,sha256=sha(binary.read_bytes()))
            row['simulation']=shared.execute(args+[str(xml)],case,'simulation',current_env)
            assert xml.is_file(),'Missing actual simulation XML'
            log=Path(row['simulation']['stdout']['path']).read_text()+Path(row['simulation']['stderr']['path']).read_text()
            review=xml_review if is_own else shared.xml_review
            row['tests']=review(xml.read_bytes(),module,row['simulation']['returncode'],mutation,log)
            row.update(status='PASS'if mutation is None else'DETECTED_ASSERTION',xml_sha256=sha(xml.read_bytes()))
            shared.save(out/'result.json',result)
        assert len(result['simulations'])==28
        assert sum(t['disposition']=='PASS'for r in result['simulations']for t in r['tests'])==110
        assert sum(t['disposition']=='DETECTED_ASSERTION'for r in result['simulations']for t in r['tests'])==6
        assert len(result['hierarchy'])==4
        result['status']='PASS_EPOCH_INGRESS_110_RTL_6_MUTATIONS_4_HIERARCHIES'
    except BaseException as exc:
        error=exc;result.update(status='FAIL_EPOCH_INGRESS',error=repr(exc),traceback=traceback.format_exc())
    finally:
        try:pins();result['terminal_source_pins_unchanged']=True
        except BaseException as exc:
            result['terminal_pin_error']=repr(exc);result['status']='FAIL_EPOCH_INGRESS';error=error or exc
        result['outputs']=shared.inventory(out);shared.save(out/'result.json',result)
    if error:raise error
    return result

def publish(out,destination):
    import cloud_chunked_results
    import ensure_cloud_tested_source_release as release
    m=pins();authorize_native(m);out=Path(out).resolve();destination=Path(destination).resolve()
    assert out.is_relative_to(ROOT/'hw/soc/out')and out.exists()
    assert not destination.is_relative_to(out)
    destination.mkdir(parents=True,exist_ok=False)
    tag,source=release.context('pcie-training-epoch-ingress-v1',os.environ)
    info=release.api('releases/tags/'+tag)
    proof=release.validate_release(info,release.api('git/ref/tags/'+tag),tag,source)
    assert proof['existing_assets']==[],'Never overwrite or retry a partial publication'
    stem='pcie-training-epoch-ingress-v1'
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
    shared.save(destination/'publication-receipt.json',receipt)
    subprocess.run(['gh','release','upload',tag,str(destination/'publication-receipt.json'),'-R',release.REPO],check=True)
    print(json.dumps(receipt,indent=2))

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--source-controls',action='store_true');g.add_argument('--out')
    g.add_argument('--admit-reservation',action='store_true');g.add_argument('--publish')
    p.add_argument('--destination')
    a=p.parse_args()
    if a.source_controls:
        m=pins();print(json.dumps(dict(status='PASS_SOURCE_PINS_ONLY',source=os.environ['GITHUB_SHA'],
          protected=len(m['protected']),native_executed=False,native_authorized=m['native_authorized'],
          physical_and_protocol_acceptance=m['physical_and_protocol_acceptance']),indent=2))
    elif a.admit_reservation:print(json.dumps(reservation(pins()),indent=2))
    elif a.publish:publish(a.publish,a.destination)
    else:run(a.out)
if __name__=='__main__':main()
