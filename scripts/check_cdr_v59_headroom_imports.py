#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed import-time repository closure and real isolated import fixtures."""
import ast,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-headroom-readback-methods.json'
ROOTS=['scripts/cloud_cdr_v59_headroom_readback.py','scripts/check_cdr_v59_headroom_readback.py',
 'scripts/check_cdr_v59_headroom_publication.py','scripts/check_cdr_v59_headroom_imports.py']
WAITER='wait_cloud_tested_source_release'
GUARD='ensure_cloud_tested_source_release'
WAITER_SHA='4c749e3f6f072c053f2dd5d45e9ad4f8cb2eca1e7c7b1cf480177f637fb04b73'
# The sole explicit installed dependency is the already-used pinned NumPy.
# Missing repository imports cannot fall through to third-party classification.
INSTALLED_ALLOWLIST={'numpy':'2.3.3'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def immediate_imports(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
    for child in ast.iter_child_nodes(node):yield from immediate_imports(child)
def closure(root,protected,roots):
    root=Path(root);queue=list(roots);seen={};edges=[]
    standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)
    while queue:
        name=queue.pop()
        if name in seen:continue
        path=root/name
        assert path.is_file()and not path.is_symlink()and name in protected,name
        assert sha(path)==protected[name],name
        seen[name]=protected[name]
        for node in immediate_imports(ast.parse(path.read_bytes())):
            if isinstance(node,ast.ImportFrom):assert node.level==0,'Relative import requires explicit repository mapping'
            mods=[item.name for item in node.names]if isinstance(node,ast.Import)else[node.module]
            for module in mods:
                assert module
                relative='scripts/'+module.replace('.','/')+'.py';target=root/relative
                if target.exists()or target.is_symlink():
                    assert target.is_file()and not target.is_symlink()and relative in protected,relative
                    assert sha(target)==protected[relative],relative
                    queue.append(relative);kind='protected_repository'
                elif module.split('.')[0]in standard:kind='standard_library'
                else:
                    assert module in INSTALLED_ALLOWLIST,'Unresolved repository or undeclared external import: '+module
                    kind='explicit_installed_allowlist'
                edges.append(dict(source=name,line=node.lineno,module=module,kind=kind))
    return dict(files=seen,edges=edges,installed_allowlist=INSTALLED_ALLOWLIST,
      scope='Transitive module-initialization imports; deferred function imports are not executed or qualified')
def child(directory,program,*args):
    command=[sys.executable,'-I','-B','-c',program,str(directory),*args]
    p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert len(p.stdout)<16384 and len(p.stderr)<16384
    return dict(returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode(),
      stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest())
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    m=json.loads((ROOT/METHOD).read_bytes());assert m['source_controls_authorized']is True
    for name,digest in m['protected'].items():assert sha(ROOT/name)==digest,name
    assert sha(ROOT/'scripts'/str(WAITER+'.py'))==WAITER_SHA
    proof=closure(ROOT,m['protected'],ROOTS);positives=['actual_repository_import_time_closure'];rejected=[];processes={}
    stage=(ROOT/'scripts/cloud_cdr_v59_headroom_readback.py').read_text()
    nodes=[n for n in ast.parse(stage).body if isinstance(n,ast.Import)and any(x.name==WAITER for x in n.names)]
    assert len(nodes)==1 and len(nodes[0].names)==1
    statement=ast.get_source_segment(stage,nodes[0]);assert statement=='import wait_cloud_tested_source_release as waiter'
    full_program="import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import cloud_cdr_v59_headroom_readback as w;import numpy;assert numpy.__version__=='2.3.3';assert Path(w.waiter.__file__).resolve()==Path(sys.argv[1])/('wait_cloud_tested_source_release.py');print(json.dumps(dict(stage_imported=True,numpy_version=numpy.__version__,waiter=str(Path(w.waiter.__file__).resolve()))))"
    actual=child(ROOT/'scripts',full_program);assert actual['returncode']==0 and not actual['stderr'],actual
    assert json.loads(actual['stdout'])['stage_imported']is True and json.loads(actual['stdout'])['numpy_version']=='2.3.3'
    processes['actual_stage']=actual;positives.append('actual_full_stage_import')
    fixture_program="import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);scope={};exec(compile(sys.argv[2],'<exact-stage-waiter-import>','exec'),scope);assert Path(scope['waiter'].__file__).resolve()==Path(sys.argv[1])/('wait_cloud_tested_source_release.py');print(json.dumps(dict(exact_statement_imported=True)))"
    def refuse(label,fn):
        try:fn()
        except(AssertionError,FileNotFoundError):rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    with tempfile.TemporaryDirectory(prefix='cdr-v59-headroom-real-import-')as temp:
        root=Path(temp);scripts=root/'scripts';scripts.mkdir()
        for name in (WAITER,GUARD):shutil.copyfile(ROOT/'scripts'/str(name+'.py'),scripts/str(name+'.py'))
        entry=scripts/'entry.py';entry.write_text(statement+'\n')
        pins={'scripts/'+p.name:sha(p)for p in scripts.iterdir()}
        small=closure(root,pins,['scripts/entry.py']);assert set(small['files'])==set(pins)
        positives.append('real_fixture_transitive_closure')
        positive=child(scripts,fixture_program,statement)
        assert positive['returncode']==0 and not positive['stderr']and json.loads(positive['stdout'])['exact_statement_imported'],positive
        processes['exact_statement_positive']=positive;positives.append('exact_waiter_statement_fixture')
        waiter=scripts/(WAITER+'.py');guard=scripts/(GUARD+'.py')
        saved=waiter.read_bytes();waiter.unlink()
        refuse('missing_repository_waiter',lambda:closure(root,pins,['scripts/entry.py']))
        missing=child(scripts,fixture_program,statement)
        assert missing['returncode']!=0 and "ModuleNotFoundError: No module named '"+WAITER+"'"in missing['stderr']
        assert not missing['stdout'];processes['missing_waiter']=missing;rejected.append('actual_missing_waiter_import')
        waiter.write_bytes(saved)
        raw=guard.read_bytes();guard.unlink()
        refuse('missing_transitive_guard',lambda:closure(root,pins,['scripts/entry.py']))
        missing=child(scripts,fixture_program,statement)
        assert missing['returncode']!=0 and "ModuleNotFoundError: No module named '"+GUARD+"'"in missing['stderr']
        assert not missing['stdout'];processes['missing_guard']=missing;rejected.append('actual_missing_transitive_import')
        guard.write_bytes(raw)
        absent=dict(pins);del absent['scripts/'+WAITER+'.py']
        refuse('unprotected_waiter',lambda:closure(root,absent,['scripts/entry.py']))
        waiter.write_bytes(saved+b'\n')
        refuse('changed_waiter',lambda:closure(root,pins,['scripts/entry.py']));waiter.unlink()
        waiter.symlink_to(ROOT/'scripts'/str(WAITER+'.py'))
        refuse('symlink_waiter',lambda:closure(root,pins,['scripts/entry.py']));waiter.unlink();waiter.write_bytes(saved)
        entry.write_text(statement+'\nimport absent_cdr_repository_fixture\n')
        altered=dict(pins);altered['scripts/entry.py']=sha(entry)
        refuse('unknown_external_not_implicitly_allowed',lambda:closure(root,altered,['scripts/entry.py']))
        entry.write_text(statement+'\n')
        (scripts/'json.py').write_text('# unprotected stdlib shadow\n')
        refuse('unprotected_stdlib_shadow',lambda:closure(root,pins,['scripts/entry.py']))
    assert len(positives)==4 and len(rejected)==9 and len(set(rejected))==9
    return dict(status='PASS_CURRENT_V59_HEADROOM_IMPORT_CLOSURE_NOT_CAPTURE_ANALYSIS',
      positives=positives,rejected=rejected,closure=proof,actual_process_results=processes,
      exact_waiter_sha256=WAITER_SHA,source_controls_only=True,
      preparation_executed=False,simulation_executed=False,prior_archive_downloaded=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
