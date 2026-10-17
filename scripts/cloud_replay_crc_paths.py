#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract complete critical paths from exact native repair evidence in Actions."""
import hashlib,json,os,re,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-replay-crc-paths'
RUN=39052168254
SUMMARY='11629f12b2e63ebdf4ec4b17986ecd74ca31e5f44d01f62da3925d3c765b87b3'
PARTS='773fdc951552241fbac8a8b5dade8571bc1c1f13ca30a1f2e80b23dd389eff2d'
PROOF_SHA='0febaabd9eccadfa3b665b422c4367925b53d24895ab409dbf81bcf81dfe36f7'

def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def asset(number,digest):
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(number),'-H','Accept: application/octet-stream'])
    assert hashlib.sha256(raw).hexdigest()==digest
    return json.loads(raw)

def parse_paths(text):
    blocks=re.split(r'(?m)(?=^Startpoint:)',text)[1:];assert blocks,'Native report has no path records'
    result=[]
    for block in blocks:
        def field(name):
            found=re.findall(r'(?m)^'+re.escape(name)+r':\s*(.*)$',block);assert len(found)==1,(name,found)
            return found[0]
        slacks=re.findall(r'(?m)^\s*([-+0-9.eE]+)\s+slack \((VIOLATED|MET)\)',block);assert len(slacks)==1,block[:500]
        slack=float(slacks[0][0]);assert (slack<0)==(slacks[0][1]=='VIOLATED')or slack==0
        result.append(dict(startpoint=field('Startpoint'),endpoint=field('Endpoint'),path_group=field('Path Group'),path_type=field('Path Type'),slack=slack,native_report=block.strip()))
    return result

def controls():
    sample='Startpoint: top/a\nEndpoint: top/b\nPath Group: clk\nPath Type: max\n -1.25 slack (VIOLATED)\n'
    assert parse_paths(sample)[0]['slack']==-1.25
    bad=[sample.replace('Endpoint: top/b\n',''),sample.replace('slack (VIOLATED)','slack (MET)'),sample+sample.split('Path Type: max\n')[1]]
    for text in bad:
        try:parse_paths(text)
        except AssertionError:pass
        else:raise AssertionError('Malformed native path accepted')
    return dict(positive=1,rejected=3)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,scope='Read-only extraction of exact existing native STA reports, not a new STA run or routing/signoff evidence.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['parser_controls']=controls()
        for number,path,head in [(RUN,'.github/workflows/replay-crc-postcts-cloud.yml','2f32b51eec3d0dfc0c5d695c1aec921044e6a90b'),(39054520337,'.github/workflows/replay-crc-logic-cloud.yml','f31c8ffc45f2c1f802b264b9ab1c512ce9e506f9')]:
            run=api('actions/runs/'+str(number));assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==head and run['path']==path and run['run_attempt']==1
        native=asset(651175558,SUMMARY);proof=asset(651178762,PROOF_SHA)
        assert native['source_head']=='2f32b51eec3d0dfc0c5d695c1aec921044e6a90b'and native['sources_unchanged']and native['returncode']==0
        assert proof['sources_unchanged']and proof['status']=='PASS_NEW_BANKED_CTS_TO_REPAIR_LOGIC_NOT_ROUTE_OR_TIMING_SIGNOFF'
        assert proof['proof']['retained_cells']==97707 and proof['proof']['status']=='PASS within scope'
        assert proof['sources'][1]['archive']['run']==RUN and proof['sources'][1]['archive']['summary_sha256']==SUMMARY and proof['sources'][1]['archive']['manifest_sha256']==PARTS
        assert proof['sources'][1]['native_odb_sha256']==native['repaired_odb_sha256']=='e9b9c113193ed1550d0922b503dd3b1f5b1703377f17f7911fd7e42ed6ad91a3'
        assert proof['sources'][1]['netlist_sha256']=='51944631cdad92d9ce31c4cc01674b375357f127ab5cb2cbc239968c1d146093'
        names=[p for p in native['outputs']if p.endswith('.rpt')or p.endswith('/config.json')or p.endswith('/state_out.json')or p.endswith('.sdc')]
        restored,receipt=reports.restore_report('replay-crc-postcts',RUN,SUMMARY,PARTS,OUT/'native',names);assert restored==native
        r.update(restore=receipt,logic_proof=proof,measurements=native['measurements'],native_odb_sha256=native['repaired_odb_sha256']);save()
        paths={}
        for phase,corners in native['measurements'].items():
            for corner,measurement in corners.items():
                for delay in ('max','min'):
                    name=measurement['directory']+'/'+delay+'.rpt';file=OUT/'native'/name
                    assert name in names and sha(file)==native['outputs'][name]
                    records=parse_paths(file.read_text());assert all(x['path_type']==delay for x in records)
                    records.sort(key=lambda x:x['slack'])
                    paths[phase+'/'+corner+'/'+delay]=dict(file=name,sha256=sha(file),path_count=len(records),worst_paths=records[:20],endpoint_groups=dict(Counter('/'.join(x['endpoint'].split('/')[:3])for x in records)),path_groups=dict(Counter(x['path_group']for x in records)))
        r.update(paths=paths,status='PASS_VERIFIED_NATIVE_PATH_EXTRACTION_NOT_NEW_STA_OR_SIGNOFF')
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
