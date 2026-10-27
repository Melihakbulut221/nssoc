#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Orchestration evidence only; never changes numerical or geometry decisions."""
import hashlib,json,os,sys,traceback
from pathlib import Path
def error_record(error):
    return dict(type=type(error).__name__,error=repr(error),
        traceback=''.join(traceback.format_exception(type(error),error,error.__traceback__)))
def require(value,message):
    if not value:raise AssertionError(message)
def sha(path):
    path=Path(path)
    for item in (path,*path.parents):require(not item.is_symlink(),'Symlink in terminal evidence')
    require(path.is_file(),'Nonregular terminal evidence')
    with path.open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    require(not path.is_symlink()and not temporary.exists()and not temporary.is_symlink(),
        'Occupied or nonregular atomic result destination')
    encoded=json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n'
    with temporary.open('x')as stream:
        stream.write(encoded);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
def inventory(out,result_name='result.json'):
    require(out.is_dir()and not out.is_symlink(),'Nonregular terminal output root')
    result={}
    for path in out.rglob('*'):
        require(not path.is_symlink(),'Symlink in terminal inventory')
        if path.is_dir():continue
        require(path.is_file(),'Nonregular terminal output')
        if path!=out/result_name:result[str(path.relative_to(out))]=sha(path)
    return result
def preserve_fragment(out,result,stage,result_name='result.json'):
    temporary=out/(result_name+'.tmp')
    if not(temporary.exists()or temporary.is_symlink()):return
    require(not temporary.is_symlink()and temporary.is_file(),'Nonregular atomic result fragment')
    original_hash=sha(temporary);original_size=temporary.stat().st_size
    directory=out/'terminal-save-fragments'
    require(not directory.is_symlink(),'Symlink atomic fragment directory')
    directory.mkdir(exist_ok=True);require(directory.is_dir(),'Non-directory atomic fragment destination')
    serial=0
    while True:
        retained=directory/(result_name+'.tmp.%06d'%serial)
        try:os.link(temporary,retained,follow_symlinks=False);break
        except FileExistsError:serial+=1
    record=dict(stage=stage,source=temporary.name,retained=str(retained.relative_to(out)),
        bytes=original_size,sha256=original_hash,source_name_removed=False)
    result.setdefault('retained_atomic_fragments',[]).append(record)
    require(sha(temporary)==sha(retained)==original_hash and
        temporary.stat().st_size==retained.stat().st_size==original_size,'Changed atomic result fragment')
    temporary.unlink();record['source_name_removed']=True
def finalize(out,result,save,guards=(),primary=None,result_name='result.json'):
    errors=[];actions=[]
    result['status_before_terminal']=result['status']
    result['terminal_finalization_complete']=False
    result['active_primary_exception_before_terminal']=None if primary is None else error_record(primary)
    def attempt(label,call):
        try:call();actions.append(dict(action=label,completed=True))
        except BaseException as error:
            errors.append((label,error));actions.append(dict(action=label,completed=False,**error_record(error)))
    def outputs():
        result['terminal_inventory_complete']=False
        result['outputs']=inventory(out,result_name)
        result['terminal_inventory_complete']=True
    def sync():
        result['terminal_actions']=actions
        result['terminal_errors']=[dict(action=label,**error_record(error))for label,error in errors]
    for label,call in guards:attempt(label,call)
    attempt('preserve_preexisting_atomic_fragment',lambda:preserve_fragment(out,result,'before_final_save',result_name))
    attempt('complete_output_inventory',outputs)
    sync()
    if errors or primary is not None:result['status']='FAIL_CURRENT_POSTROUTE_TERMINAL'
    result['terminal_finalization_complete']=not errors
    result['terminal_save_attempted']=False
    try:
        temporary=out/(result_name+'.tmp')
        require(not(temporary.exists()or temporary.is_symlink()),'Unretained atomic result fragment prevents overwrite')
        result['terminal_save_attempted']=True;save()
    except BaseException as error:
        errors.append(('save_result',error));result['status']='FAIL_CURRENT_POSTROUTE_TERMINAL_SAVE'
        result['terminal_finalization_complete']=False
        attempt('preserve_failed_save_fragment',lambda:preserve_fragment(out,result,'after_failed_save',result_name))
        attempt('refresh_failed_save_inventory',outputs);sync()
        try:print(json.dumps(dict(unsaved_terminal_postroute_result=result),sort_keys=True,allow_nan=False),file=sys.stderr,flush=True)
        except BaseException as emission_error:
            emergency=dict(status='FAIL_UNSAVED_TERMINAL_REPORT_EMISSION',result_repr=repr(result),
                save_error=error_record(error),emission_error=error_record(emission_error))
            try:print(json.dumps(emergency,sort_keys=True),file=sys.stderr,flush=True)
            except BaseException:pass
    return primary if primary is not None else(errors[0][1]if errors else None)
def finalize_worker(out,result,save):
    import mainchip_current_postroute_admission as admission
    primary=sys.exception()
    failure=finalize(out,result,save,[('protected_sources',admission.methods)],primary)
    if failure is not None and primary is None:raise failure
