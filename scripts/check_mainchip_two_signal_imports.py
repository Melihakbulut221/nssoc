#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual isolated imports and exact original module-level JSON data readers."""
import ast,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/mainchip-two-signal-repair-methods.json'
DATA={
 'docs/evidence/cloud-refined-load-hold-targets-20261016.json':('8eabcf9f3e0ace7ec6240474f1a5a0758c31f0350d559c5ef70a64b43572342b','refined_hold_targets.py',31),
 'docs/evidence/route146-all-reachable-branch-recipe-20261016.json':('12795513c5d9694eaae9daed4ca6b2c6209a42040c1ff8bdba9a23f249e8b31a','branch_hold_targets.py',32),
 'docs/evidence/cloud-measured-load-hold-conflicts-20261016.json':('55046b17b57dc82eeecbd26783ac62241bde725fce3eab21f9f271dd9a76565b','measured_hold_targets.py',30)}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(root,name):
    p=PurePosixPath(name)
    assert not p.is_absolute()and str(p)==name and p.parts and all(x not in ('','.','..')for x in p.parts)
    result=root.joinpath(*p.parts)
    assert result.is_file()
    for part in [result,*result.parents]:
        assert not part.is_symlink()
        if part==root:break
    return result.read_bytes()
def initial(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
    for child in ast.iter_child_nodes(node):yield from initial(child)
def closure(root,m):
    todo=list(m['import_time_roots']);found={};edges=[]
    standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)
    while todo:
        name=todo.pop()
        if name in found:continue
        raw=read(root,name);assert name in m['protected']and sha(raw)==m['protected'][name]
        found[name]=sha(raw)
        for node in initial(ast.parse(raw)):
            if isinstance(node,ast.ImportFrom):assert node.level==0
            for module in ([a.name for a in node.names]if isinstance(node,ast.Import)else[node.module]):
                options=[d+'/'+module.replace('.','/')+'.py'for d in ('scripts','hw/soc/flow')]
                local=[p for p in options if(root/p).exists()]
                if local:assert len(local)==1;todo.extend(local);kind='repository'
                else:assert module.split('.')[0]in standard,('Unknown import',module);kind='stdlib'
                edges.append(dict(source=name,module=module,kind=kind))
    assert sorted(found)==m['import_time_modules']
    for p,(digest,_,_)in DATA.items():assert m['protected'][p]==sha(read(root,p))==digest
    return dict(modules=found,edges=edges,data={p:v[0]for p,v in DATA.items()},external_import_time_modules=[])
PROGRAM="""import hashlib,importlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();pins=json.loads(sys.argv[2])
sys.path[:0]=[str(root/'scripts'),str(root/'hw/soc/flow')]
observed={}
for relative,digest in pins.items():
    name=Path(relative).stem;module=importlib.import_module(name)
    path=Path(module.__file__).resolve()
    assert path==root/relative
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    observed[relative]=digest
print(json.dumps(observed,sort_keys=True))
"""
def run(root,pins):
    return subprocess.run([sys.executable,'-I','-B','-c',PROGRAM,str(root),json.dumps(pins)],
        cwd=root,capture_output=True,text=True,check=False,timeout=60)
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads(read(ROOT,str(METHOD.relative_to(ROOT))))
    assert m['source_controls_authorized']is True
    proof=closure(ROOT,m);positive=[];refused=[]
    with tempfile.TemporaryDirectory(prefix='two-signal-import-')as temp:
        root=Path(temp)
        for p in set(proof['modules'])|set(DATA):
            target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(read(ROOT,p))
        result=run(root,proof['modules'])
        assert result.returncode==0,(result.stdout,result.stderr)
        assert json.loads(result.stdout)==proof['modules']
        positive.append('actual_all_module_initialization_in_isolated_copied_root')
        for path,(digest,owner,line)in DATA.items():
            target=root/path;raw=target.read_bytes();target.unlink()
            missing=run(root,proof['modules'])
            assert missing.returncode!=0 and 'FileNotFoundError'in missing.stderr
            assert Path(path).name in missing.stderr and owner in missing.stderr and 'line '+str(line)in missing.stderr
            refused.append(dict(name='actual_missing:'+path,stderr=missing.stderr))
            target.write_bytes(raw+b' ')
            bad=run(root,proof['modules'])
            assert bad.returncode!=0 and bad.stderr.rstrip().endswith('AssertionError')
            assert owner in bad.stderr
            refused.append(dict(name='actual_tampered:'+path,stderr=bad.stderr))
            target.write_bytes(raw)
        path='scripts/wait_cloud_tested_source_release.py';raw=(root/path).read_bytes();(root/path).unlink()
        missing=run(root,proof['modules'])
        assert missing.returncode!=0 and 'ModuleNotFoundError'in missing.stderr and 'wait_cloud_tested_source_release'in missing.stderr
        refused.append(dict(name='actual_missing_waiter',stderr=missing.stderr));(root/path).write_bytes(raw)
        again=run(root,proof['modules'])
        assert again.returncode==0 and json.loads(again.stdout)==proof['modules']
        assert not list(root.rglob('__pycache__'))
        positive.append('complete_pristine_reimport_after_real_mutations')
    assert len(positive)==2 and len(refused)==7
    return dict(status='PASS_ACTUAL_TWO_SIGNAL_IMPORT_DATA_CLOSURE',positive=positive,rejected=refused,
        closure=proof,authored_CAD_executed=False,prior_archive_accessed=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
