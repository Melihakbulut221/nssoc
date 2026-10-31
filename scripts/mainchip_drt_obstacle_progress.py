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
STACK_SECONDS=60
class Progress:
    def __init__(self,emit,clock=time.monotonic):
        self.emit=emit;self.clock=clock;self.started=clock();self.last=self.started
        self.sequence=0;self.stage=None;self.endpoint=None;self.items=0;self.active=False
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
def emitter(out):
    out=Path(out)
    def emit(row):
        raw=(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        with(out/"substage-events.jsonl").open("ab")as stream:stream.write(raw)
        target=out/"substage-progress.json";tmp=out/"substage-progress.json.partial"
        tmp.write_bytes(k.q.encode(row));tmp.replace(target)
    return emit
def start_stacks():
    # Built-in watchdog observes Python frames even when the main thread is in native code.
    # The explicit 3600 s owner supervisor bounds this 60 s repeating diagnostic.
    faulthandler.dump_traceback_later(STACK_SECONDS,repeat=True,file=sys.stderr,exit=False)
def stop_stacks():
    faulthandler.cancel_dump_traceback_later()
