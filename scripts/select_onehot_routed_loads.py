#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Select measured weak data drivers after launch and before arrival, never clock paths."""
import re

def select(text):
    drivers={}
    for p in re.split(r'(?m)(?=^Startpoint:)',text):
        if not p.startswith('Startpoint:'):continue
        start=p.splitlines()[0].removeprefix('Startpoint:').strip().split(' (')[0]
        end=re.search(r'(?m)^Endpoint:\s*(\S+)',p)
        slack=re.search(r'(?m)^\s*([-+]?\d+(?:\.\d+)?)\s+slack\s+\(VIOLATED\)',p)
        group=re.search(r'(?m)^Path Group:\s*(.+)',p)
        if not slack or float(slack[1])>=0:continue
        assert end and group
        in_data=False
        for line in p.split('data arrival time')[0].splitlines():
            words=line.split()
            if len(words)<7 or words[-2]not in ('^','v') and not words[-1].startswith('('):continue
            # Launch point appears after expanded source clock tree. This avoids
            # mistaking high-load CTS buffers for data-path repair candidates.
            if len(words)>=2 and words[-2]in (start+'/Q',start+'/Q_N',start):in_data=True
            if not in_data:continue
            m=re.fullmatch(r'\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[\^v]\s+(\S+)\s+\((sg13g2_\S+)\)',line)
            if not m:continue
            fan,cap,slew,delay,total,pin,master=m.groups();fan=int(fan);cap=float(cap);delay=float(delay)
            if cap<.1 or delay<1 or fan<1 or not master.endswith(('_1','_2')):continue
            if any(k in master for k in ('df','latch','dly','clk','lgcp')):continue
            name,term=pin.rsplit('/',1)
            if term not in ('X','Y')or name.startswith(('clkbuf','clknet')):continue
            row=drivers.setdefault(pin,dict(instance=name,pin=term,master=master,reported_fanout=fan,observations=[]))
            assert row['master']==master and row['reported_fanout']==fan
            witness=dict(startpoint=start,endpoint=end[1],group=group[1].strip(),slack_ns=float(slack[1]),cap_pf=cap,stage_delay_ns=delay,native_line=line)
            if witness not in row['observations']:row['observations'].append(witness)
    result=sorted(drivers.values(),key=lambda x:(-max(v['stage_delay_ns']for v in x['observations']),x['instance']))
    assert len({x['instance']for x in result})==len(result)
    return result

def controls():
    pre='Startpoint: launch\nEndpoint: end\nPath Group: pcie_clk_i\n'
    clk=' 2 0.4 1.0 2.0 2.0 ^ clkbuf_fake/X (sg13g2_buf_1)\n'
    q=' 2 0.4 1.0 2.0 4.0 ^ launch/Q (sg13g2_dfrbpq_1)\n'
    gate=' 2 0.4 1.0 2.0 6.0 ^ actual/Y (sg13g2_nor2_1)\n'
    post=' 6.0 data arrival time\n'+gate+' -1.0 slack (VIOLATED)\n'
    assert [r['instance']for r in select(pre+clk+q+gate+post)]==['actual']
    assert select(pre+clk+gate+post)==[]
    assert select(pre+clk+q+gate+post.replace('-1.0 slack (VIOLATED)','1.0 slack (MET)'))==[]
    assert select(pre+clk+q+post)==[]
    return dict(clock_before_launch_excluded=True,post_arrival_capture_tree_excluded=True,nonviolating_path_excluded=True,actual_data_gate_selected=True)
