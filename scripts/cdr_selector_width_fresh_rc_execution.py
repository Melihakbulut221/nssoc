#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate disabled execution authority for unchanged width fresh-RC sources."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import types
import cdr_selector_width_fresh_rc_admission as original
import cdr_selector_width_fresh_rc_legacy as stages
import ensure_cloud_tested_source_release as release
from wait_cloud_tested_source_release import wait

ROOT=original.ROOT
OUT=original.OUT
GROUP=original.GROUP
METHOD=ROOT/"scripts/cdr-selector-width-fresh-rc-execution-methods.json"
LEGACY_METHOD=original.METHOD
LEGACY_SHA="a18748a2b50ef1aced5a586d7410c54265217709443bd242ad044c277311d729"
WORKERS={'binding': 'scripts/cloud_cdr_selector_width_fresh_binding.py', 'rc': 'scripts/cloud_cdr_selector_width_fresh_wire_rc.py', 'capture': 'scripts/cloud_cdr_selector_width_fresh_mim_capture.py', 'audit': 'scripts/cloud_cdr_selector_width_fresh_mim_audit.py', 'precision': 'scripts/cloud_cdr_selector_width_fresh_mim_precision.py'}
ENTRIES={'binding': 'scripts/cloud_cdr_selector_width_fresh_binding_entry.py', 'rc': 'scripts/cloud_cdr_selector_width_fresh_wire_rc_entry.py', 'capture': 'scripts/cloud_cdr_selector_width_fresh_mim_capture_entry.py', 'audit': 'scripts/cloud_cdr_selector_width_fresh_mim_audit_entry.py', 'precision': 'scripts/cloud_cdr_selector_width_fresh_mim_precision_entry.py'}
WORKER_SHA={'binding': '2f451a43dd1cd86da99e5bbe88b98ef8efb12f8cdfe65ff79f214c00fc2916f8', 'rc': '7e890a808ed69bf6e5cf191fd25c671d65b22f157063481b828dd759fe981a5f', 'capture': '161f02685bb84b99bcd089b9f9763000f58bc8aa69686a2faa09901448746499', 'audit': 'f4dce6cee96d8317f14b1171e01fd3250ed78bc38ad4dc295597bcfdc0e6e899', 'precision': 'de6377fb842f03c168311a5289b1f7b6e2153eb38cc42eb5c7f03fc0cb7841e3'}
RESERVATION=ROOT/"hw/soc/out/cdr-selector-width-fresh-rc-preflight/reservation.json"
RESERVATION_ENV="CDR_WIDTH_RC_RESERVATION_SHA256"
NATIVE=original.NATIVE_FLAGS
FALSE=original.FALSE
SCOPE="UNCHANGED_WIDTH_CURRENT75_FRESH_RC_EXECUTION_WITH_SEPARATE_AUTHORITY"
require=original.require
regular=original.regular
sha=original.sha
read_json=original.read_json
_ORIGINAL_AUTHORIZE=original.authorize
_ORIGINAL_WORKERS=dict(stages.WORKERS)

def atomic(path,value):
    path=Path(path)
    require(not path.is_symlink(),"Symlink atomic result")
    for parent in path.parents:require(not parent.is_symlink(),"Symlink atomic ancestor")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".incomplete."+secrets.token_hex(16))
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with temp.open("xb")as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
write=atomic

def validate_authorizations(method):
    require(method["schema"]=="cdr-selector-width-fresh-rc-execution-v1"and
      method["scope"]==SCOPE,"Wrong new execution scope")
    for name in NATIVE+FALSE+("source_controls_authorized","controller_readiness"):
        require(type(method[name])is bool,"Nonboolean new execution authorization")
    require(len({method[k]for k in NATIVE})==1,"Split new execution authorization")
    require(all(method[k]is False for k in FALSE),"Unsupported new execution authority")
    require(not method[NATIVE[0]]or method["source_controls_authorized"]is
      method["controller_readiness"]is True,"Unqualified new execution controller")
    return method

def methods():
    method=validate_authorizations(read_json(METHOD))
    legacy=original.methods()
    require(sha(LEGACY_METHOD)==LEGACY_SHA and len(legacy["protected_sha256"])==1130,
      "Historical disabled method changed")
    require(legacy["controller_readiness"]is False and
      all(legacy[k]is False for k in NATIVE),"Historical authority was activated")
    for name,h in legacy["protected_sha256"].items():
        require(method["protected_sha256"].get(name)==h,"Inherited protection changed: "+name)
    require(method["protected_sha256"].get(str(LEGACY_METHOD.relative_to(ROOT)))==LEGACY_SHA,
      "Historical method not protected")
    for name,h in method["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and
          sha(regular(ROOT,name))==h,"Changed execution source: "+name)
    return method

