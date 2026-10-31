#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact 3600 s read-only budget adapter; frozen memory/exit evidence remains unchanged."""
import hashlib,inspect,types
from pathlib import Path
OBSERVATION_SECONDS=3600
CONTAINER_SECONDS=3900
OLD_GUARD='p.require(seconds in(1200,14400),"original phase or route deadline")'
NEW_GUARD='p.require(type(seconds)is int and seconds==3600,"explicit read-only observation deadline")'
RUNNER_SHA="a76bafe0809e13128af54cce41244a9935c8a54fe957de55a309a9e53cf104da"
VALIDATOR_SHA="920da4ab5a37126d6991e355478b15710242737887a83de57e0fa58e695fb9fa"
def source(function):
    return inspect.getsource(function).rstrip()+"\n"
def validator(original):
    fn=original.validate
    if hashlib.sha256(source(fn).encode()).hexdigest()!=VALIDATOR_SHA:raise ValueError("frozen command validator source")
    if original.SECONDS!=(1200,14400)or fn.__globals__is not original.__dict__:raise ValueError("frozen validator globals")
    ns=dict(original.__dict__,SECONDS=(OBSERVATION_SECONDS,))
    return types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
def runner(original):
    fn=original.supervised_run;raw=source(fn)
    if hashlib.sha256(raw.encode()).hexdigest()!=RUNNER_SHA:raise ValueError("frozen supervised runner source")
    if fn.__globals__is not original.__dict__:raise ValueError("frozen runner globals")
    if raw.count(OLD_GUARD)!=1:raise ValueError("one original budget seam")
    adapted=raw.replace(OLD_GUARD,NEW_GUARD,1)
    if adapted.count(NEW_GUARD)!=1 or adapted.replace(NEW_GUARD,OLD_GUARD,1)!=raw:raise ValueError("exact reverse budget source")
    scope=dict(original.__dict__,command_evidence=types.SimpleNamespace(validate=validator(original.command_evidence)))
    exec(compile(adapted,original.__file__,"exec"),scope)
    return scope["supervised_run"]
