#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Select measured weak DATA drivers, excluding launch/capture clock trees."""
import json,math,re,sys
from pathlib import Path
CORNERS=('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C')
ROW=re.compile(r'^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+[\^v]\s+(\S+)\s+\((\S+)\)\s*$')
MASTER=re.compile(r'sg13g2_(?:buf|inv|and[234]|or[234]|nand[234]b?|nor[234]b?|xor2|xnor2|a21o|a21oi|a221oi|o21ai|o21a|o211ai|a211oi|mux2)_[12]')
def data_rows(path):
    text=path['native_report']
    assert text.count('data arrival time')==2, 'Unexpected native path format'
    body=text.split('data arrival time',1)[0]
    assert 'Path Type: max' in body
    identity=re.fullmatch(r'(\S+)(?: \(input port clocked by (\S+)\))?',path['startpoint'])
    assert identity, ('Unknown native startpoint description',path['startpoint'])
    start=identity[1];input_port=identity[2] is not None;launched=False;rows=[]
    for line in body.splitlines():
        m=ROW.fullmatch(line)
        if not m:continue
        fanout,cap,slew,delay,arrival,terminal,master=m.groups()
        values=[float(v)for v in (cap,slew,delay,arrival)]
        assert all(math.isfinite(v)for v in values) and values[0]>=0 and values[1]>=0
        if terminal==start or terminal.startswith(start+'/'):
            assert (terminal==start and master=='in') if input_port else terminal.startswith(start+'/')
            assert not launched, 'Multiple launch output rows'
            launched=True
            continue
        if not launched:continue
        if '/' not in terminal:continue
        inst,pin=terminal.rsplit('/',1)
        rows.append(dict(instance=inst,pin=pin,master=master,reported_fanout=int(fanout),
            cap_pf=values[0],slew_ns=values[1],cell_delay_ns=values[2],arrival_ns=values[3],native_line=line))
    assert launched, ('No native launch row',start)
    return rows
def select(report):
    assert set(report['reports'])==set(CORNERS)
    selected={};counts={}
    for corner in CORNERS:
        paths=report['reports'][corner]['max']['worst_paths']
        assert 1<=len(paths)<=12
        counts[corner]=len(paths)
        for index,path in enumerate(paths):
            assert path['native_status']=='VIOLATED' and path['slack_ns']<0
            for row in data_rows(path):
                if not MASTER.fullmatch(row['master']) or row['pin']not in ('X','Y'):continue
                if row['cap_pf']<.07 or row['slew_ns']<.5 or row['cell_delay_ns']<.5:continue
                assert row['reported_fanout']>0
                assert not row['instance'].startswith(('clkbuf','clknet','nssoc_'))
                key=(row['instance'],row['pin'])
                target=selected.setdefault(key,dict(instance=row['instance'],pin=row['pin'],master=row['master'],
                    reported_fanout=row['reported_fanout'],observations=[]))
                assert target['master']==row['master'] and target['reported_fanout']==row['reported_fanout']
                target['observations'].append(dict(corner=corner,path_index=index,startpoint=path['startpoint'],
                    endpoint=path['endpoint'],path_slack_ns=path['slack_ns'],**row))
    targets=sorted(selected.values(),key=lambda t:(-max(o['cell_delay_ns']for o in t['observations']),t['instance'],t['pin']))
    assert 1<=len(targets)<=128
    return dict(targets=targets,path_sample_counts=counts,units=dict(cap='pF',time='ns'),
        selection_thresholds=dict(cap_pf=.07,slew_ns=.5,cell_delay_ns=.5),
        scope='Measured worst setup path sample only, all three original corners. Weak combinational DATA output drivers; no sequential, clock or macro edit. Positive buffers require native geometry, equation proof, fresh route/RC and all-corner setup/hold before any acceptance.')
def controls():
    sample='''Startpoint: ff
Endpoint: end
Path Type: max
 2 0.3 2.0 2.0 2.0 ^ clkbuf_fake/X (sg13g2_buf_1)
 2 0.3 2.0 2.0 4.0 ^ ff/Q (sg13g2_dfrbpq_1)
 2 0.3 2.0 2.0 6.0 ^ gate/Y (sg13g2_o21ai_1)
 6.0 data arrival time
 2 0.3 2.0 2.0 8.0 ^ capture/X (sg13g2_buf_1)
 6.0 data arrival time
'''
    path=dict(startpoint='ff',endpoint='end',slack_ns=-1,native_status='VIOLATED',native_report=sample)
    report=dict(reports={c:dict(max=dict(worst_paths=[path]))for c in CORNERS})
    rows=select(report)['targets']
    assert len(rows)==1 and rows[0]['instance']=='gate'
    port_sample=sample.replace('ff/Q (sg13g2_dfrbpq_1)','port (in)')
    port_path=dict(path,startpoint='port (input port clocked by pcie_clk_i)',native_report=port_sample)
    assert data_rows(port_path)==data_rows(path)
    try:data_rows(dict(port_path,startpoint='port (unrecognized description)'))
    except AssertionError:pass
    else:raise AssertionError('Unknown startpoint annotation accepted')
    for bad in (sample.replace('ff/Q','wrong/Q'),sample.replace('0.3','nan'),sample.replace('data arrival time','missing')):
        try:data_rows(dict(path,native_report=bad))
        except AssertionError:pass
        else:raise AssertionError('Malformed native path accepted')
    for master in ('sg13g2_dfrbpq_1','sg13g2_lgcp_1','sg13g2_buf_16','RM_IHPSG13_2P_256x16_c2_bm_bist'):
        assert not MASTER.fullmatch(master)
    return dict(launch_and_capture_clock_trees_excluded=True,missing_launch_nonfinite_malformed_paths_rejected=True,
        annotated_input_port_identity_and_unknown_annotation_controls=True,
        sequential_macro_strong_buffers_excluded=True,all_corners_retained=True)
if __name__=='__main__':
    print(json.dumps(controls()))
    if len(sys.argv)>1:
        selection=select(json.loads(Path(sys.argv[1]).read_text())['report'])
        print(json.dumps(dict(selected_count=len(selection['targets']),path_sample_counts=selection['path_sample_counts'])))
