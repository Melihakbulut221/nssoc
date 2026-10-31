#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded observer telemetry only; it never changes a geometry or acceptance decision."""
import faulthandler,json,sys,time
from pathlib import Path
import mainchip_drt_obstacle_contract as k
STAGES=("database-load","native-census","diode-connections","native-api-evidence",
 "endpoint-identity","endpoint-encoding","endpoint-wire-projection","endpoint-wire-shapes",
 "endpoint-iterm-pins","endpoint-bterm-pins","endpoint-special-wires","block-terminal-census")
BATCH=1024
CURSOR_ENDPOINT="VPWR"
CURSOR_START=65536
CURSOR_STOP=66560
CURSOR_OPERATIONS=("before-identity","identity-read","connection-checked","before-pin-geometry","pin-geometry-fed","complete-item")
CURSOR_MAX_ROWS=(CURSOR_STOP-CURSOR_START)*len(CURSOR_OPERATIONS)
class Progress:
    def __init__(self,emit,clock=time.monotonic,cursor_emit=None):
        self.emit=emit;self.clock=clock;self.started=clock();self.last=self.started
        self.sequence=0;self.stage=None;self.endpoint=None;self.items=0;self.active=False
        self.cursor=OperationCursor(cursor_emit if cursor_emit is not None else lambda row:None)
    def event(self,event):
        now=self.clock();k.q.require(now>=self.last,"monotonic progress clock")
        self.last=now
        row=dict(sequence=self.sequence,event=event,stage=self.stage,endpoint=self.endpoint,
          completed_items=self.items,elapsed_seconds=now-self.started,complete=event=="complete",**k.FLAGS)
        self.emit(row);self.sequence+=1
    def begin(self,stage,endpoint=None):
        k.q.require(stage in STAGES and not self.active,"known exclusive observer substage")
        k.q.require(endpoint is None or type(endpoint)is str and endpoint,"exact optional endpoint name")
        self.stage=stage;self.endpoint=endpoint;self.items=0;self.active=True;self.event("begin")
    def tick(self):
        k.q.require(self.active,"progress item requires active substage")
        self.items+=1
        if self.items%BATCH==0:self.event("checkpoint")
    def end(self):
        k.q.require(self.active,"progress completion requires active substage")
        self.event("complete");self.active=False
    def item_begin(self):
        k.q.require(self.active and self.stage=="endpoint-iterm-pins","ITerm cursor only in its exact stage")
        self.cursor.begin(self.endpoint,self.items)
    def item_mark(self,operation,instance=None,terminal=None):
        self.cursor.mark(operation,instance,terminal)
    def item_end(self):
        self.cursor.end()
class OperationCursor:
    """Only the observed VPWR batch window is sampled, never a proven crash index."""
    def __init__(self,emit):
        self.emit=emit;self.active=False;self.selected=False;self.operation=0
        self.sequence=0;self.last_selected=None;self.endpoint=None;self.ordinal=None
        self.instance=None;self.terminal=None
    def begin(self,endpoint,ordinal):
        k.q.require(not self.active and type(endpoint)is str and endpoint and type(ordinal)is int and ordinal>=0,"exact inactive cursor item")
        self.active=True;self.endpoint=endpoint;self.ordinal=ordinal;self.operation=0
        self.instance=None;self.terminal=None
        self.selected=endpoint==CURSOR_ENDPOINT and CURSOR_START<=ordinal<CURSOR_STOP
        if self.selected:
            expected=CURSOR_START if self.last_selected is None else self.last_selected+1
            k.q.require(ordinal==expected,"complete ordered cursor window without duplicates")
            self.last_selected=ordinal
        self.mark("before-identity")
    def mark(self,operation,instance=None,terminal=None):
        k.q.require(self.active and self.operation<len(CURSOR_OPERATIONS)and operation==CURSOR_OPERATIONS[self.operation],"exact cursor operation order")
        if operation=="before-pin-geometry":
            k.q.require(type(instance)is str and instance and type(terminal)is str and terminal,"actual named ITerm cursor")
            self.instance=instance;self.terminal=terminal
        else:k.q.require(instance is None and terminal is None,"identity supplied at exactly its established seam")
        if self.selected:
            k.q.require(self.sequence<CURSOR_MAX_ROWS,"bounded complete candidate cursor window")
            row=dict(sequence=self.sequence,endpoint=self.endpoint,zero_based_ordinal=self.ordinal,
              operation=operation,instance=self.instance,terminal=self.terminal,
              candidate_window=[CURSOR_START,CURSOR_STOP],exact_crash_index_claimed=False,**k.FLAGS)
            self.emit(row);self.sequence+=1
        self.operation+=1
    def end(self):
        self.mark("complete-item");self.active=False
def cursor_emitter(out):
    out=Path(out)
    def emit(row):
        raw=(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        with(out/"iterm-operation-events.jsonl").open("ab")as stream:stream.write(raw)
        target=out/"iterm-operation-cursor.json";tmp=out/"iterm-operation-cursor.json.partial"
        tmp.write_bytes(k.q.encode(row));tmp.replace(target)
    return emit
def emitter(out):
    out=Path(out)
    def emit(row):
        raw=(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        with(out/"substage-events.jsonl").open("ab")as stream:stream.write(raw)
        target=out/"substage-progress.json";tmp=out/"substage-progress.json.partial"
        tmp.write_bytes(k.q.encode(row));tmp.replace(target)
    return emit
def start_stacks():
    """Install fatal-only diagnostics if absent; never alter an existing handler."""
    prior=faulthandler.is_enabled()
    state=dict(previously_enabled=prior,installed=False,restored=False)
    if not prior:
        try:faulthandler.enable(file=sys.stderr,all_threads=False)
        except BaseException as primary:
            try:
                if faulthandler.is_enabled():faulthandler.disable()
            except BaseException as cleanup:primary.add_note("fatal-handler installation cleanup failed: "+repr(cleanup))
            raise
        state["installed"]=True
    return state
def stop_stacks(state):
    k.q.require(type(state)is dict and set(state)=={"previously_enabled","installed","restored"}
      and all(type(v)is bool for v in state.values())and state["installed"]is not state["previously_enabled"]
      and state["restored"]is False,"exact outstanding diagnostic ownership")
    if state["installed"]:faulthandler.disable()
    state["restored"]=True