def context(method):
    validate_authorizations(method)
    require(ROOT==Path("/home/runner/work/nssoc/nssoc")and
      os.environ.get("GITHUB_ACTIONS")=="true"and
      os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"and
      os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and
      os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and
      os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First exact hosted execution required")
    release.context(GROUP,os.environ)
    require(method["controller_readiness"]is True and
      all(method[k]is True for k in NATIVE),"Fresh RC execution is disabled")
    return method

def validate_reservation(value,method):
    tag,head=release.context(GROUP,os.environ)
    require(value["schema"]=="width-fresh-rc-reservation-v1"and
      value["source_head"]==head and type(value["run_id"])is int and
      value["run_id"]==int(os.environ["GITHUB_RUN_ID"])and
      value["run_attempt"]==1 and type(value["run_attempt"])is int,
      "Reservation execution identity changed")
    require(value["method_sha256"]==sha(METHOD)and
      value["legacy_method_sha256"]==LEGACY_SHA,"Reservation method changed")
    proof=release.validate_release(value["release"],value["ref"],tag,head)
    require(proof["existing_assets"]==[]and value["empty_before_dependencies"]is True
      and value["creation_attempted"]is False,"Reservation was not empty before dependencies")
    return proof

def reservation(method):
    path=regular(ROOT,str(RESERVATION.relative_to(ROOT)))
    require(re.fullmatch("[0-9a-f]{64}",os.environ.get(RESERVATION_ENV,""))and
      sha(path)==os.environ[RESERVATION_ENV],"Missing or changed reservation receipt")
    value=read_json(path);proof=validate_reservation(value,method)
    return dict(receipt_sha256=sha(path),receipt=value,validated=proof,
      validation="offline exact pre-dependency release/ref and current source/method context")

def authorize():
    method=context(methods());reservation(method);return method

def preflight():
    method=context(methods())
    require(not RESERVATION.exists()and not RESERVATION.is_symlink(),
      "Preflight receipt already exists")
    wait(GROUP,os.environ,emit=lambda *a,**k:print(*a,file=sys.stderr,**k))
    tag,head=release.context(GROUP,os.environ)
    value=dict(schema="width-fresh-rc-reservation-v1",source_head=head,
      run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,
      method_sha256=sha(METHOD),legacy_method_sha256=LEGACY_SHA,
      release=release.api("releases/tags/"+tag),ref=release.api("git/ref/tags/"+tag),
      empty_before_dependencies=True,creation_attempted=False)
    validate_reservation(value,method);atomic(RESERVATION,value)
    return dict(receipt=str(RESERVATION),sha256=sha(RESERVATION),reservation=value)

def publication_authorize():
    # Preserve failure bytes even when methods() was the failing integrity gate.
    method=context(validate_authorizations(read_json(METHOD)))
    reservation(method)
    tag,head=release.context(GROUP,os.environ)
    return release.validate_release(release.api("releases/tags/"+tag),
      release.api("git/ref/tags/"+tag),tag,head)

@contextlib.contextmanager
def worker_scope():
    authorize()
    require(original.authorize is _ORIGINAL_AUTHORIZE and stages.WORKERS==_ORIGINAL_WORKERS,
      "Worker authority namespace already changed")
    previous_authorize=original.authorize;previous_workers=stages.WORKERS
    original.authorize=authorize;stages.WORKERS=dict(ENTRIES)
    try:yield
    finally:
        original.authorize=previous_authorize;stages.WORKERS=previous_workers

def worker_namespace(stage):
    require(stage in WORKERS,"Unknown exact numerical worker")
    path=regular(ROOT,WORKERS[stage]);raw=path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==WORKER_SHA[stage],"Changed numerical worker bytes")
    entry=regular(ROOT,ENTRIES[stage])
    # Only __file__ changes the original self-spawn path; all function bodies
    # compile from the unchanged protected original bytes and filename.
    return raw,path,dict(__name__="__main__",__file__=str(entry),
      __package__=None,__builtins__=__builtins__)

def entry(stage):
    with worker_scope():
        raw,path,namespace=worker_namespace(stage)
        exec(compile(raw,str(path),"exec"),namespace)

def restore():
    # original.restore and its nested graph restore use their exact code objects.
    with worker_scope():
        return original.restore()
