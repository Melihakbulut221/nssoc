#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect measured logic-resize route regressions; no reroute or gate changes."""
import hashlib,json,math,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-near-driver-path-review'
def paths(text):
    starts=list(re.finditer(r'(?m)^Startpoint:',text));assert starts,'No native paths'
    found=[]
    for i,start in enumerate(starts):
        stop=starts[i+1].start() if i+1<len(starts) else len(text)
        body=text[start.start():stop]
        a=re.findall(r'(?m)^Startpoint:\s*(.+)$',body)
        b=re.findall(r'(?m)^Endpoint:\s*(.+)$',body)
        s=re.findall(r'(?m)^\s*([-+0-9.eE]+)\s+slack\s+\((VIOLATED|MET)\)',body)
        assert len(a)==len(b)==len(s)==1,'Incomplete or ambiguous native path'
        slack=float(s[0][0]);assert math.isfinite(slack)
        found.append(dict(startpoint=a[0],endpoint=b[0],slack_ns=slack,native_status=s[0][1],native_report=body))
    return found

def controls():
    good='Startpoint: a\nEndpoint: b\n -0.5 slack (VIOLATED)\n'
    assert paths(good)[0]['slack_ns']==-.5
    for bad in ('',good.replace('Endpoint: b\n',''),good.replace('slack (VIOLATED)','missing'),good+'Endpoint: c\n'):
        try:paths(bad)
        except AssertionError:pass
        else:raise AssertionError('Malformed native report accepted')
    return dict(missing_and_duplicate_fields_rejected=True)


def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,scope='Read-only exact measured routed paths and changes versus prior routed measurements. No timing repair, new extraction, clock change or acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['parser_controls']=controls()
        pinpath=ROOT/'docs/evidence/onehot-near-driver-route-result-20261019.json';pin=json.loads(pinpath.read_text())
        assert pin['run']==39243328773 and pin['source_head']=='25874ce85d044e5297a2be157eb078c2f595b9ef'
        original=pin['report']
        wanted=[n for n in original['outputs']if n.startswith('run/6-nssoc-onehotroutedsta/')and n.endswith(('.rpt','.log','.tcl','.json'))]
        assert wanted
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',wanted)
        assert prior==original and prior['sources_unchanged']and prior['returncode']==0
        assert prior['detailed_route_complete']and not prior['all_reported_timing_and_electrical_gates_met']
        r.update(source=proof,physical=dict(route_drc=prior['native_routing_drc_errors'],disconnected_pins=prior['critical_disconnected_pins'],antenna=prior['final_antenna']),
            measurements=prior['measurements'],previous_routed_measurements=prior['source_routed_measurements'],routed_topology=prior['routed_candidate_topology'],sta_script_proof=prior['native_sta_script_proof'])
        r['reports']={};r['metric_changes']={};allpaths={}
        for corner,current in prior['measurements'].items():
            old=prior['source_routed_measurements'][corner]['metrics']
            r['metric_changes'][corner]={k:dict(before=old[k],after=v,delta=v-old[k])for k,v in current['metrics'].items()if k in old and isinstance(v,(int,float))}
            out={};r['reports'][corner]=out
            for kind in ('max','min'):
                rel=current['directory']+'/'+kind+'.rpt';assert rel in wanted
                text=(OUT/'source'/rel).read_text();rows=paths(text)
                allpaths[corner+'-'+kind]=dict(source_path=rel,sha256=prior['outputs'][rel],paths=rows)
                worst=sorted(rows,key=lambda q:q['slack_ns'])[:12]
                out[kind]=dict(native_path_count=len(rows),worst_paths=worst,
                    minimum_reported_slack_ns=min(q['slack_ns']for q in rows),
                    reported_negative_path_count=sum(q['slack_ns']<0 for q in rows),
                    interpretation='Report path sample only; use native STA metrics for full endpoint violation census.')
            for name in ('checks.rpt','violator_list.rpt','clock.rpt','ws.max.rpt','ws.min.rpt'):
                rel=current['directory']+'/'+name;assert rel in wanted;text=(OUT/'source'/rel).read_text()
                out[name]=dict(sha256=prior['outputs'][rel],bytes=len(text.encode()),head=text[:24000],tail=text[-8000:])
        (OUT/'all-native-paths.json').write_text(json.dumps(allpaths,indent=2)+'\n')
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in wanted)
        r.update(status='COMPLETE_NATIVE_NEAR_DRIVER_PATH_REVIEW_NOT_TIMING_CLOSURE',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
