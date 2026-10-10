# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Sparse native callback records and exact source-bound write-frontier guards."""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_npu_write_trace as trace


def native_observation(tmp_path,width=4):
    compiler=shutil.which('iverilog');runtime=shutil.which('vvp')
    assert compiler and runtime
    # The real buffer/XOR reconvergence has two callbacks for each pulse.
    monitor=f"""nssoc_npu_write_event_trace #(.WIDTH({width}),.START(2),.LAST(4)) obs(
.clk_i(clk),.cycle_i({{32'b0,cycles}}),.signals_i({{{width-4}'b0,y,b,a}}));
""" if width>4 else """nssoc_npu_write_event_trace #(.WIDTH(4),.START(2),.LAST(4)) obs(
.clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({y,b,a}));
"""
    source="""`timescale 1ns/1ps
module tiny;
reg clk=0;integer cycles=0;reg a=0;wire [1:0] b;wire y;
assign b[0]=a;buf(b[1],b[0]);xor(y,a,b[1]);
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
always @(negedge clk) #0.002 $display("SIGNATURE cycle=%0d y=%b b=%b a=%b",cycles,y,b,a);
"""+monitor+"""initial begin #15.002;a=1;#10;a=0;#30;$finish;end
endmodule
"""
    logs={}
    for name,body in [('observed',source),('baseline',source.replace(monitor,''))]:
        p=tmp_path/(name+'.v');p.write_text(body)
        cc=subprocess.run([compiler,'-g2005-sv','-s','tiny','-o',str(tmp_path/(name+'.vvp')),str(p),str(ROOT/trace.MONITOR)],capture_output=True,text=True)
        assert cc.returncode==0,cc.stderr
        rr=subprocess.run([runtime,'-i',str(tmp_path/(name+'.vvp')),'+npu_write_dir='+str(tmp_path)],capture_output=True,text=True)
        assert rr.returncode==0,rr.stdout+rr.stderr
        logs[name]=rr.stdout
    assert re.findall(r'^SIGNATURE.*$',logs['observed'],re.M)==re.findall(r'^SIGNATURE.*$',logs['baseline'],re.M)
    return logs['observed']


@pytest.mark.parametrize('width',[4,7033,7040])
def test_sparse_native_reconvergence_preserves_all_callbacks_and_settled_values(tmp_path,width):
    log=native_observation(tmp_path,width)
    row=trace.parse(log,tmp_path,2,4,width)
    assert row['events']==10 and row['samples']==3 and not row['new_unknown_transitions']
    lines=(tmp_path/'npu-write-events.log').read_text().splitlines()
    assert all(' all=' not in line for line in lines if line.startswith('EV '))
    assert len(lines)==14
    # Vectors appear only in four INIT/S records, not in every scalar callback.
    assert sum(' all=' in line for line in lines)==4


@pytest.mark.parametrize('fault',['drop','duplicate','prior','new','sample','sequence','time','window','width','summary','summary_duplicate','events','early_finish'])
def test_sparse_parser_rejects_corrupt_actual_native_history(tmp_path,fault):
    log=native_observation(tmp_path);p=tmp_path/'npu-write-events.log';lines=p.read_text().splitlines()
    if fault=='drop':lines.pop(1)
    elif fault=='duplicate':lines.insert(1,lines[1])
    elif fault=='prior':lines[1]=lines[1].replace('prior=0','prior=1')
    elif fault=='new':lines[1]=lines[1].replace('value=1','value=0')
    elif fault=='sample':lines[6]=lines[6].replace('all=0111','all=1111')
    elif fault=='sequence':lines[1]=lines[1].replace('seq=2','seq=3')
    elif fault=='time':lines[1]=lines[1].replace('15.002','9.000')
    elif fault=='window':lines[1]=lines[1].replace('cycle=2','cycle=0')
    elif fault=='width':lines[0]+='0'
    elif fault=='summary':log=''
    elif fault=='summary_duplicate':log+=log
    elif fault=='events':log=log.replace('events=10','events=11')
    else:log=log.replace('final_cycle=6','final_cycle=4')
    p.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError):trace.parse(log,tmp_path,2,4,4)


def test_frozen_ancestors_and_full_exact_source_census():
    row=trace.lock();assert len(trace.PINS)==34
    for path,h in trace.PINS.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h
    assert [(row['variants'][v]['cells'],row['variants'][v]['signals'],row['variants'][v]['sequential_boundaries']) for v in ('original','candidate')]==[(2048,7040,625),(2041,7033,625)]
    assert row['prior']['first_candidate_unknown_cycle']==1569426


@pytest.mark.parametrize('fault',['prior','bounds','cycles','window','variant','producer'])
def test_locked_source_scope_cannot_drift(monkeypatch,tmp_path,fault):
    row=copy.deepcopy(trace.lock())
    if fault=='prior':row['prior']['run_id']+=1
    elif fault=='bounds':row['bounds']['signals']+=1
    elif fault=='cycles':row['cycle_bound']-=1
    elif fault=='window':row['window'][0]-=1
    elif fault=='variant':del row['variants']['candidate']
    else:row['producer']['source_commit']='wrong'
    p=tmp_path/trace.LOCK;p.parent.mkdir(parents=True);p.write_text(json.dumps(row));monkeypatch.setattr(trace,'ROOT',tmp_path)
    with pytest.raises(ValueError):trace.lock()


def test_new_workflow_preserves_paired_failed_boot_and_original_workload():
    s=(ROOT/'.github/workflows/timing-npu-write-trace.yml').read_text()
    assert 'variant: [original, candidate]' in s and 'cancel-in-progress: false' in s
    assert s.count('include-hidden-files: true')==2 and s.count('if: always()')==2
    assert 'fetch-depth: 0' in s and 'timeout-minutes: 360' in s
    code=(ROOT/'scripts/run_cloud_npu_write_trace.py').read_text()
    assert "command.count('-DTIMEOUT_CYCLES=3000000')==1" in code
    assert "row['observed_boot_pass']=q.passed_boot(code,text)" in code
    assert "boot_failure_preserved=not row['observed_boot_pass']" in code
    assert 'force ' not in (ROOT/trace.MONITOR).read_text()
