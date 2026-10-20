#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Attribute measured hold regressions to native data/clock report changes.

Read-only evidence. No inferred route repair, fitted clocks or timing acceptance.
"""
import json,math,os,re
from pathlib import Path
from collections import defaultdict
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-regression'
NUMBER=r'[-+0-9.eE]+'
ROW=re.compile(r'^\s*(?:(\d+)\s+('+NUMBER+r')\s+)?('+NUMBER+r')\s+('+NUMBER+r')\s+('+NUMBER+r')\s+([\^v])\s+(\S+)\s+\((\S+)\)\s*$')
def parse_rows(text):
    rows=[]
    for line in text.splitlines():
        m=ROW.fullmatch(line)
        if not m:continue
        fanout,cap,slew,delay,arrival,edge,pin,master=m.groups()
        values=[float(x)for x in (slew,delay,arrival)]
        assert all(math.isfinite(x)for x in values)
        rows.append(dict(pin=pin,master=master,edge=edge,slew_ns=values[0],delay_ns=values[1],
          arrival_ns=values[2],fanout=int(fanout)if fanout is not None else None,
          cap_pf=float(cap)if cap is not None else None,native_line=line))
    return rows
def dissect(path):
    text=path['native_report']
    assert text.count('data arrival time')==2
    prefix,capture,_=text.split('data arrival time')
    assert 'Path Type: min'in prefix
    group=re.findall(r'(?m)^Path Group:\s*(\S+)',prefix);assert len(group)==1
    arrival=re.findall(r'^\s*('+NUMBER+r')\s+data arrival time\s*$',text,re.M)
    required=re.findall(r'^\s*('+NUMBER+r')\s+data required time\s*$',text,re.M)
    assert len(arrival)==len(required)==2
    arrival,required=float(arrival[0]),float(required[0])
    assert abs((arrival-required)-path['slack_ns'])<2e-6
    clock=parse_rows(capture)
    assert all(r['pin'].startswith('clkbuf')or r['pin'].endswith('/CLK')or r['master']=='in'or 'lgcp'in r['master']for r in clock),(path['endpoint'],'unexpected capture data row')
    nets=[]
    for i,r in enumerate(clock):
        if r['fanout']is not None or i==0:continue
        prev=clock[i-1]
        if prev['fanout']is None:continue
        nets.append(dict(driver=prev['pin'],sink=r['pin'],edge=r['edge'],net_delay_ns=r['delay_ns'],
            sink_slew_ns=r['slew_ns'],driver_cap_pf=prev['cap_pf'],driver_fanout=prev['fanout'],
            driver_master=prev['master'],sink_master=r['master'],native_driver=prev['native_line'],native_sink=r['native_line']))
    return dict(endpoint=path['endpoint'],startpoint=path['startpoint'],group=group[0],slack_ns=path['slack_ns'],
        data_arrival_ns=arrival,data_required_ns=required,capture_clock_rows=clock,
        capture_clock_arrival_ns=clock[-1]['arrival_ns']if clock else None,capture_net_segments=nets)
def controls():
    text='''Startpoint: src
Endpoint: dst
Path Group: pcie_clk_i
Path Type: min
 1.0 data arrival time
 8 0.68 0.05 0.1 0.5 ^ clkbuf_a/X (sg13g2_buf_8)
 1.29 0.68 1.18 ^ clkbuf_b/A (sg13g2_buf_8)
 2 0.1 0.08 0.25 1.43 ^ clkbuf_b/X (sg13g2_buf_8)
 0.03 0.02 1.45 ^ dst/CLK (sg13g2_dfrbpq_1)
 1.5 data required time
 1.5 data required time
 -1.0 data arrival time
 -0.5 slack (VIOLATED)
'''
    p=dict(endpoint='dst',startpoint='src',slack_ns=-.5,native_report=text)
    d=dissect(p);assert d['capture_net_segments'][0]['net_delay_ns']==.68
    bads=[dict(p,slack_ns=0),dict(p,native_report=text.replace('Path Type: min','Path Type: max')),
      dict(p,native_report=text.replace('Path Group: pcie_clk_i','')),
      dict(p,native_report=text.replace('clkbuf_b/A','data_gate/A'))]
    for bad in bads:
        try:dissect(bad)
        except AssertionError:pass
        else:raise AssertionError('Malformed path accepted')
    return dict(correct_capture_segment=True,wrong_slack_kind_group_and_capture_data_rejected=4)
def endpoint_map(rows):
    out={}
    for p in rows:
        key=p['endpoint']
        if key not in out or p['slack_ns']<out[key]['slack_ns']:out[key]=p
    return out
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,
      controller_sha256=sha(Path(__file__)),scope='Measured report paths only; clock regression attribution is not a proven repair or exhaustive endpoint census. No native CAD repeated.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=controls()
        current,cp=reports.restore_report('onehot-coverage-data-path-review',39362291106,
         'ec029baa19449a546f4a17e55749aae904820f25ed67d62b9070a3aaa84892c2',
         '4f2f156b1a075948a81c28f59f2af06f9587d190487682251e1a6001978dd054',OUT/'current',['all-native-paths.json'])
        prior,pp=reports.restore_report('onehot-critical-data-path-review',39328156931,
         '1788358f43996dc914a773b20788193b8dcd31922ff6b49aa76a828a952075d1',
         'b970228561c969ce48151089f4de2839392a418beedeab97480e7c5efa995a77',OUT/'prior',['all-native-paths.json'])
        assert current['sources_unchanged']and prior['sources_unchanged']
        assert current['source']['run']==39331918238 and prior['source']['run']==39293720171
        a=json.loads((OUT/'current/all-native-paths.json').read_text());b=json.loads((OUT/'prior/all-native-paths.json').read_text())
        assert set(a)==set(b)
        r['sources']=dict(current=cp,prior=pp);r['corners']={}
        for corner in current['reports']:
            now=a[corner+'-min']['paths'];old=b[corner+'-min']['paths']
            assert len(now)==current['reports'][corner]['min']['native_path_count']
            assert len(old)==prior['reports'][corner]['min']['native_path_count']
            nm,om=endpoint_map(now),endpoint_map(old)
            neg=[dissect(p)for p in nm.values()if p['slack_ns']<0]
            branches={};changes=[]
            for p in neg:
                before=dissect(om[p['endpoint']])if p['endpoint']in om else None
                record=dict(current=p,previous=before)
                if before:
                    assert before['group']==p['group']
                    record.update(slack_delta_ns=p['slack_ns']-before['slack_ns'],
                        data_arrival_delta_ns=p['data_arrival_ns']-before['data_arrival_ns'],
                        data_required_delta_ns=p['data_required_ns']-before['data_required_ns'],
                        same_startpoint=p['startpoint']==before['startpoint'])
                    assert abs(record['slack_delta_ns']-(record['data_arrival_delta_ns']-record['data_required_delta_ns']))<4e-6
                changes.append(record)
                oldnet={(x['driver'],x['sink'],x['edge']):x for x in before['capture_net_segments']}if before else{}
                for seg in p['capture_net_segments']:
                    key=(seg['driver'],seg['sink'],seg['edge'])
                    entry=branches.setdefault(key,dict(driver=key[0],sink=key[1],edge=key[2],observations=[]))
                    x=dict(endpoint=p['endpoint'],current=seg,previous=oldnet.get(key))
                    if x['previous']:x['net_delay_delta_ns']=seg['net_delay_ns']-x['previous']['net_delay_ns']
                    entry['observations'].append(x)
            ranked=[]
            for entry in branches.values():
                obs=entry['observations']
                entry['affected_negative_endpoints']=len({x['endpoint']for x in obs})
                entry['max_current_net_delay_ns']=max(x['current']['net_delay_ns']for x in obs)
                entry['max_delta_ns']=max((x['net_delay_delta_ns']for x in obs if 'net_delay_delta_ns'in x),default=None)
                entry['min_delta_ns']=min((x['net_delay_delta_ns']for x in obs if 'net_delay_delta_ns'in x),default=None)
                ranked.append(entry)
            ranked.sort(key=lambda x:-(max(0,x['max_delta_ns']or 0)*x['affected_negative_endpoints']))
            setup={c:endpoint_map(a[c+'-max']['paths'])for c in current['reports']}
            for entry in ranked[:20]:
                endpoints={x['endpoint']for x in entry['observations']}
                entry['setup_on_same_endpoints']={c:[dict(endpoint=e,slack_ns=setup[c][e]['slack_ns'])for e in sorted(endpoints)if e in setup[c]]for c in setup}
            r['corners'][corner]=dict(negative_reported_paths=sum(p['slack_ns']<0 for p in now),
                negative_unique_endpoints=len(neg),new_negative_endpoints=sum(p['endpoint']in om and om[p['endpoint']]['slack_ns']>=0 for p in neg),
                top_capture_branch_regressions=ranked[:20])
            (OUT/(corner+'-hold-path-changes.json')).write_text(json.dumps(changes,indent=2)+'\n')
            save()
        assert sha(OUT/'current/all-native-paths.json')==current['outputs']['all-native-paths.json']
        assert sha(OUT/'prior/all-native-paths.json')==prior['outputs']['all-native-paths.json']
        assert sha(Path(__file__))==r['controller_sha256']
        r.update(status='COMPLETE_NATIVE_CAPTURE_CLOCK_AND_DATA_REGRESSION_ATTRIBUTION_NOT_REPAIR',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
