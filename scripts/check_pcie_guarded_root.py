#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit root admission and positive Icarus regression for two guarded PCIe suites."""
import argparse,ast,hashlib,json,os,re,subprocess,traceback
from pathlib import Path
import check_pcie_shared_serial_front as shared
import check_pcie_training_epoch_ingress as epoch
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/pcie-guarded-root-methods.json'
BENCH=shared.BENCH
sha=shared.sha
TESTS={**shared.TESTS,**epoch.TESTS}
SCOPE=dict(full_phy_accepted=False,mainchip_serial_integration=False,physical_acceptance=False,final_setup_hold=False)
EXPECTED={'shared':25,'epoch':30}
def check_manifest(m,raw):
    assert m['schema']=='pcie-guarded-root-regression-v1'
    assert m['scope']==SCOPE and m['expected_positive_tests']==EXPECTED
    assert set(raw)==set(m['protected'])
    for p,h in m['protected'].items():
        assert type(raw[p])is bytes and sha(raw[p])==h,'Root source pin: '+p
    observed=[]
    for name,legacy in m['legacy_manifests'].items():
        original=json.loads(raw[name])
        assert original['protected']==legacy['protected']
        for p,h in original['protected'].items():
            actual=sha(raw[p])
            if actual!=h:
                observed.append((name,p))
                delta=legacy['admitted_root_deltas'][p]
                assert delta['old_sha256']==h and delta['new_sha256']==actual
                if p.endswith('soc_pcie_gen12_raw32_align.v'):
                    b=raw[p]
                    assert b.count(b'`default_nettype none\n')==b.count(b'`default_nettype wire\n')==1
                    reversed_bytes=b.replace(b'`default_nettype none\n',b'',1).replace(b'`default_nettype wire\n',b'',1)
                    assert sha(reversed_bytes)==h,'Only nettype guards admitted'
        assert set(legacy['admitted_root_deltas'])=={p for n,p in observed if n==name}
    assert set(observed)=={
      ('scripts/pcie-shared-serial-front-methods.json','.github/workflows/pcie-gen12-record-cdc-root-controls-cloud.yml'),
      ('scripts/pcie-training-epoch-ingress-methods.json','hw/soc/rtl/pcie/soc_pcie_gen12_raw32_align.v')}
    for module,names in TESTS.items():
        t=ast.parse(raw['hw/soc/tb/cocotb/'+module+'.py'])
        found=[n.name for n in t.body if isinstance(n,ast.AsyncFunctionDef)and any(
          isinstance(d,ast.Call)and isinstance(d.func,ast.Attribute)and isinstance(d.func.value,ast.Name)
          and d.func.value.id=='cocotb'and d.func.attr=='test'for d in n.decorator_list)]
        assert found==names,'Required oracle names changed: '+module
    return m
def pins():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    assert re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA',''))
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==os.environ['GITHUB_SHA']
    m=json.loads(METHOD.read_bytes())
    return check_manifest(m,{p:(ROOT/p).read_bytes()for p in m['protected']})
def cases(suite):
    assert suite in EXPECTED
    if suite=='shared':
        return [(depth,top,module)for sim,depth,top,module,mutation in shared.matrix()if sim=='icarus'and mutation is None]
    return [(depth,epoch.CONTROL if module.endswith('control')else epoch.INGRESS,module)
            for depth in (4,8,32)for module in epoch.TESTS]
def review(raw,module,rc):
    return (epoch.xml_review if module in epoch.TESTS else shared.xml_review)(raw,module,rc)
def binding(module):
    pins();assert module in TESTS
    return True
def counts(result,expected_suite=None):
    m=pins();suite=result['suite'];assert suite in EXPECTED
    if expected_suite is not None:assert suite==expected_suite
    assert result['source']==os.environ['GITHUB_SHA']and result['run']==os.environ['GITHUB_RUN_ID']
    assert result['status']=='PASS_ROOT_GUARDED_PCIE_RTL'and not result['errors']
    assert result['scope']==SCOPE and result['terminal_source_pins_unchanged']is True
    assert result['method_sha256']==sha(METHOD.read_bytes())and result['source_pins']==m['protected']
    rows=result['simulations'];want=cases(suite)
    assert [(r['depth'],r['top'],r['module'])for r in rows]==want
    total=0
    for r in rows:
        assert r['simulator']=='icarus'and r['status']=='PASS'
        assert r['compile']['returncode']==r['simulation']['returncode']==0
        assert r['compiled_image']['bytes']>0
        assert len(r['tests'])==len(TESTS[r['module']])
        assert {x['test']for x in r['tests']}==set(TESTS[r['module']])
        assert all(x['disposition']=='PASS'and x['sim_time_ns']>0 for x in r['tests'])
        total+=len(r['tests'])
    assert total==EXPECTED[suite]
    return total,0,0
