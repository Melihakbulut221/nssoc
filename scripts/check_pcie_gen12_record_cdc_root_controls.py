#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for exact Gen12 root handoff; fixtures do not simulate RTL."""
import ast,copy,json,os,subprocess,sys,tempfile
from pathlib import Path
import check_pcie_gen12_record_cdc_root as c

def controls():
    method,original=c.pins();positive={};rejected={}
    def refuse(name,fn,kind=AssertionError):
        try:fn()
        except kind as error:rejected[name]=dict(type=type(error).__name__,error=str(error))
        else:raise AssertionError('Accepted '+name)
    def xml(top):
        import xml.etree.ElementTree as E
        tree=E.Element('testsuite')
        for name in c.TESTS[top]:
            E.SubElement(tree,'testcase',name=name,classname='test_'+top,
              file=str(c.BENCH/('test_'+top+'.py')),sim_time_ns='1.25')
        return tree
    def raw(tree):return c.ET.tostring(tree)
    for top in c.TESTS:
        tree=xml(top);assert len(c.xml_review(raw(tree),top,0))==len(c.TESTS[top])
        positive['xml-'+top]=True
    top=next(iter(c.TESTS));base=xml(top)
    mutants={}
    a=copy.deepcopy(base);a.remove(a[0]);mutants['missing-test']=a
    a=copy.deepcopy(base);a.append(copy.deepcopy(a[0]));mutants['extra-test']=a
    a=copy.deepcopy(base);a[1].set('name',a[0].get('name'));mutants['duplicate-test']=a
    a=copy.deepcopy(base);a[0].set('classname','wrong');mutants['wrong-module']=a
    a=copy.deepcopy(base);a[0].set('file','/wrong.py');mutants['wrong-file']=a
    a=copy.deepcopy(base);a[0].set('sim_time_ns','0');mutants['zero-simulation']=a
    a=copy.deepcopy(base);a[0].set('sim_time_ns','nan');mutants['nonfinite-time']=a
    a=copy.deepcopy(base);c.ET.SubElement(a[0],'skipped');mutants['skipped']=a
    a=copy.deepcopy(base);c.ET.SubElement(a[0],'failure');mutants['failure']=a
    a=copy.deepcopy(base);c.ET.SubElement(a[0],'error');mutants['error']=a
    for name,a in mutants.items():refuse('xml-'+name,lambda a=a:c.xml_review(raw(a),top,0))
    refuse('xml-nonzero-exit',lambda:c.xml_review(raw(base),top,7))
    refuse('xml-doctype',lambda:c.xml_review(b'<!DOCTYPE x>'+raw(base),top,0))
    vendor=b'module axis_async_fifo;\nendmodule\n'
    record=dict(bytes=len(vendor),sha256=c.sha(vendor),
      git_blob_sha=c.hashlib.sha1(b'blob '+str(len(vendor)).encode()+b'\0'+vendor).hexdigest())
    c.vendor_admission(vendor,record);positive['vendor-admission-synthetic']=True
    refuse('vendor-byte',lambda:c.vendor_admission(vendor+b' ',record))
    bad=dict(record,sha256='0'*64);refuse('vendor-digest',lambda:c.vendor_admission(vendor,bad))
    bad=dict(record,git_blob_sha='0'*40);refuse('vendor-git-blob',lambda:c.vendor_admission(vendor,bad))
    duplicated=vendor+vendor
    duplicated_record=dict(bytes=len(duplicated),sha256=c.sha(duplicated),
      git_blob_sha=c.hashlib.sha1(b'blob '+str(len(duplicated)).encode()+b'\0'+duplicated).hexdigest())
    refuse('vendor-duplicate-module',lambda:c.vendor_admission(duplicated,duplicated_record))
    for sims in [('icarus',),('icarus','verilator')]:
        expected=6*len(sims);assert len(c.matrix(sims,(4,8,32)))==expected
        positive['matrix-'+str(len(sims))]=True
    refuse('missing-depth',lambda:c.matrix(('icarus',),(4,32)))
    refuse('unreviewed-simulator',lambda:c.matrix(('other',),(4,8,32)))
    refuse('duplicate-simulator',lambda:c.matrix(('icarus','icarus'),(4,8,32)))
    with tempfile.TemporaryDirectory(prefix='gen12-root-controls-')as td:
        work=Path(td)
        binary=work/'binary';binary.write_bytes(b'compiled-fixture')
        c.compile_admission(0,binary);positive['compile-admission']=True
        refuse('compile-exit',lambda:c.compile_admission(3,binary))
        refuse('compile-missing',lambda:c.compile_admission(0,work/'missing'))
        binary.write_bytes(b'');refuse('compile-empty',lambda:c.compile_admission(0,binary))
        env=dict(os.environ)
        actual=c.execute([sys.executable,'-c','print("control-output")'],work/'command','success',env,30)
        assert actual['returncode']==0 and Path(actual['stdout']['path']).read_text()=='control-output\n'
        failed=c.execute([sys.executable,'-c','import sys;sys.stderr.write("control-failure");sys.exit(7)'],work/'command','failure',env,30)
        assert failed['returncode']==7 and Path(failed['stderr']['path']).read_text()=='control-failure'
        positive['actual-command-streams-and-returncode']=True
        for sims in [('icarus',),('icarus','verilator')]:
            rows=[]
            for sim,depth,t in c.matrix(sims,(4,8,32)):
                rows.append(dict(label=sim+'-'+t+'-d'+str(depth),simulator=sim,depth=depth,top=t,status='PASS',
                  compile=dict(returncode=0),simulation=dict(returncode=0),
                  tests=[dict(test=n,disposition='PASS')for n in c.TESTS[t]]))
            record=dict(status='PASS_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL',terminal_source_pins_unchanged=True,
              errors=[],simulations=rows,expected_invocations=len(rows),expected_tests=33*len(sims))
            path=work/'counts.json';c.save(path,record);assert c.counts(path)==(33*len(sims),0,0)
            positive['counts-'+str(len(sims))]=True
        for name,change in [
          ('result-driver-failed',lambda r:r.update(status='FAIL_ROOT_GEN12_RECORD_CDC_FOCUSED_RTL')),
          ('result-compile-failed',lambda r:r['simulations'][0]['compile'].update(returncode=7)),
          ('result-skipped',lambda r:r['simulations'][0]['tests'][0].update(disposition='FILTERED_NOT_EXECUTED')),
          ('result-source-changed',lambda r:r.update(terminal_source_pins_unchanged=False)),
          ('result-duplicate-label',lambda r:r['simulations'][1].update(label=r['simulations'][0]['label'])),
          ('result-missing-test',lambda r:r['simulations'][0]['tests'].pop()),
          ('result-wrong-matrix',lambda r:r['simulations'][0].update(depth=128))]:
            bad=copy.deepcopy(record);change(bad);c.save(path,bad)
            refuse(name,lambda:c.counts(path))
        shell=shell_controls(work/'shell')
    assert len(positive)==9 and len(rejected)==29 and len(shell)==7
    return dict(status='PASS_ROOT_GEN12_SOURCE_AND_HANDOFF_CONTROLS_NO_RTL',original=original,
      positive=positive,rejected=rejected,shell=shell,simulations_executed=False,
      synthesis_executed=False,compiled_fault_campaign_executed=False,terminal_pins=c.pins()[0]['protected'])

