#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute repeated read-only CDR source validators once per immutable invocation.

This never caches a native simulation or a physical/electrical result. Failed
calls are never cached. Every distinct zero-argument source validator executes.
The audit guard prohibits source writes, subprocesses, network and environment
mutation; every repository file read is hashed before and after validation.
"""
import ast,copy,functools,hashlib,importlib,importlib.abc,importlib.machinery,inspect,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
    with open(p,'rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(entry):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert entry=='check_cdr_sampler_settling_v32_streamed_sources'
    sys.dont_write_bytecode=True
    state=dict(active=True,busy=False)
    files={};calls={};executed={};stack=[];edges=set();cache={}
    def audit(event,args):
        if not state['active']or state['busy']:return
        if event in ('subprocess.Popen','os.system','socket.connect','socket.bind','os.putenv','os.unsetenv',
                     'os.remove','os.rename','os.rmdir','os.mkdir','os.symlink','os.link','os.truncate'):
            raise AssertionError(('Source validation must be read-only',event))
        if event!='open':return
        name,mode,flags=args
        if not isinstance(name,(str,bytes,os.PathLike)):return
        assert not(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)),('Write during source validation',str(name))
        state['busy']=True
        try:
            p=Path(os.fsdecode(name)).resolve()
            if p.is_relative_to(ROOT)and p.is_file()and str(p)not in files:files[str(p)]=digest(p)
        finally:state['busy']=False
    sys.addaudithook(audit)
    def wrap(module):
        fn=getattr(module,'check',None)
        if fn is None:return
        assert inspect.isfunction(fn)and not inspect.signature(fn).parameters
        tree=ast.parse(inspect.getsource(fn))
        assert not any(isinstance(n,(ast.Global,ast.Nonlocal))for n in ast.walk(tree))
        # These validators may update local structures, never module/object state.
        assert not any(isinstance(n,ast.Attribute)and isinstance(n.ctx,ast.Store)for n in ast.walk(tree))
        path=Path(fn.__code__.co_filename).resolve()
        assert path.is_relative_to(ROOT/'scripts')and path.name==module.__name__+'.py'
        key=module.__name__
        @functools.wraps(fn)
        def checked():
            calls[key]=calls.get(key,0)+1
            if stack:edges.add((stack[-1],key))
            assert key not in stack,('Recursive validator cycle',key)
            if key in cache:return copy.deepcopy(cache[key])
            stack.append(key)
            try:
                result=fn()
                assert result is None,('Unsupported stateful validator return',key)
                cache[key]=result
                executed[key]=dict(source=path.relative_to(ROOT).as_posix(),sha256=digest(path))
                return result
            finally:assert stack.pop()==key
        module.check=checked
    class Loader(importlib.abc.Loader):
        def __init__(self,original):self.original=original
        def create_module(self,spec):return self.original.create_module(spec)if hasattr(self.original,'create_module')else None
        def exec_module(self,module):
            self.original.exec_module(module)
            wrap(module)
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if not(fullname.startswith('check_cdr_')and fullname.endswith('_sources')):return None
            spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
            assert spec is not None and spec.loader is not None
            spec.loader=Loader(spec.loader)
            return spec
    finder=Finder();sys.meta_path.insert(0,finder)
    started=time.monotonic();result=dict(status='RUNNING',entry=entry,full_phy_accepted=False,native_started=False)
    try:
        assert entry not in sys.modules,'Use a fresh invocation with no previously bound validators'
        importlib.import_module(entry).check()
        assert not stack
        assert all(digest(p)==h for p,h in files.items()),'Repository input changed during validation'
        assert set(calls)==set(executed)==set(cache)
        assert all(v>=1 for v in calls.values())
        result.update(status='PASS_EVERY_DISTINCT_READ_ONLY_SOURCE_VALIDATOR_ON_IMMUTABLE_INPUTS',
            calls=calls,executed=executed,dependency_edges=sorted(edges),
            every_distinct_validator_executed=True,failed_results_cached=False,
            protected_read_files={str(Path(p).relative_to(ROOT)):h for p,h in files.items()},
            all_read_files_unchanged=True,read_only_guard_enabled=True)
    except BaseException as error:
        result.update(status='FAIL_READ_ONLY_SOURCE_VALIDATION',error=repr(error),calls=calls,
            executed=executed,all_read_files_unchanged=False)
        raise
    finally:
        state['active']=False;sys.meta_path.remove(finder)
        result['elapsed_s']=time.monotonic()-started
        return_result_path=Path(os.environ['NSSOC_VALIDATOR_REPORT'])
        return_result_path.parent.mkdir(parents=True,exist_ok=True)
        return_result_path.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ['status','elapsed_s']}),flush=True)
    return result
if __name__=='__main__':run('check_cdr_sampler_settling_v32_streamed_sources')
