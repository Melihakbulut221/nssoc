#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inspect exact banked repair paths in cloud; preserve every original violation."""
import hashlib,json,math,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_postcts import api,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-corrpre-banked-paths'
RUN=39030330882
HEAD='29aa2927dc3a16822ea8fad4cd0865de1f509623'
SUMMARY='89a9520ad6022ff0112045ab086e57c843ad3c6a2609e31c551179205b3121db'
PARTS='2e3ca4b78ad1feb5251390cf8671b0c8ec187194e222803d1dfa5db481b10953'

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
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,
        full_phy_accepted=False,scope='Exact saved NEW banked pre/post repair native paths. Read-only placement-estimate diagnosis, not all-endpoint census, routed STA, repair or serial PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=controls()
        run=api('actions/runs/'+str(RUN))
        assert run['status']=='completed' and run['conclusion']=='success' and run['head_sha']==HEAD and run['run_attempt']==1
        receipt=json.loads((ROOT/'docs/evidence/corrpre-banked-repair-20261017.json').read_text())
        assert receipt['summary_sha256']==SUMMARY and receipt['parts_sha256']==PARTS
        prior=receipt['report'];assert prior['source_head']==HEAD and prior['sources_unchanged'] and prior['returncode']==0
        assert prior['status']=='COMPLETE_NATIVE_BANKED_POSTCTS_REQUIRES_EQUIVALENCE_ROUTING_EXTRACTED_STA'
        names=[n for n in prior['outputs']if n.endswith('.rpt') or n.endswith('.log')]
        restored,proof=reports.restore_report('corrpre-banked-postcts',RUN,SUMMARY,PARTS,OUT/'native',names)
        assert restored==prior
        r['source']=proof;r['measurements']=prior['measurements'];r['repaired_odb_sha256']=prior['repaired_odb_sha256'];save()
        records={};worst={}
        for phase,corners in prior['measurements'].items():
            for corner,meta in corners.items():
                for kind in ('max','min'):
                    name=meta['directory']+'/'+kind+'.rpt'
                    rows=paths((OUT/'native'/name).read_text())
                    key=phase+'-'+corner+'-'+kind
                    records[key]=dict(count=len(rows),paths=rows,source_report=name,sha256=prior['outputs'][name])
                    worst[key]=sorted(rows,key=lambda x:x['slack_ns'])[:2]
        (OUT/'all-native-paths.json').write_text(json.dumps(records,indent=2)+'\n')
        r['worst_paths']=worst
        r['repair_messages']={}
        for name in names:
            if name.endswith('.log') and ('resizer' in name or name=='native.log'):
                lines=(OUT/'native'/name).read_text(errors='replace').splitlines()
                r['repair_messages'][name]=[l for l in lines if any(w in l.lower() for w in ('iteration','inserted','resized','repair','warning','wns','tns'))][-120:]
        assert all(sha(OUT/'native'/n)==prior['outputs'][n] for n in names)
        r.update(status='COMPLETE_NEW_BANKED_NATIVE_PATH_REVIEW_NOT_TIMING_CLOSURE',sources_unchanged=True,source_run=RUN)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
