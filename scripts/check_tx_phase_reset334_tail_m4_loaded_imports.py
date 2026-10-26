#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual isolated imports with original module-level data readers; no CAD imports."""
import ast,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-loaded-methods.json'
DATA={'docs/evidence/cloud-refined-load-hold-targets-20261016.json': '8eabcf9f3e0ace7ec6240474f1a5a0758c31f0350d559c5ef70a64b43572342b', 'docs/evidence/route146-all-reachable-branch-recipe-20261016.json': '12795513c5d9694eaae9daed4ca6b2c6209a42040c1ff8bdba9a23f249e8b31a', 'docs/evidence/cloud-measured-load-hold-conflicts-20261016.json': '55046b17b57dc82eeecbd26783ac62241bde725fce3eab21f9f271dd9a76565b'}
ROOTS=('scripts/cloud_tx_phase_reset334_tail_m4_loaded.py', 'scripts/check_tx_phase_reset334_tail_m4_loaded.py', 'scripts/check_tx_phase_reset334_tail_m4_loaded_publication.py', 'scripts/tx_phase_reset334_tail_m4_loaded_adapter.py', 'scripts/tx_phase_reset334_tail_m4_loaded_admission.py', 'scripts/cloud_tx_phase_reset334_zero_op.py')
EXTERNAL={'numpy':'2.3.3','networkx':'3.4.2'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def immediate(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
    for child in ast.iter_child_nodes(node):yield from immediate(child)
def closure(root,pins):
    todo=list(ROOTS);seen={};edges=[]
    standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)
    while todo:
        path=todo.pop()
        if path in seen:continue
        full=root/path;assert path in pins and full.is_file()and not full.is_symlink(),path
        assert digest(full)==pins[path];seen[path]=pins[path]
        for node in immediate(ast.parse(full.read_bytes())):
            if isinstance(node,ast.ImportFrom):assert node.level==0
            for module in ([a.name for a in node.names]if isinstance(node,ast.Import)else[node.module]):
                assert module
                candidates=[d+'/'+module.replace('.','/')+'.py'for d in ('scripts','hw/soc/flow')]
                local=[p for p in candidates if(root/p).exists()]
                if local:
                    assert len(local)==1;todo.append(local[0]);kind='repository'
                else:
                    top=module.split('.')[0]
                    if top in standard:kind='stdlib'
                    else:
                        import importlib.metadata
                        assert top in EXTERNAL and importlib.metadata.version(top)==EXTERNAL[top],('Unresolved import',path,module)
                        kind='pinned-third-party'
                edges.append(dict(source=path,module=module,kind=kind))
    for path,h in DATA.items():assert path in pins and pins[path]==h and digest(root/path)==h
    return dict(modules=seen,edges=edges,import_time_data=DATA,external_import_time_modules=EXTERNAL)
PROGRAM="""import importlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(root/'scripts'),str(root/'hw/soc/flow')]
names=json.loads(sys.argv[2]);loaded={}
for name in names:
    mod=importlib.import_module(name)
    assert Path(mod.__file__).resolve().is_relative_to(root)
    loaded[name]=str(Path(mod.__file__).resolve().relative_to(root))
print(json.dumps(loaded,sort_keys=True))
"""
def run(root,names):
    return subprocess.run([sys.executable,'-I','-B','-c',PROGRAM,str(root),json.dumps(names)],
                          cwd=root,capture_output=True,text=True,timeout=60,check=False)
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert digest(ROOT/p)==h,p
    proof=closure(ROOT,m['protected']);assert set(proof['modules'])==set(m['initial_repository_modules'])
    positive=[];rejected=[]
    # Source dependencies may read other protected Python files at module initialization.
    # Copy the full declared deferred source closure as well; no original-repo path is on sys.path.
    copy_names=set(m['required_repository_modules'])|set(proof['modules'])|set(DATA)
    names=[Path(p).stem for p in ROOTS]
    with tempfile.TemporaryDirectory(prefix='tail-m4-loaded-isolated-import-')as folder:
        root=Path(folder)
        for p in sorted(copy_names):
            assert p in m['protected']
            dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/p).read_bytes())
        result=run(root,names);assert result.returncode==0,(result.stdout,result.stderr)
        loaded=json.loads(result.stdout);assert set(loaded)==set(names)
        positive.append(dict(name='actual_full_isolated_module_initialization',loaded=loaded))
        # Each actual original reader must fail, not an artificial pre-copy check.
        for path,h in DATA.items():
            target=root/path;raw=target.read_bytes();assert digest(target)==h
            target.unlink();missing=run(root,names)
            assert missing.returncode!=0 and Path(path).name in missing.stderr and 'FileNotFoundError'in missing.stderr
            rejected.append(dict(name='actual_missing_data:'+path,stderr=missing.stderr))
            target.write_bytes(raw+b' ');bad=run(root,names)
            assert bad.returncode!=0 and 'AssertionError'in bad.stderr
            # Original source file and actual module-level hash assertion are in traceback.
            owner={'cloud-refined-load-hold-targets-20261016.json':'refined_hold_targets.py',
                   'route146-all-reachable-branch-recipe-20261016.json':'branch_hold_targets.py',
                   'cloud-measured-load-hold-conflicts-20261016.json':'measured_hold_targets.py'}[Path(path).name]
            assert owner in bad.stderr
            rejected.append(dict(name='actual_tampered_data:'+path,stderr=bad.stderr))
            target.write_bytes(raw)
        waiter=root/'scripts/wait_cloud_tested_source_release.py';raw=waiter.read_bytes();waiter.unlink()
        missing=run(root,names);assert missing.returncode!=0 and 'wait_cloud_tested_source_release'in missing.stderr
        rejected.append(dict(name='actual_missing_waiter',stderr=missing.stderr));waiter.write_bytes(raw)
        positive.append(dict(name='pristine_reimport_after_all_mutations',loaded=json.loads(run(root,names).stdout)))
        assert not list(root.rglob('__pycache__'))
    assert len(positive)==2 and len(rejected)==7
    return dict(status='PASS_TAIL_M4_LOADED_ACTUAL_IMPORT_AND3_DATA_CLOSURE',closure=proof,positive=positive,rejected=rejected,
                actual_imports_executed=True,authored_native_code_executed=False,archive_downloaded=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