def shell_controls(work):
    work.mkdir();original=(c.ROOT/'scripts/run_cocotb.sh').read_text()
    helpers=r'''import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
mode=(root/'mode').read_text()
with (root/'calls.jsonl').open('a')as f:f.write(json.dumps(sys.argv[1:])+'\n')
if '--bind-module'in sys.argv:
 if mode=='binding-refusal'and sys.argv[-1]=='test_soc_pcie_gen12_recovered_records_v1':sys.exit(4)
 sys.exit(0)
if '--counts'in sys.argv:
 if mode=='counts-refusal':sys.exit(5)
 print('32 0 0'if mode=='wrong-count'else'33 0 0');sys.exit(0)
out=Path(sys.argv[sys.argv.index('--out')+1]);out.mkdir(parents=True)
(out/'result.json').write_text('{}')
sys.exit(7 if mode=='driver-failure'else 0)
'''
    maker=r'''#!/usr/bin/env python3
import sys
from pathlib import Path
p=Path.cwd()
if 'clean'in sys.argv:sys.exit(0)
mk=sys.argv[sys.argv.index('-f')+1]
if mk=='Makefile.gen12_record_cdc':sys.exit(17)
(p/'results_other.xml').write_text('<testsuite><testcase name="other" classname="test_other"/></testsuite>')
root=p.parents[3]
sys.exit(9 if (root/'mode').read_text()=='other-failure'else 0)
'''
    branch='''    if [ "$name" = "gen12_record_cdc" ]; then
        run_gen12_record_cdc || suite_fail=$((suite_fail + 1))
        return
    fi
'''
    assert original.count(branch)==1
    outcomes={}
    for index,mode in enumerate(('success','driver-failure','wrong-count','counts-refusal','binding-refusal','other-failure','dispatch-removed')):
        root=work/str(index);scripts=root/'scripts';bench=root/'hw/soc/tb/cocotb'
        scripts.mkdir(parents=True);bench.mkdir(parents=True)
        text=original.replace(branch,'',1)if mode=='dispatch-removed'else original
        (scripts/'run_cocotb.sh').write_text(text)
        (scripts/'check_pcie_gen12_record_cdc_root.py').write_text(helpers)
        (scripts/'cocotb_results.py').write_bytes((c.ROOT/'scripts/cocotb_results.py').read_bytes())
        (root/'mode').write_text(mode)
        (bench/'Makefile.gen12_record_cdc').write_text('COCOTB_TEST_MODULES := test_$(TOPLEVEL)\n')
        for top in c.TESTS:(bench/('test_'+top+'.py')).write_text('# Explicit synthetic shell reachability fixture\n')
        (bench/'Makefile.other').write_text('COCOTB_TEST_MODULES := test_other\n')
        (bench/'test_other.py').write_text('# Explicit synthetic existing-suite fixture\n')
        bins=root/'bin';bins.mkdir();(bins/'make').write_text(maker);(bins/'make').chmod(0o755)
        env=dict(os.environ,PY=sys.executable,PATH=str(bins)+':'+os.environ['PATH'])
        p=subprocess.run(['bash',str(scripts/'run_cocotb.sh')],cwd=root,env=env,capture_output=True,text=True,timeout=30)
        calls=[json.loads(s)for s in(root/'calls.jsonl').read_text().splitlines()]
        bound={a[-1]for a in calls if '--bind-module'in a}
        assert bound=={'test_'+top for top in c.TESTS},(mode,bound,p.stdout,p.stderr)
        invoked=[a for a in calls if '--out'in a]
        assert len(invoked)==(0 if mode=='dispatch-removed'else 1),(mode,calls)
        if invoked:
            assert invoked[0][-6:]==['--simulators','icarus','--depths','4','8','32'],invoked
        if mode=='success':
            assert p.returncode==0 and 'cocotb: 34 passed, 0 failed, 0 suite(s) not clean, 0 skipped'in p.stdout,(p.stdout,p.stderr)
        else:
            assert p.returncode!=0,(mode,p.stdout,p.stderr)
            if mode=='binding-refusal':assert 'UNREACHED cocotb test modules'in p.stdout
            if mode=='other-failure':assert 'NOT CLEAN (make rc=9)'in p.stdout
        outcomes[mode]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,actual_calls=calls,
          synthetic_helper_and_make=True,actual_generic_runner=True)
    return outcomes

if __name__=='__main__':
    result=controls();print(json.dumps(result,indent=2,allow_nan=False))