def run(out,suite):
    m=pins();out=Path(out).resolve()
    assert out.is_relative_to(ROOT/'hw/soc/out')
    out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',suite=suite,run=os.environ['GITHUB_RUN_ID'],source=os.environ['GITHUB_SHA'],
      method_sha256=sha(METHOD.read_bytes()),source_pins=m['protected'],scope=SCOPE,simulations=[],errors=[])
    primary=None
    try:
        shared.save(out/'result.json',result)
        env,result['toolchain']=shared.runtime(out,('icarus',))
        vendor=shared.fetch_vendor(out,m['vendor'])
        result['vendor']=dict(bytes=vendor.stat().st_size,sha256=sha(vendor.read_bytes()))
        for depth,top,module in cases(suite):
            label=module+'-d'+str(depth);case=out/'simulations'/label;case.mkdir(parents=True)
            own=suite=='epoch'
            paths=epoch.paths(vendor)if own else shared.paths(vendor,top==shared.FRONT)
            assert all(p==vendor or str(p.relative_to(ROOT))in m['protected']for p in paths)
            mk=BENCH/('Makefile.pcie_training_epoch_ingress'if own else'Makefile.pcie_shared_serial_front')
            build=case/'build';xml=case/'results.xml';binary=build/'sim.vvp'
            args=['make','-f',str(mk),'SIM=icarus','TOPLEVEL='+top,'DEPTH='+str(depth),
              'COCOTB_TEST_MODULES='+module,'SIM_BUILD='+str(build),'COCOTB_RESULTS_FILE='+str(xml),
              'VERILOG_SOURCES='+' '.join(map(str,paths)),'BUILD_ARGS=-j2','WAVES=0','COCOTB_TEST_FILTER=']
            current_env=dict(env)
            if own:args+=['EPOCH_W=2'];current_env['EPOCH_WIDTH']='2'
            row=dict(label=label,simulator='icarus',depth=depth,top=top,module=module,status='COMPILING')
            result['simulations'].append(row);shared.save(out/'result.json',result)
            print('ROOT_GUARDED_CASE '+label,flush=True)
            row['compile']=shared.execute(args+[str(binary)],case,'compile',current_env)
            assert row['compile']['returncode']==0 and binary.is_file()and binary.stat().st_size>0,'Compile/setup failure'
            row['compiled_image']=dict(bytes=binary.stat().st_size,sha256=sha(binary.read_bytes()))
            row['status']='SIMULATING';shared.save(out/'result.json',result)
            row['simulation']=shared.execute(args+[str(xml)],case,'simulation',current_env)
            assert xml.is_file(),'Missing current XML'
            row['tests']=review(xml.read_bytes(),module,row['simulation']['returncode'])
            row.update(status='PASS',xml_sha256=sha(xml.read_bytes()))
            shared.save(out/'result.json',result)
        result['status']='PASS_ROOT_GUARDED_PCIE_RTL'
    except BaseException as error:
        primary=error;result.update(status='FAIL_ROOT_GUARDED_PCIE_RTL',error=repr(error),traceback=traceback.format_exc())
    finally:
        try:pins();result['terminal_source_pins_unchanged']=True
        except BaseException as error:
            result['errors'].append(dict(phase='terminal-pins',error=repr(error)));result['status']='FAIL_ROOT_GUARDED_PCIE_RTL'
            primary=primary or error
        result['outputs']=shared.inventory(out);shared.save(out/'result.json',result)
    if primary:raise primary
    try:counts(result,suite)
    except BaseException as error:
        result.update(status='FAIL_ROOT_GUARDED_PCIE_RTL',count_error=repr(error));shared.save(out/'result.json',result);raise
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--suite',choices=list(EXPECTED));p.add_argument('--out',type=Path)
    p.add_argument('--counts',type=Path);p.add_argument('--bind-module')
    a=p.parse_args()
    if a.bind_module:binding(a.bind_module);return
    if a.counts:print(*counts(json.loads(a.counts.read_bytes()),a.suite));return
    assert a.suite and a.out
    run(a.out,a.suite)
if __name__=='__main__':main()
